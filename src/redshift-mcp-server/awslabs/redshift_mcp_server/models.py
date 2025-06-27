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


class RedshiftTable(BaseModel):
    """Information about a table in a Redshift database.

    Based on the SVV_ALL_TABLES system view.
    """

    database_name: str = Field(..., description='The name of the database where the table exists')
    schema_name: str = Field(..., description='The schema name for the table')
    table_name: str = Field(..., description='The name of the table')
    table_acl: Optional[str] = Field(
        None, description='The permissions for the specified user or user group for the table'
    )
    table_type: Optional[str] = Field(
        None,
        description='The type of the table (views, base tables, external tables, shared tables)',
    )
    remarks: Optional[str] = Field(None, description='Remarks about the table')


class RedshiftColumn(BaseModel):
    """Information about a column in a Redshift table.

    Based on the SVV_ALL_COLUMNS system view.
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


class QueryResult(BaseModel):
    """Result of a SQL query execution."""

    columns: list[str] = Field(..., description='List of column names in the result set')
    rows: list[list] = Field(..., description='List of rows, where each row is a list of values')
    row_count: int = Field(..., description='Number of rows returned')
    execution_time_ms: Optional[int] = Field(
        None, description='Query execution time in milliseconds'
    )
    query_id: str = Field(..., description='Unique identifier for the query execution')
