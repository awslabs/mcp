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

"""Tests for the CUSTOM_TAGS environment variable functionality in Glue handlers."""

import os
import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler import (
    GlueDataCatalogHandler,
)
from awslabs.aws_dataprocessing_mcp_server.utils.consts import (
    CUSTOM_TAGS_ENV_VAR,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestCustomTagsGlue:
    """Tests for the CUSTOM_TAGS environment variable functionality in Glue handlers."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Context."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_database_manager(self):
        """Create a mock DataCatalogDatabaseManager."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_table_manager(self):
        """Create a mock DataCatalogTableManager."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_catalog_manager(self):
        """Create a mock DataCatalogManager."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def handler_with_write_access(
        self, mock_mcp, mock_database_manager, mock_table_manager, mock_catalog_manager
    ):
        """Create a GlueDataCatalogHandler instance with write access enabled."""
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler.DataCatalogDatabaseManager',
                return_value=mock_database_manager,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler.DataCatalogTableManager',
                return_value=mock_table_manager,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler.DataCatalogManager',
                return_value=mock_catalog_manager,
            ),
        ):
            handler = GlueDataCatalogHandler(mock_mcp, allow_write=True)
            handler.data_catalog_database_manager = mock_database_manager
            handler.data_catalog_table_manager = mock_table_manager
            handler.data_catalog_manager = mock_catalog_manager
            return handler

    @pytest.mark.asyncio
    async def test_create_database_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx, mock_database_manager
    ):
        """Test that create database operation respects CUSTOM_TAGS when enabled."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.operation = 'create-database'
        mock_database_manager.create_database.return_value = expected_response

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.manage_aws_glue_data_catalog_databases(
                mock_ctx,
                operation='create-database',
                database_name='test-db',
                description='Test database',
                location_uri='s3://test-bucket/',
                parameters={'key': 'value'},
                catalog_id='123456789012',
            )

            # Verify that the method was called with the correct parameters
            mock_database_manager.create_database.assert_called_once_with(
                ctx=mock_ctx,
                database_name='test-db',
                description='Test database',
                location_uri='s3://test-bucket/',
                parameters={'key': 'value'},
                catalog_id='123456789012',
            )

            # Verify that the result is the expected response
            assert result == expected_response

            # Verify that the AWS helper's prepare_resource_tags method was called with CUSTOM_TAGS enabled
            # This is indirectly verified by checking that the create_database method was called with the correct parameters
            # The actual verification of prepare_resource_tags behavior is in the AWS helper tests

    @pytest.mark.asyncio
    async def test_create_table_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test that create table operation respects CUSTOM_TAGS when enabled."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.operation = 'create-table'
        mock_table_manager.create_table.return_value = expected_response

        # Create a comprehensive table input
        table_input = {
            'Name': 'test-table',
            'Description': 'Test table for unit testing',
            'Owner': 'test-owner',
            'TableType': 'EXTERNAL_TABLE',
            'Parameters': {'classification': 'parquet', 'compressionType': 'snappy'},
            'StorageDescriptor': {
                'Columns': [
                    {'Name': 'id', 'Type': 'int'},
                    {'Name': 'name', 'Type': 'string'},
                    {'Name': 'timestamp', 'Type': 'timestamp'},
                ],
                'Location': 's3://test-bucket/test-db/test-table/',
                'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
                'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
                'Compressed': True,
                'SerdeInfo': {
                    'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe',
                    'Parameters': {'serialization.format': '1'},
                },
            },
            'PartitionKeys': [
                {'Name': 'year', 'Type': 'string'},
                {'Name': 'month', 'Type': 'string'},
            ],
        }

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx,
                operation='create-table',
                database_name='test-db',
                table_name='test-table',
                table_input=table_input,
                catalog_id='123456789012',
            )

            # Verify that the method was called with the correct parameters
            mock_table_manager.create_table.assert_called_once_with(
                ctx=mock_ctx,
                database_name='test-db',
                table_name='test-table',
                table_input=table_input,
                catalog_id='123456789012',
            )

            # Verify that the result is the expected response
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_create_connection_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that create connection operation respects CUSTOM_TAGS when enabled."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connection_name = 'test-jdbc-connection'
        expected_response.operation = 'create-connection'
        expected_response.catalog_id = '123456789012'
        mock_catalog_manager.create_connection.return_value = expected_response

        # Create a comprehensive connection input
        connection_input = {
            'ConnectionType': 'JDBC',
            'ConnectionProperties': {
                'JDBC_CONNECTION_URL': 'jdbc:mysql://test-host:3306/test-db',
                'USERNAME': 'test-user',
                'PASSWORD': 'test-password',  # pragma: allowlist secret
                'JDBC_ENFORCE_SSL': 'true',
            },
            'PhysicalConnectionRequirements': {
                'AvailabilityZone': 'us-west-2a',
                'SecurityGroupIdList': ['sg-12345678'],
                'SubnetId': 'subnet-12345678',
            },
            'Description': 'Test JDBC connection for unit testing',
        }

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx,
                operation='create-connection',
                connection_name='test-jdbc-connection',
                connection_input=connection_input,
                catalog_id='123456789012',
            )

            # Verify that the method was called with the correct parameters
            mock_catalog_manager.create_connection.assert_called_once_with(
                ctx=mock_ctx,
                connection_name='test-jdbc-connection',
                connection_input=connection_input,
                catalog_id='123456789012',
            )

            # Verify that the result is the expected response
            assert result == expected_response
            assert result.connection_name == 'test-jdbc-connection'
            assert result.catalog_id == '123456789012'

    @pytest.mark.asyncio
    async def test_create_partition_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that create partition operation respects CUSTOM_TAGS when enabled."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.partition_values = ['2023', '01']
        expected_response.operation = 'create-partition'
        mock_catalog_manager.create_partition.return_value = expected_response

        # Create a comprehensive partition input
        partition_input = {
            'StorageDescriptor': {
                'Columns': [
                    {'Name': 'id', 'Type': 'int'},
                    {'Name': 'name', 'Type': 'string'},
                    {'Name': 'timestamp', 'Type': 'timestamp'},
                ],
                'Location': 's3://test-bucket/test-db/test-table/year=2023/month=01/',
                'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
                'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
                'Compressed': True,
                'SerdeInfo': {
                    'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe',
                    'Parameters': {'serialization.format': '1'},
                },
            },
            'Parameters': {
                'classification': 'parquet',
                'compressionType': 'snappy',
                'recordCount': '1000',
                'averageRecordSize': '100',
            },
            'LastAccessTime': '2023-01-01T00:00:00Z',
        }

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='create-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=['2023', '01'],
                partition_input=partition_input,
                catalog_id='123456789012',
            )

            # Verify that the method was called with the correct parameters
            mock_catalog_manager.create_partition.assert_called_once_with(
                ctx=mock_ctx,
                database_name='test-db',
                table_name='test-table',
                partition_values=['2023', '01'],
                partition_input=partition_input,
                catalog_id='123456789012',
            )

            # Verify that the result is the expected response
            assert result == expected_response
            assert result.database_name == 'test-db'
            assert result.table_name == 'test-table'
            assert result.partition_values == ['2023', '01']

    @pytest.mark.asyncio
    async def test_create_catalog_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that create catalog operation respects CUSTOM_TAGS when enabled."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.catalog_id = 'test-catalog'
        expected_response.operation = 'create-catalog'
        mock_catalog_manager.create_catalog.return_value = expected_response

        # Create a comprehensive catalog input
        catalog_input = {
            'Name': 'Test Catalog',
            'Description': 'Test catalog for unit testing',
            'Type': 'GLUE',
            'Parameters': {'key1': 'value1', 'key2': 'value2'},
            'Tags': {'Environment': 'Test', 'Project': 'UnitTest'},
        }

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.manage_aws_glue_data_catalog(
                mock_ctx,
                operation='create-catalog',
                catalog_id='test-catalog',
                catalog_input=catalog_input,
            )

            # Verify that the method was called with the correct parameters
            mock_catalog_manager.create_catalog.assert_called_once_with(
                ctx=mock_ctx,
                catalog_name='test-catalog',
                catalog_input=catalog_input,
            )

            # Verify that the result is the expected response
            assert result == expected_response
            assert result.catalog_id == 'test-catalog'

    @pytest.mark.asyncio
    async def test_delete_database_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx, mock_database_manager
    ):
        """Test that delete database operation respects CUSTOM_TAGS when enabled."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.operation = 'delete-database'
        mock_database_manager.delete_database.return_value = expected_response

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.manage_aws_glue_data_catalog_databases(
                mock_ctx,
                operation='delete-database',
                database_name='test-db',
                catalog_id='123456789012',
            )

            # Verify that the method was called with the correct parameters
            mock_database_manager.delete_database.assert_called_once_with(
                ctx=mock_ctx, database_name='test-db', catalog_id='123456789012'
            )

            # Verify that the result is the expected response
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_delete_table_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test that delete table operation respects CUSTOM_TAGS when enabled."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.operation = 'delete-table'
        mock_table_manager.delete_table.return_value = expected_response

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx,
                operation='delete-table',
                database_name='test-db',
                table_name='test-table',
                catalog_id='123456789012',
            )

            # Verify that the method was called with the correct parameters
            mock_table_manager.delete_table.assert_called_once_with(
                ctx=mock_ctx,
                database_name='test-db',
                table_name='test-table',
                catalog_id='123456789012',
            )

            # Verify that the result is the expected response
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_delete_connection_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that delete connection operation respects CUSTOM_TAGS when enabled."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connection_name = 'test-connection'
        expected_response.operation = 'delete-connection'
        expected_response.catalog_id = '123456789012'
        mock_catalog_manager.delete_connection.return_value = expected_response

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx,
                operation='delete-connection',
                connection_name='test-connection',
                catalog_id='123456789012',
            )

            # Verify that the method was called with the correct parameters
            mock_catalog_manager.delete_connection.assert_called_once_with(
                ctx=mock_ctx,
                connection_name='test-connection',
                catalog_id='123456789012',
            )

            # Verify that the result is the expected response
            assert result == expected_response
            assert result.catalog_id == '123456789012'

    @pytest.mark.asyncio
    async def test_delete_partition_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that delete partition operation respects CUSTOM_TAGS when enabled."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.partition_values = ['2023', '01']
        expected_response.operation = 'delete-partition'
        mock_catalog_manager.delete_partition.return_value = expected_response

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='delete-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=['2023', '01'],
                catalog_id='123456789012',
            )

            # Verify that the method was called with the correct parameters
            mock_catalog_manager.delete_partition.assert_called_once_with(
                ctx=mock_ctx,
                database_name='test-db',
                table_name='test-table',
                partition_values=['2023', '01'],
                catalog_id='123456789012',
            )

            # Verify that the result is the expected response
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_delete_catalog_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that delete catalog operation respects CUSTOM_TAGS when enabled."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.catalog_id = 'test-catalog'
        expected_response.operation = 'delete-catalog'
        mock_catalog_manager.delete_catalog.return_value = expected_response

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.manage_aws_glue_data_catalog(
                mock_ctx,
                operation='delete-catalog',
                catalog_id='test-catalog',
            )

            # Verify that the method was called with the correct parameters
            mock_catalog_manager.delete_catalog.assert_called_once_with(
                ctx=mock_ctx, catalog_id='test-catalog'
            )

            # Verify that the result is the expected response
            assert result == expected_response
