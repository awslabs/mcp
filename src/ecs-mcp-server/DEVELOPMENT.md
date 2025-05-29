# Development Guide for ECS MCP Server

This guide provides instructions for setting up your development environment, running tests, and contributing to the ECS MCP Server project. All development should comply with the guidelines in the parent repository's [DEVELOPER_GUIDE.md](../../DEVELOPER_GUIDE.md).

## Setting Up Development Environment

### Prerequisites

- Python 3.10+ (recommended installation using `uv python install 3.10`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Git](https://git-scm.com/)
- [AWS CLI](https://aws.amazon.com/cli/) with appropriate credentials configured

### Installation

#### Clone from GitHub

```bash
# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp
```

#### Using Virtual Environment

```bash
# Create and activate a virtual environment using uv
cd src/ecs-mcp-server
uv venv
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows

# Install development dependencies
uv pip install -e ".[dev]"
```

#### Configure AWS Credentials

Ensure you have AWS credentials configured with appropriate permissions:
```bash
aws configure
AWS Access Key ID [None]: your-access-key
AWS Secret Access Key [None]: your-secret-key
Default region name [None]: us-east-1
Default output format [None]: json
```

### Alternative Installation Method

You can also run the MCP server directly from a local clone of the GitHub repository:

```bash
# Clone the repository
git clone https://github.com/awslabs/ecs-mcp-server.git

# Run the server directly using uv
uv --directory /path/to/ecs-mcp-server/src/ecs-mcp-server/awslabs/ecs_mcp_server run main.py
```

## Running the Server Locally

To run the server during development:

```bash
cd src/ecs-mcp-server
python -m awslabs.ecs_mcp_server.main
```

Alternatively, you can use `uv` to run the server:

```bash
uv --directory /path/to/ecs-mcp-server/src/ecs-mcp-server/awslabs/ecs_mcp_server run main.py
```

## Configuration

Add the ECS MCP Server to your MCP client configuration:

```json
{
  "mcpServers": {
    "awslabs.ecs-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/ecs-mcp-server/src/ecs-mcp-server/awslabs/ecs_mcp_server",
        "run",
        "main.py"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "your-aws-region",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "FASTMCP_LOG_FILE": "/path/to/logs/ecs-mcp-server.log"
      }
    }
  }
}
```

### Accessing Server Logs

The ECS MCP Server supports both console logging and file logging. During development, you can:

1. **View console logs**: By default, logs are printed to the console with level determined by `FASTMCP_LOG_LEVEL`
2. **Enable file logging**: Add the `FASTMCP_LOG_FILE` environment variable to write logs to a file
3. **View log files**: Access the log file at the specified path for debugging server issues
4. **Analyze crash logs**: In case of server crashes, the log file will contain details to help diagnose the problem

To adjust log verbosity, set `FASTMCP_LOG_LEVEL` to one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.

## Testing

### Unit Tests

To run all unit tests:

```bash
cd src/ecs-mcp-server
python -m pytest tests/unit
```

To run a specific test file:

```bash
python -m pytest tests/unit/test_main.py
```

To run a specific test case with verbose output:

```bash
python -m pytest tests/unit/test_main.py::TestMain::test_server_tools -v
```

### Integration/LLM Tests

Integration tests are available in the `tests/llm_testing` directory and are run using the `run_tests.sh` script:

```bash
cd src/ecs-mcp-server/tests/llm_testing
./run_tests.sh
```

The script will:
1. Give you many test scenarios to choose from
2. Set up necessary resources for the particular test
3. Provide you with prompts to run in an LLM and the expected outputs
4. Clean up resources (with your confirmation)

### Test Coverage

To generate a test coverage report:

```bash
# Generate coverage report
python -m pytest --cov=awslabs.ecs_mcp_server tests/
```

For a detailed HTML coverage report:

```bash
python -m pytest --cov=awslabs.ecs_mcp_server --cov-report=html tests/
```

This will create an `htmlcov` directory with an interactive HTML report that you can open in your browser.

## Code Style and Linting

Use pre-commit in [DEVELOPER_GUIDE.md](../../DEVELOPER_GUIDE.md)

## Development Workflow

1. **Create a branch**: Create a new branch for your feature or fix
2. **Make changes**: Implement your changes following the code style guidelines
3. **Run tests**: Ensure all tests pass and add new tests as needed
4. **Update documentation**: Update README.md and other documentation as needed
5. **Commit changes**: Use clear commit messages (conventional commits recommended)
6. **Submit a pull request**: Open a pull request against the main branch

All changes should comply with the guidelines in the parent repository's [DEVELOPER_GUIDE.md](../../DEVELOPER_GUIDE.md). This includes following the appropriate branching strategy, commit message format, and code review process.

## Building and Publishing

To build the package:

```bash
cd src/ecs-mcp-server
python -m build
```
