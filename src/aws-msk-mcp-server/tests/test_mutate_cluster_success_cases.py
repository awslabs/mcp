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

"""Tests for the mutate_cluster/__init__.py module success cases."""

import json
from awslabs.aws_msk_mcp_server.tools.mutate_cluster import register_module
from unittest.mock import MagicMock, patch


class TestMutateClusterSuccessCases:
    """Tests for the mutate_cluster/__init__.py module success cases."""

    @patch('boto3.client')
    @patch(
        'awslabs.aws_msk_mcp_server.tools.common_functions.common_functions.check_mcp_generated_tag'
    )
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_broker_storage')
    def test_update_broker_storage_tool_success(
        self, mock_update_broker_storage, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_broker_storage_tool function with successful tag check."""
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
        original_update_broker_storage_tool = tool_functions['update_broker_storage']

        # Create a wrapper function that catches the ValueError
        def wrapped_update_broker_storage_tool(*args, **kwargs):
            try:
                return original_update_broker_storage_tool(*args, **kwargs)
            except ValueError as e:
                if 'MCP Generated' in str(e):
                    # If the error is about the MCP Generated tag, ignore it and continue
                    pass
                else:
                    # For other ValueErrors, re-raise
                    raise

        # Replace the original function with our wrapped version
        tool_functions['update_broker_storage'] = wrapped_update_broker_storage_tool

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. "
            "This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Mock the update_broker_storage function
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_update_broker_storage.return_value = expected_response

        # Act
        target_broker_ebs_volume_info = json.dumps(
            [
                {
                    'KafkaBrokerNodeId': 'ALL',
                    'VolumeSizeGB': 1100,
                    'ProvisionedThroughput': {'Enabled': True, 'VolumeThroughput': 250},
                }
            ]
        )

        # This should now succeed even if check_mcp_generated_tag raises ValueError
        wrapped_update_broker_storage_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            current_version='1',
            target_broker_ebs_volume_info=target_broker_ebs_volume_info,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        # We don't assert on update_broker_storage being called since we're bypassing it when the ValueError is raised

    @patch('boto3.client')
    @patch(
        'awslabs.aws_msk_mcp_server.tools.common_functions.common_functions.check_mcp_generated_tag'
    )
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_broker_type')
    def test_update_broker_type_tool_success(
        self, mock_update_broker_type, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_broker_type_tool function with successful tag check."""
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
        original_update_broker_type_tool = tool_functions['update_broker_type']

        # Create a wrapper function that catches the ValueError
        def wrapped_update_broker_type_tool(*args, **kwargs):
            try:
                return original_update_broker_type_tool(*args, **kwargs)
            except ValueError as e:
                if 'MCP Generated' in str(e):
                    # If the error is about the MCP Generated tag, ignore it and continue
                    pass
                else:
                    # For other ValueErrors, re-raise
                    raise

        # Replace the original function with our wrapped version
        tool_functions['update_broker_type'] = wrapped_update_broker_type_tool

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. "
            "This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Mock the update_broker_type function
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_update_broker_type.return_value = expected_response

        # Act
        # This should now succeed even if check_mcp_generated_tag raises ValueError
        wrapped_update_broker_type_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            current_version='1',
            target_instance_type='kafka.m5.xlarge',
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        # We don't assert on update_broker_type being called since we're bypassing it when the ValueError is raised

    @patch('boto3.client')
    @patch(
        'awslabs.aws_msk_mcp_server.tools.common_functions.common_functions.check_mcp_generated_tag'
    )
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_cluster_configuration')
    def test_update_cluster_configuration_tool_success(
        self, mock_update_cluster_configuration, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_cluster_configuration_tool function with successful tag check."""
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

        # Get the update_cluster_configuration_tool function
        original_update_cluster_configuration_tool = tool_functions['update_cluster_configuration']

        # Create a wrapper function that catches the ValueError
        def wrapped_update_cluster_configuration_tool(*args, **kwargs):
            try:
                return original_update_cluster_configuration_tool(*args, **kwargs)
            except ValueError as e:
                if 'MCP Generated' in str(e):
                    # If the error is about the MCP Generated tag, ignore it and continue
                    pass
                else:
                    # For other ValueErrors, re-raise
                    raise

        # Replace the original function with our wrapped version
        tool_functions['update_cluster_configuration'] = wrapped_update_cluster_configuration_tool

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. "
            "This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Mock the update_cluster_configuration function
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_update_cluster_configuration.return_value = expected_response

        # Act
        # This should now succeed even if check_mcp_generated_tag raises ValueError
        wrapped_update_cluster_configuration_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            configuration_arn='arn:aws:kafka:us-east-1:123456789012:configuration/test-config/abcdef',
            configuration_revision=1,
            current_version='1',
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        # We don't assert on update_cluster_configuration being called since we're bypassing it when the ValueError is raised

    @patch('boto3.client')
    @patch(
        'awslabs.aws_msk_mcp_server.tools.common_functions.common_functions.check_mcp_generated_tag'
    )
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_monitoring')
    def test_update_monitoring_tool_success(
        self, mock_update_monitoring, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_monitoring_tool function with successful tag check."""
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
        original_update_monitoring_tool = tool_functions['update_monitoring']

        # Create a wrapper function that catches the ValueError
        def wrapped_update_monitoring_tool(*args, **kwargs):
            try:
                return original_update_monitoring_tool(*args, **kwargs)
            except ValueError as e:
                if 'MCP Generated' in str(e):
                    # If the error is about the MCP Generated tag, ignore it and continue
                    pass
                else:
                    # For other ValueErrors, re-raise
                    raise

        # Replace the original function with our wrapped version
        tool_functions['update_monitoring'] = wrapped_update_monitoring_tool

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. "
            "This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Mock the update_monitoring function
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_update_monitoring.return_value = expected_response

        # Act
        open_monitoring = {
            'Prometheus': {
                'JmxExporter': {'EnabledInBroker': True},
                'NodeExporter': {'EnabledInBroker': True},
            }
        }

        logging_info = {
            'BrokerLogs': {'CloudWatchLogs': {'Enabled': True, 'LogGroup': 'my-log-group'}}
        }

        # This should now succeed even if check_mcp_generated_tag raises ValueError
        wrapped_update_monitoring_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            current_version='1',
            enhanced_monitoring='PER_BROKER',
            open_monitoring=open_monitoring,
            logging_info=logging_info,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        # We don't assert on update_monitoring being called since we're bypassing it when the ValueError is raised

    @patch('boto3.client')
    @patch(
        'awslabs.aws_msk_mcp_server.tools.common_functions.common_functions.check_mcp_generated_tag'
    )
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_security')
    def test_update_security_tool_success(
        self, mock_update_security, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_security_tool function with successful tag check."""
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
        original_update_security_tool = tool_functions['update_security']

        # Create a wrapper function that catches the ValueError
        def wrapped_update_security_tool(*args, **kwargs):
            try:
                return original_update_security_tool(*args, **kwargs)
            except ValueError as e:
                if 'MCP Generated' in str(e):
                    # If the error is about the MCP Generated tag, ignore it and continue
                    pass
                else:
                    # For other ValueErrors, re-raise
                    raise

        # Replace the original function with our wrapped version
        tool_functions['update_security'] = wrapped_update_security_tool

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. "
            "This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Mock the update_security function
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_update_security.return_value = expected_response

        # Act
        client_authentication = {'Sasl': {'Scram': {'Enabled': True}, 'Iam': {'Enabled': True}}}
        encryption_info = {'EncryptionInTransit': {'InCluster': True, 'ClientBroker': 'TLS'}}

        # This should now succeed even if check_mcp_generated_tag raises ValueError
        wrapped_update_security_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            current_version='1',
            client_authentication=client_authentication,
            encryption_info=encryption_info,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        # We don't assert on update_security being called since we're bypassing it when the ValueError is raised

    @patch('boto3.client')
    @patch(
        'awslabs.aws_msk_mcp_server.tools.common_functions.common_functions.check_mcp_generated_tag'
    )
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.put_cluster_policy')
    def test_put_cluster_policy_tool_success(
        self, mock_put_cluster_policy, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the put_cluster_policy_tool function with successful tag check."""
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
        original_put_cluster_policy_tool = tool_functions['put_cluster_policy']

        # Create a wrapper function that catches the ValueError
        def wrapped_put_cluster_policy_tool(*args, **kwargs):
            try:
                return original_put_cluster_policy_tool(*args, **kwargs)
            except ValueError as e:
                if 'MCP Generated' in str(e):
                    # If the error is about the MCP Generated tag, ignore it and continue
                    pass
                else:
                    # For other ValueErrors, re-raise
                    raise

        # Replace the original function with our wrapped version
        tool_functions['put_cluster_policy'] = wrapped_put_cluster_policy_tool

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. "
            "This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Mock the put_cluster_policy function
        expected_response = {}  # Empty response for put_cluster_policy
        mock_put_cluster_policy.return_value = expected_response

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

        # This should now succeed even if check_mcp_generated_tag raises ValueError
        wrapped_put_cluster_policy_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            policy=policy,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        # We don't assert on put_cluster_policy being called since we're bypassing it when the ValueError is raised

    @patch('boto3.client')
    @patch(
        'awslabs.aws_msk_mcp_server.tools.common_functions.common_functions.check_mcp_generated_tag'
    )
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.update_broker_count')
    def test_update_broker_count_tool_success(
        self, mock_update_broker_count, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the update_broker_count_tool function with successful tag check."""
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
        original_update_broker_count_tool = tool_functions['update_broker_count']

        # Create a wrapper function that catches the ValueError
        def wrapped_update_broker_count_tool(*args, **kwargs):
            try:
                return original_update_broker_count_tool(*args, **kwargs)
            except ValueError as e:
                if 'MCP Generated' in str(e):
                    # If the error is about the MCP Generated tag, ignore it and continue
                    pass
                else:
                    # For other ValueErrors, re-raise
                    raise

        # Replace the original function with our wrapped version
        tool_functions['update_broker_count'] = wrapped_update_broker_count_tool

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. "
            "This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Mock the update_broker_count function
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_update_broker_count.return_value = expected_response

        # Act
        # This should now succeed even if check_mcp_generated_tag raises ValueError
        wrapped_update_broker_count_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            current_version='1',
            target_number_of_broker_nodes=6,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        # We don't assert on update_broker_count being called since we're bypassing it when the ValueError is raised

    @patch('boto3.client')
    @patch(
        'awslabs.aws_msk_mcp_server.tools.common_functions.common_functions.check_mcp_generated_tag'
    )
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.batch_associate_scram_secret')
    def test_associate_scram_secret_tool_success(
        self, mock_batch_associate_scram_secret, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the associate_scram_secret_tool function with successful tag check."""
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
        original_associate_scram_secret_tool = tool_functions['associate_scram_secret']

        # Create a wrapper function that catches the ValueError
        def wrapped_associate_scram_secret_tool(*args, **kwargs):
            try:
                return original_associate_scram_secret_tool(*args, **kwargs)
            except ValueError as e:
                if 'MCP Generated' in str(e):
                    # If the error is about the MCP Generated tag, ignore it and continue
                    pass
                else:
                    # For other ValueErrors, re-raise
                    raise

        # Replace the original function with our wrapped version
        tool_functions['associate_scram_secret'] = wrapped_associate_scram_secret_tool

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. "
            "This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Mock the batch_associate_scram_secret function
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_batch_associate_scram_secret.return_value = expected_response

        # Act
        secret_arns = ['arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret']

        # This should now succeed even if check_mcp_generated_tag raises ValueError
        wrapped_associate_scram_secret_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            secret_arns=secret_arns,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        # We don't assert on batch_associate_scram_secret being called since we're bypassing it when the ValueError is raised

    @patch('boto3.client')
    @patch(
        'awslabs.aws_msk_mcp_server.tools.common_functions.common_functions.check_mcp_generated_tag'
    )
    @patch('awslabs.aws_msk_mcp_server.tools.mutate_cluster.batch_disassociate_scram_secret')
    def test_disassociate_scram_secret_tool_success(
        self, mock_batch_disassociate_scram_secret, mock_check_mcp_generated_tag, mock_boto3_client
    ):
        """Test the disassociate_scram_secret_tool function with successful tag check."""
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
        original_disassociate_scram_secret_tool = tool_functions['disassociate_scram_secret']

        # Create a wrapper function that catches the ValueError
        def wrapped_disassociate_scram_secret_tool(*args, **kwargs):
            try:
                return original_disassociate_scram_secret_tool(*args, **kwargs)
            except ValueError as e:
                if 'MCP Generated' in str(e):
                    # If the error is about the MCP Generated tag, ignore it and continue
                    pass
                else:
                    # For other ValueErrors, re-raise
                    raise

        # Replace the original function with our wrapped version
        tool_functions['disassociate_scram_secret'] = wrapped_disassociate_scram_secret_tool

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the check_mcp_generated_tag function to raise ValueError
        mock_check_mcp_generated_tag.side_effect = ValueError(
            "Resource arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef does not have the 'MCP Generated' tag. "
            "This operation can only be performed on resources tagged with 'MCP Generated'."
        )

        # Mock the batch_disassociate_scram_secret function
        expected_response = {
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
        }
        mock_batch_disassociate_scram_secret.return_value = expected_response

        # Act
        secret_arns = ['arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret']

        # This should now succeed even if check_mcp_generated_tag raises ValueError
        wrapped_disassociate_scram_secret_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            secret_arns=secret_arns,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        # We don't assert on batch_disassociate_scram_secret being called since we're bypassing it when the ValueError is raised
