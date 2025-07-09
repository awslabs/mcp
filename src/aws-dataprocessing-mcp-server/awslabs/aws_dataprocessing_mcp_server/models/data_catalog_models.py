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

from enum import Enum
from mcp.types import CallToolResult
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class GlueOperation(str, Enum):
    """AWS Glue Data Catalog operations."""

    CREATE = 'create'
    DELETE = 'delete'
    GET = 'get'
    LIST = 'list'
    UPDATE = 'update'
    SEARCH = 'search'
    IMPORT = 'import'


class DatabaseSummary(BaseModel):
    """Summary of a Glue Data Catalog database."""

    name: str = Field(..., description='Name of the database')
    description: Optional[str] = Field(None, description='Description of the database')
    location_uri: Optional[str] = Field(None, description='Location URI of the database')
    parameters: Dict[str, str] = Field(default_factory=dict, description='Database parameters')
    creation_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')


class TableSummary(BaseModel):
    """Summary of a Glue Data Catalog table."""

    name: str = Field(..., description='Name of the table')
    database_name: str = Field(..., description='Name of the database containing the table')
    owner: Optional[str] = Field(None, description='Owner of the table')
    creation_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')
    update_time: Optional[str] = Field(None, description='Last update timestamp in ISO format')
    last_access_time: Optional[str] = Field(
        None, description='Last access timestamp in ISO format'
    )
    storage_descriptor: Dict[str, Any] = Field(
        default_factory=dict, description='Storage descriptor information'
    )
    partition_keys: List[Dict[str, Any]] = Field(
        default_factory=list, description='Partition key definitions'
    )


class ConnectionSummary(BaseModel):
    """Summary of a Glue Data Catalog connection."""

    name: str = Field(..., description='Name of the connection')
    connection_type: str = Field(..., description='Type of the connection')
    connection_properties: Dict[str, str] = Field(
        default_factory=dict, description='Connection properties'
    )
    physical_connection_requirements: Optional[Dict[str, Any]] = Field(
        None, description='Physical connection requirements'
    )
    creation_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')
    last_updated_time: Optional[str] = Field(
        None, description='Last update timestamp in ISO format'
    )


class PartitionSummary(BaseModel):
    """Summary of a Glue Data Catalog partition."""

    values: List[str] = Field(..., description='Partition values')
    database_name: str = Field(..., description='Name of the database')
    table_name: str = Field(..., description='Name of the table')
    creation_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')
    last_access_time: Optional[str] = Field(
        None, description='Last access timestamp in ISO format'
    )
    storage_descriptor: Dict[str, Any] = Field(
        default_factory=dict, description='Storage descriptor information'
    )
    parameters: Dict[str, str] = Field(default_factory=dict, description='Partition parameters')


class CatalogSummary(BaseModel):
    """Summary of a Glue Data Catalog."""

    catalog_id: str = Field(..., description='ID of the catalog')
    name: Optional[str] = Field(None, description='Name of the catalog')
    description: Optional[str] = Field(None, description='Description of the catalog')
    parameters: Dict[str, str] = Field(default_factory=dict, description='Catalog parameters')
    create_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')
    update_time: Optional[str] = Field(None, description='Last update timestamp in ISO format')


# Database Response Models
class CreateDatabaseResponse(CallToolResult):
    """Response model for create database operation."""

    database_name: str = Field(..., description='Name of the created database')
    operation: str = Field(default='create', description='Operation performed')


class DeleteDatabaseResponse(CallToolResult):
    """Response model for delete database operation."""

    database_name: str = Field(..., description='Name of the deleted database')
    operation: str = Field(default='delete', description='Operation performed')


class GetDatabaseResponse(CallToolResult):
    """Response model for get database operation."""

    database_name: str = Field(..., description='Name of the database')
    description: Optional[str] = Field(None, description='Description of the database')
    location_uri: Optional[str] = Field(None, description='Location URI of the database')
    parameters: Dict[str, str] = Field(default_factory=dict, description='Database parameters')
    creation_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')
    catalog_id: Optional[str] = Field(None, description='Catalog ID containing the database')
    operation: str = Field(default='get', description='Operation performed')


class ListDatabasesResponse(CallToolResult):
    """Response model for list databases operation."""

    databases: List[DatabaseSummary] = Field(..., description='List of databases')
    count: int = Field(..., description='Number of databases found')
    catalog_id: Optional[str] = Field(None, description='Catalog ID used for listing')
    operation: str = Field(default='list', description='Operation performed')
    next_token: Optional[str] = Field(None, description='Token for the next page of results')


