# Amazon EKS MCP Server

The Amazon EKS MCP server provides AI code assistants with resource management tools and real-time cluster state visibility. This provides large language models (LLMs) with essential tooling and contextual awareness, enabling AI code assistants to streamline application development through tailored guidance — from initial setup through production optimization and troubleshooting.

Integrating the EKS MCP server into AI code assistants enhances development workflow across all phases, from simplifying initial cluster setup with automated prerequisite creation and application of best practices. Further, it streamlines application deployment with high-level workflows and automated code generation. Finally, it accelerates troubleshooting through intelligent debugging tools and knowledge base access. All of this simplifies complex operations through natural language interactions in AI code assistants.

## Key features

* Enables users of AI code assistants to create new EKS clusters, complete with prerequisites such as dedicated VPCs, networking, and EKS Auto Mode node pools, by translating requests into the appropriate AWS CloudFormation actions.
* Provides the ability to deploy containerized applications by applying existing Kubernetes YAML files or by generating new deployment and service manifests based on user-provided parameters.
* Supports full lifecycle management of individual Kubernetes resources (such as Pods, Services, and Deployments) within EKS clusters, enabling create, read, update, patch, and delete operations.
* Provides the ability to list Kubernetes resources with filtering by namespace, labels, and fields, simplifying the process for both users and LLMs to gather information about the state of Kubernetes applications and EKS infrastructure.
* Facilitates operational tasks such as retrieving logs from specific pods and containers or fetching Kubernetes events related to particular resources, supporting troubleshooting and monitoring for both direct users and AI-driven workflows.
* Enables users to troubleshoot issues with an EKS cluster.

## Prerequisites

