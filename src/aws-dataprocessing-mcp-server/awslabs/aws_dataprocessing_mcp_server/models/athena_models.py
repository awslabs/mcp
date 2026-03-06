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

# Data models for Query Management
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class BatchGetQueryExecutionData(BaseModel):
    """Data model for batch get query execution operation."""

    query_executions: List[Dict[str, Any]] = Field(..., description='List of query executions')
    unprocessed_query_execution_ids: List[Dict[str, Any]] = Field(
        ..., description='List of unprocessed query execution IDs'
    )
    operation: str = Field(default='batch-get-query-execution', description='Operation performed')


class GetQueryExecutionData(BaseModel):
    """Data model for get query execution operation."""

    query_execution_id: str = Field(..., description='ID of the query execution')
    query_execution: Dict[str, Any] = Field(
        ...,
        description='Query execution details including ID, SQL query, statement type, result configuration, execution context, status, statistics, and workgroup',
    )
    operation: str = Field(default='get-query-execution', description='Operation performed')


class GetQueryResultsData(BaseModel):
    """Data model for get query results operation."""

    query_execution_id: str = Field(..., description='ID of the query execution')
    result_set: Dict[str, Any] = Field(
        ...,
        description='Query result set containing column information and rows of data',
    )
    next_token: Optional[str] = Field(
        None, description='Token for pagination of large result sets'
    )
    update_count: Optional[int] = Field(
        None,
        description='Number of rows inserted with CREATE TABLE AS SELECT, INSERT INTO, or UPDATE statements',
    )
    operation: str = Field(default='get-query-results', description='Operation performed')


class GetQueryRuntimeStatisticsData(BaseModel):
    """Data model for get query runtime statistics operation."""

    query_execution_id: str = Field(..., description='ID of the query execution')
    statistics: Dict[str, Any] = Field(
        ...,
        description='Query runtime statistics including timeline, row counts, and execution stages',
    )
    operation: str = Field(
        default='get-query-runtime-statistics', description='Operation performed'
    )


class ListQueryExecutionsData(BaseModel):
    """Data model for list query executions operation."""

    query_execution_ids: List[str] = Field(..., description='List of query execution IDs')
    count: int = Field(..., description='Number of query executions found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list-query-executions', description='Operation performed')


class StartQueryExecutionData(BaseModel):
    """Data model for start query execution operation."""

    query_execution_id: str = Field(..., description='ID of the started query execution')
    operation: str = Field(default='start-query-execution', description='Operation performed')


class StopQueryExecutionData(BaseModel):
    """Data model for stop query execution operation."""

    query_execution_id: str = Field(..., description='ID of the stopped query execution')
    operation: str = Field(default='stop-query-execution', description='Operation performed')


# Data models for Named Query Operations


class BatchGetNamedQueryData(BaseModel):
    """Data model for batch get named query operation."""

    named_queries: List[Dict[str, Any]] = Field(..., description='List of named queries')
    unprocessed_named_query_ids: List[Dict[str, Any]] = Field(
        ..., description='List of unprocessed named query IDs'
    )
    operation: str = Field(default='batch-get-named-query', description='Operation performed')


class CreateNamedQueryData(BaseModel):
    """Data model for create named query operation."""

    named_query_id: str = Field(..., description='ID of the created named query')
    operation: str = Field(default='create-named-query', description='Operation performed')


class DeleteNamedQueryData(BaseModel):
    """Data model for delete named query operation."""

    named_query_id: str = Field(..., description='ID of the deleted named query')
    operation: str = Field(default='delete-named-query', description='Operation performed')


class GetNamedQueryData(BaseModel):
    """Data model for get named query operation."""

    named_query_id: str = Field(..., description='ID of the named query')
    named_query: Dict[str, Any] = Field(
        ...,
        description='Named query details including name, description, database, query string, ID, and workgroup',
    )
    operation: str = Field(default='get-named-query', description='Operation performed')


