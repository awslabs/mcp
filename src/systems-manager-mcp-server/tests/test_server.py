# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for server.py."""

import argparse
import logging
import os
import sys
from unittest.mock import Mock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from awslabs.systems_manager_mcp_server import server


class TestServerModule:
    """Test server module components."""

    def test_mcp_server_creation(self):
        """Test that MCP server is created with correct configuration."""
        assert server.mcp is not None
        assert server.mcp.name == 'awslabs.systems-manager-mcp-server'
        assert 'AWS Systems Manager MCP Server' in server.mcp.instructions
        assert 'pydantic' in server.mcp.dependencies
        assert 'boto3' in server.mcp.dependencies
        assert 'mcp' in server.mcp.dependencies

    def test_mcp_server_instructions_content(self):
        """Test that MCP server instructions contain expected content."""
        instructions = server.mcp.instructions
        assert 'Document Management' in instructions
        assert 'Automation Execution' in instructions
        assert 'Command Execution' in instructions
        assert 'Security & Compliance' in instructions
        assert 'list_documents' in instructions
        assert 'create_document' in instructions
        assert 'Environment Variables' in instructions

    @patch('awslabs.systems_manager_mcp_server.tools.documents.register_tools')
    @patch('awslabs.systems_manager_mcp_server.tools.automation.register_tools')
    @patch('awslabs.systems_manager_mcp_server.tools.commands.register_tools')
    def test_tools_registration(self, mock_commands, mock_automation, mock_documents):
        """Test that all tools are registered with the MCP server."""
        # Import the module to trigger registration
        import importlib

        importlib.reload(server)

        # Verify all register_tools functions were called
        mock_documents.assert_called_once()
        mock_automation.assert_called_once()
        mock_commands.assert_called_once()