* [Install Python 3.10+](https://www.python.org/downloads/release/python-3100/)
* [Install the `uv` package manager](https://docs.astral.sh/uv/getting-started/installation/)
* [Install and configure the AWS CLI with credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)

## Setup

Add these IAM policies to the IAM role or user that you use to manage your EKS cluster resources.

### Read-Only Operations Policy

For read operations, the following permissions are required:

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "cloudformation:DescribeStacks",
        "cloudwatch:GetMetricData",
        "logs:StartQuery",
        "logs:GetQueryResults",
        "iam:GetRole",
        "iam:GetRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "iam:GetPolicy",
        "iam:GetPolicyVersion",
        "eks-mcpserver:QueryKnowledgeBase"
      ],
      "Resource": "*"
    }
  ]
}
```

### Write Operations Policy

For write operations, we recommend the following IAM policies to ensure successful deployment of EKS clusters using the CloudFormation template in `/awslabs/eks_mcp_server/templates/eks-templates/eks-with-vpc.yaml`:

* [**IAMFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/IAMFullAccess.html): Enables creation and management of IAM roles and policies required for cluster operation
* [**AmazonVPCFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonVPCFullAccess.html): Allows creation and configuration of VPC resources including subnets, route tables, internet gateways, and NAT gateways
* [**AWSCloudFormationFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSCloudFormationFullAccess.html): Provides permissions to create, update, and delete CloudFormation stacks that orchestrate the deployment
* **EKS Full Access (provided below)**: Required for creating and managing EKS clusters, including control plane configuration, node groups, and add-ons
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

### Kubernetes API Access Requirements

All Kubernetes API operations will only work when one of the following conditions is met:

1. The user's principal (IAM role/user) actually created the EKS cluster being accessed
2. An EKS Access Entry has been configured for the user's principal

If you encounter authorization errors when using Kubernetes API operations, verify that an access entry has been properly configured for your principal.

## Quickstart

This quickstart guide walks you through the steps to configure the Amazon EKS MCP Server for use with both the [Cursor](https://www.cursor.com/en/downloads) IDE and the [Amazon Q Developer CLI](https://github.com/aws/amazon-q-developer-cli). By following these steps, you'll setup your development environment to leverage the EKS MCP Server's tools for managing your Amazon EKS clusters and Kubernetes resources.

**Set up Cursor**

1. Open Cursor.
2. Click the gear icon (⚙️) in the top right to open the settings panel, click **MCP**, **Add new global MCP server**.
3. Paste your MCP server definition. For example, this example shows how to configure the EKS MCP Server, including enabling mutating actions by adding the `--allow-write` flag to the server arguments:

	```
	{
	  "mcpServers": {
	    "awslabs.eks-mcp-server": {
	      "autoApprove": [],
	      "disabled": false,
	      "command": "uvx",
	      "args": [
	        "awslabs.eks-mcp-server@latest",
	        "--allow-write"
	      ],
	      "env": {
	        "FASTMCP_LOG_LEVEL": "ERROR"
	      },
	      "transportType": "stdio"
	    }
	  }
	}
	```

	After a few minutes, you should see a green indicator if your MCP server definition is valid.

4. Open a chat panel in Cursor (e.g., `Ctrl/⌘ + L`).  In your Cursor chat window, enter your prompt. For example, "Create a new EKS cluster named 'my-test-cluster' in the 'us-west-2' region using Kubernetes version 1.31."

**Set up the Amazon Q Developer CLI**

1. Install the [Amazon Q Developer CLI](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-installing.html) .
2. The Q Developer CLI supports MCP servers for tools and prompts out-of-the-box. Edit your Q developer CLI's MCP configuration file named mcp.json following [these instructions](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-mcp-configuration.html). For example:

	```
	{
	  "mcpServers": {
	    "awslabs.eks-mcp-server": {
	      "command": "uvx",
	      "args": ["awslabs.eks-mcp-server@latest"],
	      "env": {
	        "FASTMCP_LOG_LEVEL": "ERROR"
	      },
	      "autoApprove": [],
	      "disabled": false
	    }
	  }
	}
	```

3. Verify your setup by running the `/tools` command in the Q Developer CLI to see the available EKS MCP tools.

Note that this is a basic quickstart. You can enable additional capabilities, such as [running MCP servers in containers](https://github.com/awslabs/mcp?tab=readme-ov-file#running-mcp-servers-in-containers) or combining more MCP servers like the [AWS Documentation MCP Server](https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server/) into a single MCP server definition. To view an example, see the [Installation and Setup](https://github.com/awslabs/mcp?tab=readme-ov-file#installation-and-setup) guide in AWS MCP Servers on GitHub. To view a real-world implementation with application code in context with an MCP server, see the [Server Developer](https://modelcontextprotocol.io/quickstart/server) guide in Anthropic documentation.

## Configurations

### Arguments

The `args` field in the MCP server definition specifies the command-line arguments passed to the server when it starts. These arguments control how the server is executed and configured. For example:

```
{
  "mcpServers": {
    "awslabs.eks-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.eks-mcp-server@latest",
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

#### `awslabs.eks-mcp-server@latest` (required)

Specifies the latest package/version specifier for the MCP client config.

* Enables MCP server startup and tool registration.

#### `--allow-write` (optional)

Enables write access mode, which allows mutating operations (e.g., create, update, delete resources) for apply_yaml, generate_app_manifest, manage_k8s_resource, manage_eks_stacks, add_inline_policy tool operations.

* Default: false (The server runs in read-only mode by default)
* Example: Add `--allow-write` to the `args` list in your MCP server definition.

#### `--allow-sensitive-data-access` (optional)

Enables access to sensitive data such as logs, events, and Kubernetes Secrets.

* Default: false (Access to sensitive data is restricted by default)
* Example: Add `--allow-sensitive-data-access` to the `args` list in your MCP server definition.

### Environment variables

The `env` field in the MCP server definition allows you to configure environment variables that control the behavior of the EKS MCP server.  For example:

```
{
  "mcpServers": {
    "awslabs.eks-mcp-server": {
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

Specifies the AWS region where EKS clusters are managed, which will be used for all AWS service operations.

* Default: None (If not set, uses default AWS region).
* Example: `"AWS_REGION": "us-west-2"`

## Tools

The following tools are provided by the EKS MCP server for managing Amazon EKS clusters and Kubernetes resources. Each tool performs a specific action that can be invoked to automate common tasks in your EKS clusters and Kubernetes workloads.

### EKS Cluster Management

#### `manage_eks_stacks`

Manages EKS CloudFormation stacks with operations for generating templates, deploying, describing, and deleting EKS clusters and their underlying infrastructure. **Note**: Cluster creation typically takes 15-20 minutes to complete.

Features:

* Generates CloudFormation templates for EKS clusters, embedding specified cluster names.
* Deploys EKS clusters using CloudFormation, creating or updating stacks with VPC, subnets, NAT gateways, IAM roles, and node pools.
* Describes existing EKS CloudFormation stacks, providing details like status, outputs, and creation time.
* Deletes EKS CloudFormation stacks and their associated resources, ensuring proper cleanup.
* Ensures safety by only modifying/deleting stacks that were originally created by this tool.

Parameters:

* operation (generate, deploy, describe, delete), template_file (for generate/deploy), cluster_name

### Kubernetes Resource Management

#### `manage_k8s_resource`

Manages individual Kubernetes resources with various operations.

Features:

* Supports create, replace, patch, delete, and read Kubernetes operations.
* Handles both namespaced and non-namespaced Kubernetes resources.

Parameters:

* operation (create, replace, patch, delete, read), cluster_name, kind, api_version, name, namespace (optional), body (for create/replace/patch)

#### `apply_yaml`

Applies Kubernetes YAML manifests to an EKS cluster.

Features:

* Supports multi-document YAML files.
* Applies all resources in the manifest to the specified namespace.
* Can update existing resources if force is true.

Parameters:

* yaml_path, cluster_name, namespace, force

#### `list_k8s_resources`

Lists Kubernetes resources of a specific kind in an EKS cluster.

Features:

* Returns summaries of EKS resources with metadata.
* Supports filtering by EKS cluster namespace, labels, and fields.

Parameters:

* cluster_name, kind, api_version, namespace (optional), label_selector (optional), field_selector (optional)

#### `list_api_versions`

Lists all available API versions in the specified Kubernetes cluster.

Features:

* Discovers all available API versions on the Kubernetes cluster.
* Helps determine the correct `apiVersion` to use for managing Kubernetes resources.
* Includes both core APIs (e.g., "v1") and API groups (e.g., "apps/v1", "networking.k8s.io/v1").

Parameters:

* cluster_name

### Application Support

#### `generate_app_manifest`

Generates Kubernetes manifests for application deployment.

Features:

* Generates Kubernetes deployment and service YAMLs with configurable parameters.
* Supports load balancer configuration and resource requests.
* Outputs Kubernetes manifest to a specified directory.

Parameters:

* app_name, image_uri, output_dir, port (optional), replicas (optional), cpu (optional), memory (optional), namespace (optional), load_balancer_scheme (optional)

#### `get_pod_logs`

Retrieves logs from pods in a Kubernetes cluster.

Features:

* Supports filtering logs by time, line count, and byte size.
* Can retrieve logs from specific containers in a pod.
* Requires `--allow-sensitive-data-access` server flag to be enabled.

Parameters:

* cluster_name, pod_name, namespace, container_name (optional), since_seconds (optional), tail_lines (optional), limit_bytes (optional)

#### `get_k8s_events`

Retrieves events related to specific Kubernetes resources.

Features:

* Returns Kubernetes event details including timestamps, count, message, reason, reporting component, and type.
* Supports both namespaced and non-namespaced Kubernetes resources.
* Requires `--allow-sensitive-data-access` server flag to be enabled.

Parameters:

* cluster_name, kind, name, namespace (optional)

### CloudWatch Integration

#### `get_cloudwatch_logs`

Retrieves logs from CloudWatch for a specific resource within an EKS cluster.

Features:

* Fetches logs based on resource type (pod, node, container), resource name, and log type.
* Allows filtering by time range (minutes, start/end time), log content (filter_pattern), and number of entries.
* Supports specifying custom fields to be included in the query results.
* Requires `--allow-sensitive-data-access` server flag to be enabled.

Parameters:

* cluster_name, log_type (application, host, performance, control-plane, custom), resource_type (pod, node, container, cluster),
resource_name (optional), minutes (optional), start_time (optional), end_time (optional), limit (optional), filter_pattern (optional), fields (optional)

#### `get_cloudwatch_metrics`

Retrieves metrics from CloudWatch for Kubernetes resources.

Features:

* Fetches metrics based on metric name and dimensions.
* Allows specification of CloudWatch namespace and time range.
* Configurable period, statistic (Average, Sum, etc.), and limit for data points.
* Supports providing custom dimensions for fine-grained metric querying.

Parameters:

* cluster_name, metric_name, namespace, dimensions, minutes (optional), start_time (optional), end_time (optional), limit (optional), stat (optional), period (optional)

#### `get_eks_metrics_guidance`

Provides guidance on available CloudWatch metrics for different resource types in EKS clusters.

Features:

* Returns a list of available Container Insights metrics for the specified resource type, including metric names, dimensions, and descriptions.
* Helps determine the correct dimensions to use with the `get_cloudwatch_metrics` tool.
* Supports the following resource types:
  * `cluster`: Metrics for EKS clusters (e.g., cluster_node_count, cluster_failed_node_count)
  * `node`: Metrics for EKS nodes (e.g., node_cpu_utilization, node_memory_utilization, node_network_total_bytes)
  * `pod`: Metrics for Kubernetes pods (e.g., pod_cpu_utilization, pod_memory_utilization, pod_network_rx_bytes)
  * `namespace`: Metrics for Kubernetes namespaces (e.g., namespace_number_of_running_pods)
  * `service`: Metrics for Kubernetes services (e.g., service_number_of_running_pods)

Parameters:

* resource_type

Implementation:

The data in `/awslabs/eks_mcp_server/data/eks_cloudwatch_metrics_guidance.json` is generated by a Python script (`/awslabs/eks_mcp_server/scripts/update_eks_cloudwatch_metrics_guidance.py`) that scrapes the [Container Insights metrics table](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html) from AWS documentation. Running the script requires installing BeautifulSoup (used for parsing HTML content) with uv: `uv pip install bs4`.

### IAM Integration

#### `get_policies_for_role`

Retrieves all policies attached to a specified IAM role, including assume role policy, managed policies, and inline policies.

Features:

* Fetches the assume role policy document for the specified IAM role.
* Lists all attached managed policies and includes their policy documents.
* Lists all embedded inline policies and includes their policy documents.

Parameters:

* role_name

#### `add_inline_policy`

Adds a new inline policy with specified permissions to an IAM role; it will not modify existing policies. It will only create new policies; it will reject requests to modify existing policies.

Features:

* Creates and attaches a new inline policy to a specified IAM role.
* Rejects requests if the policy name already exists on the role to prevent accidental modification.
* Requires `--allow-write` server flag to be enabled.
* Accepts permissions as a single JSON object (statement) or a list of JSON objects (statements).

Parameters:

* policy_name, role_name, permissions (JSON object or array of objects)

### Troubleshooting

#### `search_eks_troubleshoot_guide`

Searches the EKS Troubleshoot Guide for troubleshooting information based on a query.

Features:

* Provides detailed troubleshooting guidance for Amazon EKS issues.
* Covers EKS Auto mode node provisioning, bootstrap issues, and controller failure modes.
* Returns symptoms, step-by-step short-term, and long-term fixes for identified issues.

Parameters:

* query


## Security & permissions

### Features

The EKS MCP Server implements the following security features:

1. **AWS Authentication**: Uses AWS credentials from the environment for secure authentication.
2. **Kubernetes Authentication**: Generates temporary credentials for Kubernetes API access.
3. **SSL Verification**: Enforces SSL verification for all Kubernetes API calls.
4. **Resource Tagging**: Tags all created resources for traceability.
5. **Least Privilege**: Uses IAM roles with appropriate permissions for CloudFormation templates.
6. **Stack Protection**: Ensures CloudFormation stacks can only be modified by the tool that created them.
7. **Client Caching**: Caches Kubernetes clients with TTL-based expiration for security and performance.

### Considerations

When using the EKS MCP Server, consider the following:

* **AWS Credentials**: The server needs permission to create and manage EKS resources.
* **Kubernetes Access**: The server generates temporary credentials for Kubernetes API access.
* **Network Security**: Configure VPC and security groups properly for EKS clusters.
* **Authentication**: Use appropriate authentication mechanisms for Kubernetes resources.
* **Authorization**: Configure RBAC properly for Kubernetes resources.
* **Data Protection**: Encrypt sensitive data in Kubernetes secrets.
* **Logging and Monitoring**: Enable logging and monitoring for EKS clusters.

### Permissions

The EKS MCP Server can be used for production environments with proper security controls in place. The server runs in read-only mode by default, which is recommended and considered generally safer for production environments. Only explicitly enable write access when necessary. Below are the EKS MCP server tools available in read-only versus write-access mode:

* **Read-only mode (default)**: `manage_eks_stacks` (with operation="describe"), `manage_k8s_resource` (with operation="read"), `list_k8s_resources`, `get_pod_logs`, `get_k8s_events`, `get_cloudwatch_logs`, `get_cloudwatch_metrics`, `get_policies_for_role`, `search_eks_troubleshoot_guide`, `list_api_versions`.
* **Write-access mode**: (require `--allow-write`): `manage_eks_stacks` (with "generate", "deploy", "delete"), `manage_k8s_resource` (with "create", "replace", "patch", "delete"), `apply_yaml`, `generate_app_manifest`, `add_inline_policy`.

#### `autoApprove` (optional)

An array within the MCP server definition that lists tool names to be automatically approved by the EKS MCP Server client, bypassing user confirmation for those specific tools. For example:

```
{
  "mcpServers": {
    "awslabs.eks-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.eks-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "eks-mcp-readonly-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "autoApprove": [
        "manage_eks_stacks",
        "manage_k8s_resource",
        "list_k8s_resources",
        "get_pod_logs",
        "get_k8s_events",
        "get_cloudwatch_logs",
        "get_cloudwatch_metrics",
        "get_policies_for_role",
        "search_eks_troubleshoot_guide",
        "list_api_versions"
      ]
    }
  }
}
```

### IAM Permissions Management

When the `--allow-write` flag is enabled, the EKS MCP Server can create missing IAM permissions for EKS resources through the `add_inline_policy` tool. This tool enables the following:

* Only creates new inline policies; it never modifies existing policies.
* Is useful for automatically fixing common permissions issues with EKS clusters.
* Should be used with caution and with properly scoped IAM roles.

### Role Scoping Recommendations

In accordance with security best practices, we recommend the following:

1. **Create dedicated IAM roles** to be used by the EKS MCP Server with the principle of "least privilege."
2. **Use separate roles** for read-only and write operations.
3. **Implement resource tagging** to limit actions to resources created by the server.
4. **Enable AWS CloudTrail** to audit all API calls made by the server.
5. **Regularly review** the permissions granted to the server's IAM role.
6. **Use IAM Access Analyzer** to identify unused permissions that can be removed.

### Sensitive Information Handling

**IMPORTANT**: Do not pass secrets or sensitive information via allowed input mechanisms:

* Do not include secrets or credentials in YAML files applied with `apply_yaml`.
* Do not pass sensitive information directly in the prompt to the model.
* Do not include secrets in CloudFormation templates or application manifests.
* Avoid using MCP tools for creating Kubernetes Secrets, as this would require providing the secret data to the model.

**YAML Content Security**:

* Only use YAML files from trustworthy sources.
* The server relies on Kubernetes API validation for YAML content and does not perform its own validation.
* Audit YAML files before applying them to your cluster.

**Instead of passing secrets through MCP**:

* Use AWS Secrets Manager or Parameter Store to store sensitive information.
* Configure proper Kubernetes RBAC for service accounts.
* Use IAM roles for service accounts (IRSA) for AWS service access from pods.

## General Best Practices

* **Resource Naming**: Use descriptive names for EKS clusters and Kubernetes resources.
* **Namespace Usage**: Organize resources into namespaces for better management.
* **Error Handling**: Check for errors in tool responses and handle them appropriately.
* **Resource Cleanup**: Delete unused resources to avoid unnecessary costs.
* **Monitoring**: Monitor cluster and resource status regularly.
* **Security**: Follow AWS security best practices for EKS clusters.
* **Backup**: Regularly backup important Kubernetes resources.

## General Troubleshooting

* **Permission Errors**: Verify that your AWS credentials have the necessary permissions.
* **CloudFormation Errors**: Check the CloudFormation console for stack creation errors.
* **Kubernetes API Errors**: Verify that the EKS cluster is running and accessible.
* **Network Issues**: Check VPC and security group configurations.
* **Client Errors**: Verify that the MCP client is configured correctly.
* **Log Level**: Increase the log level to DEBUG for more detailed logs.

For general EKS issues, consult the [Amazon EKS documentation](https://docs.aws.amazon.com/eks/).

## Version

Current MCP server version: 0.1.0