class ListNamedQueriesData(BaseModel):
    """Data model for list named queries operation."""

    named_query_ids: List[str] = Field(..., description='List of named query IDs')
    count: int = Field(..., description='Number of named queries found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list-named-queries', description='Operation performed')


class UpdateNamedQueryData(BaseModel):
    """Data model for update named query operation."""

    named_query_id: str = Field(..., description='ID of the updated named query')
    operation: str = Field(default='update-named-query', description='Operation performed')


# Data models for Data Catalog Operations


class CreateDataCatalogData(BaseModel):
    """Data model for create data catalog operation."""

    name: str = Field(..., description='Name of the created data catalog')
    operation: str = Field(default='create', description='Operation performed')


class DeleteDataCatalogData(BaseModel):
    """Data model for delete data catalog operation."""

    name: str = Field(..., description='Name of the deleted data catalog')
    operation: str = Field(default='delete', description='Operation performed')


class GetDataCatalogData(BaseModel):
    """Data model for get data catalog operation."""

    data_catalog: Dict[str, Any] = Field(
        ...,
        description='Data catalog details including name, type, description, parameters, status, and connection type',
    )
    operation: str = Field(default='get', description='Operation performed')


class ListDataCatalogsData(BaseModel):
    """Data model for list data catalogs operation."""

    data_catalogs: List[Dict[str, Any]] = Field(
        ...,
        description='List of data catalog summaries, each containing catalog name, type, status, connection type, and error information',
    )
    count: int = Field(..., description='Number of data catalogs found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class UpdateDataCatalogData(BaseModel):
    """Data model for update data catalog operation."""

    name: str = Field(..., description='Name of the updated data catalog')
    operation: str = Field(default='update', description='Operation performed')


class GetDatabaseData(BaseModel):
    """Data model for get database operation."""

    database: Dict[str, Any] = Field(
        ..., description='Database details including name, description, and parameters'
    )
    operation: str = Field(default='get', description='Operation performed')


class GetTableMetadataData(BaseModel):
    """Data model for get table metadata operation."""

    table_metadata: Dict[str, Any] = Field(
        ...,
        description='Table metadata details including name, create time, last access time, table type, columns, partition keys, and parameters',
    )
    operation: str = Field(default='get', description='Operation performed')


class ListDatabasesData(BaseModel):
    """Data model for list databases operation."""

    database_list: List[Dict[str, Any]] = Field(
        ...,
        description='List of databases, each containing name, description, and parameters',
    )
    count: int = Field(..., description='Number of databases found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class ListTableMetadataData(BaseModel):
    """Data model for list table metadata operation."""

    table_metadata_list: List[Dict[str, Any]] = Field(
        ...,
        description='List of table metadata, each containing name, create time, last access time, table type, columns, partition keys, and parameters',
    )
    count: int = Field(..., description='Number of tables found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


# Data models for WorkGroup Operations


class CreateWorkGroupData(BaseModel):
    """Data model for create work group operation."""

    work_group_name: str = Field(..., description='Name of the created work group')
    operation: str = Field(default='create', description='Operation performed')


class DeleteWorkGroupData(BaseModel):
    """Data model for delete work group operation."""

    work_group_name: str = Field(..., description='Name of the deleted work group')
    operation: str = Field(default='delete', description='Operation performed')


class GetWorkGroupData(BaseModel):
    """Data model for get work group operation."""

    work_group: Dict[str, Any] = Field(..., description='Work group details')
    operation: str = Field(default='get', description='Operation performed')


class ListWorkGroupsData(BaseModel):
    """Data model for list work groups operation."""

    work_groups: List[Dict[str, Any]] = Field(..., description='List of work groups')
    count: int = Field(..., description='Number of work groups found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class UpdateWorkGroupData(BaseModel):
    """Data model for update work group operation."""

    work_group_name: str = Field(..., description='Name of the updated work group')
    operation: str = Field(default='update', description='Operation performed')
