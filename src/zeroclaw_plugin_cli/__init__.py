"""CLI tool for building ZeroClaw plugins.

Commands:
    zeroclaw-plugin init <name>   - Create a new plugin project
    zeroclaw-plugin build         - Compile plugin to .wasm and generate plugin.toml
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any


def parse_docstring_metadata(docstring: str) -> dict[str, Any]:
    """Extract metadata from docstring.

    Supports:
        Risk: low|medium|high
        Parameters: JSON schema or simple type hints
        Permissions: comma-separated list
    """
    metadata: dict[str, Any] = {}

    if not docstring:
        return metadata

    # Extract risk level
    risk_match = re.search(r'Risk:\s*(low|medium|high)', docstring, re.IGNORECASE)
    if risk_match:
        metadata['risk_level'] = risk_match.group(1).lower()

    # Extract permissions
    perm_match = re.search(r'Permissions:\s*([^\n]+)', docstring, re.IGNORECASE)
    if perm_match:
        perms = [p.strip() for p in perm_match.group(1).split(',')]
        metadata['permissions'] = [p for p in perms if p]

    # Extract parameter schema from Args section
    args_match = re.search(r'Args:\s*\n((?:\s+\w+.*\n?)+)', docstring)
    if args_match:
        props = {}
        for line in args_match.group(1).split('\n'):
            param_match = re.match(r'\s+(\w+)\s*(?:\((\w+)\))?:\s*(.+)', line)
            if param_match:
                name, type_hint, desc = param_match.groups()
                prop: dict[str, Any] = {"description": desc.strip()}
                if type_hint:
                    type_map = {
                        'str': 'string', 'string': 'string',
                        'int': 'integer', 'integer': 'integer',
                        'float': 'number', 'number': 'number',
                        'bool': 'boolean', 'boolean': 'boolean',
                        'list': 'array', 'array': 'array',
                        'dict': 'object', 'object': 'object',
                    }
                    prop['type'] = type_map.get(type_hint.lower(), 'string')
                props[name] = prop
        if props:
            metadata['parameters_schema'] = {
                'type': 'object',
                'properties': props,
            }

    return metadata


def find_plugin_functions(source_path: Path) -> list[dict[str, Any]]:
    """Parse Python source and find all @plugin_fn decorated functions."""
    source = source_path.read_text()
    tree = ast.parse(source)

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check for @plugin_fn decorator
            for decorator in node.decorator_list:
                decorator_name = None
                if isinstance(decorator, ast.Name):
                    decorator_name = decorator.id
                elif isinstance(decorator, ast.Attribute):
                    decorator_name = decorator.attr

                if decorator_name == "plugin_fn":
                    # Extract docstring
                    docstring = ast.get_docstring(node) or ""
                    first_line = docstring.split("\n")[0].strip() if docstring else f"Function {node.name}"

                    # Parse metadata from docstring
                    metadata = parse_docstring_metadata(docstring)

                    func_info = {
                        "name": node.name,
                        "description": first_line,
                        "export": node.name,
                        "risk_level": metadata.get("risk_level", "low"),
                    }

                    if "parameters_schema" in metadata:
                        func_info["parameters_schema"] = metadata["parameters_schema"]

                    if "permissions" in metadata:
                        func_info["permissions"] = metadata["permissions"]

                    functions.append(func_info)
                    break

    return functions


def format_toml_value(value: Any, indent: int = 0) -> str:
    """Format a Python value as TOML."""
    prefix = "    " * indent

    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, list):
        if all(isinstance(v, str) for v in value):
            return "[" + ", ".join(f'"{v}"' for v in value) + "]"
        return "[\n" + ",\n".join(f"{prefix}    {format_toml_value(v, indent + 1)}" for v in value) + f"\n{prefix}]"
    elif isinstance(value, dict):
        if all(isinstance(v, str) for v in value.values()):
            # Inline table for simple dicts
            items = ", ".join(f'{k} = "{v}"' for k, v in value.items())
            return "{ " + items + " }"
        # Multi-line for complex dicts
        lines = []
        for k, v in value.items():
            lines.append(f"{prefix}{k} = {format_toml_value(v, indent)}")
        return "\n".join(lines)
    return str(value)


def generate_plugin_toml(
    name: str,
    version: str,
    description: str,
    wasm_path: str,
    tools: list[dict[str, Any]],
    permissions: list[str] | None = None,
    timeout_ms: int | None = None,
    allowed_hosts: list[str] | None = None,
    filesystem_paths: dict[str, str] | None = None,
) -> str:
    """Generate plugin.toml content."""
    lines = [
        "[plugin]",
        f'name = "{name}"',
        f'version = "{version}"',
        f'description = "{description}"',
        f'wasm_path = "{wasm_path}"',
        'capabilities = ["tool"]',
    ]

    # Collect all permissions from tools
    all_permissions = set(permissions or [])
    for tool in tools:
        if "permissions" in tool:
            all_permissions.update(tool["permissions"])

    if all_permissions:
        perm_list = ", ".join(f'"{p}"' for p in sorted(all_permissions))
        lines.append(f"permissions = [{perm_list}]")

    if timeout_ms:
        lines.append(f"timeout_ms = {timeout_ms}")

    if allowed_hosts:
        hosts_list = ", ".join(f'"{h}"' for h in allowed_hosts)
        lines.append(f"allowed_hosts = [{hosts_list}]")

    lines.append("")

    # Filesystem section
    if filesystem_paths:
        lines.append("[plugin.filesystem]")
        path_items = ", ".join(f'"{k}" = "{v}"' for k, v in filesystem_paths.items())
        lines.append(f"allowed_paths = {{ {path_items} }}")
        lines.append("")

    # Tools
    for tool in tools:
        lines.append("[[tools]]")
        lines.append(f'name = "{tool["name"]}"')
        lines.append(f'description = "{tool["description"]}"')
        lines.append(f'export = "{tool["export"]}"')
        lines.append(f'risk_level = "{tool.get("risk_level", "low")}"')

        # Parameters schema
        schema = tool.get("parameters_schema", {"type": "object"})
        if schema == {"type": "object"} or not schema.get("properties"):
            lines.append('parameters_schema = { type = "object" }')
        else:
            lines.append("")
            lines.append("[tools.parameters_schema]")
            lines.append('type = "object"')
            if "properties" in schema:
                lines.append("")
                for prop_name, prop_def in schema["properties"].items():
                    lines.append(f"[tools.parameters_schema.properties.{prop_name}]")
                    for key, val in prop_def.items():
                        lines.append(f'{key} = "{val}"')

        lines.append("")

    return "\n".join(lines)


def generate_entry_point(module_name: str, functions: list[dict[str, Any]]) -> str:
    """Generate the entry point wrapper for extism-py compilation."""
    lines = [
        "import extism",
        "import json",
        f"import {module_name} as _mod",
        "",
    ]

    for func in functions:
        fn_name = func["name"]
        lines.extend([
            "@extism.plugin_fn",
            f"def {fn_name}():",
            "    raw_input = extism.input_str()",
            "    parsed = json.loads(raw_input) if raw_input else None",
            f"    result = _mod._orig_{fn_name}(parsed)",
            "    extism.output_str(json.dumps(result))",
            "",
        ])

    return "\n".join(lines)


def rewrite_source_for_build(source: str, function_names: list[str]) -> str:
    """Rewrite plugin source: remove @plugin_fn decorator and rename functions."""
    # Remove the decorator import and usage
    source = source.replace("from zeroclaw_plugin_sdk import plugin_fn", "# (build: decorator removed)")
    source = source.replace("@plugin_fn", "# (build: decorator removed)")

    # Rename functions to _orig_*
    for name in function_names:
        source = source.replace(f"def {name}(", f"def _orig_{name}(")

    return source


def find_extism_py() -> str | None:
    """Find the extism-py executable."""
    candidates = [
        "extism-py",
        os.path.expanduser("~/.local/bin/extism-py/bin/extism-py"),
        os.path.expanduser("~/.local/bin/extism-py"),
    ]

    for candidate in candidates:
        if shutil.which(candidate):
            return candidate
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def load_plugin_config(source_dir: Path) -> dict[str, Any]:
    """Load plugin.toml config if it exists (for overrides)."""
    config_path = source_dir / "plugin.toml"
    if not config_path.exists():
        return {}

    # Simple TOML parser for our subset
    config: dict[str, Any] = {}
    try:
        import tomllib  # Python 3.11+
        config = tomllib.loads(config_path.read_text())
    except ImportError:
        # Fallback: try tomli
        try:
            import tomli
            config = tomli.loads(config_path.read_text())
        except ImportError:
            pass

    return config.get("plugin", {})


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new plugin project."""
    name = args.name
    output_dir = Path(args.output or name)

    if output_dir.exists():
        print(f"Error: Directory '{output_dir}' already exists", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True)

    # Create main plugin file
    module_name = name.replace("-", "_")
    plugin_file = output_dir / f"{module_name}.py"
    plugin_file.write_text(textwrap.dedent(f'''\
        """ZeroClaw plugin: {name}

        Build with: zeroclaw-plugin build {module_name}.py
        """

        from zeroclaw_plugin_sdk import plugin_fn


        @plugin_fn
        def hello(input):
            """Say hello to someone.

            Args:
                name (str): The name to greet

            Risk: low
            """
            name = (input or {{}}).get("name", "World")
            return {{"message": f"Hello, {{name}}!"}}
    '''))

    # Create pyproject.toml
    pyproject = output_dir / "pyproject.toml"
    pyproject.write_text(textwrap.dedent(f'''\
        [project]
        name = "{name}"
        version = "0.1.0"
        description = "A ZeroClaw plugin"
        requires-python = ">=3.10"
        dependencies = ["zeroclaw-plugin-sdk"]
    '''))

    # Create README
    readme = output_dir / "README.md"
    readme.write_text(textwrap.dedent(f'''\
        # {name}

        A ZeroClaw plugin.

        ## Build

        ```bash
        cd {name}
        zeroclaw-plugin build {module_name}.py
        ```

        This produces:
        - `{module_name}.wasm` — The compiled plugin
        - `plugin.toml` — The plugin manifest

        ## Install in ZeroClaw

        Copy both files to your ZeroClaw plugins directory.

        ## Configuration

        You can customize the build with CLI flags:

        ```bash
        zeroclaw-plugin build {module_name}.py \\
            --name "{name}" \\
            --version "1.0.0" \\
            --permissions http_client,file_read \\
            --timeout 5000 \\
            --allowed-hosts "api.example.com,httpbin.org"
        ```
    '''))

    print(f"Created plugin project: {output_dir}/")
    print(f"  {module_name}.py  — Your plugin code")
    print(f"  pyproject.toml    — Project config")
    print(f"  README.md         — Documentation")
    print()
    print("Next steps:")
    print(f"  cd {output_dir}")
    print(f"  # Edit {module_name}.py")
    print(f"  zeroclaw-plugin build {module_name}.py")

    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Build a plugin to .wasm and generate plugin.toml."""
    source_path = Path(args.source)

    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}", file=sys.stderr)
        return 1

    # Find extism-py
    extism_py = find_extism_py()
    if not extism_py:
        print("Error: extism-py not found.", file=sys.stderr)
        print("Install it with:", file=sys.stderr)
        print("  curl -Ls https://raw.githubusercontent.com/extism/python-pdk/main/install.sh | bash", file=sys.stderr)
        return 1

    # Parse the source to find plugin functions
    functions = find_plugin_functions(source_path)
    if not functions:
        print(f"Error: No @plugin_fn decorated functions found in {source_path}", file=sys.stderr)
        return 1

    print(f"Found {len(functions)} plugin function(s): {', '.join(f['name'] for f in functions)}")

    # Load existing config if present
    existing_config = load_plugin_config(source_path.parent)

    # Determine output paths
    module_name = source_path.stem
    output_dir = Path(args.output) if args.output else source_path.parent
    wasm_path = output_dir / f"{module_name}.wasm"
    toml_path = output_dir / "plugin.toml"

    # Create build directory
    build_dir = Path(".zeroclaw-build")
    build_dir.mkdir(exist_ok=True)

    try:
        # Rewrite source for build
        source_content = source_path.read_text()
        function_names = [f["name"] for f in functions]
        rewritten = rewrite_source_for_build(source_content, function_names)
        (build_dir / f"{module_name}.py").write_text(rewritten)

        # Create extism_pdk shim
        (build_dir / "extism_pdk.py").write_text("from extism import *  # noqa\n")

        # Generate entry point
        entry_point = generate_entry_point(module_name, functions)
        entry_path = build_dir / "_entry.py"
        entry_path.write_text(entry_point)

        # Find SDK path for PYTHONPATH
        sdk_path = Path(__file__).parent.parent

        # Compile with extism-py
        print(f"Compiling {source_path} -> {wasm_path}")
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{build_dir}:{sdk_path}"

        result = subprocess.run(
            [extism_py, str(entry_path), "-o", str(wasm_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error: extism-py failed:\n{result.stderr}", file=sys.stderr)
            return 1

        if not wasm_path.exists():
            print(f"Error: Expected output not created: {wasm_path}", file=sys.stderr)
            return 1

        # Resolve configuration (CLI > existing config > defaults)
        plugin_name = args.name or existing_config.get("name") or module_name.replace("_", "-")
        plugin_version = args.version or existing_config.get("version") or "0.1.0"
        plugin_desc = args.description or existing_config.get("description") or f"ZeroClaw plugin: {plugin_name}"

        # Parse permissions
        permissions = None
        if args.permissions:
            permissions = [p.strip() for p in args.permissions.split(",")]
        elif "permissions" in existing_config:
            permissions = existing_config["permissions"]

        # Parse timeout
        timeout_ms = None
        if args.timeout:
            timeout_ms = args.timeout
        elif "timeout_ms" in existing_config:
            timeout_ms = existing_config["timeout_ms"]

        # Parse allowed hosts
        allowed_hosts = None
        if args.allowed_hosts:
            allowed_hosts = [h.strip() for h in args.allowed_hosts.split(",")]
        elif "allowed_hosts" in existing_config:
            allowed_hosts = existing_config["allowed_hosts"]

        # Parse filesystem paths
        filesystem_paths = None
        if args.filesystem:
            filesystem_paths = {}
            for mapping in args.filesystem.split(","):
                if "=" in mapping:
                    k, v = mapping.split("=", 1)
                    filesystem_paths[k.strip()] = v.strip()
        elif "filesystem" in existing_config and "allowed_paths" in existing_config["filesystem"]:
            filesystem_paths = existing_config["filesystem"]["allowed_paths"]

        # Generate plugin.toml
        toml_content = generate_plugin_toml(
            name=plugin_name,
            version=plugin_version,
            description=plugin_desc,
            wasm_path=wasm_path.name,
            tools=functions,
            permissions=permissions,
            timeout_ms=timeout_ms,
            allowed_hosts=allowed_hosts,
            filesystem_paths=filesystem_paths,
        )
        toml_path.write_text(toml_content)

        wasm_size = wasm_path.stat().st_size
        print(f"Created {wasm_path} ({wasm_size:,} bytes)")
        print(f"Created {toml_path}")
        print()
        print("Plugin ready! Copy both files to your ZeroClaw plugins directory.")

        return 0

    finally:
        # Clean up build directory
        shutil.rmtree(build_dir, ignore_errors=True)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="zeroclaw-plugin",
        description="Build ZeroClaw WASM plugins from Python",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init command
    init_parser = subparsers.add_parser("init", help="Create a new plugin project")
    init_parser.add_argument("name", help="Plugin name")
    init_parser.add_argument("-o", "--output", help="Output directory (default: plugin name)")

    # build command
    build_parser = subparsers.add_parser("build", help="Build plugin to .wasm and generate plugin.toml")
    build_parser.add_argument("source", help="Python source file")
    build_parser.add_argument("-o", "--output", help="Output directory (default: source directory)")
    build_parser.add_argument("-n", "--name", help="Plugin name (default: derived from filename)")
    build_parser.add_argument("-v", "--version", help="Plugin version (default: 0.1.0)")
    build_parser.add_argument("-d", "--description", help="Plugin description")
    build_parser.add_argument(
        "-p", "--permissions",
        help="Comma-separated permissions (e.g., http_client,file_read)"
    )
    build_parser.add_argument(
        "-t", "--timeout",
        type=int,
        help="Execution timeout in milliseconds"
    )
    build_parser.add_argument(
        "--allowed-hosts",
        help="Comma-separated allowed HTTP hosts (e.g., api.example.com,httpbin.org)"
    )
    build_parser.add_argument(
        "--filesystem",
        help="Filesystem path mappings (e.g., /safe=/tmp/safe,/data=/var/data)"
    )

    args = parser.parse_args()

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "build":
        return cmd_build(args)

    return 1


if __name__ == "__main__":
    sys.exit(main())
