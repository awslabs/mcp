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

"""False-positive coverage for read-only mode: what must NOT be blocked.

The rejection direction is covered in ``test_sql_guard.py``. This module covers
the opposite and less-tested direction -- legitimate reads that must pass -- and
does it against a bounded surface rather than an open-ended list of queries,
because the set of valid read queries is infinite while the guard's decision
surface is not. Read-only mode is decided by exactly three inputs:

1. the statement node type (117 exist in the PG18 grammar; 3 plus the RawStmt
   wrapper are allowed), covered exhaustively by ``STMT_NODE_CLASSIFICATION``;
2. SELECT grammar features that must survive the tree walk, covered by
   ``READ_ONLY_ALLOWED_GRAMMAR``;
3. the 67 denylisted function names, whose complement -- the reads the design
   deliberately allows -- is covered by ``DELIBERATELY_ALLOWED_FUNCTION_READS``.

Provenance: every statement in the corpora below was run against a live
PostgreSQL 16.4 inside ``BEGIN; SET TRANSACTION READ ONLY`` and confirmed to
execute there, so "this is a read" is PostgreSQL's judgment rather than the test
author's. ``tests/e2e/ro_policy_differential.py`` reproduces that comparison on
demand and fails on any divergence it cannot justify; it carries the same
statements against its own probe schema, so the two differ only in schema name.
Parsing needs no database, so the tests here run as ordinary unit tests.
"""

import pytest
import re
from awslabs.postgres_mcp_server.named_params import (
    NAMED_PARAM_PATTERN,
    to_parse_placeholders,
    to_psycopg_placeholders,
)
from awslabs.postgres_mcp_server.sql_guard import (
    READ_ONLY_ALLOWED_STMT_NODES,
    SqlPolicyError,
    assert_executable,
)
from pglast import ast, parse_sql


