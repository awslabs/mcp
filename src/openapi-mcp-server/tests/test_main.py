"""Tests for the OpenAPI MCP Server main function."""

from awslabs.openapi_mcp_server.server import main
from unittest.mock import MagicMock, patch


@patch('awslabs.openapi_mcp_server.server.create_mcp_server')
@patch('awslabs.openapi_mcp_server.server.load_config')
@patch('awslabs.openapi_mcp_server.server.argparse.ArgumentParser.parse_args')
def test_main_function(mock_parse_args, mock_load_config, mock_create_mcp_server):
    """Test the main function."""
    # Setup mocks
    mock_args = MagicMock()
    # Properly set log_level to a string value to avoid TypeError
    mock_args.log_level = 'INFO'
    mock_parse_args.return_value = mock_args

    mock_config = MagicMock()
    mock_config.transport = 'sse'
    mock_config.port = 8888
    mock_load_config.return_value = mock_config

    mock_server = MagicMock()
    mock_create_mcp_server.return_value = mock_server

    # Call main
    main()

    # Assert
    mock_parse_args.assert_called_once()
    mock_load_config.assert_called_once_with(mock_args)
    mock_create_mcp_server.assert_called_once_with(mock_config)
    mock_server.run.assert_called_once()


@patch('awslabs.openapi_mcp_server.server.create_mcp_server')
@patch('awslabs.openapi_mcp_server.server.load_config')
@patch('awslabs.openapi_mcp_server.server.argparse.ArgumentParser.parse_args')
def test_main_function_stdio(mock_parse_args, mock_load_config, mock_create_mcp_server):
    """Test the main function with stdio transport."""
    # Setup mocks
    mock_args = MagicMock()
    # Properly set log_level to a string value to avoid TypeError
    mock_args.log_level = 'INFO'
    mock_parse_args.return_value = mock_args

    mock_config = MagicMock()
    mock_config.transport = 'stdio'
    mock_load_config.return_value = mock_config

    mock_server = MagicMock()
    mock_create_mcp_server.return_value = mock_server

    # Call main
    main()

    # Assert
    mock_server.run.assert_called_once_with()
