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

"""awslabs Lake Formation MCP Server implementation.

Environment Variables:
    AWS_REGION: AWS region to use for AWS API calls
    AWS_PROFILE: AWS profile to use for credentials
    FASTMCP_LOG_LEVEL: Log level (default: WARNING)
"""

import argparse
import boto3
import json
import os
import sys
from awslabs.lakeformation_mcp_server.models import (
    DataLakeSettingsSummary,
    DescribeResourceData,
    EffectivePermissionSummary,
    GetDataLakeSettingsData,
    GetEffectivePermissionsData,
    ListPermissionsData,
    ListResourcesData,
    PermissionSummary,
    ResourceSummary,
)
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, List, Literal, Optional


SERVER_INSTRUCTIONS = """
# AWS Lake Formation MCP Server

This MCP server provides read-only tools for querying AWS Lake Formation permissions,
data lake settings, and registered resources.

## Known Limitations

- When using `manage_aws_lakeformation_permissions` with only a `principal` filter and no
  resource filter, the Lake Formation API may return incomplete or unexpected results.
  Always combine a `principal` filter with a resource filter (e.g., `database_name`,
  `table_name`, or `resource_type`) for reliable output.

## Common Workflows

### Managing Permissions
1. List permissions: `manage_aws_lakeformation_permissions(operation='list-permissions')`
2. Filter by principal: `manage_aws_lakeformation_permissions(operation='list-permissions', principal='arn:aws:iam::123456789012:user/testuser')`

### Managing Data Lake Settings
1. Get settings: `manage_aws_lakeformation_datalakesettings(operation='get-data-lake-settings')`

### Managing Resources
1. List resources: `manage_aws_lakeformation_resources(operation='list-resources')`
2. Describe resource: `manage_aws_lakeformation_resources(operation='describe-resource', resource_arn='arn:aws:s3:::my-bucket')`

### Checking Effective Permissions
1. Get effective permissions: `manage_aws_lakeformation_effective_permissions(resource_arn='arn:aws:s3:::my-bucket/data/')`
"""

DEPENDENCIES = [
    'boto3>=1.34.0',
    'loguru>=0.7.0',
    'mcp>=1.0.0',
    'pydantic>=2.0.0',
]


def get_aws_session() -> boto3.Session:
    """Get AWS session with proper configuration."""
    aws_profile = os.environ.get('AWS_PROFILE')
    aws_region = os.environ.get('AWS_REGION', 'us-east-1')

    kwargs: Dict[str, str] = {'region_name': aws_region}
    if aws_profile:
        kwargs['profile_name'] = aws_profile

    return boto3.Session(**kwargs)


def get_lakeformation_client():
    """Get Lake Formation client."""
    return get_aws_session().client('lakeformation')


