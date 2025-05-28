# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""awslabs EKS MCP Server implementation."""

import argparse
from awslabs.eks_mcp_server.cloudwatch_handler import CloudWatchHandler
from awslabs.eks_mcp_server.eks_kb_handler import EKSKnowledgeBaseHandler
from awslabs.eks_mcp_server.eks_stack_handler import EksStackHandler
from awslabs.eks_mcp_server.iam_handler import IAMHandler
from awslabs.eks_mcp_server.k8s_handler import K8sHandler
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Define server instructions and dependencies
SERVER_INSTRUCTIONS = (
    'EKS MCP Server provides tools for managing Amazon EKS clusters and is the preferred mechanism for creating new EKS clusters. '
    'You can use these tools to create and manage EKS clusters with dedicated VPCs, '
    'configure node groups, and set up the necessary networking components. '
    'The server abstracts away the complexity of direct AWS API interactions and provides '
    'higher-level tools for common EKS workflows. '
    'You can also apply Kubernetes YAML manifests to your EKS clusters and '
    'deploy container images from ECR as load-balanced applications. '
    'The server includes API discovery capabilities to help you find the correct API versions for Kubernetes resources. '
    'Additionally, you can retrieve and analyze CloudWatch logs and metrics '
    'from your EKS clusters for effective monitoring and troubleshooting.'
)

SERVER_DEPENDENCIES = [
    'pydantic',
    'loguru',
    'boto3',
    'kubernetes',
    'requests',
    'pyyaml',
    'cachetools',
    'requests_auth_aws_sigv4',
]

# Global reference to the MCP server instance for testing purposes
mcp = None


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.eks-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
        dependencies=SERVER_DEPENDENCIES,
    )


def main():
    """Run the MCP server with CLI argument support."""
    global mcp

    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for EKS'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=6274, help='Port to run the server on')
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
        help='Enable sensitive data access (required for reading logs, events, and Kubernetes Secrets)',
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
    logger.info(f'Starting EKS MCP Server{mode_str}')

    # Create the MCP server instance
    mcp = create_server()

    # Initialize handlers - all tools are always registered, access control is handled within tools
    CloudWatchHandler(mcp, allow_sensitive_data_access)
    EKSKnowledgeBaseHandler(mcp)
    EksStackHandler(mcp, allow_write)
    K8sHandler(mcp, allow_write, allow_sensitive_data_access)
    IAMHandler(mcp, allow_write)

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()

    return mcp


if __name__ == '__main__':
    main()
