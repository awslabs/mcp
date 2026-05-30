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

"""Review executor orchestrating signal evaluation."""

from awslabs.redshift_mcp_server.review.definitions import (
    RECOMMENDATIONS,
    SIGNAL_EVALUATION_SQL,
)
from awslabs.redshift_mcp_server.review.models import (
    ReviewFinding,
    ReviewRecommendation,
    ReviewResult,
)
from loguru import logger
from typing import Any, Callable


async def review_cluster(
    cluster_identifier: str,
    execute_query_func: Callable[..., Any],
    discover_clusters_func: Callable[..., Any],
    database_name: str = 'dev',
    progress_reporter_func: Callable[[int, int], Any] | None = None,
):
    """Execute a full cluster review.

    Args:
        cluster_identifier: The cluster identifier to review.
        execute_query_func: Async callable matching the signature of execute_query().
        discover_clusters_func: Async callable matching the signature of discover_clusters().
        database_name: The database to run the review against. Defaults to 'dev'.
        progress_reporter_func: Optional async callable receiving (current, total) after each query.

    Returns:
        ReviewResult with findings and deduplicated recommendations.
    """
    # Determine cluster type from cluster_info
    clusters = await discover_clusters_func()
    cluster_info = None
    for cluster in clusters:
        if cluster['identifier'] == cluster_identifier:
            cluster_info = cluster
            break

    if not cluster_info:
        raise Exception(
            f'Cluster {cluster_identifier} not found. Please use list_clusters to get valid cluster identifiers.'
        )

    is_serverless = cluster_info.get('type') == 'serverless'

    # Stage 1: Select queries, filtering provisioned-only for serverless
    queries = [
        (name, sql)
        for name, cluster_type, sql in SIGNAL_EVALUATION_SQL
        if not (is_serverless and cluster_type == 'provisioned')
    ]

    total_queries = len(queries)
    findings: list[ReviewFinding] = []
    queries_executed: list[str] = []

    # Stage 2 & 3: Execute and collect findings
    for idx, (query_name, sql) in enumerate(queries):
        logger.debug('Executing review query: {} ({}/{})', query_name, idx + 1, total_queries)

        result = await execute_query_func(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=sql,
            allow_read_write=True,
        )

        queries_executed.append(query_name)

        rows = result.get('rows', [])
        query_findings = 0
        for row in rows:
            count = row[0]
            rec_id = row[1]
            if count > 0 and rec_id:
                query_findings += 1
                findings.append(
                    ReviewFinding(
                        signal_name=query_name,
                        section=query_name,
                        affected_row_count=count,
                        recommendation_ids=[rec_id],
                    )
                )

        logger.debug(
            'Query {} returned {} rows, {} findings',
            query_name,
            len(rows),
            query_findings,
        )

        if progress_reporter_func:
            await progress_reporter_func(idx + 1, total_queries)

    # Stage 4: Resolve recommendations (deduplicate, preserve first-occurrence order)
    seen: dict[str, list[str]] = {}
    for finding in findings:
        for rec_id in finding.recommendation_ids:
            if rec_id not in seen:
                seen[rec_id] = []
            if finding.signal_name not in seen[rec_id]:
                seen[rec_id].append(finding.signal_name)

    recommendations: list[ReviewRecommendation] = []
    for rec_id, triggered_by in seen.items():
        text = RECOMMENDATIONS.get(rec_id, '')
        if not text:
            continue
        recommendations.append(
            ReviewRecommendation(
                id=rec_id,
                text=text,
                triggered_by_signals=triggered_by,
            )
        )

    logger.info(
        'Review complete: {} queries executed, {} findings, {} recommendations',
        len(queries_executed),
        len(findings),
        len(recommendations),
    )

    return ReviewResult(
        signals_evaluated=total_queries,
        findings=findings,
        recommendations=recommendations,
        queries_executed=queries_executed,
    )
