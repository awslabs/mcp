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
"""Tests for schema_manager."""

import json
import pytest
from unittest.mock import MagicMock, patch


class TestSchemaManager:
    """Test schema manager functions."""

    def test_schema_manager_singleton(self):
        """Test schema_manager singleton behavior."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm1 = schema_manager()
        sm2 = schema_manager()
        assert sm1 is sm2

    def test_schema_manager_basic_functions(self):
        """Test basic schema manager functions exist."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()
        assert hasattr(sm, 'get_schema')
        assert hasattr(sm, 'schema_registry')
        assert isinstance(sm.schema_registry, dict)

    def test_schema_manager_cache_functions(self):
        """Test schema cache functions exist."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()
        assert hasattr(sm, 'cache_dir')
        assert hasattr(sm, 'metadata_file')
        assert hasattr(sm, 'metadata')

    @pytest.mark.asyncio
    async def test_get_schema_invalid_type(self):
        """Test get_schema with invalid resource type."""
        from awslabs.ccapi_mcp_server.errors import ClientError
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()
        with pytest.raises(ClientError):
            await sm.get_schema('InvalidType')

    def test_schema_manager_metadata_loading(self):
        """Test metadata loading functions."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()
        assert hasattr(sm, '_load_metadata')
        assert hasattr(sm, '_load_cached_schemas')
        assert callable(sm._load_metadata)
        assert callable(sm._load_cached_schemas)

    @pytest.mark.asyncio
    async def test_download_resource_schema_invalid_format(self):
        """Test _download_resource_schema with invalid format."""
        from awslabs.ccapi_mcp_server.errors import ClientError
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()
        with pytest.raises(ClientError):
            await sm._download_resource_schema('InvalidFormat')

    def test_schema_manager_cache_dir_creation(self):
        """Test cache directory creation."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()
        assert sm.cache_dir.exists()
        assert sm.metadata_file.exists() or sm.metadata_file.parent.exists()

    @pytest.mark.asyncio
    async def test_get_schema_cached_recent(self):
        """Test get_schema with recent cached schema."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager
        from datetime import datetime

        sm = schema_manager()
        # Add a fake recent schema to registry with proper properties
        test_schema = {'typeName': 'AWS::Test::Resource', 'properties': {'TestProp': {'type': 'string'}}}
        sm.schema_registry['AWS::Test::Resource'] = test_schema
        sm.metadata['schemas']['AWS::Test::Resource'] = {
            'last_updated': datetime.now().isoformat()
        }

        result = await sm.get_schema('AWS::Test::Resource')
        assert result == test_schema

    @patch('awslabs.ccapi_mcp_server.schema_manager.get_aws_client')
    @pytest.mark.asyncio
    async def test_download_resource_schema_success(self, mock_client):
        """Test successful schema download - covers lines 136-155."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        mock_cfn_client = MagicMock()
        # Provide a schema with properties to pass validation
        schema_content = {
            'properties': {'BucketName': {'type': 'string'}}, 
            'readOnlyProperties': [], 
            'primaryIdentifier': []
        }
        mock_cfn_client.describe_type.return_value = {
            'Schema': json.dumps(schema_content)
        }
        mock_client.return_value = mock_cfn_client

        sm = schema_manager()
        result = await sm._download_resource_schema('AWS::S3::Bucket')

        assert 'BucketName' in result['properties']
        mock_cfn_client.describe_type.assert_called_once_with(
            Type='RESOURCE', TypeName='AWS::S3::Bucket'
        )

    @patch('awslabs.ccapi_mcp_server.schema_manager.get_aws_client')
    @pytest.mark.asyncio
    async def test_download_resource_schema_api_error(self, mock_client):
        """Test schema download API error - covers lines 156-157."""
        from awslabs.ccapi_mcp_server.errors import ClientError
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        mock_client.side_effect = Exception('API Error')

        sm = schema_manager()
        with pytest.raises(ClientError):
            await sm._download_resource_schema('AWS::S3::Bucket')

    def test_load_metadata_corrupted_file(self):
        """Test loading corrupted metadata file - covers lines 55-65."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()
        # Write corrupted JSON to metadata file
        with open(sm.metadata_file, 'w') as f:
            f.write('invalid json')

        # This should handle the corrupted file gracefully
        metadata = sm._load_metadata()
        assert metadata['version'] == '1'
        assert 'schemas' in metadata

    def test_load_cached_schemas_error(self):
        """Test loading cached schemas with error - covers lines 73-81."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()
        # Create a schema file with invalid JSON
        test_file = sm.cache_dir / 'test_schema.json'
        with open(test_file, 'w') as f:
            f.write('invalid json')

        # This should handle the error gracefully
        sm._load_cached_schemas()

        # Clean up
        test_file.unlink()

    @pytest.mark.asyncio
    async def test_get_schema_old_timestamp(self):
        """Test get_schema with old timestamp - covers lines 99-106."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager
        from datetime import datetime, timedelta

        sm = schema_manager()
        # Add a fake old schema to registry
        test_schema = {'typeName': 'AWS::Test::Resource', 'properties': {}}
        sm.schema_registry['AWS::Test::Resource'] = test_schema
        old_date = datetime.now() - timedelta(days=10)
        sm.metadata['schemas']['AWS::Test::Resource'] = {'last_updated': old_date.isoformat()}

        with patch.object(sm, '_download_resource_schema') as mock_download:
            mock_download.return_value = test_schema
            await sm.get_schema('AWS::Test::Resource')
            mock_download.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_schema_invalid_timestamp(self):
        """Test get_schema with invalid timestamp format - covers lines 102-106."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()
        # Add a fake schema with invalid timestamp
        test_schema = {'typeName': 'AWS::Test::Resource', 'properties': {}}
        sm.schema_registry['AWS::Test::Resource'] = test_schema
        sm.metadata['schemas']['AWS::Test::Resource'] = {
            'last_updated': 'invalid-timestamp-format'
        }

        with patch.object(sm, '_download_resource_schema') as mock_download:
            mock_download.return_value = test_schema
            await sm.get_schema('AWS::Test::Resource')
            # Should call download due to invalid timestamp
            mock_download.assert_called_once()

    def test_load_cached_schemas_no_typename(self):
        """Test loading cached schemas without typeName - covers lines 77-79."""
        import json
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()
        # Create a schema file without typeName
        test_file = sm.cache_dir / 'test_no_typename.json'
        with open(test_file, 'w') as f:
            json.dump({'properties': {}}, f)  # Missing typeName

        # This should handle the missing typeName gracefully
        sm._load_cached_schemas()

        # Clean up
        test_file.unlink()
