"""Unit tests for the ManifestHandler class."""

import json
import pytest
from .fixtures import CSV_MANIFEST, PARQUET_MANIFEST
from awslabs.aws_finops_mcp_server.models import SchemaFormat
from awslabs.aws_finops_mcp_server.storage_lens.manifest_handler import ManifestHandler
from unittest.mock import MagicMock, patch


class TestManifestHandler:
    """Unit tests for the ManifestHandler class."""

    @pytest.fixture
    def manifest_handler(self):
        """Create a ManifestHandler instance for testing."""
        with patch('boto3.client') as mock_boto3:
            handler = ManifestHandler()
            # Replace the real S3 client with our mock
            handler.s3_client = mock_boto3.return_value
            yield handler

    @pytest.mark.asyncio
    async def test_get_manifest_exact_path(self, manifest_handler):
        """Test getting a manifest from an exact path."""
        # Setup mock
        manifest_handler.s3_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(CSV_MANIFEST).encode('utf-8'))
        }

        # Call the method
        result = await manifest_handler.get_manifest('s3://my-bucket/path/to/manifest.json')

        # Assertions
        manifest_handler.s3_client.get_object.assert_called_once_with(
            Bucket='my-bucket', Key='path/to/manifest.json'
        )
        assert result == CSV_MANIFEST

    @pytest.mark.asyncio
    async def test_read_manifest_file_error(self, manifest_handler):
        """Test error handling when reading a manifest file fails."""
        # Setup mock to raise an exception
        manifest_handler.s3_client.get_object.side_effect = Exception('Access denied')

        # Call the method and expect an exception
        with pytest.raises(Exception) as excinfo:
            await manifest_handler._read_manifest_file('my-bucket', 'path/to/manifest.json')

        # Verify the error message
        assert 'Failed to read manifest file' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_find_latest_manifest(self, manifest_handler):
        """Test finding the latest manifest in a folder."""
        # Mock paginator
        mock_paginator = MagicMock()
        manifest_handler.s3_client.get_paginator.return_value = mock_paginator

        # Mock paginate response
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {
                        'Key': 'path/to/folder/manifest1.json',
                        'LastModified': '2020-01-01T00:00:00Z',
                    },
                    {
                        'Key': 'path/to/folder/manifest.json',
                        'LastModified': '2020-02-01T00:00:00Z',
                    },
                ]
            }
        ]

        # Mock get_object response
        manifest_handler.s3_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: json.dumps(CSV_MANIFEST).encode('utf-8'))
        }

        # Call the method
        result = await manifest_handler._find_latest_manifest('my-bucket', 'path/to/folder')

        # Assertions
        manifest_handler.s3_client.get_paginator.assert_called_once_with('list_objects_v2')
        mock_paginator.paginate.assert_called_once_with(
            Bucket='my-bucket', Prefix='path/to/folder/'
        )
        manifest_handler.s3_client.get_object.assert_called_once()
        assert result == CSV_MANIFEST

    @pytest.mark.asyncio
    async def test_find_latest_manifest_empty(self, manifest_handler):
        """Test finding the latest manifest when no manifests exist."""
        # Mock paginator
        mock_paginator = MagicMock()
        manifest_handler.s3_client.get_paginator.return_value = mock_paginator

        # Mock empty paginate response
        mock_paginator.paginate.return_value = [{'Contents': []}]

        # Call the method and expect an exception
        with pytest.raises(Exception) as excinfo:
            await manifest_handler._find_latest_manifest('my-bucket', 'path/to/folder')

        # Verify the error message
        assert 'No manifest.json files found' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_find_latest_manifest_no_contents(self, manifest_handler):
        """Test finding the latest manifest when the response has no Contents key."""
        # Mock paginator
        mock_paginator = MagicMock()
        manifest_handler.s3_client.get_paginator.return_value = mock_paginator

        # Mock response with no Contents key
        mock_paginator.paginate.return_value = [{}]

        # Call the method and expect an exception
        with pytest.raises(Exception) as excinfo:
            await manifest_handler._find_latest_manifest('my-bucket', 'path/to/folder')

        # Verify the error message
        assert 'No manifest.json files found' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_find_latest_manifest_error(self, manifest_handler):
        """Test error handling in find_latest_manifest."""
        # Mock paginator to raise an exception
        manifest_handler.s3_client.get_paginator.side_effect = Exception('Access denied')

        # Call the method and expect an exception
        with pytest.raises(Exception) as excinfo:
            await manifest_handler._find_latest_manifest('my-bucket', 'path/to/folder')

        # Verify the error message
        assert 'Failed to locate manifest file' in str(excinfo.value)

    def test_extract_data_location(self, manifest_handler):
        """Test extracting data location from manifest."""
        # Call the method
        result = manifest_handler.extract_data_location(CSV_MANIFEST)

        # Assertions
        expected = 'DestinationPrefix/StorageLens/123456789012/my-dashboard-configuration-id/V_1/reports/dt=2020-11-03'  # pragma: allowlist secret
        assert result.endswith(expected)

    def test_extract_data_location_empty_report_files(self, manifest_handler):
        """Test extracting data location when no report files exist."""
        # Create a manifest with no report files
        empty_manifest = {**CSV_MANIFEST, 'reportFiles': []}

        # Call the method and expect an exception
        with pytest.raises(Exception) as excinfo:
            manifest_handler.extract_data_location(empty_manifest)

        # Verify the error message
        assert 'No report files found in manifest' in str(excinfo.value)

    def test_extract_data_location_with_arn(self, manifest_handler):
        """Test extracting data location with ARN bucket format."""
        # Create a manifest with ARN format bucket
        arn_manifest = {**CSV_MANIFEST, 'destinationBucket': 'arn:aws:s3:::my-bucket'}

        # Call the method
        result = manifest_handler.extract_data_location(arn_manifest)

        # Verify the result starts with the correct bucket name
        assert result.startswith('s3://my-bucket/')

    def test_parse_schema_csv(self, manifest_handler):
        """Test parsing CSV schema from manifest."""
        # Call the method
        result = manifest_handler.parse_schema(CSV_MANIFEST)

        # Assertions
        assert result.format == SchemaFormat.CSV
        assert len(result.columns) == 11
        assert result.columns[0].name == 'version_number'
        assert result.columns[0].type == 'STRING'

    def test_parse_schema_parquet(self, manifest_handler):
        """Test parsing Parquet schema from manifest."""
        # Call the method
        result = manifest_handler.parse_schema(PARQUET_MANIFEST)

        # Assertions
        assert result.format == SchemaFormat.PARQUET
        assert len(result.columns) == 11
        assert result.columns[0].name == 'version_number'
        assert result.columns[0].type == 'STRING'
        assert result.columns[10].name == 'metric_value'
        assert result.columns[10].type == 'BIGINT'

    def test_parse_schema_parquet_unknown_type(self, manifest_handler):
        """Test parsing Parquet schema with unknown data types."""
        # Create a manifest with an unknown data type
        schema_with_unknown = {
            **PARQUET_MANIFEST,
            'reportSchema': 'message schema { required unknown_type field_name; }',
        }

        # Call the method
        result = manifest_handler.parse_schema(schema_with_unknown)

        # Verify that unknown types default to STRING
        assert result.columns[0].name == 'field_name'
        assert result.columns[0].type == 'STRING'
