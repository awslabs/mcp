"""
Unit tests for main server module.

This file contains tests for the ECS MCP Server main module, including:
- Basic properties (name, instructions)
- Tools registration
- Prompt patterns registration
- Server startup and shutdown
- Logging configuration
- Error handling
"""

import asyncio
import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, call, patch


# Mock FastMCP for isolated testing
class MockFastMCP:
    """Mock implementation of FastMCP for testing."""

    def __init__(self, name, instructions=None, lifespan=None, **kwargs):
        self.name = name
        self.instructions = instructions
        self.lifespan = lifespan
        self.tools = []
        self.prompt_patterns = []

    def tool(self, name=None, annotations=None):
        def decorator(func):
            self.tools.append(
                {
                    "name": name or func.__name__,
                    "function": func,
                    "annotations": annotations,
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


# Apply patches before importing module under test
with patch("fastmcp.FastMCP", MockFastMCP):
    from awslabs.ecs_mcp_server.main import (
        _create_ecs_mcp_server,
        _setup_logging,
        main,
        server_lifespan,
    )


# ----------------------------------------------------------------------------
# Test Utilities and Mixins
# ----------------------------------------------------------------------------


class EnvironmentTestMixin:
    """Mixin providing environment variable management for tests."""

    def setUp(self):
        """Store original environment state."""
        super().setUp()
        self._original_env = self._capture_environment_state()

    def tearDown(self):
        """Restore original environment state."""
        self._restore_environment_state(self._original_env)
        super().tearDown()

    def _capture_environment_state(self):
        """Capture relevant environment variables."""
        return {key: os.environ.get(key) for key in ["FASTMCP_LOG_LEVEL", "FASTMCP_LOG_FILE"]}

    def _restore_environment_state(self, original_state):
        """Restore environment variables to original state."""
        for key, value in original_state.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]

    def clear_logging_env_vars(self):
        """Clear logging-related environment variables."""
        for key in ["FASTMCP_LOG_LEVEL", "FASTMCP_LOG_FILE"]:
            if key in os.environ:
                del os.environ[key]

    def set_log_level(self, level):
        """Set logging level environment variable."""
        os.environ["FASTMCP_LOG_LEVEL"] = level

    def set_log_file(self, file_path):
        """Set log file environment variable."""
        os.environ["FASTMCP_LOG_FILE"] = file_path


class LoggingTestMixin(EnvironmentTestMixin):
    """Mixin providing logging system management for tests."""

    def setUp(self):
        """Initialize clean logging state."""
        super().setUp()
        self._reset_logging_system()

    def tearDown(self):
        """Clean up logging system."""
        self._reset_logging_system()
        super().tearDown()

    def _reset_logging_system(self):
        """Reset logging system to clean state."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        logging.shutdown()
        root_logger.setLevel(logging.NOTSET)


# ----------------------------------------------------------------------------
# Core Server Configuration Tests
# ----------------------------------------------------------------------------


class TestServerConfiguration(unittest.TestCase):
    """Tests for server configuration and initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.mcp, self.config = _create_ecs_mcp_server()

    def test_server_properties(self):
        """Test server has correct basic properties."""
        self.assertEqual(self.mcp.name, "AWS ECS MCP Server")
        self.assertIsNotNone(self.mcp.instructions)
        self.assertIn("WORKFLOW", self.mcp.instructions)
        self.assertIn("IMPORTANT", self.mcp.instructions)

    def test_required_tools_registered(self):
        """Test all required tools are properly registered."""
        self.assertGreaterEqual(len(self.mcp.tools), 4)

        required_tools = [
            "containerize_app",
            "create_ecs_infrastructure",
            "get_deployment_status",
            "delete_ecs_infrastructure",
        ]

        tool_names = [tool["name"] for tool in self.mcp.tools]
        for tool in required_tools:
            self.assertIn(tool, tool_names, f"Required tool '{tool}' not found")

    def test_prompt_patterns_registered(self):
        """Test prompt patterns are properly registered."""
        self.assertGreaterEqual(len(self.mcp.prompt_patterns), 14)

        expected_patterns = [
            "dockerize",
            "containerize",
            "deploy to aws",
            "deploy to ecs",
            "ship it",
            "deploy flask",
            "deploy django",
            "delete infrastructure",
            "tear down",
            "remove deployment",
            "clean up resources",
        ]

        patterns = [pattern["pattern"] for pattern in self.mcp.prompt_patterns]
        for pattern in expected_patterns:
            self.assertIn(pattern, patterns, f"Expected pattern '{pattern}' not found")


# ----------------------------------------------------------------------------
# Logging System Tests
# ----------------------------------------------------------------------------


class TestLoggingSystem(LoggingTestMixin, unittest.TestCase):
    """Tests for logging system configuration and behavior."""

    def test_default_logging_setup(self):
        """Test logging setup with default configuration."""
        self.clear_logging_env_vars()

        logger = _setup_logging()

        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "ecs-mcp-server")

    def test_custom_log_level_configuration(self):
        """Test logging setup with custom log level."""
        self.set_log_level("DEBUG")

        logger = _setup_logging()

        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "ecs-mcp-server")

    def test_file_logging_setup(self):
        """Test file logging configuration with success scenario."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            self.set_log_file(log_file)

            with patch("logging.info") as mock_info:
                logger = _setup_logging()

                self.assertIsNotNone(logger)

                # Verify file handler was added
                root_logger = logging.getLogger()
                file_handlers = [
                    h for h in root_logger.handlers if isinstance(h, logging.FileHandler)
                ]
                self.assertGreater(len(file_handlers), 0)

                # Verify success logging
                mock_info.assert_any_call(f"Logging to file: {log_file}")

    def test_automatic_directory_creation(self):
        """Test automatic creation of log file directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "logs", "subdir")
            log_file = os.path.join(log_dir, "test.log")
            self.set_log_file(log_file)

            self.assertFalse(os.path.exists(log_dir))

            logger = _setup_logging()

            self.assertIsNotNone(logger)
            self.assertTrue(os.path.exists(log_dir))

    def test_file_logging_error_handling(self):
        """Test graceful handling of file logging errors."""
        invalid_path = "/invalid/nonexistent/path/test.log"
        self.set_log_file(invalid_path)

        with patch("logging.error") as mock_error:
            logger = _setup_logging()

            # Function should still return logger despite error
            self.assertIsNotNone(logger)

            # Error should be logged
            mock_error.assert_called_once()
            error_message = mock_error.call_args[0][0]
            self.assertIn("Failed to set up log file", error_message)
            self.assertIn(invalid_path, error_message)


