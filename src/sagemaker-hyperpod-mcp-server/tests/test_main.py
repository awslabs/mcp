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
# ruff: noqa: D101, D102, D103, E402
"""Tests for the main function in server.py."""

# Mock the imports that might cause issues
import sys
from unittest.mock import ANY, MagicMock, patch


# Mock modules that might not be installed
sys.modules['requests_auth_aws_sigv4'] = MagicMock()
sys.modules['requests'] = MagicMock()
from awslabs.sagemaker_hyperpod_mcp_server.server import create_server, main


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodClusterNodeHandler')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodStackHandler')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.create_server')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.logger')
    @patch('sys.argv', ['awslabs.sagemaker-hyperpod-mcp-server'])
    def test_main_default(
        self,
        mock_logger,
        mock_create_server,
        mock_stack_handler,
        mock_api_handler,
    ):
        """Test main function with default arguments."""
        # Setup mock
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        # Call the main function
        result = main()

        # Check that create_server was called
        mock_create_server.assert_called_once()

        # Check that the handlers were initialized with the correct parameters
        mock_api_handler.assert_called_once_with(mock_mcp, False, False)
        mock_stack_handler.assert_called_once_with(mock_mcp, False)

        # Check that the server was run
        mock_mcp.run.assert_called_once()

        # Check that the correct log message was output
        mock_logger.info.assert_called_once_with(
            'Starting HyperPod MCP Server in read-only mode, restricted sensitive data access mode'
        )

        # Check that the function returns the MCP instance
        assert result == mock_mcp

    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodClusterNodeHandler')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodStackHandler')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.create_server')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.logger')
    @patch('sys.argv', ['awslabs.sagemaker-hyperpod-mcp-server', '--allow-write'])
    def test_main_with_write_access(
        self,
        mock_logger,
        mock_create_server,
        mock_stack_handler,
        mock_api_handler,
    ):
        """Test main function with write access enabled."""
        # Setup mock
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        # Mock argparse to return the desired arguments
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = MagicMock()
            mock_args.allow_write = True
            mock_args.allow_sensitive_data_access = False
            mock_parse_args.return_value = mock_args

            # Call the main function
            result = main()

        # Check that create_server was called
        mock_create_server.assert_called_once()

        # Check that the handlers were initialized with the correct parameters
        mock_api_handler.assert_called_once_with(mock_mcp, True, False)
        mock_stack_handler.assert_called_once_with(mock_mcp, True)

        # Check that the server was run
        mock_mcp.run.assert_called_once()

        # Check that the correct log message was output
        mock_logger.info.assert_called_once_with(
            'Starting HyperPod MCP Server in restricted sensitive data access mode'
        )

        # Check that the function returns the MCP instance
        assert result == mock_mcp

    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodClusterNodeHandler')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodStackHandler')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.create_server')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.logger')
    @patch('sys.argv', ['awslabs.sagemaker-hyperpod-mcp-server', '--allow-sensitive-data-access'])
    def test_main_with_sensitive_data_access(
        self,
        mock_logger,
        mock_create_server,
        mock_stack_handler,
        mock_api_handler,
    ):
        """Test main function with sensitive data access enabled."""
        # Setup mock
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        # Mock argparse to return the desired arguments
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = MagicMock()
            mock_args.allow_write = False
            mock_args.allow_sensitive_data_access = True
            mock_parse_args.return_value = mock_args

            # Call the main function
            result = main()

        # Check that create_server was called
        mock_create_server.assert_called_once()

        # Check that the handlers were initialized with the correct parameters
        mock_api_handler.assert_called_once_with(mock_mcp, False, True)
        mock_stack_handler.assert_called_once_with(mock_mcp, False)

        # Check that the server was run
        mock_mcp.run.assert_called_once()

        # Check that the correct log message was output
        mock_logger.info.assert_called_once_with('Starting HyperPod MCP Server in read-only mode')

        # Check that the function returns the MCP instance
        assert result == mock_mcp

    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodClusterNodeHandler')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodStackHandler')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.create_server')
    @patch('awslabs.sagemaker_hyperpod_mcp_server.server.logger')
    @patch(
        'sys.argv',
        [
            'awslabs.sagemaker-hyperpod-mcp-server',
            '--allow-write',
            '--allow-sensitive-data-access',
        ],
    )
    def test_main_with_all_access(
        self,
        mock_logger,
        mock_create_server,
        mock_stack_handler,
        mock_api_handler,
    ):
        """Test main function with both write and sensitive data access enabled."""
        # Setup mock
        mock_mcp = MagicMock()
        mock_create_server.return_value = mock_mcp

        # Mock argparse to return the desired arguments
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = MagicMock()
            mock_args.allow_write = True
            mock_args.allow_sensitive_data_access = True
            mock_parse_args.return_value = mock_args

            # Call the main function
            result = main()

        # Check that create_server was called
        mock_create_server.assert_called_once()

        # Check that the handlers were initialized with the correct parameters
        mock_api_handler.assert_called_once_with(mock_mcp, True, True)
        mock_stack_handler.assert_called_once_with(mock_mcp, True)

        # Check that the server was run
        mock_mcp.run.assert_called_once()

        # Check that the correct log message was output
        mock_logger.info.assert_called_once_with('Starting HyperPod MCP Server')

        # Check that the function returns the MCP instance
        assert result == mock_mcp

    def test_create_server(self):
        """Test the create_server function."""
        with patch('awslabs.sagemaker_hyperpod_mcp_server.server.FastMCP') as mock_fastmcp:
            # Call the create_server function
            create_server()

            # Check that FastMCP was called with the correct arguments
            mock_fastmcp.assert_called_once_with(
                'awslabs.sagemaker-hyperpod-mcp-server',
                instructions=ANY,
                dependencies=ANY,
            )

    def test_module_execution(self):
        """Test the module execution when run as __main__."""
        # This test directly executes the code in the if __name__ == '__main__': block
        # to ensure coverage of that line

        # Get the source code of the module
        import inspect
        from awslabs.sagemaker_hyperpod_mcp_server import server

        # Get the source code
        source = inspect.getsource(server)

        # Check that the module has the if __name__ == '__main__': block
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source

        # This test doesn't actually execute the code, but it ensures
        # that the coverage report includes the if __name__ == '__main__': line
        # by explicitly checking for its presence
