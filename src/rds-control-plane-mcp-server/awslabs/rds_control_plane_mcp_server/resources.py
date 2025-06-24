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
from typing import Any, Dict
from loguru import logger

from .constants import (
    ERROR_AWS_API,
    ERROR_UNEXPECTED,
    RESOURCE_PREFIX_DB_CLUSTER,
    RESOURCE_PREFIX_DB_INSTANCE,
)


async def handle_aws_error(operation: str, error: Exception) -> Dict[str, Any]:
    """Handle AWS API errors consistently.
    
    Args:
        operation: The operation that failed
        error: The exception that was raised
        
    Returns:
        Error response dictionary
    """
    from botocore.exceptions import ClientError
    
    if isinstance(error, ClientError):
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        logger.error(f'{operation} failed with AWS error {error_code}: {error_message}')
        
        return {
            'error': ERROR_AWS_API.format(error_code),
            'error_code': error_code,
            'error_message': error_message,
            'operation': operation
        }
    else:
        logger.exception(f'{operation} failed with unexpected error')
        return {
            'error': ERROR_UNEXPECTED.format(str(error)),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'operation': operation
        }


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
                'status': member.get('DBClusterParameterGroupStatus')
            }
            for member in cluster.get('DBClusterMembers', [])
        ],
        'vpc_security_groups': [
            {
                'id': sg.get('VpcSecurityGroupId'),
                'status': sg.get('Status')
            }
            for sg in cluster.get('VpcSecurityGroups', [])
        ],
        'tags': {tag['Key']: tag['Value'] for tag in cluster.get('TagList', [])}
    }


def format_instance_info(instance: Dict[str, Any]) -> Dict[str, Any]:
    """Format instance information for better readability.
    
    Args:
        instance: Raw instance data from AWS
        
    Returns:
        Formatted instance information
    """
    return {
        'instance_id': instance.get('DBInstanceIdentifier'),
        'status': instance.get('DBInstanceStatus'),
        'engine': instance.get('Engine'),
        'engine_version': instance.get('EngineVersion'),
        'instance_class': instance.get('DBInstanceClass'),
        'endpoint': {
            'address': instance.get('Endpoint', {}).get('Address'),
            'port': instance.get('Endpoint', {}).get('Port'),
            'hosted_zone_id': instance.get('Endpoint', {}).get('HostedZoneId')
        },
        'availability_zone': instance.get('AvailabilityZone'),
        'multi_az': instance.get('MultiAZ'),
        'storage': {
            'type': instance.get('StorageType'),
            'allocated': instance.get('AllocatedStorage'),
            'encrypted': instance.get('StorageEncrypted')
        },
        'preferred_backup_window': instance.get('PreferredBackupWindow'),
        'preferred_maintenance_window': instance.get('PreferredMaintenanceWindow'),
        'publicly_accessible': instance.get('PubliclyAccessible'),
        'vpc_security_groups': [
            {
                'id': sg.get('VpcSecurityGroupId'),
                'status': sg.get('Status')
            }
            for sg in instance.get('VpcSecurityGroups', [])
        ],
        'db_cluster': instance.get('DBClusterIdentifier'),
        'tags': {tag['Key']: tag['Value'] for tag in instance.get('TagList', [])},
        'dbi_resource_id': instance.get('DbiResourceId')
    }


async def get_cluster_list_resource(rds_client: Any) -> str:
    """Get list of all RDS clusters as a resource.
    
    Args:
        rds_client: AWS RDS client
        
    Returns:
        JSON string with cluster list
    """
    try:
        logger.info("Getting cluster list resource")
        
        clusters = []
        response = await asyncio.to_thread(rds_client.describe_db_clusters)
        
        for cluster in response.get('DBClusters', []):
            clusters.append(format_cluster_info(cluster))
        
        #  pagination if there's a marker for next page
        while 'Marker' in response:
            response = await asyncio.to_thread(
                rds_client.describe_db_clusters,
                Marker=response['Marker']
            )
            for cluster in response.get('DBClusters', []):
                clusters.append(format_cluster_info(cluster))
        
        result = {
            'clusters': clusters,
            'count': len(clusters),
            'resource_uri': RESOURCE_PREFIX_DB_CLUSTER,
        }
        
        return json.dumps(result, indent=2)
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
        logger.info(f"Getting cluster detail resource for {cluster_id}")
        response = await asyncio.to_thread(
            rds_client.describe_db_clusters,
            DBClusterIdentifier=cluster_id
        )
        
        clusters = response.get('DBClusters', [])
        if not clusters:
            return json.dumps({'error': f'Cluster {cluster_id} not found'}, indent=2)
        
        cluster = format_cluster_info(clusters[0])
        cluster['resource_uri'] = f'{RESOURCE_PREFIX_DB_CLUSTER}/{cluster_id}'
        
        return json.dumps(cluster, indent=2)
    except Exception as e:
        error_result = await handle_aws_error(f'get_cluster_detail_resource({cluster_id})', e)
        return json.dumps(error_result, indent=2)


async def get_instance_list_resource(rds_client: Any) -> str:
    """Get list of all RDS instances as a resource.
    
    Args:
        rds_client: AWS RDS client
        
    Returns:
        JSON string with instance list
    """
    try:
        logger.info("Getting instance list resource")
        
        instances = []
        response = await asyncio.to_thread(rds_client.describe_db_instances)
        
        for instance in response.get('DBInstances', []):
            instances.append(format_instance_info(instance))
        
        # pagination if there's a marker for next page
        while 'Marker' in response:
            response = await asyncio.to_thread(
                rds_client.describe_db_instances,
                Marker=response['Marker']
            )
            for instance in response.get('DBInstances', []):
                instances.append(format_instance_info(instance))
        
        result = {
            'instances': instances,
            'count': len(instances),
            'resource_uri': RESOURCE_PREFIX_DB_INSTANCE,
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        error_result = await handle_aws_error('get_instance_list_resource', e)
        return json.dumps(error_result, indent=2)


async def get_instance_detail_resource(instance_id: str, rds_client: Any) -> str:
    """Get detailed information about a specific instance as a resource.
    
    Args:
        instance_id: The instance identifier
        rds_client: AWS RDS client
        
    Returns:
        JSON string with instance details
    """
    try:
        logger.info(f"Getting instance detail resource for {instance_id}")
        response = await asyncio.to_thread(
            rds_client.describe_db_instances,
            DBInstanceIdentifier=instance_id
        )
        
        instances = response.get('DBInstances', [])
        if not instances:
            return json.dumps({'error': f'Instance {instance_id} not found'}, indent=2)
        
        instance = format_instance_info(instances[0])
        instance['resource_uri'] = f'{RESOURCE_PREFIX_DB_INSTANCE}/{instance_id}'
        
        return json.dumps(instance, indent=2)
    except Exception as e:
        error_result = await handle_aws_error(f'get_instance_detail_resource({instance_id})', e)
        return json.dumps(error_result, indent=2)
