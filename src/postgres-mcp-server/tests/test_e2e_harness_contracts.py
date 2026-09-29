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

"""Cheap checks on the e2e harness that do not need AWS.

The e2e suite provisions real Aurora clusters, so a defect in its own scaffolding
costs minutes and real resources to discover. Some of those defects need no cloud
at all to find. This module covers the ones that are decidable locally.

It exists because of a concrete failure: ``CapturingCtx`` assigned
``self.errors = []`` in ``__init__``, but ``Context`` is a Pydantic model, so
construction raised ``ValueError: "CapturingCtx" object has no field "errors"``
and took the entire query-enforcement suite down at its first statement --
discovered only after a cluster had been created. Nothing about that bug required
a database.

The harness is imported unconditionally rather than with ``importorskip``. It pulls
in boto3 and the server module, but the rest of the unit suite already depends on
both, so a conditional import would add no robustness -- it would only be able to
turn this file's failures into silent skips, which is precisely the outcome that
let the Pydantic bug reach a live cluster.
"""

import asyncio
import os
import re
import sys
from awslabs.postgres_mcp_server.named_params import (
    to_parse_placeholders,
    to_psycopg_placeholders,
)
from awslabs.postgres_mcp_server.sql_guard import assert_executable
from unittest import mock


# pytest puts the test file's own directory on sys.path, which is tests/, not
# tests/e2e/. Add the latter so the harness is importable by module name.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'e2e'))

import e2e_integration_test as e2e  # noqa: E402


def test_capturing_ctx_can_be_constructed():
    """The suite's context object must construct.

    ``run_query_enforcement_suite`` builds one before its first assertion, so a
    construction failure fails the whole suite regardless of cluster type. Pydantic
    rejects assignment to undeclared attributes, which is what broke it.
    """
    ctx = e2e.CapturingCtx()
    assert ctx.errors == []


def test_capturing_ctx_records_error_detail():
    """It has to actually capture, or the ctx-based assertions silently weaken.

    The RDS Data API redacts its returned error, so several assertions depend on
    reading what was reported to the context. A context that swallowed errors
    would leave those assertions comparing against an always-empty list.
    """
    ctx = e2e.CapturingCtx()
    asyncio.run(ctx.error('read-only transaction detail'))
    asyncio.run(ctx.error('second detail'))
    assert ctx.errors == ['read-only transaction detail', 'second detail']


def test_capturing_ctx_instances_do_not_share_state():
    """A mutable default must not leak between instances.

    Declaring ``errors: List[str] = []`` as a Pydantic field is safe because
    Pydantic deep-copies defaults, but the same line on a plain class would make
    every instance share one list. Pin the behavior rather than the reasoning.
    """
    first, second = e2e.CapturingCtx(), e2e.CapturingCtx()
    asyncio.run(first.error('only mine'))
    assert first.errors == ['only mine']
    assert second.errors == []


def test_capturing_ctx_supports_the_clear_between_queries():
    """The suite calls ctx.errors.clear() before each query; it must work in place."""
    ctx = e2e.CapturingCtx()
    asyncio.run(ctx.error('stale'))
    ctx.errors.clear()
    assert ctx.errors == []


def test_endpoint_auth_capability_is_a_subset_of_known_auth_types():
    """Every capability entry must name a real auth type.

    A typo here would silently drop an auth method from the run plan instead of
    failing, so the operator would believe they had tested a path they had not.
    """
    for endpoint, auths in e2e.ENDPOINT_AUTH_CAPABILITY.items():
        unknown = set(auths) - set(e2e.ALL_AUTH_TYPES)
        assert not unknown, f'{endpoint} claims unknown auth type(s): {unknown}'


def test_every_auth_type_maps_to_a_connection_method():
    """The plan resolver indexes AUTH_TYPE_TO_METHOD by auth type; it must be total."""
    missing = [a for a in e2e.ALL_AUTH_TYPES if a not in e2e.AUTH_TYPE_TO_METHOD]
    assert not missing, f'auth types with no ConnectionMethod mapping: {missing}'


