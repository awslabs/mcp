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

"""Tests for server tools, helpers, the connection factory, and main()."""

import pytest
import sys
from awslabs.db2_mcp_server import server
from awslabs.db2_mcp_server.connection.db_connection_map import (
    DEFAULT_DB2_SSL_PORT,
    ConnectionMethod,
)
from awslabs.db2_mcp_server.connection.ibm_db_connection import DB2_TCP_PORT
from botocore.exceptions import ClientError
from mcp.shared.exceptions import McpError
from unittest.mock import AsyncMock, MagicMock


# Dummy ARNs for tests (not real secrets)
DUMMY_RDS_SECRET_ARN = 'arn:rds'  # pragma: allowlist secret
DUMMY_DB2_SECRET_ARN = 'arn:aws:secretsmanager:...:secret:db2'  # pragma: allowlist secret


# --------------------------------------------------------------------------- #
# Fixtures / fakes
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def restore_server_config():
    """Snapshot and restore the global server_config around each test."""
    snapshot = dict(server.server_config.__dict__)
    yield
    server.server_config.__dict__.update(snapshot)


class FakeCtx:
    """Minimal MCP Context with an async error() sink."""

    def __init__(self):
        """Initialize the fake context."""
        self.errors = []

    async def error(self, message):
        """Record an error message."""
        self.errors.append(message)


class FakeConn:
    """Fake DB connection implementing the bits run_query touches."""

    def __init__(self, readonly=True, rows=None, exc=None):
        """Initialize the fake connection."""
        self.readonly_query = readonly
        self._rows = rows if rows is not None else []
        self._exc = exc
        self.secret_arn = 'arn:secret'  # pragma: allowlist secret

    async def execute_query(self, sql, parameters=None, max_rows=0):
        """Return canned rows or raise the configured exception."""
        if self._exc:
            raise self._exc
        return self._rows


def _client_error(code='AccessDenied', message='nope'):
    return ClientError({'Error': {'Code': code, 'Message': message}}, 'op')


# --------------------------------------------------------------------------- #
# run_query
# --------------------------------------------------------------------------- #


class TestRunQuery:
    """Tests for the run_query tool."""

    async def test_no_connection_returns_error(self, mocker):
        """When no cached connection exists, an error dict is returned."""
        mocker.patch.object(server.db_connection_map, 'get', return_value=None)
        ctx = FakeCtx()
        out = await server.run_query('SELECT 1 FROM SYSIBM.SYSDUMMY1', ctx, 'host', 'DB2DB')
        assert 'error' in out
        assert ctx.errors

    async def test_success_wraps_data(self, mocker):
        """A successful read-only query returns wrapped data with the read-only note."""
        server.server_config.readonly_query = True
        server.server_config.max_rows = 1000
        mocker.patch.object(
            server.db_connection_map, 'get', return_value=FakeConn(rows=[{'A': 1}])
        )
        out = await server.run_query('SELECT A FROM T', FakeCtx(), 'host', 'DB2DB')
        assert 'UNTRUSTED database content' in out
        assert '"A":1' in out
        assert 'read-only mode' in out

    async def test_readonly_rejects_mutating(self, mocker):
        """A mutating statement is rejected in read-only mode."""
        mocker.patch.object(server.db_connection_map, 'get', return_value=FakeConn(readonly=True))
        with pytest.raises(McpError):
            await server.run_query('DELETE FROM T', FakeCtx(), 'host', 'DB2DB')

    async def test_readonly_rejects_transaction_bypass(self, mocker):
        """A COMMIT in read-only mode is rejected as a bypass attempt."""
        mocker.patch.object(server.db_connection_map, 'get', return_value=FakeConn(readonly=True))
        with pytest.raises(McpError):
            await server.run_query(
                'SELECT 1 FROM SYSIBM.SYSDUMMY1; COMMIT', FakeCtx(), 'h', 'DB2DB'
            )

    async def test_injection_rejected(self, mocker):
        """A suspicious injection pattern is rejected."""
        server.server_config.readonly_query = True
        mocker.patch.object(server.db_connection_map, 'get', return_value=FakeConn(readonly=False))
        with pytest.raises(McpError):
            await server.run_query('SELECT * FROM T WHERE 1=1 OR 1=1', FakeCtx(), 'h', 'DB2DB')

    async def test_truncation_note(self, mocker):
        """Results beyond max_rows are truncated with a note."""
        server.server_config.readonly_query = False
        server.server_config.max_rows = 2
        mocker.patch.object(
            server.db_connection_map,
            'get',
            return_value=FakeConn(readonly=False, rows=[{'A': i} for i in range(5)]),
        )
        out = await server.run_query('SELECT A FROM T', FakeCtx(), 'host', 'DB2DB')
        assert 'truncated' in out.lower()

    async def test_client_error(self, mocker):
        """A ClientError from execute_query is surfaced as a structured dict."""
        mocker.patch.object(
            server.db_connection_map,
            'get',
            return_value=FakeConn(readonly=False, exc=_client_error('Throttling', 'slow down')),
        )
        out = await server.run_query('SELECT 1 FROM SYSIBM.SYSDUMMY1', FakeCtx(), 'h', 'DB2DB')
        assert out['code'] == 'Throttling'

    async def test_generic_exception(self, mocker):
        """A generic exception is surfaced as an error dict."""
        mocker.patch.object(
            server.db_connection_map,
            'get',
            return_value=FakeConn(readonly=False, exc=RuntimeError('boom')),
        )
        out = await server.run_query('SELECT 1 FROM SYSIBM.SYSDUMMY1', FakeCtx(), 'h', 'DB2DB')
        assert 'error' in out and 'boom' in out['error']


