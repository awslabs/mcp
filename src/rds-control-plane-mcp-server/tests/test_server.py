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

"""Tests for the RDS Control Plane MCP Server."""

import pytest
from unittest.mock import patch, MagicMock, ANY

from awslabs.rds_control_plane_mcp_server.common.constants import MCP_SERVER_VERSION
from awslabs.rds_control_plane_mcp_server.common.server import mcp, SERVER_INSTRUCTIONS, SERVER_DEPENDENCIES


def test_server_basics():
    """Test basic attributes of the server."""
    assert mcp is not None
    assert isinstance(mcp, object)
    assert hasattr(mcp, 'resource')
    assert callable(mcp.resource)


def test_server_instructions():
    """Test server instructions."""
    assert SERVER_INSTRUCTIONS is not None
    assert isinstance(SERVER_INSTRUCTIONS, str)
    assert 'Amazon RDS' in SERVER_INSTRUCTIONS
    assert len(SERVER_INSTRUCTIONS) > 0


def test_server_dependencies():
    """Test server dependencies."""
    assert SERVER_DEPENDENCIES is not None
    assert isinstance(SERVER_DEPENDENCIES, list)
    assert len(SERVER_DEPENDENCIES) > 0
    assert 'boto3' in SERVER_DEPENDENCIES
    assert 'pydantic' in SERVER_DEPENDENCIES


def test_server_version():
    """Test server version."""
    assert MCP_SERVER_VERSION is not None
    assert isinstance(MCP_SERVER_VERSION, str)
    assert '.' in MCP_SERVER_VERSION


@patch('mcp.server.fastmcp.FastMCP')
def test_resource_decorator(mock_fastmcp):
    """Test the resource decorator."""
    mock_mcp_instance = MagicMock()
    mock_fastmcp.return_value = mock_mcp_instance
    
    def test_func(): pass
    mock_resource_decorator = MagicMock()
    mock_resource_decorator.return_value = test_func
    mock_mcp_instance.resource.return_value = mock_resource_decorator
    
    with patch('awslabs.rds_control_plane_mcp_server.resources.db_cluster.get_cluster_detail.mcp', mock_mcp_instance):
        from awslabs.rds_control_plane_mcp_server.resources.db_cluster.get_cluster_detail import get_cluster_detail
    
    assert callable(get_cluster_detail)
