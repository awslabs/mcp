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

"""Data models for Database Insights (Performance Insights) MCP tools."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional


class DatabaseInstance(BaseModel):
    """Information about an RDS/Aurora database instance."""

    dbi_resource_id: str = Field(..., description='The immutable database resource identifier')
    db_instance_identifier: str = Field(..., description='The user-assigned database identifier')
    engine: str = Field(..., description='The database engine type (e.g., mysql, postgres, aurora-mysql)')
    engine_version: str = Field(..., description='The database engine version')
    insights_enabled: bool = Field(..., description='Whether Performance Insights is enabled')
    insights_retention_days: Optional[int] = Field(
        default=None, description='Performance Insights retention period in days'
    )
    instance_class: Optional[str] = Field(default=None, description='The DB instance class')
    region: str = Field(..., description='AWS region where the instance is located')


class DatabaseInsightsMetric(BaseModel):
    """A single metric data point from Performance Insights."""

    timestamp: datetime = Field(..., description='The timestamp of the metric')
    value: float = Field(..., description='The metric value (Average Active Sessions)')


class DimensionKeyDetail(BaseModel):
    """Details about a dimension key (e.g., a specific SQL statement or wait event)."""

    dimension: str = Field(..., description='The dimension name (e.g., db.sql, db.wait_event)')
    value: str = Field(..., description='The dimension value (e.g., SQL text, wait event name)')
    total: float = Field(..., description='Total contribution to database load (AAS)')
    data_points: List[DatabaseInsightsMetric] = Field(
        default_factory=list, description='Time series data for this dimension'
    )


class DatabaseLoadResult(BaseModel):
    """Result of a database load metrics query."""

    db_resource_id: str = Field(..., description='The database resource identifier')
    start_time: datetime = Field(..., description='Query start time')
    end_time: datetime = Field(..., description='Query end time')
    period_seconds: int = Field(..., description='The period between data points in seconds')
    db_load_avg: float = Field(..., description='Average database load (AAS) over the period')
    db_load_max: float = Field(..., description='Maximum database load (AAS) over the period')
    top_dimensions: List[DimensionKeyDetail] = Field(
        default_factory=list, description='Top contributors by the requested dimension'
    )
    overall_metrics: List[DatabaseInsightsMetric] = Field(
        default_factory=list, description='Overall database load time series'
    )


class ListDatabasesResult(BaseModel):
    """Result of listing databases with Performance Insights enabled.

    Note: `total_count` is the total number of database instances in the region
    prior to filtering by `include_disabled`.
    """

    databases: List[DatabaseInstance] = Field(
        default_factory=list, description='List of databases with their insights status'
    )
    region: str = Field(..., description='AWS region queried')
    total_count: int = Field(
        ..., description='Total number of databases in the region (unfiltered by include_disabled)'
    )
    insights_enabled_count: int = Field(
        ..., description='Number of databases with Performance Insights enabled'
    )


class TopSqlStatement(BaseModel):
    """A top SQL statement contributing to database load."""

    sql_id: str = Field(..., description='Unique identifier for the SQL statement')
    sql_text: str = Field(..., description='The SQL statement text (may be truncated)')
    total_load: float = Field(..., description='Total Average Active Sessions contribution')
    avg_load: float = Field(..., description='Average load per data point')
    execution_count: Optional[int] = Field(default=None, description='Number of executions if available')


class TopSqlResult(BaseModel):
    """Result of top SQL query analysis."""

    db_resource_id: str = Field(..., description='The database resource identifier')
    db_instance_identifier: Optional[str] = Field(default=None, description='The database instance name')
    start_time: datetime = Field(..., description='Query start time')
    end_time: datetime = Field(..., description='Query end time')
    total_db_load: float = Field(..., description='Total database load during the period')
    top_sql: List[TopSqlStatement] = Field(
        default_factory=list, description='Top SQL statements by load'
    )


class WaitEventDetail(BaseModel):
    """Details about a wait event contributing to database load."""

    wait_event: str = Field(..., description='The wait event name')
    wait_category: str = Field(..., description='Category of wait (IO, Lock, CPU, etc.)')
    total_load: float = Field(..., description='Total Average Active Sessions contribution')
    avg_load: float = Field(..., description='Average load per data point')
    interpretation: Optional[str] = Field(default=None, description='What this wait event typically means')


class IncidentAnalysisResult(BaseModel):
    """Comprehensive analysis of a database performance incident."""

    db_resource_id: str = Field(..., description='The database resource identifier')
    db_instance_identifier: Optional[str] = Field(default=None, description='The database instance name')
    start_time: datetime = Field(..., description='Incident window start time')
    end_time: datetime = Field(..., description='Incident window end time')
    summary: str = Field(..., description='AI-friendly summary of the incident')
    total_db_load: float = Field(..., description='Total database load during incident')
    peak_db_load: float = Field(..., description='Peak database load during incident')
    top_sql: List[TopSqlStatement] = Field(
        default_factory=list, description='Top SQL statements during incident'
    )
    top_wait_events: List[WaitEventDetail] = Field(
        default_factory=list, description='Top wait events during incident'
    )
    recommendations: List[str] = Field(
        default_factory=list, description='Suggested actions based on the analysis'
    )


class SqlDetails(BaseModel):
    """Full details for a SQL statement."""

    sql_id: str = Field(..., description='Unique identifier for the SQL statement')
    sql_text: str = Field(..., description='Full SQL statement text')
    sql_tokenized_id: Optional[str] = Field(default=None, description='Tokenized SQL ID if available')
    db_resource_id: str = Field(..., description='The database this SQL belongs to')


class CounterMetric(BaseModel):
    """A counter metric value."""

    metric_name: str = Field(..., description='Name of the counter metric')
    unit: Optional[str] = Field(default=None, description='Unit of the metric')
    avg_value: float = Field(..., description='Average value during the period')
    max_value: float = Field(..., description='Maximum value during the period')
    min_value: float = Field(..., description='Minimum value during the period')


class DatabaseCountersResult(BaseModel):
    """Result of database counter metrics query."""

    db_resource_id: str = Field(..., description='The database resource identifier')
    start_time: datetime = Field(..., description='Query start time')
    end_time: datetime = Field(..., description='Query end time')
    cpu_percent: Optional[CounterMetric] = Field(default=None, description='CPU utilization')
    memory_percent: Optional[CounterMetric] = Field(default=None, description='Memory utilization')
    read_iops: Optional[CounterMetric] = Field(default=None, description='Read IOPS')
    write_iops: Optional[CounterMetric] = Field(default=None, description='Write IOPS')
    read_throughput: Optional[CounterMetric] = Field(default=None, description='Read throughput')
    write_throughput: Optional[CounterMetric] = Field(default=None, description='Write throughput')
    additional_metrics: List[CounterMetric] = Field(
        default_factory=list, description='Additional counter metrics'
    )


class WaitEventBreakdown(BaseModel):
    """Detailed wait event breakdown with interpretations."""

    db_resource_id: str = Field(..., description='The database resource identifier')
    start_time: datetime = Field(..., description='Query start time')
    end_time: datetime = Field(..., description='Query end time')
    total_wait_load: float = Field(..., description='Total wait-related load')
    wait_events: List[WaitEventDetail] = Field(
        default_factory=list, description='Wait events with details'
    )
    summary: str = Field(..., description='Summary of wait event analysis')


class PeriodComparison(BaseModel):
    """Comparison between two time periods."""

    db_resource_id: str = Field(..., description='The database resource identifier')
    baseline_start: datetime = Field(..., description='Baseline period start')
    baseline_end: datetime = Field(..., description='Baseline period end')
    incident_start: datetime = Field(..., description='Incident period start')
    incident_end: datetime = Field(..., description='Incident period end')
    baseline_load: float = Field(..., description='Average load during baseline')
    incident_load: float = Field(..., description='Average load during incident')
    load_change_percent: float = Field(..., description='Percent change in load')
    new_sql_queries: List[TopSqlStatement] = Field(
        default_factory=list, description='SQL queries that appeared in incident but not baseline'
    )
    increased_sql_queries: List[TopSqlStatement] = Field(
        default_factory=list, description='SQL queries with significantly increased load'
    )
    new_wait_events: List[WaitEventDetail] = Field(
        default_factory=list, description='Wait events that appeared in incident but not baseline'
    )
    summary: str = Field(..., description='Summary of comparison findings')


class DatabaseResourceInfo(BaseModel):
    """Resource information for a database instance."""

    db_resource_id: str = Field(..., description='The database resource identifier')
    db_instance_identifier: Optional[str] = Field(default=None, description='The database instance name')
    engine: str = Field(..., description='Database engine type')
    engine_version: Optional[str] = Field(default=None, description='Database engine version')
    vcpu_count: Optional[int] = Field(default=None, description='Number of vCPUs (important for AAS interpretation)')
    memory_gb: Optional[float] = Field(default=None, description='Memory in GB')
    storage_type: Optional[str] = Field(default=None, description='Storage type')
    max_iops: Optional[int] = Field(default=None, description='Maximum provisioned IOPS')
    insights_retention_days: Optional[int] = Field(default=None, description='PI data retention period')

