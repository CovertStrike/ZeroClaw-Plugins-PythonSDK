# zeroclaw-plugin-sdk

[![CI](https://github.com/Biztactix-Ryan/Zeroclaw-Plugin-PythonSDK/actions/workflows/ci.yml/badge.svg)](https://github.com/Biztactix-Ryan/Zeroclaw-Plugin-PythonSDK/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/zeroclaw-plugin-sdk.svg)](https://pypi.org/project/zeroclaw-plugin-sdk/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%2FApache--2.0-blue.svg)](LICENSE-MIT)

Python SDK for building [ZeroClaw](https://github.com/Biztactix-Ryan/zeroclaw) WASM plugins.

Write Python plugins that compile to WebAssembly and run inside ZeroClaw, with access to memory, messaging, tools, and session context.

## Installation

```bash
pip install zeroclaw-plugin-sdk
```

### Prerequisites

- Python 3.10+
- [extism-py](https://github.com/extism/python-pdk) — for compiling to WASM:
  ```bash
  curl -Ls https://raw.githubusercontent.com/extism/python-pdk/main/install.sh | bash
  ```

## Quick Start

### 1. Create a new plugin

```bash
zeroclaw-plugin init my-plugin
cd my-plugin
```

This creates:
```
my-plugin/
├── my_plugin.py      # Your plugin code
├── pyproject.toml    # Project config
└── README.md
```

### 2. Edit your plugin

```python
# my_plugin.py
from zeroclaw_plugin_sdk import plugin_fn

@plugin_fn
def hello(input):
    """Say hello to someone."""
    name = (input or {}).get("name", "World")
    return {"message": f"Hello, {name}!"}
```

### 3. Build it

```bash
zeroclaw-plugin build my_plugin.py
```

This produces:
- `my_plugin.wasm` — The compiled WebAssembly plugin
- `plugin.toml` — The plugin manifest for ZeroClaw

### 4. Install in ZeroClaw

Copy both files to your ZeroClaw plugins directory and restart.

That's it! Your plugin is ready to use.

### Generated Files

The build command creates two files:

**my_plugin.wasm** — Compiled WebAssembly module

**plugin.toml** — Plugin manifest:
```toml
[plugin]
name = "my-plugin"
version = "0.1.0"
description = "ZeroClaw plugin: my-plugin"
wasm_path = "my_plugin.wasm"
capabilities = ["tool"]

[[tools]]
name = "hello"
description = "Say hello to someone."
export = "hello"
risk_level = "low"
parameters_schema = { type = "object" }
```

## CLI Reference

### `zeroclaw-plugin init <name>`

Create a new plugin project with boilerplate code.

```bash
zeroclaw-plugin init my-awesome-plugin
zeroclaw-plugin init my-plugin -o /path/to/output
```

### `zeroclaw-plugin build <source.py>`

Compile a plugin to `.wasm` and generate `plugin.toml`.

```bash
zeroclaw-plugin build my_plugin.py
zeroclaw-plugin build my_plugin.py -o dist/
zeroclaw-plugin build my_plugin.py --name "My Plugin" --version "1.0.0"

# With permissions and sandboxing
zeroclaw-plugin build my_plugin.py \
    --permissions http_client,file_read \
    --timeout 5000 \
    --allowed-hosts "api.example.com,httpbin.org" \
    --filesystem "/safe=/tmp/plugin-safe"
```

Options:
- `-o, --output` — Output directory (default: source directory)
- `-n, --name` — Plugin name (default: derived from filename)
- `-v, --version` — Plugin version (default: 0.1.0)
- `-d, --description` — Plugin description
- `-p, --permissions` — Comma-separated permissions (http_client, file_read, etc.)
- `-t, --timeout` — Execution timeout in milliseconds
- `--allowed-hosts` — Comma-separated allowed HTTP hosts
- `--filesystem` — Filesystem path mappings (e.g., /safe=/tmp/safe)

## SDK Features

### `@plugin_fn` Decorator

Handles JSON serialization automatically. Your function receives parsed input and returns a dict:

```python
from zeroclaw_plugin_sdk import plugin_fn

@plugin_fn
def process(input):
    # input is already parsed from JSON
    return {"result": "done"}  # automatically serialized to JSON
```

### Docstring Metadata

The build tool extracts metadata from docstrings to generate `plugin.toml`:

```python
@plugin_fn
def fetch_data(input):
    """Fetch data from an external API.

    Args:
        url (str): The URL to fetch
        timeout (int): Request timeout in seconds

    Risk: medium
    Permissions: http_client
    """
    ...
```

This generates:
```toml
[[tools]]
name = "fetch_data"
description = "Fetch data from an external API."
export = "fetch_data"
risk_level = "medium"

[tools.parameters_schema]
type = "object"

[tools.parameters_schema.properties.url]
type = "string"
description = "The URL to fetch"

[tools.parameters_schema.properties.timeout]
type = "integer"
description = "Request timeout in seconds"
```

### Context Module

Access session and user information:

```python
from zeroclaw_plugin_sdk import context

session = context.session()
print(session.channel_name)
print(session.conversation_id)

user = context.user_identity()
print(user.username)

config = context.agent_config()
print(config.name)
```

### Memory Module

Persistent key-value storage:

```python
from zeroclaw_plugin_sdk import memory

memory.store("user_preference", "dark_mode")
result = memory.recall("user_preference")
memory.forget("user_preference")
```

### Messaging Module

Send messages and discover channels:

```python
from zeroclaw_plugin_sdk import messaging

channels = messaging.get_channels()
messaging.send(channel="discord", recipient="user123", message="Hello!")
```

### Tools Module

Call other tools registered with ZeroClaw:

```python
from zeroclaw_plugin_sdk import tools

result = tools.tool_call("web_search", {"query": "Python WASM"})
```

## Complete Example

```python
"""A smart greeter plugin using all SDK features."""

from zeroclaw_plugin_sdk import plugin_fn
from zeroclaw_plugin_sdk import context, memory, messaging, tools

@plugin_fn
def smart_greet(input):
    """Greet users with context-aware, personalized messages."""
    name = (input or {}).get("name", "friend")

    # Get session context
    session = context.session()

    # Check if we've seen this conversation before
    memory_key = f"greeted:{session.conversation_id}"
    try:
        previous = memory.recall(memory_key)
        first_visit = not previous
    except Exception:
        first_visit = True

    greeting = f"Hello, {name}! You're on {session.channel_name}."

    if first_visit:
        try:
            fact = tools.tool_call("fun_fact", {"topic": "greeting"})
            greeting += f" Fun fact: {fact}"
        except Exception:
            pass
        memory.store(memory_key, name)
    else:
        greeting += " Welcome back!"

    return {"greeting": greeting, "first_visit": first_visit}
```

Build it:
```bash
zeroclaw-plugin build smart_greeter.py --name "Smart Greeter" --description "Context-aware greeting plugin"
```

## API Reference

### Dataclasses

- **`SessionContext`** — `channel_name`, `conversation_id`, `timestamp`
- **`UserIdentity`** — `username`, `display_name`, `channel_user_id`
- **`AgentConfig`** — `name`, `personality_traits`, `identity`

### Functions

| Module | Function | Description |
|--------|----------|-------------|
| `decorator` | `plugin_fn(func)` | Decorator for plugin entry points |
| `context` | `session()` | Get current session context |
| `context` | `user_identity()` | Get current user identity |
| `context` | `agent_config()` | Get agent configuration |
| `memory` | `store(key, value)` | Store a key-value pair |
| `memory` | `recall(query)` | Recall memories by query |
| `memory` | `forget(key)` | Delete a memory entry |
| `messaging` | `send(channel, recipient, message)` | Send a message |
| `messaging` | `get_channels()` | List available channels |
| `tools` | `tool_call(tool_name, arguments)` | Invoke another tool |

## Development

```bash
git clone https://github.com/Biztactix-Ryan/Zeroclaw-Plugin-PythonSDK
cd Zeroclaw-Plugin-PythonSDK
pip install -e ".[dev]"
pytest
```

## License

Dual-licensed under MIT or Apache 2.0, at your option.

## Related Projects

- [ZeroClaw](https://github.com/Biztactix-Ryan/zeroclaw) — The main ZeroClaw project
- [Extism](https://extism.org/) — The WebAssembly plugin system this SDK builds on
