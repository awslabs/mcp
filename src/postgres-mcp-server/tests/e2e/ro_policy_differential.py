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

"""Differential: the read-only SQL policy guard vs PostgreSQL's own read-only transaction.

Why this exists
---------------
"Is this statement a read?" is a judgement call, and a unit test only records the
judgement of whoever wrote it. This harness asks PostgreSQL instead: it runs each
candidate inside ``BEGIN; SET TRANSACTION READ ONLY`` against a live server and
compares the outcome with ``assert_executable(sql, allow_write_query=False)``.

Two kinds of divergence come out, and neither is automatically a defect:

* **false-positive candidate** -- PostgreSQL executed it, the guard rejected it.
  Either the guard is over-blocking, or it is intentionally stricter for a reason
  that has to be written down.
* **backstop-reliant** -- the guard allowed it and PostgreSQL's read-only
  transaction refused it. Not an exposure (the server always wraps read-only
  queries in that transaction) but it marks where the guard defers to the engine
  instead of deciding for itself.

Every divergence must appear in ``EXPECTED_DIVERGENCES`` with a justification.
Anything unlabeled fails the run, which turns this from a one-off report into a
regression detector: a future denylist edit that starts blocking legitimate reads
shows up here.

Requirements
------------
Any PostgreSQL 13+ server you can connect to, and a role allowed to create a
schema in it. No AWS resources and no Aurora specifics -- unlike the other
scripts in this directory, this one only needs a plain database.

Usage
-----
    python tests/e2e/ro_policy_differential.py \
        --dsn "host=/tmp port=5432 dbname=postgres"

    # keep the probe schema for inspection
    python tests/e2e/ro_policy_differential.py --dsn "..." --keep-schema

Exit status is 0 when every divergence is accounted for, 1 otherwise.
"""

import argparse
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import psycopg  # noqa: E402
from awslabs.postgres_mcp_server.sql_guard import SqlPolicyError, assert_executable  # noqa: E402


SCHEMA = 'mcp_ro_diff'

SETUP_SQL = f"""
DROP SCHEMA IF EXISTS {SCHEMA} CASCADE;
CREATE SCHEMA {SCHEMA};
CREATE TYPE {SCHEMA}.mood AS ENUM ('sad','ok','happy');
CREATE TABLE {SCHEMA}.dept (
    id serial PRIMARY KEY, name text NOT NULL UNIQUE, meta jsonb, tags text[]);
CREATE TABLE {SCHEMA}.emp (
    id serial PRIMARY KEY,
    dept_id int REFERENCES {SCHEMA}.dept(id),
    name text NOT NULL,
    salary numeric(12,2) CHECK (salary >= 0),
    hired date DEFAULT current_date,
    m {SCHEMA}.mood,
    doc xml,
    body tsvector);
CREATE INDEX emp_name_idx ON {SCHEMA}.emp (name);
CREATE INDEX emp_lower_idx ON {SCHEMA}.emp (lower(name));
CREATE VIEW {SCHEMA}.v_emp AS SELECT id, name, salary FROM {SCHEMA}.emp;
CREATE MATERIALIZED VIEW {SCHEMA}.mv_emp AS
    SELECT dept_id, count(*) c FROM {SCHEMA}.emp GROUP BY dept_id;
CREATE TABLE {SCHEMA}.part (id int, d date) PARTITION BY RANGE (d);
CREATE TABLE {SCHEMA}.part_2026 PARTITION OF {SCHEMA}.part
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE FUNCTION {SCHEMA}.raise_pct(n numeric, p numeric) RETURNS numeric
    LANGUAGE sql IMMUTABLE AS 'SELECT n * (1+p/100)';
COMMENT ON TABLE {SCHEMA}.emp IS 'employees';
COMMENT ON COLUMN {SCHEMA}.emp.salary IS 'annual';
INSERT INTO {SCHEMA}.dept(name, meta, tags)
    VALUES ('eng','{{"a":1}}','{{x,y,z}}'), ('ops','{{"b":2}}','{{p,q}}');
INSERT INTO {SCHEMA}.emp(dept_id,name,salary,m)
    VALUES (1,'ada',100.00,'happy'),(1,'bob',90.50,'ok'),(2,'cy',80.25,'sad');
ANALYZE {SCHEMA}.emp;
"""

