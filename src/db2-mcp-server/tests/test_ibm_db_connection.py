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

"""Tests for the ibm_db connection wrapper (no live Db2 required)."""

import atexit
import contextlib
import json
import os
import pytest
import tempfile
from awslabs.db2_mcp_server.connection.ibm_db_connection import IbmDbConnection
from datetime import date
from decimal import Decimal
from typing import Any, Dict


DUMMY_PASSWORD = 'pw'  # pragma: allowlist secret
BAD_JSON_PAYLOAD = 'not-json'

# A real (empty) file on disk so the SSL cert existence check passes for the
# is_test=False credential tests. Contents are irrelevant — the driver is mocked.
# delete=False is required because the path is reopened by the code under test, so
# the file is unlinked at interpreter exit instead of leaking into the temp dir.
_CERT_FILE = tempfile.NamedTemporaryFile(prefix='rds-test-', suffix='.pem', delete=False)
_CERT_FILE.write(b'-----BEGIN CERTIFICATE-----\n')
_CERT_FILE.close()
_CERT_PATH = _CERT_FILE.name


@atexit.register
def _cleanup_cert_file() -> None:
    """Remove the module-scoped temp certificate file at interpreter exit."""
    with contextlib.suppress(OSError):
        os.unlink(_CERT_PATH)


def _conn(**kwargs) -> IbmDbConnection:
    defaults = {
        'host': 'db2.example.com',
        'port': 50443,
        'database': 'DB2DB',
        'readonly': True,
        'secret_arn': 'arn:aws:secretsmanager:us-east-1:111122223333:secret:db2',  # pragma: allowlist secret
        'region': 'us-east-1',
        'ssl_server_certificate': _CERT_PATH,
        'is_test': True,
    }
    defaults.update(kwargs)
    return IbmDbConnection(**defaults)


class TestConnString:
    """Tests for connection-string construction."""

    def test_ssl_with_cert(self):
        """SSL mode adds SECURITY=SSL and the certificate path."""
        c = _conn(ssl_encryption='require', ssl_server_certificate='/tmp/rds.pem')
        s = c._build_conn_string('admin', 'pw')
        assert 'SECURITY=SSL' in s
        assert 'SSLServerCertificate=/tmp/rds.pem' in s
        assert 'PORT=50443' in s

    def test_plain_tcp(self):
        """Plain TCP mode omits SSL options."""
        c = _conn(ssl_encryption='off', port=50000)
        s = c._build_conn_string('admin', 'pw')
        assert 'SECURITY=SSL' not in s

    def test_invalid_ssl_mode(self):
        """An invalid SSL mode is rejected."""
        with pytest.raises(ValueError):
            _conn(ssl_encryption='bogus')

    def test_ssl_require_without_certificate_rejected(self):
        """ssl_encryption='require' without a certificate bundle must be rejected.

        SECURITY=SSL with no SSLServerCertificate encrypts but does not authenticate
        the server (MITM exposure), so the connection must fail fast at construction.
        """
        with pytest.raises(ValueError, match='ssl_server_certificate is required'):
            _conn(ssl_encryption='require', ssl_server_certificate=None)

    def test_plain_tcp_without_certificate_allowed(self):
        """ssl_encryption='off' does not require a certificate."""
        c = _conn(ssl_encryption='off', port=50000, ssl_server_certificate=None)
        assert 'SECURITY=SSL' not in c._build_conn_string('admin', 'pw')


class TestPositionalParams:
    """Tests for structured-to-positional parameter conversion."""

    def test_ordering_and_types(self):
        """Parameters bind positionally in order, by value type."""
        params = [
            {'name': 'a', 'value': {'stringValue': 'x'}},
            {'name': 'b', 'value': {'longValue': 5}},
            {'name': 'c', 'value': {'isNull': True}},
        ]
        assert IbmDbConnection._to_positional(params) == ('x', 5, None)

    def test_empty(self):
        """No parameters yields an empty tuple."""
        assert IbmDbConnection._to_positional(None) == ()

    def test_unknown_format(self):
        """An unrecognized value format raises."""
        with pytest.raises(ValueError):
            IbmDbConnection._to_positional([{'name': 'a', 'value': {'weird': 1}}])


class TestNormalize:
    """Tests for value normalization."""

    def test_decimal_to_float(self):
        """Decimals are coerced to float."""
        assert IbmDbConnection._normalize(Decimal('1.5')) == 1.5

    def test_date_iso(self):
        """Dates are ISO-formatted."""
        assert IbmDbConnection._normalize(date(2026, 6, 11)) == '2026-06-11'

    def test_passthrough(self):
        """Primitives pass through unchanged."""
        assert IbmDbConnection._normalize('x') == 'x'
        assert IbmDbConnection._normalize(None) is None

    def test_bytes_and_bytearray_decode(self):
        """bytes/bytearray (e.g. BINARY/BLOB columns) decode to text."""
        assert IbmDbConnection._normalize(b'hello') == 'hello'
        assert IbmDbConnection._normalize(bytearray(b'hello')) == 'hello'

    def test_memoryview_decodes_like_bytes(self):
        """A memoryview must decode the same way as bytes/bytearray, not fall through to str().

        ibm_db can return BINARY/BLOB columns as memoryview. Before the fix, that
        fell through to str(value), which serializes as the per-run,
        address-dependent '<memory at 0x...>' -- silently corrupting the row with
        no error raised.
        """
        mv = memoryview(b'hello')
        out = IbmDbConnection._normalize(mv)
        assert out == 'hello'
        assert '<memory at' not in out


