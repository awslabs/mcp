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

"""Unit tests for the get_cluster_telemetry tool in logs_and_telemetry register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.register_module import register_module
from datetime import datetime, timezone
from unittest.mock import Mock


class TestGetClusterTelemetrySimple(unittest.TestCase):
    """Simple tests for the get_cluster_telemetry tool in logs_and_telemetry register_module."""

    def _extract_tool_function(self, mock_tool_decorator, index=0):
        """Helper method to extract a tool function from the mock decorator."""
        count = 0
        for args, kwargs in mock_tool_decorator.call_args_list:
            if len(args) > 0 and callable(args[0]):
                if count == index:
                    return args[0]
                count += 1
        return None

    def test_get_cluster_telemetry_metrics_action(self):
        """Test the get_cluster_telemetry function with metrics action."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Register the module
        register_module(mock_mcp)

        # Verify the tools were registered
        self.assertEqual(mock_mcp.tool.call_count, 2)
        self.assertEqual(mock_mcp.tool.call_args_list[0][1]['name'], 'get_cluster_telemetry')

        # Verify the tool decorator was called with functions
        self.assertEqual(mock_tool_decorator.call_count, 2)
        self.assertTrue(callable(mock_tool_decorator.call_args_list[0][0][0]))

    def test_get_cluster_telemetry_list_customer_iam_access_tool(self):
        """Test the list_customer_iam_access_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Register the module
        register_module(mock_mcp)

        # Verify the tool was registered twice (once for get_cluster_telemetry, once for list_customer_iam_access_tool)
        self.assertEqual(mock_mcp.tool.call_count, 2)

        # Verify the second tool registration was for list_customer_iam_access_tool
        self.assertEqual(mock_mcp.tool.call_args_list[1][1]['name'], 'list_customer_iam_access')

        # Verify the tool decorator was called with a function
        self.assertEqual(mock_tool_decorator.call_count, 2)
        self.assertTrue(callable(mock_tool_decorator.call_args_list[1][0][0]))

    def test_get_cluster_telemetry_invalid_action(self):
        """Test the get_cluster_telemetry function with an invalid action."""
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
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'

        # Call the function with an invalid action
        with self.assertRaises(ValueError) as context:
            get_cluster_telemetry(
                region=region, action='invalid_action', cluster_arn=cluster_arn, kwargs={}
            )
        self.assertEqual(
            str(context.exception),
            'Unsupported action or missing required arguments for invalid_action',
        )

    def test_get_cluster_telemetry_missing_required_params(self):
        """Test the get_cluster_telemetry function with missing required parameters."""
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
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'

        # Test cases for missing required parameters
        test_cases = [
            {
                'name': 'missing_start_time',
                'kwargs': {
                    'end_time': datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
                    'period': 300,
                    'metrics': ['BytesInPerSec'],
                },
                'expected_error': 'start_time is required for metrics action',
            },
            {
                'name': 'missing_end_time',
                'kwargs': {
                    'start_time': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                    'period': 300,
                    'metrics': ['BytesInPerSec'],
                },
                'expected_error': 'end_time is required for metrics action',
            },
            {
                'name': 'missing_period',
                'kwargs': {
                    'start_time': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                    'end_time': datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
                    'metrics': ['BytesInPerSec'],
                },
                'expected_error': 'period is required for metrics action',
            },
            {
                'name': 'missing_metrics',
                'kwargs': {
                    'start_time': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                    'end_time': datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
                    'period': 300,
                },
                'expected_error': 'metrics is required for metrics action',
            },
        ]

        # Run each test case
        for test_case in test_cases:
            with self.subTest(test_case['name']):
                with self.assertRaises(ValueError) as context:
                    get_cluster_telemetry(
                        region=region,
                        action='metrics',
                        cluster_arn=cluster_arn,
                        kwargs=test_case['kwargs'],
                    )
                self.assertEqual(str(context.exception), test_case['expected_error'])


if __name__ == '__main__':
    unittest.main()
