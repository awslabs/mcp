# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-06

### Changed
- Restructured project to conform to awslabs/mcp repository contribution standards
- Replaced loguru with Python standard library logging
- Updated fastmcp dependency to >=3.0.0
- Replaced flake8 with ruff for linting
- Switched from requirements.txt to pyproject.toml dependency groups
- Updated entry point to `awslabs.mwaa_mcp_server.main:main`
- Aligned code style to 100-char line length

### Added
- `.python-version` file (3.10)
- `pyrightconfig.json` for type checking
- `server.json` for hosted MCP server metadata
- `DEVELOPMENT.md` with contributor setup instructions
- Expanded test coverage for Airflow API tools, readonly mode, and token creation

### Removed
- `requirements.txt` and `requirements-dev.txt` (replaced by pyproject.toml)
- `loguru` and `httpx` dependencies
- Dead `TestAirflowClient` tests referencing removed `airflow_client.py`
