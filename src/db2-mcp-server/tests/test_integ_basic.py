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

"""Live integration tests for the RDS for Db2 MCP server.

These run only against a real RDS for Db2 instance and are deselected by
default. Provide connection details via environment variables and run with
``uv run --frozen pytest -m live`` after exporting RDS_DB2_ENDPOINT,
RDS_DB2_REGION, RDS_DB2_DATABASE, and RDS_DB2_SECRET_ARN.

Requirements: network reachability to the instance (VPC/SG on 50443), a valid
master-user secret, and the RDS regional SSL certificate bundle when SSL is on.
"""

import os
import pytest
from awslabs.db2_mcp_server.connection.ibm_db_connection import IbmDbConnection


pytestmark = pytest.mark.live

_REQUIRED = ('RDS_DB2_ENDPOINT', 'RDS_DB2_REGION', 'RDS_DB2_DATABASE', 'RDS_DB2_SECRET_ARN')


def _require_env():
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        pytest.skip(f'Missing env for live test: {", ".join(missing)}')


@pytest.mark.asyncio
async def test_live_health_check():
    """A read-only connection can run SELECT 1 FROM SYSIBM.SYSDUMMY1."""
    _require_env()
    conn = IbmDbConnection(
        host=os.environ['RDS_DB2_ENDPOINT'],
        port=int(os.environ.get('RDS_DB2_PORT', '50443')),
        database=os.environ['RDS_DB2_DATABASE'],
        readonly=True,
        secret_arn=os.environ['RDS_DB2_SECRET_ARN'],
        region=os.environ['RDS_DB2_REGION'],
        ssl_encryption=os.environ.get('RDS_DB2_SSL', 'require'),
        ssl_server_certificate=os.environ.get('RDS_DB2_SSL_CERT'),
        ssl_hostname_validation=os.environ.get('RDS_DB2_SSL_HOSTNAME_VALIDATION', 'basic')
        != 'off',
    )
    try:
        assert await conn.check_connection_health() is True
    finally:
        await conn.close()


def _live_conn() -> IbmDbConnection:
    """Build a connection from the live-test environment."""
    return IbmDbConnection(
        host=os.environ['RDS_DB2_ENDPOINT'],
        port=int(os.environ.get('RDS_DB2_PORT', '50443')),
        database=os.environ['RDS_DB2_DATABASE'],
        readonly=True,
        secret_arn=os.environ['RDS_DB2_SECRET_ARN'],
        region=os.environ['RDS_DB2_REGION'],
        ssl_encryption=os.environ.get('RDS_DB2_SSL', 'require'),
        ssl_server_certificate=os.environ.get('RDS_DB2_SSL_CERT'),
        ssl_hostname_validation=os.environ.get('RDS_DB2_SSL_HOSTNAME_VALIDATION', 'basic')
        != 'off',
    )


@pytest.mark.asyncio
async def test_live_conn_string_is_accepted_by_the_real_driver():
    """The DSN from _build_conn_string must be one the real CLI driver accepts.

    This is the guard for a class of defect the mocked suite structurally cannot
    catch. Brace-quoting DSN values (`HOSTNAME={host}`, `UID={u};PWD={p}`) looked
    correct against a mocked `ibm_db` and every unit test passed, but the IBM CLI
    driver does not strip those braces -- it resolved the literal `{host}` and
    failed authentication as the literal `{user}`. The package could not connect to
    any Db2 server for a month while CI stayed green.

    A mocked driver can only confirm what we already believed about it. This test
    asserts the one thing the mock cannot: that a real driver accepts what we build.
    """
    _require_env()
    conn = _live_conn()
    try:
        # validate_sync performs a real connect (DSN parse, TCP/TLS, auth) plus a
        # trivial probe query, so it exercises the whole connection string.
        conn.validate_sync()
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_live_write_mode_executes_dml_without_fetching():
    """A non-SELECT must commit rather than raising on the absent result set.

    The mocked suite modeled `fetch_assoc` as returning falsy at end-of-rows, but the
    real driver RAISES on a 0-column statement, so every write failed before reaching
    commit(). This exercises the real 0-column path.

    Creates and drops its own scratch table, so it needs a writable connection and
    touches nothing pre-existing. Skipped unless RDS_DB2_ALLOW_WRITE_TEST is set.
    """
    _require_env()
    if not os.environ.get('RDS_DB2_ALLOW_WRITE_TEST'):
        pytest.skip('Set RDS_DB2_ALLOW_WRITE_TEST=1 to run the live write-path test')

    table = 'MCP_LIVE_PROBE_TMP'
    conn = _live_conn()
    conn._readonly = False  # opt into write mode for this probe only
    try:
        await conn.execute_query(f'CREATE TABLE {table} (C INT)')
        await conn.execute_query(f'INSERT INTO {table} (C) VALUES (1)')
        rows = await conn.execute_query(f'SELECT C FROM {table}')
        assert rows == [{'C': 1}]
    finally:
        try:
            await conn.execute_query(f'DROP TABLE {table}')
        finally:
            await conn.close()
