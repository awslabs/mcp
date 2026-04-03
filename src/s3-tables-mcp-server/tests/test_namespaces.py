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

"""Tests for the namespaces module."""

import pytest
from awslabs.s3_tables_mcp_server.namespaces import (
    create_namespace,
    delete_namespace,
    get_namespace,
)
from unittest.mock import MagicMock, patch


class TestCreateNamespace:
    """Test the create_namespace function."""

    @pytest.mark.asyncio
    async def test_successful_namespace_creation(self):
        """Test successful namespace creation."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        region = 'us-west-2'
        expected_response = {
            'namespace': 'test-namespace',
            'createdAt': '2023-01-01T00:00:00Z',
            'createdBy': 'test-user',
        }

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_namespace.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await create_namespace(table_bucket_arn, namespace, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.create_namespace.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=[namespace]
            )

    @pytest.mark.asyncio
    async def test_successful_namespace_creation_with_default_region(self):
        """Test successful namespace creation with default region."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        expected_response = {'namespace': 'test-namespace', 'createdAt': '2023-01-01T00:00:00Z'}

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_namespace.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await create_namespace(table_bucket_arn, namespace)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        error_message = 'Namespace already exists'

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_namespace.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await create_namespace(table_bucket_arn, namespace)

            # Assert
            assert result == {'error': error_message, 'tool': 'create_namespace'}

    @pytest.mark.asyncio
    async def test_complex_namespace_name(self):
        """Test namespace creation with complex namespace name."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'complex-namespace-name-with-dashes'
        region = 'us-east-1'

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_namespace.return_value = {'namespace': namespace}
            mock_get_client.return_value = mock_client

            # Act
            result = await create_namespace(table_bucket_arn, namespace, region)

            # Assert
            assert result == {'namespace': namespace}
            mock_client.create_namespace.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=[namespace]
            )


class TestDeleteNamespace:
    """Test the delete_namespace function."""

    @pytest.mark.asyncio
    async def test_successful_namespace_deletion(self):
        """Test successful namespace deletion."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        region = 'us-west-2'
        expected_response = {'status': 'success', 'message': 'Namespace deleted successfully'}

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_namespace.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_namespace(table_bucket_arn, namespace, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.delete_namespace.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=namespace
            )

    @pytest.mark.asyncio
    async def test_successful_namespace_deletion_with_default_region(self):
        """Test successful namespace deletion with default region."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        expected_response = {'status': 'success'}

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_namespace.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_namespace(table_bucket_arn, namespace)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        error_message = 'Namespace not found'

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_namespace.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_namespace(table_bucket_arn, namespace)

            # Assert
            assert result == {'error': error_message, 'tool': 'delete_namespace'}

    @pytest.mark.asyncio
    async def test_empty_response_handling(self):
        """Test handling of empty response from delete operation."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        expected_response = {}

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete_namespace.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await delete_namespace(table_bucket_arn, namespace)

            # Assert
            assert result == expected_response


class TestGetNamespace:
    """Test the get_namespace function."""

    @pytest.mark.asyncio
    async def test_successful_namespace_retrieval(self):
        """Test successful namespace retrieval."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        region = 'us-west-2'
        expected_response = {
            'namespace': 'test-namespace',
            'createdAt': '2023-01-01T00:00:00Z',
            'createdBy': 'test-user',
            'ownerAccountId': '123456789012',
            'namespaceId': 'ns-1234567890abcdef',
        }

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_namespace.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_namespace(table_bucket_arn, namespace, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.get_namespace.assert_called_once_with(
                tableBucketARN=table_bucket_arn, namespace=namespace
            )

    @pytest.mark.asyncio
    async def test_successful_namespace_retrieval_with_default_region(self):
        """Test successful namespace retrieval with default region."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        expected_response = {'namespace': 'test-namespace', 'createdAt': '2023-01-01T00:00:00Z'}

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_namespace.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_namespace(table_bucket_arn, namespace)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        error_message = 'Namespace not found'

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_namespace.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await get_namespace(table_bucket_arn, namespace)

            # Assert
            assert result == {'error': error_message, 'tool': 'get_namespace'}

    @pytest.mark.asyncio
    async def test_complex_namespace_response(self):
        """Test handling of complex namespace response."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        expected_response = {
            'namespace': 'test-namespace',
            'createdAt': '2023-01-01T00:00:00Z',
            'createdBy': 'test-user',
            'ownerAccountId': '123456789012',
            'namespaceId': 'ns-1234567890abcdef',
            'tableBucketId': 'tb-1234567890abcdef',
            'additionalMetadata': {
                'description': 'Test namespace',
                'tags': {'environment': 'test', 'project': 's3-tables'},
            },
        }

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_namespace.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_namespace(table_bucket_arn, namespace)

            # Assert
            assert result == expected_response
            assert result['namespace'] == 'test-namespace'
            assert result['additionalMetadata']['description'] == 'Test namespace'

    @pytest.mark.asyncio
    async def test_empty_response_handling(self):
        """Test handling of empty response from get operation."""
        # Arrange
        table_bucket_arn = 'arn:aws:s3tables:us-west-2:123456789012:table-bucket/test-bucket'
        namespace = 'test-namespace'
        expected_response = {}

        with patch(
            'awslabs.s3_tables_mcp_server.namespaces.get_s3tables_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_namespace.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_namespace(table_bucket_arn, namespace)

            # Assert
            assert result == expected_response
