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

"""Tests for the DataCatalogManager class."""

import pytest
from awslabs.aws_dataprocessing_mcp_server.core.glue_data_catalog.data_catalog_handler import (
    DataCatalogManager,
)
from botocore.exceptions import ClientError
from datetime import datetime
from mcp.types import CallToolResult
from unittest.mock import MagicMock, patch


class TestDataCatalogManager:
    """Tests for the DataCatalogManager class."""

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
        """Create a DataCatalogManager instance with a mocked Glue client."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            manager = DataCatalogManager(allow_write=True)
            return manager

    @pytest.mark.asyncio
    async def test_create_connection_success(self, manager, mock_ctx, mock_glue_client):
        """Test that create_connection returns a successful response when the Glue API call succeeds."""
        # Setup
        connection_name = 'test-connection'
        connection_input = {
            'ConnectionType': 'JDBC',
            'ConnectionProperties': {
                'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test',
                'USERNAME': 'test-user',
                'PASSWORD': 'test-password',  # pragma: allowlist secret
            },
        }
        catalog_id = '123456789012'
        tags = {'tag1': 'value1', 'tag2': 'value2'}

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Call the method
            result = await manager.create_connection(
                mock_ctx,
                connection_name=connection_name,
                connection_input=connection_input,
                catalog_id=catalog_id,
                tags=tags,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.create_connection.assert_called_once()
            call_args = mock_glue_client.create_connection.call_args[1]

            assert call_args['ConnectionInput']['Name'] == connection_name
            assert call_args['ConnectionInput']['ConnectionType'] == 'JDBC'
            assert (
                call_args['ConnectionInput']['ConnectionProperties']['JDBC_CONNECTION_URL']
                == 'jdbc:mysql://localhost:3306/test'
            )
            assert call_args['ConnectionInput']['ConnectionProperties']['USERNAME'] == 'test-user'
            assert (
                call_args['ConnectionInput']['ConnectionProperties']['PASSWORD']
                == 'test-password'  # pragma: allowlist secret
            )
            assert call_args['CatalogId'] == catalog_id

            # Verify that the tags were merged correctly
            expected_tags = {'tag1': 'value1', 'tag2': 'value2', 'mcp:managed': 'true'}
            assert call_args['Tags'] == expected_tags

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) == 2
            assert hasattr(result.content[0], 'text')
            assert f'Successfully created connection: {connection_name}' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_connection_error(self, manager, mock_ctx, mock_glue_client):
        """Test that create_connection returns an error response when the Glue API call fails."""
        # Setup
        connection_name = 'test-connection'
        connection_input = {
            'ConnectionType': 'JDBC',
            'ConnectionProperties': {
                'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test',
                'USERNAME': 'test-user',
                'PASSWORD': 'test-password',  # pragma: allowlist secret
            },
        }

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'AlreadyExistsException', 'Message': 'Connection already exists'}
            }
            mock_glue_client.create_connection.side_effect = ClientError(
                error_response, 'CreateConnection'
            )

            # Call the method
            result = await manager.create_connection(
                mock_ctx, connection_name=connection_name, connection_input=connection_input
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) == 1
            assert hasattr(result.content[0], 'text')
            assert 'Failed to create connection' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_connection_success(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_connection returns a successful response when the Glue API call succeeds."""
        # Setup
        connection_name = 'test-connection'
        catalog_id = '123456789012'

        # Mock the get_connection response to indicate the connection is MCP managed
        mock_glue_client.get_connection.return_value = {
            'Connection': {'Name': connection_name, 'Parameters': {'mcp:managed': 'true'}}
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.delete_connection(
                mock_ctx, connection_name=connection_name, catalog_id=catalog_id
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.delete_connection.assert_called_once_with(
                ConnectionName=connection_name, CatalogId=catalog_id
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert f'Successfully deleted connection: {connection_name}' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_connection_not_mcp_managed(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_connection returns an error when the connection is not MCP managed."""
        # Setup
        connection_name = 'test-connection'

        # Mock the get_connection response to indicate the connection is not MCP managed
        mock_glue_client.get_connection.return_value = {
            'Connection': {'Name': connection_name, 'Parameters': {}}
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=False,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.delete_connection(mock_ctx, connection_name=connection_name)

            # Verify that the Glue client was not called to delete the connection
            mock_glue_client.delete_connection.assert_not_called()

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_connection_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_connection returns a successful response when the Glue API call succeeds."""
        # Setup
        connection_name = 'test-connection'
        catalog_id = '123456789012'
        connection_type = 'JDBC'
        connection_properties = {
            'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test',
            'USERNAME': 'test-user',
        }
        creation_time = datetime(2023, 1, 1, 0, 0, 0)
        last_updated_time = datetime(2023, 1, 2, 0, 0, 0)

        # Mock the get_connection response
        mock_glue_client.get_connection.return_value = {
            'Connection': {
                'Name': connection_name,
                'ConnectionType': connection_type,
                'ConnectionProperties': connection_properties,
                'CreationTime': creation_time,
                'LastUpdatedTime': last_updated_time,
                'LastUpdatedBy': 'test-user',
                'Status': 'ACTIVE',
                'StatusReason': 'Connection is active',
            }
        }

        # Call the method
        result = await manager.get_connection(
            mock_ctx, connection_name=connection_name, catalog_id=catalog_id, hide_password=True
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_connection.assert_called_once_with(
            Name=connection_name, CatalogId=catalog_id, HidePassword=True
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert f'Successfully retrieved connection: {connection_name}' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_connections_success(self, manager, mock_ctx, mock_glue_client):
        """Test that list_connections returns a successful response when the Glue API call succeeds."""
        # Setup
        catalog_id = '123456789012'
        filter_dict = {'ConnectionType': 'JDBC'}
        hide_password = True
        next_token = 'next-token'
        max_results = 10

        # Mock the get_connections response
        creation_time = datetime(2023, 1, 1, 0, 0, 0)
        last_updated_time = datetime(2023, 1, 2, 0, 0, 0)
        mock_glue_client.get_connections.return_value = {
            'ConnectionList': [
                {
                    'Name': 'conn1',
                    'ConnectionType': 'JDBC',
                    'ConnectionProperties': {
                        'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/db1'
                    },
                    'CreationTime': creation_time,
                    'LastUpdatedTime': last_updated_time,
                },
                {
                    'Name': 'conn2',
                    'ConnectionType': 'JDBC',
                    'ConnectionProperties': {
                        'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/db2'
                    },
                    'CreationTime': creation_time,
                    'LastUpdatedTime': last_updated_time,
                },
            ],
            'NextToken': 'next-token-response',
        }

        # Call the method
        result = await manager.list_connections(
            mock_ctx,
            catalog_id=catalog_id,
            filter_dict=filter_dict,
            hide_password=hide_password,
            next_token=next_token,
            max_results=max_results,
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_connections.assert_called_once_with(
            CatalogId=catalog_id,
            Filter=filter_dict,
            HidePassword=hide_password,
            NextToken=next_token,
            MaxResults=max_results,
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Successfully listed 2 connections' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_partition_success(self, manager, mock_ctx, mock_glue_client):
        """Test that create_partition returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        partition_input = {
            'StorageDescriptor': {
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            }
        }
        catalog_id = '123456789012'

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Call the method
            result = await manager.create_partition(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                partition_input=partition_input,
                catalog_id=catalog_id,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.create_partition.assert_called_once()
            call_args = mock_glue_client.create_partition.call_args[1]

            assert call_args['DatabaseName'] == database_name
            assert call_args['TableName'] == table_name
            assert call_args['PartitionInput']['Values'] == partition_values
            assert (
                call_args['PartitionInput']['StorageDescriptor']['Location']
                == 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            )
            assert call_args['CatalogId'] == catalog_id

            # Verify that the MCP tags were added to Parameters
            assert call_args['PartitionInput']['Parameters']['mcp:managed'] == 'true'

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert (
                f'Successfully created partition in table: {database_name}.{table_name}'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_get_partition_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_partition returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        catalog_id = '123456789012'
        creation_time = datetime(2023, 1, 1, 0, 0, 0)
        last_access_time = datetime(2023, 1, 2, 0, 0, 0)

        # Mock the get_partition response
        mock_glue_client.get_partition.return_value = {
            'Partition': {
                'Values': partition_values,
                'DatabaseName': database_name,
                'TableName': table_name,
                'CreationTime': creation_time,
                'LastAccessTime': last_access_time,
                'StorageDescriptor': {
                    'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
                },
                'Parameters': {'key1': 'value1'},
            }
        }

        # Call the method
        result = await manager.get_partition(
            mock_ctx,
            database_name=database_name,
            table_name=table_name,
            partition_values=partition_values,
            catalog_id=catalog_id,
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_partition.assert_called_once_with(
            DatabaseName=database_name,
            TableName=table_name,
            PartitionValues=partition_values,
            CatalogId=catalog_id,
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert (
            f'Successfully retrieved partition from table: {database_name}.{table_name}'
            in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_list_partitions_success(self, manager, mock_ctx, mock_glue_client):
        """Test that list_partitions returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        max_results = 10
        expression = "year='2023'"
        catalog_id = '123456789012'

        # Mock the get_partitions response
        creation_time = datetime(2023, 1, 1, 0, 0, 0)
        last_access_time = datetime(2023, 1, 2, 0, 0, 0)
        mock_glue_client.get_partitions.return_value = {
            'Partitions': [
                {
                    'Values': ['2023', '01', '01'],
                    'DatabaseName': database_name,
                    'TableName': table_name,
                    'CreationTime': creation_time,
                    'LastAccessTime': last_access_time,
                    'StorageDescriptor': {
                        'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
                    },
                    'Parameters': {'key1': 'value1'},
                },
                {
                    'Values': ['2023', '01', '02'],
                    'DatabaseName': database_name,
                    'TableName': table_name,
                    'CreationTime': creation_time,
                    'LastAccessTime': last_access_time,
                    'StorageDescriptor': {
                        'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=02/'
                    },
                    'Parameters': {'key2': 'value2'},
                },
            ],
            'NextToken': 'next-token-response',
        }

        # Call the method
        result = await manager.list_partitions(
            mock_ctx,
            database_name=database_name,
            table_name=table_name,
            max_results=max_results,
            expression=expression,
            catalog_id=catalog_id,
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_partitions.assert_called_once_with(
            DatabaseName=database_name,
            TableName=table_name,
            MaxResults=max_results,
            Expression=expression,
            CatalogId=catalog_id,
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert (
            f'Successfully listed 2 partitions in table {database_name}.{table_name}'
            in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_create_catalog_success(self, manager, mock_ctx, mock_glue_client):
        """Test that create_catalog returns a successful response when the Glue API call succeeds."""
        # Setup
        catalog_name = 'test-catalog'
        catalog_input = {'Description': 'Test catalog', 'Type': 'GLUE'}
        tags = {'tag1': 'value1', 'tag2': 'value2'}

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Call the method
            result = await manager.create_catalog(
                mock_ctx, catalog_name=catalog_name, catalog_input=catalog_input, tags=tags
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.create_catalog.assert_called_once()
            call_args = mock_glue_client.create_catalog.call_args[1]

            assert call_args['Name'] == catalog_name
            assert call_args['CatalogInput']['Description'] == 'Test catalog'
            assert call_args['CatalogInput']['Type'] == 'GLUE'

            # Verify that the tags were merged correctly
            expected_tags = {'tag1': 'value1', 'tag2': 'value2', 'mcp:managed': 'true'}
            assert call_args['Tags'] == expected_tags

            # Verify that the MCP tags were added to Parameters
            assert call_args['CatalogInput']['Parameters']['mcp:managed'] == 'true'

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert f'Successfully created catalog: {catalog_name}' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_catalog_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_catalog returns a successful response when the Glue API call succeeds."""
        # Setup
        catalog_id = 'test-catalog'
        name = 'Test Catalog'
        description = 'Test catalog description'
        create_time = datetime(2023, 1, 1, 0, 0, 0)
        update_time = datetime(2023, 1, 2, 0, 0, 0)

        # Mock the get_catalog response
        mock_glue_client.get_catalog.return_value = {
            'Catalog': {
                'Name': name,
                'Description': description,
                'Parameters': {'key1': 'value1'},
                'CreateTime': create_time,
                'UpdateTime': update_time,
            }
        }

        # Call the method
        result = await manager.get_catalog(mock_ctx, catalog_id=catalog_id)

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_catalog.assert_called_once_with(CatalogId=catalog_id)

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        # Just verify we have content, don't access .text attribute directly
        assert result.content[0] is not None

    @pytest.mark.asyncio
    async def test_list_catalogs_success(self, manager, mock_ctx, mock_glue_client):
        """Test that list_connections returns a successful response when the Glue API call succeeds."""
        next_token = 'next-token'
        max_results = 10

        creation_time = datetime(2023, 1, 1, 0, 0, 0)
        last_updated_time = datetime(2023, 1, 2, 0, 0, 0)
        mock_glue_client.get_catalogs.return_value = {
            'CatalogList': [
                {
                    'CatalogId': '123',
                    'Name': 'catalog1',
                    'CreateTime': creation_time,
                    'UpdateTime': last_updated_time,
                },
                {
                    'CatalogId': '456',
                    'Name': 'catalog2',
                    'CreateTime': creation_time,
                    'UpdateTime': last_updated_time,
                },
            ],
            'NextToken': 'next-token-response',
        }

        result = await manager.list_catalogs(
            mock_ctx,
            next_token=next_token,
            max_results=max_results,
            parent_catalog_id='parent-catalog-id',
        )

        mock_glue_client.get_catalogs.assert_called_once_with(
            NextToken=next_token, MaxResults=max_results, ParentCatalogId='parent-catalog-id'
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Successfully listed 2 catalogs' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_catalogs_error(self, manager, mock_ctx, mock_glue_client):
        """Test that list_connections returns an error response when the Glue API call fails."""
        error_response = {
            'Error': {'Code': 'InternalServiceException', 'Message': 'Internal service error'}
        }
        mock_glue_client.get_catalogs.side_effect = ClientError(error_response, 'GetCatalogs')

        result = await manager.list_catalogs(mock_ctx)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Failed to list catalogs' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_catalogs_empty_result(self, manager, mock_ctx, mock_glue_client):
        """Test that list_connections handles empty results correctly."""
        mock_glue_client.get_catalogs.return_value = {'CatalogList': []}

        result = await manager.list_catalogs(mock_ctx)

        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Successfully listed 0 catalogs' in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_connection_success(self, manager, mock_ctx, mock_glue_client):
        """Test that update_connection returns a successful response when the Glue API call succeeds."""
        # Setup
        connection_name = 'test-connection'
        connection_input = {
            'ConnectionType': 'JDBC',
            'ConnectionProperties': {
                'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test-updated',
                'USERNAME': 'test-user-updated',
                'PASSWORD': 'test-password-updated',  # pragma: allowlist secret
            },
        }
        catalog_id = '123456789012'

        # Mock the get_connection response to indicate the connection is MCP managed
        mock_glue_client.get_connection.return_value = {
            'Connection': {
                'Name': connection_name,
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.update_connection(
                mock_ctx,
                connection_name=connection_name,
                connection_input=connection_input,
                catalog_id=catalog_id,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.update_connection.assert_called_once()
            call_args = mock_glue_client.update_connection.call_args[1]

            assert call_args['Name'] == connection_name
            assert call_args['ConnectionInput']['Name'] == connection_name
            assert call_args['ConnectionInput']['ConnectionType'] == 'JDBC'
            assert (
                call_args['ConnectionInput']['ConnectionProperties']['JDBC_CONNECTION_URL']
                == 'jdbc:mysql://localhost:3306/test-updated'
            )
            assert (
                call_args['ConnectionInput']['ConnectionProperties']['USERNAME']
                == 'test-user-updated'
            )
            assert (
                call_args['ConnectionInput']['ConnectionProperties']['PASSWORD']
                == 'test-password-updated'  # pragma: allowlist secret
            )
            assert call_args['CatalogId'] == catalog_id

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert f'Successfully updated connection: {connection_name}' in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_connection_not_mcp_managed(self, manager, mock_ctx, mock_glue_client):
        """Test that update_connection returns an error when the connection is not MCP managed."""
        # Setup
        connection_name = 'test-connection'
        connection_input = {
            'ConnectionType': 'JDBC',
            'ConnectionProperties': {
                'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test-updated',
                'USERNAME': 'test-user-updated',
                'PASSWORD': 'test-password-updated',  # pragma: allowlist secret
            },
        }

        # Mock the get_connection response to indicate the connection is not MCP managed
        mock_glue_client.get_connection.return_value = {
            'Connection': {'Name': connection_name, 'Parameters': {}}
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=False,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.update_connection(
                mock_ctx, connection_name=connection_name, connection_input=connection_input
            )

            # Verify that the Glue client was not called to update the connection
            mock_glue_client.update_connection.assert_not_called()

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_partition_success(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_partition returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        catalog_id = '123456789012'

        # Mock the get_partition response to indicate the partition is MCP managed
        mock_glue_client.get_partition.return_value = {
            'Partition': {
                'Values': partition_values,
                'DatabaseName': database_name,
                'TableName': table_name,
                'Parameters': {'mcp:managed': 'true', 'mcp:ResourceType': 'GluePartition'},
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.delete_partition(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                catalog_id=catalog_id,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.delete_partition.assert_called_once_with(
                DatabaseName=database_name,
                TableName=table_name,
                PartitionValues=partition_values,
                CatalogId=catalog_id,
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert (
                f'Successfully deleted partition from table: {database_name}.{table_name}'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_update_partition_success(self, manager, mock_ctx, mock_glue_client):
        """Test that update_partition returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        partition_input = {
            'StorageDescriptor': {
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            }
        }
        catalog_id = '123456789012'

        # Mock the get_partition response to indicate the partition is MCP managed
        mock_glue_client.get_partition.return_value = {
            'Partition': {
                'Values': partition_values,
                'DatabaseName': database_name,
                'TableName': table_name,
                'Parameters': {'mcp:managed': 'true', 'mcp:ResourceType': 'GluePartition'},
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.update_partition(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                partition_input=partition_input,
                catalog_id=catalog_id,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.update_partition.assert_called_once()
            call_args = mock_glue_client.update_partition.call_args[1]

            assert call_args['DatabaseName'] == database_name
            assert call_args['TableName'] == table_name
            assert call_args['PartitionValueList'] == partition_values
            assert (
                call_args['PartitionInput']['StorageDescriptor']['Location']
                == 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            )
            assert call_args['CatalogId'] == catalog_id

            # Verify that the MCP tags were preserved
            assert call_args['PartitionInput']['Parameters']['mcp:managed'] == 'true'
            assert call_args['PartitionInput']['Parameters']['mcp:ResourceType'] == 'GluePartition'

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert (
                f'Successfully updated partition in table: {database_name}.{table_name}'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_delete_catalog_success(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_catalog returns a successful response when the Glue API call succeeds."""
        # Setup
        catalog_id = 'test-catalog'

        # Mock the get_catalog response to indicate the catalog is MCP managed
        mock_glue_client.get_catalog.return_value = {
            'Catalog': {
                'Name': 'Test Catalog',
                'Parameters': {'mcp:managed': 'true', 'mcp:ResourceType': 'GlueCatalog'},
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.delete_catalog(mock_ctx, catalog_id=catalog_id)

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.delete_catalog.assert_called_once_with(CatalogId=catalog_id)

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert f'Successfully deleted catalog: {catalog_id}' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_catalog_not_mcp_managed(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_catalog returns an error when the catalog is not MCP managed."""
        # Setup
        catalog_id = 'test-catalog'

        # Mock the get_catalog response to indicate the catalog is not MCP managed
        mock_glue_client.get_catalog.return_value = {
            'Catalog': {'Name': 'Test Catalog', 'Parameters': {}}
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=False,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.delete_catalog(mock_ctx, catalog_id=catalog_id)

            # Verify that the Glue client was not called to delete the catalog
            mock_glue_client.delete_catalog.assert_not_called()

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_catalog_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_catalog returns an error when the catalog is not found."""
        # Setup
        catalog_id = 'test-catalog'

        # Mock the get_catalog to raise EntityNotFoundException
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Catalog not found'}
        }
        mock_glue_client.get_catalog.side_effect = ClientError(error_response, 'GetCatalog')

        # Call the method
        result = await manager.delete_catalog(mock_ctx, catalog_id=catalog_id)

        # Verify that the Glue client was not called to delete the catalog
        mock_glue_client.delete_catalog.assert_not_called()

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Catalog test-catalog not found' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_catalog_error(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_catalog returns an error response when the Glue API call fails."""
        # Setup
        catalog_id = 'test-catalog'

        # Mock the get_catalog response to indicate the catalog is MCP managed
        mock_glue_client.get_catalog.return_value = {
            'Catalog': {
                'Name': 'Test Catalog',
                'Parameters': {'mcp:managed': 'true', 'mcp:ResourceType': 'GlueCatalog'},
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid catalog ID'}
            }
            mock_glue_client.delete_catalog.side_effect = ClientError(
                error_response, 'DeleteCatalog'
            )

            # Call the method
            result = await manager.delete_catalog(mock_ctx, catalog_id=catalog_id)

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'Failed to delete catalog' in result.content[0].text
            assert 'ValidationException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_import_catalog_to_glue_success(self, manager, mock_ctx, mock_glue_client):
        """Test that import_catalog_to_glue returns a successful response when the Glue API call succeeds."""
        # Setup
        catalog_id = 'test-catalog'

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true', 'mcp:ResourceType': 'GlueCatalogImport'},
        ):
            # Call the method
            result = await manager.import_catalog_to_glue(
                mock_ctx,
                catalog_id=catalog_id,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.import_catalog_to_glue.assert_called_once_with(
                CatalogId=catalog_id,
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'Successfully initiated catalog import' in result.content[0].text

    @pytest.mark.asyncio
    async def test_import_catalog_to_glue_error(self, manager, mock_ctx, mock_glue_client):
        """Test that import_catalog_to_glue returns an error response when the Glue API call fails."""
        # Setup
        catalog_id = 'test-catalog'

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true', 'mcp:ResourceType': 'GlueCatalogImport'},
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid catalog ID'}
            }
            mock_glue_client.import_catalog_to_glue.side_effect = ClientError(
                error_response, 'ImportCatalogToGlue'
            )

            # Call the method
            result = await manager.import_catalog_to_glue(
                mock_ctx,
                catalog_id=catalog_id,
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'Failed to import' in result.content[0].text
            assert 'ValidationException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_partition_not_mcp_managed(self, manager, mock_ctx, mock_glue_client):
        """Test that update_partition returns an error when the partition is not MCP managed."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        partition_input = {
            'StorageDescriptor': {
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            }
        }

        # Mock the get_partition response to indicate the partition is not MCP managed
        mock_glue_client.get_partition.return_value = {
            'Partition': {
                'Values': partition_values,
                'DatabaseName': database_name,
                'TableName': table_name,
                'Parameters': {},
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=False,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.update_partition(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                partition_input=partition_input,
            )

            # Verify that the Glue client was not called to update the partition
            mock_glue_client.update_partition.assert_not_called()

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_partition_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that update_partition returns an error when the partition is not found."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        partition_input = {
            'StorageDescriptor': {
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            }
        }

        # Mock the get_partition to raise EntityNotFoundException
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Partition not found'}
        }
        mock_glue_client.get_partition.side_effect = ClientError(error_response, 'GetPartition')

        # Call the method
        result = await manager.update_partition(
            mock_ctx,
            database_name=database_name,
            table_name=table_name,
            partition_values=partition_values,
            partition_input=partition_input,
        )

        # Verify that the Glue client was not called to update the partition
        mock_glue_client.update_partition.assert_not_called()

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert (
            f'Partition in table {database_name}.{table_name} not found' in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_update_partition_error(self, manager, mock_ctx, mock_glue_client):
        """Test that update_partition returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        partition_input = {
            'StorageDescriptor': {
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            }
        }
        catalog_id = '123456789012'

        # Mock the get_partition response to indicate the partition is MCP managed
        mock_glue_client.get_partition.return_value = {
            'Partition': {
                'Values': partition_values,
                'DatabaseName': database_name,
                'TableName': table_name,
                'Parameters': {'mcp:managed': 'true', 'mcp:ResourceType': 'GluePartition'},
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid partition input'}
            }
            mock_glue_client.update_partition.side_effect = ClientError(
                error_response, 'UpdatePartition'
            )

            # Call the method
            result = await manager.update_partition(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                partition_input=partition_input,
                catalog_id=catalog_id,
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'Failed to update partition' in result.content[0].text
            assert 'ValidationException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_partition_not_mcp_managed(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_partition returns an error when the partition is not MCP managed."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']

        # Mock the get_partition response to indicate the partition is not MCP managed
        mock_glue_client.get_partition.return_value = {
            'Partition': {
                'Values': partition_values,
                'DatabaseName': database_name,
                'TableName': table_name,
                'Parameters': {},
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=False,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.delete_partition(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
            )

            # Verify that the Glue client was not called to delete the partition
            mock_glue_client.delete_partition.assert_not_called()

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_partition_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_partition returns an error when the partition is not found."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']

        # Mock the get_partition to raise EntityNotFoundException
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Partition not found'}
        }
        mock_glue_client.get_partition.side_effect = ClientError(error_response, 'GetPartition')

        # Call the method
        result = await manager.delete_partition(
            mock_ctx,
            database_name=database_name,
            table_name=table_name,
            partition_values=partition_values,
        )

        # Verify that the Glue client was not called to delete the partition
        mock_glue_client.delete_partition.assert_not_called()

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert (
            f'Partition in table {database_name}.{table_name} not found' in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_delete_partition_error(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_partition returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        catalog_id = '123456789012'

        # Mock the get_partition response to indicate the partition is MCP managed
        mock_glue_client.get_partition.return_value = {
            'Partition': {
                'Values': partition_values,
                'DatabaseName': database_name,
                'TableName': table_name,
                'Parameters': {'mcp:managed': 'true', 'mcp:ResourceType': 'GluePartition'},
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid partition values'}
            }
            mock_glue_client.delete_partition.side_effect = ClientError(
                error_response, 'DeletePartition'
            )

            # Call the method
            result = await manager.delete_partition(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                catalog_id=catalog_id,
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'Failed to delete partition' in result.content[0].text
            assert 'ValidationException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_connection_error(self, manager, mock_ctx, mock_glue_client):
        """Test that get_connection returns an error response when the Glue API call fails."""
        # Setup
        connection_name = 'test-connection'
        catalog_id = '123456789012'

        # Mock the Glue client to raise an exception
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Connection not found'}
        }
        mock_glue_client.get_connection.side_effect = ClientError(error_response, 'GetConnection')

        # Call the method
        result = await manager.get_connection(
            mock_ctx, connection_name=connection_name, catalog_id=catalog_id
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Failed to get connection' in result.content[0].text
        assert 'EntityNotFoundException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_connection_with_all_parameters(self, manager, mock_ctx, mock_glue_client):
        """Test that get_connection handles all optional parameters correctly."""
        # Setup
        connection_name = 'test-connection'
        catalog_id = '123456789012'
        hide_password = True
        apply_override_for_compute_environment = 'test-env'

        # Mock the get_connection response
        mock_glue_client.get_connection.return_value = {
            'Connection': {
                'Name': connection_name,
                'ConnectionType': 'JDBC',
                'ConnectionProperties': {
                    'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test'
                },
            }
        }

        # Call the method
        result = await manager.get_connection(
            mock_ctx,
            connection_name=connection_name,
            catalog_id=catalog_id,
            hide_password=hide_password,
            apply_override_for_compute_environment=apply_override_for_compute_environment,
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_connection.assert_called_once_with(
            Name=connection_name,
            CatalogId=catalog_id,
            HidePassword=True,
            ApplyOverrideForComputeEnvironment=apply_override_for_compute_environment,
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')

    @pytest.mark.asyncio
    async def test_list_connections_error(self, manager, mock_ctx, mock_glue_client):
        """Test that list_connections returns an error response when the Glue API call fails."""
        # Setup
        catalog_id = '123456789012'

        # Mock the Glue client to raise an exception
        error_response = {
            'Error': {'Code': 'InternalServiceException', 'Message': 'Internal service error'}
        }
        mock_glue_client.get_connections.side_effect = ClientError(
            error_response, 'GetConnections'
        )

        # Call the method
        result = await manager.list_connections(mock_ctx, catalog_id=catalog_id)

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Failed to list connections' in result.content[0].text
        assert 'InternalServiceException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_connections_empty_result(self, manager, mock_ctx, mock_glue_client):
        """Test that list_connections handles empty results correctly."""
        # Setup
        catalog_id = '123456789012'

        # Mock the get_connections response with empty list
        mock_glue_client.get_connections.return_value = {'ConnectionList': []}

        # Call the method
        result = await manager.list_connections(mock_ctx, catalog_id=catalog_id)

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Successfully listed 0 connections' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_partition_error(self, manager, mock_ctx, mock_glue_client):
        """Test that create_partition returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        partition_input = {
            'StorageDescriptor': {
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            }
        }

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'AlreadyExistsException', 'Message': 'Partition already exists'}
            }
            mock_glue_client.create_partition.side_effect = ClientError(
                error_response, 'CreatePartition'
            )

            # Call the method
            result = await manager.create_partition(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                partition_input=partition_input,
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'Failed to create partition' in result.content[0].text
            assert 'AlreadyExistsException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_partition_error(self, manager, mock_ctx, mock_glue_client):
        """Test that get_partition returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        catalog_id = '123456789012'

        # Mock the Glue client to raise an exception
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Partition not found'}
        }
        mock_glue_client.get_partition.side_effect = ClientError(error_response, 'GetPartition')

        # Call the method
        result = await manager.get_partition(
            mock_ctx,
            database_name=database_name,
            table_name=table_name,
            partition_values=partition_values,
            catalog_id=catalog_id,
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Failed to get partition' in result.content[0].text
        assert 'EntityNotFoundException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_partitions_error(self, manager, mock_ctx, mock_glue_client):
        """Test that list_partitions returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'

        # Mock the Glue client to raise an exception
        error_response = {
            'Error': {'Code': 'InternalServiceException', 'Message': 'Internal service error'}
        }
        mock_glue_client.get_partitions.side_effect = ClientError(error_response, 'GetPartitions')

        # Call the method
        result = await manager.list_partitions(
            mock_ctx, database_name=database_name, table_name=table_name
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Failed to list partitions' in result.content[0].text
        assert 'InternalServiceException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_partitions_empty_result(self, manager, mock_ctx, mock_glue_client):
        """Test that list_partitions handles empty results correctly."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'

        # Mock the get_partitions response with empty list
        mock_glue_client.get_partitions.return_value = {'Partitions': []}

        # Call the method
        result = await manager.list_partitions(
            mock_ctx, database_name=database_name, table_name=table_name
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert (
            f'Successfully listed 0 partitions in table {database_name}.{table_name}'
            in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_list_partitions_with_all_parameters(self, manager, mock_ctx, mock_glue_client):
        """Test that list_partitions handles all optional parameters correctly."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        max_results = 10
        expression = "year='2023'"
        catalog_id = '123456789012'
        segment = {'SegmentNumber': 0, 'TotalSegments': 1}
        exclude_column_schema = True
        transaction_id = 'test-transaction-id'
        query_as_of_time = '2023-01-01T00:00:00Z'

        # Mock the get_partitions response
        mock_glue_client.get_partitions.return_value = {'Partitions': []}

        # Call the method
        result = await manager.list_partitions(
            mock_ctx,
            database_name=database_name,
            table_name=table_name,
            max_results=max_results,
            expression=expression,
            catalog_id=catalog_id,
            segment=segment,
            exclude_column_schema=exclude_column_schema,
            transaction_id=transaction_id,
            query_as_of_time=query_as_of_time,
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_partitions.assert_called_once_with(
            DatabaseName=database_name,
            TableName=table_name,
            MaxResults=max_results,
            Expression=expression,
            CatalogId=catalog_id,
            Segment=segment,
            ExcludeColumnSchema='true',
            TransactionId=transaction_id,
            QueryAsOfTime=query_as_of_time,
        )

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')

    @pytest.mark.asyncio
    async def test_create_catalog_error(self, manager, mock_ctx, mock_glue_client):
        """Test that create_catalog returns an error response when the Glue API call fails."""
        # Setup
        catalog_name = 'test-catalog'
        catalog_input = {'Description': 'Test catalog', 'Type': 'GLUE'}

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'AlreadyExistsException', 'Message': 'Catalog already exists'}
            }
            mock_glue_client.create_catalog.side_effect = ClientError(
                error_response, 'CreateCatalog'
            )

            # Call the method
            result = await manager.create_catalog(
                mock_ctx, catalog_name=catalog_name, catalog_input=catalog_input
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')
            assert 'Failed to create catalog' in result.content[0].text
            assert 'AlreadyExistsException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_catalog_error(self, manager, mock_ctx, mock_glue_client):
        """Test that get_catalog returns an error response when the Glue API call fails."""
        # Setup
        catalog_id = 'test-catalog'

        # Mock the Glue client to raise an exception
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Catalog not found'}
        }
        mock_glue_client.get_catalog.side_effect = ClientError(error_response, 'GetCatalog')

        # Call the method
        result = await manager.get_catalog(mock_ctx, catalog_id=catalog_id)

        # Verify the response
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert len(result.content) >= 1
        assert hasattr(result.content[0], 'text')
        assert 'Failed to get catalog' in result.content[0].text
        assert 'EntityNotFoundException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_connection_with_empty_parameters(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that create_connection handles empty parameters correctly."""
        # Setup
        connection_name = 'test-connection'
        connection_input = {
            'ConnectionType': 'JDBC',
            'ConnectionProperties': {
                'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test',
            },
        }

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Call the method
            result = await manager.create_connection(
                mock_ctx, connection_name=connection_name, connection_input=connection_input
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.create_connection.assert_called_once()
            call_args = mock_glue_client.create_connection.call_args[1]

            assert call_args['ConnectionInput']['Name'] == connection_name
            assert call_args['ConnectionInput']['ConnectionType'] == 'JDBC'
            assert (
                call_args['ConnectionInput']['ConnectionProperties']['JDBC_CONNECTION_URL']
                == 'jdbc:mysql://localhost:3306/test'
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')

    @pytest.mark.asyncio
    async def test_update_connection_with_empty_parameters(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that update_connection handles empty parameters correctly."""
        # Setup
        connection_name = 'test-connection'
        connection_input = {
            'ConnectionType': 'JDBC',
            'ConnectionProperties': {
                'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test-updated',
            },
        }

        # Mock the get_connection response to indicate the connection is MCP managed
        mock_glue_client.get_connection.return_value = {
            'Connection': {
                'Name': connection_name,
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.update_connection(
                mock_ctx, connection_name=connection_name, connection_input=connection_input
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.update_connection.assert_called_once()
            call_args = mock_glue_client.update_connection.call_args[1]

            assert call_args['Name'] == connection_name
            assert call_args['ConnectionInput']['Name'] == connection_name
            assert call_args['ConnectionInput']['ConnectionType'] == 'JDBC'
            assert (
                call_args['ConnectionInput']['ConnectionProperties']['JDBC_CONNECTION_URL']
                == 'jdbc:mysql://localhost:3306/test-updated'
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')

    @pytest.mark.asyncio
    async def test_update_connection_with_new_parameters(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that update_connection handles new parameters correctly."""
        # Setup
        connection_name = 'test-connection'
        connection_input = {
            'ConnectionType': 'JDBC',
            'ConnectionProperties': {
                'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test-updated',
            },
        }

        # Mock the get_connection response to indicate the connection is MCP managed
        mock_glue_client.get_connection.return_value = {
            'Connection': {
                'Name': connection_name,
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.update_connection(
                mock_ctx, connection_name=connection_name, connection_input=connection_input
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.update_connection.assert_called_once()
            call_args = mock_glue_client.update_connection.call_args[1]

            assert call_args['Name'] == connection_name
            assert call_args['ConnectionInput']['Name'] == connection_name
            assert call_args['ConnectionInput']['ConnectionType'] == 'JDBC'
            assert (
                call_args['ConnectionInput']['ConnectionProperties']['JDBC_CONNECTION_URL']
                == 'jdbc:mysql://localhost:3306/test-updated'
            )

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')

    @pytest.mark.asyncio
    async def test_update_partition_with_new_parameters(self, manager, mock_ctx, mock_glue_client):
        """Test that update_partition handles new parameters correctly."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        partition_values = ['2023', '01', '01']
        partition_input = {
            'StorageDescriptor': {
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            },
            'Parameters': {'new-param': 'new-value'},
        }

        # Mock the get_partition response to indicate the partition is MCP managed
        mock_glue_client.get_partition.return_value = {
            'Partition': {
                'Values': partition_values,
                'DatabaseName': database_name,
                'TableName': table_name,
                'Parameters': {'mcp:managed': 'true', 'mcp:ResourceType': 'GluePartition'},
            }
        }

        # Mock the AWS helper is_resource_mcp_managed method
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
        ):
            # Call the method
            result = await manager.update_partition(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                partition_values=partition_values,
                partition_input=partition_input,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.update_partition.assert_called_once()
            call_args = mock_glue_client.update_partition.call_args[1]

            assert call_args['DatabaseName'] == database_name
            assert call_args['TableName'] == table_name
            assert call_args['PartitionValueList'] == partition_values
            assert (
                call_args['PartitionInput']['StorageDescriptor']['Location']
                == 's3://test-bucket/test-db/test-table/year=2023/month=01/day=01/'
            )

            # Verify that the MCP tags were preserved and new parameters were added
            assert call_args['PartitionInput']['Parameters']['mcp:managed'] == 'true'
            assert call_args['PartitionInput']['Parameters']['mcp:ResourceType'] == 'GluePartition'
            assert call_args['PartitionInput']['Parameters']['new-param'] == 'new-value'

            # Verify the response
            assert isinstance(result, CallToolResult)
            assert result.isError is False
            assert len(result.content) >= 1
            assert hasattr(result.content[0], 'text')

    # ==================== TestConnection Tests ====================

    @pytest.mark.asyncio
    async def test_test_connection_success(self, manager, mock_ctx, mock_glue_client):
        """Test that test_connection returns a successful response."""
        mock_glue_client.test_connection.return_value = {}

        result = await manager.test_connection(
            mock_ctx,
            connection_name='test-connection',
            catalog_id='123456789012',
        )

        mock_glue_client.test_connection.assert_called_once_with(
            ConnectionName='test-connection',
            CatalogId='123456789012',
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Successfully tested connection' in result.content[0].text

    @pytest.mark.asyncio
    async def test_test_connection_with_test_input(self, manager, mock_ctx, mock_glue_client):
        """Test that test_connection works with TestConnectionInput."""
        mock_glue_client.test_connection.return_value = {}
        test_input = {
            'ConnectionType': 'JDBC',
            'ConnectionProperties': {
                'JDBC_CONNECTION_URL': 'jdbc:mysql://localhost:3306/test',
            },
        }

        result = await manager.test_connection(
            mock_ctx,
            test_connection_input=test_input,
        )

        mock_glue_client.test_connection.assert_called_once_with(
            TestConnectionInput=test_input,
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False

    @pytest.mark.asyncio
    async def test_test_connection_error(self, manager, mock_ctx, mock_glue_client):
        """Test that test_connection handles errors correctly."""
        mock_glue_client.test_connection.side_effect = ClientError(
            {'Error': {'Code': 'InvalidInputException', 'Message': 'Invalid connection'}},
            'TestConnection',
        )

        result = await manager.test_connection(
            mock_ctx,
            connection_name='bad-connection',
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Failed to test connection' in result.content[0].text

    # ==================== BatchDeleteConnection Tests ====================

    @pytest.mark.asyncio
    async def test_batch_delete_connection_success(self, manager, mock_ctx, mock_glue_client):
        """Test that batch_delete_connection returns a successful response."""
        mock_glue_client.batch_delete_connection.return_value = {
            'Succeeded': ['conn-1', 'conn-2'],
            'Errors': {},
        }

        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition',
                return_value='aws',
            ),
        ):
            result = await manager.batch_delete_connection(
                mock_ctx,
                connection_name_list=['conn-1', 'conn-2'],
            )

        mock_glue_client.batch_delete_connection.assert_called_once_with(
            ConnectionNameList=['conn-1', 'conn-2'],
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert '2 succeeded' in result.content[0].text

    @pytest.mark.asyncio
    async def test_batch_delete_connection_not_mcp_managed(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that batch_delete_connection rejects non-MCP-managed connections."""
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=False,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition',
                return_value='aws',
            ),
        ):
            result = await manager.batch_delete_connection(
                mock_ctx,
                connection_name_list=['conn-1'],
            )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_batch_delete_connection_error(self, manager, mock_ctx, mock_glue_client):
        """Test that batch_delete_connection handles API errors."""
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.is_resource_mcp_managed',
                return_value=True,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_aws_partition',
                return_value='aws',
            ),
        ):
            mock_glue_client.batch_delete_connection.side_effect = ClientError(
                {'Error': {'Code': 'InternalServiceException', 'Message': 'Internal error'}},
                'BatchDeleteConnection',
            )
            result = await manager.batch_delete_connection(
                mock_ctx,
                connection_name_list=['conn-1'],
            )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Failed to batch delete connections' in result.content[0].text

    # ==================== DescribeConnectionType Tests ====================

    @pytest.mark.asyncio
    async def test_describe_connection_type_success(self, manager, mock_ctx, mock_glue_client):
        """Test that describe_connection_type returns a successful response."""
        mock_glue_client.describe_connection_type.return_value = {
            'ConnectionType': 'JDBC',
            'Description': 'JDBC connection type',
            'Capabilities': {'SupportedAuthenticationTypes': ['BASIC']},
            'ConnectionProperties': {'HOST': {'Description': 'Host name'}},
            'AuthenticationConfiguration': {'AuthenticationType': 'BASIC'},
        }

        result = await manager.describe_connection_type(
            mock_ctx,
            connection_type='JDBC',
        )

        mock_glue_client.describe_connection_type.assert_called_once_with(
            ConnectionType='JDBC',
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Successfully described connection type: JDBC' in result.content[0].text

    @pytest.mark.asyncio
    async def test_describe_connection_type_error(self, manager, mock_ctx, mock_glue_client):
        """Test that describe_connection_type handles errors correctly."""
        mock_glue_client.describe_connection_type.side_effect = ClientError(
            {'Error': {'Code': 'InvalidInputException', 'Message': 'Unknown type'}},
            'DescribeConnectionType',
        )

        result = await manager.describe_connection_type(
            mock_ctx,
            connection_type='UNKNOWN',
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Failed to describe connection type' in result.content[0].text

    # ==================== ListConnectionTypes Tests ====================

    @pytest.mark.asyncio
    async def test_list_connection_types_success(self, manager, mock_ctx, mock_glue_client):
        """Test that list_connection_types returns a successful response."""
        mock_glue_client.list_connection_types.return_value = {
            'ConnectionTypes': [
                {
                    'ConnectionType': 'JDBC',
                    'DisplayName': 'JDBC',
                    'Vendor': 'AWS',
                    'Description': 'JDBC connections',
                },
                {
                    'ConnectionType': 'KAFKA',
                    'DisplayName': 'Apache Kafka',
                    'Vendor': 'Apache',
                    'Description': 'Kafka connections',
                },
            ],
            'NextToken': None,
        }

        result = await manager.list_connection_types(mock_ctx)

        mock_glue_client.list_connection_types.assert_called_once_with()
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Successfully listed 2 connection types' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_connection_types_with_pagination(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that list_connection_types handles pagination parameters."""
        mock_glue_client.list_connection_types.return_value = {
            'ConnectionTypes': [{'ConnectionType': 'JDBC'}],
            'NextToken': 'next-page-token',
        }

        result = await manager.list_connection_types(
            mock_ctx,
            max_results=1,
            next_token='prev-token',
        )

        mock_glue_client.list_connection_types.assert_called_once_with(
            MaxResults=1,
            NextToken='prev-token',
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False

    @pytest.mark.asyncio
    async def test_list_connection_types_error(self, manager, mock_ctx, mock_glue_client):
        """Test that list_connection_types handles errors correctly."""
        mock_glue_client.list_connection_types.side_effect = ClientError(
            {'Error': {'Code': 'InternalServiceException', 'Message': 'Internal error'}},
            'ListConnectionTypes',
        )

        result = await manager.list_connection_types(mock_ctx)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Failed to list connection types' in result.content[0].text

    # ==================== ListEntities Tests ====================

    @pytest.mark.asyncio
    async def test_list_entities_success(self, manager, mock_ctx, mock_glue_client):
        """Test that list_entities returns a successful response."""
        mock_glue_client.list_entities.return_value = {
            'Entities': [
                {
                    'EntityName': 'Account',
                    'Label': 'Account',
                    'IsParentEntity': False,
                    'Description': 'Salesforce Account object',
                    'Category': 'SObject',
                },
                {
                    'EntityName': 'Contact',
                    'Label': 'Contact',
                    'IsParentEntity': False,
                    'Description': 'Salesforce Contact object',
                    'Category': 'SObject',
                },
            ],
            'NextToken': None,
        }

        result = await manager.list_entities(
            mock_ctx,
            connection_name='my-salesforce-conn',
        )

        mock_glue_client.list_entities.assert_called_once_with(
            ConnectionName='my-salesforce-conn',
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Successfully listed 2 entities' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_entities_with_all_parameters(self, manager, mock_ctx, mock_glue_client):
        """Test that list_entities handles all optional parameters."""
        mock_glue_client.list_entities.return_value = {
            'Entities': [],
            'NextToken': None,
        }

        result = await manager.list_entities(
            mock_ctx,
            connection_name='my-conn',
            catalog_id='123456789012',
            parent_entity_name='my-database',
            next_token='token-123',
            data_store_api_version='v1',
        )

        mock_glue_client.list_entities.assert_called_once_with(
            ConnectionName='my-conn',
            CatalogId='123456789012',
            ParentEntityName='my-database',
            NextToken='token-123',
            DataStoreApiVersion='v1',
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False

    @pytest.mark.asyncio
    async def test_list_entities_error(self, manager, mock_ctx, mock_glue_client):
        """Test that list_entities handles errors correctly."""
        mock_glue_client.list_entities.side_effect = ClientError(
            {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Connection not found'}},
            'ListEntities',
        )

        result = await manager.list_entities(
            mock_ctx,
            connection_name='bad-conn',
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Failed to list entities' in result.content[0].text

    # ==================== DescribeEntity Tests ====================

    @pytest.mark.asyncio
    async def test_describe_entity_success(self, manager, mock_ctx, mock_glue_client):
        """Test that describe_entity returns a successful response."""
        mock_glue_client.describe_entity.return_value = {
            'Fields': [
                {
                    'FieldName': 'Id',
                    'Label': 'ID',
                    'FieldType': 'STRING',
                    'IsPrimaryKey': True,
                    'IsNullable': False,
                    'IsFilterable': True,
                    'IsRetrievable': True,
                },
                {
                    'FieldName': 'Name',
                    'Label': 'Name',
                    'FieldType': 'STRING',
                    'IsPrimaryKey': False,
                    'IsNullable': True,
                    'IsFilterable': True,
                    'IsRetrievable': True,
                },
            ],
            'NextToken': None,
        }

        result = await manager.describe_entity(
            mock_ctx,
            connection_name='my-conn',
            entity_name='Account',
        )

        mock_glue_client.describe_entity.assert_called_once_with(
            ConnectionName='my-conn',
            EntityName='Account',
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert '2 fields' in result.content[0].text

    @pytest.mark.asyncio
    async def test_describe_entity_with_all_parameters(self, manager, mock_ctx, mock_glue_client):
        """Test that describe_entity handles all optional parameters."""
        mock_glue_client.describe_entity.return_value = {
            'Fields': [],
            'NextToken': None,
        }

        result = await manager.describe_entity(
            mock_ctx,
            connection_name='my-conn',
            entity_name='Account',
            catalog_id='123456789012',
            next_token='token-123',
            data_store_api_version='v1',
        )

        mock_glue_client.describe_entity.assert_called_once_with(
            ConnectionName='my-conn',
            EntityName='Account',
            CatalogId='123456789012',
            NextToken='token-123',
            DataStoreApiVersion='v1',
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False

    @pytest.mark.asyncio
    async def test_describe_entity_error(self, manager, mock_ctx, mock_glue_client):
        """Test that describe_entity handles errors correctly."""
        mock_glue_client.describe_entity.side_effect = ClientError(
            {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Entity not found'}},
            'DescribeEntity',
        )

        result = await manager.describe_entity(
            mock_ctx,
            connection_name='my-conn',
            entity_name='BadEntity',
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Failed to describe entity' in result.content[0].text

    # ==================== GetEntityRecords Tests ====================

    @pytest.mark.asyncio
    async def test_get_entity_records_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_entity_records returns a successful response."""
        mock_glue_client.get_entity_records.return_value = {
            'Records': [
                {'Id': '001', 'Name': 'Acme Corp'},
                {'Id': '002', 'Name': 'Globex Inc'},
            ],
            'NextToken': None,
        }

        result = await manager.get_entity_records(
            mock_ctx,
            connection_name='my-conn',
            entity_name='Account',
            limit=10,
        )

        mock_glue_client.get_entity_records.assert_called_once_with(
            ConnectionName='my-conn',
            EntityName='Account',
            Limit=10,
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Successfully retrieved 2 records' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_entity_records_with_all_parameters(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that get_entity_records handles all optional parameters."""
        mock_glue_client.get_entity_records.return_value = {
            'Records': [],
            'NextToken': None,
        }

        result = await manager.get_entity_records(
            mock_ctx,
            connection_name='my-conn',
            entity_name='Account',
            limit=5,
            catalog_id='123456789012',
            next_token='token-123',
            data_store_api_version='v1',
            connection_options={'key': 'value'},
            filter_predicate="Name = 'Acme'",
            selected_fields=['Id', 'Name'],
        )

        mock_glue_client.get_entity_records.assert_called_once_with(
            ConnectionName='my-conn',
            EntityName='Account',
            Limit=5,
            CatalogId='123456789012',
            NextToken='token-123',
            DataStoreApiVersion='v1',
            ConnectionOptions={'key': 'value'},
            FilterPredicate="Name = 'Acme'",
            SelectedFields=['Id', 'Name'],
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False

    @pytest.mark.asyncio
    async def test_get_entity_records_error(self, manager, mock_ctx, mock_glue_client):
        """Test that get_entity_records handles errors correctly."""
        mock_glue_client.get_entity_records.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid request'}},
            'GetEntityRecords',
        )

        result = await manager.get_entity_records(
            mock_ctx,
            connection_name='my-conn',
            entity_name='Account',
            limit=10,
        )

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Failed to get entity records' in result.content[0].text
