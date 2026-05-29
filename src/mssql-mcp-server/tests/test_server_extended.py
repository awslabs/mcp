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

"""Extended coverage tests for server.py: error paths, schema tool, connect tool, main()."""

import json
import pytest
import sys
from awslabs.mssql_mcp_server.connection.db_connection_map import ConnectionMethod
from awslabs.mssql_mcp_server.server import (
    DummyCtx,
    _parse_identifier_parts,
    connect_to_database,
    db_connection_map,
    extract_cell,
    get_database_connection_info,
    get_table_schema,
    internal_create_connection,
    run_query,
    validate_table_name,
)
from botocore.exceptions import ClientError
from mcp.shared.exceptions import McpError
from unittest.mock import AsyncMock, MagicMock


# ─── extract_cell value dispatch ─────────────────────────────────────────────


def test_extract_cell_null():
    """isNull=True returns None."""
    assert extract_cell({'isNull': True}) is None


def test_extract_cell_string():
    """StringValue is returned as a string."""
    assert extract_cell({'stringValue': 'hi'}) == 'hi'


def test_extract_cell_long():
    """LongValue is returned as an int."""
    assert extract_cell({'longValue': 42}) == 42


def test_extract_cell_double():
    """DoubleValue is returned as a float."""
    assert extract_cell({'doubleValue': 3.14}) == 3.14


def test_extract_cell_boolean():
    """BooleanValue is returned as a bool."""
    assert extract_cell({'booleanValue': True}) is True


def test_extract_cell_blob():
    """BlobValue is returned as bytes."""
    assert extract_cell({'blobValue': b'data'}) == b'data'


def test_extract_cell_array():
    """ArrayValue is returned as list."""
    assert extract_cell({'arrayValue': [1, 2, 3]}) == [1, 2, 3]


def test_extract_cell_unknown_key():
    """Unknown cell type returns None."""
    assert extract_cell({'mysteryValue': 'x'}) is None


# ─── DummyCtx in-module ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dummy_ctx_error_noop():
    """DummyCtx.error runs without raising."""
    ctx = DummyCtx()
    await ctx.error('boom')


# ─── _parse_identifier_parts edge cases ──────────────────────────────────────


def test_parse_identifier_null_byte_plain():
    """Null byte in plain identifier is rejected (via isalpha check)."""
    assert _parse_identifier_parts('a\x00b') is None


def test_parse_identifier_null_byte_quoted():
    """Null byte inside a double-quoted identifier is rejected."""
    assert _parse_identifier_parts('"a\x00b"') is None


def test_parse_identifier_null_byte_bracket():
    """Null byte inside a bracket-quoted identifier is rejected."""
    assert _parse_identifier_parts('[a\x00b]') is None


def test_parse_identifier_unterminated_quote():
    """Unterminated double-quote returns None."""
    assert _parse_identifier_parts('"unterminated') is None


def test_parse_identifier_unterminated_bracket():
    """Unterminated bracket returns None."""
    assert _parse_identifier_parts('[unterminated') is None


def test_parse_identifier_escaped_quote():
    """Escaped double-quote inside a quoted identifier is preserved."""
    parts = _parse_identifier_parts('"a""b"')
    assert parts == ['a"b']


def test_parse_identifier_escaped_bracket():
    """Escaped closing bracket inside a bracket identifier is preserved."""
    parts = _parse_identifier_parts('[a]]b]')
    assert parts == ['a]b']


def test_parse_identifier_empty_quoted_rejected():
    """Empty string inside a quoted identifier is rejected."""
    assert _parse_identifier_parts('""') is None


def test_parse_identifier_empty_bracket_rejected():
    """Empty string inside a bracket identifier is rejected."""
    assert _parse_identifier_parts('[]') is None


def test_parse_identifier_trailing_dot_rejected():
    """Trailing dot after an identifier is rejected."""
    assert _parse_identifier_parts('a.') is None


def test_parse_identifier_non_dot_separator_rejected():
    """Non-dot separator (space) between parts is rejected."""
    assert _parse_identifier_parts('a b') is None


