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
    server_config,
    validate_table_name,
)
from awslabs.mssql_mcp_server.server import mcp as server_mcp
from botocore.exceptions import ClientError
from mcp.shared.exceptions import McpError
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def _reset_server_config():
    """Restore server_config after each test so CLI-parsing tests don't leak state."""
    old_readonly = server_config.readonly_query
    old_arns = server_config.configured_secret_arns
    old_default = server_config.configured_default_secret_arn
    old_endpoints = server_config.allowed_endpoints
    yield
    server_config.readonly_query = old_readonly
    server_config.configured_secret_arns = old_arns
    server_config.configured_default_secret_arn = old_default
    server_config.allowed_endpoints = old_endpoints


# ─── security invariant: secret_arn not exposed to LLM ──────────────────────


def test_connect_to_database_tool_schema_does_not_expose_secret_arn():
    """The LLM-facing connect_to_database tool must never expose secret_arn."""
    tool = server_mcp._tool_manager.get_tool('connect_to_database')
    assert tool is not None
    schema = tool.parameters
    assert 'secret_arn' not in schema.get('properties', {}), (
        'secret_arn must not be exposed as a tool parameter — '
        'secrets are configured exclusively via CLI --secret_arn flags'
    )


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
        return_value=(fake_conn, '{"status": "ok"}', None),
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
        return_value=(fake_conn, '{}', None),
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


@pytest.mark.asyncio
async def test_connect_to_database_closes_replaced_connection(mocker):
    """When internal_create_connection returns a replaced connection, it is closed."""
    import awslabs.mssql_mcp_server.server as srv

    fake_conn = MagicMock(spec=srv.PymssqlPoolConnection)
    fake_conn.initialize_pool = AsyncMock()
    replaced = AsyncMock()

    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_create_connection',
        return_value=(fake_conn, '{}', replaced),
    )

    await connect_to_database(
        region='us-east-1',
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        ctx=DummyCtx(),
        port=1433,
        database='d',
    )
    replaced.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_to_database_replaced_close_failure_is_non_fatal(mocker):
    """If closing the replaced connection raises, the tool still succeeds."""
    import awslabs.mssql_mcp_server.server as srv

    fake_conn = MagicMock(spec=srv.PymssqlPoolConnection)
    fake_conn.initialize_pool = AsyncMock()
    replaced = AsyncMock()
    replaced.close = AsyncMock(side_effect=RuntimeError('close failed'))

    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_create_connection',
        return_value=(fake_conn, '{"status": "ok"}', replaced),
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
    import awslabs.mssql_mcp_server.server as srv

    cached = MagicMock()
    cached.secret_arn = 'arn:test'  # pragma: allowlist secret
    srv.server_config.configured_default_secret_arn = 'arn:test'  # pragma: allowlist secret
    mocker.patch.object(db_connection_map, 'get', return_value=cached)
    conn, llm_resp, _ = internal_create_connection(
        region='us-east-1',
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        port=1433,
        database='d',
    )
    assert conn is cached
    assert '"database": "d"' in llm_resp


def test_cache_hit_without_configured_secret_skips_rds(mocker):
    """A cached reconnect with no --secret_arn configured must NOT call RDS.

    Guards the offline-cache-hit path: RDS metadata resolution is deferred until
    after the cache check, so describe_db_instances is never issued on reconnect.
    """
    import awslabs.mssql_mcp_server.server as srv

    srv.server_config.configured_secret_arns = {}
    srv.server_config.configured_default_secret_arn = None

    cached = MagicMock()
    cached.secret_arn = (
        'arn:aws:secretsmanager:us-east-1:123:secret:rds-master'  # pragma: allowlist secret
    )
    mocker.patch.object(db_connection_map, 'get', return_value=cached)
    mock_boto = mocker.patch('awslabs.mssql_mcp_server.server.boto3')

    conn, llm_resp, replaced = internal_create_connection(
        region='us-east-1',
        connection_method=ConnectionMethod.MSSQL_PASSWORD,
        instance_identifier='i',
        db_endpoint='e',
        port=1433,
        database='d',
    )

    assert conn is cached
    assert replaced is None
    # No RDS client / describe_db_instances call on a cache hit.
    mock_boto.client.assert_not_called()


