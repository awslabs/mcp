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

"""ibm_db connection wrapper for the RDS for Db2 MCP Server.

Unlike python-oracledb, the IBM ``ibm_db`` driver is a synchronous C-extension
with no async API and no async connection pool. This module wraps a single
synchronous connection (guarded by a lock) and runs every blocking call in a
worker thread via ``asyncio.to_thread`` so the MCP tools remain ``async``.
"""

import asyncio
import boto3
import ibm_db
import json
import os
import threading
from awslabs.db2_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from botocore.exceptions import ClientError
from datetime import date, datetime, time
from decimal import Decimal
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple, Union, cast


# Service ports for RDS for Db2.
DB2_SSL_PORT = 50443
DB2_TCP_PORT = 50000


class IbmDbConnection(AbstractDBConnection):
    """Synchronous ibm_db connection to Amazon RDS for Db2.

    Credentials are resolved from AWS Secrets Manager. SSL is enabled by
    pointing ``SSLServerCertificate`` at the RDS regional certificate bundle
    (PEM) -- no keystore/keytool required.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        readonly: bool,
        secret_arn: str,
        region: str,
        ssl_encryption: str = 'require',
        ssl_server_certificate: Optional[str] = None,
        ssl_hostname_validation: bool = True,
        query_timeout_s: int = 30,
        login_timeout_s: int = 15,
        is_test: bool = False,
    ):
        """Initialize an ibm_db connection configuration.

        Args:
            host: Db2 endpoint hostname.
            port: Db2 port (50443 SSL, 50000 plain TCP).
            database: Db2 database name.
            readonly: Whether the connection is read-only.
            secret_arn: Secrets Manager ARN holding username/password.
            region: AWS region for Secrets Manager.
            ssl_encryption: 'require' (SSL) or 'off' (plain TCP).
            ssl_server_certificate: Path to the RDS regional PEM bundle. Strongly
                recommended (and required for server certificate validation) when
                ``ssl_encryption='require'``.
            ssl_hostname_validation: When True (default, and recommended for
                production), the driver validates that the server certificate
                matches the endpoint hostname. Set False ONLY when connecting
                through a tunnel/port-forward where the local hostname
                (e.g. 127.0.0.1) cannot match the certificate CN.
            query_timeout_s: Per-query timeout in seconds (0 = no timeout).
            login_timeout_s: Per-connect (TCP/TLS handshake + auth) timeout in
                seconds (0 = no timeout). query_timeout_s only bounds query
                execution; without this, a reconnect to an unreachable/black-holed
                endpoint blocks for the full OS TCP timeout while holding the
                single serialized connection lock, stalling every other query on
                this connection.
            is_test: When True, skips real Secrets Manager / driver calls.
        """
        super().__init__(readonly)
        if ssl_encryption not in ('require', 'off'):
            raise ValueError("ssl_encryption must be 'require' or 'off'")
        # SECURITY=SSL without a server certificate encrypts the channel but does
        # NOT authenticate the server: the driver has no trust anchor to verify the
        # presented certificate, so an on-path attacker can intercept credentials and
        # data (MITM). We therefore require the RDS regional bundle when SSL is on,
        # and fail fast if the path doesn't point at a readable file. (The driver
        # performs the actual chain/hostname validation; this check only guarantees
        # a bundle was supplied and exists.)
        if ssl_encryption == 'require':
            if not ssl_server_certificate:
                raise ValueError(
                    "ssl_server_certificate is required when ssl_encryption='require'. "
                    'Without the RDS regional certificate bundle the server certificate '
                    'cannot be validated, leaving the connection open to man-in-the-middle '
                    'attacks. Download the regional bundle and pass --ssl_server_certificate.'
                )
            if not is_test and not os.path.isfile(ssl_server_certificate):
                raise ValueError(
                    f'ssl_server_certificate not found or not a file: {ssl_server_certificate}'
                )

        self.host = host
        self.port = port
        self.database = database
        self.secret_arn = secret_arn
        self.region = region
        self.ssl_encryption = ssl_encryption
        self.ssl_server_certificate = ssl_server_certificate
        self.ssl_hostname_validation = ssl_hostname_validation
        self.query_timeout_s = query_timeout_s
        self.login_timeout_s = login_timeout_s
        self.is_test = is_test

        # ibm_db connection handles are NOT safe for concurrent use; serialize.
        self._conn = None
        self._lock = threading.Lock()

    @staticmethod
    def _check_dsn_value(label: str, value: str, *, redact: bool = False) -> str:
        """Reject a DSN attribute value that would corrupt or inject into the DSN.

        Values are deliberately NOT brace-quoted. Db2 CLI/ODBC documents ``{}`` for
        values containing delimiters, but that unquoting is performed by the ODBC
        *Driver Manager* -- and there is no Driver Manager in this code path.
        ``ibm_db.connect`` hands a connection string containing ``=`` straight to
        ``SQLDriverConnect`` on the IBM CLI driver (and ignores its own uid/pwd
        arguments in that case), and the CLI driver does not strip the braces. Verified
        against a live RDS for Db2 12.1 instance with ibm_db 3.2.9:

            HOSTNAME={host}  -> SQL1336N  The remote host "{host}" was not found
            UID={u};PWD={p}  -> SQL30082N reason 24 (USERNAME AND/OR PASSWORD INVALID)

        i.e. brace-quoting silently corrupts every value instead of protecting it. So
        the DSN is built unquoted and unsafe values are rejected instead.

        Only ``;`` needs rejecting: the driver splits attributes on ``;`` and then
        splits each attribute at its FIRST ``=``, so a value may legitimately contain
        ``=`` (common in generated passwords) but a ``;`` would truncate it and turn
        the remainder into a bogus attribute. A leading ``{`` is also rejected, since
        the driver may attempt to treat it as an (unsupported) quoted value.

        Args:
            label: human-readable field name for the error message.
            value: the value to check.
            redact: when True, never echo the value in the error (used for secrets).

        Returns:
            The value unchanged, when it is safe to interpolate.
        """
        bad = [c for c in (';',) if c in value]
        if value.startswith('{'):
            bad.append('leading {')
        if bad:
            shown = '<redacted>' if redact else repr(value)
            raise ValueError(
                f'{label} contains a character that cannot be represented in a Db2 '
                f'connection string ({", ".join(bad)}): {shown}. The IBM CLI driver '
                'provides no escaping mechanism on this code path, so the value cannot '
                'be passed safely. Change the value (for a password, rotate the secret '
                'to one without a semicolon).'
            )
        return value

    def _build_conn_string(self, user: str, password: str) -> str:
        """Build the ibm_db (DSN-less) connection string.

        Attribute order is security-relevant: the Db2 CLI driver takes the FIRST
        occurrence of a repeated keyword, so this method's own SECURITY / SSL
        attributes are emitted BEFORE the credentials. That way, even if a credential
        somehow carried a delimiter, anything it could append lands after -- and is
        therefore ignored in favour of -- the SSL posture set here. Do not move UID/PWD
        earlier.
        """
        # database/host originate from MCP tool parameters (agent-supplied), not just
        # operator config: without validation a value like database='DB2DB;SECURITY=NONE'
        # or host='h;SSLClientHostnameValidation=OFF' would inject an attribute into the
        # DSN. Neither a Db2 database name nor a DNS hostname can legitimately contain
        # ';', so rejecting costs nothing.
        database = self._check_dsn_value('database', self.database)
        host = self._check_dsn_value('host', self.host)

        parts = [
            f'DATABASE={database}',
            f'HOSTNAME={host}',
            f'PORT={int(self.port)}',
            'PROTOCOL=TCPIP',
        ]
        if self.ssl_encryption == 'require':
            parts.append('SECURITY=SSL')
            if self.ssl_server_certificate:
                parts.append(
                    'SSLServerCertificate='
                    + self._check_dsn_value('ssl_server_certificate', self.ssl_server_certificate)
                )
            # Emit the hostname-validation mode explicitly rather than relying on the
            # client default: BASIC in production, OFF only for tunnel/port-forward
            # testing where the local hostname cannot match the certificate CN.
            if self.ssl_hostname_validation:
                parts.append('SSLClientHostnameValidation=BASIC')
            else:
                parts.append('SSLClientHostnameValidation=OFF')

        # Credentials last -- see the docstring note on first-occurrence-wins.
        parts.append('UID=' + self._check_dsn_value('username', user))
        parts.append('PWD=' + self._check_dsn_value('password', password, redact=True))
        return ';'.join(parts) + ';'

    def _get_credentials_from_secret(self) -> Tuple[str, str]:
        """Fetch username/password from AWS Secrets Manager."""
        if self.is_test:
            return 'test_user', 'test_password'  # pragma: allowlist secret

        try:
            session = boto3.Session()
            client = session.client(service_name='secretsmanager', region_name=self.region)
            response = client.get_secret_value(SecretId=self.secret_arn)
        except ClientError as e:
            logger.exception(f'Failed to retrieve secret from Secrets Manager: {e}')
            raise ValueError(f'Failed to retrieve credentials from Secrets Manager: {e}') from e

        if 'SecretString' not in response:
            raise ValueError('Secret does not contain a SecretString')
        try:
            secret = json.loads(response['SecretString'])
        except json.JSONDecodeError as e:
            # Do not interpolate the exception: it could echo secret material.
            raise ValueError('Secret value is not valid JSON') from e

        username = secret.get('username') or secret.get('user') or secret.get('Username')
        password = secret.get('password') or secret.get('Password')
        if not username:
            raise ValueError('Secret does not contain a username field')
        if not password:
            raise ValueError('Secret does not contain a password field')
        return username, password

    def _connect_sync(self):
        """Open a synchronous ibm_db connection (autocommit OFF for read-only safety)."""
        user, password = self._get_credentials_from_secret()
        conn_str = self._build_conn_string(user, password)
        # Autocommit OFF so read-only queries can be rolled back, preventing any
        # accidental persistence. Mutating statements are also blocked upstream.
        options: Dict[int, Union[int, str]] = {
            ibm_db.SQL_ATTR_AUTOCOMMIT: ibm_db.SQL_AUTOCOMMIT_OFF
        }
        # query_timeout_s only bounds query execution (SQL_ATTR_QUERY_TIMEOUT, set
        # per-statement in _execute_sync); nothing bounds the connect-time TCP/TLS
        # handshake without this. A reconnect (_ensure_conn_sync) happens while
        # self._lock is held, so an unbounded connect to a black-holed endpoint
        # would stall every other query on this connection for the full OS TCP
        # timeout (tens of seconds to minutes).
        if self.login_timeout_s and self.login_timeout_s > 0:
            options[ibm_db.SQL_ATTR_LOGIN_TIMEOUT] = self.login_timeout_s
        logger.info(
            f'Connecting to Db2 host={self.host} port={self.port} db={self.database} '
            f'ssl={self.ssl_encryption}'
        )
        conn = ibm_db.connect(conn_str, '', '', options)
        if not conn:
            raise ValueError(f'ibm_db.connect failed: {ibm_db.conn_errormsg()}')
        # Autocommit-off is the second layer of the read-only guarantee: the
        # explicit rollback after each read-only query (below) is only meaningful
        # if autocommit is actually off. Read the setting back rather than trusting
        # that the connect-time option was honored -- if a driver/version silently
        # failed to apply it, autocommit would stay ON, every statement would commit
        # immediately, and the rollback would become a no-op while run_query still
        # tells the caller "any uncommitted changes are rolled back". Fail fast
        # instead of quietly running with a false safety guarantee.
        if ibm_db.autocommit(conn) != ibm_db.SQL_AUTOCOMMIT_OFF:
            try:
                ibm_db.close(conn)
            except Exception as e:
                # Best-effort cleanup of the rejected connection; log rather than
                # silently swallow (Bandit B110), matching the close-failure logging
                # convention used elsewhere in this module (_close_sync).
                logger.warning(f'Failed to close connection rejected for bad autocommit: {e}')
            raise ValueError(
                'Failed to disable autocommit on the Db2 connection; refusing to use it '
                '(the read-only rollback-after-query guarantee depends on autocommit being off).'
            )
        return conn

    def _ensure_conn_sync(self):
        """Return a live connection handle, (re)connecting if needed."""
        if self._conn is not None and ibm_db.active(self._conn):
            return self._conn
        self._conn = self._connect_sync()
        return self._conn

    @staticmethod
    def _to_positional(parameters: Optional[List[Dict[str, Any]]]) -> tuple:
        """Convert the structured parameter list to a positional tuple.

        Db2 uses ``?`` positional bind markers, so parameters are bound in the
        order supplied. Each item is ``{'name': ..., 'value': {<typeKey>: v}}``;
        only the value is used for binding.
        """
        if not parameters:
            return ()
        values: List[Any] = []
        for param in parameters:
            value = param.get('value', {})
            if 'stringValue' in value:
                values.append(value['stringValue'])
            elif 'longValue' in value:
                values.append(value['longValue'])
            elif 'doubleValue' in value:
                values.append(value['doubleValue'])
            elif 'booleanValue' in value:
                values.append(value['booleanValue'])
            elif 'blobValue' in value:
                values.append(value['blobValue'])
            elif 'isNull' in value:
                # An explicit null marker binds NULL. A lone {'isNull': False} carries
                # no typed value to bind, so it is treated as NULL as well rather than
                # raising the generic "unrecognized format" error.
                values.append(None)
            else:
                raise ValueError(f'Parameter has unrecognized value format: {list(value.keys())}')
        return tuple(values)

    @staticmethod
    def _normalize(value: Any) -> Any:
        """Coerce Db2/Python values into JSON-friendly primitives."""
        if value is None or isinstance(value, (str, bool, int, float)):
            return value
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        if isinstance(value, (bytes, bytearray, memoryview)):
            # ibm_db can return BINARY/BLOB columns as memoryview, which -- unlike
            # bytes/bytearray -- has no meaningful str() representation (it would
            # serialize as the per-run, address-dependent '<memory at 0x...>' and
            # silently corrupt the row with no error raised). Convert to bytes first
            # so all three binary types decode the same way.
            return bytes(value).decode('utf-8', errors='replace')
        return str(value)

    def _rollback_quietly(self, conn: Any) -> None:
        """Best-effort rollback used to clean up after a mid-statement failure.

        Autocommit is off and the connection is cached and reused, so a statement
        that fails part-way through would otherwise leave an open transaction on the
        shared handle. In read-only mode the next query's end-of-run rollback would
        still undo it, but in write mode a later successful statement's ``commit()``
        would commit the earlier failure's partial state along with its own. Failures
        here are logged rather than raised so they never mask the original error.
        """
        try:
            if not ibm_db.rollback(conn):
                logger.warning(
                    f'Cleanup rollback after a failed statement returned failure: '
                    f'{ibm_db.conn_errormsg()}'
                )
        except Exception as e:
            logger.warning(f'Cleanup rollback after a failed statement raised: {e}')

    def _execute_sync(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]], max_rows: int
    ) -> List[Dict[str, Any]]:
        """Blocking query execution; runs inside a worker thread."""
        with self._lock:
            conn = self._ensure_conn_sync()
            try:
                return self._execute_locked(conn, sql, parameters, max_rows)
            except Exception:
                # Leave the shared connection in a clean transactional state. Without
                # this, a statement that raised after `execute` (or a failed
                # commit/rollback) leaves an open transaction that a later write's
                # commit() would silently persist.
                self._rollback_quietly(conn)
                raise

    def _execute_locked(
        self,
        conn: Any,
        sql: str,
        parameters: Optional[List[Dict[str, Any]]],
        max_rows: int,
    ) -> List[Dict[str, Any]]:
        """Run one statement on an established connection. Caller holds ``self._lock``."""
        stmt = cast(Any, ibm_db.prepare(conn, sql))
        if not stmt:
            raise ValueError(f'ibm_db.prepare failed: {ibm_db.stmt_errormsg()}')
        if self.query_timeout_s and self.query_timeout_s > 0:
            set_option_error = None
            try:
                ok_timeout = ibm_db.set_option(
                    stmt, {ibm_db.SQL_ATTR_QUERY_TIMEOUT: self.query_timeout_s}, 0
                )
            except Exception as e:
                ok_timeout = False
                set_option_error = e
            if not ok_timeout:
                # set_option signals failure via a falsy return as well as by
                # raising. Do NOT silently continue: running without the operator's
                # configured timeout could hold the single serialized connection lock
                # indefinitely (self-inflicted DoS on all tools). Fail the query.
                raise ValueError(
                    f'Refusing to run query: could not enforce the configured '
                    f'{self.query_timeout_s}s query timeout '
                    f'(set_option failed: {set_option_error}).'
                ) from set_option_error

        params = self._to_positional(parameters)
        ok = ibm_db.execute(stmt, params) if params else ibm_db.execute(stmt)
        if not ok:
            raise ValueError(f'ibm_db.execute failed: {ibm_db.stmt_errormsg()}')

        results: List[Dict[str, Any]] = []
        # Only fetch when the statement actually produced a result set. A non-SELECT
        # (INSERT/UPDATE/DELETE/DDL, i.e. every statement the opt-in write mode
        # exists to run) has zero result columns, and on a 0-column statement
        # ibm_db.fetch_assoc RAISES rather than returning falsy: in the pinned
        # driver, _python_ibm_db_get_result_set_info returns -1 when
        # nResultCols == 0, and _python_ibm_db_bind_fetch_helper then does
        # PyErr_SetString(...) / return NULL. Fetching unconditionally therefore
        # made every write fail before ever reaching commit() below.
        try:
            has_result_set = bool(ibm_db.num_fields(stmt))
        except Exception as e:
            # If the column count can't be determined, fall back to attempting the
            # fetch: that is the pre-existing behavior and is correct for SELECT.
            logger.warning(f'ibm_db.num_fields failed; attempting fetch anyway: {e}')
            has_result_set = True

        if has_result_set:
            limit = max_rows + 1 if max_rows and max_rows > 0 else None
            row = cast(Any, ibm_db.fetch_assoc(stmt))
            while row:
                results.append({k: self._normalize(v) for k, v in row.items()})
                if limit is not None and len(results) >= limit:
                    break
                row = cast(Any, ibm_db.fetch_assoc(stmt))
            if not row:
                # The loop above only reaches here with a falsy `row` when the result
                # set was actually exhausted (a `limit`-triggered break leaves `row`
                # holding the last fetched, truthy row). fetch_assoc signals both
                # legitimate end-of-data and a mid-stream fetch error (network drop,
                # LOB/conversion failure) with the same falsy return; the driver
                # conflates the two. Distinguish via SQLSTATE: '02000' is end-of-data,
                # anything else means the result set was truncated and must not be
                # returned as if it were complete.
                sqlstate = ibm_db.stmt_error(stmt)
                if sqlstate and sqlstate != '02000':
                    raise ValueError(
                        f'ibm_db.fetch_assoc failed mid-stream (SQLSTATE {sqlstate}): '
                        f'{ibm_db.stmt_errormsg()}'
                    )

        # Read-only: roll back so nothing is ever persisted. ibm_db.rollback/commit
        # signal failure via a falsy return as well as by raising (the same
        # convention checked above for prepare/execute/set_option) -- check it so a
        # silently-failed rollback can never masquerade as the read-only guarantee
        # holding.
        if self.readonly_query:
            if not ibm_db.rollback(conn):
                raise ValueError(f'ibm_db.rollback failed: {ibm_db.conn_errormsg()}')
        else:
            if not ibm_db.commit(conn):
                raise ValueError(f'ibm_db.commit failed: {ibm_db.conn_errormsg()}')
        return results

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None, max_rows: int = 0
    ) -> List[Dict[str, Any]]:
        """Execute a SQL query off the event loop."""
        return await asyncio.to_thread(self._execute_sync, sql, parameters, max_rows)

    def validate_sync(self) -> None:
        """Validate connectivity synchronously with a lightweight probe.

        Mirrors the same return-value rigor _execute_sync applies to fetch_assoc
        and rollback (both driver calls signal failure via falsy return as well as
        by raising): a probe that fails mid-fetch or fails to roll back must not be
        reported as a successful validation, or connect_to_database would cache a
        connection that didn't actually complete its check.
        """
        with self._lock:
            conn = self._ensure_conn_sync()
            stmt = cast(Any, ibm_db.exec_immediate(conn, 'SELECT 1 FROM SYSIBM.SYSDUMMY1'))
            if not stmt:
                raise ValueError(f'Validation query failed: {ibm_db.stmt_errormsg()}')
            row = cast(Any, ibm_db.fetch_assoc(stmt))
            if not row:
                sqlstate = ibm_db.stmt_error(stmt)
                if sqlstate and sqlstate != '02000':
                    raise ValueError(
                        f'Validation fetch failed (SQLSTATE {sqlstate}): {ibm_db.stmt_errormsg()}'
                    )
            if not ibm_db.rollback(conn):
                raise ValueError(f'Validation rollback failed: {ibm_db.conn_errormsg()}')

    async def check_connection_health(self) -> bool:
        """Return True if a SELECT against SYSIBM.SYSDUMMY1 succeeds."""
        try:
            result = await self.execute_query('SELECT 1 AS ONE FROM SYSIBM.SYSDUMMY1')
            return len(result) > 0
        except Exception as e:
            logger.exception(f'Connection health check failed: {e}')
            return False

    def _close_sync(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    ibm_db.close(self._conn)
                except Exception as e:
                    # Best-effort close: log so an operator debugging a server-side
                    # session/connection leak on RDS Db2 has a local trace, matching
                    # the sibling close paths in db_connection_map.py.
                    logger.warning(f'Failed to close ibm_db connection: {e}')
                finally:
                    self._conn = None

    async def close(self) -> None:
        """Close the ibm_db connection."""
        await asyncio.to_thread(self._close_sync)