# --------------------------------------------------------------------------- #
# get_table_schema
# --------------------------------------------------------------------------- #


class TestGetTableSchema:
    """Tests for the get_table_schema tool."""

    async def test_invalid_table_name(self):
        """An invalid table name raises McpError."""
        with pytest.raises(McpError):
            await server.get_table_schema('host', 'DB2DB', '1bad', FakeCtx())

    async def test_invalid_schema_name(self):
        """An invalid schema name raises McpError."""
        with pytest.raises(McpError):
            await server.get_table_schema('host', 'DB2DB', 'T', FakeCtx(), schema_name='1bad')

    async def test_with_schema(self, mocker):
        """With a schema, the catalog query filters on TABSCHEMA and uppercases names."""
        rq = mocker.patch.object(server, 'run_query', new=AsyncMock(return_value='ok'))
        await server.get_table_schema(
            'host', 'DB2DB', 'systables', FakeCtx(), schema_name='sysibm'
        )
        kwargs = rq.call_args.kwargs
        assert 'TABSCHEMA = ?' in kwargs['sql']
        vals = [p['value']['stringValue'] for p in kwargs['query_parameters']]
        assert vals == ['SYSTABLES', 'SYSIBM']

    async def test_without_schema(self, mocker):
        """Without a schema, the query filters on TABNAME only."""
        rq = mocker.patch.object(server, 'run_query', new=AsyncMock(return_value='ok'))
        await server.get_table_schema('host', 'DB2DB', 'T', FakeCtx())
        sql = rq.call_args.kwargs['sql']
        assert 'WHERE TABNAME = ?' in sql and 'TABSCHEMA = ?' not in sql


# --------------------------------------------------------------------------- #
# connect_to_database / is_database_connected / connection info
# --------------------------------------------------------------------------- #


class TestConnectTool:
    """Tests for connect_to_database and connection-info tools."""

    async def test_connect_success(self, mocker):
        """connect_to_database returns the llm_response from the factory."""
        mocker.patch.object(
            server, 'internal_create_connection', return_value=(object(), {'status': 'Connected'})
        )
        out = await server.connect_to_database('us-east-1', 'host')
        assert out['status'] == 'Connected'

    async def test_connect_failure(self, mocker):
        """A factory error is returned as a Failed status."""
        mocker.patch.object(
            server, 'internal_create_connection', side_effect=ValueError('bad secret')
        )
        out = await server.connect_to_database('us-east-1', 'host')
        assert out['status'] == 'Failed' and 'bad secret' in out['error']

    def test_is_database_connected(self, mocker):
        """is_database_connected reflects the connection map."""
        mocker.patch.object(server.db_connection_map, 'get', return_value=FakeConn())
        assert server.is_database_connected('host') is True
        mocker.patch.object(server.db_connection_map, 'get', return_value=None)
        assert server.is_database_connected('host') is False

    def test_get_connection_info(self, mocker):
        """get_database_connection_info delegates to the map."""
        mocker.patch.object(
            server.db_connection_map, 'get_keys', return_value=[{'db_endpoint': 'h'}]
        )
        assert server.get_database_connection_info() == [{'db_endpoint': 'h'}]


