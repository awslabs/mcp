# AWS API MCP Server


## Overview
The AWS API MCP Server enables AI assistants to interact with AWS services and resources through AWS CLI commands. It provides programmatic access to manage your AWS infrastructure while maintaining proper security controls.

This server acts as a bridge between AI assistants and AWS services, allowing you to create, update, and manage AWS resources across all available services. It helps with AWS CLI command selection and provides access to the latest AWS API features and services, even those released after an AI model's knowledge cutoff date.


## Prerequisites
- You must have an AWS account with credentials properly configured. Please refer to the official documentation [here ↗](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials) for guidance. We recommend configuring your credentials using the `AWS_API_MCP_PROFILE_NAME` environment variable (see [Configuration Options](#%EF%B8%8F-configuration-options) section for details). If `AWS_API_MCP_PROFILE_NAME` is not specified, the system follows boto3's default credential selection order, in this case, if you have multiple AWS profiles configured on your machine, ensure the correct profile is prioritized in your credential chain.
- Ensure you have Python 3.10 or newer installed. You can download it from the [official Python website](https://www.python.org/downloads/) or use a version manager such as [pyenv](https://github.com/pyenv/pyenv).
- (Optional) Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for faster dependency management and improved Python environment handling.


## 📦 Installation Methods

Choose the installation method that best fits your workflow and get started with your favorite assistant with MCP support, like Q CLI, Cursor or Cline.

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-api-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWFwaS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20API%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-api-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22type%22%3A%22stdio%22%7D) |



### ⚡ Using uv
Add the following configuration to your MCP client config file (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

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



### 🐍 Using Python (pip)
> [!TIP]
> It's recommended to use a virtual environment because the AWS CLI version of the MCP server might not match the locally installed one
> and can cause it to be downgraded. In the MCP client config file you can change `"command"` to the path of the python executable in your
> virtual environment (e.g., `"command": "/workspace/project/.venv/bin/python"`).

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

### 🌐 HTTP Mode Configuration

The MCP server supports streamable HTTP mode. To use it, you must set:
- `AWS_API_MCP_TRANSPORT` to `"streamable-http"`
- `AUTH_TYPE` to `"no-auth"` (required; the server will fail to start otherwise)

Optionally configure the host and port with `AWS_API_MCP_HOST` and `AWS_API_MCP_PORT`.

#### For Linux/macOS:
```bash
AWS_API_MCP_TRANSPORT=streamable-http AUTH_TYPE=no-auth uvx awslabs.aws-api-mcp-server@latest
```

#### For Windows (Command Prompt):
```cmd
set AWS_API_MCP_TRANSPORT=streamable-http
set AUTH_TYPE=no-auth
uvx awslabs.aws-api-mcp-server@latest
```

#### For Windows (PowerShell):
```powershell
$env:AWS_API_MCP_TRANSPORT="streamable-http"
$env:AUTH_TYPE="no-auth"
uvx awslabs.aws-api-mcp-server@latest
```

Once the server is running, connect to it using the following configuration (ensure the host and port number match your `AWS_API_MCP_HOST` and `AWS_API_MCP_PORT` settings):"

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8000/mcp",
      "autoApprove": [],
      "disabled": false,
      "timeout": 60
    }
  }
}
```

**Note**: Replace `127.0.0.1` with your custom host if you've set `AWS_API_MCP_HOST` to a different value.

### 🔒 HTTP Mode Security Considerations

**IMPORTANT**: When using HTTP mode (`streamable-http`), please be aware of the following security considerations:

- **Single Customer Server**: This HTTP mode is intended for **single customer use only**. It is **NOT designed for multi-tenant environments** or serving multiple users simultaneously
- **No Built-in Authentication**: The server currently requires `AUTH_TYPE=no-auth` set explicitly, and provides no built-in authentication mechanisms
- **Network Security Controls**: Ensure proper network security controls are in place:
  - Bind to localhost (`127.0.0.1`) when possible
  - Configure firewall rules to restrict access
- **Encryption in Transit**: We **strongly recommend** adding encryption in transit when using HTTP mode:
  - Use HTTPS with TLS/SSL certificates
  - Avoid transmitting sensitive data over unencrypted HTTP connections



## ⚙️ Configuration Options

| Environment Variable                                              | Required                   | Default                                                  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|-------------------------------------------------------------------|----------------------------|----------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `AWS_REGION`                                                      | ❌ No                       | `"us-east-1"`                                            | Sets the default AWS region for all CLI commands, unless a specific region is provided in the request. If not provided, the MCP server will determine the region just like boto3's [configuration chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#overview) but with a fallback to `us-east-1`. This provides a consistent default while allowing flexibility to run commands in different regions as needed.                                                                                                                                                                        |
| `AWS_API_MCP_WORKING_DIR`                                         | ❌ No                       | \<Platform-specific temp directory\>/aws-api-mcp/workdir | Working directory path for the MCP server operations. Must be an absolute path when provided. Used to resolve relative paths in commands like `aws s3 cp`. Does not provide any sandboxing or security restrictions. If not provided, defaults to a platform-specific directory:<br/><br/>• **Windows**: `%TEMP%\aws-api-mcp\workdir` (typically `C:\Users\<username>\AppData\Local\Temp\aws-api-mcp\workdir`)<br/>• **macOS**: `/private/var/folders/<hash>/T/aws-api-mcp/workdir`<br/>• **Linux**: `$XDG_RUNTIME_DIR/aws-api-mcp/workdir` (if set) or `$TMPDIR/aws-api-mcp/workdir` (if set) or `/tmp/aws-api-mcp/workdir` |
| `AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS`                | ❌ No                       | `"false"`                                                | By default, restricts file operations to `AWS_API_MCP_WORKING_DIR`. When set to `true` system-wide file access is enabled and may cause unintended file overwrites.                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `AWS_API_MCP_PROFILE_NAME`                                        | ❌ No                       | `"default"`                                              | AWS Profile for credentials to use for command executions. If not provided, the MCP server will follow the boto3's [default credentials chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials) to look for credentials. We strongly recommend you to configure your credentials this way.                                                                                                                                                                                                                                                                            |
| `READ_OPERATIONS_ONLY`                                            | ❌ No                       | `"false"`                                                | When set to "true", restricts execution to read-only operations only. IAM permissions remain the primary security control. For a complete list of allowed operations under this flag, refer to the [Service Authorization Reference](https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html). Only operations where the **Access level** column is not `Write` will be allowed when this is set to "true".                                                                                                                                                 |
| `REQUIRE_MUTATION_CONSENT`                                        | ❌ No                       | `"false"`                                                | When set to "true", the MCP server will ask explicit consent before executing any operations that are **NOT** read-only. This safety mechanism uses [elicitation](https://modelcontextprotocol.io/docs/concepts/elicitation) so it requires a [client that supports elicitation](https://modelcontextprotocol.io/clients).                                                                                                                                                                                                                                                                                                   |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | ❌ No                       | -                                                        | Use environment variables to configure AWS credentials                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `AWS_API_MCP_TELEMETRY`                                           | ❌ No                       | `"true"`                                                 | Allow sending additional telemetry data to AWS related to the server configuration. This includes Whether the `call_aws()` tool is used with `READ_OPERATIONS_ONLY` set to true or false. Note: Regardless of this setting, AWS obtains information about which operations were invoked and the server version as part of normal AWS service interactions; no additional telemetry calls are made by the server for this purpose.                                                                                                                                                                                            |
| `EXPERIMENTAL_AGENT_SCRIPTS`                                      | ❌ No                       | `"false"`                                                | When set to "true", enables experimental agent scripts functionality. This provides access to structured, step-by-step workflows for complex AWS tasks through the `get_execution_plan` tool. Agent scripts are reusable workflows that automate complex processes and provide detailed guidance for accomplishing specific tasks. This feature is experimental and may change in future releases.                                                                                                                                                                                                                           |
| `AWS_API_MCP_AGENT_SCRIPTS_DIR`                                   | ❌ No                       | -                                                        | Directory path containing custom user scripts for the agent scripts functionality. When specified, the server will load additional `.script.md` files from this directory alongside the built-in scripts. The directory must exist and be readable. Scripts must follow the same format as built-in scripts with frontmatter metadata including a `description` field. This allows users to extend the agent scripts functionality with their own custom workflows.                                                                                                                                                          |
| `AWS_API_MCP_TRANSPORT`                                           | ❌ No                       | `"stdio"`                                                | Transport protocol for the MCP server. Valid options are `"stdio"` (default) for local communication or `"streamable-http"` for HTTP-based communication. When using `"streamable-http"`, the server will listen on the host and port specified by `AWS_API_MCP_HOST` and `AWS_API_MCP_PORT`.                                                                                                                                                                                                                                                                                                                                |
| `AWS_API_MCP_HOST`                                                | ❌ No                       | `"127.0.0.1"`                                            | Host address for the MCP server when using `"streamable-http"` transport. Only used when `AWS_API_MCP_TRANSPORT` is set to `"streamable-http"`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `AWS_API_MCP_PORT`                                                | ❌ No                       | `"8000"`                                                 | Port number for the MCP server when using `"streamable-http"` transport. Only used when `AWS_API_MCP_TRANSPORT` is set to `"streamable-http"`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `AWS_API_MCP_ALLOWED_HOSTS`                                       | ❌ No                       | `AWS_API_MCP_HOST`                                       | Comma-separated list of allowed host hostnames for HTTP requests. Used to validate the `Host` header in incoming requests. Set to `*` to allow all hosts (not recommended for production). Port numbers are automatically stripped during validation. Only used when `AWS_API_MCP_TRANSPORT` is set to `"streamable-http"`.                                                                                                                                                                                                                                                                                                  |
| `AWS_API_MCP_ALLOWED_ORIGINS`                                     | ❌ No                       | `AWS_API_MCP_HOST`                                       | Comma-separated list of allowed origin hostnames for HTTP requests. Used to validate the `Origin` header in incoming requests. Set to `*` to allow all origins (not recommended for production). Port numbers are automatically stripped during validation. Only used when `AWS_API_MCP_TRANSPORT` is set to `"streamable-http"`.                                                                                                                                                                                                                                                                                            |
| `AWS_API_MCP_STATELESS_HTTP`                                      | ❌ No                       | `"false"`                                                | ⚠️ **WARNING: We strongly recommend keeping this set to "false" due to significant security implications.** When set to "true", creates a completely fresh transport for each request with no session tracking or state persistence between requests. Only used when `AWS_API_MCP_TRANSPORT` is set to `"streamable-http"`.                                                                                                                                                                                                                                                                                                      |
| `AUTH_TYPE`                                                       | ❗ Yes (Only for HTTP mode) | -                                                        | Required only when `AWS_API_MCP_TRANSPORT` is `"streamable-http"`. Must be set to `"no-auth"`. If omitted or set to any other value, the server will fail to start. The server does not provide built-in authentication in HTTP mode; use network-layer controls to restrict access.                                                                                                                                                                                                                                                                                                                                         |

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
- `suggest_aws_commands`: Suggests AWS CLI commands based on a natural language query. This tool helps the model generate CLI commands by providing a description and the complete set of parameters for the 5 most likely CLI commands for the given query, including the most recent AWS CLI commands - some of which may be otherwise unknown to the model (released after the model's knowledge cut-off date).
- `get_execution_plan` *(Experimental)*: Provides structured, step-by-step guidance for accomplishing complex AWS tasks through agent scripts. This tool is only available when the `EXPERIMENTAL_AGENT_SCRIPTS` environment variable is set to "true". Agent scripts are reusable workflows that automate complex processes and provide detailed guidance for accomplishing specific tasks.


## Security Considerations
Before using this MCP Server, you should consider conducting your own independent assessment to ensure that your use would comply with your own specific security and quality control practices and standards, as well as the laws, rules, and regulations that govern you and your content.

### ⚠️ Multi-Tenant Environment Restrictions

**IMPORTANT**: This MCP server is **NOT designed for multi-tenant environments**. Do not use this server to serve multiple users or tenants simultaneously.

- **Single User Only**: Each instance of the MCP server should serve only one user with their own dedicated AWS credentials
- **Separate Directories**: When running multiple instances, create separate working directories for each instance using the `AWS_API_MCP_WORKING_DIR` environment variable

### 🔑 Credential Management and Access Control

We use credentials to control which commands this MCP server can execute. This MCP server relies on IAM roles to be configured properly, in particular:
- Using credentials for an IAM role with `AdministratorAccess` policy (usually the `Admin` IAM role) permits mutating actions (i.e. creating, deleting, modifying your AWS resources) and non-mutating actions.
- Using credentials for an IAM role with `ReadOnlyAccess` policy (usually the `ReadOnly` IAM role) only allows non-mutating actions, this is sufficient if you only want to inspect resources in your account.
- If IAM roles are not available, [these alternatives](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html#cli-configure-files-examples) can also be used to configure credentials.
- To add another layer of security, users can explicitly set the environment variable `READ_OPERATIONS_ONLY` to true in their MCP config file. When set to true, we'll compare each CLI command against a list of known read-only actions, and will only execute the command if it's found in the allowed list. "Read-Only" only refers to the API classification, not the file system, that is such "read-only" actions can still write to the file system if necessary or upon user request. While this environment variable provides an additional layer of protection, IAM permissions remain the primary and most reliable security control. Users should always configure appropriate IAM roles and policies for their use case, as IAM credentials take precedence over this environment variable.
- ⚠️ **IMPORTANT**: While using a `ReadOnlyAccess` IAM role will block write operations through the MCP server, **however some AWS read only operations can still return AWS credentials or sensitive information** in command outputs that could potentially be used outside of this server.

Our MCP server aims to support all AWS APIs. However, some of them will spawn subprocesses that expose security risks. Such APIs will be denylisted, see the full list below.

| Service | Operations |
|---------|------------|
| **deploy** | `install`, `uninstall` |
| **emr** | `ssh`,  `sock`, `get`, `put` |

### File System Access and Operating Mode

**Important**: This MCP server is intended for **STDIO mode only** as a local server using a single user's credentials. The server runs with the same permissions as the user who started it and has complete access to the file system.

#### Security and Access Considerations

- **No Sandboxing**: The `AWS_API_MCP_WORKING_DIR` environment variable sets a working directory. The `AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS` flag  by default is set to `"false"` which restricts MCP server file operations to `<AWS_API_MCP_WORKING_DIR>`. Setting to `"true"` enables system-wide file access but may cause unintended overwrites.
- **File System Access**: The server can read from and write to any location on the file system where the user has permissions.
- **No Confirmation Prompts**: Files can be modified, overwritten, or deleted without any additional user confirmation
- **Host File System Sharing**: When using this server, the host file system is directly accessible
- **Do Not Modify for Network Use**: This server is designed for local STDIO use only; network operation introduces additional security risks

#### Common File Operations

The MCP server can perform various file operations through AWS CLI commands, including:

- `aws s3 sync` - Can overwrite entire directories without warning
- `aws s3 cp` - Can overwrite existing files without confirmation
- Any AWS CLI command using the `outfile` parameter
- Commands that use the `file://` prefix to read from files

