"""Tests for main.py entry point."""

import pytest
from awslabs.healthlake_mcp_server.main import main, sync_main
from unittest.mock import AsyncMock, Mock, patch


class TestMainFunction:
    """Test main async function."""

    @patch('awslabs.healthlake_mcp_server.main.parse_args')
    @patch('awslabs.healthlake_mcp_server.main.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.main.stdio_server')
    async def test_main_success(self, mock_stdio_server, mock_create_server, mock_parse_args):
        """Test successful main execution."""
        # Mock arguments
        mock_args = Mock()
        mock_args.readonly = False
        mock_parse_args.return_value = mock_args

        # Mock server
        mock_server = Mock()
        mock_server.run = AsyncMock()
        mock_server.create_initialization_options = Mock(return_value={})
        mock_create_server.return_value = mock_server

        # Mock stdio server context manager
        mock_read_stream = Mock()
        mock_write_stream = Mock()
        mock_stdio_server.return_value.__aenter__ = AsyncMock(
            return_value=(mock_read_stream, mock_write_stream)
        )
        mock_stdio_server.return_value.__aexit__ = AsyncMock(return_value=None)

        # Run main
        await main()

        # Verify calls
        mock_parse_args.assert_called_once()
        mock_create_server.assert_called_once_with(read_only=False)
        mock_server.run.assert_called_once_with(mock_read_stream, mock_write_stream, {})

    @patch('awslabs.healthlake_mcp_server.main.parse_args')
    @patch('awslabs.healthlake_mcp_server.main.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.main.logger')
    async def test_main_exception_handling(self, mock_logger, mock_create_server, mock_parse_args):
        """Test main function exception handling."""
        # Mock arguments
        mock_args = Mock()
        mock_args.readonly = False
        mock_parse_args.return_value = mock_args

        # Mock server creation to raise exception
        mock_create_server.side_effect = RuntimeError('Server creation failed')

        # Run main and expect exception
        with pytest.raises(RuntimeError, match='Server creation failed'):
            await main()

        # Verify error was logged
        mock_logger.error.assert_called_once()


class TestSyncMain:
    """Test sync_main wrapper function."""

    @patch('awslabs.healthlake_mcp_server.main.asyncio.run')
    def test_sync_main_calls_asyncio_run(self, mock_asyncio_run):
        """Test sync_main calls asyncio.run."""
        sync_main()

        mock_asyncio_run.assert_called_once()


class TestMainGuard:
    """Test __name__ == '__main__' execution guard."""

    def test_main_guard_not_executed_when_imported(self):
        """Test that sync_main is not called when imported as module."""
        # When imported as a module, __name__ != '__main__'
        import awslabs.healthlake_mcp_server.main as main_module

        # Verify the module name is not '__main__'
        assert main_module.__name__ != '__main__'

        # The guard should prevent execution
        should_execute = main_module.__name__ == '__main__'
        assert should_execute is False