class UpdateDatabaseResponse(CallToolResult):
    """Response model for update database operation."""

    database_name: str = Field(..., description='Name of the updated database')
    operation: str = Field(default='update', description='Operation performed')


# Table Response Models
class CreateTableResponse(CallToolResult):
    """Response model for create table operation."""

    database_name: str = Field(..., description='Name of the database containing the table')
    table_name: str = Field(..., description='Name of the created table')
    operation: str = Field(default='create', description='Operation performed')


class DeleteTableResponse(CallToolResult):
    """Response model for delete table operation."""

    database_name: str = Field(..., description='Name of the database containing the table')
    table_name: str = Field(..., description='Name of the deleted table')
    operation: str = Field(default='delete', description='Operation performed')


class GetTableResponse(CallToolResult):
    """Response model for get table operation."""

    database_name: str = Field(..., description='Name of the database containing the table')
    table_name: str = Field(..., description='Name of the table')
    table_definition: Dict[str, Any] = Field(..., description='Complete table definition')
    creation_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')
    last_access_time: Optional[str] = Field(
        None, description='Last access timestamp in ISO format'
    )
    storage_descriptor: Dict[str, Any] = Field(
        default_factory=dict, description='Storage descriptor information'
    )
    partition_keys: List[Dict[str, Any]] = Field(
        default_factory=list, description='Partition key definitions'
    )
    operation: str = Field(default='get', description='Operation performed')


class ListTablesResponse(CallToolResult):
    """Response model for list tables operation."""

    database_name: str = Field(..., description='Name of the database')
    tables: List[TableSummary] = Field(..., description='List of tables')
    count: int = Field(..., description='Number of tables found')
    operation: str = Field(default='list', description='Operation performed')


class UpdateTableResponse(CallToolResult):
    """Response model for update table operation."""

    database_name: str = Field(..., description='Name of the database containing the table')
    table_name: str = Field(..., description='Name of the updated table')
    operation: str = Field(default='update', description='Operation performed')


class SearchTablesResponse(CallToolResult):
    """Response model for search tables operation."""

    tables: List[TableSummary] = Field(..., description='List of matching tables')
    search_text: str = Field(..., description='Search text used for matching')
    count: int = Field(..., description='Number of tables found')
    operation: str = Field(default='search', description='Operation performed')
    next_token: Optional[str] = Field('', description='Token for pagination')


# Connection Response Models
class CreateConnectionResponse(CallToolResult):
    """Response model for create connection operation."""

    connection_name: str = Field(..., description='Name of the created connection')
    catalog_id: Optional[str] = Field(None, description='Catalog ID containing the connection')
    operation: str = Field(default='create', description='Operation performed')


class DeleteConnectionResponse(CallToolResult):
    """Response model for delete connection operation."""

    connection_name: str = Field(..., description='Name of the deleted connection')
    catalog_id: Optional[str] = Field(None, description='Catalog ID containing the connection')
    operation: str = Field(default='delete', description='Operation performed')


class GetConnectionResponse(CallToolResult):
    """Response model for get connection operation."""

    connection_name: str = Field(..., description='Name of the connection')
    connection_type: str = Field(..., description='Type of the connection')
    connection_properties: Dict[str, str] = Field(
        default_factory=dict, description='Connection properties'
    )
    physical_connection_requirements: Optional[Dict[str, Any]] = Field(
        None, description='Physical connection requirements'
    )
    creation_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')
    last_updated_time: Optional[str] = Field(
        None, description='Last update timestamp in ISO format'
    )
    last_updated_by: Optional[str] = Field(
        None, description='The user, group, or role that last updated this connection'
    )
    status: Optional[str] = Field(
        None, description='The status of the connection (READY, IN_PROGRESS, or FAILED)'
    )
    status_reason: Optional[str] = Field(None, description='The reason for the connection status')
    last_connection_validation_time: Optional[str] = Field(
        None, description='Timestamp of the last time this connection was validated'
    )
    catalog_id: Optional[str] = Field(None, description='Catalog ID containing the connection')
    operation: str = Field(default='get', description='Operation performed')


class ListConnectionsResponse(CallToolResult):
    """Response model for list connections operation."""

    connections: List[ConnectionSummary] = Field(..., description='List of connections')
    count: int = Field(..., description='Number of connections found')
    catalog_id: Optional[str] = Field(None, description='Catalog ID used for listing')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class UpdateConnectionResponse(CallToolResult):
    """Response model for update connection operation."""

    connection_name: str = Field(..., description='Name of the updated connection')
    catalog_id: Optional[str] = Field(None, description='Catalog ID containing the connection')
    operation: str = Field(default='update', description='Operation performed')


