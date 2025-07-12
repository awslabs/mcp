"""Tests for infrastructure_generator.py module."""

import pytest
from awslabs.ccapi_mcp_server.errors import ClientError
from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code
from unittest.mock import AsyncMock, MagicMock, patch


class TestInfrastructureGenerator:
    """Test infrastructure generation functions."""

    @pytest.mark.asyncio
    async def test_generate_infrastructure_code_no_resource_type(self):
        """Test generate_infrastructure_code with no resource type."""
        with pytest.raises(ClientError, match='Please provide a resource type'):
            await generate_infrastructure_code('')

    @pytest.mark.asyncio
    async def test_generate_infrastructure_code_create_operation(self):
        """Test generate_infrastructure_code for create operation."""
        with patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager') as mock_sm:
            mock_schema_manager = MagicMock()
            mock_schema_manager.get_schema = AsyncMock(
                return_value={
                    'properties': {'BucketName': {'type': 'string'}, 'Tags': {'type': 'array'}}
                }
            )
            mock_sm.return_value = mock_schema_manager

            result = await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket',
                properties={'BucketName': 'test-bucket'},
                region='us-east-1',
            )

            assert result['operation'] == 'create'
            assert result['resource_type'] == 'AWS::S3::Bucket'
            assert 'properties' in result
            assert 'cloudformation_template' in result
            assert result['supports_tagging'] is True

    @pytest.mark.asyncio
    async def test_generate_infrastructure_code_create_no_properties(self):
        """Test generate_infrastructure_code create with no properties."""
        with patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager') as mock_sm:
            mock_schema_manager = MagicMock()
            mock_schema_manager.get_schema = AsyncMock(return_value={'properties': {}})
            mock_sm.return_value = mock_schema_manager

            with pytest.raises(ClientError, match='Please provide the properties'):
                await generate_infrastructure_code(
                    resource_type='AWS::S3::Bucket', region='us-east-1'
                )

    @pytest.mark.asyncio
    async def test_generate_infrastructure_code_update_operation(self):
        """Test generate_infrastructure_code for update operation."""
        with patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager') as mock_sm:
            mock_schema_manager = MagicMock()
            mock_schema_manager.get_schema = AsyncMock(
                return_value={
                    'properties': {'BucketName': {'type': 'string'}, 'Tags': {'type': 'array'}}
                }
            )
            mock_sm.return_value = mock_schema_manager

            with patch(
                'awslabs.ccapi_mcp_server.infrastructure_generator.get_aws_client'
            ) as mock_client:
                mock_client.return_value.get_resource.return_value = {
                    'ResourceDescription': {
                        'Properties': '{"BucketName": "existing-bucket", "Tags": []}'
                    }
                }

                result = await generate_infrastructure_code(
                    resource_type='AWS::S3::Bucket',
                    identifier='existing-bucket',
                    properties={'BucketName': 'updated-bucket'},
                    region='us-east-1',
                )

                assert result['operation'] == 'update'
                assert 'recommended_patch_document' in result

    @pytest.mark.asyncio
    async def test_generate_infrastructure_code_known_taggable_resource(self):
        """Test generate_infrastructure_code with known taggable resource even if schema doesn't show it."""
        with patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager') as mock_sm:
            mock_schema_manager = MagicMock()
            mock_schema_manager.get_schema = AsyncMock(
                return_value={'properties': {'InstanceType': {'type': 'string'}}}
            )
            mock_sm.return_value = mock_schema_manager

            result = await generate_infrastructure_code(
                resource_type='AWS::EC2::Instance',
                properties={'InstanceType': 't2.micro'},
                region='us-east-1',
            )

            # Should still support tagging for known AWS resources
            assert result['supports_tagging'] is True
