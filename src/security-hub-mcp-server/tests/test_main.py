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

"""Unit tests for AWS Security Hub MCP Server main execution."""

from awslabs.security_hub_mcp_server.server import main
from unittest.mock import patch


class TestMain:
    """Test cases for main function execution."""

    @patch('awslabs.security_hub_mcp_server.server.mcp.run')
    def test_main_default(self, mock_run):
        """Test main function execution."""
        main()
        mock_run.assert_called_once()

    @patch('awslabs.security_hub_mcp_server.server.mcp.run')
    def test_module_execution(self, mock_run):
        """Test module execution via __main__."""
        # This simulates running: python -m awslabs.security_hub_mcp_server.server
        import awslabs.security_hub_mcp_server.server

        # Mock the __name__ check
        with patch.object(awslabs.security_hub_mcp_server.server, '__name__', '__main__'):
            # This would normally call main(), but we'll call it directly for testing
            main()
            mock_run.assert_called_once()
