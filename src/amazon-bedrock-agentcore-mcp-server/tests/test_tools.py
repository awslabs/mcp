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

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools import gateway, memory
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.guide import (
    POLICY_GUIDE,
    GuideTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.models import (
    PolicyGuideResponse,
)
from unittest.mock import MagicMock


class TestMemoryTool:
    """Test cases for the memory management tool."""

    def test_manage_agentcore_memory_returns_guide(self):
        """Test that manage_agentcore_memory returns a memory guide."""
        result = memory.manage_agentcore_memory()
        assert isinstance(result, dict)
        assert 'memory_guide' in result
        assert isinstance(result['memory_guide'], str)
        assert len(result['memory_guide']) > 0


class TestGatewayTool:
    """Test cases for the gateway management tool."""

    def test_manage_agentcore_gateway_returns_guide(self):
        """Test that manage_agentcore_gateway returns a deployment guide."""
        result = gateway.manage_agentcore_gateway()
        assert isinstance(result, dict)
        assert 'deployment_guide' in result
        assert isinstance(result['deployment_guide'], str)
        assert len(result['deployment_guide']) > 0


class TestPolicyTool:
    """Test cases for the policy guide tool (sub-package entry point)."""

    @pytest.mark.asyncio
    async def test_get_policy_guide_returns_guide(self):
        """Test that the policy guide tool returns a Pydantic guide response."""
        tools = GuideTools()
        result = await tools.get_policy_guide(ctx=MagicMock())
        assert isinstance(result, PolicyGuideResponse)
        assert len(result.guide) > 0

    def test_guide_constant_is_populated(self):
        """Test that the POLICY_GUIDE constant has substantial content."""
        assert isinstance(POLICY_GUIDE, str)
        assert len(POLICY_GUIDE) > 100
