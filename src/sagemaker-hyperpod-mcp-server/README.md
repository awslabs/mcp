# Amazon SageMaker HyperPod MCP Server

The Amazon SageMaker HyperPod MCP server provides AI code assistants with resource management tools and real-time cluster state visibility. This provides large language models (LLMs) with essential tooling and contextual awareness, enabling AI code assistants to assist with application development through tailored guidance — from initial setup workflows through ongoing management.

Integrating the HyperPod MCP server into AI code assistants enhances development workflow across all phases, from assisting with initial cluster setup workflows using the same managed CloudFormation templates as the AWS SageMaker HyperPod console UI. Further, it helps with cluster management through high-level workflows and guidance. All of this simplifies complex operations through natural language interactions in AI code assistants.

## Key features

* Enables users of AI code assistants to interact with HyperPod cluster deployment workflows, utilizing the same managed CloudFormation templates used by the HyperPod console UI for consistent and approved deployments.
* Provides the ability to interface with HyperPod cluster stacks and resources via managed CloudFormation templates and user-provided custom parameter values.
* Supports full lifecycle management of HyperPod cluster nodes, enabling listing, describing, updating software, and deleting operations.

## Prerequisites

* [Install Python 3.10+](https://www.python.org/downloads/release/python-3100/)
* [Install the `uv` package manager](https://docs.astral.sh/uv/getting-started/installation/)
* [Install and configure the AWS CLI with credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)

## Setup

Add these IAM policies to the IAM role or user that you use to manage your HyperPod cluster resources.

### Read-Only Operations Policy

For read operations, the following permissions are required:

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:ListClusters",
        "sagemaker:DescribeCluster",
        "sagemaker:ListClusterNodes",
        "sagemaker:DescribeClusterNode",
        "cloudformation:DescribeStacks"
      ],
      "Resource": "*"
    }
  ]
}
```

### Write Operations Policy

For write operations, we recommend the following IAM policies to ensure successful deployment of HyperPod clusters using the managed CloudFormation templates:

* [**IAMFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/IAMFullAccess.html): Enables creation and management of IAM roles and policies required for cluster operation. After cluster creation and if no new IAM role needs to be created, we recommend reducing the scope of this policy permissions.
* [**AmazonVPCFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonVPCFullAccess.html): Allows creation and configuration of VPC resources including subnets, route tables, internet gateways, and NAT gateways
* [**AWSCloudFormationFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSCloudFormationFullAccess.html): Provides permissions to create, update, and delete CloudFormation stacks that orchestrate the deployment
* [**AmazonSageMakerFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonSageMakerFullAccess.html): Required for creating and managing HyperPod clusters and cluster nodes
* [**AmazonS3FullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonS3FullAccess.html): Required for creating S3 buckets storing LifeCyle scripts and so on
* [**AWSLambda_FullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSLambda_FullAccess.html): Required for interacting Lambda functions to manage HyperPod clusters and other resources
* [**CloudWatchLogsFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/CloudWatchLogsFullAccess.html): Required for operations on CloudWatch logs
* [**AmazonFSxFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonFSxFullAccess.html): Required for operations on FSx file systems
* **EKS Full Access (provided below)**: Required for interacting with EKS clusters orchestrating HyperPod

   ```
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "eks:*",
        "Resource": "*"
      }
    ]
  }
   ```


**Important Security Note**: Users should exercise caution when `--allow-write` and `--allow-sensitive-data-access` modes are enabled with these broad permissions, as this combination grants significant privileges to the MCP server. Only enable these flags when necessary and in trusted environments. For production use, consider creating more restrictive custom policies.

## Quickstart

This quickstart guide walks you through the steps to configure the Amazon SageMaker HyperPod MCP Server for use with the [Amazon Q Developer CLI](https://github.com/aws/amazon-q-developer-cli). By following these steps, you'll setup your development environment to leverage the HyperPod MCP Server's tools for managing your Amazon SageMaker HyperPod clusters and resources.


**Set up the Amazon Q Developer CLI**

1. Install the [Amazon Q Developer CLI](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-installing.html) .
2. The Q Developer CLI supports MCP servers for tools and prompts out-of-the-box. Edit your Q developer CLI's MCP configuration file named mcp.json following [these instructions](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-mcp-configuration.html).

The example below includes both the `--allow-write` flag for mutating operations and the `--allow-sensitive-data-access` flag for accessing logs and events (see the Arguments section for more details):

   **For Mac/Linux:**

	```
	{
	  "mcpServers": {
	    "awslabs.sagemaker-hyperpod-mcp-server": {
	      "command": "uvx",
	      "args": [
	        "awslabs.sagemaker-hyperpod-mcp-server@latest",
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
	    "awslabs.sagemaker-hyperpod-mcp-server": {
	      "command": "uvx",
	      "args": [
	        "--from",
	        "awslabs.sagemaker-hyperpod-mcp-server@latest",
	        "awslabs.sagemaker-hyperpod-mcp-server.exe",
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

3. Verify your setup by running the `/tools` command in the Q Developer CLI to see the available HyperPod MCP tools.

Note that this is a basic quickstart. You can enable additional capabilities, such as combining more MCP servers like the [AWS Documentation MCP Server](https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server/) into a single MCP server definition. To view an example, see the [Installation and Setup](https://github.com/awslabs/mcp?tab=readme-ov-file#installation-and-setup) guide in AWS MCP Servers on GitHub. To view a real-world implementation with application code in context with an MCP server, see the [Server Developer](https://modelcontextprotocol.io/quickstart/server) guide in Anthropic documentation.

## Configurations

### Arguments

The `args` field in the MCP server definition specifies the command-line arguments passed to the server when it starts. These arguments control how the server is executed and configured. For example:

**For Mac/Linux:**
```
{
  "mcpServers": {
    "awslabs.sagemaker-hyperpod-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.sagemaker-hyperpod-mcp-server@latest",
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
    "awslabs.sagemaker-hyperpod-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.sagemaker-hyperpod-mcp-server@latest",
        "awslabs.sagemaker-hyperpod-mcp-server.exe",
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
* `awslabs.sagemaker-hyperpod-mcp-server@latest` - Specifies the latest package/version specifier for the MCP client config.

**For Windows:**
* `--from awslabs.sagemaker-hyperpod-mcp-server@latest awslabs.sagemaker-hyperpod-mcp-server.exe` - Windows requires the `--from` flag to specify the package and the `.exe` extension.

Both formats enable MCP server startup and tool registration.

#### `--allow-write` (optional)

Enables write access mode, which allows mutating operations (e.g., create, update, delete resources) for manage_hyperpod_stacks, manage_hyperpod_cluster_nodes tool operations.

* Default: false (The server runs in read-only mode by default)
* Example: Add `--allow-write` to the `args` list in your MCP server definition.

#### `--allow-sensitive-data-access` (optional)

Enables access to sensitive data such as logs, events, and cluster details. This flag is required for tools that access potentially sensitive information.

* Default: false (Access to sensitive data is restricted by default)
* Example: Add `--allow-sensitive-data-access` to the `args` list in your MCP server definition.

### Environment variables

The `env` field in the MCP server definition allows you to configure environment variables that control the behavior of the HyperPod MCP server.  For example:

```
{
  "mcpServers": {
    "awslabs.sagemaker-hyperpod-mcp-server": {
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

Specifies the AWS region where HyperPod clusters are managed, which will be used for all AWS service operations.

* Default: None (If not set, uses default AWS region).
* Example: `"AWS_REGION": "us-west-2"`

## Tools

The following tools are provided by the HyperPod MCP server for managing Amazon SageMaker HyperPod clusters and resources. Each tool performs a specific action that can be invoked to automate common tasks in your HyperPod clusters.

### HyperPod Cluster Management

#### `manage_hyperpod_stacks`

Provides interface to HyperPod CloudFormation stacks with operations for initiating deployments, describing, and deleting HyperPod clusters and their underlying infrastructure. **Note**: Cluster creation typically takes around 30 minutes to complete.

Features:

* Interfaces with HyperPod cluster deployments using the same managed CloudFormation templates as the HyperPod console UI.
* Allows users to specify parameter override values as a JSON object for more customized HyperPod stack creation.
* Describes existing HyperPod CloudFormation stacks, providing details like status, outputs, and creation time.
* Deletes HyperPod CloudFormation stacks and their associated resources, ensuring proper cleanup.
* Ensures safety by only modifying/deleting stacks that were originally created by this tool.
* Does not create, modify, or provision CloudFormation templates - only interfaces with existing managed templates.

Parameters:

* operation (deploy, describe, delete), stack_name, region_name, profile_name, params_file (for deploy)

### HyperPod Cluster Node Operations

#### `manage_hyperpod_cluster_nodes`

Manages SageMaker HyperPod clusters and nodes with both read and write operations.

Features:

* Provides a consolidated interface for all cluster and node-related operations.
* Supports listing clusters with filtering by name, creation time, and training plan ARN.
* Supports listing nodes with filtering by creation time and instance group name.
* Returns detailed information about specific nodes in a cluster.
* Initiates software updates for all nodes or specific instance groups in a cluster.
* Deletes multiple nodes from a cluster in a single operation.

Operations:

* **list_clusters**: Lists SageMaker HyperPod clusters with options for pagination and filtering.
* **list_nodes**: Lists nodes in a SageMaker HyperPod cluster with options for pagination and filtering.
* **describe_node**: Gets detailed information about a specific node in a SageMaker HyperPod cluster.
* **update_software**: Updates the software for a SageMaker HyperPod cluster.
* **batch_delete**: Deletes multiple nodes from a SageMaker HyperPod cluster in a single operation.

Parameters:

* operation (list_clusters, list_nodes, describe_node, update_software, batch_delete)
* cluster_name (required for all operations except list_clusters)
* node_id (required for describe_node operation)
* node_ids (required for batch_delete operation)
* Additional parameters specific to each operation


## Security & permissions

### Features

The HyperPod MCP Server implements the following security features:

1. **AWS Authentication**: Uses AWS credentials from the environment for secure authentication.
2. **SSL Verification**: Enforces SSL verification for all AWS API calls.
3. **Resource Tagging**: Tags all created resources for traceability.
4. **Least Privilege**: Uses IAM roles with appropriate permissions for CloudFormation templates.
5. **Stack Protection**: Ensures CloudFormation stacks can only be modified by the tool that created them.

### Considerations

When using the HyperPod MCP Server, consider the following:

* **AWS Credentials**: The server needs permission to create and manage HyperPod resources.
* **Network Security**: Configure VPC and security groups properly for HyperPod clusters.
* **Authentication**: Use appropriate authentication mechanisms for AWS resources.
* **Authorization**: Configure IAM properly for AWS resources.
* **Data Protection**: Encrypt sensitive data in HyperPod clusters.
* **Logging and Monitoring**: Enable logging and monitoring for HyperPod clusters.

### Permissions

The HyperPod MCP Server can be used for production environments with proper security controls in place. The server runs in read-only mode by default, which is recommended and considered generally safer for production environments. Only explicitly enable write access when necessary. Below are the HyperPod MCP server tools available in read-only versus write-access mode:

* **Read-only mode (default)**: `manage_hyperpod_stacks` (with operation="describe"), `manage_hyperpod_cluster_nodes` (with operations="list_clusters", "list_nodes", "describe_node").
* **Write-access mode**: (require `--allow-write`): `manage_hyperpod_stacks` (with "deploy", "delete"), `manage_hyperpod_cluster_nodes` (with operations="update_software", "batch_delete").

#### `autoApprove` (optional)

An array within the MCP server definition that lists tool names to be automatically approved by the HyperPod MCP Server client, bypassing user confirmation for those specific tools. For example:

**For Mac/Linux:**
```
{
  "mcpServers": {
    "awslabs.sagemaker-hyperpod-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.sagemaker-hyperpod-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "hyperpod-mcp-readonly-profile",
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
    "awslabs.sagemaker-hyperpod-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.sagemaker-hyperpod-mcp-server@latest",
        "awslabs.sagemaker-hyperpod-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "hyperpod-mcp-readonly-profile",
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

1. **Create dedicated IAM roles** to be used by the HyperPod MCP Server with the principle of "least privilege."
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
* Use IAM roles for service accounts (IRSA) for AWS service access from pods.


### File System Access and Operating Mode

**Important**: This MCP server is intended for **STDIO mode only** as a local server using a single user's credentials. The server runs with the same permissions as the user who started it and has complete access to the file system.

#### Security and Access Considerations

- **Full File System Access**: The server can read from and writeq to any location on the file system where the user has permissions
- **Host File System Sharing**: When using this server, the host file system is directly accessible
- **Do Not Modify for Network Use**: This server is designed for local STDIO use only; network operation introduces additional security risks

#### Common File Operations

The MCP server can create a templated params json file to a user-specified absolute file path during hyperpod cluster creation.


## General Best Practices

* **Resource Naming**: Use descriptive names for HyperPod clusters and resources.
* **Error Handling**: Check for errors in tool responses and handle them appropriately.
* **Resource Cleanup**: Delete unused resources to avoid unnecessary costs.
* **Monitoring**: Monitor cluster and resource status regularly.
* **Security**: Follow AWS security best practices for HyperPod clusters.
* **Backup**: Regularly backup important HyperPod resources.

## General Troubleshooting

* **Permission Errors**: Verify that your AWS credentials have the necessary permissions.
* **CloudFormation Errors**: Check the CloudFormation console for stack creation errors.
* **SageMaker API Errors**: Verify that the HyperPod cluster is running and accessible.
* **Network Issues**: Check VPC and security group configurations.
* **Client Errors**: Verify that the MCP client is configured correctly.
* **Log Level**: Increase the log level to DEBUG for more detailed logs.

For general HyperPod issues, consult the [Amazon SageMaker HyperPod documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod.html).

## Version

Current MCP server version: 0.1.0
