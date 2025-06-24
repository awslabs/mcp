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

"""Tests for the table_buckets module."""

import pytest
from awslabs.s3_tables_mcp_server.models import (
    MaintenanceStatus,
    TableBucketMaintenanceConfigurationValue,
    TableBucketMaintenanceType,
)
from awslabs.s3_tables_mcp_server.table_buckets import (
    create_table_bucket,
    delete_table_bucket,
    delete_table_bucket_policy,
    get_table_bucket,
    get_table_bucket_maintenance_configuration,
    get_table_bucket_policy,
    put_table_bucket_maintenance_configuration,
)
from unittest.mock import MagicMock, patch


class TestCreateTableBucket:
    """Test the create_table_bucket function."""

    @pytest.mark.asyncio
    async def test_successful_table_bucket_creation(self):
        """Test successful table bucket creation."""
        # Arrange
        name = 'test-bucket'
        region = 'us-west-2'
        expected_response = {
            'tableBucket': {
                'arn': 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket',
                'name': 'test-bucket',
                'createdAt': '2023-01-01T00:00:00Z',
            }
        }

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_table_bucket.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await create_table_bucket(name, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.create_table_bucket.assert_called_once_with(name=name)

    @pytest.mark.asyncio
    async def test_successful_table_bucket_creation_with_default_region(self):
        """Test successful table bucket creation with default region."""
        # Arrange
        name = 'test-bucket'
        expected_response = {
            'tableBucket': {
                'arn': 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket',
                'name': 'test-bucket',
            }
        }

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_table_bucket.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await create_table_bucket(name)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        name = 'test-bucket'
        error_message = 'Bucket name already exists'

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_table_bucket.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await create_table_bucket(name)

            # Assert
            assert result == {'error': error_message, 'tool': 'create_table_bucket'}

    @pytest.mark.asyncio
    async def test_complex_bucket_name(self):
        """Test table bucket creation with complex bucket name."""
        # Arrange
        name = 'complex-bucket-name-with-dashes-and-underscores'
        region = 'us-east-1'

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_table_bucket.return_value = {'tableBucket': {'name': name}}
            mock_get_client.return_value = mock_client

            # Act
            result = await create_table_bucket(name, region)

            # Assert
            assert result == {'tableBucket': {'name': name}}
            mock_client.create_table_bucket.assert_called_once_with(name=name)


class TestDeleteTableBucket:
    """Test the delete_table_bucket function."""

    @pytest.mark.asyncio
    async def test_successful_table_bucket_deletion(self):
        """Test successful table bucket deletion."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        region = 'us-west-2'
        expected_response = {'status': 'success', 'message': 'Table bucket deleted successfully'}

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table_bucket.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table_bucket(table_bucket_arn, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.delete_table_bucket.assert_called_once_with(
                tableBucketARN=table_bucket_arn
            )

    @pytest.mark.asyncio
    async def test_successful_table_bucket_deletion_with_default_region(self):
        """Test successful table bucket deletion with default region."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        expected_response = {'status': 'success'}

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table_bucket.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table_bucket(table_bucket_arn)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        error_message = 'Table bucket not found'

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table_bucket.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table_bucket(table_bucket_arn)

            # Assert
            assert result == {'error': error_message, 'tool': 'delete_table_bucket'}


class TestPutTableBucketMaintenanceConfiguration:
    """Test the put_table_bucket_maintenance_configuration function."""

    @pytest.mark.asyncio
    async def test_successful_maintenance_configuration_put(self):
        """Test successful maintenance configuration put."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        maintenance_type = TableBucketMaintenanceType.ICEBERG_UNREFERENCED_FILE_REMOVAL
        value = TableBucketMaintenanceConfigurationValue(
            status=MaintenanceStatus.ENABLED, settings=None
        )
        region = 'us-west-2'
        expected_response = {'status': 'success', 'message': 'Maintenance configuration updated'}

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.put_table_bucket_maintenance_configuration.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await put_table_bucket_maintenance_configuration(
                table_bucket_arn, maintenance_type, value, region
            )

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.put_table_bucket_maintenance_configuration.assert_called_once()
            call_args = mock_client.put_table_bucket_maintenance_configuration.call_args
            assert call_args[1]['tableBucketARN'] == table_bucket_arn
            assert call_args[1]['type'] == maintenance_type.value
            assert call_args[1]['value'] == value.model_dump(by_alias=True, exclude_none=True)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        maintenance_type = TableBucketMaintenanceType.ICEBERG_UNREFERENCED_FILE_REMOVAL
        value = TableBucketMaintenanceConfigurationValue(
            status=MaintenanceStatus.ENABLED, settings=None
        )
        error_message = 'Invalid maintenance configuration'

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.put_table_bucket_maintenance_configuration.side_effect = Exception(
                error_message
            )
            mock_get_client.return_value = mock_client

            # Act
            result = await put_table_bucket_maintenance_configuration(
                table_bucket_arn, maintenance_type, value
            )

            # Assert
            assert result == {
                'error': error_message,
                'tool': 'put_table_bucket_maintenance_configuration',
            }


class TestGetTableBucket:
    """Test the get_table_bucket function."""

    @pytest.mark.asyncio
    async def test_successful_table_bucket_retrieval(self):
        """Test successful table bucket retrieval."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        region = 'us-west-2'
        expected_response = {
            'tableBucket': {
                'arn': table_bucket_arn,
                'name': 'test-bucket',
                'createdAt': '2023-01-01T00:00:00Z',
                'ownerAccountId': '123456789012',
            }
        }

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_bucket.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_bucket(table_bucket_arn, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.get_table_bucket.assert_called_once_with(tableBucketARN=table_bucket_arn)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        error_message = 'Table bucket not found'

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_bucket.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_bucket(table_bucket_arn)

            # Assert
            assert result == {'error': error_message, 'tool': 'get_table_bucket'}


class TestGetTableBucketMaintenanceConfiguration:
    """Test the get_table_bucket_maintenance_configuration function."""

    @pytest.mark.asyncio
    async def test_successful_maintenance_configuration_retrieval(self):
        """Test successful maintenance configuration retrieval."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        region = 'us-west-2'
        expected_response = {
            'maintenanceConfiguration': {
                'type': 'COMPACTION',
                'value': {'enabled': True, 'scheduleExpression': 'cron(0 2 * * ? *)'},
            }
        }

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_bucket_maintenance_configuration.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_bucket_maintenance_configuration(table_bucket_arn, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.get_table_bucket_maintenance_configuration.assert_called_once_with(
                tableBucketARN=table_bucket_arn
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        error_message = 'Maintenance configuration not found'

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_bucket_maintenance_configuration.side_effect = Exception(
                error_message
            )
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_bucket_maintenance_configuration(table_bucket_arn)

            # Assert
            assert result == {
                'error': error_message,
                'tool': 'get_table_bucket_maintenance_configuration',
            }


class TestGetTableBucketPolicy:
    """Test the get_table_bucket_policy function."""

    @pytest.mark.asyncio
    async def test_successful_policy_retrieval(self):
        """Test successful table bucket policy retrieval."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        region = 'us-west-2'
        expected_response = {
            'policy': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Principal': {'AWS': 'arn:aws:iam::123456789012:root'},
                        'Action': 's3tables:*',
                        'Resource': table_bucket_arn,
                    }
                ],
            }
        }

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_bucket_policy.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_bucket_policy(table_bucket_arn, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.get_table_bucket_policy.assert_called_once_with(
                tableBucketARN=table_bucket_arn
            )

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        error_message = 'Policy not found'

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_table_bucket_policy.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await get_table_bucket_policy(table_bucket_arn)

            # Assert
            assert result == {'error': error_message, 'tool': 'get_table_bucket_policy'}


class TestDeleteTableBucketPolicy:
    """Test the delete_table_bucket_policy function."""

    @pytest.mark.asyncio
    async def test_successful_policy_deletion(self):
        """Test successful table bucket policy deletion."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        region = 'us-west-2'
        expected_response = {'status': 'success', 'message': 'Policy deleted successfully'}

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table_bucket_policy.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table_bucket_policy(table_bucket_arn, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.delete_table_bucket_policy.assert_called_once_with(
                tableBucketARN=table_bucket_arn
            )

    @pytest.mark.asyncio
    async def test_successful_policy_deletion_with_default_region(self):
        """Test successful table bucket policy deletion with default region."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        expected_response = {'status': 'success'}

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table_bucket_policy.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table_bucket_policy(table_bucket_arn)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        error_message = 'Policy not found'

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table_bucket_policy.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table_bucket_policy(table_bucket_arn)

            # Assert
            assert result == {'error': error_message, 'tool': 'delete_table_bucket_policy'}

    @pytest.mark.asyncio
    async def test_empty_response_handling(self):
        """Test handling of empty response from delete operation."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        expected_response = {}

        with patch(
            'awslabs.s3_tables_mcp_server.table_buckets.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_table_bucket_policy.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_table_bucket_policy(table_bucket_arn)

            # Assert
            assert result == expected_response
