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
    DatabaseInstance,
    DatabaseInsightsMetric,
    DatabaseLoadResult,
    DimensionKeyDetail,
    ListDatabasesResult,
)
from botocore.config import Config
from datetime import datetime
from dateutil import parser as dateutil_parser
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Literal


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

        logger.info('Database Insights tools registered: list-databases-with-insights, get-database-load-metrics')

