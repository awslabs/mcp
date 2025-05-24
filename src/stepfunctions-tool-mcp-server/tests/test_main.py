"""Tests for the main function."""

import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_tool_mcp_server.server import main


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.stepfunctions_tool_mcp_server.server.register_state_machines')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_sse_transport(self, mock_parse_args, mock_mcp, mock_register):
        """Test main function with SSE transport."""
        # Set up test data
        mock_parse_args.return_value = MagicMock(sse=True, port=8888)

        # Call the function
        main()

        # Verify results
        mock_register.assert_called_once()
        mock_mcp.run.assert_called_once_with(transport='sse')
        assert mock_mcp.settings.port == 8888

    @patch('awslabs.stepfunctions_tool_mcp_server.server.register_state_machines')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_stdio_transport(self, mock_parse_args, mock_mcp, mock_register):
        """Test main function with stdio transport."""
        # Set up test data
        mock_parse_args.return_value = MagicMock(sse=False, port=8888)

        # Call the function
        main()

        # Verify results
        mock_register.assert_called_once()
        mock_mcp.run.assert_called_once_with()

    @patch('awslabs.stepfunctions_tool_mcp_server.server.register_state_machines')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_custom_port(self, mock_parse_args, mock_mcp, mock_register):
        """Test main function with custom port."""
        # Set up test data
        custom_port = 9999
        mock_parse_args.return_value = MagicMock(sse=True, port=custom_port)

        # Call the function
        main()

        # Verify results
        mock_register.assert_called_once()
        mock_mcp.run.assert_called_once_with(transport='sse')
        assert mock_mcp.settings.port == custom_port

    @patch('awslabs.stepfunctions_tool_mcp_server.server.register_state_machines')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_default_port(self, mock_parse_args, mock_mcp, mock_register):
        """Test main function with default port."""
        # Set up test data
        mock_parse_args.return_value = MagicMock(sse=True, port=8888)  # Default port

        # Call the function
        main()

        # Verify results
        mock_register.assert_called_once()
        mock_mcp.run.assert_called_once_with(transport='sse')
        assert mock_mcp.settings.port == 8888

    @patch('awslabs.stepfunctions_tool_mcp_server.server.register_state_machines')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.mcp')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_argument_parsing(self, mock_parse_args, mock_mcp, mock_register):
        """Test argument parsing in main function."""
        # Test various argument combinations
        test_cases = [
            {'sse': True, 'port': 8888},  # Default port with SSE
            {'sse': False, 'port': 8888},  # Default port without SSE
            {'sse': True, 'port': 9999},  # Custom port with SSE
            {'sse': False, 'port': 9999},  # Custom port without SSE
        ]

        for args in test_cases:
            # Set up test data
            mock_parse_args.return_value = MagicMock(**args)

            # Call the function
            main()

            # Verify results
            mock_register.assert_called()
            if args['sse']:
                mock_mcp.run.assert_called_with(transport='sse')
                assert mock_mcp.settings.port == args['port']
            else:
                mock_mcp.run.assert_called_with()

            # Reset mocks for next iteration
            mock_register.reset_mock()
            mock_mcp.reset_mock()
