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

"""Resource for listing availble RDS DB Clusters."""

from ...common.connection import RDSConnectionManager
from ...common.decorator import handle_exceptions
from ...common.models import ClusterModel
from ...common.server import mcp
from ...common.utils import paginate_aws_api_call
from .utils import format_cluster_info
from loguru import logger
from pydantic import BaseModel, Field
from typing import List


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


class ClusterListModel(BaseModel):
    """DB cluster list model."""

    clusters: List[ClusterModel] = Field(default_factory=list, description='List of DB clusters')
    count: int = Field(description='Total number of DB clusters')
    resource_uri: str = Field(description='The resource URI for the DB clusters')


@mcp.resource(
    uri='aws-rds://db-cluster',
    name='ListDBClusters',
    description=LIST_CLUSTERS_RESOURCE_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def list_clusters() -> ClusterListModel:
    """List all RDS clusters.

    Retrieves a complete list of all RDS database clusters in the current AWS region,
    including Aurora clusters and Multi-AZ DB clusters, with pagination handling
    for large result sets.

    Returns:
        JSON string with formatted cluster information including identifiers,
        endpoints, engine details, and other relevant metadata
    """
    logger.info('Listing RDS clusters')
    rds_client = RDSConnectionManager.get_connection()

    clusters = await paginate_aws_api_call(
        client_function=rds_client.describe_db_clusters,
        format_function=format_cluster_info,
        result_key='DBClusters',
    )

    result = ClusterListModel(
        clusters=clusters, count=len(clusters), resource_uri='aws-rds://db-cluster'
    )

    return result
