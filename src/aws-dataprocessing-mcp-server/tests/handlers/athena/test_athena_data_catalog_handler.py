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


import json
import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_data_catalog_handler import (
    AthenaDataCatalogHandler,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from unittest.mock import Mock, patch


@pytest.fixture
def mock_athena_client():
    """Create a mock Athena client instance for testing."""
    return Mock()


@pytest.fixture
def mock_aws_helper():
    """Create a mock AwsHelper instance for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_data_catalog_handler.AwsHelper'
    ) as mock:
        mock.create_boto3_client.return_value = Mock()
        mock.prepare_resource_tags.return_value = {'ManagedBy': 'MCP'}
        mock.convert_tags_to_aws_format.return_value = [{'Key': 'ManagedBy', 'Value': 'MCP'}]
        yield mock


@pytest.fixture
def handler(mock_aws_helper):
    """Create a mock AthenaDataCatalogHandler instance for testing."""
    mcp = Mock()
    return AthenaDataCatalogHandler(mcp, allow_write=True)


@pytest.fixture
def read_only_handler(mock_aws_helper):
    """Create a mock AthenaDataCatalogHandler instance with read-only access for testing."""
    mcp = Mock()
    return AthenaDataCatalogHandler(mcp, allow_write=False)


@pytest.fixture
def mock_context():
    """Create a mock context instance for testing."""
    return Mock(spec=Context)


# Initialization Tests


def test_initialization_parameters(mock_aws_helper):
    """Test initialization of parameters for AthenaDataCatalogHandler object."""
    mcp = Mock()
    handler = AthenaDataCatalogHandler(mcp, allow_write=True, allow_sensitive_data_access=True)

    assert handler.allow_write
    assert handler.allow_sensitive_data_access
    assert handler.mcp == mcp


def test_initialization_registers_tools(mock_aws_helper):
    """Test that initialization registers the tools with the MCP server."""
    mcp = Mock()
    AthenaDataCatalogHandler(mcp)

    mcp.tool.assert_any_call(name='manage_aws_athena_data_catalogs')
    mcp.tool.assert_any_call(name='manage_aws_athena_databases_and_tables')


# Data Catalog Tests


@pytest.mark.asyncio
async def test_create_data_catalog_success(handler, mock_athena_client):
    """Test successful creation of a data catalog."""
    handler.athena_client = mock_athena_client

    ctx = Mock()
    response = await handler.manage_aws_athena_data_catalogs(
        ctx,
        operation='create-data-catalog',
        name='test-catalog',
        type='GLUE',
        description='Test catalog',
        parameters={'catalog-id': '123456789012'},
        tags={'Environment': 'Test'},
    )

    assert not response.isError
    assert response.name == 'test-catalog'
    assert response.operation == 'create-data-catalog'
    mock_athena_client.create_data_catalog.assert_called_once()
    # Verify parameters were passed correctly
    call_args = mock_athena_client.create_data_catalog.call_args[1]
    assert call_args['Name'] == 'test-catalog'
    assert call_args['Type'] == 'GLUE'
    assert call_args['Description'] == 'Test catalog'
    assert call_args['Parameters'] == json.dumps({'catalog-id': '123456789012'})
    assert call_args['Tags'] == [{'Key': 'ManagedBy', 'Value': 'MCP'}]


@pytest.mark.asyncio
async def test_create_data_catalog_missing_parameters(handler):
    """Test that create data catalog fails when required parameters are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_data_catalogs(
            ctx, operation='create-data-catalog', name=None, type=None
        )


@pytest.mark.asyncio
async def test_create_data_catalog_without_write_permission(read_only_handler):
    """Test that creating a data catalog fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_data_catalogs(
        ctx, operation='create-data-catalog', name='test-catalog', type='GLUE'
    )

    assert response.isError
    assert 'not allowed without write access' in response.content[0].text


@pytest.mark.asyncio
async def test_delete_data_catalog_success(handler, mock_athena_client):
    """Test successful deletion of a data catalog."""
    handler.athena_client = mock_athena_client
    mock_athena_client.delete_data_catalog.return_value = {
        'DataCatalog': {'Status': 'DELETE_SUCCESSFUL'}
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_data_catalogs(
        ctx, operation='delete-data-catalog', name='test-catalog', delete_catalog_only=True
    )

    assert not response.isError
    assert response.name == 'test-catalog'
    assert response.operation == 'delete-data-catalog'
    mock_athena_client.delete_data_catalog.assert_called_once_with(
        Name='test-catalog', DeleteCatalogOnly='true'
    )


@pytest.mark.asyncio
async def test_delete_data_catalog_failure(handler, mock_athena_client):
    """Test handling of a failed data catalog deletion."""
    handler.athena_client = mock_athena_client
    mock_athena_client.delete_data_catalog.return_value = {
        'DataCatalog': {'Status': 'DELETE_FAILED'}
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_data_catalogs(
        ctx, operation='delete-data-catalog', name='test-catalog'
    )

    assert response.isError
    assert response.name == 'test-catalog'
    assert response.operation == 'delete-data-catalog'
    assert 'Data Catalog delete operation failed' in response.content[0].text


@pytest.mark.asyncio
async def test_delete_data_catalog_missing_parameters(handler):
    """Test that delete data catalog fails when name is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_data_catalogs(
            ctx, operation='delete-data-catalog', name=None
        )


@pytest.mark.asyncio
async def test_delete_data_catalog_without_write_permission(read_only_handler):
    """Test that deleting a data catalog fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_data_catalogs(
        ctx, operation='delete-data-catalog', name='test-catalog'
    )

    assert response.isError
    assert 'not allowed without write access' in response.content[0].text


@pytest.mark.asyncio
async def test_get_data_catalog_success(handler, mock_athena_client):
    """Test successful retrieval of a data catalog."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_data_catalog.return_value = {
        'DataCatalog': {
            'Name': 'test-catalog',
            'Type': 'GLUE',
            'Description': 'Test catalog',
            'Parameters': {'catalog-id': '123456789012'},
        }
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_data_catalogs(
        ctx, operation='get-data-catalog', name='test-catalog', work_group='primary'
    )

    assert not response.isError
    assert response.operation == 'get-data-catalog'
    assert response.data_catalog['Name'] == 'test-catalog'
    assert response.data_catalog['Type'] == 'GLUE'
    mock_athena_client.get_data_catalog.assert_called_once_with(
        Name='test-catalog', WorkGroup='primary'
    )


@pytest.mark.asyncio
async def test_get_data_catalog_missing_parameters(handler):
    """Test that get data catalog fails when name is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_data_catalogs(ctx, operation='get-data-catalog', name=None)


@pytest.mark.asyncio
async def test_list_data_catalogs_success(handler, mock_athena_client):
    """Test successful listing of data catalogs."""
    handler.athena_client = mock_athena_client
    mock_athena_client.list_data_catalogs.return_value = {
        'DataCatalogsSummary': [
            {'CatalogName': 'catalog1', 'Type': 'GLUE'},
            {'CatalogName': 'catalog2', 'Type': 'LAMBDA'},
        ],
        'NextToken': 'next-token',
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_data_catalogs(
        ctx,
        operation='list-data-catalogs',
        max_results=10,
        next_token='token',
        work_group='primary',
    )

    assert not response.isError
    assert response.operation == 'list-data-catalogs'
    assert len(response.data_catalogs) == 2
    assert response.count == 2
    assert response.next_token == 'next-token'
    mock_athena_client.list_data_catalogs.assert_called_once_with(
        MaxResults=10, NextToken='token', WorkGroup='primary'
    )


@pytest.mark.asyncio
async def test_update_data_catalog_success(handler, mock_athena_client):
    """Test successful update of a data catalog."""
    handler.athena_client = mock_athena_client

    ctx = Mock()
    response = await handler.manage_aws_athena_data_catalogs(
        ctx,
        operation='update-data-catalog',
        name='test-catalog',
        type='GLUE',
        description='Updated catalog',
        parameters={'catalog-id': '987654321098'},
    )

    assert not response.isError
    assert response.name == 'test-catalog'
    assert response.operation == 'update-data-catalog'
    mock_athena_client.update_data_catalog.assert_called_once()
    # Verify parameters were passed correctly
    call_args = mock_athena_client.update_data_catalog.call_args[1]
    assert call_args['Name'] == 'test-catalog'
    assert call_args['Type'] == 'GLUE'
    assert call_args['Description'] == 'Updated catalog'
    assert call_args['Parameters'] == json.dumps({'catalog-id': '987654321098'})


@pytest.mark.asyncio
async def test_update_data_catalog_missing_parameters(handler):
    """Test that update data catalog fails when name is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_data_catalogs(
            ctx, operation='update-data-catalog', name=None
        )


@pytest.mark.asyncio
async def test_update_data_catalog_without_write_permission(read_only_handler):
    """Test that updating a data catalog fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_data_catalogs(
        ctx, operation='update-data-catalog', name='test-catalog', description='Updated catalog'
    )

    assert response.isError
    assert 'not allowed without write access' in response.content[0].text


@pytest.mark.asyncio
async def test_invalid_data_catalog_operation(handler):
    """Test that running manage_aws_athena_data_catalogs with an invalid operation results in an error."""
    ctx = Mock()
    response = await handler.manage_aws_athena_data_catalogs(ctx, operation='invalid-operation')

    assert response.isError
    assert 'Invalid operation' in response.content[0].text


@pytest.mark.asyncio
async def test_data_catalog_client_error_handling(handler, mock_athena_client):
    """Test error handling when Athena client raises an exception."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_data_catalog.side_effect = ClientError(
        {'Error': {'Code': 'InvalidRequestException', 'Message': 'Invalid request'}},
        'GetDataCatalog',
    )

    ctx = Mock()
    response = await handler.manage_aws_athena_data_catalogs(
        ctx, operation='get-data-catalog', name='test-catalog'
    )

    assert response.isError
    assert 'Error in manage_aws_athena_data_catalogs' in response.content[0].text


