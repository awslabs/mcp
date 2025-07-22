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

"""Resource for listing available RDS DB Clusters."""

from ...common.connection import RDSConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from ...common.utils import handle_paginated_aws_api_call
from loguru import logger
from mypy_boto3_rds.type_defs import DBClusterTypeDef
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class ClusterSummary(BaseModel):
    """Simplified DB cluster model for list views."""

    cluster_id: str = Field(description='The DB cluster identifier')
    db_cluster_arn: Optional[str] = Field(None, description='The ARN of the DB cluster')
    db_cluster_resource_id: Optional[str] = Field(
        None, description='The resource ID of the DB cluster'
    )
    status: str = Field(description='The current status of the DB cluster')
    engine: str = Field(description='The database engine')
    engine_version: Optional[str] = Field(None, description='The version of the database engine')
    availability_zones: List[str] = Field(
        default_factory=list, description='The AZs where the cluster instances can be created'
    )
    multi_az: bool = Field(
        description='Whether the DB cluster has instances in multiple Availability Zones'
    )
    tag_list: Dict[str, str] = Field(default_factory=dict, description='A dictionary of tags')

    @classmethod
    def from_DBClusterTypeDef(cls, cluster: DBClusterTypeDef) -> 'ClusterSummary':
        """Format cluster information into a simplified summary model for list views.

        Args:
            cluster: Raw cluster data from AWS API response containing cluster details and configuration

        Returns:
            ClusterSummary: Formatted cluster summary information containing essential cluster details
        """
        tags = {}
        if cluster.get('TagList'):
            for tag in cluster.get('TagList', []):
                if 'Key' in tag and 'Value' in tag:
                    tags[tag['Key']] = tag['Value']

        return cls(
            cluster_id=cluster.get('DBClusterIdentifier', ''),
            db_cluster_arn=cluster.get('DBClusterArn'),
            db_cluster_resource_id=cluster.get('DbClusterResourceId'),
            status=cluster.get('Status', ''),
            engine=cluster.get('Engine', ''),
            engine_version=cluster.get('EngineVersion'),
            availability_zones=cluster.get('AvailabilityZones', []),
            multi_az=cluster.get('MultiAZ', False),
            tag_list=tags,
        )


class ClusterSummaryList(BaseModel):
    """DB cluster list model containing cluster summaries and metadata."""

    clusters: List[ClusterSummary] = Field(description='List of DB clusters')
    count: int = Field(description='Number of DB clusters')
    resource_uri: str = Field(description='The resource URI for clusters')


LIST_CLUSTERS_RESOURCE_DESCRIPTION = """List all available Amazon RDS clusters in your account.

This resource returns information about all RDS database clusters in your AWS account, including both Aurora clusters and Multi-AZ DB clusters.
"""


@mcp.resource(
    uri='aws-rds://db-cluster',
    name='ListDBClusters',
    description=LIST_CLUSTERS_RESOURCE_DESCRIPTION,
    mime_type='application/json',
)
@handle_exceptions
async def list_clusters() -> ClusterSummaryList:
    """List all RDS clusters in the current AWS region.

    Retrieves a complete list of all RDS database clusters in the current AWS region,
    including Aurora clusters and Multi-AZ DB clusters. The function handles pagination
    automatically for large result sets and formats the cluster information into a
    simplified summary model.

    Returns:
        ClusterSummaryList: Object containing list of formatted cluster summaries,
        total count, and resource URI
    """
    logger.info('Listing RDS clusters')
    rds_client = RDSConnectionManager.get_connection()

    clusters = handle_paginated_aws_api_call(
        client=rds_client,
        paginator_name='describe_db_clusters',
        operation_parameters={},
        format_function=ClusterSummary.from_DBClusterTypeDef,
        result_key='DBClusters',
    )

    result = ClusterSummaryList(
        clusters=clusters, count=len(clusters), resource_uri='aws-rds://db-cluster'
    )

    return result
