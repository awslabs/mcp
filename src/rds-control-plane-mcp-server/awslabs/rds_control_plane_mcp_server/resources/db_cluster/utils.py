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

"""Cluster specific utility functions for the RDS Control Plane MCP Server."""

from ...common.models import (
    ClusterMember,
    ClusterModel,
    VpcSecurityGroup,
)
from ...common.utils import convert_datetime_to_string
from mypy_boto3_rds.type_defs import DBClusterTypeDef


def format_cluster_info(cluster: DBClusterTypeDef) -> ClusterModel:
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
                instance_id=member.get('DBInstanceIdentifier', ''),
                is_writer=member.get('IsClusterWriter', False),
                status=member.get('DBClusterParameterGroupStatus'),
            )
        )

    vpc_security_groups = []
    for sg in cluster.get('VpcSecurityGroups', []):
        vpc_security_groups.append(
            VpcSecurityGroup(id=sg.get('VpcSecurityGroupId', ''), status=sg.get('Status', ''))
        )

    tags = {}
    if cluster.get('TagList'):
        for tag in cluster.get('TagList', []):
            if 'Key' in tag and 'Value' in tag:
                tags[tag['Key']] = tag['Value']

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
