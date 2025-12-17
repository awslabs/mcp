# AWS HealthImaging MCP Server - Project Structure

This document provides a complete overview of the project structure and all files.

## Directory Tree

```
healthimaging-mcp-server/
├── .github/
│   └── workflows/
│       ├── test.yml                    # CI/CD: Run tests on push/PR
│       └── publish.yml                 # CI/CD: Publish to PyPI on release
│
├── docs/
│   ├── API.md                          # Complete API reference for all tools
│   ├── ARCHITECTURE.md                 # System architecture and design
│   ├── QUICKSTART.md                   # Quick start guide for users
│   └── DEVELOPMENT.md                  # Development guide for contributors
│
├── examples/
│   └── example_usage.py                # Example usage of MCP tools
│
├── src/
│   └── awslabs/
│       ├── __init__.py                 # Namespace package marker
│       └── healthimaging_mcp_server/
│           ├── __init__.py             # Package initialization
│           ├── server.py               # Main MCP server implementation
│           └── tools.py                # HealthImaging tool implementations
│
├── tests/
│   ├── conftest.py                     # Pytest fixtures and configuration
│   ├── test_server.py                  # Server initialization tests
│   └── test_tools.py                   # Tool functionality tests
│
├── .gitignore                          # Git ignore patterns
├── CHANGELOG.md                        # Version history and changes
├── CONTRIBUTING.md                     # Contribution guidelines
├── LICENSE                             # Apache 2.0 license
├── Makefile                            # Development task automation
├── PROJECT_STRUCTURE.md                # This file
├── pyproject.toml                      # Project configuration and dependencies
├── README.md                           # Main project documentation
├── requirements.txt                    # Core runtime dependencies
├── requirements-dev.txt                # Development dependencies
└── SECURITY.md                         # Security policy and reporting
```

## File Descriptions

### Root Level Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, dependencies, build configuration, and tool settings (black, ruff, mypy, pytest) |
| `README.md` | Main documentation with overview, installation, configuration, and usage |
| `LICENSE` | Apache License 2.0 full text |
| `CONTRIBUTING.md` | Guidelines for contributing, code style, PR process |
| `CHANGELOG.md` | Version history following Keep a Changelog format |
| `SECURITY.md` | Security policy, vulnerability reporting, best practices |
| `Makefile` | Common development tasks (install, test, lint, format, build) |
| `requirements.txt` | Core runtime dependencies (mcp, boto3, pydantic) |
| `requirements-dev.txt` | Development dependencies (pytest, black, ruff, mypy) |
| `.gitignore` | Git ignore patterns for Python, IDEs, OS files |
| `PROJECT_STRUCTURE.md` | This file - complete project structure overview |

### Source Code (`src/awslabs/healthimaging_mcp_server/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Package initialization, version, exports |
| `server.py` | MCP server setup, tool registration, main entry point |
| `tools.py` | All HealthImaging tool implementations with boto3 integration |

### Documentation (`docs/`)

| File | Purpose |
|------|---------|
| `API.md` | Complete API reference for all tools with parameters, returns, examples |
| `ARCHITECTURE.md` | System architecture, data flow, security, scalability |
| `QUICKSTART.md` | Quick start guide for new users |
| `DEVELOPMENT.md` | Development setup, workflows, testing, debugging |

### Tests (`tests/`)

| File | Purpose |
|------|---------|
| `conftest.py` | Shared pytest fixtures (mock clients, sample data) |
| `test_server.py` | Tests for server initialization and tool registration |
| `test_tools.py` | Tests for individual tool functionality |

### Examples (`examples/`)

| File | Purpose |
|------|---------|
| `example_usage.py` | Demonstrates how to use various MCP tools |

### CI/CD (`.github/workflows/`)

| File | Purpose |
|------|---------|
| `test.yml` | Runs tests, linting, formatting, type checking on push/PR |
| `publish.yml` | Builds and publishes package to PyPI on release |

## Key Components

### 1. MCP Server (`server.py`)

- Initializes MCP server instance
- Registers all tools
- Handles stdio communication
- Main entry point for the application

### 2. Tools (`tools.py`)

Implements 8 core tools:

**Data Store Tools:**
- `list_datastores` - List all data stores
- `get_datastore` - Get data store details

**Image Set Tools:**
- `search_image_sets` - Search for image sets
- `get_image_set` - Get image set metadata
- `get_image_set_metadata` - Get detailed DICOM metadata
- `list_image_set_versions` - List image set versions

