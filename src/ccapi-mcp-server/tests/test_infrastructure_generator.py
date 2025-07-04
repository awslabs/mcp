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
