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

This module implements the ROSA MCP Server, which provides tools for managing
Red Hat OpenShift Service on AWS (ROSA) clusters and Kubernetes resources
through the Model Context Protocol (MCP).

Authentication to the OCM (OpenShift Cluster Manager) API uses an offline token
exchanged for short-lived access tokens via Red Hat SSO.

Environment Variables:
    OCM_TOKEN: Red Hat offline token (from console.redhat.com/openshift/token)
    OCM_API_URL: OCM API base URL (default: https://api.openshift.com)
    AWS_REGION: AWS region to use for AWS API calls
    AWS_PROFILE: AWS profile to use for credentials
    FASTMCP_LOG_LEVEL: Log level (default: WARNING)
"""

import argparse
from awslabs.rosa_mcp_server.cloudwatch_handler import CloudWatchHandler
from awslabs.rosa_mcp_server.iam_handler import IAMHandler
from awslabs.rosa_mcp_server.k8s_handler import K8sHandler
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from awslabs.rosa_mcp_server.rosa_addon_handler import RosaAddonHandler
from awslabs.rosa_mcp_server.rosa_advanced_handler import RosaAdvancedHandler
from awslabs.rosa_mcp_server.rosa_advisor_handler import RosaAdvisorHandler
from awslabs.rosa_mcp_server.rosa_auth_handler import RosaAuthHandler
from awslabs.rosa_mcp_server.rosa_autoscaler_handler import RosaAutoscalerHandler
from awslabs.rosa_mcp_server.rosa_cluster_handler import RosaClusterHandler
from awslabs.rosa_mcp_server.rosa_config_handler import RosaConfigHandler
from awslabs.rosa_mcp_server.rosa_irsa_handler import RosaIRSAHandler
from awslabs.rosa_mcp_server.rosa_machinepool_handler import RosaMachinePoolHandler
from awslabs.rosa_mcp_server.rosa_networking_handler import RosaNetworkingHandler
from awslabs.rosa_mcp_server.rosa_operator_handler import RosaOperatorHandler
from awslabs.rosa_mcp_server.rosa_troubleshoot_handler import RosaTroubleshootHandler
from awslabs.rosa_mcp_server.rosa_user_handler import RosaUserHandler
from loguru import logger
from mcp.server.fastmcp import FastMCP


SERVER_INSTRUCTIONS = """
# ROSA MCP Server - Red Hat OpenShift Service on AWS

This MCP server provides tools for managing ROSA clusters through the Model Context Protocol.
It communicates with the OCM (OpenShift Cluster Manager) REST API and AWS APIs directly -
no CLI tools (rosa, oc) are required on the host.

## IMPORTANT: Use MCP Tools for ROSA Operations

DO NOT use rosa, oc, or aws CLI commands directly. Always use the MCP tools provided by this
server for ROSA and OpenShift operations.

## Authentication

- **OCM API**: Set the OCM_TOKEN environment variable to your Red Hat offline token
  (obtain from https://console.redhat.com/openshift/token).
- **AWS APIs**: Standard AWS credential resolution (env vars, profiles, instance roles).

## Usage Notes

- By default, the server runs in read-only mode. Use the `--allow-write` flag to enable write
  operations (cluster creation/deletion, machine pool changes, IDP management).
- Access to sensitive data (pod logs, events) requires the `--allow-sensitive-data-access` flag.
- If OCM_TOKEN is not set, OCM-based tools will be unavailable but AWS-only tools (IAM,
  CloudWatch) will still function.

## Available Tool Categories

### Cluster Management (requires OCM_TOKEN)
- `rosa_list_clusters` - List all ROSA clusters
- `rosa_describe_cluster` - Get detailed cluster information
- `rosa_create_cluster` - Create a new ROSA cluster (requires --allow-write)
- `rosa_delete_cluster` - Delete a ROSA cluster (requires --allow-write)
- `rosa_list_versions` - List available ROSA versions
- `rosa_list_upgrades` - List available upgrades for a cluster
- `rosa_upgrade_cluster` - Schedule a cluster upgrade (requires --allow-write)
- `rosa_get_cluster_credentials` - Get cluster credentials
- `rosa_get_install_logs` - Get cluster install logs

### Machine Pools (requires OCM_TOKEN)
- `rosa_list_machinepools` - List machine pools for a cluster
- `rosa_create_machinepool` - Create a machine pool (requires --allow-write)
- `rosa_update_machinepool` - Update a machine pool (requires --allow-write)
- `rosa_delete_machinepool` - Delete a machine pool (requires --allow-write)

### Authentication & Identity (requires OCM_TOKEN)
- `rosa_whoami` - Show current ROSA/OCM identity
- `rosa_list_idps` - List identity providers
- `rosa_create_idp` - Create an identity provider (requires --allow-write)
- `rosa_delete_idp` - Delete an identity provider (requires --allow-write)
- `rosa_create_admin` - Create cluster admin (requires --allow-write)

### Networking (requires OCM_TOKEN)
- `rosa_list_ingresses` - List ingress controllers
- `rosa_create_ingress` - Create an ingress (requires --allow-write)
- `rosa_update_ingress` - Update an ingress (requires --allow-write)
- `rosa_delete_ingress` - Delete an ingress (requires --allow-write)

### Kubernetes/OpenShift Operations (requires OCM_TOKEN)
- `rosa_list_resources` - List Kubernetes resources
- `rosa_get_pod_logs` - Get pod logs (requires --allow-sensitive-data-access)
- `rosa_get_events` - Get resource events (requires --allow-sensitive-data-access)
- `rosa_apply_yaml` - Apply YAML manifests (requires --allow-write)
- `rosa_get_nodes` - Get node status

### Monitoring (AWS-only, no OCM_TOKEN required)
- `rosa_get_cloudwatch_logs` - Get CloudWatch logs (requires --allow-sensitive-data-access)
- `rosa_get_cloudwatch_metrics` - Get CloudWatch metrics

### IAM (AWS-only, no OCM_TOKEN required)
- `rosa_get_account_roles` - List ROSA account IAM roles
- `rosa_get_operator_roles` - List operator roles
- `rosa_list_oidc_providers` - List OIDC providers
- `rosa_verify_quota` - Verify service quota

## Best Practices

- Use descriptive names for clusters and machine pools.
- Always verify cluster status before performing operations.
- Use `rosa_list_versions` to check available versions before creating or upgrading clusters.
- Monitor cluster health with CloudWatch metrics.
- Follow the principle of least privilege when creating IAM roles.
"""

SERVER_DEPENDENCIES = [
    'pydantic',
    'loguru',
    'httpx',
    'boto3',
    'kubernetes',
    'pyyaml',
]

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
        help='Enable sensitive data access (required for reading logs and events)',
    )

    args = parser.parse_args()

    allow_write = args.allow_write
    allow_sensitive_data_access = args.allow_sensitive_data_access

    mode_info = []
    if not allow_write:
        mode_info.append('read-only mode')
    if not allow_sensitive_data_access:
        mode_info.append('restricted sensitive data access mode')

    mode_str = ' in ' + ', '.join(mode_info) if mode_info else ''
    logger.info(f'Starting ROSA MCP Server{mode_str}')

    mcp = create_server()

    # Initialize OCM client (from env var, or ocm config file from `ocm login`)
    ocm_client = None
    try:
        ocm_client = OCMClient()
        logger.info('OCM client initialized successfully')
    except ValueError as e:
        logger.warning(
            f'OCM client unavailable: {e}. '
            'OCM-based tools (clusters, machine pools, IDPs, networking, K8s) will be disabled. '
            'AWS-only tools (IAM, CloudWatch) will still function. '
            'To enable: set OCM_TOKEN env var or run `ocm login --use-device-code`.'
        )

    # Register OCM-based handlers (only if OCM client is available)
    if ocm_client:
        RosaClusterHandler(mcp, ocm_client, allow_write)
        RosaAuthHandler(mcp, ocm_client, allow_write)
        RosaMachinePoolHandler(mcp, ocm_client, allow_write)
        RosaNetworkingHandler(mcp, ocm_client, allow_write)
        RosaAutoscalerHandler(mcp, ocm_client, allow_write)
        RosaAddonHandler(mcp, ocm_client, allow_write)
        RosaUserHandler(mcp, ocm_client, allow_write)
        RosaAdvancedHandler(mcp, ocm_client, allow_write)
        RosaOperatorHandler(mcp, ocm_client, allow_write)
        RosaIRSAHandler(mcp, ocm_client, allow_write)
        RosaConfigHandler(mcp, ocm_client, allow_write)
        K8sHandler(mcp, ocm_client, allow_write, allow_sensitive_data_access)
        RosaTroubleshootHandler(mcp, ocm_client, allow_sensitive_data_access)

    # Register handlers that don't need OCM (always available)
    RosaAdvisorHandler(mcp)
    CloudWatchHandler(mcp, allow_sensitive_data_access)
    IAMHandler(mcp, allow_sensitive_data_access, allow_write)

    mcp.run()

    return mcp


if __name__ == '__main__':
    main()
