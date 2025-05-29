# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the AWS Lambda MCP Server."""

import pytest
from awslabs.aws_serverless_mcp_server.server import (
    describe_schema,
    list_registries,
    search_schema,
)
from unittest.mock import patch


class TestServerIntegration:
    """Integration tests for server tools."""

    def test_server_tool_registration(self):
        """Test tool registration."""
        # Check that the tools are registered
        assert hasattr(describe_schema, '__name__')
        assert hasattr(search_schema, '__name__')
        assert hasattr(list_registries, '__name__')

        # Check that the functions have docstrings
        assert describe_schema.__doc__ is not None
        assert list_registries.__doc__ is not None
        assert search_schema.__doc__ is not None


class TestListRegistries:
    """Tests for list_registries tool."""

    @pytest.mark.asyncio
    async def test_list_registries_basic(mock_context, mock_schemas_client):
        """Test list_registries with basic parameters."""
        with patch('awslabs.aws_serverless_mcp_server.server.schemas_client', mock_schemas_client):
            mock_response = {
                'Registries': [
                    {
                        'RegistryName': 'test-registry',
                        'RegistryArn': 'arn:aws:schemas:us-east-1:123456789012:registry/test-registry',
                    }
                ],
                'NextToken': None,
            }
            mock_schemas_client.list_registries.return_value = mock_response

            result = await list_registries(mock_context)
            mock_schemas_client.list_registries.assert_called_once()
            assert result == {'Registries': mock_response['Registries'], 'NextToken': None}

    @pytest.mark.asyncio
    async def test_list_registries_with_params(mock_context, mock_schemas_client):
        """Test list_registries with all parameters."""
        with patch('awslabs.aws_serverless_mcp_server.server.schemas_client', mock_schemas_client):
            await list_registries(
                mock_context,
                registry_name_prefix='test',
                scope='LOCAL',
                limit=5,
                next_token='token123',
            )
            mock_schemas_client.list_registries.assert_called_once_with(
                RegistryNamePrefix='test', Scope='LOCAL', Limit=5, NextToken='token123'
            )

    @pytest.mark.asyncio
    async def test_error_handling(mock_context, mock_schemas_client):
        """Test error handling in list_registries."""
        with patch('awslabs.aws_serverless_mcp_server.server.schemas_client', mock_schemas_client):
            # Test list_registries error
            mock_schemas_client.list_registries.side_effect = Exception('Test error')
            with pytest.raises(Exception):
                await list_registries(mock_context)


class TestSearchSchema:
    """Tests for search_schema tool."""

    @pytest.mark.asyncio
    async def test_search_schema_basic(mock_context, mock_schemas_client):
        """Test search_schema with required parameters."""
        with patch('awslabs.aws_serverless_mcp_server.server.schemas_client', mock_schemas_client):
            mock_response = {
                'Schemas': [
                    {
                        'SchemaName': 'test-schema',
                        'SchemaArn': 'arn:aws:schemas:us-east-1:123456789012:schema/test-registry/test-schema',
                    }
                ],
                'NextToken': None,
            }
            mock_schemas_client.search_schemas.return_value = mock_response

            result = await search_schema(
                mock_context, keywords='test', registry_name='test-registry'
            )
            mock_schemas_client.search_schemas.assert_called_once()
            call_args = mock_schemas_client.search_schemas.call_args[1]
            assert call_args['Keywords'] == 'test'
            assert call_args['RegistryName'] == 'test-registry'
            assert result == {'Schemas': mock_response['Schemas'], 'NextToken': None}

    @pytest.mark.asyncio
    async def test_search_schema_with_params(mock_context, mock_schemas_client):
        """Test search_schema with all parameters."""
        with patch('awslabs.aws_serverless_mcp_server.server.schemas_client', mock_schemas_client):
            await search_schema(
                mock_context,
                keywords='test',
                registry_name='test-registry',
                limit=5,
                next_token='token123',
            )
            mock_schemas_client.search_schemas.assert_called_once_with(
                Keywords='test', RegistryName='test-registry', Limit='5', NextToken='token123'
            )

    @pytest.mark.asyncio
    async def test_error_handling(mock_context, mock_schemas_client):
        """Test error handling in search_schemas."""
        with patch('awslabs.aws_serverless_mcp_server.server.schemas_client', mock_schemas_client):
            # Test search_schema error
            mock_schemas_client.search_schemas.side_effect = Exception('Test error')
            with pytest.raises(Exception):
                await search_schema(mock_context, keywords='test', registry_name='test-registry')


class TestDescribeSchema:
    """Tests for describe_schema tool."""

    @pytest.mark.asyncio
    async def test_describe_schema_basic(mock_context, mock_schemas_client):
        """Test describe_schema with required parameters."""
        with patch('awslabs.aws_serverless_mcp_server.server.schemas_client', mock_schemas_client):
            mock_response = {
                'SchemaName': 'test-schema',
                'SchemaArn': 'arn:aws:schemas:us-east-1:123456789012:schema/test-registry/test-schema',
                'Content': '{"type": "object"}',
                'SchemaVersion': '1',
                'LastModified': '2025-05-09T12:00:00Z',
            }
            mock_schemas_client.describe_schema.return_value = mock_response

            result = await describe_schema(
                mock_context, registry_name='test-registry', schema_name='test-schema'
            )
            mock_schemas_client.describe_schema.assert_called_once()
            call_args = mock_schemas_client.describe_schema.call_args[1]
            assert call_args['RegistryName'] == 'test-registry'
            assert call_args['SchemaName'] == 'test-schema'
            assert result == {
                'SchemaName': mock_response['SchemaName'],
                'SchemaArn': mock_response['SchemaArn'],
                'SchemaVersion': mock_response['SchemaVersion'],
                'Content': mock_response['Content'],
                'LastModified': mock_response['LastModified'],
            }

    @pytest.mark.asyncio
    async def test_describe_schema_with_version(mock_context, mock_schemas_client):
        """Test describe_schema with version parameter."""
        with patch('awslabs.aws_serverless_mcp_server.server.schemas_client', mock_schemas_client):
            await describe_schema(
                mock_context,
                registry_name='test-registry',
                schema_name='test-schema',
                schema_version='1',
            )
            mock_schemas_client.describe_schema.assert_called_once_with(
                RegistryName='test-registry', SchemaName='test-schema', SchemaVersion='1'
            )

    @pytest.mark.asyncio
    async def test_error_handling(mock_context, mock_schemas_client):
        """Test error handling in describe_schema."""
        with patch('awslabs.aws_serverless_mcp_server.server.schemas_client', mock_schemas_client):
            # Test describe_schema error
            mock_schemas_client.describe_schema.side_effect = Exception('Test error')
            with pytest.raises(Exception):
                await describe_schema(
                    mock_context, registry_name='test-registry', schema_name='test-schema'
                )
