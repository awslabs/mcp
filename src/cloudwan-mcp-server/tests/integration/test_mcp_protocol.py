"""MCP protocol compliance tests."""
import pytest
import json
from unittest.mock import Mock, patch

from awslabs.cloudwan_mcp_server.server import (
    trace_network_path, list_core_networks, get_global_networks
)

class TestMCPProtocol:
    """Test MCP protocol compliance using direct server function calls."""
    
    @pytest.mark.asyncio
    async def test_protocol_tool_execution(self):
        """Test MCP tool execution compliance."""
        # Mock AWS client for protocol testing
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {
                'CoreNetworks': [
                    {'CoreNetworkId': 'core-network-protocol-test', 'State': 'AVAILABLE'}
                ]
            }
            mock_get_client.return_value = mock_client
            
            # Test core networks listing
            result = await list_core_networks()
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert "core_networks" in parsed
            assert len(parsed["core_networks"]) == 1

    @pytest.mark.asyncio
    async def test_tool_error_handling_compliance(self):
        """Test MCP error handling compliance."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Protocol test error")
            
            result = await get_global_networks()
            parsed = json.loads(result)
            
            # Verify AWS Labs compliant error format
            assert parsed["success"] is False
            assert "error" in parsed
            assert "error_code" in parsed  # This should now work with our fix