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

"""Shared test fixtures for browser MCP server tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_ctx():
    """Create a mock MCP Context."""
    ctx = MagicMock()
    ctx.error = AsyncMock()
    ctx.info = AsyncMock()
    return ctx


@pytest.fixture
def mock_browser_client(monkeypatch):
    """Create a mock BrowserClient and patch get_browser_client."""
    client = MagicMock()
    client.data_plane_client = MagicMock()
    client.get_session = MagicMock()
    client.list_sessions = MagicMock()
    monkeypatch.setattr(
        'awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools.session.get_browser_client',
        lambda *args, **kwargs: client,
    )
    return client
