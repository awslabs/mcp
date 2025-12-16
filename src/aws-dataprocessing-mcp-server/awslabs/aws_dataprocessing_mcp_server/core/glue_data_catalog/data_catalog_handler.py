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

"""Handler for AWS Glue Data Catalog operations.

This module provides functionality for managing connections, partitions, and catalogs
in the AWS Glue Data Catalog, including creating, updating, retrieving, listing, and
deleting these resources.
"""

import json
from awslabs.aws_dataprocessing_mcp_server.models.data_catalog_models import (
    ConnectionSummary,
    CreateCatalogData,
    CreateConnectionData,
    CreatePartitionData,
    DeleteCatalogData,
    DeleteConnectionData,
    DeletePartitionData,
    GetCatalogData,
    GetConnectionData,
    GetPartitionData,
    ImportCatalogData,
    ListCatalogsData,
    ListConnectionsData,
    ListPartitionsData,
    PartitionSummary,
    UpdateConnectionData,
    UpdatePartitionData,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent
from typing import Any, Dict, List, Optional


class DataCatalogManager:
    """Manager for AWS Glue Data Catalog operations.

    This class provides methods for managing connections, partitions, and catalogs
    in the AWS Glue Data Catalog. It enforces access controls based on write
    permissions and handles tagging of resources for MCP management.
    """

    def __init__(self, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Data Catalog Manager.

        Args:
            allow_write: Whether to enable write operations (create-connection, update-connection, delete-connection, create-partition, delete-partition. update-partition, create-catalog, delete-catalog)
            allow_sensitive_data_access: Whether to allow access to sensitive data
        """
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.glue_client = AwsHelper.create_boto3_client('glue')

    async def create_connection(
        self,
        ctx: Context,
        connection_name: str,
        connection_input: Dict[str, Any],
        catalog_id: Optional[str] = '',
        tags: Optional[Dict[str, str]] = None,
    ) -> CallToolResult:
        """Create a new connection in the AWS Glue Data Catalog.

        Creates a new connection with the specified name and properties. The connection
        is tagged with MCP management tags to track resources created by this server.

        Args:
            ctx: MCP context containing request information
            connection_name: Name of the connection to create
            connection_input: Connection definition including type and properties
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            tags: Optional tags to apply to the connection

        Returns:
            CreateConnectionResponse with the result of the operation
        """
        try:
            connection_input['Name'] = connection_name

            kwargs: Dict[str, Any] = {'ConnectionInput': connection_input}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            # # Add MCP management tags
            resource_tags = AwsHelper.prepare_resource_tags('GlueConnection')

            # Merge user-provided tags with MCP tags
            if tags:
                merged_tags = tags.copy()
                merged_tags.update(resource_tags)
                kwargs['Tags'] = merged_tags
            else:
                kwargs['Tags'] = resource_tags

            self.glue_client.create_connection(**kwargs)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully created connection: {connection_name}',
            )

            success_msg = f'Successfully created connection: {connection_name}'
            data = CreateConnectionData(
                connection_name=connection_name,
                catalog_id=catalog_id or '',
                operation='create-connection',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to create connection {connection_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def delete_connection(
        self, ctx: Context, connection_name: str, catalog_id: Optional[str] = None
    ) -> CallToolResult:
        """Delete a connection from the AWS Glue Data Catalog.

        Deletes the specified connection if it exists and is managed by the MCP server.
        The method verifies that the connection has the required MCP management tags
        before allowing deletion.

        Args:
            ctx: MCP context containing request information
            connection_name: Name of the connection to delete
            catalog_id: Optional catalog ID (defaults to AWS account ID)

        Returns:
            DeleteConnectionResponse with the result of the operation
        """
        try:
            # First get the connection to check if it's managed by MCP
            get_kwargs = {'Name': connection_name}
            if catalog_id:
                get_kwargs['CatalogId'] = catalog_id

            try:
                # Construct the ARN for the connection
                region = AwsHelper.get_aws_region()
                account_id = catalog_id or AwsHelper.get_aws_account_id()
                partition = AwsHelper.get_aws_partition()
                connection_arn = (
                    f'arn:{partition}:glue:{region}:{account_id}:connection/{connection_name}'
                )

                # Check if the connection is managed by MCP
                if not AwsHelper.is_resource_mcp_managed(self.glue_client, connection_arn):
                    error_message = f'Cannot delete connection {connection_name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                    )
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    error_message = f'Connection {connection_name} not found'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                    )
                else:
                    raise e

            # Proceed with deletion if the connection is managed by MCP
            kwargs = {'ConnectionName': connection_name}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            self.glue_client.delete_connection(**kwargs)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully deleted connection: {connection_name}',
            )

            success_msg = f'Successfully deleted connection: {connection_name}'
            data = DeleteConnectionData(
                connection_name=connection_name,
                catalog_id=catalog_id or '',
                operation='delete-connection',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to delete connection {connection_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_connection(
        self,
        ctx: Context,
        connection_name: str,
        catalog_id: Optional[str] = None,
        hide_password: Optional[bool] = None,
        apply_override_for_compute_environment: Optional[str] = None,
    ) -> CallToolResult:
        """Get details of a connection from the AWS Glue Data Catalog.

        Retrieves detailed information about the specified connection, including
        its properties, parameters, and metadata.

        Args:
            ctx: MCP context containing request information
            connection_name: Name of the connection to retrieve
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            hide_password: Whether to hide sensitive password information
            apply_override_for_compute_environment: Optional compute environment for overrides

        Returns:
            GetConnectionResponse with the connection details
        """
        try:
            kwargs: Dict[str, Any] = {'Name': connection_name}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if hide_password:
                kwargs['HidePassword'] = hide_password
            if apply_override_for_compute_environment:
                kwargs['ApplyOverrideForComputeEnvironment'] = (
                    apply_override_for_compute_environment
                )

            response = self.glue_client.get_connection(**kwargs)
            connection = response['Connection']

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully retrieved connection: {connection_name}',
            )

            success_msg = f'Successfully retrieved connection: {connection_name}'
            data = GetConnectionData(
                connection_name=connection['Name'],
                connection_type=connection.get('ConnectionType', ''),
                connection_properties=connection.get('ConnectionProperties', {}),
                physical_connection_requirements=connection.get(
                    'PhysicalConnectionRequirements', None
                ),
                creation_time=(
                    connection.get('CreationTime', '').isoformat()
                    if connection.get('CreationTime')
                    else ''
                ),
                last_updated_time=(
                    connection.get('LastUpdatedTime', '').isoformat()
                    if connection.get('LastUpdatedTime')
                    else ''
                ),
                last_updated_by=connection.get('LastUpdatedBy', ''),
                status=connection.get('Status', ''),
                status_reason=connection.get('StatusReason', ''),
                last_connection_validation_time=(
                    connection.get('LastConnectionValidationTime', '').isoformat()
                    if connection.get('LastConnectionValidationTime')
                    else ''
                ),
                catalog_id=catalog_id or '',
                operation='get-connection',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to get connection {connection_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_connections(
        self,
        ctx: Context,
        catalog_id: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        hide_password: Optional[bool] = None,
        next_token: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> CallToolResult:
        """List connections in the AWS Glue Data Catalog.

        Retrieves a list of connections with their basic properties. Supports
        pagination through the next_token parameter and filtering by various criteria.

        Args:
            ctx: MCP context containing request information
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            filter_dict: Optional filter dictionary to narrow results
            hide_password: Whether to hide sensitive password information
            next_token: Optional pagination token for retrieving the next set of results
            max_results: Optional maximum number of results to return

        Returns:
            ListConnectionsResponse with the list of connections
        """
        try:
            kwargs = {}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if filter_dict:
                kwargs['Filter'] = filter_dict
            if hide_password:
                kwargs['HidePassword'] = hide_password
            if next_token:
                kwargs['NextToken'] = next_token
            if max_results:
                kwargs['MaxResults'] = max_results

            response = self.glue_client.get_connections(**kwargs)
            connections = response.get('ConnectionList', [])
            next_token_response = response.get('NextToken', None)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully listed {len(connections)} connections',
            )

            success_msg = f'Successfully listed {len(connections)} connections'
            data = ListConnectionsData(
                connections=[
                    ConnectionSummary(
                        name=conn['Name'],
                        connection_type=conn.get('ConnectionType', ''),
                        connection_properties=conn.get('ConnectionProperties', {}),
                        physical_connection_requirements=conn.get(
                            'PhysicalConnectionRequirements', {}
                        ),
                        creation_time=(
                            conn.get('CreationTime', '').isoformat()
                            if conn.get('CreationTime')
                            else ''
                        ),
                        last_updated_time=(
                            conn.get('LastUpdatedTime', '').isoformat()
                            if conn.get('LastUpdatedTime')
                            else ''
                        ),
                    )
                    for conn in connections
                ],
                count=len(connections),
                catalog_id=catalog_id or '',
                next_token=next_token_response,
                operation='list-connections',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to list connections: {error_code} - {e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def update_connection(
        self,
        ctx: Context,
        connection_name: str,
        connection_input: Dict[str, Any],
        catalog_id: Optional[str] = None,
    ) -> CallToolResult:
        """Update an existing connection in the AWS Glue Data Catalog.

        Updates the properties of the specified connection if it exists and is managed
        by the MCP server. The method preserves MCP management tags during the update.

        Args:
            ctx: MCP context containing request information
            connection_name: Name of the connection to update
            connection_input: New connection definition including type and properties
            catalog_id: Optional catalog ID (defaults to AWS account ID)

        Returns:
            UpdateConnectionResponse with the result of the operation
        """
        try:
            # First get the connection to check if it's managed by MCP
            get_kwargs = {'Name': connection_name}
            if catalog_id:
                get_kwargs['CatalogId'] = catalog_id

            try:
                # Construct the ARN for the connection
                region = AwsHelper.get_aws_region()
                account_id = catalog_id or AwsHelper.get_aws_account_id()
                partition = AwsHelper.get_aws_partition()
                connection_arn = (
                    f'arn:{partition}:glue:{region}:{account_id}:connection/{connection_name}'
                )

                # Check if the connection is managed by MCP
                if not AwsHelper.is_resource_mcp_managed(self.glue_client, connection_arn):
                    error_message = f'Cannot update connection {connection_name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                    )

            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    error_message = f'Connection {connection_name} not found'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                    )
                else:
                    raise e

            connection_input['Name'] = connection_name

            kwargs = {'Name': connection_name, 'ConnectionInput': connection_input}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            self.glue_client.update_connection(**kwargs)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully updated connection: {connection_name}',
            )

            success_msg = f'Successfully updated connection: {connection_name}'
            data = UpdateConnectionData(
                connection_name=connection_name,
                catalog_id=catalog_id or '',
                operation='update-connection',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to update connection {connection_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def create_partition(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        partition_values: List[str],
        partition_input: Dict[str, Any],
        catalog_id: Optional[str] = None,
    ) -> CallToolResult:
        """Create a new partition in a table in the AWS Glue Data Catalog.

        Creates a new partition with the specified values and properties. The partition
        is tagged with MCP management tags to track resources created by this server.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database containing the table
            table_name: Name of the table to add the partition to
            partition_values: Values that define the partition
            partition_input: Partition definition including storage descriptor
            catalog_id: Optional catalog ID (defaults to AWS account ID)

        Returns:
            CreatePartitionResponse with the result of the operation
        """
        try:
            partition_input['Values'] = partition_values

            # Add MCP management tags
            resource_tags = AwsHelper.prepare_resource_tags('GluePartition')

            # Add MCP management information to Parameters for backward compatibility
            if 'Parameters' not in partition_input:
                partition_input['Parameters'] = {}
            for key, value in resource_tags.items():
                partition_input['Parameters'][key] = str(value)

            kwargs: Dict[str, Any] = {
                'DatabaseName': database_name,
                'TableName': table_name,
                'PartitionInput': partition_input,
            }
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            self.glue_client.create_partition(**kwargs)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully created partition in table: {database_name}.{table_name}',
            )

            success_msg = f'Successfully created partition in table: {database_name}.{table_name}'
            data = CreatePartitionData(
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                operation='create-partition',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to create partition in table {database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def delete_partition(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        partition_values: List[str],
        catalog_id: Optional[str] = None,
    ) -> CallToolResult:
        """Delete a partition from a table in the AWS Glue Data Catalog.

        Deletes the specified partition if it exists and is managed by the MCP server.
        The method verifies that the partition has the required MCP management tags
        before allowing deletion.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database containing the table
            table_name: Name of the table containing the partition
            partition_values: Values that define the partition to delete
            catalog_id: Optional catalog ID (defaults to AWS account ID)

        Returns:
            DeletePartitionResponse with the result of the operation
        """
        try:
            # First get the partition to check if it's managed by MCP
            get_kwargs = {
                'DatabaseName': database_name,
                'TableName': table_name,
                'PartitionValues': partition_values,
            }
            if catalog_id:
                get_kwargs['CatalogId'] = catalog_id

            try:
                response = self.glue_client.get_partition(**get_kwargs)
                partition = response.get('Partition', {})
                parameters = partition.get('Parameters', {})

                # Construct the ARN for the partition
                region = AwsHelper.get_aws_region()
                account_id = catalog_id or AwsHelper.get_aws_account_id()
                partition = AwsHelper.get_aws_partition()
                partition_arn = f'arn:{partition}:glue:{region}:{account_id}:partition/{database_name}/{table_name}/{"/".join(partition_values)}'

                # Check if the partition is managed by MCP
                if not AwsHelper.is_resource_mcp_managed(
                    self.glue_client, partition_arn, parameters
                ):
                    error_message = f'Cannot delete partition in table {database_name}.{table_name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                    )
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    error_message = f'Partition in table {database_name}.{table_name} not found'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                    )
                else:
                    raise e

            # Proceed with deletion if the partition is managed by MCP
            kwargs = {
                'DatabaseName': database_name,
                'TableName': table_name,
                'PartitionValues': partition_values,
            }
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            self.glue_client.delete_partition(**kwargs)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully deleted partition from table: {database_name}.{table_name}',
            )

            success_msg = (
                f'Successfully deleted partition from table: {database_name}.{table_name}'
            )
            data = DeletePartitionData(
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                operation='delete-partition',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to delete partition from table {database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_partition(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        partition_values: List[str],
        catalog_id: Optional[str] = None,
    ) -> CallToolResult:
        """Get details of a partition from the AWS Glue Data Catalog.

        Retrieves detailed information about the specified partition, including
        its storage descriptor, parameters, and metadata.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database containing the table
            table_name: Name of the table containing the partition
            partition_values: Values that define the partition to retrieve
            catalog_id: Optional catalog ID (defaults to AWS account ID)

        Returns:
            GetPartitionResponse with the partition details
        """
        try:
            kwargs = {
                'DatabaseName': database_name,
                'TableName': table_name,
                'PartitionValues': partition_values,
            }
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            response = self.glue_client.get_partition(**kwargs)
            partition = response['Partition']

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully retrieved partition from table: {database_name}.{table_name}',
            )

            success_msg = (
                f'Successfully retrieved partition from table: {database_name}.{table_name}'
            )

            # Convert datetime objects in partition_definition to strings
            partition_definition = partition.copy()
            if 'CreationTime' in partition_definition and partition_definition['CreationTime']:
                creation_time_obj = partition_definition['CreationTime']
                if hasattr(creation_time_obj, 'isoformat'):
                    partition_definition['CreationTime'] = creation_time_obj.isoformat()
                else:
                    partition_definition['CreationTime'] = str(creation_time_obj)

            if 'LastAccessTime' in partition_definition and partition_definition['LastAccessTime']:
                last_access_time_obj = partition_definition['LastAccessTime']
                if hasattr(last_access_time_obj, 'isoformat'):
                    partition_definition['LastAccessTime'] = last_access_time_obj.isoformat()
                else:
                    partition_definition['LastAccessTime'] = str(last_access_time_obj)

            # Also check for any other datetime objects in the partition definition
            if (
                'LastAnalyzedTime' in partition_definition
                and partition_definition['LastAnalyzedTime']
            ):
                last_analyzed_time_obj = partition_definition['LastAnalyzedTime']
                if hasattr(last_analyzed_time_obj, 'isoformat'):
                    partition_definition['LastAnalyzedTime'] = last_analyzed_time_obj.isoformat()
                else:
                    partition_definition['LastAnalyzedTime'] = str(last_analyzed_time_obj)

            data = GetPartitionData(
                database_name=database_name,
                table_name=table_name,
                partition_values=partition['Values'],
                partition_definition=partition_definition,
                creation_time=(
                    partition.get('CreationTime', '').isoformat()
                    if partition.get('CreationTime')
                    else ''
                ),
                last_access_time=(
                    partition.get('LastAccessTime', '').isoformat()
                    if partition.get('LastAccessTime')
                    else ''
                ),
                storage_descriptor=partition.get('StorageDescriptor', {}),
                parameters=partition.get('Parameters', {}),
                operation='get-partition',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to get partition from table {database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_partitions(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        max_results: Optional[int] = None,
        expression: Optional[str] = None,
        catalog_id: Optional[str] = None,
        segment: Optional[Dict[str, Any]] = None,
        next_token: Optional[str] = None,
        exclude_column_schema: Optional[bool] = None,
        transaction_id: Optional[str] = None,
        query_as_of_time: Optional[str] = None,
    ) -> CallToolResult:
        """List partitions in a table in the AWS Glue Data Catalog.

        Retrieves a list of partitions with their basic properties. Supports
        pagination through the next_token parameter and filtering by expression.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database containing the table
            table_name: Name of the table to list partitions from
            max_results: Optional maximum number of results to return
            expression: Optional filter expression to narrow results
            catalog_id: Optional catalog ID (defaults to AWS account ID)
            segment: Optional segment specification for parallel listing
            next_token: Optional pagination token for retrieving the next set of results
            exclude_column_schema: Whether to exclude column schema information
            transaction_id: Optional transaction ID for consistent reads
            query_as_of_time: Optional timestamp for time-travel queries

        Returns:
            ListPartitionsResponse with the list of partitions
        """
        try:
            kwargs: Dict[str, Any] = {
                'DatabaseName': database_name,
                'TableName': table_name,
            }
            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if max_results:
                kwargs['MaxResults'] = max_results
            if expression:
                kwargs['Expression'] = expression
            if segment:
                kwargs['Segment'] = segment
            if next_token:
                kwargs['NextToken'] = next_token
            if exclude_column_schema is not None:
                kwargs['ExcludeColumnSchema'] = str(exclude_column_schema).lower()
            if transaction_id:
                kwargs['TransactionId'] = transaction_id
            if query_as_of_time:
                kwargs['QueryAsOfTime'] = query_as_of_time

            response = self.glue_client.get_partitions(**kwargs)
            partitions = response.get('Partitions', [])
            next_token_response = response.get('NextToken', None)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully listed {len(partitions)} partitions in table {database_name}.{table_name}',
            )

            success_msg = f'Successfully listed {len(partitions)} partitions in table {database_name}.{table_name}'
            data = ListPartitionsData(
                database_name=database_name,
                table_name=table_name,
                partitions=[
                    PartitionSummary(
                        values=partition['Values'],
                        database_name=partition.get('DatabaseName', database_name),
                        table_name=partition.get('TableName', table_name),
                        creation_time=(
                            partition.get('CreationTime', '').isoformat()
                            if partition.get('CreationTime')
                            else ''
                        ),
                        last_access_time=(
                            partition.get('LastAccessTime', '').isoformat()
                            if partition.get('LastAccessTime')
                            else ''
                        ),
                        storage_descriptor=partition.get('StorageDescriptor', {}),
                        parameters=partition.get('Parameters', {}),
                    )
                    for partition in partitions
                ],
                count=len(partitions),
                next_token=next_token_response,
                expression=expression,
                operation='list-partitions',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to list partitions in table {database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def update_partition(
        self,
        ctx: Context,
        database_name: str,
        table_name: str,
        partition_values: List[str],
        partition_input: Dict[str, Any],
        catalog_id: Optional[str] = None,
    ) -> CallToolResult:
        """Update an existing partition in the AWS Glue Data Catalog.

        Updates the properties of the specified partition if it exists and is managed
        by the MCP server. The method preserves MCP management tags during the update.

        Args:
            ctx: MCP context containing request information
            database_name: Name of the database containing the table
            table_name: Name of the table containing the partition
            partition_values: Values that define the partition to update
            partition_input: New partition definition including storage descriptor
            catalog_id: Optional catalog ID (defaults to AWS account ID)

        Returns:
            UpdatePartitionResponse with the result of the operation
        """
        try:
            # First get the partition to check if it's managed by MCP
            get_kwargs = {
                'DatabaseName': database_name,
                'TableName': table_name,
                'PartitionValues': partition_values,
            }
            if catalog_id:
                get_kwargs['CatalogId'] = catalog_id

            try:
                response = self.glue_client.get_partition(**get_kwargs)
                partition = response.get('Partition', {})
                parameters = partition.get('Parameters', {})

                # Construct the ARN for the partition
                region = AwsHelper.get_aws_region()
                account_id = catalog_id or AwsHelper.get_aws_account_id()
                partition = AwsHelper.get_aws_partition()
                partition_arn = f'arn:{partition}:glue:{region}:{account_id}:partition/{database_name}/{table_name}/{"/".join(partition_values)}'

                # Check if the partition is managed by MCP
                if not AwsHelper.is_resource_mcp_managed(
                    self.glue_client, partition_arn, parameters
                ):
                    error_message = f'Cannot update partition in table {database_name}.{table_name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                    )

                # Preserve MCP management tags in the update
                if 'Parameters' in partition_input:
                    # Make sure we keep the MCP tags
                    for key, value in parameters.items():
                        if key.startswith('mcp:'):
                            partition_input['Parameters'][key] = value
                else:
                    # Copy all parameters including MCP tags
                    partition_input['Parameters'] = parameters

            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    error_message = f'Partition in table {database_name}.{table_name} not found'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                    )
                else:
                    raise e

            partition_input['Values'] = partition_values

            kwargs = {
                'DatabaseName': database_name,
                'TableName': table_name,
                'PartitionValueList': partition_values,
                'PartitionInput': partition_input,
            }
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            self.glue_client.update_partition(**kwargs)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully updated partition in table: {database_name}.{table_name}',
            )

            success_msg = f'Successfully updated partition in table: {database_name}.{table_name}'
            data = UpdatePartitionData(
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                operation='update-partition',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to update partition in table {database_name}.{table_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def create_catalog(
        self,
        ctx: Context,
        catalog_name: str,
        catalog_input: Dict[str, Any],
        tags: Optional[Dict[str, str]] = None,
    ) -> CallToolResult:
        """Create a new catalog in AWS Glue.

        Creates a new catalog with the specified name and properties. The catalog
        is tagged with MCP management tags to track resources created by this server.

        Args:
            ctx: MCP context containing request information
            catalog_name: Name of the catalog to create
            catalog_input: Catalog definition including properties
            tags: Optional tags to apply to the catalog

        Returns:
            CreateCatalogResponse with the result of the operation
        """
        try:
            # Add MCP management tags
            resource_tags = AwsHelper.prepare_resource_tags('GlueCatalog')

            # Add MCP management information to Parameters for backward compatibility
            if 'Parameters' not in catalog_input:
                catalog_input['Parameters'] = {}
            for key, value in resource_tags.items():
                catalog_input['Parameters'][key] = value

            kwargs = {
                'Name': catalog_name,
                'CatalogInput': catalog_input,
            }

            # Merge user-provided tags with MCP tags
            if tags:
                merged_tags = tags.copy()
                merged_tags.update(resource_tags)
                kwargs['Tags'] = merged_tags
            else:
                kwargs['Tags'] = resource_tags

            self.glue_client.create_catalog(**kwargs)

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully created catalog: {catalog_name}'
            )

            success_msg = f'Successfully created catalog: {catalog_name}'
            data = CreateCatalogData(
                catalog_id=catalog_name,
                operation='create-catalog',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to create catalog {catalog_name}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def delete_catalog(self, ctx: Context, catalog_id: str) -> CallToolResult:
        """Delete a catalog from AWS Glue.

        Deletes the specified catalog if it exists and is managed by the MCP server.
        The method verifies that the catalog has the required MCP management tags
        before allowing deletion.

        Args:
            ctx: MCP context containing request information
            catalog_id: ID of the catalog to delete

        Returns:
            DeleteCatalogResponse with the result of the operation
        """
        try:
            # First get the catalog to check if it's managed by MCP
            get_kwargs = {'CatalogId': catalog_id}

            try:
                response = self.glue_client.get_catalog(**get_kwargs)
                catalog = response.get('Catalog', {})
                parameters = catalog.get('Parameters', {})

                # Construct the ARN for the catalog
                region = AwsHelper.get_aws_region()
                account_id = AwsHelper.get_aws_account_id()  # Get actual account ID
                partition = AwsHelper.get_aws_partition()
                catalog_arn = f'arn:{partition}:glue:{region}:{account_id}:catalog/{catalog_id}'

                # Check if the catalog is managed by MCP
                if not AwsHelper.is_resource_mcp_managed(
                    self.glue_client, catalog_arn, parameters
                ):
                    error_message = f'Cannot delete catalog {catalog_id} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                    )
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    error_message = f'Catalog {catalog_id} not found'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return CallToolResult(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                    )
                else:
                    raise e

            # Proceed with deletion if the catalog is managed by MCP
            kwargs = {'CatalogId': catalog_id}

            self.glue_client.delete_catalog(**kwargs)

            log_with_request_id(ctx, LogLevel.INFO, f'Successfully deleted catalog: {catalog_id}')

            success_msg = f'Successfully deleted catalog: {catalog_id}'
            data = DeleteCatalogData(
                catalog_id=catalog_id,
                operation='delete-catalog',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to delete catalog {catalog_id}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def get_catalog(self, ctx: Context, catalog_id: str) -> CallToolResult:
        """Get details of a catalog from AWS Glue.

        Retrieves detailed information about the specified catalog, including
        its properties, parameters, and metadata.

        Args:
            ctx: MCP context containing request information
            catalog_id: ID of the catalog to retrieve

        Returns:
            GetCatalogResponse with the catalog details
        """
        try:
            kwargs = {'CatalogId': catalog_id}

            response = self.glue_client.get_catalog(**kwargs)
            catalog = response['Catalog']

            log_with_request_id(
                ctx, LogLevel.INFO, f'Successfully retrieved catalog: {catalog_id}'
            )

            success_msg = f'Successfully retrieved catalog: {catalog_id}'

            # Convert datetime objects to ISO strings
            create_time_str = ''
            if catalog.get('CreateTime'):
                create_time_obj = catalog.get('CreateTime')
                if hasattr(create_time_obj, 'isoformat'):
                    create_time_str = create_time_obj.isoformat()
                else:
                    create_time_str = str(create_time_obj)

            update_time_str = ''
            if catalog.get('UpdateTime'):
                update_time_obj = catalog.get('UpdateTime')
                if hasattr(update_time_obj, 'isoformat'):
                    update_time_str = update_time_obj.isoformat()
                else:
                    update_time_str = str(update_time_obj)

            # Create a copy of catalog with datetime objects converted to strings
            catalog_definition = catalog.copy()
            if 'CreateTime' in catalog_definition:
                catalog_definition['CreateTime'] = create_time_str
            if 'UpdateTime' in catalog_definition:
                catalog_definition['UpdateTime'] = update_time_str

            data = GetCatalogData(
                catalog_id=catalog_id,
                catalog_definition=catalog_definition,
                name=catalog.get('Name', ''),
                description=catalog.get('Description', ''),
                parameters=catalog.get('Parameters', {}),
                create_time=create_time_str,
                update_time=update_time_str,
                operation='get-catalog',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to get catalog {catalog_id}: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def import_catalog_to_glue(
        self,
        ctx: Context,
        catalog_id: str,
    ) -> CallToolResult:
        """Import metadata from an external source into the AWS Glue Data Catalog.

        Imports metadata from external sources such as Hive metastores, Apache Spark,
        or other compatible metadata repositories into the AWS Glue Data Catalog.
        This operation can be used to migrate metadata from on-premises systems to AWS.

        Args:
            ctx: MCP context containing request information
            catalog_id: ID of the catalog to import into

        Returns:
            ImportCatalogResponse with the result of the operation
        """
        try:
            # Prepare import parameters
            import_params = {
                'CatalogId': catalog_id,
            }

            # Start the import process
            self.glue_client.import_catalog_to_glue(**import_params)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully initiated catalog import Athena Data Catalog {catalog_id} to Glue',
            )

            success_msg = f'Successfully initiated catalog import from Athena Data Catalog {catalog_id} to Glue'
            data = ImportCatalogData(
                catalog_id=catalog_id,
                operation='import-catalog-to-glue',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f'Failed to import Athena data catalog {catalog_id} to Glue: {error_code} - {e.response["Error"]["Message"]}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )

    async def list_catalogs(
        self,
        ctx: Context,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
        parent_catalog_id: Optional[str] = None,
    ) -> CallToolResult:
        """List all catalogs in AWS Glue.

        Retrieves a list of all catalogs with their basic properties. Supports
        pagination through the next_token parameter.

        Args:
            ctx: MCP context containing request information
            max_results: Optional maximum number of results to return
            next_token: Optional pagination token for retrieving the next set of results
            parent_catalog_id: Optional parent catalog which the catalog resides

        Returns:
            ListCatalogsResponse with the list of catalogs
        """
        try:
            kwargs: Dict[str, Any] = {}
            if max_results:
                kwargs['MaxResults'] = max_results
            if next_token:
                kwargs['NextToken'] = next_token
            if parent_catalog_id:
                kwargs['ParentCatalogId'] = parent_catalog_id

            response = self.glue_client.get_catalogs(**kwargs)
            catalogs = response.get('CatalogList', [])
            next_token_response = response.get('NextToken', None)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully listed {len(catalogs)} catalogs',
            )

            success_msg = f'Successfully listed {len(catalogs)} catalogs'
            data = ListCatalogsData(
                catalogs=[
                    {
                        'catalog_id': catalog.get('CatalogId', ''),
                        'name': catalog.get('Name', ''),
                        'description': catalog.get('Description', ''),
                        'parameters': catalog.get('Parameters', {}),
                        'create_time': (
                            catalog.get('CreateTime', '').isoformat()
                            if catalog.get('CreateTime')
                            else ''
                        ),
                        'update_time': (
                            catalog.get('UpdateTime', '').isoformat()
                            if catalog.get('UpdateTime')
                            else ''
                        ),
                    }
                    for catalog in catalogs
                ],
                count=len(catalogs),
                next_token=next_token_response,
                operation='list-catalogs',
            )

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(type='text', text=success_msg),
                    TextContent(type='text', text=json.dumps(data.model_dump())),
                ],
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = (
                f'Failed to list catalogs: {error_code} - {e.response["Error"]["Message"]}'
            )
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CallToolResult(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
            )
