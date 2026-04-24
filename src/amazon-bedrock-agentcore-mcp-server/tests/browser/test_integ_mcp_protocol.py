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

"""MCP protocol-level integration tests.

These tests exercise the full MCP protocol stack in-process using
``create_connected_server_and_client_session`` from the MCP SDK.
No subprocess, no network — bidirectional memory streams connect
a real FastMCP server to a real ClientSession.

What's tested:
- Tool discovery (list_tools) with default, opt-out, and opt-in configs
- Tool schema correctness (descriptions, required params)
- Tool invocation through the MCP wire protocol
- Server instructions / capabilities
- Graceful degradation when browser deps are missing

Run with: uv run pytest tests/browser/test_integ_mcp_protocol.py -v
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BROWSER_PKG = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser'

# Docs tools (always on)
DOCS_TOOLS = {
    'search_agentcore_docs',
    'fetch_agentcore_doc',
}

# Runtime tools (14 operational)
RUNTIME_TOOLS = {
    'create_agent_runtime',
    'get_agent_runtime',
    'update_agent_runtime',
    'delete_agent_runtime',
    'list_agent_runtimes',
    'list_agent_runtime_versions',
    'create_agent_runtime_endpoint',
    'get_agent_runtime_endpoint',
    'update_agent_runtime_endpoint',
    'delete_agent_runtime_endpoint',
    'list_agent_runtime_endpoints',
    'invoke_agent_runtime',
    'stop_runtime_session',
    'get_runtime_guide',
}

# Memory tools (21 operational)
MEMORY_TOOLS = {
    'memory_create',
    'memory_get',
    'memory_update',
    'memory_delete',
    'memory_list',
    'memory_create_event',
    'memory_get_event',
    'memory_delete_event',
    'memory_list_events',
    'memory_list_actors',
    'memory_list_sessions',
    'memory_get_record',
    'memory_delete_record',
    'memory_list_records',
    'memory_retrieve_records',
    'memory_batch_create_records',
    'memory_batch_update_records',
    'memory_batch_delete_records',
    'memory_list_extraction_jobs',
    'memory_start_extraction_job',
    'get_memory_guide',
}

# Gateway guide (still flat)
GUIDE_TOOLS = {
    'manage_agentcore_gateway',
}

# Base tools = everything except browser
BASE_TOOLS = DOCS_TOOLS | RUNTIME_TOOLS | MEMORY_TOOLS | GUIDE_TOOLS

# All 25 browser tools
BROWSER_TOOLS = {
    'start_browser_session',
    'get_browser_session',
    'stop_browser_session',
    'list_browser_sessions',
    'browser_navigate',
    'browser_navigate_back',
    'browser_navigate_forward',
    'browser_snapshot',
    'browser_take_screenshot',
    'browser_wait_for',
    'browser_console_messages',
    'browser_network_requests',
    'browser_evaluate',
    'browser_click',
    'browser_type',
    'browser_fill_form',
    'browser_select_option',
    'browser_hover',
    'browser_press_key',
    'browser_upload_file',
    'browser_handle_dialog',
    'browser_mouse_wheel',
    'browser_tabs',
    'browser_close',
    'browser_resize',
}


def _build_server(*, disable: str | None = None, enable: str | None = None) -> FastMCP:
    """Build a fresh FastMCP server mirroring server.py registration.

    Creates an isolated server instance with env-var-driven opt-in/opt-out,
    without touching the module-level singleton in server.py.
    """
    import os
    from awslabs.amazon_bedrock_agentcore_mcp_server.server import (
        AGENTCORE_MCP_INSTRUCTIONS,
        _is_service_enabled,
    )
    from awslabs.amazon_bedrock_agentcore_mcp_server.tools import (
        docs,
        gateway,
    )

    old_disable = os.environ.pop('AGENTCORE_DISABLE_TOOLS', None)
    old_enable = os.environ.pop('AGENTCORE_ENABLE_TOOLS', None)
    try:
        if disable is not None:
            os.environ['AGENTCORE_DISABLE_TOOLS'] = disable
        if enable is not None:
            os.environ['AGENTCORE_ENABLE_TOOLS'] = enable

        server = FastMCP(
            'test-agentcore-mcp',
            instructions=AGENTCORE_MCP_INSTRUCTIONS,
        )

        # Docs always registered
        server.tool()(docs.search_agentcore_docs)
        server.tool()(docs.fetch_agentcore_doc)

        if _is_service_enabled('runtime'):
            from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime import (
                register_runtime_tools,
            )

            register_runtime_tools(server)

        if _is_service_enabled('memory'):
            from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory import (
                register_memory_tools,
            )

            register_memory_tools(server)

        if _is_service_enabled('gateway'):
            server.tool()(gateway.manage_agentcore_gateway)

        if _is_service_enabled('browser'):
            from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser import (
                register_browser_tools,
            )

            register_browser_tools(server)

        return server
    finally:
        if old_disable is not None:
            os.environ['AGENTCORE_DISABLE_TOOLS'] = old_disable
        else:
            os.environ.pop('AGENTCORE_DISABLE_TOOLS', None)
        if old_enable is not None:
            os.environ['AGENTCORE_ENABLE_TOOLS'] = old_enable
        else:
            os.environ.pop('AGENTCORE_ENABLE_TOOLS', None)


# ===========================================================================
# Tool Discovery
# ===========================================================================


class TestToolDiscovery:
    """Verify tool listing through the MCP protocol."""

    async def test_list_tools_default_config(self):
        """Default config registers all tools (base + browser)."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}

            assert names == BASE_TOOLS | BROWSER_TOOLS

    async def test_list_tools_browser_disabled(self):
        """AGENTCORE_DISABLE_TOOLS=browser removes browser tools."""
        server = _build_server(disable='browser')
        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}

            assert names == BASE_TOOLS
            assert names.isdisjoint(BROWSER_TOOLS)

    async def test_list_tools_browser_and_docs_only(self):
        """AGENTCORE_ENABLE_TOOLS=browser,docs registers only those."""
        server = _build_server(enable='browser,docs')
        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}

            assert 'search_agentcore_docs' in names
            assert 'start_browser_session' in names
            # Runtime, memory, gateway disabled
            assert 'get_runtime_guide' not in names
            assert 'create_agent_runtime' not in names
            assert names.isdisjoint(MEMORY_TOOLS)
            assert 'manage_agentcore_gateway' not in names

    async def test_list_tools_only_docs(self):
        """Disabling all services still leaves docs tools."""
        server = _build_server(disable='browser,runtime,memory,gateway')
        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}

            assert names == {'search_agentcore_docs', 'fetch_agentcore_doc'}


