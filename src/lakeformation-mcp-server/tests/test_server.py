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

"""Tests for the Lake Formation MCP Server tools."""

import json
import pytest
from awslabs.lakeformation_mcp_server.server import (
    build_principal,
    build_resource,
    manage_aws_lakeformation_datalakesettings,
    manage_aws_lakeformation_effective_permissions,
    manage_aws_lakeformation_permissions,
    manage_aws_lakeformation_resources,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_ctx():
    """Create a mock MCP context."""
    ctx = MagicMock()
    ctx.error = AsyncMock()
    return ctx


@pytest.fixture
def mock_lf_client():
    """Create a mock Lake Formation client."""
    return MagicMock()


class TestBuildResource:
    """Tests for the build_resource helper function."""

    def test_catalog_only(self):
        """Test building a catalog-only resource."""
        assert build_resource(catalog_id='123456789012') == {
            'Catalog': {'CatalogId': '123456789012'}
        }

    def test_empty_catalog(self):
        """Test building a resource with no parameters."""
        assert build_resource() == {'Catalog': {}}

    def test_database_only(self):
        """Test building a database resource."""
        assert build_resource(database_name='mydb') == {'Database': {'Name': 'mydb'}}

    def test_database_with_catalog(self):
        """Test building a database resource with catalog ID."""
        assert build_resource(catalog_id='123', database_name='mydb') == {
            'Database': {'Name': 'mydb', 'CatalogId': '123'}
        }

    def test_table(self):
        """Test building a table resource."""
        assert build_resource(database_name='mydb', table_name='t1') == {
            'Table': {'DatabaseName': 'mydb', 'Name': 't1'}
        }

    def test_table_with_catalog(self):
        """Test building a table resource with catalog ID."""
        assert build_resource(catalog_id='123', database_name='mydb', table_name='t1') == {
            'Table': {'DatabaseName': 'mydb', 'Name': 't1', 'CatalogId': '123'}
        }

    def test_table_with_columns(self):
        """Test building a table-with-columns resource."""
        result = build_resource(database_name='mydb', table_name='t1', column_names=['c1', 'c2'])
        assert result == {
            'TableWithColumns': {'DatabaseName': 'mydb', 'Name': 't1', 'ColumnNames': ['c1', 'c2']}
        }


class TestBuildPrincipal:
    """Tests for the build_principal helper function."""

    def test_build_principal(self):
        """Test building a principal dict."""
        arn = 'arn:aws:iam::123456789012:user/testuser'
        assert build_principal(arn) == {'DataLakePrincipal': {'DataLakePrincipalIdentifier': arn}}


class TestPermissionsTool:
    """Tests for the manage_aws_lakeformation_permissions tool."""

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_list_permissions_no_filters(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test listing permissions with no filters."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.list_permissions.return_value = {
            'PrincipalResourcePermissions': [
                {
                    'Principal': {'DataLakePrincipalIdentifier': 'arn:aws:iam::123:user/admin'},
                    'Resource': {'Database': {'Name': 'mydb'}},
                    'Permissions': ['ALL'],
                    'PermissionsWithGrantOption': [],
                }
            ]
        }
        result = await manage_aws_lakeformation_permissions(
            mock_ctx, operation='list-permissions', max_results=100
        )
        data = json.loads(result)
        assert data['operation'] == 'list-permissions'
        assert len(data['permissions']) == 1
        assert data['permissions'][0]['principal'] == 'arn:aws:iam::123:user/admin'

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_list_permissions_with_principal(
        self, mock_get_client, mock_ctx, mock_lf_client
    ):
        """Test listing permissions filtered by principal."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.list_permissions.return_value = {
            'PrincipalResourcePermissions': [
                {
                    'Principal': {'DataLakePrincipalIdentifier': 'arn:aws:iam::123:user/test'},
                    'Resource': {'Table': {'DatabaseName': 'db1', 'Name': 't1'}},
                    'Permissions': ['SELECT'],
                    'PermissionsWithGrantOption': ['SELECT'],
                }
            ]
        }
        result = await manage_aws_lakeformation_permissions(
            mock_ctx,
            operation='list-permissions',
            principal='arn:aws:iam::123:user/test',
            max_results=100,
        )
        data = json.loads(result)
        assert data['permissions'][0]['permissions'] == ['SELECT']
        call_kwargs = mock_lf_client.list_permissions.call_args[1]
        assert 'Principal' in call_kwargs

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_list_permissions_with_db_and_table(
        self, mock_get_client, mock_ctx, mock_lf_client
    ):
        """Test listing permissions filtered by database and table."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.list_permissions.return_value = {'PrincipalResourcePermissions': []}
        result = await manage_aws_lakeformation_permissions(
            mock_ctx,
            operation='list-permissions',
            database_name='mydb',
            table_name='mytable',
            max_results=100,
        )
        data = json.loads(result)
        assert data['permissions'] == []
        assert 'Resource' in mock_lf_client.list_permissions.call_args[1]

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_list_permissions_with_resource_type(
        self, mock_get_client, mock_ctx, mock_lf_client
    ):
        """Test listing permissions filtered by resource type."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.list_permissions.return_value = {'PrincipalResourcePermissions': []}
        await manage_aws_lakeformation_permissions(
            mock_ctx,
            operation='list-permissions',
            resource_type='DATABASE',
            max_results=100,
        )
        assert mock_lf_client.list_permissions.call_args[1]['ResourceType'] == 'DATABASE'

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_list_permissions_pagination(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test listing permissions with pagination."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.list_permissions.side_effect = [
            {
                'PrincipalResourcePermissions': [
                    {
                        'Principal': {'DataLakePrincipalIdentifier': 'u1'},
                        'Resource': {'Database': {'Name': 'db1'}},
                        'Permissions': ['ALL'],
                    }
                ],
                'NextToken': 'token1',
            },
            {
                'PrincipalResourcePermissions': [
                    {
                        'Principal': {'DataLakePrincipalIdentifier': 'u2'},
                        'Resource': {'Database': {'Name': 'db2'}},
                        'Permissions': ['SELECT'],
                    }
                ],
            },
        ]
        result = await manage_aws_lakeformation_permissions(
            mock_ctx, operation='list-permissions', max_results=100
        )
        assert len(json.loads(result)['permissions']) == 2
        assert mock_lf_client.list_permissions.call_count == 2

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_list_permissions_error(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test error handling for permissions tool."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.list_permissions.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'}},
            'ListPermissions',
        )
        with pytest.raises(ValueError, match='Failed to manage permissions'):
            await manage_aws_lakeformation_permissions(
                mock_ctx, operation='list-permissions', max_results=100
            )


class TestSettingsTool:
    """Tests for the manage_aws_lakeformation_datalakesettings tool."""

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_get_settings_default(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test getting data lake settings with default parameters."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.get_data_lake_settings.return_value = {
            'DataLakeSettings': {
                'DataLakeAdmins': [{'DataLakePrincipalIdentifier': 'arn:aws:iam::123:role/Admin'}],
                'CreateDatabaseDefaultPermissions': [],
                'CreateTableDefaultPermissions': [],
                'AllowExternalDataFiltering': False,
            }
        }
        result = await manage_aws_lakeformation_datalakesettings(
            mock_ctx, operation='get-data-lake-settings'
        )
        data = json.loads(result)
        assert data['operation'] == 'get-data-lake-settings'
        assert data['settings']['data_lake_admins'] == ['arn:aws:iam::123:role/Admin']

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_get_settings_with_catalog_id(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test getting data lake settings with catalog_id."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.get_data_lake_settings.return_value = {
            'DataLakeSettings': {'DataLakeAdmins': [], 'AllowExternalDataFiltering': True}
        }
        result = await manage_aws_lakeformation_datalakesettings(
            mock_ctx, operation='get-data-lake-settings', catalog_id='123'
        )
        assert mock_lf_client.get_data_lake_settings.call_args[1]['CatalogId'] == '123'
        assert json.loads(result)['settings']['allow_external_data_filtering'] is True

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_get_settings_error(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test error handling for settings tool."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.get_data_lake_settings.side_effect = ClientError(
            {'Error': {'Code': 'InternalServiceException', 'Message': 'err'}},
            'GetDataLakeSettings',
        )
        with pytest.raises(ValueError, match='Failed to manage data lake settings'):
            await manage_aws_lakeformation_datalakesettings(
                mock_ctx, operation='get-data-lake-settings'
            )


class TestResourcesTool:
    """Tests for the manage_aws_lakeformation_resources tool."""

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_list_resources(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test listing resources."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.list_resources.return_value = {
            'ResourceInfoList': [
                {
                    'ResourceArn': 'arn:aws:s3:::bucket',
                    'RoleArn': 'arn:aws:iam::123:role/R',
                    'UseServiceLinkedRole': False,
                    'WithFederation': False,
                    'LastModified': '2024-01-01T00:00:00Z',
                }
            ]
        }
        result = await manage_aws_lakeformation_resources(
            mock_ctx, operation='list-resources', max_results=100
        )
        data = json.loads(result)
        assert data['operation'] == 'list-resources'
        assert data['resources'][0]['resource_arn'] == 'arn:aws:s3:::bucket'

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_list_resources_pagination(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test listing resources with pagination."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.list_resources.side_effect = [
            {
                'ResourceInfoList': [
                    {'ResourceArn': 'arn:aws:s3:::b1', 'UseServiceLinkedRole': True}
                ],
                'NextToken': 'tok',
            },
            {
                'ResourceInfoList': [
                    {'ResourceArn': 'arn:aws:s3:::b2', 'UseServiceLinkedRole': True}
                ]
            },
        ]
        result = await manage_aws_lakeformation_resources(
            mock_ctx, operation='list-resources', max_results=100
        )
        assert len(json.loads(result)['resources']) == 2

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_describe_resource(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test describing a resource."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.describe_resource.return_value = {
            'ResourceInfo': {'ResourceArn': 'arn:aws:s3:::bucket', 'WithFederation': True}
        }
        result = await manage_aws_lakeformation_resources(
            mock_ctx,
            operation='describe-resource',
            resource_arn='arn:aws:s3:::bucket',
            max_results=100,
        )
        data = json.loads(result)
        assert data['operation'] == 'describe-resource'
        assert data['resource']['with_federation'] is True

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_describe_resource_missing_arn(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test describe-resource without resource_arn returns error."""
        mock_get_client.return_value = mock_lf_client
        result = await manage_aws_lakeformation_resources(
            mock_ctx, operation='describe-resource', resource_arn=None, max_results=100
        )
        assert 'error' in json.loads(result)

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_list_resources_error(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test error handling for resources tool."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.list_resources.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'}},
            'ListResources',
        )
        with pytest.raises(ValueError, match='Failed to manage resources'):
            await manage_aws_lakeformation_resources(
                mock_ctx, operation='list-resources', max_results=100
            )


class TestEffectivePermissionsTool:
    """Tests for the manage_aws_lakeformation_effective_permissions tool."""

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_get_effective_permissions(self, mock_get_client, mock_ctx, mock_lf_client):
        """Test getting effective permissions for a path."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.get_effective_permissions_for_path.return_value = {
            'Permissions': [
                {
                    'Principal': {'DataLakePrincipalIdentifier': 'arn:aws:iam::123:user/admin'},
                    'Resource': {'DataLocation': {'ResourceArn': 'arn:aws:s3:::bucket/data/'}},
                    'Permissions': ['DATA_LOCATION_ACCESS'],
                    'PermissionsWithGrantOption': [],
                }
            ]
        }
        result = await manage_aws_lakeformation_effective_permissions(
            mock_ctx, resource_arn='arn:aws:s3:::bucket/data/'
        )
        data = json.loads(result)
        assert data['operation'] == 'batch-get-effective-permissions-for-path'
        assert len(data['effective_permissions']) == 1
        assert data['effective_permissions'][0]['permissions'] == ['DATA_LOCATION_ACCESS']

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_get_effective_permissions_with_catalog(
        self, mock_get_client, mock_ctx, mock_lf_client
    ):
        """Test getting effective permissions with catalog_id."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.get_effective_permissions_for_path.return_value = {'Permissions': []}
        result = await manage_aws_lakeformation_effective_permissions(
            mock_ctx, resource_arn='arn:aws:s3:::bucket/data/', catalog_id='123'
        )
        call_kwargs = mock_lf_client.get_effective_permissions_for_path.call_args[1]
        assert call_kwargs['CatalogId'] == '123'
        assert json.loads(result)['effective_permissions'] == []

    @pytest.mark.asyncio
    async def test_get_effective_permissions_missing_arn(self, mock_ctx):
        """Test missing resource_arn returns error."""
        result = await manage_aws_lakeformation_effective_permissions(mock_ctx, resource_arn=None)
        assert 'error' in json.loads(result)

    @pytest.mark.asyncio
    @patch('awslabs.lakeformation_mcp_server.server.get_lakeformation_client')
    async def test_get_effective_permissions_error(
        self, mock_get_client, mock_ctx, mock_lf_client
    ):
        """Test error handling for effective permissions tool."""
        mock_get_client.return_value = mock_lf_client
        mock_lf_client.get_effective_permissions_for_path.side_effect = ClientError(
            {'Error': {'Code': 'InvalidInputException', 'Message': 'bad'}},
            'GetEffectivePermissionsForPath',
        )
        with pytest.raises(ValueError, match='Failed to get effective permissions'):
            await manage_aws_lakeformation_effective_permissions(
                mock_ctx, resource_arn='arn:aws:s3:::bucket/data/'
            )
