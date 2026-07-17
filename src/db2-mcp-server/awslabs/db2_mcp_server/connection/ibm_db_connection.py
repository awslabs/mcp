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
        self.is_test = is_test

        # ibm_db connection handles are NOT safe for concurrent use; serialize.
        self._conn = None
        self._lock = threading.Lock()

    def _build_conn_string(self, user: str, password: str) -> str:
        """Build the ibm_db (DSN-less) connection string."""

        def _q(v: str) -> str:
            # Db2 CLI allows wrapping an attribute value in braces so ';' '=' and
            # other delimiters are treated literally. A literal '}' cannot be
            # represented, so reject it rather than emit a corrupt/injectable DSN.
            if '}' in v:
                raise ValueError('Value contains an unsupported character: }')
            return '{' + v + '}'

        # database/host originate from MCP tool parameters (agent-supplied), not just
        # operator config, so they get the same brace-escaping as the credentials.
        # Without it, a value like database="DB2DB;SECURITY=NONE" or
        # host="h;SSLClientHostnameValidation=OFF" would inject an attribute ahead of
        # this method's own SECURITY=SSL / SSLClientHostnameValidation, silently
        # downgrading TLS or disabling hostname validation (first-occurrence-wins).
        parts = [
            f'DATABASE={_q(self.database)}',
            f'HOSTNAME={_q(self.host)}',
            f'PORT={self.port}',
            'PROTOCOL=TCPIP',
            f'UID={_q(user)}',
            f'PWD={_q(password)}',
        ]
        if self.ssl_encryption == 'require':
            parts.append('SECURITY=SSL')
            if self.ssl_server_certificate:
                # Operator-controlled (not an MCP-tool-supplied injection vector), but
                # a ';' in the path would still corrupt the DSN -- brace-escape for
                # consistency/defense-in-depth with the other attributes above.
                parts.append(f'SSLServerCertificate={_q(self.ssl_server_certificate)}')
            # Emit the hostname-validation mode explicitly rather than relying on the
            # client default: BASIC in production, OFF only for tunnel/port-forward
            # testing where the local hostname cannot match the certificate CN.
            if self.ssl_hostname_validation:
                parts.append('SSLClientHostnameValidation=BASIC')
            else:
                parts.append('SSLClientHostnameValidation=OFF')
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
        logger.info(
            f'Connecting to Db2 host={self.host} port={self.port} db={self.database} '
            f'ssl={self.ssl_encryption}'
        )
        conn = ibm_db.connect(conn_str, '', '', options)
        if not conn:
            raise ValueError(f'ibm_db.connect failed: {ibm_db.conn_errormsg()}')
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
        if isinstance(value, (bytes, bytearray)):
            return value.decode('utf-8', errors='replace')
        return str(value)

    def _execute_sync(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]], max_rows: int
    ) -> List[Dict[str, Any]]:
        """Blocking query execution; runs inside a worker thread."""
        with self._lock:
            conn = self._ensure_conn_sync()
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
        """Validate connectivity synchronously with a lightweight probe."""
        with self._lock:
            conn = self._ensure_conn_sync()
            stmt = cast(Any, ibm_db.exec_immediate(conn, 'SELECT 1 FROM SYSIBM.SYSDUMMY1'))
            if not stmt:
                raise ValueError(f'Validation query failed: {ibm_db.stmt_errormsg()}')
            ibm_db.fetch_assoc(stmt)
            ibm_db.rollback(conn)

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
