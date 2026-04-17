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
from awslabs.redshift_mcp_server.review.config_loader import (
    QueryEntry,
    RecommendationEntry,
    SectionEntry,
)
from awslabs.redshift_mcp_server.review.review_pipeline import run_review
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Minimal config fixtures
# ---------------------------------------------------------------------------

QUERIES_CONFIG: dict[str, QueryEntry] = {
    'NodeDetails': {
        'SQL': 'SELECT node_type, storage_used_gb, storage_utilization_pct FROM stv_node_storage'
    },
    'WLMConfig': {'SQL': 'SELECT * FROM stv_wlm_service_class_config'},
    'UsagePattern': {'SQL': 'SELECT * FROM usage_pattern'},
    'TableInfo': {'SQL': 'SELECT * FROM svv_table_info'},
    'AlterTableRecommendations': {'SQL': 'SELECT * FROM svv_alter_table_recommendations'},
    'MaterializedView': {'SQL': 'SELECT * FROM stv_mv_info'},
    'Top50QueriesByRunTime': {'SQL': 'SELECT * FROM top_queries'},
    'CopyPerformance': {'SQL': 'SELECT * FROM copy_perf'},
    'ExtQueryPerformance': {'SQL': 'SELECT * FROM ext_query_perf'},
    'DataShareProducerObject': {'SQL': 'SELECT * FROM datashare_producer'},
    'DataShareConsumerUsage': {'SQL': 'SELECT * FROM datashare_consumer'},
    'ATOWorkerActions': {'SQL': 'SELECT * FROM ato_worker'},
    'WorkloadEvaluation': {'SQL': 'SELECT * FROM workload_eval'},
}

SIGNALS_CONFIG_SIMPLE: dict[str, SectionEntry] = {
    'NodeDetails': {
        'Signals': [
            {
                'Signal': 'test signal A',
                'Criteria': 'col > 10',
                'Recommendation': ['REC-001'],
            },
        ]
    },
}

RECOMMENDATIONS_CONFIG: dict[str, RecommendationEntry] = {
    'REC-001': {
        'text': 'Rec 1 text',
        'description': 'Rec 1 desc',
        'effort': 'Large',
        'documentation_links': ['https://example.com/1'],
    },
    'REC-002': {
        'text': 'Rec 2 text',
        'description': 'Rec 2 desc',
        'effort': 'Small',
        'documentation_links': ['https://example.com/2'],
    },
    'REC-003': {
        'text': 'Rec 3 text',
        'description': 'Rec 3 desc',
        'effort': 'Medium',
        'documentation_links': ['https://example.com/3'],
    },
}


def _make_count_response(count: int) -> tuple[dict, str]:
    """Build a mock Data API response for a COUNT(*) query."""
    return ({'Records': [[{'longValue': count}]]}, f'query-id-{count}')


# ---------------------------------------------------------------------------
# Serverless exclusion
# ---------------------------------------------------------------------------


class TestServerlessExclusion:
    """Verify WLMConfig/NodeDetails excluded when workgroup is set."""

    @pytest.mark.asyncio
    async def test_provisioned_only_queries_excluded_with_workgroup(self):
        """When workgroup is set, WLMConfig and NodeDetails are excluded."""
        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {
                        'Signal': 'node signal',
                        'Criteria': 'x > 0',
                        'Recommendation': ['REC-001'],
                    }
                ]
            },
            'WLMConfig': {
                'Signals': [
                    {
                        'Signal': 'wlm signal',
                        'Criteria': 'y > 0',
                        'Recommendation': ['REC-002'],
                    }
                ]
            },
            'UsagePattern': {
                'Signals': [
                    {
                        'Signal': 'usage signal',
                        'Criteria': 'z > 0',
                        'Recommendation': ['REC-003'],
                    }
                ]
            },
        }

        execute_fn = AsyncMock(side_effect=lambda *args, **kwargs: _make_count_response(0))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=signals_config,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=execute_fn,
            workgroup='my-workgroup',
        )

        # NodeDetails and WLMConfig should not appear in queries_executed
        assert 'NodeDetails' not in result.queries_executed
        assert 'WLMConfig' not in result.queries_executed

        # Verify no SQL referencing NodeDetails or WLMConfig was executed
        for call in execute_fn.call_args_list:
            sql = call.args[2]
            assert 'WITH NodeDetails AS (' not in sql
            assert 'WITH WLMConfig AS (' not in sql


