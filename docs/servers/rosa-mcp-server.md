# Red Hat OpenShift Service on AWS (ROSA) MCP Server

## Overview

The ROSA MCP Server provides comprehensive tools for managing Red Hat OpenShift Service on AWS (ROSA) clusters through the Model Context Protocol. It enables you to create, manage, and monitor ROSA clusters, handle authentication, configure networking, and deploy applications using OpenShift's enterprise Kubernetes platform.

## Key Features

- **Cluster Lifecycle Management**: Create, delete, describe, and list ROSA clusters
- **Authentication & Security**: Set up IAM roles, OIDC providers, and identity providers
- **Machine Pool Management**: Create and scale node pools with different configurations
- **Networking Configuration**: Manage ingress controllers, load balancers, and network settings
- **Kubernetes/OpenShift Operations**: Deploy applications, manage resources, and view logs
- **Monitoring Integration**: Access CloudWatch metrics and logs for cluster monitoring
- **IAM Management**: Handle IAM roles and policies specific to ROSA

## Installation

```bash
# Using uv (recommended)
uv pip install awslabs.rosa-mcp-server

# Using pip
pip install awslabs.rosa-mcp-server
```

## Configuration

### Environment Variables

- `AWS_REGION`: AWS region for operations (defaults to us-east-1)
- `AWS_PROFILE`: AWS profile to use for authentication
- `ROSA_TOKEN`: Red Hat account token (optional, for programmatic access)

### Starting the Server

```bash
# Default read-only mode
awslabs.rosa-mcp-server

# Enable write operations
awslabs.rosa-mcp-server --allow-write

# Enable sensitive data access (for logs and secrets)
awslabs.rosa-mcp-server --allow-write --allow-sensitive-data-access
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **ROSA CLI** installed and configured
3. **Python 3.10+**
4. Valid Red Hat account with ROSA access
5. AWS account with ROSA enabled

## Usage Examples

### Creating a ROSA Cluster

```python
# One-time account setup
setup_rosa_account_roles()

# Create a multi-AZ production cluster
create_rosa_cluster(
    cluster_name="production-cluster",
    region="us-east-1",
    version="4.14.0",
    multi_az=True,
    replicas=3,
    machine_type="m5.xlarge"
)

# Set up required roles and OIDC
create_rosa_operator_roles(cluster_name="production-cluster")
create_rosa_oidc_provider(cluster_name="production-cluster")
```

### Managing Machine Pools

```python
# Add a GPU machine pool for ML workloads
create_rosa_machine_pool(
    cluster_name="production-cluster",
    name="gpu-workers",
    replicas=2,
    instance_type="p3.2xlarge",
    labels={"workload": "gpu", "team": "ml"},
    taints=[{
        "key": "nvidia.com/gpu",
        "value": "true",
        "effect": "NoSchedule"
    }]
)

# Enable autoscaling for workers
update_rosa_machine_pool(
    cluster_name="production-cluster",
    name="workers",
    autoscaling_min=3,
    autoscaling_max=10
)
```

### Configuring Authentication

```python
# Add GitHub authentication
create_rosa_idp(
    cluster_name="production-cluster",
    type="github",
    name="github-auth",
    client_id="your-github-oauth-app-id",
    client_secret="your-github-oauth-secret",
    organizations=["your-org"]
)

# Grant cluster admin access
grant_rosa_user_access(
    cluster_name="production-cluster",
    username="john.doe@example.com",
    role="cluster-admin"
)
```

### Deploying Applications

```python
# Deploy an application
apply_yaml(
    yaml_path="/path/to/app-deployment.yaml",
    cluster_name="production-cluster",
    namespace="production"
)

# Check deployment status
list_k8s_resources(
    cluster_name="production-cluster",
    kind="Deployment",
    namespace="production",
    label_selector="app=myapp"
)

# View application logs
get_pod_logs(
    cluster_name="production-cluster",
    namespace="production",
    pod_name="myapp-deployment-xyz",
    tail_lines=100
)
```

### Networking Configuration

```python
# Create internal load balancer
create_rosa_ingress(
    cluster_name="production-cluster",
    listening="internal",
    lb_type="nlb",
    route_selectors={"tier": "internal"}
)

# Configure cluster for private access
update_rosa_cluster_privacy(
    cluster_name="production-cluster",
    private=True
)
```

### Monitoring and Troubleshooting

```python
# Get cluster metrics
get_rosa_metrics(
    cluster_name="production-cluster",
    metric_name="node_cpu_utilization",
    start_time="-1h",
    dimensions={"NodeName": "worker-1"}
)

# Search logs for errors
get_rosa_cloudwatch_logs(
    cluster_name="production-cluster",
    log_group="/aws/containerinsights/production-cluster/application",
    filter_pattern="ERROR",
    start_time="-30m"
)

