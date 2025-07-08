# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""awslabs ROSA MCP Server implementation.

This module implements the ROSA MCP Server, which provides tools for managing Red Hat OpenShift 
Service on AWS (ROSA) clusters through the Model Context Protocol (MCP).

Environment Variables:
    AWS_REGION: AWS region to use for AWS API calls
    AWS_PROFILE: AWS profile to use for credentials
    FASTMCP_LOG_LEVEL: Log level (default: WARNING)
    ROSA_TOKEN: Red Hat account token for ROSA operations
"""

import argparse
from awslabs.rosa_mcp_server.rosa_cluster_handler import ROSAClusterHandler
from awslabs.rosa_mcp_server.rosa_auth_handler import ROSAAuthHandler
from awslabs.rosa_mcp_server.rosa_networking_handler import ROSANetworkingHandler
from awslabs.rosa_mcp_server.k8s_handler import K8sHandler
from awslabs.rosa_mcp_server.iam_handler import IAMHandler
from awslabs.rosa_mcp_server.cloudwatch_handler import CloudWatchHandler
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Define server instructions and dependencies
SERVER_INSTRUCTIONS = """
# Red Hat OpenShift Service on AWS (ROSA) MCP Server

This MCP server provides tools for managing ROSA clusters and is the preferred mechanism for creating new ROSA clusters.

## IMPORTANT: Use MCP Tools for ROSA and OpenShift Operations

DO NOT use standard ROSA and OpenShift CLI commands (rosa, oc, kubectl). Always use the MCP tools provided by this server for ROSA and OpenShift operations.

## Usage Notes

- By default, the server runs in read-only mode. Use the `--allow-write` flag to enable write operations.
- Access to sensitive data (logs, events, OpenShift Secrets) requires the `--allow-sensitive-data-access` flag.
- Ensure you have valid AWS credentials and Red Hat account token configured.
- When creating or updating resources, always check for existing resources first to avoid conflicts.
- ROSA clusters require proper IAM policies and roles - use the provided tools to set these up.

## Common Workflows

### Creating a ROSA Cluster
1. Set up account roles: `setup_rosa_account_roles()`
2. Create cluster: `create_rosa_cluster(cluster_name='my-rosa-cluster', region='us-east-1', version='4.14.0')`
3. Create operator roles: `create_rosa_operator_roles(cluster_name='my-rosa-cluster')`
4. Create OIDC provider: `create_rosa_oidc_provider(cluster_name='my-rosa-cluster')`
5. Monitor installation: `describe_rosa_cluster(cluster_name='my-rosa-cluster')`

### Managing Machine Pools
1. List machine pools: `list_rosa_machine_pools(cluster_name='my-rosa-cluster')`
2. Create machine pool: `create_rosa_machine_pool(cluster_name='my-rosa-cluster', name='workers', replicas=3)`
3. Scale machine pool: `update_rosa_machine_pool(cluster_name='my-rosa-cluster', name='workers', replicas=5)`

### Configuring Identity Providers
1. Add GitHub IDP: `create_rosa_idp(cluster_name='my-rosa-cluster', type='github', name='github-auth', client_id='...', client_secret='...')`
2. Add LDAP IDP: `create_rosa_idp(cluster_name='my-rosa-cluster', type='ldap', name='ldap-auth', url='ldaps://...')`
3. List IDPs: `list_rosa_idps(cluster_name='my-rosa-cluster')`

### Deploying Applications
1. Connect to cluster: `get_rosa_cluster_credentials(cluster_name='my-rosa-cluster')`
2. Create namespace: `manage_k8s_resource(cluster_name='my-rosa-cluster', operation='create', kind='Namespace', api_version='v1', name='my-app')`
3. Deploy application: `apply_yaml(yaml_path='/path/to/manifest.yaml', cluster_name='my-rosa-cluster', namespace='my-app')`
4. Monitor deployment: `list_k8s_resources(cluster_name='my-rosa-cluster', kind='Pod', api_version='v1', namespace='my-app')`

