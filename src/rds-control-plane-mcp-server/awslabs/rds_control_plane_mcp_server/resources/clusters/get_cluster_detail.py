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

"""Handler for retrieving detailed information about RDS DB Clusters."""

import asyncio
import json
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_CLUSTER
from awslabs.rds_control_plane_mcp_server.common.models import (
    ClusterMember,
    ClusterModel,
    VpcSecurityGroup,
)
from awslabs.rds_control_plane_mcp_server.common.utils import (
    convert_datetime_to_string,
    handle_aws_error,
)
from loguru import logger
from pydantic import Field
from typing import Any, Dict


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


class GetClusterDetailHandler:
    """Handler for RDS DB Cluster detail operations in the RDS MCP Server.

    This class provides functionality for retrieving comprehensive information
    about specific RDS database clusters in your AWS account, including their
    configuration, status, endpoints, and associated resources.
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
            uri='aws-rds://db-cluster/{cluster_id}',
            name='GetDBClusterDetail',
            description=GET_CLUSTER_DETAIL_RESOURCE_DESCRIPTION,
            mime_type='application/json',
        )(self.get_cluster_detail_resource)

    def format_cluster_info(self, cluster: Dict[str, Any]) -> ClusterModel:
        """Format cluster information from AWS API response into a structured model.

        This method transforms the raw AWS API response data into a standardized
        ClusterModel object, extracting and organizing key cluster attributes
        including members, security groups, and tags.

        Args:
            cluster: Raw cluster data from AWS API response

        Returns:
            Formatted cluster information as a ClusterModel object
        """
        members = []
        for member in cluster.get('DBClusterMembers', []):
            members.append(
                ClusterMember(
                    instance_id=member.get('DBInstanceIdentifier'),
                    is_writer=member.get('IsClusterWriter'),
                    status=member.get('DBClusterParameterGroupStatus'),
                )
            )

        vpc_security_groups = []
        for sg in cluster.get('VpcSecurityGroups', []):
            vpc_security_groups.append(
                VpcSecurityGroup(id=sg.get('VpcSecurityGroupId'), status=sg.get('Status'))
            )

        tags = (
            {tag['Key']: tag['Value'] for tag in cluster.get('TagList', [])}
            if cluster.get('TagList')
            else {}
        )

        return ClusterModel(
            cluster_id=cluster.get('DBClusterIdentifier', ''),
            status=cluster.get('Status', ''),
            engine=cluster.get('Engine', ''),
            engine_version=cluster.get('EngineVersion'),
            endpoint=cluster.get('Endpoint'),
            reader_endpoint=cluster.get('ReaderEndpoint'),
            multi_az=cluster.get('MultiAZ', False),
            backup_retention=cluster.get('BackupRetentionPeriod', 0),
            preferred_backup_window=cluster.get('PreferredBackupWindow'),
            preferred_maintenance_window=cluster.get('PreferredMaintenanceWindow'),
            created_time=convert_datetime_to_string(cluster.get('ClusterCreateTime')),
            members=members,
            vpc_security_groups=vpc_security_groups,
            tags=tags,
            resource_uri=None,
        )

    async def get_cluster_detail_resource(
        self,
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
        try:
            logger.info(f'Getting cluster detail resource for {cluster_id}')
            response = await asyncio.to_thread(
                self.rds_client.describe_db_clusters, DBClusterIdentifier=cluster_id
            )

            clusters = response.get('DBClusters', [])
            if not clusters:
                return json.dumps({'error': f'Cluster {cluster_id} not found'}, indent=2)

            cluster = self.format_cluster_info(clusters[0])
            cluster.resource_uri = f'{RESOURCE_PREFIX_DB_CLUSTER}/{cluster_id}'

            model_dict = cluster.model_dump()

            return json.dumps(model_dict, indent=2)
        except Exception as e:
            error_result = await handle_aws_error(f'get_cluster_detail_resource({cluster_id})', e)
            return json.dumps(error_result, indent=2)
