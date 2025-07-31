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

"""Unit tests for the mutate_cluster register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.mutate_cluster.register_module import register_module
from unittest.mock import Mock, call


class TestMutateClusterRegisterModule(unittest.TestCase):
    """Tests for the mutate_cluster register_module."""

    def test_register_module(self):
        """Test that register_module registers the expected tools."""
        # Setup
        mock_mcp = Mock()
        mock_tool = Mock()
        mock_mcp.tool.return_value = mock_tool

        # Call the function
        register_module(mock_mcp)

        # Verify the correct tools were registered
        expected_tool_calls = [
            call(name='create_cluster'),
            call(name='update_broker_storage'),
            call(name='update_broker_type'),
            call(name='update_cluster_configuration'),
            call(name='update_monitoring'),
            call(name='update_security'),
            call(name='put_cluster_policy'),
            call(name='update_broker_count'),
            call(name='associate_scram_secret'),
            call(name='disassociate_scram_secret'),
            call(name='reboot_broker'),
        ]
        mock_mcp.tool.assert_has_calls(expected_tool_calls, any_order=True)
        self.assertEqual(mock_mcp.tool.call_count, len(expected_tool_calls))


if __name__ == '__main__':
    unittest.main()
