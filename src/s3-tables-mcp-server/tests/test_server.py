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

import pytest
from awslabs.s3_tables_mcp_server.models import (
    IcebergMetadata,
    IcebergSchema,
    MaintenanceStatus,
    OpenTableFormat,
    SchemaField,
    TableBucketMaintenanceConfigurationValue,
    TableBucketMaintenanceType,
    TableMaintenanceConfigurationValue,
    TableMaintenanceType,
    TableMetadata,
)
from awslabs.s3_tables_mcp_server.server import (
    app,
    create_namespace,
    create_table,
    create_table_bucket,
    delete_namespace,
    delete_table,
    delete_table_bucket,
    delete_table_bucket_policy,
    delete_table_policy,
    get_table_maintenance_configuration,
    get_table_maintenance_job_status,
    get_table_metadata_location,
    get_table_policy,
    import_csv_to_table,
    list_namespaces,
    list_table_buckets,
    list_tables,
    modify_database,
    put_table_bucket_maintenance_configuration,
    put_table_bucket_policy,
    put_table_maintenance_configuration,
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
        mock.delete_table_bucket = AsyncMock(return_value={'status': 'success'})
        mock.put_table_bucket_maintenance_configuration = AsyncMock(
            return_value={'status': 'success'}
        )
        mock.put_table_bucket_policy = AsyncMock(return_value={'status': 'success'})
        mock.delete_table_bucket_policy = AsyncMock(return_value={'status': 'success'})
        yield mock


@pytest.fixture
def mock_namespaces():
    """Mock namespaces module."""
    with patch('awslabs.s3_tables_mcp_server.server.namespaces') as mock:
        mock.create_namespace = AsyncMock(return_value={'status': 'success'})
        mock.delete_namespace = AsyncMock(return_value={'status': 'success'})
        yield mock


@pytest.fixture
def mock_tables():
    """Mock tables module."""
    with patch('awslabs.s3_tables_mcp_server.server.tables') as mock:
        mock.create_table = AsyncMock(return_value={'status': 'success'})
        mock.delete_table = AsyncMock(return_value={'status': 'success'})
        mock.delete_table_policy = AsyncMock(return_value={'status': 'success'})
        mock.get_table_maintenance_configuration = AsyncMock(return_value={'status': 'success'})
        mock.get_table_maintenance_job_status = AsyncMock(return_value={'status': 'success'})
        mock.get_table_metadata_location = AsyncMock(return_value={'status': 'success'})
        mock.get_table_policy = AsyncMock(return_value={'status': 'success'})
        mock.put_table_maintenance_configuration = AsyncMock(return_value={'status': 'success'})
        mock.rename_table = AsyncMock(return_value={'status': 'success'})
        mock.update_table_metadata_location = AsyncMock(return_value={'status': 'success'})
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
async def test_delete_table_bucket(mock_table_buckets):
    """Test delete_table_bucket tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await delete_table_bucket(table_bucket_arn=table_bucket_arn, region_name=region)

    # Assert
    assert result == expected_response
    mock_table_buckets.delete_table_bucket.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, region_name=region
    )


@pytest.mark.asyncio
async def test_delete_namespace(mock_namespaces):
    """Test delete_namespace tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await delete_namespace(
        table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_namespaces.delete_namespace.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=region
    )


@pytest.mark.asyncio
async def test_delete_table(mock_tables):
    """Test delete_table tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    version_token = 'test-version'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await delete_table(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        version_token=version_token,
        region_name=region,
    )

    # Assert
    assert result == expected_response
    mock_tables.delete_table.assert_called_once_with(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        version_token=version_token,
        region_name=region,
    )


@pytest.mark.asyncio
async def test_put_table_bucket_maintenance_configuration(mock_table_buckets):
    """Test put_table_bucket_maintenance_configuration tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    maintenance_type = TableBucketMaintenanceType.ICEBERG_UNREFERENCED_FILE_REMOVAL
    value = TableBucketMaintenanceConfigurationValue(
        status=MaintenanceStatus.ENABLED, settings=None
    )
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await put_table_bucket_maintenance_configuration(
        table_bucket_arn=table_bucket_arn,
        maintenance_type=maintenance_type,
        value=value,
        region_name=region,
    )

    # Assert
    assert result == expected_response
    mock_table_buckets.put_table_bucket_maintenance_configuration.assert_called_once_with(
        table_bucket_arn=table_bucket_arn,
        maintenance_type=maintenance_type,
        value=value,
        region_name=region,
    )


@pytest.mark.asyncio
async def test_put_table_bucket_policy(mock_table_buckets):
    """Test put_table_bucket_policy tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    resource_policy = '{"Version": "2012-10-17", "Statement": []}'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await put_table_bucket_policy(
        table_bucket_arn=table_bucket_arn, resource_policy=resource_policy, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_table_buckets.put_table_bucket_policy.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, resource_policy=resource_policy, region_name=region
    )


@pytest.mark.asyncio
async def test_delete_table_bucket_policy(mock_table_buckets):
    """Test delete_table_bucket_policy tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await delete_table_bucket_policy(
        table_bucket_arn=table_bucket_arn, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_table_buckets.delete_table_bucket_policy.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, region_name=region
    )


@pytest.mark.asyncio
async def test_delete_table_policy(mock_tables):
    """Test delete_table_policy tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await delete_table_policy(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_tables.delete_table_policy.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )


@pytest.mark.asyncio
async def test_get_table_maintenance_configuration(mock_tables):
    """Test get_table_maintenance_configuration tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await get_table_maintenance_configuration(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_tables.get_table_maintenance_configuration.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )


@pytest.mark.asyncio
async def test_get_table_maintenance_job_status(mock_tables):
    """Test get_table_maintenance_job_status tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await get_table_maintenance_job_status(
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
async def test_get_table_policy(mock_tables):
    """Test get_table_policy tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await get_table_policy(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )

    # Assert
    assert result == expected_response
    mock_tables.get_table_policy.assert_called_once_with(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
    )


@pytest.mark.asyncio
async def test_put_table_maintenance_configuration(mock_tables):
    """Test put_table_maintenance_configuration tool."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    maintenance_type = TableMaintenanceType.ICEBERG_COMPACTION
    value = TableMaintenanceConfigurationValue(status=MaintenanceStatus.ENABLED, settings=None)
    region = 'us-west-2'
    expected_response = {'status': 'success'}

    # Act
    result = await put_table_maintenance_configuration(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        maintenance_type=maintenance_type,
        value=value,
        region_name=region,
    )

    # Assert
    assert result == expected_response
    mock_tables.put_table_maintenance_configuration.assert_called_once_with(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        maintenance_type=maintenance_type,
        value=value,
        region_name=region,
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
async def test_delete_table_bucket_readonly_mode(setup_app_readonly, mock_table_buckets):
    """Test delete_table_bucket tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await delete_table_bucket(table_bucket_arn=table_bucket_arn, region_name=region)


@pytest.mark.asyncio
async def test_delete_namespace_readonly_mode(setup_app_readonly, mock_namespaces):
    """Test delete_namespace tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await delete_namespace(
            table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=region
        )


@pytest.mark.asyncio
async def test_delete_table_readonly_mode(setup_app_readonly, mock_tables):
    """Test delete_table tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    version_token = 'test-version'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await delete_table(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            name=name,
            version_token=version_token,
            region_name=region,
        )


@pytest.mark.asyncio
async def test_put_table_bucket_maintenance_configuration_readonly_mode(
    setup_app_readonly, mock_table_buckets
):
    """Test put_table_bucket_maintenance_configuration tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    maintenance_type = TableBucketMaintenanceType.ICEBERG_UNREFERENCED_FILE_REMOVAL
    value = TableBucketMaintenanceConfigurationValue(
        status=MaintenanceStatus.ENABLED, settings=None
    )
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await put_table_bucket_maintenance_configuration(
            table_bucket_arn=table_bucket_arn,
            maintenance_type=maintenance_type,
            value=value,
            region_name=region,
        )


@pytest.mark.asyncio
async def test_put_table_bucket_policy_readonly_mode(setup_app_readonly, mock_table_buckets):
    """Test put_table_bucket_policy tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    resource_policy = '{"Version": "2012-10-17", "Statement": []}'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await put_table_bucket_policy(
            table_bucket_arn=table_bucket_arn, resource_policy=resource_policy, region_name=region
        )


@pytest.mark.asyncio
async def test_delete_table_bucket_policy_readonly_mode(setup_app_readonly, mock_table_buckets):
    """Test delete_table_bucket_policy tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await delete_table_bucket_policy(table_bucket_arn=table_bucket_arn, region_name=region)


@pytest.mark.asyncio
async def test_delete_table_policy_readonly_mode(setup_app_readonly, mock_tables):
    """Test delete_table_policy tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await delete_table_policy(
            table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
        )


@pytest.mark.asyncio
async def test_get_table_maintenance_configuration_readonly_mode(setup_app_readonly, mock_tables):
    """Test get_table_maintenance_configuration tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await get_table_maintenance_configuration(
            table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
        )


@pytest.mark.asyncio
async def test_get_table_maintenance_job_status_readonly_mode(setup_app_readonly, mock_tables):
    """Test get_table_maintenance_job_status tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await get_table_maintenance_job_status(
            table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
        )


@pytest.mark.asyncio
async def test_get_table_metadata_location_readonly_mode(setup_app_readonly, mock_tables):
    """Test get_table_metadata_location tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await get_table_metadata_location(
            table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
        )


@pytest.mark.asyncio
async def test_get_table_policy_readonly_mode(setup_app_readonly, mock_tables):
    """Test get_table_policy tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await get_table_policy(
            table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region
        )


@pytest.mark.asyncio
async def test_put_table_maintenance_configuration_readonly_mode(setup_app_readonly, mock_tables):
    """Test put_table_maintenance_configuration tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    maintenance_type = TableMaintenanceType.ICEBERG_COMPACTION
    value = TableMaintenanceConfigurationValue(status=MaintenanceStatus.ENABLED, settings=None)
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await put_table_maintenance_configuration(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            name=name,
            maintenance_type=maintenance_type,
            value=value,
            region_name=region,
        )


@pytest.mark.asyncio
async def test_rename_table_readonly_mode(setup_app_readonly, mock_tables):
    """Test rename_table tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    new_name = 'new-table'
    new_namespace_name = 'new-namespace'
    version_token = 'test-version'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await rename_table(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            name=name,
            new_name=new_name,
            new_namespace_name=new_namespace_name,
            version_token=version_token,
            region_name=region,
        )


@pytest.mark.asyncio
async def test_update_table_metadata_location_readonly_mode(setup_app_readonly, mock_tables):
    """Test update_table_metadata_location tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    name = 'test-table'
    metadata_location = 's3://test-bucket/metadata.json'
    version_token = 'test-version'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await update_table_metadata_location(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            name=name,
            metadata_location=metadata_location,
            version_token=version_token,
            region_name=region,
        )


@pytest.mark.asyncio
async def test_modify_database_readonly_mode(setup_app_readonly):
    """Test modify_database tool when allow_write is disabled."""
    # Arrange
    table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
    namespace = 'test-namespace'
    query = 'INSERT INTO test_table VALUES (1, "test")'
    region = 'us-west-2'

    # Act & Assert
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await modify_database(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
            region_name=region,
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
