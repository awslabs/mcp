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
from awslabs.redshift_mcp_server.models import RedshiftCluster
from awslabs.redshift_mcp_server.review.definitions import (
    NODE_TYPE_PLACEHOLDER,
    NODE_TYPE_UNKNOWN,
    RECOMMENDATIONS,
    SIGNAL_EVALUATION_SQL,
    SIGNAL_UNITS,
)
from awslabs.redshift_mcp_server.review.executor import resolve_node_type, review_cluster
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


def _cluster(
    identifier='test-cluster',
    cluster_type='provisioned',
    node_type: str | None = 'ra3.xlplus',
):
    """Build a RedshiftCluster model for discover_clusters mocks."""
    return RedshiftCluster.model_validate(
        {
            'identifier': identifier,
            'type': cluster_type,
            'status': 'available',
            'database_name': 'dev',
            'node_type': None if cluster_type == 'serverless' else node_type,
        }
    )


def _make_discover_clusters(cluster_type='provisioned', node_type: str | None = 'ra3.xlplus'):
    """Build a mock discover_clusters returning a single cluster."""
    return AsyncMock(return_value=[_cluster(cluster_type=cluster_type, node_type=node_type)])


def _make_sql_recorder():
    """Build an execute_query mock that records the SQL sent for each query name.

    Every diagnostic query starts with a '-- <QueryName>' comment line, which is used
    to key the recorded SQL.

    Returns:
        A (execute_query_func, recorded) tuple, where recorded maps query name to SQL.
    """
    recorded: dict[str, str] = {}

    async def _execute(cluster_identifier, database_name, sql, allow_read_write=False):
        recorded[sql.splitlines()[0].removeprefix('--').strip()] = sql
        return _make_empty_response()

    return _execute, recorded


def _branch_where(sql: str, rec_id: str, label_fragment: str) -> str:
    """Return the predicate of the UNION ALL branch selecting rec_id with a matching label.

    Args:
        sql: The full diagnostic query.
        rec_id: The recommendation ID the branch emits, for example 'REC_001'.
        label_fragment: A fragment of the branch's signal label, used to pick one
            branch when several share a recommendation ID.

    Returns:
        The text following the branch's own WHERE keyword. The last WHERE in the branch
        is the branch predicate; earlier ones belong to the CTE or its subqueries.

    Raises:
        AssertionError: If no single branch matches.
    """
    matches = [
        branch
        for branch in sql.split('UNION ALL')
        if f"'{rec_id}'" in branch and label_fragment in branch
    ]
    assert len(matches) == 1, (
        f'expected 1 branch for {rec_id}/{label_fragment}, got {len(matches)}'
    )
    branch = matches[0]
    assert 'WHERE' in branch, f'branch {rec_id}/{label_fragment} has no predicate'
    return branch.rsplit('WHERE', 1)[-1]


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
                _cluster(cluster_type='serverless'),
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
                _cluster(),
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
                _cluster(),
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
                _cluster(identifier='other-cluster'),
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
# Node type resolution and substitution
# ---------------------------------------------------------------------------


class TestNodeTypeResolution:
    """Validate resolve_node_type() accepts real node types and rejects the rest."""

    @pytest.mark.parametrize(
        'node_type',
        [
            'dc2.large',
            'dc2.8xlarge',
            'ds2.xlarge',
            'ds2.8xlarge',
            'ra3.large',
            'ra3.xlplus',
            'ra3.4xlarge',
            'ra3.16xlarge',
            'rg.xlarge',
            'rg.4xlarge',
        ],
    )
    def test_real_node_types_pass_through(self, node_type):
        """Every node type Redshift currently reports is used verbatim."""
        assert resolve_node_type(node_type) == node_type

    @pytest.mark.parametrize(
        'node_type',
        [
            None,
            '',
            'ra3',
            'RA3.xlplus',
            'ra3.xlplus; DROP TABLE t',
            "ra3.xlplus'--",
            'ra3.xlplus OR 1=1',
        ],
    )
    def test_unusable_node_types_fall_back(self, node_type):
        """Absent or malformed node types resolve to the unknown sentinel."""
        assert resolve_node_type(node_type) == NODE_TYPE_UNKNOWN


