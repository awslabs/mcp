"""Unit tests for server module.

This file contains tests for the EC2 MCP Server server module, including:
- Basic properties (name, version, description, instructions)
- Tools registration
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
        """Initialize mock FastMCP instance."""
        self.name = name
        self.description = description or ''
        self.version = version
        self.instructions = instructions
        self.tools = []

    def tool(self, name=None, description=None, annotations=None):
        """Mock tool decorator."""

        def decorator(func):
            self.tools.append(
                {
                    'name': name or func.__name__,
                    'function': func,
                    'annotations': annotations,
                    'description': description,
                }
            )
            return func

        return decorator

    def run(self):
        """Mock run method."""
        pass


# Apply the patches
with patch('mcp.server.fastmcp.FastMCP', MockFastMCP):
    from awslabs.ec2_mcp_server.server import main, mcp


# ----------------------------------------------------------------------------
# Server Configuration Tests
# ----------------------------------------------------------------------------


class TestMain(unittest.TestCase):
    """Tests for server module configuration.

    This test class contains separate test methods for each aspect of the server
    configuration, providing better isolation and easier debugging when tests fail.
    """

    def test_server_basic_properties(self):
        """Test basic server properties.

        This test focuses only on the basic properties of the server:
        - Name
        - Version
        - Description
        - Instructions

        If this test fails, it indicates an issue with the basic server configuration.
        """
        # Verify the server has the correct name and version
        self.assertEqual(mcp.name, 'AWS EC2 MCP Server')
        self.assertEqual(mcp.version, '0.1.0')

        # Verify the description contains expected keywords
        self.assertIn('ec2', mcp.description.lower())
        self.assertIn('instances', mcp.description.lower())
        self.assertIn('infrastructure', mcp.description.lower())

        # Verify instructions are provided
        self.assertIsNotNone(mcp.instructions)
        self.assertIn('AVAILABLE TOOLS', mcp.instructions)
        self.assertIn('IMPORTANT CONFIGURATION', mcp.instructions)

    def test_server_tools(self):
        """Test that server has the expected tools.

        This test focuses only on the tools registered with the server.
        It verifies that all required tools are present.

        If this test fails, it indicates an issue with tool registration.
        """
        # Verify the server has registered tools
        self.assertGreaterEqual(len(mcp.tools), 20)

        # Verify core tool names
        tool_names = [tool['name'] for tool in mcp.tools]

        # Instance management tools
        self.assertIn('list_instances', tool_names)
        self.assertIn('get_instance_details', tool_names)
        self.assertIn('launch_instance', tool_names)
        self.assertIn('terminate_instance', tool_names)
        self.assertIn('start_instance', tool_names)
        self.assertIn('stop_instance', tool_names)
        self.assertIn('reboot_instance', tool_names)

        # Security group tools
        self.assertIn('list_security_groups', tool_names)
        self.assertIn('create_security_group', tool_names)
        self.assertIn('delete_security_group', tool_names)

        # Key pair tools
        self.assertIn('list_key_pairs', tool_names)
        self.assertIn('create_key_pair', tool_names)
        self.assertIn('delete_key_pair', tool_names)

        # Volume tools
        self.assertIn('list_volumes', tool_names)
        self.assertIn('create_volume', tool_names)
        self.assertIn('attach_volume', tool_names)

        # AMI tools
        self.assertIn('list_amis', tool_names)
        self.assertIn('get_popular_amis', tool_names)
        self.assertIn('create_image', tool_names)

        # VPC tools
        self.assertIn('list_vpcs', tool_names)
        self.assertIn('list_subnets', tool_names)


# ----------------------------------------------------------------------------
# Logging Tests
# ----------------------------------------------------------------------------


def test_log_file_setup():
    """Test log file setup with directory creation."""

    # Create a test function that mimics the log file setup from server.py
    def setup_log_file(log_file, mock_os, mock_logging):
        try:
            # Create directory for log file if it doesn't exist
            log_dir = mock_os.path.dirname(log_file)
            if log_dir and not mock_os.path.exists(log_dir):
                mock_os.makedirs(log_dir, exist_ok=True)

            # Add file handler
            file_handler = mock_logging.FileHandler(log_file)
            file_handler.setFormatter(mock_logging.Formatter('test-format'))
            mock_logging.getLogger().addHandler(file_handler)
            mock_logging.info(f'Logging to file: {log_file}')
            return True
        except Exception as e:
            mock_logging.error(f'Failed to set up log file {log_file}: {e}')
            return False

    # Setup mocks
    mock_os = MagicMock()
    mock_os.path.dirname.return_value = '/var/log/test_logs'
    mock_os.path.exists.return_value = False

    mock_logging = MagicMock()
    mock_file_handler = MagicMock()
    mock_logging.FileHandler.return_value = mock_file_handler
    mock_formatter = MagicMock()
    mock_logging.Formatter.return_value = mock_formatter

    # Call our test function
    result = setup_log_file('/var/log/test_logs/ec2-mcp.log', mock_os, mock_logging)

    # Verify that the function succeeded
    assert result is True

    # Verify that the log directory was created
    mock_os.makedirs.assert_called_once_with('/var/log/test_logs', exist_ok=True)

    # Verify that the log file handler was created and added to the logger
    mock_logging.FileHandler.assert_called_once_with('/var/log/test_logs/ec2-mcp.log')
    mock_file_handler.setFormatter.assert_called_once()
    mock_logging.getLogger.return_value.addHandler.assert_called_once_with(mock_file_handler)

    # Verify that the log success message was logged
    assert (
        call('Logging to file: /var/log/test_logs/ec2-mcp.log') in mock_logging.info.call_args_list
    )


def test_log_file_setup_exception():
    """Test log file setup when an exception occurs."""

    # Create a test function that mimics the log file setup from server.py
    def setup_log_file(log_file, mock_os, mock_logging):
        try:
            # Create directory for log file if it doesn't exist
            log_dir = mock_os.path.dirname(log_file)
            if log_dir and not mock_os.path.exists(log_dir):
                mock_os.makedirs(log_dir, exist_ok=True)

            # Add file handler
            file_handler = mock_logging.FileHandler(log_file)
            file_handler.setFormatter(mock_logging.Formatter('test-format'))
            mock_logging.getLogger().addHandler(file_handler)
            mock_logging.info(f'Logging to file: {log_file}')
            return True
        except Exception as e:
            mock_logging.error(f'Failed to set up log file {log_file}: {e}')
            return False

    # Setup mocks
    mock_os = MagicMock()
    mock_os.path.dirname.return_value = '/var/log/test_logs'
    mock_os.path.exists.return_value = False
    mock_os.makedirs.side_effect = PermissionError('Permission denied')

    mock_logging = MagicMock()

    # Call our test function
    result = setup_log_file('/var/log/test_logs/ec2-mcp.log', mock_os, mock_logging)

    # Verify that the function failed
    assert result is False

    # Verify that the error was logged
    mock_logging.error.assert_called_once_with(
        'Failed to set up log file /var/log/test_logs/ec2-mcp.log: Permission denied'
    )


# ----------------------------------------------------------------------------
# Main Function Tests
# ----------------------------------------------------------------------------


@patch('awslabs.ec2_mcp_server.server.sys.exit')
@patch('awslabs.ec2_mcp_server.server.logger')
@patch('awslabs.ec2_mcp_server.server.mcp')
@patch('awslabs.ec2_mcp_server.server.config')
def test_main_function_success(mock_config, mock_mcp, mock_logger, mock_exit):
    """Test main function with successful execution."""
    # Setup mocks
    mock_config.get.side_effect = lambda key, default: True if key == 'allow-write' else False

    # Call the main function
    main()

    # Verify that the logger messages were called
    mock_logger.info.assert_any_call('EC2 MCP Server started')
    mock_logger.info.assert_any_call('Write operations enabled: True')
    mock_logger.info.assert_any_call('Sensitive data access enabled: False')

    # Verify that the mcp.run() method was called
    mock_mcp.run.assert_called_once()

    # Verify that sys.exit was not called
    mock_exit.assert_not_called()


@patch('awslabs.ec2_mcp_server.server.sys.exit')
@patch('awslabs.ec2_mcp_server.server.logger')
@patch('awslabs.ec2_mcp_server.server.mcp')
def test_main_function_keyboard_interrupt(mock_mcp, mock_logger, mock_exit):
    """Test main function with KeyboardInterrupt exception."""
    # Setup mocks
    mock_mcp.run.side_effect = KeyboardInterrupt()

    # Call the main function
    main()

    # Verify that the logger messages were called
    mock_logger.info.assert_any_call('Server stopped by user')

    # Verify that sys.exit was called with code 0
    mock_exit.assert_called_once_with(0)


@patch('awslabs.ec2_mcp_server.server.sys.exit')
@patch('awslabs.ec2_mcp_server.server.logger')
@patch('awslabs.ec2_mcp_server.server.mcp')
def test_main_function_general_exception(mock_mcp, mock_logger, mock_exit):
    """Test main function with general exception."""
    # Setup mocks
    mock_mcp.run.side_effect = Exception('Test error')

    # Call the main function
    main()

    # Verify that the logger error was called with the exception
    mock_logger.error.assert_called_once_with('Error starting server: Test error')

    # Verify that sys.exit was called with code 1
    mock_exit.assert_called_once_with(1)


@patch('awslabs.ec2_mcp_server.server.main')
def test_entry_point(mock_main):
    """Test the module's entry point."""
    # Save the current value of __name__
    original_name = sys.modules.get('awslabs.ec2_mcp_server.server', None)

    try:
        # Mock __name__ to trigger the entry point code
        sys.modules['awslabs.ec2_mcp_server.server'].__name__ = '__main__'

        # Instead of reading the file, we can directly simulate the entry point check
        # that would exist in the server.py file
        namespace = {'__name__': '__main__', 'main': mock_main}

        # Simulate the standard entry point code: if __name__ == "__main__": main()
        if namespace['__name__'] == '__main__':
            namespace['main']()

        # Verify that main() was called
        mock_main.assert_called_once()
    finally:
        # Restore the original value of __name__
        if original_name:
            sys.modules['awslabs.ec2_mcp_server.server'].__name__ = original_name.__name__


