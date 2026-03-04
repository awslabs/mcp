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

"""Unit tests for server.py — lifespan, tool registration, and main entry point."""

import signal
from unittest.mock import AsyncMock, MagicMock, patch


PATCH_BASE = 'awslabs.amazon_agentcore_browser_mcp_server.server'


class TestServerLifespan:
    """Tests for server_lifespan context manager."""

    async def test_lifespan_calls_cleanup_on_exit(self):
        """Lifespan cleans up connection manager in finally block."""
        with patch(f'{PATCH_BASE}.connection_manager') as mock_cm:
            mock_cm.cleanup = AsyncMock()
            from awslabs.amazon_agentcore_browser_mcp_server.server import server_lifespan

            mock_server = MagicMock()
            async with server_lifespan(mock_server):
                pass

            mock_cm.cleanup.assert_awaited_once()

    async def test_lifespan_registers_signal_handlers(self):
        """Lifespan registers SIGTERM and SIGINT handlers."""
        with (
            patch(f'{PATCH_BASE}.connection_manager') as mock_cm,
            patch(f'{PATCH_BASE}.asyncio') as mock_asyncio,
        ):
            mock_cm.cleanup = AsyncMock()
            mock_loop = MagicMock()
            mock_asyncio.get_running_loop.return_value = mock_loop

            from awslabs.amazon_agentcore_browser_mcp_server.server import server_lifespan

            mock_server = MagicMock()
            async with server_lifespan(mock_server):
                # Verify signal handlers were registered for both SIGTERM and SIGINT
                assert mock_loop.add_signal_handler.call_count == 2
                registered_signals = [
                    call.args[0] for call in mock_loop.add_signal_handler.call_args_list
                ]
                assert signal.SIGTERM in registered_signals
                assert signal.SIGINT in registered_signals

    async def test_lifespan_cleans_up_on_exception(self):
        """Lifespan cleans up even when an exception occurs."""
        with patch(f'{PATCH_BASE}.connection_manager') as mock_cm:
            mock_cm.cleanup = AsyncMock()
            from awslabs.amazon_agentcore_browser_mcp_server.server import server_lifespan

            mock_server = MagicMock()
            try:
                async with server_lifespan(mock_server):
                    raise RuntimeError('test error')
            except RuntimeError:
                pass

            mock_cm.cleanup.assert_awaited_once()


class TestToolRegistration:
    """Tests for tool group registration at module level."""

    def test_mcp_instance_created(self):
        """FastMCP instance is created with correct name."""
        from awslabs.amazon_agentcore_browser_mcp_server.server import mcp

        assert mcp.name == 'awslabs.amazon-agentcore-browser-mcp-server'

    def test_mcp_has_lifespan(self):
        """FastMCP instance has lifespan set."""
        from awslabs.amazon_agentcore_browser_mcp_server.server import mcp, server_lifespan

        assert mcp.settings.lifespan is server_lifespan


class TestMain:
    """Tests for the main entry point."""

    def test_main_calls_mcp_run(self):
        """main() invokes mcp.run()."""
        with patch(f'{PATCH_BASE}.mcp') as mock_mcp:
            from awslabs.amazon_agentcore_browser_mcp_server.server import main

            main()

            mock_mcp.run.assert_called_once()
