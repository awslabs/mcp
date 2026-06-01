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

"""Additional tests closing coverage gaps in oracle_mcp_server.

These tests exercise error paths (ClientError, generic Exception), Secrets
Manager integration variants, parameter conversion, startup validation,
identifier parsing edge cases, and connection-map validation branches.
"""

import json
import pytest
from awslabs.oracle_mcp_server.connection.abstract_db_connection import (
    AbstractDBConnection,
)
from awslabs.oracle_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DBConnectionMap,
)
from awslabs.oracle_mcp_server.connection.oracledb_pool_connection import (
    OracledbPoolConnection,
)
from awslabs.oracle_mcp_server.server import (
    ServerConfig,
    db_connection_map,
    internal_create_connection,
    server_config,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock


class DummyCtx:
    """Minimal context stub used to capture error messages."""

    def __init__(self):
        """Record messages emitted via ctx.error for assertions."""
        self.errors = []

    async def error(self, message):
        """Capture the error message."""
        self.errors.append(message)


@pytest.fixture(autouse=True)
def _reset_server_config():
    """Reset server_config and the connection map after each test."""
    defaults = ServerConfig()
    yield
    server_config.readonly_query = defaults.readonly_query
    server_config.default_secret_arn = defaults.default_secret_arn
    server_config.ssl_encryption_mode = defaults.ssl_encryption_mode
    server_config.configured_port = defaults.configured_port
    server_config.max_rows = defaults.max_rows
    server_config.call_timeout_ms = defaults.call_timeout_ms
    with db_connection_map._lock:
        db_connection_map.map.clear()


# --- server.run_query error paths --------------------------------------------


@pytest.mark.asyncio
async def test_run_query_injection_risk_returns_error(mocker):
    """Injection-risk pattern is rejected before the query reaches the DB."""
    from awslabs.oracle_mcp_server.server import run_query
    from mcp.shared.exceptions import McpError

    mock_conn = MagicMock()
    mock_conn.readonly_query = False  # skip the readonly branch
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()

    with pytest.raises(McpError):
        await run_query(
            sql="EXECUTE IMMEDIATE 'DROP TABLE t'",
            ctx=ctx,
            connection_method=ConnectionMethod.ORACLE_PASSWORD,
            db_endpoint='ep1',
            database='ORCL',
        )

    mock_conn.execute_query.assert_not_called()


@pytest.mark.asyncio
async def test_run_query_client_error_returns_structured_error(mocker):
    """A boto3 ClientError from execute_query surfaces code and message."""
    from awslabs.oracle_mcp_server.server import run_query

    err = ClientError(
        error_response={'Error': {'Code': 'AccessDenied', 'Message': 'denied by policy'}},
        operation_name='GetSecretValue',
    )

    mock_conn = MagicMock()
    mock_conn.readonly_query = False
    mock_conn.execute_query = AsyncMock(side_effect=err)
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()

    result = await run_query(
        sql='SELECT 1 FROM DUAL',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        db_endpoint='ep1',
        database='ORCL',
    )

    assert isinstance(result, dict)
    assert result['code'] == 'AccessDenied'
    assert result['message'] == 'denied by policy'
    assert 'ClientError' in result['error'] or 'run_query' in result['error']


@pytest.mark.asyncio
async def test_run_query_generic_exception_returns_error(mocker):
    """A non-ClientError exception is wrapped into a generic error dict."""
    from awslabs.oracle_mcp_server.server import run_query

    mock_conn = MagicMock()
    mock_conn.readonly_query = False
    mock_conn.execute_query = AsyncMock(side_effect=RuntimeError('boom'))
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)
    ctx = DummyCtx()

    result = await run_query(
        sql='SELECT 1 FROM DUAL',
        ctx=ctx,
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        db_endpoint='ep1',
        database='ORCL',
    )

    assert isinstance(result, dict)
    assert 'RuntimeError' in result['error']
    assert 'boom' in result['error']


# --- server.get_table_schema validation --------------------------------------


@pytest.mark.asyncio
async def test_get_table_schema_invalid_name_raises_mcp_error():
    """An invalid table name triggers an McpError before any DB call."""
    from awslabs.oracle_mcp_server.server import get_table_schema
    from mcp.shared.exceptions import McpError

    ctx = DummyCtx()
    with pytest.raises(McpError):
        await get_table_schema(
            connection_method=ConnectionMethod.ORACLE_PASSWORD,
            db_endpoint='ep1',
            database='ORCL',
            table_name='bad name; DROP TABLE x--',
            ctx=ctx,
        )


