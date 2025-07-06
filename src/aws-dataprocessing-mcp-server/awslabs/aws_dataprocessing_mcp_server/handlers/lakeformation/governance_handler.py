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

"""GovernanceHandler for Data Processing MCP Server."""

from awslabs.aws_dataprocessing_mcp_server.core.lakeformation.governance_manager import (
    GovernanceManager,
)
from awslabs.aws_dataprocessing_mcp_server.models.governance_models import (
    ListPermissionsResponse,
    GetDataLakeSettingsResponse,
    ListResourcesResponse,
    DescribeResourceResponse,
    BatchGetEffectivePermissionsForPathResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict, List, Optional, Union


class GovernanceHandler:
    """Handler for AWS Lake Formation governance operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Lake Formation Governance handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.governance_manager = GovernanceManager(
            self.allow_write, self.allow_sensitive_data_access
        )

        # Register tools
        self.mcp.tool(name='manage_aws_lakeformation_permissions') (
            self.manage_aws_lakeformation_permissions
        )
        self.mcp.tool(name='manage_aws_lakeformation_datalakesettings')(
            self.manage_aws_lakeformation_datalakesettings
        )
        self.mcp.tool(name='manage_aws_lakeformation_resources')(
            self.manage_aws_lakeformation_resources
        )

    async def manage_aws_lakeformation_permissions(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: list-permissions, batch-get-effective-permissions-for-path.',
        ),
        principal: Optional[str] = Field(
            None,
            description='The principal to be granted a permission.',
        ),
        resource_type: Optional[str] = Field(
            None,
            description='The type of the resource.',
        ),
        resource_path: Optional[str] = Field(
            None,
            description='The path to the resource.',
        ),
        catalog_id: Optional[str] = Field(
            None,
            description='ID of the catalog (optional, defaults to account ID).',
        ),
    ) -> Union[
        ListPermissionsResponse,
        BatchGetEffectivePermissionsForPathResponse,
    ]:
        """Manage AWS Lake Formation permissions.

        This tool provides operations for managing AWS Lake Formation permissions, including listing permissions
        and getting effective permissions for a path.

        Args:
            ctx: MCP context
            operation: Operation to perform (list-permissions, batch-get-effective-permissions-for-path)
            principal: The principal for which to list permissions.
            resource_type: The type of resource for which to list permissions.
            resource_path: The path to the resource for which to get effective permissions.
            catalog_id: ID of the catalog (optional, defaults to account ID)

        Returns:
            Union of response types specific to the operation performed
        """
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Received request to manage AWS Lake Formation permissions with operation: {operation}',
        )
        try:
            if operation == 'list-permissions':
                return await self.governance_manager.list_permissions(
                    ctx=ctx,
                    principal=principal,
                    resource_type=resource_type,
                    catalog_id=catalog_id,
                )
            elif operation == 'batch-get-effective-permissions-for-path':
                if resource_path is None:
                    raise ValueError('resource_path is required for batch-get-effective-permissions-for-path operation')
                return await self.governance_manager.batch_get_effective_permissions_for_path(
                    ctx=ctx,
                    resource_path=resource_path,
                    catalog_id=catalog_id,
                )
            else:
                error_message = f'Invalid operation: {operation}. Must be one of: list-permissions, batch-get-effective-permissions-for-path'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return ListPermissionsResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    permissions=[],
                    operation='list-permissions',
                )
        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_lakeformation_permissions: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return ListPermissionsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                permissions=[],
                operation='list-permissions',
            )

    async def manage_aws_lakeformation_datalakesettings(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: get-data-lake-settings.',
        ),
        catalog_id: Optional[str] = Field(
            None,
            description='ID of the catalog (optional, defaults to account ID).',
        ),
    ) -> GetDataLakeSettingsResponse:
        """Manage AWS Lake Formation data lake settings.

        This tool provides operations for managing AWS Lake Formation data lake settings, including getting the settings.

        Args:
            ctx: MCP context
            operation: Operation to perform (get-data-lake-settings)
            catalog_id: ID of the catalog (optional, defaults to account ID)

        Returns:
            The response for the get-data-lake-settings operation
        """
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Received request to manage AWS Lake Formation data lake settings with operation: {operation}',
        )
        try:
            if operation == 'get-data-lake-settings':
                return await self.governance_manager.get_data_lake_settings(
                    ctx=ctx,
                    catalog_id=catalog_id,
                )
            else:
                error_message = f'Invalid operation: {operation}. Must be one of: get-data-lake-settings'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetDataLakeSettingsResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    data_lake_settings={},
                    operation='get-data-lake-settings',
                )
        except Exception as e:
            error_message = f'Error in manage_aws_lakeformation_datalakesettings: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetDataLakeSettingsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                data_lake_settings={},
                operation='get-data-lake-settings',
            )

    async def manage_aws_lakeformation_resources(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: list-resources, describe-resource.',
        ),
        resource_arn: Optional[str] = Field(
            None,
            description='The ARN of the resource to describe.',
        ),
    ) -> Union[
        ListResourcesResponse,
        DescribeResourceResponse,
    ]:
        """Manage AWS Lake Formation resources.

        This tool provides operations for managing AWS Lake Formation resources, including listing and describing resources.

        Args:
            ctx: MCP context
            operation: Operation to perform (list-resources, describe-resource)
            resource_arn: The ARN of the resource to describe.

        Returns:
            Union of response types specific to the operation performed
        """
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Received request to manage AWS Lake Formation resources with operation: {operation}',
        )
        try:
            if operation == 'list-resources':
                return await self.governance_manager.list_resources(
                    ctx=ctx,
                )
            elif operation == 'describe-resource':
                if resource_arn is None:
                    raise ValueError('resource_arn is required for describe-resource operation')
                return await self.governance_manager.describe_resource(
                    ctx=ctx,
                    resource_arn=resource_arn,
                )
            else:
                error_message = f'Invalid operation: {operation}. Must be one of: list-resources, describe-resource'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return ListResourcesResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    resources=[],
                    operation='list-resources',
                )
        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_lakeformation_resources: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return ListResourcesResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                resources=[],
                operation='list-resources',
            )
