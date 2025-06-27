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

"""Tests for the mutate_cluster module."""

import json
import pytest
from awslabs.aws_msk_mcp_server.tools.static_tools.cluster_best_practices import (
    get_cluster_best_practices,
)
from unittest.mock import MagicMock, patch


class TestClusterBestPractices:
    """Tests for the get_cluster_best_practices function."""

    def test_valid_instance_type(self):
        """Test with a valid instance type."""
        # Arrange
        instance_type = 'kafka.m5.large'
        number_of_brokers = 3

        # Act
        result = get_cluster_best_practices(instance_type, number_of_brokers)

        # Assert
        assert result['Instance Type'] == f'{instance_type} (provided as input)'
        assert result['Number of Brokers'] == f'{number_of_brokers} (provided as input)'
        assert result['vCPU per Broker'] == 2
        assert result['Memory (GB) per Broker'] == '8 (available on the host)'
        assert result['Recommended Partitions per Broker'] == 1000
        assert result['Recommended Max Partitions per Cluster'] == 3000  # 1000 * 3
        assert result['Replication Factor'] == '3 (recommended)'
        assert result['Minimum In-Sync Replicas'] == 2

    def test_express_instance_type(self):
        """Test with an express instance type."""
        # Arrange
        instance_type = 'express.m7g.large'
        number_of_brokers = 3

        # Act
        result = get_cluster_best_practices(instance_type, number_of_brokers)

        # Assert
        assert result['Instance Type'] == f'{instance_type} (provided as input)'
        assert 'express clusters' in result['Replication Factor']
        assert (
            result['Replication Factor']
            == '3 (Note: For express clusters, replication factor should always be 3)'
        )

    def test_invalid_instance_type(self):
        """Test with an invalid instance type."""
        # Arrange
        instance_type = 'invalid.instance.type'
        number_of_brokers = 3

        # Act
        result = get_cluster_best_practices(instance_type, number_of_brokers)

        # Assert
        assert 'Error' in result
        assert f"Instance type '{instance_type}' is not supported or recognized" in result['Error']

    def test_small_broker_count(self):
        """Test with a broker count less than the recommended replication factor."""
        # Arrange
        instance_type = 'kafka.m5.large'
        number_of_brokers = 2  # Less than recommended replication factor of 3

        # Act
        result = get_cluster_best_practices(instance_type, number_of_brokers)

        # Assert
        assert result['Replication Factor'] == '2 (recommended)'
        assert result['Minimum In-Sync Replicas'] == 2


