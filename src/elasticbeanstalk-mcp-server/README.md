# AWS Elastic Beanstalk MCP Server

An AWS Labs Model Context Protocol (MCP) server for interacting with AWS Elastic Beanstalk resources.

## Overview

The Elastic Beanstalk MCP Server provides tools for interacting with AWS Elastic Beanstalk environments, applications, and events. It allows AI assistants to retrieve information about your Elastic Beanstalk resources and help you manage them effectively.

## Features

- **Describe Environments**: Get detailed information about your Elastic Beanstalk environments
- **Describe Applications**: Retrieve information about your Elastic Beanstalk applications
- **Describe Events**: Access event logs and history for your Elastic Beanstalk resources
- **Describe Configuration Settings**: View configuration settings for environments and templates

## Installation

You can install the Elastic Beanstalk MCP Server using `pip`:

```bash
pip install awslabs.elasticbeanstalk-mcp-server
```

Or using `uv`:

```bash
uv pip install awslabs.elasticbeanstalk-mcp-server
```

## Usage

### Running the Server

You can run the server directly:

```bash
awslabs.elasticbeanstalk-mcp-server
```

Or with Python:

```bash
python -m awslabs.elasticbeanstalk_mcp_server.server
```

### Configuration

The server supports the following configuration options:

- `--readonly`: Run the server in read-only mode (default: False)

### AWS Credentials

The server uses the standard AWS credential provider chain:

1. Environment variables (`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`)
2. Shared credential file (`~/.aws/credentials`)
3. IAM role for Amazon EC2 / ECS task role / EKS pod identity
4. AWS SSO or Web Identity token

You can specify a region using the `AWS_REGION` environment variable or pass it directly to the tools.

## Available Tools

### DescribeEnvironmentsTool

Retrieves descriptions for existing Elastic Beanstalk environments.

**Parameters:**
- `application_name`: (Optional) Restricts the returned descriptions to environments of this application
- `environment_names`: (Optional) List of environment names to describe
- `environment_ids`: (Optional) List of environment IDs to describe
- `include_deleted`: (Optional) Include deleted environments if they existed within the last hour
- `region_name`: (Optional) The AWS region to run the tool

### DescribeApplicationsTool

Returns descriptions for existing Elastic Beanstalk applications.

**Parameters:**
- `application_names`: (Optional) List of application names to describe
- `region_name`: (Optional) The AWS region to run the tool

### DescribeEventsTool

Returns a list of events for an environment, application, or platform.

**Parameters:**
- `application_name`: (Optional) Application name filter
- `environment_name`: (Optional) Environment name filter
- `environment_id`: (Optional) Environment ID filter
- `start_time`: (Optional) Start time for retrieving events (ISO 8601 format)
- `end_time`: (Optional) End time for retrieving events (ISO 8601 format)
- `max_items`: (Optional) Maximum number of records to retrieve
- `severity`: (Optional) Severity level filter (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
- `region_name`: (Optional) The AWS region to run the tool

### DescribeConfigurationSettingsTool

Returns descriptions of the configuration settings for a specified configuration set.

**Parameters:**
- `application_name`: (Required) The application name for the configuration settings
- `environment_name`: (Optional) The environment name to retrieve configuration settings for
- `template_name`: (Optional) The configuration template name to retrieve settings for
- `region_name`: (Optional) The AWS region to run the tool

**Note:** Either `environment_name` or `template_name` must be provided.

## Development

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/elasticbeanstalk-mcp-server

# Create a virtual environment and install dependencies
uv venv
uv sync --all-groups
```

### Running Tests

```bash
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
```

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.
