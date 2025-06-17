"""Tests for the main MCP server functionality."""

import json
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestMCPServer:
    """Test cases for the main MCP server functionality."""

    def test_server_imports_successfully(self):
        """Test that server imports without errors."""
        from awslabs.datazone_mcp_server import server

        assert hasattr(server, "mcp")
        assert hasattr(server, "main")

    def test_server_has_fastmcp_instance(self):
        """Test that server has FastMCP instance."""
        from awslabs.datazone_mcp_server import server

        assert server.mcp is not None
        # Verify it's a FastMCP instance (name property is available)
        assert hasattr(server.mcp, "name")

    @patch("mcp.server.fastmcp.FastMCP.run")
    def test_main_function_normal_operation(self, mock_run):
        """Test main function under normal operation."""
        from awslabs.datazone_mcp_server.server import main

        # Arrange
        mock_run.return_value = None

        # Act & Assert (should not raise)
        main()

        # Verify MCP was called with correct transport
        mock_run.assert_called_once_with(transport="stdio")

    @patch("mcp.server.fastmcp.FastMCP.run")
    @patch("sys.exit")
    @patch("builtins.print")
    def test_main_function_error_handling(self, mock_print, mock_exit, mock_run):
        """Test main function error handling."""
        from awslabs.datazone_mcp_server.server import main

        # Arrange
        mock_run.side_effect = Exception("Test error")

        # Act
        main()

        # Assert
        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        # Verify error was printed as JSON
        printed_arg = mock_print.call_args[0][0]
        assert "Test error" in printed_arg
        assert "error" in printed_arg

    @patch("mcp.server.fastmcp.FastMCP.run")
    @patch("sys.exit")
    @patch("builtins.print")
    def test_runtime_error_handling(self, mock_print, mock_exit, mock_run):
        """Test handling of runtime errors."""
        from awslabs.datazone_mcp_server.server import main

        # Arrange
        mock_run.side_effect = RuntimeError("Runtime error occurred")

        # Act
        main()

        # Assert
        mock_exit.assert_called_once_with(1)
        printed_output = mock_print.call_args[0][0]
        assert "RuntimeError" in printed_output
        assert "Runtime error occurred" in printed_output

    @patch("mcp.server.fastmcp.FastMCP.run")
    @patch("sys.exit")
    @patch("builtins.print")
    def test_keyboard_interrupt_handling(self, mock_print, mock_exit, mock_run):
        """Test handling of keyboard interrupts."""
        from awslabs.datazone_mcp_server.server import main

        # Arrange
        mock_run.side_effect = KeyboardInterrupt()

        # Act
        main()

        # Assert
        mock_print.assert_called_with(
            "KeyboardInterrupt received. Shutting down gracefully.", file=sys.stderr
        )
        mock_exit.assert_called_once_with(0)

    @patch("mcp.server.fastmcp.FastMCP.run")
    @patch("sys.exit")
    @patch("builtins.print")
    def test_json_error_response_format(self, mock_print, mock_exit, mock_run):
        """Test that error responses are valid JSON."""
        from awslabs.datazone_mcp_server.server import main

        # Arrange
        mock_run.side_effect = ValueError("Test value error")

        # Act
        main()

        # Assert
        printed_output = mock_print.call_args[0][0]

        # Should be valid JSON
        try:
            error_data = json.loads(printed_output)
            assert "error" in error_data
            assert "type" in error_data
            assert "message" in error_data
            assert error_data["type"] == "ValueError"
            assert "Test value error" in error_data["error"]
        except json.JSONDecodeError:
            pytest.fail("Error output is not valid JSON")


class TestServerConfiguration:
    """Test server configuration and setup."""

    def test_logger_configuration(self):
        """Test that logger is properly configured."""
        import logging

        from awslabs.datazone_mcp_server import server

        # Check that the logger exists and has the right level
        logger = logging.getLogger(server.__name__)
        assert logger.level == logging.INFO

    def test_server_name(self):
        """Test that server is initialized with correct name."""
        from awslabs.datazone_mcp_server import server

        # This verifies the MCP server is named 'datazone'
        assert server.mcp.name == "datazone"


