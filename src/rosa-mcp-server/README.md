# Red Hat OpenShift Service on AWS (ROSA) MCP Server

An MCP (Model Context Protocol) server for managing Red Hat OpenShift Service on AWS (ROSA) clusters. This server provides a comprehensive set of tools for creating, managing, and monitoring ROSA clusters through a unified interface.

## Features

- **Cluster Management**: Create, delete, describe, and list ROSA clusters
- **Authentication**: Set up IAM roles, OIDC providers, and identity providers
- **Machine Pools**: Create and manage node pools with different configurations
- **Networking**: Configure ingress controllers, load balancers, and network settings
- **Kubernetes/OpenShift Operations**: Deploy applications, manage resources, view logs
- **Monitoring**: Access CloudWatch metrics and logs for cluster monitoring
- **IAM Integration**: Manage IAM roles and policies for ROSA

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **ROSA CLI** installed and configured
3. **Python 3.10+**
4. Valid Red Hat account with ROSA access
5. AWS account with ROSA enabled

## Installation

```bash
# Using uv (recommended)
uv pip install awslabs.rosa-mcp-server

# Using pip
pip install awslabs.rosa-mcp-server
```

## Configuration

The server uses the following environment variables:

- `AWS_REGION`: AWS region for operations (defaults to us-east-1)
- `AWS_PROFILE`: AWS profile to use for authentication
- `ROSA_TOKEN`: Red Hat account token (optional, for programmatic access)

## Usage

### Starting the Server

```bash
# Start in read-only mode (default)
awslabs.rosa-mcp-server

# Enable write operations
awslabs.rosa-mcp-server --allow-write

# Enable sensitive data access (for logs and secrets)
awslabs.rosa-mcp-server --allow-write --allow-sensitive-data-access
```

### Common Operations

#### Creating a ROSA Cluster

```python
# Set up account roles (one-time setup)
setup_rosa_account_roles()

# Create a cluster
create_rosa_cluster(
    cluster_name="my-rosa-cluster",
    region="us-east-1",
    version="4.14.0",
    multi_az=True,
    replicas=3
)

# Create operator roles and OIDC provider
create_rosa_operator_roles(cluster_name="my-rosa-cluster")
create_rosa_oidc_provider(cluster_name="my-rosa-cluster")
```

#### Managing Machine Pools

```python
# List machine pools
list_rosa_machine_pools(cluster_name="my-rosa-cluster")

# Create a new machine pool
create_rosa_machine_pool(
    cluster_name="my-rosa-cluster",
    name="gpu-workers",
    replicas=2,
    instance_type="p3.2xlarge",
    labels={"workload": "gpu"}
)

# Scale a machine pool
update_rosa_machine_pool(
    cluster_name="my-rosa-cluster",
    name="workers",
    replicas=5
)
```

#### Configuring Authentication

```python
# Add GitHub identity provider
create_rosa_idp(
    cluster_name="my-rosa-cluster",
    type="github",
    name="github-auth",
    client_id="your-client-id",
    client_secret="your-client-secret",
    organizations=["your-org"]
)

# Grant user access
grant_rosa_user_access(
    cluster_name="my-rosa-cluster",
    username="john.doe",
    role="cluster-admin"
)
```

#### Deploying Applications

```python
# Apply Kubernetes manifest
apply_yaml(
    yaml_path="/path/to/deployment.yaml",
    cluster_name="my-rosa-cluster",
    namespace="default"
)

# List pods
list_k8s_resources(
    cluster_name="my-rosa-cluster",
    kind="Pod",
    namespace="default"
)

# Get pod logs
get_pod_logs(
    cluster_name="my-rosa-cluster",
    namespace="default",
    pod_name="my-app-pod"
)
```

#### Monitoring

```python
# Get cluster metrics
get_rosa_metrics(
    cluster_name="my-rosa-cluster",
    metric_name="node_cpu_utilization",
    start_time="-1h"
)

# View CloudWatch logs
get_rosa_cloudwatch_logs(
    cluster_name="my-rosa-cluster",
    log_group="/aws/containerinsights/my-rosa-cluster/application",
    start_time="-1h",
    filter_pattern="ERROR"
)
```

## Available Tools

### Cluster Management
- `list_rosa_clusters` - List all ROSA clusters
- `describe_rosa_cluster` - Get cluster details
- `create_rosa_cluster` - Create a new cluster
- `delete_rosa_cluster` - Delete a cluster
- `get_rosa_cluster_credentials` - Get cluster access credentials
- `get_rosa_cluster_logs` - Get installation/uninstallation logs

### Authentication & IAM
- `setup_rosa_account_roles` - Set up account-wide IAM roles
- `create_rosa_operator_roles` - Create operator-specific roles
- `create_rosa_oidc_provider` - Create OIDC provider
- `list_rosa_idps` - List identity providers
- `create_rosa_idp` - Create identity provider
- `delete_rosa_idp` - Delete identity provider
- `create_rosa_admin` - Create temporary admin user
- `grant_rosa_user_access` - Grant user access

### Machine Pools
- `list_rosa_machine_pools` - List machine pools
- `create_rosa_machine_pool` - Create machine pool
- `update_rosa_machine_pool` - Update machine pool
- `delete_rosa_machine_pool` - Delete machine pool

### Networking
- `edit_rosa_cluster_network` - Edit network settings
- `list_rosa_ingresses` - List ingress controllers
- `create_rosa_ingress` - Create ingress controller
- `edit_rosa_ingress` - Edit ingress controller
- `delete_rosa_ingress` - Delete ingress controller
- `configure_rosa_autoscaling` - Configure cluster autoscaling
- `update_rosa_cluster_privacy` - Update cluster privacy settings

### Kubernetes/OpenShift
- `apply_yaml` - Apply YAML manifests
- `list_k8s_resources` - List resources
- `manage_k8s_resource` - CRUD operations on resources
- `get_pod_logs` - Get pod logs
- `get_k8s_events` - Get resource events
- `list_api_versions` - List available API versions

### Monitoring
- `get_rosa_metrics` - Get CloudWatch metrics
- `list_rosa_metrics` - List available metrics
- `get_rosa_cloudwatch_logs` - Get CloudWatch logs
- `create_rosa_cloudwatch_alarm` - Create CloudWatch alarm

### IAM
- `list_rosa_iam_roles` - List ROSA-related IAM roles
- `create_rosa_iam_policy` - Create IAM policy
- `attach_rosa_policy_to_role` - Attach policy to role
- `list_rosa_role_policies` - List role policies
- `create_rosa_service_linked_role` - Create service-linked role
- `validate_rosa_permissions` - Validate IAM permissions

## Security Considerations

1. **Read-Only by Default**: The server starts in read-only mode. Use `--allow-write` to enable modifications.
2. **Sensitive Data Protection**: Access to logs and secrets requires `--allow-sensitive-data-access`.
3. **IAM Permissions**: Ensure your AWS credentials have necessary permissions for ROSA operations.
4. **Resource Tagging**: All resources created by the server are tagged for tracking.

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure AWS CLI and ROSA CLI are properly configured
2. **Permission Denied**: Check IAM permissions and use appropriate flags
3. **Cluster Creation Fails**: Verify account roles and service quotas
4. **Network Connectivity**: Check VPC and security group configurations

### Debug Mode

Set environment variable for verbose logging:
```bash
export FASTMCP_LOG_LEVEL=DEBUG
```

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests to our repository.

## Support

For issues and feature requests, please file an issue on our GitHub repository.