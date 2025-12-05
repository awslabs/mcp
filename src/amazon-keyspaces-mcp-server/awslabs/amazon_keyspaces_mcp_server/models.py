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
"""Data models for Keyspaces MCP Server."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator


@dataclass
class KeyspaceInfo:
    """Information about a Cassandra keyspace.

    This model represents metadata about a keyspace in Cassandra or Amazon Keyspaces,
    including its replication configuration.

    Attributes:
        name: The name of the keyspace.
        replication_strategy: The replication strategy class (e.g., SimpleStrategy,
            NetworkTopologyStrategy).
        replication_factor: The number of replicas for the keyspace data.
    """

    name: str
    replication_strategy: str = ''
    replication_factor: int = 0


@dataclass
class ColumnInfo:
    """Information about a Cassandra column.

    This model represents metadata about a column in a Cassandra table,
    including its data type and role in the primary key structure.

    Attributes:
        name: The name of the column.
        type: The CQL data type of the column (e.g., text, int, uuid).
        is_primary_key: Whether this column is part of the primary key.
        is_partition_key: Whether this column is part of the partition key.
        is_clustering_column: Whether this column is a clustering column.
    """

    name: str
    type: str
    is_primary_key: bool = False
    is_partition_key: bool = False
    is_clustering_column: bool = False


@dataclass
class TableInfo:
    """Information about a Cassandra table.

    This model represents metadata about a table in Cassandra or Amazon Keyspaces,
    including its columns and schema information.

    Attributes:
        name: The name of the table.
        keyspace: The keyspace containing this table.
        columns: List of column metadata for the table.
    """

    name: str
    keyspace: str
    columns: List[ColumnInfo] = field(default_factory=list)


@dataclass
class QueryResult:
    """Result of a CQL query execution.

    This model encapsulates the results returned from executing a CQL query,
    including the data rows and execution metadata.

    Attributes:
        columns: List of column names in the result set.
        rows: List of result rows, where each row is a dictionary mapping
            column names to values.
        row_count: Total number of rows returned by the query.
        execution_info: Additional execution metadata such as queried host
            and performance metrics.
    """

    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryAnalysisResult:
    """Result of a query performance analysis.

    This model contains the analysis results for a CQL query, identifying
    potential performance issues and providing optimization recommendations.

    Attributes:
        query: The CQL query that was analyzed.
        table_name: The name of the table being queried.
        uses_partition_key: Whether the query filters on the partition key.
        uses_clustering_columns: Whether the query uses clustering columns in WHERE clause.
        uses_allow_filtering: Whether the query uses ALLOW FILTERING clause.
        uses_secondary_index: Whether the query uses a secondary index.
        is_full_table_scan: Whether the query requires a full table scan.
        recommendations: List of optimization recommendations for the query.
        performance_assessment: Overall assessment of the query's performance characteristics.
    """

    query: str
    table_name: str = ''
    uses_partition_key: bool = False
    uses_clustering_columns: bool = False
    uses_allow_filtering: bool = False
    uses_secondary_index: bool = False
    is_full_table_scan: bool = False
    recommendations: List[str] = field(default_factory=list)
    performance_assessment: str = ''


# Pydantic models for input validation
class KeyspaceInput(BaseModel):
    """Validated keyspace input."""
    keyspace: str = Field(
        ...,
        min_length=1,
        max_length=48,
        pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$',
        description='Keyspace name (alphanumeric and underscore only)'
    )


class TableInput(BaseModel):
    """Validated table input."""
    keyspace: str = Field(
        ...,
        min_length=1,
        max_length=48,
        pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$'
    )
    table: str = Field(
        ...,
        min_length=1,
        max_length=48,
        pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$'
    )


class QueryInput(BaseModel):
    """Validated query input."""
    keyspace: str = Field(
        ...,
        min_length=1,
        max_length=48,
        pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$'
    )
    query: str = Field(..., min_length=1, max_length=10000)

    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Strip hidden unicode and control characters."""
        v = re.sub(r'[\u200B-\u200D\uFEFF\u0000-\u001F\u007F-\u009F]', '', v)
        return v.strip()


class ResourceArnInput(BaseModel):
    """Validated resource ARN input."""
    resource_arn: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description='ARN of the resource (keyspace or table)'
    )


