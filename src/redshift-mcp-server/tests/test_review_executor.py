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
from awslabs.redshift_mcp_server.review.definitions import (
    RECOMMENDATIONS,
    SIGNAL_EVALUATION_SQL,
    SIGNAL_UNITS,
)
from awslabs.redshift_mcp_server.review.executor import review_cluster
from unittest.mock import AsyncMock


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


def _make_discover_clusters(cluster_type='provisioned'):
    """Build a mock discover_clusters returning a single cluster."""
    return AsyncMock(return_value=[{'identifier': 'test-cluster', 'type': cluster_type}])


# ---------------------------------------------------------------------------
# Serverless exclusion
# ---------------------------------------------------------------------------


class TestServerlessExclusion:
    """Verify provisioned-only queries excluded for serverless clusters."""

    @pytest.mark.asyncio
    async def test_provisioned_only_queries_excluded_for_serverless(self):
        """When cluster is serverless, NodeDetails and WLMConfig are excluded."""
        execute_query_func = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())
        discover_clusters_func = AsyncMock(
            return_value=[
                {'identifier': 'test-cluster', 'type': 'serverless'},
            ]
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=discover_clusters_func,
        )

        assert 'NodeDetails' not in result.queries_executed
        assert 'WLMConfig' not in result.queries_executed
        assert 'WorkloadEvaluation' not in result.queries_executed

    @pytest.mark.asyncio
    async def test_provisioned_queries_included_for_provisioned(self):
        """For provisioned clusters, all queries including provisioned-only are executed."""
        execute_query_func = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())
        discover_clusters_func = AsyncMock(
            return_value=[
                {'identifier': 'test-cluster', 'type': 'provisioned'},
            ]
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=discover_clusters_func,
        )

        assert 'NodeDetails' in result.queries_executed
        assert 'WLMConfig' in result.queries_executed

    @pytest.mark.asyncio
    async def test_serverless_only_queries_excluded_for_provisioned(self):
        """For provisioned clusters, serverless-only queries are excluded."""
        execute_query_func = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())
        discover_clusters_func = AsyncMock(
            return_value=[
                {'identifier': 'test-cluster', 'type': 'provisioned'},
            ]
        )

        result = await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=discover_clusters_func,
        )

        assert 'ServerlessScaling' not in result.queries_executed


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
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(),
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
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(),
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
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(),
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
        discover_clusters_func = AsyncMock(
            return_value=[
                {'identifier': 'other-cluster', 'type': 'provisioned'},
            ]
        )

        with pytest.raises(Exception, match='Cluster missing-cluster not found'):
            await review_cluster(
                cluster_identifier='missing-cluster',
                execute_query_func=execute_query_func,
                discover_clusters_func=discover_clusters_func,
            )

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
                execute_query_func=execute_query_func,
                discover_clusters_func=_make_discover_clusters(),
            )

    @pytest.mark.asyncio
    async def test_permission_denied_aborts_review(self):
        """A permission denied error aborts with a helpful superuser message."""
        execute_query_func = AsyncMock(
            side_effect=RuntimeError('permission denied for relation sys_auto_table_optimization')
        )

        with pytest.raises(Exception, match='Review requires superuser'):
            await review_cluster(
                cluster_identifier='test-cluster',
                execute_query_func=execute_query_func,
                discover_clusters_func=_make_discover_clusters(),
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
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(),
        )

        rec_ids = [r.id for r in result.recommendations]
        assert rec_ids.count('REC_003') == 1


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
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(),
            progress_reporter_func=mock_progress,
        )

        total = result.signals_evaluated
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
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(),
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
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(),
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
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(),
        )

        assert len(result.findings) > 0
        assert len(result.recommendations) == 0


# ---------------------------------------------------------------------------
# Review queries constants validation
# ---------------------------------------------------------------------------


class TestReviewQueriesConstants:
    """Validate the SIGNAL_EVALUATION_SQL and RECOMMENDATIONS constants."""

    def test_all_queries_have_sql(self):
        """Every entry in SIGNAL_EVALUATION_SQL has non-empty SQL."""
        for name, cluster_type, sql in SIGNAL_EVALUATION_SQL:
            assert sql.strip(), f'{name} has empty SQL'

    def test_every_query_has_a_unit(self):
        """Every query in SIGNAL_EVALUATION_SQL maps to a non-empty unit."""
        for name, _cluster_type, _sql in SIGNAL_EVALUATION_SQL:
            assert SIGNAL_UNITS.get(name), f'{name} is missing a unit in SIGNAL_UNITS'

    def test_every_branch_emits_a_signal_label(self):
        """Every rec branch selects a 3rd literal (its -- Signal label)."""
        import re

        no_label = re.compile(r"SELECT count\(\*\),\s*'REC_\d+'(?!\s*,)")
        for name, _ct, sql in SIGNAL_EVALUATION_SQL:
            assert not no_label.findall(sql), f'{name} has a branch without a label column'

    def test_branch_rec_label_pairs_unique_per_query(self):
        """Within a query, no two branches share the same (rec_id, label)."""
        import re

        pair = re.compile(r"SELECT count\(\*\),\s*'(REC_\d+)',\s*'((?:[^']|'')*)'")
        for name, _ct, sql in SIGNAL_EVALUATION_SQL:
            pairs = pair.findall(sql)
            assert len(pairs) == len(set(pairs)), (
                f'{name} has duplicate (rec, label) branches: {pairs}'
            )

    def test_recommendations_not_empty(self):
        """RECOMMENDATIONS dict is not empty."""
        assert len(RECOMMENDATIONS) > 0

    def test_provisioned_only_flags(self):
        """NodeDetails and WLMConfig are marked provisioned-only."""
        provisioned = {name for name, ct, _ in SIGNAL_EVALUATION_SQL if ct == 'provisioned'}
        assert 'NodeDetails' in provisioned
        assert 'WLMConfig' in provisioned
        assert 'WorkloadEvaluation' in provisioned
