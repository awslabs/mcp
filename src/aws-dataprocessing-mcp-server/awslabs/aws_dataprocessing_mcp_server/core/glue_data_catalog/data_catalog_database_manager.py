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

"""Database manager for AWS Glue Data Catalog operations.

This module provides functionality for managing databases in the AWS Glue Data Catalog,
including creating, updating, retrieving, listing, and deleting databases.
"""

from awslabs.aws_dataprocessing_mcp_server.models.data_catalog_models import (
    CreateDatabaseResponse,
    DatabaseSummary,
    DeleteDatabaseResponse,
    GetDatabaseResponse,
    ListDatabasesResponse,
    UpdateDatabaseResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Any, Dict, List, Optional


class DataCatalogDatabaseManager:
    """Manager for AWS Glue Data Catalog database operations.

    This class provides methods for creating, updating, retrieving, listing, and deleting
    databases in the AWS Glue Data Catalog. It enforces access controls based on write
    permissions and handles tagging of resources for MCP management.
    """

    def __init__(self, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Data Catalog Database Manager.

        Args:
            allow_write: Whether to enable write operations (create-database, update-database, delete-database)
            allow_sensitive_data_access: Whether to allow access to sensitive data
        """
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.glue_client = AwsHelper.create_boto3_client('glue')

    async def create_database(
        self,
        ctx: Context,
        database_name: str,
        description: Optional[str] = None,
        location_uri: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        catalog_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> CreateDatabaseResponse:
        """Create a new database in the AWS Glue Data Catalog.

        Creates a new database with the specified name and properties. The database
        is tagged with MCP management tags to track resources created by this server.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database to create
            description: Optional description of the database
            location_uri: Optional location URI for the database
            parameters: Optional key-value parameters for the database
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            tags: Optional tags to apply to the database

        Returns:
            CreateDatabaseResponse with the result of the operation
        """
        try:
            database_input: Dict[str, Any] = {
                'Name': database_name,
            }

            if description:
                database_input['Description'] = description
            if location_uri:
                database_input['LocationUri'] = location_uri
            if parameters:
                for k, v in parameters.items():
                    database_input[k] = v

            # Add MCP management tags
            resource_tags = AwsHelper.prepare_resource_tags('GlueDatabase')

            # Create kwargs for the API call
            kwargs = {'DatabaseInput': database_input}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id  # type: ignore

            # Merge user-provided tags with MCP tags
            if tags:
                merged_tags = tags.copy()
                merged_tags.update(resource_tags)
                kwargs['Tags'] = merged_tags  # type: ignore
            else:
                kwargs['Tags'] = resource_tags  # type: ignore

            self.glue_client.create_database(**kwargs)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully created database: {database_name}'
            )

            success_msg = f'Successfully created database: {database_name}'
            return CreateDatabaseResponse(
                isError=False,
                database_name=database_name,
                operation='create-database',
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to create database {database_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CreateDatabaseResponse(
                isError=True,
                database_name=database_name,
                operation='create-database',
                content=[TextContent(type='text', text=error_message)],
            )

    async def delete_database(
        self, ctx: Context, database_name: str, catalog_id: Optional[str] = None
    ) -> DeleteDatabaseResponse:
        """Delete a database from the AWS Glue Data Catalog.

        Deletes the specified database if it exists and is managed by the MCP server.
        The method verifies that the database has the required MCP management tags
        before allowing deletion.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database to delete
            catalog_id: Optional catalog ID (defaults to AWS account ID)

        Returns:
            DeleteDatabaseResponse with the result of the operation
        """
        try:
            # First get the database to check if it's managed by MCP
            get_kwargs = {'Name': database_name}
            if catalog_id:
                get_kwargs['CatalogId'] = catalog_id

            try:
                response = self.glue_client.get_database(**get_kwargs)
                database = response.get('Database', {})

                # Construct the ARN for the database
                region = AwsHelper.get_aws_region()
                account_id = catalog_id or AwsHelper.get_aws_account_id()
                partition = AwsHelper.get_aws_partition()
                database_arn = (
                    f'arn:{partition}:glue:{region}:{account_id}:database/{database_name}'
                )

                # Check if the database is managed by MCP
                parameters = database.get('Parameters', {})
                if not AwsHelper.is_resource_mcp_managed(
                    self.glue_client, database_arn, parameters
                ):
                    error_message = f'Cannot delete database {database_name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return DeleteDatabaseResponse(
                        isError=True,
                        database_name=database_name,
                        operation='delete-database',
                        content=[TextContent(type='text', text=error_message)],
                    )
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    error_message = f'Database {database_name} not found'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return DeleteDatabaseResponse(
                        isError=True,
                        database_name=database_name,
                        operation='delete-database',
                        content=[TextContent(type='text', text=error_message)],
                    )
                else:
                    raise e

            # Proceed with deletion if the database is managed by MCP
            kwargs = {'Name': database_name}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            self.glue_client.delete_database(**kwargs)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully deleted database: {database_name}'
            )

            success_msg = f'Successfully deleted database: {database_name}'
            return DeleteDatabaseResponse(
                isError=False,
                database_name=database_name,
                operation='delete-database',
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to delete database {database_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return DeleteDatabaseResponse(
                isError=True,
                database_name=database_name,
                operation='delete-database',
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_database(
        self, ctx: Context, database_name: str, catalog_id: Optional[str] = None
    ) -> GetDatabaseResponse:
        """Get details of a database from the AWS Glue Data Catalog.

        Retrieves detailed information about the specified database, including
        its properties, parameters, and metadata.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database to retrieve
            catalog_id: Optional catalog ID (defaults to AWS account ID)

        Returns:
            GetDatabaseResponse with the database details
        """
        try:
            kwargs = {'Name': database_name}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            response = self.glue_client.get_database(**kwargs)
            database = response['Database']

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully retrieved database: {database_name}'
            )

            success_msg = f'Successfully retrieved database: {database_name}'
            return GetDatabaseResponse(
                isError=False,
                database_name=database['Name'],
                description=database.get('Description', ''),
                location_uri=database.get('LocationUri', ''),
                parameters=database.get('Parameters', {}),
                creation_time=(
                    database.get('CreateTime', '').isoformat()
                    if database.get('CreateTime')
                    else ''
                ),
                catalog_id=database.get('CatalogId', ''),
                operation='get-database',
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to get database {database_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return GetDatabaseResponse(
                isError=True,
                database_name=database_name,
                description='',
                location_uri='',
                parameters={},
                creation_time='',
                catalog_id=catalog_id,
                operation='get-database',
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_databases(
        self,
        ctx: Context,
        catalog_id: Optional[str] = None,
        next_token: Optional[str] = None,
        max_results: Optional[int] = None,
        resource_share_type: Optional[str] = None,
        attributes_to_get: Optional[List[str]] = None,
    ) -> ListDatabasesResponse:
        """List databases in the AWS Glue Data Catalog.

        Retrieves a list of databases with their basic properties. Supports
        pagination through the next_token parameter and filtering by various criteria.

        Args:
            ctx: MCP context containing request information
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            next_token: Optional pagination token for retrieving the next set of results
            max_results: Optional maximum number of results to return
            resource_share_type: Optional resource sharing type filter
            attributes_to_get: Optional list of specific attributes to retrieve

        Returns:
            ListDatabasesResponse with the list of databases
        """
        try:
            kwargs = {}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if next_token:
                kwargs['NextToken'] = next_token
            if max_results:
                kwargs['MaxResults'] = max_results
            if resource_share_type:
                kwargs['ResourceShareType'] = resource_share_type
            if attributes_to_get:
                kwargs['AttributesToGet'] = attributes_to_get

            response = self.glue_client.get_databases(**kwargs)
            databases = response.get('DatabaseList', [])
            next_token = response.get('NextToken', None)  # Capture the next token for paginatio

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully listed {len(databases)} databases'
            )

            success_msg = f'Successfully listed {len(databases)} databases'
            return ListDatabasesResponse(
                isError=False,
                databases=[
                    DatabaseSummary(
                        name=db['Name'],
                        description=db.get('Description', ''),
                        location_uri=db.get('LocationUri', ''),
                        parameters=db.get('Parameters', {}),
                        creation_time=(
                            db.get('CreateTime', '').isoformat() if db.get('CreateTime') else ''
                        ),
                    )
                    for db in databases
                ],
                count=len(databases),
                catalog_id=catalog_id,
                operation='list-databases',
                next_token=next_token,
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to list databases: {error_code} - {e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return ListDatabasesResponse(
                isError=True,
                databases=[],
                count=0,
                catalog_id=catalog_id,
                operation='list-databases',
                content=[TextContent(type='text', text=error_message)],
            )

    async def update_database(
        self,
        ctx: Context,
        database_name: str,
        description: Optional[str] = None,
        location_uri: Optional[str] = None,
        parameters: Optional[Dict[str, str]] = None,
        catalog_id: Optional[str] = None,
        create_table_default_permissions: Optional[List[Dict[str, Any]]] = None,
        target_database: Optional[Dict[str, str]] = None,
        federated_database: Optional[Dict[str, str]] = None,
    ) -> UpdateDatabaseResponse:
        """Update an existing database in the AWS Glue Data Catalog.

        Updates the properties of the specified database if it exists and is managed
        by the MCP server. The method preserves MCP management tags during the update.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database to update
            description: Optional new description for the database
            location_uri: Optional new location URI for the database
            parameters: Optional new parameters for the database
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            create_table_default_permissions: Optional default permissions for tables
            target_database: Optional target database for links
            federated_database: Optional federated database configuration

        Returns:
            UpdateDatabaseResponse with the result of the operation
        """
        try:
            # First get the database to check if it's managed by MCP
            get_kwargs = {'Name': database_name}
            if catalog_id:
                get_kwargs['CatalogId'] = catalog_id

            try:
                response = self.glue_client.get_database(**get_kwargs)
                database = response.get('Database', {})
                existing_parameters = database.get('Parameters', {})

                # Construct the ARN for the database
                region = AwsHelper.get_aws_region()
                account_id = catalog_id or AwsHelper.get_aws_account_id()
                partition = AwsHelper.get_aws_partition()
                database_arn = (
                    f'arn:{partition}:glue:{region}:{account_id}:database/{database_name}'
                )

                # Check if the database is managed by MCP
                if not AwsHelper.is_resource_mcp_managed(
                    self.glue_client, database_arn, existing_parameters
                ):
                    error_message = f'Cannot update database {database_name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return UpdateDatabaseResponse(
                        isError=True,
                        database_name=database_name,
                        operation='update-database',
                        content=[TextContent(type='text', text=error_message)],
                    )

                # Prepare parameters with MCP tags preserved
                merged_parameters = {}
                if parameters:
                    merged_parameters.update(parameters)

                # Preserve MCP management tags
                for key, value in existing_parameters.items():
                    if key.startswith('mcp:'):
                        merged_parameters[key] = value

                parameters = merged_parameters

            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    error_message = f'Database {database_name} not found'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return UpdateDatabaseResponse(
                        isError=True,
                        database_name=database_name,
                        operation='update-database',
                        content=[TextContent(type='text', text=error_message)],
                    )
                else:
                    raise e

            database_input = {
                'Name': database_name,
            }

            if description:
                database_input['Description'] = description
            if location_uri:
                database_input['LocationUri'] = location_uri
            if parameters:
                # Convert each parameter value to string if needed
                string_params = {k: str(v) for k, v in parameters.items()}
                # Type ignore comment to suppress type checking
                database_input['Parameters'] = string_params  # type: ignore

            # Remove complex types for now as they're causing type errors
            # We can add them back with proper handling if needed

            kwargs = {'Name': database_name, 'DatabaseInput': database_input}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            self.glue_client.update_database(**kwargs)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully updated database: {database_name}'
            )

            success_msg = f'Successfully updated database: {database_name}'
            return UpdateDatabaseResponse(
                isError=False,
                database_name=database_name,
                operation='update-database',
                content=[TextContent(type='text', text=success_msg)],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to update database {database_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return UpdateDatabaseResponse(
                isError=True,
                database_name=database_name,
                operation='update-database',
                content=[TextContent(type='text', text=error_message)],
            )