class TestCredentials:
    """Tests for Secrets Manager credential extraction."""

    def test_is_test_shortcut(self):
        """is_test returns deterministic dummy credentials."""
        assert _conn()._get_credentials_from_secret() == ('test_user', 'test_password')

    def test_extract_from_secret(self, mocker):
        """Username/password are parsed from the secret JSON."""
        c = _conn(is_test=False)
        fake_client = mocker.Mock()
        fake_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'admin', 'password': 'pw'})
        }
        fake_session = mocker.Mock()
        fake_session.client.return_value = fake_client
        mocker.patch('boto3.Session', return_value=fake_session)
        assert c._get_credentials_from_secret() == ('admin', 'pw')


class TestHostnameValidation:
    """Tests for the SSL hostname-validation option."""

    def test_default_on_emits_basic(self):
        """By default the conn string explicitly enables BASIC hostname validation."""
        s = _conn(ssl_encryption='require')._build_conn_string('u', 'p')
        assert 'SSLClientHostnameValidation=BASIC' in s

    def test_off_adds_keyword(self):
        """Disabling validation adds SSLClientHostnameValidation=OFF."""
        s = _conn(ssl_encryption='require', ssl_hostname_validation=False)._build_conn_string(
            'u', 'p'
        )
        assert 'SSLClientHostnameValidation=OFF' in s


def _fake_ibm_db(
    mocker,
    *,
    rows,
    active=False,
    prepare_ok=True,
    execute_ok=True,
    connect_ok=True,
    num_fields=None,
):
    """Build a fake ibm_db module covering the calls the connection makes."""
    fake = mocker.MagicMock()
    # Real driver constants. These MUST NOT be collapsed to convenient values: when
    # the attribute key and its value are both 0, a swapped key/value -- or flipping
    # SQL_AUTOCOMMIT_OFF to SQL_AUTOCOMMIT_ON in the connect options -- is
    # indistinguishable to every assertion in the suite, so the test protecting the
    # primary layer of the read-only guarantee cannot fail.
    fake.SQL_ATTR_AUTOCOMMIT = 102
    fake.SQL_AUTOCOMMIT_OFF = 0
    fake.SQL_AUTOCOMMIT_ON = 1
    fake.SQL_ATTR_QUERY_TIMEOUT = 1
    fake.SQL_ATTR_LOGIN_TIMEOUT = 2

    # Derive autocommit() from the options actually passed to connect(), the way a real
    # driver would, rather than hardcoding the answer. Hardcoding it meant the
    # read-back guard in _connect_sync was asserting against a constant and could
    # never observe a connection opened with autocommit ON.
    _connect_state: Dict[str, Any] = {'autocommit': fake.SQL_AUTOCOMMIT_OFF}

    def _fake_connect(_conn_str, _user, _password, options=None):
        if options and fake.SQL_ATTR_AUTOCOMMIT in options:
            _connect_state['autocommit'] = options[fake.SQL_ATTR_AUTOCOMMIT]
        else:
            # No autocommit option supplied -> the driver default is ON.
            _connect_state['autocommit'] = fake.SQL_AUTOCOMMIT_ON
        return 'CONN' if connect_ok else 0

    fake.connect.side_effect = _fake_connect
    fake.autocommit.side_effect = lambda _conn: _connect_state['autocommit']
    fake.active.return_value = active
    fake.prepare.return_value = 'STMT' if prepare_ok else 0
    fake.exec_immediate.return_value = 'STMT'
    fake.execute.return_value = execute_ok
    # Model the real driver: num_fields reports the result-set column count (0 for a
    # non-SELECT), and fetch_assoc RAISES on a 0-column statement rather than
    # returning falsy. Callers that need the DML shape pass num_fields=0.
    fake.num_fields.return_value = num_fields if num_fields is not None else 1
    if num_fields == 0:
        fake.fetch_assoc.side_effect = Exception(
            'Column information cannot be retrieved: [IBM][CLI Driver] '
            'CLI0110E Invalid cursor state.'
        )
    else:
        fake.fetch_assoc.side_effect = list(rows) + [None]
    fake.conn_errormsg.return_value = 'conn err'
    fake.stmt_errormsg.return_value = 'stmt err'
    fake.stmt_error.return_value = '02000'  # legitimate end-of-data by default
    fake.rollback.return_value = True
    fake.commit.return_value = True
    fake.close.return_value = True
    mocker.patch('awslabs.db2_mcp_server.connection.ibm_db_connection.ibm_db', fake)
    return fake


