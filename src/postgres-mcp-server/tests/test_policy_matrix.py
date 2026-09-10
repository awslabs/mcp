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

"""The policy matrix: every corpus statement classified, then driven in both modes.

The other policy test modules verify specific behaviors -- encoding evasion,
exhaustive statement-node coverage, name-set iteration, placeholder rewrites --
and each is organized around what it is trying to prove. This module is organized
around the *contract* instead, and its job is to guarantee the contract is total:
no statement anywhere in the policy corpora may escape classification, and every
classified statement is driven in both modes.

Four sets, taken from the design's classification (docs/design/
parser-based-sql-policy.md section 3.1):

    set 1  reads               allowed read-only,  allowed write
    set 2  write set (W)       rejected read-only, allowed write
    set 3  dangerous set (D)   rejected read-only, rejected write
    set 4  fail-closed input   rejected read-only, rejected write

Sets 3 and 4 share their expectations but not their meaning, and the distinction
is deliberate. Set 3 classifies an *operation* as dangerous regardless of mode.
Set 4 is not a classification at all: the guard rejects the input because it
cannot establish what the input is (more than one statement, unparseable, beyond
the size cap). Calling ``SELECT 1; SELECT 2`` dangerous would be false -- it is
two reads -- so it gets its own set with the same expectations and an honest
reason. The design doc draws the same line, treating these as FR1/FR7
preconditions rather than set membership.

A fifth combination is logically expressible and must be empty: allowed in
read-only but rejected in write mode. It cannot occur, because write mode runs a
strict subset of the checks -- the dangerous pass runs in both modes and only the
write-set pass is skipped. ``test_no_statement_is_allowed_read_only_but_rejected_in_write_mode``
pins that, which is also the only circumstance under which the set-1 write-mode
cell could ever fail.

Statements are imported from the existing corpora rather than copied, so there is
one source of truth per statement and the specific tests keep their targeted
failure messages.
"""

import pytest
import test_sql_guard as guard_tests
import test_sql_guard_read_only_corpus as corpus_tests
from awslabs.postgres_mcp_server.sql_guard import (
    DANGEROUS_FUNCTIONS,
    DANGEROUS_QUALIFIED_FUNCTIONS,
    READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS,
    READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS,
    SECURITY_SENSITIVE_GUCS,
    SqlPolicyError,
    assert_executable,
)


def _sql_only(entries):
    """Return the SQL from a corpus that may hold plain strings or (label, sql)."""
    out = []
    for entry in entries:
        out.append(entry if isinstance(entry, str) else entry[1])
    return out


# --- Set 1: reads. Allowed in both modes -----------------------------------
# Includes BACKSTOP_RELIANT_READS (SELECT ... FOR UPDATE). At the guard level
# those are set 1: the guard allows them in both modes on purpose. At the system
# level they behave like set 2, because the read-only transaction the connection
# opens refuses them -- which is why they are also asserted end-to-end in
# tests/e2e/e2e_integration_test.py (BACKSTOP_ENFORCED_QUERIES). This module tests
# the guard, so they belong here.
SET_1_READS = sorted(
    set(guard_tests.READ_ONLY_ALLOWED)
    | set(guard_tests.NAMED_PARAM_ALLOWED)
    | set(guard_tests.ARRAY_SLICE_READS)
    | set(guard_tests.QUALIFIED_NEGATIVE)
    | set(_sql_only(corpus_tests.READ_ONLY_ALLOWED_GRAMMAR))
    | set(_sql_only(corpus_tests.READ_ONLY_ALLOWED_TOOLING))
    | set(_sql_only(corpus_tests.READ_ONLY_ALLOWED_PARAMETERIZED))
    | set(_sql_only(corpus_tests.DELIBERATELY_ALLOWED_FUNCTION_READS))
    | set(corpus_tests.BACKSTOP_RELIANT_READS)
)

# --- Set 2: the write set. Rejected read-only, allowed in write mode --------
# The function-name inventories are expanded into calls here so the matrix covers
# names as well as statements; test_sql_guard.py asserts the same names
# individually with per-name test ids.
SET_2_WRITES = sorted(
    set(guard_tests.WRITE_SET_STATEMENTS)
    | set(corpus_tests.BLOCKED_STATEMENT_BY_NODE_TYPE.values())
    | set(corpus_tests._OTHER_CORPUS_BLOCKED_SQL)
    | {f'SELECT {name}()' for name in READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS}
    | {f'SELECT {schema}.{name}()' for schema, name in READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS}
    # set_config of an ordinary GUC is a session write, not a dangerous one.
    | {"SELECT set_config('work_mem', '8MB', false)"}
)