# --------------------------------------------------------------------------- #
# Discovery tools
# --------------------------------------------------------------------------- #


class TestDiscovery:
    """Tests for list_db2_instances and describe_db2_instance."""

    async def test_list_filters_db2(self, mocker):
        """Only db2-engine instances are summarized."""
        rds = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                'DBInstances': [
                    {'DBInstanceIdentifier': 'a', 'Engine': 'db2-se', 'Endpoint': {'Port': 50443}},
                    {'DBInstanceIdentifier': 'b', 'Engine': 'postgres'},
                ]
            }
        ]
        rds.get_paginator.return_value = paginator
        mocker.patch.object(server.boto3, 'client', return_value=rds)
        out = await server.list_db2_instances('us-east-1')
        assert '"a"' in out and 'postgres' not in out

    async def test_list_client_error(self, mocker):
        """A ClientError from RDS is surfaced as a structured dict."""
        rds = MagicMock()
        rds.get_paginator.side_effect = _client_error()
        mocker.patch.object(server.boto3, 'client', return_value=rds)
        out = await server.list_db2_instances('us-east-1')
        assert out['code'] == 'AccessDenied'

    async def test_describe_found(self, mocker):
        """describe_db2_instance summarizes a found instance."""
        rds = MagicMock()
        rds.describe_db_instances.return_value = {
            'DBInstances': [{'DBInstanceIdentifier': 'a', 'Engine': 'db2-se'}]
        }
        mocker.patch.object(server.boto3, 'client', return_value=rds)
        out = await server.describe_db2_instance('us-east-1', 'a')
        assert '"a"' in out

    async def test_describe_not_found(self, mocker):
        """An empty result yields an error message."""
        rds = MagicMock()
        rds.describe_db_instances.return_value = {'DBInstances': []}
        mocker.patch.object(server.boto3, 'client', return_value=rds)
        out = await server.describe_db2_instance('us-east-1', 'missing')
        assert 'error' in out

    async def test_describe_client_error(self, mocker):
        """A ClientError is surfaced as a structured dict."""
        rds = MagicMock()
        rds.describe_db_instances.side_effect = _client_error('DBInstanceNotFound', 'no')
        mocker.patch.object(server.boto3, 'client', return_value=rds)
        out = await server.describe_db2_instance('us-east-1', 'a')
        assert out['code'] == 'DBInstanceNotFound'


# --------------------------------------------------------------------------- #
# internal_create_connection
# --------------------------------------------------------------------------- #


