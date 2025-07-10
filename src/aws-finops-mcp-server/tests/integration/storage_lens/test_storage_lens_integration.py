"""Integration tests for the S3 Storage Lens Query Module.

These tests require:
1. AWS credentials with appropriate permissions
2. An S3 bucket with Storage Lens exports
3. Athena permissions to create databases and tables

To run these tests:
pytest -m integration tests/integration/storage_lens/test_storage_lens_integration.py
"""

import os
import pytest
import pytest_asyncio
from awslabs.aws_finops_mcp_server.models import StorageLensQueryRequest
from awslabs.aws_finops_mcp_server.storage_lens import StorageLensQueryTool
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Skip all tests if no AWS credentials are available
pytestmark = [pytest.mark.integration]

# This value should be set to match your environment
# You can override it with an environment variable
MANIFEST_LOCATION = os.environ.get(
    'STORAGE_LENS_MANIFEST_LOCATION', 's3://your-bucket/storage-lens-exports/'
)


@pytest.mark.asyncio
class TestStorageLensIntegration:
    """Integration tests for the StorageLensQueryTool."""

    @pytest_asyncio.fixture
    async def query_tool(self):
        """Create a StorageLensQueryTool instance for testing."""
        tool = StorageLensQueryTool()
        return tool  # Return the actual tool, not the coroutine

    async def test_get_manifest(self, query_tool):
        """Test getting a manifest file."""
        # Debug print to see what value is being used
        print(f'MANIFEST_LOCATION = {MANIFEST_LOCATION}')

        # Skip if no manifest location is provided
        if MANIFEST_LOCATION == 's3://your-bucket/storage-lens-exports/':
            pytest.skip('No manifest location provided')

        manifest = await query_tool.manifest_handler.get_manifest(MANIFEST_LOCATION)

        # Basic validation of manifest structure
        assert 'reportFormat' in manifest
        assert 'reportSchema' in manifest
        assert 'reportFiles' in manifest

    async def test_simple_query(self, query_tool):
        """Test running a simple query."""
        # Skip if no manifest location is provided
        if MANIFEST_LOCATION == 's3://your-bucket/storage-lens-exports/':
            pytest.skip('No manifest location provided')

        # Run a simple query to get storage by region
        request = StorageLensQueryRequest(
            manifest_location=MANIFEST_LOCATION,
            query="""
            SELECT
                aws_region,
                SUM(CAST(metric_value AS BIGINT)) as total_bytes
            FROM
                {table}
            WHERE
                metric_name = 'StorageBytes'
            GROUP BY
                aws_region
            ORDER BY
                total_bytes DESC
            LIMIT 10
            """,
        )
        result = await query_tool.query_storage_lens(request)

        # Validate result structure
        assert hasattr(result, 'columns')
        assert hasattr(result, 'rows')
        assert hasattr(result, 'statistics')

        # Validate that we got some data
        if len(result.rows) > 0:
            assert 'aws_region' in result.rows[0]
            assert 'total_bytes' in result.rows[0]