# --- Axis 1: exhaustive statement-node classification ----------------------
# Every ``*Stmt`` node type in the grammar, classified. The categories carry
# review meaning, not just a boolean:
#
#   'read'       -- a pure read; MUST be in the guard's read-only allowlist.
#   'write'      -- mutates database or server state; correctly rejected.
#   'by-design'  -- semantically a read or state-neutral, but deliberately
#                   rejected. Each entry states why. PostgreSQL itself permits
#                   these inside a read-only transaction, so they are the
#                   guard's intentional extra strictness and the place to look
#                   first if a user reports over-blocking.
#   'nested'     -- cannot be submitted as a standalone statement; only ever
#                   appears inside another statement's tree (where the enclosing
#                   statement's own classification governs).
#
# A new PG version that adds a node type fails ``test_every_stmt_node_is_classified``
# until someone classifies it, which is what makes this bounded rather than
# best-effort.
STMT_NODE_CLASSIFICATION: dict[str, tuple[str, str]] = {
    # -- the reads --------------------------------------------------------
    'RawStmt': ('read', 'per-statement wrapper around the real node'),
    'SelectStmt': ('read', 'SELECT / VALUES / TABLE / WITH ... SELECT'),
    'VariableShowStmt': ('read', 'SHOW reads a GUC'),
    'ExplainStmt': ('read', 'EXPLAIN; an inner write is caught by the tree walk'),
    # -- deliberately rejected despite not being data writes --------------
    'DeclareCursorStmt': (
        'by-design',
        'cursors cannot span the stateless, pooled per-request connection',
    ),
    'FetchStmt': (
        'by-design',
        'FETCH/MOVE needs a cursor that cannot survive to the next request',
    ),
    'ClosePortalStmt': (
        'by-design',
        'CLOSE needs a cursor that cannot survive to the next request',
    ),
    'PrepareStmt': (
        'by-design',
        'prepared statements cannot be reached by a later pooled request',
    ),
    'ExecuteStmt': ('by-design', 'the named plan cannot be assumed to exist on this backend'),
    'DeallocateStmt': ('by-design', 'session-scoped plan cleanup with nothing to clean up'),
    'ListenStmt': ('by-design', 'asynchronous notification channel is a side channel'),
    'UnlistenStmt': ('by-design', 'counterpart to LISTEN, which is itself rejected'),
    'VariableSetStmt': ('by-design', 'SET/RESET leaks session state across pooled requests'),
    'DiscardStmt': ('by-design', 'bulk session reset; DISCARD ALL is dangerous in both modes'),
    'TransactionStmt': ('by-design', 'the server owns the transaction wrapping each request'),
    'ConstraintsSetStmt': (
        'by-design',
        'SET CONSTRAINTS alters constraint timing for the transaction',
    ),
    'LockStmt': ('by-design', 'explicit table locks are an availability risk'),
    'CopyStmt': ('by-design', 'all COPY is rejected; TO STDOUT is a read but SELECT covers it'),
    # -- statements that only ever appear nested ---------------------------
    'SetOperationStmt': (
        'nested',
        'analyzed-query node; raw set operations stay inside SelectStmt',
    ),
    'ReturnStmt': ('nested', 'RETURN inside a SQL-body function definition'),
    'PLAssignStmt': ('nested', 'PL/pgSQL assignment inside a routine body'),
    'ReplicaIdentityStmt': ('nested', 'subcommand of ALTER TABLE'),
    # -- data writes -------------------------------------------------------
    'InsertStmt': ('write', 'DML'),
    'UpdateStmt': ('write', 'DML'),
    'DeleteStmt': ('write', 'DML'),
    'MergeStmt': ('write', 'DML'),
    'TruncateStmt': ('write', 'removes all rows'),
    # -- procedural execution ---------------------------------------------
    'DoStmt': ('write', 'anonymous code block with an opaque body'),
    'CallStmt': ('write', 'procedure call with an opaque body'),
    # -- schema / object DDL ----------------------------------------------
    'CreateStmt': ('write', 'CREATE TABLE'),
    'CreateTableAsStmt': ('write', 'CREATE TABLE AS / CREATE MATERIALIZED VIEW'),
    'CreateSchemaStmt': ('write', 'CREATE SCHEMA'),
    'CreateSeqStmt': ('write', 'CREATE SEQUENCE'),
    'AlterSeqStmt': ('write', 'ALTER SEQUENCE'),
    'AlterTableStmt': ('write', 'ALTER TABLE'),
    'DropStmt': ('write', 'DROP of any object'),
    'RenameStmt': ('write', 'RENAME of any object'),
    'IndexStmt': ('write', 'CREATE INDEX'),
    'ViewStmt': ('write', 'CREATE VIEW'),
    'RuleStmt': ('write', 'CREATE RULE'),
    'CommentStmt': ('write', 'catalog comment write'),
    'SecLabelStmt': ('write', 'security label write'),
    'DefineStmt': ('write', 'CREATE AGGREGATE / OPERATOR / TYPE / TS objects'),
    'CompositeTypeStmt': ('write', 'CREATE TYPE AS'),
    'CreateEnumStmt': ('write', 'CREATE TYPE AS ENUM'),
    'CreateRangeStmt': ('write', 'CREATE TYPE AS RANGE'),
    'AlterEnumStmt': ('write', 'ALTER TYPE ... ADD VALUE'),
    'AlterTypeStmt': ('write', 'ALTER TYPE'),
    'CreateDomainStmt': ('write', 'CREATE DOMAIN'),
    'AlterDomainStmt': ('write', 'ALTER DOMAIN'),
    'CreateStatsStmt': ('write', 'CREATE STATISTICS'),
    'AlterStatsStmt': ('write', 'ALTER STATISTICS'),
    'CreateTrigStmt': ('write', 'CREATE TRIGGER'),
    'CreateEventTrigStmt': ('write', 'CREATE EVENT TRIGGER'),
    'AlterEventTrigStmt': ('write', 'ALTER EVENT TRIGGER'),
    'CreateFunctionStmt': ('write', 'CREATE FUNCTION / PROCEDURE'),
    'AlterFunctionStmt': ('write', 'ALTER FUNCTION'),
    'CreatePLangStmt': ('write', 'CREATE LANGUAGE'),
    'CreateCastStmt': ('write', 'CREATE CAST'),
    'CreateConversionStmt': ('write', 'CREATE CONVERSION'),
    'CreateTransformStmt': ('write', 'CREATE TRANSFORM'),
    'CreateAmStmt': ('write', 'CREATE ACCESS METHOD'),
    'CreateOpClassStmt': ('write', 'CREATE OPERATOR CLASS'),
    'CreateOpFamilyStmt': ('write', 'CREATE OPERATOR FAMILY'),
    'AlterOpFamilyStmt': ('write', 'ALTER OPERATOR FAMILY'),
    'AlterOperatorStmt': ('write', 'ALTER OPERATOR'),
    'AlterCollationStmt': ('write', 'ALTER COLLATION'),
    'AlterTSConfigurationStmt': ('write', 'ALTER TEXT SEARCH CONFIGURATION'),
    'AlterTSDictionaryStmt': ('write', 'ALTER TEXT SEARCH DICTIONARY'),
    'AlterObjectDependsStmt': ('write', 'ALTER ... DEPENDS ON EXTENSION'),
    'AlterObjectSchemaStmt': ('write', 'ALTER ... SET SCHEMA'),
    'AlterOwnerStmt': ('write', 'ALTER ... OWNER TO'),
    # -- extensions, FDW, foreign objects ---------------------------------
    'CreateExtensionStmt': ('write', 'CREATE EXTENSION'),
    'AlterExtensionStmt': ('write', 'ALTER EXTENSION'),
    'AlterExtensionContentsStmt': ('write', 'ALTER EXTENSION ... ADD/DROP'),
    'CreateFdwStmt': ('write', 'CREATE FOREIGN DATA WRAPPER'),
    'AlterFdwStmt': ('write', 'ALTER FOREIGN DATA WRAPPER'),
    'CreateForeignServerStmt': ('write', 'CREATE SERVER; can name an arbitrary host'),
    'AlterForeignServerStmt': ('write', 'ALTER SERVER; can repoint at another host'),
    'CreateForeignTableStmt': ('write', 'CREATE FOREIGN TABLE'),
    'CreateUserMappingStmt': ('write', 'CREATE USER MAPPING'),
    'AlterUserMappingStmt': ('write', 'ALTER USER MAPPING'),
    'DropUserMappingStmt': ('write', 'DROP USER MAPPING'),
    'ImportForeignSchemaStmt': (
        'write',
        'creates foreign tables and opens an outbound connection',
    ),
    # -- roles, privileges, policies --------------------------------------
    'CreateRoleStmt': ('write', 'CREATE ROLE'),
    'AlterRoleStmt': ('write', 'ALTER ROLE'),
    'AlterRoleSetStmt': ('write', 'ALTER ROLE ... SET'),
    'DropRoleStmt': ('write', 'DROP ROLE'),
    'GrantStmt': ('write', 'GRANT / REVOKE on objects'),
    'GrantRoleStmt': ('write', 'GRANT / REVOKE role membership'),
    'AlterDefaultPrivilegesStmt': ('write', 'ALTER DEFAULT PRIVILEGES'),
    'CreatePolicyStmt': ('write', 'CREATE POLICY'),
    'AlterPolicyStmt': ('write', 'ALTER POLICY'),
    'ReassignOwnedStmt': ('write', 'REASSIGN OWNED'),
    'DropOwnedStmt': ('write', 'DROP OWNED'),
    # -- databases, tablespaces, server-wide ------------------------------
    'CreatedbStmt': ('write', 'CREATE DATABASE'),
    'DropdbStmt': ('write', 'DROP DATABASE'),
    'AlterDatabaseStmt': ('write', 'ALTER DATABASE'),
    'AlterDatabaseSetStmt': ('write', 'ALTER DATABASE ... SET'),
    'AlterDatabaseRefreshCollStmt': ('write', 'ALTER DATABASE ... REFRESH COLLATION VERSION'),
    'CreateTableSpaceStmt': ('write', 'CREATE TABLESPACE'),
    'DropTableSpaceStmt': ('write', 'DROP TABLESPACE'),
    'AlterTableSpaceOptionsStmt': ('write', 'ALTER TABLESPACE'),
    'AlterTableMoveAllStmt': ('write', 'ALTER TABLE ALL IN TABLESPACE'),
    'AlterSystemStmt': ('write', 'ALTER SYSTEM rewrites server configuration'),
    'CheckPointStmt': ('write', 'forces a checkpoint; server-wide I/O'),
    'LoadStmt': ('write', 'loads a shared library into the backend'),
    # -- maintenance -------------------------------------------------------
    'VacuumStmt': ('write', 'VACUUM / ANALYZE; ANALYZE writes statistics'),
    'ClusterStmt': ('write', 'CLUSTER rewrites heap order'),
    'ReindexStmt': ('write', 'REINDEX rebuilds index storage'),
    'RefreshMatViewStmt': ('write', 'REFRESH MATERIALIZED VIEW rewrites contents'),
    # -- replication -------------------------------------------------------
    'CreatePublicationStmt': ('write', 'CREATE PUBLICATION'),
    'AlterPublicationStmt': ('write', 'ALTER PUBLICATION'),
    'CreateSubscriptionStmt': ('write', 'CREATE SUBSCRIPTION; also an outbound connection'),
    'AlterSubscriptionStmt': ('write', 'ALTER SUBSCRIPTION'),
    'DropSubscriptionStmt': ('write', 'DROP SUBSCRIPTION'),
    # -- notification -------------------------------------------------------
    'NotifyStmt': ('write', 'NOTIFY delivers a message to other sessions'),
}

READ_CATEGORY_NODES = frozenset(
    name for name, (category, _) in STMT_NODE_CLASSIFICATION.items() if category == 'read'
)


def test_every_stmt_node_is_classified():
    """No statement node type may go unreviewed.

    Fails when a PostgreSQL upgrade introduces a node type, forcing a decision
    instead of letting it be silently rejected as an unknown write.
    """
    grammar_nodes = {name for name in dir(ast) if name.endswith('Stmt')}
    unclassified = sorted(grammar_nodes - STMT_NODE_CLASSIFICATION.keys())
    assert not unclassified, (
        f'{len(unclassified)} statement node type(s) added by a grammar upgrade and not yet '
        f'classified read/write/by-design/nested: {unclassified}'
    )


