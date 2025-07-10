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

"""Tests for the Glue Data Catalog Handler."""

import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler import (
    GlueDataCatalogHandler,
)
from unittest.mock import ANY, AsyncMock, MagicMock, patch


class TestGlueDataCatalogHandler:
    """Tests for the GlueDataCatalogHandler class."""

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
    def handler(self, mock_mcp, mock_database_manager, mock_table_manager, mock_catalog_manager):
        """Create a GlueDataCatalogHandler instance with mocked dependencies."""
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
            handler = GlueDataCatalogHandler(mock_mcp)
            handler.data_catalog_database_manager = mock_database_manager
            handler.data_catalog_table_manager = mock_table_manager
            handler.data_catalog_manager = mock_catalog_manager
            return handler

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

    def test_initialization(self, mock_mcp):
        """Test that the handler is initialized correctly."""
        # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=MagicMock(),
        ):
            handler = GlueDataCatalogHandler(mock_mcp)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.allow_write is False
            assert handler.allow_sensitive_data_access is False

            # Verify that the tools were registered
            assert mock_mcp.tool.call_count == 5

            # Get all call args
            call_args_list = mock_mcp.tool.call_args_list

            # Get all tool names that were registered
            tool_names = [call_args[1]['name'] for call_args in call_args_list]

            # Verify that expected tools are registered
            assert 'manage_aws_glue_databases' in tool_names
            assert 'manage_aws_glue_tables' in tool_names
            assert 'manage_aws_glue_connections' in tool_names
            assert 'manage_aws_glue_partitions' in tool_names
            assert 'manage_aws_glue_catalog' in tool_names

    def test_initialization_with_write_access(self, mock_mcp):
        """Test that the handler is initialized correctly with write access."""
        # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=MagicMock(),
        ):
            handler = GlueDataCatalogHandler(mock_mcp, allow_write=True)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.allow_write is True
            assert handler.allow_sensitive_data_access is False

    def test_initialization_with_sensitive_data_access(self, mock_mcp):
        """Test that the handler is initialized correctly with sensitive data access."""
        # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=MagicMock(),
        ):
            handler = GlueDataCatalogHandler(mock_mcp, allow_sensitive_data_access=True)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.allow_write is False
            assert handler.allow_sensitive_data_access is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_create_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that create database operation is not allowed without write access."""
        # Mock the response class
        mock_response = MagicMock()
        mock_response.isError = True
        mock_response.content = [MagicMock()]
        mock_response.content[
            0
        ].text = 'Operation create-database is not allowed without write access'
        mock_response.database_name = ''
        mock_response.operation = 'create'

        # Patch the CreateDatabaseResponse class
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.models.data_catalog_models.CreateDatabaseResponse',
            return_value=mock_response,
        ):
            # Call the method with a write operation
            result = await handler.manage_aws_glue_data_catalog_databases(
                mock_ctx, operation='create-database', database_name='test-db'
            )

            # Verify the result
            assert result.isError is True
            assert 'not allowed without write access' in result.content[0].text
            assert result.database_name == ''
            assert result.operation == 'create-database'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_delete_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that delete database operation is not allowed without write access."""
        # Mock the response class
        mock_response = MagicMock()
        mock_response.isError = True
        mock_response.content = [MagicMock()]
        mock_response.content[
            0
        ].text = 'Operation delete-database is not allowed without write access'
        mock_response.database_name = ''
        mock_response.operation = 'delete'

        # Patch the DeleteDatabaseResponse class
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.models.data_catalog_models.DeleteDatabaseResponse',
            return_value=mock_response,
        ):
            # Call the method with a write operation
            result = await handler.manage_aws_glue_data_catalog_databases(
                mock_ctx, operation='delete-database', database_name='test-db'
            )

            # Verify the result
            assert result.isError is True
            assert 'not allowed without write access' in result.content[0].text
            assert result.database_name == ''
            assert result.operation == 'delete-database'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_update_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that update database operation is not allowed without write access."""
        # Mock the response class
        mock_response = MagicMock()
        mock_response.isError = True
        mock_response.content = [MagicMock()]
        mock_response.content[
            0
        ].text = 'Operation update-database is not allowed without write access'
        mock_response.database_name = ''
        mock_response.operation = 'update'

        # Patch the UpdateDatabaseResponse class
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.models.data_catalog_models.UpdateDatabaseResponse',
            return_value=mock_response,
        ):
            # Call the method with a write operation
            result = await handler.manage_aws_glue_data_catalog_databases(
                mock_ctx, operation='update-database', database_name='test-db'
            )

            # Verify the result
            assert result.isError is True
            assert 'not allowed without write access' in result.content[0].text
            assert result.database_name == ''
            assert result.operation == 'update-database'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_get_read_access(
        self, handler, mock_ctx, mock_database_manager
    ):
        """Test that get database operation is allowed with read access."""
        from unittest.mock import ANY

        # Mock the response class
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.database_name = 'test-db'
        mock_response.description = 'Test database'
        mock_response.location_uri = 's3://test-bucket/'
        mock_response.parameters = {}
        mock_response.creation_time = '2023-01-01T00:00:00Z'
        mock_response.operation = 'get'
        mock_response.catalog_id = '123456789012'

        # Setup the mock to return a response
        mock_database_manager.get_database.return_value = mock_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog_databases(
            mock_ctx, operation='get-database', database_name='test-db'
        )

        # Verify that the method was called with the correct parameters
        # Use ANY for catalog_id to handle the FieldInfo object
        mock_database_manager.get_database.assert_called_once_with(
            ctx=mock_ctx, database_name='test-db', catalog_id=ANY
        )

        # Verify that the result is the expected response
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_get_missing_database_name(
        self, handler, mock_ctx, mock_database_manager
    ):
        """Test that get database operation is allowed with read access."""
        with pytest.raises(ValueError) as e:
            await handler.manage_aws_glue_data_catalog_databases(
                mock_ctx, operation='get-database', database_name=None
            )
        assert 'database_name is required' in str(e.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_list_read_access(
        self, handler, mock_ctx, mock_database_manager
    ):
        """Test that list databases operation is allowed with read access."""
        from unittest.mock import ANY

        # Mock the response class
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.databases = []
        mock_response.count = 0
        mock_response.catalog_id = '123456789012'
        mock_response.operation = 'list'

        # Setup the mock to return a response
        mock_database_manager.list_databases.return_value = mock_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog_databases(
            mock_ctx, operation='list-databases'
        )

        # Verify that the method was called with the correct parameters
        # Use ANY for catalog_id to handle the FieldInfo object
        mock_database_manager.list_databases.assert_called_once_with(
            ctx=mock_ctx, catalog_id=ANY, max_results=ANY, next_token=ANY
        )

        # Verify that the result is the expected response
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_create_with_write_access(
        self, handler_with_write_access, mock_ctx, mock_database_manager
    ):
        """Test that create database operation is allowed with write access."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.operation = 'create'
        mock_database_manager.create_database.return_value = expected_response

        # Call the method with a write operation
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

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_delete_with_write_access(
        self, handler_with_write_access, mock_ctx, mock_database_manager
    ):
        """Test that delete database operation is allowed with write access."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.operation = 'delete'
        mock_database_manager.delete_database.return_value = expected_response

        # Call the method with a write operation
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
    async def test_manage_aws_glue_data_catalog_databases_delete_missing_database_name(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that delete database operation with missing database name."""
        with pytest.raises(ValueError) as e:
            await handler_with_write_access.manage_aws_glue_data_catalog_databases(
                mock_ctx, operation='delete-database', database_name=None
            )
        assert 'database_name is required' in str(e.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_update_missing_database_name(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that get database operation with write access."""
        with pytest.raises(ValueError) as e:
            await handler_with_write_access.manage_aws_glue_data_catalog_databases(
                mock_ctx, operation='update-database', database_name=None
            )
        assert 'database_name is required' in str(e.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_update_with_read_access(
        self, handler, mock_ctx
    ):
        """Test that updadte database operation with read access."""
        result = await handler.manage_aws_glue_data_catalog_databases(
            mock_ctx, operation='update-database', database_name=None
        )
        assert result.isError is True
        assert len(result.content) == 1
        assert 'is not allowed without write access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_update_with_write_access(
        self, handler_with_write_access, mock_ctx, mock_database_manager
    ):
        """Test that update database operation is allowed with write access."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.operation = 'update'
        mock_database_manager.update_database.return_value = expected_response

        # Call the method with a write operation
        result = await handler_with_write_access.manage_aws_glue_data_catalog_databases(
            mock_ctx,
            operation='update-database',
            database_name='test-db',
            description='Updated database',
            location_uri='s3://updated-bucket/',
            parameters={'key': 'updated-value'},
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_database_manager.update_database.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            description='Updated database',
            location_uri='s3://updated-bucket/',
            parameters={'key': 'updated-value'},
            catalog_id='123456789012',
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_invalid_operation(
        self, handler, mock_ctx
    ):
        """Test that an invalid operation returns an error response."""
        # Set write access to true to bypass the "not allowed without write access" check
        handler.allow_write = True

        # Call the method with an invalid operation
        result = await handler.manage_aws_glue_data_catalog_databases(
            mock_ctx, operation='invalid-operation', database_name='test-db'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text
        assert result.database_name == ''
        assert result.operation == 'get-database'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_missing_database_name(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing database_name parameter raises a ValueError."""
        # Call the method without database_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_databases(
                mock_ctx, operation='create-database', database_name=None
            )

        # Verify that the correct error message is raised
        assert 'database_name is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_exception_handling(
        self, handler, mock_ctx, mock_database_manager
    ):
        """Test that exceptions are handled correctly."""
        # Setup the mock to raise an exception
        mock_database_manager.get_database.side_effect = Exception('Test exception')

        # Patch the handler's method to handle the exception properly
        with patch.object(
            handler,
            'manage_aws_glue_data_catalog_databases',
            side_effect=handler.manage_aws_glue_data_catalog_databases,
        ):
            # Create a mock response for the GetDatabaseResponse
            mock_response = MagicMock()
            mock_response.isError = True
            mock_response.content = [MagicMock()]
            mock_response.content[
                0
            ].text = 'Error in manage_aws_glue_data_catalog_databases: Test exception'
            mock_response.database_name = 'test-db'
            mock_response.operation = 'get'

            # Patch the GetDatabaseResponse class
            with patch(
                'awslabs.aws_dataprocessing_mcp_server.models.data_catalog_models.GetDatabaseResponse',
                return_value=mock_response,
            ):
                # Call the method
                result = await handler.manage_aws_glue_data_catalog_databases(
                    mock_ctx, operation='get-database', database_name='test-db'
                )

                # Verify that the result is an error response
                assert result.isError is True
                assert (
                    'Error in manage_aws_glue_data_catalog_databases: Test exception'
                    in result.content[0].text
                )
                assert result.database_name == 'test-db'
                assert result.operation == 'get-database'

    # Tests for manage_aws_glue_data_catalog_tables method

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_create_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that create table operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='create-table',
            database_name='test-db',
            table_name='test-table',
            table_input={},
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.database_name == 'test-db'
        assert result.table_name == ''
        assert result.operation == 'create-table'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_get_read_access(
        self, handler, mock_ctx, mock_table_manager
    ):
        """Test that get table operation is allowed with read access."""
        from unittest.mock import ANY

        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.table_definition = {}
        expected_response.creation_time = '2023-01-01T00:00:00Z'
        expected_response.last_access_time = '2023-01-01T00:00:00Z'
        expected_response.operation = 'get'
        mock_table_manager.get_table.return_value = expected_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx, operation='get-table', database_name='test-db', table_name='test-table'
        )

        # Verify that the method was called with the correct parameters
        # Use ANY for catalog_id to handle the FieldInfo object
        mock_table_manager.get_table.assert_called_once_with(
            ctx=mock_ctx, database_name='test-db', table_name='test-table', catalog_id=ANY
        )

        # Verify that the result is the expected response
        assert result == expected_response

    # Tests for manage_aws_glue_data_catalog_connections method

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_create_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that create connection operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='create-connection',
            connection_name='test-connection',
            connection_input={},
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.connection_name == ''
        assert result.operation == 'create-connection'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_get_read_access(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test that get connection operation is allowed with read access."""
        from unittest.mock import ANY

        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connection_name = 'test-connection'
        expected_response.connection_type = 'JDBC'
        expected_response.connection_properties = {}
        expected_response.physical_connection_requirements = None
        expected_response.creation_time = '2023-01-01T00:00:00Z'
        expected_response.last_updated_time = '2023-01-01T00:00:00Z'
        expected_response.last_updated_by = ''
        expected_response.status = ''
        expected_response.status_reason = ''
        expected_response.last_connection_validation_time = ''
        expected_response.catalog_id = ''
        expected_response.operation = 'get'
        mock_catalog_manager.get_connection.return_value = expected_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx, operation='get-connection', connection_name='test-connection'
        )

        # Verify that the method was called with the correct parameters
        # Use ANY for catalog_id to handle the FieldInfo object
        mock_catalog_manager.get_connection.assert_called_once_with(
            ctx=mock_ctx, connection_name='test-connection', catalog_id=ANY, hide_password=ANY
        )

        # Verify that the result is the expected response
        assert result == expected_response

    # Tests for manage_aws_glue_data_catalog_partitions method

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_create_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that create partition operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='create-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
            partition_input={},
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        assert result.partition_values == []
        assert result.operation == 'create-partition'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_get_read_access(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test that get partition operation is allowed with read access."""
        from unittest.mock import ANY

        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.partition_values = ['2023']
        expected_response.partition_definition = {}
        expected_response.creation_time = '2023-01-01T00:00:00Z'
        expected_response.last_access_time = '2023-01-01T00:00:00Z'
        expected_response.operation = 'get'
        mock_catalog_manager.get_partition.return_value = expected_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='get-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
        )

        # Verify that the method was called with the correct parameters
        # Use ANY for catalog_id to handle the FieldInfo object
        mock_catalog_manager.get_partition.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
            catalog_id=ANY,
        )

        # Verify that the result is the expected response
        assert result == expected_response

    # Tests for manage_aws_glue_data_catalog method

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_create_no_write_access(self, handler, mock_ctx):
        """Test that create catalog operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx, operation='create-catalog', catalog_id='test-catalog', catalog_input={}
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.catalog_id == ''
        assert result.operation == 'create-catalog'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_get_read_access(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test that get catalog operation is allowed with read access."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.catalog_id = 'test-catalog'
        expected_response.catalog_definition = {}
        expected_response.name = 'Test Catalog'
        expected_response.description = 'Test catalog description'
        expected_response.create_time = '2023-01-01T00:00:00Z'
        expected_response.update_time = '2023-01-01T00:00:00Z'
        expected_response.operation = 'get'
        mock_catalog_manager.get_catalog.return_value = expected_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx, operation='get-catalog', catalog_id='test-catalog'
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.get_catalog.assert_called_once_with(
            ctx=mock_ctx, catalog_id='test-catalog'
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_create_with_write_access(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that create catalog operation is allowed with write access."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.catalog_id = 'test-catalog'
        expected_response.operation = 'create-catalog'
        mock_catalog_manager.create_catalog.return_value = expected_response

        # Call the method with a write operation
        result = await handler_with_write_access.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='create-catalog',
            catalog_id='test-catalog',
            catalog_input={'Description': 'Test catalog', 'Type': 'GLUE'},
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.create_catalog.assert_called_once_with(
            ctx=mock_ctx,
            catalog_name='test-catalog',
            catalog_input={'Description': 'Test catalog', 'Type': 'GLUE'},
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_delete_with_write_access(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that delete catalog operation is allowed with write access."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.catalog_id = 'test-catalog'
        expected_response.operation = 'delete-catalog'
        mock_catalog_manager.delete_catalog.return_value = expected_response

        # Call the method with a write operation
        result = await handler_with_write_access.manage_aws_glue_data_catalog(
            mock_ctx, operation='delete-catalog', catalog_id='test-catalog'
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.delete_catalog.assert_called_once_with(
            ctx=mock_ctx, catalog_id='test-catalog'
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_invalid_operation(self, handler, mock_ctx):
        """Test that an invalid operation returns an error response."""
        # Set write access to true to bypass the "not allowed without write access" check
        handler.allow_write = True

        # Call the method with an invalid operation
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx, operation='invalid-operation', catalog_id='test-catalog'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text
        assert result.catalog_id == ''
        assert result.operation == 'get-catalog'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_list_catalogs(self, handler, mock_ctx):
        """Test that list_catalogs operation returns a not implemented error."""
        # Call the method with list-catalogs operation
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.catalogs = []
        mock_response.count = 0
        mock_response.catalog_id = '123456789012'
        mock_response.operation = 'list-catalogs'
        handler.data_catalog_manager.list_catalogs.return_value = mock_response
        result = await handler.manage_aws_glue_data_catalog(mock_ctx, operation='list-catalogs')

        assert result.isError is False
        assert result.operation == 'list-catalogs'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_list_catalogs_error(self, handler, mock_ctx):
        """Test that list_catalogs operation returns a not implemented error."""
        with patch.object(
            handler.data_catalog_manager,
            'list_catalogs',
            side_effect=Exception('Invalid next_token provided'),
        ):
            with pytest.raises(Exception) as e:
                result = await handler.manage_aws_glue_data_catalog(
                    mock_ctx, operation='list-catalogs'
                )

                assert result.isError is False
                assert result.operation == 'list-catalogs'
                assert 'Invalid next_token provided' in str(e)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_import_catalog_with_read_only_access(
        self, handler, mock_ctx
    ):
        """Test that import_catalog_to_glue operation returns a not implemented error."""
        # Call the method with import-catalog-to-glue operation
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='import-catalog-to-glue',
            catalog_id='test-catalog',
        )

        assert result.isError is True
        assert result.operation == 'import-catalog-to-glue'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_import_catalog(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that import_catalog_to_glue operation returns a not implemented error."""
        # Call the method with import-catalog-to-glue operation
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.catalog_id = '123456789012'
        mock_response.operation = 'import-catalog-to-glue'
        handler_with_write_access.data_catalog_manager.import_catalog_to_glue.return_value = (
            mock_response
        )
        result = await handler_with_write_access.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='import-catalog-to-glue',
            catalog_id='test-catalog',
        )

        assert result.isError is False
        assert result.operation == 'import-catalog-to-glue'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_missing_catalog_id(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing catalog_id parameter causes an error."""
        # Mock the error response
        error_response = MagicMock()
        error_response.isError = True
        error_response.catalog_id = ''
        error_response.operation = 'create-catalog'

        # Mock the create_catalog method to return the error response
        handler_with_write_access.data_catalog_manager.create_catalog.return_value = error_response

        # Call the method without catalog_id
        result = await handler_with_write_access.manage_aws_glue_data_catalog(
            mock_ctx, operation='create-catalog', catalog_input={}
        )

        # Verify that the result is the expected error response
        assert result == error_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_exception_handling(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test that exceptions are handled correctly in manage_aws_glue_data_catalog."""
        # Setup the mock to raise an exception
        mock_catalog_manager.get_catalog.side_effect = Exception('Test exception')

        # Call the method
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx, operation='get-catalog', catalog_id='test-catalog'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Error in manage_aws_glue_data_catalog' in result.content[0].text
        assert 'Test exception' in result.content[0].text
        assert result.catalog_id == 'test-catalog'
        assert result.operation == 'get-catalog'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_list_tables_error(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test that list_tables handles errors correctly."""
        # Setup the mock to raise an exception
        mock_table_manager.list_tables.side_effect = Exception('Test exception')

        # Call the method
        result = await handler_with_write_access.manage_aws_glue_data_catalog_tables(
            mock_ctx, operation='list-tables', database_name='test-db'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert any(
            'Error in manage_aws_glue_data_catalog_tables: Test exception' in content.text
            for content in result.content
        )
        assert result.database_name == 'test-db'
        assert result.table_name == ''  # Empty string for table_name in error responses
        assert result.operation == 'get-table'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_search_tables_error(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test that search_tables handles errors correctly."""
        # Setup the mock to raise an exception
        mock_table_manager.search_tables.side_effect = Exception('Test exception')

        # Call the method
        result = await handler_with_write_access.manage_aws_glue_data_catalog_tables(
            mock_ctx, operation='search-tables', database_name='test-db', search_text='test'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert any(
            'Error in manage_aws_glue_data_catalog_tables: Test exception' in content.text
            for content in result.content
        )
        assert result.database_name == 'test-db'
        assert result.table_name == ''  # Empty string for table_name in error responses
        assert result.operation == 'get-table'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_missing_table_name(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing table_name parameter causes an error."""
        # Call the method without table_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx, operation='get-table', database_name='test-db', table_name=None
            )

        # Verify that the correct error message is raised
        assert 'table_name is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_list_connections_error(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that list_connections handles errors correctly."""
        # Setup the mock to raise an exception
        mock_catalog_manager.list_connections.side_effect = Exception('Test exception')

        # Call the method
        result = await handler_with_write_access.manage_aws_glue_data_catalog_connections(
            mock_ctx, operation='list-connections'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert any(
            'Error in manage_aws_glue_data_catalog_connections: Test exception' in content.text
            for content in result.content
        )
        assert result.connection_name == ''  # Empty string for connection_name in error responses
        assert result.catalog_id == ''  # Empty string for catalog_id in error responses
        assert result.operation == 'get-connection'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_missing_connection_name(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing connection_name parameter causes an error."""
        # Mock the ValueError that should be raised
        with patch.object(
            handler_with_write_access.data_catalog_manager,
            'get_connection',
            side_effect=ValueError('connection_name is required for get operation'),
        ):
            # Call the method without connection_name
            with pytest.raises(ValueError) as excinfo:
                await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                    mock_ctx, operation='get-connection'
                )

            # Verify that the correct error message is raised
            assert 'connection_name is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_list_partitions_error(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that list_partitions handles errors correctly."""
        # Setup the mock to raise an exception
        mock_catalog_manager.list_partitions.side_effect = Exception('Test exception')

        # Call the method
        result = await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
            mock_ctx, operation='list-partitions', database_name='test-db', table_name='test-table'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert any(
            'Error in manage_aws_glue_data_catalog_partitions: Test exception' in content.text
            for content in result.content
        )
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        assert result.partition_values == []  # Empty list for partition_values in error responses
        assert result.operation == 'get-partition'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_missing_partition_values(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing partition_values parameter causes an error."""
        # Mock the ValueError that should be raised
        with patch.object(
            handler_with_write_access.data_catalog_manager,
            'get_partition',
            side_effect=ValueError('partition_values is required for get-partition operation'),
        ):
            # Call the method without partition_values
            with pytest.raises(ValueError) as excinfo:
                await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                    mock_ctx,
                    operation='get-partition',
                    database_name='test-db',
                    table_name='test-table',
                )

            # Verify that the correct error message is raised
            assert 'partition_values is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_delete_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that delete table operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='delete-table',
            database_name='test-db',
            table_name='test-table',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.database_name == 'test-db'
        assert result.table_name == ''
        assert result.operation == 'delete-table'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_delete_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that delete connection operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx, operation='delete-connection', connection_name='test-connection'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.connection_name == ''
        assert result.operation == 'delete-connection'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_update_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that update connection operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='update-connection',
            connection_name='test-connection',
            connection_input={},
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.connection_name == ''
        assert result.operation == 'update-connection'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_delete_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that delete partition operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='delete-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        assert result.partition_values == []
        assert result.operation == 'delete-partition'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_update_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that update partition operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='update-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
            partition_input={},
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        assert result.partition_values == []
        assert result.operation == 'update-partition'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_delete_no_write_access(self, handler, mock_ctx):
        """Test that delete catalog operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx, operation='delete-catalog', catalog_id='test-catalog'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.catalog_id == ''
        assert result.operation == 'delete-catalog'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_with_all_parameters(
        self, handler_with_write_access, mock_ctx, mock_database_manager
    ):
        """Test that all parameters are passed correctly to the database manager."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.operation = 'create'
        mock_database_manager.create_database.return_value = expected_response

        # Call the method with all parameters
        result = await handler_with_write_access.manage_aws_glue_data_catalog_databases(
            mock_ctx,
            operation='create-database',
            database_name='test-db',
            description='Test database',
            location_uri='s3://test-bucket/',
            parameters={'key1': 'value1', 'key2': 'value2'},
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_database_manager.create_database.assert_called_once()
        assert mock_database_manager.create_database.call_args[1]['database_name'] == 'test-db'
        assert mock_database_manager.create_database.call_args[1]['description'] == 'Test database'
        assert (
            mock_database_manager.create_database.call_args[1]['location_uri']
            == 's3://test-bucket/'
        )
        assert mock_database_manager.create_database.call_args[1]['parameters'] == {
            'key1': 'value1',
            'key2': 'value2',
        }
        assert mock_database_manager.create_database.call_args[1]['catalog_id'] == '123456789012'

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_with_short_operation_names(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test that short operation names (create, delete, etc.) work correctly for tables."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.operation = 'create-table'
        mock_table_manager.create_table.return_value = expected_response

        # Call the method with a short operation name
        result = await handler_with_write_access.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='create-table',  # Short form of 'create-table'
            database_name='test-db',
            table_name='test-table',
            table_input={'Name': 'test-table'},
        )

        # Verify that the method was called with the correct parameters
        mock_table_manager.create_table.assert_called_once()
        assert mock_table_manager.create_table.call_args[1]['database_name'] == 'test-db'
        assert mock_table_manager.create_table.call_args[1]['table_name'] == 'test-table'
        assert mock_table_manager.create_table.call_args[1]['table_input'] == {
            'Name': 'test-table'
        }

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_search_with_short_operation_name(
        self, handler, mock_ctx, mock_table_manager
    ):
        """Test that search operation with short name works correctly for tables."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.tables = []
        expected_response.search_text = 'test'
        expected_response.count = 0
        expected_response.operation = 'search-tables'
        mock_table_manager.search_tables.return_value = expected_response

        # Call the method with a short operation name
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='search-tables',  # Short form of 'search-tables'
            database_name='test-db',
            search_text='test',
        )

        # Verify that the method was called with the correct parameters
        mock_table_manager.search_tables.assert_called_once()
        assert mock_table_manager.search_tables.call_args[1]['search_text'] == 'test'

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_with_short_operation_names(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that short operation names (create, delete, etc.) work correctly for connections."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connection_name = 'test-connection'
        expected_response.operation = 'create-connection'
        mock_catalog_manager.create_connection.return_value = expected_response

        # Call the method with a short operation name
        result = await handler_with_write_access.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='create-connection',  # Short form of 'create-connection'
            connection_name='test-connection',
            connection_input={'ConnectionType': 'JDBC'},
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.create_connection.assert_called_once()
        assert (
            mock_catalog_manager.create_connection.call_args[1]['connection_name']
            == 'test-connection'
        )
        assert mock_catalog_manager.create_connection.call_args[1]['connection_input'] == {
            'ConnectionType': 'JDBC'
        }

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_with_short_operation_names(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that short operation names (create, delete, etc.) work correctly for partitions."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.partition_values = ['2023']
        expected_response.operation = 'create-partition'
        mock_catalog_manager.create_partition.return_value = expected_response

        # Call the method with a short operation name
        result = await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='create-partition',  # Short form of 'create-partition'
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
            partition_input={'StorageDescriptor': {'Location': 's3://bucket/path/2023'}},
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.create_partition.assert_called_once()
        assert mock_catalog_manager.create_partition.call_args[1]['database_name'] == 'test-db'
        assert mock_catalog_manager.create_partition.call_args[1]['table_name'] == 'test-table'
        assert mock_catalog_manager.create_partition.call_args[1]['partition_values'] == ['2023']
        assert mock_catalog_manager.create_partition.call_args[1]['partition_input'] == {
            'StorageDescriptor': {'Location': 's3://bucket/path/2023'}
        }

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_with_short_operation_names(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that short operation names (create, delete, etc.) work correctly for catalog."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.catalog_id = 'test-catalog'
        expected_response.operation = 'create-catalog'
        mock_catalog_manager.create_catalog.return_value = expected_response

        # Call the method with a short operation name
        result = await handler_with_write_access.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='create-catalog',  # Short form of 'create-catalog'
            catalog_id='test-catalog',
            catalog_input={'Description': 'Test catalog'},
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.create_catalog.assert_called_once()
        assert mock_catalog_manager.create_catalog.call_args[1]['catalog_name'] == 'test-catalog'
        assert mock_catalog_manager.create_catalog.call_args[1]['catalog_input'] == {
            'Description': 'Test catalog'
        }

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_create_missing_table_input(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing table_input parameter for create-table operation raises a ValueError."""
        # Mock the data_catalog_table_manager to raise the expected ValueError
        handler_with_write_access.data_catalog_table_manager.create_table.side_effect = ValueError(
            'table_name and table_input are required for create-table operation'
        )

        # Call the method without table_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx,
                operation='create-table',
                database_name='test-db',
                table_name='test-table',
            )

        # Verify that the correct error message is raised
        assert 'table_name and table_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_update_missing_table_input(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing table_input parameter for update-table operation raises a ValueError."""
        # Mock the data_catalog_table_manager to raise the expected ValueError
        handler_with_write_access.data_catalog_table_manager.update_table.side_effect = ValueError(
            'table_name and table_input are required for update-table operation'
        )

        # Call the method without table_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx,
                operation='update-table',
                database_name='test-db',
                table_name='test-table',
            )

        # Verify that the correct error message is raised
        assert 'table_name and table_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_create_missing_connection_input(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing connection_input parameter for create operation raises a ValueError."""
        # Mock the data_catalog_manager to raise the expected ValueError
        handler_with_write_access.data_catalog_manager.create_connection.side_effect = ValueError(
            'connection_name and connection_input are required for create operation'
        )

        # Call the method without connection_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx,
                operation='create-connection',
                connection_name='test-connection',
            )

        # Verify that the correct error message is raised
        assert 'connection_name and connection_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_update_missing_connection_input(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing connection_input parameter for update operation raises a ValueError."""
        # Mock the data_catalog_manager to raise the expected ValueError
        handler_with_write_access.data_catalog_manager.update_connection.side_effect = ValueError(
            'connection_name and connection_input are required for update operation'
        )

        # Call the method without connection_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx,
                operation='update-connection',
                connection_name='test-connection',
            )

        # Verify that the correct error message is raised
        assert 'connection_name and connection_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_create_missing_partition_input(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing partition_input parameter for create-partition operation raises a ValueError."""
        # Mock the data_catalog_manager to raise the expected ValueError
        handler_with_write_access.data_catalog_manager.create_partition.side_effect = ValueError(
            'partition_values and partition_input are required for create-partition operation'
        )

        # Call the method without partition_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='create-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=['2023'],
            )

        # Verify that the correct error message is raised
        assert 'partition_values and partition_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_update_missing_partition_input(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing partition_input parameter for update-partition operation raises a ValueError."""
        # Mock the data_catalog_manager to raise the expected ValueError
        handler_with_write_access.data_catalog_manager.update_partition.side_effect = ValueError(
            'partition_values and partition_input are required for update-partition operation'
        )

        # Call the method without partition_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='update-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=['2023'],
            )

        # Verify that the correct error message is raised
        assert 'partition_values and partition_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_catalog_missing_catalog_input(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing catalog_input parameter for create-catalog operation raises a ValueError."""
        # Mock the ValueError that should be raised
        with patch.object(
            handler_with_write_access.data_catalog_manager,
            'create_catalog',
            side_effect=ValueError('catalog_input is required for create-catalog operation'),
        ):
            # Call the method without catalog_input
            with pytest.raises(ValueError) as excinfo:
                await handler_with_write_access.manage_aws_glue_data_catalog(
                    mock_ctx,
                    operation='create-catalog',
                    catalog_id='test-catalog',
                )

            # Verify that the correct error message is raised
            assert 'catalog_input is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_create_with_table_input(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test creating a table with a complete table input."""
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

        # Call the method with the table input
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
    async def test_manage_aws_glue_data_catalog_tables_update_with_table_input(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test updating a table with a complete table input."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.operation = 'update-table'
        mock_table_manager.update_table.return_value = expected_response

        # Create a comprehensive table input for update
        table_input = {
            'Name': 'test-table',
            'Description': 'Updated test table description',
            'Owner': 'updated-owner',
            'Parameters': {
                'classification': 'parquet',
                'compressionType': 'gzip',  # Changed from snappy to gzip
                'updatedAt': '2023-01-01',
            },
            'StorageDescriptor': {
                'Columns': [
                    {'Name': 'id', 'Type': 'int'},
                    {'Name': 'name', 'Type': 'string'},
                    {'Name': 'timestamp', 'Type': 'timestamp'},
                    {'Name': 'new_column', 'Type': 'string'},  # Added a new column
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
        }

        # Call the method with the table input
        result = await handler_with_write_access.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='update-table',
            database_name='test-db',
            table_name='test-table',
            table_input=table_input,
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_table_manager.update_table.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            table_input=table_input,
            catalog_id='123456789012',
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_create_with_connection_input(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test creating a connection with a complete connection input."""
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

        # Call the method with the connection input
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
    async def test_manage_aws_glue_data_catalog_connections_update_with_connection_input(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test updating a connection with a complete connection input."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connection_name = 'test-jdbc-connection'
        expected_response.operation = 'update-connection'
        expected_response.catalog_id = '123456789012'
        mock_catalog_manager.update_connection.return_value = expected_response

        # Create a comprehensive connection input for update
        connection_input = {
            'ConnectionType': 'JDBC',
            'ConnectionProperties': {
                'JDBC_CONNECTION_URL': 'jdbc:mysql://updated-host:3306/updated-db',
                'USERNAME': 'updated-user',
                'PASSWORD': 'updated-password',  # pragma: allowlist secret
                'JDBC_ENFORCE_SSL': 'true',
            },
            'PhysicalConnectionRequirements': {
                'AvailabilityZone': 'us-west-2b',  # Changed from us-west-2a
                'SecurityGroupIdList': ['sg-87654321'],  # Changed security group
                'SubnetId': 'subnet-87654321',  # Changed subnet
            },
            'Description': 'Updated JDBC connection for unit testing',
        }

        # Call the method with the connection input
        result = await handler_with_write_access.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='update-connection',
            connection_name='test-jdbc-connection',
            connection_input=connection_input,
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.update_connection.assert_called_once_with(
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
    async def test_manage_aws_glue_data_catalog_partitions_create_with_partition_input(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test creating a partition with a complete partition input."""
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

        # Call the method with the partition input
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
    async def test_manage_aws_glue_data_catalog_partitions_update_with_partition_input(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test updating a partition with a complete partition input."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.partition_values = ['2023', '01']
        expected_response.operation = 'update-partition'
        mock_catalog_manager.update_partition.return_value = expected_response

        # Create a comprehensive partition input for update
        partition_input = {
            'StorageDescriptor': {
                'Columns': [
                    {'Name': 'id', 'Type': 'int'},
                    {'Name': 'name', 'Type': 'string'},
                    {'Name': 'timestamp', 'Type': 'timestamp'},
                    {'Name': 'new_column', 'Type': 'string'},  # Added a new column
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
                'compressionType': 'gzip',  # Changed from snappy to gzip
                'recordCount': '2000',  # Updated record count
                'averageRecordSize': '120',  # Updated average record size
                'updatedAt': '2023-02-01T00:00:00Z',  # Added update timestamp
            },
            'LastAccessTime': '2023-02-01T00:00:00Z',  # Updated last access time
        }

        # Call the method with the partition input
        result = await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='update-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023', '01'],
            partition_input=partition_input,
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.update_partition.assert_called_once_with(
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
    async def test_manage_aws_glue_data_catalog_tables_search_tables_with_parameters(
        self, handler, mock_ctx, mock_table_manager
    ):
        """Test that search tables operation works correctly with all parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.tables = [
            {'DatabaseName': 'test-db', 'Name': 'test-table1', 'Description': 'First test table'},
            {'DatabaseName': 'test-db', 'Name': 'test-table2', 'Description': 'Second test table'},
        ]
        expected_response.search_text = 'test'
        expected_response.count = 2
        expected_response.operation = 'search-tables'
        # expected_response.next_token = 'next-token-value'
        mock_table_manager.search_tables.return_value = expected_response

        # Call the method with search-tables operation and all parameters
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='search-tables',
            database_name='test-db',
            search_text='test',
            max_results=10,
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_table_manager.search_tables.assert_called_once_with(
            ctx=mock_ctx,
            search_text='test',
            max_results=10,
            catalog_id='123456789012',
        )

        # Verify that the result is the expected response
        assert result == expected_response
        assert len(result.tables) == 2
        assert result.tables[0]['Name'] == 'test-table1'
        assert result.tables[1]['Name'] == 'test-table2'
        assert result.search_text == 'test'
        assert result.count == 2
        # assert result.next_token == 'next-token-value'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_list_partitions_with_parameters(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test that list partitions operation works correctly with all parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.partitions = [
            {
                'Values': ['2023', '01'],
                'StorageDescriptor': {'Location': 's3://bucket/path/2023/01'},
            },
            {
                'Values': ['2023', '02'],
                'StorageDescriptor': {'Location': 's3://bucket/path/2023/02'},
            },
        ]
        expected_response.count = 2
        expected_response.operation = 'list-partitions'
        # expected_response.next_token = 'next-token-value'
        mock_catalog_manager.list_partitions.return_value = expected_response

        # Call the method with list-partitions operation and all parameters
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='list-partitions',
            database_name='test-db',
            table_name='test-table',
            max_results=10,
            expression="year='2023'",
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.list_partitions.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            max_results=10,
            expression="year='2023'",
            catalog_id='123456789012',
            next_token=ANY,
        )

        # Verify that the result is the expected response
        assert result == expected_response
        assert len(result.partitions) == 2
        assert result.partitions[0]['Values'] == ['2023', '01']
        assert result.partitions[1]['Values'] == ['2023', '02']
        assert result.count == 2
        # assert result.next_token == 'next-token-value'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_create_with_catalog_input(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test creating a catalog with a complete catalog input."""
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

        # Call the method with the catalog input
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
    async def test_manage_aws_glue_data_catalog_get_catalog_with_parameters(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test that get catalog operation works correctly with all parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.catalog_id = 'test-catalog'
        expected_response.catalog_definition = {
            'Name': 'Test Catalog',
            'Description': 'Test catalog description',
            'Type': 'GLUE',
            'Parameters': {'key1': 'value1', 'key2': 'value2'},
        }
        expected_response.name = 'Test Catalog'
        expected_response.description = 'Test catalog description'
        expected_response.create_time = '2023-01-01T00:00:00Z'
        expected_response.update_time = '2023-01-01T00:00:00Z'
        expected_response.operation = 'get-catalog'
        mock_catalog_manager.get_catalog.return_value = expected_response

        # Call the method with get-catalog operation
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='get-catalog',
            catalog_id='test-catalog',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.get_catalog.assert_called_once_with(
            ctx=mock_ctx,
            catalog_id='test-catalog',
        )

        # Verify that the result is the expected response
        assert result == expected_response
        assert result.catalog_id == 'test-catalog'
        assert result.name == 'Test Catalog'
        assert result.description == 'Test catalog description'
        assert result.create_time == '2023-01-01T00:00:00Z'
        assert result.update_time == '2023-01-01T00:00:00Z'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_invalid_operation_with_write_access(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that an invalid operation returns an error response with write access."""
        # Call the method with an invalid operation
        result = await handler_with_write_access.manage_aws_glue_data_catalog_tables(
            mock_ctx, operation='invalid-operation', database_name='test-db'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text
        assert result.database_name == 'test-db'
        assert result.table_name == ''
        assert result.operation == 'get-table'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_invalid_operation_with_write_access(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that an invalid operation returns an error response with write access."""
        # Call the method with an invalid operation
        result = await handler_with_write_access.manage_aws_glue_data_catalog_connections(
            mock_ctx, operation='invalid-operation', connection_name='test-connection'
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text
        assert result.connection_name == ''
        assert result.operation == 'get-connection'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_invalid_operation_with_write_access(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that an invalid operation returns an error response with write access."""
        # Call the method with an invalid operation
        result = await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='invalid-operation',
            database_name='test-db',
            table_name='test-table',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        assert result.partition_values == []
        assert result.operation == 'get-partition'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_search_tables_no_parameters(
        self, handler, mock_ctx, mock_table_manager
    ):
        """Test that search tables operation works correctly with minimal parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.tables = []
        expected_response.search_text = None
        expected_response.count = 0
        expected_response.operation = 'search-tables'
        mock_table_manager.search_tables.return_value = expected_response

        # Call the method with search-tables operation and minimal parameters
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='search-tables',
            database_name='test-db',
        )

        # Verify that the method was called
        assert mock_table_manager.search_tables.call_count == 1

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_list_partitions_no_parameters(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test that list partitions operation works correctly with minimal parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.partitions = []
        expected_response.count = 0
        expected_response.operation = 'list-partitions'
        mock_catalog_manager.list_partitions.return_value = expected_response

        # Call the method with list-partitions operation and minimal parameters
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='list-partitions',
            database_name='test-db',
            table_name='test-table',
        )

        # Verify that the method was called
        assert mock_catalog_manager.list_partitions.call_count == 1

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_missing_catalog_id_for_get(
        self, handler, mock_ctx
    ):
        """Test that missing catalog_id parameter for get-catalog operation returns an error response."""
        # Mock the get_catalog method to return an error response
        mock_response = MagicMock()
        mock_response.isError = True
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = 'catalog_id is required for get-catalog operation'
        mock_response.catalog_id = ''
        mock_response.operation = 'get-catalog'
        handler.data_catalog_manager.get_catalog.return_value = mock_response

        # Call the method without catalog_id
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='get-catalog',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert result.catalog_id == ''
        assert result.operation == 'get-catalog'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_missing_catalog_id_for_delete(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing catalog_id parameter for delete-catalog operation returns an error response."""
        # Mock the delete_catalog method to return an error response
        mock_response = MagicMock()
        mock_response.isError = True
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = 'catalog_id is required for delete-catalog operation'
        mock_response.catalog_id = ''
        mock_response.operation = 'delete-catalog'
        handler_with_write_access.data_catalog_manager.delete_catalog.return_value = mock_response

        # Call the method without catalog_id
        result = await handler_with_write_access.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='delete-catalog',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert result.catalog_id == ''
        assert result.operation == 'delete-catalog'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_other_write_access_error(
        self, handler, mock_ctx
    ):
        """Test that other write operations are not allowed without write access."""
        # Call the method with a non-standard write operation
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='other-write-operation',
            database_name='test-db',
            table_name='test-table',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text
        assert result.database_name == 'test-db'
        assert result.table_name == ''

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_other_write_access_error(
        self, handler, mock_ctx
    ):
        """Test that other write operations are not allowed without write access."""
        # Call the method with a non-standard write operation
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='other-write-operation',
            connection_name='test-connection',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text
        assert result.connection_name == ''

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_other_write_access_error(
        self, handler, mock_ctx
    ):
        """Test that other write operations are not allowed without write access."""
        # Call the method with a non-standard write operation
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='other-write-operation',
            database_name='test-db',
            table_name='test-table',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Invalid operation: other-write-operation' in result.content[0].text
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        assert result.partition_values == []

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_other_write_access_error(self, handler, mock_ctx):
        """Test that other write operations are not allowed without write access."""
        # Call the method with a non-standard write operation
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='other-write-operation',
            catalog_id='test-catalog',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Invalid operation: other-write-operation' in result.content[0].text
        assert result.catalog_id == ''

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_create_with_catalog_id(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test creating a table with a catalog ID."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.operation = 'create-table'
        mock_table_manager.create_table.return_value = expected_response

        # Call the method with a catalog ID
        result = await handler_with_write_access.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='create-table',
            database_name='test-db',
            table_name='test-table',
            table_input={'Name': 'test-table'},
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_table_manager.create_table.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            table_input={'Name': 'test-table'},
            catalog_id='123456789012',
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_list_tables_with_max_results(
        self, handler, mock_ctx, mock_table_manager
    ):
        """Test listing tables with max_results parameter."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.tables = [{'Name': 'test-table1'}, {'Name': 'test-table2'}]
        expected_response.count = 2
        expected_response.operation = 'list-tables'
        mock_table_manager.list_tables.return_value = expected_response

        # Call the method with max_results
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='list-tables',
            database_name='test-db',
            max_results=10,
        )

        # Verify that the method was called with the correct parameters
        assert mock_table_manager.list_tables.call_count == 1
        assert mock_table_manager.list_tables.call_args[1]['max_results'] == 10

        # Verify that the result is the expected response
        assert result == expected_response
        assert len(result.tables) == 2

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_get_with_catalog_id(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test getting a connection with a catalog ID."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connection_name = 'test-connection'
        expected_response.operation = 'get-connection'
        expected_response.catalog_id = '123456789012'
        mock_catalog_manager.get_connection.return_value = expected_response

        # Call the method with a catalog ID
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='get-connection',
            connection_name='test-connection',
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        assert mock_catalog_manager.get_connection.call_count == 1
        assert mock_catalog_manager.get_connection.call_args[1]['catalog_id'] == '123456789012'

        # Verify that the result is the expected response
        assert result == expected_response
        assert result.catalog_id == '123456789012'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_get_with_catalog_id(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test getting a partition with a catalog ID."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.partition_values = ['2023', '01']
        expected_response.operation = 'get-partition'
        mock_catalog_manager.get_partition.return_value = expected_response

        # Call the method with a catalog ID
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='get-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023', '01'],
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        assert mock_catalog_manager.get_partition.call_count == 1
        assert mock_catalog_manager.get_partition.call_args[1]['catalog_id'] == '123456789012'

        # Verify that the result is the expected response
        assert result == expected_response
        assert result.partition_values == ['2023', '01']

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_exception_handling_specific(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test specific exception handling in manage_aws_glue_data_catalog_tables."""
        # Setup the mock to raise a specific exception
        mock_table_manager.create_table.side_effect = ValueError('Specific test exception')

        # Call the method
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx,
                operation='create-table',
                database_name='test-db',
                table_name='test-table',
                table_input={'Name': 'test-table'},
            )

        # Verify that the correct error message is raised
        assert 'Specific test exception' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_exception_handling_specific(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test specific exception handling in manage_aws_glue_data_catalog_connections."""
        # Setup the mock to raise a specific exception
        mock_catalog_manager.create_connection.side_effect = ValueError('Specific test exception')

        # Call the method
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx,
                operation='create-connection',
                connection_name='test-connection',
                connection_input={'ConnectionType': 'JDBC'},
            )

        # Verify that the correct error message is raised
        assert 'Specific test exception' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_exception_handling_specific(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test specific exception handling in manage_aws_glue_data_catalog_partitions."""
        # Setup the mock to raise a specific exception
        mock_catalog_manager.create_partition.side_effect = ValueError('Specific test exception')

        # Call the method
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='create-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=['2023', '01'],
                partition_input={'StorageDescriptor': {'Location': 's3://bucket/path/2023/01'}},
            )

        # Verify that the correct error message is raised
        assert 'Specific test exception' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_exception_handling_specific(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test specific exception handling in manage_aws_glue_data_catalog."""
        # Setup the mock to raise a specific exception
        mock_catalog_manager.create_catalog.side_effect = ValueError('Specific test exception')

        # Call the method
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog(
                mock_ctx,
                operation='create-catalog',
                catalog_id='test-catalog',
                catalog_input={'Description': 'Test catalog'},
            )

        # Verify that the correct error message is raised
        assert 'Specific test exception' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_with_sensitive_data_access(
        self, mock_mcp, mock_ctx, mock_database_manager
    ):
        """Test that the handler works correctly with sensitive data access."""
        # Create a handler with sensitive data access
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler.DataCatalogDatabaseManager',
                return_value=mock_database_manager,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler.DataCatalogTableManager',
                return_value=MagicMock(),
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler.DataCatalogManager',
                return_value=MagicMock(),
            ),
        ):
            handler = GlueDataCatalogHandler(mock_mcp, allow_sensitive_data_access=True)
            handler.data_catalog_database_manager = mock_database_manager

            # Setup the mock to return a response
            expected_response = MagicMock()
            expected_response.isError = False
            expected_response.content = []
            expected_response.database_name = 'test-db'
            expected_response.operation = 'get'
            mock_database_manager.get_database.return_value = expected_response

            # Call the method
            result = await handler.manage_aws_glue_data_catalog_databases(
                mock_ctx,
                operation='get-database',
                database_name='test-db',
            )

            # Verify that the result is the expected response
            assert result == expected_response
            assert handler.allow_sensitive_data_access is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_with_both_access_flags(
        self, mock_mcp, mock_ctx, mock_database_manager
    ):
        """Test that the handler works correctly with both write and sensitive data access."""
        # Create a handler with both write and sensitive data access
        with (
            patch(
                'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler.DataCatalogDatabaseManager',
                return_value=mock_database_manager,
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler.DataCatalogTableManager',
                return_value=MagicMock(),
            ),
            patch(
                'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler.DataCatalogManager',
                return_value=MagicMock(),
            ),
        ):
            handler = GlueDataCatalogHandler(
                mock_mcp, allow_write=True, allow_sensitive_data_access=True
            )
            handler.data_catalog_database_manager = mock_database_manager

            # Setup the mock to return a response
            expected_response = MagicMock()
            expected_response.isError = False
            expected_response.content = []
            expected_response.database_name = 'test-db'
            expected_response.operation = 'create'
            mock_database_manager.create_database.return_value = expected_response

            # Call the method
            result = await handler.manage_aws_glue_data_catalog_databases(
                mock_ctx,
                operation='create-database',
                database_name='test-db',
            )

            # Verify that the result is the expected response
            assert result == expected_response
            assert handler.allow_write is True
            assert handler.allow_sensitive_data_access is True

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_update_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that update table operation is not allowed without write access."""
        # Call the method with a write operation
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='update-table',
            database_name='test-db',
            table_name='test-table',
            table_input={'Name': 'test-table'},
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        assert result.database_name == 'test-db'
        assert result.table_name == ''
        assert result.operation == 'update-table'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_search_tables_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that search tables operation is allowed without write access."""
        # Mock the search_tables method to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.tables = []
        expected_response.search_text = 'test'
        expected_response.count = 0
        expected_response.operation = 'search-tables'
        handler.data_catalog_table_manager.search_tables.return_value = expected_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='search-tables',
            database_name='test-db',
            search_text='test',
        )

        # Verify that the result is the expected response
        assert result == expected_response
        assert result.isError is False
        assert handler.data_catalog_table_manager.search_tables.call_count == 1

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_list_tables_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that list tables operation is allowed without write access."""
        # Mock the list_tables method to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.tables = []
        expected_response.count = 0
        expected_response.operation = 'list-tables'
        handler.data_catalog_table_manager.list_tables.return_value = expected_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='list-tables',
            database_name='test-db',
        )

        # Verify that the result is the expected response
        assert result == expected_response
        assert result.isError is False
        assert handler.data_catalog_table_manager.list_tables.call_count == 1

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_list_connections_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that list connections operation is allowed without write access."""
        # Mock the list_connections method to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connections = []
        expected_response.count = 0
        expected_response.operation = 'list-connections'
        handler.data_catalog_manager.list_connections.return_value = expected_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='list-connections',
        )

        # Verify that the result is the expected response
        assert result == expected_response
        assert result.isError is False
        assert handler.data_catalog_manager.list_connections.call_count == 1

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_get_partition_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that get partition operation is allowed without write access."""
        # Mock the get_partition method to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.partition_values = ['2023']
        expected_response.operation = 'get-partition'
        handler.data_catalog_manager.get_partition.return_value = expected_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='get-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
        )

        # Verify that the result is the expected response
        assert result == expected_response
        assert result.isError is False
        assert handler.data_catalog_manager.get_partition.call_count == 1

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_get_catalog_no_write_access(
        self, handler, mock_ctx
    ):
        """Test that get catalog operation is allowed without write access."""
        # Mock the get_catalog method to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.catalog_id = 'test-catalog'
        expected_response.operation = 'get-catalog'
        handler.data_catalog_manager.get_catalog.return_value = expected_response

        # Call the method with a read operation
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='get-catalog',
            catalog_id='test-catalog',
        )

        # Verify that the result is the expected response
        assert result == expected_response
        assert result.isError is False
        assert handler.data_catalog_manager.get_catalog.call_count == 1

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_exception_handling_general(
        self, handler, mock_ctx
    ):
        """Test general exception handling in manage_aws_glue_data_catalog_tables."""
        # Mock the get_table method to raise a general exception
        handler.data_catalog_table_manager.get_table.side_effect = Exception(
            'General test exception'
        )

        # Call the method
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='get-table',
            database_name='test-db',
            table_name='test-table',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert (
            'Error in manage_aws_glue_data_catalog_tables: General test exception'
            in result.content[0].text
        )
        assert result.database_name == 'test-db'
        assert result.table_name == ''
        assert result.operation == 'get-table'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_exception_handling_general(
        self, handler, mock_ctx
    ):
        """Test general exception handling in manage_aws_glue_data_catalog_connections."""
        # Mock the get_connection method to raise a general exception
        handler.data_catalog_manager.get_connection.side_effect = Exception(
            'General test exception'
        )

        # Call the method
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='get-connection',
            connection_name='test-connection',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert (
            'Error in manage_aws_glue_data_catalog_connections: General test exception'
            in result.content[0].text
        )
        assert result.connection_name == ''
        assert result.operation == 'get-connection'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_exception_handling_general(
        self, handler, mock_ctx
    ):
        """Test general exception handling in manage_aws_glue_data_catalog_partitions."""
        # Mock the get_partition method to raise a general exception
        handler.data_catalog_manager.get_partition.side_effect = Exception(
            'General test exception'
        )

        # Call the method
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='get-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert (
            'Error in manage_aws_glue_data_catalog_partitions: General test exception'
            in result.content[0].text
        )
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        assert result.partition_values == []
        assert result.operation == 'get-partition'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_exception_handling_general(
        self, handler, mock_ctx
    ):
        """Test general exception handling in manage_aws_glue_data_catalog."""
        # Mock the get_catalog method to raise a general exception
        handler.data_catalog_manager.get_catalog.side_effect = Exception('General test exception')

        # Call the method
        result = await handler.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='get-catalog',
            catalog_id='test-catalog',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert (
            'Error in manage_aws_glue_data_catalog: General test exception'
            in result.content[0].text
        )
        assert result.catalog_id == 'test-catalog'
        assert result.operation == 'get-catalog'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_error_response_for_other_operations(
        self, handler, mock_ctx
    ):
        """Test that an error response is returned for operations not explicitly handled."""
        # Set write access to true to bypass the "not allowed without write access" check
        handler.allow_write = True

        # Call the method with an operation that doesn't match any of the explicit cases
        result = await handler.manage_aws_glue_data_catalog_databases(
            mock_ctx,
            operation='unknown-operation',
            database_name='test-db',
        )

        # Verify that the result is an error response
        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text
        assert result.database_name == ''
        assert result.description == ''
        assert result.location_uri == ''
        assert result.parameters == {}
        assert result.creation_time == ''
        assert result.operation == 'get-database'
        assert result.catalog_id == ''

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_with_none_parameters(
        self, handler_with_write_access, mock_ctx, mock_database_manager
    ):
        """Test that the handler works correctly with None parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.operation = 'create'
        mock_database_manager.create_database.return_value = expected_response

        # Call the method with None parameters
        result = await handler_with_write_access.manage_aws_glue_data_catalog_databases(
            mock_ctx,
            operation='create-database',
            database_name='test-db',
            description=None,
            location_uri=None,
            parameters=None,
            catalog_id=None,
        )

        # Verify that the method was called with the correct parameters
        mock_database_manager.create_database.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            description=None,
            location_uri=None,
            parameters=None,
            catalog_id=None,
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_with_none_parameters(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test that the handler works correctly with None parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.operation = 'create-table'
        mock_table_manager.create_table.return_value = expected_response

        # Call the method with None parameters
        result = await handler_with_write_access.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='create-table',
            database_name='test-db',
            table_name='test-table',
            table_input={'Name': 'test-table'},
            catalog_id=None,
        )

        # Verify that the method was called with the correct parameters
        mock_table_manager.create_table.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            table_input={'Name': 'test-table'},
            catalog_id=None,
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_with_none_parameters(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that the handler works correctly with None parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connection_name = 'test-connection'
        expected_response.operation = 'create-connection'
        mock_catalog_manager.create_connection.return_value = expected_response

        # Call the method with None parameters
        result = await handler_with_write_access.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='create-connection',
            connection_name='test-connection',
            connection_input={'ConnectionType': 'JDBC'},
            catalog_id=None,
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.create_connection.assert_called_once_with(
            ctx=mock_ctx,
            connection_name='test-connection',
            connection_input={'ConnectionType': 'JDBC'},
            catalog_id=None,
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_with_none_parameters(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that the handler works correctly with None parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.partition_values = ['2023']
        expected_response.operation = 'create-partition'
        mock_catalog_manager.create_partition.return_value = expected_response

        # Call the method with None parameters
        result = await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='create-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
            partition_input={'StorageDescriptor': {'Location': 's3://bucket/path/2023'}},
            catalog_id=None,
            max_results=None,
            expression=None,
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.create_partition.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
            partition_input={'StorageDescriptor': {'Location': 's3://bucket/path/2023'}},
            catalog_id=None,
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_with_none_parameters(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test that the handler works correctly with None parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.catalog_id = 'test-catalog'
        expected_response.operation = 'create-catalog'
        mock_catalog_manager.create_catalog.return_value = expected_response

        # Call the method with None parameters
        result = await handler_with_write_access.manage_aws_glue_data_catalog(
            mock_ctx,
            operation='create-catalog',
            catalog_id='test-catalog',
            catalog_input={'Description': 'Test catalog'},
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.create_catalog.assert_called_once_with(
            ctx=mock_ctx,
            catalog_name='test-catalog',
            catalog_input={'Description': 'Test catalog'},
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_missing_database_name(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing database_name parameter raises a ValueError."""
        # Mock the get_table method to raise the expected ValueError
        handler_with_write_access.data_catalog_table_manager.get_table.side_effect = ValueError(
            'database_name is required for get-table operation'
        )

        # Call the method without database_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx,
                operation='get-table',
                table_name='test-table',
            )

        # Verify that the correct error message is raised
        assert 'database_name is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_missing_database_name(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing database_name parameter raises a ValueError."""
        # Mock the get_partition method to raise the expected ValueError
        handler_with_write_access.data_catalog_manager.get_partition.side_effect = ValueError(
            'database_name is required for get-partition operation'
        )

        # Call the method without database_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='get-partition',
                table_name='test-table',
                partition_values=['2023'],
            )

        # Verify that the correct error message is raised
        assert 'database_name is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_missing_table_name(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that missing table_name parameter raises a ValueError."""
        # Mock the get_partition method to raise the expected ValueError
        handler_with_write_access.data_catalog_manager.get_partition.side_effect = ValueError(
            'table_name is required for get-partition operation'
        )

        # Call the method without table_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='get-partition',
                database_name='test-db',
                partition_values=['2023'],
            )

        # Verify that the correct error message is raised
        assert 'table_name is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_update_with_catalog_id(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test updating a table with a catalog ID."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.operation = 'update-table'
        mock_table_manager.update_table.return_value = expected_response

        # Call the method with a catalog ID
        result = await handler_with_write_access.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='update-table',
            database_name='test-db',
            table_name='test-table',
            table_input={'Name': 'test-table'},
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_table_manager.update_table.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            table_input={'Name': 'test-table'},
            catalog_id='123456789012',
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_update_with_catalog_id(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test updating a connection with a catalog ID."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connection_name = 'test-connection'
        expected_response.operation = 'update-connection'
        expected_response.catalog_id = '123456789012'
        mock_catalog_manager.update_connection.return_value = expected_response

        # Call the method with a catalog ID
        result = await handler_with_write_access.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='update-connection',
            connection_name='test-connection',
            connection_input={'ConnectionType': 'JDBC'},
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.update_connection.assert_called_once_with(
            ctx=mock_ctx,
            connection_name='test-connection',
            connection_input={'ConnectionType': 'JDBC'},
            catalog_id='123456789012',
        )

        # Verify that the result is the expected response
        assert result == expected_response
        assert result.catalog_id == '123456789012'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_update_with_catalog_id(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test updating a partition with a catalog ID."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.partition_values = ['2023']
        expected_response.operation = 'update-partition'
        mock_catalog_manager.update_partition.return_value = expected_response

        # Call the method with a catalog ID
        result = await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='update-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
            partition_input={'StorageDescriptor': {'Location': 's3://bucket/path/2023'}},
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.update_partition.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
            partition_input={'StorageDescriptor': {'Location': 's3://bucket/path/2023'}},
            catalog_id='123456789012',
        )

        # Verify that the result is the expected response
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_delete_with_catalog_id(
        self, handler_with_write_access, mock_ctx, mock_table_manager
    ):
        """Test deleting a table with a catalog ID."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.operation = 'delete-table'
        mock_table_manager.delete_table.return_value = expected_response

        # Call the method with a catalog ID
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
    async def test_manage_aws_glue_data_catalog_connections_delete_with_catalog_id(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test deleting a connection with a catalog ID."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connection_name = 'test-connection'
        expected_response.operation = 'delete-connection'
        expected_response.catalog_id = '123456789012'
        mock_catalog_manager.delete_connection.return_value = expected_response

        # Call the method with a catalog ID
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
    async def test_manage_aws_glue_data_catalog_partitions_delete_with_catalog_id(
        self, handler_with_write_access, mock_ctx, mock_catalog_manager
    ):
        """Test deleting a partition with a catalog ID."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.database_name = 'test-db'
        expected_response.table_name = 'test-table'
        expected_response.partition_values = ['2023']
        expected_response.operation = 'delete-partition'
        mock_catalog_manager.delete_partition.return_value = expected_response

        # Call the method with a catalog ID
        result = await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='delete-partition',
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.delete_partition.assert_called_once_with(
            ctx=mock_ctx,
            database_name='test-db',
            table_name='test-table',
            partition_values=['2023'],
            catalog_id='123456789012',
        )

        # Verify that the result is the expected response
        assert result == expected_response

    # Additional tests to increase coverage for specific lines

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_with_max_results(
        self, handler, mock_ctx, mock_table_manager
    ):
        """Test listing tables with max_results parameter."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.tables = [{'Name': 'test-table1'}, {'Name': 'test-table2'}]
        expected_response.count = 2
        expected_response.operation = 'list-tables'
        mock_table_manager.list_tables.return_value = expected_response

        # Call the method with max_results
        result = await handler.manage_aws_glue_data_catalog_tables(
            mock_ctx,
            operation='list-tables',
            database_name='test-db',
            max_results=10,
        )

        # Verify that the method was called with the correct parameters
        assert mock_table_manager.list_tables.call_count == 1
        assert mock_table_manager.list_tables.call_args[1]['max_results'] == 10

        # Verify that the result is the expected response
        assert result == expected_response
        assert len(result.tables) == 2

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_databases_create_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that create database operation with missing required parameters raises a ValueError."""
        # Mock the ValueError that should be raised
        with patch.object(
            handler_with_write_access.data_catalog_database_manager,
            'create_database',
            side_effect=ValueError('database_name is required for create-database operation'),
        ):
            # Call the method without database_name
            with pytest.raises(ValueError) as excinfo:
                await handler_with_write_access.manage_aws_glue_data_catalog_databases(
                    mock_ctx, operation='create-database'
                )

        # Verify that the correct error message is raised
        assert 'database_name is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_create_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that create table operation with missing required parameters raises a ValueError."""
        # Call the method without table_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx, operation='create-table', database_name='test-db', table_name=None
            )

        # Verify that the correct error message is raised
        assert 'database_name, table_input and table_name are required' in str(excinfo.value)

        # Call the method without table_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx,
                operation='create-table',
                database_name='test-db',
                table_name='test-table',
                table_input=None,
            )

        # Verify that the correct error message is raised
        assert 'database_name, table_input and table_name are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_delete_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that delete table operation with missing required parameters raises a ValueError."""
        # Call the method without table_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx, operation='delete-table', database_name='test-db', table_name=None
            )

        # Verify that the correct error message is raised
        assert 'table_name and database_name required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_get_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that get table operation with missing required parameters raises a ValueError."""
        # Call the method without table_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx, operation='get-table', database_name='test-db', table_name=None
            )

        # Verify that the correct error message is raised
        assert 'table_name is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_tables_update_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that update table operation with missing required parameters raises a ValueError."""
        # Call the method without table_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx, operation='update-table', database_name='test-db', table_name=None
            )

        # Verify that the correct error message is raised
        assert 'table_name and table_input are required' in str(excinfo.value)

        # Call the method without table_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_tables(
                mock_ctx,
                operation='update-table',
                database_name='test-db',
                table_name='test-table',
                table_input=None,
            )

        # Verify that the correct error message is raised
        assert 'table_name and table_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_create_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that create connection operation with missing required parameters raises a ValueError."""
        # Call the method without connection_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx, operation='create-connection', connection_name=None
            )

        # Verify that the correct error message is raised
        assert 'connection_name and connection_input are required' in str(excinfo.value)

        # Call the method without connection_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx,
                operation='create-connection',
                connection_name='test-connection',
                connection_input=None,
            )

        # Verify that the correct error message is raised
        assert 'connection_name and connection_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_delete_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that delete connection operation with missing required parameters raises a ValueError."""
        # Call the method without connection_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx, operation='delete-connection', connection_name=None
            )

        # Verify that the correct error message is raised
        assert 'connection_name is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_get_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that get connection operation with missing required parameters raises a ValueError."""
        # Call the method without connection_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx, operation='get-connection', connection_name=None
            )

        # Verify that the correct error message is raised
        assert 'connection_name is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_update_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that update connection operation with missing required parameters raises a ValueError."""
        # Call the method without connection_name
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx, operation='update-connection', connection_name=None
            )

        # Verify that the correct error message is raised
        assert 'connection_name and connection_input are required' in str(excinfo.value)

        # Call the method without connection_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_connections(
                mock_ctx,
                operation='update-connection',
                connection_name='test-connection',
                connection_input=None,
            )

        # Verify that the correct error message is raised
        assert 'connection_name and connection_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_create_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that create partition operation with missing required parameters raises a ValueError."""
        # Call the method without partition_values
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='create-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=None,
            )

        # Verify that the correct error message is raised
        assert 'partition_values and partition_input are required' in str(excinfo.value)

        # Call the method without partition_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='create-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=['2023'],
                partition_input=None,
            )

        # Verify that the correct error message is raised
        assert 'partition_values and partition_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_delete_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that delete partition operation with missing required parameters raises a ValueError."""
        # Call the method without partition_values
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='delete-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=None,
            )

        # Verify that the correct error message is raised
        assert 'partition_values is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_get_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that get partition operation with missing required parameters raises a ValueError."""
        # Call the method without partition_values
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='get-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=None,
            )

        # Verify that the correct error message is raised
        assert 'partition_values is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_update_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that update partition operation with missing required parameters raises a ValueError."""
        # Call the method without partition_values
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='update-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=None,
            )

        # Verify that the correct error message is raised
        assert 'partition_values and partition_input are required' in str(excinfo.value)

        # Call the method without partition_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog_partitions(
                mock_ctx,
                operation='update-partition',
                database_name='test-db',
                table_name='test-table',
                partition_values=['2023'],
                partition_input=None,
            )

        # Verify that the correct error message is raised
        assert 'partition_values and partition_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_create_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that create catalog operation with missing required parameters raises a ValueError."""
        # Call the method without catalog_id
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog(
                mock_ctx, operation='create-catalog', catalog_id=None
            )

        # Verify that the correct error message is raised
        assert 'catalog_id and catalog_input are required' in str(excinfo.value)

        # Call the method without catalog_input
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog(
                mock_ctx, operation='create-catalog', catalog_id='test-catalog', catalog_input=None
            )

        # Verify that the correct error message is raised
        assert 'catalog_id and catalog_input are required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_delete_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that delete catalog operation with missing required parameters raises a ValueError."""
        # Call the method without catalog_id
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog(
                mock_ctx, operation='delete-catalog', catalog_id=None
            )

        # Verify that the correct error message is raised
        assert 'catalog_id is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_get_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that get catalog operation with missing required parameters raises a ValueError."""
        # Call the method without catalog_id
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog(
                mock_ctx, operation='get-catalog', catalog_id=None
            )

        # Verify that the correct error message is raised
        assert 'catalog_id is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_import_missing_required_params(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that import catalog operation with missing required parameters raises a ValueError."""
        # Call the method without catalog_id
        with pytest.raises(ValueError) as excinfo:
            await handler_with_write_access.manage_aws_glue_data_catalog(
                mock_ctx, operation='import-catalog-to-glue', catalog_id=None
            )

        # Verify that the correct error message is raised
        assert 'catalog_id is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_partitions_list_with_all_parameters(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test listing partitions with all parameters including next_token."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.partitions = [{'Values': ['2023', '01']}, {'Values': ['2023', '02']}]
        expected_response.count = 2
        expected_response.next_token = 'next-token-value'
        expected_response.operation = 'list-partitions'
        mock_catalog_manager.list_partitions.return_value = expected_response

        # Call the method with all parameters
        result = await handler.manage_aws_glue_data_catalog_partitions(
            mock_ctx,
            operation='list-partitions',
            database_name='test-db',
            table_name='test-table',
            max_results=10,
            expression="year='2023'",
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.list_partitions.assert_called_once()
        assert mock_catalog_manager.list_partitions.call_args[1]['database_name'] == 'test-db'
        assert mock_catalog_manager.list_partitions.call_args[1]['table_name'] == 'test-table'
        assert mock_catalog_manager.list_partitions.call_args[1]['max_results'] == 10
        assert mock_catalog_manager.list_partitions.call_args[1]['expression'] == "year='2023'"
        assert mock_catalog_manager.list_partitions.call_args[1]['catalog_id'] == '123456789012'

        # Verify that the result is the expected response
        assert result == expected_response
        assert len(result.partitions) == 2

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_list_with_max_results(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test listing connections with max_results parameter."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connections = [
            {'Name': 'connection1', 'ConnectionType': 'JDBC'},
            {'Name': 'connection2', 'ConnectionType': 'KAFKA'},
        ]
        expected_response.count = 2
        expected_response.operation = 'list-connections'
        mock_catalog_manager.list_connections.return_value = expected_response

        # Call the method with max_results
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='list-connections',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.list_connections.assert_called_once()

        # Verify that the result is the expected response
        assert result == expected_response
        assert len(result.connections) == 2

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_list_with_all_parameters(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test listing connections with all parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connections = [
            {'Name': 'connection1', 'ConnectionType': 'JDBC'},
            {'Name': 'connection2', 'ConnectionType': 'KAFKA'},
        ]
        expected_response.count = 2
        expected_response.next_token = 'next-token-value'
        expected_response.operation = 'list-connections'
        mock_catalog_manager.list_connections.return_value = expected_response

        # Call the method with all parameters
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='list-connections',
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.list_connections.assert_called_once()
        assert mock_catalog_manager.list_connections.call_args[1]['catalog_id'] == '123456789012'

        # Verify that the result is the expected response
        assert result == expected_response
        assert len(result.connections) == 2

    @pytest.mark.asyncio
    async def test_manage_aws_glue_data_catalog_connections_get_with_all_parameters(
        self, handler, mock_ctx, mock_catalog_manager
    ):
        """Test getting a connection with all parameters."""
        # Setup the mock to return a response
        expected_response = MagicMock()
        expected_response.isError = False
        expected_response.content = []
        expected_response.connection_name = 'test-connection'
        expected_response.connection_type = 'JDBC'
        expected_response.connection_properties = {
            'JDBC_CONNECTION_URL': 'jdbc:mysql://test-host:3306/test-db'
        }
        expected_response.operation = 'get'
        mock_catalog_manager.get_connection.return_value = expected_response

        # Call the method with all parameters
        result = await handler.manage_aws_glue_data_catalog_connections(
            mock_ctx,
            operation='get-connection',
            connection_name='test-connection',
            catalog_id='123456789012',
        )

        # Verify that the method was called with the correct parameters
        mock_catalog_manager.get_connection.assert_called_once()
        assert (
            mock_catalog_manager.get_connection.call_args[1]['connection_name']
            == 'test-connection'
        )
        assert mock_catalog_manager.get_connection.call_args[1]['catalog_id'] == '123456789012'

        # Verify that the result is the expected response
        assert result == expected_response