def test_policy_matrix_is_importable_from_the_harness():
    """--full-policy-corpus depends on this import, and refuses to run without it.

    The wrapper script invokes the harness through ``uv run --frozen``, so this
    also guards against the matrix becoming unreachable if the dev dependency that
    carries pytest were dropped from the locked environment.
    """
    assert e2e.POLICY_MATRIX_AVAILABLE, getattr(e2e, '_MATRIX_IMPORT_ERROR', None)
    assert e2e.SET_1_READS and e2e.SET_2_WRITES
    assert e2e.SET_3_DANGEROUS and e2e.SET_4_FAIL_CLOSED


def test_full_policy_corpus_is_off_by_default():
    """The sweep is opt-in; a default flip would slow every run by ~1000 round trips."""
    assert e2e.FULL_POLICY_CORPUS is False


# --- Response classification against real observed error strings -------------
# Verbatim from an Aurora PostgreSQL 17.5 run (e2e log 20260910-133056). The
# write-mode backstop assertion originally demanded overall success and failed on
# InsufficientPrivilege, which cost a cluster to discover. These pin the
# classification so the same class of mistake is a unit-test failure instead.

READONLY_TRANSACTION_ERROR = (
    'ReadOnlySqlTransaction: cannot execute SELECT FOR UPDATE in a read-only transaction'
)
INSUFFICIENT_PRIVILEGE_ERROR = 'InsufficientPrivilege: permission denied for table pg_class'
GUARD_READONLY_ERROR = 'Statement type not allowed in read-only mode: InsertStmt'
GUARD_DANGEROUS_ERROR = 'Dangerous function call not allowed: pg_read_file'


def test_rows_with_no_error_are_not_rejected():
    """A successful read must not be classified as any kind of rejection."""
    rows = [{'n': 7}]
    assert not e2e.is_rejected(rows)
    assert not e2e.is_readonly_policy_rejection(rows)
    assert not e2e.is_database_readonly_rejection(rows, [])


def test_guard_readonly_rejection_is_attributed_to_the_guard():
    """The guard's write-set refusal must be distinguishable from the engine's."""
    rows = [{'error': GUARD_READONLY_ERROR}]
    assert e2e.is_rejected(rows)
    assert e2e.is_readonly_policy_rejection(rows)
    assert not e2e.is_database_readonly_rejection(rows, [])


def test_engine_readonly_transaction_error_is_attributed_to_the_database():
    """The two-layer claim depends on telling the engine's refusal from the guard's.

    If this were misattributed, ``readonly:backstop-blocks`` would pass whenever
    the guard grew a locking-clause check, silently converting a live proof of the
    transaction wrapper into a tautology about the guard.
    """
    rows = [{'error': READONLY_TRANSACTION_ERROR}]
    assert e2e.is_rejected(rows)
    assert e2e.is_database_readonly_rejection(rows, [])
    assert not e2e.is_readonly_policy_rejection(rows)


def test_data_api_redacted_error_is_recovered_from_the_context():
    """The RDS Data API hides the detail in its return, so ctx errors must be searched."""
    rows = [{'error': 'query_failed'}]
    assert not e2e.is_database_readonly_rejection(rows, [])
    assert e2e.is_database_readonly_rejection(rows, [READONLY_TRANSACTION_ERROR])


def test_privilege_error_is_not_a_readonly_refusal_of_either_kind():
    """The write-mode backstop assertion rests entirely on this.

    Row locking needs more than SELECT and the suite connects as a least-privilege
    role, so write mode yields InsufficientPrivilege. That must not count as a
    read-only refusal, or the assertion becomes impossible to satisfy -- which is
    exactly the bug this replaced.
    """
    rows = [{'error': INSUFFICIENT_PRIVILEGE_ERROR}]
    assert e2e.is_rejected(rows)
    assert not e2e.is_database_readonly_rejection(rows, [INSUFFICIENT_PRIVILEGE_ERROR])
    assert not e2e.is_readonly_policy_rejection(rows)


def test_dangerous_rejection_is_not_mistaken_for_a_readonly_refusal():
    """Dangerous-set refusals are mode-independent and must classify separately."""
    rows = [{'error': GUARD_DANGEROUS_ERROR}]
    assert e2e.is_rejected(rows)
    assert not e2e.is_readonly_policy_rejection(rows)
    assert not e2e.is_database_readonly_rejection(rows, [])