def test_validate_table_name_three_parts_too_long():
    """Identifier parts exceeding MAX_IDENTIFIER_BYTES are rejected."""
    long_name = 'a' * 200
    assert validate_table_name(long_name) is False


def test_validate_table_name_three_parts_ok():
    """Up to three parts are allowed."""
    assert validate_table_name('a.b.c') is True


# ─── run_query error paths ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_query_client_error(mocker):
    """ClientError from execute_query returns a structured error JSON."""
    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mock_conn.execute_query = AsyncMock(
        side_effect=ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'nope'}}, 'GetSecretValue'
        )
    )
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    result = await run_query(
        sql='SELECT 1',
        ctx=DummyCtx(),
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        database='d',
    )
    assert 'error' in json.loads(result)[0]


@pytest.mark.asyncio
async def test_run_query_generic_exception(mocker):
    """Generic exception from execute_query returns a typed error JSON."""
    mock_conn = MagicMock()
    mock_conn.readonly_query = True
    mock_conn.execute_query = AsyncMock(side_effect=RuntimeError('boom'))
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    result = await run_query(
        sql='SELECT 1',
        ctx=DummyCtx(),
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        database='d',
    )
    payload = json.loads(result)[0]
    assert 'RuntimeError' in payload['error']
    assert 'boom' in payload['error']


@pytest.mark.asyncio
async def test_run_query_injection_risk_blocked(mocker):
    """Injection risk in write mode is rejected even with readonly=False."""
    mock_conn = MagicMock()
    mock_conn.readonly_query = False  # write mode
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    with pytest.raises(McpError):
        await run_query(
            sql="EXEC xp_cmdshell 'whoami'",
            ctx=DummyCtx(),
            connection_method=ConnectionMethod.MSSQL_PASSWORD,
            instance_identifier='i',
            db_endpoint='e',
            database='d',
        )


# ─── get_table_schema ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_table_schema_invalid_table_name():
    """An invalid table name raises McpError with INVALID_PARAMS."""
    with pytest.raises(McpError):
        await get_table_schema(
            connection_method=ConnectionMethod.MSSQL_PASSWORD,
            instance_identifier='i',
            db_endpoint='e',
            database='d',
            table_name="evil'; DROP TABLE foo--",
            ctx=DummyCtx(),
        )


@pytest.mark.asyncio
async def test_get_table_schema_invalid_schema_name():
    """An invalid schema name raises McpError with INVALID_PARAMS."""
    with pytest.raises(McpError):
        await get_table_schema(
            connection_method=ConnectionMethod.MSSQL_PASSWORD,
            instance_identifier='i',
            db_endpoint='e',
            database='d',
            table_name='users',
            ctx=DummyCtx(),
            schema_name="bad'; DROP--",
        )


@pytest.mark.asyncio
async def test_get_table_schema_no_connection(mocker):
    """Missing connection returns an error JSON instead of raising."""
    mocker.patch.object(db_connection_map, 'get', return_value=None)
    result = await get_table_schema(
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        database='d',
        table_name='users',
        ctx=DummyCtx(),
    )
    assert 'error' in json.loads(result)[0]


@pytest.mark.asyncio
async def test_get_table_schema_with_schema_name_success(mocker):
    """Passing a schema_name runs the schema-filtered query and wraps the result."""
    mock_conn = MagicMock()
    mock_conn.execute_query = AsyncMock(
        return_value={
            'columnMetadata': [{'name': 'COLUMN_NAME'}],
            'records': [[{'stringValue': 'id'}]],
        }
    )
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)

    result = await get_table_schema(
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        database='d',
        table_name='users',
        ctx=DummyCtx(),
        schema_name='dbo',
    )
    assert 'UNTRUSTED' in result
    # Verify schema-scoped SQL was used and both params supplied
    called_sql, called_params = mock_conn.execute_query.call_args.args
    assert 'TABLE_SCHEMA' in called_sql
    assert called_params == ('users', 'dbo')


