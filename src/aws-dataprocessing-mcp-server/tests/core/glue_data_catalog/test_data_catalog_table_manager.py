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

import json
import pytest
from awslabs.aws_dataprocessing_mcp_server.core.glue_data_catalog.data_catalog_table_manager import (
    DataCatalogTableManager,
)
from botocore.exceptions import ClientError
from datetime import datetime
from mcp.types import CallToolResult
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
            # Verify the response structure
            assert result.isError is False
            assert len(result.content) == 2
            assert (
                f'Successfully created table: {database_name}.{table_name}'
                in result.content[0].text
            )

            # Parse and verify the JSON data
            import json

            data_json = json.loads(result.content[1].text)
            assert data_json['database_name'] == database_name
            assert data_json['table_name'] == table_name
            assert data_json['operation'] == 'create-table'

    @pytest.mark.asyncio
    async def test_create_table_error(self, manager, mock_ctx, mock_glue_client):
        """Test that create_table handles errors properly when the Glue API call fails."""
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

            # Call the method and verify it returns an error result
            result = await manager.create_table(
                mock_ctx,
                database_name=database_name,
                table_name=table_name,
                table_input=table_input,
            )

            # Verify the response indicates an error
            mock_glue_client.create_table.assert_called_once()
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert f'Failed to create table {database_name}.{table_name}' in result.content[0].text
            assert 'AlreadyExistsException' in result.content[0].text

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
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_or_default_aws_region',
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

            # Verify the response structure
            assert result.isError is False
            assert len(result.content) == 2
            assert (
                f'Successfully deleted table: {database_name}.{table_name}'
                in result.content[0].text
            )

            # Parse and verify the JSON data
            import json

            data_json = json.loads(result.content[1].text)
            assert data_json['database_name'] == database_name
            assert data_json['table_name'] == table_name
            assert data_json['operation'] == 'delete-table'

    @pytest.mark.asyncio
    async def test_get_table_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_table handles datetime serialization issues correctly."""
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

        result = await manager.get_table(
            mock_ctx, database_name=database_name, table_name=table_name, catalog_id=catalog_id
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        assert 'Successfully retrieved table:' in result.content[0].text

        # Verify that the Glue client was called with the correct parameters
        mock_glue_client.get_table.assert_called_once_with(
            DatabaseName=database_name, Name=table_name, CatalogId=catalog_id
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

        # Verify the response structure
        assert result.isError is False
        assert len(result.content) == 2
        assert 'Successfully listed 2 tables in database' in result.content[0].text

        # Parse and verify the JSON data
        import json

        data_json = json.loads(result.content[1].text)
        assert data_json['database_name'] == database_name
        assert data_json['count'] == 2
        assert data_json['operation'] == 'list-tables'

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
                'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.get_or_default_aws_region',
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

            # Verify the response structure
            assert result.isError is False
            assert len(result.content) == 2
            assert (
                f'Successfully updated table: {database_name}.{table_name}'
                in result.content[0].text
            )

            # Parse and verify the JSON data
            import json

            data_json = json.loads(result.content[1].text)
            assert data_json['database_name'] == database_name
            assert data_json['table_name'] == table_name
            assert data_json['operation'] == 'update-table'

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

        # Verify the response structure
        assert result.isError is False
        assert len(result.content) == 2
        assert 'Search found 2 tables' in result.content[0].text

        # Parse and verify the JSON data
        import json

        data_json = json.loads(result.content[1].text)
        assert data_json['search_text'] == search_text
        assert data_json['count'] == 2
        assert data_json['operation'] == 'search-tables'
        assert len(data_json['tables']) == 2

    @pytest.mark.asyncio
    async def test_error_handling(self, manager, mock_ctx, mock_glue_client):
        """Test that error handling works correctly for various operations."""
        # Setup error response
        error_response = {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}

        # Test get_table error handling
        mock_glue_client.get_table.side_effect = ClientError(error_response, 'GetTable')
        result = await manager.get_table(
            mock_ctx, database_name='test-db', table_name='test-table'
        )
        assert result is not None

        # Reset side effect
        mock_glue_client.get_table.side_effect = None

        # Test list_tables error handling
        mock_glue_client.get_tables.side_effect = ClientError(error_response, 'GetTables')
        result = await manager.list_tables(mock_ctx, database_name='test-db')
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Failed to list tables in database' in result.content[0].text

        # Test search_tables error handling
        mock_glue_client.search_tables.side_effect = ClientError(error_response, 'SearchTables')
        result = await manager.search_tables(mock_ctx, search_text='test')
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert 'Failed to search tables' in result.content[0].text

    @pytest.mark.asyncio
    async def test_detect_table_format_iceberg(self, manager, mock_ctx, mock_glue_client):
        """Test that detect_table_format identifies an Iceberg table from its table_type parameter."""
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': 'iceberg-table',
                'Parameters': {'table_type': 'ICEBERG', 'metadata_location': 's3://bucket/x.json'},
                'StorageDescriptor': {},
            }
        }

        result = await manager.detect_table_format(
            mock_ctx, database_name='test-db', table_name='iceberg-table'
        )

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['table_format'] == 'ICEBERG'
        assert 'table_type' in data['detection_basis']

    @pytest.mark.asyncio
    async def test_detect_table_format_hive(self, manager, mock_ctx, mock_glue_client):
        """Test that detect_table_format identifies a Hive-style table from its SerDe info."""
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': 'hive-table',
                'Parameters': {},
                'StorageDescriptor': {
                    'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                    'SerdeInfo': {
                        'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
                    },
                },
            }
        }

        result = await manager.detect_table_format(
            mock_ctx, database_name='test-db', table_name='hive-table'
        )

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['table_format'] == 'HIVE'

    @pytest.mark.asyncio
    async def test_detect_table_format_delta_by_parameter_prefix(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that detect_table_format identifies a Delta table from delta.* parameter keys."""
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': 'delta-table',
                'Parameters': {'delta.minReaderVersion': '1'},
                'StorageDescriptor': {},
            }
        }

        result = await manager.detect_table_format(
            mock_ctx, database_name='test-db', table_name='delta-table'
        )

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['table_format'] == 'DELTA'

    @pytest.mark.asyncio
    async def test_detect_table_format_hudi_by_parameter_prefix(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that detect_table_format identifies a Hudi table from hoodie.* parameter keys."""
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': 'hudi-table',
                'Parameters': {'hoodie.table.name': 'hudi-table'},
                'StorageDescriptor': {},
            }
        }

        result = await manager.detect_table_format(
            mock_ctx, database_name='test-db', table_name='hudi-table'
        )

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['table_format'] == 'HUDI'

    @pytest.mark.asyncio
    async def test_detect_table_format_unknown(self, manager, mock_ctx, mock_glue_client):
        """Test that detect_table_format falls back to UNKNOWN when no signal is present."""
        mock_glue_client.get_table.return_value = {
            'Table': {'Name': 'mystery-table', 'Parameters': {}, 'StorageDescriptor': {}}
        }

        result = await manager.detect_table_format(
            mock_ctx, database_name='test-db', table_name='mystery-table'
        )

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['table_format'] == 'UNKNOWN'

    @pytest.mark.asyncio
    async def test_detect_table_format_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that detect_table_format returns an error for a non-existent table."""
        error_response = {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}
        mock_glue_client.get_table.side_effect = ClientError(error_response, 'GetTable')

        result = await manager.detect_table_format(
            mock_ctx, database_name='test-db', table_name='missing-table'
        )

        assert result.isError is True
        assert 'Failed to detect table format' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_iceberg_table_info_is_iceberg(self, manager, mock_ctx, mock_glue_client):
        """Test that get_iceberg_table_info surfaces metadata for an Iceberg table."""
        mock_glue_client.get_table.return_value = {
            'Table': {
                'Name': 'iceberg-table',
                'Parameters': {
                    'table_type': 'ICEBERG',
                    'metadata_location': 's3://bucket/metadata/00001.metadata.json',
                    'previous_metadata_location': 's3://bucket/metadata/00000.metadata.json',
                    'format-version': '2',
                },
                'StorageDescriptor': {},
            }
        }

        result = await manager.get_iceberg_table_info(
            mock_ctx, database_name='test-db', table_name='iceberg-table'
        )

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['is_iceberg'] is True
        assert data['metadata_location'] == 's3://bucket/metadata/00001.metadata.json'
        assert data['previous_metadata_location'] == 's3://bucket/metadata/00000.metadata.json'
        assert data['format_version'] == '2'

    @pytest.mark.asyncio
    async def test_get_iceberg_table_info_not_iceberg(self, manager, mock_ctx, mock_glue_client):
        """Test that get_iceberg_table_info reports is_iceberg=False for a non-Iceberg table, not an error."""
        mock_glue_client.get_table.return_value = {
            'Table': {'Name': 'hive-table', 'Parameters': {}, 'StorageDescriptor': {}}
        }

        result = await manager.get_iceberg_table_info(
            mock_ctx, database_name='test-db', table_name='hive-table'
        )

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['is_iceberg'] is False
        assert data['metadata_location'] is None

    @pytest.mark.asyncio
    async def test_get_iceberg_table_info_error(self, manager, mock_ctx, mock_glue_client):
        """Test that get_iceberg_table_info returns an error for a non-existent table."""
        error_response = {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}
        mock_glue_client.get_table.side_effect = ClientError(error_response, 'GetTable')

        result = await manager.get_iceberg_table_info(
            mock_ctx, database_name='test-db', table_name='missing-table'
        )

        assert result.isError is True
        assert 'Failed to get Iceberg table info' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_table_versions_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_table_versions returns a successful response with version history."""
        update_time = datetime(2023, 1, 2, 0, 0, 0)
        mock_glue_client.get_table_versions.return_value = {
            'TableVersions': [
                {
                    'Table': {'Name': 'test-table', 'UpdateTime': update_time},
                    'VersionId': '2',
                },
                {'Table': {'Name': 'test-table'}, 'VersionId': '1'},
            ],
            'NextToken': 'next-page',
        }

        result = await manager.get_table_versions(
            mock_ctx, database_name='test-db', table_name='test-table', max_results=10
        )

        mock_glue_client.get_table_versions.assert_called_once_with(
            DatabaseName='test-db', TableName='test-table', MaxResults=10
        )
        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['count'] == 2
        assert data['next_token'] == 'next-page'
        assert data['versions'][0]['version_id'] == '2'

    @pytest.mark.asyncio
    async def test_get_table_versions_empty(self, manager, mock_ctx, mock_glue_client):
        """Test that get_table_versions handles a table with no recorded version history."""
        mock_glue_client.get_table_versions.return_value = {'TableVersions': []}

        result = await manager.get_table_versions(
            mock_ctx, database_name='test-db', table_name='new-table'
        )

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['count'] == 0
        assert data['versions'] == []

    @pytest.mark.asyncio
    async def test_get_table_versions_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that get_table_versions returns an error for a non-existent table."""
        error_response = {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}
        mock_glue_client.get_table_versions.side_effect = ClientError(
            error_response, 'GetTableVersions'
        )

        result = await manager.get_table_versions(
            mock_ctx, database_name='test-db', table_name='missing-table'
        )

        assert result.isError is True
        assert 'Failed to get versions for table' in result.content[0].text

    @pytest.mark.asyncio
    async def test_batch_delete_table_version_success(self, manager, mock_ctx, mock_glue_client):
        """Test that batch_delete_table_version returns a successful response with no errors."""
        mock_glue_client.batch_delete_table_version.return_value = {'Errors': []}

        result = await manager.batch_delete_table_version(
            mock_ctx,
            database_name='test-db',
            table_name='test-table',
            version_ids=['1', '2'],
        )

        mock_glue_client.batch_delete_table_version.assert_called_once_with(
            DatabaseName='test-db', TableName='test-table', VersionIds=['1', '2']
        )
        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['version_ids'] == ['1', '2']
        assert data['errors'] == []

    @pytest.mark.asyncio
    async def test_batch_delete_table_version_partial_errors(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that batch_delete_table_version surfaces per-version errors without failing the whole call."""
        mock_glue_client.batch_delete_table_version.return_value = {
            'Errors': [
                {
                    'VersionId': '1',
                    'ErrorDetail': {'ErrorCode': 'EntityNotFoundException', 'ErrorMessage': 'x'},
                }
            ]
        }

        result = await manager.batch_delete_table_version(
            mock_ctx,
            database_name='test-db',
            table_name='test-table',
            version_ids=['1', '2'],
        )

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert len(data['errors']) == 1
        assert data['errors'][0]['VersionId'] == '1'

    @pytest.mark.asyncio
    async def test_batch_delete_table_version_error(self, manager, mock_ctx, mock_glue_client):
        """Test that batch_delete_table_version returns an error when the Glue API call fails."""
        error_response = {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}
        mock_glue_client.batch_delete_table_version.side_effect = ClientError(
            error_response, 'BatchDeleteTableVersion'
        )

        result = await manager.batch_delete_table_version(
            mock_ctx,
            database_name='test-db',
            table_name='missing-table',
            version_ids=['1'],
        )

        assert result.isError is True
        assert 'Failed to batch delete versions for table' in result.content[0].text