def test_classification_has_no_stale_entries():
    """Every classified name still exists, so renames and removals surface here."""
    grammar_nodes = {name for name in dir(ast) if name.endswith('Stmt')}
    stale = sorted(STMT_NODE_CLASSIFICATION.keys() - grammar_nodes)
    assert not stale, f'classified node type(s) no longer in the grammar: {stale}'


def test_allowlist_is_exactly_the_read_node_types():
    """The guard's allowlist and the reviewed read set must not drift apart."""
    assert READ_ONLY_ALLOWED_STMT_NODES == READ_CATEGORY_NODES


@pytest.mark.parametrize(
    'node,reason',
    sorted(
        (name, reason)
        for name, (category, reason) in STMT_NODE_CLASSIFICATION.items()
        if category == 'by-design'
    ),
)
def test_intentional_strictness_is_documented(node, reason):
    """Rejecting something PostgreSQL would allow read-only requires a stated reason."""
    assert reason and len(reason) > 15, f'{node} needs a substantive justification'


def test_set_operations_do_not_introduce_a_foreign_statement_node():
    """UNION / INTERSECT / EXCEPT must stay inside SelectStmt.

    ``SetOperationStmt`` is deliberately absent from the allowlist. That is only
    safe because the raw parse tree represents set operations as a ``SelectStmt``
    with ``op``/``larg``/``rarg``; if a grammar change started emitting
    ``SetOperationStmt`` in raw trees, every UNION would be rejected. Pin it.
    """
    for sql in (
        'SELECT 1 UNION SELECT 2',
        'SELECT 1 UNION ALL SELECT 2',
        'SELECT 1 INTERSECT SELECT 2',
        'SELECT 1 EXCEPT SELECT 2',
        '(SELECT 1) UNION (SELECT 2) ORDER BY 1',
    ):
        node_types = {type(n).__name__ for n in _walk(parse_sql(sql)[0])}
        assert 'SetOperationStmt' not in node_types
        assert node_types <= READ_ONLY_ALLOWED_STMT_NODES | {
            n for n in node_types if not n.endswith('Stmt')
        }


def _walk(node):
    """Yield every node in a parse tree (mirrors the guard's own traversal)."""
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, ast.Node):
            yield item
            for attr in item:
                stack.append(getattr(item, attr, None))
        elif isinstance(item, (tuple, list)):
            stack.extend(item)


def _statement_node_types(sql):
    """Return the ``*Stmt`` node type names produced by parsing ``sql``."""
    return {
        type(n).__name__ for n in _walk(parse_sql(sql)[0]) if type(n).__name__.endswith('Stmt')
    }


# --- The rejection direction, one real statement per blocked node type ------
# The guard rejects any statement node outside the allowlist, so in principle
# every non-read type is rejected by construction and
# ``test_allowlist_is_exactly_the_read_node_types`` proves it. That proof has a
# blind spot: it assumes each operation actually *produces* its distinctive node.
# ``SELECT ... INTO`` is the counter-example that motivated an explicit check --
# a table creation whose parse tree contains only allowed node types. So each
# blocked type also gets a real statement here, asserting both that the SQL
# produces the node we think it does and that the guard rejects it.
#
# Written to be non-executable against a real database (objects that do not
# exist) since nothing here runs SQL -- these strings are only ever parsed.
BLOCKED_STATEMENT_BY_NODE_TYPE = {
    'AlterCollationStmt': 'ALTER COLLATION c REFRESH VERSION',
    'AlterDatabaseRefreshCollStmt': 'ALTER DATABASE d REFRESH COLLATION VERSION',
    'AlterDatabaseSetStmt': 'ALTER DATABASE d SET work_mem = $$8MB$$',
    'AlterDatabaseStmt': 'ALTER DATABASE d WITH CONNECTION LIMIT 5',
    'AlterDefaultPrivilegesStmt': (
        'ALTER DEFAULT PRIVILEGES IN SCHEMA s GRANT SELECT ON TABLES TO bob'
    ),
    'AlterDomainStmt': 'ALTER DOMAIN dom SET NOT NULL',
    'AlterEnumStmt': "ALTER TYPE mood ADD VALUE 'meh'",
    'AlterEventTrigStmt': 'ALTER EVENT TRIGGER et DISABLE',
    'AlterExtensionContentsStmt': 'ALTER EXTENSION ext ADD FUNCTION f()',
    'AlterExtensionStmt': 'ALTER EXTENSION ext UPDATE',
    'AlterFdwStmt': 'ALTER FOREIGN DATA WRAPPER w OPTIONS (SET a $$b$$)',
    # An attacker-chosen endpoint on an existing foreign server: rejected in
    # read-only mode as DDL, and documented as role-owned in write mode.
    'AlterForeignServerStmt': "ALTER SERVER srv OPTIONS (SET host '169.254.169.254')",
    'AlterFunctionStmt': 'ALTER FUNCTION f() IMMUTABLE',
    'AlterObjectDependsStmt': 'ALTER FUNCTION f() DEPENDS ON EXTENSION ext',
    'AlterObjectSchemaStmt': 'ALTER TABLE t SET SCHEMA s2',
    'AlterOpFamilyStmt': 'ALTER OPERATOR FAMILY of USING btree ADD OPERATOR 1 = (int, int)',
    'AlterOperatorStmt': 'ALTER OPERATOR = (int, int) SET (RESTRICT = eqsel)',
    # ALTER TABLE ... OWNER TO parses as AlterTableStmt, so a non-table object
    # is needed to reach AlterOwnerStmt itself.
    'AlterOwnerStmt': 'ALTER SCHEMA s OWNER TO bob',
    'AlterPolicyStmt': 'ALTER POLICY p ON t USING (true)',
    'AlterPublicationStmt': 'ALTER PUBLICATION pub ADD TABLE t',
    'AlterRoleSetStmt': 'ALTER ROLE bob SET work_mem = $$8MB$$',
    'AlterRoleStmt': 'ALTER ROLE bob WITH SUPERUSER',
    'AlterSeqStmt': 'ALTER SEQUENCE seq RESTART WITH 1',
    'AlterStatsStmt': 'ALTER STATISTICS st SET STATISTICS 100',
    'AlterSubscriptionStmt': 'ALTER SUBSCRIPTION sub ENABLE',
    'AlterTSConfigurationStmt': (
        'ALTER TEXT SEARCH CONFIGURATION cfg ADD MAPPING FOR word WITH simple'
    ),
    'AlterTSDictionaryStmt': 'ALTER TEXT SEARCH DICTIONARY dict (StopWords = english)',
    'AlterTableMoveAllStmt': 'ALTER TABLE ALL IN TABLESPACE ts SET TABLESPACE ts2',
    'AlterTableSpaceOptionsStmt': 'ALTER TABLESPACE ts SET (random_page_cost = 1.1)',
    'AlterTypeStmt': 'ALTER TYPE ty SET (RECEIVE = NONE)',
    'AlterUserMappingStmt': 'ALTER USER MAPPING FOR bob SERVER srv OPTIONS (SET user $$x$$)',
    'CompositeTypeStmt': 'CREATE TYPE ct AS (a int, b text)',
    'ConstraintsSetStmt': 'SET CONSTRAINTS ALL DEFERRED',
    'CreateAmStmt': 'CREATE ACCESS METHOD am TYPE INDEX HANDLER h',
    'CreateCastStmt': 'CREATE CAST (int AS text) WITH FUNCTION f(int)',
    'CreateConversionStmt': "CREATE CONVERSION conv FOR 'UTF8' TO 'LATIN1' FROM f",
    'CreateDomainStmt': 'CREATE DOMAIN dom AS int CHECK (VALUE > 0)',
    'CreateEnumStmt': "CREATE TYPE mood AS ENUM ('a','b')",
    'CreateEventTrigStmt': 'CREATE EVENT TRIGGER et ON ddl_command_start EXECUTE FUNCTION f()',
    'CreateFdwStmt': 'CREATE FOREIGN DATA WRAPPER w HANDLER h',
    'CreateForeignServerStmt': (
        "CREATE SERVER srv FOREIGN DATA WRAPPER postgres_fdw OPTIONS (host '169.254.169.254')"
    ),
    'CreateForeignTableStmt': 'CREATE FOREIGN TABLE ft (a int) SERVER srv',
    'CreateOpClassStmt': 'CREATE OPERATOR CLASS oc FOR TYPE int USING btree AS OPERATOR 1 =',
    'CreateOpFamilyStmt': 'CREATE OPERATOR FAMILY of USING btree',
    # A bare CREATE LANGUAGE parses as CreateExtensionStmt; the HANDLER form is
    # what reaches CreatePLangStmt.
    'CreatePLangStmt': 'CREATE TRUSTED PROCEDURAL LANGUAGE plx HANDLER h',
    'CreatePolicyStmt': 'CREATE POLICY p ON t USING (true)',
    'CreatePublicationStmt': 'CREATE PUBLICATION pub FOR ALL TABLES',
    'CreateRangeStmt': 'CREATE TYPE rng AS RANGE (SUBTYPE = int)',
    'CreateRoleStmt': "CREATE ROLE bob LOGIN PASSWORD 'x'",
    'CreateStatsStmt': 'CREATE STATISTICS st ON a, b FROM t',
    # An outbound connection string in DDL form.
    'CreateSubscriptionStmt': "CREATE SUBSCRIPTION sub CONNECTION 'host=evil' PUBLICATION pub",
    'CreateTableSpaceStmt': "CREATE TABLESPACE ts LOCATION '/mnt/x'",
    'CreateTransformStmt': (
        'CREATE TRANSFORM FOR int LANGUAGE sql (FROM SQL WITH FUNCTION f(internal))'
    ),
    'CreateTrigStmt': 'CREATE TRIGGER tg BEFORE INSERT ON t FOR EACH ROW EXECUTE FUNCTION f()',
    'CreateUserMappingStmt': 'CREATE USER MAPPING FOR bob SERVER srv OPTIONS (user $$x$$)',
    'CreatedbStmt': 'CREATE DATABASE newdb',
    'DefineStmt': 'CREATE AGGREGATE agg (int) (SFUNC = f, STYPE = int)',
    'DropOwnedStmt': 'DROP OWNED BY bob',
    'DropRoleStmt': 'DROP ROLE bob',
    'DropSubscriptionStmt': 'DROP SUBSCRIPTION sub',
    'DropTableSpaceStmt': 'DROP TABLESPACE ts',
    'DropUserMappingStmt': 'DROP USER MAPPING FOR bob SERVER srv',
    'DropdbStmt': 'DROP DATABASE d',
    # Privilege escalation in one statement, if the role has the membership.
    'GrantRoleStmt': 'GRANT rds_superuser TO current_user',
    'RuleStmt': 'CREATE RULE r AS ON INSERT TO t DO INSTEAD NOTHING',
}


