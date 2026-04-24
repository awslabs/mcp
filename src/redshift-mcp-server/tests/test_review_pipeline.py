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

"""Tests for review pipeline orchestration."""

import pytest
from awslabs.redshift_mcp_server.review.review_pipeline import run_review
from awslabs.redshift_mcp_server.review.review_queries import (
    RECOMMENDATIONS,
    REVIEW_QUERIES,
)
from unittest.mock import AsyncMock


def _make_response(rows: list[tuple[int, str]]) -> tuple[dict, str]:
    """Build a mock Data API response with (count, rec_id) rows."""
    records = [[{'longValue': count}, {'stringValue': rec_id}] for count, rec_id in rows]
    return ({'Records': records}, 'query-id')


def _make_empty_response() -> tuple[dict, str]:
    """Build a mock Data API response with no records."""
    return ({'Records': []}, 'query-id')


# ---------------------------------------------------------------------------
# Serverless exclusion
# ---------------------------------------------------------------------------


class TestServerlessExclusion:
    """Verify provisioned-only queries excluded when workgroup is set."""

    @pytest.mark.asyncio
    async def test_provisioned_only_queries_excluded_with_workgroup(self):
        """When workgroup is set, NodeDetails and WLMConfig are excluded."""
        execute_fn = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            execute_fn=execute_fn,
            workgroup='my-workgroup',
        )

        assert 'NodeDetails' not in result.queries_executed
        assert 'WLMConfig' not in result.queries_executed

    @pytest.mark.asyncio
    async def test_provisioned_queries_included_without_workgroup(self):
        """Without workgroup, all queries including provisioned-only are executed."""
        execute_fn = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            execute_fn=execute_fn,
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
        execute_fn = AsyncMock(side_effect=lambda *a, **kw: _make_response([(5, 'REC_001')]))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            execute_fn=execute_fn,
        )

        assert len(result.findings) > 0
        rec_ids = [f.recommendation_ids[0] for f in result.findings]
        assert 'REC_001' in rec_ids

    @pytest.mark.asyncio
    async def test_no_findings_when_all_counts_zero(self):
        """Rows with count == 0 do not produce findings."""
        execute_fn = AsyncMock(side_effect=lambda *a, **kw: _make_response([(0, 'REC_001')]))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            execute_fn=execute_fn,
        )

        assert len(result.findings) == 0


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


class TestErrorPropagation:
    """Errors during query execution propagate to the caller."""

    @pytest.mark.asyncio
    async def test_failed_query_raises(self):
        """A failing query propagates the exception."""
        execute_fn = AsyncMock(side_effect=RuntimeError('Data API timeout'))

        with pytest.raises(RuntimeError, match='Data API timeout'):
            await run_review(
                cluster_identifier='test-cluster',
                database='dev',
                execute_fn=execute_fn,
            )


# ---------------------------------------------------------------------------
# Recommendation deduplication
# ---------------------------------------------------------------------------


class TestRecommendationDeduplication:
    """Recommendations are deduplicated across findings."""

    @pytest.mark.asyncio
    async def test_duplicate_rec_ids_deduplicated(self):
        """Same rec ID from multiple queries produces one recommendation."""
        execute_fn = AsyncMock(
            side_effect=lambda *a, **kw: _make_response([(3, 'REC_003'), (2, 'REC_003')])
        )

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            execute_fn=execute_fn,
        )

        rec_ids = [r.id for r in result.recommendations]
        assert rec_ids.count('REC_003') == 1


# ---------------------------------------------------------------------------
# Progress reporting
# ---------------------------------------------------------------------------


class TestProgressReporting:
    """progress_fn is called for each query."""

    @pytest.mark.asyncio
    async def test_progress_fn_called(self):
        """progress_fn receives (current, total) after each query."""
        execute_fn = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())
        progress_calls = []

        async def mock_progress(current, total):
            progress_calls.append((current, total))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            execute_fn=execute_fn,
            progress_fn=mock_progress,
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
        execute_fn = AsyncMock(
            side_effect=lambda *a, **kw: _make_response([(1, 'REC_007'), (0, 'REC_008')])
        )

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            execute_fn=execute_fn,
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
        execute_fn = AsyncMock(side_effect=lambda *a, **kw: _make_empty_response())

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            execute_fn=execute_fn,
        )

        assert len(result.findings) == 0
        assert len(result.recommendations) == 0

    @pytest.mark.asyncio
    async def test_missing_recommendation_id_skipped(self):
        """Recommendation IDs not in RECOMMENDATIONS are silently skipped."""
        execute_fn = AsyncMock(side_effect=lambda *a, **kw: _make_response([(5, 'NONEXISTENT')]))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            execute_fn=execute_fn,
        )

        assert len(result.findings) > 0
        assert len(result.recommendations) == 0


# ---------------------------------------------------------------------------
# Review queries constants validation
# ---------------------------------------------------------------------------


class TestReviewQueriesConstants:
    """Validate the REVIEW_QUERIES and RECOMMENDATIONS constants."""

    def test_all_queries_have_sql(self):
        """Every entry in REVIEW_QUERIES has non-empty SQL."""
        for name, sql, _ in REVIEW_QUERIES:
            assert sql.strip(), f'{name} has empty SQL'

    def test_recommendations_not_empty(self):
        """RECOMMENDATIONS dict is not empty."""
        assert len(RECOMMENDATIONS) > 0

    def test_provisioned_only_flags(self):
        """NodeDetails and WLMConfig are marked provisioned-only."""
        provisioned = {name for name, _, flag in REVIEW_QUERIES if flag}
        assert 'NodeDetails' in provisioned
        assert 'WLMConfig' in provisioned
