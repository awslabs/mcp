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

"""GovernanceManager for Data Processing MCP Server."""

import boto3
from botocore.exceptions import ClientError
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
from typing import Optional


class GovernanceManager:
    """Manager for AWS Lake Formation governance operations."""

    def __init__(self, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Lake Formation Governance manager."""
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.lakeformation_client = boto3.client("lakeformation")

    async def list_permissions(
        self,
        ctx: Context,
        principal: Optional[str] = None,
        resource_type: Optional[str] = None,
        catalog_id: Optional[str] = None,
        next_token: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> ListPermissionsResponse:
        """List AWS Lake Formation permissions."""
        try:
            all_permissions = []
            current_next_token = next_token
            while True:
                params = {}
                if principal:
                    params["Principal"] = {"DataLakePrincipalIdentifier": principal}
                if resource_type:
                    params["ResourceType"] = resource_type
                if catalog_id:
                    params["CatalogId"] = catalog_id
                if max_results:
                    params["MaxResults"] = max_results
                if current_next_token:
                    params["NextToken"] = current_next_token

                response = self.lakeformation_client.list_permissions(**params)
                all_permissions.extend(response.get("PrincipalResourcePermissions", []))
                current_next_token = response.get("NextToken")
                if not current_next_token:
                    break

            return ListPermissionsResponse(
                isError=False,
                content=[],
                permissions=all_permissions,
                operation="list-permissions",
                next_token=current_next_token,
            )
        except ClientError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f"Error listing permissions: {e}")
            return ListPermissionsResponse(
                isError=True,
                content=[TextContent(type="text", text=str(e))],
                permissions=[],
                operation="list-permissions",
            )

    async def get_data_lake_settings(
        self, ctx: Context, catalog_id: Optional[str] = None
    ) -> GetDataLakeSettingsResponse:
        """Get AWS Lake Formation data lake settings."""
        try:
            params = {}
            if catalog_id:
                params["CatalogId"] = catalog_id

            response = self.lakeformation_client.get_data_lake_settings(**params)
            return GetDataLakeSettingsResponse(
                isError=False,
                content=[],
                data_lake_settings=response.get("DataLakeSettings", {}),
                operation="get-data-lake-settings",
            )
        except ClientError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f"Error getting data lake settings: {e}")
            return GetDataLakeSettingsResponse(
                isError=True,
                content=[TextContent(type="text", text=str(e))],
                data_lake_settings={},
                operation="get-data-lake-settings",
            )

    async def list_resources(
        self, ctx: Context, next_token: Optional[str] = None, max_results: Optional[int] = None
    ) -> ListResourcesResponse:
        """List AWS Lake Formation resources."""
        try:
            all_resources = []
            current_next_token = next_token
            while True:
                params = {}
                if max_results:
                    params["MaxResults"] = max_results
                if current_next_token:
                    params["NextToken"] = current_next_token

                response = self.lakeformation_client.list_resources(**params)
                all_resources.extend(response.get("ResourceInfoList", []))
                current_next_token = response.get("NextToken")
                if not current_next_token:
                    break

            return ListResourcesResponse(
                isError=False,
                content=[],
                resources=all_resources,
                operation="list-resources",
                next_token=current_next_token,
            )
        except ClientError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f"Error listing resources: {e}")
            return ListResourcesResponse(
                isError=True,
                content=[TextContent(type="text", text=str(e))],
                resources=[],
                operation="list-resources",
            )

    async def describe_resource(
        self, ctx: Context, resource_arn: str
    ) -> DescribeResourceResponse:
        """Describe an AWS Lake Formation resource."""
        try:
            response = self.lakeformation_client.describe_resource(ResourceArn=resource_arn)
            return DescribeResourceResponse(
                isError=False,
                content=[],
                resource_info=response.get("ResourceInfo", {}),
                operation="describe-resource",
            )
        except ClientError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f"Error describing resource: {e}")
            return DescribeResourceResponse(
                isError=True,
                content=[TextContent(type="text", text=str(e))],
                resource_info={},
                operation="describe-resource",
            )

    async def batch_get_effective_permissions_for_path(
        self, ctx: Context, resource_path: str, catalog_id: Optional[str] = None
    ) -> BatchGetEffectivePermissionsForPathResponse:
        """Get effective permissions for a path in AWS Lake Formation."""
        try:
            params = {"ResourcePath": resource_path}
            if catalog_id:
                params["CatalogId"] = catalog_id

            response = self.lakeformation_client.batch_get_effective_permissions_for_path(
                **params
            )
            return BatchGetEffectivePermissionsForPathResponse(
                isError=False,
                content=[],
                permissions=response.get("Permissions", []),
                operation="batch-get-effective-permissions-for-path",
            )
        except ClientError as e:
            log_with_request_id(
                ctx, LogLevel.ERROR, f"Error getting effective permissions for path: {e}"
            )
            return BatchGetEffectivePermissionsForPathResponse(
                isError=True,
                content=[TextContent(type="text", text=str(e))],
                permissions=[],
                operation="batch-get-effective-permissions-for-path",
            )
