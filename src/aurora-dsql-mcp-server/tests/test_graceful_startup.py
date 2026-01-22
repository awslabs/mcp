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
"""Tests for graceful startup without cluster configuration."""

import pytest
from awslabs.aurora_dsql_mcp_server import server
from awslabs.aurora_dsql_mcp_server.server import get_schema, readonly_query, transact


class MockContext:
    """Mock MCP context for testing."""

    def __init__(self):
        self.errors = []

    async def error(self, message):
        self.errors.append(message)


@pytest.mark.asyncio
async def test_readonly_query_without_cluster_config():
    """Test that readonly_query returns helpful error when cluster not configured."""
    original_endpoint = server.cluster_endpoint
    server.cluster_endpoint = None

    ctx = MockContext()

    with pytest.raises(Exception) as exc_info:
        await readonly_query("SELECT 1", ctx)

    assert "Database not configured" in str(exc_info.value)
    assert len(ctx.errors) == 1
    assert "Database not configured" in ctx.errors[0]

    server.cluster_endpoint = original_endpoint


@pytest.mark.asyncio
async def test_transact_without_cluster_config():
    """Test that transact returns helpful error when cluster not configured."""
    original_endpoint = server.cluster_endpoint
    server.cluster_endpoint = None

    ctx = MockContext()

    with pytest.raises(Exception) as exc_info:
        await transact(["SELECT 1"], ctx)

    assert "Database not configured" in str(exc_info.value)
    assert len(ctx.errors) == 1
    assert "Database not configured" in ctx.errors[0]

    server.cluster_endpoint = original_endpoint


@pytest.mark.asyncio
async def test_get_schema_without_cluster_config():
    """Test that get_schema returns helpful error when cluster not configured."""
    original_endpoint = server.cluster_endpoint
    server.cluster_endpoint = None

    ctx = MockContext()

    with pytest.raises(Exception) as exc_info:
        await get_schema("test_table", ctx)

    assert "Database not configured" in str(exc_info.value)
    assert len(ctx.errors) == 1
    assert "Database not configured" in ctx.errors[0]

    server.cluster_endpoint = original_endpoint
