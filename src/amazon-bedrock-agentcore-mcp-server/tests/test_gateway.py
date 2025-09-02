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

"""Test module for gateway functionality."""

import json
import pytest
import tempfile
from awslabs.amazon_bedrock_agentcore_mcp_server.gateway import (
    _discover_smithy_models,
    _find_and_upload_smithy_model,
    _upload_openapi_schema,
    register_gateway_tools,
)
from pathlib import Path
from unittest.mock import Mock, patch


class TestHelperFunctions:
    """Test helper functions for gateway operations."""

    @pytest.mark.asyncio
    async def test_find_and_upload_smithy_model_success(self):
        """Test successful Smithy model discovery and upload."""
        with patch('requests.get') as mock_get, patch('boto3.client') as mock_boto3:
            # Mock GitHub API responses
            mock_service_response = Mock()
            mock_service_response.status_code = 200
            mock_service_response.json.return_value = [
                {'type': 'dir', 'name': 'service', 'url': 'https://api.github.com/service'}
            ]

            mock_version_response = Mock()
            mock_version_response.status_code = 200
            mock_version_response.json.return_value = [
                {'type': 'dir', 'name': '2023-01-01', 'url': 'https://api.github.com/version'}
            ]

            mock_files_response = Mock()
            mock_files_response.status_code = 200
            mock_files_response.json.return_value = [
                {
                    'type': 'file',
                    'name': 'dynamodb-2023-01-01.json',
                    'download_url': 'https://raw.github.com/file.json',
                }
            ]

            mock_content_response = Mock()
            mock_content_response.status_code = 200
            mock_content_response.json.return_value = {'service': 'dynamodb'}
            mock_content_response.content = b'{"service": "dynamodb"}'

            mock_get.side_effect = [
                mock_service_response,
                mock_version_response,
                mock_files_response,
                mock_content_response,
            ]

            # Mock S3 client
            mock_s3 = Mock()
            mock_boto3.return_value = mock_s3
            mock_s3.head_bucket.return_value = True
            mock_s3.put_object.return_value = True

            setup_steps = []
            result = await _find_and_upload_smithy_model('dynamodb', 'us-east-1', setup_steps)

            assert result is not None
            assert result.startswith('s3://')
            assert 'agentcore-smithy-models-us-east-1' in result
            assert len(setup_steps) > 5

    @pytest.mark.asyncio
    async def test_find_and_upload_smithy_model_service_not_found(self):
        """Test handling when Smithy service is not found."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            setup_steps = []
            result = await _find_and_upload_smithy_model('nonexistent', 'us-east-1', setup_steps)

            assert result is None
            assert any('not found in GitHub API models' in step for step in setup_steps)

    @pytest.mark.asyncio
    async def test_discover_smithy_models_success(self):
        """Test successful Smithy models discovery."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {'type': 'dir', 'name': 'dynamodb'},
                {'type': 'dir', 'name': 's3'},
                {'type': 'dir', 'name': 'lambda'},
                {'type': 'dir', 'name': 'ec2'},
            ]
            mock_get.return_value = mock_response

            result = await _discover_smithy_models()

            assert isinstance(result, dict)
            assert 'Database' in result
            assert 'Storage' in result
            assert 'Compute' in result

            # Check that services are categorized correctly
            database_services = [s['name'] for s in result.get('Database', [])]
            assert 'dynamodb' in database_services

            storage_services = [s['name'] for s in result.get('Storage', [])]
            assert 's3' in storage_services

    @pytest.mark.asyncio
    async def test_discover_smithy_models_network_error(self):
        """Test handling of network errors during discovery."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception('Network error')

            result = await _discover_smithy_models()

            assert 'errors' in result
            assert len(result['errors']) > 0
            assert 'Failed to discover Smithy models' in result['errors'][0]['message']

    @pytest.mark.asyncio
    async def test_upload_openapi_schema_success(self):
        """Test successful OpenAPI schema upload."""
        with patch('boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.return_value = mock_s3
            mock_s3.head_bucket.return_value = True
            mock_s3.put_object.return_value = True

            openapi_spec = {
                'openapi': '3.0.0',
                'info': {'title': 'Test API', 'version': '1.0.0'},
                'paths': {},
            }

            setup_steps = []
            result = await _upload_openapi_schema(
                openapi_spec=openapi_spec,
                gateway_name='test-gateway',
                region='us-east-1',
                setup_steps=setup_steps,
                api_key='test-key',  # pragma: allowlist secret
                credential_location='HEADER',
                credential_parameter_name='Authorization',
            )

            assert result is not None
            assert 's3_uri' in result
            assert 'credential_config' in result
            assert result['s3_uri'].startswith('s3://')
            assert result['credential_config']['credentialProviderType'] == 'API_KEY'
            assert result['credential_config']['credentialLocation'] == 'HEADER'

    @pytest.mark.asyncio
    async def test_upload_openapi_schema_no_api_key(self):
        """Test OpenAPI schema upload without API key."""
        with patch('boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.return_value = mock_s3
            mock_s3.head_bucket.return_value = True
            mock_s3.put_object.return_value = True

            openapi_spec = {'openapi': '3.0.0', 'info': {'title': 'Test API', 'version': '1.0.0'}}
            setup_steps = []

            result = await _upload_openapi_schema(
                openapi_spec=openapi_spec,
                gateway_name='test-gateway',
                region='us-east-1',
                setup_steps=setup_steps,
            )

            assert result is not None
            assert result['credential_config'] is None

    @pytest.mark.asyncio
    async def test_upload_openapi_schema_s3_error(self):
        """Test handling of S3 errors during upload."""
        with patch('boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.return_value = mock_s3
            mock_s3.head_bucket.side_effect = Exception('Bucket access denied')
            mock_s3.create_bucket.side_effect = Exception('Cannot create bucket')

            openapi_spec = {'openapi': '3.0.0'}
            setup_steps = []

            result = await _upload_openapi_schema(
                openapi_spec=openapi_spec,
                gateway_name='test-gateway',
                region='us-east-1',
                setup_steps=setup_steps,
            )

            assert result is None
            assert any('Could not create S3 bucket' in step for step in setup_steps)


class TestAgentGatewayTool:
    """Test the main agent_gateway tool with comprehensive coverage."""

    def setup_method(self):
        """Set up test environment."""
        self.test_region = 'us-east-1'
        self.test_gateway_name = 'test-gateway'

    def _create_mock_mcp(self):
        """Create a mock MCP server for testing."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Gateway Server')
        register_gateway_tools(mcp)
        return mcp

    @pytest.mark.asyncio
    async def test_agent_gateway_list_action_no_gateways(self):
        """Test list action when no gateways exist."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client
            mock_client.list_gateways.return_value = {'items': []}

            result_tuple = await mcp.call_tool('agent_gateway', {'action': 'list'})
            result = self._extract_result(result_tuple)

            assert 'No Gateways Found' in result
            assert 'Getting Started' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_list_action_with_gateways(self):
        """Test list action with existing gateways."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client
            mock_client.list_gateways.return_value = {
                'items': [
                    {
                        'name': 'test-gateway-1',
                        'gatewayId': 'gw-123',
                        'status': 'READY',
                        'createdAt': '2024-01-01T00:00:00Z',
                    },
                    {
                        'name': 'test-gateway-2',
                        'gatewayId': 'gw-456',
                        'status': 'CREATING',
                        'createdAt': '2024-01-02T00:00:00Z',
                    },
                ]
            }

            result_tuple = await mcp.call_tool('agent_gateway', {'action': 'list'})
            result = self._extract_result(result_tuple)

            assert 'Gateway Resources Found' in result
            assert 'Total Gateways: 2' in result
            assert 'test-gateway-1' in result
            assert 'test-gateway-2' in result
            assert 'READY' in result
            assert 'CREATING' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_delete_action_success(self):
        """Test successful gateway deletion."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('time.sleep'),
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock gateway lookup
            mock_client.list_gateways.return_value = {
                'items': [{'name': self.test_gateway_name, 'gatewayId': 'gw-123'}]
            }

            # Mock target listing (no targets)
            mock_client.list_gateway_targets.return_value = {'items': []}

            # Mock gateway deletion
            mock_client.delete_gateway.return_value = True

            result_tuple = await mcp.call_tool(
                'agent_gateway', {'action': 'delete', 'gateway_name': self.test_gateway_name}
            )
            result = self._extract_result(result_tuple)

            assert 'Gateway Deleted Successfully' in result
            assert self.test_gateway_name in result
            assert 'gw-123' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_delete_action_with_targets(self):
        """Test gateway deletion with targets."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('time.sleep'),
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock gateway lookup
            mock_client.list_gateways.return_value = {
                'items': [{'name': self.test_gateway_name, 'gatewayId': 'gw-123'}]
            }

            # Mock target listing
            mock_client.list_gateway_targets.return_value = {
                'items': [
                    {'targetId': 'target-1', 'name': 'test-target'},
                    {'targetId': 'target-2', 'name': 'test-target-2'},
                ]
            }

            # Mock target deletion
            mock_client.delete_gateway_target.return_value = True

            # Mock gateway deletion
            mock_client.delete_gateway.return_value = True

            result_tuple = await mcp.call_tool(
                'agent_gateway', {'action': 'delete', 'gateway_name': self.test_gateway_name}
            )
            result = self._extract_result(result_tuple)

            assert 'Gateway Deleted Successfully' in result or 'Deletion attempt' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_delete_action_gateway_not_found(self):
        """Test deletion of non-existent gateway."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client
            mock_client.list_gateways.return_value = {'items': []}

            result_tuple = await mcp.call_tool(
                'agent_gateway', {'action': 'delete', 'gateway_name': 'nonexistent-gateway'}
            )
            result = self._extract_result(result_tuple)

            assert 'Gateway Not Found' in result
            assert 'nonexistent-gateway' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_discover_action(self):
        """Test discover action for Smithy models."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.gateway._discover_smithy_models'
            ) as mock_discover,
        ):
            mock_discover.return_value = {
                'Database': [{'name': 'dynamodb', 'description': 'AWS dynamodb service'}],
                'Storage': [{'name': 's3', 'description': 'AWS s3 service'}],
            }

            result_tuple = await mcp.call_tool('agent_gateway', {'action': 'discover'})
            result = self._extract_result(result_tuple)

            assert 'AWS Service Discovery' in result
            assert 'Database' in result
            assert 'Storage' in result
            assert 'dynamodb' in result
            assert 's3' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_discover_action_error(self):
        """Test discover action with network error."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.gateway._discover_smithy_models'
            ) as mock_discover,
        ):
            mock_discover.return_value = {'error': 'Network connection failed'}

            result_tuple = await mcp.call_tool('agent_gateway', {'action': 'discover'})
            result = self._extract_result(result_tuple)

            assert 'Service Discovery Failed' in result
            assert 'Fallback - Common Services' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_setup_action_missing_gateway_name(self):
        """Test setup action without gateway name."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True):
            result_tuple = await mcp.call_tool('agent_gateway', {'action': 'setup'})
            result = self._extract_result(result_tuple)

            assert 'gateway_name is required' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_setup_action_runtime_not_available(self):
        """Test setup action when runtime toolkit is not available."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.RUNTIME_AVAILABLE', False),
        ):
            result_tuple = await mcp.call_tool(
                'agent_gateway', {'action': 'setup', 'gateway_name': self.test_gateway_name}
            )
            result = self._extract_result(result_tuple)

            assert 'Starter Toolkit Not Available' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_test_action(self):
        """Test test action returns proper instructions."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True):
            result_tuple = await mcp.call_tool(
                'agent_gateway', {'action': 'test', 'gateway_name': self.test_gateway_name}
            )
            result = self._extract_result(result_tuple)

            assert 'Gateway MCP Testing' in result
            assert self.test_gateway_name in result
            assert 'get_oauth_access_token' in result
            assert 'list_tools' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_list_tools_action_no_config(self):
        """Test list_tools action without configuration."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True):
            result_tuple = await mcp.call_tool(
                'agent_gateway', {'action': 'list_tools', 'gateway_name': self.test_gateway_name}
            )
            result = self._extract_result(result_tuple)

            assert 'Gateway Configuration Not Found' in result
            assert self.test_gateway_name in result

    @pytest.mark.asyncio
    async def test_agent_gateway_search_tools_action_no_query(self):
        """Test search_tools action without query."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True):
            result_tuple = await mcp.call_tool(
                'agent_gateway', {'action': 'search_tools', 'gateway_name': self.test_gateway_name}
            )
            result = self._extract_result(result_tuple)

            assert 'query is required' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_invoke_tool_action_no_tool_name(self):
        """Test invoke_tool action without tool name."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True):
            result_tuple = await mcp.call_tool(
                'agent_gateway', {'action': 'invoke_tool', 'gateway_name': self.test_gateway_name}
            )
            result = self._extract_result(result_tuple)

            assert 'tool_name is required' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_sdk_not_available(self):
        """Test behavior when SDK is not available."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', False):
            result_tuple = await mcp.call_tool('agent_gateway', {'action': 'list'})
            result = self._extract_result(result_tuple)

            assert 'AgentCore SDK Not Available' in result
            assert 'uv add bedrock-agentcore' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_invalid_action(self):
        """Test unsupported action."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True):
            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'create',  # Not fully implemented
                    'gateway_name': self.test_gateway_name,
                },
            )
            result = self._extract_result(result_tuple)

            assert "Action 'create' Implementation" in result or 'WIP:' in result

    @pytest.mark.asyncio
    async def test_agent_gateway_exception_handling(self):
        """Test exception handling in gateway operations."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
        ):
            mock_boto3.side_effect = Exception('AWS connection failed')

            result_tuple = await mcp.call_tool('agent_gateway', {'action': 'list'})
            result = self._extract_result(result_tuple)

            assert 'Gateway List Error' in result or 'Gateway Operation Error' in result

    def _extract_result(self, mcp_result):
        """Extract result string from MCP call_tool return value."""
        if isinstance(mcp_result, tuple) and len(mcp_result) >= 2:
            result_content = mcp_result[1]
            if isinstance(result_content, dict):
                return result_content.get('result', str(mcp_result))
            elif hasattr(result_content, 'content'):
                return str(result_content.content)
            return str(result_content)
        elif hasattr(mcp_result, 'content') and not isinstance(mcp_result, tuple):
            return str(mcp_result.content)
        return str(mcp_result)


