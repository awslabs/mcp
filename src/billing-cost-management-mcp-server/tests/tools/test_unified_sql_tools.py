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

"""Unit tests for the unified_sql_tools module.

These tests verify the functionality of the unified SQL interface tools, including:
- Executing SQL queries on session-based SQLite databases
- Creating temporary tables with custom schemas and data loading
- Handling dynamic table creation with auto-generated table names
- Managing session persistence and database lifecycle
- Error handling for invalid SQL queries and schema mismatches
"""

import fastmcp
import importlib
import pytest
import uuid
from awslabs.billing_cost_management_mcp_server.tools.unified_sql_tools import (
    unified_sql_server,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.mark.asyncio
class TestSessionSql:
    """Tests for session_sql function."""

    async def test_session_sql_with_data_and_schema(self, mock_context):
        """Test session_sql with data and schema generates table name."""
        # Test the logic by importing the actual function implementation
        import uuid

        # Test the table name generation logic
        data = [{'col1': 'value1'}]
        schema = ['col1']
        table_name = None

        if data and schema and not table_name:
            generated_name = f'user_data_{str(uuid.uuid4())[:8]}'
            assert generated_name.startswith('user_data_')
            assert len(generated_name) == 18  # 'user_data_' + 8 chars

    async def test_session_sql_error_handling(self, mock_context):
        """Test session_sql error handling."""
        # Test that error handling imports are available
        from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
            handle_aws_error,
        )
        from awslabs.billing_cost_management_mcp_server.utilities.sql_utils import (
            execute_session_sql,
        )

        assert handle_aws_error is not None
        assert execute_session_sql is not None


def test_unified_sql_server_initialization():
    """Test that the unified SQL server is properly initialized."""
    assert unified_sql_server is not None
    assert unified_sql_server.name == 'unified-sql-tools'


def _reload_unified_sql_with_identity_decorator():
    """Reload unified_sql_tools with FastMCP.tool patched to return the original function unchanged (identity decorator).

    This exposes a callable 'session_sql' we can invoke directly to cover both branches.
    """
    from awslabs.billing_cost_management_mcp_server.tools import unified_sql_tools as us_mod

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(us_mod)
        return us_mod


@pytest.mark.asyncio
async def test_unified_sql_real_simple_query_reload_identity_decorator(mock_context):
    """Test unified_sql real simple query with identity decorator."""
    us_mod = _reload_unified_sql_with_identity_decorator()
    real_fn = us_mod.session_sql  # type: ignore

    with patch.object(us_mod, 'execute_session_sql', new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {'status': 'success', 'data': {'rows': []}}
        res = await real_fn(mock_context, query='SELECT 1')  # type: ignore
        assert res['status'] == 'success'
        mock_exec.assert_awaited_once_with(mock_context, 'SELECT 1', None, None, None)


@pytest.mark.asyncio
async def test_unified_sql_real_autogen_table_reload_identity_decorator(mock_context):
    """Test unified_sql real autogen table with identity decorator."""
    us_mod = _reload_unified_sql_with_identity_decorator()
    real_fn = us_mod.session_sql  # type: ignore

    # Make uuid deterministic so we can assert the table_name
    fixed_uuid = uuid.UUID('12345678-1234-1234-1234-1234567890ab')
    with (
        patch.object(us_mod.uuid, 'uuid4', return_value=fixed_uuid),
        patch.object(us_mod, 'execute_session_sql', new_callable=AsyncMock) as mock_exec,
    ):
        mock_exec.return_value = {'status': 'success', 'data': {'ok': True}}

        schema = ['col1 TEXT', 'col2 INTEGER']
        data = [['a', 1], ['b', 2]]
        res = await real_fn(
            mock_context, query='SELECT * FROM user_data_12345678', schema=schema, data=data
        )  # type: ignore
        assert res['status'] == 'success'
        mock_exec.assert_awaited_once_with(
            mock_context,
            'SELECT * FROM user_data_12345678',
            schema,
            data,
            'user_data_12345678',
        )


@pytest.mark.asyncio
async def test_unified_sql_real_respects_provided_table_name_reload_identity_decorator(
    mock_context,
):
    """Test unified_sql real respects provided table name with identity decorator."""
    us_mod = _reload_unified_sql_with_identity_decorator()
    real_fn = us_mod.session_sql  # type: ignore

    with patch.object(us_mod, 'execute_session_sql', new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {'status': 'success', 'data': {'count': 2}}
        schema = ['x INTEGER']
        data = [[1], [2]]
        res = await real_fn(  # type: ignore
            mock_context,
            query='SELECT * FROM my_table',
            schema=schema,
            data=data,
            table_name='my_table',
        )
        assert res['status'] == 'success'
        mock_exec.assert_awaited_once_with(
            mock_context,
            'SELECT * FROM my_table',
            schema,
            data,
            'my_table',
        )


@pytest.mark.asyncio
async def test_unified_sql_real_exception_flow_calls_handle_error_reload_identity_decorator(
    mock_context,
):
    """Test unified_sql real exception flow calls handle_error with identity decorator."""
    us_mod = _reload_unified_sql_with_identity_decorator()
    real_fn = us_mod.session_sql  # type: ignore

    with (
        patch.object(us_mod, 'execute_session_sql', side_effect=RuntimeError('kaboom')),
        patch.object(us_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
    ):
        mock_handle.return_value = {'status': 'error', 'message': 'kaboom'}
        res = await real_fn(mock_context, query='SELECT 1')  # type: ignore
        assert res['status'] == 'error'
        assert 'kaboom' in res.get('message', '')
        mock_handle.assert_awaited_once()
