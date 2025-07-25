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

from awslabs.rds_control_plane_mcp_server.common.constants import MCP_SERVER_VERSION
from awslabs.rds_control_plane_mcp_server.common.server import (
    SERVER_DEPENDENCIES,
    SERVER_INSTRUCTIONS,
    mcp,
)
from mcp.server.fastmcp import FastMCP


class TestServerConfiguration:
    """Test server configuration constants."""

    def test_server_version(self):
        """Test server version is defined."""
        assert MCP_SERVER_VERSION == '0.1.0'

    def test_server_instructions(self):
        """Test server instructions content."""
        assert SERVER_INSTRUCTIONS is not None
        assert isinstance(SERVER_INSTRUCTIONS, str)
        assert 'Amazon RDS' in SERVER_INSTRUCTIONS
        assert len(SERVER_INSTRUCTIONS) > 0

    def test_server_dependencies(self):
        """Test server dependencies list."""
        expected_deps = ['pydantic', 'loguru', 'boto3', 'mypy-boto3-rds', 'mypy-boto3-cloudwatch']
        assert SERVER_DEPENDENCIES == expected_deps
        assert all(dep in SERVER_DEPENDENCIES for dep in expected_deps)


class TestMCPInstance:
    """Test MCP server instance."""

    def test_mcp_instance_creation(self):
        """Test MCP instance is properly created."""
        assert mcp is not None
        assert isinstance(mcp, FastMCP)

    def test_mcp_has_required_methods(self):
        """Test MCP instance has required methods."""
        assert hasattr(mcp, 'resource')
        assert hasattr(mcp, 'tool')
        assert callable(mcp.resource)
        assert callable(mcp.tool)
