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

"""Review pipeline orchestrating signal evaluation."""

from awslabs.redshift_mcp_server.models import (
    ReviewFinding,
    ReviewRecommendation,
    ReviewResult,
)
from awslabs.redshift_mcp_server.review.review_queries import (
    RECOMMENDATIONS,
    REVIEW_QUERIES,
)
from collections.abc import Callable
from loguru import logger
from typing import Any


async def run_review(
    cluster_identifier: str,
    database: str,
    execute_fn: Callable[..., Any],
    workgroup: str | None = None,
    progress_fn: Callable[[int, int], Any] | None = None,
) -> ReviewResult:
    """Execute a full cluster review.

    Pipeline stages:
    1. Select review queries (filter out provisioned-only when serverless)
    2. Execute each query and collect (count, rec_id) rows
    3. Build findings from rows where count > 0
    4. Resolve and deduplicate recommendations, ordered by first occurrence
    """
    # Stage 1: Select queries, filtering provisioned-only for serverless
    queries = [
        (name, sql)
        for name, sql, provisioned_only in REVIEW_QUERIES
        if not (workgroup and provisioned_only)
    ]

    total_queries = len(queries)
    findings: list[ReviewFinding] = []
    queries_executed: list[str] = []

    # Stage 2 & 3: Execute and collect findings
    for idx, (query_name, sql) in enumerate(queries):
        logger.debug('Executing review query: {} ({}/{})', query_name, idx + 1, total_queries)

        results_response, _ = await execute_fn(
            cluster_identifier,
            database,
            sql,
            allow_read_write=True,
        )

        queries_executed.append(query_name)

        records = results_response.get('Records', [])
        query_findings = 0
        for row in records:
            count = row[0].get('longValue', 0)
            rec_id = row[1].get('stringValue', '')
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
            len(records),
            query_findings,
        )

        if progress_fn:
            await progress_fn(idx + 1, total_queries)

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
