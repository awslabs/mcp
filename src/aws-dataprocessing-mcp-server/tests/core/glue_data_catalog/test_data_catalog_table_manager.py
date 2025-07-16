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

"""Tests for the DataCatalogTableManager class."""

import pytest
from awslabs.aws_dataprocessing_mcp_server.core.glue_data_catalog.data_catalog_table_manager import (
    DataCatalogTableManager,
)
from awslabs.aws_dataprocessing_mcp_server.models.data_catalog_models import (
    CreateTableResponse,
    DeleteTableResponse,
    GetTableResponse,
    ListTablesResponse,
    SearchTablesResponse,
    UpdateTableResponse,
)
from botocore.exceptions import ClientError
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestDataCatalogTableManager:
    """Tests for the DataCatalogTableManager class."""

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
        """Create a DataCatalogTableManager instance with a mocked Glue client."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            manager = DataCatalogTableManager(allow_write=True)
            return manager

    @pytest.mark.asyncio
    async def test_create_table_success(self, manager, mock_ctx, mock_glue_client):
        """Test that create_table returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        table_input = {
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}],
                'Location': 's3://test-bucket/test-db/test-table/',
                'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                'SerdeInfo': {
                    'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
                },
            },
            'PartitionKeys': [
                {'Name': 'year', 'Type': 'string'},
                {'Name': 'month', 'Type': 'string'},
                {'Name': 'day', 'Type': 'string'},
            ],
            'TableType': 'EXTERNAL_TABLE',
        }
        catalog_id = '123456789012'

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'ManagedBy': 'DataprocessingMCPServer'},
        ):
            # Call the method
            result = await manager.create_table(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                table_input=table_input,
                catalog_id=catalog_id,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.create_table.assert_called_once()
            call_args = mock_glue_client.create_table.call_args[1]

            assert call_args['DatabaseName'] == database_name
            assert call_args['TableInput']['Name'] == table_name
            assert call_args['TableInput']['StorageDescriptor']['Columns'][0]['Name'] == 'id'
            assert call_args['TableInput']['StorageDescriptor']['Columns'][1]['Name'] == 'name'
            assert call_args['TableInput']['PartitionKeys'][0]['Name'] == 'year'
            assert call_args['TableInput']['TableType'] == 'EXTERNAL_TABLE'
            assert call_args['CatalogId'] == catalog_id

            # Verify that the MCP tags were added to Parameters
            assert call_args['TableInput']['Parameters']['ManagedBy'] == 'DataprocessingMCPServer'

            # Verify the response
            assert isinstance(result, CreateTableResponse)
            assert result.isError is False
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'create-table'
            assert len(result.content) == 1
            assert (
                result.content[0].text
                == f'Successfully created table: {database_name}.{table_name}'
            )

    @pytest.mark.asyncio
    async def test_create_table_error(self, manager, mock_ctx, mock_glue_client):
        """Test that create_table returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        table_input = {
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}]
            }
        }

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'AlreadyExistsException', 'Message': 'Table already exists'}
            }
            mock_glue_client.create_table.side_effect = ClientError(error_response, 'CreateTable')

            # Call the method
            result = await manager.create_table(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                table_input=table_input,
            )

            # Verify the response
            assert isinstance(result, CreateTableResponse)
            assert result.isError is True
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'create-table'
            assert len(result.content) == 1
            assert 'Failed to create table' in result.content[0].text
            assert 'AlreadyExistsException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_table_without_parameters(self, manager, mock_ctx, mock_glue_client):
        """Test that create_table handles the case where table_input doesn't have Parameters."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        table_input = {
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}],
                'Location': 's3://test-bucket/test-db/test-table/',
            },
            'TableType': 'EXTERNAL_TABLE',
        }
        # Note: No Parameters field in table_input

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Call the method
            result = await manager.create_table(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                table_input=table_input,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.create_table.assert_called_once()
            call_args = mock_glue_client.create_table.call_args[1]

            # Verify that Parameters was created with MCP tags
            assert 'Parameters' in call_args['TableInput']
            assert call_args['TableInput']['Parameters'] == {'mcp:managed': 'true'}

            # Verify the response
            assert isinstance(result, CreateTableResponse)
            assert result.isError is False
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'create-table'

    @pytest.mark.asyncio
    async def test_create_table_with_all_optional_params(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that create_table handles all optional parameters correctly."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        table_input = {
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}],
            },
            'Parameters': {'existing_param': 'value'},
        }
        partition_indexes = [{'Keys': ['year', 'month']}]
        transaction_id = 'test-transaction-id'
        open_table_format_input = {'FormatType': 'iceberg'}

        # Mock the AWS helper prepare_resource_tags method
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.prepare_resource_tags',
            return_value={'mcp:managed': 'true'},
        ):
            # Call the method
            result = await manager.create_table(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                table_input=table_input,
                partition_indexes=partition_indexes,
                transaction_id=transaction_id,
                open_table_format_input=open_table_format_input,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.create_table.assert_called_once()
            call_args = mock_glue_client.create_table.call_args[1]

            # Verify all optional parameters were passed correctly
            assert call_args['PartitionIndexes'] == partition_indexes
            assert call_args['TransactionId'] == transaction_id
            assert call_args['OpenTableFormatInput'] == open_table_format_input

            # Verify that MCP tags were added to existing Parameters
            assert call_args['TableInput']['Parameters']['existing_param'] == 'value'
            assert call_args['TableInput']['Parameters']['mcp:managed'] == 'true'

            # Verify the response
            assert isinstance(result, CreateTableResponse)
            assert result.isError is False

    @pytest.mark.asyncio
    async def test_delete_table_success(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_table returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        catalog_id = '123456789012'

        # Mock the get_table response to indicate the table is MCP managed
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': table_name,
                'DatabaseName': database_name,
                'Parameters': {'mcp:managed': 'true'},
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
        ):
            # Call the method
            result = await manager.delete_table(
                mock_ctx, database_name=database_name, table_name=table_name, catalog_id=catalog_id
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.delete_table.assert_called_once_with(
                DatabaseName=database_name, Name=table_name, CatalogId=catalog_id
            )

            # Verify the response
            assert isinstance(result, DeleteTableResponse)
            assert result.isError is False
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'delete-table'
            assert len(result.content) == 1
            assert (
                result.content[0].text
                == f'Successfully deleted table: {database_name}.{table_name}'
            )

    @pytest.mark.asyncio
    async def test_delete_table_not_mcp_managed(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_table returns an error when the table is not MCP managed."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'

        # Mock the get_table response to indicate the table is not MCP managed
        mock_glue_client.get_table.return_value = {
            'Table': {'Name': table_name, 'DatabaseName': database_name, 'Parameters': {}}
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
        ):
            # Call the method
            result = await manager.delete_table(
                mock_ctx, database_name=database_name, table_name=table_name
            )

            # Verify that the Glue client was not called to delete the table
            mock_glue_client.delete_table.assert_not_called()

            # Verify the response
            assert isinstance(result, DeleteTableResponse)
            assert result.isError is True
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'delete-table'
            assert len(result.content) == 1
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_table_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_table returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        catalog_id = '123456789012'
        creation_time = datetime(2023, 1, 1, 0, 0, 0)
        last_access_time = datetime(2023, 1, 2, 0, 0, 0)

        # Mock the get_table response
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': table_name,
                'DatabaseName': database_name,
                'CreateTime': creation_time,
                'LastAccessTime': last_access_time,
                'StorageDescriptor': {
                    'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}],
                    'Location': 's3://test-bucket/test-db/test-table/',
                    'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                    'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                    'SerdeInfo': {
                        'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
                    },
                },
                'PartitionKeys': [
                    {'Name': 'year', 'Type': 'string'},
                    {'Name': 'month', 'Type': 'string'},
                    {'Name': 'day', 'Type': 'string'},
                ],
                'TableType': 'EXTERNAL_TABLE',
                'Parameters': {'mcp:managed': 'true'},
            }
        }

        # Call the method
        result = await manager.get_table(
            mock_ctx, database_name=database_name, table_name=table_name, catalog_id=catalog_id
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_table.assert_called_once_with(
            DatabaseName=database_name, Name=table_name, CatalogId=catalog_id
        )

        # Verify the response
        assert isinstance(result, GetTableResponse)
        assert result.isError is False
        assert result.database_name == database_name
        assert result.table_name == table_name
        assert result.creation_time == creation_time.isoformat()
        assert result.last_access_time == last_access_time.isoformat()
        assert result.storage_descriptor['Columns'][0]['Name'] == 'id'
        assert result.storage_descriptor['Columns'][1]['Name'] == 'name'
        assert result.partition_keys[0]['Name'] == 'year'
        assert result.partition_keys[1]['Name'] == 'month'
        assert result.partition_keys[2]['Name'] == 'day'
        assert result.operation == 'get-table'
        assert len(result.content) == 1
        assert (
            result.content[0].text == f'Successfully retrieved table: {database_name}.{table_name}'
        )

    @pytest.mark.asyncio
    async def test_list_tables_success(self, manager, mock_ctx, mock_glue_client):
        """Test that list_tables returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        max_results = 10
        catalog_id = '123456789012'

        # Mock the get_tables response
        creation_time = datetime(2023, 1, 1, 0, 0, 0)
        update_time = datetime(2023, 1, 2, 0, 0, 0)
        last_access_time = datetime(2023, 1, 3, 0, 0, 0)
        mock_glue_client.get_tables.return_value = {
            'TableList': [
                {
                    'Name': 'table1',
                    'DatabaseName': database_name,
                    'Owner': 'owner1',
                    'CreateTime': creation_time,
                    'UpdateTime': update_time,
                    'LastAccessTime': last_access_time,
                    'StorageDescriptor': {
                        'Columns': [
                            {'Name': 'id', 'Type': 'int'},
                            {'Name': 'name', 'Type': 'string'},
                        ]
                    },
                    'PartitionKeys': [{'Name': 'year', 'Type': 'string'}],
                },
                {
                    'Name': 'table2',
                    'DatabaseName': database_name,
                    'Owner': 'owner2',
                    'CreateTime': creation_time,
                    'UpdateTime': update_time,
                    'LastAccessTime': last_access_time,
                    'StorageDescriptor': {
                        'Columns': [
                            {'Name': 'id', 'Type': 'int'},
                            {'Name': 'value', 'Type': 'double'},
                        ]
                    },
                    'PartitionKeys': [{'Name': 'date', 'Type': 'string'}],
                },
            ]
        }

        # Call the method
        result = await manager.list_tables(
            mock_ctx, database_name=database_name, max_results=max_results, catalog_id=catalog_id
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_tables.assert_called_once_with(
            DatabaseName=database_name, MaxResults=max_results, CatalogId=catalog_id
        )

        # Verify the response
        assert isinstance(result, ListTablesResponse)
        assert result.isError is False
        assert result.database_name == database_name
        assert len(result.tables) == 2
        assert result.count == 2
        assert result.operation == 'list-tables'
        assert len(result.content) == 1
        assert (
            result.content[0].text == f'Successfully listed 2 tables in database {database_name}'
        )

        # Verify the table summaries
        assert result.tables[0].name == 'table1'
        assert result.tables[0].database_name == database_name
        assert result.tables[0].owner == 'owner1'
        assert result.tables[0].creation_time == creation_time.isoformat()
        assert result.tables[0].update_time == update_time.isoformat()
        assert result.tables[0].last_access_time == last_access_time.isoformat()
        assert result.tables[0].storage_descriptor['Columns'][0]['Name'] == 'id'
        assert result.tables[0].storage_descriptor['Columns'][1]['Name'] == 'name'
        assert result.tables[0].partition_keys[0]['Name'] == 'year'

        assert result.tables[1].name == 'table2'
        assert result.tables[1].database_name == database_name
        assert result.tables[1].owner == 'owner2'
        assert result.tables[1].creation_time == creation_time.isoformat()
        assert result.tables[1].update_time == update_time.isoformat()
        assert result.tables[1].last_access_time == last_access_time.isoformat()
        assert result.tables[1].storage_descriptor['Columns'][0]['Name'] == 'id'
        assert result.tables[1].storage_descriptor['Columns'][1]['Name'] == 'value'
        assert result.tables[1].partition_keys[0]['Name'] == 'date'

    @pytest.mark.asyncio
    async def test_update_table_success(self, manager, mock_ctx, mock_glue_client):
        """Test that update_table returns a successful response when the Glue API call succeeds."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        table_input = {
            'StorageDescriptor': {
                'Columns': [
                    {'Name': 'id', 'Type': 'int'},
                    {'Name': 'name', 'Type': 'string'},
                    {'Name': 'value', 'Type': 'double'},  # Added a new column
                ]
            }
        }
        catalog_id = '123456789012'

        # Mock the get_table response to indicate the table is MCP managed
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': table_name,
                'DatabaseName': database_name,
                'Parameters': {'mcp:managed': 'true'},
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
        ):
            # Call the method
            result = await manager.update_table(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                table_input=table_input,
                catalog_id=catalog_id,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.update_table.assert_called_once()
            call_args = mock_glue_client.update_table.call_args[1]

            assert call_args['DatabaseName'] == database_name
            assert call_args['TableInput']['Name'] == table_name
            assert call_args['TableInput']['StorageDescriptor']['Columns'][0]['Name'] == 'id'
            assert call_args['TableInput']['StorageDescriptor']['Columns'][1]['Name'] == 'name'
            assert call_args['TableInput']['StorageDescriptor']['Columns'][2]['Name'] == 'value'
            assert call_args['CatalogId'] == catalog_id

            # Verify that the MCP tags were preserved in Parameters
            assert call_args['TableInput']['Parameters']['mcp:managed'] == 'true'

            # Verify the response
            assert isinstance(result, UpdateTableResponse)
            assert result.isError is False
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'update-table'
            assert len(result.content) == 1
            assert (
                result.content[0].text
                == f'Successfully updated table: {database_name}.{table_name}'
            )

    @pytest.mark.asyncio
    async def test_update_table_not_mcp_managed(self, manager, mock_ctx, mock_glue_client):
        """Test that update_table returns an error when the table is not MCP managed."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        table_input = {
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}]
            }
        }

        # Mock the get_table response to indicate the table is not MCP managed
        mock_glue_client.get_table.return_value = {
            'Table': {'Name': table_name, 'DatabaseName': database_name, 'Parameters': {}}
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
        ):
            # Call the method
            result = await manager.update_table(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                table_input=table_input,
            )

            # Verify that the Glue client was not called to update the table
            mock_glue_client.update_table.assert_not_called()

            # Verify the response
            assert isinstance(result, UpdateTableResponse)
            assert result.isError is True
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'update-table'
            assert len(result.content) == 1
            assert 'not managed by the MCP server' in result.content[0].text

    @pytest.mark.asyncio
    async def test_search_tables_success(self, manager, mock_ctx, mock_glue_client):
        """Test that search_tables returns a successful response when the Glue API call succeeds."""
        # Setup
        search_text = 'test'
        max_results = 10
        catalog_id = '123456789012'

        # Mock the search_tables response
        creation_time = datetime(2023, 1, 1, 0, 0, 0)
        update_time = datetime(2023, 1, 2, 0, 0, 0)
        last_access_time = datetime(2023, 1, 3, 0, 0, 0)
        mock_glue_client.search_tables.return_value = {
            'TableList': [
                {
                    'Name': 'test_table1',
                    'DatabaseName': 'db1',
                    'Owner': 'owner1',
                    'CreateTime': creation_time,
                    'UpdateTime': update_time,
                    'LastAccessTime': last_access_time,
                    'StorageDescriptor': {
                        'Columns': [
                            {'Name': 'id', 'Type': 'int'},
                            {'Name': 'name', 'Type': 'string'},
                        ]
                    },
                    'PartitionKeys': [{'Name': 'year', 'Type': 'string'}],
                },
                {
                    'Name': 'test_table2',
                    'DatabaseName': 'db2',
                    'Owner': 'owner2',
                    'CreateTime': creation_time,
                    'UpdateTime': update_time,
                    'LastAccessTime': last_access_time,
                    'StorageDescriptor': {
                        'Columns': [
                            {'Name': 'id', 'Type': 'int'},
                            {'Name': 'value', 'Type': 'double'},
                        ]
                    },
                    'PartitionKeys': [{'Name': 'date', 'Type': 'string'}],
                },
            ]
        }

        # Call the method
        result = await manager.search_tables(
            mock_ctx, search_text=search_text, max_results=max_results, catalog_id=catalog_id
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.search_tables.assert_called_once_with(
            SearchText=search_text, MaxResults=max_results, CatalogId=catalog_id
        )

        # Verify the response
        assert isinstance(result, SearchTablesResponse)
        assert result.isError is False
        assert result.search_text == search_text
        assert len(result.tables) == 2
        assert result.count == 2
        assert result.operation == 'search-tables'
        assert len(result.content) == 1
        assert result.content[0].text == 'Search found 2 tables'

        # Verify the table summaries
        assert result.tables[0].name == 'test_table1'
        assert result.tables[0].database_name == 'db1'
        assert result.tables[0].owner == 'owner1'
        assert result.tables[0].creation_time == creation_time.isoformat()
        assert result.tables[0].update_time == update_time.isoformat()
        assert result.tables[0].last_access_time == last_access_time.isoformat()
        assert result.tables[0].storage_descriptor['Columns'][0]['Name'] == 'id'
        assert result.tables[0].storage_descriptor['Columns'][1]['Name'] == 'name'
        assert result.tables[0].partition_keys[0]['Name'] == 'year'

        assert result.tables[1].name == 'test_table2'
        assert result.tables[1].database_name == 'db2'
        assert result.tables[1].owner == 'owner2'
        assert result.tables[1].creation_time == creation_time.isoformat()
        assert result.tables[1].update_time == update_time.isoformat()
        assert result.tables[1].last_access_time == last_access_time.isoformat()
        assert result.tables[1].storage_descriptor['Columns'][0]['Name'] == 'id'
        assert result.tables[1].storage_descriptor['Columns'][1]['Name'] == 'value'
        assert result.tables[1].partition_keys[0]['Name'] == 'date'

    @pytest.mark.asyncio
    async def test_get_table_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that get_table returns an error when the table is not found."""
        # Setup
        database_name = 'test-db'
        table_name = 'nonexistent-table'
        catalog_id = '123456789012'

        # Mock the get_table to raise EntityNotFoundException
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Table not found'}
        }
        mock_glue_client.get_table.side_effect = ClientError(error_response, 'GetTable')

        # Call the method
        result = await manager.get_table(
            mock_ctx, database_name=database_name, table_name=table_name, catalog_id=catalog_id
        )

        # Verify the response
        assert isinstance(result, GetTableResponse)
        assert result.isError is True
        assert result.database_name == database_name
        assert result.table_name == table_name
        assert result.operation == 'get-table'
        assert len(result.content) == 1
        assert 'Failed to get table' in result.content[0].text
        assert 'EntityNotFoundException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_table_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that update_table returns an error when the table is not found."""
        # Setup
        database_name = 'test-db'
        table_name = 'nonexistent-table'
        table_input = {
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}]
            }
        }
        catalog_id = '123456789012'

        # Mock the get_table to raise EntityNotFoundException
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Table not found'}
        }
        mock_glue_client.get_table.side_effect = ClientError(error_response, 'GetTable')

        # Call the method
        result = await manager.update_table(
            mock_ctx,
            database_name=database_name,
            table_name=table_name,
            table_input=table_input,
            catalog_id=catalog_id,
        )

        # Verify that the Glue client was not called to update the table
        mock_glue_client.update_table.assert_not_called()

        # Verify the response
        assert isinstance(result, UpdateTableResponse)
        assert result.isError is True
        assert result.database_name == database_name
        assert result.table_name == table_name
        assert result.operation == 'update-table'
        assert len(result.content) == 1
        assert f'Table {database_name}.{table_name} not found' in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_table_error(self, manager, mock_ctx, mock_glue_client):
        """Test that update_table returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        table_input = {
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}]
            }
        }
        catalog_id = '123456789012'

        # Mock the get_table response to indicate the table is MCP managed
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': table_name,
                'DatabaseName': database_name,
                'Parameters': {'mcp:managed': 'true'},
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
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid table input'}
            }
            mock_glue_client.update_table.side_effect = ClientError(error_response, 'UpdateTable')

            # Call the method
            result = await manager.update_table(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                table_input=table_input,
                catalog_id=catalog_id,
            )

            # Verify the response
            assert isinstance(result, UpdateTableResponse)
            assert result.isError is True
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'update-table'
            assert len(result.content) == 1
            assert 'Failed to update table' in result.content[0].text
            assert 'ValidationException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_update_table_with_optional_params(self, manager, mock_ctx, mock_glue_client):
        """Test that update_table handles all optional parameters correctly."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        table_input = {
            'StorageDescriptor': {
                'Columns': [{'Name': 'id', 'Type': 'int'}],
            },
        }
        skip_archive = True
        transaction_id = 'test-transaction-id'
        version_id = 'test-version-id'
        view_update_action = 'REPLACE'
        force = True

        # Mock the get_table response to indicate the table is MCP managed
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': table_name,
                'DatabaseName': database_name,
                'Parameters': {'mcp:managed': 'true'},
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
        ):
            # Call the method with all optional parameters
            result = await manager.update_table(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                table_input=table_input,
                skip_archive=skip_archive,
                transaction_id=transaction_id,
                version_id=version_id,
                view_update_action=view_update_action,
                force=force,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.update_table.assert_called_once()
            call_args = mock_glue_client.update_table.call_args[1]

            assert call_args['DatabaseName'] == database_name
            assert call_args['TableInput']['Name'] == table_name
            assert call_args['SkipArchive'] == skip_archive
            assert call_args['TransactionId'] == transaction_id
            assert call_args['VersionId'] == version_id
            assert call_args['ViewUpdateAction'] == view_update_action
            assert call_args['Force'] == force

            # Verify the response
            assert isinstance(result, UpdateTableResponse)
            assert result.isError is False
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'update-table'

    @pytest.mark.asyncio
    async def test_list_tables_error(self, manager, mock_ctx, mock_glue_client):
        """Test that list_tables returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'
        max_results = 10
        catalog_id = '123456789012'

        # Mock the Glue client to raise an exception
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Database not found'}
        }
        mock_glue_client.get_tables.side_effect = ClientError(error_response, 'GetTables')

        # Call the method
        result = await manager.list_tables(
            mock_ctx, database_name=database_name, max_results=max_results, catalog_id=catalog_id
        )

        # Verify the response
        assert isinstance(result, ListTablesResponse)
        assert result.isError is True
        assert result.database_name == database_name
        assert result.tables == []
        assert result.count == 0
        assert result.operation == 'list-tables'
        assert len(result.content) == 1
        assert 'Failed to list tables' in result.content[0].text
        assert 'EntityNotFoundException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_tables_with_optional_params(self, manager, mock_ctx, mock_glue_client):
        """Test that list_tables handles all optional parameters correctly."""
        # Setup
        database_name = 'test-db'
        expression = 'table*'
        next_token = 'next-token-value'
        transaction_id = 'test-transaction-id'
        query_as_of_time = datetime(2023, 1, 1, 0, 0, 0)
        include_status_details = True
        attributes_to_get = ['Name', 'Owner']

        # Mock the get_tables response
        mock_glue_client.get_tables.return_value = {
            'TableList': [
                {
                    'Name': 'table1',
                    'DatabaseName': database_name,
                    'Owner': 'owner1',
                    'CreateTime': datetime(2023, 1, 1, 0, 0, 0),
                }
            ]
        }

        # Call the method with all optional parameters
        result = await manager.list_tables(
            mock_ctx,
            database_name=database_name,
            expression=expression,
            next_token=next_token,
            transaction_id=transaction_id,
            query_as_of_time=query_as_of_time,
            include_status_details=include_status_details,
            attributes_to_get=attributes_to_get,
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_tables.assert_called_once_with(
            DatabaseName=database_name,
            Expression=expression,
            NextToken=next_token,
            TransactionId=transaction_id,
            QueryAsOfTime=query_as_of_time,
            IncludeStatusDetails=include_status_details,
            AttributesToGet=attributes_to_get,
        )

        # Verify the response
        assert isinstance(result, ListTablesResponse)
        assert result.isError is False
        assert result.database_name == database_name
        assert len(result.tables) == 1
        assert result.count == 1
        assert result.operation == 'list-tables'

    @pytest.mark.asyncio
    async def test_search_tables_error(self, manager, mock_ctx, mock_glue_client):
        """Test that search_tables returns an error response when the Glue API call fails."""
        # Setup
        search_text = 'test'
        max_results = 10
        catalog_id = '123456789012'

        # Mock the Glue client to raise an exception
        error_response = {
            'Error': {'Code': 'ValidationException', 'Message': 'Invalid search text'}
        }
        mock_glue_client.search_tables.side_effect = ClientError(error_response, 'SearchTables')

        # Call the method
        result = await manager.search_tables(
            mock_ctx, search_text=search_text, max_results=max_results, catalog_id=catalog_id
        )

        # Verify the response
        assert isinstance(result, SearchTablesResponse)
        assert result.isError is True
        assert result.search_text == search_text
        assert result.tables == []
        assert result.count == 0
        assert result.operation == 'search-tables'
        assert len(result.content) == 1
        assert 'Failed to search tables' in result.content[0].text
        assert 'ValidationException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_search_tables_with_optional_params(self, manager, mock_ctx, mock_glue_client):
        """Test that search_tables handles all optional parameters correctly."""
        # Setup
        search_text = 'test'
        next_token = 'next-token-value'
        filters = [{'Key': 'DatabaseName', 'Value': 'test-db'}]
        sort_criteria = [{'FieldName': 'Name', 'Sort': 'ASC'}]
        resource_share_type = 'ALL'
        include_status_details = True

        # Mock the search_tables response
        mock_glue_client.search_tables.return_value = {
            'TableList': [
                {
                    'Name': 'test_table1',
                    'DatabaseName': 'db1',
                    'Owner': 'owner1',
                    'CreateTime': datetime(2023, 1, 1, 0, 0, 0),
                }
            ]
        }

        # Call the method with all optional parameters
        result = await manager.search_tables(
            mock_ctx,
            search_text=search_text,
            next_token=next_token,
            filters=filters,
            sort_criteria=sort_criteria,
            resource_share_type=resource_share_type,
            include_status_details=include_status_details,
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.search_tables.assert_called_once_with(
            SearchText=search_text,
            NextToken=next_token,
            Filters=filters,
            SortCriteria=sort_criteria,
            ResourceShareType=resource_share_type,
            IncludeStatusDetails=include_status_details,
        )

        # Verify the response
        assert isinstance(result, SearchTablesResponse)
        assert result.isError is False
        assert result.search_text == search_text
        assert len(result.tables) == 1
        assert result.count == 1
        assert result.operation == 'search-tables'

    @pytest.mark.asyncio
    async def test_delete_table_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_table returns an error when the table is not found."""
        # Setup
        database_name = 'test-db'
        table_name = 'nonexistent-table'
        catalog_id = '123456789012'

        # Mock the get_table to raise EntityNotFoundException
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Table not found'}
        }
        mock_glue_client.get_table.side_effect = ClientError(error_response, 'GetTable')

        # Call the method
        result = await manager.delete_table(
            mock_ctx, database_name=database_name, table_name=table_name, catalog_id=catalog_id
        )

        # Verify that the Glue client was not called to delete the table
        mock_glue_client.delete_table.assert_not_called()

        # Verify the response
        assert isinstance(result, DeleteTableResponse)
        assert result.isError is True
        assert result.database_name == database_name
        assert result.table_name == table_name
        assert result.operation == 'delete-table'
        assert len(result.content) == 1
        assert f'Table {database_name}.{table_name} not found' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_table_error(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_table returns an error response when the Glue API call fails."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        catalog_id = '123456789012'

        # Mock the get_table response to indicate the table is MCP managed
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': table_name,
                'DatabaseName': database_name,
                'Parameters': {'mcp:managed': 'true'},
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
        ):
            # Mock the Glue client to raise an exception
            error_response = {
                'Error': {'Code': 'InternalServiceException', 'Message': 'Internal service error'}
            }
            mock_glue_client.delete_table.side_effect = ClientError(error_response, 'DeleteTable')

            # Call the method
            result = await manager.delete_table(
                mock_ctx, database_name=database_name, table_name=table_name, catalog_id=catalog_id
            )

            # Verify the response
            assert isinstance(result, DeleteTableResponse)
            assert result.isError is True
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'delete-table'
            assert len(result.content) == 1
            assert 'Failed to delete table' in result.content[0].text
            assert 'InternalServiceException' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_table_with_transaction_id(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_table handles the transaction_id parameter correctly."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        transaction_id = 'test-transaction-id'

        # Mock the get_table response to indicate the table is MCP managed
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': table_name,
                'DatabaseName': database_name,
                'Parameters': {'mcp:managed': 'true'},
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
        ):
            # Call the method with transaction_id
            result = await manager.delete_table(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                transaction_id=transaction_id,
            )

            # Verify that the Glue client was called with the correct parameters
            mock_glue_client.delete_table.assert_called_once_with(
                DatabaseName=database_name, Name=table_name, TransactionId=transaction_id
            )

            # Verify the response
            assert isinstance(result, DeleteTableResponse)
            assert result.isError is False
            assert result.database_name == database_name
            assert result.table_name == table_name
            assert result.operation == 'delete-table'

    @pytest.mark.asyncio
    async def test_get_table_with_optional_params(self, manager, mock_ctx, mock_glue_client):
        """Test that get_table handles all optional parameters correctly."""
        # Setup
        database_name = 'test-db'
        table_name = 'test-table'
        transaction_id = 'test-transaction-id'
        query_as_of_time = datetime(2023, 1, 1, 0, 0, 0)
        include_status_details = True

        # Mock the get_table response
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': table_name,
                'DatabaseName': database_name,
                'CreateTime': datetime(2023, 1, 1, 0, 0, 0),
                'Parameters': {'mcp:managed': 'true'},
            }
        }

        # Call the method with all optional parameters
        result = await manager.get_table(
            mock_ctx,
            database_name=database_name,
            table_name=table_name,
            transaction_id=transaction_id,
            query_as_of_time=query_as_of_time,
            include_status_details=include_status_details,
        )

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_table.assert_called_once_with(
            DatabaseName=database_name,
            Name=table_name,
            TransactionId=transaction_id,
            QueryAsOfTime=query_as_of_time,
            IncludeStatusDetails=include_status_details,
        )

        # Verify the response
        assert isinstance(result, GetTableResponse)
        assert result.isError is False
        assert result.database_name == database_name
        assert result.table_name == table_name
        assert result.operation == 'get-table'