@pytest.mark.asyncio
async def test_get_table_schema_explicit_schema_name_override(mocker):
    """Explicit schema_name parameter overrides any schema parsed from table_name."""
    from awslabs.oracle_mcp_server.server import get_table_schema

    mock_conn = MagicMock()
    mock_conn.readonly_query = False
    mock_conn.execute_query = AsyncMock(return_value=[])
    mocker.patch.object(db_connection_map, 'get', return_value=mock_conn)

    ctx = DummyCtx()
    await get_table_schema(
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        db_endpoint='ep1',
        database='ORCL',
        table_name='FOO.EMPLOYEES',
        schema_name='HR',  # overrides FOO
        ctx=ctx,
    )

    # Inspect the parameters forwarded to execute_query
    call_args = mock_conn.execute_query.await_args
    params = call_args[0][1]
    owners = [p['value']['stringValue'] for p in params if p['name'] == 'schema_name']
    assert owners == ['HR']


def test_get_database_connection_info_returns_map_keys(mocker):
    """get_database_connection_info returns the list from DBConnectionMap.get_keys()."""
    from awslabs.oracle_mcp_server.server import get_database_connection_info

    sentinel = [{'instance_identifier': 'i1'}]
    mocker.patch.object(db_connection_map, 'get_keys', return_value=sentinel)
    assert get_database_connection_info() is sentinel


# --- server.internal_create_connection RDS describe path ---------------------


def test_internal_create_connection_without_secret_uses_rds_describe(mocker):
    """When no secret_arn is supplied, fall back to RDS describe_db_instances."""
    mocker.patch.object(db_connection_map, 'get', return_value=None)
    mocker.patch.object(db_connection_map, 'set')

    rds_client = MagicMock()
    rds_client.describe_db_instances.return_value = {
        'DBInstances': [
            {
                'MasterUsername': 'admin',
                'MasterUserSecret': {
                    'SecretArn': 'arn:aws:secretsmanager:us-east-1:123:secret:rds'  # pragma: allowlist secret
                },
            }
        ]
    }
    mocker.patch('boto3.client', return_value=rds_client)

    conn, response, replaced = internal_create_connection(
        region='us-east-1',
        connection_method=ConnectionMethod.ORACLE_PASSWORD,
        instance_identifier='my-instance',
        db_endpoint='my-instance.rds.amazonaws.com',
        port=1521,
        database='ORCL',
        service_name='ORCL',
        secret_arn=None,  # force fallback
    )

    assert isinstance(conn, OracledbPoolConnection)
    assert (
        conn.secret_arn
        == 'arn:aws:secretsmanager:us-east-1:123:secret:rds'  # pragma: allowlist secret
    )
    rds_client.describe_db_instances.assert_called_once_with(DBInstanceIdentifier='my-instance')


def test_internal_create_connection_missing_connection_method():
    """Empty connection_method raises ValueError."""
    with pytest.raises(ValueError, match='connection_method'):
        internal_create_connection(
            region='us-east-1',
            connection_method=None,  # type: ignore[arg-type]
            instance_identifier='inst1',
            db_endpoint='ep1',
            port=1521,
            database='ORCL',
            service_name='ORCL',
        )


def test_internal_create_connection_missing_endpoint():
    """Empty db_endpoint raises ValueError."""
    with pytest.raises(ValueError, match='db_endpoint'):
        internal_create_connection(
            region='us-east-1',
            connection_method=ConnectionMethod.ORACLE_PASSWORD,
            instance_identifier='inst1',
            db_endpoint='',
            port=1521,
            database='ORCL',
            service_name='ORCL',
        )


# --- server.main startup failure ----------------------------------------------