### Troubleshooting ROSA Issues
1. Check cluster status: `describe_rosa_cluster(cluster_name='my-rosa-cluster')`
2. Get cluster logs: `get_rosa_cluster_logs(cluster_name='my-rosa-cluster')`
3. Check pod status: `list_k8s_resources(cluster_name='my-rosa-cluster', kind='Pod', api_version='v1', namespace='openshift-*')`
4. Get pod logs: `get_pod_logs(cluster_name='my-rosa-cluster', namespace='openshift-logging', pod_name='cluster-logging-operator-*')`

### Enhanced Workflows (Based on ROSA E-book Best Practices)

#### Production-Ready Cluster Creation
Use the enhanced workflow for production clusters:
`create_production_rosa_cluster(cluster_name='prod-cluster', region='us-east-1', environment='production')`

#### Day 2 Operations
Get a comprehensive checklist for ongoing operations:
`get_day2_operations_checklist(cluster_name='my-rosa-cluster')`

#### Migration Planning
Generate migration plans from other platforms:
`generate_rosa_migration_plan(source_platform='kubernetes', target_cluster='my-rosa-cluster', applications=['app1', 'app2'])`

## Best Practices

- Use descriptive names for clusters and resources to make them easier to identify and manage.
- Enable STS mode for enhanced security when creating clusters.
- Configure proper network access (PrivateLink for private clusters).
- Set up identity providers before granting cluster access to users.
- Monitor cluster costs using AWS Cost Explorer and ROSA cost management.
- Use machine pools to manage different node types and workloads.
- Apply proper labels and tags to resources for better organization.
- Follow OpenShift security best practices for workload deployment.
- Regularly update ROSA clusters to the latest stable version.
- **NEW**: Use validation helpers to ensure cluster configurations follow best practices.
- **NEW**: Leverage workflow helpers for production-ready deployments.
- **NEW**: Follow the Day 2 operations checklist for optimal cluster management.
"""

SERVER_DEPENDENCIES = [
    'pydantic',
    'loguru',
    'boto3',
    'kubernetes',
    'requests',
    'pyyaml',
    'cachetools',
    'requests_auth_aws_sigv4',
    'click',
]

# Global reference to the MCP server instance for testing purposes
mcp = None


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.rosa-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
        dependencies=SERVER_DEPENDENCIES,
    )


def main():
    """Run the MCP server with CLI argument support."""
    global mcp

    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for Red Hat OpenShift Service on AWS (ROSA)'
    )
    parser.add_argument(
        '--allow-write',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable write access mode (allow mutating operations)',
    )
    parser.add_argument(
        '--allow-sensitive-data-access',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable sensitive data access (required for reading logs, events, and OpenShift Secrets)',
    )

    args = parser.parse_args()

    allow_write = args.allow_write
    allow_sensitive_data_access = args.allow_sensitive_data_access

    # Log startup mode
    mode_info = []
    if not allow_write:
        mode_info.append('read-only mode')
    if not allow_sensitive_data_access:
        mode_info.append('restricted sensitive data access mode')

    mode_str = ' in ' + ', '.join(mode_info) if mode_info else ''
    logger.info(f'Starting ROSA MCP Server{mode_str}')

    # Create the MCP server instance
    mcp = create_server()

    # Initialize handlers - all tools are always registered, access control is handled within tools
    ROSAClusterHandler(mcp, allow_write)
    ROSAAuthHandler(mcp, allow_write)
    ROSANetworkingHandler(mcp, allow_write)
    K8sHandler(mcp, allow_write, allow_sensitive_data_access)
    IAMHandler(mcp, allow_write)
    CloudWatchHandler(mcp, allow_sensitive_data_access)

    # Run server
    mcp.run()

    return mcp


if __name__ == '__main__':
    main()