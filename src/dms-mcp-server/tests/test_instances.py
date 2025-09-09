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

"""Tests for replication instance operations."""

import pytest
from awslabs.dms_mcp_server.context import Context
from awslabs.dms_mcp_server.models import (
    CreateReplicationInstanceResponse,
    ReplicationInstanceListResponse,
)
from awslabs.dms_mcp_server.tools.instances import (
    create_replication_instance,
    describe_replication_instances,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


@pytest.fixture
def mock_dms_client():
    """Mock DMS client for testing."""
    with patch('awslabs.dms_mcp_server.tools.instances.get_dms_client') as mock_get_client:
        mock_dms = Mock()
        mock_get_client.return_value = mock_dms

        # Mock describe_replication_instances response
        mock_dms.describe_replication_instances.return_value = {
            'ReplicationInstances': [
                {
                    'ReplicationInstanceIdentifier': 'test-instance',
                    'ReplicationInstanceClass': 'dms.t3.micro',
                    'ReplicationInstanceStatus': 'available',
                    'AllocatedStorage': 20,
                    'InstanceCreateTime': '2023-01-01T00:00:00Z',
                    'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-12345', 'Status': 'active'}],
                    'AvailabilityZone': 'us-east-1a',
                    'ReplicationSubnetGroup': {
                        'ReplicationSubnetGroupIdentifier': 'test-subnet-group',
                        'ReplicationSubnetGroupDescription': 'Test subnet group',
                        'VpcId': 'vpc-12345',
                        'SubnetGroupStatus': 'Complete',
                    },
                    'PreferredMaintenanceWindow': 'sun:10:30-sun:14:30',
                    'PendingModifiedValues': {},
                    'MultiAZ': False,
                    'EngineVersion': '3.4.7',
                    'AutoMinorVersionUpgrade': True,
                    'KmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012',
                    'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                    'ReplicationInstancePublicIpAddress': '1.2.3.4',
                    'ReplicationInstancePrivateIpAddress': '10.0.0.1',
                    'ReplicationInstancePublicIpAddresses': ['1.2.3.4'],
                    'ReplicationInstancePrivateIpAddresses': ['10.0.0.1'],
                    'PubliclyAccessible': True,
                    'SecondaryAvailabilityZone': None,
                    'FreeUntil': None,
                    'DnsNameServers': 'ns1.example.com',
                }
            ],
            'Marker': None,
        }

        # Mock create_replication_instance response
        mock_dms.create_replication_instance.return_value = {
            'ReplicationInstance': {
                'ReplicationInstanceIdentifier': 'new-instance',
                'ReplicationInstanceClass': 'dms.t3.micro',
                'ReplicationInstanceStatus': 'creating',
                'AllocatedStorage': 20,
                'InstanceCreateTime': '2023-01-01T00:00:00Z',
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-12345678', 'Status': 'active'}],
                'AvailabilityZone': 'us-east-1a',
                'ReplicationSubnetGroup': {
                    'ReplicationSubnetGroupIdentifier': 'default',
                    'ReplicationSubnetGroupDescription': 'default',
                    'VpcId': 'vpc-12345678',
                    'SubnetGroupStatus': 'Complete',
                    'Subnets': [],
                },
                'PreferredMaintenanceWindow': 'sun:10:30-sun:14:30',
                'PendingModifiedValues': {},
                'MultiAZ': False,
                'EngineVersion': '3.4.7',
                'AutoMinorVersionUpgrade': True,
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:new-instance',
                'ReplicationInstancePublicIpAddress': None,
                'ReplicationInstancePrivateIpAddress': None,
                'PubliclyAccessible': False,
            }
        }

        yield mock_dms


@pytest.mark.asyncio
class TestDescribeReplicationInstances:
    """Tests for describe_replication_instances function."""

    async def test_describe_all_instances(self, mock_dms_client):
        """Test describing all replication instances."""
        result = await describe_replication_instances()

        assert isinstance(result, ReplicationInstanceListResponse)
        assert len(result.replication_instances) == 1
        assert result.replication_instances[0].replication_instance_identifier == 'test-instance'
        assert result.replication_instances[0].replication_instance_class == 'dms.t3.micro'
        assert result.replication_instances[0].replication_instance_status == 'available'
        assert result.replication_instances[0].allocated_storage == 20
        assert result.replication_instances[0].multi_az is False

        mock_dms_client.describe_replication_instances.assert_called_once()

    async def test_describe_specific_instance(self, mock_dms_client):
        """Test describing a specific replication instance."""
        await describe_replication_instances(replication_instance_identifier='test-instance')

        call_args = mock_dms_client.describe_replication_instances.call_args[1]
        assert 'Filters' in call_args
        assert len(call_args['Filters']) == 1
        assert call_args['Filters'][0]['Name'] == 'replication-instance-id'
        assert call_args['Filters'][0]['Values'] == ['test-instance']

    async def test_describe_with_pagination(self, mock_dms_client):
        """Test describing instances with pagination."""
        await describe_replication_instances(max_records=50, marker='test-marker')

        call_args = mock_dms_client.describe_replication_instances.call_args[1]
        assert call_args['MaxRecords'] == 50
        assert call_args['Marker'] == 'test-marker'

    async def test_describe_instances_response_mapping(self, mock_dms_client):
        """Test that all response fields are properly mapped."""
        result = await describe_replication_instances()

        instance = result.replication_instances[0]
        assert instance.replication_instance_identifier == 'test-instance'
        assert instance.replication_instance_class == 'dms.t3.micro'
        assert instance.replication_instance_status == 'available'
        assert instance.allocated_storage == 20
        assert instance.availability_zone == 'us-east-1a'
        assert instance.multi_az is False
        assert instance.engine_version == '3.4.7'
        assert instance.auto_minor_version_upgrade is True
        assert instance.replication_instance_public_ip_address == '1.2.3.4'
        assert instance.replication_instance_private_ip_address == '10.0.0.1'


