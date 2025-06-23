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

"""Tests for the static_tools/__init__.py module."""

from awslabs.aws_msk_mcp_server.tools.static_tools import register_module
from unittest.mock import MagicMock, patch


class TestStaticToolsInit:
    """Tests for the static_tools/__init__.py module."""

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
        mock_mcp.tool.assert_any_call(name='get_cluster_best_practices')

    @patch('awslabs.aws_msk_mcp_server.tools.static_tools.get_cluster_best_practices')
    def test_get_cluster_best_practices_tool(self, mock_get_cluster_best_practices):
        """Test the get_cluster_best_practices_tool function."""
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
        get_cluster_best_practices_func = decorated_functions['get_cluster_best_practices']
        assert get_cluster_best_practices_func is not None, (
            'get_cluster_best_practices tool was not registered'
        )

        # Mock the get_cluster_best_practices function
        expected_response = {
            'Instance Type': 'kafka.m5.large (provided as input)',
            'Number of Brokers': '3 (provided as input)',
            'vCPU per Broker': 2,
            'Memory (GB) per Broker': '8 (available on the host)',
            'Network Bandwidth (Gbps) per Broker': '10.0 (available on the host)',
            'Ingress Throughput Recommended (MBps)': '4.8 (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)',
            'Ingress Throughput Max (MBps)': '7.2 (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)',
            'Egress Throughput Recommended (MBps)': '9.6 (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)',
            'Egress Throughput Max (MBps)': '18.0 (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)',
            'Recommended Partitions per Broker': 1000,
            'Max Partitions per Broker': '1500 (Note: Each partition should be 3-way replicated. For example, 1000 total partitions with three brokers will mean each broker has 1000 partitions.)',
            'Recommended Max Partitions per Cluster': 3000,
            'Max Partitions per Cluster': 4500,
            'CPU Utilization Guidelines': 'Keep below 60% regularly; never exceed 70%.',
            'Disk Utilization Guidelines': 'Warning at 85%, critical at 90%.',
            'Replication Factor': '3 (recommended)',
            'Minimum In-Sync Replicas': 2,
            'Under-Replicated Partitions Tolerance': 0,
            'Leader Imbalance Tolerance (%)': 10,
        }
        mock_get_cluster_best_practices.return_value = expected_response

        # Act
        instance_type = 'kafka.m5.large'
        number_of_brokers = 3

        result = get_cluster_best_practices_func(
            instance_type=instance_type, number_of_brokers=number_of_brokers
        )

        # Assert
        mock_get_cluster_best_practices.assert_called_once_with(instance_type, number_of_brokers)
        assert result == expected_response

    @patch('awslabs.aws_msk_mcp_server.tools.static_tools.get_cluster_best_practices')
    def test_get_cluster_best_practices_tool_express_instance(
        self, mock_get_cluster_best_practices
    ):
        """Test the get_cluster_best_practices_tool function with an express instance type."""
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
        get_cluster_best_practices_func = decorated_functions['get_cluster_best_practices']
        assert get_cluster_best_practices_func is not None, (
            'get_cluster_best_practices tool was not registered'
        )

        # Mock the get_cluster_best_practices function
        expected_response = {
            'Instance Type': 'express.m7g.large (provided as input)',
            'Number of Brokers': '3 (provided as input)',
            'vCPU per Broker': 2,
            'Memory (GB) per Broker': '8 (available on the host)',
            'Network Bandwidth (Gbps) per Broker': '12.5 (available on the host)',
            'Ingress Throughput Recommended (MBps)': '15.6 (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)',
            'Ingress Throughput Max (MBps)': '23.4 (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)',
            'Egress Throughput Recommended (MBps)': '31.2 (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)',
            'Egress Throughput Max (MBps)': '58.5 (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)',
            'Recommended Partitions per Broker': 1000,
            'Max Partitions per Broker': '1500 (Note: Each partition should be 3-way replicated. For example, 1000 total partitions with three brokers will mean each broker has 1000 partitions.)',
            'Recommended Max Partitions per Cluster': 3000,
            'Max Partitions per Cluster': 4500,
            'CPU Utilization Guidelines': 'Keep below 60% regularly; never exceed 70%.',
            'Disk Utilization Guidelines': 'Warning at 85%, critical at 90%.',
            'Replication Factor': '3 (Note: For express clusters, replication factor should always be 3)',
            'Minimum In-Sync Replicas': 2,
            'Under-Replicated Partitions Tolerance': 0,
            'Leader Imbalance Tolerance (%)': 10,
        }
        mock_get_cluster_best_practices.return_value = expected_response

        # Act
        instance_type = 'express.m7g.large'
        number_of_brokers = 3

        result = get_cluster_best_practices_func(
            instance_type=instance_type, number_of_brokers=number_of_brokers
        )

        # Assert
        mock_get_cluster_best_practices.assert_called_once_with(instance_type, number_of_brokers)
        assert result == expected_response

    @patch('awslabs.aws_msk_mcp_server.tools.static_tools.get_cluster_best_practices')
    def test_get_cluster_best_practices_tool_invalid_instance(
        self, mock_get_cluster_best_practices
    ):
        """Test the get_cluster_best_practices_tool function with an invalid instance type."""
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
        get_cluster_best_practices_func = decorated_functions['get_cluster_best_practices']
        assert get_cluster_best_practices_func is not None, (
            'get_cluster_best_practices tool was not registered'
        )

        # Mock the get_cluster_best_practices function
        expected_response = {
            'Error': "Instance type 'invalid.instance' is not supported or recognized."
        }
        mock_get_cluster_best_practices.return_value = expected_response

        # Act
        instance_type = 'invalid.instance'
        number_of_brokers = 3

        result = get_cluster_best_practices_func(
            instance_type=instance_type, number_of_brokers=number_of_brokers
        )

        # Assert
        mock_get_cluster_best_practices.assert_called_once_with(instance_type, number_of_brokers)
        assert result == expected_response
        assert 'Error' in result
        assert (
            "Instance type 'invalid.instance' is not supported or recognized." in result['Error']
        )
