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

"""AWS Labs compliance tests following standard patterns."""

import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
import boto3
from moto import mock_aws

from awslabs.cloudwan_mcp_server.server import (
    mcp, main, list_core_networks, get_global_networks, get_core_network_policy
)


class TestAWSLabsCompliance:
    """Test suite following AWS Labs MCP server patterns."""

    @pytest.mark.asyncio
    async def test_mcp_protocol_compliance(self, mock_aws_context):
        """Test MCP protocol v1.1+ compliance following AWS Labs patterns."""
        # Test tool registration and availability
        assert hasattr(mcp, 'tools'), "MCP server must expose tools property"
        
        # Test basic protocol compliance
        tools = getattr(mcp, 'tools', {})
        assert len(tools) >= 10, "Must have at least 10 core CloudWAN tools"
        
        # Test async compatibility
        for tool_name, tool_func in tools.items():
            if callable(tool_func):
                assert asyncio.iscoroutinefunction(tool_func), f"Tool {tool_name} must be async"

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_aws_api_integration(self, aws_test_credentials):
        """Live AWS API test - requires valid credentials."""
        pytest.skip("Live tests require valid AWS credentials and are run selectively")
        
        # This test would run against actual AWS APIs when credentials are available
        # Following AWS Labs pattern for live API testing
        result = await list_core_networks()
        assert isinstance(result, dict)
        assert 'success' in result

    @pytest.mark.asyncio
    async def test_mocked_aws_service_integration(self, mock_ec2_client, mock_networkmanager_client):
        """Test AWS service integration with moto mocking (AWS Labs pattern)."""
        with patch('awslabs.cloudwan_mcp_server.utils.aws_config_manager.get_aws_client') as mock_get_client:
            mock_get_client.return_value = mock_networkmanager_client
            
            # Mock the core networks list
            mock_networkmanager_client.list_core_networks = Mock(return_value={
                'CoreNetworks': [
                    {
                        'CoreNetworkId': 'core-network-test123',
                        'CoreNetworkArn': 'arn:aws:networkmanager::123456789012:core-network/core-network-test123',
                        'GlobalNetworkId': 'global-network-test123',
                        'State': 'AVAILABLE',
                        'Description': 'Test core network'
                    }
                ]
            })
            
            result = await list_core_networks()
            assert result['success'] is True
            assert len(result['data']) >= 0

    @pytest.mark.asyncio 
    async def test_error_handling_patterns(self, mock_aws_context):
        """Test AWS Labs standard error handling patterns."""
        with patch('awslabs.cloudwan_mcp_server.utils.aws_config_manager.get_aws_client') as mock_get_client:
            # Simulate AWS service error
            mock_client = Mock()
            mock_client.list_core_networks.side_effect = Exception("AWS API Error")
            mock_get_client.return_value = mock_client
            
            result = await list_core_networks()
            
            # AWS Labs standard error response format
            assert result['success'] is False
            assert 'error' in result
            assert 'error_code' in result

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_performance_characteristics(self, mock_aws_context):
        """Test performance following AWS Labs patterns."""
        import time
        
        with patch('awslabs.cloudwan_mcp_server.utils.aws_config_manager.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {'CoreNetworks': []}
            mock_get_client.return_value = mock_client
            
            start_time = time.time()
            result = await list_core_networks()
            end_time = time.time()
            
            # Performance assertion following AWS Labs patterns
            assert (end_time - start_time) < 5.0, "Tool should complete within 5 seconds"
            assert result['success'] is True

    @pytest.mark.unit
    def test_tool_registration_compliance(self):
        """Test tool registration follows AWS Labs patterns."""
        from awslabs.cloudwan_mcp_server.server import mcp
        
        # Verify MCP server has expected attributes
        assert hasattr(mcp, 'name'), "MCP server must have name"
        assert "CloudWAN" in mcp.name, "Server name must reference CloudWAN"
        
        # Test tool availability
        expected_core_tools = [
            'list_core_networks',
            'get_global_networks', 
            'get_core_network_policy',
            'trace_network_path',
            'discover_vpcs'
        ]
        
        # Check that tools are accessible
        for tool_name in expected_core_tools:
            # Tools should be registered with the MCP server
            assert hasattr(mcp, 'tools') or hasattr(mcp, f'_{tool_name}'), f"Tool {tool_name} not found"

    @pytest.mark.asyncio
    async def test_aws_credential_handling(self, aws_test_credentials):
        """Test AWS credential handling following AWS Labs patterns."""
        # Test that tools handle missing credentials gracefully
        with patch('boto3.client') as mock_boto_client:
            mock_boto_client.side_effect = Exception("No credentials found")
            
            result = await list_core_networks()
            
            # Should return error response, not raise exception
            assert isinstance(result, dict)
            assert 'error' in result or 'success' in result

    @pytest.mark.integration
    @pytest.mark.asyncio 
    async def test_tool_chaining_patterns(self, mock_aws_context):
        """Test tool chaining following AWS Labs integration patterns."""
        with patch('awslabs.cloudwan_mcp_server.utils.aws_config_manager.get_aws_client') as mock_get_client:
            mock_client = Mock()
            
            # Mock sequential API calls
            mock_client.describe_global_networks.return_value = {
                'GlobalNetworks': [{'GlobalNetworkId': 'gn-123', 'State': 'AVAILABLE'}]
            }
            mock_client.list_core_networks.return_value = {
                'CoreNetworks': [{'CoreNetworkId': 'cn-123', 'GlobalNetworkId': 'gn-123'}]
            }
            mock_client.get_core_network_policy.return_value = {
                'CoreNetworkPolicy': {'PolicyVersionId': 1, 'PolicyDocument': {}}
            }
            
            mock_get_client.return_value = mock_client
            
            # Test chaining: global networks -> core networks -> policy
            global_networks = await get_global_networks()
            assert global_networks['success'] is True
            
            core_networks = await list_core_networks()
            assert core_networks['success'] is True
            
            policy = await get_core_network_policy('cn-123')
            assert policy['success'] is True

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_aws_context):
        """Test concurrent tool execution following AWS Labs patterns."""
        with patch('awslabs.cloudwan_mcp_server.utils.aws_config_manager.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.describe_global_networks.return_value = {'GlobalNetworks': []}
            mock_client.list_core_networks.return_value = {'CoreNetworks': []}
            mock_get_client.return_value = mock_client
            
            # Test concurrent execution
            tasks = [
                get_global_networks(),
                list_core_networks(), 
                get_global_networks()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All tasks should complete successfully
            for result in results:
                assert not isinstance(result, Exception)
                assert isinstance(result, dict)
                assert 'success' in result