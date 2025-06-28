# AWS MCP Server


## Overview
The AWS MCP Server enables AI assistants to interact with AWS services and resources through AWS CLI commands. It provides programmatic access to manage your AWS infrastructure while maintaining proper security controls and consent mechanisms.

This server bridges the gap between AI assistants and AWS services, allowing you to create, update, and manage AWS resources across all available services. It helps with AWS CLI command selection and provides access to the latest AWS API features and services, even those released after an AI model's knowledge cutoff date. The server implements safety measures to ensure that critical operations require explicit user approval before execution.


## Features

- **Comprehensive AWS CLI Support**: Supports all commands available in the latest AWS CLI version, ensuring access to the most recent AWS services and features
- **Help in Command Selection**: Helps AI assistants select the most appropriate AWS CLI commands to accomplish specific tasks
- **Read-Only Mode**: Provides a safety-first approach with read-only mode that disables all mutating operations, allowing safe exploration of AWS resources
- **Explicit Consent Mechanism**: Prevents accidental execution of destructive operations by requiring explicit user consent before running any mutating commands
- **Command Validation**: Ensures safety by validating all AWS CLI commands before execution, preventing invalid or potentially harmful operations
- **Hallucination Protection**: Eliminates the risk of model hallucination by strictly limiting execution to valid AWS CLI commands only - no arbitrary code execution is permitted
- **Security-First Design**: Built with security as a core principle, providing multiple layers of protection to safeguard your AWS infrastructure



## Prerequisites
- Have an AWS account with [credentials configured](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)
- Install uv from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
- Install Python 3.10 or newer using uv python install 3.10 (or a more recent version)
- Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)


## Installation
You can download the AWS MCP Server from GitHub. To get started using your favorite code assistant with MCP support, like Q CLI, Cursor or Cline.

Add the following code to your MCP client configuration. The AWS MCP server uses the default AWS profile by default. Specify a value in AWS_PROFILE if you want to use a different profile. Similarly, adjust the AWS Region and log level values as needed.

```
{
  "mcpServers": {
    "awslabs.aws-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-mcp-server@latest",
      ],
      "env": {
        "AWS_REGION": "us-east-1", // Required. Set your default region to be assumed for CLI commands, if not specified explicitly in the request.
        "AWS_PROFILE": "profile", // Optional. AWS Profile for credentials, 'default' will be used if not specified.
        "MAX_OUTPUT_TOKENS": "50000", // Optional. Limits the output of the AWS CLI command to the set amount of tokens.
        "READ_OPERATIONS_ONLY": "true" // Optional. Only allows read-only operations as per ReadOnlyAccess policy. Default is "true"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

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

3. Configure AWS credentials:
   - Ensure you have AWS credentials configured in `~/.aws/credentials` or set the appropriate environment variables.

4. Run the server:
   ```bash
   uv run awslabs.aws-mcp-server
   ```



## Environment variables
#### Required
- `AWS_REGION` (e.g. "eu-central-1"): Default region to be assumed when running AWS CLI commands


#### Optional
- `AWS_PROFILE` (string, default: "default"): AWS Profile for credentials to use for command executions, 'default' will be used if not specified
- `MAX_OUTPUT_TOKENS` (int): Limits the output of the AWS CLI command to the set amount of tokens, default sets this to unlimited. The size of data that LLMs can reason about is limited and this can become a problem when you have a large number of AWS resources in your account and you are asking questions about these resources. The tool makes a best effort estimation since tokenization is different for every LLM and will stop paginating the AWS CLI command once it estimates that the specified token limit has been reached.
- `READ_OPERATIONS_ONLY` (boolean, default: true): When set to "true", restricts execution to read-only operations. For a complete list of allowed operations under this flag, refer to the [ReadOnlyAccess](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/ReadOnlyAccess.html) policy.
