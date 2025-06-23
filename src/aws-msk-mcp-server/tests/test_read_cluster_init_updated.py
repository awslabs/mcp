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

"""Tests for the read_cluster/__init__.py module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_cluster import register_module
from mcp.server.fastmcp import FastMCP
from typing import cast
from unittest.mock import MagicMock, patch


class TestReadClusterInit:
    """Tests for the read_cluster/__init__.py module."""

    def test_register_module(self):
        """Test the register_module function."""
        # Arrange
        mock_mcp = MagicMock()

        # Act
        register_module(mock_mcp)

        # Assert
        # Verify that the tool decorators were called
        assert mock_mcp.tool.call_count == 2

        # Verify that the expected tools were registered
        mock_mcp.tool.assert_any_call(name='describe_cluster_operation')
        mock_mcp.tool.assert_any_call(name='get_cluster_info')

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.describe_cluster_operation')
    def test_describe_cluster_operation_tool(
        self, mock_describe_cluster_operation, mock_boto3_client
    ):
        """Test the describe_cluster_operation_tool function."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        describe_cluster_operation_tool = decorated_functions['describe_cluster_operation']
        assert describe_cluster_operation_tool is not None, (
            'describe_cluster_operation tool was not registered'
        )

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the describe_cluster_operation function
        expected_response = {
            'ClusterOperationInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
                'OperationType': 'UPDATE',
                'OperationState': 'COMPLETED',
                'CreationTime': '2025-06-20T10:00:00.000Z',
                'EndTime': '2025-06-20T10:30:00.000Z',
            }
        }
        mock_describe_cluster_operation.return_value = expected_response

        # Act
        cluster_operation_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation'
        )
        result = describe_cluster_operation_tool(
            region='us-east-1', cluster_operation_arn=cluster_operation_arn
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_describe_cluster_operation.assert_called_once_with(cluster_operation_arn, mock_client)
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.describe_cluster')
    def test_get_cluster_info_metadata(self, mock_describe_cluster, mock_boto3_client):
        """Test the get_cluster_info function with metadata info_type."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the describe_cluster function
        expected_response = {
            'ClusterInfo': {
                'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'ClusterName': 'test-cluster',
                'State': 'ACTIVE',
                'CreationTime': '2025-06-20T10:00:00.000Z',
                'CurrentVersion': '1',
            }
        }
        mock_describe_cluster.return_value = expected_response

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = wrapper_func(region='us-east-1', cluster_arn=cluster_arn, info_type='metadata')

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_describe_cluster.assert_called_once_with(cluster_arn, mock_client)
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.get_bootstrap_brokers')
    def test_get_cluster_info_brokers(self, mock_get_bootstrap_brokers, mock_boto3_client):
        """Test the get_cluster_info function with brokers info_type."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the get_bootstrap_brokers function
        expected_response = {
            'BootstrapBrokerString': 'broker1:9092,broker2:9092,broker3:9092',
            'BootstrapBrokerStringTls': 'broker1:9094,broker2:9094,broker3:9094',
            'BootstrapBrokerStringSaslScram': 'broker1:9096,broker2:9096,broker3:9096',
        }
        mock_get_bootstrap_brokers.return_value = expected_response

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = wrapper_func(region='us-east-1', cluster_arn=cluster_arn, info_type='brokers')

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_get_bootstrap_brokers.assert_called_once_with(cluster_arn, mock_client)
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.list_nodes')
    def test_get_cluster_info_nodes(self, mock_list_nodes, mock_boto3_client):
        """Test the get_cluster_info function with nodes info_type."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the list_nodes function
        expected_response = {
            'NodeInfoList': [
                {
                    'BrokerNodeInfo': {
                        'BrokerId': 1,
                        'ClientVpcIpAddress': '10.0.0.1',
                        'ClientSubnet': 'subnet-1',
                        'CurrentBrokerSoftwareInfo': {'KafkaVersion': '2.8.1'},
                    }
                }
            ]
        }
        mock_list_nodes.return_value = expected_response

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = wrapper_func(region='us-east-1', cluster_arn=cluster_arn, info_type='nodes')

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_list_nodes.assert_called_once_with(cluster_arn, mock_client)
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.get_compatible_kafka_versions')
    def test_get_cluster_info_compatible_versions(
        self, mock_get_compatible_kafka_versions, mock_boto3_client
    ):
        """Test the get_cluster_info function with compatible_versions info_type."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the get_compatible_kafka_versions function
        expected_response = {
            'CompatibleKafkaVersions': [
                {'SourceVersion': '2.8.1', 'TargetVersions': ['3.3.1', '3.4.0']}
            ]
        }
        mock_get_compatible_kafka_versions.return_value = expected_response

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = wrapper_func(
            region='us-east-1', cluster_arn=cluster_arn, info_type='compatible_versions'
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_get_compatible_kafka_versions.assert_called_once_with(cluster_arn, mock_client)
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.get_cluster_policy')
    def test_get_cluster_info_policy(self, mock_get_cluster_policy, mock_boto3_client):
        """Test the get_cluster_info function with policy info_type."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the get_cluster_policy function
        expected_response = {
            'Policy': '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/ExampleRole"},"Action":["kafka:GetBootstrapBrokers","kafka:DescribeCluster"],"Resource":"*"}]}'
        }
        mock_get_cluster_policy.return_value = expected_response

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = wrapper_func(region='us-east-1', cluster_arn=cluster_arn, info_type='policy')

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_get_cluster_policy.assert_called_once_with(cluster_arn, mock_client)
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.list_cluster_operations')
    def test_get_cluster_info_operations_with_kwargs(
        self, mock_list_cluster_operations, mock_boto3_client
    ):
        """Test the get_cluster_info function with operations info_type and kwargs."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the list_cluster_operations function
        expected_response = {
            'ClusterOperationInfoList': [
                {
                    'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                    'ClusterOperationArn': 'arn:aws:kafka:us-east-1:123456789012:cluster-operation/test-cluster/abcdef/operation',
                    'OperationType': 'UPDATE',
                    'OperationState': 'COMPLETED',
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'EndTime': '2025-06-20T10:30:00.000Z',
                }
            ],
            'NextToken': 'next-token',
        }
        mock_list_cluster_operations.return_value = expected_response

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        kwargs_dict = {'max_results': 20, 'next_token': 'token'}
        result = wrapper_func(
            region='us-east-1', cluster_arn=cluster_arn, info_type='operations', kwargs=kwargs_dict
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_list_cluster_operations.assert_called_once_with(cluster_arn, mock_client, 20, 'token')
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.list_client_vpc_connections')
    def test_get_cluster_info_client_vpc_connections_with_kwargs(
        self, mock_list_client_vpc_connections, mock_boto3_client
    ):
        """Test the get_cluster_info function with client_vpc_connections info_type and kwargs."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the list_client_vpc_connections function
        expected_response = {
            'VpcConnectionInfoList': [
                {
                    'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-connection/abcdef',
                    'VpcId': 'vpc-12345',
                    'SubnetIds': ['subnet-1', 'subnet-2', 'subnet-3'],
                    'SecurityGroups': ['sg-1'],
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                    'VpcConnectionState': 'ACTIVE',
                }
            ],
            'NextToken': 'next-token',
        }
        mock_list_client_vpc_connections.return_value = expected_response

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        kwargs_dict = {'max_results': 15, 'next_token': 'token'}
        result = wrapper_func(
            region='us-east-1',
            cluster_arn=cluster_arn,
            info_type='client_vpc_connections',
            kwargs=kwargs_dict,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_list_client_vpc_connections.assert_called_once_with(
            cluster_arn, mock_client, 15, 'token'
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.list_scram_secrets')
    def test_get_cluster_info_scram_secrets_with_kwargs(
        self, mock_list_scram_secrets, mock_boto3_client
    ):
        """Test the get_cluster_info function with scram_secrets info_type and kwargs."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the list_scram_secrets function
        expected_response = {
            'SecretArnList': ['arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'],
            'NextToken': 'next-token',
        }
        mock_list_scram_secrets.return_value = expected_response

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        kwargs_dict = {'max_results': 5, 'next_token': 'token'}
        result = wrapper_func(
            region='us-east-1',
            cluster_arn=cluster_arn,
            info_type='scram_secrets',
            kwargs=kwargs_dict,
        )

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_list_scram_secrets.assert_called_once_with(cluster_arn, mock_client, 5, 'token')
        assert result == expected_response

    @patch('boto3.client')
    def test_get_cluster_info_invalid_info_type(self, mock_boto3_client):
        """Test the get_cluster_info function with an invalid info_type."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Act & Assert
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ValueError) as excinfo:
            wrapper_func(region='us-east-1', cluster_arn=cluster_arn, info_type='invalid_type')

        assert 'Unsupported info_type: invalid_type' in str(excinfo.value)
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.describe_cluster')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.get_bootstrap_brokers')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.list_nodes')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.get_compatible_kafka_versions')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.get_cluster_policy')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.list_cluster_operations')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.list_client_vpc_connections')
    def test_get_cluster_info_all(
        self,
        mock_list_client_vpc_connections,
        mock_list_cluster_operations,
        mock_get_cluster_policy,
        mock_get_compatible_kafka_versions,
        mock_list_nodes,
        mock_get_bootstrap_brokers,
        mock_describe_cluster,
        mock_boto3_client,
    ):
        """Test the get_cluster_info function with 'all' info_type."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the function responses
        mock_describe_cluster.return_value = {'metadata': 'data'}
        mock_get_bootstrap_brokers.return_value = {'brokers': 'data'}
        mock_list_nodes.return_value = {'nodes': 'data'}
        mock_get_compatible_kafka_versions.return_value = {'versions': 'data'}
        mock_get_cluster_policy.return_value = {'policy': 'data'}
        mock_list_cluster_operations.return_value = {'operations': 'data'}
        mock_list_client_vpc_connections.return_value = {'connections': 'data'}

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = wrapper_func(region='us-east-1', cluster_arn=cluster_arn, info_type='all')

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_describe_cluster.assert_called_once_with(cluster_arn, mock_client)
        mock_get_bootstrap_brokers.assert_called_once_with(cluster_arn, mock_client)
        mock_list_nodes.assert_called_once_with(cluster_arn, mock_client)
        mock_get_compatible_kafka_versions.assert_called_once_with(cluster_arn, mock_client)
        mock_get_cluster_policy.assert_called_once_with(cluster_arn, mock_client)
        mock_list_cluster_operations.assert_called_once_with(cluster_arn, mock_client)
        mock_list_client_vpc_connections.assert_called_once_with(cluster_arn, mock_client)

        # Check that the result contains all the expected keys with their mock values
        assert result['metadata'] == {'metadata': 'data'}
        assert result['brokers'] == {'brokers': 'data'}
        assert result['nodes'] == {'nodes': 'data'}
        assert result['compatible_versions'] == {'versions': 'data'}
        assert result['policy'] == {'policy': 'data'}
        assert result['operations'] == {'operations': 'data'}
        assert result['client_vpc_connections'] == {'connections': 'data'}

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.describe_cluster')
    @patch('awslabs.aws_msk_mcp_server.tools.read_cluster.get_bootstrap_brokers')
    def test_get_cluster_info_all_with_error(
        self, mock_get_bootstrap_brokers, mock_describe_cluster, mock_boto3_client
    ):
        """Test the get_cluster_info function with 'all' info_type when one function raises an error."""
        # Arrange
        # Create a spy that will capture the decorated functions
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        # Register the tools with our spy
        register_module(cast(FastMCP, MockMCP()))

        # Get the captured function
        get_cluster_info_tool = decorated_functions['get_cluster_info']
        assert get_cluster_info_tool is not None, 'get_cluster_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Make describe_cluster raise an exception
        mock_describe_cluster.side_effect = Exception('Test error')

        # Make get_bootstrap_brokers return a normal response
        mock_get_bootstrap_brokers.return_value = {'brokers': 'data'}

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, cluster_arn, info_type='all', kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_cluster_info_tool(
                region=region, cluster_arn=cluster_arn, info_type=info_type, kwargs=kwargs
            )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = wrapper_func(region='us-east-1', cluster_arn=cluster_arn, info_type='all')

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_describe_cluster.assert_called_once_with(cluster_arn, mock_client)
        mock_get_bootstrap_brokers.assert_called_once_with(cluster_arn, mock_client)
        assert result['metadata'] == {'error': 'Test error'}
        assert result['brokers'] == {'brokers': 'data'}