@pytest.mark.parametrize(
    'node_type,sql',
    sorted(BLOCKED_STATEMENT_BY_NODE_TYPE.items()),
    ids=sorted(BLOCKED_STATEMENT_BY_NODE_TYPE),
)
def test_blocked_statement_produces_the_expected_node(node_type, sql):
    """The probe must exercise the node type it claims to.

    Without this, a probe whose SQL quietly parses into a different node (as
    ``ALTER TABLE ... OWNER TO`` does) would appear to cover a type it never
    touches, and the rejection assertion below would prove nothing about it.
    """
    assert node_type in _statement_node_types(sql)


@pytest.mark.parametrize(
    'node_type,sql',
    sorted(BLOCKED_STATEMENT_BY_NODE_TYPE.items()),
    ids=sorted(BLOCKED_STATEMENT_BY_NODE_TYPE),
)
def test_blocked_statement_is_rejected_in_read_only_mode(node_type, sql):
    """Every non-read statement type must be rejected, exercised by real SQL."""
    with pytest.raises(SqlPolicyError):
        assert_executable(sql, allow_write_query=False)


@pytest.mark.parametrize(
    'node_type,sql',
    sorted(BLOCKED_STATEMENT_BY_NODE_TYPE.items()),
    ids=sorted(BLOCKED_STATEMENT_BY_NODE_TYPE),
)
def test_blocked_statement_is_write_set_not_dangerous_set(node_type, sql):
    """These are write-set members, so write mode must let them past the guard.

    Pins the mode contract per statement type: had one of them belonged in the
    dangerous set instead, it would be rejected here too and this test would say
    so rather than leaving the distinction implicit.
    """
    assert_executable(sql, allow_write_query=True)


def test_every_blocked_node_type_has_a_probe():
    """No blocked statement type may be covered by the construction proof alone.

    The allowlist proof shows the guard rejects anything outside the read set;
    this closes the remaining question of whether each operation really produces
    its own node. The four 'nested' types are exempt because no standalone
    statement can produce them -- they only appear inside another statement's
    tree, where the enclosing statement's classification already applies.
    """
    expected = {
        name
        for name, (category, _) in STMT_NODE_CLASSIFICATION.items()
        if category in ('write', 'by-design')
    }
    covered = set(BLOCKED_STATEMENT_BY_NODE_TYPE) | {
        node
        for node in expected
        for corpus_sql in _OTHER_CORPUS_BLOCKED_SQL
        if node in _statement_node_types(corpus_sql)
    }
    missing = sorted(expected - covered)
    assert not missing, f'blocked statement types with no SQL probe anywhere: {missing}'