def test_internal_create_connection_evicts_on_secret_change(mocker):
    """Cached connection is evicted when the resolved ARN differs."""
    import awslabs.mssql_mcp_server.server as srv

    old_conn = MagicMock()
    old_conn.secret_arn = 'arn:old'  # pragma: allowlist secret
    mocker.patch.object(db_connection_map, 'get', return_value=old_conn)
    mock_remove = mocker.patch.object(db_connection_map, 'remove')
    mocker.patch.object(db_connection_map, 'set')
    mocker.patch('awslabs.mssql_mcp_server.server.validate_endpoint', return_value=('ep1', 1433))
    old_readonly = srv.server_config.readonly_query
    srv.server_config.readonly_query = True
    old_default = srv.server_config.configured_default_secret_arn
    srv.server_config.configured_default_secret_arn = 'arn:new'  # pragma: allowlist secret

    try:
        conn, _, replaced = internal_create_connection(
            region='us-east-1',
            connection_method=ConnectionMethod.MSSQL_PASSWORD,
            instance_identifier='i',
            db_endpoint='ep1',
            port=1433,
            database='d',
        )
        assert replaced is old_conn
        assert conn.secret_arn == 'arn:new'  # pragma: allowlist secret
        mock_remove.assert_called_once()
    finally:
        srv.server_config.readonly_query = old_readonly
        srv.server_config.configured_default_secret_arn = old_default


def test_internal_create_connection_rds_not_found_error(mocker):
    """ClientError with DBInstanceNotFound raises clear ValueError."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(db_connection_map, 'get', return_value=None)
    old_arns = srv.server_config.configured_secret_arns
    old_default = srv.server_config.configured_default_secret_arn
    srv.server_config.configured_secret_arns = {}
    srv.server_config.configured_default_secret_arn = None

    err = ClientError(
        error_response={'Error': {'Code': 'DBInstanceNotFound', 'Message': 'not found'}},
        operation_name='DescribeDBInstances',
    )
    mock_rds = MagicMock()
    mock_rds.describe_db_instances.side_effect = err
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    try:
        with pytest.raises(ValueError, match='not found in region'):
            internal_create_connection(
                region='us-east-1',
                connection_method=ConnectionMethod.MSSQL_PASSWORD,
                instance_identifier='missing-inst',
                db_endpoint='ep1',
                port=1433,
                database='d',
            )
    finally:
        srv.server_config.configured_secret_arns = old_arns
        srv.server_config.configured_default_secret_arn = old_default


def test_internal_create_connection_rds_other_client_error(mocker):
    """ClientError with non-DBInstanceNotFound code raises ValueError."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(db_connection_map, 'get', return_value=None)
    old_arns = srv.server_config.configured_secret_arns
    old_default = srv.server_config.configured_default_secret_arn
    srv.server_config.configured_secret_arns = {}
    srv.server_config.configured_default_secret_arn = None

    err = ClientError(
        error_response={'Error': {'Code': 'AccessDenied', 'Message': 'no access'}},
        operation_name='DescribeDBInstances',
    )
    mock_rds = MagicMock()
    mock_rds.describe_db_instances.side_effect = err
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    try:
        with pytest.raises(ValueError, match='Failed to describe RDS instance'):
            internal_create_connection(
                region='us-east-1',
                connection_method=ConnectionMethod.MSSQL_PASSWORD,
                instance_identifier='inst1',
                db_endpoint='ep1',
                port=1433,
                database='d',
            )
    finally:
        srv.server_config.configured_secret_arns = old_arns
        srv.server_config.configured_default_secret_arn = old_default


def test_internal_create_connection_empty_instances_raises(mocker):
    """Empty DBInstances list raises ValueError."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(db_connection_map, 'get', return_value=None)
    old_arns = srv.server_config.configured_secret_arns
    old_default = srv.server_config.configured_default_secret_arn
    srv.server_config.configured_secret_arns = {}
    srv.server_config.configured_default_secret_arn = None

    mock_rds = MagicMock()
    mock_rds.describe_db_instances.return_value = {'DBInstances': []}
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    try:
        with pytest.raises(ValueError, match='returned no instances'):
            internal_create_connection(
                region='us-east-1',
                connection_method=ConnectionMethod.MSSQL_PASSWORD,
                instance_identifier='inst1',
                db_endpoint='ep1',
                port=1433,
                database='d',
            )
    finally:
        srv.server_config.configured_secret_arns = old_arns
        srv.server_config.configured_default_secret_arn = old_default


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
        return_value=(fake_conn, '{}', None),
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
        return_value=(fake_conn, '{}', None),
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    with pytest.raises(SystemExit) as exc_info:
        srv.main()
    assert exc_info.value.code == 1


# ─── --secret_arn CLI parsing ─────────────────────────────────────────────────


def test_main_secret_arn_per_target_parsing(mocker):
    """--secret_arn with key=arn syntax populates configured_secret_arns."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--secret_arn',
            'inst1=arn:aws:secretsmanager:us-east-1:123:secret:s1',
            '--secret_arn',
            'inst2=arn:aws:secretsmanager:us-east-1:123:secret:s2',
        ],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    srv.main()

    assert srv.server_config.configured_secret_arns == {
        'inst1': 'arn:aws:secretsmanager:us-east-1:123:secret:s1',
        'inst2': 'arn:aws:secretsmanager:us-east-1:123:secret:s2',
    }
    assert srv.server_config.configured_default_secret_arn is None


