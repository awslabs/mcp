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

"""What happens to a statement after the guard approves it, without a database.

``tests/test_sql_guard*.py`` prove the guard reaches the right verdict. They stop
there, and the verdict is not the whole story: ``run_query`` still has to hand the
statement to a connection unchanged, and the psycopg path still rewrites
placeholders and opens a read-only transaction before executing. A read can
satisfy the guard and then be corrupted or executed with the wrong transaction
mode, which the guard cannot see and a pure guard test cannot catch.

These tests cover that seam with mocks, so they run in CI with no PostgreSQL and
no MCP server process:

* a guard-approved read reaches ``execute_query`` with its SQL byte-identical;
* a guard-rejected statement never reaches the connection at all;
* the psycopg executor issues ``SET TRANSACTION READ ONLY`` before the statement
  when the connection is read-only, and does not when it is not;
* the SQL the executor actually hands to the driver still parses.

The layer above this -- the guard and the read-only transaction acting together
against a real engine -- is only observable end-to-end, and lives in
``tests/e2e/e2e_integration_test.py``.
"""

import pytest
import re
from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import PsycopgPoolConnection
from awslabs.postgres_mcp_server.server import ConnectionMethod, run_query
from conftest import DummyCtx
from pglast import parse_sql
from test_policy_matrix import (
    SET_1_READS,
    SET_2_WRITES,
    SET_3_DANGEROUS,
    SET_4_FAIL_CLOSED,
)
from unittest.mock import AsyncMock, patch


# A few representative reads from the read-only corpus, including the shapes that
# cross the placeholder rewrite.
GUARD_APPROVED_READS = [
    'SELECT 1',
    'SELECT * FROM fp.emp WHERE salary > 50',
    'WITH x AS (SELECT 1) SELECT * FROM x',
    'SELECT tags[1:2] FROM fp.dept',
    "SELECT column_name FROM information_schema.columns WHERE table_name = 'emp'",
    'EXPLAIN ANALYZE SELECT 1',
    'SHOW work_mem',
]

GUARD_REJECTED_STATEMENTS = [
    'INSERT INTO fp.emp (name) VALUES ($$x$$)',
    'SELECT pg_read_file($$/etc/passwd$$)',
    'SELECT 1; SELECT 2',
    'DO $$ BEGIN PERFORM 1; END $$',
    'SET row_security = off',
]


def _connection_double(readonly=True):
    """A connection that records what run_query hands it."""
    connection = AsyncMock()
    connection.readonly_query = readonly
    connection.execute_query.return_value = {'columnMetadata': [], 'records': []}
    return connection


@pytest.mark.asyncio
@pytest.mark.parametrize('sql', GUARD_APPROVED_READS)
async def test_approved_read_reaches_the_connection_unchanged(sql):
    """run_query must not alter the statement it approved."""
    connection = _connection_double(readonly=True)
    with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
        mock_map.get.return_value = connection
        result = await run_query(
            sql=sql,
            ctx=DummyCtx(),
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='c',
            db_endpoint='e',
            database='d',
        )

    assert not (result and isinstance(result[0], dict) and 'error' in result[0]), result
    connection.execute_query.assert_awaited_once()
    forwarded_sql = connection.execute_query.await_args.args[0]
    assert forwarded_sql == sql


@pytest.mark.asyncio
@pytest.mark.parametrize('sql', GUARD_REJECTED_STATEMENTS)
async def test_rejected_statement_never_reaches_the_connection(sql):
    """A rejection must stop before the database, not merely be reported."""
    connection = _connection_double(readonly=True)
    with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
        mock_map.get.return_value = connection
        result = await run_query(
            sql=sql,
            ctx=DummyCtx(),
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='c',
            db_endpoint='e',
            database='d',
        )

    connection.execute_query.assert_not_awaited()
    assert result and 'error' in result[0]


@pytest.mark.asyncio
async def test_write_mode_forwards_a_write_unchanged():
    """With writes enabled the same wiring must forward write statements too."""
    sql = 'INSERT INTO fp.emp (name) VALUES ($$x$$)'
    connection = _connection_double(readonly=False)
    with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
        mock_map.get.return_value = connection
        await run_query(
            sql=sql,
            ctx=DummyCtx(),
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='c',
            db_endpoint='e',
            database='d',
        )

    connection.execute_query.assert_awaited_once()
    assert connection.execute_query.await_args.args[0] == sql


