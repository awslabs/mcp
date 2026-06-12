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

import json
import pytest
from awslabs.db2_mcp_server.connection.ibm_db_connection import IbmDbConnection
from datetime import date
from decimal import Decimal


DUMMY_PASSWORD = 'pw'  # pragma: allowlist secret
BAD_JSON_PAYLOAD = 'not-json'


def _conn(**kwargs) -> IbmDbConnection:
    defaults = {
        'host': 'db2.example.com',
        'port': 50443,
        'database': 'DB2DB',
        'readonly': True,
        'secret_arn': 'arn:aws:secretsmanager:us-east-1:111122223333:secret:db2',  # pragma: allowlist secret
        'region': 'us-east-1',
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

    def test_default_on_omits_keyword(self):
        """By default the conn string does not disable hostname validation."""
        s = _conn(ssl_encryption='require')._build_conn_string('u', 'p')
        assert 'SSLClientHostnameValidation' not in s

    def test_off_adds_keyword(self):
        """Disabling validation adds SSLClientHostnameValidation=OFF."""
        s = _conn(ssl_encryption='require', ssl_hostname_validation=False)._build_conn_string(
            'u', 'p'
        )
        assert 'SSLClientHostnameValidation=OFF' in s


def _fake_ibm_db(mocker, *, rows, active=False, prepare_ok=True, execute_ok=True, connect_ok=True):
    """Build a fake ibm_db module covering the calls the connection makes."""
    fake = mocker.MagicMock()
    fake.SQL_ATTR_AUTOCOMMIT = 0
    fake.SQL_AUTOCOMMIT_OFF = 0
    fake.SQL_ATTR_QUERY_TIMEOUT = 1
    fake.connect.return_value = 'CONN' if connect_ok else 0
    fake.active.return_value = active
    fake.prepare.return_value = 'STMT' if prepare_ok else 0
    fake.exec_immediate.return_value = 'STMT'
    fake.execute.return_value = execute_ok
    fake.fetch_assoc.side_effect = list(rows) + [None]
    fake.conn_errormsg.return_value = 'conn err'
    fake.stmt_errormsg.return_value = 'stmt err'
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
        """A writable connection commits after execution."""
        fake = _fake_ibm_db(mocker, rows=[])
        c = _conn(readonly=False)
        await c.execute_query('SELECT 1 FROM SYSIBM.SYSDUMMY1')
        fake.commit.assert_called_once()

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
