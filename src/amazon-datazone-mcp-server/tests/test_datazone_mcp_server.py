"""Unit tests for Amazon DataZone MCP Server."""

from pathlib import Path
from unittest.mock import Mock, patch


class TestDatazoneMCPServer:
    """Test cases for the main DataZone MCP Server functionality."""

    def test_version_with_existing_file(self):
        """Test version reading when VERSION file exists."""
        # Import the module to test version reading
        from awslabs.amazon_datazone_mcp_server import __version__

        # The version should be read from the VERSION file
        assert isinstance(__version__, str)
        assert __version__ != 'unknown'  # Should have actual version from file

    def test_version_without_file(self):
        """Test version handling when VERSION file doesn't exist."""
        import sys

        # Clear module from cache
        module_name = 'awslabs.amazon_datazone_mcp_server'
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Mock Path.exists to return False
        with patch.object(Path, 'exists', return_value=False):
            # Import the module fresh to trigger the version reading logic
            from awslabs.amazon_datazone_mcp_server import __version__

            # Should default to 'unknown' when file doesn't exist
            assert __version__ == 'unknown'

    def test_main_function_execution(self):
        """Test the main function execution path."""
        from awslabs.amazon_datazone_mcp_server.server import main

        # Mock the mcp.run method to avoid actual execution
        with patch('awslabs.amazon_datazone_mcp_server.server.mcp') as mock_mcp:
            mock_mcp.run = Mock()

            # Test normal execution
            main()

            # Verify mcp.run was called with correct transport
            mock_mcp.run.assert_called_once_with(transport='stdio')

    def test_main_function_with_keyboard_interrupt(self):
        """Test main function handling KeyboardInterrupt."""
        from awslabs.amazon_datazone_mcp_server.server import main

        with patch('awslabs.amazon_datazone_mcp_server.server.mcp') as mock_mcp:
            # Mock mcp.run to raise KeyboardInterrupt
            mock_mcp.run.side_effect = KeyboardInterrupt()

            # Mock sys.exit to prevent actual exit
            with patch('sys.exit') as mock_exit:
                main()
                # Should exit with code 0 on KeyboardInterrupt
                mock_exit.assert_called_once_with(0)

    def test_main_function_with_exception(self):
        """Test main function handling general exceptions."""
        from awslabs.amazon_datazone_mcp_server.server import main

        with patch('awslabs.amazon_datazone_mcp_server.server.mcp') as mock_mcp:
            # Mock mcp.run to raise a general exception
            mock_mcp.run.side_effect = Exception('Test error')

            # Mock sys.exit and print to capture output
            with patch('sys.exit') as mock_exit, patch('builtins.print') as mock_print:
                main()

                # Should exit with code 1 on general exception
                mock_exit.assert_called_once_with(1)
                # Should print JSON error response
                mock_print.assert_called()


def test_datazone_mcp_server_importable():
    """Test datazone_mcp_server is importable."""
    import awslabs.amazon_datazone_mcp_server  # noqa: F401
