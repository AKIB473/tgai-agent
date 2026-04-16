# Contributing to tgai-agent

Thank you for your interest in contributing! 🎉

## Getting Started

```bash
git clone https://github.com/your-org/tgai-agent
cd tgai-agent
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Development Workflow

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feat/my-feature`
3. **Write code** + tests
4. **Run checks**: `make lint test`
5. **Commit** with a clear message (see below)
6. **Push** and open a Pull Request

## Commit Message Format

```
type(scope): short description

[optional body]
[optional footer]
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

Examples:
- `feat(plugins): add weather plugin`
- `fix(memory): handle empty history edge case`
- `docs(readme): update quickstart`

## Writing a Plugin

1. Create `src/tgai_agent/plugins/builtin/my_plugin.py`
2. Inherit from `BasePlugin`
3. Implement `execute(params, context) -> str`
4. Call `PluginRegistry.register(MyPlugin())` at module level
5. Add tests in `tests/plugins/test_my_plugin.py`

## Running Tests

```bash
pytest                    # full suite
pytest -k test_memory     # single test
pytest --cov              # with coverage
```

## Code Style

- Line length: 100
- Formatter: Black (`make fmt`)
- Linter: Ruff (`make lint`)
- Type hints on all public functions

## Reporting Bugs

Please use the GitHub issue tracker with the **bug** template.
Include: Python version, OS, error traceback, minimal reproduction steps.