def test_backstop_assertions_hold_for_the_observed_mode_pair():
    """Replay the exact pair of outcomes Aurora produced for one statement.

    Read-only mode gave ReadOnlySqlTransaction; write mode gave
    InsufficientPrivilege for the identical statement and role. PostgreSQL checks
    the read-only transaction before privileges, so that difference is what
    demonstrates the wrapper was present in one mode and absent in the other.
    """
    readonly_rows = [{'error': READONLY_TRANSACTION_ERROR}]
    write_rows = [{'error': INSUFFICIENT_PRIVILEGE_ERROR}]

    # readonly:backstop-blocks -- refused, and refused by the database.
    assert e2e.is_database_readonly_rejection(readonly_rows, []) and not (
        e2e.is_readonly_policy_rejection(readonly_rows)
    )

    # write:backstop-absent -- no read-only refusal from either layer.
    assert not e2e.is_database_readonly_rejection(write_rows, [INSUFFICIENT_PRIVILEGE_ERROR])
    assert not e2e.is_readonly_policy_rejection(write_rows)


# --- Detached cluster teardown ----------------------------------------------
# Teardown runs in a child process that outlives the harness, so the mechanics
# have to be right: wrong interpreter and the package is unimportable, no new
# session and a signal to our process group takes the child with it, no
# redirection and a failure disappears. None of that is observable from the
# harness's own exit, which is why it is pinned here.


def test_detached_delete_snippet_is_valid_python():
    """The child runs this as -c, so a syntax error would only show in its log."""
    compile(e2e._DETACHED_DELETE_SNIPPET, '<detached-delete>', 'exec')


def test_detached_delete_snippet_calls_the_real_deleter_with_argv():
    """It must invoke internal_delete_cluster, taking arguments from argv.

    argv rather than interpolation means a cluster id never has to be escaped into
    the snippet.
    """
    assert 'internal_delete_cluster' in e2e._DETACHED_DELETE_SNIPPET
    assert 'sys.argv[1]' in e2e._DETACHED_DELETE_SNIPPET
    assert 'sys.argv[2]' in e2e._DETACHED_DELETE_SNIPPET


def test_spawn_detached_returns_pid_and_log_path(tmp_path):
    """The caller needs both, to tell the operator what to watch."""
    with mock.patch.object(e2e.subprocess, 'Popen') as popen:
        popen.return_value = mock.Mock(pid=4242)
        result = e2e.spawn_detached_cluster_deletion('us-west-2', 'c1', log_dir=str(tmp_path))

    assert result is not None
    pid, log_path = result
    assert pid == 4242
    assert 'c1' in os.path.basename(log_path)
    assert os.path.dirname(log_path) == str(tmp_path)


def test_spawn_detached_uses_this_interpreter_and_passes_argv(tmp_path):
    """sys.executable keeps the child inside the venv, so the package imports.

    A bare ``python`` could resolve to a system interpreter without the package
    installed, and the failure would be invisible until someone read the log.
    """
    with mock.patch.object(e2e.subprocess, 'Popen') as popen:
        popen.return_value = mock.Mock(pid=1)
        e2e.spawn_detached_cluster_deletion('eu-west-1', 'my-cluster', log_dir=str(tmp_path))

    argv = popen.call_args.args[0]
    assert argv[0] == sys.executable
    assert argv[1] == '-c'
    assert argv[2] == e2e._DETACHED_DELETE_SNIPPET
    assert argv[3:] == ['eu-west-1', 'my-cluster']


def test_spawn_detached_starts_a_new_session(tmp_path):
    """Without start_new_session the child shares our process group.

    It would then receive the same SIGINT/SIGTERM the harness gets, so a Ctrl-C
    during teardown would abandon a half-deleted cluster.
    """
    with mock.patch.object(e2e.subprocess, 'Popen') as popen:
        popen.return_value = mock.Mock(pid=1)
        e2e.spawn_detached_cluster_deletion('us-west-2', 'c', log_dir=str(tmp_path))

    assert popen.call_args.kwargs['start_new_session'] is True


