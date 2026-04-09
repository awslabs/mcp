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

"""Review pipeline orchestrating CTE-based signal evaluation."""

from collections.abc import Callable
from typing import Any

from loguru import logger

from awslabs.redshift_mcp_server.models import (
    CONCERN_QUERY_MAP,
    PROVISIONED_ONLY_QUERIES,
    ConcernCategory,
    ClusterMetadata,
    QueryFailureInfo,
    ReviewFinding,
    ReviewRecommendation,
    ReviewResult,
)
from awslabs.redshift_mcp_server.review.cte_builder import build_signal_query, validate_sql_readonly
from awslabs.redshift_mcp_server.review.config_loader import (
    QueryEntry,
    RecommendationEntry,
    SectionEntry,
)

EFFORT_ORDER = {'Small': 0, 'Medium': 1, 'Large': 2}


async def run_review(
    cluster_identifier: str,
    database: str,
    concern: ConcernCategory,
    queries_config: dict[str, QueryEntry],
    signals_config: dict[str, SectionEntry],
    recommendations_config: dict[str, RecommendationEntry],
    execute_fn: Callable[..., Any],
    workgroup: str | None = None,
    progress_fn: Callable[[int, int], Any] | None = None,
) -> ReviewResult:
    """Execute a full cluster review.

    Pipeline stages:
    1. Resolve concern -> query names via CONCERN_QUERY_MAP
    2. Filter out provisioned-only queries if workgroup is set
    3. For each query, for each signal: build CTE SQL, validate, execute, extract count
    4. Build findings list (signal triggered if count > 0)
    5. Resolve recommendation IDs -> full recommendation objects, deduplicate
    6. Order recommendations by effort (Small -> Medium -> Large)
    7. Aggregate triggered_by_signals per recommendation
    8. Extract cluster metadata from NodeDetails results (fallback for serverless)
    """
    # Stage 1: Resolve concern -> query names
    query_names = list(CONCERN_QUERY_MAP[concern])

    # Stage 2: Filter out provisioned-only queries when workgroup is set (serverless)
    if workgroup:
        query_names = [q for q in query_names if q not in PROVISIONED_ONLY_QUERIES]

    # Stage 8 (early): Extract cluster metadata
    cluster_metadata = await _extract_cluster_metadata(
        cluster_identifier=cluster_identifier,
        database=database,
        query_names=query_names,
        queries_config=queries_config,
        execute_fn=execute_fn,
        workgroup=workgroup,
    )

    # Stage 3 & 4: Evaluate signals and build findings
    findings: list[ReviewFinding] = []
    query_failures: list[QueryFailureInfo] = []
    queries_executed: list[str] = []
    signals_evaluated = 0

    # Count total signals for progress reporting
    total_signals = sum(
        len(signals_config[q]['Signals'])
        for q in query_names
        if q in signals_config and queries_config.get(q, {}).get('SQL')
    )

    for query_name in query_names:
        if query_name not in signals_config:
            continue

        section = signals_config[query_name]
        base_sql = queries_config.get(query_name, {}).get('SQL', '')
        if not base_sql:
            continue

        if query_name not in queries_executed:
            queries_executed.append(query_name)

        for signal_entry in section['Signals']:
            signal_name = signal_entry['Signal']
            criteria = signal_entry['Criteria']
            population_criteria = signal_entry.get('PopulationCriteria')
            recommendation_ids = signal_entry.get('Recommendation', [])

            try:
                # Build CTE SQL
                sql = build_signal_query(
                    query_name=query_name,
                    base_sql=base_sql,
                    criteria=criteria,
                    population_criteria=population_criteria,
                )

                # Validate read-only
                validate_sql_readonly(sql)

                # Execute via execute_fn (sequential per AD-2)
                # allow_read_write=True because review queries are server-generated,
                # validated by validate_sql_readonly(), and some diagnostic queries
                # (e.g. WLMConfig using stv_ tables with LISTAGG) require write-capable
                # transactions internally even though they only read data.
                results_response, query_id = await execute_fn(
                    cluster_identifier, database, sql, allow_read_write=True
                )

                # Extract count
                records = results_response.get('Records', [])
                if records and records[0]:
                    count = records[0][0].get('longValue', 0)
                else:
                    count = 0

                signals_evaluated += 1

                if progress_fn:
                    await progress_fn(signals_evaluated, total_signals)

                if count > 0:
                    findings.append(
                        ReviewFinding(
                            signal_name=signal_name,
                            section=query_name,
                            affected_row_count=count,
                            recommendation_ids=recommendation_ids,
                        )
                    )
                    logger.debug(
                        'Signal triggered: "{}" in section {} (count={})',
                        signal_name,
                        query_name,
                        count,
                    )
                else:
                    logger.debug(
                        'Signal not triggered: "{}" in section {}',
                        signal_name,
                        query_name,
                    )

            except Exception as e:
                signals_evaluated += 1
                if progress_fn:
                    await progress_fn(signals_evaluated, total_signals)
                query_failures.append(
                    QueryFailureInfo(
                        query_name=query_name,
                        signal_name=signal_name,
                        error_message=str(e),
                    )
                )
                logger.debug(
                    'Signal evaluation failed: "{}" in section {}: {}',
                    signal_name,
                    query_name,
                    e,
                )

    # Stage 5-7: Resolve, deduplicate, order, and aggregate recommendations
    recommendations = _resolve_recommendations(
        findings=findings,
        recommendations_config=recommendations_config,
    )

    logger.info(
        'Review complete: {} signals evaluated, {} findings, {} failures',
        signals_evaluated,
        len(findings),
        len(query_failures),
    )

    return ReviewResult(
        cluster_metadata=cluster_metadata,
        concern=concern,
        signals_evaluated=signals_evaluated,
        findings=findings,
        recommendations=recommendations,
        queries_executed=queries_executed,
        query_failures=query_failures,
    )