# ---------------------------------------------------------------------------
# Property 3: Signal triggered if and only if count > 0
# ---------------------------------------------------------------------------


class TestSignalTriggered:
    """Property 3: Signal triggered if and only if count > 0."""

    @pytest.mark.asyncio
    async def test_signal_triggered_when_count_positive(self):
        """Signal with count > 0 appears in findings."""
        execute_fn = AsyncMock(side_effect=lambda *args, **kwargs: _make_count_response(5))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=SIGNALS_CONFIG_SIMPLE,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=execute_fn,
        )

        assert len(result.findings) == 1
        assert result.findings[0].signal_name == 'test signal A'
        assert result.findings[0].affected_row_count == 5

    @pytest.mark.asyncio
    async def test_signal_not_triggered_when_count_zero(self):
        """Signal with count == 0 does not appear in findings."""
        execute_fn = AsyncMock(side_effect=lambda *args, **kwargs: _make_count_response(0))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=SIGNALS_CONFIG_SIMPLE,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=execute_fn,
        )

        assert len(result.findings) == 0


# ---------------------------------------------------------------------------
# Property 10: Error isolation — failed signal does not block others
# ---------------------------------------------------------------------------


class TestErrorIsolation:
    """Property 10: Failed signal does not block others."""

    @pytest.mark.asyncio
    async def test_failed_signal_does_not_block_others(self):
        """One failing signal doesn't prevent other signals from executing."""
        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {
                        'Signal': 'failing signal',
                        'Criteria': 'bad_col > 0',
                        'Recommendation': ['REC-001'],
                    },
                    {
                        'Signal': 'passing signal',
                        'Criteria': 'good_col > 0',
                        'Recommendation': ['REC-002'],
                    },
                ]
            },
        }

        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # First call: first signal fails
            if call_count == 1:
                raise RuntimeError('Simulated query failure')
            # Second call: second signal succeeds
            return _make_count_response(3)

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=signals_config,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=mock_execute,
        )

        # The failing signal should be recorded in query_failures
        assert len(result.query_failures) == 1
        assert result.query_failures[0].signal_name == 'failing signal'
        assert 'Simulated query failure' in result.query_failures[0].error_message

        # The passing signal should still produce a finding
        assert len(result.findings) == 1
        assert result.findings[0].signal_name == 'passing signal'

        # Total signals evaluated should be 2
        assert result.signals_evaluated == 2


# ---------------------------------------------------------------------------
# Property 6: Recommendation ordering by effort
# ---------------------------------------------------------------------------


class TestRecommendationOrdering:
    """Property 6: Recommendations ordered by effort."""

    @pytest.mark.asyncio
    async def test_recommendations_ordered_small_medium_large(self):
        """Recommendations are ordered Small → Medium → Large."""
        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {
                        'Signal': 'sig-large',
                        'Criteria': 'a > 0',
                        'Recommendation': ['REC-001'],  # Large
                    },
                    {
                        'Signal': 'sig-small',
                        'Criteria': 'b > 0',
                        'Recommendation': ['REC-002'],  # Small
                    },
                    {
                        'Signal': 'sig-medium',
                        'Criteria': 'c > 0',
                        'Recommendation': ['REC-003'],  # Medium
                    },
                ]
            },
        }

        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_count_response(1)

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=signals_config,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=mock_execute,
        )

        efforts = [r.effort for r in result.recommendations]
        assert efforts == ['Small', 'Medium', 'Large']


# ---------------------------------------------------------------------------
# Property 8: Recommendation deduplication with first-occurrence order
# ---------------------------------------------------------------------------


