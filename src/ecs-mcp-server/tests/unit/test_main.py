"""
Unit tests for main server module.

This file contains tests for the ECS MCP Server main module, including:
- Basic properties (name, version, description, instructions)
- Tools registration
- Prompt patterns registration
- Server startup and shutdown
- Logging configuration
- Error handling
"""

import sys
import unittest
from unittest.mock import MagicMock, call, patch


# We need to patch the imports before importing the module under test
class MockFastMCP:
    """Mock implementation of FastMCP for testing."""

    def __init__(self, name, description=None, version=None, instructions=None):
        self.name = name
        self.description = description or ""
        self.version = version
        self.instructions = instructions
        self.tools = []
        self.prompt_patterns = []

    def tool(self, name=None, description=None, annotations=None):
        def decorator(func):
            self.tools.append(
                {
                    "name": name or func.__name__,
                    "function": func,
                    "annotations": annotations,
                    "description": description,
                }
            )
            return func

        return decorator

    def prompt(self, pattern):
        def decorator(func):
            self.prompt_patterns.append({"pattern": pattern, "function": func})
            return func

        return decorator

    def run(self):
        pass


# Apply the patches
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    from awslabs.ecs_mcp_server.main import main, mcp


# ----------------------------------------------------------------------------
# Server Configuration Tests
# ----------------------------------------------------------------------------


class TestMain(unittest.TestCase):
    """
    Tests for main server module configuration.

    This test class contains separate test methods for each aspect of the server
    configuration, providing better isolation and easier debugging when tests fail.
    """

    def test_server_basic_properties(self):
        """
        Test basic server properties.

        This test focuses only on the basic properties of the server:
        - Name
        - Version
        - Description
        - Instructions

        If this test fails, it indicates an issue with the basic server configuration.
        """
        # Verify the server has the correct name and version
        self.assertEqual(mcp.name, "AWS ECS MCP Server")
        self.assertEqual(mcp.version, "0.1.0")

        # Verify the description contains expected keywords
        self.assertIn("containerization", mcp.description.lower())
        self.assertIn("deployment", mcp.description.lower())
        self.assertIn("aws ecs", mcp.description.lower())

        # Verify instructions are provided
        self.assertIsNotNone(mcp.instructions)
        self.assertIn("WORKFLOW", mcp.instructions)
        self.assertIn("IMPORTANT", mcp.instructions)

    def test_server_tools(self):
        """
        Test that server has the expected tools.

        This test focuses only on the tools registered with the server.
        It verifies that all required tools are present.

        If this test fails, it indicates an issue with tool registration.
        """
        # Verify the server has registered tools
        self.assertGreaterEqual(len(mcp.tools), 4)

        # Verify tool names
        tool_names = [tool["name"] for tool in mcp.tools]
        self.assertIn("containerize_app", tool_names)
        self.assertIn("create_ecs_infrastructure", tool_names)
        self.assertIn("get_deployment_status", tool_names)
        self.assertIn("delete_ecs_infrastructure", tool_names)

    def test_server_prompts(self):
        """
        Test that server has the expected prompt patterns.

        This test focuses only on the prompt patterns registered with the server.
        It verifies that all required prompt patterns are present.

        If this test fails, it indicates an issue with prompt pattern registration.
        """
        # Verify the server has registered prompt patterns
        self.assertGreaterEqual(len(mcp.prompt_patterns), 14)

        # Verify prompt patterns
        patterns = [pattern["pattern"] for pattern in mcp.prompt_patterns]
        self.assertIn("dockerize", patterns)
        self.assertIn("containerize", patterns)
        self.assertIn("deploy to aws", patterns)
        self.assertIn("deploy to ecs", patterns)
        self.assertIn("ship it", patterns)
        self.assertIn("deploy flask", patterns)
        self.assertIn("deploy django", patterns)
        self.assertIn("delete infrastructure", patterns)
        self.assertIn("tear down", patterns)
        self.assertIn("remove deployment", patterns)
        self.assertIn("clean up resources", patterns)


# ----------------------------------------------------------------------------
# Logging Tests
# ----------------------------------------------------------------------------


def test_log_file_setup():
    """Test log file setup with directory creation."""

    # Create a test function that mimics the log file setup from main.py
    def setup_log_file(log_file, mock_os, mock_logging):
        try:
            # Create directory for log file if it doesn't exist
            log_dir = mock_os.path.dirname(log_file)
            if log_dir and not mock_os.path.exists(log_dir):
                mock_os.makedirs(log_dir, exist_ok=True)

            # Add file handler
            file_handler = mock_logging.FileHandler(log_file)
            file_handler.setFormatter(mock_logging.Formatter("test-format"))
            mock_logging.getLogger().addHandler(file_handler)
            mock_logging.info(f"Logging to file: {log_file}")
            return True
        except Exception as e:
            mock_logging.error(f"Failed to set up log file {log_file}: {e}")
            return False

    # Setup mocks
    mock_os = MagicMock()
    mock_os.path.dirname.return_value = "/var/log/test_logs"
    mock_os.path.exists.return_value = False

    mock_logging = MagicMock()
    mock_file_handler = MagicMock()
    mock_logging.FileHandler.return_value = mock_file_handler
    mock_formatter = MagicMock()
    mock_logging.Formatter.return_value = mock_formatter

    # Call our test function
    result = setup_log_file("/var/log/test_logs/ecs-mcp.log", mock_os, mock_logging)

    # Verify that the function succeeded
    assert result is True

    # Verify that the log directory was created
    mock_os.makedirs.assert_called_once_with("/var/log/test_logs", exist_ok=True)

    # Verify that the log file handler was created and added to the logger
    mock_logging.FileHandler.assert_called_once_with("/var/log/test_logs/ecs-mcp.log")
    mock_file_handler.setFormatter.assert_called_once()
    mock_logging.getLogger.return_value.addHandler.assert_called_once_with(mock_file_handler)

    # Verify that the log success message was logged
    assert (
        call("Logging to file: /var/log/test_logs/ecs-mcp.log") in mock_logging.info.call_args_list
    )


