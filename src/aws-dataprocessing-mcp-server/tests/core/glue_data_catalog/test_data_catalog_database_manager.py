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

"""Tests for the DataCatalogDatabaseManager class."""

import pytest
from awslabs.aws_dataprocessing_mcp_server.core.glue_data_catalog.data_catalog_database_manager import (
    DataCatalogDatabaseManager,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from botocore.exceptions import ClientError
from datetime import datetime
from mcp.types import CallToolResult
from unittest.mock import MagicMock, call, patch


class TestDataCatalogDatabaseManager:
    """Tests for the DataCatalogDatabaseManager class."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Context."""
        mock = MagicMock()
        mock.request_id = 'test-request-id'
        return mock

    @pytest.fixture
    def mock_glue_client(self):
        """Create a mock Glue client."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def manager(self, mock_glue_client):
        """Create a DataCatalogDatabaseManager instance with a mocked Glue client."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            manager = DataCatalogDatabaseManager(allow_write=True)
            return manager

    def test_uses_supplied_client_factory(self, mock_glue_client):
        """A supplied client factory creates the manager's Glue client."""
        client_factory = MagicMock(return_value=mock_glue_client)

        manager = DataCatalogDatabaseManager(client_factory=client_factory)

        assert manager.glue_client is mock_glue_client
        assert manager._provided_client_factory is client_factory
        client_factory.assert_called_once_with('glue')

    @pytest.mark.asyncio
    async def test_default_identity_lookup_uses_ambient_cache(
        self, mock_ctx, mock_glue_client, monkeypatch
    ):
        """Default manager identity lookups preserve ambient account and partition caches."""
        mock_glue_client.get_database.return_value = {
            'Database': {'Parameters': {'mcp:managed': 'true'}}
        }
        monkeypatch.setattr(AwsHelper, '_aws_account_id', '111111111111')
        monkeypatch.setattr(AwsHelper, '_aws_partition', 'aws-us-gov')

        with (
            patch.object(AwsHelper, 'create_boto3_client', return_value=mock_glue_client),
            patch.object(AwsHelper, 'get_or_default_aws_region', return_value='us-gov-west-1'),
            patch.object(AwsHelper, 'is_resource_mcp_managed', return_value=True) as is_managed,
            patch('boto3.client') as ambient_boto3_client,
        ):
            manager = DataCatalogDatabaseManager(allow_write=True)
            result = await manager.delete_database(mock_ctx, database_name='test-db')

        assert result.is_error is False
        assert manager._provided_client_factory is None
        ambient_boto3_client.assert_not_called()
        is_managed.assert_called_once_with(
            mock_glue_client,
            'arn:aws-us-gov:glue:us-gov-west-1:111111111111:database/test-db',
            {'mcp:managed': 'true'},
        )

    @pytest.mark.asyncio
    async def test_injected_identity_lookup_bypasses_ambient_cache(
        self, mock_ctx, mock_glue_client, monkeypatch
    ):
        """Injected manager identity lookups use factory STS without mutating ambient caches."""
        mock_glue_client.get_database.return_value = {
            'Database': {'Parameters': {'mcp:managed': 'true'}}
        }
        sts_client = MagicMock()
        sts_client.get_caller_identity.return_value = {
            'Account': '222222222222',
            'Arn': 'arn:aws-us-gov:sts::222222222222:assumed-role/test/session',
        }
        clients = {'glue': mock_glue_client, 'sts': sts_client}
        client_factory = MagicMock(side_effect=lambda service_name: clients[service_name])
        monkeypatch.setattr(AwsHelper, '_aws_account_id', '111111111111')
        monkeypatch.setattr(AwsHelper, '_aws_partition', 'aws')

        with (
            patch.object(AwsHelper, 'get_or_default_aws_region', return_value='us-gov-west-1'),
            patch.object(AwsHelper, 'is_resource_mcp_managed', return_value=True) as is_managed,
            patch('boto3.client') as ambient_boto3_client,
        ):
            manager = DataCatalogDatabaseManager(allow_write=True, client_factory=client_factory)
            result = await manager.delete_database(mock_ctx, database_name='test-db')

        assert result.is_error is False
        assert AwsHelper._aws_account_id == '111111111111'
        assert AwsHelper._aws_partition == 'aws'
        ambient_boto3_client.assert_not_called()
        assert client_factory.call_args_list == [call('glue'), call('sts'), call('sts')]
        is_managed.assert_called_once_with(
            mock_glue_client,
            'arn:aws-us-gov:glue:us-gov-west-1:222222222222:database/test-db',
            {'mcp:managed': 'true'},
        )

    @pytest.mark.asyncio
    async def test_create_database_success(self, manager, mock_ctx, mock_glue_client):
        """Test that create_database returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        description = 'Test database'
        location_uri = 's3://test-bucket/'
        parameters = {'key1': 'value1', 'key2': 'value2'}
        catalog_id = '123456789012'
        tags = {'tag1': 'value1', 'tag2': 'value2'}

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Call the method
            result = await manager.create_database(
                mock_ctx,
                database_name=database_name,
                description=description,
                location_uri=location_uri,
                parameters=parameters,
                catalog_id=catalog_id,
                tags=tags,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.create_database.assert_called_once()
            call_args = mock_glue_client.create_database.call_args[1]

            assert call_args['DatabaseInput']['Name'] == database_name
            assert call_args['DatabaseInput']['Description'] == description
            assert call_args['DatabaseInput']['LocationUri'] == location_uri
            assert call_args['CatalogId'] == catalog_id

            # Verify that the tags were merged correctly
            expected_tags = {'tag1': 'value1', 'tag2': 'value2', 'mcp:managed': 'true'}
            assert call_args['Tags'] == expected_tags

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) == 2
            assert hasattr(result.content[0], 'text')
            assert f'Successfully created database: {database_name}' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_database_error(self, manager, mock_ctx, mock_glue_client):
        """Test that create_database returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'AlreadyExistsException', 'Message': 'Database already exists'},
                'ResponseMetadata': {'HTTPStatusCode': 400, 'RequestId': 'glue-request-id'},
            }
            mock_glue_client.create_database.side_effect = ClientError(
                error_response, 'CreateDatabase'
            )

            # Call the method
            result = await manager.create_database(mock_ctx, database_name=database_name)

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.is_error is True
            assert len(result.content) == 1
            assert hasattr(result.content[0], 'text')
            assert 'Failed to create database' in result.content[0].text
            assert 'AlreadyExistsException' in result.content[0].text
            assert result.structured_content == {
                'error': {
                    'code': 'AlreadyExistsException',
                    'error_type': 'ClientError',
                    'message': 'Database already exists',
                    'http_status': 400,
                    'request_id': 'glue-request-id',
                }
            }

    @pytest.mark.asyncio
    async def test_delete_database_success(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_database returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        catalog_id = '123456789012'

        # Mock the get_database response to indicate the database is MCP managed
        mock_glue_client.get_database.return_value = {
            'Database': {'Name': database_name, 'Parameters': {'mcp:managed': 'true'}}
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_or_default_aws_region',
                return_value='us-east-1',
            ),
        ):
            # Call the method
            result = await manager.delete_database(
                mock_ctx, database_name=database_name, catalog_id=catalog_id
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.delete_database.assert_called_once_with(
                Name=database_name, CatalogId=catalog_id
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) == 2
            assert hasattr(result.content[0], 'text')
            assert f'Successfully deleted database: {database_name}' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_database_not_mcp_managed(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_database returns an error when the database is not MCP managed."""
        # Setup
        database_name = 'test-db'

        # Mock the get_database response to indicate the database is not MCP managed
        mock_glue_client.get_database.return_value = {
            'Database': {'Name': database_name, 'Parameters': {}}
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=False,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_or_default_aws_region',
                return_value='us-east-1',
            ),
        ):
            # Call the method
            result = await manager.delete_database(mock_ctx, database_name=database_name)

            # Verify that the Glue client was not called to delete the database
            mock_glue_client.delete_database.assert_not_called()

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.is_error is True
            assert len(result.content) == 1
            assert hasattr(result.content[0], 'text')
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_database_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_database returns an error when the database is not found."""
        # Setup
        database_name = 'test-db'

        # Mock the get_database to raise an EntityNotFoundException
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Database not found'}
        }
        mock_glue_client.get_database.side_effect = ClientError(error_response, 'GetDatabase')

        # Call the method
        result = await manager.delete_database(mock_ctx, database_name=database_name)

        # Verify that the Glue client was not called to delete the database
        mock_glue_client.delete_database.assert_not_called()

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.is_error is True
        assert len(result.content) == 1
        assert hasattr(result.content[0], 'text')
        assert 'Database test-db not found' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_database_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_database returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        catalog_id = '123456789012'
        description = 'Test database'
        location_uri = 's3://test-bucket/'
        parameters = {'key1': 'value1', 'key2': 'value2'}
        create_time = datetime(2023, 1, 1, 0, 0, 0)

        # Mock the get_database response
        mock_glue_client.get_database.return_value = {
            'Database': {
                'Name': database_name,
                'Description': description,
                'LocationUri': location_uri,
                'Parameters': parameters,
                'CreateTime': create_time,
                'CatalogId': catalog_id,
            }
        }

        # Call the method
        result = await manager.get_database(
            mock_ctx, database_name=database_name, catalog_id=catalog_id
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_database.assert_called_once_with(
            Name=database_name, CatalogId=catalog_id
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.is_error is False
        assert len(result.content) == 2
        assert hasattr(result.content[0], 'text')
        assert f'Successfully retrieved database: {database_name}' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_database_error(self, manager, mock_ctx, mock_glue_client):
        """Test that get_database returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'
        catalog_id = '123456789012'

        # Mock the get_database to raise an exception
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Database not found'}
        }
        mock_glue_client.get_database.side_effect = ClientError(error_response, 'GetDatabase')

        # Call the method
        result = await manager.get_database(
            mock_ctx, database_name=database_name, catalog_id=catalog_id
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.is_error is True
        assert len(result.content) == 1
        assert hasattr(result.content[0], 'text')
        assert 'Failed to get database' in result.content[0].text
        assert 'EntityNotFoundException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_databases_success(self, manager, mock_ctx, mock_glue_client):
        """Test that list_databases returns a successful response when the Glue API call succeeds."""
        # Setup
        catalog_id = '123456789012'
        next_token = 'next-token'
        max_results = 10
        resource_share_type = 'ALL'
        attributes_to_get = ['Name', 'Description']

        # Mock the get_databases response
        create_time = datetime(2023, 1, 1, 0, 0, 0)
        mock_glue_client.get_databases.return_value = {
            'DatabaseList': [
                {
                    'Name': 'db1',
                    'Description': 'Database 1',
                    'LocationUri': 's3://bucket1/',
                    'Parameters': {'key1': 'value1'},
                    'CreateTime': create_time,
                },
                {
                    'Name': 'db2',
                    'Description': 'Database 2',
                    'LocationUri': 's3://bucket2/',
                    'Parameters': {'key2': 'value2'},
                    'CreateTime': create_time,
                },
            ]
        }

        # Call the method
        result = await manager.list_databases(
            mock_ctx,
            catalog_id=catalog_id,
            next_token=next_token,
            max_results=max_results,
            resource_share_type=resource_share_type,
            attributes_to_get=attributes_to_get,
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_databases.assert_called_once_with(
            CatalogId=catalog_id,
            NextToken=next_token,
            MaxResults=max_results,
            ResourceShareType=resource_share_type,
            AttributesToGet=attributes_to_get,
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.is_error is False
        assert len(result.content) == 2
        assert hasattr(result.content[0], 'text')
        assert 'Successfully listed 2 databases' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_databases_error(self, manager, mock_ctx, mock_glue_client):
        """Test that list_databases returns an error response when the Glue API call fails."""
        # Setup
        catalog_id = '123456789012'

        # Mock the get_databases to raise an exception
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        mock_glue_client.get_databases.side_effect = ClientError(error_response, 'GetDatabases')

        # Call the method
        result = await manager.list_databases(mock_ctx, catalog_id=catalog_id)

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.is_error is True
        assert len(result.content) == 1
        assert hasattr(result.content[0], 'text')
        assert 'Failed to list databases' in result.content[0].text
        assert 'AccessDeniedException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_database_success(self, manager, mock_ctx, mock_glue_client):
        """Test that update_database returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        description = 'Updated description'
        location_uri = 's3://updated-bucket/'
        parameters = {'key1': 'updated-value1', 'key2': 'updated-value2'}
        catalog_id = '123456789012'

        # Mock the get_database response to indicate the database is MCP managed
        mock_glue_client.get_database.return_value = {
            'Database': {'Name': database_name, 'Parameters': {'mcp:managed': 'true'}}
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_or_default_aws_region',
                return_value='us-east-1',
            ),
        ):
            # Call the method
            result = await manager.update_database(
                mock_ctx,
                database_name=database_name,
                description=description,
                location_uri=location_uri,
                parameters=parameters,
                catalog_id=catalog_id,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.update_database.assert_called_once()
            call_args = mock_glue_client.update_database.call_args[1]

            assert call_args['Name'] == database_name
            assert call_args['DatabaseInput']['Name'] == database_name
            assert call_args['DatabaseInput']['Description'] == description
            assert call_args['DatabaseInput']['LocationUri'] == location_uri
            assert 'mcp:managed' in call_args['DatabaseInput']['Parameters']
            assert call_args['DatabaseInput']['Parameters']['key1'] == 'updated-value1'
            assert call_args['DatabaseInput']['Parameters']['key2'] == 'updated-value2'
            assert call_args['CatalogId'] == catalog_id

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) == 2
            assert hasattr(result.content[0], 'text')
            assert f'Successfully updated database: {database_name}' in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_database_not_mcp_managed(self, manager, mock_ctx, mock_glue_client):
        """Test that update_database returns an error when the database is not MCP managed."""
        # Setup
        database_name = 'test-db'

        # Mock the get_database response to indicate the database is not MCP managed
        mock_glue_client.get_database.return_value = {
            'Database': {'Name': database_name, 'Parameters': {}}
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=False,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_or_default_aws_region',
                return_value='us-east-1',
            ),
        ):
            # Call the method
            result = await manager.update_database(mock_ctx, database_name=database_name)

            # Verify that the Glue client was not called to update the database
            mock_glue_client.update_database.assert_not_called()

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.is_error is True
            assert len(result.content) == 1
            assert hasattr(result.content[0], 'text')
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_database_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that update_database returns an error when the database is not found."""
        # Setup
        database_name = 'test-db'

        # Mock the get_database to raise an EntityNotFoundException
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Database not found'}
        }
        mock_glue_client.get_database.side_effect = ClientError(error_response, 'GetDatabase')

        # Call the method
        result = await manager.update_database(mock_ctx, database_name=database_name)

        # Verify that the Glue client was not called to update the database
        mock_glue_client.update_database.assert_not_called()

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.is_error is True
        assert len(result.content) == 1
        assert hasattr(result.content[0], 'text')
        assert 'Database test-db not found' in result.content[0].text
