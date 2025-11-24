# Amazon SageMaker AI MCP Server

The Amazon SageMaker AI MCP server provides agents with tools to enable high-performance, low-cost AI/ML model development. Currently, this server includes tools for managing SageMaker HyperPod clusters.

## Available Features

### SageMaker HyperPod

Provides comprehensive tools for managing SageMaker HyperPod clusters orchestrated with Amazon EKS or Slurm, including cluster deployment, node management, and lifecycle operations. See the [HyperPod documentation](https://github.com/awslabs/mcp/blob/main/src/sagemaker-ai-mcp-server/awslabs/sagemaker_ai_mcp_server/README.md) for detailed information on the supported tools.

## Prerequisites

* [Install Python 3.10+](https://www.python.org/downloads/release/python-3100/)
* [Install the `uv` package manager](https://docs.astral.sh/uv/getting-started/installation/)
* [Install and configure the AWS CLI with credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)

## Quickstart

This quickstart guide walks you through the steps to configure the Amazon SageMaker AI MCP Server for use with both the [Cursor](https://www.cursor.com/en/downloads) IDE and the [Amazon Q Developer CLI](https://github.com/aws/amazon-q-developer-cli).


**Set up Cursor**

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.sagemaker-ai-mcp-server&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwiY29tbWFuZCI6InV2eCBhd3NsYWJzLnNhZ2VtYWtlci1haS1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIC0tYWxsb3ctc2Vuc2l0aXZlLWRhdGEtYWNjZXNzIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwidHJhbnNwb3J0VHlwZSI6InN0ZGlvIn0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=SageMaker%20AI%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.sagemaker-ai-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |

**Set up the Amazon Q Developer CLI**

1. Install the [Amazon Q Developer CLI](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-installing.html).
2. The Q Developer CLI supports MCP servers for tools and prompts out-of-the-box. Edit your Q developer CLI's MCP configuration file named mcp.json following [these instructions](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-mcp-configuration.html).

The example below includes both the `--allow-write` flag for mutating operations and the `--allow-sensitive-data-access` flag for accessing logs and events:

   **For Mac/Linux:**

	```
	{
	  "mcpServers": {
	    "awslabs.sagemaker-ai-mcp-server": {
	      "command": "uvx",
	      "args": [
	        "awslabs.sagemaker-ai-mcp-server@latest",
	        "--allow-write",
	        "--allow-sensitive-data-access"
	      ],
	      "env": {
	        "FASTMCP_LOG_LEVEL": "ERROR"
	      },
	      "autoApprove": [],
	      "disabled": false
	    }
	  }
	}
	```

   **For Windows:**

	```
	{
	  "mcpServers": {
	    "awslabs.sagemaker-ai-mcp-server": {
	      "command": "uvx",
	      "args": [
	        "--from",
	        "awslabs.sagemaker-ai-mcp-server@latest",
	        "awslabs.sagemaker-ai-mcp-server.exe",
	        "--allow-write",
	        "--allow-sensitive-data-access"
	      ],
	      "env": {
	        "FASTMCP_LOG_LEVEL": "ERROR"
	      },
	      "autoApprove": [],
	      "disabled": false
	    }
	  }
	}
	```

3. Verify your setup by running the `/tools` command in the Q Developer CLI to see the available SageMaker AI MCP tools.

Note that this is a basic quickstart. We recommend to use SageMaker AI MCP server  in conjunction with [AWS API MCP Server](https://awslabs.github.io/mcp/servers/aws-api-mcp-server), [AWS Knowledge MCP Server](https://awslabs.github.io/mcp/servers/aws-knowledge-mcp-server)/[AWS Documentation MCP Server](https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server), and [AWS EKS MCP Server](https://awslabs.github.io/mcp/servers/eks-mcp-server) to gain complete coverage for all SageMaker APIs and effectively troubleshoot common issues.

## Configurations

### Arguments

The `args` field in the MCP server definition specifies the command-line arguments passed to the server when it starts. These arguments control how the server is executed and configured. For example:

**For Mac/Linux:**
```
{
  "mcpServers": {
    "awslabs.sagemaker-ai-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.sagemaker-ai-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "AWS_PROFILE": "your-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

**For Windows:**
```
{
  "mcpServers": {
    "awslabs.sagemaker-ai-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.sagemaker-ai-mcp-server@latest",
        "awslabs.sagemaker-ai-mcp-server.exe",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "AWS_PROFILE": "your-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

#### Command Format

The command format differs between operating systems:

**For Mac/Linux:**
* `awslabs.sagemaker-ai-mcp-server@latest` - Specifies the latest package/version specifier for the MCP client config.

**For Windows:**
* `--from awslabs.sagemaker-ai-mcp-server@latest awslabs.sagemaker-ai-mcp-server.exe` - Windows requires the `--from` flag to specify the package and the `.exe` extension.

#### `--allow-write` (optional)

Enables write access mode, which allows mutating operations (e.g., create, update, delete resources).

* Default: true (The server runs in write mode by default)
* Example: remove `--allow-write` from the `args` list in your MCP server definition to switch to readonly mode.

#### `--allow-sensitive-data-access` (optional)

Enables access to sensitive data such as logs, events, and resource details. This flag is required for tools that access potentially sensitive information.

* Default: true (Access to sensitive data is allowed by default)
* Example: remove `--allow-sensitive-data-access` from the `args` list in your MCP server definition to disable it.

### Environment variables

The `env` field in the MCP server definition allows you to configure environment variables that control the behavior of the SageMaker AI MCP server. For example:

```
{
  "mcpServers": {
    "awslabs.sagemaker-ai-mcp-server": {
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "my-profile",
        "AWS_REGION": "us-west-2"
      }
    }
  }
}
```

#### `FASTMCP_LOG_LEVEL` (optional)

Sets the logging level verbosity for the server.

* Valid values: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
* Default: "WARNING"
* Example: `"FASTMCP_LOG_LEVEL": "ERROR"`

#### `AWS_PROFILE` (optional)

Specifies the AWS profile to use for authentication.

* Default: None (If not set, uses default AWS credentials).
* Example: `"AWS_PROFILE": "my-profile"`

#### `AWS_REGION` (optional)

Specifies the AWS region where SageMaker resources are managed, which will be used for all AWS service operations.

* Default: None (If not set, uses default AWS region).
* Example: `"AWS_REGION": "us-west-2"`

## Security & Permissions

### Features

The SageMaker AI MCP Server implements the following security features:

1. **AWS Authentication**: Uses AWS credentials from the environment for secure authentication.
2. **SSL Verification**: Enforces SSL verification for all AWS API calls.
3. **Resource Tagging**: Tags all created resources for traceability.
4. **Least Privilege**: Uses IAM roles with appropriate permissions.
5. **Stack Protection**: Ensures CloudFormation stacks for HyperPod can only be modified by the tool that created them.

### Considerations

When using the SageMaker AI MCP Server, consider the following:

* **AWS Credentials**: The server needs permission to create and manage SageMaker AI resources.
* **Network Security**: Configure VPC and security groups properly for SageMaker AI resources.
* **Authentication**: Use appropriate authentication mechanisms for AWS resources.
* **Authorization**: Configure IAM properly for AWS resources.
* **Data Protection**: Encrypt sensitive data in SageMaker AI resources.
* **Logging and Monitoring**: Enable logging and monitoring for SageMaker AI resources.

### Permissions

The SageMaker AI MCP Server can be used for production environments with proper security controls in place. The server runs in read-only mode by default, which is recommended and considered generally safer for production environments. Only explicitly enable write access when necessary. Below are the HyperPod MCP tools available in read-only versus write-access mode:

* **Read-only mode (default)**: `manage_hyperpod_stacks` (with operation="describe"), `manage_hyperpod_cluster_nodes` (with operations="list_clusters", "list_nodes", "describe_node").
* **Write-access mode**: (require `--allow-write`): `manage_hyperpod_stacks` (with "deploy", "delete"), `manage_hyperpod_cluster_nodes` (with operations="update_software", "batch_delete").

#### `autoApprove` (optional)

An array within the MCP server definition that lists tool names to be automatically approved by the MCP Server client, bypassing user confirmation for those specific tools. For example:

**For Mac/Linux:**
```
{
  "mcpServers": {
    "awslabs.sagemaker-ai-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.sagemaker-ai-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "sagemaker-ai-mcp-readonly-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "autoApprove": [
        "manage_hyperpod_stacks",
        "manage_hyperpod_cluster_nodes"
      ]
    }
  }
}
```

**For Windows:**
```
{
  "mcpServers": {
    "awslabs.sagemaker-ai-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.sagemaker-ai-mcp-server@latest",
        "awslabs.sagemaker-ai-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "sagemaker-ai-mcp-readonly-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "autoApprove": [
        "manage_hyperpod_stacks",
        "manage_hyperpod_cluster_nodes"
      ]
    }
  }
}
```

### Role Scoping Recommendations

In accordance with security best practices, we recommend the following:

1. **Create dedicated IAM roles** to be used by the SageMaker AI MCP Server with the principle of "least privilege."
2. **Use separate roles** for read-only and write operations.
3. **Implement resource tagging** to limit actions to resources created by the server.
4. **Enable AWS CloudTrail** to audit all API calls made by the server.
5. **Regularly review** the permissions granted to the server's IAM role.
6. **Use IAM Access Analyzer** to identify unused permissions that can be removed.

### Sensitive Information Handling

**IMPORTANT**: Do not pass secrets or sensitive information via allowed input mechanisms:

* Do not include secrets or credentials in CloudFormation templates.
* Do not pass sensitive information directly in the prompt to the model.
* Avoid using MCP tools for creating secrets, as this would require providing the secret data to the model.

**CloudFormation Template Security**:

* Only use CloudFormation templates from trustworthy sources.
* The server relies on CloudFormation API validation for template content and does not perform its own validation.
* Audit CloudFormation templates before applying them to your cluster.

**Instead of passing secrets through MCP**:

* Use AWS Secrets Manager or Parameter Store to store sensitive information.
* Configure proper IAM roles for service accounts.
* Use IAM roles for service accounts (IRSA) for AWS service access.

### File System Access and Operating Mode

**Important**: This MCP server is intended for **STDIO mode only** as a local server using a single user's credentials. The server runs with the same permissions as the user who started it and has complete access to the file system.

#### Security and Access Considerations

- **Full File System Access**: The server can read from and write to any location on the file system where the user has permissions
- **Host File System Sharing**: When using this server, the host file system is directly accessible
- **Do Not Modify for Network Use**: This server is designed for local STDIO use only; network operation introduces additional security risks

#### Common File Operations

The MCP server can create a templated params json file to a user-specified absolute file path during hyperpod cluster creation.


## General Best Practices

* **Resource Naming**: Use descriptive names for SageMaker AI resources.
* **Error Handling**: Check for errors in tool responses and handle them appropriately.
* **Resource Cleanup**: Delete unused resources to avoid unnecessary costs.
* **Monitoring**: Monitor resource status regularly.
* **Security**: Follow AWS security best practices for SageMaker AI resources.
* **Backup**: Regularly backup important SageMaker AI resources.

## General Troubleshooting

* **Permission Errors**: Verify that your AWS credentials have the necessary permissions.
* **CloudFormation Errors**: Check the CloudFormation console for stack creation errors.
* **SageMaker API Errors**: Verify that the HyperPod cluster is running and accessible.
* **Network Issues**: Check VPC and security group configurations.
* **Client Errors**: Verify that the MCP client is configured correctly.
* **Log Level**: Increase the log level to DEBUG for more detailed logs.

For service-specific issues, consult the relevant service documentation:
- [HyperPod Documentation](https://github.com/awslabs/mcp/blob/main/src/sagemaker-ai-mcp-server/awslabs/sagemaker_ai_mcp_server/README.md)
- [Amazon SageMaker AI Documentation](https://docs.aws.amazon.com/sagemaker/)

## Version

Current MCP server version: 1.0.0
