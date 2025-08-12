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

"""Tests for the s3_operations module."""

import pytest
from awslabs.s3_tables_mcp_server.s3_operations import get_bucket_metadata_table_configuration
from unittest.mock import MagicMock, patch


class TestGetBucketMetadataTableConfiguration:
    """Test the get_bucket_metadata_table_configuration function."""

    @pytest.mark.asyncio
    async def test_successful_configuration_retrieval(self):
        """Test successful retrieval of bucket metadata table configuration."""
        # Arrange
        bucket = 'test-bucket'
        region = 'us-west-2'
        expected_response = {
            'MetadataTableConfiguration': {'Status': 'ENABLED', 'TableFormat': 'ICEBERG'}
        }

        with patch('awslabs.s3_tables_mcp_server.s3_operations.get_s3_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_bucket_metadata_configuration.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_bucket_metadata_table_configuration(bucket, region)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(region)
            mock_client.get_bucket_metadata_configuration.assert_called_once_with(Bucket=bucket)

    @pytest.mark.asyncio
    async def test_successful_configuration_retrieval_with_default_region(self):
        """Test successful retrieval with default region."""
        # Arrange
        bucket = 'test-bucket'
        expected_response = {'MetadataTableConfiguration': {'Status': 'DISABLED'}}

        with patch('awslabs.s3_tables_mcp_server.s3_operations.get_s3_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_bucket_metadata_configuration.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_bucket_metadata_table_configuration(bucket)

            # Assert
            assert result == expected_response
            mock_get_client.assert_called_once_with(None)
            mock_client.get_bucket_metadata_configuration.assert_called_once_with(Bucket=bucket)

    @pytest.mark.asyncio
    async def test_empty_configuration_response(self):
        """Test handling of empty configuration response."""
        # Arrange
        bucket = 'test-bucket'
        expected_response = {}

        with patch('awslabs.s3_tables_mcp_server.s3_operations.get_s3_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_bucket_metadata_configuration.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_bucket_metadata_table_configuration(bucket)

            # Assert
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_complex_configuration_response(self):
        """Test handling of complex configuration response."""
        # Arrange
        bucket = 'test-bucket'
        expected_response = {
            'MetadataTableConfiguration': {
                'Status': 'ENABLED',
                'TableFormat': 'ICEBERG',
                'AdditionalSettings': {'Compression': 'GZIP', 'Partitioning': 'HIVE'},
            },
            'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': 200},
        }

        with patch('awslabs.s3_tables_mcp_server.s3_operations.get_s3_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_bucket_metadata_configuration.return_value = expected_response
            mock_get_client.return_value = mock_client

            # Act
            result = await get_bucket_metadata_table_configuration(bucket)

            # Assert
            assert result == expected_response
            assert result['MetadataTableConfiguration']['Status'] == 'ENABLED'
            assert result['MetadataTableConfiguration']['TableFormat'] == 'ICEBERG'

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are handled by the decorator."""
        # Arrange
        bucket = 'test-bucket'
        error_message = 'Access Denied'

        with patch('awslabs.s3_tables_mcp_server.s3_operations.get_s3_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_bucket_metadata_configuration.side_effect = Exception(error_message)
            mock_get_client.return_value = mock_client

            # Act
            result = await get_bucket_metadata_table_configuration(bucket)

            # Assert
            assert result == {
                'error': error_message,
                'tool': 'get_bucket_metadata_table_configuration',
            }

    @pytest.mark.asyncio
    async def test_client_initialization_with_region(self):
        """Test that client is initialized with the correct region."""
        # Arrange
        bucket = 'test-bucket'
        region = 'eu-west-1'

        with patch('awslabs.s3_tables_mcp_server.s3_operations.get_s3_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_bucket_metadata_configuration.return_value = {}
            mock_get_client.return_value = mock_client

            # Act
            await get_bucket_metadata_table_configuration(bucket, region)

            # Assert
            mock_get_client.assert_called_once_with(region)

    @pytest.mark.asyncio
    async def test_bucket_parameter_passed_correctly(self):
        """Test that bucket parameter is passed correctly to the client method."""
        # Arrange
        bucket = 'my-special-bucket-name'
        region = 'us-east-1'

        with patch('awslabs.s3_tables_mcp_server.s3_operations.get_s3_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_bucket_metadata_configuration.return_value = {}
            mock_get_client.return_value = mock_client

            # Act
            await get_bucket_metadata_table_configuration(bucket, region)

            # Assert
            mock_client.get_bucket_metadata_configuration.assert_called_once_with(Bucket=bucket)
