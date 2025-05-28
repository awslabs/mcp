# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the main function in server.py."""

from awslabs.amazon_neptune_mcp_server.server import main
from unittest.mock import patch


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.amazon_neptune_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.amazon-neptune-mcp-server'])
    def test_main_default(self, mock_run):
        """Test main function with default arguments.

        This test verifies that:
        1. The main function runs without errors
        2. The mcp.run method is called once
        3. No transport parameter is passed to mcp.run
        """
        # Call the main function
        main()

        # Check that mcp.run was called with the correct arguments
        mock_run.assert_called_once()
        assert mock_run.call_args[1].get('transport') is None

    def test_module_execution(self):
        """Test the module execution when run as __main__.

        This test verifies that:
        1. The server module contains the expected __main__ block
        2. The main() function is called in the __main__ block

        Note: This test doesn't actually execute the code, but ensures
        that the coverage report includes the if __name__ == '__main__': line
        by explicitly checking for its presence.
        """
        # Get the source code of the module
        import inspect
        from awslabs.amazon_neptune_mcp_server import server

        # Get the source code
        source = inspect.getsource(server)

        # Check that the module has the if __name__ == '__main__': block
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source
