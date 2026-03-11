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
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.session import BrowserSessionTools
from unittest.mock import AsyncMock, MagicMock


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

    async def test_start_session_with_extensions(
        self, session_tools, mock_ctx, mock_browser_client
    ):
        """Start session with browser extensions from S3."""
        from bedrock_agentcore.tools.config import BrowserExtension, ExtensionS3Location

        mock_browser_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'session-789',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {'streamEndpoint': 'wss://auto.example.com/789'},
                'liveViewStream': {},
            },
            'createdAt': '2025-01-01T00:00:00Z',
        }

        exts = [
            BrowserExtension(
                s3_location=ExtensionS3Location(
                    bucket='my-bucket',
                    prefix='extensions/ublock.zip',
                )
            )
        ]
        result = await session_tools.start_browser_session(
            ctx=mock_ctx,
            extensions=exts,
        )

        assert result.session_id == 'session-789'
        call_kwargs = mock_browser_client.data_plane_client.start_browser_session.call_args
        assert call_kwargs.kwargs.get('extensions') == [
            {'location': {'s3': {'bucket': 'my-bucket', 'prefix': 'extensions/ublock.zip'}}}
        ]

    async def test_start_session_with_proxy_configuration(
        self, session_tools, mock_ctx, mock_browser_client
    ):
        """Start session with proxy configuration."""
        from bedrock_agentcore.tools.config import ExternalProxy, ProxyConfiguration

        mock_browser_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'session-proxy',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {'streamEndpoint': 'wss://auto.example.com/proxy'},
                'liveViewStream': {},
            },
            'createdAt': '2025-01-01T00:00:00Z',
        }

        proxy_config = ProxyConfiguration(
            proxies=[ExternalProxy(server='proxy.example.com', port=8080)],
            bypass_patterns=['.amazonaws.com'],
        )
        result = await session_tools.start_browser_session(
            ctx=mock_ctx,
            proxy_configuration=proxy_config,
        )

        assert result.session_id == 'session-proxy'
        call_kwargs = mock_browser_client.data_plane_client.start_browser_session.call_args
        assert call_kwargs.kwargs.get('proxyConfiguration') == {
            'proxies': [{'externalProxy': {'server': 'proxy.example.com', 'port': 8080}}],
            'bypass': {'domainPatterns': ['.amazonaws.com']},
        }

    async def test_start_session_with_profile_configuration(
        self, session_tools, mock_ctx, mock_browser_client
    ):
        """Start session with browser profile for persistent state."""
        from bedrock_agentcore.tools.config import ProfileConfiguration

        mock_browser_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'session-profile',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {'streamEndpoint': 'wss://auto.example.com/profile'},
                'liveViewStream': {},
            },
            'createdAt': '2025-01-01T00:00:00Z',
        }

        profile_config = ProfileConfiguration(profile_identifier='my-ecommerce-profile')
        result = await session_tools.start_browser_session(
            ctx=mock_ctx,
            profile_configuration=profile_config,
        )

        assert result.session_id == 'session-profile'
        call_kwargs = mock_browser_client.data_plane_client.start_browser_session.call_args
        assert call_kwargs.kwargs.get('profileConfiguration') == {
            'profileIdentifier': 'my-ecommerce-profile',
        }

    async def test_start_session_api_error(self, session_tools, mock_ctx, mock_browser_client):
        """Start session raises on API error and reports via ctx.error."""
        mock_browser_client.data_plane_client.start_browser_session.side_effect = Exception(
            'AccessDenied'
        )

        with pytest.raises(Exception, match='AccessDenied'):
            await session_tools.start_browser_session(ctx=mock_ctx)

        mock_ctx.error.assert_awaited_once()

    async def test_start_session_viewport_out_of_bounds(
        self, session_tools, mock_ctx, mock_browser_client
    ):
        """Start session with viewport out of bounds raises ValueError."""
        with pytest.raises(ValueError, match='out of bounds'):
            await session_tools.start_browser_session(
                ctx=mock_ctx, viewport_width=50, viewport_height=50
            )

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

    async def test_stop_session_no_connection_manager(self, mock_ctx, mock_browser_client):
        """Stop session with no connection_manager skips disconnect."""
        tools = BrowserSessionTools(connection_manager=None, snapshot_manager=MagicMock())
        mock_browser_client.data_plane_client.stop_browser_session.return_value = {}

        result = await tools.stop_browser_session(ctx=mock_ctx, session_id='session-123')

        assert result.status == 'TERMINATED'

    async def test_stop_session_no_snapshot_manager(self, mock_ctx, mock_browser_client):
        """Stop session with no snapshot_manager skips cleanup."""
        mock_cm = MagicMock()
        mock_cm.disconnect = AsyncMock()
        tools = BrowserSessionTools(connection_manager=mock_cm, snapshot_manager=None)
        mock_browser_client.data_plane_client.stop_browser_session.return_value = {}

        result = await tools.stop_browser_session(ctx=mock_ctx, session_id='session-123')

        assert result.status == 'TERMINATED'
        mock_cm.disconnect.assert_awaited_once()

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


