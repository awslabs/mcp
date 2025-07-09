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

"""Table manager for AWS Glue Data Catalog operations.

This module provides functionality for managing tables in the AWS Glue Data Catalog,
including creating, updating, retrieving, listing, searching, and deleting tables.
"""

from awslabs.aws_dataprocessing_mcp_server.models.data_catalog_models import (
    CreateTableResponse,
    DeleteTableResponse,
    GetTableResponse,
    ListTablesResponse,
    SearchTablesResponse,
    TableSummary,
    UpdateTableResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from botocore.exceptions import ClientError
from datetime import datetime
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Any, Dict, List, Optional


class DataCatalogTableManager:
    """Manager for AWS Glue Data Catalog table operations.

    This class provides methods for creating, updating, retrieving, listing, searching,
    and deleting tables in the AWS Glue Data Catalog. It enforces access controls based
    on write permissions and handles tagging of resources for MCP management.
    """

    def __init__(self, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Data Catalog Table Manager.

        Args:
            allow_write: Whether to enable write operations (create-table, update-table, delete-table)
            allow_sensitive_data_access: Whether to allow access to sensitive data
        """
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.glue_client = AwsHelper.create_boto3_client('glue')

    async def create_table(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        table_input: Dict[str, Any],
        catalog_id: Optional[str] = None,
        partition_indexes: Optional[List[Dict[str, Any]]] = None,
        transaction_id: Optional[str] = None,
        open_table_format_input: Optional[Dict[str, Any]] = None,
    ) -> CreateTableResponse:
        """Create a new table in the AWS Glue Data Catalog.

        Creates a new table with the specified name and properties in the given database.
        The table is tagged with MCP management tags to track resources created by this server.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database to create the table in
            table_name: Name of the table to create
            table_input: Table definition including columns, storage descriptor, etc.
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            partition_indexes: Optional partition indexes for the table
            transaction_id: Optional transaction ID for ACID operations
            open_table_format_input: Optional open table format configuration

        Returns:
            CreateTableResponse with the result of the operation
        """
        try:
            table_input['Name'] = table_name

            # Add MCP management tags
            resource_tags = AwsHelper.prepare_resource_tags('GlueTable')

            # Add tags to table input parameters for backward compatibility
            if 'Parameters' in table_input:
                # Add MCP tags to Parameters
                for key, value in resource_tags.items():
                    table_input['Parameters'][key] = value
            else:
                # Create Parameters with MCP tags
                table_input['Parameters'] = resource_tags

            # Also add AWS resource tags
            kwargs = {
                'DatabaseName': database_name,
                'TableInput': table_input,
            }

            # Note: kwargs already defined above with Tags included

            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if partition_indexes:
                kwargs['PartitionIndexes'] = partition_indexes
            if transaction_id:
                kwargs['TransactionId'] = transaction_id
            if open_table_format_input:
                kwargs['OpenTableFormatInput'] = open_table_format_input

            self.glue_client.create_table(**kwargs)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully created table: {database_name}.{table_name}',
            )

            success_msg = f'Successfully created table: {database_name}.{table_name}'
            return CreateTableResponse(
                isError=False,
                database_name=database_name,
                table_name=table_name,
                operation='create-table',
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to create table {database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CreateTableResponse(
                isError=True,
                database_name=database_name,
                table_name=table_name,
                operation='create-table',
                content=[TextContent(type='text', text=error_message)],
            )

    async def delete_table(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        catalog_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
    ) -> DeleteTableResponse:
        """Delete a table from the AWS Glue Data Catalog.

        Deletes the specified table if it exists and is managed by the MCP server.
        The method verifies that the table has the required MCP management tags
        before allowing deletion.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database containing the table
            table_name: Name of the table to delete
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            transaction_id: Optional transaction ID for ACID operations

        Returns:
            DeleteTableResponse with the result of the operation
        """
        try:
            # First get the table to check if it's managed by MCP
            get_kwargs = {'DatabaseName': database_name, 'Name': table_name}
            if catalog_id:
                get_kwargs['CatalogId'] = catalog_id

            try:
                response = self.glue_client.get_table(**get_kwargs)
                table = response.get('Table', {})
                parameters = table.get('Parameters', {})

                # Construct the ARN for the table
                region = AwsHelper.get_aws_region()
                account_id = catalog_id or AwsHelper.get_aws_account_id()
                partition = AwsHelper.get_aws_partition()
                table_arn = f'arn:{partition}:glue:{region}:{account_id}:table/{database_name}/{table_name}'

                # Check if the table is managed by MCP
                if not AwsHelper.is_resource_mcp_managed(self.glue_client, table_arn, parameters):
                    error_message = f'Cannot delete table {database_name}.{table_name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return DeleteTableResponse(
                        isError=True,
                        database_name=database_name,
                        table_name=table_name,
                        operation='delete-table',
                        content=[TextContent(type='text', text=error_message)],
                    )
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    error_message = f'Table {database_name}.{table_name} not found'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return DeleteTableResponse(
                        isError=True,
                        database_name=database_name,
                        table_name=table_name,
                        operation='delete-table',
                        content=[TextContent(type='text', text=error_message)],
                    )
                else:
                    raise e

            # Proceed with deletion if the table is managed by MCP
            kwargs = {'DatabaseName': database_name, 'Name': table_name}

            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if transaction_id:
                kwargs['TransactionId'] = transaction_id

            self.glue_client.delete_table(**kwargs)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully deleted table: {database_name}.{table_name}',
            )

            success_msg = f'Successfully deleted table: {database_name}.{table_name}'
            return DeleteTableResponse(
                isError=False,
                database_name=database_name,
                table_name=table_name,
                operation='delete-table',
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to delete table {database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return DeleteTableResponse(
                isError=True,
                database_name=database_name,
                table_name=table_name,
                operation='delete-table',
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_table(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        catalog_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        query_as_of_time: Optional[datetime] = None,
        include_status_details: Optional[bool] = None,
    ) -> GetTableResponse:
        """Get details of a table from the AWS Glue Data Catalog.

        Retrieves detailed information about the specified table, including
        its schema, storage descriptor, parameters, and metadata.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database containing the table
            table_name: Name of the table to retrieve
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            transaction_id: Optional transaction ID for ACID operations
            query_as_of_time: Optional timestamp for time-travel queries
            include_status_details: Whether to include status details in the response

        Returns:
            GetTableResponse with the table details
        """
        try:
            kwargs = {'DatabaseName': database_name, 'Name': table_name}

            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if transaction_id:
                kwargs['TransactionId'] = transaction_id
            if query_as_of_time:
                kwargs['QueryAsOfTime'] = query_as_of_time  # type: ignore
            if include_status_details is not None:
                kwargs['IncludeStatusDetails'] = include_status_details  # type: ignore

            response = self.glue_client.get_table(**kwargs)
            table = response['Table']

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully retrieved table: {database_name}.{table_name}',
            )

            success_msg = f'Successfully retrieved table: {database_name}.{table_name}'
            return GetTableResponse(
                isError=False,
                database_name=database_name,
                table_name=table['Name'],
                table_definition=table,
                creation_time=(
                    table.get('CreateTime', '').isoformat() if table.get('CreateTime') else ''
                ),
                last_access_time=(
                    table.get('LastAccessTime', '').isoformat()
                    if table.get('LastAccessTime')
                    else ''
                ),
                storage_descriptor=table.get('StorageDescriptor', {}),
                partition_keys=table.get('PartitionKeys', []),
                operation='get-table',
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to get table {database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return GetTableResponse(
                isError=True,
                database_name=database_name,
                table_name=table_name,
                table_definition={},
                creation_time='',
                last_access_time='',
                storage_descriptor={},
                partition_keys=[],
                operation='get-table',
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_tables(
        self,
        ctx: Context,
        database_name: str,
        max_results: Optional[int] = None,
        catalog_id: Optional[str] = None,
        expression: Optional[str] = None,
        next_token: Optional[str] = None,
        transaction_id: Optional[str] = None,
        query_as_of_time: Optional[datetime] = None,
        include_status_details: Optional[bool] = None,
        attributes_to_get: Optional[List[str]] = None,
    ) -> ListTablesResponse:
        """List tables in a database in the AWS Glue Data Catalog.

        Retrieves a list of tables with their basic properties. Supports
        pagination through the next_token parameter and filtering by expression.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database to list tables from
            max_results: Optional maximum number of results to return
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            expression: Optional filter expression to narrow results
            next_token: Optional pagination token for retrieving the next set of results
            transaction_id: Optional transaction ID for ACID operations
            query_as_of_time: Optional timestamp for time-travel queries
            include_status_details: Whether to include status details in the response
            attributes_to_get: Optional list of specific attributes to retrieve

        Returns:
            ListTablesResponse with the list of tables
        """
        try:
            kwargs = {'DatabaseName': database_name}

            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if expression:
                kwargs['Expression'] = expression
            if next_token:
                kwargs['NextToken'] = next_token
            if max_results:
                kwargs['MaxResults'] = max_results  # type: ignore
            if transaction_id:
                kwargs['TransactionId'] = transaction_id
            if query_as_of_time:
                kwargs['QueryAsOfTime'] = query_as_of_time  # type: ignore
            if include_status_details is not None:
                kwargs['IncludeStatusDetails'] = include_status_details  # type: ignore
            if attributes_to_get:
                kwargs['AttributesToGet'] = attributes_to_get  # type: ignore

            response = self.glue_client.get_tables(**kwargs)
            tables = response.get('TableList', [])
            next_token_response = response.get('NextToken', None)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully listed {len(tables)} tables in database {database_name}',
            )

            success_msg = f'Successfully listed {len(tables)} tables in database {database_name}'
            return ListTablesResponse(
                isError=False,
                database_name=database_name,
                tables=[
                    TableSummary(
                        name=table['Name'],
                        database_name=table.get('DatabaseName', database_name),
                        owner=table.get('Owner', ''),
                        creation_time=(
                            table.get('CreateTime', '').isoformat()
                            if table.get('CreateTime')
                            else ''
                        ),
                        update_time=(
                            table.get('UpdateTime', '').isoformat()
                            if table.get('UpdateTime')
                            else ''
                        ),
                        last_access_time=(
                            table.get('LastAccessTime', '').isoformat()
                            if table.get('LastAccessTime')
                            else ''
                        ),
                        storage_descriptor=table.get('StorageDescriptor', {}),
                        partition_keys=table.get('PartitionKeys', []),
                    )
                    for table in tables
                ],
                count=len(tables),
                operation='list-tables',
                next_token=next_token_response,
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to list tables in database {database_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return ListTablesResponse(
                isError=True,
                database_name=database_name,
                tables=[],
                count=0,
                operation='list-tables',
                content=[TextContent(type='text', text=error_message)],
            )

    async def update_table(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        table_input: Dict[str, Any],
        catalog_id: Optional[str] = None,
        skip_archive: Optional[bool] = None,
        transaction_id: Optional[str] = None,
        version_id: Optional[str] = None,
        view_update_action: Optional[str] = None,
        force: Optional[bool] = None,
    ) -> UpdateTableResponse:
        """Update an existing table in the AWS Glue Data Catalog.

        Updates the properties of the specified table if it exists and is managed
        by the MCP server. The method preserves MCP management tags during the update.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database containing the table
            table_name: Name of the table to update
            table_input: New table definition including columns, storage descriptor, etc.
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            skip_archive: Whether to skip archiving the previous version
            transaction_id: Optional transaction ID for ACID operations
            version_id: Optional version ID for optimistic locking
            view_update_action: Optional action for view updates
            force: Whether to force the update even if it might cause data loss

        Returns:
            UpdateTableResponse with the result of the operation
        """
        try:
            # First get the table to check if it's managed by MCP
            get_kwargs = {'DatabaseName': database_name, 'Name': table_name}
            if catalog_id:
                get_kwargs['CatalogId'] = catalog_id

            try:
                response = self.glue_client.get_table(**get_kwargs)
                table = response.get('Table', {})
                parameters = table.get('Parameters', {})

                # Construct the ARN for the table
                region = AwsHelper.get_aws_region()
                account_id = catalog_id or AwsHelper.get_aws_account_id()
                partition = AwsHelper.get_aws_partition()
                table_arn = f'arn:{partition}:glue:{region}:{account_id}:table/{database_name}/{table_name}'

                # Check if the table is managed by MCP
                if not AwsHelper.is_resource_mcp_managed(self.glue_client, table_arn, parameters):
                    error_message = f'Cannot update table {database_name}.{table_name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return UpdateTableResponse(
                        isError=True,
                        database_name=database_name,
                        table_name=table_name,
                        operation='update-table',
                        content=[TextContent(type='text', text=error_message)],
                    )

                # Preserve MCP management tags in the update
                if 'Parameters' in table_input:
                    # Make sure we keep the MCP tags
                    for key, value in parameters.items():
                        if key.startswith('mcp:'):
                            table_input['Parameters'][key] = value
                else:
                    # Copy all parameters including MCP tags
                    table_input['Parameters'] = parameters

            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    error_message = f'Table {database_name}.{table_name} not found'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return UpdateTableResponse(
                        isError=True,
                        database_name=database_name,
                        table_name=table_name,
                        operation='update-table',
                        content=[TextContent(type='text', text=error_message)],
                    )
                else:
                    raise e

            table_input['Name'] = table_name

            kwargs = {'DatabaseName': database_name, 'TableInput': table_input}

            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if skip_archive is not None:
                kwargs['SkipArchive'] = skip_archive  # type: ignore
            if transaction_id:
                kwargs['TransactionId'] = transaction_id
            if version_id:
                kwargs['VersionId'] = version_id
            if view_update_action:
                kwargs['ViewUpdateAction'] = view_update_action
            if force is not None:
                kwargs['Force'] = force  # type: ignore

            self.glue_client.update_table(**kwargs)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully updated table: {database_name}.{table_name}',
            )

            success_msg = f'Successfully updated table: {database_name}.{table_name}'
            return UpdateTableResponse(
                isError=False,
                database_name=database_name,
                table_name=table_name,
                operation='update-table',
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to update table {database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return UpdateTableResponse(
                isError=True,
                database_name=database_name,
                table_name=table_name,
                operation='update-table',
                content=[TextContent(type='text', text=error_message)],
            )

    async def search_tables(
        self,
        ctx: Context,
        search_text: Optional[str] = None,
        max_results: Optional[int] = None,
        catalog_id: Optional[str] = None,
        next_token: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        sort_criteria: Optional[List[Dict[str, str]]] = None,
        resource_share_type: Optional[str] = None,
        include_status_details: Optional[bool] = None,
    ) -> SearchTablesResponse:
        """Search for tables in the AWS Glue Data Catalog.

        Searches for tables across databases using text matching and filters.
        Supports pagination through the next_token parameter and sorting.

        Args:
            ctx: MCP context containing request information
            search_text: Optional text to search for in table names and properties
            max_results: Optional maximum number of results to return
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            next_token: Optional pagination token for retrieving the next set of results
            filters: Optional list of filter criteria to narrow results
            sort_criteria: Optional list of sort criteria for ordering results
            resource_share_type: Optional resource sharing type filter
            include_status_details: Whether to include status details in the response

        Returns:
            SearchTablesResponse with the search results
        """
        try:
            kwargs = {}

            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if next_token:
                kwargs['NextToken'] = next_token
            if filters:
                kwargs['Filters'] = filters
            if search_text:
                kwargs['SearchText'] = search_text
            if sort_criteria:
                kwargs['SortCriteria'] = sort_criteria
            if max_results:
                kwargs['MaxResults'] = max_results
            if resource_share_type:
                kwargs['ResourceShareType'] = resource_share_type
            if include_status_details is not None:
                kwargs['IncludeStatusDetails'] = include_status_details  # type: ignore

            response = self.glue_client.search_tables(**kwargs)
            tables = response.get('TableList', [])
            next_token_response = response.get('NextToken', None)

            log_with_request_id(ctx, LogLevel.INFO, f'Search found {len(tables)} tables')

            success_msg = f'Search found {len(tables)} tables'
            return SearchTablesResponse(
                isError=False,
                tables=[
                    TableSummary(
                        name=table['Name'],
                        database_name=table.get('DatabaseName', ''),
                        owner=table.get('Owner', ''),
                        creation_time=(
                            table.get('CreateTime', '').isoformat()
                            if table.get('CreateTime')
                            else ''
                        ),
                        update_time=(
                            table.get('UpdateTime', '').isoformat()
                            if table.get('UpdateTime')
                            else ''
                        ),
                        last_access_time=(
                            table.get('LastAccessTime', '').isoformat()
                            if table.get('LastAccessTime')
                            else ''
                        ),
                        storage_descriptor=table.get('StorageDescriptor', {}),
                        partition_keys=table.get('PartitionKeys', []),
                    )
                    for table in tables
                ],
                search_text=search_text or '',
                count=len(tables),
                operation='search-tables',
                next_token=next_token_response,
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to search tables: {error_code} - {e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return SearchTablesResponse(
                isError=True,
                tables=[],
                search_text=search_text or '',
                count=0,
                operation='search-tables',
                content=[TextContent(type='text', text=error_message)],
            )
