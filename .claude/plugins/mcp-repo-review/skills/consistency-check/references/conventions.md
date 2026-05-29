# Monorepo Conventions

All 55 servers under `src/*-mcp-server/` must follow these conventions uniformly.

## pyproject.toml

Every server must have:

| Field | Convention | Example |
|---|---|---|
| `[project].name` | `awslabs.<name>-mcp-server` | `awslabs.aws-documentation-mcp-server` |
| `[project].version` | Semver string | `1.1.21` |
| `[project].description` | Starts with "An AWS Labs Model Context Protocol (MCP) server" | - |
| `[project].readme` | `"README.md"` | - |
| `[project].requires-python` | `">=3.10"` | - |
| `[project].license` | `{text = "Apache-2.0"}` | - |
| `[project].license-files` | `["LICENSE", "NOTICE"]` | - |
| `[project.scripts]` | Entry name matches project name, value ends in `server:main` | `"awslabs.aws-documentation-mcp-server" = "awslabs.aws_documentation_mcp_server.server:main"` |
| `[tool.commitizen]` | Present with `version_files` referencing pyproject.toml and __init__.py | - |

## Version Sync

- `__version__` in `awslabs/<module>/__init__.py` must match `[project].version` in `pyproject.toml`
- `[tool.commitizen].version` must also match

## License Headers

All `.py` files under `awslabs/` must start with the Apache 2.0 license header (13 lines starting with `# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.`).

## Directory Structure

Every server must have:
- `awslabs/` directory with `__init__.py`
- `awslabs/<module>/` with `__init__.py`, `server.py`
- `tests/` directory
- `pyproject.toml`, `README.md`, `LICENSE` at root

## Entry Points

- Single entry point in `server.py` (no `main.py`)
- `main()` function with `if __name__ == '__main__': main()` guard
- `[project.scripts]` in pyproject.toml references `server:main`

## Dependencies

Common required dependencies:
- `mcp[cli]>=1.23.0`
- `pydantic>=2.10.6`
- `loguru>=0.7.0`

## Code Style

- `ruff` for formatting and linting (config in root `.ruff.toml`)
- `pre-commit` hooks configured
- Line length: 99 characters
- Quote style: single quotes