class TestRecommendationDeduplication:
    """Property 8: Deduplication with first-occurrence order."""

    @pytest.mark.asyncio
    async def test_duplicate_recommendations_deduplicated(self):
        """Multiple findings referencing the same rec ID produce one recommendation."""
        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {
                        'Signal': 'sig-1',
                        'Criteria': 'a > 0',
                        'Recommendation': ['REC-001', 'REC-002'],
                    },
                    {
                        'Signal': 'sig-2',
                        'Criteria': 'b > 0',
                        'Recommendation': ['REC-002', 'REC-003'],
                    },
                ]
            },
        }

        execute_fn = AsyncMock(side_effect=lambda *args, **kwargs: _make_count_response(1))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=signals_config,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=execute_fn,
        )

        rec_ids = [r.id for r in result.recommendations]
        # Each rec ID appears exactly once
        assert len(rec_ids) == len(set(rec_ids))
        assert len(rec_ids) == 3

    @pytest.mark.asyncio
    async def test_first_occurrence_order_preserved(self):
        """Within the same effort level, first-occurrence order is preserved."""
        # Both REC-002 (Small) and a new Small rec — first-occurrence should win
        recs_config = {
            **RECOMMENDATIONS_CONFIG,
            'REC-004': {
                'text': 'Rec 4 text',
                'description': 'Rec 4 desc',
                'effort': 'Small',
                'documentation_links': ['https://example.com/4'],
            },
        }

        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {
                        'Signal': 'sig-1',
                        'Criteria': 'a > 0',
                        'Recommendation': ['REC-004'],  # Small, seen first
                    },
                    {
                        'Signal': 'sig-2',
                        'Criteria': 'b > 0',
                        'Recommendation': ['REC-002'],  # Small, seen second
                    },
                ]
            },
        }

        execute_fn = AsyncMock(side_effect=lambda *args, **kwargs: _make_count_response(1))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=signals_config,
            recommendations_config=recs_config,
            execute_fn=execute_fn,
        )

        small_recs = [r for r in result.recommendations if r.effort == 'Small']
        assert len(small_recs) == 2
        # REC-004 was encountered first, so it should come before REC-002
        assert small_recs[0].id == 'REC-004'
        assert small_recs[1].id == 'REC-002'


# ---------------------------------------------------------------------------
# Property 9: Recommendation triggered_by aggregation
# ---------------------------------------------------------------------------


class TestRecommendationTriggeredBy:
    """Property 9: triggered_by_signals aggregation."""

    @pytest.mark.asyncio
    async def test_triggered_by_aggregates_across_findings(self):
        """A recommendation triggered by multiple signals lists all of them."""
        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {
                        'Signal': 'signal-alpha',
                        'Criteria': 'a > 0',
                        'Recommendation': ['REC-001'],
                    },
                    {
                        'Signal': 'signal-beta',
                        'Criteria': 'b > 0',
                        'Recommendation': ['REC-001'],
                    },
                ]
            },
        }

        execute_fn = AsyncMock(side_effect=lambda *args, **kwargs: _make_count_response(2))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=signals_config,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=execute_fn,
        )

        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.id == 'REC-001'
        assert 'signal-alpha' in rec.triggered_by_signals
        assert 'signal-beta' in rec.triggered_by_signals
        assert len(rec.triggered_by_signals) == 2