@pytest.mark.asyncio
async def test_dangerous_statement_is_stopped_even_in_write_mode():
    """The dangerous set is mode-independent all the way to the connection."""
    connection = _connection_double(readonly=False)
    with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
        mock_map.get.return_value = connection
        result = await run_query(
            sql='SELECT pg_read_file($$/etc/passwd$$)',
            ctx=DummyCtx(),
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='c',
            db_endpoint='e',
            database='d',
        )

    connection.execute_query.assert_not_awaited()
    assert result and 'error' in result[0]


# --- The psycopg executor: transaction mode and the placeholder rewrite -----


class _RecordingCursor:
    """Async cursor double that records every statement it is given."""

    def __init__(self, log):
        self._log = log
        self.description = None

    async def execute(self, sql, params=None):
        self._log.append((str(sql), params))

    async def fetchall(self):
        return []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _NoopTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _RecordingConnection:
    """Async connection double: records conn.execute() and cursor statements."""

    def __init__(self, log):
        self._log = log

    async def execute(self, sql, params=None):
        self._log.append((str(sql), params))

    def transaction(self):
        return _NoopTransaction()

    def cursor(self):
        return _RecordingCursor(self._log)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _psycopg_connection(readonly):
    """A real PsycopgPoolConnection with the pool replaced by a recorder."""
    connection = PsycopgPoolConnection(
        host='db.example.com',
        port=5432,
        database='test_db',
        readonly=readonly,
        secret_arn='arn:aws:secretsmanager:us-west-2:1:secret:x',  # pragma: allowlist secret
        db_user='u',
        region='us-west-2',
        is_iam_auth=False,
        is_test=True,
    )
    log: list[tuple[str, object]] = []
    connection._get_connection = AsyncMock(return_value=_RecordingConnection(log))
    return connection, log


@pytest.mark.asyncio
async def test_read_only_connection_opens_a_read_only_transaction_first():
    """The backstop the guard depends on must actually be issued, and issued first.

    The guard permits row-locking SELECTs precisely because this statement
    refuses them at the engine. If it stopped being sent, that reliance would
    become an exposure silently.
    """
    connection, log = _psycopg_connection(readonly=True)
    await connection.execute_query('SELECT 1')

    statements = [sql for sql, _ in log]
    assert statements[0] == 'SET TRANSACTION READ ONLY'
    assert statements[1] == 'SELECT 1'


@pytest.mark.asyncio
async def test_write_connection_does_not_force_read_only():
    """Write mode must not send the read-only transaction marker."""
    connection, log = _psycopg_connection(readonly=False)
    await connection.execute_query('INSERT INTO t VALUES (1)')

    statements = [sql for sql, _ in log]
    assert 'SET TRANSACTION READ ONLY' not in statements
    assert statements == ['INSERT INTO t VALUES (1)']


