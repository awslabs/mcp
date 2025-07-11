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

"""Tests for the logs_and_telemetry module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry import register_module
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP
from typing import cast
from unittest.mock import MagicMock, patch


class TestLogsAndTelemetry:
    """Tests for the logs_and_telemetry module."""

    def test_register_module(self):
        """Test the register_module function."""
        # Arrange
        mock_mcp = MagicMock(spec=FastMCP)

        # Act
        register_module(mock_mcp)

        # Assert
        # Verify that the tool decorator was called twice (for get_cluster_telemetry and list_customer_iam_access)
        assert mock_mcp.tool.call_count == 2

        # Check that the tool names are correct
        tool_names = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
        assert 'get_cluster_telemetry' in tool_names
        assert 'list_customer_iam_access' in tool_names

    def test_register_module_with_spy(self):
        """Test the register_module function with a spy to capture the decorated functions."""
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

        # Act
        register_module(cast(FastMCP, MockMCP()))

        # Assert
        assert 'get_cluster_telemetry' in decorated_functions
        assert 'list_customer_iam_access' in decorated_functions

        # Now we can test the captured functions directly
        assert callable(decorated_functions['get_cluster_telemetry'])
        assert callable(decorated_functions['list_customer_iam_access'])

    def test_get_cluster_telemetry_metrics(self):
        """Test the get_cluster_telemetry function with metrics action."""
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
        get_cluster_telemetry = decorated_functions['get_cluster_telemetry']
        assert get_cluster_telemetry is not None, 'get_cluster_telemetry tool was not registered'

        # Set up mock response for get_cluster_metrics
        expected_response = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'GlobalTopicCount',
                    'Timestamps': [datetime.now() - timedelta(minutes=i * 5) for i in range(12)],
                    'Values': [10, 10, 10, 10, 12, 12, 12, 12, 12, 15, 15, 15],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Set up parameters for metrics action
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        period = 300  # 5 minutes
        metrics = ['GlobalTopicCount']

        # Mock all the necessary functions
        with (
            patch('awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.AWSClientManager'),
            patch(
                'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.get_cluster_metrics',
                return_value=expected_response,
            ) as mock_get_metrics,
        ):
            # Act
            result = get_cluster_telemetry(
                region=region,
                action='metrics',
                cluster_arn=cluster_arn,
                kwargs={
                    'start_time': start_time,
                    'end_time': end_time,
                    'period': period,
                    'metrics': metrics,
                },
            )

            # Assert
            mock_get_metrics.assert_called_once()
            assert result == expected_response

    def test_get_cluster_telemetry_available_metrics(self):
        """Test the get_cluster_telemetry function with available_metrics action."""
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
        get_cluster_telemetry = decorated_functions['get_cluster_telemetry']
        assert get_cluster_telemetry is not None, 'get_cluster_telemetry tool was not registered'

        # Set up mock response for list_available_metrics
        expected_metrics = {
            'GlobalTopicCount': {
                'monitoring_level': 'DEFAULT',
                'default_statistic': 'Average',
                'dimensions': ['Cluster Name'],
            },
            'BytesInPerSec': {
                'monitoring_level': 'PER_BROKER',
                'default_statistic': 'Sum',
                'dimensions': ['Cluster Name', 'Broker ID'],
            },
        }

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Mock all the necessary functions
        with (
            patch(
                'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.AWSClientManager'
            ) as mock_client_manager_class,
            patch(
                'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.list_available_metrics',
                return_value=expected_metrics,
            ) as mock_list_available_metrics,
        ):
            # Create a mock client manager and kafka client
            mock_client_manager = MagicMock()
            mock_client_manager_class.return_value = mock_client_manager

            mock_kafka_client = MagicMock()
            mock_client_manager.get_client.return_value = mock_kafka_client

            # Mock the response from describe_cluster
            mock_kafka_client.describe_cluster.return_value = {
                'ClusterInfo': {'EnhancedMonitoring': 'PER_BROKER'}
            }

            # Act
            result = get_cluster_telemetry(
                region=region, action='available_metrics', cluster_arn=cluster_arn, kwargs={}
            )

            # Assert
            mock_list_available_metrics.assert_called_once_with(monitoring_level='PER_BROKER')
            assert result == expected_metrics

    def test_get_cluster_telemetry_missing_required_parameters(self):
        """Test the get_cluster_telemetry function with missing required parameters."""
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
        get_cluster_telemetry = decorated_functions['get_cluster_telemetry']
        assert get_cluster_telemetry is not None, 'get_cluster_telemetry tool was not registered'

        # Act & Assert - Missing start_time
        with pytest.raises(ValueError) as excinfo:
            get_cluster_telemetry(
                region='us-east-1',
                action='metrics',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                kwargs={
                    'end_time': datetime.now(),
                    'period': 300,
                    'metrics': ['GlobalTopicCount'],
                },
            )
        assert 'start_time is required for metrics action' in str(excinfo.value)

        # Act & Assert - Missing end_time
        with pytest.raises(ValueError) as excinfo:
            get_cluster_telemetry(
                region='us-east-1',
                action='metrics',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                kwargs={
                    'start_time': datetime.now() - timedelta(hours=1),
                    'period': 300,
                    'metrics': ['GlobalTopicCount'],
                },
            )
        assert 'end_time is required for metrics action' in str(excinfo.value)

        # Act & Assert - Missing period
        with pytest.raises(ValueError) as excinfo:
            get_cluster_telemetry(
                region='us-east-1',
                action='metrics',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                kwargs={
                    'start_time': datetime.now() - timedelta(hours=1),
                    'end_time': datetime.now(),
                    'metrics': ['GlobalTopicCount'],
                },
            )
        assert 'period is required for metrics action' in str(excinfo.value)

        # Act & Assert - Missing metrics
        with pytest.raises(ValueError) as excinfo:
            get_cluster_telemetry(
                region='us-east-1',
                action='metrics',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                kwargs={
                    'start_time': datetime.now() - timedelta(hours=1),
                    'end_time': datetime.now(),
                    'period': 300,
                },
            )
        assert 'metrics is required for metrics action' in str(excinfo.value)

    def test_get_cluster_telemetry_invalid_action(self):
        """Test the get_cluster_telemetry function with an invalid action."""
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
        get_cluster_telemetry = decorated_functions['get_cluster_telemetry']
        assert get_cluster_telemetry is not None, 'get_cluster_telemetry tool was not registered'

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            get_cluster_telemetry(
                region='us-east-1',
                action='invalid_action',
                cluster_arn='arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                kwargs={},
            )
        assert 'Unsupported action or missing required arguments for invalid_action' in str(
            excinfo.value
        )

    def test_get_cluster_telemetry_available_metrics_missing_cluster_arn(self):
        """Test the get_cluster_telemetry function with available_metrics action and missing cluster ARN."""
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
        get_cluster_telemetry = decorated_functions['get_cluster_telemetry']
        assert get_cluster_telemetry is not None, 'get_cluster_telemetry tool was not registered'

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            get_cluster_telemetry(
                region='us-east-1', action='available_metrics', cluster_arn=None, kwargs={}
            )
        assert 'Cluster ARN must be provided to determine monitoring level' in str(excinfo.value)

    def test_list_customer_iam_access_tool(self):
        """Test the list_customer_iam_access_tool function."""
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
        list_customer_iam_access_tool = decorated_functions['list_customer_iam_access']
        assert list_customer_iam_access_tool is not None, (
            'list_customer_iam_access tool was not registered'
        )

        # Set up expected response
        expected_response = {
            'cluster_info': {
                'cluster_arn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
                'cluster_name': 'test-cluster',
                'iam_auth_enabled': True,
            },
            'resource_policies': ['test-policy'],
            'matching_policies': {
                'arn:aws:iam::123456789012:policy/TestPolicy': {
                    'PolicyName': 'TestPolicy',
                    'Statement': {
                        'Effect': 'Allow',
                        'Action': ['kafka:GetBootstrapBrokers', 'kafka:DescribeCluster'],
                        'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/*',
                    },
                    'ResourceType': 'cluster_wildcard',
                    'AttachedRoles': [],
                    'PolicyRoles': [{'RoleName': 'TestRole', 'RoleId': 'AROAEXAMPLEID'}],
                }
            },
        }

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Mock the list_customer_iam_access function
        with patch(
            'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.list_customer_iam_access',
            return_value=expected_response,
        ) as mock_list_customer_iam_access:
            # Act
            result = list_customer_iam_access_tool(region=region, cluster_arn=cluster_arn)

            # Assert
            mock_list_customer_iam_access.assert_called_once()
            assert result == expected_response

    def test_list_customer_iam_access_tool_with_error(self):
        """Test the list_customer_iam_access_tool function when an error occurs."""
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
        list_customer_iam_access_tool = decorated_functions['list_customer_iam_access']
        assert list_customer_iam_access_tool is not None, (
            'list_customer_iam_access tool was not registered'
        )

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'invalid-arn'  # Invalid ARN to trigger an error

        # Mock the list_customer_iam_access function to raise an error
        with patch(
            'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.list_customer_iam_access',
            side_effect=ValueError('cluster_arn must be a valid MSK cluster ARN'),
        ) as mock_list_customer_iam_access:
            # Act & Assert
            with pytest.raises(ValueError) as excinfo:
                list_customer_iam_access_tool(region=region, cluster_arn=cluster_arn)

            # Verify the error
            assert 'cluster_arn must be a valid MSK cluster ARN' in str(excinfo.value)
            mock_list_customer_iam_access.assert_called_once()
