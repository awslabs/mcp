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
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class DatabaseEngine(str, Enum):
    """Supported database engines for Performance Insights."""

    AURORA_MYSQL = 'aurora-mysql'
    AURORA_POSTGRESQL = 'aurora-postgresql'
    MYSQL = 'mysql'
    POSTGRESQL = 'postgres'
    MARIADB = 'mariadb'
    SQLSERVER = 'sqlserver'
    ORACLE = 'oracle'
    DOCDB = 'docdb'


class MetricType(str, Enum):
    """Types of Performance Insights metrics."""

    DB_LOAD = 'db.load'
    DB_LOAD_CPU = 'db.load.cpu'
    DB_LOAD_IO = 'db.load.io'
    DB_LOAD_WAIT = 'db.load.wait'


class GroupByDimension(str, Enum):
    """Dimensions to group database load by."""

    SQL = 'db.sql'
    WAIT_EVENT = 'db.wait_event'
    USER = 'db.user'
    HOST = 'db.host'
    APPLICATION = 'db.application'
    SESSION_TYPE = 'db.session_type'


class DatabaseInstance(BaseModel):
    """Information about an RDS/Aurora database instance."""

    dbi_resource_id: str = Field(..., description='The immutable database resource identifier')
    db_instance_identifier: str = Field(..., description='The user-assigned database identifier')
    engine: DatabaseEngine = Field(..., description='The database engine type')
    engine_version: str = Field(..., description='The database engine version')
    insights_enabled: bool = Field(..., description='Whether Performance Insights is enabled')
    insights_retention_days: Optional[int] = Field(
        None, description='Performance Insights retention period in days'
    )
    instance_class: Optional[str] = Field(None, description='The DB instance class')
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
    vcpu_count: Optional[int] = Field(
        None, description='Number of vCPUs (load > vCPUs indicates contention)'
    )
    top_dimensions: List[DimensionKeyDetail] = Field(
        default_factory=list, description='Top contributors by the requested dimension'
    )
    overall_metrics: List[DatabaseInsightsMetric] = Field(
        default_factory=list, description='Overall database load time series'
    )


class ListDatabasesResult(BaseModel):
    """Result of listing databases with Performance Insights enabled."""

    databases: List[DatabaseInstance] = Field(
        default_factory=list, description='List of databases with their insights status'
    )
    region: str = Field(..., description='AWS region queried')
    total_count: int = Field(..., description='Total number of databases found')
    insights_enabled_count: int = Field(
        ..., description='Number of databases with Performance Insights enabled'
    )

