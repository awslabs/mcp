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

"""Tests for AgentCore management tools."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools import gateway
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.guide import (
    MEMORY_GUIDE,
    GuideTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.models import (
    MemoryGuideResponse,
)


class TestMemoryTool:
    """Test cases for the memory guide tool."""

    async def test_get_memory_guide_returns_guide(self):
        """Test that get_memory_guide returns a MemoryGuideResponse."""
        from unittest.mock import MagicMock

        tools = GuideTools()
        result = await tools.get_memory_guide(ctx=MagicMock())
        assert isinstance(result, MemoryGuideResponse)
        assert len(result.guide) > 0

    def test_memory_guide_constant_is_populated(self):
        """Test that MEMORY_GUIDE constant has substantial content."""
        assert isinstance(MEMORY_GUIDE, str)
        assert len(MEMORY_GUIDE) > 100
        assert 'AgentCore Memory' in MEMORY_GUIDE


class TestGatewayTool:
    """Test cases for the gateway management tool."""

    def test_manage_agentcore_gateway_returns_guide(self):
        """Test that manage_agentcore_gateway returns a deployment guide."""
        result = gateway.manage_agentcore_gateway()
        assert isinstance(result, dict)
        assert 'deployment_guide' in result
        assert isinstance(result['deployment_guide'], str)
        assert len(result['deployment_guide']) > 0
