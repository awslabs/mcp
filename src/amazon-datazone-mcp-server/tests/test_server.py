"""Tests for the main MCP server functionality."""

import json
import pytest
import sys
from unittest.mock import patch


class TestMCPServer:
    """Test cases for the main MCP server functionality."""

    def test_server_imports_successfully(self):
        """Test that server imports without errors."""
        from awslabs.amazon_datazone_mcp_server import server

        assert hasattr(server, 'mcp')
        assert hasattr(server, 'main')

    def test_server_has_fastmcp_instance(self):
        """Test that server has FastMCP instance."""
        from awslabs.amazon_datazone_mcp_server import server

        assert server.mcp is not None
        # Verify it's a FastMCP instance (name property is available)
        assert hasattr(server.mcp, 'name')

    @patch('mcp.server.fastmcp.FastMCP.run')
    def test_main_function_normal_operation(self, mock_run):
        """Test main function under normal operation."""
        from awslabs.amazon_datazone_mcp_server.server import main

        # Arrange
        mock_run.return_value = None

        # Act & Assert (should not raise)
        main()

        # Verify MCP was called with correct transport
        mock_run.assert_called_once_with(transport='stdio')

    @patch('mcp.server.fastmcp.FastMCP.run')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_main_function_error_handling(self, mock_print, mock_exit, mock_run):
        """Test main function error handling."""
        from awslabs.amazon_datazone_mcp_server.server import main

        # Arrange
        mock_run.side_effect = Exception('Test error')

        # Act
        main()

        # Assert
        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        # Verify error was printed as JSON
        printed_arg = mock_print.call_args[0][0]
        assert 'Test error' in printed_arg
        assert 'error' in printed_arg

    @patch('mcp.server.fastmcp.FastMCP.run')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_runtime_error_handling(self, mock_print, mock_exit, mock_run):
        """Test handling of runtime errors."""
        from awslabs.amazon_datazone_mcp_server.server import main

        # Arrange
        mock_run.side_effect = RuntimeError('Runtime error occurred')

        # Act
        main()

        # Assert
        mock_exit.assert_called_once_with(1)
        printed_output = mock_print.call_args[0][0]
        assert 'RuntimeError' in printed_output
        assert 'Runtime error occurred' in printed_output

    @patch('mcp.server.fastmcp.FastMCP.run')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_keyboard_interrupt_handling(self, mock_print, mock_exit, mock_run):
        """Test handling of keyboard interrupts."""
        from awslabs.amazon_datazone_mcp_server.server import main

        # Arrange
        mock_run.side_effect = KeyboardInterrupt()

        # Act
        main()

        # Assert
        mock_print.assert_called_with(
            'KeyboardInterrupt received. Shutting down gracefully.', file=sys.stderr
        )
        mock_exit.assert_called_once_with(0)

    @patch('mcp.server.fastmcp.FastMCP.run')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_json_error_response_format(self, mock_print, mock_exit, mock_run):
        """Test that error responses are valid JSON."""
        from awslabs.amazon_datazone_mcp_server.server import main

        # Arrange
        mock_run.side_effect = ValueError('Test value error')

        # Act
        main()

        # Assert
        printed_output = mock_print.call_args[0][0]

        # Should be valid JSON
        try:
            error_data = json.loads(printed_output)
            assert 'error' in error_data
            assert 'type' in error_data
            assert 'message' in error_data
            assert error_data['type'] == 'ValueError'
            assert 'Test value error' in error_data['error']
        except json.JSONDecodeError:
            pytest.fail('Error output is not valid JSON')


class TestVersionHandling:
    """Test version handling in __init__.py."""

    @patch('pathlib.Path.exists')
    def test_version_file_missing(self, mock_exists):
        """Test version handling when VERSION file doesn't exist."""
        # Mock the VERSION file as not existing
        mock_exists.return_value = False

        # Import the module to trigger the version reading logic
        import sys

        # Remove the module from cache if it exists
        if 'awslabs.amazon_datazone_mcp_server' in sys.modules:
            del sys.modules['awslabs.amazon_datazone_mcp_server']

        # Import the module which should trigger the version reading
        import awslabs.amazon_datazone_mcp_server

        # The version should be 'unknown' when file doesn't exist
        assert awslabs.amazon_datazone_mcp_server.__version__ == 'unknown'


class TestServerConfiguration:
    """Test server configuration and setup."""

    def test_logger_configuration(self):
        """Test that logger is properly configured."""
        import logging
        from awslabs.amazon_datazone_mcp_server import server

        # Check that the logger exists and has the right level
        logger = logging.getLogger(server.__name__)
        assert logger.level == logging.INFO

    def test_server_name(self):
        """Test that server is initialized with correct name."""
        from awslabs.amazon_datazone_mcp_server import server

        # This verifies the MCP server is named 'datazone'
        assert server.mcp.name == 'datazone'


