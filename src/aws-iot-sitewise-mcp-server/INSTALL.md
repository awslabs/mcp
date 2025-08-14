# Installation Guide for AWS IoT SiteWise MCP Server

This guide provides detailed instructions for installing and configuring the AWS IoT SiteWise MCP server using modern Python tools.

## Prerequisites

- Python 3.10 or higher
- AWS credentials configured for IoT SiteWise access

## Installation Options

### Option 1: UVX (Recommended for MCP Client Usage)

[UVX](https://github.com/astral-sh/uv) provides a simple way to install and run Python applications globally without virtual environment management.

```bash
# Install UV if you don't have it yet
curl -sSf https://astral.sh/uv/install | sh

# Clone the repository
git clone https://github.com/awslabs/aws-iot-sitewise-mcp.git
cd aws-iot-sitewise-mcp

# Install as a uv tool (this makes it available globally via uvx)
uv tool install .

# The server is now available globally via uvx
uvx awslabs-aws-iot-sitewise-mcp-server

# Note: The server runs silently, waiting for MCP client connections.
# You'll need to configure an MCP client to connect to it.
```

### Option 2: UV Development Setup

[UV](https://github.com/astral-sh/uv) is a fast Python package installer and resolver that significantly speeds up package installation.

```bash
# Install UV if you don't have it yet
curl -sSf https://astral.sh/uv/install | sh

# Clone the repository
git clone https://github.com/awslabs/aws-iot-sitewise-mcp.git
cd aws-iot-sitewise-mcp

# Install dependencies using uv sync
uv sync

# Install the package in development mode
uv pip install -e .

# Run the server (this will start the MCP server, waiting for MCP client connections)
uv run python -m awslabs.aws_iot_sitewise_mcp_server.server

# Note: The server runs silently, waiting for MCP client connections.
# You'll need to configure an MCP client to connect to it.
```

### Option 3: Pip

```bash
# Install from PyPI (when published)
pip install aws-iot-sitewise-mcp

# Or install from source
git clone https://github.com/awslabs/aws-iot-sitewise-mcp.git
cd aws-iot-sitewise-mcp
pip install .

# Run the server (this will start the MCP server, waiting for MCP client connections)
python -m awslabs.aws_iot_sitewise_mcp_server.server

# Note: The server runs silently, waiting for MCP client connections.
# You'll need to configure an MCP client to connect to it.
```

## AWS Configuration

You need to configure AWS credentials with proper IoT SiteWise permissions. You can use any of these methods:

### Method 1: AWS CLI (Recommended)

```bash
aws configure
```

This will prompt you for your AWS Access Key ID, Secret Access Key, default region, and output format.

### Method 2: Environment Variables

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-west-2
```

### Method 3: AWS Profiles

```bash
export AWS_PROFILE=your-profile-name
```

## MCP Client Configuration

### Claude Desktop

Add to your `claude_desktop_config.json`:

**Option 1: UVX (Recommended - requires `uv tool install .` first)**
```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uvx",
      "args": ["awslabs-aws-iot-sitewise-mcp-server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**Option 2: UV Development Setup (replace `/path/to/your/project` with your actual project path)**
```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/project/aws-iot-sitewise-mcp",
        "run",
        "python", 
        "-c",
        "import sys; sys.path.insert(0, '/path/to/your/project/aws-iot-sitewise-mcp'); from awslabs.aws_iot_sitewise_mcp_server.server import main; main()"
      ],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**Option 3: Direct Python Execution**
```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "python",
      "args": ["-m", "awslabs.aws_iot_sitewise_mcp_server.server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

### Claude Code

Configure in your workspace or global settings:

**Option 1: UVX (Recommended - requires `uv tool install .` first)**
```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uvx",
      "args": ["awslabs-aws-iot-sitewise-mcp-server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**Option 2: UV Development Setup (replace `/path/to/your/project` with your actual project path)**
```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/project/aws-iot-sitewise-mcp",
        "run",
        "python",
        "-c",
        "import sys; sys.path.insert(0, '/path/to/your/project/aws-iot-sitewise-mcp'); from awslabs.aws_iot_sitewise_mcp_server.server import main; main()"
      ],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**Notes:**
- Replace `your-profile-name` with your actual AWS profile name, or remove the `AWS_PROFILE` line to use default credentials
- For Option 2, make sure to replace `/path/to/your/project/aws-iot-sitewise-mcp` with the actual absolute path to your project directory
- The UVX option is recommended for production use as it's cleaner and doesn't require path configuration

## IAM Permissions

Your AWS credentials need permissions for IoT SiteWise operations. Here's a sample policy for testing (not for production use):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iotsitewise:*"
      ],
      "Resource": "*"
    }
  ]
}
```

For production, use the principle of least privilege by restricting actions and resources appropriately.

## Validation

To verify your installation is working correctly:

```bash
# Validate the installation
python -c "import awslabs.aws_iot_sitewise_mcp_server; print('AWS IoT SiteWise MCP server installed successfully')"

# Test AWS connectivity
python -c "import boto3; client = boto3.client('iotsitewise'); print('AWS IoT SiteWise connection successful!')"
```

## Development Setup

For development work on the package:

```bash
# Install package in development mode with development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Format code
black awslabs test
isort awslabs test

# Run type checking
mypy awslabs
```

## Troubleshooting

### AWS Credential Issues

- Verify credentials are correctly configured: `aws sts get-caller-identity`
- Check AWS region is set correctly
- Ensure IAM permissions include IoT SiteWise access

### Package Installation Issues

- Update tools: `uv self-update` or `pip install --upgrade pip`
- Check Python version: `python --version`
- Verify package imports: `python -c "import awslabs.aws_iot_sitewise_mcp_server"`

### Internal Amazon Packages

This package may reference internal Amazon packages like `requests-midway` that are not available in public repositories:

- If you're using this outside Amazon's internal environment, these dependencies are commented out in `pyproject.toml` and `requirements.txt`.
- If you're inside Amazon's environment, you may need to uncomment these dependencies or configure access to internal package repositories.

### Import Errors

- Make sure all dependencies are installed: `uv pip list` or `pip list`
- Verify the package is installed: `uv pip show aws-iot-sitewise-mcp` or `pip show aws-iot-sitewise-mcp`
- Check for package conflicts: `uv pip check` or `pip check`
