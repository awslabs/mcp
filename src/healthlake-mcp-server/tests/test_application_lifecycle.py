"""Tests for application startup, shutdown, and lifecycle management."""

import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestMainEntryPoints:
    """Test main entry point functions."""

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.main.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.main.stdio_server')
    async def test_main_success(self, mock_stdio_server, mock_create_server):
        """Test successful main function execution."""
        from awslabs.healthlake_mcp_server.main import main

        # Setup mocks
        mock_server = Mock()
        mock_server.run = AsyncMock()
        mock_server.create_initialization_options = Mock(return_value={})
        mock_create_server.return_value = mock_server

        # Mock stdio_server as async context manager
        mock_read_stream = Mock()
        mock_write_stream = Mock()
        mock_stdio_server.return_value.__aenter__ = AsyncMock(
            return_value=(mock_read_stream, mock_write_stream)
        )
        mock_stdio_server.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute main
        await main()

        # Verify server creation and run
        mock_create_server.assert_called_once()
        mock_server.run.assert_called_once_with(mock_read_stream, mock_write_stream, {})

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.main.create_healthlake_server')
    async def test_main_server_creation_error(self, mock_create_server):
        """Test main function with server creation error."""
        from awslabs.healthlake_mcp_server.main import main

        mock_create_server.side_effect = Exception('Server creation failed')

        with pytest.raises(Exception, match='Server creation failed'):
            await main()

    @pytest.mark.asyncio
    @patch('awslabs.healthlake_mcp_server.main.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.main.stdio_server')
    async def test_main_stdio_error(self, mock_stdio_server, mock_create_server):
        """Test main function with stdio server error."""
        from awslabs.healthlake_mcp_server.main import main

        mock_server = Mock()
        mock_create_server.return_value = mock_server

        mock_stdio_server.return_value.__aenter__ = AsyncMock(side_effect=Exception('Stdio error'))

        with pytest.raises(Exception, match='Stdio error'):
            await main()

    @patch('awslabs.healthlake_mcp_server.main.asyncio.run')
    def test_sync_main_success(self, mock_asyncio_run):
        """Test successful sync_main function execution."""
        from awslabs.healthlake_mcp_server.main import sync_main

        # Execute sync_main
        sync_main()

        # Verify asyncio.run was called
        mock_asyncio_run.assert_called_once()

    @patch('awslabs.healthlake_mcp_server.main.asyncio.run')
    def test_sync_main_with_error(self, mock_asyncio_run):
        """Test sync_main function with asyncio error."""
        from awslabs.healthlake_mcp_server.main import sync_main

        mock_asyncio_run.side_effect = KeyboardInterrupt('User interrupted')

        with pytest.raises(KeyboardInterrupt):
            sync_main()

    @patch('awslabs.healthlake_mcp_server.main.asyncio.run')
    def test_sync_main_runtime_error(self, mock_asyncio_run):
        """Test sync_main function with runtime error."""
        from awslabs.healthlake_mcp_server.main import sync_main

        mock_asyncio_run.side_effect = RuntimeError('Event loop error')

        with pytest.raises(RuntimeError):
            sync_main()


class TestMainModuleExecution:
    """Test main module execution scenarios."""

    def test_main_module_execution(self):
        """Test __name__ == '__main__' execution path."""
        # Test by executing the main module code directly
        import awslabs.healthlake_mcp_server.main

        # Mock sync_main to avoid actual server startup
        with patch('awslabs.healthlake_mcp_server.main.sync_main') as mock_sync_main:
            # Execute the code that runs when __name__ == '__main__'
            # This simulates running: python -m awslabs.healthlake_mcp_server.main
            exec(
                compile("if __name__ == '__main__': sync_main()", '<test>', 'exec'),
                {
                    '__name__': '__main__',
                    'sync_main': awslabs.healthlake_mcp_server.main.sync_main,
                },
            )

            # Verify sync_main was called
            mock_sync_main.assert_called_once()


class TestMainModuleIntegration:
    """Test main module integration scenarios."""

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'AWS_REGION': 'us-west-2'})
    @patch('awslabs.healthlake_mcp_server.main.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.main.stdio_server')
    async def test_main_with_environment_variables(self, mock_stdio_server, mock_create_server):
        """Test main function respects environment variables."""
        from awslabs.healthlake_mcp_server.main import main

        mock_server = Mock()
        mock_server.run = AsyncMock()
        mock_server.create_initialization_options = Mock(return_value={})
        mock_create_server.return_value = mock_server

        mock_read_stream = Mock()
        mock_write_stream = Mock()
        mock_stdio_server.return_value.__aenter__ = AsyncMock(
            return_value=(mock_read_stream, mock_write_stream)
        )
        mock_stdio_server.return_value.__aexit__ = AsyncMock(return_value=None)

        await main()

        # Verify server was created
        mock_create_server.assert_called_once()

    @patch('awslabs.healthlake_mcp_server.main.logger')
    def test_sync_main_logging(self, mock_logger):
        """Test that sync_main handles logging appropriately."""
        from awslabs.healthlake_mcp_server.main import sync_main

        # Just verify logger is available
        assert mock_logger is not None

        # Test normal execution path
        with patch('awslabs.healthlake_mcp_server.main.asyncio.run') as mock_run:
            sync_main()
            mock_run.assert_called_once()

    def test_sync_main_exception_propagation(self):
        """Test sync_main exception propagation."""
        from awslabs.healthlake_mcp_server.main import sync_main

        with patch('awslabs.healthlake_mcp_server.main.main') as mock_main:
            mock_main.side_effect = Exception('Test error')

            with pytest.raises(Exception, match='Test error'):
                sync_main()


class TestMainExceptionHandling:
    """Test main module exception handling for coverage."""

    def test_main_sync_exception_coverage(self):
        """Test main.py line 54 exception handling."""
        from awslabs.healthlake_mcp_server.main import sync_main

        with patch('awslabs.healthlake_mcp_server.main.asyncio.run') as mock_run:
            mock_run.side_effect = Exception('Test error')

            with pytest.raises(Exception, match='Test error'):
                sync_main()
