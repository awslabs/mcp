# AWS Fault Injection Service (FIS) MCP Server

This MCP server provides tools for working with AWS Fault Injection Service (FIS), allowing users to create, manage, and execute fault injection experiments.

## Overview

AWS Fault Injection Service (FIS) is a managed service that enables you to perform fault injection experiments on your AWS workloads. This MCP server provides capabilities to interact with FIS, making it easier to create and manage chaos engineering experiments.

## Security Features

### Read-Only Mode by Default

The server operates in **read-only mode by default** for enhanced security. Write operations (create, start, stop, delete) require explicit enablement with the `--allow-writes` flag.

**Benefits:**
- **Secure by Default**: Prevents accidental destructive operations
- **Explicit Enable**: Write operations require explicit enablement
- **Clear Messaging**: Blocked operations provide informative error messages

## Features

### Read-Only Operations (Always Available)
- `list_experiment_templates` - List experiment templates
- `get_experiment_template` - Get experiment template details
- `list_experiments` - List experiments
- `get_experiment` - Get experiment details
- `list_action_types` - List action types
- `generate_template_example` - Generate template examples

### Write Operations (Require --allow-writes)
- `start_experiment` - Start an experiment
- `stop_experiment` - Stop an experiment
- `create_experiment_template` - Create experiment template
- `delete_experiment_template` - Delete experiment template

## Installation and Usage

### Option 1: Using uvx (Recommended)

The easiest way to run the server is using `uvx`. This method doesn't require managing virtual environments:

```bash
# Run directly with uvx (installs and runs in one command)
uvx aws-fis-mcp

# Or run from GitHub directly
uvx --from git+https://github.com/RadiumGu/AWS-FIS-MCP.git aws-fis-mcp

# Or install from local directory
cd /home/ec2-user/mcp-servers/AWS-FIS-MCP
uvx --from . aws-fis-mcp
```

### Option 2: Using pip install

```bash
# Install globally or in a virtual environment
pip install aws-fis-mcp

# Then run
aws-fis-mcp
```

### Option 3: Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/RadiumGu/AWS-FIS-MCP.git
cd AWS-FIS-MCP
```

2. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)

3. Install Python using `uv python install 3.10`

4. Set up a virtual environment:
```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

5. Run the MCP server:
```bash
# Using the installed script
aws-fis-mcp

# Or using python -m
python -m aws_fis_mcp

# Or using uv run
uv run main.py
```

## MCP Client Configuration

### For uvx usage (Recommended):

#### Read-Only Mode (Default - Secure):
```json
{
  "mcpServers": {
    "aws_fis_mcp": {
      "command": "uvx",
      "args": ["aws-fis-mcp"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      },
      "transportType": "stdio"
    }
  }
}
```

#### With Write Operations Enabled:
```json
{
  "mcpServers": {
    "aws_fis_mcp": {
      "command": "uvx",
      "args": ["aws-fis-mcp", "--", "--allow-writes"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      },
      "transportType": "stdio"
    }
  }
}
```

**Note**: The `--` separator is required to pass arguments to the application rather than to uvx itself.

### For pip installed version:
```json
{
  "mcpServers": {
    "aws_fis_mcp": {
      "command": "aws-fis-mcp",
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      },
      "transportType": "stdio"
    }
  }
}
```

### For local development:

#### Read-Only Mode (Default):
```json
{
  "mcpServers": {
    "aws_fis_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/ec2-user/mcp-servers/aws-fis-mcp-server",
        "run",
        "aws_fis_mcp/server.py"
      ],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      },
      "transportType": "stdio"
    }
  }
}
```

#### With Write Operations Enabled:
```json
{
  "mcpServers": {
    "aws_fis_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/ec2-user/mcp-servers/aws-fis-mcp-server",
        "run",
        "aws_fis_mcp/server.py",
        "--allow-writes"
      ],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      },
      "transportType": "stdio"
    }
  }
}
```

## Available Tools

### Experiment Templates
- `list_experiment_templates`: List all AWS FIS experiment templates
- `get_experiment_template`: Get detailed information about a specific template
- `create_experiment_template`: Create a new experiment template *(requires --allow-writes)*
- `delete_experiment_template`: Delete an experiment template *(requires --allow-writes)*

### Experiments
- `list_experiments`: List all AWS FIS experiments
- `get_experiment`: Get detailed information about a specific experiment
- `start_experiment`: Start a new experiment based on a template *(requires --allow-writes)*
- `stop_experiment`: Stop a running experiment *(requires --allow-writes)*

### Action Types
- `list_action_types`: List all available AWS FIS action types
- `generate_template_example`: Generate an example template for a given target and action type

## Security and Error Handling

### Read-Only Mode Error Messages

When attempting write operations in read-only mode, you'll receive structured error messages:

```json
{
  "error": "Write operations are disabled",
  "message": "The 'start_experiment' operation requires write mode. Please restart the server with --allow-writes flag to enable write operations.",
  "operation": "start_experiment",
  "read_only_mode": true
}
```

### Region Support

All functions support specifying AWS regions, with configurable defaults:

```bash
# Examples of region usage
List all my FIS experiment templates in us-west-2
Start an experiment using template exp-12345abcde in eu-west-1
```

## Example Usage

Once connected to Amazon Q with the MCP server running, you can use commands like:

```
List all my FIS experiment templates in us-west-2
```

```
Start an experiment using template exp-12345abcde in us-east-1
```

```
Generate an example template for stopping EC2 instances
```

## Requirements

- Python 3.10+
- boto3
- AWS credentials configured with appropriate permissions for FIS

## License

This project is licensed under the MIT License - see the LICENSE file for details.