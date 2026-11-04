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

"""Tests for review cluster executor."""

import pytest
import sqlglot
from awslabs.redshift_mcp_server.models import RedshiftCluster
from awslabs.redshift_mcp_server.review.definitions import SIGNAL_EVALUATION_SQL
from awslabs.redshift_mcp_server.review.executor import review_cluster
from helpers import _fake_cluster
from mcp.server.mcpserver.exceptions import ToolError
from sqlglot import exp
from unittest.mock import AsyncMock


@pytest.mark.asyncio
@pytest.mark.parametrize('cluster_type', ['provisioned', 'serverless'])
async def test_a_review_runs_every_query_scoped_to_all(cluster_type):
    """Seven of the twelve queries apply to every cluster; skipped, the review looked complete."""
    scoped_to_all = {name for name, scope, _ in SIGNAL_EVALUATION_SQL if scope == 'all'}
    assert scoped_to_all

    async def run(**kwargs):
        return {'rows': []}

    async def resolve(identifier, requested_type, fresh=False):
        assert requested_type == cluster_type
        return _fake_cluster(type=cluster_type)

    result = await review_cluster('c', cluster_type, run, resolve)

    assert scoped_to_all <= set(result.queries_executed)


def _terms(condition: exp.Expression):
    """Yield the terms a WHERE or HAVING joins with AND and OR, looking through NOT."""
    while isinstance(condition, (exp.Paren, exp.Not, exp.Escape)):
        condition = condition.this
    if isinstance(condition, exp.Connector):
        yield from _terms(condition.left)
        yield from _terms(condition.right)
    else:
        yield condition


@pytest.mark.parametrize(
    'sql',
    [sql for _, _, sql in SIGNAL_EVALUATION_SQL],
    ids=[name for name, _, _ in SIGNAL_EVALUATION_SQL],
)
def test_every_filter_term_is_a_condition(sql):
    """Redshift reads a number used as a filter as true whenever it is nonzero.

    So a count meant as `> 0` tests `<> 0`. REC_004 filtered on a count that way, and was right
    only because another term excluded its one negative case.
    """
    tree = sqlglot.parse_one(sql.format(node_type='ra3.xlplus'), read='redshift')
    # A bare command is sqlglot's fallback for SQL it cannot parse, and has no clauses to check.
    assert not isinstance(tree, exp.Command)

    terms = [
        term
        for clause in (*tree.find_all(exp.Where), *tree.find_all(exp.Having))
        for term in _terms(clause.this)
    ]

    assert [
        term.sql(dialect='redshift')
        for term in terms
        if not isinstance(term, (exp.Predicate, exp.Boolean))
    ] == []


def _make_response(rows: list[tuple]) -> dict:
    """Build a mock execute_query response with (count, rec_id[, signal]) rows."""
    built = [list(r) for r in rows]
    has_label = any(len(r) > 2 for r in built)
    return {
        'rows': built,
        'columns': ['count', 'rec_id'] + (['signal'] if has_label else []),
        'row_count': len(built),
    }


def _make_empty_response() -> dict:
    """Build a mock execute_query response with no rows."""
    return {'rows': [], 'columns': ['count', 'rec_id'], 'row_count': 0}


def _cluster(
    identifier='test-cluster',
    cluster_type='provisioned',
    node_type: str | None = 'ra3.xlplus',
):
    """Build a RedshiftCluster model for resolve_cluster mocks."""
    return RedshiftCluster.model_validate(
        {
            'identifier': identifier,
            'type': cluster_type,
            'status': 'available',
            'database_name': 'dev',
            'node_type': None if cluster_type == 'serverless' else node_type,
        }
    )


def _make_resolve_cluster(cluster_type='provisioned', node_type: str | None = 'ra3.xlplus'):
    """Build a mock resolve_cluster returning one cluster."""
    return AsyncMock(return_value=_cluster(cluster_type=cluster_type, node_type=node_type))


def _make_sql_recorder():
    """Build an execute_query mock that records the SQL sent for each query name.

    Every diagnostic query starts with a '-- <QueryName>' comment line, which is used
    to key the recorded SQL.

    Returns:
        A (execute_query_func, recorded) tuple, where recorded maps query name to SQL.
    """
    recorded: dict[str, str] = {}

    async def _execute(cluster_identifier, database_name, sql, enforce_read_only=True, **_):
        recorded[sql.splitlines()[0].removeprefix('--').strip()] = sql
        return _make_empty_response()

    return _execute, recorded


# ---------------------------------------------------------------------------
# Serverless exclusion
# ---------------------------------------------------------------------------


