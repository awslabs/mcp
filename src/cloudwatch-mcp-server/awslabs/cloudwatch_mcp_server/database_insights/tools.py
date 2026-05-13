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

"""Database Insights (Performance Insights) tools for MCP server."""

import json
import boto3
import os
from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
from awslabs.cloudwatch_mcp_server.database_insights.models import (
    CounterMetric,
    DatabaseCountersResult,
    DatabaseInstance,
    DatabaseInsightsMetric,
    DatabaseLoadResult,
    DatabaseResourceInfo,
    DimensionKeyDetail,
    IncidentAnalysisResult,
    ListDatabasesResult,
    PeriodComparison,
    SqlDetails,
    TopSqlResult,
    TopSqlStatement,
    WaitEventBreakdown,
    WaitEventDetail,
)
from botocore.config import Config
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateutil_parser
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Literal, Optional


class DatabaseInsightsTools:
    """Database Insights (Performance Insights) tools for MCP server."""

    def __init__(self):
        """Initialize the Database Insights tools."""
        logger.info('DatabaseInsightsTools initialized')

    def _get_boto_session(self, region: str):
        """Create a boto3 session for the specified region."""
        if aws_profile := os.environ.get('AWS_PROFILE'):
            return boto3.Session(profile_name=aws_profile, region_name=region)
        return boto3.Session(region_name=region)

    def _get_boto_config(self):
        """Get the botocore config with user agent."""
        return Config(user_agent_extra=f'awslabs/mcp/cloudwatch-mcp-server/{MCP_SERVER_VERSION}')

    def _get_rds_client(self, region: str):
        """Create an RDS client for the specified region."""
        return self._get_boto_session(region).client('rds', config=self._get_boto_config())

    def _get_pi_client(self, region: str):
        """Create a Performance Insights client for the specified region."""
        return self._get_boto_session(region).client('pi', config=self._get_boto_config())

    def _estimate_vcpu(self, instance_class: str) -> Optional[int]:
        """Estimate vCPU count from RDS instance class."""
        # Common RDS instance vCPU mappings
        vcpu_map = {
            'db.t3.micro': 2, 'db.t3.small': 2, 'db.t3.medium': 2, 'db.t3.large': 2,
            'db.t3.xlarge': 4, 'db.t3.2xlarge': 8,
            'db.t4g.micro': 2, 'db.t4g.small': 2, 'db.t4g.medium': 2, 'db.t4g.large': 2,
            'db.t4g.xlarge': 4, 'db.t4g.2xlarge': 8,
            'db.r5.large': 2, 'db.r5.xlarge': 4, 'db.r5.2xlarge': 8, 'db.r5.4xlarge': 16,
            'db.r5.8xlarge': 32, 'db.r5.12xlarge': 48, 'db.r5.16xlarge': 64, 'db.r5.24xlarge': 96,
            'db.r6g.large': 2, 'db.r6g.xlarge': 4, 'db.r6g.2xlarge': 8, 'db.r6g.4xlarge': 16,
            'db.r6g.8xlarge': 32, 'db.r6g.12xlarge': 48, 'db.r6g.16xlarge': 64,
            'db.r6i.large': 2, 'db.r6i.xlarge': 4, 'db.r6i.2xlarge': 8, 'db.r6i.4xlarge': 16,
            'db.r6i.8xlarge': 32, 'db.r6i.12xlarge': 48, 'db.r6i.16xlarge': 64, 'db.r6i.24xlarge': 96,
            'db.m5.large': 2, 'db.m5.xlarge': 4, 'db.m5.2xlarge': 8, 'db.m5.4xlarge': 16,
            'db.m5.8xlarge': 32, 'db.m5.12xlarge': 48, 'db.m5.16xlarge': 64, 'db.m5.24xlarge': 96,
            'db.m6g.large': 2, 'db.m6g.xlarge': 4, 'db.m6g.2xlarge': 8, 'db.m6g.4xlarge': 16,
            'db.m6g.8xlarge': 32, 'db.m6g.12xlarge': 48, 'db.m6g.16xlarge': 64,
            'db.m6i.large': 2, 'db.m6i.xlarge': 4, 'db.m6i.2xlarge': 8, 'db.m6i.4xlarge': 16,
            'db.m6i.8xlarge': 32, 'db.m6i.12xlarge': 48, 'db.m6i.16xlarge': 64, 'db.m6i.24xlarge': 96,
        }
        return vcpu_map.get(instance_class)

    def register(self, mcp: FastMCP):
        """Register Database Insights tools with the MCP server."""

        @mcp.tool(name='list-databases-with-insights')
        async def list_databases_with_insights(
            ctx: Context,
            region: str = Field(
                'us-east-1',
                description='AWS region to query. Defaults to us-east-1.',
            ),
            include_disabled: bool = Field(
                False,
                description='Include databases that do not have Performance Insights enabled.',
            ),
        ) -> str:
            """List RDS and Aurora database instances with their Performance Insights status.

            ## When to Use This Tool
            Use this tool FIRST before calling other Database Insights tools. It returns
            the DbiResourceId values needed for get-database-load-metrics.

            ## Usage Requirements
            - Call this tool to discover available databases before querying metrics
            - The DbiResourceId (not the DB identifier) is required for PI API calls

            ## Output Format
            Returns JSON with:
            - databases: List of database instances with their PI status
            - insights_enabled_count: How many have Performance Insights enabled (in the returned list)
            - total_count: Total number of databases in the region (unfiltered by include_disabled)
            """
            try:
                rds_client = self._get_rds_client(region)
                paginator = rds_client.get_paginator('describe_db_instances')

                databases = []
                total_instances = 0
                for page in paginator.paginate():
                    for db in page['DBInstances']:
                        total_instances += 1
                        pi_enabled = db.get('PerformanceInsightsEnabled', False)
                        if not include_disabled and not pi_enabled:
                            continue

                        databases.append(DatabaseInstance(
                            dbi_resource_id=db.get('DbiResourceId', ''),
                            db_instance_identifier=db['DBInstanceIdentifier'],
                            engine=db.get('Engine', 'unknown'),
                            engine_version=db.get('EngineVersion', ''),
                            insights_enabled=pi_enabled,
                            insights_retention_days=db.get('PerformanceInsightsRetentionPeriod'),
                            instance_class=db.get('DBInstanceClass'),
                            region=region,
                        ))

                insights_enabled_count = sum(d.insights_enabled for d in databases)
                result = ListDatabasesResult(
                    databases=databases,
                    region=region,
                    total_count=total_instances,
                    insights_enabled_count=insights_enabled_count,
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error listing databases: {str(e)}')
                return json.dumps({'error': str(e)})

        @mcp.tool(name='get-database-load-metrics')
        async def get_database_load_metrics(
            ctx: Context,
            db_resource_id: str = Field(
                ...,
                description='The DbiResourceId from list-databases-with-insights. '
                'CRITICAL: You MUST first call list-databases-with-insights to get valid IDs.',
            ),
            start_time: str = Field(
                ...,
                description='ISO 8601 formatted start time (e.g., "2025-01-10T00:00:00Z").',
            ),
            end_time: str = Field(
                ...,
                description='ISO 8601 formatted end time (e.g., "2025-01-10T01:00:00Z").',
            ),
            group_by: Literal['db.sql', 'db.wait_event', 'db.user', 'db.host'] = Field(
                'db.sql',
                description='Dimension to group database load by. Use db.sql to find top queries, '
                'db.wait_event to understand what the database is waiting on.',
            ),
            region: str = Field(
                'us-east-1',
                description='AWS region to query. Defaults to us-east-1.',
            ),
            limit: int = Field(
                10,
                description='Maximum number of top dimensions to return (1-25).',
            ),
        ) -> str:
            """Retrieve database load metrics from AWS Performance Insights.

            ## When to Use This Tool
            Use this tool when:
            - CloudWatch DBLoad metric shows elevated values
            - You need to identify TOP SQL queries causing load
            - You need to understand WHAT the database is waiting on (I/O, locks, CPU)
            - Application traces show slow database operations

            ## Usage Requirements
            - You MUST first call list-databases-with-insights to get the db_resource_id
            - The database MUST have Performance Insights enabled

            ## Interpreting Results
            - db_load_avg: Average Active Sessions (AAS)
            - group_by=db.sql: Shows which SQL queries consume the most database time
            - group_by=db.wait_event: Shows what the database is waiting on
              - IO:* events indicate storage bottlenecks
              - Lock:* events indicate locking/blocking issues
              - CPU events indicate compute-bound queries

            Note: SQL text is truncated to 200 characters; each dimension includes up to 10 data points.
            """
            try:
                # Validate limit bounds
                if limit < 1:
                    limit = 1
                elif limit > 25:
                    limit = 25

                pi_client = self._get_pi_client(region)

                # Parse time strings using dateutil for robust ISO 8601 parsing
                start_dt = dateutil_parser.isoparse(start_time)
                end_dt = dateutil_parser.isoparse(end_time)

                # Validate end_time is after start_time
                if end_dt <= start_dt:
                    return json.dumps({'error': 'end_time must be after start_time'})

                # Calculate appropriate period (minimum 60 seconds for PI)
                duration_seconds = (end_dt - start_dt).total_seconds()
                if duration_seconds <= 3600:  # 1 hour or less
                    period = 60
                elif duration_seconds <= 86400:  # 1 day or less
                    period = 300
                else:
                    period = 3600

                # Build metric queries
                # Request overall db.load.avg (no GroupBy) first so we can compute accurate summary stats,
                # and also request the GroupBy query to collect top dimension contributors.
                metric_queries = [
                    {
                        'Metric': 'db.load.avg',
                    },
                    {
                        'Metric': 'db.load.avg',
                        'GroupBy': {'Group': group_by, 'Limit': min(limit, 25)},
                    },
                ]

                response = pi_client.get_resource_metrics(
                    ServiceType='RDS',
                    Identifier=db_resource_id,
                    MetricQueries=metric_queries,
                    StartTime=start_dt,
                    EndTime=end_dt,
                    PeriodInSeconds=period,
                )

                # Process response and collect overall metrics for summary stats
                top_dimensions = []
                overall_data_points = []
                # Store full data points per dimension for accurate fallback calculation
                dimension_full_data = []

                for metric_list in response.get('MetricList', []):
                    dimensions = metric_list.get('Key', {}).get('Dimensions', {})

                    # Collect overall data points (without dimension grouping) for summary
                    if not dimensions:
                        for dp in metric_list.get('DataPoints', []):
                            if 'Value' in dp:
                                overall_data_points.append(DatabaseInsightsMetric(
                                    timestamp=dp['Timestamp'],
                                    value=dp['Value'],
                                ))
                        continue

                    # Process dimension data - each MetricList entry represents one grouped dimension.
                    # We only group by one dimension at a time, so take the first (and expected only) one.
                    # This avoids double-counting if PI ever returns multiple dimensions per entry.
                    dim_name, dim_value = next(iter(dimensions.items()))
                    data_points = []
                    total = 0.0
                    for dp in metric_list.get('DataPoints', []):
                        if 'Value' in dp:
                            total += dp['Value']
                            data_points.append(DatabaseInsightsMetric(
                                timestamp=dp['Timestamp'],
                                value=dp['Value'],
                            ))
                    # Store full data points for fallback before truncating
                    dimension_full_data.append(data_points)
                    top_dimensions.append(DimensionKeyDetail(
                        dimension=dim_name,
                        value=str(dim_value)[:200],  # Truncate long SQL
                        total=total,
                        data_points=data_points[:10],  # Limit data points in response
                    ))

                # Calculate summary stats from overall data points, or fall back to dimension data
                if not overall_data_points:
                    # No overall time series returned by PI; fall back to per-dimension time series.
                    # To avoid undercounting total load, sum values across dimensions for each timestamp
                    # (instead of averaging). This gives a better approximation of overall DB load.
                    # Use full (non-truncated) data points for accurate calculation.
                    logger.warning(
                        f'No overall metric returned for db {db_resource_id}; '
                        'falling back to summed per-dimension metrics. '
                        'Summary stats will be approximate.'
                    )
                    ts_map = {}
                    for data_points in dimension_full_data:
                        for dp in data_points:
                            ts_map.setdefault(dp.timestamp, []).append(dp.value)
                    deduped = []
                    for ts, vals in ts_map.items():
                        summed_val = sum(vals)
                        deduped.append(DatabaseInsightsMetric(timestamp=ts, value=summed_val))
                    deduped.sort(key=lambda x: x.timestamp)
                    overall_data_points = deduped

                if overall_data_points:
                    total = sum(dp.value for dp in overall_data_points)
                    count = len(overall_data_points)
                    db_load_avg = total / count if count else 0.0
                    db_load_max = max((dp.value for dp in overall_data_points), default=0.0)
                else:
                    db_load_avg = 0.0
                    db_load_max = 0.0

                result = DatabaseLoadResult(
                    db_resource_id=db_resource_id,
                    start_time=start_dt,
                    end_time=end_dt,
                    period_seconds=period,
                    db_load_avg=round(db_load_avg, 3),
                    db_load_max=round(db_load_max, 3),
                    top_dimensions=sorted(top_dimensions, key=lambda x: x.total, reverse=True),
                    overall_metrics=overall_data_points,
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error getting database load metrics: {str(e)}')
                return json.dumps({'error': str(e)})

        @mcp.tool(name='get-database-top-sql')
        async def get_database_top_sql(
            ctx: Context,
            db_resource_id: str = Field(
                ...,
                description='The DbiResourceId from list-databases-with-insights. '
                'CRITICAL: You MUST first call list-databases-with-insights to get valid IDs.',
            ),
            start_time: str = Field(
                ...,
                description='ISO 8601 formatted start time (e.g., "2025-01-10T00:00:00Z").',
            ),
            end_time: str = Field(
                ...,
                description='ISO 8601 formatted end time (e.g., "2025-01-10T01:00:00Z").',
            ),
            region: str = Field(
                'us-east-1',
                description='AWS region to query. Defaults to us-east-1.',
            ),
            limit: int = Field(
                10,
                description='Maximum number of top SQL statements to return (1-25).',
            ),
        ) -> str:
            """Get the top SQL statements by database load.

            ## When to Use This Tool
            Use this tool to identify the SQL queries consuming the most database resources
            during a specific time window. This is ideal for:
            - Finding slow or resource-intensive queries
            - Identifying queries causing high CPU or I/O
            - Troubleshooting application performance issues

            ## Output Format
            Returns a clean list of top SQL statements with:
            - sql_text: The actual SQL statement (truncated if very long)
            - total_load: Total contribution to database load (AAS)
            - avg_load: Average load per sample period
            """
            try:
                pi_client = self._get_pi_client(region)

                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

                duration_seconds = (end_dt - start_dt).total_seconds()
                if duration_seconds <= 3600:
                    period = 60
                elif duration_seconds <= 86400:
                    period = 300
                else:
                    period = 3600

                response = pi_client.get_resource_metrics(
                    ServiceType='RDS',
                    Identifier=db_resource_id,
                    MetricQueries=[{
                        'Metric': 'db.load.avg',
                        'GroupBy': {'Group': 'db.sql', 'Limit': min(limit, 25)},
                    }],
                    StartTime=start_dt,
                    EndTime=end_dt,
                    PeriodInSeconds=period,
                )

                top_sql = []
                seen_ids = set()
                total_load = 0.0

                for metric_list in response.get('MetricList', []):
                    dimensions = metric_list.get('Key', {}).get('Dimensions', {})

                    sql_id = dimensions.get('db.sql.id', dimensions.get('db.sql.tokenized_id', ''))
                    sql_text = dimensions.get('db.sql.statement', 'N/A')

                    if not sql_id or sql_id in seen_ids:
                        continue
                    seen_ids.add(sql_id)

                    values = [dp['Value'] for dp in metric_list.get('DataPoints', []) if 'Value' in dp]
                    if not values:
                        continue

                    stmt_total = sum(values)
                    total_load += stmt_total

                    top_sql.append(TopSqlStatement(
                        sql_id=sql_id,
                        sql_text=sql_text[:1000],  # Truncate very long SQL
                        total_load=round(stmt_total, 4),
                        avg_load=round(stmt_total / len(values), 4) if values else 0,
                    ))

                result = TopSqlResult(
                    db_resource_id=db_resource_id,
                    start_time=start_dt,
                    end_time=end_dt,
                    total_db_load=round(total_load, 4),
                    top_sql=sorted(top_sql, key=lambda x: x.total_load, reverse=True)[:limit],
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error getting top SQL: {str(e)}')
                return f'{{"error": "{str(e)}"}}'

        @mcp.tool(name='analyze-database-incident')
        async def analyze_database_incident(
            ctx: Context,
            db_resource_id: str = Field(
                ...,
                description='The DbiResourceId from list-databases-with-insights.',
            ),
            start_time: str = Field(
                ...,
                description='ISO 8601 formatted incident start time.',
            ),
            end_time: str = Field(
                ...,
                description='ISO 8601 formatted incident end time.',
            ),
            region: str = Field(
                'us-east-1',
                description='AWS region to query. Defaults to us-east-1.',
            ),
        ) -> str:
            """Comprehensive analysis of a database performance incident.

            ## When to Use This Tool
            Use this tool when investigating a database performance incident. It combines:
            - Top SQL queries during the incident
            - Top wait events (what the database was waiting on)
            - Actionable recommendations based on the findings

            ## Output Format
            Returns a structured analysis with:
            - summary: Human-readable incident summary
            - top_sql: SQL statements causing the most load
            - top_wait_events: What the database was waiting on
            - recommendations: Suggested actions to investigate/resolve
            """
            try:
                pi_client = self._get_pi_client(region)

                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

                duration_seconds = (end_dt - start_dt).total_seconds()
                if duration_seconds <= 3600:
                    period = 60
                elif duration_seconds <= 86400:
                    period = 300
                else:
                    period = 3600

                # Get both SQL and wait events in parallel-ish (sequential for now)
                sql_response = pi_client.get_resource_metrics(
                    ServiceType='RDS',
                    Identifier=db_resource_id,
                    MetricQueries=[{
                        'Metric': 'db.load.avg',
                        'GroupBy': {'Group': 'db.sql', 'Limit': 10},
                    }],
                    StartTime=start_dt,
                    EndTime=end_dt,
                    PeriodInSeconds=period,
                )

                wait_response = pi_client.get_resource_metrics(
                    ServiceType='RDS',
                    Identifier=db_resource_id,
                    MetricQueries=[{
                        'Metric': 'db.load.avg',
                        'GroupBy': {'Group': 'db.wait_event', 'Limit': 10},
                    }],
                    StartTime=start_dt,
                    EndTime=end_dt,
                    PeriodInSeconds=period,
                )

                # Process SQL results
                top_sql = []
                seen_sql_ids = set()
                total_load = 0.0
                peak_load = 0.0

                for metric_list in sql_response.get('MetricList', []):
                    dimensions = metric_list.get('Key', {}).get('Dimensions', {})
                    sql_id = dimensions.get('db.sql.id', '')
                    sql_text = dimensions.get('db.sql.statement', 'N/A')

                    if not sql_id or sql_id in seen_sql_ids:
                        continue
                    seen_sql_ids.add(sql_id)

                    values = [dp['Value'] for dp in metric_list.get('DataPoints', []) if 'Value' in dp]
                    if not values:
                        continue

                    stmt_total = sum(values)
                    total_load += stmt_total
                    peak_load = max(peak_load, max(values))

                    top_sql.append(TopSqlStatement(
                        sql_id=sql_id,
                        sql_text=sql_text[:500],
                        total_load=round(stmt_total, 4),
                        avg_load=round(stmt_total / len(values), 4),
                    ))

                # Process wait event results
                top_waits = []
                seen_waits = set()
                wait_interpretations = {
                    'CPU': 'Query is compute-bound, consider query optimization',
                    'IO': 'Storage I/O bottleneck, check IOPS limits or storage performance',
                    'Lock': 'Lock contention, check for blocking queries or deadlocks',
                    'LWLock': 'Internal lock contention (PostgreSQL), may indicate shared buffer issues',
                    'IPC': 'Inter-process communication wait, often parallel query related',
                    'Timeout': 'Timeout or sleep wait, often application-driven',
                    'Client': 'Waiting for client, network latency or slow application',
                }

                for metric_list in wait_response.get('MetricList', []):
                    dimensions = metric_list.get('Key', {}).get('Dimensions', {})
                    wait_name = dimensions.get('db.wait_event.name', '')
                    wait_type = dimensions.get('db.wait_event.type', 'Unknown')

                    if not wait_name or wait_name in seen_waits:
                        continue
                    seen_waits.add(wait_name)

                    values = [dp['Value'] for dp in metric_list.get('DataPoints', []) if 'Value' in dp]
                    if not values:
                        continue

                    wait_total = sum(values)

                    # Determine category and interpretation
                    category = wait_type
                    interpretation = wait_interpretations.get(category, f'{category} wait event')

                    top_waits.append(WaitEventDetail(
                        wait_event=wait_name,
                        wait_category=category,
                        total_load=round(wait_total, 4),
                        avg_load=round(wait_total / len(values), 4),
                        interpretation=interpretation,
                    ))

                # Generate recommendations
                recommendations = []
                sorted_sql = sorted(top_sql, key=lambda x: x.total_load, reverse=True)
                sorted_waits = sorted(top_waits, key=lambda x: x.total_load, reverse=True)

                if sorted_sql:
                    recommendations.append(
                        f"Review top SQL query: {sorted_sql[0].sql_text[:100]}..."
                    )

                if sorted_waits:
                    top_wait = sorted_waits[0]
                    if 'IO' in top_wait.wait_category.upper():
                        recommendations.append('Check storage IOPS and throughput limits')
                        recommendations.append('Consider provisioned IOPS or storage optimization')
                    elif 'LOCK' in top_wait.wait_category.upper():
                        recommendations.append('Check for blocking sessions and long-running transactions')
                        recommendations.append('Review transaction isolation levels')
                    elif 'CPU' in top_wait.wait_category.upper():
                        recommendations.append('Analyze query execution plans for optimization')
                        recommendations.append('Consider adding indexes or query rewrites')

                # Generate summary
                num_data_points = int(duration_seconds / period)
                avg_load = total_load / num_data_points if num_data_points > 0 else 0

                summary = (
                    f"During the {int(duration_seconds/60)} minute incident window, "
                    f"the database experienced an average load of {avg_load:.2f} AAS "
                    f"with a peak of {peak_load:.2f} AAS. "
                )
                if sorted_waits:
                    summary += f"Primary wait event was '{sorted_waits[0].wait_event}' ({sorted_waits[0].wait_category}). "
                if sorted_sql:
                    summary += f"Top query was: {sorted_sql[0].sql_text[:80]}..."

                result = IncidentAnalysisResult(
                    db_resource_id=db_resource_id,
                    start_time=start_dt,
                    end_time=end_dt,
                    summary=summary,
                    total_db_load=round(total_load, 4),
                    peak_db_load=round(peak_load, 4),
                    top_sql=sorted_sql[:5],
                    top_wait_events=sorted_waits[:5],
                    recommendations=recommendations,
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error analyzing database incident: {str(e)}')
                return f'{{"error": "{str(e)}"}}'

        @mcp.tool(name='get-sql-details')
        async def get_sql_details(
            ctx: Context,
            db_resource_id: str = Field(
                ...,
                description='The DbiResourceId from list-databases-with-insights.',
            ),
            sql_id: str = Field(
                ...,
                description='The SQL ID to get details for (from get-database-top-sql or analyze-database-incident).',
            ),
            region: str = Field(
                'us-east-1',
                description='AWS region to query. Defaults to us-east-1.',
            ),
        ) -> str:
            """Get full SQL text for a specific SQL ID.

            ## When to Use This Tool
            Use this tool when you have a SQL ID (from get-database-top-sql or
            analyze-database-incident) and need to see the full, untruncated SQL text.

            ## Usage Requirements
            - You need a SQL ID from a previous call to get-database-top-sql or similar
            - The database must have Performance Insights enabled
            """
            try:
                pi_client = self._get_pi_client(region)

                response = pi_client.describe_dimension_keys(
                    ServiceType='RDS',
                    Identifier=db_resource_id,
                    StartTime=datetime.now(timezone.utc) - timedelta(hours=1),
                    EndTime=datetime.now(timezone.utc),
                    Metric='db.load.avg',
                    GroupBy={'Group': 'db.sql', 'Dimensions': ['db.sql.statement'], 'Limit': 25},
                    Filter={'db.sql.id': sql_id},
                )

                sql_text = 'SQL not found'
                sql_tokenized_id = None

                for key in response.get('Keys', []):
                    dimensions = key.get('Dimensions', {})
                    if 'db.sql.statement' in dimensions:
                        sql_text = dimensions['db.sql.statement']
                    if 'db.sql.tokenized_id' in dimensions:
                        sql_tokenized_id = dimensions['db.sql.tokenized_id']

                result = SqlDetails(
                    sql_id=sql_id,
                    sql_text=sql_text,
                    sql_tokenized_id=sql_tokenized_id,
                    db_resource_id=db_resource_id,
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error getting SQL details: {str(e)}')
                return f'{{"error": "{str(e)}"}}'

        @mcp.tool(name='get-database-counters')
        async def get_database_counters(
            ctx: Context,
            db_resource_id: str = Field(
                ...,
                description='The DbiResourceId from list-databases-with-insights.',
            ),
            start_time: str = Field(
                ...,
                description='ISO 8601 formatted start time.',
            ),
            end_time: str = Field(
                ...,
                description='ISO 8601 formatted end time.',
            ),
            region: str = Field(
                'us-east-1',
                description='AWS region to query. Defaults to us-east-1.',
            ),
        ) -> str:
            """Get OS-level counter metrics from Performance Insights.

            ## When to Use This Tool
            Use this tool to get system-level metrics that correlate with database load:
            - CPU utilization
            - Memory usage
            - Disk I/O (IOPS and throughput)
            - Network I/O

            ## Why Use This Instead of CloudWatch Metrics?
            - PI counters can be correlated with SQL statements and wait events
            - Finer granularity in some cases
            - Part of the same PI analysis workflow
            """
            try:
                pi_client = self._get_pi_client(region)

                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

                duration_seconds = (end_dt - start_dt).total_seconds()
                if duration_seconds <= 3600:
                    period = 60
                elif duration_seconds <= 86400:
                    period = 300
                else:
                    period = 3600

                # Use db.load metrics which are available across all engines
                # OS-level counters may not be available on all instance types
                metric_queries = [
                    {'Metric': 'db.load.avg'},
                ]

                response = pi_client.get_resource_metrics(
                    ServiceType='RDS',
                    Identifier=db_resource_id,
                    MetricQueries=metric_queries,
                    StartTime=start_dt,
                    EndTime=end_dt,
                    PeriodInSeconds=period,
                )

                # Extract db.load data
                load_values = []
                for m in response.get('MetricList', []):
                    if m.get('Key', {}).get('Metric') == 'db.load.avg':
                        load_values = [dp['Value'] for dp in m.get('DataPoints', []) if 'Value' in dp]
                        break

                # For OS-level metrics, try to get them but handle gracefully if not available
                os_metrics = {}
                try:
                    os_response = pi_client.get_resource_metrics(
                        ServiceType='RDS',
                        Identifier=db_resource_id,
                        MetricQueries=[
                            {'Metric': 'os.cpuUtilization.total.avg'},
                            {'Metric': 'os.memory.free.avg'},
                        ],
                        StartTime=start_dt,
                        EndTime=end_dt,
                        PeriodInSeconds=period,
                    )
                    for m in os_response.get('MetricList', []):
                        metric_name = m.get('Key', {}).get('Metric', '')
                        values = [dp['Value'] for dp in m.get('DataPoints', []) if 'Value' in dp]
                        if values:
                            os_metrics[metric_name] = values
                except Exception:
                    pass  # OS metrics not available for this engine/instance type

                def make_counter(name, values):
                    if not values:
                        return None
                    return CounterMetric(
                        metric_name=name,
                        avg_value=round(sum(values) / len(values), 2),
                        max_value=round(max(values), 2),
                        min_value=round(min(values), 2),
                    )

                # Build additional_metrics list, filtering out None values
                db_load_counter = make_counter('db_load', load_values)
                additional_metrics_list: list[CounterMetric] = []
                if db_load_counter is not None:
                    additional_metrics_list.append(db_load_counter)

                result = DatabaseCountersResult(
                    db_resource_id=db_resource_id,
                    start_time=start_dt,
                    end_time=end_dt,
                    cpu_percent=make_counter('cpu', os_metrics.get('os.cpuUtilization.total.avg', [])),
                    memory_percent=make_counter('memory', os_metrics.get('os.memory.free.avg', [])),
                    read_iops=None,
                    write_iops=None,
                    read_throughput=None,
                    write_throughput=None,
                    additional_metrics=additional_metrics_list,
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error getting database counters: {str(e)}')
                return f'{{"error": "{str(e)}"}}'

        @mcp.tool(name='get-wait-event-breakdown')
        async def get_wait_event_breakdown(
            ctx: Context,
            db_resource_id: str = Field(
                ...,
                description='The DbiResourceId from list-databases-with-insights.',
            ),
            start_time: str = Field(
                ...,
                description='ISO 8601 formatted start time.',
            ),
            end_time: str = Field(
                ...,
                description='ISO 8601 formatted end time.',
            ),
            region: str = Field(
                'us-east-1',
                description='AWS region to query. Defaults to us-east-1.',
            ),
            limit: int = Field(
                10,
                description='Maximum number of wait events to return (1-25).',
            ),
        ) -> str:
            """Get detailed wait event breakdown with interpretations.

            ## When to Use This Tool
            Use this tool to understand WHAT the database is waiting on:
            - IO waits: Storage is the bottleneck
            - Lock waits: Contention between queries
            - CPU waits: Compute-bound queries
            - Network waits: Client or network issues

            ## Output Format
            Returns wait events with:
            - Category (IO, Lock, CPU, etc.)
            - Contribution to load
            - Interpretation of what this wait means
            """
            try:
                pi_client = self._get_pi_client(region)

                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

                duration_seconds = (end_dt - start_dt).total_seconds()
                if duration_seconds <= 3600:
                    period = 60
                elif duration_seconds <= 86400:
                    period = 300
                else:
                    period = 3600

                response = pi_client.get_resource_metrics(
                    ServiceType='RDS',
                    Identifier=db_resource_id,
                    MetricQueries=[{
                        'Metric': 'db.load.avg',
                        'GroupBy': {'Group': 'db.wait_event', 'Limit': min(limit, 25)},
                    }],
                    StartTime=start_dt,
                    EndTime=end_dt,
                    PeriodInSeconds=period,
                )

                wait_interpretations = {
                    'CPU': 'Query is compute-bound. Review query execution plans and consider optimization.',
                    'IO': 'Storage I/O bottleneck. Check IOPS limits, consider provisioned IOPS or storage tier upgrade.',
                    'Lock': 'Lock contention between sessions. Check for blocking queries, long transactions, or deadlocks.',
                    'LWLock': 'PostgreSQL internal lock wait. May indicate shared buffer pressure or high concurrency.',
                    'BufferIO': 'Buffer I/O wait. Database is waiting for data to be read from disk into memory.',
                    'Client': 'Waiting for client response. Check network latency or application processing time.',
                    'Commit': 'Transaction commit wait. Check storage write performance and transaction patterns.',
                    'IPC': 'Inter-process communication. Often related to parallel query execution.',
                    'Timeout': 'Timeout or idle wait. Usually application-driven sleep or polling.',
                    'Network': 'Network-related wait. Check network connectivity and bandwidth.',
                }

                wait_events = []
                seen_waits = set()
                total_load = 0.0

                for metric_list in response.get('MetricList', []):
                    dimensions = metric_list.get('Key', {}).get('Dimensions', {})
                    wait_name = dimensions.get('db.wait_event.name', '')
                    wait_type = dimensions.get('db.wait_event.type', 'Unknown')

                    if not wait_name or wait_name in seen_waits:
                        continue
                    seen_waits.add(wait_name)

                    values = [dp['Value'] for dp in metric_list.get('DataPoints', []) if 'Value' in dp]
                    if not values:
                        continue

                    wait_total = sum(values)
                    total_load += wait_total

                    interpretation = wait_interpretations.get(
                        wait_type,
                        f'{wait_type} wait event. Consult database documentation for details.'
                    )

                    wait_events.append(WaitEventDetail(
                        wait_event=wait_name,
                        wait_category=wait_type,
                        total_load=round(wait_total, 4),
                        avg_load=round(wait_total / len(values), 4),
                        interpretation=interpretation,
                    ))

                sorted_waits = sorted(wait_events, key=lambda x: x.total_load, reverse=True)

                # Generate summary
                summary = f"Analyzed {len(sorted_waits)} distinct wait events. "
                if sorted_waits:
                    top = sorted_waits[0]
                    pct = (top.total_load / total_load * 100) if total_load > 0 else 0
                    summary += f"Top wait: '{top.wait_event}' ({top.wait_category}) accounting for {pct:.1f}% of wait time."

                result = WaitEventBreakdown(
                    db_resource_id=db_resource_id,
                    start_time=start_dt,
                    end_time=end_dt,
                    total_wait_load=round(total_load, 4),
                    wait_events=sorted_waits[:limit],
                    summary=summary,
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error getting wait event breakdown: {str(e)}')
                return f'{{"error": "{str(e)}"}}'

        @mcp.tool(name='compare-database-periods')
        async def compare_database_periods(
            ctx: Context,
            db_resource_id: str = Field(
                ...,
                description='The DbiResourceId from list-databases-with-insights.',
            ),
            baseline_start: str = Field(
                ...,
                description='ISO 8601 formatted start time for baseline (normal) period.',
            ),
            baseline_end: str = Field(
                ...,
                description='ISO 8601 formatted end time for baseline period.',
            ),
            incident_start: str = Field(
                ...,
                description='ISO 8601 formatted start time for incident period.',
            ),
            incident_end: str = Field(
                ...,
                description='ISO 8601 formatted end time for incident period.',
            ),
            region: str = Field(
                'us-east-1',
                description='AWS region to query. Defaults to us-east-1.',
            ),
        ) -> str:
            """Compare database load between two time periods.

            ## When to Use This Tool
            Use this tool to identify WHAT CHANGED between a normal baseline period
            and an incident period:
            - New SQL queries that appeared during incident
            - SQL queries that increased significantly in load
            - New wait events during incident

            ## Best Practice
            Choose a baseline period that represents normal operation, ideally:
            - Same time of day as incident (to account for daily patterns)
            - Recent enough to reflect current workload
            """
            try:
                pi_client = self._get_pi_client(region)

                baseline_start_dt = datetime.fromisoformat(baseline_start.replace('Z', '+00:00'))
                baseline_end_dt = datetime.fromisoformat(baseline_end.replace('Z', '+00:00'))
                incident_start_dt = datetime.fromisoformat(incident_start.replace('Z', '+00:00'))
                incident_end_dt = datetime.fromisoformat(incident_end.replace('Z', '+00:00'))

                def get_period_data(start_dt, end_dt):
                    duration = (end_dt - start_dt).total_seconds()
                    period = 60 if duration <= 3600 else (300 if duration <= 86400 else 3600)

                    sql_resp = pi_client.get_resource_metrics(
                        ServiceType='RDS',
                        Identifier=db_resource_id,
                        MetricQueries=[{
                            'Metric': 'db.load.avg',
                            'GroupBy': {'Group': 'db.sql', 'Limit': 25},
                        }],
                        StartTime=start_dt,
                        EndTime=end_dt,
                        PeriodInSeconds=period,
                    )

                    wait_resp = pi_client.get_resource_metrics(
                        ServiceType='RDS',
                        Identifier=db_resource_id,
                        MetricQueries=[{
                            'Metric': 'db.load.avg',
                            'GroupBy': {'Group': 'db.wait_event', 'Limit': 15},
                        }],
                        StartTime=start_dt,
                        EndTime=end_dt,
                        PeriodInSeconds=period,
                    )

                    sql_data = {}
                    total_load = 0.0
                    for m in sql_resp.get('MetricList', []):
                        dims = m.get('Key', {}).get('Dimensions', {})
                        sql_id = dims.get('db.sql.id', '')
                        sql_text = dims.get('db.sql.statement', '')
                        if sql_id:
                            values = [dp['Value'] for dp in m.get('DataPoints', []) if 'Value' in dp]
                            load = sum(values)
                            total_load += load
                            sql_data[sql_id] = {'text': sql_text[:300], 'load': load, 'count': len(values)}

                    wait_data = {}
                    for m in wait_resp.get('MetricList', []):
                        dims = m.get('Key', {}).get('Dimensions', {})
                        wait_name = dims.get('db.wait_event.name', '')
                        wait_type = dims.get('db.wait_event.type', 'Unknown')
                        if wait_name:
                            values = [dp['Value'] for dp in m.get('DataPoints', []) if 'Value' in dp]
                            wait_data[wait_name] = {'type': wait_type, 'load': sum(values)}

                    return sql_data, wait_data, total_load

                baseline_sql, baseline_waits, baseline_load = get_period_data(baseline_start_dt, baseline_end_dt)
                incident_sql, incident_waits, incident_load = get_period_data(incident_start_dt, incident_end_dt)

                # Find new SQL queries
                new_sql = []
                for sql_id, data in incident_sql.items():
                    if sql_id not in baseline_sql:
                        new_sql.append(TopSqlStatement(
                            sql_id=sql_id,
                            sql_text=data['text'],
                            total_load=round(data['load'], 4),
                            avg_load=round(data['load'] / data['count'], 4) if data['count'] else 0,
                        ))

                # Find increased SQL queries (>2x increase)
                increased_sql = []
                for sql_id, data in incident_sql.items():
                    if sql_id in baseline_sql:
                        baseline_val = baseline_sql[sql_id]['load']
                        if baseline_val > 0 and data['load'] > baseline_val * 2:
                            increased_sql.append(TopSqlStatement(
                                sql_id=sql_id,
                                sql_text=data['text'],
                                total_load=round(data['load'], 4),
                                avg_load=round(data['load'] / data['count'], 4) if data['count'] else 0,
                            ))

                # Find new wait events
                new_waits = []
                for wait_name, data in incident_waits.items():
                    if wait_name not in baseline_waits:
                        new_waits.append(WaitEventDetail(
                            wait_event=wait_name,
                            wait_category=data['type'],
                            total_load=round(data['load'], 4),
                            avg_load=round(data['load'], 4),
                        ))

                # Calculate change percent
                change_pct = ((incident_load - baseline_load) / baseline_load * 100) if baseline_load > 0 else 0

                # Generate summary
                summary = f"Load changed from {baseline_load:.2f} to {incident_load:.2f} AAS ({change_pct:+.1f}%). "
                if new_sql:
                    summary += f"Found {len(new_sql)} new SQL queries. "
                if increased_sql:
                    summary += f"Found {len(increased_sql)} SQL queries with >2x load increase. "
                if new_waits:
                    summary += f"Found {len(new_waits)} new wait events."

                result = PeriodComparison(
                    db_resource_id=db_resource_id,
                    baseline_start=baseline_start_dt,
                    baseline_end=baseline_end_dt,
                    incident_start=incident_start_dt,
                    incident_end=incident_end_dt,
                    baseline_load=round(baseline_load, 4),
                    incident_load=round(incident_load, 4),
                    load_change_percent=round(change_pct, 2),
                    new_sql_queries=sorted(new_sql, key=lambda x: x.total_load, reverse=True)[:5],
                    increased_sql_queries=sorted(increased_sql, key=lambda x: x.total_load, reverse=True)[:5],
                    new_wait_events=sorted(new_waits, key=lambda x: x.total_load, reverse=True)[:5],
                    summary=summary,
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error comparing database periods: {str(e)}')
                return f'{{"error": "{str(e)}"}}'

        @mcp.tool(name='get-database-resource-info')
        async def get_database_resource_info(
            ctx: Context,
            db_resource_id: str = Field(
                ...,
                description='The DbiResourceId from list-databases-with-insights.',
            ),
            region: str = Field(
                'us-east-1',
                description='AWS region to query. Defaults to us-east-1.',
            ),
        ) -> str:
            """Get database instance resource information.

            ## When to Use This Tool
            Use this tool to get instance metadata needed for load interpretation:
            - vCPU count: Critical for interpreting Average Active Sessions (AAS)
              - If AAS > vCPU count, database has CPU contention
            - Memory: Helps understand buffer pool capacity
            - Storage info: IOPS limits, storage type

            ## Example Interpretation
            If a database has 4 vCPUs and AAS = 6.0, that means on average
            6 sessions are active but only 4 can run concurrently, indicating
            contention and queueing.
            """
            try:
                # Get metadata from PI
                pi_client = self._get_pi_client(region)

                response = pi_client.get_resource_metadata(
                    ServiceType='RDS',
                    Identifier=db_resource_id,
                )

                metadata = response.get('Metadata', {})

                # Also get instance details from RDS for additional info
                rds_client = self._get_rds_client(region)
                db_identifier = None
                engine = metadata.get('Engine', 'unknown')
                engine_version = metadata.get('EngineVersion')
                vcpu = None
                memory_gb = None
                storage_type = None
                max_iops = None
                retention = None

                # Try to find instance by resource ID
                try:
                    paginator = rds_client.get_paginator('describe_db_instances')
                    for page in paginator.paginate():
                        for db in page['DBInstances']:
                            if db.get('DbiResourceId') == db_resource_id:
                                db_identifier = db['DBInstanceIdentifier']
                                engine = db.get('Engine', engine)
                                engine_version = db.get('EngineVersion', engine_version)
                                storage_type = db.get('StorageType')
                                max_iops = db.get('Iops')
                                retention = db.get('PerformanceInsightsRetentionPeriod')

                                # Estimate vCPU from instance class
                                instance_class = db.get('DBInstanceClass', '')
                                vcpu = self._estimate_vcpu(instance_class)
                                break
                except Exception as e:
                    logger.warning(f'Could not get RDS instance details: {e}')

                result = DatabaseResourceInfo(
                    db_resource_id=db_resource_id,
                    db_instance_identifier=db_identifier,
                    engine=engine,
                    engine_version=engine_version,
                    vcpu_count=vcpu,
                    memory_gb=memory_gb,
                    storage_type=storage_type,
                    max_iops=max_iops,
                    insights_retention_days=retention,
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error getting database resource info: {str(e)}')
                return f'{{"error": "{str(e)}"}}'

        logger.info(
            'Database Insights tools registered: list-databases-with-insights, '
            'get-database-load-metrics, get-database-top-sql, analyze-database-incident, '
            'get-sql-details, get-database-counters, get-wait-event-breakdown, '
            'compare-database-periods, get-database-resource-info'
        )