# Blocked statements that already live in test_sql_guard.py's write-set and
# dangerous-set corpora. Listed here so the coverage assertion above can credit
# them instead of duplicating them.
_OTHER_CORPUS_BLOCKED_SQL = [
    'INSERT INTO t (a) VALUES (1)',
    'UPDATE t SET a = 1',
    'DELETE FROM t',
    'MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN DELETE',
    'TRUNCATE t',
    'CREATE TABLE t (id int)',
    'CREATE TABLE t2 AS SELECT 1',
    'ALTER TABLE t ADD COLUMN c int',
    'DROP TABLE t',
    'ALTER TABLE t RENAME TO t2',
    'CREATE VIEW v AS SELECT 1',
    'CREATE INDEX i ON t (a)',
    'CREATE SEQUENCE seq',
    'CREATE SCHEMA s',
    'CREATE FUNCTION f() RETURNS int AS $$ SELECT 1 $$ LANGUAGE sql',
    'CREATE EXTENSION citext',
    "COMMENT ON TABLE t IS 'x'",
    "SECURITY LABEL ON TABLE t IS 'x'",
    'IMPORT FOREIGN SCHEMA remote FROM SERVER srv INTO local',
    'GRANT SELECT ON t TO bob',
    'VACUUM t',
    'ANALYZE t',
    'CLUSTER t USING i',
    'REINDEX TABLE t',
    'REFRESH MATERIALIZED VIEW mv',
    'DO $$ BEGIN PERFORM 1; END $$',
    'CALL p()',
    'PREPARE p AS SELECT 1',
    'EXECUTE p',
    'DEALLOCATE p',
    'DECLARE c CURSOR FOR SELECT 1',
    'FETCH 1 FROM c',
    'CLOSE c',
    'LISTEN chan',
    'NOTIFY chan',
    'UNLISTEN chan',
    'LOCK TABLE t',
    'SET work_mem = $$8MB$$',
    'DISCARD PLANS',
    'BEGIN',
    'CHECKPOINT',
    'LOAD $$x$$',
    'ALTER SYSTEM SET log_statement = $$none$$',
    'REASSIGN OWNED BY bob TO alice',
    'COPY t FROM STDIN',
    'ALTER TABLE t REPLICA IDENTITY FULL',
    # A SQL-body function: the only way a ReturnStmt reaches a submitted
    # statement, nested inside the CreateFunctionStmt that is itself rejected.
    'CREATE FUNCTION f() RETURNS int LANGUAGE sql RETURN 1',
]


def test_nested_only_node_types_are_genuinely_unreachable():
    """The two node types with no probe must be unreachable, not merely untested.

    ``ReturnStmt`` turned out to be reachable through a SQL-body function and now
    has a probe. These two do not:

    * ``PLAssignStmt`` -- a PL/pgSQL assignment lives in a routine body, which the
      raw parser treats as an opaque string; a ``DO`` block yields only DoStmt.
    * ``SetOperationStmt`` -- an analyzed-query node; raw set operations stay
      inside SelectStmt (pinned separately by
      ``test_set_operations_do_not_introduce_a_foreign_statement_node``).

    Both enclosing statements are rejected in read-only mode regardless, so the
    absence of a probe costs no coverage.
    """
    do_block = 'DO $$ DECLARE x int; BEGIN x := 1; END $$'
    assert _statement_node_types(do_block) == {'RawStmt', 'DoStmt'}
    with pytest.raises(SqlPolicyError):
        assert_executable(do_block, allow_write_query=False)

    sql_body_function = 'CREATE FUNCTION f() RETURNS int LANGUAGE sql RETURN 1'
    assert 'ReturnStmt' in _statement_node_types(sql_body_function)
    with pytest.raises(SqlPolicyError):
        assert_executable(sql_body_function, allow_write_query=False)