def test_main_secret_arn_bare_default(mocker):
    """A bare --secret_arn (no '=') sets configured_default_secret_arn."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--secret_arn',
            'arn:aws:secretsmanager:us-east-1:123:secret:default',
        ],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    srv.main()

    assert srv.server_config.configured_default_secret_arn == (
        'arn:aws:secretsmanager:us-east-1:123:secret:default'
    )
    assert srv.server_config.configured_secret_arns == {}


def test_main_secret_arn_invalid_key_arn_exits(mocker):
    """--secret_arn with empty key in key=arn syntax exits with code 2."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        ['prog', '--region', 'us-east-1', '--secret_arn', '=arn:bad'],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    with pytest.raises(SystemExit) as exc_info:
        srv.main()
    assert exc_info.value.code == 2


def test_main_secret_arn_empty_arn_in_key_pair_exits(mocker):
    """--secret_arn with a valid key but empty ARN (key=) exits with code 2."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        ['prog', '--region', 'us-east-1', '--secret_arn', 'inst1='],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    with pytest.raises(SystemExit) as exc_info:
        srv.main()
    assert exc_info.value.code == 2


def test_main_secret_arn_duplicate_key_exits(mocker):
    """Duplicate --secret_arn keys exit with code 2."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--secret_arn',
            'inst1=arn:aws:secretsmanager:us-east-1:123:secret:s1',
            '--secret_arn',
            'inst1=arn:aws:secretsmanager:us-east-1:123:secret:s2',
        ],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    with pytest.raises(SystemExit) as exc_info:
        srv.main()
    assert exc_info.value.code == 2


def test_main_secret_arn_two_bare_defaults_exits(mocker):
    """Two bare --secret_arn values (no '=') exits with code 2."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--secret_arn',
            'arn:aws:secretsmanager:us-east-1:123:secret:a',
            '--secret_arn',
            'arn:aws:secretsmanager:us-east-1:123:secret:b',
        ],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    with pytest.raises(SystemExit) as exc_info:
        srv.main()
    assert exc_info.value.code == 2


def test_main_secret_arn_mixed_per_target_and_default(mocker):
    """Mixing per-target and bare --secret_arn values works correctly."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--secret_arn',
            'inst1=arn:aws:secretsmanager:us-east-1:123:secret:specific',
            '--secret_arn',
            'arn:aws:secretsmanager:us-east-1:123:secret:fallback',
        ],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    srv.main()

    assert srv.server_config.configured_secret_arns == {
        'inst1': 'arn:aws:secretsmanager:us-east-1:123:secret:specific',
    }
    assert srv.server_config.configured_default_secret_arn == (
        'arn:aws:secretsmanager:us-east-1:123:secret:fallback'
    )


def test_main_secret_arn_empty_value_exits(mocker):
    """An empty bare --secret_arn value exits with code 2."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--secret_arn',
            '',
        ],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    with pytest.raises(SystemExit) as exc_info:
        srv.main()
    assert exc_info.value.code == 2


def test_main_invalid_connection_method_exits(mocker):
    """Invalid --connection_method at startup exits with code 1."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--connection_method',
            'INVALID_METHOD',
            '--instance_identifier',
            'inst1',
            '--db_endpoint',
            'ep1',
        ],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    with pytest.raises(SystemExit) as exc_info:
        srv.main()
    assert exc_info.value.code == 1


# ─── whitespace stripping in --secret_arn parsing ────────────────────────────


def test_main_secret_arn_whitespace_stripped_per_target(mocker):
    """Whitespace around key and ARN in per-target --secret_arn is stripped."""
    import awslabs.mssql_mcp_server.server as srv

    padded_value = '  inst1  =  arn:aws:secretsmanager:us-east-1:123:secret:x  '
    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--secret_arn',
            padded_value,
        ],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    srv.main()

    assert srv.server_config.configured_secret_arns == {
        'inst1': 'arn:aws:secretsmanager:us-east-1:123:secret:x',
    }


def test_main_secret_arn_whitespace_stripped_bare_default(mocker):
    """Whitespace around a bare default --secret_arn is stripped."""
    import awslabs.mssql_mcp_server.server as srv

    padded_value = '   arn:aws:secretsmanager:us-east-1:123:secret:default   '
    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--secret_arn',
            padded_value,
        ],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    srv.main()

    assert srv.server_config.configured_default_secret_arn == (
        'arn:aws:secretsmanager:us-east-1:123:secret:default'
    )


def test_main_secret_arn_whitespace_only_key_exits(mocker):
    """A per-target value whose key is whitespace-only exits with code 2."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(
        sys,
        'argv',
        [
            'prog',
            '--region',
            'us-east-1',
            '--secret_arn',
            '   =arn:aws:secretsmanager:us-east-1:123:secret:x',
        ],
    )
    mocker.patch.object(srv.mcp, 'run')
    mocker.patch.object(srv.db_connection_map, 'close_all')

    with pytest.raises(SystemExit) as exc_info:
        srv.main()
    assert exc_info.value.code == 2
