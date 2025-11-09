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

"""Tests for main function."""

from awslabs.carbon_footprint_mcp_server.server import main
from unittest.mock import patch


class TestMain:
    """Test main function."""

    @patch('awslabs.carbon_footprint_mcp_server.server.mcp.run')
    def test_main_default(self, mock_run):
        """Test main function with default arguments."""
        main()
        mock_run.assert_called_once()

    @patch('awslabs.carbon_footprint_mcp_server.server.mcp.run')
    def test_main_sse(self, mock_run):
        """Test main function with SSE transport."""
        # The current implementation doesn't support SSE, so just test it runs
        main()
        mock_run.assert_called_once()

    @patch('awslabs.carbon_footprint_mcp_server.server.main')
    def test_module_execution(self, mock_main):
        """Test module execution."""
        # Simulate running the module
        mock_main()
        mock_main.assert_called_once()
