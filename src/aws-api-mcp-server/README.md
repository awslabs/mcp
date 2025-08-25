# AWS API MCP Server


## Overview
The AWS API MCP Server enables AI assistants to interact with AWS services and resources through AWS CLI commands. It provides programmatic access to manage your AWS infrastructure while maintaining proper security controls.

This server acts as a bridge between AI assistants and AWS services, allowing you to create, update, and manage AWS resources across all available services. It helps with AWS CLI command selection and provides access to the latest AWS API features and services, even those released after an AI model's knowledge cutoff date.

This MCP server is meant for testing, development, and evaluation purposes.


## Prerequisites
- You must have an AWS account with credentials properly configured. Please refer to the official documentation [here ↗](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials) for guidance. We recommend configuring your credentials using the `AWS_API_MCP_PROFILE_NAME` environment variable (see [Configuration Options](#%EF%B8%8F-configuration-options) section for details). If `AWS_API_MCP_PROFILE_NAME` is not specified, the system follows boto3's default credential selection order, in this case, if you have multiple AWS profiles configured on your machine, ensure the correct profile is prioritized in your credential chain.
- Ensure you have Python 3.10 or newer installed. You can download it from the [official Python website](https://www.python.org/downloads/) or use a version manager such as [pyenv](https://github.com/pyenv/pyenv).
- (Optional) Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for faster dependency management and improved Python environment handling.


## 📦 Installation Methods

> [!IMPORTANT]
> Getting server timeouts? Add `"timeout": 60` (or `60000`, depending on your client) to your MCP client config file.
> The server startup time varies based on your system's performance, and default timeouts may be too short.

Choose the installation method that best fits your workflow and get started with your favorite assistant with MCP support, like Q CLI, Cursor or Cline.

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-api-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWFwaS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20API%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-api-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22type%22%3A%22stdio%22%7D) |



### 🐍 Using Python (pip)

**Step 1: Install the package**
```bash
pip install awslabs.aws-api-mcp-server
```

**Step 2: Configure your MCP client**
Add the following configuration to your MCP client config file (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "python",
      "args": [
        "-m",
        "awslabs.aws_api_mcp_server.server"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### ⚡ Using uv

**For Linux/MacOS users:**

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-api-mcp-server@latest"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**For Windows users:**

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.aws-api-mcp-server@latest",
        "awslabs.aws-api-mcp-server.exe"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 🐳 Using Docker

You can isolate the MCP server by running it in a Docker container. The Docker image is available on the [public AWS ECR registry](https://gallery.ecr.aws/awslabs-mcp/awslabs/aws-api-mcp-server).

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "AWS_REGION=us-east-1",
        "--volume",
        "/full/path/to/.aws:/app/.aws",
        "public.ecr.aws/awslabs-mcp/awslabs/aws-api-mcp-server:latest"
      ],
      "env": {}
    }
  }
}
```

### 🔧 Using Cloned Repository

For detailed instructions on setting up your local development environment and running the server from source, please see the CONTRIBUTING.md file.



## ⚙️ Configuration Options

| Environment Variable                                              | Required | Default                                                  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|-------------------------------------------------------------------|----------|----------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `AWS_REGION`                                                      | ❌ No     | `"us-east-1"`                                            | Sets the default AWS region for all CLI commands, unless a specific region is provided in the request. If not provided, the MCP server will determine the region just like boto3's [configuration chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#overview) but with a fallback to `us-east-1`. This provides a consistent default while allowing flexibility to run commands in different regions as needed.                                                                                                                                                                        |
| `AWS_API_MCP_WORKING_DIR`                                         | ❌ No     | \<Platform-specific temp directory\>/aws-api-mcp/workdir | Working directory path for the MCP server operations. Must be an absolute path when provided. Used to resolve relative paths in commands like `aws s3 cp`. Does not provide any sandboxing or security restrictions. If not provided, defaults to a platform-specific directory:<br/><br/>• **Windows**: `%TEMP%\aws-api-mcp\workdir` (typically `C:\Users\<username>\AppData\Local\Temp\aws-api-mcp\workdir`)<br/>• **macOS**: `/private/var/folders/<hash>/T/aws-api-mcp/workdir`<br/>• **Linux**: `$XDG_RUNTIME_DIR/aws-api-mcp/workdir` (if set) or `$TMPDIR/aws-api-mcp/workdir` (if set) or `/tmp/aws-api-mcp/workdir` |
| `AWS_API_MCP_PROFILE_NAME`                                        | ❌ No     | `"default"`                                              | AWS Profile for credentials to use for command executions. If not provided, the MCP server will follow the boto3's [default credentials chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials) to look for credentials. We strongly recommend you to configure your credentials this way.                                                                                                                                                                                                                                                                            |
| `READ_OPERATIONS_ONLY`                                            | ❌ No     | `"false"`                                                | When set to "true", restricts execution to read-only operations only. IAM permissions remain the primary security control. For a complete list of allowed operations under this flag, refer to the [Service Authorization Reference](https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html). Only operations where the **Access level** column is not `Write` will be allowed when this is set to "true".                                                                                                                                                 |
| `REQUIRE_MUTATION_CONSENT`                                        | ❌ No     | `"false"`                                                | When set to "true", the MCP server will ask explicit consent before executing any operations that are **NOT** read-only. This safety mechanism uses [elicitation](https://modelcontextprotocol.io/docs/concepts/elicitation) so it requires a [client that supports elicitation](https://modelcontextprotocol.io/clients).                                                                                                                                                                                                                                                                                                   |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | ❌ No     | -                                                        | Use environment variables to configure AWS credentials                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `AWS_API_MCP_TELEMETRY`                                           | ❌ No     | `"true"`                                                 | Allow sending additional telemetry data to AWS related to the server configuration. This includes Whether the `call_aws()` tool is used with `READ_OPERATIONS_ONLY` set to true or false. Note: Regardless of this setting, AWS obtains information about which operations were invoked and the server version as part of normal AWS service interactions; no additional telemetry calls are made by the server for this purpose.                                                                                                                                                                                            |
| `EMBEDDING_MODEL_DIR`                                             | ❌ No     | `$AWS_API_MCP_WORKING_DIR/embedding_models`              | Directory path where embedding models are stored or cached. When specified, this directory will be used for model storage and retrieval operations. Must be an absolute path when provided.                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `EXPERIMENTAL_AGENT_SCRIPTS`                                      | ❌ No     | `"false"`                                                | When set to "true", enables experimental agent scripts functionality. This provides access to structured, step-by-step workflows for complex AWS tasks through the `get_execution_plan` tool. Agent scripts are reusable workflows that automate complex processes and provide detailed guidance for accomplishing specific tasks. This feature is experimental and may change in future releases.                                                                                                                                                                                                                                                                                              |

### 🚀 Quick Start

Once configured, you can ask your AI assistant questions such as:

- **"List all my EC2 instances"**
- **"Show me S3 buckets in us-west-2"**
- **"Create a new security group for web servers"** *(Only with write permission)*


## Features

- **Comprehensive AWS CLI Support**: Supports all commands available in the latest AWS CLI version, ensuring access to the most recent AWS services and features
- **Help in Command Selection**: Helps AI assistants select the most appropriate AWS CLI commands to accomplish specific tasks
- **Command Validation**: Ensures safety by validating all AWS CLI commands before execution, preventing invalid or potentially harmful operations
- **Hallucination Protection**: Mitigates the risk of model hallucination by strictly limiting execution to valid AWS CLI commands only - no arbitrary code execution is permitted
- **Security-First Design**: Built with security as a core principle, providing multiple layers of protection to safeguard your AWS infrastructure
- **Read-Only Mode**: Provides an extra layer of security that disables all mutating operations, allowing safe exploration of AWS resources


## Available MCP Tools
The tool names are subject to change, please refer to CHANGELOG.md for any changes and adapt your workflows accordingly.

- `call_aws`: Executes AWS CLI commands with validation and proper error handling
- `suggest_aws_commands`: Suggests AWS CLI commands based on a natural language query. This tool helps the model generate CLI commands by providing a description and the complete set of parameters for the 5 most likely CLI commands for the given query, including the most recent AWS CLI commands - some of which may be otherwise unknown to the model (released after the model's knowledge cut-off date). This enables RAG (Retrieval-Augmented Generation) for CLI command generation via the AWS CLI command table as the knowledge source, M3 text embedding model [Chen et al., Findings of ACL 2024] for representing query and CLI documents as dense vectors, and FAISS for nearest neighbour search.
- `get_execution_plan` *(Experimental)*: Provides structured, step-by-step guidance for accomplishing complex AWS tasks through agent scripts. This tool is only available when the `EXPERIMENTAL_AGENT_SCRIPTS` environment variable is set to "true". Agent scripts are reusable workflows that automate complex processes and provide detailed guidance for accomplishing specific tasks.


## Security Considerations
Before using this MCP Server, you should consider conducting your own independent assessment to ensure that your use would comply with your own specific security and quality control practices and standards, as well as the laws, rules, and regulations that govern you and your content.

We use credentials to control which commands this MCP server can execute. This MCP server relies on IAM roles to be configured properly, in particular:
- Using credentials for an IAM role with `AdministratorAccess` policy (usually the `Admin` IAM role) permits mutating actions (i.e. creating, deleting, modifying your AWS resources) and non-mutating actions.
- Using credentials for an IAM role with `ReadOnlyAccess` policy (usually the `ReadOnly` IAM role) only allows non-mutating actions, this is sufficient if you only want to inspect resources in your account.
- If IAM roles are not available, [these alternatives](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html#cli-configure-files-examples) can also be used to configure credentials.
- To add another layer of security, users can explicitly set the environment variable `READ_OPERATIONS_ONLY` to true in their MCP config file. When set to true, we'll compare each CLI command against a list of known read-only actions, and will only execute the command if it's found in the allowed list. "Read-Only" only refers to the API classification, not the file system, that is such "read-only" actions can still write to the file system if necessary or upon user request. While this environment variable provides an additional layer of protection, IAM permissions remain the primary and most reliable security control. Users should always configure appropriate IAM roles and policies for their use case, as IAM credentials take precedence over this environment variable.

Our MCP server aims to support all AWS APIs. However, some of them will spawn subprocesses that expose security risks. Such APIs will be denylisted, see the full list below.

| Service | Operations |
|---------|------------|
| **deploy** | `install`, `uninstall` |
| **emr** | `ssh`,  `sock`, `get`, `put` |
| **opsworks** | `register` |

### File System Access and Operating Mode

**Important**: This MCP server is intended for **STDIO mode only** as a local server using a single user's credentials. The server runs with the same permissions as the user who started it and has complete access to the file system.

#### Security and Access Considerations

- **No Sandboxing**: The `AWS_API_MCP_WORKING_DIR` environment variable sets a working directory but does **not** provide any security restrictions
- **Full File System Access**: The server can read from and write to any location on the file system where the user has permissions
- **No Confirmation Prompts**: Files can be modified, overwritten, or deleted without any additional user confirmation
- **Host File System Sharing**: When using this server, the host file system is directly accessible
- **Do Not Modify for Network Use**: This server is designed for local STDIO use only; network operation introduces additional security risks

#### Common File Operations

The MCP server can perform various file operations through AWS CLI commands, including:

- `aws s3 sync` - Can overwrite entire directories without warning
- `aws s3 cp` - Can overwrite existing files without confirmation
- Any AWS CLI command using the `outfile` parameter
- Commands that use the `file://` prefix to read from files

**Note**: While the `AWS_API_MCP_WORKING_DIR` environment variable sets where the server starts, it does not restrict where files can be written or accessed.

### Prompt Injection and Untrusted Data
This MCP server executes AWS CLI commands as instructed by an AI model, which can be vulnerable to prompt injection attacks:

- **Do not connect this MCP server to data sources with untrusted data** (e.g., CloudWatch logs containing raw user data, user-generated content in databases, etc.)
- Always use scoped-down IAM credentials with minimal permissions necessary for the specific task.
- Be aware that prompt injection vulnerabilities are a known issue with LLMs and not caused by MCP servers inherently. When working with untrusted data use a client that supports command validation with a human in the loop.

### Logging

Logs of the MCP server are stored in the system's temporary directory, under **aws-api-mcp** subfolder - on Windows and macOS, this is the system temp directory, while on Linux it uses `XDG_RUNTIME_DIR`, `TMPDIR`, or `/tmp` as fallback. The logs contain MCP server operational data including command executions, errors, and debugging information to help users monitor and perform forensics of the MCP server.

### Security Best Practices

- **Principle of Least Privilege**: While the examples above use AWS managed policies like `AdministratorAccess` and `ReadOnlyAccess` for simplicity, we **strongly** recommend following the principle of least privilege by creating custom policies tailored to your specific use case.
- **Minimal Permissions**: Start with minimal permissions and gradually add access as needed for your specific workflows.
- **Condition Statements**: Combine custom policies with condition statements to further restrict access by region or other factors based on your security requirements.
- **Untrusted Data Sources**: When connecting to potentially untrusted data sources, use scoped-down credentials with minimal permissions.
- **Regular Monitoring**: Monitor AWS CloudTrail logs to track actions performed by the MCP server.

## License
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License").


## Disclaimer
This aws-api-mcp package is provided "as is" without warranty of any kind, express or implied, and is intended for development, testing, and evaluation purposes only. We do not provide any guarantee on the quality, performance, or reliability of this package. LLMs are non-deterministic and they make mistakes, we advise you to always thoroughly test and follow the best practices of your organization before using these tools on customer facing accounts. Users of this package are solely responsible for implementing proper security controls and MUST use AWS Identity and Access Management (IAM) to manage access to AWS resources. You are responsible for configuring appropriate IAM policies, roles, and permissions, and any security vulnerabilities resulting from improper IAM configuration are your sole responsibility. By using this package, you acknowledge that you have read and understood this disclaimer and agree to use the package at your own risk.
