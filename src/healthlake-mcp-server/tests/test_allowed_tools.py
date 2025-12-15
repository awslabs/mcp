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

"""Tests for allowed_tools functionality in the server."""

import pytest
from unittest.mock import patch, Mock, AsyncMock

from awslabs.healthlake_mcp_server.server import (
    ALL_TOOLS,
    READ_ONLY_TOOLS,
    WRITE_TOOLS,
    ToolHandler,
    create_healthlake_server,
)


class TestAllToolsConstant:
    """Test the ALL_TOOLS constant."""

    def test_all_tools_is_superset_of_readonly(self):
        """Test ALL_TOOLS contains all read-only tools."""
        assert READ_ONLY_TOOLS.issubset(ALL_TOOLS)

    def test_all_tools_is_superset_of_write(self):
        """Test ALL_TOOLS contains all write tools."""
        assert WRITE_TOOLS.issubset(ALL_TOOLS)

    def test_all_tools_equals_readonly_plus_write(self):
        """Test ALL_TOOLS is exactly read-only plus write tools."""
        assert ALL_TOOLS == READ_ONLY_TOOLS | WRITE_TOOLS

    def test_readonly_and_write_no_overlap(self):
        """Test read-only and write tools don't overlap."""
        assert READ_ONLY_TOOLS & WRITE_TOOLS == set()


class TestToolHandlerAllowedTools:
    """Test ToolHandler with allowed_tools parameter."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_allowed_tools_limits_handlers(self, mock_client):
        """Test that allowed_tools limits available handlers."""
        allowed = {'read_fhir_resource', 'search_fhir_resources'}
        handler = ToolHandler(mock_client.return_value, allowed_tools=allowed)

        assert len(handler.handlers) == 2
        assert set(handler.handlers.keys()) == allowed

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_allowed_tools_single_tool(self, mock_client):
        """Test allowed_tools with a single tool."""
        allowed = {'read_fhir_resource'}
        handler = ToolHandler(mock_client.return_value, allowed_tools=allowed)

        assert len(handler.handlers) == 1
        assert 'read_fhir_resource' in handler.handlers

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_allowed_tools_all_tools(self, mock_client):
        """Test allowed_tools with all tools."""
        handler = ToolHandler(mock_client.return_value, allowed_tools=ALL_TOOLS)

        assert len(handler.handlers) == len(ALL_TOOLS)
        assert set(handler.handlers.keys()) == ALL_TOOLS

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_allowed_tools_takes_precedence_over_readonly(self, mock_client):
        """Test that allowed_tools takes precedence over read_only."""
        # Include a write tool even though read_only is True
        allowed = {'read_fhir_resource', 'create_fhir_resource'}
        handler = ToolHandler(mock_client.return_value, read_only=True, allowed_tools=allowed)

        # allowed_tools should take precedence
        assert len(handler.handlers) == 2
        assert 'create_fhir_resource' in handler.handlers

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_allowed_tools_empty_set(self, mock_client):
        """Test allowed_tools with empty set - treated as 'allow all' (falsy value)."""
        # Note: Empty set is falsy in Python, so it's treated the same as None
        # This is intentional - use a non-empty set to restrict tools
        allowed = set()
        handler = ToolHandler(mock_client.return_value, allowed_tools=allowed)

        # Empty set is falsy, so all tools are allowed
        assert len(handler.handlers) == len(ALL_TOOLS)

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_allowed_tools_none_defaults_to_all(self, mock_client):
        """Test that allowed_tools=None allows all tools."""
        handler = ToolHandler(mock_client.return_value, allowed_tools=None)

        assert len(handler.handlers) == len(ALL_TOOLS)

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_allowed_tools_none_with_readonly(self, mock_client):
        """Test that allowed_tools=None respects read_only mode."""
        handler = ToolHandler(mock_client.return_value, read_only=True, allowed_tools=None)

        assert len(handler.handlers) == len(READ_ONLY_TOOLS)
        assert set(handler.handlers.keys()) == READ_ONLY_TOOLS


class TestToolHandlerAllowedToolsExecution:
    """Test tool execution with allowed_tools filtering."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    async def test_allowed_tool_can_execute(self, mock_client):
        """Test that an allowed tool can be executed."""
        allowed = {'list_datastores'}
        handler = ToolHandler(mock_client.return_value, allowed_tools=allowed)

        # Mock the client method as AsyncMock since it's an async method
        mock_client.return_value.list_datastores = AsyncMock(
            return_value={'DatastorePropertiesList': []}
        )

        # Should not raise - tool is allowed
        result = await handler.handle_tool('list_datastores', {})
        assert result is not None

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    async def test_disallowed_tool_raises_error(self, mock_client):
        """Test that a disallowed tool raises an error."""
        allowed = {'read_fhir_resource'}
        handler = ToolHandler(mock_client.return_value, allowed_tools=allowed)

        with pytest.raises(ValueError, match='Unknown tool'):
            await handler.handle_tool('search_fhir_resources', {})

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    async def test_write_tool_blocked_when_not_allowed(self, mock_client):
        """Test that write tools are blocked when not in allowed_tools."""
        allowed = {'read_fhir_resource'}
        handler = ToolHandler(mock_client.return_value, allowed_tools=allowed)

        with pytest.raises(ValueError, match='Unknown tool'):
            await handler.handle_tool('create_fhir_resource', {})