# Divergences that are understood and accepted. Keyed by probe name; the value is
# the reason the guard's verdict differs from PostgreSQL's. Grouped by the shared
# rationale rather than listed flat, because most of them share one.
#
# The dominant reason is structural: the MCP server accepts exactly one statement
# per request and wraps each one in its own transaction on a pooled connection.
# Anything whose value depends on a second statement, on session continuity, or on
# an open transaction cannot work through this interface even if it were allowed --
# so rejecting it costs nothing and keeps the read-only contract simple.
EXPECTED_DIVERGENCES = {
    # -- no session or transaction continuity across requests --------------
    'declare cursor': 'a cursor cannot be FETCHed by a later request on a pooled connection',
    'prepare': 'a prepared plan cannot be EXECUTEd by a later request on a pooled connection',
    'deallocate all': 'session-scoped plan cleanup; nothing reachable to clean up',
    'listen': 'notifications would be delivered to a connection nobody is reading',
    'unlisten': 'counterpart to LISTEN, which is itself rejected',
    'set local': 'transaction-scoped and the transaction ends with this one statement',
    'reset named': 'session state would leak into later requests sharing the backend',
    'discard plans': 'session state reset; DISCARD ALL is dangerous in both modes',
    'savepoint': 'the server owns the transaction wrapping each request',
    'begin': 'the server owns the transaction wrapping each request',
    'commit': 'the server owns the transaction wrapping each request',
    'set role': 'role changes would leak into later requests sharing the backend',
    # -- availability ------------------------------------------------------
    'lock table access share': 'all explicit LOCK is rejected; SELECT already takes ACCESS SHARE',
    'lock table exclusive': 'an explicit exclusive lock blocks other workloads',
    'advisory lock': 'advisory locks are an application-level DoS primitive',
    'pg_sleep short': 'holds a pooled connection open; the family is blocked in both modes',
    'pg_notify': 'delivers a message to other sessions -- a side channel',
    # -- reads by PostgreSQL's definition, writes by the guard's -----------
    # This group is the reason the mutating-function inventory exists: a
    # read-only transaction only blocks table-data writes, so each of these
    # mutates durable or shared state and is still permitted by the engine.
    'stats reset': 'discards cumulative statistics; permitted read-only by the engine',
    'analyze': 'writes planner statistics; permitted read-only by the engine',
    'checkpoint': 'forces server-wide I/O; permitted read-only by the engine',
    'setseed': 'mutates the session random sequence',
    'pg_switch_wal': 'forces a WAL segment switch',
    'pg_logical_emit_message': 'writes a WAL record',
    'advisory unlock all': 'mutates shared advisory lock state',
    'gin clean pending': 'writes GIN index pages',
    # -- deliberate strictness beyond the engine ---------------------------
    'copy to stdout': 'all COPY is rejected in read-only mode; SELECT covers the same need',
    'copy query to stdout': 'all COPY is rejected in read-only mode; SELECT covers the same need',
    'select into': 'creates a table -- a write wearing a SelectStmt',
    'refresh matview': 'rewrites materialized view contents',
    'nextval': 'advances a sequence',
    # -- backstop-reliant --------------------------------------------------
    'for update': 'row locks; refused by SET TRANSACTION READ ONLY, not duplicated in the parser',
    'for no key update': 'row locks; refused by SET TRANSACTION READ ONLY',
    'for share': 'row locks; refused by SET TRANSACTION READ ONLY',
    'for key share skip locked': 'row locks; refused by SET TRANSACTION READ ONLY',
}


