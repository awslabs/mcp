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


"""Performance and load testing for MCP server."""

import asyncio
import json
import time

import pytest


class TestServerPerformance:
    """Test server performance characteristics."""

    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_aws_client, performance_thresholds) -> None:
        """Test concurrent tool execution under load."""
        from awslabs.cloudwan_mcp_server.server import list_core_networks

        start_time = time.time()
        tasks = [list_core_networks("us-east-1") for _ in range(10)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        assert duration < performance_thresholds["max_tool_execution_time"]
        assert all(json.loads(r)["success"] for r in results)

    @pytest.mark.asyncio
    async def test_memory_usage(self, mock_aws_client, performance_thresholds) -> None:
        """Test memory usage during tool execution."""
        import psutil

        from awslabs.cloudwan_mcp_server.server import analyze_segment_routes

        process = psutil.Process()
        start_mem = process.memory_info().rss / 1024 / 1024

        await analyze_segment_routes("core-123", "prod")
        current_mem = process.memory_info().rss / 1024 / 1024

        assert current_mem - start_mem < performance_thresholds["max_memory_mb"]