**Note**: While the `AWS_API_MCP_WORKING_DIR` environment variable sets where the server starts, it does not restrict where files can be accessed.

### Prompt Injection and Untrusted Data
This MCP server executes AWS CLI commands as instructed by an AI model, which can be vulnerable to prompt injection attacks:

- **Do not connect this MCP server to data sources with untrusted data** (e.g., CloudWatch logs containing raw user data, user-generated content in databases, etc.)
- Always use scoped-down IAM credentials with minimal permissions necessary for the specific task.
- Be aware that prompt injection vulnerabilities are a known issue with LLMs and not caused by MCP servers inherently. When working with untrusted data use a client that supports command validation with a human in the loop.

### Logging

The AWS API MCP server writes logs to help you monitor command executions, troubleshoot issues, and perform debugging. These logs are automatically rotated and contain operational data including command executions, errors, and debug information.

#### Log file location

Logs are written to a rotating file at:

- **macOS/Linux**: `<HOME>/.aws/aws-api-mcp/aws-api-mcp-server.log`
- **Windows**: `%USERPROFILE%\.aws\aws-api-mcp\aws-api-mcp-server.log`

#### Shipping logs to Amazon CloudWatch Logs

To centralize your logs in AWS CloudWatch for better monitoring and analysis, you can use the CloudWatch Agent to automatically ship the MCP server logs to a CloudWatch log group.