def build_corpus(schema):
    """Return [(group, name, sql)] with schema-qualified object names."""
    s = schema
    grammar = [
        ('basic projection', f'SELECT id, name FROM {s}.emp'),
        ('star', f'SELECT * FROM {s}.emp'),
        ('inner join', f'SELECT e.name FROM {s}.emp e JOIN {s}.dept d ON e.dept_id = d.id'),
        ('left join', f'SELECT e.name FROM {s}.emp e LEFT JOIN {s}.dept d ON e.dept_id = d.id'),
        ('right join', f'SELECT d.name FROM {s}.emp e RIGHT JOIN {s}.dept d ON e.dept_id = d.id'),
        ('full join', f'SELECT 1 FROM {s}.emp e FULL JOIN {s}.dept d ON e.dept_id = d.id'),
        ('cross join', f'SELECT 1 FROM {s}.emp CROSS JOIN {s}.dept'),
        ('natural join', f'SELECT 1 FROM {s}.emp NATURAL JOIN {s}.dept'),
        ('join using', f'SELECT 1 FROM {s}.emp e JOIN {s}.dept d USING (id)'),
        ('union', f'SELECT name FROM {s}.emp UNION SELECT name FROM {s}.dept'),
        ('intersect', f'SELECT name FROM {s}.emp INTERSECT SELECT name FROM {s}.dept'),
        ('except', f'SELECT name FROM {s}.emp EXCEPT SELECT name FROM {s}.dept'),
        ('parenthesized set ops', '(SELECT 1) UNION (SELECT 2) ORDER BY 1'),
        ('cte', f'WITH x AS (SELECT * FROM {s}.emp) SELECT count(*) FROM x'),
        ('cte materialized', 'WITH x AS MATERIALIZED (SELECT 1 a) SELECT * FROM x'),
        ('cte not materialized', 'WITH x AS NOT MATERIALIZED (SELECT 1 a) SELECT * FROM x'),
        (
            'recursive cte',
            'WITH RECURSIVE t(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM t WHERE n < 5) SELECT sum(n) FROM t',
        ),
        (
            'recursive cte cycle',
            'WITH RECURSIVE t(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM t WHERE n<3) '
            'CYCLE n SET c USING p SELECT n FROM t',
        ),
        ('window fn', f'SELECT rank() OVER (ORDER BY salary DESC) FROM {s}.emp'),
        (
            'named window',
            f'SELECT sum(salary) OVER w FROM {s}.emp WINDOW w AS (PARTITION BY dept_id)',
        ),
        (
            'frame rows',
            f'SELECT sum(salary) OVER (ORDER BY id ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) FROM {s}.emp',
        ),
        (
            'frame groups exclude',
            f'SELECT count(*) OVER (ORDER BY dept_id GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW '
            f'EXCLUDE TIES) FROM {s}.emp',
        ),
        ('grouping sets', f'SELECT count(*) FROM {s}.emp GROUP BY GROUPING SETS ((dept_id),(m))'),
        ('cube', f'SELECT count(*) FROM {s}.emp GROUP BY CUBE (dept_id, m)'),
        ('rollup', f'SELECT count(*) FROM {s}.emp GROUP BY ROLLUP (dept_id, m)'),
        ('group by distinct', f'SELECT dept_id FROM {s}.emp GROUP BY DISTINCT ROLLUP (dept_id)'),
        ('grouping()', f'SELECT grouping(dept_id) FROM {s}.emp GROUP BY ROLLUP (dept_id)'),
        ('having', f'SELECT dept_id FROM {s}.emp GROUP BY dept_id HAVING count(*) > 1'),
        ('agg filter', f'SELECT count(*) FILTER (WHERE salary > 90) FROM {s}.emp'),
        ('agg order by', f'SELECT string_agg(name, $$,$$ ORDER BY name) FROM {s}.emp'),
        ('count distinct', f'SELECT count(DISTINCT name) FROM {s}.emp'),
        (
            'within group',
            f'SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY salary) FROM {s}.emp',
        ),
        ('json agg', f'SELECT json_object_agg(name, salary) FROM {s}.emp'),
        ('distinct', f'SELECT DISTINCT dept_id FROM {s}.emp'),
        ('distinct on', f'SELECT DISTINCT ON (dept_id) dept_id FROM {s}.emp ORDER BY dept_id'),
        (
            'order by collate',
            f'SELECT name FROM {s}.emp ORDER BY name COLLATE "C" DESC NULLS LAST',
        ),
        ('order by ordinal', f'SELECT name FROM {s}.emp ORDER BY 1'),
        ('limit offset', f'SELECT * FROM {s}.emp ORDER BY id LIMIT 2 OFFSET 1'),
        (
            'fetch first with ties',
            f'SELECT * FROM {s}.emp ORDER BY salary FETCH FIRST 2 ROWS WITH TIES',
        ),
        ('lateral', f'SELECT x.c FROM {s}.emp e, LATERAL (SELECT count(*) c FROM {s}.dept) x'),
        ('lateral join', f'SELECT 1 FROM {s}.dept d JOIN LATERAL (SELECT 1) y ON true'),
        ('subquery in from', f'SELECT * FROM (SELECT * FROM {s}.emp) q'),
        ('subquery in select', f'SELECT (SELECT count(*) FROM {s}.dept) FROM {s}.emp'),
        ('subquery in where', f'SELECT * FROM {s}.emp WHERE dept_id IN (SELECT id FROM {s}.dept)'),
        (
            'correlated exists',
            f'SELECT * FROM {s}.emp e WHERE EXISTS (SELECT 1 FROM {s}.dept d WHERE d.id = e.dept_id)',
        ),
        ('any all', f'SELECT * FROM {s}.emp WHERE salary > ALL (SELECT 1)'),
        (
            'scalar subquery arithmetic',
            f'SELECT (SELECT max(salary) FROM {s}.emp) - (SELECT min(salary) FROM {s}.emp)',
        ),
        ('tablesample bernoulli', f'SELECT * FROM {s}.emp TABLESAMPLE BERNOULLI (50)'),
        (
            'tablesample system repeatable',
            f'SELECT * FROM {s}.emp TABLESAMPLE SYSTEM (50) REPEATABLE (7)',
        ),
        ('values', 'VALUES (1, $$a$$), (2, $$b$$)'),
        ('table cmd', f'TABLE {s}.emp'),
        ('row constructor', 'SELECT ROW(1, $$a$$)'),
        ('array constructor', 'SELECT ARRAY[1,2,3]'),
        ('array subscript', f'SELECT tags[1] FROM {s}.dept'),
        ('array slice', f'SELECT tags[1:2] FROM {s}.dept'),
        ('array slice open', f'SELECT tags[:2] FROM {s}.dept'),
        ('unnest with ordinality', 'SELECT * FROM unnest(ARRAY[1,2]) WITH ORDINALITY'),
        ('srf in select list', 'SELECT generate_series(1,3)'),
        ('srf in from', 'SELECT * FROM generate_series(1,3) g(n)'),
        ('rows from', 'SELECT * FROM ROWS FROM (generate_series(1,2), generate_series(1,3))'),
        ('srf column defs', 'SELECT * FROM json_to_recordset($$[{"a":1}]$$) AS x(a int)'),
        ('cast forms', f'SELECT CAST(salary AS int), salary::int FROM {s}.emp'),
        ('case', f'SELECT CASE WHEN salary > 90 THEN $$hi$$ ELSE $$lo$$ END FROM {s}.emp'),
        (
            'coalesce nullif greatest',
            f'SELECT coalesce(dept_id,0), nullif(id,0), greatest(1,2) FROM {s}.emp',
        ),
        ('jsonb ops', f"SELECT meta->>'a', meta #> '{{a}}' FROM {s}.dept"),
        ('jsonb path', f"SELECT jsonb_path_query_first(meta, '$.a') FROM {s}.dept"),
        ('json build', f'SELECT json_build_object($$k$$, name) FROM {s}.emp'),
        ('multirange contains', 'SELECT int4multirange(int4range(1,3)) @> 2'),
        ('full text search', f"SELECT * FROM {s}.emp WHERE body @@ to_tsquery('english','x')"),
        ('regex ops', f"SELECT name FROM {s}.emp WHERE name ~ '^a'"),
        ('like escape', f"SELECT * FROM {s}.emp WHERE name LIKE 'a!%' ESCAPE '!'"),
        ('ilike similar', f"SELECT * FROM {s}.emp WHERE name ILIKE 'A%' OR name SIMILAR TO 'a%'"),
        ('is distinct from', f'SELECT * FROM {s}.emp WHERE dept_id IS DISTINCT FROM 1'),
        ('between symmetric', f'SELECT * FROM {s}.emp WHERE salary BETWEEN SYMMETRIC 100 AND 1'),
        ('enum compare', f"SELECT * FROM {s}.emp WHERE m = 'happy'"),
        ('sql value functions', 'SELECT current_date, current_timestamp, localtime, current_role'),
        ('extract', f'SELECT extract(year FROM hired) FROM {s}.emp'),
        ('substring from for', f'SELECT substring(name FROM 1 FOR 2) FROM {s}.emp'),
        ('trim both', f'SELECT trim(BOTH $$a$$ FROM name) FROM {s}.emp'),
        ('overlay placing', f'SELECT overlay(name PLACING $$x$$ FROM 1) FROM {s}.emp'),
        ('position in', f'SELECT position($$a$$ IN name) FROM {s}.emp'),
        ('at time zone', f"SELECT hired::timestamp AT TIME ZONE 'UTC' FROM {s}.emp"),
        ('partitioned read', f'SELECT * FROM {s}.part'),
        ('view read', f'SELECT * FROM {s}.v_emp'),
        ('matview read', f'SELECT * FROM {s}.mv_emp'),
        ('user function', f'SELECT {s}.raise_pct(salary, 10) FROM {s}.emp'),
        ('expression index predicate', f'SELECT * FROM {s}.emp WHERE lower(name) = $$ada$$'),
        ('explain', f'EXPLAIN SELECT * FROM {s}.emp'),
        ('explain analyze', f'EXPLAIN ANALYZE SELECT * FROM {s}.emp'),
        ('explain format json', 'EXPLAIN (FORMAT JSON) SELECT 1'),
        ('explain verbose costs off', 'EXPLAIN (VERBOSE, COSTS OFF) SELECT 1'),
        ('comment styles', 'SELECT 1 -- trailing\n/* block */'),
        ('dollar quoted literal', "SELECT $tag$has '' quote$tag$"),
        ('e string', "SELECT E'\\n'"),
        ('unicode identifier', 'SELECT 1 AS U&"caf\\00e9"'),
        ('for update', f'SELECT * FROM {s}.emp FOR UPDATE'),
        ('for no key update', f'SELECT * FROM {s}.emp FOR NO KEY UPDATE'),
        ('for share', f'SELECT * FROM {s}.emp FOR SHARE'),
        ('for key share skip locked', f'SELECT * FROM {s}.emp FOR KEY SHARE SKIP LOCKED'),
    ]

    tooling = [
        (
            'information_schema.columns',
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'emp'",
        ),
        (
            'information_schema.tables',
            f"SELECT table_name FROM information_schema.tables WHERE table_schema='{s}'",
        ),
        (
            'information_schema constraints',
            'SELECT c.constraint_name, k.column_name FROM information_schema.table_constraints c '
            'JOIN information_schema.key_column_usage k USING (constraint_name)',
        ),
        (
            'information_schema referential',
            'SELECT * FROM information_schema.referential_constraints',
        ),
        (
            'information_schema.views',
            'SELECT table_name, view_definition FROM information_schema.views',
        ),
        (
            'information_schema.routines',
            f"SELECT routine_name FROM information_schema.routines WHERE specific_schema='{s}'",
        ),
        (
            'psql backslash-d columns',
            'SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod), '
            'pg_catalog.pg_get_expr(d.adbin, d.adrelid), a.attnotnull '
            'FROM pg_catalog.pg_attribute a LEFT JOIN pg_catalog.pg_attrdef d '
            'ON a.attrelid = d.adrelid AND a.attnum = d.adnum '
            f"WHERE a.attrelid = '{s}.emp'::regclass AND a.attnum > 0 AND NOT a.attisdropped "
            'ORDER BY a.attnum',
        ),
        (
            'pg_class + namespace',
            'SELECT c.relname, n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace '
            f"WHERE n.nspname = '{s}'",
        ),
        (
            'index defs',
            'SELECT indexname, pg_get_indexdef(i.indexrelid) FROM pg_indexes JOIN pg_index i ON true '
            f"WHERE schemaname='{s}' LIMIT 5",
        ),
        (
            'constraint defs',
            f"SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = '{s}.emp'::regclass",
        ),
        ('view def', f"SELECT pg_get_viewdef('{s}.v_emp'::regclass, true)"),
        ('function def', f"SELECT pg_get_functiondef('{s}.raise_pct'::regproc)"),
        ('serial sequence', f"SELECT pg_get_serial_sequence('{s}.emp','id')"),
        (
            'comments',
            f"SELECT obj_description('{s}.emp'::regclass), col_description('{s}.emp'::regclass, 4)",
        ),
        ('to_regclass', f"SELECT to_regclass('{s}.emp')"),
        ('partition key def', f"SELECT pg_get_partkeydef('{s}.part'::regclass)"),
        (
            'enum values',
            "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid WHERE t.typname='mood'",
        ),
        ('relation size', f"SELECT pg_size_pretty(pg_total_relation_size('{s}.emp'))"),
        ('database size', 'SELECT pg_database_size(current_database())'),
        ('table stats', 'SELECT relname, n_live_tup FROM pg_stat_user_tables'),
        ('column stats', "SELECT attname, n_distinct FROM pg_stats WHERE tablename = 'emp'"),
        (
            'session activity',
            'SELECT pid, state, query FROM pg_stat_activity WHERE pid <> pg_backend_pid()',
        ),
        ('locks', 'SELECT locktype, mode FROM pg_locks LIMIT 5'),
        ('settings', "SELECT name, setting FROM pg_settings WHERE name = 'work_mem'"),
        ('current_setting', "SELECT current_setting('work_mem')"),
        ('roles', 'SELECT rolname, rolsuper FROM pg_roles LIMIT 5'),
        (
            'privilege probe',
            'SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user',
        ),
        ('has_table_privilege', f"SELECT has_table_privilege('{s}.emp','SELECT')"),
        ('databases', 'SELECT datname FROM pg_database'),
        ('session identity', 'SELECT version(), current_database(), current_user, session_user'),
        (
            'explain for tuning',
            f'EXPLAIN (ANALYZE, BUFFERS, VERBOSE) SELECT count(*) FROM {s}.emp',
        ),
        ('show setting', 'SHOW search_path'),
        ('show all', 'SHOW ALL'),
    ]

    statements = [
        ('declare cursor', 'DECLARE c CURSOR FOR SELECT 1'),
        ('copy to stdout', f'COPY {s}.emp TO STDOUT'),
        ('copy query to stdout', 'COPY (SELECT 1) TO STDOUT'),
        ('prepare', 'PREPARE st AS SELECT 1'),
        ('deallocate all', 'DEALLOCATE ALL'),
        ('listen', 'LISTEN chan'),
        ('unlisten', 'UNLISTEN chan'),
        ('set local', 'SET LOCAL work_mem = $$8MB$$'),
        ('reset named', 'RESET work_mem'),
        ('discard plans', 'DISCARD PLANS'),
        ('lock table access share', f'LOCK TABLE {s}.emp IN ACCESS SHARE MODE'),
        ('lock table exclusive', f'LOCK TABLE {s}.emp'),
        ('savepoint', 'SAVEPOINT sp1'),
        ('begin', 'BEGIN'),
        ('commit', 'COMMIT'),
        ('checkpoint', 'CHECKPOINT'),
        ('analyze', f'ANALYZE {s}.emp'),
        ('select into', f'SELECT * INTO {s}.copy_of_emp FROM {s}.emp'),
        ('refresh matview', f'REFRESH MATERIALIZED VIEW {s}.mv_emp'),
        ('set role', 'SET ROLE NONE'),
        ('stats reset', 'SELECT pg_stat_reset()'),
        ('nextval', f"SELECT nextval('{s}.emp_id_seq')"),
        ('setseed', 'SELECT setseed(0.5)'),
        ('advisory lock', 'SELECT pg_advisory_lock(42)'),
        ('advisory unlock all', 'SELECT pg_advisory_unlock_all()'),
        ('pg_switch_wal', 'SELECT pg_switch_wal()'),
        ('pg_logical_emit_message', "SELECT pg_logical_emit_message(false,'a','b')"),
        ('pg_notify', "SELECT pg_notify('chan','msg')"),
        ('pg_sleep short', 'SELECT pg_sleep(0.01)'),
    ]

    return (
        [('SELECT grammar', n, q) for n, q in grammar]
        + [('real-world tooling', n, q) for n, q in tooling]
        + [('statement types', n, q) for n, q in statements]
    )


