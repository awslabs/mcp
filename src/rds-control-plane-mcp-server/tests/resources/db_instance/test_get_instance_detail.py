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

"""Tests for get_instance_detail resource."""

import json
import pytest
from unittest.mock import MagicMock, patch

from awslabs.rds_control_plane_mcp_server.resources.db_instance.get_instance_detail import get_instance_detail
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_INSTANCE


@pytest.mark.asyncio
async def test_get_instance_detail_success():
    """Test successful retrieval of instance details."""
    instance_id = 'test-instance-1'

    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_instances.return_value = {
        'DBInstances': [
            {
                'DBInstanceIdentifier': instance_id,
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
            }
        ]
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await get_instance_detail(instance_id)

        mock_rds_client.describe_db_instances.assert_called_once_with(
            DBInstanceIdentifier=instance_id
        )

        result_dict = json.loads(result)

        assert result_dict['instance_id'] == instance_id
        assert result_dict['instance_class'] == 'db.r5.large'
        assert result_dict['engine'] == 'aurora-mysql'
        assert result_dict['engine_version'] == '5.7.12'
        assert result_dict['status'] == 'available'
        assert result_dict['resource_uri'] == f'{RESOURCE_PREFIX_DB_INSTANCE}/{instance_id}'

        assert 'endpoint' in result_dict
        assert result_dict['endpoint']['address'] == 'test-instance-1.abc123.us-east-1.rds.amazonaws.com'
        assert result_dict['endpoint']['port'] == 3306

        assert len(result_dict['vpc_security_groups']) == 1
        assert result_dict['vpc_security_groups'][0]['id'] == 'sg-12345'
        assert result_dict['vpc_security_groups'][0]['status'] == 'active'

        assert result_dict['storage']['type'] == 'aurora'
        assert result_dict['storage']['encrypted'] is True

        assert 'Environment' in result_dict['tags']
        assert result_dict['tags']['Environment'] == 'Production'


@pytest.mark.asyncio
async def test_get_instance_detail_not_found():
    """Test get_instance_detail when instance is not found."""
    instance_id = 'non-existent-instance'

    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_instances.return_value = {
        'DBInstances': []
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await get_instance_detail(instance_id)

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert f'Instance {instance_id} not found' == result_dict['error']


@pytest.mark.asyncio
async def test_get_instance_detail_client_error():
    """Test get_instance_detail when RDS client raises an error."""
    from botocore.exceptions import ClientError

    instance_id = 'test-error'

    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_instances.side_effect = ClientError(
        {
            'Error': {
                'Code': 'DBInstanceNotFound',
                'Message': f'DBInstance {instance_id} not found'
            }
        },
        'DescribeDBInstances'
    )

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await get_instance_detail(instance_id)

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert 'error_code' in result_dict
        assert result_dict['error_code'] == 'DBInstanceNotFound'
        assert f'DBInstance {instance_id} not found' in result_dict['error_message']