**Prerequisites:**

1. **Install the CloudWatch Agent** on your machine:
   - **Amazon Linux 2/2023**: `sudo yum install amazon-cloudwatch-agent`
   - **Other platforms**: Download from [CloudWatch Agent download page](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/download-CloudWatch-Agent-on-EC2-Instance-commandline-first.html)
   - **Learn more**: [CloudWatch Agent overview](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)

2. **Configure IAM permissions**: Ensure your instance/user has permissions to write to CloudWatch Logs. You can attach the `CloudWatchAgentServerPolicy` or create a custom policy with these permissions:
   - `logs:CreateLogGroup`
   - `logs:CreateLogStream`
   - `logs:PutLogEvents`

**Configuration steps:**

1. **Run the configuration wizard** to set up log collection. The wizard will guide you through configuring the log group name, stream name, and other settings. For detailed wizard documentation, see [Create the CloudWatch agent configuration file with the wizard](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/create-cloudwatch-agent-configuration-file-wizard.html).:

   **Linux/macOS:**
   ```bash
   sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
   ```

   **Windows:**
   ```cmd
   cd "C:\Program Files\Amazon\AmazonCloudWatchAgent"
   .\amazon-cloudwatch-agent-config-wizard.exe
   ```

2. **When prompted for log file path**, specify the MCP server log location:
   - **macOS**: `/Users/<user>/.aws/aws-api-mcp/aws-api-mcp-server.log`
   - **Linux**: `/home/<user>/.aws/aws-api-mcp/aws-api-mcp-server.log`
   - **Windows**: `C:\Users\<user>\.aws\aws-api-mcp\aws-api-mcp-server.log`