@pytest.mark.asyncio
class TestCreateReplicationInstance:
    """Tests for create_replication_instance function."""

    async def test_create_requires_write_access(self, mock_dms_client):
        """Test that create requires write access."""
        from awslabs.dms_mcp_server.context import Context

        Context.initialize(readonly=True)

        with pytest.raises(ValueError, match='Your DMS MCP server does not allow writes'):
            await create_replication_instance(
                replication_instance_identifier='test-instance',
                replication_instance_class='dms.t3.micro',
                allocated_storage=20,
            )

    async def test_create_instance_success(self, mock_dms_client):
        """Test successful instance creation."""
        from awslabs.dms_mcp_server.context import Context

        Context.initialize(readonly=False)

        result = await create_replication_instance(
            replication_instance_identifier='new-instance',
            replication_instance_class='dms.t3.micro',
            allocated_storage=20,
            multi_az=False,
            engine_version=None,
            auto_minor_version_upgrade=True,
            preferred_maintenance_window=None,
            replication_subnet_group_identifier=None,
            vpc_security_group_ids=None,
            publicly_accessible=False,
            kms_key_id=None,
            tags=None,
        )

        assert isinstance(result, CreateReplicationInstanceResponse)
        assert result.replication_instance.replication_instance_identifier == 'new-instance'
        assert result.replication_instance.replication_instance_class == 'dms.t3.micro'
        assert result.replication_instance.replication_instance_status == 'creating'

    async def test_create_instance_invalid_json_tags(self, mock_dms_client):
        """Test create_replication_instance with invalid JSON tags."""
        Context.initialize(readonly=False)

        with pytest.raises(ValueError, match='tags must be valid JSON format'):
            await create_replication_instance(
                replication_instance_identifier='test-instance',
                replication_instance_class='dms.t3.micro',
                allocated_storage=20,
                multi_az=False,
                engine_version=None,
                auto_minor_version_upgrade=True,
                preferred_maintenance_window=None,
                replication_subnet_group_identifier=None,
                vpc_security_group_ids=None,
                publicly_accessible=False,
                kms_key_id=None,
                tags='invalid_json',  # Invalid JSON
            )

    async def test_create_instance_aws_error(self, mock_dms_client):
        """Test create_replication_instance with AWS error."""
        Context.initialize(readonly=False)

        mock_dms_client.create_replication_instance.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ReplicationInstanceAlreadyExistsFault',
                    'Message': 'Instance exists',
                }
            },
            'CreateReplicationInstance',
        )

        with pytest.raises(ValueError, match='Failed to create replication instance'):
            await create_replication_instance(
                replication_instance_identifier='existing-instance',
                replication_instance_class='dms.t3.micro',
                allocated_storage=20,
                multi_az=False,
                engine_version=None,
                auto_minor_version_upgrade=True,
                preferred_maintenance_window=None,
                replication_subnet_group_identifier=None,
                vpc_security_group_ids=None,
                publicly_accessible=False,
                kms_key_id=None,
                tags=None,
            )

    async def test_create_instance_with_all_optional_params(self, mock_dms_client):
        """Test create_replication_instance with all optional parameters."""
        Context.initialize(readonly=False)

        mock_dms_client.create_replication_instance.return_value = {
            'ReplicationInstance': {
                'ReplicationInstanceIdentifier': 'test-instance',
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                'ReplicationInstanceClass': 'dms.t3.micro',
                'ReplicationInstanceStatus': 'creating',
                'AllocatedStorage': 20,
                'MultiAZ': True,
                'AutoMinorVersionUpgrade': False,
            }
        }

        result = await create_replication_instance(
            replication_instance_identifier='test-instance',
            replication_instance_class='dms.t3.micro',
            allocated_storage=20,
            multi_az=True,
            engine_version='3.4.7',
            auto_minor_version_upgrade=False,
            preferred_maintenance_window='sun:23:00-mon:01:00',
            replication_subnet_group_identifier='test-subnet-group',
            vpc_security_group_ids='sg-12345,sg-67890',
            publicly_accessible=True,
            kms_key_id='arn:aws:kms:us-east-1:123456789012:key/test-key',
            tags='[{"Key": "Environment", "Value": "test"}]',
        )

        assert isinstance(result, CreateReplicationInstanceResponse)

        # Verify all optional parameters were passed
        call_args = mock_dms_client.create_replication_instance.call_args[1]
        assert call_args['EngineVersion'] == '3.4.7'
        assert call_args['PreferredMaintenanceWindow'] == 'sun:23:00-mon:01:00'
        assert call_args['ReplicationSubnetGroupIdentifier'] == 'test-subnet-group'
        assert call_args['VpcSecurityGroupIds'] == ['sg-12345', 'sg-67890']
        assert call_args['KmsKeyId'] == 'arn:aws:kms:us-east-1:123456789012:key/test-key'
        assert 'Tags' in call_args
        assert call_args['AllocatedStorage'] == 20
        assert call_args['MultiAZ'] is True
        assert call_args['PubliclyAccessible'] is True
