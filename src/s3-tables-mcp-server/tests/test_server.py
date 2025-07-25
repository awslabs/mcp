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

"""Tests for the S3 Tables MCP Server."""

import os
import pytest
import sys
from awslabs.s3_tables_mcp_server.models import (
    IcebergMetadata,
    IcebergSchema,
    OpenTableFormat,
    SchemaField,
    TableMetadata,
)
from awslabs.s3_tables_mcp_server.server import (
    app,
    append_rows_to_table,
    create_namespace,
    create_table,
    create_table_bucket,
    get_bucket_metadata_config,
    get_maintenance_job_status,
    get_table_maintenance_config,
    get_table_metadata_location,
    import_csv_to_table,
    import_parquet_to_table,
    list_namespaces,
    list_table_buckets,
    list_tables,
    query_database,
    rename_table,
    update_table_metadata_location,
)
from unittest.mock import AsyncMock, patch


# Fixtures
@pytest.fixture(autouse=True)
def setup_app():
    """Set up app for each test."""
    app.allow_write = True
    yield
    app.allow_write = False


@pytest.fixture
def setup_app_readonly():
    """Set up app in read-only mode for testing write operation restrictions."""
    app.allow_write = False
    yield
    app.allow_write = False


@pytest.fixture
def mock_resources():
    """Mock resources module."""
    with patch('awslabs.s3_tables_mcp_server.server.resources') as mock:
        mock.list_table_buckets_resource = AsyncMock(
            return_value='{"table_buckets": [], "total_count": 0}'
        )
        mock.list_namespaces_resource = AsyncMock(
            return_value='{"namespaces": [], "total_count": 0}'
        )
        mock.list_tables_resource = AsyncMock(return_value='{"tables": [], "total_count": 0}')
        yield mock


@pytest.fixture
def mock_table_buckets():
    """Mock table_buckets module."""
    with patch('awslabs.s3_tables_mcp_server.server.table_buckets') as mock:
        mock.create_table_bucket = AsyncMock(return_value={'status': 'success'})
        yield mock


@pytest.fixture
def mock_namespaces():
    """Mock namespaces module."""
    with patch('awslabs.s3_tables_mcp_server.server.namespaces') as mock:
        mock.create_namespace = AsyncMock(return_value={'status': 'success'})
        yield mock


@pytest.fixture
def mock_tables():
    """Mock tables module."""
    with patch('awslabs.s3_tables_mcp_server.server.tables') as mock:
        mock.create_table = AsyncMock(return_value={'status': 'success'})
        mock.get_table_maintenance_configuration = AsyncMock(return_value={'status': 'success'})
        mock.get_table_maintenance_job_status = AsyncMock(return_value={'status': 'success'})
        mock.get_table_metadata_location = AsyncMock(return_value={'status': 'success'})
        mock.rename_table = AsyncMock(return_value={'status': 'success'})
        mock.update_table_metadata_location = AsyncMock(return_value={'status': 'success'})
        yield mock


@pytest.fixture(autouse=True)
def patch_log_tool_call():
    """Patch the log_tool_call function for all tests to suppress logging side effects."""
    with patch('awslabs.s3_tables_mcp_server.server.log_tool_call'):
        yield


@pytest.fixture
def mock_database():
    """Mock database module."""
    with patch('awslabs.s3_tables_mcp_server.server.database') as mock:
        mock.query_database_resource = AsyncMock(return_value={'status': 'success'})
        mock.append_rows_to_table_resource = AsyncMock(return_value={'status': 'success'})
        yield mock


@pytest.fixture
def mock_s3_operations():
    """Mock s3_operations module."""
    with patch('awslabs.s3_tables_mcp_server.server.s3_operations') as mock:
        mock.get_bucket_metadata_table_configuration = AsyncMock(
            return_value={'status': 'success'}
        )
        yield mock


# Resource Tests
@pytest.mark.asyncio
async def test_list_table_buckets(mock_resources):
    """Test list_table_buckets resource."""
    # Act
    result = await list_table_buckets()

    # Assert
    assert result == '{"table_buckets": [], "total_count": 0}'
    mock_resources.list_table_buckets_resource.assert_called_once()


@pytest.mark.asyncio
async def test_list_namespaces(mock_resources):
    """Test list_namespaces resource."""
    # Act
    result = await list_namespaces()

    # Assert
    assert result == '{"namespaces": [], "total_count": 0}'
    mock_resources.list_namespaces_resource.assert_called_once()


