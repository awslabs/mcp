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

"""General utility functions for the RDS Control Plane MCP Server."""

from ..constants import MCP_SERVER_VERSION
from ..context import RDSContext
from botocore.client import BaseClient
from typing import Any, Callable, Dict, List, TypeVar


T = TypeVar('T', bound=object)


def handle_paginated_aws_api_call(
    client: BaseClient,
    paginator_name: str,
    operation_parameters: Dict[str, Any],
    format_function: Callable[[Any], T],
    result_key: str,
) -> List[T]:
    """Fetch all results using AWS API pagination.

    Args:
        client: Boto3 client to use for the API call
        paginator_name: Name of the paginator to use (e.g. 'describe_db_clusters')
        operation_parameters: Parameters to pass to the paginator
        format_function: Function to format each item in the result
        result_key: Key in the response that contains the list of items

    Returns:
        List of formatted results
    """
    results = []
    paginator = client.get_paginator(paginator_name)
    operation_parameters['PaginationConfig'] = RDSContext.get_pagination_config()
    page_iterator = paginator.paginate(**operation_parameters)
    for page in page_iterator:
        for item in page.get(result_key, []):
            results.append(format_function(item))

    return results


def format_rds_api_response(response: Dict[str, Any]) -> Dict[str, Any]:
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


def add_mcp_tags(params: Dict[str, Any]) -> Dict[str, Any]:
    """Add MCP server version tag to resource creation parameters.

    Args:
        params: Parameters for resource creation

    Returns:
        Parameters with MCP tags added
    """
    tags = params.get('Tags', [])
    tags.append({'Key': 'mcp_server_version', 'Value': MCP_SERVER_VERSION})
    tags.append({'Key': 'created_by', 'Value': 'rds-control-plane-mcp-server'})
    params['Tags'] = tags
    return params


def format_cluster_info(cluster: Dict[str, Any]) -> Dict[str, Any]:
    """Format cluster information for better readability.

    Args:
        cluster: Raw cluster data from AWS

    Returns:
        Formatted cluster information
    """
    return {
        'cluster_id': cluster.get('DBClusterIdentifier'),
        'status': cluster.get('Status'),
        'engine': cluster.get('Engine'),
        'engine_version': cluster.get('EngineVersion'),
        'endpoint': cluster.get('Endpoint'),
        'reader_endpoint': cluster.get('ReaderEndpoint'),
        'multi_az': cluster.get('MultiAZ'),
        'backup_retention': cluster.get('BackupRetentionPeriod'),
        'preferred_backup_window': cluster.get('PreferredBackupWindow'),
        'preferred_maintenance_window': cluster.get('PreferredMaintenanceWindow'),
        'created_time': convert_datetime_to_string(cluster.get('ClusterCreateTime')),
        'members': [
            {
                'instance_id': member.get('DBInstanceIdentifier'),
                'is_writer': member.get('IsClusterWriter'),
                'status': member.get('DBClusterParameterGroupStatus'),
            }
            for member in cluster.get('DBClusterMembers', [])
        ],
        'vpc_security_groups': [
            {'id': sg.get('VpcSecurityGroupId'), 'status': sg.get('Status')}
            for sg in cluster.get('VpcSecurityGroups', [])
        ],
        'tags': {tag['Key']: tag['Value'] for tag in cluster.get('TagList', [])}
        if cluster.get('TagList')
        else {},
    }


def format_instance_info(instance: Dict[str, Any]) -> Dict[str, Any]:
    """Format instance information for better readability.

    Args:
        instance: Raw instance data from AWS

    Returns:
        Formatted instance information
    """
    # Handle potentially nested endpoint structure
    endpoint = {}
    if instance.get('Endpoint'):
        if isinstance(instance['Endpoint'], dict):
            endpoint = {
                'address': instance['Endpoint'].get('Address'),
                'port': instance['Endpoint'].get('Port'),
                'hosted_zone_id': instance['Endpoint'].get('HostedZoneId'),
            }
        else:
            endpoint = {'address': instance.get('Endpoint')}

    return {
        'instance_id': instance.get('DBInstanceIdentifier'),
        'status': instance.get('DBInstanceStatus'),
        'engine': instance.get('Engine'),
        'engine_version': instance.get('EngineVersion'),
        'instance_class': instance.get('DBInstanceClass'),
        'endpoint': endpoint,
        'availability_zone': instance.get('AvailabilityZone'),
        'multi_az': instance.get('MultiAZ', False),
        'storage': {
            'type': instance.get('StorageType'),
            'allocated': instance.get('AllocatedStorage'),
            'encrypted': instance.get('StorageEncrypted'),
        },
        'publicly_accessible': instance.get('PubliclyAccessible', False),
        'vpc_security_groups': [
            {'id': sg.get('VpcSecurityGroupId'), 'status': sg.get('Status')}
            for sg in instance.get('VpcSecurityGroups', [])
        ],
        'db_cluster': instance.get('DBClusterIdentifier'),
        'preferred_backup_window': instance.get('PreferredBackupWindow'),
        'preferred_maintenance_window': instance.get('PreferredMaintenanceWindow'),
        'tags': {tag['Key']: tag['Value'] for tag in instance.get('TagList', [])}
        if instance.get('TagList')
        else {},
        'resource_id': instance.get('DbiResourceId'),
    }