3. **Start the CloudWatch Agent** following the official AWS documentation:
   - [Starting the CloudWatch agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/start-CloudWatch-Agent-on-premise-SSM-onprem.html)

#### Troubleshooting

If you encounter issues with the CloudWatch Agent setup or log shipping, refer to the [Troubleshooting the CloudWatch agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/troubleshooting-CloudWatch-Agent.html).

### Security Best Practices

- **Principle of Least Privilege**: While the examples above use AWS managed policies like `AdministratorAccess` and `ReadOnlyAccess` for simplicity, we **strongly** recommend following the principle of least privilege by creating custom policies tailored to your specific use case.
- **Minimal Permissions**: Start with minimal permissions and gradually add access as needed for your specific workflows.
- **Condition Statements**: Combine custom policies with condition statements to further restrict access by region or other factors based on your security requirements.
- **Untrusted Data Sources**: When connecting to potentially untrusted data sources, use scoped-down credentials with minimal permissions.
- **Regular Monitoring**: Monitor AWS CloudTrail logs to track actions performed by the MCP server.

### Custom Security Policy Configuration

You can create a custom security policy file to define additional security controls beyond IAM permissions. The MCP server will look for a security policy file at `~/.aws/aws-api-mcp/mcp-security-policy.json`.

#### Security Policy File Format