# Database and Table Tests


@pytest.mark.asyncio
async def test_get_database_success(handler, mock_athena_client):
    """Test successful retrieval of a database."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_database.return_value = {
        'Database': {
            'Name': 'test-db',
            'Description': 'Test database',
            'Parameters': {'created-by': 'test-user'},
        }
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_databases_and_tables(
        ctx,
        operation='get-database',
        catalog_name='test-catalog',
        database_name='test-db',
        work_group='primary',
    )

    assert not response.isError
    assert response.operation == 'get-database'
    assert response.database['Name'] == 'test-db'
    mock_athena_client.get_database.assert_called_once_with(
        CatalogName='test-catalog', DatabaseName='test-db', WorkGroup='primary'
    )


@pytest.mark.asyncio
async def test_get_database_missing_parameters(handler):
    """Test that get database fails when database_name is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_databases_and_tables(
            ctx, operation='get-database', catalog_name='test-catalog', database_name=None
        )


@pytest.mark.asyncio
async def test_get_table_metadata_success(handler, mock_athena_client):
    """Test successful retrieval of table metadata."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_table_metadata.return_value = {
        'TableMetadata': {
            'Name': 'test-table',
            'CreateTime': '2023-01-01T00:00:00Z',
            'LastAccessTime': '2023-01-02T00:00:00Z',
            'TableType': 'EXTERNAL_TABLE',
            'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}],
        }
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_databases_and_tables(
        ctx,
        operation='get-table-metadata',
        catalog_name='test-catalog',
        database_name='test-db',
        table_name='test-table',
        work_group='primary',
    )

    assert not response.isError
    assert response.operation == 'get-table-metadata'
    assert response.table_metadata['Name'] == 'test-table'
    assert len(response.table_metadata['Columns']) == 2
    mock_athena_client.get_table_metadata.assert_called_once_with(
        CatalogName='test-catalog',
        DatabaseName='test-db',
        TableName='test-table',
        WorkGroup='primary',
    )


@pytest.mark.asyncio
async def test_get_table_metadata_missing_parameters(handler):
    """Test that get table metadata fails when required parameters are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_databases_and_tables(
            ctx,
            operation='get-table-metadata',
            catalog_name='test-catalog',
            database_name='test-db',
            table_name=None,
        )

    with pytest.raises(ValueError):
        await handler.manage_aws_athena_databases_and_tables(
            ctx,
            operation='get-table-metadata',
            catalog_name='test-catalog',
            database_name=None,
            table_name='test-table',
        )


