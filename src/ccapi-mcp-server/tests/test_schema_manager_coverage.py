"""Tests to increase schema_manager.py coverage."""

import json
import pytest
from awslabs.ccapi_mcp_server.errors import ClientError
from unittest.mock import MagicMock, patch


class TestSchemaManagerCoverage:
    """Tests to increase schema_manager.py coverage."""

    @pytest.mark.asyncio
    async def test_get_schema_corrupted_cache_reload(self):
        """Test get_schema with corrupted cached schema that needs reload."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager
        from datetime import datetime

        sm = schema_manager()

        # Add a corrupted schema (empty properties) to registry
        corrupted_schema = {'typeName': 'AWS::Test::Resource', 'properties': {}}
        sm.schema_registry['AWS::Test::Resource'] = corrupted_schema
        sm.metadata['schemas']['AWS::Test::Resource'] = {
            'last_updated': datetime.now().isoformat()
        }

        # Mock the download to return a valid schema
        with patch.object(sm, '_download_resource_schema') as mock_download:
            valid_schema = {
                'typeName': 'AWS::Test::Resource',
                'properties': {'TestProp': {'type': 'string'}},
            }
            mock_download.return_value = valid_schema

            result = await sm.get_schema('AWS::Test::Resource')

            # Should have called download due to corrupted cache
            mock_download.assert_called_once()
            assert result == valid_schema

    @pytest.mark.asyncio
    async def test_download_resource_schema_short_response(self):
        """Test _download_resource_schema with short response."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        with patch('awslabs.ccapi_mcp_server.schema_manager.get_aws_client') as mock_client:
            mock_cfn_client = MagicMock()
            # Return a very short schema response (less than 100 chars)
            mock_cfn_client.describe_type.return_value = {
                'Schema': '{"properties": {}}'  # Only 19 characters
            }
            mock_client.return_value = mock_cfn_client

            with pytest.raises(ClientError, match='Schema response too short'):
                await sm._download_resource_schema('AWS::S3::Bucket')

    @pytest.mark.asyncio
    async def test_download_resource_schema_no_properties(self):
        """Test _download_resource_schema with schema that has no properties."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        with patch('awslabs.ccapi_mcp_server.schema_manager.get_aws_client') as mock_client:
            mock_cfn_client = MagicMock()
            # Return schema without properties
            schema_without_props = {
                'typeName': 'AWS::Test::Resource',
                'readOnlyProperties': [],
                'primaryIdentifier': [],
            }
            mock_cfn_client.describe_type.return_value = {
                'Schema': json.dumps(schema_without_props)
            }
            mock_client.return_value = mock_cfn_client

            with pytest.raises(ClientError):
                await sm._download_resource_schema('AWS::Test::Resource')

    @pytest.mark.asyncio
    async def test_download_resource_schema_tagging_warning(self):
        """Test _download_resource_schema with known taggable resource missing Tags."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        with patch('awslabs.ccapi_mcp_server.schema_manager.get_aws_client') as mock_client:
            mock_cfn_client = MagicMock()
            # Return schema for S3 bucket without Tags property
            schema_no_tags = {
                'typeName': 'AWS::S3::Bucket',
                'properties': {'BucketName': {'type': 'string'}},
                'readOnlyProperties': [],
                'primaryIdentifier': [],
            }
            mock_cfn_client.describe_type.return_value = {'Schema': json.dumps(schema_no_tags)}
            mock_client.return_value = mock_cfn_client

            # Should succeed but print warning
            result = await sm._download_resource_schema('AWS::S3::Bucket')
            assert result['properties']['BucketName']['type'] == 'string'

    @pytest.mark.asyncio
    async def test_download_resource_schema_retry_logic(self):
        """Test _download_resource_schema retry logic."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        with patch('awslabs.ccapi_mcp_server.schema_manager.get_aws_client') as mock_client:
            mock_cfn_client = MagicMock()

            # First two calls fail, third succeeds
            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise Exception(f'API Error attempt {call_count}')
                # Return a longer schema to pass validation
                return {
                    'Schema': json.dumps(
                        {
                            'properties': {
                                'TestProp': {
                                    'type': 'string',
                                    'description': 'A test property for validation',
                                }
                            },
                            'readOnlyProperties': [],
                            'primaryIdentifier': [],
                            'additionalProperties': False,
                        }
                    )
                }

            mock_cfn_client.describe_type.side_effect = side_effect
            mock_client.return_value = mock_cfn_client

            # Should succeed on third attempt
            result = await sm._download_resource_schema('AWS::Test::Resource')
            assert result['properties']['TestProp']['type'] == 'string'
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_download_resource_schema_max_retries_exceeded(self):
        """Test _download_resource_schema when max retries exceeded."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        with patch('awslabs.ccapi_mcp_server.schema_manager.get_aws_client') as mock_client:
            mock_cfn_client = MagicMock()
            # Always fail
            mock_cfn_client.describe_type.side_effect = Exception('Persistent API Error')
            mock_client.return_value = mock_cfn_client

            with pytest.raises(
                ClientError, match='Failed to download valid schema.*after 3 attempts'
            ):
                await sm._download_resource_schema('AWS::Test::Resource')

    def test_load_metadata_file_not_exists(self):
        """Test _load_metadata when metadata file doesn't exist."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        # Delete metadata file if it exists
        if sm.metadata_file.exists():
            sm.metadata_file.unlink()

        metadata = sm._load_metadata()

        # Should return default metadata structure
        assert metadata['version'] == '1'
        assert 'schemas' in metadata
        assert isinstance(metadata['schemas'], dict)

    def test_load_cached_schemas_file_not_json(self):
        """Test _load_cached_schemas with non-JSON file."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        # Create a non-JSON file in cache directory
        non_json_file = sm.cache_dir / 'not_json.json'
        with open(non_json_file, 'w') as f:
            f.write('This is not JSON content')

        try:
            # Should handle the error gracefully
            sm._load_cached_schemas()
            # If we get here, the error was handled gracefully
            assert True
        finally:
            # Clean up
            if non_json_file.exists():
                non_json_file.unlink()

    def test_load_cached_schemas_missing_typename(self):
        """Test _load_cached_schemas with schema missing typeName."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        # Create a JSON file without typeName
        no_typename_file = sm.cache_dir / 'no_typename.json'
        with open(no_typename_file, 'w') as f:
            json.dump({'properties': {'test': 'value'}}, f)

        try:
            # Should handle missing typeName gracefully
            sm._load_cached_schemas()
            # Schema should not be loaded into registry
            assert 'no_typename' not in sm.schema_registry
        finally:
            # Clean up
            if no_typename_file.exists():
                no_typename_file.unlink()

    def test_load_cached_schemas_permission_error(self):
        """Test _load_cached_schemas with permission error."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        # Create a file and then mock permission error
        test_file = sm.cache_dir / 'permission_test.json'
        with open(test_file, 'w') as f:
            json.dump({'typeName': 'AWS::Test::Resource', 'properties': {}}, f)

        try:
            with patch('builtins.open', side_effect=PermissionError('Permission denied')):
                # Should handle permission error gracefully
                sm._load_cached_schemas()
                assert True  # If we get here, error was handled
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    @pytest.mark.asyncio
    async def test_get_schema_timestamp_parsing_error(self):
        """Test get_schema with timestamp parsing error."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        # Add schema with invalid timestamp
        test_schema = {'typeName': 'AWS::Test::Resource', 'properties': {'test': 'value'}}
        sm.schema_registry['AWS::Test::Resource'] = test_schema
        sm.metadata['schemas']['AWS::Test::Resource'] = {'last_updated': 'not-a-valid-timestamp'}

        with patch.object(sm, '_download_resource_schema') as mock_download:
            mock_download.return_value = test_schema

            await sm.get_schema('AWS::Test::Resource')

            # Should call download due to invalid timestamp
            mock_download.assert_called_once()

    def test_schema_registry_initialization(self):
        """Test schema registry initialization."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        # Should have empty registry initially
        assert isinstance(sm.schema_registry, dict)

        # Should have metadata structure
        assert isinstance(sm.metadata, dict)
        assert 'version' in sm.metadata
        assert 'schemas' in sm.metadata