class TestToolRegistration:
    """Test that all tools are properly registered."""

    def test_server_initialization_registers_tools(self):
        """Test that server initializes and has tools registered."""
        from awslabs.amazon_datazone_mcp_server import server

        # The server should have been initialized with tools
        assert server.mcp is not None
        # FastMCP should have tools registered (tools are registered at module import)
        # We can't directly inspect registered tools without accessing private members,
        # but we can verify the registration calls would have succeeded by checking imports
        assert hasattr(server, 'domain_management')
        assert hasattr(server, 'project_management')
        assert hasattr(server, 'data_management')
        assert hasattr(server, 'glossary')
        assert hasattr(server, 'environment')

    def test_tool_modules_have_register_functions(self):
        """Test that all tool modules have register_tools functions."""
        from awslabs.amazon_datazone_mcp_server.tools import (
            data_management,
            domain_management,
            environment,
            glossary,
            project_management,
        )

        # Verify all modules have register_tools function
        assert hasattr(domain_management, 'register_tools')
        assert hasattr(project_management, 'register_tools')
        assert hasattr(data_management, 'register_tools')
        assert hasattr(glossary, 'register_tools')
        assert hasattr(environment, 'register_tools')

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
        """Test that tool modules can be imported."""
        from awslabs.amazon_datazone_mcp_server.tools import (
            data_management,
            domain_management,
            environment,
            glossary,
            project_management,
        )

        # Verify modules are importable
        assert data_management is not None
        assert domain_management is not None
        assert environment is not None
        assert glossary is not None
        assert project_management is not None

    def test_standard_library_imports(self):
        """Test that standard library modules can be imported."""
        import json
        import logging
        import sys

        assert json is not None
        assert logging is not None
        assert sys is not None


class TestCommandLineInterface:
    """Test command line interface functionality."""

    @patch('mcp.server.fastmcp.FastMCP.run')
    def test_main_if_name_main_execution(self, mock_run):
        """Test __main__ execution path."""
        from awslabs.amazon_datazone_mcp_server import server

        # Execute the main function directly to cover line 76
        server.main()

        mock_run.assert_called_once_with(transport='stdio')

    def test_console_script_entry_point(self):
        """Test that the console script entry point exists."""
        import importlib.util

        # Test that we can import the module
        spec = importlib.util.find_spec('awslabs.amazon_datazone_mcp_server.server')
        assert spec is not None

        # Test that main function exists
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            assert hasattr(module, 'main')
            assert callable(module.main)


class TestServerIntegration:
    """Integration tests for server functionality."""

    @pytest.mark.slow
    def test_server_initialization_performance(self):
        """Test that server initializes within reasonable time."""
        import time

        start_time = time.time()
        from awslabs.amazon_datazone_mcp_server import server

        end_time = time.time()

        # Server should initialize within 2 seconds
        assert (end_time - start_time) < 2.0
        assert server.mcp is not None


class TestServerEntryPointErrorHandling:
    """Test server entry point error handling scenarios."""

    @patch('awslabs.amazon_datazone_mcp_server.server.mcp')
    @patch('sys.exit')
    def test_main_keyboard_interrupt_pragma_coverage(self, mock_exit, mock_mcp):
        """Test KeyboardInterrupt handling in main function - covers pragma no cover."""
        from awslabs.amazon_datazone_mcp_server.server import main

        mock_mcp.run.side_effect = KeyboardInterrupt()

        with patch('sys.stderr.write'):
            main()

        mock_exit.assert_called_once_with(0)

    @patch('awslabs.amazon_datazone_mcp_server.server.mcp')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_main_exception_handling_pragma_coverage(self, mock_print, mock_exit, mock_mcp):
        """Test general exception handling in main function - covers pragma no cover."""
        from awslabs.amazon_datazone_mcp_server.server import main

        test_exception = Exception('Test error')
        mock_mcp.run.side_effect = test_exception

        main()

        # Verify error response was printed
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        error_response = json.loads(call_args)

        assert error_response['error'] == 'Test error'
        assert error_response['type'] == 'Exception'
        assert error_response['message'] == 'MCP server encountered an error'

        mock_exit.assert_called_once_with(1)


class TestServerMainFunctionHandling:
    """Test main function error handling scenarios."""

    @pytest.mark.asyncio
    async def test_main_function_exception_handling_pragma_coverage(self, monkeypatch):
        """Test main function exception handling that calls sys.exit(1) - covers line 65."""
        import json
        import sys
        from awslabs.amazon_datazone_mcp_server.server import main
        from io import StringIO

        # Mock stdout to capture print output
        captured_output = StringIO()
        monkeypatch.setattr(sys, 'stdout', captured_output)

        # Mock mcp.run to raise an exception
        def mock_run(*args, **kwargs):
            raise ValueError('Test exception for coverage')

        # Mock the mcp object's run method
        from awslabs.amazon_datazone_mcp_server.server import mcp
        monkeypatch.setattr(mcp, 'run', mock_run)

        # Mock sys.exit to capture the exit call
        exit_calls = []
        def mock_exit(code):
            exit_calls.append(code)
        monkeypatch.setattr(sys, 'exit', mock_exit)

        # Call main function
        main()

        # Verify exception handling behavior
        assert len(exit_calls) == 1
        assert exit_calls[0] == 1  # Should exit with code 1

        # Verify JSON error response was printed
        output = captured_output.getvalue()
        try:
            error_response = json.loads(output)
            assert 'error' in error_response
            assert 'Test exception for coverage' in error_response['error']
            assert error_response['type'] == 'ValueError'
            assert error_response['message'] == 'MCP server encountered an error'
        except json.JSONDecodeError:
            pytest.fail('Expected JSON error response to be printed')
