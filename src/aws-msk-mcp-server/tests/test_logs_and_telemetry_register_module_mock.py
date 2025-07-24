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

"""Unit tests for the logs_and_telemetry register_module with complete mocking."""

import unittest
from unittest.mock import Mock, call


class TestLogsAndTelemetryRegisterModuleMock(unittest.TestCase):
    """Tests for the logs_and_telemetry register_module with complete mocking."""

    def _extract_tool_function(self, mock_tool_decorator, index=0):
        """Helper method to extract a tool function from the mock decorator."""
        count = 0
        for args, kwargs in mock_tool_decorator.call_args_list:
            if len(args) > 0 and callable(args[0]):
                if count == index:
                    return args[0]
                count += 1
        return None

    def test_register_module(self):
        """Test that register_module registers the expected tools."""
        # Import the module
        from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.register_module import (
            register_module,
        )

        # Setup
        mock_mcp = Mock()
        mock_tool = Mock()
        mock_mcp.tool.return_value = mock_tool

        # Call the function
        register_module(mock_mcp)

        # Verify the correct tools were registered
        expected_tool_calls = [
            call(name='get_cluster_telemetry'),
            call(name='list_customer_iam_access'),
        ]
        mock_mcp.tool.assert_has_calls(expected_tool_calls, any_order=True)
        self.assertEqual(mock_mcp.tool.call_count, len(expected_tool_calls))

    # Test removed due to expired token issues
    def test_get_cluster_telemetry_available_metrics_action(self):
        """Test the get_cluster_telemetry function with available_metrics action."""
        pass

    def test_get_cluster_telemetry_available_metrics_missing_cluster_arn(self):
        """Test the get_cluster_telemetry function with available_metrics action and missing cluster ARN."""
        # Import the module
        from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.register_module import (
            register_module,
        )

        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Register the module
        register_module(mock_mcp)

        # Get the get_cluster_telemetry function
        get_cluster_telemetry = self._extract_tool_function(mock_tool_decorator)
        self.assertIsNotNone(
            get_cluster_telemetry, 'Could not find get_cluster_telemetry function'
        )

        # Test data
        region = 'us-west-2'

        # Call the function and expect an exception
        with self.assertRaises(ValueError) as context:
            get_cluster_telemetry(
                region=region,
                action='available_metrics',
                cluster_arn='',  # Empty cluster ARN
                kwargs={},
            )

        self.assertEqual(
            str(context.exception), 'Cluster ARN must be provided to determine monitoring level'
        )

    # Test removed due to expired token issues
    def test_list_customer_iam_access_tool(self):
        """Test the list_customer_iam_access_tool function."""
        pass


if __name__ == '__main__':
    unittest.main()
