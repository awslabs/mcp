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

"""awslabs SageMaker AI MCP Server implementation.

This module implements the SageMaker AI MCP Server, which provides tools for managing Amazon SageMaker AI resources
including HyperPod clusters and nodes through the Model Context Protocol (MCP).

Environment Variables:
    AWS_REGION: AWS region to use for AWS API calls
    AWS_PROFILE: AWS profile to use for credentials
    FASTMCP_LOG_LEVEL: Log level (default: WARNING)
"""

import argparse
import os
import sys
from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.hyperpod_cluster_node_handler import (
    HyperPodClusterNodeHandler,
)
from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.hyperpod_stack_handler import (
    HyperPodStackHandler,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Define server instructions and dependencies
SERVER_INSTRUCTIONS = """
# Amazon SageMaker AI MCP Server

This MCP server provides comprehensive tools for managing Amazon SageMaker AI resources, currently including HyperPod cluster management.

## IMPORTANT: Use MCP Tools for SageMaker HyperPod Operations

DO NOT use standard SageMaker CLI commands (aws sagemaker). Always use the MCP tools provided by this server for SageMaker HyperPod operations.

## Available MCP Tools

### 1. HyperPod Cluster Node Management: `manage_hyperpod_cluster_nodes`
**Primary tool for cluster node operations**

**Operations:**
- `list_clusters`: List all HyperPod clusters with filtering and pagination
- `list_nodes`: List nodes in a specific cluster with filtering options
- `describe_node`: Get detailed information about a specific node
- `update_software`: Update cluster software/AMI versions (requires --allow-write)
- `batch_delete`: Delete multiple nodes from a cluster (requires --allow-write)

### 2. HyperPod Cluster Stack Management: `manage_hyperpod_stacks`
**Tool for managing HyperPod clusters and resources through CloudFormation**

**Operations:**
- `deploy`: Create or update a HyperPod cluster via CloudFormation stack (requires --allow-write)
- `describe`: Get information about an existing CloudFormation stack
- `delete`: Delete a CloudFormation stack and associated HyperPod cluster (requires --allow-write)


## Usage Notes

- By default, the server runs in read-only mode
- Use `--allow-write` flag to enable write operations (deploy, delete, update_software, batch_delete)
- When creating or updating resources, always check for existing resources first to avoid conflicts.

## Common Workflows

### 1. Listing and Managing Existing HyperPod Clusters
```
# List all clusters in a region
manage_hyperpod_cluster_nodes(operation='list_clusters', region_name='us-east-1')

# List nodes in a specific cluster
manage_hyperpod_cluster_nodes(operation='list_nodes', cluster_name='my-cluster')

# Get detailed information about a specific node
manage_hyperpod_cluster_nodes(operation='describe_node', cluster_name='my-cluster', node_id='i-1234567890abcdef0')

# Update cluster software (requires --allow-write)
manage_hyperpod_cluster_nodes(operation='update_software', cluster_name='my-cluster')
```

### 2. Creating HyperPod Clusters via CloudFormation
```
# Create or update a HyperPod cluster (requires --allow-write)
manage_hyperpod_stacks(operation='deploy', stack_name='my-cluster-stack', params_file='/path/to/params.json', region_name='us-east-1')

# Check deployment status
manage_hyperpod_stacks(operation='describe', stack_name='my-cluster-stack', region_name='us-east-1')
```

### 3. Deleting HyperPod Resources
```
# Delete specific nodes from a cluster (requires --allow-write)
manage_hyperpod_cluster_nodes(operation='batch_delete', cluster_name='my-cluster', node_ids=['i-1234567890abcdef0', 'i-0987654321fedcba0'])

# Delete entire cluster via CloudFormation (requires --allow-write)
manage_hyperpod_stacks(operation='delete', stack_name='my-cluster-stack', region_name='us-east-1')
```


## Best Practices

- **Resource Naming**: Use descriptive names for resources to make them easier to identify
- **Stack Management**: Use CloudFormation stacks (manage_hyperpod_stacks) for infrastructure as code and consistent deployments
- **Monitoring**: Regularly check cluster and node status using list and describe operations
- **Safety**: Always verify resource details before performing destructive operations (delete, batch_delete)
- **Access Control**: Follow the principle of least privilege when configuring IAM policies
- **Regional Considerations**: Specify the correct region for all operations to ensure you're working with the right resources

## Important Safety Notes

- **Destructive Operations**: batch_delete and stack deletion operations cannot be undone
- **Data Backup**: Always backup important data before deleting nodes or clusters
- **Write Access**: Mutating operations require the server to be started with --allow-write flag
- **Stack Ownership**: The stack management tool only operates on stacks it created (tagged appropriately)
"""

SERVER_DEPENDENCIES = [
    'pydantic',
    'loguru',
    'boto3',
    'requests',
    'pyyaml',
    'cachetools',
]

# Global reference to the MCP server instance for testing purposes
mcp = None


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.sagemaker-ai-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
        dependencies=SERVER_DEPENDENCIES,
    )


def main():
    """Run the MCP server with CLI argument support."""
    global mcp

    # Configure loguru logging
    logger.remove()
    logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for SageMaker AI'
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
        help='Enable sensitive data access (required for reading logs, events, and sensitive information)',
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
    logger.info(f'Starting SageMaker AI MCP Server{mode_str}')

    # Create the MCP server instance
    mcp = create_server()

    # Initialize handlers - all tools are always registered, access control is handled within tools
    HyperPodClusterNodeHandler(mcp, allow_write, allow_sensitive_data_access)
    HyperPodStackHandler(mcp, allow_write)

    # Run server
    mcp.run()

    return mcp


if __name__ == '__main__':
    main()
