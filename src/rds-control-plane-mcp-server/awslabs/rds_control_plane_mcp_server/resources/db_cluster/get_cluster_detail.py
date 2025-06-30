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

"""Resource for retrieving detailed information about RDS DB Clusters."""

import asyncio
import json
from ...common.connection import RDSConnectionManager
from ...common.constants import RESOURCE_PREFIX_DB_CLUSTER
from ...common.decorator import handle_exceptions
from ...common.server import mcp
from .utils import format_cluster_info
from loguru import logger
from pydantic import Field


GET_CLUSTER_DETAIL_RESOURCE_DESCRIPTION = """Get detailed information about a specific Amazon RDS cluster.

<use_case>
Use this resource to retrieve comprehensive details about a specific RDS database cluster
identified by its cluster ID. This is particularly useful for monitoring the status,
configuration, and connectivity options of an individual cluster.
</use_case>

<important_notes>
1. The cluster ID must exist in your AWS account and region
2. The response contains full configuration details about the specified cluster
3. Error responses will be returned if the cluster doesn't exist or you lack permissions
4. The information returned includes backup and maintenance windows useful for operational planning
5. Security group information can be used to verify network configurations
</important_notes>

## Response structure
Returns a JSON document containing detailed cluster information including:
- Status, engine type, and version
- Writer and reader endpoints for connection
- Multi-AZ deployment status
- Backup configuration and retention periods
- Maintenance windows
- Creation timestamp
- Member instances with their roles (writer/reader)
- Security groups configuration
- Associated tags
"""


@mcp.resource(
    uri='aws-rds://db-cluster/{cluster_id}',
    name='GetDBClusterDetail',
    description=GET_CLUSTER_DETAIL_RESOURCE_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def get_cluster_detail(
    cluster_id: str = Field(
        ..., description='The unique identifier of the RDS DB cluster to retrieve details for'
    ),
) -> str:
    """Retrieve detailed information about a specific RDS cluster.

    This method queries the AWS RDS API for comprehensive information about
    a specific DB cluster identified by its unique cluster ID. It handles
    AWS API interactions, error conditions, and formats the response data
    into a consistent JSON structure.

    Args:
        cluster_id: The unique identifier of the DB cluster to retrieve

    Returns:
        JSON string containing detailed cluster information including configuration,
        status, endpoints, backup settings, member instances, and security groups.
        Returns error information if the cluster doesn't exist or cannot be accessed.
    """
    logger.info(f'Getting cluster detail resource for {cluster_id}')
    rds_client = RDSConnectionManager.get_connection()
    response = await asyncio.to_thread(
        rds_client.describe_db_clusters, DBClusterIdentifier=cluster_id
    )

    clusters = response.get('DBClusters', [])
    if not clusters:
        return json.dumps({'error': f'Cluster {cluster_id} not found'}, indent=2)

    cluster = format_cluster_info(clusters[0])
    cluster.resource_uri = f'{RESOURCE_PREFIX_DB_CLUSTER}/{cluster_id}'

    model_dict = cluster.model_dump()

    return json.dumps(model_dict, indent=2)