# --- Set 3: the dangerous set. Rejected in both modes ----------------------
SET_3_DANGEROUS = sorted(
    set(guard_tests.DANGEROUS_BOTH_MODES)
    | set(guard_tests.EVASION_VARIANTS)
    | {f'SELECT {name}()' for name in DANGEROUS_FUNCTIONS}
    | {f'SELECT {schema}.{name}()' for schema, name in DANGEROUS_QUALIFIED_FUNCTIONS}
    | {f'SET {guc} = off' for guc in SECURITY_SENSITIVE_GUCS}
    | {f'RESET {guc}' for guc in SECURITY_SENSITIVE_GUCS}
    | {f"SELECT set_config('{guc}', 'off', false)" for guc in SECURITY_SENSITIVE_GUCS}
    | {'RESET ALL', 'DISCARD ALL'}
    # Conservative extension of D: the GUC name cannot be resolved to a literal,
    # so it cannot be proven not to be a security-sensitive one.
    | {"SELECT set_config('row_' || 'security', 'off', false)"}
)

# --- Set 4: fail-closed input. Rejected in both modes ---------------------
SET_4_FAIL_CLOSED = sorted(set(guard_tests.FAIL_CLOSED))

ALL_SETS = {
    1: SET_1_READS,
    2: SET_2_WRITES,
    3: SET_3_DANGEROUS,
    4: SET_4_FAIL_CLOSED,
}


# --- The eight cells -------------------------------------------------------


@pytest.mark.parametrize('sql', SET_1_READS)
def test_set1_read_is_allowed_in_read_only_mode(sql):
    """Cell (1, read-only): a read must pass."""
    assert_executable(sql, allow_write_query=False)


@pytest.mark.parametrize('sql', SET_1_READS)
def test_set1_read_is_allowed_in_write_mode(sql):
    """Cell (1, write): enabling writes must never restrict a read.

    True by construction today -- write mode skips the write-set pass and runs
    nothing extra -- so this cell is insurance against a future write-mode-only
    check, and it fails loudly if one is ever added without thought.
    """
    assert_executable(sql, allow_write_query=True)


@pytest.mark.parametrize('sql', SET_2_WRITES)
def test_set2_write_is_rejected_in_read_only_mode(sql):
    """Cell (2, read-only): a write must be refused."""
    with pytest.raises(SqlPolicyError):
        assert_executable(sql, allow_write_query=False)


@pytest.mark.parametrize('sql', SET_2_WRITES)
def test_set2_write_is_allowed_in_write_mode(sql):
    """Cell (2, write): a write-enabled operator legitimately runs these.

    This is the cell that keeps the write set honest. If a statement here were
    quietly moved into the dangerous set, write mode would start rejecting it and
    this test would say which statement.
    """
    assert_executable(sql, allow_write_query=True)


@pytest.mark.parametrize('sql', SET_3_DANGEROUS)
def test_set3_dangerous_is_rejected_in_read_only_mode(sql):
    """Cell (3, read-only): dangerous constructs are refused."""
    with pytest.raises(SqlPolicyError):
        assert_executable(sql, allow_write_query=False)


@pytest.mark.parametrize('sql', SET_3_DANGEROUS)
def test_set3_dangerous_is_rejected_in_write_mode(sql):
    """Cell (3, write): enabling writes must not unlock a dangerous construct.

    The whole point of D being mode-independent. ``--allow_write_query`` is a
    statement about writing to your own data, not about opening sockets, reading
    the host filesystem, or disabling row-level security.
    """
    with pytest.raises(SqlPolicyError):
        assert_executable(sql, allow_write_query=True)


@pytest.mark.parametrize('sql', SET_4_FAIL_CLOSED)
def test_set4_unclassifiable_input_is_rejected_in_read_only_mode(sql):
    """Cell (4, read-only): input the guard cannot classify is refused."""
    with pytest.raises(SqlPolicyError):
        assert_executable(sql, allow_write_query=False)


@pytest.mark.parametrize('sql', SET_4_FAIL_CLOSED)
def test_set4_unclassifiable_input_is_rejected_in_write_mode(sql):
    """Cell (4, write): failing closed cannot depend on the mode.

    Write mode grants permission to write, not permission to submit input the
    guard was unable to analyze.
    """
    with pytest.raises(SqlPolicyError):
        assert_executable(sql, allow_write_query=True)


# --- The partition itself --------------------------------------------------


def test_the_four_sets_are_disjoint():
    """A statement may belong to exactly one set, or the matrix is contradictory."""
    collisions = {}
    for left in ALL_SETS:
        for right in ALL_SETS:
            if left < right:
                shared = set(ALL_SETS[left]) & set(ALL_SETS[right])
                if shared:
                    collisions[f'set{left} n set{right}'] = sorted(shared)
    assert not collisions, f'statements classified into more than one set: {collisions}'


def test_no_statement_is_allowed_read_only_but_rejected_in_write_mode():
    """The fourth outcome pair must be empty.

    Write mode runs a strict subset of read-only's checks, so no statement can be
    permitted read-only and refused with writes enabled. If this ever fails,
    someone has added a check that fires only in write mode and the classification
    scheme needs a fifth set before the change can land.
    """
    offenders = []
    for sql in [s for entries in ALL_SETS.values() for s in entries]:
        try:
            assert_executable(sql, allow_write_query=False)
        except SqlPolicyError:
            continue  # rejected read-only: cannot be in the impossible cell
        try:
            assert_executable(sql, allow_write_query=True)
        except SqlPolicyError as e:
            offenders.append((sql, str(e)))
    assert not offenders, f'allowed read-only yet rejected in write mode: {offenders}'


