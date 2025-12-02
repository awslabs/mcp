# Amazon SageMaker HyperPod Tools

This module provides MCP tools for managing Amazon SageMaker HyperPod clusters and resources.

## Key Features

* Enables AI agents to reliably setup HyperPod clusters orchestrated by Amazon EKS or Slurm complete with pre-requisites, powered by CloudFormation templates that optimize networking, storage, and compute resources. Clusters created via this MCP server are fully optimized for high-performance distributed training and inference workloads, leveraging best practice architectures to maximize throughput and minimize latency at scale.
* Provides the ability to interface with HyperPod cluster stacks and resources via managed CloudFormation templates and user-provided custom parameter values.
* Supports full lifecycle management of HyperPod cluster nodes, enabling listing, describing, updating software i.e AMIs, and deleting operations.

## Prerequisites

In addition to the general prerequisites for the SageMaker AI MCP Server, HyperPod-specific operations require appropriate IAM permissions.

### IAM Permissions

Add these IAM policies to the IAM role or user that you use to manage your HyperPod cluster resources.

#### Read-Only Operations Policy

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

#### Write Operations Policy

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

## Tools

The following tools are provided for managing Amazon SageMaker HyperPod clusters and resources. Each tool performs a specific action that can be invoked to automate common tasks in your HyperPod clusters.

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

## Best Practices

* **Resource Naming**: Use descriptive names for HyperPod clusters and resources.
* **Error Handling**: Check for errors in tool responses and handle them appropriately.
* **Resource Cleanup**: Delete unused resources to avoid unnecessary costs.
* **Monitoring**: Monitor cluster and resource status regularly.
* **Security**: Follow AWS security best practices for HyperPod clusters.
* **Backup**: Regularly backup important HyperPod resources.

## Troubleshooting

* **Permission Errors**: Verify that your AWS credentials have the necessary permissions.
* **CloudFormation Errors**: Check the CloudFormation console for stack creation errors.
* **SageMaker API Errors**: Verify that the HyperPod cluster is running and accessible.
* **Network Issues**: Check VPC and security group configurations.
* **Client Errors**: Verify that the MCP client is configured correctly.
* **Log Level**: Increase the log level to DEBUG for more detailed logs.

For general HyperPod issues, consult the [Amazon SageMaker HyperPod documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod.html).
