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

"""Tests for list_instances resource."""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from awslabs.rds_control_plane_mcp_server.resources.db_instance.list_instances import list_instances
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_INSTANCE


@pytest.mark.asyncio
async def test_list_instances_success():
    """Test successful retrieval of instance list."""
    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_instances.return_value = {
        'DBInstances': [
            {
                'DBInstanceIdentifier': 'test-instance-1',
                'DBInstanceClass': 'db.r5.large',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.12',
                'DBInstanceStatus': 'available',
                'MasterUsername': 'admin',
                'Endpoint': {
                    'Address': 'test-instance-1.abc123.us-east-1.rds.amazonaws.com',
                    'Port': 3306,
                    'HostedZoneId': 'Z2R2ITUGPM61AM'
                },
                'InstanceCreateTime': '2023-01-01T00:00:00Z',
                'PreferredBackupWindow': '03:00-04:00',
                'BackupRetentionPeriod': 7,
                'DBSecurityGroups': [],
                'VpcSecurityGroups': [
                    {
                        'VpcSecurityGroupId': 'sg-12345',
                        'Status': 'active'
                    }
                ],
                'DBParameterGroups': [
                    {
                        'DBParameterGroupName': 'default.aurora-mysql5.7',
                        'ParameterApplyStatus': 'in-sync'
                    }
                ],
                'AvailabilityZone': 'us-east-1a',
                'DBSubnetGroup': {
                    'DBSubnetGroupName': 'default',
                    'DBSubnetGroupDescription': 'default',
                    'VpcId': 'vpc-12345',
                    'SubnetGroupStatus': 'Complete',
                    'Subnets': [
                        {
                            'SubnetIdentifier': 'subnet-12345',
                            'SubnetAvailabilityZone': {'Name': 'us-east-1a'},
                            'SubnetStatus': 'Active'
                        }
                    ]
                },
                'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
                'PendingModifiedValues': {},
                'MultiAZ': False,
                'PubliclyAccessible': False,
                'StorageType': 'aurora',
                'StorageEncrypted': True,
                'DbiResourceId': 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                'TagList': [
                    {
                        'Key': 'Environment',
                        'Value': 'Production'
                    }
                ]
            },
            {
                'DBInstanceIdentifier': 'test-instance-2',
                'DBInstanceClass': 'db.t3.medium',
                'Engine': 'mysql',
                'EngineVersion': '8.0.23',
                'DBInstanceStatus': 'available',
                'Endpoint': {
                    'Address': 'test-instance-2.def456.us-east-1.rds.amazonaws.com',
                    'Port': 3306,
                    'HostedZoneId': 'Z2R2ITUGPM61AM'
                },
                'AvailabilityZone': 'us-east-1b',
                'MultiAZ': False,
                'PubliclyAccessible': False,
                'StorageType': 'gp2',
                'AllocatedStorage': 20,
                'StorageEncrypted': False,
                'VpcSecurityGroups': [],
                'TagList': []
            }
        ]
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await list_instances()

        result_dict = json.loads(result)

        assert 'instances' in result_dict
        assert 'count' in result_dict
        assert 'resource_uri' in result_dict

        assert result_dict['count'] == 2
        assert len(result_dict['instances']) == 2
        assert result_dict['resource_uri'] == RESOURCE_PREFIX_DB_INSTANCE

        instance1 = result_dict['instances'][0]
        assert instance1['instance_id'] == 'test-instance-1'
        assert instance1['instance_class'] == 'db.r5.large'
        assert instance1['engine'] == 'aurora-mysql'
        assert instance1['engine_version'] == '5.7.12'
        assert instance1['status'] == 'available'
        assert instance1['endpoint']['address'] == 'test-instance-1.abc123.us-east-1.rds.amazonaws.com'
        assert instance1['endpoint']['port'] == 3306
        assert instance1['availability_zone'] == 'us-east-1a'
        assert instance1['multi_az'] is False
        assert instance1['storage']['type'] == 'aurora'
        assert instance1['storage']['encrypted'] is True
        assert len(instance1['vpc_security_groups']) == 1
        assert instance1['vpc_security_groups'][0]['id'] == 'sg-12345'
        assert 'Environment' in instance1['tags']
        assert instance1['tags']['Environment'] == 'Production'

        instance2 = result_dict['instances'][1]
        assert instance2['instance_id'] == 'test-instance-2'
        assert instance2['instance_class'] == 'db.t3.medium'
        assert instance2['engine'] == 'mysql'
        assert instance2['engine_version'] == '8.0.23'
        assert instance2['availability_zone'] == 'us-east-1b'
        assert instance2['storage']['type'] == 'gp2'
        assert instance2['storage']['allocated'] == 20
        assert instance2['storage']['encrypted'] is False
        assert len(instance2['vpc_security_groups']) == 0
        assert len(instance2['tags']) == 0


@pytest.mark.asyncio
async def test_list_instances_empty():
    """Test list_instances when no instances exist."""
    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_instances.return_value = {
        'DBInstances': []
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await list_instances()

        result_dict = json.loads(result)
        assert result_dict['instances'] == []
        assert result_dict['count'] == 0
        assert result_dict['resource_uri'] == RESOURCE_PREFIX_DB_INSTANCE


@pytest.mark.asyncio
async def test_list_instances_with_pagination():
    """Test list_instances with pagination."""
    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_instances.side_effect = [
        {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'test-instance-1',
                    'DBInstanceClass': 'db.r5.large',
                    'Engine': 'aurora-mysql',
                    'DBInstanceStatus': 'available',
                    'VpcSecurityGroups': [],
                    'TagList': []
                }
            ],
            'Marker': 'next-page'
        },
        {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'test-instance-2',
                    'DBInstanceClass': 'db.t3.medium',
                    'Engine': 'mysql',
                    'DBInstanceStatus': 'available',
                    'VpcSecurityGroups': [],
                    'TagList': []
                }
            ]
        }
    ]

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await list_instances()

        assert mock_rds_client.describe_db_instances.call_count == 2

        result_dict = json.loads(result)
        assert result_dict['count'] == 2
        assert len(result_dict['instances']) == 2

        instance_ids = [i['instance_id'] for i in result_dict['instances']]
        assert 'test-instance-1' in instance_ids
        assert 'test-instance-2' in instance_ids


@pytest.mark.asyncio
async def test_list_instances_client_error():
    """Test list_instances when RDS client raises an error."""
    from botocore.exceptions import ClientError

    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_instances.side_effect = ClientError(
        {
            'Error': {
                'Code': 'InvalidParameterCombination',
                'Message': 'Invalid parameter combination'
            }
        },
        'DescribeDBInstances'
    )

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await list_instances()

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert 'error_code' in result_dict
        assert result_dict['error_code'] == 'InvalidParameterCombination'
        assert 'Invalid parameter combination' in result_dict['error_message']
