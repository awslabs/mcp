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

"""Tests for create_replication_group function."""

import pytest
from awslabs.elasticache_mcp_server.tools.rg import create_replication_group
from awslabs.elasticache_mcp_server.tools.rg.create import (
    CreateReplicationGroupRequest,
    LogDeliveryConfiguration,
    LogDeliveryDestinationDetails,
    NodeGroupConfiguration,
)
from unittest.mock import MagicMock, patch


def create_test_request(**kwargs) -> CreateReplicationGroupRequest:
    """Create a test request with default values."""
    defaults = {
        'replication_group_id': 'test-rg',
        'replication_group_description': 'Test replication group',
        'cache_node_type': None,
        'engine': None,
        'engine_version': None,
        'num_cache_clusters': None,
        'preferred_cache_cluster_azs': None,
        'num_node_groups': None,
        'replicas_per_node_group': None,
        'node_group_configuration': None,
        'cache_parameter_group_name': None,
        'cache_subnet_group_name': None,
        'cache_security_group_names': None,
        'security_group_ids': None,
        'tags': None,
        'snapshot_arns': None,
        'snapshot_name': None,
        'preferred_maintenance_window': None,
        'port': None,
        'notification_topic_arn': None,
        'auto_minor_version_upgrade': None,
        'snapshot_retention_limit': None,
        'snapshot_window': None,
        'auth_token': None,
        'transit_encryption_enabled': None,
        'at_rest_encryption_enabled': None,
        'kms_key_id': None,
        'user_group_ids': None,
        'log_delivery_configurations': None,
    }
    defaults.update(kwargs)
    return CreateReplicationGroupRequest(**defaults)


@pytest.fixture
def mock_elasticache_client():
    """Create a mock ElastiCache client."""
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection'
    ) as mock_get_connection:
        mock_client = MagicMock()
        mock_get_connection.return_value = mock_client
        yield mock_client


