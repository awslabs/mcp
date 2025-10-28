# Scripts

This directory contains utility scripts for the MCP project.

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
