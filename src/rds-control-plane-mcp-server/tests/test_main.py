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

"""Tests for the main function of the RDS control plane MCP Server."""

import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from awslabs.rds_control_plane_mcp_server.server import main
from awslabs.rds_control_plane_mcp_server.constants import MCP_SERVER_VERSION


@pytest.fixture
def mock_fastmcp():
    """Mock the FastMCP instance used in the server module."""
    with patch('awslabs.rds_control_plane_mcp_server.server.mcp') as mock_mcp:
        yield mock_mcp


@pytest.fixture
def mock_argparse():
    """Mock argparse to simulate command line arguments."""
    with patch('awslabs.rds_control_plane_mcp_server.server.argparse.ArgumentParser', autospec=True) as mock_argparse:
        mock_parser = MagicMock()
        mock_argparse.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.region = 'us-east-1'
        mock_args.readonly = 'true'
        mock_args.profile = None
        mock_args.port = 8888  # Default port
        mock_parser.parse_args.return_value = mock_args
        yield mock_argparse


def test_main_standard_run(mock_fastmcp, mock_argparse):
    """Test that main runs with standard settings."""
    with patch('awslabs.rds_control_plane_mcp_server.server.logger') as mock_logger:
        main()

        mock_logger.info.assert_any_call(f"Starting RDS Control Plane MCP Server v{MCP_SERVER_VERSION}")
        mock_logger.info.assert_any_call("Region: us-east-1")
        mock_logger.info.assert_any_call("Read-only mode: True")
        mock_fastmcp.run.assert_called_once()


def test_main_with_port(mock_fastmcp, mock_argparse):
    """Test that main runs with a custom port."""
    # SSE option has been removed, just test port setting
    mock_argparse.return_value.parse_args.return_value.port = 8888

    with patch('awslabs.rds_control_plane_mcp_server.server.logger') as mock_logger:
        main()

        # Verify the port is set correctly
        assert mock_fastmcp.settings.port == 8888
        # Verify that run is called with default transport (no arguments)
        mock_fastmcp.run.assert_called_once()


def test_main_with_aws_profile(mock_fastmcp, mock_argparse):
    """Test that main sets AWS profile if specified."""
    mock_argparse.return_value.parse_args.return_value.profile = 'test-profile'

    with patch('awslabs.rds_control_plane_mcp_server.server.logger') as mock_logger, \
         patch.dict(os.environ, {}, clear=True):  # Start with empty environment
        main()

        assert os.environ.get('AWS_PROFILE') == 'test-profile'
        mock_logger.info.assert_any_call("AWS Profile: test-profile")


def test_main_with_readonly_false(mock_fastmcp, mock_argparse):
    """Test that main properly handles readonly=false."""
    mock_argparse.return_value.parse_args.return_value.readonly = 'false'

    with patch('awslabs.rds_control_plane_mcp_server.server.logger') as mock_logger:
        main()

        mock_logger.info.assert_any_call("Read-only mode: False")
