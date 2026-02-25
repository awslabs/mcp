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

"""Unit tests for browser session lifecycle tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.session import BrowserSessionTools
from unittest.mock import MagicMock


@pytest.fixture
def session_tools():
    """Create a BrowserSessionTools instance."""
    return BrowserSessionTools()


class TestStartBrowserSession:
    """Tests for start_browser_session tool."""

    async def test_start_session_default_params(
        self, session_tools, mock_ctx, mock_browser_client
    ):
        """Start session with default parameters returns expected response."""
        mock_browser_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'session-123',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {
                    'streamEndpoint': 'wss://automation.example.com/session-123',
                },
                'liveViewStream': {
                    'streamEndpoint': 'https://liveview.example.com/session-123',
                },
            },
            'createdAt': '2025-01-01T00:00:00Z',
        }

        result = await session_tools.start_browser_session(ctx=mock_ctx)

        assert result.session_id == 'session-123'
        assert result.status == 'ACTIVE'
        assert result.browser_identifier == 'aws.browser.v1'
        assert result.automation_stream_url == 'wss://automation.example.com/session-123'
        assert result.live_view_url == 'https://liveview.example.com/session-123'
        assert result.viewport_width == 1456
        assert result.viewport_height == 819
        assert 'started successfully' in result.message

        mock_browser_client.data_plane_client.start_browser_session.assert_called_once_with(
            browserIdentifier='aws.browser.v1',
            sessionTimeoutSeconds=900,
            viewPort={'width': 1456, 'height': 819},
        )

    async def test_start_session_custom_params(self, session_tools, mock_ctx, mock_browser_client):
        """Start session with custom viewport and timeout."""
        mock_browser_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'session-456',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {'streamEndpoint': 'wss://auto.example.com/456'},
                'liveViewStream': {'streamEndpoint': 'https://live.example.com/456'},
            },
            'createdAt': '2025-01-01T00:00:00Z',
        }

        result = await session_tools.start_browser_session(
            ctx=mock_ctx,
            viewport_width=1920,
            viewport_height=1080,
            timeout_seconds=3600,
        )

        assert result.session_id == 'session-456'
        assert result.viewport_width == 1920
        assert result.viewport_height == 1080

        mock_browser_client.data_plane_client.start_browser_session.assert_called_once_with(
            browserIdentifier='aws.browser.v1',
            sessionTimeoutSeconds=3600,
            viewPort={'width': 1920, 'height': 1080},
        )

    async def test_start_session_with_extension(
        self, session_tools, mock_ctx, mock_browser_client
    ):
        """Start session with browser extension S3 URL."""
        mock_browser_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'session-789',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {'streamEndpoint': 'wss://auto.example.com/789'},
                'liveViewStream': {},
            },
            'createdAt': '2025-01-01T00:00:00Z',
        }

        result = await session_tools.start_browser_session(
            ctx=mock_ctx,
            extension_s3_url='s3://my-bucket/extensions/ublock.zip',
        )

        assert result.session_id == 'session-789'
        call_kwargs = mock_browser_client.data_plane_client.start_browser_session.call_args
        assert call_kwargs.kwargs.get('extension') == 's3://my-bucket/extensions/ublock.zip'

    async def test_start_session_api_error(self, session_tools, mock_ctx, mock_browser_client):
        """Start session raises on API error and reports via ctx.error."""
        mock_browser_client.data_plane_client.start_browser_session.side_effect = Exception(
            'AccessDenied'
        )

        with pytest.raises(Exception, match='AccessDenied'):
            await session_tools.start_browser_session(ctx=mock_ctx)

        mock_ctx.error.assert_awaited_once()

    async def test_start_session_missing_streams(
        self, session_tools, mock_ctx, mock_browser_client
    ):
        """Start session handles missing stream endpoints gracefully."""
        mock_browser_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'session-no-streams',
            'streams': {},
            'createdAt': '2025-01-01T00:00:00Z',
        }

        result = await session_tools.start_browser_session(ctx=mock_ctx)

        assert result.session_id == 'session-no-streams'
        assert result.automation_stream_url is None
        assert result.live_view_url is None


class TestGetBrowserSession:
    """Tests for get_browser_session tool."""

    async def test_get_session(self, session_tools, mock_ctx, mock_browser_client):
        """Get session returns correct session metadata."""
        mock_browser_client.get_session.return_value = {
            'sessionId': 'session-123',
            'status': 'READY',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {'streamEndpoint': 'wss://auto.example.com/123'},
                'liveViewStream': {'streamEndpoint': 'https://live.example.com/123'},
            },
            'viewPort': {'width': 1456, 'height': 819},
            'createdAt': '2025-01-01T00:00:00Z',
        }

        result = await session_tools.get_browser_session(
            ctx=mock_ctx,
            session_id='session-123',
        )

        assert result.session_id == 'session-123'
        assert result.status == 'READY'
        assert result.viewport_width == 1456
        assert result.viewport_height == 819
        assert result.automation_stream_url == 'wss://auto.example.com/123'

        mock_browser_client.get_session.assert_called_once_with(
            browser_id='aws.browser.v1',
            session_id='session-123',
        )

    async def test_get_session_not_found(self, session_tools, mock_ctx, mock_browser_client):
        """Get session raises on non-existent session."""
        mock_browser_client.get_session.side_effect = Exception('ResourceNotFoundException')

        with pytest.raises(Exception, match='ResourceNotFoundException'):
            await session_tools.get_browser_session(
                ctx=mock_ctx,
                session_id='nonexistent',
            )

        mock_ctx.error.assert_awaited_once()


class TestStopBrowserSession:
    """Tests for stop_browser_session tool."""

    async def test_stop_session(self, session_tools, mock_ctx, mock_browser_client):
        """Stop session returns TERMINATED status."""
        mock_browser_client.data_plane_client.stop_browser_session.return_value = {}

        result = await session_tools.stop_browser_session(
            ctx=mock_ctx,
            session_id='session-123',
        )

        assert result.session_id == 'session-123'
        assert result.status == 'TERMINATED'
        assert 'terminated' in result.message.lower()

        mock_browser_client.data_plane_client.stop_browser_session.assert_called_once_with(
            browserIdentifier='aws.browser.v1',
            sessionId='session-123',
        )

    async def test_stop_session_api_error(self, session_tools, mock_ctx, mock_browser_client):
        """Stop session raises on API error."""
        mock_browser_client.data_plane_client.stop_browser_session.side_effect = Exception(
            'InternalError'
        )

        with pytest.raises(Exception, match='InternalError'):
            await session_tools.stop_browser_session(
                ctx=mock_ctx,
                session_id='session-123',
            )

        mock_ctx.error.assert_awaited_once()


class TestListBrowserSessions:
    """Tests for list_browser_sessions tool."""

    async def test_list_sessions(self, session_tools, mock_ctx, mock_browser_client):
        """List sessions returns session summaries."""
        mock_browser_client.list_sessions.return_value = {
            'items': [
                {
                    'sessionId': 'session-1',
                    'status': 'ACTIVE',
                    'createdAt': '2025-01-01T00:00:00Z',
                },
                {
                    'sessionId': 'session-2',
                    'status': 'READY',
                    'createdAt': '2025-01-01T01:00:00Z',
                },
            ],
        }

        result = await session_tools.list_browser_sessions(ctx=mock_ctx)

        assert len(result.sessions) == 2
        assert result.sessions[0].session_id == 'session-1'
        assert result.sessions[0].status == 'ACTIVE'
        assert result.sessions[1].session_id == 'session-2'
        assert result.has_more is False
        assert '2 session(s)' in result.message

    async def test_list_sessions_empty(self, session_tools, mock_ctx, mock_browser_client):
        """List sessions returns empty list when no sessions exist."""
        mock_browser_client.list_sessions.return_value = {
            'items': [],
        }

        result = await session_tools.list_browser_sessions(ctx=mock_ctx)

        assert len(result.sessions) == 0
        assert result.has_more is False

    async def test_list_sessions_respects_max_results(
        self, session_tools, mock_ctx, mock_browser_client
    ):
        """List sessions truncates to max_results and sets has_more."""
        sessions_data = [
            {'sessionId': f'session-{i}', 'status': 'ACTIVE', 'createdAt': '2025-01-01T00:00:00Z'}
            for i in range(5)
        ]
        mock_browser_client.list_sessions.return_value = {
            'items': sessions_data,
        }

        result = await session_tools.list_browser_sessions(
            ctx=mock_ctx,
            max_results=3,
        )

        assert len(result.sessions) == 3
        assert result.has_more is True

    async def test_list_sessions_api_error(self, session_tools, mock_ctx, mock_browser_client):
        """List sessions raises on API error."""
        mock_browser_client.list_sessions.side_effect = Exception('ThrottlingException')

        with pytest.raises(Exception, match='ThrottlingException'):
            await session_tools.list_browser_sessions(ctx=mock_ctx)

        mock_ctx.error.assert_awaited_once()


class TestToolRegistration:
    """Tests for tool registration with MCP server."""

    def test_register_tools(self, session_tools):
        """All four session tools are registered."""
        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda fn: fn

        session_tools.register(mock_mcp)

        tool_names = [call.kwargs['name'] for call in mock_mcp.tool.call_args_list]
        assert 'start_browser_session' in tool_names
        assert 'get_browser_session' in tool_names
        assert 'stop_browser_session' in tool_names
        assert 'list_browser_sessions' in tool_names
        assert len(tool_names) == 4
