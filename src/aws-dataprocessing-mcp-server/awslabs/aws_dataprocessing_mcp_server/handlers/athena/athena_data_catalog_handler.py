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

"""AthenaDataCatalogHandler for Data Processing MCP Server."""

import json
from awslabs.aws_dataprocessing_mcp_server.models.athena_models import (
    CreateDataCatalogResponse,
    DeleteDataCatalogResponse,
    GetDatabaseResponse,
    GetDataCatalogResponse,
    GetTableMetadataResponse,
    ListDatabasesResponse,
    ListDataCatalogsResponse,
    ListTableMetadataResponse,
    UpdateDataCatalogResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict, Optional, Union


class AthenaDataCatalogHandler:
    """Handler for Amazon Athena Data Catalog operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Athena Data Catalog handler.

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
        self.mcp.tool(name='manage_aws_athena_data_catalogs')(self.manage_aws_athena_data_catalogs)
        self.mcp.tool(name='manage_aws_athena_databases_and_tables')(
            self.manage_aws_athena_databases_and_tables
        )

    async def manage_aws_athena_data_catalogs(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: create-data-catalog, delete-data-catalog, get-data-catalog, list-data-catalogs, update-data-catalog. Choose read-only operations when write access is disabled.',
        ),
        name: Optional[str] = Field(
            None,
            description='Name of the data catalog (required for create-data-catalog, delete-data-catalog, get-data-catalog, update-data-catalog). The catalog name must be unique for the AWS account and can use a maximum of 127 alphanumeric, underscore, at sign, or hyphen characters.',
        ),
        type: Optional[str] = Field(
            None,
            description='Type of the data catalog (required for create-data-catalog and update-data-catalog). Valid values: LAMBDA, GLUE, HIVE, FEDERATED.',
        ),
        description: Optional[str] = Field(
            None,
            description='Description of the data catalog (optional for create-data-catalog and update-data-catalog).',
        ),
        parameters: Optional[Dict[str, str]] = Field(
            None,
            description="Parameters for the data catalog (optional for create-data-catalog and update-data-catalog). Format depends on catalog type (e.g., for LAMBDA: 'metadata-function=lambda_arn,record-function=lambda_arn' or 'function=lambda_arn').",
        ),
        tags: Optional[Dict[str, str]] = Field(
            None,
            description='Tags for the data catalog (optional for create-data-catalog).',
        ),
        max_results: Optional[int] = Field(
            None,
            description='Maximum number of results to return for list-data-catalogs operation (range: 2-50).',
        ),
        next_token: Optional[str] = Field(
            None,
            description='Pagination token for list-data-catalogs operation.',
        ),
        work_group: Optional[str] = Field(
            None,
            description='The name of the workgroup (required if making an IAM Identity Center request).',
        ),
        delete_catalog_only: Optional[bool] = Field(
            None,
            description='For delete-data-catalog operation, whether to delete only the Athena Data Catalog (true) or also its resources (false). Only applicable for FEDERATED catalogs.',
        ),
    ) -> Union[
        CreateDataCatalogResponse,
        DeleteDataCatalogResponse,
        GetDataCatalogResponse,
        ListDataCatalogsResponse,
        UpdateDataCatalogResponse,
    ]:
        """Manage AWS Athena data catalogs with both read and write operations.

        This tool provides operations for managing Athena data catalogs, including creating,
        retrieving, listing, updating, and deleting data catalogs. Data catalogs are used to
        organize and access data sources in Athena, enabling you to query data across various
        sources like AWS Glue Data Catalog, Apache Hive metastores, or federated sources.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-data-catalog, delete-data-catalog, and update-data-catalog operations
        - Appropriate AWS permissions for Athena data catalog operations

        ## Operations
        - **create-data-catalog**: Create a new data catalog
        - **delete-data-catalog**: Delete an existing data catalog
        - **get-data-catalog**: Get information about a single data catalog
        - **list-data-catalogs**: List all data catalogs
        - **update-data-catalog**: Update an existing data catalog

        ## Usage Tips
        - Use list-data-catalogs to find available data catalogs
        - Data catalogs can be of type LAMBDA, GLUE, HIVE, or FEDERATED
        - Parameters are specific to the type of data catalog

        ## Example
        ```
        # List all data catalogs
        {'operation': 'list-data-catalogs', 'max_results': 10}

        # Create a Glue data catalog
        {
            'operation': 'create-data-catalog',
            'name': 'my-glue-catalog',
            'type': 'GLUE',
            'description': 'My Glue Data Catalog',
            'parameters': {'catalog-id': '123456789012'},
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            name: Name of the data catalog
            type: Type of the data catalog (LAMBDA, GLUE, HIVE, FEDERATED)
            description: Description of the data catalog
            parameters: Parameters for the data catalog
            tags: Tags for the data catalog
            max_results: Maximum number of results to return
            next_token: Pagination token
            work_group: The name of the workgroup
            delete_catalog_only: Whether to delete only the Athena Data Catalog

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation in [
                'create-data-catalog',
                'delete-data-catalog',
                'update-data-catalog',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'create-data-catalog':
                    return CreateDataCatalogResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        name='',
                        operation='create-data-catalog',
                    )
                elif operation == 'delete-data-catalog':
                    return DeleteDataCatalogResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        name='',
                        operation='delete-data-catalog',
                    )
                elif operation == 'update-data-catalog':
                    return UpdateDataCatalogResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        name='',
                        operation='update-data-catalog',
                    )

            if operation == 'create-data-catalog':
                if name is None or type is None:
                    raise ValueError(
                        'name and type are required for create-data-catalog operation'
                    )

                # Prepare parameters
                params = {
                    'Name': name,
                    'Type': type,
                }

                if description is not None:
                    params['Description'] = description

                if parameters is not None:
                    params['Parameters'] = json.dumps(parameters)

                # Add MCP management tags
                resource_tags = AwsHelper.prepare_resource_tags('AthenaDataCatalog', tags)
                aws_tags = AwsHelper.convert_tags_to_aws_format(resource_tags)
                params['Tags'] = aws_tags

                # Create data catalog
                self.athena_client.create_data_catalog(**params)

                return CreateDataCatalogResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully created data catalog {name}',
                        )
                    ],
                    name=name,
                    operation='create-data-catalog',
                )

            elif operation == 'delete-data-catalog':
                if name is None:
                    raise ValueError('name is required for delete-data-catalog operation')

                # Prepare parameters
                params = {'Name': name}
                if delete_catalog_only is not None:
                    params['DeleteCatalogOnly'] = str(delete_catalog_only).lower()

                # Delete data catalog
                response = self.athena_client.delete_data_catalog(**params)
                status = response.get('DataCatalog', {}).get('Status', '')
                if status == 'DELETE_FAILED':
                    return DeleteDataCatalogResponse(
                        isError=True,
                        content=[
                            TextContent(
                                type='text',
                                text='Data Catalog delete operation failed',
                            )
                        ],
                        name=name,
                        operation='delete-data-catalog',
                    )
                else:
                    return DeleteDataCatalogResponse(
                        isError=False,
                        content=[
                            TextContent(
                                type='text',
                                text=f'Successfully deleted data catalog {name}',
                            )
                        ],
                        name=name,
                        operation='delete-data-catalog',
                    )

            elif operation == 'get-data-catalog':
                if name is None:
                    raise ValueError('name is required for get-data-catalog operation')

                # Prepare parameters
                params = {'Name': name}
                if work_group is not None:
                    params['WorkGroup'] = work_group

                # Get data catalog
                response = self.athena_client.get_data_catalog(**params)

                return GetDataCatalogResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved data catalog {name}',
                        )
                    ],
                    data_catalog=response.get('DataCatalog', {}),
                    operation='get-data-catalog',
                )

            elif operation == 'list-data-catalogs':
                # Prepare parameters
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token
                if work_group is not None:
                    params['WorkGroup'] = work_group

                # List data catalogs
                response = self.athena_client.list_data_catalogs(**params)

                data_catalogs = response.get('DataCatalogsSummary', [])
                return ListDataCatalogsResponse(
                    isError=False,
                    content=[TextContent(type='text', text='Successfully listed data catalogs')],
                    data_catalogs=data_catalogs,
                    count=len(data_catalogs),
                    next_token=response.get('NextToken'),
                    operation='list-data-catalogs',
                )

            elif operation == 'update-data-catalog':
                if name is None:
                    raise ValueError('name is required for update-data-catalog operation')
                # Prepare parameters
                params = {'Name': name}

                if type is not None:
                    params['Type'] = type

                if description is not None:
                    params['Description'] = description

                if parameters is not None:
                    params['Parameters'] = json.dumps(parameters)

                # Update data catalog
                self.athena_client.update_data_catalog(**params)

                return UpdateDataCatalogResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully updated data catalog {name}',
                        )
                    ],
                    name=name,
                    operation='update-data-catalog',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-data-catalog, delete-data-catalog, get-data-catalog, list-data-catalogs, update-data-catalog'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetDataCatalogResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    data_catalog={},
                    operation='get-data-catalog',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_athena_data_catalogs: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetDataCatalogResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                data_catalog={},
                operation='get-data-catalog',
            )

    async def manage_aws_athena_databases_and_tables(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: get-database, get-table-metadata, list-databases, list-table-metadata. These are read-only operations.',
        ),
        catalog_name: str = Field(
            ...,
            description='Name of the data catalog.',
        ),
        database_name: Optional[str] = Field(
            None,
            description='Name of the database (required for get-database, get-table-metadata, list-table-metadata).',
        ),
        table_name: Optional[str] = Field(
            None,
            description='Name of the table (required for get-table-metadata).',
        ),
        expression: Optional[str] = Field(
            None,
            description='Expression to filter tables (optional for list-table-metadata). A regex pattern that pattern-matches table names.',
        ),
        max_results: Optional[int] = Field(
            None,
            description='Maximum number of results to return for list-databases (range: 1-50) and list-table-metadata (range: 1-50) operations.',
        ),
        next_token: Optional[str] = Field(
            None,
            description='Pagination token for list-databases and list-table-metadata operations.',
        ),
        work_group: Optional[str] = Field(
            None,
            description='The name of the workgroup (required if making an IAM Identity Center request).',
        ),
    ) -> Union[
        GetDatabaseResponse,
        GetTableMetadataResponse,
        ListDatabasesResponse,
        ListTableMetadataResponse,
    ]:
        """Manage AWS Athena databases and tables with read operations.

        This tool provides operations for retrieving information about databases and tables
        in Athena data catalogs. These are read-only operations that do not modify any resources.

        ## Requirements
        - Appropriate AWS permissions for Athena database and table operations

        ## Operations
        - **get-database**: Get information about a single database
        - **get-table-metadata**: Get metadata for a specific table
        - **list-databases**: List all databases in a data catalog
        - **list-table-metadata**: List metadata for all tables in a database

        ## Usage Tips
        - Use list-databases to find available databases in a data catalog
        - Use list-table-metadata to find available tables in a database
        - The expression parameter for list-table-metadata supports filtering tables by name pattern

        ## Example
        ```
        # List all databases in a catalog
        {'operation': 'list-databases', 'catalog_name': 'AwsDataCatalog', 'max_results': 10}

        # Get metadata for a specific table
        {
            'operation': 'get-table-metadata',
            'catalog_name': 'AwsDataCatalog',
            'database_name': 'my_database',
            'table_name': 'my_table',
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            catalog_name: Name of the data catalog
            database_name: Name of the database
            table_name: Name of the table
            expression: Expression to filter tables
            max_results: Maximum number of results to return
            next_token: Pagination token
            work_group: The name of the workgroup

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if operation == 'get-database':
                if database_name is None:
                    raise ValueError('database_name is required for get-database operation')

                # Prepare parameters
                params = {
                    'CatalogName': catalog_name,
                    'DatabaseName': database_name,
                }
                if work_group is not None:
                    params['WorkGroup'] = work_group

                # Get database
                response = self.athena_client.get_database(**params)

                return GetDatabaseResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved database {database_name} from catalog {catalog_name}',
                        )
                    ],
                    database=response.get('Database', {}),
                    operation='get-database',
                )

            elif operation == 'get-table-metadata':
                if database_name is None or table_name is None:
                    raise ValueError(
                        'database_name and table_name are required for get-table-metadata operation'
                    )

                # Prepare parameters
                params = {
                    'CatalogName': catalog_name,
                    'DatabaseName': database_name,
                    'TableName': table_name,
                }
                if work_group is not None:
                    params['WorkGroup'] = work_group

                # Get table metadata
                response = self.athena_client.get_table_metadata(**params)

                return GetTableMetadataResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved metadata for table {table_name} in database {database_name} from catalog {catalog_name}',
                        )
                    ],
                    table_metadata=response.get('TableMetadata', {}),
                    operation='get-table-metadata',
                )

            elif operation == 'list-databases':
                # Prepare parameters
                params: Dict[str, Any] = {'CatalogName': catalog_name}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token
                if work_group is not None:
                    params['WorkGroup'] = work_group

                # List databases
                response = self.athena_client.list_databases(**params)

                database_list = response.get('DatabaseList', [])
                return ListDatabasesResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully listed databases in catalog {catalog_name}',
                        )
                    ],
                    database_list=database_list,
                    count=len(database_list),
                    next_token=response.get('NextToken'),
                    operation='list-databases',
                )

            elif operation == 'list-table-metadata':
                if database_name is None:
                    raise ValueError('database_name is required for list-table-metadata operation')

                # Prepare parameters
                params: Dict[str, Any] = {
                    'CatalogName': catalog_name,
                    'DatabaseName': database_name,
                }
                if expression is not None:
                    params['Expression'] = expression
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token
                if work_group is not None:
                    params['WorkGroup'] = work_group

                # List table metadata
                response = self.athena_client.list_table_metadata(**params)

                table_metadata_list = response.get('TableMetadataList', [])
                return ListTableMetadataResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully listed table metadata in database {database_name} from catalog {catalog_name}',
                        )
                    ],
                    table_metadata_list=table_metadata_list,
                    count=len(table_metadata_list),
                    next_token=response.get('NextToken'),
                    operation='list-table-metadata',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: get-database, get-table-metadata, list-databases, list-table-metadata'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetDatabaseResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    database={},
                    operation='get-database',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_athena_databases_and_tables: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetDatabaseResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                database={},
                operation='get-database',
            )
