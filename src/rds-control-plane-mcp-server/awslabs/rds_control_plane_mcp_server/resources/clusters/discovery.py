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

"""Resource implementations for RDS Control Plane MCP Server."""

import asyncio
import json
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_CLUSTER
from awslabs.rds_control_plane_mcp_server.common.models import (
    ClusterListModel,
    ClusterMember,
    ClusterModel,
    VpcSecurityGroup,
)
from awslabs.rds_control_plane_mcp_server.common.utils import (
    convert_datetime_to_string,
    handle_aws_error,
)
from loguru import logger
from typing import Any, Dict


def format_cluster_info(cluster: Dict[str, Any]) -> ClusterModel:
    """Format cluster information for better readability.

    Args:
        cluster: Raw cluster data from AWS

    Returns:
        Formatted cluster information as a ClusterModel
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
        cluster_id=cluster.get('DBClusterIdentifier'),
        status=cluster.get('Status'),
        engine=cluster.get('Engine'),
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


async def get_cluster_list_resource(rds_client: Any) -> str:
    """Get list of all RDS clusters as a resource.

    Args:
        rds_client: AWS RDS client

    Returns:
        JSON string with cluster list
    """
    try:
        logger.info('Getting cluster list resource')

        clusters = []
        response = await asyncio.to_thread(rds_client.describe_db_clusters)

        for cluster in response.get('DBClusters', []):
            clusters.append(format_cluster_info(cluster))

        #  pagination if there's a marker for next page
        while 'Marker' in response:
            response = await asyncio.to_thread(
                rds_client.describe_db_clusters, Marker=response['Marker']
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


async def get_cluster_detail_resource(cluster_id: str, rds_client: Any) -> str:
    """Get detailed information about a specific cluster as a resource.

    Args:
        cluster_id: The cluster identifier
        rds_client: AWS RDS client

    Returns:
        JSON string with cluster details
    """
    try:
        logger.info(f'Getting cluster detail resource for {cluster_id}')
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
    except Exception as e:
        error_result = await handle_aws_error(f'get_cluster_detail_resource({cluster_id})', e)
        return json.dumps(error_result, indent=2)