class TestExecuteQuery:
    """Tests for query execution against a mocked ibm_db driver."""

    async def test_readonly_rollback(self, mocker):
        """A read-only query fetches rows and rolls back."""
        fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
        c = _conn(readonly=True)
        out = await c.execute_query('SELECT A FROM T')
        assert out == [{'A': 1}]
        fake.rollback.assert_called_once()

    async def test_write_commits(self, mocker):
        """A writable connection commits after a SELECT (result-set-producing) statement."""
        fake = _fake_ibm_db(mocker, rows=[])
        c = _conn(readonly=False)
        await c.execute_query('SELECT 1 FROM SYSIBM.SYSDUMMY1')
        fake.commit.assert_called_once()

    @pytest.mark.parametrize(
        'sql',
        [
            "INSERT INTO T (C) VALUES ('x')",
            'UPDATE T SET C = 1 WHERE ID = 2',
            'DELETE FROM T WHERE ID = 2',
            'CREATE TABLE T2 (C INT)',
        ],
    )
    async def test_write_dml_commits_without_fetching(self, mocker, sql):
        """A non-SELECT in write mode must commit, not blow up on the absent result set.

        This is the regression test for the write path being non-functional: a
        non-SELECT produces zero result columns, and the real ibm_db.fetch_assoc
        RAISES on a 0-column statement (it does not return falsy), so fetching
        unconditionally made every write fail before reaching commit(). The fake
        here reproduces that raising behavior via num_fields=0, so this test fails
        against the unguarded implementation.
        """
        fake = _fake_ibm_db(mocker, rows=[], num_fields=0)
        c = _conn(readonly=False)
        out = await c.execute_query(sql)
        assert out == []
        fake.fetch_assoc.assert_not_called()
        fake.commit.assert_called_once()
        fake.rollback.assert_not_called()

    async def test_readonly_dml_shape_still_rolls_back(self, mocker):
        """A 0-column statement in read-only mode rolls back rather than raising.

        Read-only mode blocks mutating SQL upstream in run_query, but the driver
        layer must still handle a 0-column statement without raising (e.g. a
        statement the keyword detector doesn't classify as mutating).
        """
        fake = _fake_ibm_db(mocker, rows=[], num_fields=0)
        c = _conn(readonly=True)
        out = await c.execute_query('SET CURRENT SCHEMA = MYSCHEMA')
        assert out == []
        fake.fetch_assoc.assert_not_called()
        fake.rollback.assert_called_once()
        fake.commit.assert_not_called()

    async def test_num_fields_failure_falls_back_to_fetching(self, mocker):
        """If num_fields raises, fall back to fetching (prior behavior, correct for SELECT)."""
        fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
        fake.num_fields.side_effect = Exception('num_fields unavailable')
        c = _conn(readonly=True)
        out = await c.execute_query('SELECT A FROM T')
        assert out == [{'A': 1}]
        fake.fetch_assoc.assert_called()

    async def test_max_rows_truncates_fetch(self, mocker):
        """Fetching stops at max_rows + 1."""
        _fake_ibm_db(mocker, rows=[{'A': 1}, {'A': 2}, {'A': 3}])
        c = _conn(readonly=True)
        out = await c.execute_query('SELECT A FROM T', max_rows=1)
        assert len(out) == 2  # max_rows + 1 sentinel

    async def test_prepare_failure(self, mocker):
        """A prepare failure raises ValueError."""
        _fake_ibm_db(mocker, rows=[], prepare_ok=False)
        with pytest.raises(ValueError, match='prepare'):
            await _conn().execute_query('SELECT 1 FROM SYSIBM.SYSDUMMY1')

    async def test_execute_failure(self, mocker):
        """An execute failure raises ValueError."""
        _fake_ibm_db(mocker, rows=[], execute_ok=False)
        with pytest.raises(ValueError, match='execute'):
            await _conn().execute_query('SELECT 1 FROM SYSIBM.SYSDUMMY1')

    async def test_connect_failure(self, mocker):
        """A connect failure raises ValueError."""
        _fake_ibm_db(mocker, rows=[], connect_ok=False)
        with pytest.raises(ValueError, match='connect'):
            await _conn().execute_query('SELECT 1 FROM SYSIBM.SYSDUMMY1')

    async def test_parameters_bound(self, mocker):
        """Positional parameters are passed to ibm_db.execute."""
        fake = _fake_ibm_db(mocker, rows=[{'X': 1}])
        c = _conn(readonly=True)
        await c.execute_query(
            'SELECT X FROM T WHERE Y = ?',
            parameters=[{'name': 'y', 'value': {'stringValue': 'z'}}],
        )
        fake.execute.assert_called_with('STMT', ('z',))