class TestServerlessExclusion:
    """Verify provisioned-only queries excluded for serverless clusters."""

    @pytest.mark.asyncio
    async def test_provisioned_only_queries_excluded_for_serverless(self):
        """When cluster is serverless, NodeDetails and WLMConfig are excluded."""
        execute_query_func = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())
        resolve_cluster_func = AsyncMock(return_value=_cluster(cluster_type='serverless'))

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='serverless',
            execute_query_func=execute_query_func,
            resolve_cluster_func=resolve_cluster_func,
        )

        assert 'NodeDetails' not in result.queries_executed
        assert 'WLMConfig' not in result.queries_executed
        assert 'WorkloadEvaluation' not in result.queries_executed

    @pytest.mark.asyncio
    async def test_provisioned_queries_included_for_provisioned(self):
        """For provisioned clusters, all queries including provisioned-only are executed."""
        execute_query_func = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())
        resolve_cluster_func = AsyncMock(return_value=_cluster())

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=resolve_cluster_func,
        )

        assert 'NodeDetails' in result.queries_executed
        assert 'WLMConfig' in result.queries_executed

    @pytest.mark.asyncio
    async def test_serverless_only_queries_excluded_for_provisioned(self):
        """For provisioned clusters, serverless-only queries are excluded."""
        execute_query_func = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())
        resolve_cluster_func = AsyncMock(return_value=_cluster())

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=resolve_cluster_func,
        )

        assert 'ServerlessScaling' not in result.queries_executed


# ---------------------------------------------------------------------------
# Identifier handling
# ---------------------------------------------------------------------------


class TestClusterType:
    """The type the caller gives reaches the resolver and every query."""

    @pytest.mark.asyncio
    async def test_a_cluster_type_is_reviewed_as_that_type(self):
        """With cluster_type=serverless, the review scopes to the workgroup of that name."""
        execute_query_func, recorded = _make_sql_recorder()
        resolve_cluster_func = AsyncMock(return_value=_cluster(cluster_type='serverless'))

        result = await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            resolve_cluster_func=resolve_cluster_func,
            cluster_type='serverless',
        )

        # The type reaches the resolver, and the serverless scope is what ran. Fresh,
        # because the node type is read: from the stored discovery after a resize, the node-type
        # signals were evaluated for the node type the cluster had before it.
        resolve_cluster_func.assert_awaited_once_with('test-cluster', 'serverless', fresh=True)
        assert 'ServerlessScaling' in result.queries_executed
        assert 'NodeDetails' not in result.queries_executed
        assert recorded

    @pytest.mark.asyncio
    @pytest.mark.parametrize('cluster_type', ['provisioned', 'serverless'])
    async def test_every_query_carries_the_given_type(self, cluster_type):
        """Each carries the review's identifier and type, so none reaches another warehouse."""
        targets: list[tuple[str, str]] = []

        async def _execute(
            cluster_identifier, cluster_type, database_name, sql, enforce_read_only
        ):
            targets.append((cluster_identifier, cluster_type))
            return _make_empty_response()

        await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type=cluster_type,
            execute_query_func=_execute,
            resolve_cluster_func=_make_resolve_cluster(cluster_type=cluster_type),
        )

        assert targets
        assert set(targets) == {('test-cluster', cluster_type)}


# ---------------------------------------------------------------------------
# Signal triggering
# ---------------------------------------------------------------------------


class TestSignalTriggered:
    """Findings are created when count > 0."""

    @pytest.mark.asyncio
    async def test_finding_created_when_count_positive(self):
        """Rows with count > 0 produce findings."""
        execute_query_func = AsyncMock(
            side_effect=lambda *a, **kw: _make_response([(5, 'REC_001')])
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
        )

        assert len(result.findings) > 0
        rec_ids = [f.recommendation_ids[0] for f in result.findings]
        assert 'REC_001' in rec_ids
        # Every finding carries a non-empty unit for its affected_row_count.
        assert all(f.unit for f in result.findings)

    @pytest.mark.asyncio
    async def test_no_findings_when_all_counts_zero(self):
        """Rows with count == 0 do not produce findings."""
        execute_query_func = AsyncMock(
            side_effect=lambda *a, **kw: _make_response([(0, 'REC_001')])
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
        )

        assert len(result.findings) == 0


# ---------------------------------------------------------------------------
# Finding deduplication
# ---------------------------------------------------------------------------


class TestPerBranchFindings:
    """Branches that share a recommendation stay as distinct findings."""

    @pytest.mark.asyncio
    async def test_distinct_branch_labels_are_not_collapsed(self):
        """Same rec from two different -- Signal branches yields two findings, one rec."""
        execute_query_func = AsyncMock(
            side_effect=lambda *a, **kw: _make_response(
                [(3, 'REC_001', 'signal A'), (5, 'REC_001', 'signal B')]
            )
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
        )

        rec1 = [f for f in result.findings if f.recommendation_ids == ['REC_001']]
        # Both branch labels are retained (not collapsed into one finding).
        assert {'signal A', 'signal B'} <= {f.signal_name for f in rec1}
        # Per-branch counts are preserved (no max-collapse): both 3 and 5 present.
        assert {3, 5} <= {f.affected_row_count for f in rec1}
        # signal_name is the branch label, distinct from the section (query name).
        assert all(f.signal_name != f.section for f in rec1)
        # The recommendation is still deduplicated to a single REC_001.
        assert [r.id for r in result.recommendations] == ['REC_001']


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


