# Contributing to zeroclaw-plugin-sdk

Thank you for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/Zeroclaw-Plugin-PythonSDK
   cd Zeroclaw-Plugin-PythonSDK
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Create a branch for your changes:
   ```bash
   git checkout -b my-feature
   ```

## Development Workflow

### Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=zeroclaw_plugin_sdk
```

### Code Style

We use `ruff` for linting and formatting:

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/
```

### Type Checking

```bash
mypy src/
```

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Add a changelog entry under `[Unreleased]`
4. Submit a pull request with a clear description

## Code of Conduct

Be respectful and constructive in all interactions.

## Questions?

Open an issue if you have questions or need help.