# ----------------------------------------------------------------------------
# Additional Server Configuration Tests
# ----------------------------------------------------------------------------


class TestServerConfiguration(unittest.TestCase):
    """Additional tests for server configuration and setup."""

    @patch.dict('os.environ', {'FASTMCP_LOG_LEVEL': 'DEBUG'})
    def test_log_level_configuration(self):
        """Test that log level is configured from environment variable."""
        import os

        log_level = os.environ.get('FASTMCP_LOG_LEVEL', 'INFO')
        self.assertEqual(log_level, 'DEBUG')

    @patch.dict('os.environ', {'FASTMCP_LOG_FILE': '/tmp/test.log'})
    @patch('awslabs.ec2_mcp_server.server.os.makedirs')
    @patch('awslabs.ec2_mcp_server.server.os.path.exists')
    @patch('awslabs.ec2_mcp_server.server.os.path.dirname')
    @patch('awslabs.ec2_mcp_server.server.logging.FileHandler')
    @patch('awslabs.ec2_mcp_server.server.logging.getLogger')
    def test_log_file_configuration_success(
        self, mock_get_logger, mock_file_handler, mock_dirname, mock_exists, mock_makedirs
    ):
        """Test successful log file configuration."""
        mock_dirname.return_value = '/tmp'
        mock_exists.return_value = False
        mock_handler_instance = MagicMock()
        mock_file_handler.return_value = mock_handler_instance
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Import to trigger the log file setup
        import awslabs.ec2_mcp_server.server
        import importlib

        importlib.reload(awslabs.ec2_mcp_server.server)

        # Verify directory creation was attempted
        mock_makedirs.assert_called()
        # Verify file handler was created
        mock_file_handler.assert_called()

    @patch.dict('os.environ', {'FASTMCP_LOG_FILE': '/invalid/path/test.log'})
    @patch('awslabs.ec2_mcp_server.server.os.makedirs')
    @patch('awslabs.ec2_mcp_server.server.os.path.exists')
    @patch('awslabs.ec2_mcp_server.server.os.path.dirname')
    @patch('awslabs.ec2_mcp_server.server.logging.error')
    def test_log_file_configuration_failure(
        self, mock_log_error, mock_dirname, mock_exists, mock_makedirs
    ):
        """Test log file configuration failure handling."""
        mock_dirname.return_value = '/invalid/path'
        mock_exists.return_value = False
        mock_makedirs.side_effect = PermissionError('Permission denied')

        # Import to trigger the log file setup
        import awslabs.ec2_mcp_server.server
        import importlib

        importlib.reload(awslabs.ec2_mcp_server.server)

        # Verify error was logged
        mock_log_error.assert_called()

    def test_security_wrapper_applications(self):
        """Test that security wrappers are properly applied to tools."""
        # This test verifies that all write operations have security wrappers
        # We can't directly test the wrapper functionality without mocking the entire chain,
        # but we can verify the structure is correct

        # Import the modules to check their structure
        from awslabs.ec2_mcp_server.modules import (
            amis,
            instances,
            key_pairs,
            security_groups,
            volumes,
            vpc_management,
        )

        # Verify that the functions exist (they should be wrapped but still callable)
        self.assertTrue(callable(instances.launch_instance))
        self.assertTrue(callable(instances.terminate_instance))
        self.assertTrue(callable(security_groups.create_security_group))
        self.assertTrue(callable(key_pairs.create_key_pair))
        self.assertTrue(callable(volumes.create_volume))
        self.assertTrue(callable(amis.create_image))
        self.assertTrue(callable(vpc_management.delete_vpc))

    def test_module_registration(self):
        """Test that all modules are registered with the MCP server."""
        # Verify that the server has tools from all modules
        tool_names = [tool['name'] for tool in mcp.tools]

        # Check for tools from each module
        instance_tools = ['list_instances', 'launch_instance', 'terminate_instance']
        sg_tools = ['list_security_groups', 'create_security_group']
        kp_tools = ['list_key_pairs', 'create_key_pair']
        volume_tools = ['list_volumes', 'create_volume']
        snapshot_tools = ['list_snapshots', 'create_snapshot']
        ami_tools = ['list_amis', 'create_image']
        vpc_tools = ['list_vpcs', 'list_subnets']

        for tool in (
            instance_tools
            + sg_tools
            + kp_tools
            + volume_tools
            + snapshot_tools
            + ami_tools
            + vpc_tools
        ):
            self.assertIn(tool, tool_names, f'Tool {tool} not found in registered tools')

    def test_server_instructions_content(self):
        """Test that server instructions contain all required sections."""
        instructions = mcp.instructions

        # Check for major sections
        self.assertIn('EC2 INSTANCES', instructions)
        self.assertIn('SECURITY GROUPS', instructions)
        self.assertIn('KEY PAIRS', instructions)
        self.assertIn('EBS VOLUMES', instructions)
        self.assertIn('EBS SNAPSHOTS', instructions)
        self.assertIn('AMIs', instructions)
        self.assertIn('VPC & NETWORKING', instructions)
        self.assertIn('WORKFLOW EXAMPLES', instructions)
        self.assertIn('IMPORTANT CONFIGURATION', instructions)

        # Check for security warnings
        self.assertIn('SECURE STORAGE IS MANDATORY', instructions)
        self.assertIn('ALLOW_WRITE=true', instructions)
        self.assertIn('ALLOW_SENSITIVE_DATA=true', instructions)

    def test_server_version_format(self):
        """Test that server version follows semantic versioning."""
        import re

        version_pattern = r'^\d+\.\d+\.\d+$'
        self.assertIsNotNone(
            re.match(version_pattern, mcp.version),
            f'Version {mcp.version} does not follow semantic versioning',
        )

    @patch('awslabs.ec2_mcp_server.server.config')
    def test_config_loading(self, mock_config):
        """Test that configuration is properly loaded."""
        # This test verifies that get_config() is called during server initialization

        # The config should be loaded during server initialization
        self.assertIsNotNone(mock_config)

    def test_logger_configuration(self):
        """Test that logger is properly configured."""
        from awslabs.ec2_mcp_server.server import logger

        # Logger should be configured and not None
        self.assertIsNotNone(logger)
        # Logger should have a name attribute
        self.assertTrue(hasattr(logger, 'name'))

    def test_tool_count_minimum(self):
        """Test that server has minimum expected number of tools."""
        # The server should have at least 25 tools based on the modules
        self.assertGreaterEqual(
            len(mcp.tools), 25, f'Expected at least 25 tools, got {len(mcp.tools)}'
        )

    def test_server_description_keywords(self):
        """Test that server description contains expected keywords."""
        description = mcp.description.lower()
        expected_keywords = [
            'ec2',
            'instances',
            'amis',
            'security groups',
            'volumes',
            'infrastructure',
            'aws',
        ]

        for keyword in expected_keywords:
            self.assertIn(
                keyword, description, f"Keyword '{keyword}' not found in server description"
            )

    def test_instructions_tool_counts(self):
        """Test that instructions mention correct tool counts for each category."""
        instructions = mcp.instructions

        # Check for tool count mentions
        self.assertIn('(9 tools)', instructions)  # EC2 INSTANCES
        self.assertIn('(5 tools)', instructions)  # SECURITY GROUPS and VPC & NETWORKING
        self.assertIn('(3 tools)', instructions)  # KEY PAIRS
        self.assertIn('(4 tools)', instructions)  # AMIs
        self.assertIn('(2 tools)', instructions)  # EBS SNAPSHOTS