class TestCreateReplicationGroup:
    """Tests for the create_replication_group function."""

    @pytest.mark.asyncio
    async def test_create_basic_replication_group(self, mock_elasticache_client):
        """Test creating a replication group with basic parameters."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'creating'}
        }

        mock_elasticache_client.create_replication_group.return_value = expected_response

        request = create_test_request()

        response = await create_replication_group(request)

        mock_elasticache_client.create_replication_group.assert_called_once_with(
            ReplicationGroupId='test-rg', ReplicationGroupDescription='Test replication group'
        )
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_create_replication_group_with_all_params(self, mock_elasticache_client):
        """Test creating a replication group with all optional parameters."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'creating'}
        }

        mock_elasticache_client.create_replication_group.return_value = expected_response

        node_group_config = [
            NodeGroupConfiguration(
                NodeGroupId='001',
                Slots='0-8191',
                ReplicaCount=2,
                PrimaryAvailabilityZone='us-west-2a',
                ReplicaAvailabilityZones=['us-west-2b', 'us-west-2c'],
            )
        ]

        log_delivery_config = [
            LogDeliveryConfiguration(
                LogType='slow-log',
                DestinationType='cloudwatch-logs',
                DestinationDetails=LogDeliveryDestinationDetails(
                    CloudWatchLogsDetails={'LogGroup': '/aws/elasticache/test'},
                    KinesisFirehoseDetails=None,
                ),
                LogFormat='text',
                Enabled=True,
            )
        ]

        request = create_test_request(
            cache_node_type='cache.t3.micro',
            engine='redis',
            engine_version='6.x',
            num_cache_clusters=3,
            preferred_cache_cluster_azs=['us-west-2a', 'us-west-2b', 'us-west-2c'],
            num_node_groups=1,
            replicas_per_node_group=2,
            node_group_configuration=node_group_config,
            cache_parameter_group_name='default.redis6.x',
            cache_subnet_group_name='subnet-group-1',
            cache_security_group_names=['sg-1', 'sg-2'],
            security_group_ids=['sg-3', 'sg-4'],
            tags={'Environment': 'test'},
            snapshot_arns=['arn:aws:s3:::bucket/snapshot1'],
            snapshot_name='snapshot-1',
            preferred_maintenance_window='sun:05:00-sun:09:00',
            port=6379,
            notification_topic_arn='arn:aws:sns:region:account:topic',
            auto_minor_version_upgrade=True,
            snapshot_retention_limit=7,
            snapshot_window='05:00-09:00',
            auth_token='secret-token',
            transit_encryption_enabled=True,
            at_rest_encryption_enabled=True,
            kms_key_id='key-1',
            user_group_ids=['group-1', 'group-2'],
            log_delivery_configurations=log_delivery_config,
        )

        response = await create_replication_group(request)

        mock_elasticache_client.create_replication_group.assert_called_once()
        call_args = mock_elasticache_client.create_replication_group.call_args[1]

        assert call_args['ReplicationGroupId'] == 'test-rg'
        assert call_args['ReplicationGroupDescription'] == 'Test replication group'
        assert call_args['CacheNodeType'] == 'cache.t3.micro'
        assert call_args['Engine'] == 'redis'
        assert call_args['EngineVersion'] == '6.x'
        assert call_args['NumCacheClusters'] == 3
        assert call_args['PreferredCacheClusterAZs'] == ['us-west-2a', 'us-west-2b', 'us-west-2c']
        assert call_args['NumNodeGroups'] == 1
        assert call_args['ReplicasPerNodeGroup'] == 2
        assert call_args['NodeGroupConfiguration'] == [
            {
                'NodeGroupId': '001',
                'Slots': '0-8191',
                'ReplicaCount': 2,
                'PrimaryAvailabilityZone': 'us-west-2a',
                'ReplicaAvailabilityZones': ['us-west-2b', 'us-west-2c'],
            }
        ]
        assert call_args['CacheParameterGroupName'] == 'default.redis6.x'
        assert call_args['CacheSubnetGroupName'] == 'subnet-group-1'
        assert call_args['CacheSecurityGroupNames'] == ['sg-1', 'sg-2']
        assert call_args['SecurityGroupIds'] == ['sg-3', 'sg-4']
        assert call_args['Tags'] == [{'Key': 'Environment', 'Value': 'test'}]
        assert call_args['SnapshotArns'] == ['arn:aws:s3:::bucket/snapshot1']
        assert call_args['SnapshotName'] == 'snapshot-1'
        assert call_args['PreferredMaintenanceWindow'] == 'sun:05:00-sun:09:00'
        assert call_args['Port'] == 6379
        assert call_args['NotificationTopicArn'] == 'arn:aws:sns:region:account:topic'
        assert call_args['AutoMinorVersionUpgrade'] is True
        assert call_args['SnapshotRetentionLimit'] == 7
        assert call_args['SnapshotWindow'] == '05:00-09:00'
        assert call_args['AuthToken'] == 'secret-token'
        assert call_args['TransitEncryptionEnabled'] is True
        assert call_args['AtRestEncryptionEnabled'] is True
        assert call_args['KmsKeyId'] == 'key-1'
        assert call_args['UserGroupIds'] == ['group-1', 'group-2']
        assert call_args['LogDeliveryConfigurations'] == [
            {
                'LogType': 'slow-log',
                'DestinationType': 'cloudwatch-logs',
                'DestinationDetails': {
                    'CloudWatchLogsDetails': {'LogGroup': '/aws/elasticache/test'}
                },
                'LogFormat': 'text',
                'Enabled': True,
            }
        ]

        assert response == expected_response

    @pytest.mark.asyncio
    async def test_create_replication_group_with_shorthand_nodegroups(
        self, mock_elasticache_client
    ):
        """Test creating a replication group with shorthand nodegroup syntax."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'creating'}
        }

        mock_elasticache_client.create_replication_group.return_value = expected_response

        # Test shorthand syntax
        shorthand = 'NodeGroupId=ng-1,Slots=0-8191,ReplicaCount=2,PrimaryAvailabilityZone=us-west-2a,ReplicaAvailabilityZones=us-west-2b,us-west-2c'

        request = create_test_request(node_group_configuration=shorthand)

        response = await create_replication_group(request)

        mock_elasticache_client.create_replication_group.assert_called_once()
        call_args = mock_elasticache_client.create_replication_group.call_args[1]

        assert 'NodeGroupConfiguration' in call_args
        config = call_args['NodeGroupConfiguration']
        assert len(config) == 1
        assert config[0]['NodeGroupId'] == 'ng-1'
        assert config[0]['Slots'] == '0-8191'
        assert config[0]['ReplicaCount'] == 2
        assert config[0]['PrimaryAvailabilityZone'] == 'us-west-2a'
        assert config[0]['ReplicaAvailabilityZones'] == ['us-west-2b', 'us-west-2c']
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_create_replication_group_with_multiple_shorthand_nodegroups(
        self, mock_elasticache_client
    ):
        """Test creating a replication group with multiple shorthand nodegroups."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'creating'}
        }

        mock_elasticache_client.create_replication_group.return_value = expected_response

        # Test multiple nodegroups
        shorthand = """NodeGroupId=ng-1,Slots=0-8191,ReplicaCount=2 NodeGroupId=ng-2,Slots=8192-16383,ReplicaCount=2"""

        request = create_test_request(node_group_configuration=shorthand)

        response = await create_replication_group(request)

        mock_elasticache_client.create_replication_group.assert_called_once()
        call_args = mock_elasticache_client.create_replication_group.call_args[1]

        assert 'NodeGroupConfiguration' in call_args
        config = call_args['NodeGroupConfiguration']
        assert len(config) == 2
        assert config[0]['NodeGroupId'] == 'ng-1'
        assert config[0]['Slots'] == '0-8191'
        assert config[0]['ReplicaCount'] == 2
        assert config[1]['NodeGroupId'] == 'ng-2'
        assert config[1]['Slots'] == '8192-16383'
        assert config[1]['ReplicaCount'] == 2
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_create_replication_group_with_invalid_shorthand_nodegroups(
        self, mock_elasticache_client
    ):
        """Test creating a replication group with invalid shorthand nodegroup syntax."""
        # Test missing NodeGroupId
        request = create_test_request(node_group_configuration='Slots=0-8191,ReplicaCount=2')

        exception_class = 'ValueError'
        error_message = 'Missing required field: NodeGroupId'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.create_replication_group.side_effect = mock_exception(
            error_message
        )

        response = await create_replication_group(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid parameter
        request = create_test_request(
            node_group_configuration='NodeGroupId=ng-1,InvalidParam=value'
        )

        exception_class = 'ValueError'
        error_message = 'Invalid parameter: InvalidParam'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.create_replication_group.side_effect = mock_exception(
            error_message
        )

        response = await create_replication_group(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid ReplicaCount
        request = create_test_request(
            node_group_configuration='NodeGroupId=ng-1,ReplicaCount=invalid'
        )

        exception_class = 'ValueError'
        error_message = 'Invalid value for ReplicaCount'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.create_replication_group.side_effect = mock_exception(
            error_message
        )

        response = await create_replication_group(request)
        assert 'error' in response
        assert error_message in response['error']

    @pytest.mark.asyncio
    async def test_create_replication_group_with_json_nodegroups(self, mock_elasticache_client):
        """Test creating a replication group with JSON nodegroup syntax."""
        expected_response = {
            'ReplicationGroup': {'ReplicationGroupId': 'test-rg', 'Status': 'creating'}
        }

        mock_elasticache_client.create_replication_group.return_value = expected_response

        # Test JSON format
        json_config = [
            NodeGroupConfiguration(
                NodeGroupId='ng-1',
                Slots='0-8191',
                ReplicaCount=2,
                PrimaryAvailabilityZone='us-west-2a',
                ReplicaAvailabilityZones=['us-west-2b', 'us-west-2c'],
            )
        ]

        request = create_test_request(node_group_configuration=json_config)

        response = await create_replication_group(request)

        mock_elasticache_client.create_replication_group.assert_called_once()
        call_args = mock_elasticache_client.create_replication_group.call_args[1]

        assert 'NodeGroupConfiguration' in call_args
        config = call_args['NodeGroupConfiguration']
        assert len(config) == 1
        assert config[0]['NodeGroupId'] == 'ng-1'
        assert config[0]['Slots'] == '0-8191'
        assert config[0]['ReplicaCount'] == 2
        assert config[0]['PrimaryAvailabilityZone'] == 'us-west-2a'
        assert config[0]['ReplicaAvailabilityZones'] == ['us-west-2b', 'us-west-2c']
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_create_replication_group_with_invalid_json_nodegroups(
        self, mock_elasticache_client
    ):
        """Test creating a replication group with invalid JSON nodegroup syntax."""
        # Test missing NodeGroupId
        request = create_test_request(
            node_group_configuration=[
                NodeGroupConfiguration(
                    NodeGroupId=None,  # Missing required field
                    Slots='0-8191',
                    ReplicaCount=2,
                    PrimaryAvailabilityZone='us-west-2a',
                    ReplicaAvailabilityZones=['us-west-2b', 'us-west-2c'],
                )
            ]
        )

        exception_class = 'ValueError'
        error_message = 'Missing required field: NodeGroupId'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.create_replication_group.side_effect = mock_exception(
            error_message
        )

        response = await create_replication_group(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid ReplicaCount
        request = create_test_request(
            node_group_configuration=[
                NodeGroupConfiguration(
                    NodeGroupId='ng-1',
                    Slots='0-8191',
                    ReplicaCount=None,  # Invalid value
                    PrimaryAvailabilityZone='us-west-2a',
                    ReplicaAvailabilityZones=['us-west-2b', 'us-west-2c'],
                )
            ]
        )

        exception_class = 'ValueError'
        error_message = 'ReplicaCount must be an integer'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.create_replication_group.side_effect = mock_exception(
            error_message
        )

        response = await create_replication_group(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid ReplicaAvailabilityZones
        request = create_test_request(
            node_group_configuration=[
                NodeGroupConfiguration(
                    NodeGroupId='ng-1',
                    Slots='0-8191',
                    ReplicaCount=2,
                    PrimaryAvailabilityZone='us-west-2a',
                    ReplicaAvailabilityZones=None,  # Invalid value
                )
            ]
        )

        exception_class = 'ValueError'
        error_message = 'ReplicaAvailabilityZones must be a string or list of strings'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.create_replication_group.side_effect = mock_exception(
            error_message
        )

        response = await create_replication_group(request)
        assert 'error' in response
        assert error_message in response['error']

    @pytest.mark.asyncio
    async def test_create_replication_group_aws_exceptions(self, mock_elasticache_client):
        """Test creating a replication group with various AWS exceptions."""
        # Test replication group already exists
        request = create_test_request(replication_group_id='existing-rg')

        exception_class = 'ReplicationGroupAlreadyExistsFault'
        error_message = 'An error occurred: ReplicationGroupAlreadyExistsFault'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.create_replication_group.side_effect = mock_exception(
            error_message
        )

        response = await create_replication_group(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid state
        request = create_test_request()

        exception_class = 'InvalidReplicationGroupStateFault'
        error_message = 'An error occurred: InvalidReplicationGroupStateFault'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.create_replication_group.side_effect = mock_exception(
            error_message
        )

        response = await create_replication_group(request)
        assert 'error' in response
        assert error_message in response['error']

        # Test invalid parameter
        request = create_test_request()

        exception_class = 'InvalidParameterValueException'
        error_message = 'An error occurred: InvalidParameterValueException'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_elasticache_client.exceptions, exception_class, mock_exception)
        mock_elasticache_client.create_replication_group.side_effect = mock_exception(
            error_message
        )

        response = await create_replication_group(request)
        assert 'error' in response
        assert error_message in response['error']