def test_main_startup_validation_failure_exits(mocker):
    """validate_sync() failure during startup triggers sys.exit(1)."""
    from awslabs.oracle_mcp_server import server as server_module

    mock_pool_conn = MagicMock(spec=OracledbPoolConnection)
    mock_pool_conn.validate_sync = MagicMock(side_effect=Exception('refused'))

    mocker.patch(
        'sys.argv',
        [
            'prog',
            '--connection_method',
            'ORACLE_PASSWORD',
            '--db_endpoint',
            'myhost.rds.amazonaws.com',
            '--region',
            'us-east-1',
            '--secret_arn',
            'arn:aws:secretsmanager:us-east-1:123:secret:test',
        ],
    )
    mocker.patch.object(server_module, 'mcp')
    mocker.patch(
        'awslabs.oracle_mcp_server.server.internal_create_connection',
        return_value=(mock_pool_conn, {}, None),
    )

    with pytest.raises(SystemExit) as excinfo:
        server_module.main()
    assert excinfo.value.code == 1


def test_main_both_service_name_and_sid_exits(mocker):
    """Passing both --service_name and --sid exits with code 1."""
    from awslabs.oracle_mcp_server import server as server_module

    mocker.patch(
        'sys.argv',
        [
            'prog',
            '--service_name',
            'ORCL',
            '--sid',
            'ORCL',
        ],
    )
    with pytest.raises(SystemExit) as excinfo:
        server_module.main()
    assert excinfo.value.code == 1


def test_main_readonly_appends_notice_to_tool_descriptions(mocker):
    """In readonly mode, main() appends a notice to run_query/get_table_schema."""
    from awslabs.oracle_mcp_server import server as server_module

    mocker.patch('sys.argv', ['prog'])  # readonly is the default
    mocker.patch.object(server_module, 'mcp')

    # Capture the tool description changes
    dummy_run_query = MagicMock()
    dummy_run_query.description = 'base description'
    dummy_get_table_schema = MagicMock()
    dummy_get_table_schema.description = 'base description'

    def tool_lookup(name):
        return {
            'run_query': dummy_run_query,
            'get_table_schema': dummy_get_table_schema,
        }.get(name)

    server_module.mcp._tool_manager = MagicMock()
    server_module.mcp._tool_manager.get_tool = MagicMock(side_effect=tool_lookup)

    server_module.main()

    assert 'READ-ONLY' in dummy_run_query.description
    assert 'READ-ONLY' in dummy_get_table_schema.description


# --- server._parse_identifier_parts edge cases -------------------------------


def test_parse_identifier_parts_unterminated_quote_returns_none():
    """An unterminated double-quoted identifier returns None."""
    from awslabs.oracle_mcp_server.server import _parse_identifier_parts

    # The loop's else-clause only executes if the inner while doesn't break —
    # i.e. when the quote is unterminated. That requires running out of input.
    assert _parse_identifier_parts('"unterminated') is None


def test_parse_identifier_parts_empty_quoted_returns_none():
    """An empty quoted identifier (``""``) is rejected."""
    from awslabs.oracle_mcp_server.server import _parse_identifier_parts

    assert _parse_identifier_parts('""') is None


def test_parse_identifier_parts_null_byte_in_quoted_returns_none():
    """A null byte inside a quoted identifier is rejected."""
    from awslabs.oracle_mcp_server.server import _parse_identifier_parts

    assert _parse_identifier_parts('"bad\0name"') is None


def test_parse_identifier_parts_dot_at_end_returns_none():
    """A trailing dot with no following part is rejected."""
    from awslabs.oracle_mcp_server.server import _parse_identifier_parts

    assert _parse_identifier_parts('schema.') is None


def test_parse_identifier_parts_unexpected_char_returns_none():
    """A non-separator character between parts is rejected."""
    from awslabs.oracle_mcp_server.server import _parse_identifier_parts

    # After consuming 'schema', the next char is '!' which is neither '.' nor end.
    assert _parse_identifier_parts('schema!table') is None


def test_parse_identifier_parts_doubled_quote_escape():
    """A doubled ("") inside a quoted identifier is treated as a literal quote."""
    from awslabs.oracle_mcp_server.server import _parse_identifier_parts

    # Oracle allows "" to mean a literal " inside a quoted identifier.
    parts = _parse_identifier_parts('"he""llo"')
    assert parts is not None
    assert parts == [('he"llo', True)]


def test_identifier_to_catalog_form_unparseable_falls_back_to_upper():
    """Unparseable raw identifiers fall back to .upper()."""
    from awslabs.oracle_mcp_server.server import _identifier_to_catalog_form

    # Raw starting with digit fails the parser → falls back to upper().
    assert _identifier_to_catalog_form('123abc') == '123ABC'


