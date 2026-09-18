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
