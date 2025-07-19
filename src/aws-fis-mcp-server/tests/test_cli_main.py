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

"""Tests for CLI argument parsing and main function."""

import awslabs.aws_fis_mcp_server.server as server_module
import pytest
import sys
from awslabs.aws_fis_mcp_server.server import main
from unittest.mock import patch


class TestCliMain:
    """Test cases for CLI argument parsing and main function."""

    @patch('awslabs.aws_fis_mcp_server.server.mcp.run')
    @patch('awslabs.aws_fis_mcp_server.server.initialize_aws_clients')
    @patch('awslabs.aws_fis_mcp_server.server.logger')
    def test_main_default_arguments(self, mock_logger, mock_initialize, mock_mcp_run):
        """Test main function with default arguments."""
        with patch.object(sys, 'argv', ['aws-fis-mcp-server']):
            main()

        # With default arguments, initialize_aws_clients should not be called
        # because clients are initialized at module level
        mock_initialize.assert_not_called()

        # Verify logging calls
        mock_logger.info.assert_any_call(
            'AWS FIS MCP Server starting with AWS_PROFILE: %s, AWS_REGION: %s, ALLOW_WRITES: %s',
            'default',
            'us-east-1',
            False,
        )
        mock_logger.info.assert_any_call('AWS FIS MCP server starting')

        # Verify MCP server was started
        mock_mcp_run.assert_called_once()

    @patch('awslabs.aws_fis_mcp_server.server.mcp.run')
    @patch('awslabs.aws_fis_mcp_server.server.initialize_aws_clients')
    @patch('awslabs.aws_fis_mcp_server.server.logger')
    def test_main_with_all_arguments(self, mock_logger, mock_initialize, mock_mcp_run):
        """Test main function with all CLI arguments provided."""
        test_args = [
            'aws-fis-mcp-server',
            '--aws-profile',
            'test-profile',
            '--aws-region',
            'eu-west-1',
            '--allow-writes',
        ]

        with patch.object(sys, 'argv', test_args):
            main()

        # Verify AWS clients were initialized with provided arguments
        mock_initialize.assert_called_once_with('eu-west-1', 'test-profile')

        # Verify logging calls with correct values
        mock_logger.info.assert_any_call(
            'AWS FIS MCP Server starting with AWS_PROFILE: %s, AWS_REGION: %s, ALLOW_WRITES: %s',
            'test-profile',
            'eu-west-1',
            True,
        )

        # Verify global variables were set correctly
        assert server_module.allow_writes
        assert server_module.aws_profile_override == 'test-profile'
        assert server_module.aws_region_override == 'eu-west-1'

    @patch('awslabs.aws_fis_mcp_server.server.mcp.run')
    @patch('awslabs.aws_fis_mcp_server.server.initialize_aws_clients')
    @patch('awslabs.aws_fis_mcp_server.server.logger')
    @patch.dict('os.environ', {'AWS_REGION': 'us-west-2'})
    def test_main_with_environment_region(self, mock_logger, mock_initialize, mock_mcp_run):
        """Test main function uses environment variable for region."""
        with patch.object(sys, 'argv', ['aws-fis-mcp-server']):
            main()

        # With only environment variable set, initialize_aws_clients should not be called
        # because no custom CLI parameters were provided
        mock_initialize.assert_not_called()

    @patch('awslabs.aws_fis_mcp_server.server.mcp.run')
    @patch('awslabs.aws_fis_mcp_server.server.initialize_aws_clients')
    @patch('awslabs.aws_fis_mcp_server.server.logger')
    @patch.dict('os.environ', {'AWS_REGION': 'us-west-2'})
    def test_main_cli_overrides_environment(self, mock_logger, mock_initialize, mock_mcp_run):
        """Test CLI argument overrides environment variable."""
        test_args = ['aws-fis-mcp-server', '--aws-region', 'ap-southeast-1']

        with patch.object(sys, 'argv', test_args):
            main()

        # CLI argument provided, so initialize_aws_clients should be called
        mock_initialize.assert_called_once_with('ap-southeast-1', None)

    @patch('awslabs.aws_fis_mcp_server.server.mcp.run')
    @patch('awslabs.aws_fis_mcp_server.server.initialize_aws_clients')
    @patch('awslabs.aws_fis_mcp_server.server.logger')
    def test_main_profile_only(self, mock_logger, mock_initialize, mock_mcp_run):
        """Test main function with only profile argument."""
        test_args = ['aws-fis-mcp-server', '--aws-profile', 'production']

        with patch.object(sys, 'argv', test_args):
            main()

        # Should use profile with default region
        mock_initialize.assert_called_once_with('us-east-1', 'production')

        # Verify logging
        mock_logger.info.assert_any_call(
            'AWS FIS MCP Server starting with AWS_PROFILE: %s, AWS_REGION: %s, ALLOW_WRITES: %s',
            'production',
            'us-east-1',
            False,
        )

    @patch('awslabs.aws_fis_mcp_server.server.mcp.run')
    @patch('awslabs.aws_fis_mcp_server.server.initialize_aws_clients')
    @patch('awslabs.aws_fis_mcp_server.server.logger')
    def test_main_region_only(self, mock_logger, mock_initialize, mock_mcp_run):
        """Test main function with only region argument."""
        test_args = ['aws-fis-mcp-server', '--aws-region', 'ca-central-1']

        with patch.object(sys, 'argv', test_args):
            main()

        # Should use region with default profile (None)
        mock_initialize.assert_called_once_with('ca-central-1', None)

    @patch('awslabs.aws_fis_mcp_server.server.mcp.run')
    @patch('awslabs.aws_fis_mcp_server.server.initialize_aws_clients')
    @patch('awslabs.aws_fis_mcp_server.server.logger')
    def test_main_allow_writes_only(self, mock_logger, mock_initialize, mock_mcp_run):
        """Test main function with only allow-writes flag."""
        test_args = ['aws-fis-mcp-server', '--allow-writes']

        with patch.object(sys, 'argv', test_args):
            main()

        # With only --allow-writes flag, initialize_aws_clients should not be called
        # because no custom region or profile parameters were provided
        mock_initialize.assert_not_called()

        # Verify allow_writes was set to True
        assert server_module.allow_writes

        mock_logger.info.assert_any_call(
            'AWS FIS MCP Server starting with AWS_PROFILE: %s, AWS_REGION: %s, ALLOW_WRITES: %s',
            'default',
            'us-east-1',
            True,
        )

    @patch('awslabs.aws_fis_mcp_server.server.mcp.run')
    @patch('awslabs.aws_fis_mcp_server.server.initialize_aws_clients')
    def test_main_initialization_error_propagates(self, mock_initialize, mock_mcp_run):
        """Test that initialization errors are propagated when custom parameters are provided."""
        mock_initialize.side_effect = Exception('AWS initialization failed')

        # Use custom region to trigger initialize_aws_clients call
        with patch.object(sys, 'argv', ['aws-fis-mcp-server', '--aws-region', 'us-west-1']):
            with pytest.raises(Exception, match='AWS initialization failed'):
                main()

        # initialize_aws_clients should have been called due to custom region
        mock_initialize.assert_called_once_with('us-west-1', None)
        # MCP server should not start if initialization fails
        mock_mcp_run.assert_not_called()

    def test_main_argument_parser_help(self):
        """Test that argument parser help works correctly."""
        test_args = ['aws-fis-mcp-server', '--help']

        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Help should exit with code 0
            assert exc_info.value.code == 0

    def test_main_invalid_argument(self):
        """Test handling of invalid arguments."""
        test_args = ['aws-fis-mcp-server', '--invalid-argument']

        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Invalid argument should exit with non-zero code
            assert exc_info.value.code != 0
