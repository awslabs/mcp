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

"""Verify that parser rejections stop before the database connection."""

import pytest
from unittest.mock import AsyncMock, patch

from awslabs.aurora_dsql_mcp_server.consts import ERROR_QUERY_INJECTION_RISK
from awslabs.aurora_dsql_mcp_server.server import readonly_query, transact


ESCAPED_SLEEP = r'''SELECT U&"pg_sl\0065ep"(10)'''
UNBOUND_PERCENT_BYPASS = 'SELECT 1%setseed(0.5)'


@pytest.mark.asyncio
async def test_readonly_query_stops_unicode_escape_before_connection():
    """The escaped function must not reach the read-only transaction."""
    ctx = AsyncMock()
    with (
        patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'example.dsql'),
        patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection', new_callable=AsyncMock
        ) as get_connection,
    ):
        with pytest.raises(Exception, match=ERROR_QUERY_INJECTION_RISK):
            await readonly_query(ESCAPED_SLEEP, ctx)

    get_connection.assert_not_awaited()


@pytest.mark.asyncio
async def test_write_mode_transact_stops_unicode_escape_before_connection():
    """Dangerous functions remain blocked when ordinary writes are enabled."""
    ctx = AsyncMock()
    with (
        patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'example.dsql'),
        patch('awslabs.aurora_dsql_mcp_server.server.read_only', False),
        patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection', new_callable=AsyncMock
        ) as get_connection,
    ):
        with pytest.raises(Exception, match=ERROR_QUERY_INJECTION_RISK):
            await transact([ESCAPED_SLEEP], ctx)

    get_connection.assert_not_awaited()


@pytest.mark.asyncio
async def test_write_mode_transact_stops_transaction_control_before_connection():
    """Caller SQL cannot commit the transaction managed by the tool."""
    ctx = AsyncMock()
    with (
        patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'example.dsql'),
        patch('awslabs.aurora_dsql_mcp_server.server.read_only', False),
        patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection', new_callable=AsyncMock
        ) as get_connection,
    ):
        with pytest.raises(Exception, match=ERROR_QUERY_INJECTION_RISK):
            await transact(['COMMIT', 'UPDATE t SET value = 1'], ctx)

    get_connection.assert_not_awaited()


@pytest.mark.asyncio
async def test_readonly_query_uses_unbound_percent_semantics():
    """Without params, modulo syntax cannot be mistaken for a placeholder."""
    ctx = AsyncMock()
    with (
        patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'example.dsql'),
        patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection', new_callable=AsyncMock
        ) as get_connection,
    ):
        with pytest.raises(Exception, match=ERROR_QUERY_INJECTION_RISK):
            await readonly_query(UNBOUND_PERCENT_BYPASS, ctx)

    get_connection.assert_not_awaited()


@pytest.mark.asyncio
async def test_readonly_query_passes_parameter_binding_context_to_guard():
    """A supplied params list enables psycopg placeholder parsing."""
    ctx = AsyncMock()
    with (
        patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'example.dsql'),
        patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection', new_callable=AsyncMock
        ) as get_connection,
        patch(
            'awslabs.aurora_dsql_mcp_server.server.execute_query', new_callable=AsyncMock
        ) as execute_query,
    ):
        get_connection.return_value = AsyncMock()
        execute_query.side_effect = [None, [{'value': 1}], None, None, None]
        result = await readonly_query('SELECT %s AS value', ctx, params=[1])

    assert result == [{'value': 1}]
    assert execute_query.await_args_list[1].args[3] == [1]


@pytest.mark.asyncio
async def test_readonly_query_stops_raw_placeholder_count_mismatch_before_connection():
    """Quoted and commented markers count as psycopg placeholders."""
    ctx = AsyncMock()
    sql = "SELECT '%s', id FROM t WHERE id = %s -- %s"
    with (
        patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'example.dsql'),
        patch(
            'awslabs.aurora_dsql_mcp_server.server.get_connection', new_callable=AsyncMock
        ) as get_connection,
    ):
        with pytest.raises(Exception, match=ERROR_QUERY_INJECTION_RISK):
            await readonly_query(sql, ctx, params=[1])

    get_connection.assert_not_awaited()