class TestServerCreationWithAllowedTools:
    """Test server creation with allowed_tools parameter."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_create_server_with_allowed_tools(self, mock_client):
        """Test creating server with allowed_tools."""
        allowed = {'read_fhir_resource', 'search_fhir_resources'}
        server = create_healthlake_server(allowed_tools=allowed)
        assert server is not None

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_create_server_allowed_tools_none(self, mock_client):
        """Test creating server with allowed_tools=None (all tools)."""
        server = create_healthlake_server(allowed_tools=None)
        assert server is not None

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_create_server_allowed_tools_with_readonly(self, mock_client):
        """Test creating server with both allowed_tools and read_only."""
        # allowed_tools should take precedence
        allowed = {'read_fhir_resource', 'create_fhir_resource'}
        server = create_healthlake_server(read_only=True, allowed_tools=allowed)
        assert server is not None


class TestToolFilteringLogic:
    """Test the tool filtering logic."""

    def test_filter_to_readonly_equivalent(self):
        """Test filtering to read-only equivalent set."""
        allowed = READ_ONLY_TOOLS.copy()
        filtered = {t for t in ALL_TOOLS if t in allowed}
        assert filtered == READ_ONLY_TOOLS

    def test_filter_to_minimal_set(self):
        """Test filtering to minimal read set."""
        allowed = {'read_fhir_resource', 'search_fhir_resources'}
        filtered = {t for t in ALL_TOOLS if t in allowed}
        assert filtered == allowed

    def test_filter_to_write_only(self):
        """Test filtering to only write tools."""
        allowed = WRITE_TOOLS.copy()
        filtered = {t for t in ALL_TOOLS if t in allowed}
        assert filtered == WRITE_TOOLS

    def test_filter_mixed_tools(self):
        """Test filtering to mixed read and write tools."""
        allowed = {'read_fhir_resource', 'create_fhir_resource', 'list_datastores'}
        filtered = {t for t in ALL_TOOLS if t in allowed}
        assert filtered == allowed


class TestToolHandlerAttributes:
    """Test ToolHandler attribute initialization with allowed_tools."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_handler_stores_allowed_tools(self, mock_client):
        """Test that handler stores allowed_tools attribute."""
        allowed = {'read_fhir_resource'}
        handler = ToolHandler(mock_client.return_value, allowed_tools=allowed)

        assert handler.allowed_tools == allowed

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_handler_stores_none_allowed_tools(self, mock_client):
        """Test that handler stores None for allowed_tools."""
        handler = ToolHandler(mock_client.return_value, allowed_tools=None)

        assert handler.allowed_tools is None

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_handler_readonly_still_stored(self, mock_client):
        """Test that read_only is still stored with allowed_tools."""
        allowed = {'read_fhir_resource'}
        handler = ToolHandler(mock_client.return_value, read_only=True, allowed_tools=allowed)

        assert handler.read_only is True
        assert handler.allowed_tools == allowed


class TestEdgeCases:
    """Test edge cases for allowed_tools."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_allowed_tools_with_unknown_tool_name(self, mock_client):
        """Test allowed_tools with an unknown tool name - it just won't match."""
        allowed = {'read_fhir_resource', 'nonexistent_tool'}
        handler = ToolHandler(mock_client.return_value, allowed_tools=allowed)

        # Only the valid tool should be in handlers
        assert 'read_fhir_resource' in handler.handlers
        assert 'nonexistent_tool' not in handler.handlers
        assert len(handler.handlers) == 1

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_allowed_tools_datastore_operations(self, mock_client):
        """Test allowed_tools with only datastore operations."""
        allowed = {'list_datastores', 'get_datastore_details'}
        handler = ToolHandler(mock_client.return_value, allowed_tools=allowed)

        assert len(handler.handlers) == 2
        assert 'list_datastores' in handler.handlers
        assert 'get_datastore_details' in handler.handlers

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_allowed_tools_job_operations(self, mock_client):
        """Test allowed_tools with only job operations."""
        allowed = {'list_fhir_jobs', 'start_fhir_import_job', 'start_fhir_export_job'}
        handler = ToolHandler(mock_client.return_value, allowed_tools=allowed)

        assert len(handler.handlers) == 3
        for tool in allowed:
            assert tool in handler.handlers