@pytest.mark.asyncio
async def test_get_table_schema_no_schema_name_success(mocker):
    """Without schema_name, the un-scoped query is issued with only the table name."""
    mock_conn = MagicMock()
    mock_conn.execute_query = AsyncMock(
        return_value={
            'columnMetadata': [{'name': 'COLUMN_NAME'}],
            'records': [[{'stringValue': 'id'}]],
        }
    )
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)

    result = await get_table_schema(
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        database='d',
        table_name='users',
        ctx=DummyCtx(),
    )
    assert 'UNTRUSTED' in result
    _, called_params = mock_conn.execute_query.call_args.args
    assert called_params == ('users',)


@pytest.mark.asyncio
async def test_get_table_schema_execute_error_returns_error_json(mocker):
    """An exception inside execute_query is converted to an error JSON."""
    mock_conn = MagicMock()
    mock_conn.execute_query = AsyncMock(side_effect=RuntimeError('pool broken'))
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)

    result = await get_table_schema(
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        database='d',
        table_name='users',
        ctx=DummyCtx(),
    )
    payload = json.loads(result)[0]
    assert 'RuntimeError' in payload['error']


# ─── connect_to_database tool ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_to_database_success(mocker):
    """Successful connect invokes initialize_pool and returns the llm_response."""
    import awslabs.mssql_mcp_server.server as srv

    # spec=PymssqlPoolConnection makes isinstance(fake_conn, PymssqlPoolConnection) True
    fake_conn = MagicMock(spec=srv.PymssqlPoolConnection)
    fake_conn.initialize_pool = AsyncMock()
    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_create_connection',
        return_value=(fake_conn, '{"status": "ok"}'),
    )

    result = await connect_to_database(
        region='us-east-1',
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        ctx=DummyCtx(),
        port=1433,
        database='d',
    )
    assert 'ok' in result
    fake_conn.initialize_pool.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_to_database_pool_init_fails(mocker):
    """initialize_pool failure triggers close() and remove()."""
    import awslabs.mssql_mcp_server.server as srv

    # spec=PymssqlPoolConnection makes isinstance(fake_conn, PymssqlPoolConnection) True
    fake_conn = MagicMock(spec=srv.PymssqlPoolConnection)
    fake_conn.initialize_pool = AsyncMock(side_effect=Exception('pool err'))
    fake_conn.close = AsyncMock()
    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_create_connection',
        return_value=(fake_conn, '{}'),
    )
    remove_spy = mocker.patch.object(db_connection_map, 'remove')

    result = await connect_to_database(
        region='us-east-1',
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        ctx=DummyCtx(),
        port=1433,
        database='d',
    )
    payload = json.loads(result)
    assert payload['status'] == 'Failed'
    fake_conn.close.assert_awaited_once()
    remove_spy.assert_called_once()


@pytest.mark.asyncio
async def test_connect_to_database_internal_raises(mocker):
    """Any exception from internal_create_connection is returned as failure JSON."""
    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_create_connection',
        side_effect=ValueError('bad args'),
    )
    result = await connect_to_database(
        region='us-east-1',
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        ctx=DummyCtx(),
        port=1433,
        database='d',
    )
    payload = json.loads(result)
    assert payload['status'] == 'Failed'
    assert 'bad args' in payload['error']


# ─── internal_create_connection validation / reuse ───────────────────────────


def test_internal_create_connection_missing_region_raises():
    """Missing region raises ValueError."""
    with pytest.raises(ValueError, match='region'):
        internal_create_connection(
            region='',
            connection_method=ConnectionMethod.MSSQL_PASSWORD,
            instance_identifier='i',
            db_endpoint='e',
            port=1433,
            database='d',
        )


def test_internal_create_connection_missing_endpoint_raises():
    """Missing db_endpoint raises ValueError."""
    with pytest.raises(ValueError, match='db_endpoint'):
        internal_create_connection(
            region='us-east-1',
            connection_method=ConnectionMethod.MSSQL_PASSWORD,
            instance_identifier='i',
            db_endpoint='',
            port=1433,
            database='d',
        )


def test_internal_create_connection_missing_method_raises():
    """Missing connection_method raises ValueError."""
    with pytest.raises(ValueError, match='connection_method'):
        internal_create_connection(
            region='us-east-1',
            connection_method=None,  # type: ignore[arg-type]
            instance_identifier='i',
            db_endpoint='e',
            port=1433,
            database='d',
        )


