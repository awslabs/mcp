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

    # Additional coverage tests
    @pytest.mark.asyncio
    async def test_infrastructure_generator_patch_edge_cases(self):
        """Test infrastructure generator patch edge cases."""
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
                    'ResourceDescription': {'Properties': '{"BucketName": "test", "Tags": []}'}
                }

                # Test with move operation
                result = await generate_infrastructure_code(
                    resource_type='AWS::S3::Bucket',
                    identifier='test-bucket',
                    patch_document=[
                        {'op': 'move', 'from': '/BucketName', 'path': '/NewBucketName'}
                    ],
                    region='us-east-1',
                )

                assert result['operation'] == 'update'

    @pytest.mark.asyncio
    async def test_infrastructure_generator_tag_merging(self):
        """Test tag merging logic."""
        with patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager') as mock_sm:
            mock_schema_manager = MagicMock()
            mock_schema_manager.get_schema = AsyncMock(
                return_value={'properties': {'Tags': {'type': 'array'}}}
            )
            mock_sm.return_value = mock_schema_manager

            with patch(
                'awslabs.ccapi_mcp_server.infrastructure_generator.get_aws_client'
            ) as mock_client:
                mock_client.return_value.get_resource.return_value = {
                    'ResourceDescription': {
                        'Properties': '{"BucketName": "test", "Tags": [{"Key": "Existing", "Value": "Tag"}]}'
                    }
                }

                # Test patch operation that adds invalid tag format
                result = await generate_infrastructure_code(
                    resource_type='AWS::S3::Bucket',
                    identifier='test-bucket',
                    patch_document=[
                        {'op': 'add', 'path': '/Tags/-', 'value': 'invalid-string-tag'},
                        {'op': 'add', 'path': '/Tags/-', 'value': {'InvalidKey': 'NoKeyValue'}},
                    ],
                    region='us-east-1',
                )

                # Should filter out invalid tags
                assert result['operation'] == 'update'

    @pytest.mark.asyncio
    async def test_infrastructure_generator_no_existing_resource(self):
        """Test infrastructure generator when resource doesn't exist."""
        with patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager') as mock_sm:
            mock_schema_manager = MagicMock()
            mock_schema_manager.get_schema = AsyncMock(
                return_value={'properties': {'BucketName': {'type': 'string'}}}
            )
            mock_sm.return_value = mock_schema_manager

            with patch(
                'awslabs.ccapi_mcp_server.infrastructure_generator.get_aws_client'
            ) as mock_client:
                # Resource doesn't exist
                mock_client.return_value.get_resource.side_effect = Exception('ResourceNotFound')

                with pytest.raises(ClientError):
                    await generate_infrastructure_code(
                        resource_type='AWS::S3::Bucket',
                        identifier='nonexistent-bucket',
                        patch_document=[
                            {'op': 'replace', 'path': '/BucketName', 'value': 'new-name'}
                        ],
                        region='us-east-1',
                    )

    @pytest.mark.asyncio
    async def test_infrastructure_generator_no_identifier_update(self):
        """Test infrastructure generator update without identifier."""
        with patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager') as mock_sm:
            mock_schema_manager = MagicMock()
            mock_schema_manager.get_schema = AsyncMock(
                return_value={'properties': {'BucketName': {'type': 'string'}}}
            )
            mock_sm.return_value = mock_schema_manager

            with pytest.raises(ClientError):
                await generate_infrastructure_code(
                    resource_type='AWS::S3::Bucket',
                    identifier='',  # Empty identifier
                    patch_document=[{'op': 'replace', 'path': '/BucketName', 'value': 'new-name'}],
                    region='us-east-1',
                )

    @pytest.mark.asyncio
    async def test_infrastructure_generator_copy_operation(self):
        """Test infrastructure generator with copy operation."""
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
                        'Properties': '{"BucketName": "test", "Tags": [{"Key": "Source", "Value": "Tag"}]}'
                    }
                }

                result = await generate_infrastructure_code(
                    resource_type='AWS::S3::Bucket',
                    identifier='test-bucket',
                    patch_document=[
                        {'op': 'copy', 'from': '/Tags/0', 'path': '/Tags/-'},
                        {'op': 'test', 'path': '/BucketName', 'value': 'test'},
                    ],
                    region='us-east-1',
                )

                assert result['operation'] == 'update'

    @pytest.mark.asyncio
    async def test_infrastructure_generator_remove_operation(self):
        """Test infrastructure generator with remove operation."""
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
                        'Properties': '{"BucketName": "test", "Tags": [{"Key": "Remove", "Value": "Me"}]}'
                    }
                }

                result = await generate_infrastructure_code(
                    resource_type='AWS::S3::Bucket',
                    identifier='test-bucket',
                    patch_document=[{'op': 'remove', 'path': '/Tags/0'}],
                    region='us-east-1',
                )

                assert result['operation'] == 'update'

    @pytest.mark.asyncio
    async def test_infrastructure_generator_add_tags_operation(self):
        """Test infrastructure generator with add tags operation."""
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
                    'ResourceDescription': {'Properties': '{"BucketName": "test", "Tags": []}'}
                }

                # Test with add operation for entire Tags array
                result = await generate_infrastructure_code(
                    resource_type='AWS::S3::Bucket',
                    identifier='test-bucket',
                    patch_document=[
                        {
                            'op': 'add',
                            'path': '/Tags',
                            'value': [{'Key': 'NewTag', 'Value': 'NewValue'}],
                        }
                    ],
                    region='us-east-1',
                )

                assert result['operation'] == 'update'
                assert any(tag['Key'] == 'NewTag' for tag in result['properties']['Tags'])

    @pytest.mark.asyncio
    async def test_infrastructure_generator_replace_tags_operation(self):
        """Test infrastructure generator with replace tags operation."""
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
                        'Properties': '{"BucketName": "test", "Tags": [{"Key": "OldTag", "Value": "OldValue"}]}'
                    }
                }

                # Test with replace operation for Tags
                result = await generate_infrastructure_code(
                    resource_type='AWS::S3::Bucket',
                    identifier='test-bucket',
                    patch_document=[
                        {
                            'op': 'replace',
                            'path': '/Tags',
                            'value': [{'Key': 'ReplacedTag', 'Value': 'ReplacedValue'}],
                        }
                    ],
                    region='us-east-1',
                )

                assert result['operation'] == 'update'
                assert any(tag['Key'] == 'ReplacedTag' for tag in result['properties']['Tags'])

    @pytest.mark.asyncio
    async def test_infrastructure_generator_update_with_properties(self):
        """Test infrastructure generator update with properties instead of patch document."""
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
                        'Properties': '{"BucketName": "test", "Tags": [{"Key": "OldTag", "Value": "OldValue"}]}'
                    }
                }

                # Test update with properties instead of patch document
                result = await generate_infrastructure_code(
                    resource_type='AWS::S3::Bucket',
                    identifier='test-bucket',
                    properties={
                        'BucketName': 'updated-bucket',
                        'Tags': [{'Key': 'NewTag', 'Value': 'NewValue'}],
                    },
                    region='us-east-1',
                )

                assert result['operation'] == 'update'
                assert result['properties']['BucketName'] == 'updated-bucket'
                assert any(tag['Key'] == 'NewTag' for tag in result['properties']['Tags'])