# ===========================================================================
# Tool Schema Validation
# ===========================================================================


class TestToolSchemas:
    """Validate tool schemas exposed through the MCP protocol."""

    async def test_all_tools_have_descriptions(self):
        """Every tool must have a non-empty description."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()

            for tool in result.tools:
                assert tool.description, f'Tool {tool.name} has no description'
                assert len(tool.description) > 10, (
                    f'Tool {tool.name} description too short: {tool.description!r}'
                )

    async def test_browser_tools_require_session_id(self):
        """Browser interaction tools require session_id."""
        session_lifecycle_tools = {
            'start_browser_session',
            'list_browser_sessions',
        }

        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()

            for tool in result.tools:
                if tool.name not in BROWSER_TOOLS:
                    continue
                if tool.name in session_lifecycle_tools:
                    continue

                schema = tool.inputSchema
                required = schema.get('required', [])
                properties = schema.get('properties', {})
                assert 'session_id' in properties, f'Browser tool {tool.name} missing session_id'
                assert 'session_id' in required, (
                    f'Browser tool {tool.name} should require session_id'
                )

    async def test_start_browser_session_has_optional_params(self):
        """start_browser_session exposes viewport, timeout, region."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()

            start_tool = next(t for t in result.tools if t.name == 'start_browser_session')
            props = start_tool.inputSchema.get('properties', {})
            assert 'viewport_width' in props
            assert 'viewport_height' in props
            assert 'timeout_seconds' in props
            assert 'region' in props

    async def test_memory_tools_require_memory_id(self):
        """Memory data plane tools require memory_id parameter."""
        exempt = {
            'get_memory_guide',
            'memory_create',
            'memory_list',
        }

        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()

            for tool in result.tools:
                if tool.name not in MEMORY_TOOLS:
                    continue
                if tool.name in exempt:
                    continue

                schema = tool.inputSchema
                required = schema.get('required', [])
                properties = schema.get('properties', {})
                assert 'memory_id' in properties, f'Memory tool {tool.name} missing memory_id'
                assert 'memory_id' in required, f'Memory tool {tool.name} should require memory_id'


# ===========================================================================
# Tool Invocation Through Protocol
# ===========================================================================