class TestLifecycle:
    """Tests for validate_sync, health check, and close."""

    def test_validate_sync(self, mocker):
        """validate_sync runs the probe query and rolls back."""
        fake = _fake_ibm_db(mocker, rows=[{'1': 1}])
        _conn(readonly=True).validate_sync()
        fake.exec_immediate.assert_called_once()
        fake.rollback.assert_called_once()

    async def test_health_check_true(self, mocker):
        """A healthy connection returns True."""
        _fake_ibm_db(mocker, rows=[{'ONE': 1}])
        assert await _conn().check_connection_health() is True

    async def test_health_check_false(self, mocker):
        """A failing probe returns False."""
        _fake_ibm_db(mocker, rows=[], execute_ok=False)
        assert await _conn().check_connection_health() is False

    async def test_close(self, mocker):
        """close() invokes ibm_db.close and clears the handle."""
        fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
        c = _conn(readonly=True)
        await c.execute_query('SELECT A FROM T')  # establishes _conn
        await c.close()
        fake.close.assert_called_once()
        assert c._conn is None


class TestCredentialErrors:
    """Error paths for Secrets Manager credential extraction."""

    def _patch_session(self, mocker, *, response=None, side_effect=None):
        """Patch boto3.Session so get_secret_value returns/raises as configured."""
        fake_client = mocker.Mock()
        if side_effect is not None:
            fake_client.get_secret_value.side_effect = side_effect
        else:
            fake_client.get_secret_value.return_value = response
        fake_session = mocker.Mock()
        fake_session.client.return_value = fake_client
        mocker.patch('boto3.Session', return_value=fake_session)

    def test_client_error_raises(self, mocker):
        """A Secrets Manager ClientError is wrapped in a ValueError."""
        from botocore.exceptions import ClientError

        err = ClientError({'Error': {'Code': 'AccessDenied', 'Message': 'no'}}, 'GetSecretValue')
        self._patch_session(mocker, side_effect=err)
        with pytest.raises(ValueError, match='Secrets Manager'):
            _conn(is_test=False)._get_credentials_from_secret()

    def test_missing_secret_string(self, mocker):
        """A response without SecretString raises."""
        self._patch_session(mocker, response={})
        with pytest.raises(ValueError, match='SecretString'):
            _conn(is_test=False)._get_credentials_from_secret()

    def test_invalid_json(self, mocker):
        """A SecretString that is not valid JSON raises."""
        self._patch_session(mocker, response={'SecretString': BAD_JSON_PAYLOAD})
        with pytest.raises(ValueError, match='valid JSON'):
            _conn(is_test=False)._get_credentials_from_secret()

    def test_missing_username(self, mocker):
        """A secret without a username raises."""
        self._patch_session(
            mocker, response={'SecretString': json.dumps({'password': DUMMY_PASSWORD})}
        )
        with pytest.raises(ValueError, match='username'):
            _conn(is_test=False)._get_credentials_from_secret()

    def test_missing_password(self, mocker):
        """A secret without a password raises."""
        self._patch_session(mocker, response={'SecretString': json.dumps({'username': 'admin'})})
        with pytest.raises(ValueError, match='password'):
            _conn(is_test=False)._get_credentials_from_secret()


def test_to_positional_double_boolean_blob():
    """Double, boolean, and blob value types bind positionally."""
    params = [
        {'name': 'd', 'value': {'doubleValue': 1.5}},
        {'name': 'b', 'value': {'booleanValue': True}},
        {'name': 'l', 'value': {'blobValue': b'xyz'}},
    ]
    assert IbmDbConnection._to_positional(params) == (1.5, True, b'xyz')


def test_validate_sync_failure(mocker):
    """A failed validation probe raises ValueError."""
    fake = _fake_ibm_db(mocker, rows=[])
    fake.exec_immediate.return_value = 0
    with pytest.raises(ValueError, match='Validation query failed'):
        _conn(readonly=True).validate_sync()


def test_validate_sync_fetch_midstream_error_raises(mocker):
    """validate_sync mirrors _execute_sync's fetch_assoc EOF-vs-error distinction.

    A falsy fetch_assoc with a non-'02000' SQLSTATE means the probe fetch failed
    mid-stream, not that it cleanly ran out of rows -- must raise, not report a
    successful validation.
    """
    fake = _fake_ibm_db(mocker, rows=[])
    fake.stmt_error.return_value = '08001'  # non-end-of-data SQLSTATE
    with pytest.raises(ValueError, match='Validation fetch failed'):
        _conn(readonly=True).validate_sync()


def test_validate_sync_clean_eof_does_not_raise(mocker):
    """A clean end-of-data ('02000') during the probe fetch is not a fetch error."""
    fake = _fake_ibm_db(mocker, rows=[{'1': 1}])
    fake.stmt_error.return_value = '02000'
    _conn(readonly=True).validate_sync()  # must not raise
    fake.rollback.assert_called_once()


