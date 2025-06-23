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

"""Pydantic models for Athena MCP server."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any


class WorkgroupState(str, Enum):
    """Athena workgroup states."""

    ENABLED = 'ENABLED'
    DISABLED = 'DISABLED'


class TableType(str, Enum):
    """Athena table types."""

    EXTERNAL_TABLE = 'EXTERNAL_TABLE'
    MANAGED_TABLE = 'MANAGED_TABLE'
    VIRTUAL_VIEW = 'VIRTUAL_VIEW'


class DataCatalogType(str, Enum):
    """Data catalog types."""

    GLUE = 'GLUE'
    HIVE = 'HIVE'
    LAMBDA = 'LAMBDA'


class ColumnInfo(BaseModel):
    """Column information for query results."""

    name: str = Field(min_length=1, max_length=255, description='Column name')
    type: str = Field(min_length=1, description='Column data type')
    nullable: bool | None = Field(default=None, description='Whether column allows null values')
    precision: int | None = Field(default=None, ge=0, description='Numeric precision')
    scale: int | None = Field(default=None, ge=0, description='Numeric scale')


class QueryResults(BaseModel):
    """Query execution results with execution metadata."""

    column_info: list[ColumnInfo] = Field(description='Column metadata')
    rows: list[dict[str, str | None]] = Field(
        description='Result rows as objects with column names as keys'
    )
    total_rows: int = Field(ge=0, description='Total number of rows returned')
    query_execution_id: str = Field(description='Query execution ID for reference')
    next_token: str | None = Field(default=None, description='Token for pagination')
    data_scanned_in_bytes: int | None = Field(
        default=None, ge=0, description='Amount of data scanned by the query in bytes'
    )
    execution_time_in_millis: int | None = Field(
        default=None, ge=0, description='Query execution time in milliseconds'
    )


class DatabaseInfo(BaseModel):
    """Database information."""

    name: str = Field(min_length=1, max_length=255, description='Database name')
    description: str | None = Field(default=None, description='Database description')
    parameters: dict[str, str] | None = Field(default=None, description='Database parameters')


class TableInfo(BaseModel):
    """Table information."""

    name: str = Field(min_length=1, max_length=255, description='Table name')
    table_type: TableType | None = Field(
        default=None, description='Table type (e.g., EXTERNAL_TABLE)'
    )
    create_time: datetime | None = Field(default=None, description='Table creation time')
    last_access_time: datetime | None = Field(default=None, description='Last access time')
    columns: list[ColumnInfo] | None = Field(default=None, description='Table columns')
    partition_keys: list[ColumnInfo] | None = Field(default=None, description='Partition keys')
    location: str | None = Field(default=None, description='S3 location of table data')
    input_format: str | None = Field(default=None, description='Input format class')
    output_format: str | None = Field(default=None, description='Output format class')
    serde_info: dict[str, Any] | None = Field(default=None, description='SerDe information')
    parameters: dict[str, str] | None = Field(default=None, description='Table parameters')


class ErrorResponse(BaseModel):
    """Error response model."""

    error_code: str = Field(description='Error code')
    error_message: str = Field(description='Error message')
    error_type: str | None = Field(default=None, description='Error type')


# Base classes for response containers
class PaginatedResponse(BaseModel):
    """Base class for paginated API responses."""

    next_token: str | None = Field(default=None, description='Token for pagination')


# Response container models
class ListDatabasesResponse(PaginatedResponse):
    """Response from list_databases function."""

    databases: list[dict[str, Any]] = Field(description='List of databases with metadata')


class TableSummary(BaseModel):
    """Summary information for a table in list responses."""

    name: str = Field(min_length=1, max_length=255, description='Table name')
    columns_count: int = Field(ge=0, description='Number of columns in the table')
    partition_keys_count: int = Field(ge=0, description='Number of partition keys')
    table_type: TableType | None = Field(default=None, description='Table type')
    create_time: datetime | None = Field(default=None, description='Table creation time')
    last_access_time: datetime | None = Field(default=None, description='Last access time')


class ListTablesResponse(PaginatedResponse):
    """Response from list_tables function."""

    tables: list[TableSummary] = Field(description='List of tables with summary information')


class WorkgroupSummary(BaseModel):
    """Summary information for a workgroup."""

    name: str = Field(min_length=1, max_length=128, description='Workgroup name')
    state: WorkgroupState = Field(description='Workgroup state')
    description: str | None = Field(default=None, description='Workgroup description')
    creation_time: datetime | None = Field(default=None, description='Creation time')


class ListWorkgroupsResponse(PaginatedResponse):
    """Response from list_work_groups function."""

    workgroups: list[WorkgroupSummary] = Field(
        description='List of workgroups with summary information'
    )


class WorkgroupDetailsResponse(BaseModel):
    """Response from get_work_group function."""

    name: str = Field(min_length=1, max_length=128, description='Workgroup name')
    state: WorkgroupState = Field(description='Workgroup state')
    configuration: dict[str, Any] = Field(description='Workgroup configuration details')
    description: str | None = Field(default=None, description='Workgroup description')
    creation_time: datetime | None = Field(default=None, description='Creation time')


class DataCatalogSummary(BaseModel):
    """Summary information for a data catalog."""

    catalog_name: str = Field(min_length=1, max_length=255, description='Data catalog name')
    type: DataCatalogType = Field(description='Catalog type')


class ListDataCatalogsResponse(PaginatedResponse):
    """Response from list_data_catalogs function."""

    data_catalogs: list[DataCatalogSummary] = Field(
        description='List of data catalogs with summary information'
    )