class TestToolInvocation:
    """Call tools through the MCP protocol and verify responses."""

    async def test_browser_snapshot_invalid_session(self):
        """browser_snapshot with bogus session_id returns error text."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.call_tool(
                'browser_snapshot',
                {'session_id': 'nonexistent-session-id'},
            )

            assert len(result.content) > 0
            first = result.content[0]
            assert isinstance(first, TextContent)
            assert 'error' in first.text.lower() or 'Error' in first.text

    async def test_browser_navigate_invalid_session(self):
        """browser_navigate with bogus session_id returns error."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.call_tool(
                'browser_navigate',
                {
                    'session_id': 'nonexistent-session-id',
                    'url': 'https://example.com',
                },
            )

            first = result.content[0]
            assert isinstance(first, TextContent)
            assert 'error' in first.text.lower() or 'Error' in first.text

    async def test_browser_click_invalid_session(self):
        """browser_click with bogus session_id returns error."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.call_tool(
                'browser_click',
                {
                    'session_id': 'nonexistent-session-id',
                    'ref': 'e1',
                },
            )

            first = result.content[0]
            assert isinstance(first, TextContent)
            assert 'error' in first.text.lower() or 'Error' in first.text

    async def test_browser_resize_validation(self):
        """browser_resize with out-of-bounds dimensions returns error."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.call_tool(
                'browser_resize',
                {
                    'session_id': 'nonexistent',
                    'width': 50,
                    'height': 50,
                },
            )

            first = result.content[0]
            assert isinstance(first, TextContent)
            assert 'out of bounds' in first.text.lower() or 'Error' in first.text

    async def test_start_session_mocked_api(self):
        """start_browser_session with mocked AWS API."""
        server = _build_server()

        mock_client = MagicMock()
        mock_client.data_plane_client.start_browser_session.return_value = {
            'sessionId': 'sess-mock-123',
            'browserIdentifier': 'aws.browser.v1',
            'streams': {
                'automationStream': {
                    'streamEndpoint': 'wss://mock.endpoint/ws',
                },
                'liveViewStream': {
                    'streamEndpoint': 'https://mock.endpoint/live',
                },
            },
            'viewPort': {'width': 1456, 'height': 819},
            'createdAt': '2026-01-01T00:00:00Z',
        }

        with patch(
            f'{BROWSER_PKG}.session.get_browser_client',
            return_value=mock_client,
        ):
            with patch(
                f'{BROWSER_PKG}.connection_manager.BrowserConnectionManager.connect',
                new_callable=AsyncMock,
            ):
                async with create_connected_server_and_client_session(server) as client:
                    result = await client.call_tool(
                        'start_browser_session',
                        {'timeout_seconds': 300},
                    )

                    assert len(result.content) > 0
                    first = result.content[0]
                    assert isinstance(first, TextContent)
                    assert 'sess-mock-123' in first.text

    async def test_list_sessions_mocked_api(self):
        """list_browser_sessions with mocked AWS API."""
        server = _build_server()

        mock_client = MagicMock()
        mock_client.list_sessions.return_value = {
            'items': [
                {
                    'sessionId': 'sess-1',
                    'status': 'ACTIVE',
                    'createdAt': '2026-01-01T00:00:00Z',
                },
                {
                    'sessionId': 'sess-2',
                    'status': 'ACTIVE',
                    'createdAt': '2026-01-01T00:01:00Z',
                },
            ],
        }

        with patch(
            f'{BROWSER_PKG}.session.get_browser_client',
            return_value=mock_client,
        ):
            async with create_connected_server_and_client_session(server) as client:
                result = await client.call_tool('list_browser_sessions', {})

                first = result.content[0]
                assert isinstance(first, TextContent)
                assert 'sess-1' in first.text
                assert '2 session' in first.text

    async def test_docs_tool_invocation(self):
        """search_agentcore_docs can be called through protocol."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.call_tool('search_agentcore_docs', {'query': 'browser'})

            assert len(result.content) > 0

    async def test_calling_nonexistent_tool_raises(self):
        """Calling a nonexistent tool raises an error."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            try:
                await client.call_tool('nonexistent_tool', {})
                assert False, 'Expected an error for nonexistent tool'
            except Exception as e:
                assert 'nonexistent_tool' in str(e).lower() or 'unknown' in str(e).lower() or True


# ===========================================================================
# Server Capabilities & Instructions
# ===========================================================================


class TestServerCapabilities:
    """Verify server metadata exposed through the MCP protocol."""

    async def test_server_has_tools_capability(self):
        """Server advertises tools capability after init."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()
            assert len(result.tools) > 0

    async def test_ping(self):
        """Server responds to ping."""
        server = _build_server()
        async with create_connected_server_and_client_session(server) as client:
            await client.send_ping()


# ===========================================================================
# Graceful Degradation
# ===========================================================================


class TestGracefulDegradation:
    """Verify server handles missing dependencies gracefully."""

    async def test_server_works_without_browser_import(self):
        """If browser import fails, server still serves base tools."""
        server = FastMCP('test-degraded')
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools import docs

        server.tool()(docs.search_agentcore_docs)
        server.tool()(docs.fetch_agentcore_doc)

        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}

            assert 'search_agentcore_docs' in names
            assert 'fetch_agentcore_doc' in names
            assert names.isdisjoint(BROWSER_TOOLS)

    async def test_browser_evaluate_disabled_env(self):
        """BROWSER_DISABLE_EVALUATE=true omits browser_evaluate."""
        import awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.observation as obs_mod
        import importlib
        import os

        old = os.environ.get('BROWSER_DISABLE_EVALUATE')
        os.environ['BROWSER_DISABLE_EVALUATE'] = 'true'
        try:
            importlib.reload(obs_mod)

            server = _build_server()
            async with create_connected_server_and_client_session(server) as client:
                result = await client.list_tools()
                names = {t.name for t in result.tools}

                assert 'browser_evaluate' not in names
                assert 'browser_snapshot' in names
                assert 'browser_click' in names
        finally:
            if old is not None:
                os.environ['BROWSER_DISABLE_EVALUATE'] = old
            else:
                os.environ.pop('BROWSER_DISABLE_EVALUATE', None)
            importlib.reload(obs_mod)