def build_resource(
    catalog_id: Optional[str] = None,
    database_name: Optional[str] = None,
    table_name: Optional[str] = None,
    column_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a Lake Formation Resource dict."""
    if table_name and database_name:
        table_resource: Dict[str, Any] = {'DatabaseName': database_name, 'Name': table_name}
        if catalog_id:
            table_resource['CatalogId'] = catalog_id
        if column_names:
            return {'TableWithColumns': {**table_resource, 'ColumnNames': column_names}}
        return {'Table': table_resource}

    if database_name:
        db_resource: Dict[str, Any] = {'Name': database_name}
        if catalog_id:
            db_resource['CatalogId'] = catalog_id
        return {'Database': db_resource}

    if catalog_id:
        return {'Catalog': {'CatalogId': catalog_id}}

    return {'Catalog': {}}


def build_principal(principal_arn: str) -> Dict[str, Any]:
    """Build a DataLakePrincipal dict."""
    return {'DataLakePrincipal': {'DataLakePrincipalIdentifier': principal_arn}}


# Initialize FastMCP server
mcp = FastMCP(
    'awslabs.lakeformation-mcp-server',
    instructions=SERVER_INSTRUCTIONS,
    dependencies=DEPENDENCIES,
)


@mcp.tool(name='manage_aws_lakeformation_permissions')
async def manage_aws_lakeformation_permissions(
    ctx: Context,
    operation: Literal['list-permissions'] = Field(
        default='list-permissions', description='Operation to perform'
    ),
    principal: Optional[str] = Field(default=None, description='Principal ARN to filter by'),
    database_name: Optional[str] = Field(default=None, description='Database name to filter by'),
    table_name: Optional[str] = Field(default=None, description='Table name to filter by'),
    catalog_id: Optional[str] = Field(
        default=None, description='AWS account ID of the Data Catalog'
    ),
    resource_type: Optional[Literal['CATALOG', 'DATABASE', 'TABLE', 'DATA_LOCATION']] = Field(
        default=None, description='Resource type filter'
    ),
    max_results: int = Field(default=100, ge=1, le=1000, description='Maximum results'),
) -> str:
    """Manage AWS Lake Formation permissions."""
    try:
        client = get_lakeformation_client()

        if operation == 'list-permissions':
            kwargs: Dict[str, Any] = {'MaxResults': max_results}

            if catalog_id:
                kwargs['CatalogId'] = catalog_id
            if principal:
                kwargs['Principal'] = build_principal(principal)
            if resource_type:
                kwargs['ResourceType'] = resource_type
            if database_name or table_name:
                kwargs['Resource'] = build_resource(
                    catalog_id=catalog_id,
                    database_name=database_name,
                    table_name=table_name,
                )

            all_entries: List[Dict[str, Any]] = []
            while True:
                response = client.list_permissions(**kwargs)
                all_entries.extend(response.get('PrincipalResourcePermissions', []))
                next_token = response.get('NextToken')
                if not next_token or len(all_entries) >= max_results:
                    break
                kwargs['NextToken'] = next_token

            permissions = []
            for entry in all_entries[:max_results]:
                permissions.append(
                    PermissionSummary(
                        principal=entry['Principal']['DataLakePrincipalIdentifier'],
                        resource=entry['Resource'],
                        permissions=entry['Permissions'],
                        permissions_with_grant_option=entry.get('PermissionsWithGrantOption', []),
                    )
                )

            result = ListPermissionsData(permissions=permissions)
            return json.dumps(result.model_dump(), indent=2)

        else:
            return json.dumps({'error': f'Unsupported operation: {operation}'}, indent=2)

    except (BotoCoreError, ClientError) as e:
        logger.error(f'manage_aws_lakeformation_permissions failed: {e}')
        await ctx.error(f'Failed to manage permissions: {e}')
        raise ValueError(f'Failed to manage permissions: {e}')


@mcp.tool(name='manage_aws_lakeformation_datalakesettings')
async def manage_aws_lakeformation_datalakesettings(
    ctx: Context,
    operation: Literal['get-data-lake-settings'] = Field(
        default='get-data-lake-settings', description='Operation to perform'
    ),
    catalog_id: Optional[str] = Field(default=None, description='AWS account ID'),
) -> str:
    """Manage AWS Lake Formation data lake settings."""
    try:
        client = get_lakeformation_client()

        if operation == 'get-data-lake-settings':
            kwargs: Dict[str, str] = {}
            if catalog_id:
                kwargs['CatalogId'] = catalog_id

            response = client.get_data_lake_settings(**kwargs)
            settings_data = response.get('DataLakeSettings', {})

            admins = [
                admin['DataLakePrincipalIdentifier']
                for admin in settings_data.get('DataLakeAdmins', [])
            ]

            settings = DataLakeSettingsSummary(
                data_lake_admins=admins,
                create_database_default_permissions=settings_data.get(
                    'CreateDatabaseDefaultPermissions'
                ),
                create_table_default_permissions=settings_data.get(
                    'CreateTableDefaultPermissions'
                ),
                allow_external_data_filtering=settings_data.get(
                    'AllowExternalDataFiltering', False
                ),
            )

            result = GetDataLakeSettingsData(settings=settings)
            return json.dumps(result.model_dump(), indent=2)

        else:
            return json.dumps({'error': f'Unsupported operation: {operation}'}, indent=2)

    except (BotoCoreError, ClientError) as e:
        logger.error(f'manage_aws_lakeformation_datalakesettings failed: {e}')
        await ctx.error(f'Failed to manage data lake settings: {e}')
        raise ValueError(f'Failed to manage data lake settings: {e}')


@mcp.tool(name='manage_aws_lakeformation_resources')
async def manage_aws_lakeformation_resources(
    ctx: Context,
    operation: Literal['list-resources', 'describe-resource'] = Field(
        ..., description='Operation to perform'
    ),
    resource_arn: Optional[str] = Field(
        default=None, description='S3 resource ARN for describe-resource operation'
    ),
    max_results: int = Field(
        default=100, ge=1, le=1000, description='Maximum results for list operations'
    ),
) -> str:
    """Manage AWS Lake Formation resources."""
    try:
        client = get_lakeformation_client()

        if operation == 'list-resources':
            kwargs: Dict[str, Any] = {'MaxResults': max_results}

            all_resources: List[Dict[str, Any]] = []
            while True:
                response = client.list_resources(**kwargs)
                all_resources.extend(response.get('ResourceInfoList', []))
                next_token = response.get('NextToken')
                if not next_token or len(all_resources) >= max_results:
                    break
                kwargs['NextToken'] = next_token

            resources = []
            for resource_info in all_resources[:max_results]:
                resources.append(
                    ResourceSummary(
                        resource_arn=resource_info['ResourceArn'],
                        role_arn=resource_info.get('RoleArn'),
                        use_service_linked_role=resource_info.get('UseServiceLinkedRole', True),
                        with_federation=resource_info.get('WithFederation', False),
                        last_modified=str(resource_info['LastModified'])
                        if resource_info.get('LastModified')
                        else None,
                    )
                )

            result = ListResourcesData(resources=resources)
            return json.dumps(result.model_dump(), indent=2, default=str)

        elif operation == 'describe-resource':
            if not resource_arn:
                return json.dumps(
                    {'error': 'resource_arn is required for describe-resource operation'},
                    indent=2,
                )

            response = client.describe_resource(ResourceArn=resource_arn)
            resource_info = response.get('ResourceInfo', {})

            resource = ResourceSummary(
                resource_arn=resource_info['ResourceArn'],
                role_arn=resource_info.get('RoleArn'),
                use_service_linked_role=resource_info.get('UseServiceLinkedRole', True),
                with_federation=resource_info.get('WithFederation', False),
                last_modified=str(resource_info['LastModified'])
                if resource_info.get('LastModified')
                else None,
            )

            result_desc = DescribeResourceData(resource=resource)
            return json.dumps(result_desc.model_dump(), indent=2, default=str)

        else:
            return json.dumps({'error': f'Unsupported operation: {operation}'}, indent=2)

    except (BotoCoreError, ClientError) as e:
        logger.error(f'manage_aws_lakeformation_resources failed: {e}')
        await ctx.error(f'Failed to manage resources: {e}')
        raise ValueError(f'Failed to manage resources: {e}')


@mcp.tool(name='manage_aws_lakeformation_effective_permissions')
async def manage_aws_lakeformation_effective_permissions(
    ctx: Context,
    resource_arn: Optional[str] = Field(
        default=None, description='S3 path ARN to get effective permissions for'
    ),
    catalog_id: Optional[str] = Field(
        default=None, description='AWS account ID of the Data Catalog'
    ),
) -> str:
    """Get effective permissions for a given S3 resource path in AWS Lake Formation."""
    try:
        if not resource_arn:
            return json.dumps(
                {'error': 'resource_arn is required for batch-get-effective-permissions-for-path'},
                indent=2,
            )

        client = get_lakeformation_client()

        kwargs: Dict[str, str] = {'ResourceArn': resource_arn}
        if catalog_id:
            kwargs['CatalogId'] = catalog_id

        all_entries: List[Dict[str, Any]] = []
        while True:
            response = client.get_effective_permissions_for_path(**kwargs)
            all_entries.extend(response.get('Permissions', []))
            next_token = response.get('NextToken')
            if not next_token:
                break
            kwargs['NextToken'] = next_token

        effective_permissions = []
        for entry in all_entries:
            principal_info = entry.get('Principal', {})
            effective_permissions.append(
                EffectivePermissionSummary(
                    principal=principal_info.get('DataLakePrincipalIdentifier', ''),
                    resource=entry.get('Resource', {}),
                    permissions=entry.get('Permissions', []),
                    permissions_with_grant_option=entry.get('PermissionsWithGrantOption', []),
                )
            )

        result = GetEffectivePermissionsData(effective_permissions=effective_permissions)
        return json.dumps(result.model_dump(), indent=2)

    except (BotoCoreError, ClientError) as e:
        logger.error(f'manage_aws_lakeformation_effective_permissions failed: {e}')
        await ctx.error(f'Failed to get effective permissions: {e}')
        raise ValueError(f'Failed to get effective permissions: {e}')


def main():
    """Main entry point for the MCP server."""
    parser = argparse.ArgumentParser(description='Lake Formation MCP Server')
    parser.add_argument('--allow-write', action='store_true', help='Allow write operations')
    parser.add_argument(
        '--allow-sensitive-data-access',
        action='store_true',
        help='Allow access to sensitive data',
    )
    parser.parse_args()

    # Configure logging
    log_level = os.environ.get('FASTMCP_LOG_LEVEL', 'WARNING')
    logger.remove()
    logger.add(sys.stderr, level=log_level)

    logger.info('Starting Lake Formation MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()