# --- Axis 2: SELECT grammar surface ---------------------------------------
# Each entry executed successfully inside a live PG 16.4 read-only transaction,
# so PostgreSQL agrees it is a read.
READ_ONLY_ALLOWED_GRAMMAR = [
    ('basic projection', 'SELECT id, name FROM fp.emp'),
    ('star', 'SELECT * FROM fp.emp'),
    ('alias and qualified name', 'SELECT e.name AS who FROM fp.emp AS e'),
    (
        'where with dollar-quoted literal',
        'SELECT * FROM fp.emp WHERE salary > 50 AND name <> $$x$$',
    ),
    ('inner join', 'SELECT e.name, d.name FROM fp.emp e JOIN fp.dept d ON e.dept_id = d.id'),
    ('left join', 'SELECT e.name FROM fp.emp e LEFT JOIN fp.dept d ON e.dept_id = d.id'),
    ('right join', 'SELECT d.name FROM fp.emp e RIGHT JOIN fp.dept d ON e.dept_id = d.id'),
    ('full join', 'SELECT 1 FROM fp.emp e FULL JOIN fp.dept d ON e.dept_id = d.id'),
    ('cross join', 'SELECT 1 FROM fp.emp CROSS JOIN fp.dept'),
    ('natural join', 'SELECT 1 FROM fp.emp NATURAL JOIN fp.dept'),
    ('join using', 'SELECT 1 FROM fp.emp e JOIN fp.dept d USING (id)'),
    ('self join', 'SELECT a.name FROM fp.emp a JOIN fp.emp b ON a.id <> b.id'),
    ('union', 'SELECT name FROM fp.emp UNION SELECT name FROM fp.dept'),
    ('union all', 'SELECT name FROM fp.emp UNION ALL SELECT name FROM fp.dept'),
    ('intersect', 'SELECT name FROM fp.emp INTERSECT SELECT name FROM fp.dept'),
    ('except', 'SELECT name FROM fp.emp EXCEPT SELECT name FROM fp.dept'),
    ('parenthesized set operations', '(SELECT 1) UNION (SELECT 2) ORDER BY 1'),
    ('cte', 'WITH x AS (SELECT * FROM fp.emp) SELECT count(*) FROM x'),
    ('cte materialized', 'WITH x AS MATERIALIZED (SELECT 1 a) SELECT * FROM x'),
    ('cte not materialized', 'WITH x AS NOT MATERIALIZED (SELECT 1 a) SELECT * FROM x'),
    (
        'recursive cte',
        'WITH RECURSIVE t(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM t WHERE n < 5) SELECT sum(n) FROM t',
    ),
    (
        'recursive cte with cycle clause',
        'WITH RECURSIVE t(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM t WHERE n<3) '
        'CYCLE n SET c USING p SELECT n FROM t',
    ),
    ('multiple ctes', 'WITH a AS (SELECT 1 x), b AS (SELECT 2 y) SELECT * FROM a, b'),
    (
        'cte referencing an earlier cte',
        'WITH a AS (SELECT 1 x), b AS (SELECT x+1 y FROM a) SELECT * FROM b',
    ),
    ('window function', 'SELECT name, rank() OVER (ORDER BY salary DESC) FROM fp.emp'),
    (
        'named window',
        'SELECT name, sum(salary) OVER w FROM fp.emp WINDOW w AS (PARTITION BY dept_id)',
    ),
    (
        'frame rows',
        'SELECT sum(salary) OVER (ORDER BY id ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) FROM fp.emp',
    ),
    (
        'frame range unbounded',
        'SELECT sum(salary) OVER (ORDER BY id RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) FROM fp.emp',
    ),
    (
        'frame groups exclude ties',
        'SELECT count(*) OVER (ORDER BY dept_id GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW EXCLUDE TIES) FROM fp.emp',
    ),
    (
        'frame exclude current row',
        'SELECT count(*) OVER (ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW '
        'EXCLUDE CURRENT ROW) FROM fp.emp',
    ),
    (
        'grouping sets',
        'SELECT dept_id, m, count(*) FROM fp.emp GROUP BY GROUPING SETS ((dept_id),(m))',
    ),
    ('cube', 'SELECT dept_id, m, count(*) FROM fp.emp GROUP BY CUBE (dept_id, m)'),
    ('rollup', 'SELECT dept_id, m, count(*) FROM fp.emp GROUP BY ROLLUP (dept_id, m)'),
    ('group by distinct', 'SELECT dept_id FROM fp.emp GROUP BY DISTINCT ROLLUP (dept_id)'),
    ('grouping()', 'SELECT grouping(dept_id) FROM fp.emp GROUP BY ROLLUP (dept_id)'),
    ('having', 'SELECT dept_id FROM fp.emp GROUP BY dept_id HAVING count(*) > 1'),
    ('aggregate filter', 'SELECT count(*) FILTER (WHERE salary > 90) FROM fp.emp'),
    ('aggregate order by', 'SELECT string_agg(name, $$,$$ ORDER BY name) FROM fp.emp'),
    ('count distinct', 'SELECT count(DISTINCT name) FROM fp.emp'),
    ('within group', 'SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY salary) FROM fp.emp'),
    ('json aggregate', 'SELECT json_object_agg(name, salary) FROM fp.emp'),
    ('distinct', 'SELECT DISTINCT dept_id FROM fp.emp'),
    (
        'distinct on',
        'SELECT DISTINCT ON (dept_id) dept_id, name FROM fp.emp ORDER BY dept_id, name',
    ),
    (
        'order by collate nulls last',
        'SELECT name FROM fp.emp ORDER BY name COLLATE "C" DESC NULLS LAST',
    ),
    ('order by ordinal', 'SELECT name FROM fp.emp ORDER BY 1'),
    ('limit offset', 'SELECT * FROM fp.emp ORDER BY id LIMIT 2 OFFSET 1'),
    ('fetch first with ties', 'SELECT * FROM fp.emp ORDER BY salary FETCH FIRST 2 ROWS WITH TIES'),
    (
        'lateral subquery',
        'SELECT e.name, x.c FROM fp.emp e, LATERAL (SELECT count(*) c FROM fp.dept) x',
    ),
    ('lateral join', 'SELECT 1 FROM fp.dept d JOIN LATERAL (SELECT 1) y ON true'),
    ('subquery in from', 'SELECT * FROM (SELECT * FROM fp.emp) s'),
    ('subquery in select list', 'SELECT (SELECT count(*) FROM fp.dept) FROM fp.emp'),
    ('subquery in where', 'SELECT * FROM fp.emp WHERE dept_id IN (SELECT id FROM fp.dept)'),
    (
        'correlated exists',
        'SELECT * FROM fp.emp e WHERE EXISTS (SELECT 1 FROM fp.dept d WHERE d.id = e.dept_id)',
    ),
    (
        'any and all',
        'SELECT * FROM fp.emp WHERE salary > ALL (SELECT 1) AND id = ANY (SELECT id FROM fp.emp)',
    ),
    (
        'scalar subquery arithmetic',
        'SELECT (SELECT max(salary) FROM fp.emp) - (SELECT min(salary) FROM fp.emp)',
    ),
    ('tablesample bernoulli', 'SELECT * FROM fp.emp TABLESAMPLE BERNOULLI (50)'),
    (
        'tablesample system repeatable',
        'SELECT * FROM fp.emp TABLESAMPLE SYSTEM (50) REPEATABLE (7)',
    ),
    ('values', 'VALUES (1, $$a$$), (2, $$b$$)'),
    ('table command', 'TABLE fp.emp'),
    ('row constructor', 'SELECT ROW(1, $$a$$)'),
    ('array constructor', 'SELECT ARRAY[1,2,3]'),
    ('array subscript', 'SELECT tags[1] FROM fp.dept'),
    ('array slice', 'SELECT tags[1:2] FROM fp.dept'),
    ('array slice open lower bound', 'SELECT tags[:2] FROM fp.dept'),
    ('unnest with ordinality', 'SELECT * FROM unnest(ARRAY[1,2]) WITH ORDINALITY'),
    ('set-returning function in select list', 'SELECT generate_series(1,3)'),
    ('set-returning function in from', 'SELECT * FROM generate_series(1,3) g(n)'),
    ('rows from', 'SELECT * FROM ROWS FROM (generate_series(1,2), generate_series(1,3))'),
    (
        'set-returning function with column definitions',
        'SELECT * FROM json_to_recordset($$[{"a":1}]$$) AS x(a int)',
    ),
    ('cast forms', 'SELECT CAST(salary AS int), salary::int FROM fp.emp'),
    ('case', 'SELECT CASE WHEN salary > 90 THEN $$hi$$ ELSE $$lo$$ END FROM fp.emp'),
    (
        'coalesce nullif greatest',
        'SELECT coalesce(dept_id,0), nullif(id,0), greatest(1,2) FROM fp.emp',
    ),
    ('jsonb operators', "SELECT meta->>'a', meta #> '{a}', meta @> '{}' FROM fp.dept"),
    ('jsonb path query', "SELECT jsonb_path_query_first(meta, '$.a') FROM fp.dept"),
    ('json build object', 'SELECT json_build_object($$k$$, name) FROM fp.emp'),
    ('multirange containment', 'SELECT int4multirange(int4range(1,3)) @> 2'),
    (
        'xmltable',
        "SELECT * FROM xmltable('/r' PASSING XMLPARSE(DOCUMENT '<r><a>1</a></r>') COLUMNS a int PATH 'a')",
    ),
    ('full text search', "SELECT * FROM fp.emp WHERE body @@ to_tsquery('english','x')"),
    ('regex operators', "SELECT name FROM fp.emp WHERE name ~ '^a' AND name !~~ 'z%'"),
    ('like with escape', "SELECT * FROM fp.emp WHERE name LIKE 'a!%' ESCAPE '!'"),
    ('ilike and similar to', "SELECT * FROM fp.emp WHERE name ILIKE 'A%' OR name SIMILAR TO 'a%'"),
    ('is distinct from', 'SELECT * FROM fp.emp WHERE dept_id IS DISTINCT FROM 1'),
    ('between symmetric', 'SELECT * FROM fp.emp WHERE salary BETWEEN SYMMETRIC 100 AND 1'),
    ('enum comparison', "SELECT * FROM fp.emp WHERE m = 'happy'"),
    # SQL-standard function syntax: parses as a dedicated node or SQLValueFunction
    # rather than FuncCall, so it reaches the guard by a different path.
    ('sql value functions', 'SELECT current_date, current_timestamp, localtime, current_role'),
    ('extract', 'SELECT extract(year FROM hired) FROM fp.emp'),
    ('substring from for', 'SELECT substring(name FROM 1 FOR 2) FROM fp.emp'),
    ('trim both', 'SELECT trim(BOTH $$a$$ FROM name) FROM fp.emp'),
    ('overlay placing', 'SELECT overlay(name PLACING $$x$$ FROM 1) FROM fp.emp'),
    ('position in', 'SELECT position($$a$$ IN name) FROM fp.emp'),
    ('at time zone', "SELECT hired::timestamp AT TIME ZONE 'UTC' FROM fp.emp"),
    ('partitioned table read', 'SELECT * FROM fp.part'),
    ('view read', 'SELECT * FROM fp.v_emp'),
    ('materialized view read', 'SELECT * FROM fp.mv_emp'),
    ('user-defined function call', 'SELECT fp.raise_pct(salary, 10) FROM fp.emp'),
    ('expression index predicate', 'SELECT * FROM fp.emp WHERE lower(name) = $$ada$$'),
    ('explain', 'EXPLAIN SELECT * FROM fp.emp'),
    ('explain analyze', 'EXPLAIN ANALYZE SELECT * FROM fp.emp'),
    ('explain format json', 'EXPLAIN (FORMAT JSON) SELECT 1'),
    ('explain verbose costs off', 'EXPLAIN (VERBOSE, COSTS OFF) SELECT 1'),
    ('comment styles', 'SELECT 1 -- trailing\n/* block */'),
    ('dollar-quoted literal containing a quote', "SELECT $tag$has '' quote$tag$"),
    ('escape string', "SELECT E'\\n'"),
    ('unicode-escaped identifier', 'SELECT 1 AS U&"caf\\00e9"'),
]


