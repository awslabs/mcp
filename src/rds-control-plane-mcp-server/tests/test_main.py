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

"""Tests for the RDS Control Plane MCP Server main module."""

import os
import pytest
from unittest.mock import patch, MagicMock, ANY

from awslabs.rds_control_plane_mcp_server.common.constants import MCP_SERVER_VERSION
from awslabs.rds_control_plane_mcp_server.common.server import mcp, SERVER_INSTRUCTIONS, SERVER_DEPENDENCIES


def test_mcp_server_version():
    """Test that the MCP server version is set correctly."""
    assert MCP_SERVER_VERSION is not None
    assert isinstance(MCP_SERVER_VERSION, str)
    # Version should follow semantic versioning
    assert len(MCP_SERVER_VERSION.split('.')) >= 2


def test_mcp_server_instructions():
    """Test that the MCP server instructions are set correctly."""
    assert SERVER_INSTRUCTIONS is not None
    assert isinstance(SERVER_INSTRUCTIONS, str)
    assert len(SERVER_INSTRUCTIONS) > 0
    
    # Instructions should contain key information about the server
    assert 'Amazon RDS' in SERVER_INSTRUCTIONS
    assert 'database' in SERVER_INSTRUCTIONS.lower()
    assert any(keyword in SERVER_INSTRUCTIONS.lower() for keyword in ['instance', 'cluster'])


def test_mcp_server_dependencies():
    """Test that the MCP server dependencies are set correctly."""
    assert SERVER_DEPENDENCIES is not None
    assert isinstance(SERVER_DEPENDENCIES, list)
    assert len(SERVER_DEPENDENCIES) > 0
    
    # Check for required dependencies
    assert 'boto3' in SERVER_DEPENDENCIES
    assert 'pydantic' in SERVER_DEPENDENCIES
    assert 'loguru' in SERVER_DEPENDENCIES


def test_mcp_object():
    """Test the mcp object."""
    assert mcp is not None
    assert hasattr(mcp, 'resource')
    assert callable(mcp.resource)


@patch.dict(os.environ, {'AWS_REGION': 'us-west-2'})
def test_environment_variables():
    """Test that the server respects environment variables."""
    # Import connection manager to test environment variables
    from awslabs.rds_control_plane_mcp_server.common.connection import RDSConnectionManager
    
    # Reset connection to ensure it's recreated with our environment variables
    RDSConnectionManager._client = None
    
    with patch('boto3.Session') as mock_session:
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client
        
        # Call get_connection to trigger session creation with environment variables
        RDSConnectionManager.get_connection()
        
        # Verify the session was created with the region from environment variables
        mock_session.assert_called_once()
        args, kwargs = mock_session.call_args
        assert kwargs['region_name'] == 'us-west-2'
