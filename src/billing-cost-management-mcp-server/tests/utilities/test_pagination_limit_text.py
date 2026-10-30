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

"""The paging clause in tool descriptions shows the configured limit, not a literal.

`PAGINATION_LIMIT_TEXT` is built at import from `PAGINATION_MAX_SECONDS`, and the
tool descriptions splice it in, so a `BCM_MCP_PAGINATION_MAX_SECONDS` override set
before the server starts is reflected in the description the model is served. With
the default environment the rendered text is identical to the previous hardcoded
"up to 300 seconds (BCM_MCP_PAGINATION_MAX_SECONDS)".

Both cases reload `constants` and a representative tool module so the description is
rebuilt against the test's environment; a fixture reloads them back to the default
afterwards so other tests see the unchanged modules.
"""

import asyncio
import fastmcp
import importlib
import pytest
from awslabs.billing_cost_management_mcp_server.tools import free_tier_usage_tools
from awslabs.billing_cost_management_mcp_server.utilities import constants


ENV = 'BCM_MCP_PAGINATION_MAX_SECONDS'
# A representative tool module that splices PAGINATION_LIMIT_TEXT into a description.
REPRESENTATIVE = free_tier_usage_tools


def _served_descriptions(module):
    """Every tool description published by the FastMCP servers in a tool module."""

    async def collect():
        out = []
        for value in vars(module).values():
            if isinstance(value, fastmcp.FastMCP):
                async with fastmcp.Client(value) as client:
                    out.extend((t.description or '') for t in await client.list_tools())
        return out

    return asyncio.run(collect())


@pytest.fixture
def reload_against_env(monkeypatch):
    """Reload constants + the representative module against the test's env, then restore.

    The restore reloads both with no override so the modules other tests import are
    left exactly as they were.
    """

    def reload():
        importlib.reload(constants)
        importlib.reload(REPRESENTATIVE)

    yield reload

    monkeypatch.delenv(ENV, raising=False)
    importlib.reload(constants)
    importlib.reload(REPRESENTATIVE)


def test_default_env_renders_300(reload_against_env, monkeypatch):
    """Unset, the constant and every served description keep the original 300s text."""
    monkeypatch.delenv(ENV, raising=False)
    reload_against_env()

    assert constants.PAGINATION_LIMIT_TEXT == 'up to 300 seconds (BCM_MCP_PAGINATION_MAX_SECONDS)'

    descriptions = _served_descriptions(REPRESENTATIVE)
    paging = [d for d in descriptions if 'BCM_MCP_PAGINATION_MAX_SECONDS' in d]
    assert paging, 'representative module served no paging clause'
    assert all('up to 300 seconds (BCM_MCP_PAGINATION_MAX_SECONDS)' in d for d in paging)


def test_env_override_renders_in_served_description(reload_against_env, monkeypatch):
    """With the override set before import, the served description shows that value."""
    monkeypatch.setenv(ENV, '45')
    reload_against_env()

    assert constants.PAGINATION_LIMIT_TEXT == 'up to 45 seconds (BCM_MCP_PAGINATION_MAX_SECONDS)'

    descriptions = _served_descriptions(REPRESENTATIVE)
    paging = [d for d in descriptions if 'BCM_MCP_PAGINATION_MAX_SECONDS' in d]
    assert paging, 'representative module served no paging clause'
    assert all('up to 45 seconds (BCM_MCP_PAGINATION_MAX_SECONDS)' in d for d in paging)
    assert all('up to 300 seconds' not in d for d in paging)