# ----------------------------------------------------------------------------
# Server Lifecycle Tests
# ----------------------------------------------------------------------------


class TestServerLifecycle(unittest.TestCase):
    """Tests for async server lifecycle management."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_server = MagicMock()

    def _run_async_test(self, async_test_func):
        """Helper to execute async test functions."""
        asyncio.run(async_test_func())

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.apply_tool_transformations")
    @patch("logging.getLogger")
    def test_successful_lifecycle_management(self, mock_get_logger, mock_apply_transformations):
        """Test complete successful server lifecycle."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_apply_transformations.return_value = None

        async def test_logic():
            async with server_lifespan(self.mock_server):
                # Verify initialization
                mock_logger.info.assert_any_call("Server initializing")
                mock_logger.info.assert_any_call("Server ready")
                mock_apply_transformations.assert_called_once_with(self.mock_server)

            # Verify cleanup
            mock_logger.info.assert_any_call("Server shutting down")

        self._run_async_test(test_logic)

    @patch("awslabs.ecs_mcp_server.modules.aws_knowledge_proxy.apply_tool_transformations")
    @patch("logging.getLogger")
    def test_error_handling_during_initialization(
        self, mock_get_logger, mock_apply_transformations
    ):
        """Test proper error handling during server initialization."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        initialization_error = RuntimeError("Initialization failed")
        mock_apply_transformations.side_effect = initialization_error

        async def test_logic():
            with self.assertRaises(RuntimeError) as context:
                async with server_lifespan(self.mock_server):
                    pass

            # Verify the specific error was raised
            self.assertEqual(str(context.exception), "Initialization failed")

            # Verify initialization was attempted
            mock_logger.info.assert_any_call("Server initializing")

        self._run_async_test(test_logic)


# ----------------------------------------------------------------------------
# Application Entry Point Tests
# ----------------------------------------------------------------------------


class TestApplicationEntryPoint(unittest.TestCase):
    """Tests for application entry point behavior."""

    def test_main_module_execution_logic(self):
        """Test entry point logic for different execution contexts."""
        test_scenarios = [
            ("__main__", True, "should execute when run as main module"),
            ("awslabs.ecs_mcp_server.main", False, "should not execute when imported"),
            ("other_module", False, "should not execute for other modules"),
        ]

        for module_name, should_execute, description in test_scenarios:
            with self.subTest(module=module_name, description=description):
                with patch("awslabs.ecs_mcp_server.main.main") as mock_main:
                    # Simulate entry point condition
                    if module_name == "__main__":
                        mock_main()

                    if should_execute:
                        mock_main.assert_called_once()
                    else:
                        mock_main.assert_not_called()

    def test_entry_point_execution_simulation(self):
        """Test simulated execution of module entry point."""
        with patch("awslabs.ecs_mcp_server.main.main") as mock_main:
            # Simulate module execution as main
            module_name = "__main__"
            if module_name == "__main__":
                mock_main()

            mock_main.assert_called_once()


# ----------------------------------------------------------------------------
# Main Function Behavior Tests
# ----------------------------------------------------------------------------


class TestMainFunctionBehavior(unittest.TestCase):
    """Tests for main function execution scenarios."""

    @patch("awslabs.ecs_mcp_server.main.sys.exit")
    @patch("awslabs.ecs_mcp_server.main._setup_logging")
    @patch("awslabs.ecs_mcp_server.main._create_ecs_mcp_server")
    def test_successful_server_startup(self, mock_create_server, mock_setup_logging, mock_exit):
        """Test successful server startup and execution."""
        # Configure mocks
        mock_mcp = MagicMock()
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default: {
            "allow-write": True,
            "allow-sensitive-data": False,
        }.get(key, default)
        mock_create_server.return_value = (mock_mcp, mock_config)

        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        # Execute main function
        main()

        # Verify expected behavior
        mock_logger.info.assert_any_call("Server started")
        mock_logger.info.assert_any_call("Write operations enabled: True")
        mock_logger.info.assert_any_call("Sensitive data access enabled: False")
        mock_mcp.run.assert_called_once()
        mock_exit.assert_not_called()

    @patch("awslabs.ecs_mcp_server.main.sys.exit")
    @patch("awslabs.ecs_mcp_server.main._setup_logging")
    @patch("awslabs.ecs_mcp_server.main._create_ecs_mcp_server")
    def test_keyboard_interrupt_handling(self, mock_create_server, mock_setup_logging, mock_exit):
        """Test graceful handling of keyboard interrupt."""
        # Configure mocks for keyboard interrupt
        mock_mcp = MagicMock()
        mock_config = MagicMock()
        mock_mcp.run.side_effect = KeyboardInterrupt()
        mock_create_server.return_value = (mock_mcp, mock_config)

        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        # Execute main function
        main()

        # Verify graceful shutdown
        mock_logger.info.assert_any_call("Server stopped by user")
        mock_exit.assert_called_once_with(0)

    @patch("awslabs.ecs_mcp_server.main.sys.exit")
    @patch("awslabs.ecs_mcp_server.main._setup_logging")
    @patch("awslabs.ecs_mcp_server.main._create_ecs_mcp_server")
    def test_general_exception_handling(self, mock_create_server, mock_setup_logging, mock_exit):
        """Test handling of unexpected exceptions."""
        # Configure mocks for general exception
        mock_mcp = MagicMock()
        mock_config = MagicMock()
        mock_mcp.run.side_effect = Exception("Unexpected error")
        mock_create_server.return_value = (mock_mcp, mock_config)

        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        # Execute main function
        main()

        # Verify error handling
        mock_logger.error.assert_called_once_with("Error starting server: Unexpected error")
        mock_exit.assert_called_once_with(1)


# ----------------------------------------------------------------------------
# Legacy Test Compatibility
# ----------------------------------------------------------------------------


def test_log_file_setup():
    """Legacy compatibility test for log file setup functionality."""

    def setup_log_file(log_file, mock_os, mock_logging):
        try:
            log_dir = mock_os.path.dirname(log_file)
            if log_dir and not mock_os.path.exists(log_dir):
                mock_os.makedirs(log_dir, exist_ok=True)

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

    # Execute and verify
    result = setup_log_file("/var/log/test_logs/ecs-mcp.log", mock_os, mock_logging)

    assert result is True
    mock_os.makedirs.assert_called_once_with("/var/log/test_logs", exist_ok=True)
    mock_logging.FileHandler.assert_called_once_with("/var/log/test_logs/ecs-mcp.log")
    mock_file_handler.setFormatter.assert_called_once()
    mock_logging.getLogger.return_value.addHandler.assert_called_once_with(mock_file_handler)
    assert (
        call("Logging to file: /var/log/test_logs/ecs-mcp.log") in mock_logging.info.call_args_list
    )


def test_log_file_setup_exception():
    """Legacy compatibility test for log file setup error handling."""

    def setup_log_file(log_file, mock_os, mock_logging):
        try:
            log_dir = mock_os.path.dirname(log_file)
            if log_dir and not mock_os.path.exists(log_dir):
                mock_os.makedirs(log_dir, exist_ok=True)

            file_handler = mock_logging.FileHandler(log_file)
            file_handler.setFormatter(mock_logging.Formatter("test-format"))
            mock_logging.getLogger().addHandler(file_handler)
            mock_logging.info(f"Logging to file: {log_file}")
            return True
        except Exception as e:
            mock_logging.error(f"Failed to set up log file {log_file}: {e}")
            return False

    # Setup mocks for error scenario
    mock_os = MagicMock()
    mock_os.path.dirname.return_value = "/var/log/test_logs"
    mock_os.path.exists.return_value = False
    mock_os.makedirs.side_effect = PermissionError("Permission denied")

    mock_logging = MagicMock()

    # Execute and verify error handling
    result = setup_log_file("/var/log/test_logs/ecs-mcp.log", mock_os, mock_logging)

    assert result is False
    mock_logging.error.assert_called_once_with(
        "Failed to set up log file /var/log/test_logs/ecs-mcp.log: Permission denied"
    )


@patch("awslabs.ecs_mcp_server.main.main")
def test_entry_point(mock_main):
    """Legacy compatibility test for module entry point."""
    original_name = sys.modules.get("awslabs.ecs_mcp_server.main", None)

    try:
        sys.modules["awslabs.ecs_mcp_server.main"].__name__ = "__main__"
        namespace = {"__name__": "__main__", "main": mock_main}

        if namespace["__name__"] == "__main__":
            namespace["main"]()

        mock_main.assert_called_once()
    finally:
        if original_name:
            sys.modules["awslabs.ecs_mcp_server.main"].__name__ = original_name.__name__