class TestToolRegistration:
    """Test that all tools are properly registered."""

    def test_server_initialization_registers_tools(self):
        """Test that server initializes and has tools registered."""
        from awslabs.datazone_mcp_server import server

        # The server should have been initialized with tools
        assert server.mcp is not None
        # FastMCP should have tools registered (tools are registered at module import)
        # We can't directly inspect registered tools without accessing private members,
        # but we can verify the registration calls would have succeeded by checking imports
        assert hasattr(server, "domain_management")
        assert hasattr(server, "project_management")
        assert hasattr(server, "data_management")
        assert hasattr(server, "glossary")
        assert hasattr(server, "environment")

    def test_tool_modules_have_register_functions(self):
        """Test that all tool modules have register_tools functions."""
        from awslabs.datazone_mcp_server.tools import (
            data_management,
            domain_management,
            environment,
            glossary,
            project_management,
        )

        # Verify all modules have register_tools function
        assert hasattr(domain_management, "register_tools")
        assert hasattr(project_management, "register_tools")
        assert hasattr(data_management, "register_tools")
        assert hasattr(glossary, "register_tools")
        assert hasattr(environment, "register_tools")

        # Verify they are callable
        assert callable(domain_management.register_tools)
        assert callable(project_management.register_tools)
        assert callable(data_management.register_tools)
        assert callable(glossary.register_tools)
        assert callable(environment.register_tools)


class TestModuleImports:
    """Test that all required modules can be imported."""

    def test_fastmcp_import(self):
        """Test that FastMCP can be imported."""
        from mcp.server.fastmcp import FastMCP

        assert FastMCP is not None

    def test_tool_modules_import(self):
        """Test that all tool modules can be imported."""
        from awslabs.datazone_mcp_server.tools import (
            data_management,
            domain_management,
            environment,
            glossary,
            project_management,
        )

        # Verify modules are not None
        assert domain_management is not None
        assert project_management is not None
        assert data_management is not None
        assert glossary is not None
        assert environment is not None

    def test_standard_library_imports(self):
        """Test that standard library modules work."""
        import json
        import logging
        import sys

        # Basic functionality test
        test_data = {"test": "value"}
        json_str = json.dumps(test_data)
        parsed = json.loads(json_str)
        assert parsed == test_data


class TestCommandLineInterface:
    """Test command line interface functionality."""

    @patch("mcp.server.fastmcp.FastMCP.run")
    def test_main_if_name_main_execution(self, mock_run):
        """Test that __main__ execution works."""
        # This test verifies that the if __name__ == "__main__" block can execute
        # We can't easily test this directly, but we can test the main() function
        from awslabs.datazone_mcp_server.server import main

        main()
        mock_run.assert_called_once_with(transport="stdio")

    def test_console_script_entry_point(self):
        """Test that the entry point exists in setup."""
        # This would normally check setup.py or pyproject.toml
        # For now, just verify the main function exists and is callable
        from awslabs.datazone_mcp_server.server import main

        assert callable(main)


class TestServerIntegration:
    """Test server integration and performance aspects."""

    @pytest.mark.slow
    def test_server_initialization_performance(self):
        """Test that server initialization is reasonably fast."""
        import time

        start_time = time.time()

        # Re-import to test initialization time
        import importlib

        from awslabs.datazone_mcp_server import server

        importlib.reload(server)

        end_time = time.time()
        initialization_time = end_time - start_time

        # Should initialize in less than 5 seconds
        assert initialization_time < 5.0, f"Server took {initialization_time}s to initialize"

    def test_memory_usage_reasonable(self):
        """Test that memory usage is reasonable after import."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        # Import server
        from awslabs.datazone_mcp_server import server

        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before

        # Memory increase should be less than 50MB (50 * 1024 * 1024 bytes)
        max_memory_increase = 50 * 1024 * 1024
        assert (
            memory_increase < max_memory_increase
        ), f"Memory increased by {memory_increase / 1024 / 1024:.1f}MB"
