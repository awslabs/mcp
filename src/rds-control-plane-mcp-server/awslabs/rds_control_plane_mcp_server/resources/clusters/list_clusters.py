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

"""List Clusters handler for the RDS Control Plane MCP Server."""

import asyncio
import json
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_CLUSTER
from awslabs.rds_control_plane_mcp_server.common.models import (
    ClusterListModel,
)
from awslabs.rds_control_plane_mcp_server.common.utils import format_cluster_info, handle_aws_error
from loguru import logger


LIST_CLUSTERS_RESOURCE_DESCRIPTION = """List all available Amazon RDS clusters in your account.

<use_case>
Use this resource to discover all available RDS database clusters in your AWS account.
</use_case>

<important_notes>
1. The response provides essential information about each cluster
2. Cluster identifiers returned can be used with the db-cluster/{cluster_id} resource
3. Clusters are filtered to the AWS region specified in your environment configuration
</important_notes>

## Response structure
Returns a JSON document containing:
- `clusters`: Array of DB cluster objects
- `count`: Number of clusters found
- `resource_uri`: Base URI for accessing clusters
"""


class ListClustersHandler:
    """Handler for RDS DB Cluster listing operations in the RDS MCP Server.

    This class provides tools for discovering and retrieving information about
    RDS database clusters in your AWS account.
    """

    def __init__(self, mcp, rds_client):
        """Initialize the RDS Cluster handler.

        Args:
            mcp: The MCP server instance
            rds_client: The AWS RDS client instance
        """
        self.mcp = mcp
        self.rds_client = rds_client

        # Register resources
        self.mcp.resource(
            uri='aws-rds://db-cluster',
            name='ListDBClusters',
            description=LIST_CLUSTERS_RESOURCE_DESCRIPTION,
            mime_type='application/json',
        )(self.get_cluster_list_resource)

    async def get_cluster_list_resource(self) -> str:
        """Get list of all RDS clusters as a resource.

        Retrieves a complete list of all RDS database clusters in the current AWS region,
        including Aurora clusters and Multi-AZ DB clusters, with pagination handling
        for large result sets.

        Returns:
            JSON string with formatted cluster information including identifiers,
            endpoints, engine details, and other relevant metadata
        """
        try:
            logger.info('Getting cluster list resource')

            clusters = []
            response = await asyncio.to_thread(self.rds_client.describe_db_clusters)

            for cluster in response.get('DBClusters', []):
                clusters.append(format_cluster_info(cluster))

            #  pagination if there's a marker for next page
            while 'Marker' in response:
                response = await asyncio.to_thread(
                    self.rds_client.describe_db_clusters, Marker=response['Marker']
                )
                for cluster in response.get('DBClusters', []):
                    clusters.append(format_cluster_info(cluster))

            # Create the model
            result = ClusterListModel(
                clusters=clusters, count=len(clusters), resource_uri=RESOURCE_PREFIX_DB_CLUSTER
            )

            model_dict = result.model_dump()
            return json.dumps(model_dict, indent=2)
        except Exception as e:
            error_result = await handle_aws_error('get_cluster_list_resource', e)
            return json.dumps(error_result, indent=2)
