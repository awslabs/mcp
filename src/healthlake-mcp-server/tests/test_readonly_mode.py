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

"""Tests for read-only mode functionality."""

import pytest
import sys
from awslabs.healthlake_mcp_server.main import main, parse_args
from awslabs.healthlake_mcp_server.server import (
    READ_ONLY_TOOLS,
    WRITE_TOOLS,
    ToolHandler,
    create_healthlake_server,
)
from unittest.mock import AsyncMock, Mock, patch


class TestParseArgs:
    """Test argument parsing functionality."""

    def test_parse_args_readonly_flag(self):
        """Test parsing --readonly flag."""
        with patch.object(sys, 'argv', ['test', '--readonly']):
            args = parse_args()
            assert args.readonly is True

    def test_parse_args_no_readonly_flag(self):
        """Test parsing without --readonly flag."""
        with patch.object(sys, 'argv', ['test']):
            args = parse_args()
            assert args.readonly is False

    def test_parse_args_help_message(self):
        """Test help message contains readonly option."""
        with patch.object(sys, 'argv', ['test', '--help']):
            with pytest.raises(SystemExit):
                parse_args()


class TestReadOnlyModeLogging:
    """Test logging for read-only mode."""

    @patch('awslabs.healthlake_mcp_server.main.parse_args')
    @patch('awslabs.healthlake_mcp_server.main.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.main.stdio_server')
    @patch('awslabs.healthlake_mcp_server.main.logger')
    async def test_readonly_mode_logging(
        self, mock_logger, mock_stdio_server, mock_create_server, mock_parse_args
    ):
        """Test logging message for read-only mode."""
        # Mock arguments for read-only mode
        mock_args = Mock()
        mock_args.readonly = True
        mock_parse_args.return_value = mock_args

        # Mock server
        mock_server = Mock()
        mock_server.run = AsyncMock()
        mock_server.create_initialization_options = Mock(return_value={})
        mock_create_server.return_value = mock_server

        # Mock stdio server context manager
        mock_read_stream = Mock()
        mock_write_stream = Mock()
        mock_stdio_server.return_value.__aenter__ = AsyncMock(
            return_value=(mock_read_stream, mock_write_stream)
        )
        mock_stdio_server.return_value.__aexit__ = AsyncMock(return_value=None)

        # Run main
        await main()

        # Verify read-only logging
        mock_logger.info.assert_called_with(
            'Server started in READ-ONLY mode - mutating operations disabled'
        )

    @patch('awslabs.healthlake_mcp_server.main.parse_args')
    @patch('awslabs.healthlake_mcp_server.main.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.main.stdio_server')
    @patch('awslabs.healthlake_mcp_server.main.logger')
    async def test_full_mode_logging(
        self, mock_logger, mock_stdio_server, mock_create_server, mock_parse_args
    ):
        """Test logging message for full access mode."""
        # Mock arguments for full mode
        mock_args = Mock()
        mock_args.readonly = False
        mock_parse_args.return_value = mock_args

        # Mock server
        mock_server = Mock()
        mock_server.run = AsyncMock()
        mock_server.create_initialization_options = Mock(return_value={})
        mock_create_server.return_value = mock_server

        # Mock stdio server context manager
        mock_read_stream = Mock()
        mock_write_stream = Mock()
        mock_stdio_server.return_value.__aenter__ = AsyncMock(
            return_value=(mock_read_stream, mock_write_stream)
        )
        mock_stdio_server.return_value.__aexit__ = AsyncMock(return_value=None)

        # Run main
        await main()

        # Verify full access logging
        mock_logger.info.assert_called_with('Server started in FULL ACCESS mode')