def guard_verdict(sql):
    """Return ('ALLOW'|'REJECT', reason)."""
    try:
        assert_executable(sql, allow_write_query=False)
        return 'ALLOW', ''
    except SqlPolicyError as e:
        return 'REJECT', str(e)


def pg_verdict(dsn, sql):
    """Run sql in BEGIN; SET TRANSACTION READ ONLY on a throwaway connection.

    One connection per probe: COPY ... TO STDOUT leaves the session mid-protocol,
    which would poison every later probe on a shared connection.
    """
    is_copy_out = sql.lstrip().upper().startswith('COPY') and 'STDOUT' in sql.upper()
    try:
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute('BEGIN')
                cur.execute('SET TRANSACTION READ ONLY')
                if is_copy_out:
                    # psycopg refuses COPY through execute(); it needs the copy()
                    # API. Without this branch the probe reports a client-side
                    # error and PostgreSQL's actual read-only verdict is unknown.
                    with cur.copy(sql) as copy:
                        for _ in copy:
                            pass
                else:
                    cur.execute(sql)
        return 'OK', ''
    except psycopg.Error as e:
        msg = str(e).strip().split('\n')[0]
        low = msg.lower()
        if 'read-only transaction' in low:
            return 'RO_BLOCKED', msg
        if 'permission denied' in low or 'must be superuser' in low:
            return 'PRIV', msg
        return 'ERR', msg


