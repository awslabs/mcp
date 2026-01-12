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

import boto3
import os
from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
from awslabs.cloudwatch_mcp_server.database_insights.models import (
    DatabaseEngine,
    DatabaseInstance,
    DatabaseInsightsMetric,
    DatabaseLoadResult,
    DimensionKeyDetail,
    GroupByDimension,
    ListDatabasesResult,
)
from botocore.config import Config
from datetime import datetime, timedelta, timezone
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import List, Literal, Optional


class DatabaseInsightsTools:
    """Database Insights (Performance Insights) tools for MCP server."""

    def __init__(self):
        """Initialize the Database Insights tools."""
        logger.info('DatabaseInsightsTools initialized')

    def _get_rds_client(self, region: str):
        """Create an RDS client for the specified region."""
        config = Config(user_agent_extra=f'awslabs/mcp/cloudwatch-mcp-server/{MCP_SERVER_VERSION}')
        try:
            if aws_profile := os.environ.get('AWS_PROFILE'):
                return boto3.Session(profile_name=aws_profile, region_name=region).client(
                    'rds', config=config
                )
            else:
                return boto3.Session(region_name=region).client('rds', config=config)
        except Exception as e:
            logger.error(f'Error creating RDS client for region {region}: {str(e)}')
            raise

    def _get_pi_client(self, region: str):
        """Create a Performance Insights client for the specified region."""
        config = Config(user_agent_extra=f'awslabs/mcp/cloudwatch-mcp-server/{MCP_SERVER_VERSION}')
        try:
            if aws_profile := os.environ.get('AWS_PROFILE'):
                return boto3.Session(profile_name=aws_profile, region_name=region).client(
                    'pi', config=config
                )
            else:
                return boto3.Session(region_name=region).client('pi', config=config)
        except Exception as e:
            logger.error(f'Error creating PI client for region {region}: {str(e)}')
            raise

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
            - insights_enabled_count: How many have Performance Insights enabled
            """
            try:
                rds_client = self._get_rds_client(region)
                paginator = rds_client.get_paginator('describe_db_instances')

                databases = []
                for page in paginator.paginate():
                    for db in page['DBInstances']:
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

                result = ListDatabasesResult(
                    databases=databases,
                    region=region,
                    total_count=len(databases) if include_disabled else len([d for d in databases if d.insights_enabled]),
                    insights_enabled_count=len([d for d in databases if d.insights_enabled]),
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error listing databases: {str(e)}')
                return f'{{"error": "{str(e)}"}}'

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
            - db_load_avg: Average Active Sessions (AAS) - if > vCPU count, there's contention
            - group_by=db.sql: Shows which SQL queries consume the most database time
            - group_by=db.wait_event: Shows what the database is waiting on
              - IO:* events indicate storage bottlenecks
              - Lock:* events indicate locking/blocking issues
              - CPU events indicate compute-bound queries
            """
            try:
                pi_client = self._get_pi_client(region)

                # Parse time strings
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

                # Calculate appropriate period (minimum 60 seconds for PI)
                duration_seconds = (end_dt - start_dt).total_seconds()
                if duration_seconds <= 3600:  # 1 hour or less
                    period = 60
                elif duration_seconds <= 86400:  # 1 day or less
                    period = 300
                else:
                    period = 3600

                # Build metric queries
                metric_queries = [
                    {
                        'Metric': 'db.load.avg',
                        'GroupBy': {'Group': group_by, 'Limit': min(limit, 25)},
                    }
                ]

                response = pi_client.get_resource_metrics(
                    ServiceType='RDS',
                    Identifier=db_resource_id,
                    MetricQueries=metric_queries,
                    StartTime=start_dt,
                    EndTime=end_dt,
                    PeriodInSeconds=period,
                )

                # Process response
                top_dimensions = []
                overall_values = []

                for metric_list in response.get('MetricList', []):
                    for key in metric_list.get('Key', {}).get('Dimensions', {}).items():
                        dim_name, dim_value = key
                        data_points = []
                        total = 0.0
                        for dp in metric_list.get('DataPoints', []):
                            if 'Value' in dp:
                                total += dp['Value']
                                data_points.append(DatabaseInsightsMetric(
                                    timestamp=dp['Timestamp'],
                                    value=dp['Value'],
                                ))
                        top_dimensions.append(DimensionKeyDetail(
                            dimension=dim_name,
                            value=str(dim_value)[:200],  # Truncate long SQL
                            total=total,
                            data_points=data_points[:10],  # Limit data points
                        ))

                # Calculate summary stats
                all_values = [dp.value for dim in top_dimensions for dp in dim.data_points]
                db_load_avg = sum(all_values) / len(all_values) if all_values else 0.0
                db_load_max = max(all_values) if all_values else 0.0

                result = DatabaseLoadResult(
                    db_resource_id=db_resource_id,
                    start_time=start_dt,
                    end_time=end_dt,
                    period_seconds=period,
                    db_load_avg=round(db_load_avg, 3),
                    db_load_max=round(db_load_max, 3),
                    top_dimensions=sorted(top_dimensions, key=lambda x: x.total, reverse=True),
                )
                return result.model_dump_json(indent=2)

            except Exception as e:
                logger.error(f'Error getting database load metrics: {str(e)}')
                return f'{{"error": "{str(e)}"}}'

        logger.info('Database Insights tools registered: list-databases-with-insights, get-database-load-metrics')