class TestErrorPropagation:
    """Errors during query execution propagate to the caller."""

    @pytest.mark.asyncio
    async def test_cluster_not_found_raises(self):
        """A nonexistent cluster raises early with a clear message."""
        execute_query_func = AsyncMock()
        resolve_cluster_func = AsyncMock(
            side_effect=ToolError('Cluster missing-cluster not found.')
        )

        with pytest.raises(ToolError, match='Cluster missing-cluster not found'):
            await review_cluster(
                cluster_identifier='missing-cluster',
                cluster_type='provisioned',
                execute_query_func=execute_query_func,
                resolve_cluster_func=resolve_cluster_func,
            )

        execute_query_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_denied_listing_cause_reaches_the_caller(self):
        """The resolver's account of a denied listing is not replaced by a bare not found."""
        execute_query_func = AsyncMock()
        resolve_cluster_func = AsyncMock(
            side_effect=ToolError(
                'Cluster missing-cluster not found. Listing serverless clusters was denied, so '
                'any of that type is absent here and from list_clusters; grant the listing '
                'permission to address it.'
            )
        )

        with pytest.raises(ToolError, match='Listing serverless clusters was denied'):
            await review_cluster(
                cluster_identifier='missing-cluster',
                cluster_type='serverless',
                execute_query_func=execute_query_func,
                resolve_cluster_func=resolve_cluster_func,
            )

        resolve_cluster_func.assert_awaited_once_with('missing-cluster', 'serverless', fresh=True)
        execute_query_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_failure_aborts_review(self):
        """Any query failure aborts the entire review."""
        call_count = [0]

        async def _side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError('table does not exist')
            return _make_empty_response()

        execute_query_func = AsyncMock(side_effect=_side_effect)

        with pytest.raises(RuntimeError, match='table does not exist'):
            await review_cluster(
                cluster_identifier='test-cluster',
                cluster_type='provisioned',
                execute_query_func=execute_query_func,
                resolve_cluster_func=_make_resolve_cluster(),
            )

    @pytest.mark.asyncio
    async def test_permission_denied_aborts_review(self):
        """A permission denied error aborts with the grant that resolves it."""
        execute_query_func = AsyncMock(
            side_effect=RuntimeError('permission denied for relation sys_auto_table_optimization')
        )

        with pytest.raises(ToolError, match='Review requires superuser or sys:monitor access'):
            await review_cluster(
                cluster_identifier='test-cluster',
                cluster_type='provisioned',
                execute_query_func=execute_query_func,
                resolve_cluster_func=_make_resolve_cluster(),
            )


# ---------------------------------------------------------------------------
# Recommendation deduplication
# ---------------------------------------------------------------------------


class TestRecommendationDeduplication:
    """Recommendations are deduplicated across findings."""

    @pytest.mark.asyncio
    async def test_duplicate_rec_ids_deduplicated(self):
        """Same rec ID from multiple queries produces one recommendation."""
        execute_query_func = AsyncMock(
            side_effect=lambda *a, **kw: _make_response([(3, 'REC_003'), (2, 'REC_003')])
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
        )

        rec_ids = [r.id for r in result.recommendations]
        assert rec_ids.count('REC_003') == 1

    @pytest.mark.asyncio
    async def test_one_signal_with_two_recommendations_is_one_finding(self):
        """Several branches share a signal label, so len(findings) would overcount problems.

        `definitions.py` emits one row per recommendation, and a signal that maps to two of
        them appears twice under the same label with the same count. The caller is told to
        count problems as len(findings), so those two rows have to become one finding.
        """
        rows = [
            (4, 'REC_009', 'long running queries using Nested Loop Joins'),
            (4, 'REC_019', 'long running queries using Nested Loop Joins'),
        ]
        first = True

        async def execute_query_func(*_args, **_kwargs):
            nonlocal first
            if first:
                first = False
                return _make_response(rows)
            return _make_empty_response()

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
        )

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.signal_name == 'long running queries using Nested Loop Joins'
        # Both recommendations are carried, and the count is not doubled by merging them.
        assert finding.recommendation_ids == ['REC_009', 'REC_019']
        assert finding.affected_row_count == 4
        assert sorted(r.id for r in result.recommendations) == ['REC_009', 'REC_019']


# ---------------------------------------------------------------------------
# Progress reporting
# ---------------------------------------------------------------------------


