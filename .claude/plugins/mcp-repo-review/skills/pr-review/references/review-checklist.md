# PR Review Checklist for awslabs/mcp

## Project Structure
- [ ] Server code is under `src/<name>-mcp-server/`
- [ ] Source code is in `awslabs/<module_name>/` (underscores, not hyphens)
- [ ] `tests/` directory exists
- [ ] `pyproject.toml`, `README.md`, `LICENSE`, `NOTICE` present

## Package Naming and Versioning
- [ ] `pyproject.toml` name follows `awslabs.<name>-mcp-server` pattern
- [ ] Version in `__init__.py` matches `pyproject.toml` version
- [ ] `[tool.commitizen]` section present in `pyproject.toml`
- [ ] `version_files` in commitizen references both `pyproject.toml:version` and `__init__.py:__version__`

## License and Copyright
- [ ] All `.py` files start with Apache 2.0 license header
- [ ] Header text matches: `# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.`

## Entry Points
- [ ] Single entry point in `server.py` (no separate `main.py`)
- [ ] `main()` function defined in `server.py`
- [ ] `[project.scripts]` entry ends with `server:main`

## Tool Definitions
- [ ] Tool names: max 64 characters, start with letter, alphanumeric + underscores/hyphens only
- [ ] Consistent naming style within server (snake_case recommended)
- [ ] All parameters use `Field()` with descriptions
- [ ] Required parameters use `...` as default
- [ ] Optional parameters have sensible defaults and `Optional` type hint
- [ ] `Context` parameter included for error reporting

## Code Quality
- [ ] Async/await used for all MCP tool and resource functions
- [ ] `loguru` logger used (not stdlib `logging`)
- [ ] Log level configurable via `FASTMCP_LOG_LEVEL` env var
- [ ] Error handling uses try/except with `ctx.error()` reporting
- [ ] Constants in dedicated `consts.py` file

## Security
- [ ] AWS auth supports both `AWS_PROFILE` and default credentials
- [ ] Region configurable via `AWS_REGION` env var
- [ ] No hardcoded credentials or secrets
- [ ] User-provided code execution uses controlled namespaces
- [ ] Timeouts on long-running operations
- [ ] Explicit allowlists for permitted operations

## Documentation
- [ ] Comprehensive docstrings on all MCP tools
- [ ] `README.md` includes setup instructions and usage examples
- [ ] All environment variables documented in README
- [ ] `FastMCP` constructor includes `instructions` parameter

## Testing
- [ ] Unit tests exist in `tests/`
- [ ] Integration tests follow `integ_<test-name>.py` or `test_integ_*.py` naming
- [ ] `pytest-asyncio` used for async test functions
- [ ] AWS services mocked (moto or similar)