@pytest.mark.parametrize(
    'feature,sql', READ_ONLY_ALLOWED_GRAMMAR, ids=[f for f, _ in READ_ONLY_ALLOWED_GRAMMAR]
)
def test_select_grammar_not_over_blocked(feature, sql):
    """Every SELECT grammar feature PostgreSQL runs read-only must pass the guard."""
    assert_executable(sql, allow_write_query=False)


# --- Axis 4: queries real tooling issues ----------------------------------
# Introspection an agent, ORM, dashboard, or psql actually runs. These are the
# queries whose over-blocking would be noticed immediately in production.
READ_ONLY_ALLOWED_TOOLING = [
    (
        'information_schema columns',
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'emp'",
    ),
    (
        'information_schema tables',
        "SELECT table_name FROM information_schema.tables WHERE table_schema='fp'",
    ),
    (
        'information_schema constraints join',
        'SELECT c.constraint_name, k.column_name FROM information_schema.table_constraints c '
        'JOIN information_schema.key_column_usage k USING (constraint_name)',
    ),
    ('information_schema referential', 'SELECT * FROM information_schema.referential_constraints'),
    (
        'information_schema views',
        'SELECT table_name, view_definition FROM information_schema.views',
    ),
    (
        'information_schema routines',
        "SELECT routine_name FROM information_schema.routines WHERE specific_schema='fp'",
    ),
    (
        'psql backslash-d column query',
        'SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod), '
        'pg_catalog.pg_get_expr(d.adbin, d.adrelid), a.attnotnull '
        'FROM pg_catalog.pg_attribute a LEFT JOIN pg_catalog.pg_attrdef d '
        'ON a.attrelid = d.adrelid AND a.attnum = d.adnum '
        "WHERE a.attrelid = 'fp.emp'::regclass AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum",
    ),
    (
        'pg_class joined to namespace',
        'SELECT c.relname, n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace '
        "WHERE n.nspname = 'fp'",
    ),
    (
        'index definitions',
        'SELECT indexname, pg_get_indexdef(i.indexrelid) FROM pg_indexes JOIN pg_index i ON true '
        "WHERE schemaname='fp' LIMIT 5",
    ),
    (
        'constraint definitions',
        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'fp.emp'::regclass",
    ),
    ('view definition', "SELECT pg_get_viewdef('fp.v_emp'::regclass, true)"),
    ('function definition', "SELECT pg_get_functiondef('fp.raise_pct'::regproc)"),
    ('serial sequence lookup', "SELECT pg_get_serial_sequence('fp.emp','id')"),
    (
        'object and column comments',
        "SELECT obj_description('fp.emp'::regclass), col_description('fp.emp'::regclass, 4)",
    ),
    ('to_regclass probe', "SELECT to_regclass('fp.emp')"),
    ('partition key definition', "SELECT pg_get_partkeydef('fp.part'::regclass)"),
    (
        'enum values',
        "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid WHERE t.typname='mood'",
    ),
    ('relation size', "SELECT pg_size_pretty(pg_total_relation_size('fp.emp'))"),
    ('database size', 'SELECT pg_database_size(current_database())'),
    ('table statistics', 'SELECT relname, n_live_tup FROM pg_stat_user_tables'),
    ('column statistics', "SELECT attname, n_distinct FROM pg_stats WHERE tablename = 'emp'"),
    (
        'session activity',
        'SELECT pid, state, query FROM pg_stat_activity WHERE pid <> pg_backend_pid()',
    ),
    ('lock inspection', 'SELECT locktype, mode FROM pg_locks LIMIT 5'),
    ('settings lookup', "SELECT name, setting FROM pg_settings WHERE name = 'work_mem'"),
    ('current_setting', "SELECT current_setting('work_mem')"),
    ('role listing', 'SELECT rolname, rolsuper FROM pg_roles LIMIT 5'),
    (
        'the privilege guardrail probe itself',
        'SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user',
    ),
    ('privilege check function', "SELECT has_table_privilege('fp.emp','SELECT')"),
    ('database listing', 'SELECT datname FROM pg_database'),
    ('session identity', 'SELECT version(), current_database(), current_user, session_user'),
    ('explain for tuning', 'EXPLAIN (ANALYZE, BUFFERS, VERBOSE) SELECT count(*) FROM fp.emp'),
    ('show a setting', 'SHOW search_path'),
    ('show all settings', 'SHOW ALL'),
]


@pytest.mark.parametrize(
    'name,sql', READ_ONLY_ALLOWED_TOOLING, ids=[n for n, _ in READ_ONLY_ALLOWED_TOOLING]
)
def test_real_world_tooling_queries_not_over_blocked(name, sql):
    """Introspection that agents, ORMs, and psql actually issue must pass."""
    assert_executable(sql, allow_write_query=False)