class TestNodeTypeSubstitution:
    """Verify the cluster's real node type reaches the diagnostic SQL."""

    @pytest.mark.asyncio
    async def test_node_type_is_inlined_into_node_details(self):
        """NodeDetails selects the node type reported by the API, not a derived one."""
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(node_type='rg.xlarge'),
        )

        assert "'rg.xlarge'::varchar(32) AS node_type" in recorded['NodeDetails']

    @pytest.mark.asyncio
    async def test_no_executed_query_retains_the_placeholder(self):
        """Substitution leaves no unresolved placeholder in any executed query."""
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(node_type='rg.4xlarge'),
        )

        assert recorded
        for name, sql in recorded.items():
            assert NODE_TYPE_PLACEHOLDER not in sql, f'{name} kept an unsubstituted placeholder'

    @pytest.mark.asyncio
    async def test_missing_node_type_falls_back_in_sql(self):
        """A provisioned cluster without a node type inlines the unknown sentinel."""
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(node_type=None),
        )

        assert f"'{NODE_TYPE_UNKNOWN}'::varchar(32) AS node_type" in recorded['NodeDetails']

    @pytest.mark.asyncio
    async def test_legacy_node_types_still_get_the_rg_migration_signal(self):
        """Pre-RG node families remain eligible for the migrate-to-RG recommendation."""
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(node_type='ra3.xlplus'),
        )

        predicate = _branch_where(recorded['NodeDetails'], 'REC_001', 'migrating to RG')
        assert "'ra3.xlplus'" in predicate

    @pytest.mark.asyncio
    @pytest.mark.parametrize('node_type', ['rg.xlarge', 'rg.4xlarge'])
    async def test_rg_cluster_matches_no_node_type_signal(self, node_type):
        """No node-type-gated signal applies to RG.

        REC_001 would advise migrating to the node type already in use. The storage
        branches divide per-node `used` by the cluster-wide managed storage quota that
        stv_node_storage_capacity reports for RG, so their thresholds do not describe
        RG utilization. The node type is therefore expected exactly once in the query,
        in the projection, and in no predicate.
        """
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(node_type=node_type),
        )

        sql = recorded['NodeDetails']
        assert f"'{node_type}'::varchar(32) AS node_type" in sql
        assert sql.count(f"'{node_type}'") == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('rec_id', 'label_fragment'),
        [
            ('REC_001', 'migrating to RG'),
            ('REC_002', 'recommended storage threshold of 70%'),
            ('REC_006', 'storage threshold of 50%'),
            ('REC_011', 'under-utilized storage'),
        ],
    )
    async def test_rg_excluded_from_each_node_type_branch(self, rec_id, label_fragment):
        """Each node-type-gated branch individually excludes RG."""
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(node_type='rg.xlarge'),
        )

        predicate = _branch_where(recorded['NodeDetails'], rec_id, label_fragment)
        assert "'rg.xlarge'" not in predicate

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('rec_id', 'label_fragment'),
        [
            ('REC_001', 'migrating to RG'),
            ('REC_002', 'recommended storage threshold of 70%'),
            ('REC_006', 'storage threshold of 50%'),
            ('REC_011', 'under-utilized storage'),
        ],
    )
    async def test_pre_rg_node_types_keep_storage_signals(self, rec_id, label_fragment):
        """Excluding RG must not disturb the node families these signals were written for."""
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(node_type='dc2.large'),
        )

        predicate = _branch_where(recorded['NodeDetails'], rec_id, label_fragment)
        assert "'dc2.large'" in predicate

    @pytest.mark.asyncio
    async def test_data_skew_signal_still_applies_to_rg(self):
        """The skew branch is not node-type gated, so it remains active on RG.

        Unlike the storage thresholds, skew compares per-node usage against per-node
        usage, which stays meaningful on managed storage.
        """
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(node_type='rg.xlarge'),
        )

        predicate = _branch_where(recorded['NodeDetails'], 'REC_008', 'data skew')
        assert 'node_type' not in predicate

    @pytest.mark.asyncio
    async def test_serverless_review_executes_no_placeholder_query(self):
        """Serverless workgroups have no node type and run no query needing one."""
        execute_query_func, recorded = _make_sql_recorder()

        await review_cluster(
            cluster_identifier='test-cluster',
            execute_query_func=execute_query_func,
            discover_clusters_func=_make_discover_clusters(cluster_type='serverless'),
        )

        assert 'NodeDetails' not in recorded
        for sql in recorded.values():
            assert NODE_TYPE_UNKNOWN not in sql


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

    def test_node_type_placeholder_confined_to_node_details(self):
        """Only NodeDetails uses the node type placeholder."""
        users = {name for name, _ct, sql in SIGNAL_EVALUATION_SQL if NODE_TYPE_PLACEHOLDER in sql}
        assert users == {'NodeDetails'}

    def test_node_type_placeholder_query_is_provisioned_only(self):
        """The placeholder is only used where a node type exists (provisioned)."""
        for name, cluster_type, sql in SIGNAL_EVALUATION_SQL:
            if NODE_TYPE_PLACEHOLDER in sql:
                assert cluster_type == 'provisioned', (
                    f'{name} needs a node type but is {cluster_type}'
                )

    def test_no_unrecognized_placeholders(self):
        """The node type placeholder is the only substitution token in any query.

        Guards against a new {token} being added and silently shipped unsubstituted.
        """
        import re

        token = re.compile(r'\{[a-z_]+\}')
        for name, _ct, sql in SIGNAL_EVALUATION_SQL:
            unknown = set(token.findall(sql)) - {NODE_TYPE_PLACEHOLDER}
            assert not unknown, f'{name} has unsupported placeholders: {unknown}'

    def test_recommendations_not_empty(self):
        """RECOMMENDATIONS dict is not empty."""
        assert len(RECOMMENDATIONS) > 0

    def test_provisioned_only_flags(self):
        """NodeDetails and WLMConfig are marked provisioned-only."""
        provisioned = {name for name, ct, _ in SIGNAL_EVALUATION_SQL if ct == 'provisioned'}
        assert 'NodeDetails' in provisioned
        assert 'WLMConfig' in provisioned
        assert 'WorkloadEvaluation' in provisioned
