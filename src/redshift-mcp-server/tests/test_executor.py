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
)
from awslabs.redshift_mcp_server.review.executor import review_cluster
from unittest.mock import AsyncMock


def _make_response(rows: list[tuple[int, str]]) -> dict:
    """Build a mock execute_query response with (count, rec_id) rows."""
    return {
        'rows': [[count, rec_id] for count, rec_id in rows],
        'columns': ['count', 'rec_id'],
        'row_count': len(rows),
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
    async def test_failed_query_raises(self):
        """A failing query propagates the exception."""
        execute_query_func = AsyncMock(side_effect=RuntimeError('Data API timeout'))

        with pytest.raises(RuntimeError, match='Data API timeout'):
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

    def test_recommendations_not_empty(self):
        """RECOMMENDATIONS dict is not empty."""
        assert len(RECOMMENDATIONS) > 0

    def test_provisioned_only_flags(self):
        """NodeDetails and WLMConfig are marked provisioned-only."""
        provisioned = {name for name, ct, _ in SIGNAL_EVALUATION_SQL if ct == 'provisioned'}
        assert 'NodeDetails' in provisioned
        assert 'WLMConfig' in provisioned
