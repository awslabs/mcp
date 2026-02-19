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

"""EKS cluster discovery handler for the EKS MCP Server.

This module provides tools for discovering and listing configured EKS clusters
across multiple AWS regions and accounts.
"""

import json
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.config import ClusterConfig, ConfigManager
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field
from typing import List, Optional


class ClusterInfo(BaseModel):
    """Information about a configured EKS cluster.

    Attributes:
        name: EKS cluster name
        region: AWS region where the cluster is located
        account_id: AWS account ID (if provided in config)
        description: Human-readable description (if provided in config)
        access_method: How credentials are obtained (role_assumption, profile, or default)
        status: Cluster status (ACTIVE, CREATING, etc.) - only populated when validate=True
        version: Kubernetes version - only populated when validate=True
    """

    name: str = Field(..., description='EKS cluster name')
    region: str = Field(..., description='AWS region')
    account_id: Optional[str] = Field(None, description='AWS account ID')
    description: Optional[str] = Field(None, description='Cluster description')
    access_method: str = Field(
        ...,
        description='Credential access method: role_assumption, profile, or default',
    )
    status: Optional[str] = Field(None, description='Cluster status (only when validated)')
    version: Optional[str] = Field(None, description='Kubernetes version (only when validated)')


class ListClustersData(BaseModel):
    """Response data for list_eks_clusters tool.

    Attributes:
        count: Number of configured clusters
        clusters: List of cluster information
    """

    count: int = Field(..., description='Number of configured clusters')
    clusters: List[ClusterInfo] = Field(..., description='List of cluster information')


class EKSDiscoveryHandler:
    """Handler for EKS cluster discovery operations.

    This class provides tools for discovering and listing EKS clusters
    that are configured in the cluster configuration file.
    """

    def __init__(self, mcp):
        """Initialize the EKS discovery handler.

        Args:
            mcp: The MCP server instance
        """
        self.mcp = mcp

        # Register tools
        self.mcp.tool(name='list_eks_clusters')(self.list_eks_clusters)

    async def list_eks_clusters(
        self,
        ctx: Context,
        validate: bool = Field(
            False,
            description="""Whether to validate each cluster is accessible by calling describe_cluster.
            When true, includes cluster status and Kubernetes version in the response.
            When false, returns only the configuration data without making API calls.""",
        ),
    ) -> CallToolResult:
        """List all configured EKS clusters.

        This tool returns the list of EKS clusters from the configuration file.
        It can optionally validate each cluster is accessible by querying the AWS API.

        ## Requirements
        - A cluster configuration file must be provided via --cluster-config flag
          or EKS_CLUSTER_CONFIG environment variable

        ## Response Information
        The response includes for each cluster:
        - name: Cluster name
        - region: AWS region
        - account_id: AWS account ID (if configured)
        - description: Description (if configured)
        - access_method: How credentials are obtained (role_assumption, profile, or default)
        - status: Cluster status (only when validate=True)
        - version: Kubernetes version (only when validate=True)

        ## Usage Tips
        - Use without validation for quick listing of configured clusters
        - Use with validation to verify cluster accessibility and get current status
        - Validation makes API calls and may take longer for many clusters

        Args:
            ctx: MCP context
            validate: Whether to validate cluster accessibility (default: False)

        Returns:
            ListClustersResponse with list of configured clusters
        """
        try:
            # Check if configuration is loaded
            if not ConfigManager.is_configured():
                error_msg = (
                    'No cluster configuration loaded. '
                    'Please provide a cluster configuration file via --cluster-config flag '
                    'or EKS_CLUSTER_CONFIG environment variable.'
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_msg)],
                )

            clusters = ConfigManager.list_clusters()
            log_with_request_id(ctx, LogLevel.INFO, f'Found {len(clusters)} configured clusters')

            results: List[ClusterInfo] = []
            for cluster in clusters:
                info = ClusterInfo(
                    name=cluster.name,
                    region=cluster.region,
                    account_id=cluster.account_id,
                    description=cluster.description,
                    access_method=cluster.get_access_method(),
                    status=None,
                    version=None,
                )

                # Optionally validate cluster accessibility
                if validate:
                    try:
                        log_with_request_id(
                            ctx,
                            LogLevel.DEBUG,
                            f'Validating cluster {cluster.name} in {cluster.region}',
                        )
                        eks_client = AwsHelper.create_boto3_client_for_cluster(cluster, 'eks')
                        response = eks_client.describe_cluster(name=cluster.name)
                        info.status = response['cluster']['status']
                        info.version = response['cluster']['version']
                        log_with_request_id(
                            ctx,
                            LogLevel.DEBUG,
                            f'Cluster {cluster.name}: status={info.status}, version={info.version}',
                        )
                    except Exception as e:
                        info.status = f'ERROR: {str(e)}'
                        log_with_request_id(
                            ctx,
                            LogLevel.WARNING,
                            f'Failed to validate cluster {cluster.name}: {e}',
                        )

                results.append(info)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully listed {len(results)} clusters'
                + (' with validation' if validate else ''),
            )

            data = ListClustersData(
                count=len(results),
                clusters=results,
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Found {len(results)} configured EKS clusters'
                        + (' (validated)' if validate else ''),
                    ),
                    TextContent(
                        type='text',
                        text=json.dumps(data.model_dump()),
                    ),
                ],
            )

        except Exception as e:
            error_msg = f'Failed to list EKS clusters: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
            )