class TestStartSessionAutoConnect:
    """Tests for auto-connect Playwright on session start."""

    async def test_start_session_auto_connects_playwright(self, mock_ctx, mock_browser_client):
        """Start session with connection_manager auto-connects Playwright."""
        mock_cm = MagicMock()
        mock_cm.connect = AsyncMock()
        sm = MagicMock()
        tools = BrowserSessionTools(connection_manager=mock_cm, snapshot_manager=sm)

        mock_browser_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'sess-auto',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {'streamEndpoint': 'wss://auto.example.com/sess-auto'},
                'liveViewStream': {},
            },
            'createdAt': '2025-01-01T00:00:00Z',
        }

        result = await tools.start_browser_session(ctx=mock_ctx)

        assert result.session_id == 'sess-auto'
        mock_cm.connect.assert_awaited_once()
        call_args = mock_cm.connect.call_args
        assert call_args.args[0] == 'sess-auto'
        assert call_args.kwargs['browser_identifier'] == 'aws.browser.v1'
        assert call_args.kwargs['region']  # region is set (value depends on env)

    async def test_start_session_region_consistent(self, mock_ctx, monkeypatch):
        """API client and Playwright connect use the same resolved region."""
        captured_regions = []

        def fake_get_client(region=None):
            captured_regions.append(region)
            client = MagicMock()
            client.data_plane_client.start_browser_session.return_value = {
                'sessionId': 'sess-region',
                'browserIdentifier': 'aws.browser.v1',
                'streams': {
                    'automationStream': {'streamEndpoint': 'wss://auto.example.com/sess'},
                    'liveViewStream': {},
                },
                'createdAt': '2025-01-01T00:00:00Z',
            }
            return client

        monkeypatch.setattr(
            'awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.session.get_browser_client',
            fake_get_client,
        )

        mock_cm = MagicMock()
        mock_cm.connect = AsyncMock()
        tools = BrowserSessionTools(connection_manager=mock_cm, snapshot_manager=MagicMock())

        await tools.start_browser_session(ctx=mock_ctx, region='ap-southeast-1')

        # API client gets the explicit region
        assert captured_regions == ['ap-southeast-1']
        # Playwright connect gets the same region
        assert mock_cm.connect.call_args.kwargs['region'] == 'ap-southeast-1'


class TestStartSessionOrphanCleanup:
    """Tests for orphaned session cleanup when Playwright connect fails."""

    async def test_start_session_stops_orphan_on_connect_failure(
        self, mock_ctx, mock_browser_client
    ):
        """If Playwright connect fails, the cloud session is stopped to avoid leaking it."""
        mock_cm = MagicMock()
        mock_cm.connect = AsyncMock(side_effect=Exception('CDP connection refused'))
        tools = BrowserSessionTools(connection_manager=mock_cm, snapshot_manager=MagicMock())

        mock_browser_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'sess-orphan',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {'streamEndpoint': 'wss://auto.example.com/sess-orphan'},
                'liveViewStream': {},
            },
            'createdAt': '2025-01-01T00:00:00Z',
        }

        with pytest.raises(Exception, match='CDP connection refused'):
            await tools.start_browser_session(ctx=mock_ctx)

        # Verify the orphaned session was stopped
        mock_browser_client.data_plane_client.stop_browser_session.assert_called_once_with(
            browserIdentifier='aws.browser.v1', sessionId='sess-orphan'
        )

    async def test_start_session_orphan_cleanup_failure_still_raises_original(
        self, mock_ctx, mock_browser_client
    ):
        """If both connect and orphan cleanup fail, the original connect error is raised."""
        mock_cm = MagicMock()
        mock_cm.connect = AsyncMock(side_effect=Exception('CDP timeout'))
        mock_browser_client.data_plane_client.stop_browser_session.side_effect = Exception(
            'StopSession failed'
        )
        tools = BrowserSessionTools(connection_manager=mock_cm, snapshot_manager=MagicMock())

        mock_browser_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'sess-orphan2',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {'streamEndpoint': 'wss://auto.example.com/sess-orphan2'},
                'liveViewStream': {},
            },
            'createdAt': '2025-01-01T00:00:00Z',
        }

        with pytest.raises(Exception, match='CDP timeout'):
            await tools.start_browser_session(ctx=mock_ctx)


class TestToStr:
    """Tests for _to_str helper."""

    def test_to_str_with_string(self):
        """String values pass through unchanged."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.session import _to_str

        assert _to_str('hello') == 'hello'

    def test_to_str_with_none(self):
        """None returns empty string."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.session import _to_str

        assert _to_str(None) == ''

    def test_to_str_converts_datetime(self):
        """Non-string values (like datetime) are converted via str()."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.session import _to_str
        from datetime import datetime, timezone

        dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = _to_str(dt)
        assert '2025' in result
        assert isinstance(result, str)


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
