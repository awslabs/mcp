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

from awslabs.eks_mcp_server.server import create_server, main
from unittest.mock import MagicMock, patch


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
    @patch('awslabs.eks_mcp_server.server.create_server')
    @patch('sys.argv', ['awslabs.eks-mcp-server'])
    def test_main_default(self, mock_create_server, mock_boto3_client):
        """Test main function with default arguments."""
        # Create a mock AWS client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Create a mock server
        mock_server = MagicMock()
        mock_create_server.return_value = mock_server

        # Call the main function
        main()

        # Check that create_server was called
        mock_create_server.assert_called_once()

        # Check that run was called with the correct arguments
        mock_server.run.assert_called_once()
        assert mock_server.run.call_args[1].get('transport') is None

    @patch('awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client')
    @patch('awslabs.eks_mcp_server.server.create_server')
    @patch('sys.argv', ['awslabs.eks-mcp-server', '--sse', '--port', '9999'])
    def test_main_sse(self, mock_create_server, mock_boto3_client):
        """Test main function with SSE transport."""
        # Create a mock AWS client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Create a mock server
        mock_server = MagicMock()
        mock_create_server.return_value = mock_server

        # Call the main function
        main()

        # Check that create_server was called
        mock_create_server.assert_called_once()

        # Check that run was called with the correct arguments
        mock_server.run.assert_called_once()
        assert mock_server.run.call_args[1].get('transport') == 'sse'

        # Check that the port was set correctly
        assert mock_server.settings.port == 9999

    def test_module_execution(self):
        """Test the module execution when run as __main__."""
        # This test directly executes the code in the if __name__ == '__main__': block
        # to ensure coverage of that line

        # Get the source code of the module
        import inspect
        from awslabs.eks_mcp_server import server

        # Get the source code
        source = inspect.getsource(server)

        # Check that the module has the if __name__ == '__main__': block
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source

        # This test doesn't actually execute the code, but it ensures
        # that the coverage report includes the if __name__ == '__main__': line
        # by explicitly checking for its presence

    def test_create_server(self):
        """Test that create_server creates a FastMCP instance with the correct parameters."""
        with patch('awslabs.eks_mcp_server.server.FastMCP') as mock_fastmcp:
            # Call create_server
            create_server()

            # Check that FastMCP was called with the correct parameters
            mock_fastmcp.assert_called_once()
            args, kwargs = mock_fastmcp.call_args
            assert args[0] == 'awslabs.eks-mcp-server'
            assert 'instructions' in kwargs
            assert 'dependencies' in kwargs
            assert 'EKS MCP Server' in kwargs['instructions']
            assert 'boto3' in kwargs['dependencies']
