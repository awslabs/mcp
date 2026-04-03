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

from awslabs.s3_tables_mcp_server.server import app, main
from unittest.mock import patch


class TestMain:
    """Test cases for the main function."""

    def test_main_default(self):
        """Test main function with default arguments."""
        with (
            patch('sys.argv', ['server.py']),
            patch('awslabs.s3_tables_mcp_server.server.app.run') as mock_run,
        ):
            main()
            mock_run.assert_called_once()
            assert app.allow_write is False

    def test_main_with_write_permission(self):
        """Test main function with --allow-write argument."""
        with (
            patch('sys.argv', ['server.py', '--allow-write']),
            patch('awslabs.s3_tables_mcp_server.server.app.run') as mock_run,
        ):
            main()
            mock_run.assert_called_once()
            assert app.allow_write is True

    def test_main_with_exception(self):
        """Test main function when an exception occurs."""
        with (
            patch('sys.argv', ['server.py']),
            patch(
                'awslabs.s3_tables_mcp_server.server.app.run', side_effect=Exception('Test error')
            ),
        ):
            try:
                main()
            except Exception:
                pass  # Expected exception
            # The test should not fail due to the exception being raised

    def test_module_execution(self):
        """Test the module execution when run as __main__."""
        # Get the source code of the module
        import inspect
        from awslabs.s3_tables_mcp_server import server

        # Get the source code
        source = inspect.getsource(server)

        # Check that the module has the if __name__ == "__main__": block
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source