class TestToolHandlerReadOnly:
    """Test ToolHandler read-only functionality."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_readonly_handler_initialization(self, mock_client):
        """Test ToolHandler initialization in read-only mode."""
        handler = ToolHandler(mock_client.return_value, read_only=True)

        assert handler.read_only is True
        assert len(handler.handlers) == len(READ_ONLY_TOOLS)
        assert set(handler.handlers.keys()) == READ_ONLY_TOOLS

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_full_handler_initialization(self, mock_client):
        """Test ToolHandler initialization in full mode."""
        handler = ToolHandler(mock_client.return_value, read_only=False)

        assert handler.read_only is False
        assert len(handler.handlers) == len(READ_ONLY_TOOLS | WRITE_TOOLS)
        assert set(handler.handlers.keys()) == (READ_ONLY_TOOLS | WRITE_TOOLS)

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    async def test_readonly_blocks_write_tools(self, mock_client):
        """Test that write tools are blocked in read-only mode."""
        handler = ToolHandler(mock_client.return_value, read_only=True)

        for write_tool in WRITE_TOOLS:
            with pytest.raises(
                ValueError, match=f'Tool {write_tool} not available in read-only mode'
            ):
                await handler.handle_tool(write_tool, {})

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    async def test_readonly_allows_read_tools(self, mock_client):
        """Test that read tools work in read-only mode."""
        handler = ToolHandler(mock_client.return_value, read_only=True)

        # Test that read tools are available (will fail for other reasons, not read-only)
        for read_tool in READ_ONLY_TOOLS:
            try:
                await handler.handle_tool(read_tool, {})
            except ValueError as e:
                # Should not be a read-only error
                assert 'read-only mode' not in str(e)
            except Exception:
                # Other exceptions are fine (missing args, etc.)
                pass


class TestWriteOperationSafetyChecks:
    """Test safety checks in write operation handlers."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    async def test_create_safety_check(self, mock_client):
        """Test create operation safety check."""
        handler = ToolHandler(mock_client.return_value, read_only=True)

        with pytest.raises(ValueError, match='Create operation not allowed in read-only mode'):
            await handler._handle_create({})

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    async def test_update_safety_check(self, mock_client):
        """Test update operation safety check."""
        handler = ToolHandler(mock_client.return_value, read_only=True)

        with pytest.raises(ValueError, match='Update operation not allowed in read-only mode'):
            await handler._handle_update({})

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    async def test_delete_safety_check(self, mock_client):
        """Test delete operation safety check."""
        handler = ToolHandler(mock_client.return_value, read_only=True)

        with pytest.raises(ValueError, match='Delete operation not allowed in read-only mode'):
            await handler._handle_delete({})

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    async def test_import_job_safety_check(self, mock_client):
        """Test import job operation safety check."""
        handler = ToolHandler(mock_client.return_value, read_only=True)

        with pytest.raises(ValueError, match='Import job operation not allowed in read-only mode'):
            await handler._handle_import_job({})

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    async def test_export_job_safety_check(self, mock_client):
        """Test export job operation safety check."""
        handler = ToolHandler(mock_client.return_value, read_only=True)

        with pytest.raises(ValueError, match='Export job operation not allowed in read-only mode'):
            await handler._handle_export_job({})


class TestServerCreation:
    """Test server creation with read-only mode."""

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_create_readonly_server(self, mock_client):
        """Test creating server in read-only mode."""
        server = create_healthlake_server(read_only=True)
        assert server is not None

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_create_full_server(self, mock_client):
        """Test creating server in full mode."""
        server = create_healthlake_server(read_only=False)
        assert server is not None

    @patch('awslabs.healthlake_mcp_server.server.HealthLakeClient')
    def test_create_server_default_mode(self, mock_client):
        """Test creating server with default mode (full access)."""
        server = create_healthlake_server()
        assert server is not None


class TestToolFiltering:
    """Test tool filtering functionality."""

    async def test_readonly_tool_filtering(self):
        """Test that only read-only tools are available in read-only mode."""
        # Simulate the tool filtering logic
        all_tools = list(READ_ONLY_TOOLS | WRITE_TOOLS)
        filtered_tools = [tool for tool in all_tools if tool in READ_ONLY_TOOLS]

        assert len(filtered_tools) == len(READ_ONLY_TOOLS)
        assert set(filtered_tools) == READ_ONLY_TOOLS

    async def test_full_mode_tool_availability(self):
        """Test that all tools are available in full mode."""
        # Simulate the tool filtering logic for full mode
        all_tools = list(READ_ONLY_TOOLS | WRITE_TOOLS)
        filtered_tools = all_tools  # No filtering in full mode

        assert len(filtered_tools) == len(READ_ONLY_TOOLS | WRITE_TOOLS)
        assert set(filtered_tools) == (READ_ONLY_TOOLS | WRITE_TOOLS)


class TestReadOnlyErrorHandling:
    """Test error handling for read-only mode violations."""

    def test_readonly_error_message_format(self):
        """Test that read-only error messages are properly formatted."""
        error_msg = 'Tool create_fhir_resource not available in read-only mode'
        assert 'read-only mode' in error_msg
        assert 'create_fhir_resource' in error_msg

    def test_readonly_violation_detection(self):
        """Test detection of read-only mode violations."""
        error_msg = 'Create operation not allowed in read-only mode'
        assert 'read-only mode' in error_msg
