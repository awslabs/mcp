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

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class KeyspaceInfo:
    """Information about a Cassandra keyspace."""

    name: str
    replication_strategy: str = ''
    replication_factor: int = 0


@dataclass
class ColumnInfo:
    """Information about a Cassandra column."""

    name: str
    type: str
    is_primary_key: bool = False
    is_partition_key: bool = False
    is_clustering_column: bool = False


@dataclass
class TableInfo:
    """Information about a Cassandra table."""

    name: str
    keyspace: str
    columns: List[ColumnInfo] = field(default_factory=list)


@dataclass
class QueryResult:
    """Result of a CQL query execution."""

    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryAnalysisResult:
    """Result of a query performance analysis."""

    query: str
    table_name: str = ''
    uses_partition_key: bool = False
    uses_clustering_columns: bool = False
    uses_allow_filtering: bool = False
    uses_secondary_index: bool = False
    is_full_table_scan: bool = False
    recommendations: List[str] = field(default_factory=list)
    performance_assessment: str = ''
