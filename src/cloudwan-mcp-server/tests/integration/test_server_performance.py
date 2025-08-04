"""Performance and load testing for MCP server."""
import pytest
import json
import time

class TestServerPerformance:
    """Test server performance characteristics."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_aws_client, performance_thresholds):
        """Test concurrent tool execution under load."""
        from awslabs.cloudwan_mcp_server.server import list_core_networks
        
        start_time = time.time()
        tasks = [list_core_networks("us-east-1") for _ in range(10)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        assert duration < performance_thresholds["max_tool_execution_time"]
        assert all(json.loads(r)["success"] for r in results)

    @pytest.mark.asyncio
    async def test_memory_usage(self, mock_aws_client, performance_thresholds):
        """Test memory usage during tool execution."""
        import psutil
        from awslabs.cloudwan_mcp_server.server import analyze_segment_routes
        
        process = psutil.Process()
        start_mem = process.memory_info().rss / 1024 / 1024
        
        result = await analyze_segment_routes("core-123", "prod")
        current_mem = process.memory_info().rss / 1024 / 1024
        
        assert current_mem - start_mem < performance_thresholds["max_memory_mb"]