class TestInternalCreateConnection:
    """Tests for the connection factory."""

    def test_requires_region(self):
        """A missing region raises ValueError."""
        with pytest.raises(ValueError):
            server.internal_create_connection('', 'id', 'host', 50443, 'DB2DB')

    def test_returns_cached(self, mocker):
        """An existing cached connection is reused."""
        cached = FakeConn()
        cached.secret_arn = 'arn:secret'  # pragma: allowlist secret
        mocker.patch.object(server.db_connection_map, 'get', return_value=cached)
        conn, resp = server.internal_create_connection(
            'us-east-1',
            'id',
            'host',
            50443,
            'DB2DB',
            secret_arn='arn:secret',  # pragma: allowlist secret
        )
        assert conn is cached and 'cached' in resp['status'].lower()

    def test_explicit_secret_creates_connection(self, mocker):
        """An explicit secret_arn skips RDS describe and builds a connection."""
        mocker.patch.object(server.db_connection_map, 'get', return_value=None)
        set_spy = mocker.patch.object(server.db_connection_map, 'set')
        fake = mocker.patch.object(server, 'IbmDbConnection', return_value=FakeConn())
        conn, resp = server.internal_create_connection(
            'us-east-1',
            'id',
            'host',
            50443,
            'DB2DB',
            secret_arn='arn:explicit',  # pragma: allowlist secret
        )
        assert resp['status'] == 'Connected'
        fake.assert_called_once()
        set_spy.assert_called_once()

    def test_resolves_rds_master_secret(self, mocker):
        """With no secret, the RDS managed master secret is resolved."""
        mocker.patch.object(server.db_connection_map, 'get', return_value=None)
        mocker.patch.object(server.db_connection_map, 'set')
        mocker.patch.object(server, 'IbmDbConnection', return_value=FakeConn())
        rds = MagicMock()
        rds.describe_db_instances.return_value = {
            'DBInstances': [{'MasterUserSecret': {'SecretArn': DUMMY_RDS_SECRET_ARN}}]
        }
        mocker.patch.object(server.boto3, 'client', return_value=rds)
        conn, resp = server.internal_create_connection('us-east-1', 'id', 'host', 50443, 'DB2DB')
        assert resp['status'] == 'Connected'

    def test_instance_not_found(self, mocker):
        """A DBInstanceNotFound error becomes a clear ValueError."""
        mocker.patch.object(server.db_connection_map, 'get', return_value=None)
        rds = MagicMock()
        rds.describe_db_instances.side_effect = _client_error('DBInstanceNotFound', 'no')
        mocker.patch.object(server.boto3, 'client', return_value=rds)
        with pytest.raises(ValueError, match='not found'):
            server.internal_create_connection('us-east-1', 'id', 'host', 50443, 'DB2DB')

    def test_no_managed_secret(self, mocker):
        """An instance without a managed secret raises a helpful ValueError."""
        mocker.patch.object(server.db_connection_map, 'get', return_value=None)
        rds = MagicMock()
        rds.describe_db_instances.return_value = {'DBInstances': [{}]}
        mocker.patch.object(server.boto3, 'client', return_value=rds)
        with pytest.raises(ValueError, match='managed master secret'):
            server.internal_create_connection('us-east-1', 'id', 'host', 50443, 'DB2DB')


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


class TestResolvePort:
    """Tests for SSL-mode-aware port resolution."""

    def test_explicit_port_wins(self):
        """An explicit port overrides the SSL-mode default."""
        assert server._resolve_port(60000) == 60000

    def test_ssl_default(self):
        """SSL mode resolves to 50443 when no port is given."""
        server.server_config.ssl_encryption_mode = 'require'
        assert server._resolve_port(None) == DEFAULT_DB2_SSL_PORT

    def test_plain_default(self):
        """Plain TCP mode resolves to 50000 when no port is given."""
        server.server_config.ssl_encryption_mode = 'off'
        assert server._resolve_port(None) == DB2_TCP_PORT


class TestIdentifierValidation:
    """Tests for Db2 identifier validation and catalog form."""

    @pytest.mark.parametrize(
        'name,valid',
        [
            ('EMPLOYEE', True),
            ('myschema.mytable', True),
            ('"Mixed Case"', True),
            ('a.b.c', False),
            ('1bad', False),
            ('', False),
            (None, False),
            ('"a""b"', True),  # doubled quote = one escaped quote inside a quoted id
            ('""', False),  # empty quoted identifier
            ('"open', False),  # unterminated quoted identifier
            ('a.', False),  # trailing separator
            ('a b', False),  # invalid character after first part
            ('"a\x00b"', False),  # NUL inside quoted identifier
            ('A' * 129, False),  # exceeds the max identifier byte length
        ],
    )
    def test_validate_identifier(self, name, valid):
        """Identifier validation accepts valid one/two-part names only."""
        assert server.validate_identifier(name) is valid

    def test_catalog_form_uppercases_unquoted(self):
        """Unquoted identifiers fold to uppercase in catalog form."""
        assert server._catalog_form('employee') == 'EMPLOYEE'

    def test_catalog_form_preserves_quoted(self):
        """Quoted identifiers preserve case."""
        assert server._catalog_form('"MixedCase"') == 'MixedCase'

    def test_catalog_form_qualified_falls_back(self):
        """A multi-part name falls back to uppercasing the whole string."""
        assert server._catalog_form('a.b') == 'A.B'