def test_validate_table_name_overlong_identifier_rejected():
    """Identifiers exceeding 128 bytes are rejected."""
    from awslabs.oracle_mcp_server.server import validate_table_name

    overlong = 'A' * 129
    assert validate_table_name(overlong) is False


# --- OracledbPoolConnection parameter conversion variants --------------------


def _make_conn(**overrides):
    """Construct an OracledbPoolConnection with test defaults."""
    defaults = {
        'host': 'localhost',
        'port': 1521,
        'database': 'ORCL',
        'readonly': True,
        'secret_arn': (
            'arn:aws:secretsmanager:us-east-1:123:secret:test'  # pragma: allowlist secret
        ),
        'region': 'us-east-1',
        'service_name': 'ORCL',
        'is_test': True,
    }
    defaults.update(overrides)
    return OracledbPoolConnection(**defaults)


def test_convert_parameters_long_value():
    """LongValue parameters are mapped directly."""
    conn = _make_conn()
    params = [{'name': 'n', 'value': {'longValue': 42}}]
    assert conn._convert_parameters(params) == {'n': 42}


def test_convert_parameters_double_value():
    """DoubleValue parameters are mapped directly."""
    conn = _make_conn()
    params = [{'name': 'n', 'value': {'doubleValue': 3.14}}]
    assert conn._convert_parameters(params) == {'n': 3.14}


def test_convert_parameters_boolean_value():
    """BooleanValue parameters are mapped directly."""
    conn = _make_conn()
    params = [{'name': 'n', 'value': {'booleanValue': True}}]
    assert conn._convert_parameters(params) == {'n': True}


def test_convert_parameters_blob_value():
    """BlobValue parameters are mapped directly."""
    conn = _make_conn()
    data = b'\x00\x01\x02'
    params = [{'name': 'n', 'value': {'blobValue': data}}]
    assert conn._convert_parameters(params) == {'n': data}


def test_convert_parameters_mixed_variants():
    """A mix of parameter variants is converted correctly."""
    conn = _make_conn()
    params = [
        {'name': 's', 'value': {'stringValue': 'hi'}},
        {'name': 'i', 'value': {'longValue': 7}},
        {'name': 'd', 'value': {'doubleValue': 1.5}},
        {'name': 'b', 'value': {'booleanValue': False}},
        {'name': 'n', 'value': {'isNull': True}},
    ]
    assert conn._convert_parameters(params) == {
        's': 'hi',
        'i': 7,
        'd': 1.5,
        'b': False,
        'n': None,
    }


# --- OracledbPoolConnection.execute_query with parameters --------------------


@pytest.mark.asyncio
async def test_execute_query_returns_none_for_null_columns():
    """A row value of None is preserved as None in the returned dict."""
    from datetime import datetime

    conn = _make_conn(readonly=False)

    mock_cursor = MagicMock()
    mock_cursor.description = [('ID',), ('NAME',)]
    mock_cursor.execute = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[(1, None)])
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock()
    mock_conn.commit = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    conn.pool = mock_pool
    conn.created_time = datetime.now()

    result = await conn.execute_query('SELECT ID, NAME FROM t')
    assert result == [{'ID': 1, 'NAME': None}]


@pytest.mark.asyncio
async def test_execute_query_passes_converted_parameters():
    """execute_query converts query_parameters and forwards to cursor.execute."""
    from datetime import datetime

    conn = _make_conn(readonly=False)

    mock_cursor = MagicMock()
    mock_cursor.description = [('NAME',)]
    mock_cursor.execute = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[('Alice',)])
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock()
    mock_conn.commit = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    conn.pool = mock_pool
    conn.created_time = datetime.now()

    params = [{'name': 'owner', 'value': {'stringValue': 'HR'}}]
    result = await conn.execute_query('SELECT NAME FROM t WHERE owner = :owner', params)

    mock_cursor.execute.assert_awaited_once_with(
        'SELECT NAME FROM t WHERE owner = :owner', {'owner': 'HR'}
    )
    assert result == [{'NAME': 'Alice'}]


# --- OracledbPoolConnection secrets manager paths ----------------------------


