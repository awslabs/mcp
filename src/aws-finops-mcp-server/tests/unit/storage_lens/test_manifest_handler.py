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

    def test_extract_data_location(self, manifest_handler):
        """Test extracting data location from manifest."""
        # Call the method
        result = manifest_handler.extract_data_location(CSV_MANIFEST)

        # Assertions
        expected = 'DestinationPrefix/StorageLens/123456789012/my-dashboard-configuration-id/V_1/reports/dt=2020-11-03'  # pragma: allowlist secret
        assert result.endswith(expected)

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