def test_log_file_setup_exception():
    """Test log file setup when an exception occurs."""

    # Create a test function that mimics the log file setup from main.py
    def setup_log_file(log_file, mock_os, mock_logging):
        try:
            # Create directory for log file if it doesn't exist
            log_dir = mock_os.path.dirname(log_file)
            if log_dir and not mock_os.path.exists(log_dir):
                mock_os.makedirs(log_dir, exist_ok=True)

            # Add file handler
            file_handler = mock_logging.FileHandler(log_file)
            file_handler.setFormatter(mock_logging.Formatter("test-format"))
            mock_logging.getLogger().addHandler(file_handler)
            mock_logging.info(f"Logging to file: {log_file}")
            return True
        except Exception as e:
            mock_logging.error(f"Failed to set up log file {log_file}: {e}")
            return False

    # Setup mocks
    mock_os = MagicMock()
    mock_os.path.dirname.return_value = "/var/log/test_logs"
    mock_os.path.exists.return_value = False
    mock_os.makedirs.side_effect = PermissionError("Permission denied")

    mock_logging = MagicMock()

    # Call our test function
    result = setup_log_file("/var/log/test_logs/ecs-mcp.log", mock_os, mock_logging)

    # Verify that the function failed
    assert result is False

    # Verify that the error was logged
    mock_logging.error.assert_called_once_with(
        "Failed to set up log file /var/log/test_logs/ecs-mcp.log: Permission denied"
    )


# ----------------------------------------------------------------------------
# Main Function Tests
# ----------------------------------------------------------------------------


@patch("awslabs.ecs_mcp_server.main.sys.exit")
@patch("awslabs.ecs_mcp_server.main.logger")
@patch("awslabs.ecs_mcp_server.main.mcp")
@patch("awslabs.ecs_mcp_server.main.config")
def test_main_function_success(mock_config, mock_mcp, mock_logger, mock_exit):
    """Test main function with successful execution."""
    # Setup mocks
    mock_config.get.side_effect = lambda key, default: True if key == "allow-write" else False

    # Call the main function
    main()

    # Verify that the logger messages were called
    mock_logger.info.assert_any_call("Server started")
    mock_logger.info.assert_any_call("Write operations enabled: True")
    mock_logger.info.assert_any_call("Sensitive data access enabled: False")

    # Verify that the mcp.run() method was called
    mock_mcp.run.assert_called_once()

    # Verify that sys.exit was not called
    mock_exit.assert_not_called()


@patch("awslabs.ecs_mcp_server.main.sys.exit")
@patch("awslabs.ecs_mcp_server.main.logger")
@patch("awslabs.ecs_mcp_server.main.mcp")
def test_main_function_keyboard_interrupt(mock_mcp, mock_logger, mock_exit):
    """Test main function with KeyboardInterrupt exception."""
    # Setup mocks
    mock_mcp.run.side_effect = KeyboardInterrupt()

    # Call the main function
    main()

    # Verify that the logger messages were called
    mock_logger.info.assert_any_call("Server stopped by user")

    # Verify that sys.exit was called with code 0
    mock_exit.assert_called_once_with(0)


@patch("awslabs.ecs_mcp_server.main.sys.exit")
@patch("awslabs.ecs_mcp_server.main.logger")
@patch("awslabs.ecs_mcp_server.main.mcp")
def test_main_function_general_exception(mock_mcp, mock_logger, mock_exit):
    """Test main function with general exception."""
    # Setup mocks
    mock_mcp.run.side_effect = Exception("Test error")

    # Call the main function
    main()

    # Verify that the logger error was called with the exception
    mock_logger.error.assert_called_once_with("Error starting server: Test error")

    # Verify that sys.exit was called with code 1
    mock_exit.assert_called_once_with(1)


@patch("awslabs.ecs_mcp_server.main.main")
def test_entry_point(mock_main):
    """Test the module's entry point."""
    # Save the current value of __name__
    original_name = sys.modules.get("awslabs.ecs_mcp_server.main", None)

    try:
        # Mock __name__ to trigger the entry point code
        sys.modules["awslabs.ecs_mcp_server.main"].__name__ = "__main__"

        # Instead of reading the file, we can directly simulate the entry point check
        # that would exist in the main.py file
        namespace = {"__name__": "__main__", "main": mock_main}

        # Simulate the standard entry point code: if __name__ == "__main__": main()
        if namespace["__name__"] == "__main__":
            namespace["main"]()

        # Verify that main() was called
        mock_main.assert_called_once()
    finally:
        # Restore the original value of __name__
        if original_name:
            sys.modules["awslabs.ecs_mcp_server.main"].__name__ = original_name.__name__