def test_internal_create_connection_returns_existing(mocker):
    """Second call with the same key returns the cached connection."""
    cached = MagicMock()
    mocker.patch.object(db_connection_map, 'get', return_value=cached)
    conn, llm_resp = internal_create_connection(
        region='us-east-1',
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        port=1433,
        database='d',
    )
    assert conn is cached
    assert '"database": "d"' in llm_resp


# ─── get_database_connection_info ────────────────────────────────────────────


def test_get_database_connection_info_returns_json():
    """get_database_connection_info returns a JSON-serialisable string."""
    out = get_database_connection_info()
    # valid JSON even when map is empty
    json.loads(out)


# ─── main() argument parsing and startup ─────────────────────────────────────


def test_main_readonly_default_no_startup_connection(mocker):
    """main() with minimal args enters readonly mode and runs mcp.run() without connecting."""
    import awslabs.mssql_mcp_server.server as srv

    # No instance_identifier/db_endpoint => skip startup validation
    mocker.patch.object(sys, 'argv', ['prog', '--region', 'us-east-1'])
    run_spy = mocker.patch.object(srv.mcp, 'run')
    close_all_spy = mocker.patch.object(srv.db_connection_map, 'close_all')

    srv.main()

    assert srv.server_config.readonly_query is True  # no --allow_write_query
    run_spy.assert_called_once()
    close_all_spy.assert_called_once()


def test_main_allow_write_query_flag_sets_write_mode(mocker):
    """--allow_write_query disables readonly mode."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        ['prog', '--region', 'us-east-1', '--allow_write_query'],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    try:
        srv.main()
        assert srv.server_config.readonly_query is False
    finally:
        # Reset global state for other tests
        srv.server_config.readonly_query = True


def test_main_with_startup_connection_validates(mocker):
    """Providing instance_identifier+db_endpoint runs a SELECT 1 validation."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--connection_method',
            'MSSQL_PASSWORD',
            '--instance_identifier',
            'inst1',
            '--db_endpoint',
            'ep1',
            '--database',
            'master',
        ],
    )

    # Build a fake PymssqlPoolConnection-like object
    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = [(1,)]
    fake_raw_conn = MagicMock()
    fake_raw_conn.cursor.return_value = fake_cursor

    # spec=PymssqlPoolConnection makes isinstance(fake_conn, PymssqlPoolConnection) True
    fake_conn = MagicMock(spec=srv.PymssqlPoolConnection)
    fake_conn._get_credentials_from_secret.return_value = ('u', 'p')
    fake_conn._create_raw_connection.return_value = fake_raw_conn
    fake_conn.secret_arn = 'arn'  # pragma: allowlist secret
    fake_conn.region = 'us-east-1'

    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_create_connection',
        return_value=(fake_conn, '{}'),
    )
    run_spy = mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    srv.main()

    # Validation ran and server started
    fake_conn._create_raw_connection.assert_called_once_with('u', 'p')
    fake_cursor.execute.assert_called_once_with('SELECT 1')
    fake_raw_conn.close.assert_called_once()
    run_spy.assert_called_once()


def test_main_startup_connection_validation_returns_empty(mocker):
    """If SELECT 1 returns no rows, main() exits with status 1."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--connection_method',
            'MSSQL_PASSWORD',
            '--instance_identifier',
            'inst1',
            '--db_endpoint',
            'ep1',
        ],
    )

    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = []  # empty => sys.exit(1)
    fake_raw_conn = MagicMock()
    fake_raw_conn.cursor.return_value = fake_cursor

    # spec=PymssqlPoolConnection makes isinstance(fake_conn, PymssqlPoolConnection) True
    fake_conn = MagicMock(spec=srv.PymssqlPoolConnection)
    fake_conn._get_credentials_from_secret.return_value = ('u', 'p')
    fake_conn._create_raw_connection.return_value = fake_raw_conn
    fake_conn.secret_arn = 'arn'  # pragma: allowlist secret
    fake_conn.region = 'us-east-1'

    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_create_connection',
        return_value=(fake_conn, '{}'),
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    with pytest.raises(SystemExit) as exc_info:
        srv.main()
    assert exc_info.value.code == 1