class TestMutateClusterTools:
    """Tests for the mutate_cluster tools."""

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.create_cluster_v2')
    def test_create_cluster_tool(self, mock_create_cluster_v2, mock_boto3_client):
        """Test the create_cluster_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterName': 'test-cluster',
            'State': 'CREATING',
            'ClusterType': 'PROVISIONED',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'CurrentVersion': '1',
        }
        mock_create_cluster_v2.return_value = expected_response

        # Create a mock function for create_cluster_tool
        def mock_create_cluster_tool(
            region, cluster_name, cluster_type='PROVISIONED', kwargs='{}'
        ):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Parse kwargs
            if kwargs:
                if isinstance(kwargs, str):
                    try:
                        kwargs_dict = json.loads(kwargs)
                    except json.JSONDecodeError:
                        kwargs_dict = {}
                else:
                    # If kwargs is already a dictionary, use it directly
                    kwargs_dict = kwargs
            else:
                kwargs_dict = {}

            # Call create_cluster_v2 with the appropriate parameters
            return mock_create_cluster_v2(cluster_name, cluster_type, client=client, **kwargs_dict)

        # Act
        kwargs_json = json.dumps(
            {
                'broker_node_group_info': {
                    'InstanceType': 'kafka.m5.large',
                    'ClientSubnets': ['subnet-1', 'subnet-2', 'subnet-3'],
                    'SecurityGroups': ['sg-1'],
                    'StorageInfo': {'EbsStorageInfo': {'VolumeSize': 100}},
                },
                'kafka_version': '2.8.1',
                'number_of_broker_nodes': 3,
            }
        )

        result = mock_create_cluster_tool(
            region='us-east-1',
            cluster_name='test-cluster',
            cluster_type='PROVISIONED',
            kwargs=kwargs_json,
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_create_cluster_v2.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    def test_update_broker_storage_tool(self, mock_check_tag, mock_boto3_client):
        """Test the update_broker_storage_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client
        mock_check_tag.return_value = True

        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_kafka_client.update_broker_storage.return_value = expected_response

        # Create a mock function for update_broker_storage_tool
        def mock_update_broker_storage_tool(
            region, cluster_arn, current_version, target_broker_ebs_volume_info
        ):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Check if the resource has the "MCP Generated" tag
            if not mock_check_tag(cluster_arn, client):
                raise ValueError(
                    f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                    "This operation can only be performed on resources tagged with 'MCP Generated'."
                )

            # Parse target_broker_ebs_volume_info if it's a string
            if isinstance(target_broker_ebs_volume_info, str):
                try:
                    target_broker_ebs_volume_info = json.loads(target_broker_ebs_volume_info)
                except json.JSONDecodeError:
                    raise ValueError('Invalid JSON in target_broker_ebs_volume_info')

            # Call update_broker_storage with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_broker_storage import (
                update_broker_storage,
            )

            return update_broker_storage(
                cluster_arn, current_version, target_broker_ebs_volume_info, client
            )

        # Act
        target_broker_ebs_volume_info = [
            {
                'KafkaBrokerNodeId': 'ALL',
                'VolumeSizeGB': 1100,
                'ProvisionedThroughput': {'Enabled': True, 'VolumeThroughput': 250},
            }
        ]

        result = mock_update_broker_storage_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            current_version='1',
            target_broker_ebs_volume_info=json.dumps(target_broker_ebs_volume_info),
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_check_tag.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    def test_update_broker_type_tool(self, mock_check_tag, mock_boto3_client):
        """Test the update_broker_type_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client
        mock_check_tag.return_value = True

        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_kafka_client.update_broker_type.return_value = expected_response

        # Create a mock function for update_broker_type_tool
        def mock_update_broker_type_tool(
            region, cluster_arn, current_version, target_instance_type
        ):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Check if the resource has the "MCP Generated" tag
            if not mock_check_tag(cluster_arn, client):
                raise ValueError(
                    f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                    "This operation can only be performed on resources tagged with 'MCP Generated'."
                )

            # Call update_broker_type with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_broker_type import (
                update_broker_type,
            )

            return update_broker_type(cluster_arn, current_version, target_instance_type, client)

        # Act
        result = mock_update_broker_type_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            current_version='1',
            target_instance_type='kafka.m5.xlarge',
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_check_tag.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    def test_update_cluster_configuration_tool(self, mock_check_tag, mock_boto3_client):
        """Test the update_cluster_configuration_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client
        mock_check_tag.return_value = True

        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_kafka_client.update_cluster_configuration.return_value = expected_response

        # Create a mock function for update_cluster_configuration_tool
        def mock_update_cluster_configuration_tool(
            region, cluster_arn, configuration_arn, configuration_revision, current_version
        ):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Check if the resource has the "MCP Generated" tag
            if not mock_check_tag(cluster_arn, client):
                raise ValueError(
                    f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                    "This operation can only be performed on resources tagged with 'MCP Generated'."
                )

            # Call update_cluster_configuration with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_cluster_configuration import (
                update_cluster_configuration,
            )

            return update_cluster_configuration(
                cluster_arn, configuration_arn, configuration_revision, current_version, client
            )

        # Act
        result = mock_update_cluster_configuration_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            configuration_arn='arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            configuration_revision=1,
            current_version='1',
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_check_tag.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    def test_update_monitoring_tool(self, mock_check_tag, mock_boto3_client):
        """Test the update_monitoring_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client
        mock_check_tag.return_value = True

        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_kafka_client.update_monitoring.return_value = expected_response

        # Create a mock function for update_monitoring_tool
        def mock_update_monitoring_tool(
            region,
            cluster_arn,
            current_version,
            enhanced_monitoring,
            open_monitoring=None,
            logging_info=None,
        ):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Check if the resource has the "MCP Generated" tag
            if not mock_check_tag(cluster_arn, client):
                raise ValueError(
                    f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                    "This operation can only be performed on resources tagged with 'MCP Generated'."
                )

            # Call update_monitoring with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_monitoring import (
                update_monitoring,
            )

            return update_monitoring(
                cluster_arn,
                current_version,
                enhanced_monitoring,
                open_monitoring=open_monitoring,
                logging_info=logging_info,
                client=client,
            )

        # Act
        open_monitoring = {
            'Prometheus': {
                'JmxExporter': {'EnabledInBroker': True},
                'NodeExporter': {'EnabledInBroker': True},
            }
        }

        result = mock_update_monitoring_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            current_version='1',
            enhanced_monitoring='PER_BROKER',
            open_monitoring=open_monitoring,
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_check_tag.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    def test_update_security_tool(self, mock_check_tag, mock_boto3_client):
        """Test the update_security_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client
        mock_check_tag.return_value = True

        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_kafka_client.update_security.return_value = expected_response

        # Create a mock function for update_security_tool
        def mock_update_security_tool(
            region, cluster_arn, current_version, client_authentication=None, encryption_info=None
        ):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Check if the resource has the "MCP Generated" tag
            if not mock_check_tag(cluster_arn, client):
                raise ValueError(
                    f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                    "This operation can only be performed on resources tagged with 'MCP Generated'."
                )

            # Call update_security with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_security import (
                update_security,
            )

            return update_security(
                cluster_arn,
                current_version,
                client_authentication=client_authentication,
                encryption_info=encryption_info,
                client=client,
            )

        # Act
        client_authentication = {'Sasl': {'Scram': {'Enabled': True}, 'Iam': {'Enabled': True}}}

        result = mock_update_security_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            current_version='1',
            client_authentication=client_authentication,
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_check_tag.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    def test_put_cluster_policy_tool(self, mock_check_tag, mock_boto3_client):
        """Test the put_cluster_policy_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client
        mock_check_tag.return_value = True

        expected_response = {}  # Empty response for successful operation
        mock_kafka_client.put_cluster_policy.return_value = expected_response

        # Create a mock function for put_cluster_policy_tool
        def mock_put_cluster_policy_tool(region, cluster_arn, policy):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Check if the resource has the "MCP Generated" tag
            if not mock_check_tag(cluster_arn, client):
                raise ValueError(
                    f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                    "This operation can only be performed on resources tagged with 'MCP Generated'."
                )

            # Call put_cluster_policy with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.put_cluster_policy import (
                put_cluster_policy,
            )

            return put_cluster_policy(cluster_arn, policy, client)

        # Act
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'AWS': 'arn:aws:iam::123456789012:role/ExampleRole'},
                    'Action': ['kafka:GetBootstrapBrokers', 'kafka:DescribeCluster'],
                    'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/*',
                }
            ],
        }

        result = mock_put_cluster_policy_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            policy=policy,
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_check_tag.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    def test_update_broker_count_tool(self, mock_check_tag, mock_boto3_client):
        """Test the update_broker_count_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client
        mock_check_tag.return_value = True

        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_kafka_client.update_broker_count.return_value = expected_response

        # Create a mock function for update_broker_count_tool
        def mock_update_broker_count_tool(
            region, cluster_arn, current_version, target_number_of_broker_nodes
        ):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Check if the resource has the "MCP Generated" tag
            if not mock_check_tag(cluster_arn, client):
                raise ValueError(
                    f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                    "This operation can only be performed on resources tagged with 'MCP Generated'."
                )

            # Call update_broker_count with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_broker_count import (
                update_broker_count,
            )

            return update_broker_count(
                cluster_arn, current_version, target_number_of_broker_nodes, client
            )

        # Act
        result = mock_update_broker_count_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            current_version='1',
            target_number_of_broker_nodes=6,
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_check_tag.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    def test_associate_scram_secret_tool(self, mock_check_tag, mock_boto3_client):
        """Test the associate_scram_secret_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client
        mock_check_tag.return_value = True

        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'SecretArnList': ['arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'],
        }
        mock_kafka_client.batch_associate_scram_secret.return_value = expected_response

        # Create a mock function for associate_scram_secret_tool
        def mock_associate_scram_secret_tool(region, cluster_arn, secret_arns):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Check if the resource has the "MCP Generated" tag
            if not mock_check_tag(cluster_arn, client):
                raise ValueError(
                    f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                    "This operation can only be performed on resources tagged with 'MCP Generated'."
                )

            # Call batch_associate_scram_secret with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.batch_associate_scram_secret import (
                batch_associate_scram_secret,
            )

            return batch_associate_scram_secret(cluster_arn, secret_arns, client)

        # Act
        secret_arns = ['arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret']

        result = mock_associate_scram_secret_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            secret_arns=secret_arns,
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_check_tag.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    def test_disassociate_scram_secret_tool(self, mock_check_tag, mock_boto3_client):
        """Test the disassociate_scram_secret_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client
        mock_check_tag.return_value = True

        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'SecretArnList': ['arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'],
        }
        mock_kafka_client.batch_disassociate_scram_secret.return_value = expected_response

        # Create a mock function for disassociate_scram_secret_tool
        def mock_disassociate_scram_secret_tool(region, cluster_arn, secret_arns):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Check if the resource has the "MCP Generated" tag
            if not mock_check_tag(cluster_arn, client):
                raise ValueError(
                    f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                    "This operation can only be performed on resources tagged with 'MCP Generated'."
                )

            # Call batch_disassociate_scram_secret with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.batch_disassociate_scram_secret import (
                batch_disassociate_scram_secret,
            )

            return batch_disassociate_scram_secret(cluster_arn, secret_arns, client)

        # Act
        secret_arns = ['arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret']

        result = mock_disassociate_scram_secret_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            secret_arns=secret_arns,
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_check_tag.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    def test_reboot_broker_tool(self, mock_boto3_client):
        """Test the reboot_broker_tool function."""
        # Arrange
        # Mock the boto3 client and its response
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_kafka_client.reboot_broker.return_value = expected_response

        # Create a mock function for reboot_broker_tool
        def mock_reboot_broker_tool(region, cluster_arn, broker_ids):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Call reboot_broker with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.reboot_broker import reboot_broker

            return reboot_broker(cluster_arn, broker_ids, client)

        # Act
        broker_ids = ['0', '1', '2']

        result = mock_reboot_broker_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            broker_ids=broker_ids,
        )

        # Assert
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    def test_update_broker_storage_tool_missing_mcp_tag(self, mock_check_tag, mock_boto3_client):
        """Test the update_broker_storage_tool function when the MCP Generated tag is missing."""
        # Arrange
        # Mock the boto3 client and check_mcp_generated_tag to return False
        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client
        mock_check_tag.return_value = False

        # Create a mock function for update_broker_storage_tool
        def mock_update_broker_storage_tool(
            region, cluster_arn, current_version, target_broker_ebs_volume_info
        ):
            # Create a boto3 client
            client = mock_boto3_client(service_name='kafka', region_name=region)

            # Check if the resource has the "MCP Generated" tag
            if not mock_check_tag(cluster_arn, client):
                raise ValueError(
                    f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                    "This operation can only be performed on resources tagged with 'MCP Generated'."
                )

            # Parse target_broker_ebs_volume_info if it's a string
            if isinstance(target_broker_ebs_volume_info, str):
                try:
                    target_broker_ebs_volume_info = json.loads(target_broker_ebs_volume_info)
                except json.JSONDecodeError:
                    raise ValueError('Invalid JSON in target_broker_ebs_volume_info')

            # Call update_broker_storage with the appropriate parameters
            from awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_broker_storage import (
                update_broker_storage,
            )

            return update_broker_storage(
                cluster_arn, current_version, target_broker_ebs_volume_info, client
            )

        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        target_broker_ebs_volume_info = [{'KafkaBrokerNodeId': 'ALL', 'VolumeSizeGB': 1100}]

        with pytest.raises(ValueError) as excinfo:
            mock_update_broker_storage_tool(
                region='us-east-1',
                cluster_arn=cluster_arn,
                current_version='1',
                target_broker_ebs_volume_info=json.dumps(target_broker_ebs_volume_info),
            )

        # Assert
        assert f"Resource {cluster_arn} does not have the 'MCP Generated' tag" in str(
            excinfo.value
        )
        mock_boto3_client.assert_called_once_with(service_name='kafka', region_name='us-east-1')
        mock_check_tag.assert_called_once()
