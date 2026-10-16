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
    SIGNAL_UNITS,
)
from awslabs.redshift_mcp_server.review.models import (
    ReviewFinding,
    ReviewRecommendation,
    ReviewResult,
)
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError
from typing import Any, Callable


async def review_cluster(
    cluster_identifier: str,
    cluster_type: str,
    execute_query_func: Callable[..., Any],
    resolve_cluster_func: Callable[..., Any],
    database_name: str = 'dev',
    progress_reporter_func: Callable[[int, int], Any] | None = None,
):
    """Execute a full cluster review.

    Args:
        cluster_identifier: The cluster identifier to review.
        cluster_type: `provisioned` or `serverless`.
        execute_query_func: Async callable matching the signature of execute_query().
        resolve_cluster_func: Async callable matching the signature of resolve_cluster().
        database_name: The database to run the review against. Defaults to 'dev'.
        progress_reporter_func: Optional async callable receiving (current, total) after each query.

    Returns:
        ReviewResult with findings and deduplicated recommendations.
    """
    # Resolved rather than searched for: a local scan over discovery reads a cluster whose listing
    # IAM denied as not found with no mention of the denial. Fresh, because the node type is read
    # below: answered from the stored discovery after a resize, the review evaluated the node-type
    # signals for the node type the cluster had before it.
    cluster_info = await resolve_cluster_func(cluster_identifier, cluster_type, fresh=True)

    is_serverless = cluster_info.type == 'serverless'

    # Stage 1: select queries in this cluster's type scope and render each with the
    # node type from the Redshift API so node-type signals evaluate it directly.
    node_type = cluster_info.node_type or 'unknown'
    queries = [
        (name, sql.format(node_type=node_type))
        for name, scope, sql in SIGNAL_EVALUATION_SQL
        if scope == 'all'
        or (is_serverless and scope == 'serverless')
        or (not is_serverless and scope == 'provisioned')
    ]

    total_queries = len(queries)
    # Keyed by signal and section, so one triggered signal is one finding however many
    # recommendations it maps to. Branches that share a recommendation under *different*
    # labels stay distinct, each with its own affected_row_count, which is what the per-branch
    # -- Signal: labels are for. Recommendation-level dedup happens in Stage 4.
    findings_by_signal: dict[tuple[str, str], ReviewFinding] = {}
    queries_executed: list[str] = []
    # Keyed as the findings are, so the two are comparable: a signal that ran counts once however
    # many rows carry it. A query holds one signal per UNION ALL branch and each branch returns
    # one row, but several branches repeat a label to attach a second and third recommendation to
    # it, so rows exceed signals - 55 against 48 on a provisioned cluster, 37 against 32 on a
    # workgroup.
    evaluated: set[tuple[str, str]] = set()

    # Stage 2 & 3: Execute each query and collect a finding per triggered signal.
    for idx, (query_name, sql) in enumerate(queries):
        logger.debug('Executing review query: {} ({}/{})', query_name, idx + 1, total_queries)

        try:
            result = await execute_query_func(
                cluster_identifier=cluster_identifier,
                cluster_type=cluster_type,
                database_name=database_name,
                sql=sql,
                enforce_read_only=False,
            )
        except Exception as e:
            logger.error('Review query {} failed: {}', query_name, str(e))
            if 'permission denied' in str(e).lower():
                raise ToolError(
                    f'Review requires superuser or sys:monitor access. Request an administrator '
                    f'to run: '
                    f'GRANT ROLE sys:monitor TO "<database_user>"; where <database_user> is the '
                    f'output of SELECT current_user - for IAM identities it looks like '
                    f'IAM:alice or IAMR:MyRole and the quotes are required. '
                    f'Query {query_name} failed with: {e}'
                ) from e
            raise

        queries_executed.append(query_name)

        rows = result.get('rows', [])
        unit = SIGNAL_UNITS.get(query_name, 'items')
        query_findings = 0
        for row in rows:
            count = row[0]
            rec_id = row[1]
            # The 3rd column is the branch's own -- Signal: label. Fall back to the
            # query name if a query ever returns only (count, rec_id).
            signal_label = row[2] if len(row) > 2 else query_name
            # Recorded whether or not it triggered: the predicate ran either way.
            evaluated.add((signal_label, query_name))
            if count > 0 and rec_id:
                existing = findings_by_signal.get((signal_label, query_name))
                if existing is None:
                    query_findings += 1
                    findings_by_signal[(signal_label, query_name)] = ReviewFinding(
                        signal_name=signal_label,
                        section=query_name,
                        affected_row_count=count,
                        unit=unit,
                        recommendation_ids=[rec_id],
                    )
                elif rec_id not in existing.recommendation_ids:
                    # The same signal again, carrying another recommendation. Its count comes
                    # from the same predicate, so only the recommendation is new.
                    existing.recommendation_ids.append(rec_id)

        logger.debug(
            'Query {} returned {} rows, {} findings',
            query_name,
            len(rows),
            query_findings,
        )

        if progress_reporter_func:
            await progress_reporter_func(idx + 1, total_queries)

    findings = list(findings_by_signal.values())

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
        signals_evaluated=len(evaluated),
        findings=findings,
        recommendations=recommendations,
        queries_executed=queries_executed,
    )
