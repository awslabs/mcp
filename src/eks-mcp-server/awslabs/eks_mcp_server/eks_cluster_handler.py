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


from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.eks_mcp_server.models import ListClustersResponse
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import List, Optional


class EksClusterHandler:
    """Handler for Amazon EKS cluster operations.

    This class provides tools for interacting with Amazon EKS clusters,
    including listing available clusters.
    """

    def __init__(self, mcp):
        """Initialize the EKS cluster handler.

        Args:
            mcp: The MCP server instance
        """
        self.mcp = mcp

        # Register tools
        self.mcp.tool(name='list_clusters')(self.list_clusters)

    async def list_clusters(
        self,
        ctx: Context,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
        include: Optional[List[str]] = None,
    ) -> ListClustersResponse:
        """List all EKS clusters in the current AWS account and region.

        This tool retrieves a list of all Amazon EKS clusters in the current AWS
        account and region. It's useful for discovering available clusters before
        performing operations on them, such as deploying applications or querying
        Kubernetes resources.

        ## Requirements
        - Valid AWS credentials configured
        - EKS permissions to list clusters

        ## Response Information
        The response includes a list of cluster names and the total count.

        Args:
            ctx: MCP context
            max_results: Maximum number of results (1-100)
            next_token: Token for pagination
            include: List containing 'all' to include external clusters

        Returns:
            ListClustersResponse with cluster names and count
        """
        try:
            log_with_request_id(ctx, LogLevel.INFO, 'Listing EKS clusters')

            # Get EKS client and list clusters
            eks_client = AwsHelper.create_boto3_client('eks')

            # Build parameters for list_clusters call
            params = {}
            if max_results is not None:
                params['maxResults'] = max_results
            if next_token is not None:
                params['nextToken'] = next_token
            if include is not None:
                params['include'] = include

            response = eks_client.list_clusters(**params)
            cluster_names = response['clusters']
            response_next_token = response.get('nextToken')

            # Log success
            log_with_request_id(ctx, LogLevel.INFO, f'Found {len(cluster_names)} EKS clusters')

            # Return success response
            return ListClustersResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully listed {len(cluster_names)} EKS clusters',
                    )
                ],
                clusters=cluster_names,
                count=len(cluster_names),
                next_token=response_next_token,
            )

        except Exception as e:
            # Log error
            error_msg = f'Failed to list EKS clusters: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return ListClustersResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                clusters=[],
                count=0,
                next_token=None,
            )
