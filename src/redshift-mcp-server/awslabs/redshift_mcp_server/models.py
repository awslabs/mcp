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

"""Redshift MCP Server Pydantic models."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, Optional


class RedshiftCluster(BaseModel):
    """Information about a Redshift cluster or serverless workgroup."""

    identifier: str = Field(..., description='Unique identifier for the cluster/workgroup')
    type: str = Field(..., description='Type of cluster (provisioned or serverless)')
    status: str = Field(..., description='Current status of the cluster')
    database_name: str = Field(..., description='Default database name')
    endpoint: Optional[str] = Field(None, description='Connection endpoint')
    port: Optional[int] = Field(None, description='Connection port')
    vpc_id: Optional[str] = Field(None, description='VPC ID where the cluster resides')
    node_type: Optional[str] = Field(None, description='Node type (provisioned only)')
    number_of_nodes: Optional[int] = Field(None, description='Number of nodes (provisioned only)')
    creation_time: Optional[datetime] = Field(None, description='When the cluster was created')
    master_username: Optional[str] = Field(None, description='Master username for the cluster')
    publicly_accessible: Optional[bool] = Field(None, description='Whether publicly accessible')
    encrypted: Optional[bool] = Field(None, description='Whether the cluster is encrypted')
    tags: Optional[Dict[str, str]] = Field(
        default_factory=dict, description='Tags associated with the cluster'
    )


class RedshiftDatabase(BaseModel):
    """Information about a database in a Redshift cluster.

    Based on the SVV_REDSHIFT_DATABASES system view.
    """

    database_name: str = Field(..., description='The name of the database')
    database_owner: Optional[int] = Field(None, description='The database owner user ID')
    database_type: Optional[str] = Field(
        None, description='The type of database (local or shared)'
    )
    database_acl: Optional[str] = Field(
        None, description='Access control information (for internal use)'
    )
    database_options: Optional[str] = Field(None, description='The properties of the database')
    database_isolation_level: Optional[str] = Field(
        None,
        description='The isolation level of the database (Snapshot Isolation or Serializable)',
    )


class RedshiftSchema(BaseModel):
    """Information about a schema in a Redshift database.

    Based on the SVV_ALL_SCHEMAS system view.
    """

    database_name: str = Field(..., description='The name of the database where the schema exists')
    schema_name: str = Field(..., description='The name of the schema')
    schema_owner: Optional[int] = Field(None, description='The user ID of the schema owner')
    schema_type: Optional[str] = Field(
        None, description='The type of the schema (external, local, or shared)'
    )
    schema_acl: Optional[str] = Field(
        None, description='The permissions for the specified user or user group for the schema'
    )
    source_database: Optional[str] = Field(
        None, description='The name of the source database for external schema'
    )
    schema_option: Optional[str] = Field(
        None, description='The options of the schema (external schema attribute)'
    )


class RedshiftColumn(BaseModel):
    """Information about a column in a Redshift table.

    Based on SVV_REDSHIFT_COLUMNS and SVV_EXTERNAL_COLUMNS with UNION ALL.
    """

    database_name: str = Field(..., description='The name of the database')
    schema_name: str = Field(..., description='The name of the schema')
    table_name: str = Field(..., description='The name of the table')
    column_name: str = Field(..., description='The name of the column')
    ordinal_position: Optional[int] = Field(
        None, description='The position of the column in the table'
    )
    column_default: Optional[str] = Field(None, description='The default value of the column')
    is_nullable: Optional[str] = Field(
        None, description='Whether the column is nullable (yes or no)'
    )
    data_type: Optional[str] = Field(None, description='The data type of the column')
    character_maximum_length: Optional[int] = Field(
        None, description='The maximum number of characters in the column'
    )
    numeric_precision: Optional[int] = Field(None, description='The numeric precision')
    numeric_scale: Optional[int] = Field(None, description='The numeric scale')
    remarks: Optional[str] = Field(None, description='Remarks about the column')
    # Redshift-specific properties (from SVV_REDSHIFT_COLUMNS)
    redshift_encoding: Optional[str] = Field(None, description='Compression encoding')
    redshift_distkey: Optional[bool] = Field(
        None, description='Whether this column is the distribution key'
    )
    redshift_sortkey: Optional[int] = Field(
        None, description='Sort key position (0 if not a sort key, 1+ for position)'
    )
    # External table properties (from SVV_EXTERNAL_COLUMNS)
    external_type: Optional[str] = Field(None, description='External column type')
    external_part_key: Optional[int] = Field(
        None,
        description='Partition key order (0 if not a partition key, 1+ for partition key position)',
    )


class RedshiftTable(BaseModel):
    """Information about a table in a Redshift database.

    Based on SVV_REDSHIFT_TABLES and SVV_EXTERNAL_TABLES with UNION ALL.
    Additional metadata from PG_TABLES_SQL is fetched separately and merged.
    """

    database_name: str = Field(..., description='The name of the database where the table exists')
    schema_name: str = Field(..., description='The schema name for the table')
    table_name: str = Field(..., description='The name of the table')
    table_acl: Optional[str] = Field(
        None, description='The permissions for the specified user or user group for the table'
    )
    table_type: Optional[str] = Field(
        None,
        description='The type of the table (TABLE, EXTERNAL TABLE)',
    )
    remarks: Optional[str] = Field(None, description='Remarks about the table')
    # Redshift-specific properties (from PG_TABLES_SQL using pg_catalog tables)
    redshift_diststyle: Optional[str] = Field(
        None, description='Distribution style (KEY, EVEN, ALL, AUTO)'
    )
    redshift_sortkey1: Optional[str] = Field(None, description='Primary sort key column name')
    redshift_encoded: Optional[str] = Field(
        None, description='Whether the table has compression encoding (Y/N)'
    )
    redshift_tbl_rows: Optional[int] = Field(None, description='Approximate number of rows')
    redshift_size: Optional[int] = Field(None, description='Table size in MB')
    redshift_pct_used: Optional[float] = Field(
        None, description='Percentage of table capacity used'
    )
    redshift_stats_off: Optional[float] = Field(
        None, description='Percentage that table statistics are out of date'
    )
    redshift_skew_rows: Optional[float] = Field(
        None, description='Ratio of rows in largest slice to smallest slice'
    )
    # External table properties (from SVV_EXTERNAL_TABLES)
    external_location: Optional[str] = Field(None, description='External table location (S3 path)')
    external_parameters: Optional[str] = Field(
        None, description='External table parameters (JSON)'
    )
    # Column design information (only populated in execution plan analysis)
    columns: Optional[list[RedshiftColumn]] = Field(
        None, description='Column design information (only populated in execution plan analysis)'
    )


class QueryResult(BaseModel):
    """Result of a SQL query execution."""

    columns: list[str] = Field(..., description='List of column names in the result set')
    rows: list[list] = Field(..., description='List of rows, where each row is a list of values')
    row_count: int = Field(..., description='Number of rows returned')
    execution_time_ms: Optional[int] = Field(
        None, description='Query execution time in milliseconds'
    )
    query_id: str = Field(..., description='Unique identifier for the query execution')


class ExecutionPlanNode(BaseModel):
    """Individual node in the query execution plan tree."""

    node_id: int = Field(..., description='Unique node identifier')
    parent_node_id: Optional[int] = Field(None, description='Parent node ID')
    level: int = Field(..., description='Tree depth (0 = root)')
    operation: str = Field(..., description='Operation type')
    relation_name: Optional[str] = Field(None, description='Table or view name')
    prefix: Optional[str] = Field(None, description='Execution prefix (e.g., XN)')
    distribution_type: Optional[str] = Field(None, description='Data distribution method')
    cost_startup: Optional[float] = Field(None, description='Startup cost')
    cost_total: Optional[float] = Field(None, description='Total cost')
    rows: Optional[int] = Field(None, description='Estimated rows')
    width: Optional[int] = Field(None, description='Row width in bytes')
    scan_relid: Optional[int] = Field(None, description='Relation ID for scan operations')
    join_type: Optional[str] = Field(None, description='Join type (Inner, Left, etc.)')
    join_condition: Optional[str] = Field(None, description='Join condition')
    filter_condition: Optional[str] = Field(None, description='Filter condition')
    sort_key: Optional[str] = Field(None, description='Sort key info')
    agg_strategy: Optional[str] = Field(None, description='Aggregation strategy')
    data_movement: Optional[str] = Field(None, description='Data movement type')
    output_columns: Optional[list[str]] = Field(None, description='Output columns')


class ExecutionPlan(BaseModel):
    """Result of an EXPLAIN VERBOSE query execution."""

    query_id: str = Field(..., description='Explain execution identifier')
    explained_query: str = Field(..., description='Original SQL query')
    planning_time_ms: Optional[int] = Field(None, description='Planning time in milliseconds')
    plan_nodes: list[ExecutionPlanNode] = Field(..., description='Execution plan nodes')
    table_designs: list[RedshiftTable] = Field(
        default_factory=list, description='Table design information for referenced tables'
    )
    human_readable_plan: Optional[str] = Field(
        None, description='Human-readable plan text (show only if fits on screen)'
    )
    suggestions: list[str] = Field(
        default_factory=list, description='Performance optimization suggestions'
    )