@pytest.mark.asyncio
async def test_list_tables(mock_resources):
    """Test list_tables resource."""
    # Act
    result = await list_tables()

    # Assert
    assert result == '{"tables": [], "total_count": 0}'
    mock_resources.list_tables_resource.assert_called_once()


# Tool Tests
@pytest.mark.asyncio
async def test_create_table_bucket(mock_table_buckets):
    """Test create_table_bucket tool."""
    # Arrange
    name = 'test-bucket'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await create_table_bucket(name=name, region_name=region)

    # Assert
    assert result == expected_response
    mock_table_buckets.create_table_bucket.assert_called_once_with(name=name, region_name=region)


@pytest.mark.asyncio
async def test_create_namespace(mock_namespaces):
    """Test create_namespace tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await create_namespace(
        table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_namespaces.create_namespace.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=region
    )


@pytest.mark.asyncio
async def test_create_table(mock_tables):
    """Test create_table tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    format = 'ICEBERG'
    metadata = TableMetadata(
        iceberg=IcebergMetadata(
            schema=IcebergSchema(
                fields=[
                    SchemaField(name='id', type='long', required=True),
                    SchemaField(name='name', type='string', required=True),
                ]
            )
        )
    )
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await create_table(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        format=format,
        metadata=metadata,
        region_name=region,
    )

    # Assert
    assert result == expected_response
    mock_tables.create_table.assert_called_once_with(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        format=OpenTableFormat.ICEBERG,
        metadata=metadata,
        region_name=region,
    )


@pytest.mark.asyncio
async def test_get_table_maintenance_config(mock_tables):
    """Test get_table_maintenance_config tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await get_table_maintenance_config(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_tables.get_table_maintenance_configuration.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )


@pytest.mark.asyncio
async def test_get_maintenance_job_status(mock_tables):
    """Test get_maintenance_job_status tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await get_maintenance_job_status(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_tables.get_table_maintenance_job_status.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )


@pytest.mark.asyncio
async def test_get_table_metadata_location(mock_tables):
    """Test get_table_metadata_location tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await get_table_metadata_location(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_tables.get_table_metadata_location.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )


@pytest.mark.asyncio
async def test_rename_table(mock_tables):
    """Test rename_table tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    new_name = 'new-table'
    new_namespace_name = 'new-namespace'
    version_token = 'test-version'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await rename_table(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        new_name=new_name,
        new_namespace_name=new_namespace_name,
        version_token=version_token,
        region_name=region,
    )

    # Assert
    assert result == expected_response
    mock_tables.rename_table.assert_called_once_with(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        new_name=new_name,
        new_namespace_name=new_namespace_name,
        version_token=version_token,
        region_name=region,
    )


@pytest.mark.asyncio
async def test_update_table_metadata_location(mock_tables):
    """Test update_table_metadata_location tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    metadata_location = 's3://test-bucket/metadata.json'
    version_token = 'test-version'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await update_table_metadata_location(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        metadata_location=metadata_location,
        version_token=version_token,
        region_name=region,
    )

    # Assert
    assert result == expected_response
    mock_tables.update_table_metadata_location.assert_called_once_with(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        metadata_location=metadata_location,
        version_token=version_token,
        region_name=region,
    )


# Write Operation Tests with allow_write disabled
@pytest.mark.asyncio
async def test_create_table_bucket_readonly_mode(setup_app_readonly, mock_table_buckets):
    """Test create_table_bucket tool when allow_write is disabled."""
    # Arrange
    name = 'test-bucket'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await create_table_bucket(name=name, region_name=region)


@pytest.mark.asyncio
async def test_create_namespace_readonly_mode(setup_app_readonly, mock_namespaces):
    """Test create_namespace tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await create_namespace(
            table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=region
        )


@pytest.mark.asyncio
async def test_create_table_readonly_mode(setup_app_readonly, mock_tables):
    """Test create_table tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    format = 'ICEBERG'
    metadata = TableMetadata(
        iceberg=IcebergMetadata(
            schema=IcebergSchema(
                fields=[
                    SchemaField(name='id', type='long', required=True),
                    SchemaField(name='name', type='string', required=True),
                ]
            )
        )
    )
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await create_table(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            name=name,
            format=format,
            metadata=metadata,
            region_name=region,
        )


@pytest.mark.asyncio
async def test_get_table_maintenance_config_readonly_mode(setup_app_readonly, mock_tables):
    """Test get_table_maintenance_config tool when allow_write is disabled (should still work)."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await get_table_maintenance_config(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_tables.get_table_maintenance_configuration.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )


