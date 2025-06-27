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

"""Tests for the create_cluster_v2.py module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_cluster.create_cluster_v2 import create_cluster_v2
from unittest.mock import MagicMock


class TestCreateClusterV2:
    """Tests for the create_cluster_v2 function."""

    def test_create_cluster_v2_no_client(self):
        """Test create_cluster_v2 with no client provided."""
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            create_cluster_v2('test-cluster')

        assert 'Client must be provided' in str(excinfo.value)

    def test_create_cluster_v2_provisioned(self):
        """Test create_cluster_v2 with PROVISIONED cluster type."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterName': 'test-cluster',
            'State': 'CREATING',
            'ClusterType': 'PROVISIONED',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'CurrentVersion': '1',
        }
        mock_client.create_cluster_v2.return_value = expected_response

        # Act
        result = create_cluster_v2(
            cluster_name='test-cluster',
            cluster_type='PROVISIONED',
            client=mock_client,
            broker_node_group_info={
                'InstanceType': 'kafka.m5.large',
                'ClientSubnets': ['subnet-1', 'subnet-2', 'subnet-3'],
                'SecurityGroups': ['sg-1'],
                'StorageInfo': {'EbsStorageInfo': {'VolumeSize': 100}},
            },
            kafka_version='2.8.1',
            number_of_broker_nodes=3,
            client_authentication={'Sasl': {'Scram': {'Enabled': True}, 'Iam': {'Enabled': True}}},
            encryption_info={'EncryptionInTransit': {'InCluster': True, 'ClientBroker': 'TLS'}},
            enhanced_monitoring='PER_BROKER',
            open_monitoring={
                'Prometheus': {
                    'JmxExporter': {'EnabledInBroker': True},
                    'NodeExporter': {'EnabledInBroker': True},
                }
            },
            logging_info={
                'BrokerLogs': {'CloudWatchLogs': {'Enabled': True, 'LogGroup': 'my-log-group'}}
            },
            configuration_info={
                'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
                'Revision': 1,
            },
            storage_mode='TIERED',
            tags={'Environment': 'Test', 'Owner': 'TestTeam'},
        )

        # Assert
        mock_client.create_cluster_v2.assert_called_once()
        call_args = mock_client.create_cluster_v2.call_args[1]

        assert call_args['ClusterName'] == 'test-cluster'
        assert 'Provisioned' in call_args
        assert call_args['Provisioned']['BrokerNodeGroupInfo'] == {
            'InstanceType': 'kafka.m5.large',
            'ClientSubnets': ['subnet-1', 'subnet-2', 'subnet-3'],
            'SecurityGroups': ['sg-1'],
            'StorageInfo': {'EbsStorageInfo': {'VolumeSize': 100}},
        }
        assert call_args['Provisioned']['KafkaVersion'] == '2.8.1'
        assert call_args['Provisioned']['NumberOfBrokerNodes'] == 3
        assert call_args['Provisioned']['ClientAuthentication'] == {
            'Sasl': {'Scram': {'Enabled': True}, 'Iam': {'Enabled': True}}
        }
        assert call_args['Provisioned']['EncryptionInfo'] == {
            'EncryptionInTransit': {'InCluster': True, 'ClientBroker': 'TLS'}
        }
        assert call_args['Provisioned']['EnhancedMonitoring'] == 'PER_BROKER'
        assert call_args['Provisioned']['OpenMonitoring'] == {
            'Prometheus': {
                'JmxExporter': {'EnabledInBroker': True},
                'NodeExporter': {'EnabledInBroker': True},
            }
        }
        assert call_args['Provisioned']['LoggingInfo'] == {
            'BrokerLogs': {'CloudWatchLogs': {'Enabled': True, 'LogGroup': 'my-log-group'}}
        }
        assert call_args['Provisioned']['ConfigurationInfo'] == {
            'Arn': 'arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            'Revision': 1,
        }
        assert call_args['Provisioned']['StorageMode'] == 'TIERED'
        assert call_args['Tags'] == {'Environment': 'Test', 'Owner': 'TestTeam'}
        assert result == expected_response

    def test_create_cluster_v2_serverless(self):
        """Test create_cluster_v2 with SERVERLESS cluster type."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterName': 'test-cluster',
            'State': 'CREATING',
            'ClusterType': 'SERVERLESS',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'CurrentVersion': '1',
        }
        mock_client.create_cluster_v2.return_value = expected_response

        # Act
        result = create_cluster_v2(
            cluster_name='test-cluster',
            cluster_type='SERVERLESS',
            client=mock_client,
            vpc_configs=[
                {'SubnetIds': ['subnet-1', 'subnet-2', 'subnet-3'], 'SecurityGroupIds': ['sg-1']}
            ],
            client_authentication={'Sasl': {'Iam': {'Enabled': True}}},
            tags={'Environment': 'Test', 'Owner': 'TestTeam'},
        )

        # Assert
        mock_client.create_cluster_v2.assert_called_once()
        call_args = mock_client.create_cluster_v2.call_args[1]

        assert call_args['ClusterName'] == 'test-cluster'
        assert 'Serverless' in call_args
        assert call_args['Serverless']['VpcConfigs'] == [
            {'SubnetIds': ['subnet-1', 'subnet-2', 'subnet-3'], 'SecurityGroupIds': ['sg-1']}
        ]
        assert call_args['Serverless']['ClientAuthentication'] == {
            'Sasl': {'Iam': {'Enabled': True}}
        }
        assert call_args['Tags'] == {'Environment': 'Test', 'Owner': 'TestTeam'}
        assert result == expected_response

    def test_create_cluster_v2_minimal_provisioned(self):
        """Test create_cluster_v2 with minimal parameters for PROVISIONED cluster type."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterName': 'test-cluster',
            'State': 'CREATING',
            'ClusterType': 'PROVISIONED',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'CurrentVersion': '1',
        }
        mock_client.create_cluster_v2.return_value = expected_response

        # Act
        result = create_cluster_v2(
            cluster_name='test-cluster',
            client=mock_client,
            broker_node_group_info={
                'InstanceType': 'kafka.m5.large',
                'ClientSubnets': ['subnet-1', 'subnet-2', 'subnet-3'],
                'SecurityGroups': ['sg-1'],
            },
            kafka_version='2.8.1',
            number_of_broker_nodes=3,
        )

        # Assert
        mock_client.create_cluster_v2.assert_called_once()
        call_args = mock_client.create_cluster_v2.call_args[1]

        assert call_args['ClusterName'] == 'test-cluster'
        assert 'Provisioned' in call_args
        assert call_args['Provisioned']['BrokerNodeGroupInfo'] == {
            'InstanceType': 'kafka.m5.large',
            'ClientSubnets': ['subnet-1', 'subnet-2', 'subnet-3'],
            'SecurityGroups': ['sg-1'],
        }
        assert call_args['Provisioned']['KafkaVersion'] == '2.8.1'
        assert call_args['Provisioned']['NumberOfBrokerNodes'] == 3
        assert result == expected_response

    def test_create_cluster_v2_minimal_serverless(self):
        """Test create_cluster_v2 with minimal parameters for SERVERLESS cluster type."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterName': 'test-cluster',
            'State': 'CREATING',
            'ClusterType': 'SERVERLESS',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'CurrentVersion': '1',
        }
        mock_client.create_cluster_v2.return_value = expected_response

        # Act
        result = create_cluster_v2(
            cluster_name='test-cluster',
            cluster_type='SERVERLESS',
            client=mock_client,
            vpc_configs=[
                {'SubnetIds': ['subnet-1', 'subnet-2', 'subnet-3'], 'SecurityGroupIds': ['sg-1']}
            ],
        )

        # Assert
        mock_client.create_cluster_v2.assert_called_once()
        call_args = mock_client.create_cluster_v2.call_args[1]

        assert call_args['ClusterName'] == 'test-cluster'
        assert 'Serverless' in call_args
        assert call_args['Serverless']['VpcConfigs'] == [
            {'SubnetIds': ['subnet-1', 'subnet-2', 'subnet-3'], 'SecurityGroupIds': ['sg-1']}
        ]
        assert result == expected_response

    def test_create_cluster_v2_kwargs_handling(self):
        """Test create_cluster_v2 with kwargs handling."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterName': 'test-cluster',
            'State': 'CREATING',
            'ClusterType': 'PROVISIONED',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'CurrentVersion': '1',
        }
        mock_client.create_cluster_v2.return_value = expected_response

        # Test with string kwargs
        kwargs_str = '{"broker_node_group_info": {"InstanceType": "kafka.m5.large", "ClientSubnets": ["subnet-1", "subnet-2", "subnet-3"], "SecurityGroups": ["sg-1"]}, "kafka_version": "2.8.1", "number_of_broker_nodes": 3}'

        # Act
        result = create_cluster_v2(
            cluster_name='test-cluster', client=mock_client, **{'kwargs': kwargs_str}
        )

        # Assert
        mock_client.create_cluster_v2.assert_called_once()
        call_args = mock_client.create_cluster_v2.call_args[1]

        assert call_args['ClusterName'] == 'test-cluster'
        assert 'Provisioned' in call_args
        assert result == expected_response
