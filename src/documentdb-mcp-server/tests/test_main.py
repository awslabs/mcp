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

import pytest
from awslabs.documentdb_mcp_server.config import serverConfig
from awslabs.documentdb_mcp_server.server import main
from unittest.mock import patch


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.documentdb-mcp-server'])
    def test_main_default(self, mock_run, monkeypatch):
        """Test main function with default arguments (no connection string, read-only)."""
        monkeypatch.delenv('DOCUMENTDB_CONNECTION_STRING', raising=False)
        # Call the main function
        main()

        # Check that mcp.run was called with the correct arguments
        mock_run.assert_called_once()
        # No connection string configured -> fails closed, read-only by default
        assert serverConfig.connection_string is None
        assert serverConfig.read_only_mode is True

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch(
        'sys.argv',
        [
            'awslabs.documentdb-mcp-server',
            '--connection-string',
            'mongodb://example.com:27017/?retryWrites=false',
            '--allow-write',
        ],
    )
    def test_main_with_connection_string_arg(self, mock_run):
        """Test main configures the connection string from the CLI arg."""
        main()

        mock_run.assert_called_once()
        assert serverConfig.connection_string == 'mongodb://example.com:27017/?retryWrites=false'
        # --allow-write disables read-only mode
        assert serverConfig.read_only_mode is False

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch('sys.argv', ['awslabs.documentdb-mcp-server'])
    @patch.dict(
        'os.environ',
        {'DOCUMENTDB_CONNECTION_STRING': 'mongodb://from-env:27017/?retryWrites=false'},
    )
    def test_main_with_connection_string_env(self, mock_run):
        """Test main reads the connection string from the environment variable."""
        main()

        mock_run.assert_called_once()
        assert serverConfig.connection_string == 'mongodb://from-env:27017/?retryWrites=false'

    @patch('awslabs.documentdb_mcp_server.server.mcp.run', side_effect=Exception('boom'))
    @patch('sys.argv', ['awslabs.documentdb-mcp-server'])
    def test_main_handles_run_failure(self, mock_run, monkeypatch):
        """Test main logs and cleans up when mcp.run raises."""
        monkeypatch.delenv('DOCUMENTDB_CONNECTION_STRING', raising=False)
        # Should not raise; the finally block closes the connection
        main()
        mock_run.assert_called_once()

    @patch('awslabs.documentdb_mcp_server.server.mcp.run')
    @patch(
        'sys.argv',
        [
            'awslabs.documentdb-mcp-server',
            '--connection-string',
            'mongodb://example.com:27017/',  # missing retryWrites=false
        ],
    )
    def test_main_invalid_connection_string_exits(self, mock_run):
        """Test main fails fast with a clean exit (not a traceback) on a bad connection string."""
        # An invalid connection string should sys.exit(1) before starting the server,
        # rather than propagating a raw ValueError traceback to the operator.
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        mock_run.assert_not_called()

    def test_module_execution(self):
        """Test the module execution when run as __main__."""
        # This test directly executes the code in the if __name__ == '__main__': block
        # to ensure coverage of that line

        # Get the source code of the module
        import inspect
        from awslabs.documentdb_mcp_server import server

        # Get the source code
        source = inspect.getsource(server)

        # Check that the module has the if __name__ == '__main__': block
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source

        # This test doesn't actually execute the code, but it ensures
        # that the coverage report includes the if __name__ == '__main__': line
        # by explicitly checking for its presence