**Image Frame Tools:**
- `get_image_frame` - Get image frame information

### 3. AWS Integration

- Uses boto3 for AWS HealthImaging API calls
- Handles AWS credential resolution
- Manages error handling for AWS exceptions
- Formats responses as JSON

### 4. Testing

- Unit tests with pytest
- Mocked AWS API calls
- Fixtures for common test data
- Coverage reporting

### 5. Documentation

- User-facing: README, QUICKSTART, API reference
- Developer-facing: ARCHITECTURE, DEVELOPMENT, CONTRIBUTING
- Security: SECURITY policy
- Project: CHANGELOG, LICENSE

## Dependencies

### Runtime Dependencies

```
mcp>=0.9.0              # Model Context Protocol SDK
boto3>=1.34.0           # AWS SDK for Python
pydantic>=2.0.0         # Data validation
```

### Development Dependencies

```
pytest>=7.0.0           # Testing framework
pytest-asyncio>=0.21.0  # Async test support
black>=23.0.0           # Code formatting
ruff>=0.1.0             # Linting
mypy>=1.0.0             # Type checking
```

## Build and Distribution

### Package Structure

```
awslabs.healthimaging-mcp-server
├── awslabs/                    # Namespace package
│   └── healthimaging_mcp_server/
│       ├── __init__.py
│       ├── server.py
│       └── tools.py
```

### Entry Points

```toml
[project.scripts]
healthimaging-mcp-server = "awslabs.healthimaging_mcp_server.server:main"
```

### Build System

- **Build backend**: hatchling
- **Package format**: wheel + sdist
- **Distribution**: PyPI

## Configuration Files

### `pyproject.toml`

Contains:
- Project metadata (name, version, description)
- Dependencies
- Build system configuration
- Tool configurations (black, ruff, mypy, pytest)
- Entry points

### `.gitignore`

Ignores:
- Python artifacts (`__pycache__`, `*.pyc`)
- Build artifacts (`dist/`, `build/`)
- Test artifacts (`.pytest_cache`, `htmlcov/`)
- IDE files (`.vscode/`, `.idea/`)
- OS files (`.DS_Store`)

## Development Workflow

1. **Setup**: Clone repo, install dependencies
2. **Develop**: Make changes, add tests
3. **Test**: Run pytest, check coverage
4. **Format**: Run black
5. **Lint**: Run ruff
6. **Type Check**: Run mypy
7. **Commit**: Follow conventional commits
8. **PR**: Create pull request
9. **CI**: Automated tests run
10. **Merge**: After approval
11. **Release**: Tag version, publish to PyPI

## Usage Flow

```
User → MCP Client → MCP Server → Tools → boto3 → AWS HealthImaging
                                                         ↓
User ← MCP Client ← MCP Server ← Tools ← boto3 ← AWS HealthImaging
```

## Documentation Hierarchy

1. **README.md** - Start here for overview
2. **docs/QUICKSTART.md** - Get started quickly
3. **docs/API.md** - Detailed tool reference
4. **docs/ARCHITECTURE.md** - Understand the system
5. **docs/DEVELOPMENT.md** - Contribute to the project
6. **CONTRIBUTING.md** - Contribution guidelines
7. **SECURITY.md** - Security considerations

## Comparison with HealthLake MCP Server

This project follows the same structure as the HealthLake MCP Server:

✅ Same directory structure
✅ Same documentation files
✅ Same build configuration
✅ Same testing approach
✅ Same CI/CD setup
✅ Same code quality tools
✅ Same contribution guidelines
✅ Same security policy

## Next Steps

1. **For Users**: Start with README.md → QUICKSTART.md
2. **For Developers**: Read DEVELOPMENT.md → CONTRIBUTING.md
3. **For API Reference**: See docs/API.md
4. **For Architecture**: See docs/ARCHITECTURE.md

## Maintenance

### Regular Tasks

- Update dependencies
- Review and merge PRs
- Respond to issues
- Update documentation
- Release new versions
- Monitor security advisories

### Version Management

- Follow Semantic Versioning (SemVer)
- Update CHANGELOG.md for each release
- Tag releases in Git
- Publish to PyPI

## Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: docs/ directory
- **Examples**: examples/ directory

---

**Last Updated**: 2024-12-10
**Version**: 0.1.0
**License**: Apache 2.0
