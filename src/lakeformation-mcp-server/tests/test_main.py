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

"""Tests for the main function in server.py."""

import inspect
from awslabs.lakeformation_mcp_server.server import main
from unittest.mock import patch


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.lakeformation_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.lakeformation-mcp-server'])
    def test_main_default(self, mock_run):
        """Test main function with default arguments."""
        main()
        mock_run.assert_called_once()

    def test_module_execution(self):
        """Test the module has the __main__ block."""
        from awslabs.lakeformation_mcp_server import server

        source = inspect.getsource(server)
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source