# Every uppercase attribute of the two corpus modules, mapped either to the set
# it feeds or to the reason it is not a SQL corpus. The point is the assertion
# below: a corpus added without a decision here fails the suite instead of
# silently sitting outside the matrix.
CORPUS_REGISTRY: dict[tuple[str, str], object] = {
    ('test_sql_guard', 'READ_ONLY_ALLOWED'): 1,
    ('test_sql_guard', 'NAMED_PARAM_ALLOWED'): 1,
    ('test_sql_guard', 'ARRAY_SLICE_READS'): 1,
    ('test_sql_guard', 'QUALIFIED_NEGATIVE'): 1,
    ('test_sql_guard', 'WRITE_SET_STATEMENTS'): 2,
    ('test_sql_guard', 'DANGEROUS_BOTH_MODES'): 3,
    ('test_sql_guard', 'EVASION_VARIANTS'): 3,
    ('test_sql_guard', 'FAIL_CLOSED'): 4,
    ('test_sql_guard', 'DANGEROUS_FUNCTIONS'): 3,
    ('test_sql_guard', 'DANGEROUS_QUALIFIED_FUNCTIONS'): 3,
    ('test_sql_guard', 'SECURITY_SENSITIVE_GUCS'): 3,
    ('test_sql_guard', 'READ_ONLY_PROHIBITED_MUTATING_FUNCTIONS'): 2,
    ('test_sql_guard', 'READ_ONLY_PROHIBITED_QUALIFIED_FUNCTIONS'): 2,
    ('test_sql_guard', 'MAX_SQL_LEN'): 'size cap, not a corpus (drives set 4)',
    ('test_sql_guard_read_only_corpus', 'READ_ONLY_ALLOWED_GRAMMAR'): 1,
    ('test_sql_guard_read_only_corpus', 'READ_ONLY_ALLOWED_TOOLING'): 1,
    ('test_sql_guard_read_only_corpus', 'READ_ONLY_ALLOWED_PARAMETERIZED'): 1,
    ('test_sql_guard_read_only_corpus', 'DELIBERATELY_ALLOWED_FUNCTION_READS'): 1,
    ('test_sql_guard_read_only_corpus', 'BACKSTOP_RELIANT_READS'): 1,
    ('test_sql_guard_read_only_corpus', 'BLOCKED_STATEMENT_BY_NODE_TYPE'): 2,
    ('test_sql_guard_read_only_corpus', '_OTHER_CORPUS_BLOCKED_SQL'): 2,
    ('test_sql_guard_read_only_corpus', 'STMT_NODE_CLASSIFICATION'): (
        'node-type classification map, not SQL'
    ),
    ('test_sql_guard_read_only_corpus', 'READ_CATEGORY_NODES'): 'node type names, not SQL',
    ('test_sql_guard_read_only_corpus', 'READ_ONLY_ALLOWED_STMT_NODES'): (
        'the guard allowlist itself, not SQL'
    ),
    ('test_sql_guard_read_only_corpus', 'NAMED_PARAM_PATTERN'): 'regex, not SQL',
}


def test_every_corpus_is_registered_in_the_matrix():
    """No policy corpus may exist outside the classification.

    Reflects over both corpus modules; a new uppercase corpus that nobody
    classified fails here. Without this the matrix would only cover the corpora
    that happened to be wired up when it was written.
    """
    unregistered = []
    for module, module_name in (
        (guard_tests, 'test_sql_guard'),
        (corpus_tests, 'test_sql_guard_read_only_corpus'),
    ):
        for attribute in dir(module):
            if not (attribute.isupper() or attribute.startswith('_OTHER')):
                continue
            if (module_name, attribute) not in CORPUS_REGISTRY:
                unregistered.append(f'{module_name}.{attribute}')
    assert not unregistered, (
        'corpora with no entry in CORPUS_REGISTRY -- assign each to set 1/2/3/4 or '
        f'state why it is not SQL: {unregistered}'
    )


def test_registry_has_no_stale_entries():
    """A registry entry for something that no longer exists is a maintenance trap."""
    stale = [
        f'{module_name}.{attribute}'
        for (module_name, attribute) in CORPUS_REGISTRY
        if not hasattr(guard_tests if module_name == 'test_sql_guard' else corpus_tests, attribute)
    ]
    assert not stale, f'CORPUS_REGISTRY references attributes that no longer exist: {stale}'


def test_matrix_covers_a_meaningful_number_of_statements():
    """Guard against the matrix silently emptying out.

    A refactor that renamed or moved the corpora could leave the parametrized
    cells with almost nothing in them and every test would still pass. Assert the
    scale is roughly what it should be so that failure mode is visible.
    """
    assert len(SET_1_READS) > 150, len(SET_1_READS)
    assert len(SET_2_WRITES) > 150, len(SET_2_WRITES)
    assert len(SET_3_DANGEROUS) > 80, len(SET_3_DANGEROUS)
    assert len(SET_4_FAIL_CLOSED) >= 9, len(SET_4_FAIL_CLOSED)
