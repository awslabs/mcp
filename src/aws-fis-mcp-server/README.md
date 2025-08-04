# AWS Fault Injection Service (FIS) MCP Server

This MCP server provides tools for working with AWS Fault Injection Service (FIS), allowing users to create, manage, and execute fault injection experiments.

## Overview

AWS Fault Injection Service (FIS) is a managed service that enables you to perform fault injection experiments on your AWS workloads. This MCP server provides capabilities to interact with FIS, making it easier to create and manage chaos engineering experiments.

## Features

- List and retrieve experiment templates
- Create and delete experiment templates
- Start and stop experiments
- List available action types
- Generate example templates

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
```json
{
  "mcpServers": {
    "aws_fis_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/ec2-user/mcp-servers/AWS-FIS-MCP",
        "run",
        "main.py"
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
- `create_experiment_template`: Create a new experiment template
- `delete_experiment_template`: Delete an experiment template

### Experiments
- `list_experiments`: List all AWS FIS experiments
- `get_experiment`: Get detailed information about a specific experiment
- `start_experiment`: Start a new experiment based on a template
- `stop_experiment`: Stop a running experiment

### Action Types
- `list_action_types`: List all available AWS FIS action types
- `generate_template_example`: Generate an example template for a given target and action type

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