# ---------------------------------------------------------------------------
# Full pipeline end-to-end
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """End-to-end pipeline test with mocked Data API."""

    @pytest.mark.asyncio
    async def test_full_pipeline_returns_complete_review_result(self):
        """Full pipeline with multiple signals produces a complete ReviewResult."""
        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {
                        'Signal': 'high storage utilization',
                        'Criteria': 'storage_utilization_pct > 80',
                        'Recommendation': ['REC-001'],
                    },
                ]
            },
            'TableInfo': {
                'Signals': [
                    {
                        'Signal': 'unsorted tables',
                        'Criteria': 'unsorted > 50',
                        'Recommendation': ['REC-002'],
                    },
                    {
                        'Signal': 'no compression',
                        'Criteria': 'encoded = false',
                        'Recommendation': ['REC-003'],
                    },
                ]
            },
        }

        call_count = 0

        async def mock_execute(cluster_id, database, sql, **kwargs):
            nonlocal call_count
            call_count += 1
            # Call 1: NodeDetails signal — triggered (count=3)
            if call_count == 1:
                return _make_count_response(3)
            # Call 2: TableInfo signal 1 — triggered (count=10)
            if call_count == 2:
                return _make_count_response(10)
            # Call 3: TableInfo signal 2 — not triggered (count=0)
            return _make_count_response(0)

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=signals_config,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=mock_execute,
        )

        # 3 signals evaluated
        assert result.signals_evaluated == 3

        # 2 findings (third signal had count=0)
        assert len(result.findings) == 2
        finding_names = [f.signal_name for f in result.findings]
        assert 'high storage utilization' in finding_names
        assert 'unsorted tables' in finding_names

        # Recommendations ordered by effort: Small (REC-002) → Large (REC-001)
        assert len(result.recommendations) == 2
        assert result.recommendations[0].effort == 'Small'
        assert result.recommendations[1].effort == 'Large'

        # No failures
        assert len(result.query_failures) == 0

        # Queries executed
        assert 'NodeDetails' in result.queries_executed
        assert 'TableInfo' in result.queries_executed

    @pytest.mark.asyncio
    async def test_progress_fn_called_for_each_signal(self):
        """progress_fn is called with (current, total) after each signal."""
        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {'Signal': 'sig1', 'Criteria': 'x > 0', 'Recommendation': []},
                    {'Signal': 'sig2', 'Criteria': 'y > 0', 'Recommendation': []},
                ]
            },
        }

        async def mock_execute(cluster_id, database, sql, **kwargs):
            return _make_count_response(0)

        progress_calls = []

        async def mock_progress(current, total):
            progress_calls.append((current, total))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=signals_config,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=mock_execute,
            progress_fn=mock_progress,
        )

        assert result.signals_evaluated == 2
        assert progress_calls == [(1, 2), (2, 2)]

    @pytest.mark.asyncio
    async def test_skips_query_with_no_sql(self):
        """Queries with empty SQL are skipped."""
        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {'Signal': 'sig1', 'Criteria': 'x > 0', 'Recommendation': []},
                ]
            },
        }
        queries_with_empty_sql: dict[str, QueryEntry] = {
            'NodeDetails': {'SQL': ''},
        }

        async def mock_execute(cluster_id, database, sql, **kwargs):
            return _make_count_response(0)

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=queries_with_empty_sql,
            signals_config=signals_config,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=mock_execute,
        )
        assert result.signals_evaluated == 0

    @pytest.mark.asyncio
    async def test_empty_records_returns_count_zero(self):
        """Empty Records in response treated as count=0."""
        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {'Signal': 'sig1', 'Criteria': 'x > 0', 'Recommendation': []},
                ]
            },
        }

        async def mock_execute(cluster_id, database, sql, **kwargs):
            return ({'Records': []}, 'qid')

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=signals_config,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=mock_execute,
        )
        assert result.signals_evaluated == 1
        assert len(result.findings) == 0

    @pytest.mark.asyncio
    async def test_missing_recommendation_id_skipped(self):
        """Recommendation IDs not in config are silently skipped."""
        signals_config: dict[str, SectionEntry] = {
            'NodeDetails': {
                'Signals': [
                    {'Signal': 'sig1', 'Criteria': 'x > 0', 'Recommendation': ['NONEXISTENT']},
                ]
            },
        }

        execute_fn = AsyncMock(side_effect=lambda *args, **kwargs: _make_count_response(5))

        result = await run_review(
            cluster_identifier='test-cluster',
            database='dev',
            queries_config=QUERIES_CONFIG,
            signals_config=signals_config,
            recommendations_config=RECOMMENDATIONS_CONFIG,
            execute_fn=execute_fn,
        )
        assert len(result.findings) == 1
        assert len(result.recommendations) == 0