def test_validate_sync_rollback_falsy_return_raises(mocker):
    """A falsy rollback() during validate_sync must raise, not report success.

    Mirrors the same falsy-return check _execute_sync applies to rollback/commit --
    a probe that fails to roll back must not be reported as a successful validation.
    """
    fake = _fake_ibm_db(mocker, rows=[{'1': 1}])
    fake.rollback.return_value = False
    with pytest.raises(ValueError, match='Validation rollback failed'):
        _conn(readonly=True).validate_sync()


def test_credential_error_excludes_secret_material(mocker):
    """A missing-field credential error must not echo secret values or key names."""
    # Secret is valid JSON and contains a password, but no username field.
    payload = {'password': DUMMY_PASSWORD, 'host': 'internal-db.example.com'}
    fake_client = mocker.Mock()
    fake_client.get_secret_value.return_value = {'SecretString': json.dumps(payload)}
    fake_session = mocker.Mock()
    fake_session.client.return_value = fake_client
    mocker.patch('boto3.Session', return_value=fake_session)

    with pytest.raises(ValueError) as exc_info:
        _conn(is_test=False)._get_credentials_from_secret()

    message = str(exc_info.value)
    # No secret value and no secret key names should leak into the error surfaced
    # back to the model/caller.
    assert DUMMY_PASSWORD not in message
    assert 'internal-db.example.com' not in message
    assert 'host' not in message


# --------------------------------------------------------------------------- #
# Additional coverage from review round 2
# --------------------------------------------------------------------------- #


def test_isnull_true_and_false_bind_none():
    """Both {'isNull': True} and an explicit {'isNull': False} bind NULL without raising."""
    params = [
        {'name': 'a', 'value': {'isNull': True}},
        {'name': 'b', 'value': {'isNull': False}},
    ]
    assert IbmDbConnection._to_positional(params) == (None, None)


def test_ssl_require_missing_cert_file_rejected():
    """A cert path that does not point at a real file is rejected (fast-fail)."""
    with pytest.raises(ValueError, match='not found'):
        IbmDbConnection(
            host='h',
            port=50443,
            database='DB2DB',
            readonly=True,
            secret_arn='arn:aws:secretsmanager:us-east-1:111122223333:secret:db2',  # pragma: allowlist secret
            region='us-east-1',
            ssl_encryption='require',
            ssl_server_certificate='/no/such/bundle.pem',
            is_test=False,
        )


async def test_timeout_set_option_failure_refuses_query(mocker):
    """If the configured query timeout cannot be applied, the query is refused.

    Running unbounded would hold the single serialized connection lock indefinitely,
    so execute_query must raise rather than silently drop the safety bound.
    """
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    fake.set_option.side_effect = RuntimeError('driver has no timeout support')
    c = _conn(readonly=True)  # default query_timeout_s=30 -> set_option is attempted
    with pytest.raises(ValueError, match='timeout'):
        await c.execute_query('SELECT A FROM T')


async def test_timeout_set_option_falsy_return_refuses_query(mocker):
    """If set_option returns falsy (False/0), the query is also refused.

    ibm_db.set_option can signal failure by returning falsy without raising, so
    both paths must be checked to avoid silently dropping the timeout.
    """
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    fake.set_option.return_value = 0  # falsy return, no exception
    c = _conn(readonly=True, query_timeout_s=30)
    with pytest.raises(ValueError, match='timeout'):
        await c.execute_query('SELECT A FROM T')


async def test_rollback_falsy_return_raises(mocker):
    """A falsy rollback() return must raise, not be treated as a successful rollback.

    ibm_db.rollback signals failure via a falsy return as well as by raising (the
    same convention already checked for prepare/execute/set_option). If this were
    silently ignored, a read-only query could return its rows as success while
    leaving an open, uncommitted transaction on the shared connection -- the exact
    "nothing is ever persisted" guarantee the read-only mode promises.
    """
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    fake.rollback.return_value = False
    c = _conn(readonly=True)
    with pytest.raises(ValueError, match='rollback'):
        await c.execute_query('SELECT A FROM T')


async def test_commit_falsy_return_raises(mocker):
    """A falsy commit() return must raise, not be treated as a successful commit."""
    fake = _fake_ibm_db(mocker, rows=[])
    fake.commit.return_value = False
    c = _conn(readonly=False)
    with pytest.raises(ValueError, match='commit'):
        await c.execute_query('SELECT 1 FROM SYSIBM.SYSDUMMY1')


async def test_fetch_assoc_midstream_error_raises_not_truncates(mocker):
    """A fetch_assoc failure mid-stream (non-'02000' SQLSTATE) raises, not truncates.

    fetch_assoc returns falsy at both legitimate end-of-data and on a mid-stream
    error (e.g. a network drop or LOB conversion failure); the driver conflates the
    two. A real error must not be silently treated as "the query legitimately
    returned exactly these rows".
    """
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    fake.stmt_error.return_value = '08001'  # non-end-of-data SQLSTATE
    c = _conn(readonly=True)
    with pytest.raises(ValueError, match='mid-stream'):
        await c.execute_query('SELECT A FROM T')