# --- The parameterized path ------------------------------------------------
# ``get_table_schema`` and any caller passing ``query_parameters`` sends
# Aurora-style ``:name`` placeholders. Those reads cross two rewrites that plain
# reads never touch -- the guard's parse-only ``$1`` substitution and the psycopg
# executor's ``%(name)s`` substitution -- so a read can satisfy the guard and
# still be corrupted before it reaches the server. That is not hypothetical: the
# executor once mangled ``tags[1:limit_idx]`` into ``tags[1%(limit_idx)s]``.
# Every entry is checked three ways below: the guard allows it, the executor's
# rewrite still parses, and both layers rewrote the same spans.
READ_ONLY_ALLOWED_PARAMETERIZED = [
    ('equality placeholder', 'SELECT * FROM fp.emp WHERE id = :id'),
    ('placeholder without spaces', 'SELECT * FROM fp.emp WHERE id=:id'),
    ('two placeholders', 'SELECT * FROM fp.emp WHERE dept_id = :dept AND name = :name'),
    ('placeholder in function argument', 'SELECT to_regclass(:table_name)'),
    (
        'the get_table_schema query',
        """
        SELECT a.attname AS column_name,
               pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
               col_description(a.attrelid, a.attnum) AS column_comment
        FROM pg_attribute a
        WHERE a.attrelid = to_regclass(:table_name)
          AND a.attnum > 0
          AND NOT a.attisdropped
        ORDER BY a.attnum
    """,
    ),
    ('placeholder with cast', 'SELECT * FROM fp.emp WHERE hired > :since::date'),
    ('placeholder in array constructor', 'SELECT * FROM fp.dept WHERE tags && ARRAY[:tag]'),
    ('placeholder in IN list', 'SELECT * FROM fp.emp WHERE dept_id IN (:a, :b)'),
    ('placeholder in LIMIT', 'SELECT * FROM fp.emp ORDER BY id LIMIT :n'),
    ('placeholder in a CTE', 'WITH x AS (SELECT * FROM fp.emp WHERE id = :id) SELECT * FROM x'),
    ('placeholder beside an array slice', 'SELECT tags[1:2] FROM fp.dept WHERE id = :id'),
    (
        'array slice with a named bound stays a slice',
        'SELECT tags[1:limit_idx] FROM fp.dept WHERE id = :id',
    ),
    ('placeholder and a literal colon', "SELECT 'a:b' AS lit FROM fp.emp WHERE id = :id"),
    (
        'placeholder in a join condition',
        'SELECT 1 FROM fp.emp e JOIN fp.dept d ON d.id = e.dept_id AND d.id = :d',
    ),
]


@pytest.mark.parametrize(
    'name,sql',
    READ_ONLY_ALLOWED_PARAMETERIZED,
    ids=[n for n, _ in READ_ONLY_ALLOWED_PARAMETERIZED],
)
def test_parameterized_reads_not_over_blocked(name, sql):
    """A read carrying :name placeholders must pass the guard."""
    assert_executable(sql, allow_write_query=False)


@pytest.mark.parametrize(
    'name,sql',
    READ_ONLY_ALLOWED_PARAMETERIZED,
    ids=[n for n, _ in READ_ONLY_ALLOWED_PARAMETERIZED],
)
def test_parameterized_reads_survive_the_executor_rewrite(name, sql):
    """What the psycopg path actually sends must still be valid SQL.

    Passing the guard is not enough: the executor rewrites the same statement
    independently, and a rewrite that lands inside an array subscript produces a
    statement the database cannot parse. Reduce ``%(name)s`` to the positional
    form psycopg ultimately sends and confirm the result parses.
    """
    sent = to_psycopg_placeholders(sql)
    parse_sql(re.sub(r'%\(\w+\)s', '$1', sent))


@pytest.mark.parametrize(
    'name,sql',
    READ_ONLY_ALLOWED_PARAMETERIZED,
    ids=[n for n, _ in READ_ONLY_ALLOWED_PARAMETERIZED],
)
def test_both_rewrites_agree_on_the_parameterized_corpus(name, sql):
    """The guard and the executor must treat the same colons as placeholders."""
    expected = len(NAMED_PARAM_PATTERN.findall(sql))
    assert to_parse_placeholders(sql).count('$1') == expected
    assert len(re.findall(r'%\(\w+\)s', to_psycopg_placeholders(sql))) == expected


# --- Axis 3 complement: functions the design deliberately allows ----------
# Design section 5.4.2 "Deliberate allowed boundaries". The denylist's own
# entries are covered in test_sql_guard.py; this is the other half -- the
# observation-only calls that must NOT be swept up by it.
DELIBERATELY_ALLOWED_FUNCTION_READS = [
    ('sequence readers', "SELECT currval('s'), lastval()"),
    ('statistics readers', 'SELECT pg_stat_get_db_xact_commit(oid) FROM pg_database'),
    ('snapshot discard is not a mutation', 'SELECT pg_stat_clear_snapshot()'),
    (
        'nondeterministic generators',
        'SELECT random(), now(), clock_timestamp(), gen_random_uuid()',
    ),
    ('current xid readers', 'SELECT txid_current(), pg_current_xact_id()'),
    ('exported snapshot', 'SELECT pg_export_snapshot()'),
    ('cache-only prewarm', "SELECT pg_prewarm('t')"),
    ('logical slot peek does not consume', "SELECT pg_logical_slot_peek_changes('s',NULL,NULL)"),
    ('replication progress reader', "SELECT pg_replication_origin_progress('o', true)"),
    ('large object read', 'SELECT lo_get(1)'),
    ('fdw connection reader', 'SELECT postgres_fdw_get_connections()'),
    ('wal position readers', 'SELECT pg_current_wal_lsn(), pg_last_wal_receive_lsn()'),
    ('size and type helpers', "SELECT pg_relation_size('t'), pg_typeof(1)"),
]


@pytest.mark.parametrize(
    'name,sql',
    DELIBERATELY_ALLOWED_FUNCTION_READS,
    ids=[n for n, _ in DELIBERATELY_ALLOWED_FUNCTION_READS],
)
def test_observation_only_functions_stay_allowed(name, sql):
    """Reads that resemble mutators must not be swept into the denylist."""
    assert_executable(sql, allow_write_query=False)


# --- Backstop-reliant: allowed by the guard, refused by PostgreSQL ---------
# These pass the guard and are then rejected by ``SET TRANSACTION READ ONLY``
# with "cannot execute SELECT FOR ... in a read-only transaction" (verified on
# PG 16.4). The guard deliberately does not duplicate that check; this test
# records the reliance so that removing the read-only transaction wrapper, or
# adding a parser-level locking-clause check, is a conscious decision.
BACKSTOP_RELIANT_READS = [
    'SELECT * FROM fp.emp FOR UPDATE',
    'SELECT * FROM fp.emp FOR NO KEY UPDATE',
    'SELECT * FROM fp.emp FOR SHARE',
    'SELECT * FROM fp.emp FOR KEY SHARE SKIP LOCKED',
]


@pytest.mark.parametrize('sql', BACKSTOP_RELIANT_READS)
def test_locking_clauses_pass_the_guard_and_rely_on_the_transaction(sql):
    """Row-locking SELECTs pass the guard; the read-only transaction refuses them."""
    assert_executable(sql, allow_write_query=False)


def test_locking_clause_reliance_is_narrow():
    """A locking clause must not become a way to smuggle anything else past the guard."""
    with pytest.raises(SqlPolicyError):
        assert_executable('SELECT pg_read_file($$/etc/passwd$$) FROM fp.emp FOR UPDATE')
    with pytest.raises(SqlPolicyError):
        assert_executable('UPDATE fp.emp SET name = $$x$$', allow_write_query=False)