class TestProgressReporting:
    """progress_reporter_func is called for each query."""

    @pytest.mark.asyncio
    async def test_progress_reporter_func_called(self):
        """progress_reporter_func receives (current, total) after each query."""
        execute_query_func = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())
        progress_calls = []

        async def mock_progress(current, total):
            progress_calls.append((current, total))

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
            progress_reporter_func=mock_progress,
        )

        # Progress is per query, and a query carries several signals, so the tick count is the
        # number of queries and not signals_evaluated.
        total = len(result.queries_executed)
        assert len(progress_calls) == total
        assert progress_calls[-1] == (total, total)


# ---------------------------------------------------------------------------
# Full pipeline end-to-end
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """End-to-end pipeline test with mocked Data API."""

    @pytest.mark.asyncio
    async def test_full_pipeline_returns_complete_review_result(self):
        """Full pipeline produces a complete ReviewResult."""
        execute_query_func = AsyncMock(
            side_effect=lambda *a, **kw: _make_response([(1, 'REC_007'), (0, 'REC_008')])
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
        )

        assert result.signals_evaluated > 0
        assert len(result.queries_executed) > 0
        # REC_007 triggered, REC_008 not
        rec_ids = [r.id for r in result.recommendations]
        assert 'REC_007' in rec_ids
        assert 'REC_008' not in rec_ids

    @pytest.mark.asyncio
    async def test_empty_records_returns_no_findings(self):
        """Empty Records in response produces no findings."""
        execute_query_func = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
        )

        assert len(result.findings) == 0
        assert len(result.recommendations) == 0

    @pytest.mark.asyncio
    async def test_missing_recommendation_id_skipped(self):
        """Recommendation IDs not in RECOMMENDATIONS are silently skipped."""
        execute_query_func = AsyncMock(
            side_effect=lambda *a, **kw: _make_response([(5, 'NONEXISTENT')])
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
        )

        assert len(result.findings) > 0
        assert len(result.recommendations) == 0


# ---------------------------------------------------------------------------
# Node type substitution
# ---------------------------------------------------------------------------


class TestNodeTypeSubstitution:
    """Verify the cluster's real node type reaches the diagnostic SQL."""

    @pytest.mark.asyncio
    async def test_known_node_type_is_inlined_in_sql(self):
        """A provisioned cluster's reported node type is inlined into NodeDetails."""
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(node_type='ra3.xlplus'),
        )

        assert "'ra3.xlplus'::text AS node_type" in recorded['NodeDetails']

    @pytest.mark.asyncio
    async def test_missing_node_type_falls_back_in_sql(self):
        """A provisioned cluster without a node type inlines the unknown sentinel."""
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(node_type=None),
        )

        assert "'unknown'::text AS node_type" in recorded['NodeDetails']

    @pytest.mark.asyncio
    async def test_serverless_review_executes_no_placeholder_query(self):
        """Serverless workgroups have no node type and run no query needing one."""
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='serverless',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(cluster_type='serverless'),
        )

        assert 'NodeDetails' not in recorded


class TestSignalsEvaluatedCountsSignals:
    """`signals_evaluated` has to mean signals, or it cannot be read against findings."""

    @pytest.mark.asyncio
    async def test_a_label_repeated_to_carry_more_recommendations_counts_once(self):
        """Several definitions repeat one predicate under one label to attach more than one.

        Counted per returned row, those repeats inflate the number: the shipped definitions give
        55 rows against 48 signals on a provisioned cluster, and 37 against 32 on a workgroup. A
        caller comparing findings to it would read a cluster as healthier than it is.
        """
        execute_query_func = AsyncMock(
            return_value=_make_response(
                [
                    (1, 'REC_016', 'high count of WLM queuing'),
                    (1, 'REC_017', 'high count of WLM queuing'),
                    (1, 'REC_022', 'high count of WLM queuing'),
                    (0, 'REC_027', 'high concurrency scaling usage'),
                ]
            )
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
        )

        # Four rows per query, two distinct signals, across every query that ran.
        assert result.signals_evaluated == 2 * len(result.queries_executed)
        # And the repeats became one finding carrying all three recommendations.
        wlm = [f for f in result.findings if f.signal_name == 'high count of WLM queuing']
        assert wlm, 'the triggered signal must still be reported'
        assert wlm[0].recommendation_ids == ['REC_016', 'REC_017', 'REC_022']

    @pytest.mark.asyncio
    async def test_a_signal_that_did_not_trigger_still_counts_as_evaluated(self):
        """Its predicate ran, which is what the number reports."""
        execute_query_func = AsyncMock(
            return_value=_make_response([(0, 'REC_004', 'nothing to report')])
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            cluster_type='provisioned',
            execute_query_func=execute_query_func,
            resolve_cluster_func=_make_resolve_cluster(),
        )

        assert result.signals_evaluated == len(result.queries_executed)
        assert result.findings == []