async def test_fetch_assoc_clean_eof_does_not_raise(mocker):
    """A clean end-of-data ('02000' SQLSTATE) is not mistaken for a fetch error."""
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    fake.stmt_error.return_value = '02000'  # legitimate end-of-data
    c = _conn(readonly=True)
    out = await c.execute_query('SELECT A FROM T')
    assert out == [{'A': 1}]


async def test_fetch_assoc_error_not_checked_on_max_rows_truncation(mocker):
    """A max_rows-triggered break does not spuriously check for a fetch error.

    When the loop stops early because max_rows was reached, the last fetched row is
    truthy (not the falsy end/error sentinel), so stmt_error must not be consulted.
    """
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}, {'A': 2}, {'A': 3}])
    c = _conn(readonly=True)
    out = await c.execute_query('SELECT A FROM T', max_rows=1)
    assert out == [{'A': 1}, {'A': 2}]
    fake.stmt_error.assert_not_called()


async def test_close_logs_warning_on_failure(mocker):
    """A failing ibm_db.close is logged, not silently swallowed."""
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    c = _conn(readonly=True)
    await c.execute_query('SELECT A FROM T')  # establishes _conn
    fake.close.side_effect = RuntimeError('close failed')
    log_warning = mocker.patch(
        'awslabs.db2_mcp_server.connection.ibm_db_connection.logger.warning'
    )
    await c.close()
    log_warning.assert_called_once()
    assert c._conn is None


def test_conn_string_does_not_brace_quote_any_value():
    """No value may be brace-quoted -- the CLI driver does not strip the braces.

    Verified against live RDS for Db2 12.1 / ibm_db 3.2.9: HOSTNAME={host} fails with
    SQL1336N naming the literal "{host}", and UID={u};PWD={p} fails with SQL30082N
    reason 24. Brace-quoting is an ODBC Driver Manager convention and there is no
    Driver Manager on this path (ibm_db passes the DSN straight to SQLDriverConnect),
    so quoting silently corrupts every value. This test pins that regression.
    """
    conn_str = _conn(
        database='DB2DB',
        host='db2.example.com',
        ssl_encryption='require',
        ssl_server_certificate='/tmp/rds.pem',
    )._build_conn_string('admin', 'pw')
    assert '{' not in conn_str
    assert '}' not in conn_str
    assert 'DATABASE=DB2DB;' in conn_str
    assert 'HOSTNAME=db2.example.com;' in conn_str
    assert 'UID=admin;' in conn_str
    assert 'PWD=pw;' in conn_str


def test_conn_string_allows_equals_in_password():
    """'=' in a password is safe: the driver splits each attribute at its FIRST '='."""
    conn_str = _conn()._build_conn_string('admin', 'p@ss=w0rd=')
    assert 'PWD=p@ss=w0rd=' in conn_str


def test_conn_string_rejects_semicolon_in_credential():
    """A ';' in a credential would truncate the value, so it is rejected."""
    c = _conn()
    with pytest.raises(ValueError, match='password contains a character'):
        c._build_conn_string('admin', 'pass;word')
    with pytest.raises(ValueError, match='username contains a character'):
        c._build_conn_string('ad;min', 'pw')


def test_conn_string_rejection_never_echoes_the_password():
    """The rejection error must not leak the secret it rejected."""
    with pytest.raises(ValueError) as exc:
        _conn()._build_conn_string('admin', 'sup3rs3cret;x')
    message = str(exc.value)
    assert 'sup3rs3cret' not in message
    assert '<redacted>' in message


def test_conn_string_rejects_leading_brace_in_value():
    """A leading '{' is rejected -- the driver may try to treat it as a quoted value."""
    with pytest.raises(ValueError, match='leading'):
        _conn()._build_conn_string('admin', '{pw')
    with pytest.raises(ValueError, match='leading'):
        _conn(database='{DB2DB')._build_conn_string('admin', 'pw')


def test_conn_string_emits_credentials_after_ssl_attributes():
    """UID/PWD must come after the SSL attributes (first-occurrence-wins ordering).

    The Db2 CLI driver honors the FIRST occurrence of a repeated keyword, so emitting
    the SSL posture before the credentials means nothing a credential could append
    can override SECURITY=SSL or the hostname-validation mode.
    """
    conn_str = _conn(
        ssl_encryption='require', ssl_server_certificate='/tmp/rds.pem'
    )._build_conn_string('admin', 'pw')
    assert conn_str.index('SECURITY=SSL') < conn_str.index('UID=')
    assert conn_str.index('SSLClientHostnameValidation=') < conn_str.index('UID=')
    assert conn_str.index('UID=') < conn_str.index('PWD=')


