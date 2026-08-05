# Scripts

This directory contains utility scripts for the MCP project.

## migrate-mcp-v2.py

Migrates servers from MCP Python SDK v1 to v2, reversing the `mcp[cli]<2.0.0` cap added in
PR #4360. SDK 2.0.0 removed `mcp.server.fastmcp` outright and renamed `FastMCP` ->
`MCPServer`.

### Usage

```bash
scripts/migrate-mcp-v2.py                                   # dry-run report, whole fleet
scripts/migrate-mcp-v2.py --server lambda-tool-mcp-server   # one server
scripts/migrate-mcp-v2.py --apply --server iam-mcp-server   # write changes
scripts/migrate-mcp-v2.py --json                            # machine-readable
```

**Dry-run by default** — nothing is written without `--apply`.

### What it does

1. Rewrites all seven v1 import forms to `mcp.server.mcpserver[.sub]`.
2. Renames the `FastMCP` identifier to `MCPServer`, but only in files that imported it from
   `mcp.server.fastmcp` — never in files using the standalone `fastmcp` PyPI package, which
   is a different project that also exports `FastMCP`.
3. Rewrites string monkeypatch targets like `patch('mcp.server.fastmcp.FastMCP')`, renaming
   both halves (module *and* attribute) and flagging each for review.
4. Bumps the dependency to `>=2.0.0,<3.0.0`, preserving declared extras.

It does **not** touch `uv.lock` (generated — run `uv lock`), and does not move
`stateless_http=` from the constructor to `run()`; affected files are reported instead.

### Completing a migration

```bash
scripts/migrate-mcp-v2.py --apply --server <name>
cd src/<name> && uv lock && uv run pytest
```

The rename and the cap bump must land in the same commit — v2-only imports break under a
1.x resolution.

See https://github.com/awslabs/mcp/issues/4448 for the full migration plan and the list of
servers needing individual review.

## verify_package_name.py

A Python script that verifies package name consistency between `pyproject.toml` and `README.md` files.

### Usage

```bash
python3 scripts/verify_package_name.py <package_directory> [--verbose]
```

### Examples

```bash
# Basic usage
python3 scripts/verify_package_name.py src/amazon-neptune-mcp-server

# Verbose output
python3 scripts/verify_package_name.py src/amazon-neptune-mcp-server --verbose
```

### What it does

1. Extracts the package name from the `pyproject.toml` file in the specified directory
2. Searches the `README.md` file for package name references in installation instructions, including:
   - JSON configuration blocks
   - Command-line examples (`uvx`, `uv tool run`, `pip install`)
   - Cursor installation links (with Base64-encoded config)
   - VS Code installation links (with URL-encoded JSON config)
   - Docker run commands
3. Intelligently filters out false positives like:
   - AWS service references (e.g., `aws.s3@ObjectCreated`)
   - JSON configuration keys
   - Command-line flags
   - Common non-package words
4. Verifies that all package references match the actual package name from `pyproject.toml`
5. Reports any mismatches that could lead to installation errors, including line numbers for easy debugging

### Integration

This script is automatically run as part of the GitHub Actions workflow for each MCP server to ensure package name consistency.

### Dependencies

- Python 3.10+
- `tomli` package (for Python < 3.11) or built-in `tomllib` (for Python 3.11+)

The script will automatically try to use the built-in `tomllib` (Python 3.11+) first, then fall back to `tomli` if needed.

Install tomli if needed:
```bash
pip install tomli
```