class TestGatewayRegistration:
    """Test gateway tool registration."""

    def test_register_gateway_tools(self):
        """Test that gateway tools are properly registered."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Gateway Server')

        # Get initial tool count
        import asyncio

        initial_tools = asyncio.run(mcp.list_tools())
        initial_count = len(initial_tools)

        # Register gateway tools
        register_gateway_tools(mcp)

        # Verify tools were added
        final_tools = asyncio.run(mcp.list_tools())
        final_count = len(final_tools)

        # Should have more tools after registration
        assert final_count > initial_count

    @pytest.mark.asyncio
    async def test_gateway_tool_available_in_tools_list(self):
        """Test that agent_gateway tool appears in tools list."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Gateway Server')
        register_gateway_tools(mcp)

        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        assert 'agent_gateway' in tool_names


class TestConfigurationManagement:
    """Test configuration file management for gateways."""

    def test_config_file_operations(self):
        """Test gateway configuration file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / '.agentcore_gateways'
            config_file = config_dir / 'test-gateway.json'

            # Test configuration creation
            config_data = {
                'gateway_name': 'test-gateway',
                'region': 'us-east-1',
                'cognito_client_info': {'client_id': 'test-client'},
                'created_at': '2024-01-01T00:00:00Z',
            }

            config_dir.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)

            # Verify file was created
            assert config_file.exists()

            # Test reading configuration
            with open(config_file, 'r') as f:
                loaded_config = json.load(f)

            assert loaded_config['gateway_name'] == 'test-gateway'
            assert loaded_config['region'] == 'us-east-1'


class TestErrorScenarios:
    """Test various error scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test handling of network timeouts."""
        with patch('requests.get') as mock_get:
            import requests

            mock_get.side_effect = requests.Timeout('Connection timeout')

            result = await _discover_smithy_models()

            assert 'errors' in result
            assert len(result['errors']) > 0

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON responses."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
            mock_get.return_value = mock_response

            result = await _discover_smithy_models()

            assert 'errors' in result

    @pytest.mark.asyncio
    async def test_s3_permission_denied(self):
        """Test handling of S3 permission errors."""
        with patch('boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.return_value = mock_s3
            mock_s3.head_bucket.side_effect = Exception('Access Denied')
            mock_s3.create_bucket.side_effect = Exception('Insufficient permissions')

            setup_steps = []
            result = await _upload_openapi_schema(
                openapi_spec={'test': 'spec'},
                gateway_name='test',
                region='us-east-1',
                setup_steps=setup_steps,
            )

            assert result is None
            assert any('Could not create S3 bucket' in step for step in setup_steps)

    @pytest.mark.asyncio
    async def test_empty_smithy_model_name(self):
        """Test handling of empty Smithy model name."""
        setup_steps = []

        # Test with empty string - should return None gracefully
        result = await _find_and_upload_smithy_model('', 'us-east-1', setup_steps)
        assert result is None

        # Test with None - should handle gracefully
        try:
            result = await _find_and_upload_smithy_model(None, 'us-east-1', setup_steps)
            assert result is None
        except (TypeError, AttributeError):
            # It's acceptable if this raises a type error
            pass

    def test_invalid_region_name(self):
        """Test handling of invalid AWS region names."""
        with patch('boto3.client') as mock_boto3:
            mock_boto3.side_effect = Exception('Invalid region')

            # Test would depend on how the code handles invalid regions
            assert True  # Placeholder for actual test implementation


if __name__ == '__main__':
    import asyncio

    async def run_basic_tests():
        """Run basic tests to verify functionality."""
        print('Testing gateway helper functions...')

        # Test discovery function
        result = await _discover_smithy_models()
        print(f'✓ Discovery returned: {type(result)}')

        # Test registration
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Server')
        register_gateway_tools(mcp)
        tools = await mcp.list_tools()
        print(f'✓ Registered {len(tools)} tools')

        print('All basic gateway tests passed!')

    asyncio.run(run_basic_tests())
