# AWS MCP Server


## Overview
The AWS MCP Server enables AI assistants to interact with AWS services and resources through AWS CLI commands. It provides programmatic access to manage your AWS infrastructure while maintaining proper security controls.

This server bridges the gap between AI assistants and AWS services, allowing you to create, update, and manage AWS resources across all available services. It helps with AWS CLI command selection and provides access to the latest AWS API features and services, even those released after an AI model's knowledge cutoff date.


## Features

- **Comprehensive AWS CLI Support**: Supports all commands available in the latest AWS CLI version, ensuring access to the most recent AWS services and features
- **Help in Command Selection**: Helps AI assistants select the most appropriate AWS CLI commands to accomplish specific tasks
- **Command Validation**: Ensures safety by validating all AWS CLI commands before execution, preventing invalid or potentially harmful operations
- **Hallucination Protection**: Eliminates the risk of model hallucination by strictly limiting execution to valid AWS CLI commands only - no arbitrary code execution is permitted
- **Security-First Design**: Built with security as a core principle, providing multiple layers of protection to safeguard your AWS infrastructure
- **Read-Only Mode**: Provides an extra layer of security that disables all mutating operations, allowing safe exploration of AWS resources


## Available MCP Tools
- `call_aws`: Executes AWS CLI commands with validation and proper error handling
- `suggest_aws_commands`: Suggests AWS CLI commands based on user's natural language query. This is a fallback tool when the model is uncertain about the exact AWS CLI command needed to fulfill user's request


## Prerequisites
- Have an AWS account with [credentials configured](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)
- Install uv from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
- Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)
- Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)


## Installation
[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.aws-mcp-server&config=JTdCJTIyY29tbWFuZCUyMiUzQSUyMnV2eCUyMGF3c2xhYnMuYXdzLW1jcC1zZXJ2ZXIlNDBsYXRlc3QlMjIlMkMlMjJlbnYlMjIlM0ElN0IlMjJBV1NfUkVHSU9OJTIyJTNBJTIydXMtZWFzdC0xJTIyJTdEJTdE)

Add the following code to your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`).

Remember to remove all comments when you finish configuration, otherwise the config file will not load properly.

```
{
  "mcpServers": {
    "awslabs.aws-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-mcp-server@latest"
      ],
      "env": {
        "AWS_REGION": "us-east-1", // Required. Set your default region to be assumed for CLI commands, if not specified explicitly in the request.
        "AWS_PROFILE": "default", // Optional. AWS Profile for credentials, 'default' will be used if not specified.
        "READ_OPERATIONS_ONLY": "false", // Optional. Only allows read-only operations as per ReadOnlyAccess policy. Default is "false"
        "AWS_MCP_TELEMETRY": "false" // Optional. Allow the storage of telemetry data. Default is "false"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Once configured, you can ask your AI assistant questions such as:

- "List all my EC2 instances"
- "Show me S3 buckets in us-west-2"
- "Create a new security group for web servers" (Admin policy only)
- "What's my current AWS bill this month?"

## Security Considerations
We primarily use credentials to control which commands this MCP server can execute. We recommend using IAM roles, in particular:
- Using credentials for an IAM role with `AdministratorAccess` policy (usually the `Admin` IAM role) permits mutating actions (i.e. creating, deleting, modifying your AWS resources).
- Using credentials for an IAM role with `ReadOnlyAccess` policy (usually the `ReadOnly` IAM role) only allows non-mutating actions, this is sufficient if you only want to inspect your account.
- Apart from IAM roles, [these alternatives](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html#cli-configure-files-examples) can also be used to configure credentials.
- To add another layer of security, users can explicitly set the environment variable `READ_OPERATIONS_ONLY` to true in their MCP config file. When set to true, we'll compare each CLI command against a list of known read-only actions, and will only execute the command if it's found in the allowed list. While this environment variable provides an additional layer of protection, IAM permissions remain the primary and most reliable security control. Users should always configure appropriate IAM roles and policies for their use case, as IAM credentials take precedence over this environment variable.



## Environment variables
#### Required
- `AWS_REGION` (e.g. "eu-central-1"): Default region to be assumed when running AWS CLI commands


#### Optional
- `AWS_PROFILE` (string, default: "default"): AWS Profile for credentials to use for command executions, 'default' will be used if not specified
- `READ_OPERATIONS_ONLY` (boolean, default: false): Primarily IAM permissions are used to control if mutating actions are allowed, so defaulting to "false" to reduce friction. We keep this as a best effort attempt to recognize and further control read-only actions. When set to "true", restricts execution to read-only operations. For a complete list of allowed operations under this flag, refer to the [ReadOnlyAccess](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/ReadOnlyAccess.html) policy.
- `AWS_MCP_TELEMETRY` (boolean, default: false): Allow sending additional telemetry data to AWS related to the server configuration.




## Local development
To make changes to this MCP locally and run it:

1. Clone this repository:
   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd mcp/src/aws-mcp-server
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure AWS credentials and environment variables:
   - Ensure you have AWS credentials configured in `~/.aws/credentials` or set the appropriate [environment variables](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#environment-variables) in the MCP server configuration.
   - `export AWS_REGION=us-east-1` or any other region of your preference


4. Run the server:
   ```bash
   uv run awslabs.aws-mcp-server
   ```