def test_conn_string_emits_hostname_validation_explicitly():
    """SSLClientHostnameValidation is always emitted (BASIC or OFF) when SSL is on."""
    c_on = _conn(ssl_encryption='require', ssl_hostname_validation=True)
    assert 'SSLClientHostnameValidation=BASIC' in c_on._build_conn_string('u', 'p')

    c_off = _conn(ssl_encryption='require', ssl_hostname_validation=False)
    assert 'SSLClientHostnameValidation=OFF' in c_off._build_conn_string('u', 'p')


def test_conn_string_rejects_database_and_host_attribute_injection():
    """An agent-supplied database/host that would inject a DSN attribute is rejected.

    Neither a Db2 database name nor a DNS hostname can legitimately contain ';', so
    rejecting closes the injection vector at no cost. (Escaping is not an option --
    the CLI driver does not honor brace-quoting on this path.)
    """
    with pytest.raises(ValueError, match='database contains a character'):
        _conn(database='DB2DB;SECURITY=NONE')._build_conn_string('admin', 'pw')
    with pytest.raises(ValueError, match='host contains a character'):
        _conn(host='h;SSLClientHostnameValidation=OFF')._build_conn_string('admin', 'pw')


def test_conn_string_rejects_semicolon_in_cert_path():
    """A ';' in the certificate path would corrupt the DSN, so it is rejected."""
    with pytest.raises(ValueError, match='ssl_server_certificate contains a character'):
        _conn(ssl_encryption='require', ssl_server_certificate='/tmp/a;b.pem')._build_conn_string(
            'admin', 'pw'
        )


async def test_connect_rejects_when_autocommit_not_disabled(mocker):
    """If the driver silently fails to disable autocommit, the connection is refused.

    Autocommit-off is the second layer of the read-only guarantee -- the rollback
    after each read-only query is only meaningful if autocommit is actually off. If
    ibm_db.autocommit() reads back anything other than SQL_AUTOCOMMIT_OFF after
    connect, the connection must not be used (fail fast rather than silently running
    with a false safety guarantee).
    """
    fake = _fake_ibm_db(mocker, rows=[])
    # Simulate a driver that ignores the connect-time option: autocommit reads back ON
    # regardless of what was requested.
    fake.autocommit.side_effect = lambda _conn: fake.SQL_AUTOCOMMIT_ON
    c = _conn(readonly=True)
    with pytest.raises(ValueError, match='autocommit'):
        await c.execute_query('SELECT 1 FROM SYSIBM.SYSDUMMY1')
    # The bad connection must be closed rather than cached for reuse.
    fake.close.assert_called_once()


async def test_connect_accepts_when_autocommit_confirmed_off(mocker):
    """A connection is used normally when autocommit reads back as OFF."""
    _fake_ibm_db(mocker, rows=[{'A': 1}])
    c = _conn(readonly=True)
    out = await c.execute_query('SELECT A FROM T')
    assert out == [{'A': 1}]


async def test_connect_requests_autocommit_off(mocker):
    """The connect options must explicitly request SQL_AUTOCOMMIT_OFF.

    This is the assertion the suite was missing. Autocommit-off is the primary layer
    of the read-only guarantee (the post-query rollback is only meaningful if
    autocommit is actually off), yet nothing checked the autocommit entry in the
    connect options -- so flipping it to SQL_AUTOCOMMIT_ON survived the entire suite.
    With the real driver constants (key 102, OFF 0, ON 1) that mutation is now
    detectable.
    """
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    c = _conn(readonly=True)
    await c.execute_query('SELECT A FROM T')
    options = fake.connect.call_args.args[3]
    assert options[fake.SQL_ATTR_AUTOCOMMIT] == fake.SQL_AUTOCOMMIT_OFF
    # Guard against the key/value collapse that hid this: they must be distinct, or
    # a swapped key/value would be indistinguishable.
    assert fake.SQL_ATTR_AUTOCOMMIT != fake.SQL_AUTOCOMMIT_OFF


async def test_connect_refuses_when_autocommit_option_omitted(mocker):
    """Omitting the autocommit option entirely must be caught by the read-back guard.

    A real driver defaults to autocommit ON, so a regression that dropped the option
    would silently lose the guarantee. The fake models that default.
    """
    fake = _fake_ibm_db(mocker, rows=[])
    mocker.patch.object(
        IbmDbConnection,
        '_build_conn_string',
        return_value='DATABASE=DB2DB;',
    )

    def _connect_without_options(_conn_str, _user, _password, _options=None):
        # Ignore the requested options, as a driver that dropped them would.
        fake.autocommit.side_effect = lambda _c: fake.SQL_AUTOCOMMIT_ON
        return 'CONN'

    fake.connect.side_effect = _connect_without_options
    c = _conn(readonly=True)
    with pytest.raises(ValueError, match='autocommit'):
        await c.execute_query('SELECT 1 FROM SYSIBM.SYSDUMMY1')