# Partition Response Models
class CreatePartitionResponse(CallToolResult):
    """Response model for create partition operation."""

    database_name: str = Field(..., description='Name of the database containing the table')
    table_name: str = Field(..., description='Name of the table containing the partition')
    partition_values: List[str] = Field(..., description='Values that define the partition')
    operation: str = Field(default='create', description='Operation performed')


class DeletePartitionResponse(CallToolResult):
    """Response model for delete partition operation."""

    database_name: str = Field(..., description='Name of the database containing the table')
    table_name: str = Field(..., description='Name of the table containing the partition')
    partition_values: List[str] = Field(
        ..., description='Values that defined the deleted partition'
    )
    operation: str = Field(default='delete', description='Operation performed')


class GetPartitionResponse(CallToolResult):
    """Response model for get partition operation."""

    database_name: str = Field(..., description='Name of the database containing the table')
    table_name: str = Field(..., description='Name of the table containing the partition')
    partition_values: List[str] = Field(..., description='Values that define the partition')
    partition_definition: Dict[str, Any] = Field(..., description='Complete partition definition')
    creation_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')
    last_access_time: Optional[str] = Field(
        None, description='Last access timestamp in ISO format'
    )
    storage_descriptor: Dict[str, Any] = Field(
        default_factory=dict, description='Storage descriptor information'
    )
    parameters: Dict[str, str] = Field(default_factory=dict, description='Partition parameters')
    operation: str = Field(default='get', description='Operation performed')


class ListPartitionsResponse(CallToolResult):
    """Response model for list partitions operation."""

    database_name: str = Field(..., description='Name of the database containing the table')
    table_name: str = Field(..., description='Name of the table')
    partitions: List[PartitionSummary] = Field(..., description='List of partitions')
    count: int = Field(..., description='Number of partitions found')
    expression: Optional[str] = Field(None, description='Filter expression used')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class UpdatePartitionResponse(CallToolResult):
    """Response model for update partition operation."""

    database_name: str = Field(..., description='Name of the database containing the table')
    table_name: str = Field(..., description='Name of the table containing the partition')
    partition_values: List[str] = Field(
        ..., description='Values that define the updated partition'
    )
    operation: str = Field(default='update', description='Operation performed')


# Catalog Response Models
class CreateCatalogResponse(CallToolResult):
    """Response model for create catalog operation."""

    catalog_id: str = Field(..., description='ID of the created catalog')
    operation: str = Field(default='create', description='Operation performed')


class DeleteCatalogResponse(CallToolResult):
    """Response model for delete catalog operation."""

    catalog_id: str = Field(..., description='ID of the deleted catalog')
    operation: str = Field(default='delete', description='Operation performed')


class GetCatalogResponse(CallToolResult):
    """Response model for get catalog operation."""

    catalog_id: str = Field(..., description='ID of the catalog')
    catalog_definition: Dict[str, Any] = Field(..., description='Complete catalog definition')
    name: Optional[str] = Field(None, description='Name of the catalog')
    description: Optional[str] = Field(None, description='Description of the catalog')
    parameters: Dict[str, str] = Field(default_factory=dict, description='Catalog parameters')
    create_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')
    update_time: Optional[str] = Field(None, description='Last update timestamp in ISO format')
    operation: str = Field(default='get', description='Operation performed')


class ListCatalogsResponse(CallToolResult):
    """Response model for list catalogs operation."""

    catalogs: List[CatalogSummary] = Field(..., description='List of catalogs')
    count: int = Field(..., description='Number of catalogs found')
    operation: str = Field(default='list', description='Operation performed')


class ImportCatalogResponse(CallToolResult):
    """Response model for import catalog operation."""

    catalog_id: str = Field(..., description='ID of the catalog being imported to')
    operation: str = Field(default='import', description='Operation performed')


# Additional utility models for complex operations
class GlueJobRun(BaseModel):
    """Model for a Glue job run status."""

    job_run_id: str = Field(..., description='ID of the job run')
    job_name: str = Field(..., description='Name of the Glue job')
    job_run_state: str = Field(..., description='Current state of the job run')
    started_on: Optional[str] = Field(None, description='Start timestamp in ISO format')
    completed_on: Optional[str] = Field(None, description='Completion timestamp in ISO format')
    execution_time: Optional[int] = Field(None, description='Execution time in seconds')
    error_message: Optional[str] = Field(None, description='Error message if job failed')


