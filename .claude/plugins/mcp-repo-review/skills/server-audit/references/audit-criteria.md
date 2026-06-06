# Server Audit Criteria

## Expected Directory Layout

```
<name>-mcp-server/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── NOTICE
├── Dockerfile (optional)
├── .pre-commit-config.yaml (optional)
├── awslabs/
│   ├── __init__.py
│   └── <module_name>/
│       ├── __init__.py      # Contains __version__
│       ├── server.py        # Entry point with main()
│       ├── models.py        # Pydantic models (optional)
│       ├── consts.py        # Constants (optional)
│       └── ...              # Additional modules
└── tests/
    ├── test_*.py            # Unit tests
    └── test_integ_*.py      # Integration tests (optional)
```

## Code Quality Criteria

### Entry Point (server.py)
- Defines `main()` function
- Handles command-line arguments
- Sets up environment and logging
- Initializes FastMCP server with `instructions` parameter
- `if __name__ == '__main__': main()` guard present

### Models (models.py)
- Pydantic BaseModel used for all data models
- Comprehensive type hints
- Field validation with `Field()` constraints
- Enums for constrained values
- Model validators where appropriate

### Constants (consts.py)
- UPPER_CASE naming
- Grouped by category
- Documented with docstrings

### Async Patterns
- All MCP tool/resource functions are `async`
- `asyncio.gather` for concurrent operations
- Non-blocking I/O for external API calls

### Security Patterns
- boto3 auth: supports AWS_PROFILE and default credentials
- Region via AWS_REGION env var
- Controlled execution: isolated namespace, timeout handlers
- Allowlists for permitted operations/modules
- Input validation for all tool parameters

### Logging
- Uses `loguru` (not stdlib logging)
- Configurable via FASTMCP_LOG_LEVEL env var
- Appropriate log levels (debug/info/warning/error)
- Context included in log messages

### Error Handling
- try/except with ctx.error() for MCP context
- Meaningful error messages
- Exceptions logged with context