async def test_connect_passes_login_timeout_option(mocker):
    """A configured login_timeout_s is passed via SQL_ATTR_LOGIN_TIMEOUT at connect.

    query_timeout_s only bounds query execution; without a connect-time timeout, a
    reconnect to a black-holed endpoint would block for the full OS TCP timeout
    while holding self._lock, stalling every other query on this connection.
    """
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    c = _conn(readonly=True, login_timeout_s=20)
    await c.execute_query('SELECT A FROM T')
    options = fake.connect.call_args.args[3]
    assert options[fake.SQL_ATTR_LOGIN_TIMEOUT] == 20


async def test_connect_omits_login_timeout_when_zero(mocker):
    """login_timeout_s=0 means no connect-time timeout, matching query_timeout_s=0."""
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    c = _conn(readonly=True, login_timeout_s=0)
    await c.execute_query('SELECT A FROM T')
    options = fake.connect.call_args.args[3]
    assert fake.SQL_ATTR_LOGIN_TIMEOUT not in options


async def test_autocommit_rejection_logs_warning_on_close_failure(mocker):
    """A failure while closing the autocommit-rejected connection is logged, not swallowed.

    Bandit (B110/try-except-pass) flags a bare `except Exception: pass` here; the
    cleanup close is genuinely best-effort (the connection is being discarded either
    way), but a failure must still be logged so an operator has a trace, matching the
    close-failure logging convention used elsewhere in this module (_close_sync).
    """
    fake = _fake_ibm_db(mocker, rows=[])
    # Driver ignores the connect-time option and reports autocommit ON.
    fake.autocommit.side_effect = lambda _conn: fake.SQL_AUTOCOMMIT_ON
    fake.close.side_effect = RuntimeError('close failed')
    log_warning = mocker.patch(
        'awslabs.db2_mcp_server.connection.ibm_db_connection.logger.warning'
    )
    c = _conn(readonly=True)
    with pytest.raises(ValueError, match='autocommit'):
        await c.execute_query('SELECT 1 FROM SYSIBM.SYSDUMMY1')
    log_warning.assert_called_once()
    assert 'autocommit' in log_warning.call_args.args[0].lower()


# --------------------------------------------------------------------------- #
# Round-8: transactional cleanup after a mid-statement failure
# --------------------------------------------------------------------------- #


async def test_execute_failure_rolls_back_to_clean_transaction_state(mocker):
    """A statement that fails after execute must leave no open transaction behind.

    Autocommit is off and the connection is cached/reused. Without a cleanup
    rollback, a failed statement's partial state stays in the open transaction, and
    in write mode a later successful statement's commit() would persist it.
    """
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    fake.fetch_assoc.side_effect = Exception('network drop mid-fetch')
    c = _conn(readonly=False)
    with pytest.raises(Exception, match='network drop mid-fetch'):
        await c.execute_query('SELECT A FROM T')
    # Cleanup rollback ran, and the failed statement was never committed.
    fake.rollback.assert_called_once()
    fake.commit.assert_not_called()


async def test_prepare_failure_rolls_back(mocker):
    """A prepare failure also triggers the cleanup rollback."""
    fake = _fake_ibm_db(mocker, rows=[], prepare_ok=False)
    c = _conn(readonly=False)
    with pytest.raises(ValueError, match='prepare'):
        await c.execute_query('SELECT 1 FROM SYSIBM.SYSDUMMY1')
    fake.rollback.assert_called_once()


async def test_commit_failure_rolls_back(mocker):
    """A failed commit is followed by a cleanup rollback so nothing partial lingers."""
    fake = _fake_ibm_db(mocker, rows=[], num_fields=0)
    fake.commit.return_value = False
    c = _conn(readonly=False)
    with pytest.raises(ValueError, match='commit'):
        await c.execute_query("INSERT INTO T (C) VALUES ('x')")
    fake.rollback.assert_called_once()


async def test_cleanup_rollback_failure_does_not_mask_original_error(mocker):
    """If the cleanup rollback itself fails, the original error still propagates."""
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    fake.fetch_assoc.side_effect = Exception('original failure')
    fake.rollback.side_effect = Exception('rollback also failed')
    log_warning = mocker.patch(
        'awslabs.db2_mcp_server.connection.ibm_db_connection.logger.warning'
    )
    c = _conn(readonly=False)
    with pytest.raises(Exception, match='original failure'):
        await c.execute_query('SELECT A FROM T')
    log_warning.assert_called()


async def test_cleanup_rollback_falsy_return_is_logged(mocker):
    """A falsy cleanup rollback is logged, not raised, so it can't mask the real error."""
    fake = _fake_ibm_db(mocker, rows=[{'A': 1}])
    fake.fetch_assoc.side_effect = Exception('original failure')
    fake.rollback.return_value = False
    log_warning = mocker.patch(
        'awslabs.db2_mcp_server.connection.ibm_db_connection.logger.warning'
    )
    c = _conn(readonly=False)
    with pytest.raises(Exception, match='original failure'):
        await c.execute_query('SELECT A FROM T')
    log_warning.assert_called()
