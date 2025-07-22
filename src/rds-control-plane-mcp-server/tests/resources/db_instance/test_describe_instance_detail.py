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

"""Tests for describe_instance_detail resource."""

import pytest
from awslabs.rds_control_plane_mcp_server.resources.db_instance.describe_instance_detail import (
    Instance,
    InstanceEndpoint,
    InstanceStorage,
    describe_instance_detail,
)
from typing import Any


class TestDescribeInstanceDetail:
    """Test describe_instance_detail function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_rds_client):
        """Test successful instance detail retrieval."""
        mock_rds_client.describe_db_instances.return_value = {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'test-instance',
                    'DBInstanceStatus': 'available',
                    'Engine': 'mysql',
                    'EngineVersion': '8.0.23',
                    'DBInstanceClass': 'db.t3.medium',
                    'Endpoint': {
                        'Address': 'test-instance.abc123.us-east-1.rds.amazonaws.com',
                        'Port': 3306,
                        'HostedZoneId': 'Z2R2ITUGPM61AM',
                    },
                    'AvailabilityZone': 'us-east-1a',
                    'MultiAZ': True,
                    'StorageType': 'gp2',
                    'AllocatedStorage': 20,
                    'StorageEncrypted': False,
                    'PreferredBackupWindow': '03:00-04:00',
                    'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
                    'PubliclyAccessible': False,
                    'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-12345', 'Status': 'active'}],
                    'DBClusterIdentifier': 'test-cluster',
                    'DbiResourceId': 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                    'TagList': [{'Key': 'Environment', 'Value': 'Production'}],
                }
            ]
        }

        result = await describe_instance_detail(instance_id='test-instance')

        assert result.instance_id == 'test-instance'
        assert result.status == 'available'
        assert result.engine == 'mysql'
        assert result.engine_version == '8.0.23'
        assert result.instance_class == 'db.t3.medium'
        assert result.endpoint is not None
        assert result.endpoint.address == 'test-instance.abc123.us-east-1.rds.amazonaws.com'
        assert result.endpoint.port == 3306
        assert result.multi_az is True
        assert result.storage is not None
        assert result.storage.type == 'gp2'
        assert result.storage.allocated == 20
        assert result.db_cluster == 'test-cluster'
        assert result.tags['Environment'] == 'Production'
        assert result.resource_uri == 'aws-rds://db-instance/test-instance'

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_parameters(self, mock_rds_client):
        """Test API is called with correct parameters."""
        mock_rds_client.describe_db_instances.return_value = {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'test-instance',
                    'DBInstanceStatus': 'available',
                    'Engine': 'mysql',
                    'DBInstanceClass': 'db.t3.medium',
                    'MultiAZ': False,
                    'PubliclyAccessible': False,
                    'VpcSecurityGroups': [],
                    'TagList': [],
                }
            ]
        }

        await describe_instance_detail(instance_id='test-instance')

        mock_rds_client.describe_db_instances.assert_called_once_with(
            DBInstanceIdentifier='test-instance'
        )


class TestInstance:
    """Test Instance model."""

    def test_from_db_instance_typedef(self):
        """Test model creation from AWS API response."""
        api_response: Any = {
            'DBInstanceIdentifier': 'test-instance',
            'DBInstanceStatus': 'available',
            'Engine': 'mysql',
            'EngineVersion': '8.0.23',
            'DBInstanceClass': 'db.t3.medium',
            'Endpoint': {
                'Address': 'test-instance.abc123.us-east-1.rds.amazonaws.com',
                'Port': 3306,
                'HostedZoneId': 'Z2R2ITUGPM61AM',
            },
            'AvailabilityZone': 'us-east-1a',
            'MultiAZ': True,
            'StorageType': 'gp2',
            'AllocatedStorage': 20,
            'StorageEncrypted': False,
            'PubliclyAccessible': False,
            'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-12345', 'Status': 'active'}],
            'DBClusterIdentifier': 'test-cluster',
            'DbiResourceId': 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'TagList': [{'Key': 'Environment', 'Value': 'Production'}],
        }

        instance = Instance.from_DBInstanceTypeDef(api_response)

        assert instance.instance_id == 'test-instance'
        assert instance.status == 'available'
        assert instance.engine == 'mysql'
        assert instance.endpoint is not None
        assert instance.endpoint.address == 'test-instance.abc123.us-east-1.rds.amazonaws.com'
        assert instance.endpoint.port == 3306
        assert instance.storage is not None
        assert instance.storage.type == 'gp2'
        assert instance.storage.allocated == 20
        assert instance.multi_az is True
        assert instance.db_cluster == 'test-cluster'
        assert instance.tags['Environment'] == 'Production'

    def test_handles_missing_fields(self):
        """Test model handles missing API response fields."""
        api_response: Any = {
            'DBInstanceIdentifier': 'test-instance',
            'DBInstanceStatus': 'available',
            'Engine': 'mysql',
            'DBInstanceClass': 'db.t3.medium',
        }

        instance = Instance.from_DBInstanceTypeDef(api_response)

        assert instance.instance_id == 'test-instance'
        assert instance.engine_version == ''
        assert instance.endpoint is None
        assert instance.availability_zone is None
        assert instance.multi_az is False
        assert instance.storage is not None
        assert instance.storage.type is None
        assert instance.db_cluster is None
        assert instance.tags == {}


class TestInstanceEndpoint:
    """Test InstanceEndpoint model."""

    def test_model_creation(self):
        """Test endpoint model creation."""
        endpoint = InstanceEndpoint(
            address='test-instance.abc123.us-east-1.rds.amazonaws.com',
            port=3306,
            hosted_zone_id='Z2R2ITUGPM61AM',
        )

        assert endpoint.address == 'test-instance.abc123.us-east-1.rds.amazonaws.com'
        assert endpoint.port == 3306
        assert endpoint.hosted_zone_id == 'Z2R2ITUGPM61AM'


class TestInstanceStorage:
    """Test InstanceStorage model."""

    def test_model_creation(self):
        """Test storage model creation."""
        storage = InstanceStorage(type='gp2', allocated=20, encrypted=False)

        assert storage.type == 'gp2'
        assert storage.allocated == 20
        assert storage.encrypted is False