def test_get_credentials_from_secret_happy_path(mocker):
    """Standard secret with username + password keys is parsed successfully."""
    conn = _make_conn(is_test=False)

    mock_sm = MagicMock()
    mock_sm.get_secret_value.return_value = {
        'SecretString': json.dumps(
            {'username': 'admin', 'password': 's3cr3t'}  # pragma: allowlist secret
        )
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_sm
    mocker.patch('boto3.Session', return_value=mock_session)

    user, password = conn._get_credentials_from_secret(
        'arn:aws:secretsmanager:us-east-1:123:secret:prod',
        'us-east-1',
    )
    assert user == 'admin'
    assert password == 's3cr3t'  # pragma: allowlist secret
    mock_session.client.assert_called_once_with(
        service_name='secretsmanager', region_name='us-east-1'
    )


def test_get_credentials_from_secret_alternate_casings(mocker):
    """Secrets with `user`/`Username`/`Password` keys are still parsed."""
    conn = _make_conn(is_test=False)

    mock_sm = MagicMock()
    mock_sm.get_secret_value.return_value = {
        'SecretString': json.dumps({'user': 'u1', 'Password': 'p1'})  # pragma: allowlist secret
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_sm
    mocker.patch('boto3.Session', return_value=mock_session)

    user, password = conn._get_credentials_from_secret('arn:any', 'us-east-1')
    assert user == 'u1'
    assert password == 'p1'  # pragma: allowlist secret


def test_get_credentials_from_secret_missing_username(mocker):
    """A secret without a username field raises ValueError."""
    conn = _make_conn(is_test=False)

    mock_sm = MagicMock()
    mock_sm.get_secret_value.return_value = {
        'SecretString': json.dumps({'password': 's3cr3t'})  # pragma: allowlist secret
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_sm
    mocker.patch('boto3.Session', return_value=mock_session)

    with pytest.raises(ValueError, match='does not contain username'):
        conn._get_credentials_from_secret('arn:any', 'us-east-1')


def test_get_credentials_from_secret_missing_password(mocker):
    """A secret without a password field raises ValueError."""
    conn = _make_conn(is_test=False)

    mock_sm = MagicMock()
    mock_sm.get_secret_value.return_value = {'SecretString': json.dumps({'username': 'admin'})}
    mock_session = MagicMock()
    mock_session.client.return_value = mock_sm
    mocker.patch('boto3.Session', return_value=mock_session)

    with pytest.raises(ValueError, match='does not contain password'):
        conn._get_credentials_from_secret('arn:any', 'us-east-1')


def test_get_credentials_from_secret_no_secret_string(mocker):
    """When the response has no SecretString, a ValueError is raised."""
    conn = _make_conn(is_test=False)

    mock_sm = MagicMock()
    mock_sm.get_secret_value.return_value = {'SecretBinary': b'not-used'}
    mock_session = MagicMock()
    mock_session.client.return_value = mock_sm
    mocker.patch('boto3.Session', return_value=mock_session)

    with pytest.raises(ValueError, match='does not contain a SecretString'):
        conn._get_credentials_from_secret('arn:any', 'us-east-1')


def test_get_credentials_from_secret_client_error_wrapped(mocker):
    """A botocore ClientError is wrapped as ValueError."""
    conn = _make_conn(is_test=False)

    err = ClientError(
        error_response={'Error': {'Code': 'AccessDenied', 'Message': 'no'}},
        operation_name='GetSecretValue',
    )
    mock_sm = MagicMock()
    mock_sm.get_secret_value.side_effect = err
    mock_session = MagicMock()
    mock_session.client.return_value = mock_sm
    mocker.patch('boto3.Session', return_value=mock_session)

    with pytest.raises(ValueError, match='Failed to retrieve credentials'):
        conn._get_credentials_from_secret('arn:any', 'us-east-1')


# --- DBConnectionMap validation branches -------------------------------------


def test_db_connection_map_get_missing_method_raises():
    """DBConnectionMap.get raises ValueError when method is None."""
    m = DBConnectionMap()
    with pytest.raises(ValueError, match='method'):
        m.get(None, 'inst', 'ep', 'db', 1521)  # type: ignore[arg-type]


def test_db_connection_map_get_empty_database_raises():
    """DBConnectionMap.get raises ValueError when database is empty."""
    m = DBConnectionMap()
    with pytest.raises(ValueError, match='database'):
        m.get(ConnectionMethod.ORACLE_PASSWORD, 'inst', 'ep', '', 1521)


def test_db_connection_map_remove_empty_database_raises():
    """DBConnectionMap.remove raises ValueError when database is empty."""
    m = DBConnectionMap()
    with pytest.raises(ValueError, match='database'):
        m.remove(ConnectionMethod.ORACLE_PASSWORD, 'inst', 'ep', '', 1521)


def test_db_connection_map_close_all_handles_sync_exception():
    """A sync close() that raises during close_all is logged and swallowed."""
    m = DBConnectionMap()
    bad = MagicMock()
    bad.close = MagicMock(side_effect=RuntimeError('nope'))
    m.set(ConnectionMethod.ORACLE_PASSWORD, 'i', 'e', 'd', bad, 1521)

    # Should not raise
    m.close_all()
    assert len(m.map) == 0


def test_db_connection_map_close_all_awaits_async_close():
    """close_all runs awaitable close() coroutines to completion."""
    m = DBConnectionMap()

    call_log: list[str] = []

    class AsyncCloser(AbstractDBConnection):
        def __init__(self):
            super().__init__(readonly=True)

        async def execute_query(self, sql, parameters=None, max_rows=0):
            return []  # pragma: no cover

        async def close(self):
            call_log.append('closed')

        async def check_connection_health(self):
            return True  # pragma: no cover

    m.set(ConnectionMethod.ORACLE_PASSWORD, 'i', 'e', 'd', AsyncCloser(), 1521)
    m.close_all()
    assert call_log == ['closed']
    assert len(m.map) == 0


def test_db_connection_map_close_all_logs_when_loop_active():
    """When an event loop is already running, close_all logs and clears the map."""
    import asyncio

    m = DBConnectionMap()

    class AsyncCloser(AbstractDBConnection):
        def __init__(self):
            super().__init__(readonly=True)

        async def execute_query(self, sql, parameters=None, max_rows=0):
            return []  # pragma: no cover

        async def close(self):
            pass

        async def check_connection_health(self):
            return True  # pragma: no cover

    m.set(ConnectionMethod.ORACLE_PASSWORD, 'i', 'e', 'd', AsyncCloser(), 1521)

    async def runner():
        m.close_all()

    asyncio.get_event_loop_policy()
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(runner())
    finally:
        loop.close()

    # Map is cleared regardless of whether coroutines completed.
    assert len(m.map) == 0


def test_db_connection_map_close_all_gathers_exception():
    """An exception raised by an async close() during gather is logged, not raised."""
    m = DBConnectionMap()

    class BadAsyncCloser(AbstractDBConnection):
        def __init__(self):
            super().__init__(readonly=True)

        async def execute_query(self, sql, parameters=None, max_rows=0):
            return []  # pragma: no cover

        async def close(self):
            raise RuntimeError('async boom')

        async def check_connection_health(self):
            return True  # pragma: no cover

    m.set(ConnectionMethod.ORACLE_PASSWORD, 'i', 'e', 'd', BadAsyncCloser(), 1521)
    # Should not raise.
    m.close_all()
    assert len(m.map) == 0


# --- AbstractDBConnection -----------------------------------------------------


def test_abstract_db_connection_abstract_methods_not_implemented():
    """Subclasses that skip the abstract methods cannot be instantiated."""
    with pytest.raises(TypeError):
        AbstractDBConnection(readonly=True)  # type: ignore[abstract]


# --- __init__ fallback version -----------------------------------------------


def test_init_version_fallback(monkeypatch):
    """When importlib.metadata.version raises, __version__ falls back to the literal in __init__."""
    import awslabs.oracle_mcp_server as pkg
    import importlib
    import re

    def raise_(_):
        raise Exception('not installed')

    monkeypatch.setattr('importlib.metadata.version', raise_)
    reloaded = importlib.reload(pkg)
    try:
        # Assert the fallback is a valid semver literal rather than a specific
        # value, so the test survives release version bumps of __init__.py.
        assert re.fullmatch(r'\d+\.\d+\.\d+', reloaded.__version__)
        assert reloaded.__user_agent__.endswith(reloaded.__version__)
        assert 'oracle-mcp-server' in reloaded.__user_agent__
    finally:
        # Reload once more with the real metadata available so later tests
        # see the normal __version__ again.
        monkeypatch.undo()
        importlib.reload(pkg)
