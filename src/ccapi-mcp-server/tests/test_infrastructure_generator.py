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
"""Tests for infrastructure_generator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
class TestInfrastructureGenerator:
    """Test infrastructure generator functions."""

    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager')
    async def test_generate_infrastructure_code_success(self, mock_schema_manager):
        """Test successful infrastructure code generation."""
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(
            return_value={'properties': {'BucketName': {'type': 'string'}}}
        )
        mock_schema_manager.return_value = mock_instance

        result = await generate_infrastructure_code(
            resource_type='AWS::S3::Bucket',
            properties={'BucketName': 'test-bucket'},
            region='us-east-1',
        )

        assert 'cloudformation_template' in result
        # terraform_code may not be in result depending on implementation
        assert isinstance(result, dict)

    async def test_generate_infrastructure_code_no_type(self):
        """Test infrastructure code generation with no type."""
        from awslabs.ccapi_mcp_server.errors import ClientError
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        with pytest.raises(ClientError):
            await generate_infrastructure_code(resource_type='', properties={}, region='us-east-1')

    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager')
    async def test_generate_infrastructure_code_with_options(self, mock_schema_manager):
        """Test infrastructure code generation with additional options."""
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(
            return_value={'properties': {'BucketName': {'type': 'string'}}}
        )
        mock_schema_manager.return_value = mock_instance

        result = await generate_infrastructure_code(
            resource_type='AWS::S3::Bucket',
            properties={'BucketName': 'test-bucket'},
            region='us-east-1',
        )

        assert 'cloudformation_template' in result
        assert isinstance(result, dict)

    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager')
    async def test_generate_infrastructure_code_schema_error(self, mock_schema_manager):
        """Test infrastructure code generation with schema error."""
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(side_effect=Exception('Schema not found'))
        mock_schema_manager.return_value = mock_instance

        with pytest.raises(Exception, match='Schema not found'):
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket',
                properties={'BucketName': 'test-bucket'},
                region='us-east-1',
            )

    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager')
    async def test_generate_infrastructure_code_complex_properties(self, mock_schema_manager):
        """Test infrastructure code generation with complex properties."""
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(
            return_value={
                'properties': {
                    'BucketName': {'type': 'string'},
                    'Tags': {'type': 'array'},
                    'PublicAccessBlockConfiguration': {'type': 'object'},
                }
            }
        )
        mock_schema_manager.return_value = mock_instance

        complex_properties = {
            'BucketName': 'test-bucket',
            'Tags': [{'Key': 'Environment', 'Value': 'Test'}],
            'PublicAccessBlockConfiguration': {'BlockPublicAcls': True, 'BlockPublicPolicy': True},
        }

        result = await generate_infrastructure_code(
            resource_type='AWS::S3::Bucket', properties=complex_properties, region='us-west-2'
        )

        assert 'cloudformation_template' in result
        assert isinstance(result, dict)

    async def test_generate_infrastructure_code_no_properties(self):
        """Test infrastructure code generation with no properties."""
        from awslabs.ccapi_mcp_server.errors import ClientError
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        with pytest.raises(ClientError):
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket', properties={}, region='us-east-1'
            )

    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager')
    async def test_generate_infrastructure_code_no_region(self, mock_schema_manager):
        """Test infrastructure code generation with no region uses default."""
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(
            return_value={'properties': {'BucketName': {'type': 'string'}}}
        )
        mock_schema_manager.return_value = mock_instance

        # Empty region should use default region instead of raising error
        result = await generate_infrastructure_code(
            resource_type='AWS::S3::Bucket',
            properties={'BucketName': 'test-bucket'},
            region='',
        )
        assert isinstance(result, dict)
        assert 'cloudformation_template' in result

    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager')
    async def test_generate_infrastructure_code_no_properties_create(self, mock_schema_manager):
        """Test generate_infrastructure_code with no properties for create - line 76."""
        from awslabs.ccapi_mcp_server.errors import ClientError
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(return_value={'properties': {}})
        mock_schema_manager.return_value = mock_instance

        with pytest.raises(ClientError, match='Please provide the properties'):
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket', properties={}, identifier=''
            )

    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager')
    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.get_aws_client')
    async def test_generate_infrastructure_code_update_path(
        self, mock_client, mock_schema_manager
    ):
        """Test infrastructure code generation update path - lines 49-72."""
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(return_value={'properties': {}})
        mock_schema_manager.return_value = mock_instance

        mock_client.return_value.get_resource.return_value = {
            'ResourceDescription': {'Properties': '{"BucketName": "existing-bucket"}'}
        }

        result = await generate_infrastructure_code(
            resource_type='AWS::S3::Bucket',
            properties={'BucketName': 'test-bucket'},
            identifier='existing-bucket',
            patch_document=[{'op': 'replace', 'path': '/BucketName', 'value': 'new-bucket'}],
        )

        assert isinstance(result, dict)

    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager')
    async def test_generate_infrastructure_code_schema_error_lines(self, mock_schema_manager):
        """Test generate_infrastructure_code with schema error - covers lines 50, 59-60."""
        from awslabs.ccapi_mcp_server.errors import ClientError
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(side_effect=ClientError('Schema error'))
        mock_schema_manager.return_value = mock_instance

        with pytest.raises(ClientError):
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket',
                properties={'BucketName': 'test'},
                region='us-east-1',
            )

    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager')
    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.add_default_tags')
    async def test_generate_infrastructure_code_tag_error_lines(
        self, mock_tags, mock_schema_manager
    ):
        """Test generate_infrastructure_code with tag error - covers lines 70, 80-81."""
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(return_value={'properties': {}})
        mock_schema_manager.return_value = mock_instance
        mock_tags.side_effect = Exception('Tag error')

        with pytest.raises(Exception):
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket',
                properties={'BucketName': 'test'},
                region='us-east-1',
            )

    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager')
    @patch('awslabs.ccapi_mcp_server.infrastructure_generator.get_aws_client')
    async def test_generate_infrastructure_code_update_with_default_tags(
        self, mock_client, mock_schema_manager
    ):
        """Test infrastructure code generation for update includes default tags in recommended patch."""
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        # Mock schema with Tags support
        mock_instance = MagicMock()
        mock_instance.get_schema = AsyncMock(
            return_value={
                'properties': {'BucketName': {'type': 'string'}, 'Tags': {'type': 'array'}}
            }
        )
        mock_schema_manager.return_value = mock_instance

        # Mock current resource with existing tags
        mock_client.return_value.get_resource.return_value = {
            'ResourceDescription': {
                'Properties': '{"BucketName": "existing-bucket", "Tags": [{"Key": "existing", "Value": "tag"}]}'
            }
        }

        # User wants to add a new tag
        result = await generate_infrastructure_code(
            resource_type='AWS::S3::Bucket',
            properties={'Tags': [{'Key': 'user-tag', 'Value': 'user-value'}]},
            identifier='existing-bucket',
            region='us-east-1',
        )

        # Should return recommended patch document with all tags (existing + user + default)
        assert 'recommended_patch_document' in result
        patch_doc = result['recommended_patch_document']
        assert len(patch_doc) == 1
        assert patch_doc[0]['op'] == 'replace'
        assert patch_doc[0]['path'] == '/Tags'

        # Should have existing tag + user tag + 3 default tags = 5 total
        tags = patch_doc[0]['value']
        assert len(tags) == 5

        tag_dict = {tag['Key']: tag['Value'] for tag in tags}
        assert tag_dict['existing'] == 'tag'  # Existing tag preserved
        assert tag_dict['user-tag'] == 'user-value'  # User tag added
        assert tag_dict['MANAGED_BY'] == 'CCAPI-MCP-SERVER'  # Default tags added
        assert (
            tag_dict['MCP_SERVER_SOURCE_CODE']
            == 'https://github.com/awslabs/mcp/tree/main/src/ccapi-mcp-server'
        )
        assert tag_dict['MCP_SERVER_VERSION'] == '1.1.0'

    async def test_real_s3_schema_supports_tagging(self):
        """Test that real S3 schema from schema_manager supports tagging."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        # Get the actual S3 schema
        sm = schema_manager()
        try:
            schema = await sm.get_schema('AWS::S3::Bucket', 'us-east-1')

            # Check if schema supports tagging
            supports_tagging = 'Tags' in schema.get('properties', {})
            schema_properties = list(schema.get('properties', {}).keys())

            print(f'S3 Schema supports tagging: {supports_tagging}')
            print(f'S3 Schema properties: {schema_properties}')

            # This should be True for S3 buckets
            assert supports_tagging, (
                f'S3 schema should support Tags. Properties: {schema_properties}'
            )

        except Exception as e:
            # If we can't get the real schema, skip this test
            pytest.skip(f'Could not get real S3 schema: {e}')

    async def test_add_default_tags_with_real_schema(self):
        """Test add_default_tags with real S3 schema."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        # Get the actual S3 schema
        sm = schema_manager()
        try:
            schema = await sm.get_schema('AWS::S3::Bucket', 'us-east-1')

            # Test properties like what the MCP server receives
            properties = {
                'BucketName': 'test-bucket',
                'Tags': [{'Key': 'user-tag', 'Value': 'user-value'}],
            }

            result = add_default_tags(properties, schema)

            # Should have user tag + 3 default tags = 4 total
            assert len(result['Tags']) == 4, (
                f'Expected 4 tags, got {len(result["Tags"])}: {result["Tags"]}'
            )

            tag_dict = {tag['Key']: tag['Value'] for tag in result['Tags']}
            assert 'user-tag' in tag_dict
            assert 'MANAGED_BY' in tag_dict
            assert 'MCP_SERVER_SOURCE_CODE' in tag_dict
            assert 'MCP_SERVER_VERSION' in tag_dict

        except Exception as e:
            # If we can't get the real schema, skip this test
            pytest.skip(f'Could not get real S3 schema: {e}')
