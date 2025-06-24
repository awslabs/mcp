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

"""Tests for the tables module."""

import pytest
from awslabs.s3_tables_mcp_server.models import (
    IcebergMetadata,
    IcebergSchema,
    MaintenanceStatus,
    OpenTableFormat,
    SchemaField,
    TableMaintenanceConfigurationValue,
    TableMaintenanceType,
    TableMetadata,
)
from awslabs.s3_tables_mcp_server.tables import (
    create_table,
    delete_table,
    delete_table_policy,
    get_table,
    get_table_maintenance_configuration,
    get_table_maintenance_job_status,
    get_table_metadata_location,
    get_table_policy,
    put_table_maintenance_configuration,
    rename_table,
    update_table_metadata_location,
)
from unittest.mock import MagicMock, patch


class TestCreateTable:
    """Test the create_table function."""

    @pytest.mark.asyncio
    async def test_successful_table_creation(self):
        """Test successful table creation."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        format = OpenTableFormat.ICEBERG
        region = 'us-west-2'
        expected_response = {
            'table': {
                'name': 'test-table',
                'namespace': 'test-namespace',
                'createdAt': '2023-01-01T00:00:00Z',
            }
        }

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_table.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await create_table(
                table_bucket_arn, namespace, name, format, region_name=region
            )

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.create_table.assert_called_once_with(
                tableBucketARN=table_bucket_arn,
                namespace=namespace,
                name=name,
                format=format.value,
            )

    @pytest.mark.asyncio
    async def test_successful_table_creation_with_metadata(self):
        """Test successful table creation with metadata."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        format = OpenTableFormat.ICEBERG

        # Create metadata
        schema_field = SchemaField(name='id', type='int', required=True)
        schema = IcebergSchema(fields=[schema_field])
        metadata = TableMetadata(iceberg=IcebergMetadata(schema=schema))

        expected_response = {
            'table': {
                'name': 'test-table',
                'namespace': 'test-namespace',
                'metadata': metadata.model_dump(by_alias=True, exclude_none=True),
            }
        }

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_table.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await create_table(table_bucket_arn, namespace, name, format, metadata)

            # Assert
            assert result == expected_response
            call_args = mock_client.create_table.call_args
            assert call_args[1]['metadata'] == metadata.model_dump(
                by_alias=True, exclude_none=True
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        format = OpenTableFormat.ICEBERG
        error_message = 'Table already exists'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_table.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await create_table(table_bucket_arn, namespace, name, format)

            # Assert
            assert result == {'error': error_message, 'tool': 'create_table'}


class TestDeleteTable:
    """Test the delete_table function."""

    @pytest.mark.asyncio
    async def test_successful_table_deletion(self):
        """Test successful table deletion."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        region = 'us-west-2'
        expected_response = {'status': 'success', 'message': 'Table deleted successfully'}

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table(table_bucket_arn, namespace, name, region_name=region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.delete_table.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=namespace, name=name
            )

    @pytest.mark.asyncio
    async def test_successful_table_deletion_with_version_token(self):
        """Test successful table deletion with version token."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        version_token = 'test-version-token'
        expected_response = {'status': 'success'}

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table(table_bucket_arn, namespace, name, version_token)

            # Assert
            assert result == expected_response
            call_args = mock_client.delete_table.call_args
            assert call_args[1]['versionToken'] == version_token

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        error_message = 'Table not found'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table(table_bucket_arn, namespace, name)

            # Assert
            assert result == {'error': error_message, 'tool': 'delete_table'}


class TestGetTable:
    """Test the get_table function."""

    @pytest.mark.asyncio
    async def test_successful_table_retrieval(self):
        """Test successful table retrieval."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        region = 'us-west-2'
        expected_response = {
            'table': {
                'name': 'test-table',
                'namespace': 'test-namespace',
                'createdAt': '2023-01-01T00:00:00Z',
                'ownerAccountId': '123456789012',
            }
        }

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table(table_bucket_arn, namespace, name, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.get_table.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=namespace, name=name
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        error_message = 'Table not found'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table(table_bucket_arn, namespace, name)

            # Assert
            assert result == {'error': error_message, 'tool': 'get_table'}


class TestDeleteTablePolicy:
    """Test the delete_table_policy function."""

    @pytest.mark.asyncio
    async def test_successful_policy_deletion(self):
        """Test successful table policy deletion."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        region = 'us-west-2'
        expected_response = {'status': 'success', 'message': 'Policy deleted successfully'}

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table_policy.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table_policy(table_bucket_arn, namespace, name, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.delete_table_policy.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=namespace, name=name
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        error_message = 'Policy not found'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table_policy.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table_policy(table_bucket_arn, namespace, name)

            # Assert
            assert result == {'error': error_message, 'tool': 'delete_table_policy'}


class TestGetTableMaintenanceConfiguration:
    """Test the get_table_maintenance_configuration function."""

    @pytest.mark.asyncio
    async def test_successful_maintenance_configuration_retrieval(self):
        """Test successful maintenance configuration retrieval."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        region = 'us-west-2'
        expected_response = {
            'maintenanceConfiguration': {
                'type': 'COMPACTION',
                'value': {'enabled': True, 'scheduleExpression': 'cron(0 2 * * ? *)'},
            }
        }

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_maintenance_configuration.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_maintenance_configuration(
                table_bucket_arn, namespace, name, region
            )

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.get_table_maintenance_configuration.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=namespace, name=name
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        error_message = 'Maintenance configuration not found'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_maintenance_configuration.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_maintenance_configuration(table_bucket_arn, namespace, name)

            # Assert
            assert result == {
                'error': error_message,
                'tool': 'get_table_maintenance_configuration',
            }


class TestGetTableMaintenanceJobStatus:
    """Test the get_table_maintenance_job_status function."""

    @pytest.mark.asyncio
    async def test_successful_job_status_retrieval(self):
        """Test successful maintenance job status retrieval."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        region = 'us-west-2'
        expected_response = {
            'maintenanceJobStatus': {'status': 'RUNNING', 'startedAt': '2023-01-01T00:00:00Z'}
        }

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_maintenance_job_status.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_maintenance_job_status(
                table_bucket_arn, namespace, name, region
            )

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.get_table_maintenance_job_status.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=namespace, name=name
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        error_message = 'Maintenance job not found'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_maintenance_job_status.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_maintenance_job_status(table_bucket_arn, namespace, name)

            # Assert
            assert result == {'error': error_message, 'tool': 'get_table_maintenance_job_status'}


class TestGetTableMetadataLocation:
    """Test the get_table_metadata_location function."""

    @pytest.mark.asyncio
    async def test_successful_metadata_location_retrieval(self):
        """Test successful metadata location retrieval."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        region = 'us-west-2'
        expected_response = {'metadataLocation': 's3://test-bucket/metadata/table-metadata.json'}

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_metadata_location.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_metadata_location(table_bucket_arn, namespace, name, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.get_table_metadata_location.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=namespace, name=name
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        error_message = 'Metadata location not found'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_metadata_location.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_metadata_location(table_bucket_arn, namespace, name)

            # Assert
            assert result == {'error': error_message, 'tool': 'get_table_metadata_location'}


class TestGetTablePolicy:
    """Test the get_table_policy function."""

    @pytest.mark.asyncio
    async def test_successful_policy_retrieval(self):
        """Test successful table policy retrieval."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        region = 'us-west-2'
        expected_response = {
            'policy': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Principal': {'AWS': 'arn:aws:iam::123456789012:root'},
                        'Action': 's3tables:*',
                        'Resource': f'{table_bucket_arn}/table/{namespace}/{name}',
                    }
                ],
            }
        }

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_policy.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_policy(table_bucket_arn, namespace, name, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.get_table_policy.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=namespace, name=name
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        error_message = 'Policy not found'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_policy.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_policy(table_bucket_arn, namespace, name)

            # Assert
            assert result == {'error': error_message, 'tool': 'get_table_policy'}


class TestPutTableMaintenanceConfiguration:
    """Test the put_table_maintenance_configuration function."""

    @pytest.mark.asyncio
    async def test_successful_maintenance_configuration_put(self):
        """Test successful maintenance configuration put."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        maintenance_type = TableMaintenanceType.ICEBERG_COMPACTION
        value = TableMaintenanceConfigurationValue(status=MaintenanceStatus.ENABLED)
        region = 'us-west-2'
        expected_response = {'status': 'success', 'message': 'Maintenance configuration updated'}

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.put_table_maintenance_configuration.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await put_table_maintenance_configuration(
                table_bucket_arn, namespace, name, maintenance_type, value, region
            )

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.put_table_maintenance_configuration.assert_called_once()
            call_args = mock_client.put_table_maintenance_configuration.call_args
            assert call_args[1]['tableBucketARN'] == table_bucket_arn
            assert call_args[1]['namespace'] == namespace
            assert call_args[1]['name'] == name
            assert call_args[1]['type'] == maintenance_type.value
            assert call_args[1]['value'] == value.model_dump(by_alias=True, exclude_none=True)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        maintenance_type = TableMaintenanceType.ICEBERG_COMPACTION
        value = TableMaintenanceConfigurationValue(status=MaintenanceStatus.ENABLED)
        error_message = 'Invalid maintenance configuration'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.put_table_maintenance_configuration.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await put_table_maintenance_configuration(
                table_bucket_arn, namespace, name, maintenance_type, value
            )

            # Assert
            assert result == {
                'error': error_message,
                'tool': 'put_table_maintenance_configuration',
            }


class TestRenameTable:
    """Test the rename_table function."""

    @pytest.mark.asyncio
    async def test_successful_table_rename(self):
        """Test successful table rename."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'old-table-name'
        new_name = 'new-table-name'
        region = 'us-west-2'
        expected_response = {'table': {'name': 'new-table-name', 'namespace': 'test-namespace'}}

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.rename_table.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await rename_table(
                table_bucket_arn, namespace, name, new_name, region_name=region
            )

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.rename_table.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=namespace, name=name, newName=new_name
            )

    @pytest.mark.asyncio
    async def test_successful_table_rename_with_new_namespace(self):
        """Test successful table rename with new namespace."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'old-namespace'
        name = 'old-table-name'
        new_name = 'new-table-name'
        new_namespace_name = 'new-namespace'
        version_token = 'test-version-token'
        expected_response = {'status': 'success'}

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.rename_table.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await rename_table(
                table_bucket_arn, namespace, name, new_name, new_namespace_name, version_token
            )

            # Assert
            assert result == expected_response
            call_args = mock_client.rename_table.call_args
            assert call_args[1]['newNamespaceName'] == new_namespace_name
            assert call_args[1]['versionToken'] == version_token

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'old-table-name'
        new_name = 'new-table-name'
        error_message = 'Table not found'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.rename_table.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await rename_table(table_bucket_arn, namespace, name, new_name)

            # Assert
            assert result == {'error': error_message, 'tool': 'rename_table'}


class TestUpdateTableMetadataLocation:
    """Test the update_table_metadata_location function."""

    @pytest.mark.asyncio
    async def test_successful_metadata_location_update(self):
        """Test successful metadata location update."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        metadata_location = 's3://test-bucket/metadata/new-metadata.json'
        version_token = 'test-version-token'
        region = 'us-west-2'
        expected_response = {'status': 'success', 'message': 'Metadata location updated'}

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.update_table_metadata_location.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await update_table_metadata_location(
                table_bucket_arn, namespace, name, metadata_location, version_token, region
            )

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.update_table_metadata_location.assert_called_once_with(
                tableBucketARN=table_bucket_arn,
                namespace=namespace,
                name=name,
                metadataLocation=metadata_location,
                versionToken=version_token,
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        name = 'test-table'
        metadata_location = 's3://test-bucket/metadata/new-metadata.json'
        version_token = 'test-version-token'
        error_message = 'Invalid metadata location'

        with patch('awslabs.s3_tables_mcp_server.tables.get_s3tables_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.update_table_metadata_location.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await update_table_metadata_location(
                table_bucket_arn, namespace, name, metadata_location, version_token
            )

            # Assert
            assert result == {'error': error_message, 'tool': 'update_table_metadata_location'}