# Get cluster installation logs
get_rosa_cluster_logs(
    cluster_name="production-cluster",
    install=True
)
```

## Available Tools

### Cluster Management
- `list_rosa_clusters` - List all ROSA clusters
- `describe_rosa_cluster` - Get detailed cluster information
- `create_rosa_cluster` - Create a new ROSA cluster
- `delete_rosa_cluster` - Delete a ROSA cluster
- `get_rosa_cluster_credentials` - Get cluster access credentials
- `get_rosa_cluster_logs` - Get installation/uninstallation logs

### Authentication & IAM
- `setup_rosa_account_roles` - Set up account-wide IAM roles
- `create_rosa_operator_roles` - Create operator-specific IAM roles
- `create_rosa_oidc_provider` - Create OIDC provider for STS
- `list_rosa_idps` - List configured identity providers
- `create_rosa_idp` - Add identity provider (GitHub, LDAP, etc.)
- `delete_rosa_idp` - Remove identity provider
- `create_rosa_admin` - Create temporary admin user
- `grant_rosa_user_access` - Grant user cluster access
- `list_rosa_iam_roles` - List ROSA-related IAM roles
- `validate_rosa_permissions` - Validate IAM setup

### Machine Pools
- `list_rosa_machine_pools` - List all machine pools
- `create_rosa_machine_pool` - Create new machine pool
- `update_rosa_machine_pool` - Update machine pool configuration
- `delete_rosa_machine_pool` - Delete machine pool

### Networking
- `edit_rosa_cluster_network` - Configure proxy and CA bundles
- `list_rosa_ingresses` - List ingress controllers
- `create_rosa_ingress` - Create ingress controller
- `edit_rosa_ingress` - Modify ingress configuration
- `delete_rosa_ingress` - Remove ingress controller
- `configure_rosa_autoscaling` - Set up cluster autoscaling
- `update_rosa_cluster_privacy` - Change API endpoint visibility

### Kubernetes/OpenShift Operations
- `apply_yaml` - Apply YAML manifests
- `list_k8s_resources` - List Kubernetes resources
- `manage_k8s_resource` - CRUD operations on resources
- `get_pod_logs` - Retrieve pod logs
- `get_k8s_events` - Get resource events
- `list_api_versions` - List available API versions

### Monitoring
- `get_rosa_metrics` - Retrieve CloudWatch metrics
- `list_rosa_metrics` - List available metrics
- `get_rosa_cloudwatch_logs` - Get CloudWatch logs
- `create_rosa_cloudwatch_alarm` - Create metric alarms

## Best Practices

### Security
- Always use STS mode for enhanced security
- Configure identity providers before granting user access
- Use machine pools with taints for specialized workloads
- Enable private cluster access for production environments

### Cost Optimization
- Use appropriate instance types for your workloads
- Enable autoscaling to optimize resource usage
- Monitor cluster metrics to identify underutilized resources
- Use machine pools to segregate workloads efficiently

### Operations
- Tag all resources for better organization
- Set up CloudWatch alarms for critical metrics
- Regularly update to the latest stable OpenShift version
- Use separate machine pools for different workload types

## Common Use Cases

### Multi-tenant Cluster
```python
# Create dedicated machine pools per team
for team in ["frontend", "backend", "data"]:
    create_rosa_machine_pool(
        cluster_name="shared-cluster",
        name=f"{team}-pool",
        replicas=3,
        labels={"team": team},
        taints=[{"key": f"team/{team}", "value": "true", "effect": "NoSchedule"}]
    )
```

### High Availability Setup
```python
# Create HA cluster across AZs
create_rosa_cluster(
    cluster_name="ha-cluster",
    region="us-east-1",
    multi_az=True,
    replicas=3,
    machine_type="m5.xlarge"
)

# Add multiple ingress controllers
create_rosa_ingress(
    cluster_name="ha-cluster",
    listening="external",
    lb_type="nlb",
    replicas=3
)
```

### Development Environment
```python
# Create cost-optimized dev cluster
create_rosa_cluster(
    cluster_name="dev-cluster",
    region="us-east-1",
    multi_az=False,
    replicas=2,
    machine_type="t3.large"
)

# Enable autoscaling for cost efficiency
configure_rosa_autoscaling(
    cluster_name="dev-cluster",
    enable=True,
    min_nodes=2,
    max_nodes=5
)
```

## Troubleshooting

### Common Issues

1. **Cluster Creation Fails**
   - Verify account roles: `validate_rosa_permissions()`
   - Check service quotas in AWS
   - Ensure ROSA is enabled for your Red Hat account

2. **Authentication Issues**
   - Verify identity provider configuration
   - Check user permissions in the IDP
   - Ensure OIDC provider is created for STS clusters

3. **Network Connectivity**
   - Check VPC and subnet configurations
   - Verify security group rules
   - Ensure proxy settings are correct for private clusters

4. **Application Deployment Failures**
   - Check pod events: `get_k8s_events()`
   - Review pod logs: `get_pod_logs()`
   - Verify resource quotas and limits

## Security Considerations

- The server runs in read-only mode by default
- Write operations require explicit `--allow-write` flag
- Sensitive data access requires `--allow-sensitive-data-access`
- All resources are tagged for tracking and compliance
- IAM roles follow the principle of least privilege

## Additional Resources

- [Red Hat OpenShift Documentation](https://docs.openshift.com/)
- [ROSA Documentation](https://docs.openshift.com/rosa/welcome/index.html)
- [AWS ROSA Service Page](https://aws.amazon.com/rosa/)
- [OpenShift CLI Reference](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html)