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
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from ...common.utils import convert_datetime_to_string
from mypy_boto3_rds.type_defs import DBClusterTypeDef


class ClusterSummaryModel(BaseModel):
    """Simplified DB cluster model for list views."""

    cluster_id: str = Field(description='The DB cluster identifier')
    db_cluster_arn: Optional[str] = Field(None, description='The ARN of the DB cluster')
    db_cluster_resource_id: Optional[str] = Field(None, description='The resource ID of the DB cluster')
    status: str = Field(description='The current status of the DB cluster')
    engine: str = Field(description='The database engine')
    engine_version: Optional[str] = Field(None, description='The version of the database engine')
    availability_zones: List[str] = Field(default_factory=list, description='The AZs where the cluster instances can be created')
    multi_az: bool = Field(
        description='Whether the DB cluster has instances in multiple Availability Zones'
    )
    tag_list: Dict[str, str] = Field(default_factory=dict, description='A list of tags')
    resource_uri: Optional[str] = Field(None, description='The resource URI for this cluster')


def format_cluster_summary(cluster: DBClusterTypeDef) -> ClusterSummaryModel:
    """Format cluster information into a simplified summary model for list views.

    Args:
        cluster: Raw cluster data from AWS API response

    Returns:
        Formatted cluster summary information as a ClusterSummaryModel object
    """
    tags = {}
    if cluster.get('TagList'):
        for tag in cluster.get('TagList', []):
            if 'Key' in tag and 'Value' in tag:
                tags[tag['Key']] = tag['Value']

    return ClusterSummaryModel(
        cluster_id=cluster.get('DBClusterIdentifier', ''),
        db_cluster_arn=cluster.get('DBClusterArn'),
        db_cluster_resource_id=cluster.get('DbClusterResourceId'),
        status=cluster.get('Status', ''),
        engine=cluster.get('Engine', ''),
        engine_version=cluster.get('EngineVersion'),
        availability_zones=cluster.get('AvailabilityZones', []),
        multi_az=cluster.get('MultiAZ', False),
        tag_list=tags,
        resource_uri=None,
    )


def format_cluster_detail(cluster: DBClusterTypeDef) -> ClusterModel:
    """Format cluster information from AWS API response into a detailed structured model.

    This method transforms the raw AWS API response data into a standardized
    ClusterModel object, extracting and organizing key cluster attributes
    including members, security groups, and tags.

    Args:
        cluster: Raw cluster data from AWS API response

    Returns:
        Formatted cluster information as a ClusterModel object with comprehensive details
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