def test_spawn_detached_redirects_output_and_detaches_stdin(tmp_path):
    """Output must land in the log and the child must never read from a terminal."""
    with mock.patch.object(e2e.subprocess, 'Popen') as popen:
        popen.return_value = mock.Mock(pid=1)
        e2e.spawn_detached_cluster_deletion('us-west-2', 'c', log_dir=str(tmp_path))

    kwargs = popen.call_args.kwargs
    assert kwargs['stderr'] == e2e.subprocess.STDOUT
    assert kwargs['stdin'] == e2e.subprocess.DEVNULL
    assert kwargs['stdout'] is not None


def test_spawn_detached_returns_none_instead_of_raising_when_spawn_fails(tmp_path):
    """Teardown must not fail a run whose assertions already completed.

    Returning None lets the caller fall back to a blocking delete rather than
    leaking the cluster, which is what the cleanup block does.
    """
    with mock.patch.object(e2e.subprocess, 'Popen', side_effect=OSError('no fork for you')):
        assert e2e.spawn_detached_cluster_deletion('us-west-2', 'c', log_dir=str(tmp_path)) is None


def test_spawn_detached_returns_none_when_the_log_cannot_be_opened():
    """An unwritable log directory is reported, not raised."""
    assert (
        e2e.spawn_detached_cluster_deletion(
            'us-west-2', 'c', log_dir='/nonexistent-dir-for-e2e-test'
        )
        is None
    )


def test_spawn_detached_does_not_hold_the_log_descriptor_open(tmp_path):
    """The parent's handle is closed; the child owns its own.

    Left open, the file would stay held for the lifetime of the harness -- and on
    the fallback path the harness can then run for another twenty minutes.
    """
    fake = mock.Mock(pid=7)
    with mock.patch.object(e2e.subprocess, 'Popen', return_value=fake):
        with mock.patch('builtins.open', mock.mock_open()) as opened:
            e2e.spawn_detached_cluster_deletion('us-west-2', 'c', log_dir=str(tmp_path))

    opened.return_value.close.assert_called_once()


# --- The RDS Data API array-slice limitation --------------------------------
# Observed on Aurora PG 17.5: the Data API's own parameter scanner reads the
# colon in an array slice as a named placeholder and rejects the call with
# "Cannot find parameter: 2" before PostgreSQL sees it. Our two layers handle it
# correctly, so the statements live in a separate corpus that is recorded N/A on
# RDS_API. These tests pin the split so the slice cases cannot drift back into
# the corpus that runs on every connection method.


def test_slice_reads_are_held_separately_from_the_general_parameterized_corpus():
    """A slice case in the shared corpus would fail every RDS_API run."""
    general = [sql for sql, _ in e2e.PARAMETERIZED_READ_QUERIES]
    assert e2e.PARAMETERIZED_SLICE_READS, 'the slice corpus must not be empty'
    for sql in general:
        assert '[1:' not in sql and '[2:' not in sql, (
            f'array slice found in PARAMETERIZED_READ_QUERIES, which runs on RDS_API: {sql}'
        )


def test_every_slice_read_actually_contains_a_slice_and_a_placeholder():
    """Both halves are needed, or the case does not exercise the interaction."""
    for sql, params in e2e.PARAMETERIZED_SLICE_READS:
        assert '[' in sql and ':' in sql
        assert params, f'{sql} needs at least one bound parameter'
        # A numeric slice bound is exactly the shape the Data API misreads.
        assert re.search(r'\[\d+:\d+\]', sql), f'{sql} has no numeric slice bound'


def test_our_own_rewrites_leave_slice_reads_intact():
    """The guard and the psycopg executor must both pass a slice through unchanged.

    This is the half we own. The Data API's behavior is AWS's, but a regression in
    our shared pattern would break the PG-Wire paths too, and this catches that
    without a cluster.
    """
    for sql, _ in e2e.PARAMETERIZED_SLICE_READS:
        assert to_parse_placeholders(sql).count('$1') == 1, sql
        rewritten = to_psycopg_placeholders(sql)
        assert '[1:2]' in rewritten or '[2:3]' in rewritten, rewritten
        assert_executable(sql, allow_write_query=False)


def test_data_api_limitation_reason_is_stated_and_attributed():
    """An N/A needs a reason a reader can act on, and this one is not our bug."""
    reason = e2e.DATA_API_SLICE_LIMITATION
    assert 'Cannot find parameter' in reason
    assert 'unrelated to the MCP server' in reason