def main():
    """Run the corpus through both verdicts and report; return a process exit code."""
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument(
        '--dsn', required=True, help='libpq connection string for a live PostgreSQL'
    )
    parser.add_argument(
        '--keep-schema', action='store_true', help=f'leave the {SCHEMA} schema in place'
    )
    args = parser.parse_args()

    dsn = args.dsn
    if 'statement_timeout' not in dsn:
        dsn = f'{dsn} options=-cstatement_timeout=5000'

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(SETUP_SQL)
        row = conn.execute('SHOW server_version').fetchone()
        server_version = row[0] if row else 'unknown'

    corpus = build_corpus(SCHEMA)
    false_positives, backstop, inconclusive = [], [], []
    per_group = {}

    for group, name, sql in corpus:
        g, greason = guard_verdict(sql)
        p, pmsg = pg_verdict(dsn, sql)
        agree, total = per_group.get(group, (0, 0))
        if p == 'OK' and g == 'REJECT':
            false_positives.append((group, name, sql, greason))
        elif p == 'RO_BLOCKED' and g == 'ALLOW':
            backstop.append((group, name, sql, pmsg))
        elif p in ('ERR', 'PRIV'):
            inconclusive.append((group, name, sql, g, p, pmsg))
        else:
            agree += 1
        per_group[group] = (agree, total + 1)

    print(f'\nguard read-only verdict vs PostgreSQL {server_version} read-only transaction')
    print('=' * 92)
    for group, (agree, total) in per_group.items():
        print(f'  {group:24} {agree:3}/{total:3} agree')

    unlabeled = []
    print(f'\nFALSE-POSITIVE CANDIDATES (PG executed; guard rejected) -- {len(false_positives)}')
    print('=' * 92)
    for group, name, sql, reason in false_positives:
        label = EXPECTED_DIVERGENCES.get(name)
        mark = 'expected' if label else '*** UNLABELED ***'
        if not label:
            unlabeled.append(name)
        print(f'  [{mark}] {name}\n      sql   : {sql[:96]}\n      guard : {reason}')
        if label:
            print(f'      why   : {label}')

    print(f'\nBACKSTOP-RELIANT (guard allowed; PG read-only txn refused) -- {len(backstop)}')
    print('=' * 92)
    for group, name, sql, msg in backstop:
        label = EXPECTED_DIVERGENCES.get(name)
        mark = 'expected' if label else '*** UNLABELED ***'
        if not label:
            unlabeled.append(name)
        print(f'  [{mark}] {name}\n      sql : {sql[:96]}\n      pg  : {msg[:96]}')
        if label:
            print(f'      why : {label}')

    if inconclusive:
        print(f'\nINCONCLUSIVE (PG error unrelated to read-only) -- {len(inconclusive)}')
        print('=' * 92)
        print('  Usually a corpus bug or a server built without an optional feature.')
        for group, name, sql, g, p, msg in inconclusive:
            print(f'  [{p}] {name}: guard={g}\n      sql: {sql[:92]}\n      pg : {msg[:92]}')

    if not args.keep_schema:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS {SCHEMA} CASCADE')

    if unlabeled:
        print(f'\nFAIL: {len(unlabeled)} unlabeled divergence(s): {sorted(set(unlabeled))}')
        print('Add a justification to EXPECTED_DIVERGENCES, or fix the guard.')
        return 1
    print(f'\nOK: every divergence is accounted for ({len(EXPECTED_DIVERGENCES)} labeled).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