class TestSummarizeInstance:
    """Tests for describe_db_instances summarization."""

    def test_summary_extracts_connection_fields(self):
        """The summary surfaces endpoint, port, and master secret ARN."""
        inst = {
            'DBInstanceIdentifier': 'db2-prod',
            'Engine': 'db2-se',
            'Endpoint': {'Address': 'db2.rds.amazonaws.com', 'Port': 50443},
            'MasterUserSecret': {'SecretArn': DUMMY_DB2_SECRET_ARN},
        }
        out = server._summarize_instance(inst)
        assert out['endpoint_address'] == 'db2.rds.amazonaws.com'
        assert out['endpoint_port'] == 50443
        assert out['master_user_secret_arn'] == DUMMY_DB2_SECRET_ARN


class TestWrapUntrustedData:
    """Tests for untrusted-data wrapping."""

    def test_wrap_contains_boundary_and_payload(self):
        """Wrapped data carries a boundary marker and the serialized payload."""
        wrapped = server._wrap_untrusted_data([{'COLNAME': 'ID'}])
        assert 'UNTRUSTED database content' in wrapped and 'COLNAME' in wrapped


# --------------------------------------------------------------------------- #
# main()
# --------------------------------------------------------------------------- #


class TestMain:
    """Tests for the CLI entry point."""

    def test_main_readonly_default(self, mocker, monkeypatch):
        """main() defaults to read-only and starts the server."""
        monkeypatch.setattr(sys, 'argv', ['prog', '--region', 'us-east-1'])
        run = mocker.patch.object(server.mcp, 'run')
        mocker.patch.object(server.db_connection_map, 'close_all')
        server.main()
        assert server.server_config.readonly_query is True
        run.assert_called_once()

    def test_main_write_and_hostname_off(self, mocker, monkeypatch):
        """--allow_write_query and --ssl_hostname_validation off are honored."""
        monkeypatch.setattr(
            sys,
            'argv',
            ['prog', '--allow_write_query', '--ssl_hostname_validation', 'off'],
        )
        mocker.patch.object(server.mcp, 'run')
        mocker.patch.object(server.db_connection_map, 'close_all')
        server.main()
        assert server.server_config.readonly_query is False
        assert server.server_config.ssl_hostname_validation is False

    def test_main_startup_connect_validates(self, mocker, monkeypatch):
        """With --db_endpoint, main() creates and validates a connection at startup."""
        monkeypatch.setattr(
            sys,
            'argv',
            [
                'prog',
                '--region',
                'us-east-1',
                '--db_endpoint',
                'host',
                '--secret_arn',
                'arn:x',
            ],  # pragma: allowlist secret
        )
        validated = MagicMock()
        mocker.patch.object(
            server, 'internal_create_connection', return_value=(validated, {'status': 'Connected'})
        )
        mocker.patch.object(server.mcp, 'run')
        mocker.patch.object(server.db_connection_map, 'close_all')
        server.main()
        validated.validate_sync.assert_called_once()

    def test_main_endpoint_requires_region_exits(self, mocker, monkeypatch):
        """--db_endpoint without --region exits with a non-zero status."""
        monkeypatch.setattr(sys, 'argv', ['prog', '--db_endpoint', 'host'])
        mocker.patch.object(server.mcp, 'run')
        mocker.patch.object(server.db_connection_map, 'close_all')
        with pytest.raises(SystemExit):
            server.main()

    def test_main_startup_validate_failure_exits(self, mocker, monkeypatch):
        """A failed startup validation exits with a non-zero status."""
        monkeypatch.setattr(
            sys,
            'argv',
            [
                'prog',
                '--region',
                'us-east-1',
                '--db_endpoint',
                'host',
                '--secret_arn',
                'arn:x',
            ],  # pragma: allowlist secret
        )
        bad = MagicMock()
        bad.validate_sync.side_effect = RuntimeError('boom')
        mocker.patch.object(
            server, 'internal_create_connection', return_value=(bad, {'status': 'Connected'})
        )
        mocker.patch.object(server.mcp, 'run')
        mocker.patch.object(server.db_connection_map, 'close_all')
        with pytest.raises(SystemExit):
            server.main()


def test_connection_method_enum():
    """The DB2 password connection method is defined."""
    assert ConnectionMethod.DB2_PASSWORD.value == 'db2_password'
