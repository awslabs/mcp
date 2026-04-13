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

"""DataCatalogHandler for Data Processing MCP Server."""

from awslabs.aws_dataprocessing_mcp_server.core.glue_data_catalog.data_catalog_database_manager import (
    DataCatalogDatabaseManager,
)
from awslabs.aws_dataprocessing_mcp_server.core.glue_data_catalog.data_catalog_handler import (
    DataCatalogManager,
)
from awslabs.aws_dataprocessing_mcp_server.core.glue_data_catalog.data_catalog_table_manager import (
    DataCatalogTableManager,
)
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


class GlueDataCatalogHandler:
    """Handler for Amazon Glue Data Catalog operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Glue Data Catalog handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.data_catalog_database_manager = DataCatalogDatabaseManager(
            self.allow_write, self.allow_sensitive_data_access
        )
        self.data_catalog_table_manager = DataCatalogTableManager(
            self.allow_write, self.allow_sensitive_data_access
        )
        self.data_catalog_manager = DataCatalogManager(
            self.allow_write, self.allow_sensitive_data_access
        )

        # Register tools
        self.mcp.tool(name='manage_aws_glue_databases')(
            self.manage_aws_glue_data_catalog_databases
        )
        self.mcp.tool(name='manage_aws_glue_tables')(self.manage_aws_glue_data_catalog_tables)
        self.mcp.tool(name='manage_aws_glue_connections')(
            self.manage_aws_glue_data_catalog_connections
        )
        self.mcp.tool(name='manage_aws_glue_connection_types')(
            self.manage_aws_glue_connection_types
        )
        self.mcp.tool(name='manage_aws_glue_connection_metadata')(
            self.manage_aws_glue_connection_metadata
        )
        self.mcp.tool(name='manage_aws_glue_partitions')(
            self.manage_aws_glue_data_catalog_partitions
        )
        self.mcp.tool(name='manage_aws_glue_catalog')(self.manage_aws_glue_data_catalog)

    async def manage_aws_glue_data_catalog_databases(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: create-database, delete-database, get-database, list-databases, or update-database. Choose "get-database" or "list-databases" for read-only operations when write access is disabled.',
            ),
        ],
        database_name: Annotated[
            Optional[str],
            Field(
                description='Name of the database (required for create-database, delete-database, get-database, and update-database operations).',
            ),
        ] = None,
        description: Annotated[
            Optional[str],
            Field(
                description='Description of the database (for create-database and update-database operations).',
            ),
        ] = None,
        location_uri: Annotated[
            Optional[str],
            Field(
                description='Location URI of the database (for create-database and update-database operations).',
            ),
        ] = None,
        parameters: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='Key-value pairs that define parameters and properties of the database.',
            ),
        ] = None,
        catalog_id: Annotated[
            Optional[str],
            Field(
                description='ID of the catalog (optional, defaults to account ID).',
            ),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(description='The maximum number of databases to return in one response.'),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(
                description='A continuation token, if this is a continuation call.',
            ),
        ] = None,
    ) -> CallToolResult:
        """Manage AWS Glue Data Catalog databases with both read and write operations.

        This tool provides operations for managing Glue Data Catalog databases, including creating,
        updating, retrieving, listing, and deleting databases. It serves as the primary mechanism
        for database management within the AWS Glue Data Catalog.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-database, update-database, and delete-database operations
        - Appropriate AWS permissions for Glue Data Catalog operations

        ## Operations
        - **create-database**: Create a new database in the Glue Data Catalog
        - **delete-database**: Delete an existing database from the Glue Data Catalog
        - **get-database**: Retrieve detailed information about a specific database
        - **list-databases**: List all databases in the Glue Data Catalog
        - **update-database**: Update an existing database's properties

        ## Usage Tips
        - Use the get-database or list-databases operations first to check existing databases
        - Database names must be unique within your AWS account and region
        - Deleting a database will also delete all tables within it

        Args:
            ctx: MCP context
            operation: Operation to perform (create-database, delete-database, get-database, list-databases, update-database)
            database_name: Name of the database (required for most operations)
            description: Description of the database
            location_uri: Location URI of the database
            parameters: Additional parameters for the database
            catalog_id: ID of the catalog (optional, defaults to account ID)
            max_results: The maximum number of databases to return in one response.
            next_token: A continuation string token, if this is a continuation call.

        Returns:
            Union of response types specific to the operation performed
        """
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Received request to manage AWS Glue Data Catalog databases with operation: {operation} database_name: {database_name}, description {description}',
        )
        try:
            if not self.allow_write and operation not in [
                'get-database',
                'list-databases',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

            if operation == 'create-database':
                if database_name is None:
                    raise ValueError('database_name is required for create-database operation')
                return await self.data_catalog_database_manager.create_database(
                    ctx=ctx,
                    database_name=database_name,
                    description=description,
                    location_uri=location_uri,
                    parameters=parameters,
                    catalog_id=catalog_id,
                )

            elif operation == 'delete-database':
                if database_name is None:
                    raise ValueError('database_name is required for delete-database operation')
                return await self.data_catalog_database_manager.delete_database(
                    ctx=ctx, database_name=database_name, catalog_id=catalog_id
                )

            elif operation == 'get-database':
                if database_name is None:
                    raise ValueError('database_name is required for get-database operation')
                return await self.data_catalog_database_manager.get_database(
                    ctx=ctx, database_name=database_name, catalog_id=catalog_id
                )

            elif operation == 'list-databases':
                return await self.data_catalog_database_manager.list_databases(
                    ctx=ctx, catalog_id=catalog_id, next_token=next_token, max_results=max_results
                )

            elif operation == 'update-database':
                if database_name is None:
                    raise ValueError('database_name is required for update-database operation')
                return await self.data_catalog_database_manager.update_database(
                    ctx=ctx,
                    database_name=database_name,
                    description=description,
                    location_uri=location_uri,
                    parameters=parameters,
                    catalog_id=catalog_id,
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-database, delete-database, get-database, list-databases, update-database'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_data_catalog_databases: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def manage_aws_glue_data_catalog_tables(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: create-table, delete-table, get-table, list-tables, update-table, or search-tables. Choose "get-table", "list-tables", or "search-tables" for read-only operations.',
            ),
        ],
        database_name: Annotated[
            str,
            Field(
                description='Name of the database containing the table.',
            ),
        ],
        table_name: Annotated[
            Optional[str],
            Field(
                description='Name of the table (required for create-table, delete-table, get-table, and update-table operations).',
            ),
        ] = None,
        catalog_id: Annotated[
            Optional[str],
            Field(
                description='ID of the catalog (optional, defaults to account ID).',
            ),
        ] = None,
        table_input: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='Table definition for create-table and update-table operations.',
            ),
        ] = None,
        search_text: Annotated[
            Optional[str],
            Field(
                description='Search text for search-tables operation.',
            ),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(
                description='Maximum number of results to return for list and search-tables operations.',
            ),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(description='A continuation token, included if this is a continuation call.'),
        ] = None,
    ) -> CallToolResult:
        """Manage AWS Glue Data Catalog tables with both read and write operations.

        This tool provides comprehensive operations for managing Glue Data Catalog tables,
        including creating, updating, retrieving, listing, searching, and deleting tables.
        Tables define the schema and metadata for data stored in various formats and locations.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-table, update-table, and delete-table operations
        - Database must exist before creating tables within it
        - Appropriate AWS permissions for Glue Data Catalog operations

        ## Operations
        - **create-table**: Create a new table in the specified database
        - **delete-table**: Delete an existing table from the database
        - **get-table**: Retrieve detailed information about a specific table
        - **list-tables**: List all tables in the specified database
        - **update-table**: Update an existing table's properties
        - **search-tables**: Search for tables using text matching

        ## Usage Tips
        - Table names must be unique within a database
        - Use get-table or list-tables operations to check existing tables before creating
        - Table input should include storage descriptor, columns, and partitioning information

        Args:
            ctx: MCP context
            operation: Operation to perform
            database_name: Name of the database
            table_name: Name of the table
            catalog_id: ID of the catalog (optional, defaults to account ID)
            table_input: Table definition
            search_text: Search text for search operation
            max_results: Maximum results to return
            next_token: A continuation string token, if this is a continuation call

        Returns:
            Union of response types specific to the operation performed
        """
        if operation not in [
            'create-table',
            'delete-table',
            'get-table',
            'list-tables',
            'update-table',
            'search-tables',
        ]:
            error_message = f'Invalid operation: {operation}. Must be one of: create-table, delete-table, get-table, list-tables, update-table, search-tables'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

        try:
            if not self.allow_write and operation not in [
                'get-table',
                'list-tables',
                'search-tables',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

            if operation == 'create-table':
                if database_name is None or table_input is None or table_name is None:
                    raise ValueError(
                        'database_name, table_input and table_name are required for create-table operation'
                    )
                return await self.data_catalog_table_manager.create_table(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    table_input=table_input,
                    catalog_id=catalog_id,
                )

            elif operation == 'delete-table':
                if table_name is None or database_name is None:
                    raise ValueError(
                        'table_name and database_name required for delete-table operation'
                    )
                return await self.data_catalog_table_manager.delete_table(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    catalog_id=catalog_id,
                )

            elif operation == 'get-table':
                if table_name is None:
                    raise ValueError('table_name is required for get-table operation')
                return await self.data_catalog_table_manager.get_table(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    catalog_id=catalog_id,
                )

            elif operation == 'list-tables':
                return await self.data_catalog_table_manager.list_tables(
                    ctx=ctx,
                    database_name=database_name,
                    max_results=max_results,
                    catalog_id=catalog_id,
                    next_token=next_token,
                )

            elif operation == 'update-table':
                if table_name is None or table_input is None:
                    raise ValueError(
                        'table_name and table_input are required for update-table operation'
                    )
                return await self.data_catalog_table_manager.update_table(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    table_input=table_input,
                    catalog_id=catalog_id,
                )

            elif operation == 'search-tables':
                return await self.data_catalog_table_manager.search_tables(
                    ctx=ctx,
                    search_text=search_text,
                    max_results=max_results,
                    catalog_id=catalog_id,
                )
            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-table, delete-table, get-table, list-tables, update-table, search-tables'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_data_catalog_tables: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def manage_aws_glue_data_catalog_connections(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: create-connection, delete-connection, get-connection, list-connections, update-connection, test-connection, or batch-delete-connection. Choose "get-connection" or "list-connections" for read-only operations.',
            ),
        ],
        connection_name: Annotated[
            Optional[str],
            Field(
                description='Name of the connection (required for create-connection, delete-connection, get-connection, update-connection, and test-connection operations).',
            ),
        ] = None,
        connection_input: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='Connection definition for create and update operations.',
            ),
        ] = None,
        catalog_id: Annotated[
            Optional[str],
            Field(
                description='Catalog ID for the connection (optional, defaults to account ID).',
            ),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(description='The maximum number of connections to return in one response.'),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(description='A continuation token, if this is a continuation call.'),
        ] = None,
        hide_password: Annotated[
            Optional[bool],
            Field(
                description='Flag to retrieve the connection metadata without returning the password(for get-connection and list-connections operation).',
            ),
        ] = True,
        test_connection_input: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='TestConnectionInput for testing a non-existing connection (for test-connection operation). Provide either connection_name or test_connection_input.',
            ),
        ] = None,
        connection_name_list: Annotated[
            Optional[List[str]],
            Field(
                description='List of connection names to delete (required for batch-delete-connection operation, max 25).',
            ),
        ] = None,
    ) -> CallToolResult:
        """Manage AWS Glue Data Catalog connections with both read and write operations.

        Connections in AWS Glue store connection information for data stores,
        such as databases, data warehouses, and other data sources. They contain
        connection properties like JDBC URLs, usernames, and other metadata needed
        to connect to external data sources.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create, update, delete, test, and batch-delete operations
        - Appropriate AWS permissions for Glue Data Catalog operations
        - Connection properties must be valid for the connection type

        ## Operations
        - **create-connection**: Create a new connection
        - **delete-connection**: Delete an existing connection
        - **get-connection**: Retrieve detailed information about a specific connection
        - **list-connections**: List all connections
        - **update-connection**: Update an existing connection's properties
        - **test-connection**: Test a connection to validate service credentials
        - **batch-delete-connection**: Delete multiple connections in a single call

        ## Usage Tips
        - Connection names must be unique within your catalog
        - Connection input should include ConnectionType and ConnectionProperties
        - Use get or list operations to check existing connections before creating
        - For test-connection, provide either connection_name (existing) or test_connection_input (new)

        Args:
            ctx: MCP context
            operation: Operation to perform
            connection_name: Name of the connection
            connection_input: Connection definition
            catalog_id: Catalog ID for the connection
            max_results: Maximum results to return
            next_token: A continuation string token, if this is a continuation call
            hide_password: The boolean flag to control connection password in return value for get-connection and list-connections operation
            test_connection_input: TestConnectionInput for test-connection operation
            connection_name_list: List of connection names for batch-delete-connection operation

        Returns:
            Union of response types specific to the operation performed
        """
        if operation not in [
            'create-connection',
            'delete-connection',
            'get-connection',
            'list-connections',
            'update-connection',
            'test-connection',
            'batch-delete-connection',
        ]:
            error_message = f'Invalid operation: {operation}. Must be one of: create-connection, delete-connection, get-connection, list-connections, update-connection, test-connection, batch-delete-connection'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

        try:
            if not self.allow_write and operation not in [
                'get-connection',
                'list-connections',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

            if operation == 'create-connection':
                if connection_name is None or connection_input is None:
                    raise ValueError(
                        'connection_name and connection_input are required for create operation'
                    )
                return await self.data_catalog_manager.create_connection(
                    ctx=ctx,
                    connection_name=connection_name,
                    connection_input=connection_input,
                    catalog_id=catalog_id,
                )

            elif operation == 'delete-connection':
                if connection_name is None:
                    raise ValueError('connection_name is required for delete operation')
                return await self.data_catalog_manager.delete_connection(
                    ctx=ctx, connection_name=connection_name, catalog_id=catalog_id
                )

            elif operation == 'get-connection':
                if connection_name is None:
                    raise ValueError('connection_name is required for get operation')
                return await self.data_catalog_manager.get_connection(
                    ctx=ctx,
                    connection_name=connection_name,
                    catalog_id=catalog_id,
                    hide_password=hide_password,
                )

            elif operation == 'list-connections':
                return await self.data_catalog_manager.list_connections(
                    ctx=ctx,
                    catalog_id=catalog_id,
                    max_results=max_results,
                    next_token=next_token,
                    hide_password=hide_password,
                )

            elif operation == 'update-connection':
                if connection_name is None or connection_input is None:
                    raise ValueError(
                        'connection_name and connection_input are required for update operation'
                    )
                return await self.data_catalog_manager.update_connection(
                    ctx=ctx,
                    connection_name=connection_name,
                    connection_input=connection_input,
                    catalog_id=catalog_id,
                )

            elif operation == 'test-connection':
                if connection_name is None and test_connection_input is None:
                    raise ValueError(
                        'Either connection_name or test_connection_input is required for test-connection operation'
                    )
                return await self.data_catalog_manager.test_connection(
                    ctx=ctx,
                    connection_name=connection_name,
                    catalog_id=catalog_id,
                    test_connection_input=test_connection_input,
                )

            elif operation == 'batch-delete-connection':
                if connection_name_list is None or len(connection_name_list) == 0:
                    raise ValueError(
                        'connection_name_list is required for batch-delete-connection operation'
                    )
                return await self.data_catalog_manager.batch_delete_connection(
                    ctx=ctx,
                    connection_name_list=connection_name_list,
                    catalog_id=catalog_id,
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-connection, delete-connection, get-connection, list-connections, update-connection, test-connection, batch-delete-connection'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_data_catalog_connections: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def manage_aws_glue_connection_types(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: describe-connection-type, list-connection-types. Both are read-only operations.',
            ),
        ],
        connection_type: Annotated[
            Optional[str],
            Field(
                description='The name of the connection type to describe (required for describe-connection-type operation, e.g. JDBC, KAFKA, SALESFORCE).',
            ),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(description='Maximum number of results to return for list-connection-types operation.'),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(description='A continuation token, if this is a continuation call.'),
        ] = None,
    ) -> CallToolResult:
        """Discover and describe AWS Glue connection types.

        This tool provides operations for discovering available connection types in AWS Glue
        and getting detailed information about specific connection types, including their
        supported properties, authentication methods, and compute environments.

        ## Operations
        - **describe-connection-type**: Get full details of a specific connection type including properties, auth config, and compute environments
        - **list-connection-types**: List all available connection types with brief descriptions

        ## Example
        ```python
        # List all available connection types
        manage_aws_glue_connection_types(operation='list-connection-types')

        # Describe a specific connection type
        manage_aws_glue_connection_types(operation='describe-connection-type', connection_type='JDBC')
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            connection_type: Name of the connection type (for describe-connection-type)
            max_results: Maximum results to return
            next_token: Pagination token

        Returns:
            Union of response types specific to the operation performed
        """
        if operation not in ['describe-connection-type', 'list-connection-types']:
            error_message = f'Invalid operation: {operation}. Must be one of: describe-connection-type, list-connection-types'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

        try:
            if operation == 'describe-connection-type':
                if connection_type is None:
                    raise ValueError(
                        'connection_type is required for describe-connection-type operation'
                    )
                return await self.data_catalog_manager.describe_connection_type(
                    ctx=ctx,
                    connection_type=connection_type,
                )

            elif operation == 'list-connection-types':
                return await self.data_catalog_manager.list_connection_types(
                    ctx=ctx,
                    max_results=max_results,
                    next_token=next_token,
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: describe-connection-type, list-connection-types'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_connection_types: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def manage_aws_glue_connection_metadata(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: list-entities, describe-entity, get-entity-records. Choose "list-entities" or "describe-entity" for metadata-only operations. "get-entity-records" requires --allow-sensitive-data-access flag.',
            ),
        ],
        connection_name: Annotated[
            str,
            Field(
                description='Name of the connection that has required credentials to query the connection type (required for all operations).',
            ),
        ],
        entity_name: Annotated[
            Optional[str],
            Field(
                description='Name of the entity (required for describe-entity and get-entity-records operations).',
            ),
        ] = None,
        catalog_id: Annotated[
            Optional[str],
            Field(
                description='Catalog ID (optional, defaults to AWS account ID).',
            ),
        ] = None,
        parent_entity_name: Annotated[
            Optional[str],
            Field(
                description='Name of the parent entity for listing child entities (for list-entities operation).',
            ),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(description='A continuation token, if this is a continuation call.'),
        ] = None,
        data_store_api_version: Annotated[
            Optional[str],
            Field(
                description='The API version of the SaaS connector.',
            ),
        ] = None,
        limit: Annotated[
            Optional[int],
            Field(
                description='Maximum number of records to fetch (1-1000, required for get-entity-records operation).',
            ),
        ] = None,
        connection_options: Annotated[
            Optional[Dict[str, str]],
            Field(
                description='Connector options required to query the data (for get-entity-records operation).',
            ),
        ] = None,
        filter_predicate: Annotated[
            Optional[str],
            Field(
                description='A filter predicate to apply in the query request (for get-entity-records operation).',
            ),
        ] = None,
        selected_fields: Annotated[
            Optional[List[str]],
            Field(
                description='List of fields to fetch as part of preview data (for get-entity-records operation).',
            ),
        ] = None,
    ) -> CallToolResult:
        """Access connection metadata and preview entity data from AWS Glue connections.

        This tool provides operations for discovering entities available through a connection,
        describing entity schemas, and previewing entity data. Useful for exploring data sources
        connected via AWS Glue connections such as SaaS applications, databases, and other data stores.

        ## Requirements
        - The server must be run with the `--allow-sensitive-data-access` flag for get-entity-records operation
        - Appropriate AWS permissions for Glue connection metadata operations
        - A valid connection with credentials must exist

        ## Operations
        - **list-entities**: List available entities (e.g., tables, SObjects) for a connection
        - **describe-entity**: Get the schema/field details for a specific entity
        - **get-entity-records**: Preview data records from an entity (requires sensitive data access)

        ## Example
        ```python
        # List entities for a Salesforce connection
        manage_aws_glue_connection_metadata(
            operation='list-entities',
            connection_name='my-salesforce-connection',
        )

        # Describe the Account entity
        manage_aws_glue_connection_metadata(
            operation='describe-entity',
            connection_name='my-salesforce-connection',
            entity_name='Account',
        )

        # Preview records from the Account entity
        manage_aws_glue_connection_metadata(
            operation='get-entity-records',
            connection_name='my-salesforce-connection',
            entity_name='Account',
            limit=10,
        )
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            connection_name: Name of the connection
            entity_name: Name of the entity
            catalog_id: Catalog ID
            parent_entity_name: Parent entity name for listing children
            next_token: Pagination token
            data_store_api_version: API version of the SaaS connector
            limit: Maximum number of records to fetch
            connection_options: Connector options for querying data
            filter_predicate: Filter predicate for the query
            selected_fields: List of fields to fetch

        Returns:
            Union of response types specific to the operation performed
        """
        if operation not in ['list-entities', 'describe-entity', 'get-entity-records']:
            error_message = f'Invalid operation: {operation}. Must be one of: list-entities, describe-entity, get-entity-records'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

        try:
            if operation == 'get-entity-records' and not self.allow_sensitive_data_access:
                error_message = 'Operation get-entity-records requires --allow-sensitive-data-access flag to be enabled'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

            if operation == 'list-entities':
                return await self.data_catalog_manager.list_entities(
                    ctx=ctx,
                    connection_name=connection_name,
                    catalog_id=catalog_id,
                    parent_entity_name=parent_entity_name,
                    next_token=next_token,
                    data_store_api_version=data_store_api_version,
                )

            elif operation == 'describe-entity':
                if entity_name is None:
                    raise ValueError(
                        'entity_name is required for describe-entity operation'
                    )
                return await self.data_catalog_manager.describe_entity(
                    ctx=ctx,
                    connection_name=connection_name,
                    entity_name=entity_name,
                    catalog_id=catalog_id,
                    next_token=next_token,
                    data_store_api_version=data_store_api_version,
                )

            elif operation == 'get-entity-records':
                if entity_name is None:
                    raise ValueError(
                        'entity_name is required for get-entity-records operation'
                    )
                if limit is None:
                    raise ValueError(
                        'limit is required for get-entity-records operation'
                    )
                return await self.data_catalog_manager.get_entity_records(
                    ctx=ctx,
                    connection_name=connection_name,
                    entity_name=entity_name,
                    limit=limit,
                    catalog_id=catalog_id,
                    next_token=next_token,
                    data_store_api_version=data_store_api_version,
                    connection_options=connection_options,
                    filter_predicate=filter_predicate,
                    selected_fields=selected_fields,
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: list-entities, describe-entity, get-entity-records'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_connection_metadata: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def manage_aws_glue_data_catalog_partitions(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: create-partition, delete-partition, get-partition, list-partitions, or update-partition. Choose "get-partition" or "list-partitions" for read-only operations.',
            ),
        ],
        database_name: Annotated[
            str,
            Field(
                description='Name of the database containing the table.',
            ),
        ],
        table_name: Annotated[
            str,
            Field(
                description='Name of the table containing the partition.',
            ),
        ],
        partition_values: Annotated[
            Optional[List[str]],
            Field(
                description='Values that define the partition (required for create-partition, delete-partition, get-partition, and update-partition operations).',
            ),
        ] = None,
        partition_input: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='Partition definition for create-partition and update-partition operations.',
            ),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(
                description='Maximum number of results to return for list-partitions operation.',
            ),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(
                description='A continuation token, if this is not the first call to retrieve these partitions.',
            ),
        ] = None,
        expression: Annotated[
            Optional[str],
            Field(
                description='Filter expression for list-partitions operation.',
            ),
        ] = None,
        catalog_id: Annotated[
            Optional[str],
            Field(
                description='ID of the catalog (optional, defaults to account ID).',
            ),
        ] = None,
    ) -> CallToolResult:
        """Manage AWS Glue Data Catalog partitions with both read and write operations.

        Partitions in AWS Glue represent a way to organize table data based on the values
        of one or more columns. They enable efficient querying and processing of large datasets
        by allowing queries to target specific subsets of data.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-partition, update-partition, and delete-partition operations
        - Database and table must exist before creating partitions
        - Partition values must match the partition schema defined in the table

        ## Operations
        - **create-partition**: Create a new partition in the specified table
        - **delete-partition**: Delete an existing partition from the table
        - **get-partition**: Retrieve detailed information about a specific partition
        - **list-partitions**: List all partitions in the specified table
        - **update-partition**: Update an existing partition's properties

        ## Usage Tips
        - Partition values must be provided in the same order as partition columns in the table
        - Use get-partition or list-partitions operations to check existing partitions before creating
        - Partition input should include storage descriptor and location information

        Args:
            ctx: MCP context
            operation: Operation to perform
            database_name: Name of the database
            table_name: Name of the table
            partition_values: Values that define the partition
            partition_input: Partition definition
            max_results: Maximum results to return
            next_token: A continuation token, if this is not the first call to retrieve these partitions
            expression: Filter expression for list-partitions operation
            catalog_id: ID of the catalog (optional, defaults to account ID)

        Returns:
            Union of response types specific to the operation performed
        """
        if operation not in [
            'create-partition',
            'delete-partition',
            'get-partition',
            'list-partitions',
            'update-partition',
        ]:
            error_message = f'Invalid operation: {operation}. Must be one of: create-partition, delete-partition, get-partition, list-partitions, update-partition'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
        try:
            if not self.allow_write and operation not in [
                'get-partition',
                'list-partitions',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

            if operation == 'create-partition':
                if partition_values is None or partition_input is None:
                    raise ValueError(
                        'partition_values and partition_input are required for create-partition operation'
                    )
                return await self.data_catalog_manager.create_partition(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    partition_values=partition_values,
                    partition_input=partition_input,
                    catalog_id=catalog_id,
                )

            elif operation == 'delete-partition':
                if partition_values is None:
                    raise ValueError('partition_values is required for delete-partition operation')
                return await self.data_catalog_manager.delete_partition(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    partition_values=partition_values,
                    catalog_id=catalog_id,
                )

            elif operation == 'get-partition':
                if partition_values is None:
                    raise ValueError('partition_values is required for get-partition operation')
                return await self.data_catalog_manager.get_partition(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    partition_values=partition_values,
                    catalog_id=catalog_id,
                )

            elif operation == 'list-partitions':
                return await self.data_catalog_manager.list_partitions(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    max_results=max_results,
                    expression=expression,
                    catalog_id=catalog_id,
                    next_token=next_token,
                )

            elif operation == 'update-partition':
                if partition_values is None or partition_input is None:
                    raise ValueError(
                        'partition_values and partition_input are required for update-partition operation'
                    )
                return await self.data_catalog_manager.update_partition(
                    ctx=ctx,
                    database_name=database_name,
                    table_name=table_name,
                    partition_values=partition_values,
                    partition_input=partition_input,
                    catalog_id=catalog_id,
                )
            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-partition, delete-partition, get-partition, list-partitions, update-partition'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_data_catalog_partitions: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def manage_aws_glue_data_catalog(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: create-catalog, delete-catalog, get-catalog, list-catalogs, or import-catalog-to-glue. Choose "get-catalog" or "list-catalogs" for read-only operations.',
            ),
        ],
        catalog_id: Annotated[
            Optional[str],
            Field(
                description='ID of the catalog (required for create-catalog, delete-catalog, get-catalog, and import-catalog-to-glue operations).',
            ),
        ] = None,
        catalog_input: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='Catalog definition for create-catalog operations.',
            ),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(description='The maximum number of catalogs to return in one response.'),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(description='A continuation token, if this is a continuation call.'),
        ] = None,
        parent_catalog_id: Annotated[
            Optional[str],
            Field(
                description='The ID of the parent catalog in which the catalog resides. If none is provided, the AWS Account Number is used by default.',
            ),
        ] = None,
    ) -> CallToolResult:
        """Manage AWS Glue Data Catalog with both read and write operations.

        This tool provides operations for managing the Glue Data Catalog itself,
        including creating custom catalogs, importing from external sources,
        and managing catalog-level configurations.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-catalog, delete-catalog, and import operations
        - Appropriate AWS permissions for Glue Data Catalog operations
        - For import operations, access to the external data source is required

        ## Operations
        - **create-catalog**: Create a new data catalog
        - **delete-catalog**: Delete an existing data catalog
        - **get-catalog**: Retrieve detailed information about a specific catalog
        - **list-catalogs**: List all available catalogs
        - **import-catalog-to-glue**: Import metadata from external sources into Glue Data Catalog

        ## Usage Tips
        - The default catalog ID is your AWS account ID
        - Custom catalogs allow for better organization and access control
        - Import operations can take significant time depending on source size

        Args:
            ctx: MCP context
            operation: Operation to perform
            catalog_id: ID of the catalog
            catalog_input: Catalog definition
            max_results: The maximum number of catalogs to return in one response
            next_token: A continuation token, if this is a continuation call.
            parent_catalog_id: The ID of the parent catalog in which the catalog resides

        Returns:
            Union of response types specific to the operation performed
        """
        if operation not in [
            'create-catalog',
            'delete-catalog',
            'get-catalog',
            'list-catalogs',
            'import-catalog-to-glue',
        ]:
            error_message = f'Invalid operation: {operation}. Must be one of: create-catalog, delete-catalog, get-catalog, list-catalogs, import-catalog-to-glue'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

        try:
            if not self.allow_write and operation not in [
                'get-catalog',
                'list-catalogs',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

            if operation == 'create-catalog':
                if catalog_id is None or catalog_input is None:
                    raise ValueError(
                        'catalog_id and catalog_input are required for create-catalog operation'
                    )
                return await self.data_catalog_manager.create_catalog(
                    ctx=ctx, catalog_name=catalog_id, catalog_input=catalog_input
                )

            elif operation == 'delete-catalog':
                if catalog_id is None:
                    raise ValueError('catalog_id is required for delete-catalog operation')
                return await self.data_catalog_manager.delete_catalog(
                    ctx=ctx, catalog_id=catalog_id
                )

            elif operation == 'get-catalog':
                if catalog_id is None:
                    raise ValueError('catalog_id is required for get-catalog operation')
                return await self.data_catalog_manager.get_catalog(ctx=ctx, catalog_id=catalog_id)

            elif operation == 'list-catalogs':
                return await self.data_catalog_manager.list_catalogs(
                    ctx=ctx,
                    max_results=max_results,
                    next_token=next_token,
                    parent_catalog_id=parent_catalog_id,
                )

            elif operation == 'import-catalog-to-glue':
                if catalog_id is None:
                    raise ValueError('catalog_id is required for import-catalog-to-glue operation')
                return await self.data_catalog_manager.import_catalog_to_glue(
                    ctx=ctx,
                    catalog_id=catalog_id,
                )
            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-catalog, delete-catalog, get-catalog, list-catalogs, import-catalog-to-glue'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_data_catalog: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
