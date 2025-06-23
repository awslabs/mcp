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

"""Tests for the read_global/__init__.py module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_global import register_module
from unittest.mock import MagicMock, patch


class TestReadGlobalInit:
    """Tests for the read_global/__init__.py module."""

    def test_register_module(self):
        """Test the register_module function."""
        # Arrange
        mock_mcp = MagicMock()

        # Act
        register_module(mock_mcp)

        # Assert
        # Verify that the tool decorators were called
        assert mock_mcp.tool.call_count == 1

        # Verify that the expected tools were registered
        mock_mcp.tool.assert_any_call(name='get_global_info')

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_global.list_clusters')
    @patch('awslabs.aws_msk_mcp_server.tools.read_global.list_configurations')
    @patch('awslabs.aws_msk_mcp_server.tools.read_global.list_vpc_connections')
    @patch('awslabs.aws_msk_mcp_server.tools.read_global.list_kafka_versions')
    def test_get_global_info_all(
        self,
        mock_list_kafka_versions,
        mock_list_vpc_connections,
        mock_list_configurations,
        mock_list_clusters,
        mock_boto3_client,
    ):
        """Test the get_global_info function with 'all' info_type."""
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
        register_module(MockMCP())

        # Get the captured function
        get_global_info_func = decorated_functions['get_global_info']
        assert get_global_info_func is not None, 'get_global_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the list_* functions
        mock_list_clusters.return_value = {'ClusterInfoList': []}
        mock_list_configurations.return_value = {'ConfigurationInfoList': []}
        mock_list_vpc_connections.return_value = {'VpcConnectionInfoList': []}
        mock_list_kafka_versions.return_value = {'KafkaVersions': []}

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, info_type, kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_global_info_func(region=region, info_type=info_type, kwargs=kwargs)

        result = wrapper_func(region='us-east-1', info_type='all')

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_list_clusters.assert_called_once_with(
            mock_client,
            cluster_name_filter=None,
            cluster_type_filter=None,
            max_results=10,
            next_token=None,
        )
        mock_list_configurations.assert_called_once_with(
            mock_client, max_results=10, next_token=None
        )
        mock_list_vpc_connections.assert_called_once_with(
            mock_client, max_results=10, next_token=None
        )
        mock_list_kafka_versions.assert_called_once_with(mock_client)

        assert result == {
            'clusters': {'ClusterInfoList': []},
            'configurations': {'ConfigurationInfoList': []},
            'vpc_connections': {'VpcConnectionInfoList': []},
            'kafka_versions': {'KafkaVersions': []},
        }

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_global.list_clusters')
    def test_get_global_info_clusters(self, mock_list_clusters, mock_boto3_client):
        """Test the get_global_info function with 'clusters' info_type."""
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
        register_module(MockMCP())

        # Get the captured function
        get_global_info_func = decorated_functions['get_global_info']
        assert get_global_info_func is not None, 'get_global_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the list_clusters function
        mock_list_clusters.return_value = {'ClusterInfoList': []}

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, info_type, kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_global_info_func(region=region, info_type=info_type, kwargs=kwargs)

        kwargs_dict = {
            'cluster_name_filter': 'test-cluster',
            'cluster_type_filter': 'PROVISIONED',
            'max_results': 20,
            'next_token': 'token',
        }

        result = wrapper_func(region='us-east-1', info_type='clusters', kwargs=kwargs_dict)

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_list_clusters.assert_called_once_with(
            mock_client,
            cluster_name_filter='test-cluster',
            cluster_type_filter='PROVISIONED',
            max_results=20,
            next_token='token',
        )

        assert result == {'ClusterInfoList': []}

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_global.list_configurations')
    def test_get_global_info_configurations(self, mock_list_configurations, mock_boto3_client):
        """Test the get_global_info function with 'configurations' info_type."""
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
        register_module(MockMCP())

        # Get the captured function
        get_global_info_func = decorated_functions['get_global_info']
        assert get_global_info_func is not None, 'get_global_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the list_configurations function
        mock_list_configurations.return_value = {'ConfigurationInfoList': []}

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, info_type, kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_global_info_func(region=region, info_type=info_type, kwargs=kwargs)

        kwargs_dict = {'max_results': 15, 'next_token': 'token'}

        result = wrapper_func(region='us-east-1', info_type='configurations', kwargs=kwargs_dict)

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_list_configurations.assert_called_once_with(
            mock_client, max_results=15, next_token='token'
        )

        assert result == {'ConfigurationInfoList': []}

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_global.list_vpc_connections')
    def test_get_global_info_vpc_connections(self, mock_list_vpc_connections, mock_boto3_client):
        """Test the get_global_info function with 'vpc_connections' info_type."""
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
        register_module(MockMCP())

        # Get the captured function
        get_global_info_func = decorated_functions['get_global_info']
        assert get_global_info_func is not None, 'get_global_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the list_vpc_connections function
        mock_list_vpc_connections.return_value = {'VpcConnectionInfoList': []}

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, info_type, kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_global_info_func(region=region, info_type=info_type, kwargs=kwargs)

        kwargs_dict = {'max_results': 25, 'next_token': 'token'}

        result = wrapper_func(region='us-east-1', info_type='vpc_connections', kwargs=kwargs_dict)

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_list_vpc_connections.assert_called_once_with(
            mock_client, max_results=25, next_token='token'
        )

        assert result == {'VpcConnectionInfoList': []}

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_global.list_kafka_versions')
    def test_get_global_info_kafka_versions(self, mock_list_kafka_versions, mock_boto3_client):
        """Test the get_global_info function with 'kafka_versions' info_type."""
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
        register_module(MockMCP())

        # Get the captured function
        get_global_info_func = decorated_functions['get_global_info']
        assert get_global_info_func is not None, 'get_global_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Mock the list_kafka_versions function
        mock_list_kafka_versions.return_value = {'KafkaVersions': ['2.8.1', '3.3.1']}

        # Act
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, info_type, kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_global_info_func(region=region, info_type=info_type, kwargs=kwargs)

        result = wrapper_func(region='us-east-1', info_type='kafka_versions')

        # Assert
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
        mock_list_kafka_versions.assert_called_once_with(mock_client)

        assert result == {'KafkaVersions': ['2.8.1', '3.3.1']}

    @patch('boto3.client')
    def test_get_global_info_invalid_type(self, mock_boto3_client):
        """Test the get_global_info function with an invalid info_type."""
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
        register_module(MockMCP())

        # Get the captured function
        get_global_info_func = decorated_functions['get_global_info']
        assert get_global_info_func is not None, 'get_global_info tool was not registered'

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Act & Assert
        # We need to modify the function to handle the kwargs parameter correctly
        # Create a wrapper function that converts the kwargs parameter to a dictionary
        def wrapper_func(region, info_type, kwargs=None):
            if kwargs is None:
                kwargs = {}
            return get_global_info_func(region=region, info_type=info_type, kwargs=kwargs)

        with pytest.raises(ValueError) as excinfo:
            wrapper_func(region='us-east-1', info_type='invalid_type')

        assert 'Unsupported info_type: invalid_type' in str(excinfo.value)
        mock_boto3_client.assert_called_once_with('kafka', region_name='us-east-1')