@pytest.mark.asyncio
async def test_list_databases_success(handler, mock_athena_client):
    """Test successful listing of databases."""
    handler.athena_client = mock_athena_client
    mock_athena_client.list_databases.return_value = {
        'DatabaseList': [
            {'Name': 'db1', 'Description': 'Database 1'},
            {'Name': 'db2', 'Description': 'Database 2'},
        ],
        'NextToken': 'next-token',
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_databases_and_tables(
        ctx,
        operation='list-databases',
        catalog_name='test-catalog',
        max_results=10,
        next_token='token',
        work_group='primary',
    )

    assert not response.isError
    assert response.operation == 'list-databases'
    assert len(response.database_list) == 2
    assert response.count == 2
    assert response.next_token == 'next-token'
    mock_athena_client.list_databases.assert_called_once_with(
        CatalogName='test-catalog', MaxResults=10, NextToken='token', WorkGroup='primary'
    )


@pytest.mark.asyncio
async def test_list_table_metadata_success(handler, mock_athena_client):
    """Test successful listing of table metadata."""
    handler.athena_client = mock_athena_client
    mock_athena_client.list_table_metadata.return_value = {
        'TableMetadataList': [
            {'Name': 'table1', 'TableType': 'EXTERNAL_TABLE'},
            {'Name': 'table2', 'TableType': 'MANAGED_TABLE'},
        ],
        'NextToken': 'next-token',
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_databases_and_tables(
        ctx,
        operation='list-table-metadata',
        catalog_name='test-catalog',
        database_name='test-db',
        expression='table*',
        max_results=10,
        next_token='token',
        work_group='primary',
    )

    assert not response.isError
    assert response.operation == 'list-table-metadata'
    assert len(response.table_metadata_list) == 2
    assert response.count == 2
    assert response.next_token == 'next-token'
    mock_athena_client.list_table_metadata.assert_called_once_with(
        CatalogName='test-catalog',
        DatabaseName='test-db',
        Expression='table*',
        MaxResults=10,
        NextToken='token',
        WorkGroup='primary',
    )


@pytest.mark.asyncio
async def test_list_table_metadata_missing_parameters(handler):
    """Test that list table metadata fails when database_name is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_databases_and_tables(
            ctx, operation='list-table-metadata', catalog_name='test-catalog', database_name=None
        )


@pytest.mark.asyncio
async def test_invalid_database_table_operation(handler):
    """Test that running manage_aws_athena_databases_and_tables with an invalid operation results in an error."""
    ctx = Mock()
    response = await handler.manage_aws_athena_databases_and_tables(
        ctx, operation='invalid-operation', catalog_name='test-catalog'
    )

    assert response.isError
    assert 'Invalid operation' in response.content[0].text


@pytest.mark.asyncio
async def test_database_table_client_error_handling(handler, mock_athena_client):
    """Test error handling when Athena client raises an exception."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_database.side_effect = ClientError(
        {'Error': {'Code': 'InvalidRequestException', 'Message': 'Invalid request'}},
        'GetDatabase',
    )

    ctx = Mock()
    response = await handler.manage_aws_athena_databases_and_tables(
        ctx, operation='get-database', catalog_name='test-catalog', database_name='test-db'
    )

    assert response.isError
    assert 'Error in manage_aws_athena_databases_and_tables' in response.content[0].text
