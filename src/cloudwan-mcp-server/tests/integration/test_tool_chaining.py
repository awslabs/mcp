"""Integration tests for tool chaining scenarios."""
import pytest
import json

class TestToolChaining:
    """Test multi-tool workflows."""
    
    @pytest.mark.asyncio
    async def test_core_network_analysis_chain(self, mock_aws_client):
        """Test core network analysis chain."""
        from awslabs.cloudwan_mcp_server.server import (
            list_core_networks,
            get_core_network_policy,
            analyze_segment_routes
        )
        
        # Step 1: List core networks
        list_result = await list_core_networks("us-east-1")
        list_data = json.loads(list_result)
        core_network_id = list_data["core_networks"][0]["CoreNetworkId"]
        
        # Step 2: Get policy
        policy_result = await get_core_network_policy(core_network_id)
        policy_data = json.loads(policy_result)
        
        # Step 3: Analyze routes
        analyze_result = await analyze_segment_routes(
            core_network_id,
            "production",
            "us-east-1"
        )
        analyze_data = json.loads(analyze_result)
        
        assert all([
            list_data["success"],
            policy_data["success"],
            analyze_data["success"]
        ])

    @pytest.mark.asyncio
    async def test_path_tracing_workflow(self, mock_aws_client):
        """Test complete path tracing workflow."""
        from awslabs.cloudwan_mcp_server.server import (
            discover_ip_details,
            trace_network_path,
            analyze_tgw_routes
        )
        
        # Get IP context
        ip_result = await discover_ip_details("10.0.1.100", "us-east-1")
        ip_data = json.loads(ip_result)
        
        # Trace path
        trace_result = await trace_network_path(
            "10.0.1.100",
            "10.0.2.100",
            region="us-east-1"
        )
        trace_data = json.loads(trace_result)
        
        # Analyze routes
        route_result = await analyze_tgw_routes(
            "tgw-rtb-1234567890abcdef0",
            "us-east-1"
        )
        route_data = json.loads(route_result)
        
        assert all([
            ip_data["success"],
            trace_data["success"],
            route_data["success"]
        ])