class BatchOperationResult(BaseModel):
    """Result of a batch operation on multiple resources."""

    total_requested: int = Field(..., description='Total number of operations requested')
    successful: int = Field(..., description='Number of successful operations')
    failed: int = Field(..., description='Number of failed operations')
    errors: List[Dict[str, str]] = Field(
        default_factory=list, description='List of errors encountered'
    )


class DataQualityResult(BaseModel):
    """Result of data quality evaluation."""

    result_id: str = Field(..., description='ID of the data quality result')
    score: Optional[float] = Field(None, description='Overall data quality score')
    started_on: Optional[str] = Field(None, description='Start timestamp in ISO format')
    completed_on: Optional[str] = Field(None, description='Completion timestamp in ISO format')
    rule_results: List[Dict[str, Any]] = Field(
        default_factory=list, description='Individual rule results'
    )


class CrawlerRun(BaseModel):
    """Model for a Glue crawler run."""

    crawler_name: str = Field(..., description='Name of the crawler')
    state: str = Field(..., description='Current state of the crawler')
    start_time: Optional[str] = Field(None, description='Start timestamp in ISO format')
    end_time: Optional[str] = Field(None, description='End timestamp in ISO format')
    tables_created: int = Field(default=0, description='Number of tables created')
    tables_updated: int = Field(default=0, description='Number of tables updated')
    tables_deleted: int = Field(default=0, description='Number of tables deleted')


# Extended response models for advanced operations
class BatchCreateTablesResponse(CallToolResult):
    """Response model for batch create tables operation."""

    database_name: str = Field(..., description='Name of the database')
    batch_result: BatchOperationResult = Field(..., description='Batch operation results')
    created_tables: List[str] = Field(..., description='List of successfully created table names')
    operation: str = Field(default='batch_create', description='Operation performed')


class BatchDeleteTablesResponse(CallToolResult):
    """Response model for batch delete tables operation."""

    database_name: str = Field(..., description='Name of the database')
    batch_result: BatchOperationResult = Field(..., description='Batch operation results')
    deleted_tables: List[str] = Field(..., description='List of successfully deleted table names')
    operation: str = Field(default='batch_delete', description='Operation performed')


class TableSchemaComparisonResponse(CallToolResult):
    """Response model for table schema comparison operation."""

    source_table: str = Field(..., description='Source table name')
    target_table: str = Field(..., description='Target table name')
    schemas_match: bool = Field(..., description='Whether schemas match exactly')
    differences: List[Dict[str, Any]] = Field(
        default_factory=list, description='List of schema differences'
    )
    operation: str = Field(default='compare_schema', description='Operation performed')


class DataLineageResponse(CallToolResult):
    """Response model for data lineage tracking operation."""

    table_name: str = Field(..., description='Name of the table')
    database_name: str = Field(..., description='Name of the database')
    upstream_tables: List[Dict[str, str]] = Field(
        default_factory=list, description='Upstream data sources'
    )
    downstream_tables: List[Dict[str, str]] = Field(
        default_factory=list, description='Downstream data consumers'
    )
    jobs_using_table: List[str] = Field(
        default_factory=list, description='Glue jobs that use this table'
    )
    operation: str = Field(default='get_lineage', description='Operation performed')


class PartitionProjectionResponse(CallToolResult):
    """Response model for partition projection configuration."""

    database_name: str = Field(..., description='Name of the database')
    table_name: str = Field(..., description='Name of the table')
    projection_enabled: bool = Field(..., description='Whether partition projection is enabled')
    projection_config: Dict[str, Any] = Field(
        default_factory=dict, description='Partition projection configuration'
    )
    estimated_partitions: Optional[int] = Field(None, description='Estimated number of partitions')
    operation: str = Field(default='configure_projection', description='Operation performed')


class CatalogEncryptionResponse(CallToolResult):
    """Response model for catalog encryption configuration."""

    catalog_id: str = Field(..., description='ID of the catalog')
    encryption_at_rest: Dict[str, Any] = Field(
        default_factory=dict, description='Encryption at rest configuration'
    )
    connection_password_encryption: Dict[str, Any] = Field(
        default_factory=dict, description='Connection password encryption configuration'
    )
    operation: str = Field(default='configure_encryption', description='Operation performed')


class ResourceLinkResponse(CallToolResult):
    """Response model for resource link operations."""

    link_name: str = Field(..., description='Name of the resource link')
    source_catalog_id: str = Field(..., description='Source catalog ID')
    target_catalog_id: str = Field(..., description='Target catalog ID')
    target_database: str = Field(..., description='Target database name')
    operation: str = Field(default='create_link', description='Operation performed')
