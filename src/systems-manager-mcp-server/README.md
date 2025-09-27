# AWS Systems Manager MCP Server

Model Context Protocol (MCP) server that enables LLMs to manage AWS Systems Manager documents, automation executions, command operations, and Parameter Store through natural language interactions for comprehensive CloudOps workflows.

## Features

- **Document Management**: Create, read, update, and delete Systems Manager documents
- **Automation Execution**: Start, stop, and monitor automation workflows for CloudOps operations
- **Command Execution**: Send and monitor commands on EC2 instances and on-premises servers
- **Parameter Store**: Manage configuration parameters with support for encrypted values
- **Document Permissions**: Control document sharing across AWS accounts
- **Version Control**: Manage document versions with proper tracking
- **Multi-Type Support**: Handle Command, Automation, Policy, Session, Package, and other document types
- **Natural Language Interface**: Transform infrastructure management from static authoring to dynamic conversations
- **Read-Only Mode**: Optional read-only operation for safe exploration
- **Comprehensive Guidance**: Built-in prompts for best practices and troubleshooting

## Prerequisites

1. Configure AWS credentials:
   - Via AWS CLI: `aws configure`
   - Or set environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION)
2. Ensure your IAM role or user has the necessary permissions (see [Security Considerations](#security-considerations))

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.systems-manager-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuc3lzdGVtcy1tYW5hZ2VyLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1uYW1lZC1wcm9maWxlIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Systems%20Manager%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.systems-manager-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-named-profile%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.systems-manager-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.systems-manager-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-named-profile"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

If you would like to prevent the MCP from taking any mutating actions (i.e. Create/Update/Delete operations), you can specify the readonly flag:

```json
{
  "mcpServers": {
    "awslabs.systems-manager-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.systems-manager-mcp-server@latest",
        "--readonly"
      ],
      "env": {
        "AWS_PROFILE": "your-named-profile"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.systems-manager-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.systems-manager-mcp-server@latest",
        "awslabs.systems-manager-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

## Tools

### Document Management

#### list_documents

Lists Systems Manager documents with optional filtering capabilities.
**Example**: List all command documents owned by Amazon.

#### get_document

Retrieves document content and metadata for a specific Systems Manager document.
**Example**: Get the content of the AWS-RunShellScript document.

#### create_document

Creates new Systems Manager documents (Command, Automation, Policy, etc.).
**Example**: Create a command document that installs Docker on Linux instances.

#### update_document

Updates existing Systems Manager documents with version control.
**Example**: Update MyCustomDocument with new shell commands.

#### delete_document

Deletes Systems Manager documents or specific versions.
**Example**: Delete version 2 of MyCustomDocument.

#### describe_document_permission

Views document sharing permissions across AWS accounts.
**Example**: Show which accounts have access to MySharedDocument.

#### modify_document_permission

Modifies document sharing settings and permissions.
**Example**: Share MyDocument with AWS account 123456789012.

### Automation Execution

#### start_automation_execution

Starts automation executions for CloudOps workflows.
**Example**: Start the AWS-RestartEC2Instance automation on specific instances.

#### get_automation_execution

Gets detailed information about an automation execution.
**Example**: Check the status and progress of automation execution ae-1234567890abcdef0.

#### stop_automation_execution

Stops a running automation execution.
**Example**: Stop automation execution ae-1234567890abcdef0.

#### describe_automation_executions

Lists automation executions with optional filtering.
**Example**: List all failed automation executions from the last 24 hours.

#### send_automation_signal

Sends signals to interactive automation executions.
**Example**: Send an Approve signal to a waiting automation step.

### Command Execution

#### send_command

Sends commands to EC2 instances or on-premises servers.
**Example**: Run a shell script on all instances tagged with Environment=Production.

#### get_command_invocation

Gets detailed results of a command execution on a specific instance.
**Example**: Get the output of command cmd-1234567890abcdef0 on instance i-1234567890abcdef0.

#### list_commands

Lists command executions with optional filtering.
**Example**: List all commands executed in the last hour.

#### cancel_command

Cancels a running command execution.
**Example**: Cancel command cmd-1234567890abcdef0 on specific instances.

### Parameter Store

#### get_parameter

Retrieves a parameter from Parameter Store.
**Example**: Get the database connection string parameter.

#### put_parameter

Stores a parameter in Parameter Store.
**Example**: Store an encrypted API key as a SecureString parameter.

#### get_parameters

Retrieves multiple parameters from Parameter Store.
**Example**: Get all parameters for a specific application environment.

#### delete_parameter

Deletes a parameter from Parameter Store.
**Example**: Remove an obsolete configuration parameter.

## Basic Usage

Examples of how to use the AWS Systems Manager MCP Server:

**Document Management:**
- "Create a command document that installs Docker on Linux instances"
- "List all automation documents in my account"
- "Update the maintenance document to include new security patches"
- "Delete the old version of the deployment document"
- "Share the backup automation document with the production account"
- "Show me the content of the AWS-RunShellScript document"

**Automation Workflows:**
- "Start the AWS-RestartEC2Instance automation on instances tagged Environment=Production"
- "Check the status of automation execution ae-1234567890abcdef0"
- "Stop the running automation that's taking too long"
- "List all failed automation executions from today"
- "Send an approval signal to the waiting automation step"

**Command Operations:**
- "Run a system update command on all Linux instances in us-east-1"
- "Execute a PowerShell script on Windows servers tagged Role=WebServer"
- "Check the results of the last command execution on instance i-1234567890abcdef0"
- "Cancel the long-running command on the development instances"
- "List all commands executed in the last 2 hours"

**Parameter Store:**
- "Store the database connection string as a SecureString parameter"
- "Get the API key parameter for the production environment"
- "Retrieve all parameters under the /myapp/prod/ path"
- "Delete the obsolete configuration parameter"
- "Update the application version parameter to 2.1.0"

**CloudOps Scenarios:**
- "Set up automated patching for all production servers"
- "Create a disaster recovery automation workflow"
- "Configure automated backup procedures for critical instances"
- "Implement compliance scanning across the infrastructure"
- "Set up automated scaling based on CloudWatch metrics"

## Security Considerations

When using this MCP server, you should consider:

- Ensuring proper IAM permissions are configured before use
- Use AWS CloudTrail for additional security monitoring
- Configure resource-specific permissions when possible instead of wildcard permissions
- Consider using resource tagging for better governance and cost management
- Review all changes made by the MCP server as part of your regular security reviews
- If you would like to restrict the MCP to readonly operations, specify --readonly in the startup arguments

### Required IAM Permissions

Ensure your AWS credentials have the following minimum permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:ListDocuments",
                "ssm:GetDocument",
                "ssm:CreateDocument",
                "ssm:UpdateDocument",
                "ssm:DeleteDocument",
                "ssm:DescribeDocumentPermission",
                "ssm:ModifyDocumentPermission",
                "ssm:StartAutomationExecution",
                "ssm:GetAutomationExecution",
                "ssm:StopAutomationExecution",
                "ssm:DescribeAutomationExecutions",
                "ssm:DescribeAutomationStepExecutions",
                "ssm:SendAutomationSignal",
                "ssm:SendCommand",
                "ssm:GetCommandInvocation",
                "ssm:ListCommands",
                "ssm:ListCommandInvocations",
                "ssm:CancelCommand",
                "ssm:GetParameter",
                "ssm:GetParameters",
                "ssm:GetParametersByPath",
                "ssm:PutParameter",
                "ssm:DeleteParameter",
                "ssm:DescribeInstanceInformation"
            ],
            "Resource": "*"
        }
    ]
}
```

## Limitations

- Operations are limited to Systems Manager services and features
- Performance depends on the underlying AWS services' response times
- Some complex workflows may require multiple operations
- Automation execution monitoring requires additional CloudWatch permissions
- Rate limiting may affect operations when managing many resources simultaneously
- Some document types might have service-specific constraints
- Document sharing is limited to AWS accounts within the same partition
- Parameter Store has limits on parameter size and throughput
- Command execution depends on SSM Agent availability on target instances
