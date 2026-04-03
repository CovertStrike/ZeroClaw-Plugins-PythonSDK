# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-XX-XX

### Added

- Initial release of the ZeroClaw Python Plugin SDK
- **`zeroclaw-plugin` CLI** for easy plugin development:
  - `zeroclaw-plugin init <name>` — Create a new plugin project
  - `zeroclaw-plugin build <source.py>` — Compile to `.wasm` and generate `plugin.toml`
- `@plugin_fn` decorator for automatic JSON marshalling
- `context` module with `session()`, `user_identity()`, and `agent_config()` functions
- `memory` module with `store()`, `recall()`, and `forget()` functions
- `messaging` module with `send()` and `get_channels()` functions
- `tools` module with `tool_call()` function
- Typed dataclasses for `SessionContext`, `UserIdentity`, and `AgentConfig`
- Comprehensive test suite
- Example plugins
- GitHub Actions for CI and automated PyPI publishing

[Unreleased]: https://github.com/CovertStrike/ZeroClaw-Plugins-PythonSDK/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/CovertStrike/ZeroClaw-Plugins-PythonSDK/releases/tag/v0.1.0
