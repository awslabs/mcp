"""Tests to boost coverage for server.py."""

import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.server import (
    create_mcp_server,
    setup_signal_handlers,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestServerCoverageBoost:
    """Tests to boost coverage for server.py."""

    @pytest.fixture
    def mock_fastmcp(self):
        """Create a mock FastMCP instance."""
        server = MagicMock()
        server.start = AsyncMock()
        server.stop = AsyncMock()
        server.register_tool = AsyncMock()
        server.register_resource = AsyncMock()
        return server

    @pytest.fixture
    def mock_prompt_manager(self):
        """Create a mock prompt manager."""
        manager = MagicMock()
        manager.generate_prompts = AsyncMock()
        manager.register_api_tool_handler = AsyncMock()
        manager.register_api_resource_handler = AsyncMock()
        return manager

    @patch('signal.signal')
    def test_setup_signal_handlers(self, mock_signal):
        """Test setup_signal_handlers function."""
        # Call setup_signal_handlers
        setup_signal_handlers()

        # Verify signal handlers were set up
        mock_signal.assert_called()

    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    def test_create_mcp_server_basic(self, mock_fastmcp):
        """Test create_mcp_server function with basic configuration."""
        # Create a mock config
        mock_config = MagicMock(spec=Config)
        mock_config.api_name = 'Test API'
        mock_config.api_spec_url = None
        mock_config.api_spec_path = None
        mock_config.api_base_url = None
        mock_config.auth_type = 'none'
        mock_config.server_name = 'Test Server'
        mock_config.debug = True
        mock_config.message_timeout = 30
        mock_config.host = 'localhost'
        mock_config.port = 8000
        mock_config.transport = 'stdio'

        # Mock FastMCP instance
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server

        # Call create_mcp_server with patched sys.exit to avoid actual exit
        with patch('sys.exit'):
            create_mcp_server(mock_config)

        # Verify FastMCP was created
        mock_fastmcp.assert_called_once()
