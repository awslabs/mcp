# AI3 Diagrams Expert MCP Server

An MCP server that seamlessly creates diagrams using the Python diagrams package DSL. This server allows you to generate AWS diagrams, sequence diagrams, flow diagrams, and class diagrams using Python code.

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to access the Diagram expert API

## Installation

Install the MCP server:
```bash
uv tool install --default-index=https://__token__:$GITLAB_TOKEN@gitlab.aws.dev/api/v4/projects/115863/packages/pypi/simple ai3-diagrams-expert --force 
```

Add the server to your MCP client config (e.g. `~/.cursor-server/data/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`):
```json
{
  "mcpServers": {
    "ai3-diagrams-expert": {
      "command": "uvx",
      "args": ["ai3-diagrams-expert"],
      "env": {
        "SHELL": "/usr/bin/zsh"
      }
    }
  }
}
```

### AWS Authentication

The MCP server uses the AWS profile specified in the `AWS_PROFILE` environment variable. If not provided, it defaults to the "default" profile in your AWS configuration file.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

Make sure the AWS profile has permissions to access the AWS Pricing API. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for accessing AWS services.

## Development

### Testing

The project includes a comprehensive test suite to ensure the functionality of the MCP server. The tests are organized by module and cover all aspects of the server's functionality.

To run the tests, use the provided script:

```bash
./run_tests.sh
```

Or run pytest directly:

```bash
pytest -xvs tests/
```

To run with coverage:

```bash
pytest --cov=ai3_diagrams_expert --cov-report=term-missing tests/
```

For more information about the tests, see the [tests README](tests/README.md).

### Development Dependencies

To set up the development environment, install the development dependencies:

```bash
uv pip install -e ".[dev]"
```

This will install the required dependencies for development, including pytest, pytest-asyncio, and pytest-cov.