PARAMETERIZED_READS = [
    ('SELECT * FROM fp.emp WHERE id = :id', {'id': 1}),
    ('SELECT to_regclass(:table_name)', {'table_name': 'fp.emp'}),
    ('SELECT tags[1:2] FROM fp.dept WHERE id = :id', {'id': 1}),
    ('SELECT tags[1:limit_idx] FROM fp.dept WHERE id = :id', {'id': 1}),
    ("SELECT 'a:b' AS lit FROM fp.emp WHERE id = :id", {'id': 1}),
    ('SELECT * FROM fp.emp WHERE dept_id IN (:a, :b)', {'a': 1, 'b': 2}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'sql,params', PARAMETERIZED_READS, ids=[s for s, _ in PARAMETERIZED_READS]
)
async def test_statement_sent_to_the_driver_still_parses(sql, params):
    """The executor's rewrite must not corrupt a statement the guard approved.

    This is the regression seam for the array-slice defect: the guard accepted
    ``tags[1:limit_idx]`` while the executor turned it into
    ``tags[1%(limit_idx)s]``, which no server can parse. Assert on what the
    driver is actually handed rather than on the rewrite helper in isolation.
    """
    connection, log = _psycopg_connection(readonly=True)
    parameters = [{'name': k, 'value': {'stringValue': str(v)}} for k, v in params.items()]
    await connection.execute_query(sql, parameters)

    sent = [s for s, _ in log if s != 'SET TRANSACTION READ ONLY']
    assert len(sent) == 1
    # psycopg binds %(name)s server-side; reduce to the positional form it sends.
    parse_sql(re.sub(r'%\(\w+\)s', '$1', sent[0]))


@pytest.mark.asyncio
async def test_unparameterized_statement_is_not_rewritten_at_all():
    """Without parameters the original text must reach the driver untouched."""
    sql = "SELECT 'ping :host' AS note FROM fp.emp"
    connection, log = _psycopg_connection(readonly=True)
    await connection.execute_query(sql)

    sent = [s for s, _ in log if s != 'SET TRANSACTION READ ONLY']
    assert sent == [sql]


# --- The whole policy matrix, driven through run_query with a mock -----------
# tests/e2e/e2e_integration_test.py --full-policy-corpus drives these same eight
# cells through run_query against real Aurora. That run needs AWS credentials and
# minutes of round trips, so the same expectations are checked here against a mock
# connection: if a cell is going to disagree, it should be visible in the ordinary
# suite rather than only after a cluster spins up.
#
# The whole sweep costs about 0.3s, so each cell is one test that loops and
# reports every offending statement instead of 1030 parametrized cases.


def _rejected(rows):
    return bool(rows) and isinstance(rows[0], dict) and 'error' in rows[0]


async def _verdicts(corpus, readonly):
    """Return [(sql, error_or_None)] for a corpus driven through run_query."""
    connection = _connection_double(readonly=readonly)
    out = []
    with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
        mock_map.get.return_value = connection
        for sql in corpus:
            rows = await run_query(
                sql=sql,
                ctx=DummyCtx(),
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='c',
                db_endpoint='e',
                database='d',
            )
            out.append((sql, str(rows[0]['error']) if _rejected(rows) else None))
    return out


@pytest.mark.asyncio
@pytest.mark.parametrize('readonly', [True, False], ids=['read-only', 'write'])
async def test_matrix_set1_reads_permitted_through_run_query(readonly):
    """Cells (1, read-only) and (1, write): reads reach the connection in both modes."""
    offenders = [(sql, err) for sql, err in await _verdicts(SET_1_READS, readonly) if err]
    assert not offenders, f'reads rejected by the tool ({len(offenders)}): {offenders[:5]}'


@pytest.mark.asyncio
async def test_matrix_set2_writes_rejected_in_read_only_mode_through_run_query():
    """Cell (2, read-only): every write is refused before the connection is used."""
    permitted = [sql for sql, err in await _verdicts(SET_2_WRITES, True) if not err]
    assert not permitted, f'writes permitted read-only ({len(permitted)}): {permitted[:5]}'


@pytest.mark.asyncio
async def test_matrix_set2_writes_permitted_in_write_mode_through_run_query():
    """Cell (2, write): the same writes reach the connection once writes are enabled."""
    offenders = [(sql, err) for sql, err in await _verdicts(SET_2_WRITES, False) if err]
    assert not offenders, f'writes rejected in write mode ({len(offenders)}): {offenders[:5]}'


@pytest.mark.asyncio
@pytest.mark.parametrize('readonly', [True, False], ids=['read-only', 'write'])
async def test_matrix_set3_dangerous_rejected_through_run_query(readonly):
    """Cells (3, read-only) and (3, write): dangerous constructs never reach the DB."""
    permitted = [sql for sql, err in await _verdicts(SET_3_DANGEROUS, readonly) if not err]
    assert not permitted, f'dangerous statements permitted ({len(permitted)}): {permitted[:5]}'


@pytest.mark.asyncio
@pytest.mark.parametrize('readonly', [True, False], ids=['read-only', 'write'])
async def test_matrix_set4_fail_closed_rejected_through_run_query(readonly):
    """Cells (4, read-only) and (4, write): unclassifiable input is refused in both."""
    permitted = [sql for sql, err in await _verdicts(SET_4_FAIL_CLOSED, readonly) if not err]
    assert not permitted, f'unclassifiable input permitted ({len(permitted)}): {permitted[:5]}'


@pytest.mark.asyncio
async def test_no_matrix_statement_reaches_the_database_when_rejected():
    """A rejection anywhere in the matrix must stop before execute_query.

    Rejecting in the response while still executing the statement would be the
    worst possible failure mode, and it would not be visible from the verdicts
    alone -- both look like an error to the caller.
    """
    for corpus, readonly in (
        (SET_2_WRITES, True),
        (SET_3_DANGEROUS, True),
        (SET_3_DANGEROUS, False),
        (SET_4_FAIL_CLOSED, True),
        (SET_4_FAIL_CLOSED, False),
    ):
        connection = _connection_double(readonly=readonly)
        with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
            mock_map.get.return_value = connection
            for sql in corpus:
                await run_query(
                    sql=sql,
                    ctx=DummyCtx(),
                    connection_method=ConnectionMethod.RDS_API,
                    cluster_identifier='c',
                    db_endpoint='e',
                    database='d',
                )
        connection.execute_query.assert_not_awaited()
