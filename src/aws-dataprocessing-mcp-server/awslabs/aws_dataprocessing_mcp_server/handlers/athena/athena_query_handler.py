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

"""AthenaQueryHandler for Data Processing MCP Server."""

from awslabs.aws_dataprocessing_mcp_server.models.athena_models import (
    BatchGetNamedQueryResponse,
    BatchGetQueryExecutionResponse,
    CreateNamedQueryResponse,
    DeleteNamedQueryResponse,
    GetNamedQueryResponse,
    GetQueryExecutionResponse,
    GetQueryResultsResponse,
    GetQueryRuntimeStatisticsResponse,
    ListNamedQueriesResponse,
    ListQueryExecutionsResponse,
    StartQueryExecutionResponse,
    StopQueryExecutionResponse,
    UpdateNamedQueryResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict, List, Optional, Union


class AthenaQueryHandler:
    """Handler for Amazon Athena Query operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Athena Query handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.athena_client = AwsHelper.create_boto3_client('athena')

        # Register tools
        self.mcp.tool(name='manage_aws_athena_query_executions')(self.manage_aws_athena_queries)
        self.mcp.tool(name='manage_aws_athena_named_queries')(self.manage_aws_athena_named_queries)

    async def manage_aws_athena_queries(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: batch-get-query-execution, get-query-execution, get-query-results, get-query-runtime-statistics, list-query-executions, start-query-execution, stop-query-execution. Choose read-only operations when write access is disabled.',
        ),
        query_execution_id: Optional[str] = Field(
            None,
            description='ID of the query execution (required for get-query-execution, get-query-results, get-query-runtime-statistics, stop-query-execution).',
        ),
        query_execution_ids: Optional[List[str]] = Field(
            None,
            description='List of query execution IDs (required for batch-get-query-execution, max 50 IDs).',
        ),
        query_string: Optional[str] = Field(
            None,
            description='The SQL query string to execute (required for start-query-execution).',
        ),
        client_request_token: Optional[str] = Field(
            None,
            description='A unique case-sensitive string used to ensure the request to create the query is idempotent (optional for start-query-execution).',
        ),
        query_execution_context: Optional[Dict[str, str]] = Field(
            None,
            description='Context for the query execution, such as database name and catalog (optional for start-query-execution).',
        ),
        result_configuration: Optional[Dict[str, Any]] = Field(
            None,
            description='Configuration for query results, such as output location and encryption (optional for start-query-execution).',
        ),
        work_group: Optional[str] = Field(
            None,
            description='The name of the workgroup in which the query is being started (optional for start-query-execution, list-query-executions).',
        ),
        execution_parameters: Optional[List[str]] = Field(
            None,
            description='Execution parameters for parameterized queries (optional for start-query-execution).',
        ),
        result_reuse_configuration: Optional[Dict[str, Any]] = Field(
            None,
            description='Specifies the query result reuse behavior for the query (optional for start-query-execution).',
        ),
        max_results: Optional[int] = Field(
            None,
            description='Maximum number of results to return (1-1000 for get-query-results, 0-50 for list-query-executions).',
        ),
        next_token: Optional[str] = Field(
            None,
            description='Pagination token for get-query-results and list-query-executions operations.',
        ),
        query_result_type: Optional[str] = Field(
            None,
            description='Type of query results to return: DATA_ROWS (default) or DATA_MANIFEST (optional for get-query-results).',
        ),
    ) -> Union[
        BatchGetQueryExecutionResponse,
        GetQueryExecutionResponse,
        GetQueryResultsResponse,
        GetQueryRuntimeStatisticsResponse,
        ListQueryExecutionsResponse,
        StartQueryExecutionResponse,
        StopQueryExecutionResponse,
    ]:
        """Execute and manage AWS Athena SQL queries.

        This tool provides comprehensive operations for AWS Athena query management, including
        starting new queries, monitoring execution status, retrieving results, and analyzing
        performance statistics.

        ## Requirements
        - The server must be run with the `--allow-write` flag if start-query-execution contains any write operation for example DDL commands, Insert, Update, Delete Commands or any flag updates
        - Appropriate AWS permissions for Athena query operations

        ## Operations
        - **batch-get-query-execution**: Get details for up to 50 query executions by their IDs
        - **get-query-execution**: Get complete information about a single query execution
        - **get-query-results**: Retrieve the results of a completed query
        - **get-query-runtime-statistics**: Get performance statistics for a query execution
        - **list-query-executions**: List available query execution IDs (up to 50)
        - **start-query-execution**: Execute a new SQL query
        - **stop-query-execution**: Cancel a running query

        ## Example
        ```python
        # Start a new query
        response = await manage_aws_athena_queries(
            operation='start-query-execution',
            query_string='SELECT * FROM my_database.my_table LIMIT 10',
            query_execution_context={'Database': 'my_database', 'Catalog': 'my_catalog'},
            work_group='primary',
        )

        # Get the query results
        results = await manage_aws_athena_queries(
            operation='get-query-results', query_execution_id=response.query_execution_id
        )
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            query_execution_id: ID of the query execution
            query_execution_ids: List of query execution IDs (max 50)
            query_string: The SQL query string to execute
            client_request_token: Unique token for idempotent requests
            query_execution_context: Context with database and catalog information
            result_configuration: Configuration for query results location and encryption
            work_group: The name of the workgroup
            execution_parameters: Parameters for parameterized queries
            result_reuse_configuration: Query result reuse behavior configuration
            max_results: Maximum number of results to return
            next_token: Pagination token
            query_result_type: Type of query results to return (DATA_ROWS or DATA_MANIFEST)

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Athena Query Handler - Tool: manage_aws_athena_queries - Operation: {operation}',
            )

            if not self.allow_write and operation in [
                'start-query-execution',
            ]:
                error_message = (
                    f'Operation {operation} for select query is only allowed without write access'
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if (
                    operation == 'start-query-execution'
                    and query_string
                    and (
                        'select' not in query_string.lower()
                        or 'create table as select' in query_string.lower()
                    )
                ):
                    return StartQueryExecutionResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        query_execution_id='',
                        operation='start-query-execution',
                    )

            if operation == 'batch-get-query-execution':
                if query_execution_ids is None:
                    raise ValueError(
                        'query_execution_ids is required for batch-get-query-execution operation'
                    )

                # Get batch query executions
                response = self.athena_client.batch_get_query_execution(
                    QueryExecutionIds=query_execution_ids
                )

                query_executions = response.get('QueryExecutions', [])
                unprocessed_ids = response.get('UnprocessedQueryExecutionIds', [])
                return BatchGetQueryExecutionResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text='Successfully retrieved query executions',
                        )
                    ],
                    query_executions=query_executions,
                    unprocessed_query_execution_ids=unprocessed_ids,
                    operation='batch-get-query-execution',
                )

            elif operation == 'get-query-execution':
                if query_execution_id is None:
                    raise ValueError(
                        'query_execution_id is required for get-query-execution operation'
                    )

                # Get query execution
                response = self.athena_client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )

                return GetQueryExecutionResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved query execution {query_execution_id}',
                        )
                    ],
                    query_execution_id=query_execution_id,
                    query_execution=response.get('QueryExecution', {}),
                    operation='get-query-execution',
                )

            elif operation == 'get-query-results':
                if query_execution_id is None:
                    raise ValueError(
                        'query_execution_id is required for get-query-results operation'
                    )

                # Prepare parameters
                params: Dict[str, Any] = {'QueryExecutionId': query_execution_id}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token
                if query_result_type is not None:
                    params['QueryResultType'] = query_result_type

                # Get query results
                response = self.athena_client.get_query_results(**params)

                return GetQueryResultsResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved query results for {query_execution_id}',
                        )
                    ],
                    query_execution_id=query_execution_id,
                    result_set=response.get('ResultSet', {}),
                    next_token=response.get('NextToken'),
                    update_count=response.get('UpdateCount'),
                    operation='get-query-results',
                )

            elif operation == 'get-query-runtime-statistics':
                if query_execution_id is None:
                    raise ValueError(
                        'query_execution_id is required for get-query-runtime-statistics operation'
                    )

                # Get query runtime statistics
                response = self.athena_client.get_query_runtime_statistics(
                    QueryExecutionId=query_execution_id
                )

                return GetQueryRuntimeStatisticsResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved query runtime statistics for {query_execution_id}',
                        )
                    ],
                    query_execution_id=query_execution_id,
                    statistics=response.get('QueryRuntimeStatistics', {}),
                    operation='get-query-runtime-statistics',
                )

            elif operation == 'list-query-executions':
                # Prepare parameters
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token
                if work_group is not None:
                    params['WorkGroup'] = work_group

                # List query executions
                response = self.athena_client.list_query_executions(**params)

                query_execution_ids_res: List[str] = response.get('QueryExecutionIds', [])
                return ListQueryExecutionsResponse(
                    isError=False,
                    content=[
                        TextContent(type='text', text='Successfully listed query executions')
                    ],
                    query_execution_ids=query_execution_ids_res,
                    count=len(query_execution_ids_res),
                    next_token=response.get('NextToken'),
                    operation='list-query-executions',
                )

            elif operation == 'start-query-execution':
                if query_string is None:
                    raise ValueError(
                        'query_string is required for start-query-execution operation'
                    )

                # Prepare parameters
                params = {'QueryString': query_string}

                if client_request_token is not None:
                    params['ClientRequestToken'] = client_request_token

                if query_execution_context is not None:
                    params['QueryExecutionContext'] = query_execution_context

                if result_configuration is not None:
                    params['ResultConfiguration'] = result_configuration

                if work_group is not None:
                    params['WorkGroup'] = work_group

                if execution_parameters is not None:
                    params['ExecutionParameters'] = execution_parameters

                if result_reuse_configuration is not None:
                    params['ResultReuseConfiguration'] = result_reuse_configuration

                # Start query execution
                response = self.athena_client.start_query_execution(**params)

                return StartQueryExecutionResponse(
                    isError=False,
                    content=[
                        TextContent(type='text', text='Successfully started query execution')
                    ],
                    query_execution_id=response.get('QueryExecutionId', ''),
                    operation='start-query-execution',
                )

            elif operation == 'stop-query-execution':
                if query_execution_id is None:
                    raise ValueError(
                        'query_execution_id is required for stop-query-execution operation'
                    )

                # Stop query execution
                self.athena_client.stop_query_execution(QueryExecutionId=query_execution_id)

                return StopQueryExecutionResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully stopped query execution {query_execution_id}',
                        )
                    ],
                    query_execution_id=query_execution_id,
                    operation='stop-query-execution',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: batch-get-query-execution, get-query-execution, get-query-results, get-query-runtime-statistics, list-query-executions, start-query-execution, stop-query-execution'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetQueryExecutionResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    query_execution_id='',
                    query_execution={},
                    operation='get-query-execution',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_athena_queries: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetQueryExecutionResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                query_execution_id=query_execution_id or '',
                query_execution={},
                operation='get-query-execution',
            )

    async def manage_aws_athena_named_queries(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: batch-get-named-query, create-named-query, delete-named-query, get-named-query, list-named-queries, update-named-query. Choose read-only operations when write access is disabled.',
        ),
        named_query_id: Optional[str] = Field(
            None,
            description='ID of the named query (required for get-named-query, delete-named-query, update-named-query).',
        ),
        named_query_ids: Optional[List[str]] = Field(
            None,
            description='List of named query IDs (required for batch-get-named-query, max 50 IDs).',
        ),
        name: Optional[str] = Field(
            None,
            description='Name of the named query (required for create-named-query and update-named-query).',
        ),
        description: Optional[str] = Field(
            None,
            description='Description of the named query (optional for create-named-query and update-named-query, max 1024 chars).',
        ),
        database: Optional[str] = Field(
            None,
            description='Database context for the named query (required for create-named-query, optional for update-named-query).',
        ),
        query_string: Optional[str] = Field(
            None,
            description='The SQL query string (required for create-named-query and update-named-query).',
        ),
        client_request_token: Optional[str] = Field(
            None,
            description='A unique case-sensitive string used to ensure the request to create the query is idempotent (optional for create-named-query).',
        ),
        work_group: Optional[str] = Field(
            None,
            description='The name of the workgroup (optional for create-named-query and list-named-queries).',
        ),
        max_results: Optional[int] = Field(
            None,
            description='Maximum number of results to return for list-named-queries operation.',
        ),
        next_token: Optional[str] = Field(
            None,
            description='Pagination token for list-named-queries operation.',
        ),
    ) -> Union[
        BatchGetNamedQueryResponse,
        CreateNamedQueryResponse,
        DeleteNamedQueryResponse,
        GetNamedQueryResponse,
        ListNamedQueriesResponse,
        UpdateNamedQueryResponse,
    ]:
        """Manage saved SQL queries in AWS Athena.

        This tool provides operations for creating, retrieving, updating, and deleting named queries
        in AWS Athena. Named queries are saved SQL statements that can be easily reused, shared with
        team members, and executed without having to rewrite complex queries.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-named-query, delete-named-query, and update-named-query operations
        - Appropriate AWS permissions for Athena named query operations

        ## Operations
        - **batch-get-named-query**: Get details for up to 50 named queries by their IDs
        - **create-named-query**: Save a new SQL query with a name and description
        - **delete-named-query**: Remove a saved query
        - **get-named-query**: Retrieve a single named query by ID
        - **list-named-queries**: List available named query IDs
        - **update-named-query**: Modify an existing named query

        ## Example
        ```python
        # Create a named query
        create_response = await manage_aws_athena_named_queries(
            operation='create-named-query',
            name='Daily Active Users',
            description='Query to calculate daily active users',
            database='analytics',
            query_string='SELECT date, COUNT(DISTINCT user_id) AS active_users FROM user_events GROUP BY date ORDER BY date DESC',
            work_group='primary',
        )

        # Later, retrieve the named query
        query = await manage_aws_athena_named_queries(
            operation='get-named-query', named_query_id=create_response.named_query_id
        )
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            named_query_id: ID of the named query
            named_query_ids: List of named query IDs (max 50)
            name: Name of the named query
            description: Description of the named query (max 1024 chars)
            database: Database context for the named query
            query_string: The SQL query string
            client_request_token: Unique token for idempotent requests
            work_group: The name of the workgroup
            max_results: Maximum number of results to return
            next_token: Pagination token

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Athena Query Handler - Tool: manage_aws_athena_named_queries - Operation: {operation}',
            )

            if not self.allow_write and operation in [
                'create-named-query',
                'delete-named-query',
                'update-named-query',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'create-named-query':
                    return CreateNamedQueryResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        named_query_id='',
                        operation='create-named-query',
                    )
                elif operation == 'delete-named-query':
                    return DeleteNamedQueryResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        named_query_id='',
                        operation='delete-named-query',
                    )
                elif operation == 'update-named-query':
                    return UpdateNamedQueryResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        named_query_id='',
                        operation='update-named-query',
                    )

            if operation == 'batch-get-named-query':
                if named_query_ids is None:
                    raise ValueError(
                        'named_query_ids is required for batch-get-named-query operation'
                    )

                # Get batch named queries
                response = self.athena_client.batch_get_named_query(NamedQueryIds=named_query_ids)

                named_queries = response.get('NamedQueries', [])
                unprocessed_ids = response.get('UnprocessedNamedQueryIds', [])
                return BatchGetNamedQueryResponse(
                    isError=False,
                    content=[
                        TextContent(type='text', text='Successfully retrieved named queries')
                    ],
                    named_queries=named_queries,
                    unprocessed_named_query_ids=unprocessed_ids,
                    operation='batch-get-named-query',
                )

            elif operation == 'create-named-query':
                if name is None or query_string is None or database is None:
                    raise ValueError(
                        'name, query_string, and database are required for create-named-query operation'
                    )

                # Prepare parameters
                params = {
                    'Name': name,
                    'QueryString': query_string,
                    'Database': database,
                }

                if description is not None:
                    params['Description'] = description

                if work_group is not None:
                    params['WorkGroup'] = work_group

                if client_request_token is not None:
                    params['ClientRequestToken'] = client_request_token

                # Create named query
                response = self.athena_client.create_named_query(**params)

                return CreateNamedQueryResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully created named query {name}',
                        )
                    ],
                    named_query_id=response.get('NamedQueryId', ''),
                    operation='create-named-query',
                )

            elif operation == 'delete-named-query':
                if named_query_id is None:
                    raise ValueError('named_query_id is required for delete-named-query operation')

                # Delete named query
                self.athena_client.delete_named_query(NamedQueryId=named_query_id)

                return DeleteNamedQueryResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully deleted named query {named_query_id}',
                        )
                    ],
                    named_query_id=named_query_id,
                    operation='delete-named-query',
                )

            elif operation == 'get-named-query':
                if named_query_id is None:
                    raise ValueError('named_query_id is required for get-named-query operation')

                # Get named query
                response = self.athena_client.get_named_query(NamedQueryId=named_query_id)

                return GetNamedQueryResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved named query {named_query_id}',
                        )
                    ],
                    named_query_id=named_query_id,
                    named_query=response.get('NamedQuery', {}),
                    operation='get-named-query',
                )

            elif operation == 'list-named-queries':
                # Prepare parameters
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token
                if work_group is not None:
                    params['WorkGroup'] = work_group

                # List named queries
                response = self.athena_client.list_named_queries(**params)

                named_query_ids_res = response.get('NamedQueryIds', [])
                return ListNamedQueriesResponse(
                    isError=False,
                    content=[TextContent(type='text', text='Successfully listed named queries')],
                    named_query_ids=named_query_ids_res,
                    count=len(named_query_ids_res),
                    next_token=response.get('NextToken'),
                    operation='list-named-queries',
                )

            elif operation == 'update-named-query':
                if named_query_id is None:
                    raise ValueError('named_query_id is required for update-named-query operation')

                # Prepare parameters
                params = {'NamedQueryId': named_query_id}

                if name is not None:
                    params['Name'] = name

                if description is not None:
                    params['Description'] = description

                if database is not None:
                    params['Database'] = database

                if query_string is not None:
                    params['QueryString'] = query_string

                # Update named query
                self.athena_client.update_named_query(**params)

                return UpdateNamedQueryResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully updated named query {named_query_id}',
                        )
                    ],
                    named_query_id=named_query_id,
                    operation='update-named-query',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: batch-get-named-query, create-named-query, delete-named-query, get-named-query, list-named-queries, update-named-query'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetNamedQueryResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    named_query_id='',
                    named_query={'': ''},
                    operation='get-named-query',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_athena_named_queries: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetNamedQueryResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                named_query_id=named_query_id or '',
                named_query={},
                operation='get-named-query',
            )