@pytest.mark.asyncio
async def test_get_maintenance_job_status_readonly_mode(setup_app_readonly, mock_tables):
    """Test get_maintenance_job_status tool when allow_write is disabled (should still work)."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await get_maintenance_job_status(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_tables.get_table_maintenance_job_status.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )


@pytest.mark.asyncio
async def test_get_table_metadata_location_readonly_mode(setup_app_readonly, mock_tables):
    """Test get_table_metadata_location tool when allow_write is disabled (should still work)."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await get_table_metadata_location(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_tables.get_table_metadata_location.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )


@pytest.mark.asyncio
async def test_import_csv_to_table_readonly_mode(setup_app_readonly):
    """Test import_csv_to_table tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    s3_url = 's3://test-bucket/test.csv'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await import_csv_to_table(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            name=name,
            s3_url=s3_url,
            region_name=region,
        )


# New tests for uncovered tools


@pytest.mark.asyncio
async def test_query_database(mock_database):
    """Test query_database tool."""
    warehouse = 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
    region = 'us-west-2'
    namespace = 'test-namespace'
    query = 'SELECT * FROM test-table'
    uri = 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'
    expected_response = {'status': 'success'}

    result = await query_database(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        query=query,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
    )
    assert result == expected_response
    mock_database.query_database_resource.assert_called_once_with(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        query=query,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
    )


@pytest.mark.asyncio
async def test_get_bucket_metadata_config(mock_s3_operations):
    """Test get_bucket_metadata_config tool."""
    bucket = 'test-bucket'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    result = await get_bucket_metadata_config(bucket=bucket, region_name=region)
    assert result == expected_response
    mock_s3_operations.get_bucket_metadata_table_configuration.assert_called_once_with(
        bucket=bucket, region_name=region
    )


@pytest.mark.asyncio
async def test_append_rows_to_table(mock_database):
    """Test append_rows_to_table tool."""
    warehouse = 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
    region = 'us-west-2'
    namespace = 'test-namespace'
    table_name = 'test-table'
    rows = [{'id': 1, 'name': 'Alice'}]
    uri = 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'
    expected_response = {'status': 'success'}

    result = await append_rows_to_table(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        rows=rows,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
    )
    assert result == expected_response
    mock_database.append_rows_to_table_resource.assert_called_once_with(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        rows=rows,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
    )


def test_append_rows_to_table_readonly_mode(setup_app_readonly, mock_database):
    """Test append_rows_to_table tool when allow_write is disabled."""
    warehouse = 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
    region = 'us-west-2'
    namespace = 'test-namespace'
    table_name = 'test-table'
    rows = [{'id': 1, 'name': 'Alice'}]
    uri = 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'

    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        # Must be awaited in an event loop
        import asyncio

        asyncio.get_event_loop().run_until_complete(
            append_rows_to_table(
                warehouse=warehouse,
                region=region,
                namespace=namespace,
                table_name=table_name,
                rows=rows,
                uri=uri,
                catalog_name=catalog_name,
                rest_signing_name=rest_signing_name,
                rest_sigv4_enabled=rest_sigv4_enabled,
            )
        )


@pytest.mark.asyncio
async def test_query_database_default_uri(mock_database):
    """Test query_database uses default uri if None."""
    warehouse = 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
    region = 'us-west-2'
    namespace = 'test-namespace'
    query = 'SELECT * FROM test-table'
    await query_database(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        query=query,
        uri=None,
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )
    args, kwargs = mock_database.query_database_resource.call_args
    assert kwargs['uri'] == 'https://s3tables.us-west-2.amazonaws.com/iceberg'


@pytest.mark.asyncio
async def test_import_csv_to_table_default_uri(monkeypatch, setup_app):
    """Test import_csv_to_table uses default uri if None."""
    import awslabs.s3_tables_mcp_server.server as server_mod

    # Mock the imported function from file_processor module
    mock_import_func = AsyncMock(return_value={'status': 'success'})
    monkeypatch.setattr(
        'awslabs.s3_tables_mcp_server.server.import_csv_to_table_func',
        mock_import_func,
    )
    warehouse = 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
    region = 'us-west-2'
    namespace = 'test-namespace'
    table_name = 'test-table'
    s3_url = 's3://bucket/file.csv'
    await server_mod.import_csv_to_table(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        s3_url=s3_url,
        uri=None,
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )
    args, kwargs = mock_import_func.call_args  # type: ignore
    assert kwargs['uri'] == 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    assert not kwargs['preserve_case']


@pytest.mark.asyncio
async def test_import_csv_to_table(monkeypatch, setup_app):
    """Test import_csv_to_table tool."""
    import awslabs.s3_tables_mcp_server.server as server_mod

    # Mock the imported function from file_processor module
    mock_import_func = AsyncMock(return_value={'status': 'success'})
    monkeypatch.setattr(
        'awslabs.s3_tables_mcp_server.server.import_csv_to_table_func',
        mock_import_func,
    )
    warehouse = 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
    region = 'us-west-2'
    namespace = 'test-namespace'
    table_name = 'test-table'
    s3_url = 's3://bucket/file.csv'
    uri = 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'
    expected_response = {'status': 'success'}

    result = await server_mod.import_csv_to_table(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        s3_url=s3_url,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
    )
    assert result == expected_response
    mock_import_func.assert_called_once_with(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        s3_url=s3_url,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
        preserve_case=False,
    )


@pytest.mark.asyncio
async def test_import_parquet_to_table(monkeypatch, setup_app):
    """Test import_parquet_to_table tool."""
    import awslabs.s3_tables_mcp_server.server as server_mod

    # Mock the imported function from file_processor module
    mock_import_func = AsyncMock(return_value={'status': 'success'})
    monkeypatch.setattr(
        'awslabs.s3_tables_mcp_server.server.import_parquet_to_table_func',
        mock_import_func,
    )
    warehouse = 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
    region = 'us-west-2'
    namespace = 'test-namespace'
    table_name = 'test-table'
    s3_url = 's3://bucket/file.parquet'
    uri = 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    catalog_name = 's3tablescatalog'
    rest_signing_name = 's3tables'
    rest_sigv4_enabled = 'true'
    expected_response = {'status': 'success'}

    result = await server_mod.import_parquet_to_table(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        s3_url=s3_url,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
    )
    assert result == expected_response
    mock_import_func.assert_called_once_with(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        s3_url=s3_url,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
        preserve_case=False,
    )


@pytest.mark.asyncio
async def test_import_parquet_to_table_readonly_mode(setup_app_readonly):
    """Test import_parquet_to_table tool when allow_write is disabled."""
    # Arrange
    warehouse = 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
    region = 'us-west-2'
    namespace = 'test-namespace'
    table_name = 'test-table'
    s3_url = 's3://bucket/file.parquet'
    uri = 'https://s3tables.us-west-2.amazonaws.com/iceberg'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await import_parquet_to_table(
            warehouse=warehouse,
            region=region,
            namespace=namespace,
            table_name=table_name,
            s3_url=s3_url,
            uri=uri,
        )


@pytest.mark.asyncio
async def test_import_parquet_to_table_default_uri(monkeypatch, setup_app):
    """Test import_parquet_to_table uses default uri if None."""
    import awslabs.s3_tables_mcp_server.server as server_mod

    # Mock the imported function from file_processor module
    mock_import_func = AsyncMock(return_value={'status': 'success'})
    monkeypatch.setattr(
        'awslabs.s3_tables_mcp_server.server.import_parquet_to_table_func',
        mock_import_func,
    )
    warehouse = 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
    region = 'us-west-2'
    namespace = 'test-namespace'
    table_name = 'test-table'
    s3_url = 's3://bucket/file.parquet'
    await server_mod.import_parquet_to_table(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        s3_url=s3_url,
        uri=None,
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )
    args, kwargs = mock_import_func.call_args  # type: ignore
    assert kwargs['uri'] == 'https://s3tables.us-west-2.amazonaws.com/iceberg'
    assert not kwargs['preserve_case']


@pytest.mark.asyncio
async def test_append_rows_to_table_default_uri(mock_database):
    """Test append_rows_to_table uses default uri if None."""
    warehouse = 'arn:aws:s3tables:us-west-2:123456789012:bucket/test-bucket'
    region = 'us-west-2'
    namespace = 'test-namespace'
    table_name = 'test-table'
    rows = [{'id': 1, 'name': 'Alice'}]
    await append_rows_to_table(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        rows=rows,
        uri=None,
        catalog_name='s3tablescatalog',
        rest_signing_name='s3tables',
        rest_sigv4_enabled='true',
    )
    args, kwargs = mock_database.append_rows_to_table_resource.call_args
    assert kwargs['uri'] == 'https://s3tables.us-west-2.amazonaws.com/iceberg'


def test_main_sets_log_dir(monkeypatch):
    """Test main sets log_dir if --log-dir is provided."""
    import awslabs.s3_tables_mcp_server.server as server_mod

    monkeypatch.setattr(sys, 'argv', ['prog', '--allow-write', '--log-dir', '~/mylogs'])
    monkeypatch.setattr(server_mod.app, 'run', lambda: None)
    monkeypatch.setattr(server_mod, 'log_tool_call', lambda *a, **k: None)
    server_mod.main()
    assert server_mod.app.log_dir == os.path.expanduser('~/mylogs')


def test_main_entry(monkeypatch):
    """Test main entrypoint logic is callable and triggers app.run."""
    import awslabs.s3_tables_mcp_server.server as server_mod

    monkeypatch.setattr(server_mod.app, 'run', lambda: setattr(server_mod, '_main_called', True))
    monkeypatch.setattr(server_mod, 'log_tool_call', lambda *a, **k: None)
    monkeypatch.setattr(sys, 'argv', ['prog'])
    server_mod.main()
    assert getattr(server_mod, '_main_called', False)


@pytest.mark.asyncio
async def test_create_table_bucket_invalid_region(mock_table_buckets):
    """Test create_table_bucket tool with invalid region_name."""
    name = 'test-bucket'
    region = 'bad-region'
    mock_table_buckets.create_table_bucket.side_effect = Exception('Invalid region')
    with pytest.raises(Exception, match='Invalid region'):
        await create_table_bucket(name=name, region_name=region)


@pytest.mark.asyncio
async def test_create_table_bucket_default_region(mock_table_buckets):
    """Test create_table_bucket tool with default (None) region_name."""
    name = 'test-bucket'
    expected_response = {'status': 'success'}
    result = await create_table_bucket(name=name, region_name=None)
    assert result == expected_response
    mock_table_buckets.create_table_bucket.assert_called_with(name=name, region_name=None)


@pytest.mark.asyncio
async def test_create_namespace_invalid_region(mock_namespaces):
    """Test create_namespace tool with invalid region_name."""
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    region = 'bad-region'
    mock_namespaces.create_namespace.side_effect = Exception('Invalid region')
    with pytest.raises(Exception, match='Invalid region'):
        await create_namespace(
            table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=region
        )


@pytest.mark.asyncio
async def test_create_namespace_default_region(mock_namespaces):
    """Test create_namespace tool with default (None) region_name."""
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    expected_response = {'status': 'success'}
    result = await create_namespace(
        table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=None
    )
    assert result == expected_response
    mock_namespaces.create_namespace.assert_called_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=None
    )


@pytest.mark.asyncio
async def test_create_table_invalid_region(mock_tables):
    """Test create_table tool with invalid region_name."""
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    format = 'ICEBERG'
    metadata = TableMetadata(
        iceberg=IcebergMetadata(
            schema=IcebergSchema(
                fields=[
                    SchemaField(name='id', type='long', required=True),
                    SchemaField(name='name', type='string', required=True),
                ]
            )
        )
    )
    region = 'bad-region'
    mock_tables.create_table.side_effect = Exception('Invalid region')
    with pytest.raises(Exception, match='Invalid region'):
        await create_table(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            name=name,
            format=format,
            metadata=metadata,
            region_name=region,
        )


@pytest.mark.asyncio
async def test_create_table_default_region(mock_tables):
    """Test create_table tool with default (None) region_name."""
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    format = 'ICEBERG'
    metadata = TableMetadata(
        iceberg=IcebergMetadata(
            schema=IcebergSchema(
                fields=[
                    SchemaField(name='id', type='long', required=True),
                    SchemaField(name='name', type='string', required=True),
                ]
            )
        )
    )
    expected_response = {'status': 'success'}
    result = await create_table(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        format=format,
        metadata=metadata,
        region_name=None,
    )
    assert result == expected_response
    mock_tables.create_table.assert_called_with(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        format=OpenTableFormat.ICEBERG,
        metadata=metadata,
        region_name=None,
    )
