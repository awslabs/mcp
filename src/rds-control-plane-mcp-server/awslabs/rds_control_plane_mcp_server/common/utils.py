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

"""Utility functions for the RDS Control Plane MCP Server."""

from .constants import ERROR_AWS_API, ERROR_UNEXPECTED
from .models import (
    ClusterMember,
    ClusterModel,
    InstanceEndpoint,
    InstanceModel,
    InstanceStorage,
    VpcSecurityGroup,
)
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.fastmcp import Context
from mypy_boto3_rds.type_defs import DBClusterTypeDef, DBInstanceTypeDef
from typing import Any, Dict, Optional


def format_aws_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Format AWS API response for MCP.

    Args:
        response: Raw AWS API response

    Returns:
        Formatted response dictionary
    """
    # remove ResponseMetadata as it's not useful for LLMs
    if 'ResponseMetadata' in response:
        del response['ResponseMetadata']

    # convert datetime objects to strings
    return convert_datetime_to_string(response)


def convert_datetime_to_string(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings.

    Args:
        obj: Object to convert

    Returns:
        Object with datetime objects converted to strings
    """
    import datetime

    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_datetime_to_string(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_string(item) for item in obj]
    return obj


async def handle_aws_error(
    operation: str, error: Exception, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Handle AWS API errors consistently.

    Args:
        operation: The operation that failed
        error: The exception that was raised
        ctx: MCP context for error reporting

    Returns:
        Error response dictionary
    """
    if isinstance(error, ClientError):
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        logger.error(f'{operation} failed with AWS error {error_code}: {error_message}')

        error_response = {
            'error': ERROR_AWS_API.format(error_code),
            'error_code': error_code,
            'error_message': error_message,
            'operation': operation,
        }

        if ctx:
            await ctx.error(f'{error_code}: {error_message}')

    else:
        logger.exception(f'{operation} failed with unexpected error')
        error_response = {
            'error': ERROR_UNEXPECTED.format(str(error)),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'operation': operation,
        }

        if ctx:
            await ctx.error(str(error))

    return error_response


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


def format_instance_info(instance: DBInstanceTypeDef) -> InstanceModel:
    """Format instance information for better readability.

    Args:
        instance: Raw instance data from AWS

    Returns:
        Formatted instance information as an InstanceModel
    """
    endpoint = InstanceEndpoint(
        address=instance.get('Endpoint', {}).get('Address'),
        port=instance.get('Endpoint', {}).get('Port'),
        hosted_zone_id=instance.get('Endpoint', {}).get('HostedZoneId'),
    )

    storage = InstanceStorage(
        type=instance.get('StorageType'),
        allocated=instance.get('AllocatedStorage'),
        encrypted=instance.get('StorageEncrypted'),
    )

    vpc_security_groups = []
    for sg in instance.get('VpcSecurityGroups', []):
        vpc_security_groups.append(
            VpcSecurityGroup(id=sg.get('VpcSecurityGroupId', ''), status=sg.get('Status', ''))
        )

    tags = {}
    if instance.get('TagList'):
        for tag in instance.get('TagList', []):
            if 'Key' in tag and 'Value' in tag:
                tags[tag['Key']] = tag['Value']

    return InstanceModel(
        instance_id=instance.get('DBInstanceIdentifier', ''),
        status=instance.get('DBInstanceStatus', ''),
        engine=instance.get('Engine', ''),
        engine_version=instance.get('EngineVersion', ''),
        instance_class=instance.get('DBInstanceClass', ''),
        endpoint=endpoint,
        availability_zone=instance.get('AvailabilityZone'),
        multi_az=instance.get('MultiAZ', False),
        storage=storage,
        preferred_backup_window=instance.get('PreferredBackupWindow'),
        preferred_maintenance_window=instance.get('PreferredMaintenanceWindow'),
        publicly_accessible=instance.get('PubliclyAccessible', False),
        vpc_security_groups=vpc_security_groups,
        db_cluster=instance.get('DBClusterIdentifier'),
        tags=tags,
        dbi_resource_id=instance.get('DbiResourceId'),
        resource_uri=None,
    )
