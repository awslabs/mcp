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

"""Util to format and process information about RDS database instances."""

from typing import Any, Dict


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