```json
{
  "version": "1.0",
  "policy": {
    "denyList": [],
    "elicitList": []
  }
}
```

#### Command Format Requirements

**Important**: Commands must be specified in the exact format that the AWS CLI uses internally:

- **Format**: `aws <service> <operation>`
- **Service names**: Use the AWS CLI service name (e.g., `s3api`, `ec2`, `iam`, `lambda`)
- **Operation names**: Use kebab-case format (e.g., `delete-user`, `list-buckets`, `stop-instances`)

#### Examples of Correct Command Formats

| AWS CLI Command | Security Policy Format |
|-----------------|------------------------|
| `aws iam delete-user --user-name john` | `"aws iam delete-user"` |
| `aws s3api list-buckets` | `"aws s3api list-buckets"` |
| `aws ec2 describe-instances` | `"aws ec2 describe-instances"` |
| `aws lambda delete-function --function-name my-func` | `"aws lambda delete-function"` |
| `aws s3 cp file.txt s3://bucket/` | `"aws s3 cp"` |
| `aws cloudformation delete-stack --stack-name my-stack` | `"aws cloudformation delete-stack"` |

#### Policy Configuration Options

- **`denyList`**: Array of AWS CLI commands that will be completely blocked. Commands in this list will never be executed.
- **`elicitList`**: Array of AWS CLI commands that will require explicit user consent before execution. This requires a client that supports [elicitation](https://modelcontextprotocol.io/docs/concepts/elicitation).

#### Pattern Matching and Wildcards

**Current Limitation**: The security policy uses **exact string matching only**. Wildcard patterns (like `iam:delete-*` or `organizations:*`) are **not supported** in the current implementation.

Each command must be specified exactly as it appears in the AWS CLI format. For comprehensive blocking, you need to list each command individually:

```json
{
  "version": "1.0",
  "policy": {
    "denyList": [
      "aws iam delete-user",
      "aws iam delete-role",
      "aws iam delete-group",
      "aws iam delete-policy",
      "aws iam delete-access-key"
    ],
    "elicitList": [
      "aws s3api delete-object",
      "aws ec2 stop-instances",
      "aws lambda delete-function",
      "aws rds delete-db-instance",
      "aws cloudformation delete-stack"
    ]
  }
}
```

#### Finding the Correct Command Format

To determine the exact format for a command:

1. **Check AWS CLI documentation**: Look up the service and operation names
2. **Use kebab-case**: Convert camelCase operations to kebab-case (e.g., `ListBuckets` → `list-buckets`)
3. **Test with logging**: Enable debug logging to see how commands are parsed internally

#### Security Policy Precedence

1. **Denylist** - Operations in the denylist are blocked completely
2. **Elicitation Required** - Operations requiring consent will prompt the user
3. **IAM Permissions** - Standard AWS IAM controls apply to all operations
4. **READ_OPERATIONS_ONLY** - Environment variable restriction (if enabled)

**Note**: IAM permissions remain the primary security control mechanism. The security policy provides an additional layer of protection but cannot override IAM restrictions.

## License
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License").


## Disclaimer
This aws-api-mcp package is provided "as is" without warranty of any kind, express or implied, and is intended for development, testing, and evaluation purposes only. We do not provide any guarantee on the quality, performance, or reliability of this package. LLMs are non-deterministic and they make mistakes, we advise you to always thoroughly test and follow the best practices of your organization before using these tools on customer facing accounts. Users of this package are solely responsible for implementing proper security controls and MUST use AWS Identity and Access Management (IAM) to manage access to AWS resources. You are responsible for configuring appropriate IAM policies, roles, and permissions, and any security vulnerabilities resulting from improper IAM configuration are your sole responsibility. By using this package, you acknowledge that you have read and understood this disclaimer and agree to use the package at your own risk.