async def _extract_cluster_metadata(
    cluster_identifier: str,
    database: str,
    query_names: list[str],
    queries_config: dict[str, QueryEntry],
    execute_fn: Callable[..., Any],
    workgroup: str | None = None,
) -> ClusterMetadata:
    """Extract cluster metadata from NodeDetails query or use serverless defaults."""
    # Serverless fallback
    if workgroup or 'NodeDetails' not in query_names:
        return ClusterMetadata(
            cluster_id=cluster_identifier,
            node_type='serverless',
            node_count=0,
            region='unknown',
        )

    # Try to execute NodeDetails base SQL for metadata
    base_sql = queries_config.get('NodeDetails', {}).get('SQL', '')
    if not base_sql:
        return ClusterMetadata(
            cluster_id=cluster_identifier,
            node_type='unknown',
            node_count=0,
            region='unknown',
        )

    try:
        results_response, _ = await execute_fn(
            cluster_identifier, database, base_sql, allow_read_write=True
        )
        records = results_response.get('Records', [])
        if records and records[0]:
            # First column is node_type (stringValue)
            node_type = records[0][0].get('stringValue', 'unknown')
            # Node count is the number of rows
            node_count = len(records)
            return ClusterMetadata(
                cluster_id=cluster_identifier,
                node_type=node_type,
                node_count=node_count,
                region='unknown',
            )
    except Exception as e:
        logger.debug('Failed to extract cluster metadata: {}', e)

    return ClusterMetadata(
        cluster_id=cluster_identifier,
        node_type='unknown',
        node_count=0,
        region='unknown',
    )


def _resolve_recommendations(
    findings: list[ReviewFinding],
    recommendations_config: dict[str, RecommendationEntry],
) -> list[ReviewRecommendation]:
    """Resolve, deduplicate, order, and aggregate recommendations from findings."""
    # Track first-occurrence order and triggered_by_signals per rec ID
    rec_order: dict[str, int] = {}
    triggered_by: dict[str, list[str]] = {}
    order_counter = 0

    for finding in findings:
        for rec_id in finding.recommendation_ids:
            if rec_id not in rec_order:
                rec_order[rec_id] = order_counter
                order_counter += 1
                triggered_by[rec_id] = []
            if finding.signal_name not in triggered_by[rec_id]:
                triggered_by[rec_id].append(finding.signal_name)

    # Build recommendation objects
    resolved: list[ReviewRecommendation] = []
    for rec_id in rec_order:
        entry = recommendations_config.get(rec_id)
        if not entry:
            continue
        resolved.append(
            ReviewRecommendation(
                id=rec_id,
                text=entry['text'],
                description=entry['description'],
                effort=entry['effort'],
                documentation_links=entry['documentation_links'],
                triggered_by_signals=triggered_by[rec_id],
            )
        )

    # Sort by effort (Small -> Medium -> Large), preserving first-occurrence within same effort
    resolved.sort(key=lambda r: (EFFORT_ORDER.get(r.effort, 99), rec_order.get(r.id, 99)))

    return resolved