class TestMainFunction:
    """Test main function and CLI argument parsing."""

    @patch('awslabs.systems_manager_mcp_server.server.mcp')
    @patch('awslabs.systems_manager_mcp_server.server.Context')
    @patch('awslabs.systems_manager_mcp_server.server.logger')
    def test_main_default_arguments(self, mock_logger, mock_context_class, mock_mcp):
        """Test main function with default arguments."""
        mock_context = Mock()
        mock_context_class.return_value = mock_context

        with patch('sys.argv', ['server.py']):
            server.main()

        # Verify context was created
        mock_context_class.assert_called_once()

        # Verify MCP server was started
        mock_mcp.run.assert_called_once()

        # Verify logging
        mock_logger.info.assert_called()

    @patch('awslabs.systems_manager_mcp_server.server.mcp')
    @patch('awslabs.systems_manager_mcp_server.server.Context')
    @patch('awslabs.systems_manager_mcp_server.server.logger')
    def test_main_readonly_argument(self, mock_logger, mock_context_class, mock_mcp):
        """Test main function with readonly argument."""
        mock_context = Mock()
        mock_context_class.return_value = mock_context

        with patch('sys.argv', ['server.py', '--readonly']):
            server.main()

        # Verify readonly mode was set
        mock_context.set_readonly.assert_called_once_with(True)
        mock_mcp.run.assert_called_once()

    @patch('awslabs.systems_manager_mcp_server.server.mcp')
    @patch('awslabs.systems_manager_mcp_server.server.Context')
    @patch('awslabs.systems_manager_mcp_server.server.logger')
    def test_main_allow_write_argument(self, mock_logger, mock_context_class, mock_mcp):
        """Test main function with allow-write argument."""
        mock_context = Mock()
        mock_context_class.return_value = mock_context

        with patch('sys.argv', ['server.py', '--allow-write']):
            server.main()

        # Verify readonly mode was disabled
        mock_context.set_readonly.assert_called_once_with(False)
        mock_mcp.run.assert_called_once()

    @patch('awslabs.systems_manager_mcp_server.server.mcp')
    @patch('awslabs.systems_manager_mcp_server.server.Context')
    @patch('awslabs.systems_manager_mcp_server.server.logger')
    def test_main_aws_configuration_arguments(self, mock_logger, mock_context_class, mock_mcp):
        """Test main function with AWS configuration arguments."""
        mock_context = Mock()
        mock_context_class.return_value = mock_context

        with patch(
            'sys.argv', ['server.py', '--region', 'us-west-2', '--profile', 'test-profile']
        ):
            server.main()

        # Verify AWS configuration was set
        mock_context.set_aws_region.assert_called_once_with('us-west-2')
        mock_context.set_aws_profile.assert_called_once_with('test-profile')
        mock_mcp.run.assert_called_once()

    @patch('awslabs.systems_manager_mcp_server.server.mcp')
    @patch('awslabs.systems_manager_mcp_server.server.Context')
    @patch('awslabs.systems_manager_mcp_server.server.logger')
    @patch('logging.getLogger')
    def test_main_log_level_argument(
        self, mock_get_logger, mock_logger, mock_context_class, mock_mcp
    ):
        """Test main function with log level argument."""
        mock_context = Mock()
        mock_context_class.return_value = mock_context
        mock_root_logger = Mock()
        mock_get_logger.return_value = mock_root_logger

        with patch('sys.argv', ['server.py', '--log-level', 'DEBUG']):
            server.main()

        # Verify log level was set
        mock_context.set_log_level.assert_called_once_with('DEBUG')
        mock_root_logger.setLevel.assert_called_once_with(logging.DEBUG)
        mock_mcp.run.assert_called_once()

    @patch('awslabs.systems_manager_mcp_server.server.mcp')
    @patch('awslabs.systems_manager_mcp_server.server.Context')
    @patch('awslabs.systems_manager_mcp_server.server.logger')
    def test_main_all_arguments(self, mock_logger, mock_context_class, mock_mcp):
        """Test main function with all arguments."""
        mock_context = Mock()
        mock_context.is_readonly.return_value = False
        mock_context._aws_region = 'us-east-1'
        mock_context._aws_profile = 'default'
        mock_context._log_level = 'INFO'
        mock_context_class.return_value = mock_context

        with patch(
            'sys.argv',
            [
                'server.py',
                '--allow-write',
                '--region',
                'us-east-1',
                '--profile',
                'default',
                '--log-level',
                'INFO',
                '--allow-sensitive-data-access',
            ],
        ):
            server.main()

        # Verify all configurations were set
        mock_context.set_readonly.assert_called_once_with(False)
        mock_context.set_aws_region.assert_called_once_with('us-east-1')
        mock_context.set_aws_profile.assert_called_once_with('default')
        mock_context.set_log_level.assert_called_once_with('INFO')

        # Verify logging output
        mock_logger.info.assert_any_call('Starting AWS Systems Manager MCP Server')
        mock_logger.info.assert_any_call('Read-only mode: False')
        mock_logger.info.assert_any_call('AWS Region: us-east-1')
        mock_logger.info.assert_any_call('AWS Profile: default')
        mock_logger.info.assert_any_call('Log Level: INFO')

        mock_mcp.run.assert_called_once()


class TestArgumentParser:
    """Test argument parser configuration."""

    def test_argument_parser_creation(self):
        """Test that argument parser is created with correct configuration."""
        parser = argparse.ArgumentParser(
            description='AWS Systems Manager MCP Server',
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Add arguments like in main function
        parser.add_argument('--readonly', action='store_true')
        parser.add_argument('--region', type=str)
        parser.add_argument('--profile', type=str)
        parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        parser.add_argument('--allow-write', action='store_true')
        parser.add_argument('--allow-sensitive-data-access', action='store_true')

        # Test parsing various argument combinations
        args = parser.parse_args(['--readonly'])
        assert args.readonly is True
        assert args.allow_write is False

        args = parser.parse_args(['--region', 'us-west-2', '--profile', 'test'])
        assert args.region == 'us-west-2'
        assert args.profile == 'test'

        args = parser.parse_args(['--log-level', 'DEBUG'])
        assert args.log_level == 'DEBUG'

        args = parser.parse_args(['--allow-write', '--allow-sensitive-data-access'])
        assert args.allow_write is True
        assert args.allow_sensitive_data_access is True


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_logger_creation(self):
        """Test that logger is created with correct name."""
        assert server.logger is not None
        assert server.logger.name == 'awslabs.systems_manager_mcp_server.server'
