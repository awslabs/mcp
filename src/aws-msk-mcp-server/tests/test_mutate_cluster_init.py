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

"""Tests for the mutate_cluster/__init__.py module."""

import json
import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_cluster import register_module
from unittest.mock import MagicMock, patch


class TestMutateClusterInit:
    """Tests for the mutate_cluster/__init__.py module."""

    def test_register_module(self):
        """Test the register_module function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Act
        register_module(mock_mcp)

        # Assert
        # Verify that the tool decorators were called with the expected names
        assert len(tool_functions) == 11
        assert 'create_cluster' in tool_functions
        assert 'update_broker_storage' in tool_functions
        assert 'update_broker_type' in tool_functions
        assert 'update_cluster_configuration' in tool_functions
        assert 'update_monitoring' in tool_functions
        assert 'update_security' in tool_functions
        assert 'put_cluster_policy' in tool_functions
        assert 'update_broker_count' in tool_functions
        assert 'associate_scram_secret' in tool_functions
        assert 'disassociate_scram_secret' in tool_functions
        assert 'reboot_broker' in tool_functions

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.create_cluster_v2')
    def test_create_cluster_tool(self, mock_create_cluster_v2, mock_boto3_client):
        """Test the create_cluster_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the create_cluster_tool function
        create_cluster_tool = tool_functions['create_cluster']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the create_cluster_v2 function
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterName': 'test-cluster',
            'State': 'CREATING',
            'ClusterType': 'PROVISIONED',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'CurrentVersion': '1',
        }
        mock_create_cluster_v2.return_value = expected_response

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

        result = create_cluster_tool(
            region='us-east-1',
            cluster_name='test-cluster',
            cluster_type='PROVISIONED',
            kwargs=kwargs_json,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_create_cluster_v2.assert_called_once()
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_broker_storage')
    def test_update_broker_storage_tool(
        self, mock_update_broker_storage, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_broker_storage_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the update_broker_storage_tool function
        update_broker_storage_tool = tool_functions['update_broker_storage']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Act & Assert
        target_broker_ebs_volume_info = json.dumps(
            [
                {
                    'KafkaBrokerNodeId': 'ALL',
                    'VolumeSizeGB': 1100,
                    'ProvisionedThroughput': {'Enabled': True, 'VolumeThroughput': 250},
                }
            ]
        )

        with pytest.raises(
            ValueError,
            match="Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'.",
        ):
            update_broker_storage_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                current_version='1',
                target_broker_ebs_volume_info=target_broker_ebs_volume_info,
            )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_update_broker_storage.assert_not_called()

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_broker_type')
    def test_update_broker_type_tool(
        self, mock_update_broker_type, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_broker_type_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the update_broker_type_tool function
        update_broker_type_tool = tool_functions['update_broker_type']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'.",
        ):
            update_broker_type_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                current_version='1',
                target_instance_type='kafka.m5.xlarge',
            )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_update_broker_type.assert_not_called()

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_monitoring')
    def test_update_monitoring_tool(
        self, mock_update_monitoring, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_monitoring_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the update_monitoring_tool function
        update_monitoring_tool = tool_functions['update_monitoring']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Act & Assert
        open_monitoring = {
            'Prometheus': {
                'JmxExporter': {'EnabledInBroker': True},
                'NodeExporter': {'EnabledInBroker': True},
            }
        }

        logging_info = {
            'BrokerLogs': {'CloudWatchLogs': {'Enabled': True, 'LogGroup': 'my-log-group'}}
        }

        with pytest.raises(
            ValueError,
            match="Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'.",
        ):
            update_monitoring_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                current_version='1',
                enhanced_monitoring='PER_BROKER',
                open_monitoring=open_monitoring,
                logging_info=logging_info,
            )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_update_monitoring.assert_not_called()

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_security')
    def test_update_security_tool(
        self, mock_update_security, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_security_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the update_security_tool function
        update_security_tool = tool_functions['update_security']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Act & Assert
        client_authentication = {'Sasl': {'Scram': {'Enabled': True}, 'Iam': {'Enabled': True}}}

        encryption_info = {'EncryptionInTransit': {'InCluster': True, 'ClientBroker': 'TLS'}}

        with pytest.raises(
            ValueError,
            match="Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'.",
        ):
            update_security_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                current_version='1',
                client_authentication=client_authentication,
                encryption_info=encryption_info,
            )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_update_security.assert_not_called()

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.put_cluster_policy')
    def test_put_cluster_policy_tool(
        self, mock_put_cluster_policy, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the put_cluster_policy_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the put_cluster_policy_tool function
        put_cluster_policy_tool = tool_functions['put_cluster_policy']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Act & Assert
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

        with pytest.raises(
            ValueError,
            match="Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'.",
        ):
            put_cluster_policy_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                policy=policy,
            )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_put_cluster_policy.assert_not_called()

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_broker_count')
    def test_update_broker_count_tool(
        self, mock_update_broker_count, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_broker_count_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the update_broker_count_tool function
        update_broker_count_tool = tool_functions['update_broker_count']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'.",
        ):
            update_broker_count_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                current_version='1',
                target_number_of_broker_nodes=6,
            )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_update_broker_count.assert_not_called()

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.batch_associate_scram_secret')
    def test_associate_scram_secret_tool(
        self, mock_batch_associate_scram_secret, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the associate_scram_secret_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the associate_scram_secret_tool function
        associate_scram_secret_tool = tool_functions['associate_scram_secret']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Act & Assert
        secret_arns = ['arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret']

        with pytest.raises(
            ValueError,
            match="Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'.",
        ):
            associate_scram_secret_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                secret_arns=secret_arns,
            )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_batch_associate_scram_secret.assert_not_called()

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.check_mcp_generated_tag')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.batch_disassociate_scram_secret')
    def test_disassociate_scram_secret_tool(
        self, mock_batch_disassociate_scram_secret, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the disassociate_scram_secret_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the disassociate_scram_secret_tool function
        disassociate_scram_secret_tool = tool_functions['disassociate_scram_secret']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Act & Assert
        secret_arns = ['arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret']

        with pytest.raises(
            ValueError,
            match="Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. This operation can only be performed on resources tagged with 'MCP Generated'.",
        ):
            disassociate_scram_secret_tool(
                region='us-east-1',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                secret_arns=secret_arns,
            )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_batch_disassociate_scram_secret.assert_not_called()

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.reboot_broker')
    def test_reboot_broker_tool(self, mock_reboot_broker, mock_boto3_client):
        """Test the reboot_broker_tool function."""
        # Arrange
        mock_mcp = MagicMock()

        # Configure the tool decorator to capture the decorated function
        tool_functions = {}

        def mock_tool_decorator(**kwargs):
            def capture_function(func):
                tool_functions[kwargs.get('name')] = func
                return func

            return capture_function

        mock_mcp.tool.side_effect = mock_tool_decorator

        # Register the module to capture the tool functions
        register_module(mock_mcp)

        # Get the reboot_broker_tool function
        reboot_broker_tool = tool_functions['reboot_broker']

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the reboot_broker function
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_reboot_broker.return_value = expected_response

        # Act
        broker_ids = ['1', '2', '3']

        result = reboot_broker_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            broker_ids=broker_ids,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_reboot_broker.assert_called_once()
        assert result == expected_response
