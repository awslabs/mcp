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

"""Util to format and process information about RDS database clusters."""

from ...common.utils import convert_datetime_to_string
from typing import Any, Dict


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
