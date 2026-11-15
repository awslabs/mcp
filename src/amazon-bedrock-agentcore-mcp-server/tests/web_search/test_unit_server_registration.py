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

"""Tests for how server.py registers the web search tool."""

import asyncio
import importlib
import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server import server
from unittest.mock import patch


REGISTER = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools.web_search.register_web_search_tools'


def _tool_names() -> set[str]:
    return {t.name for t in asyncio.run(server.mcp.list_tools())}


@pytest.fixture
def reload_server(monkeypatch):
    """Reload server.py under the test's env, then restore the default module."""
    monkeypatch.delenv('AGENTCORE_DISABLE_TOOLS', raising=False)

    def _reload():
        importlib.reload(server)

    yield _reload
    monkeypatch.delenv('AGENTCORE_ENABLE_TOOLS', raising=False)
    importlib.reload(server)


class TestWebSearchServerRegistration:
    """server.py registers web_search when enabled and survives a failure."""

    def test_registered_when_enabled(self, monkeypatch, reload_server):
        """AGENTCORE_ENABLE_TOOLS=web_search registers web_search and the docs tools."""
        monkeypatch.setenv('AGENTCORE_ENABLE_TOOLS', 'web_search')
        reload_server()

        assert _tool_names() == {'web_search', 'search_agentcore_docs', 'fetch_agentcore_doc'}

    def test_not_registered_when_disabled(self, monkeypatch, reload_server):
        """web_search is absent when another primitive is the only one enabled."""
        monkeypatch.setenv('AGENTCORE_ENABLE_TOOLS', 'policy')
        reload_server()

        assert 'web_search' not in _tool_names()

    def test_registration_failure_is_logged_not_raised(self, monkeypatch, reload_server):
        """A failing registration logs an error and the server still loads."""
        monkeypatch.setenv('AGENTCORE_ENABLE_TOOLS', 'web_search')
        with (
            patch(REGISTER, side_effect=RuntimeError('boom')),
            patch.object(server.logger, 'error') as log_error,
        ):
            reload_server()

        assert 'web_search' not in _tool_names()
        assert any('Web search tools disabled' in c.args[0] for c in log_error.call_args_list)
