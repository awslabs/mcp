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

from awslabs.amazon_bedrock_agentcore_mcp_server.tools import gateway, memory, runtime


class TestMemoryTool:
    """Test cases for the memory management tool."""

    def test_manage_agentcore_memory_returns_guide(self):
        """Test that manage_agentcore_memory returns a memory guide."""
        result = memory.manage_agentcore_memory()

        assert isinstance(result, dict)
        assert 'memory_guide' in result
        assert isinstance(result['memory_guide'], str)
        assert len(result['memory_guide']) > 0


class TestRuntimeTool:
    """Test cases for the runtime management tool."""

    def test_manage_agentcore_runtime_returns_guide(self):
        """Test that manage_agentcore_runtime returns a deployment guide."""
        result = runtime.manage_agentcore_runtime()

        assert isinstance(result, dict)
        assert 'deployment_guide' in result
        assert isinstance(result['deployment_guide'], str)
        assert len(result['deployment_guide']) > 0


class TestGatewayTool:
    """Test cases for the gateway management tool."""

    def test_manage_agentcore_gateway_returns_guide(self):
        """Test that manage_agentcore_gateway returns a deployment guide."""
        result = gateway.manage_agentcore_gateway()

        assert isinstance(result, dict)
        assert 'deployment_guide' in result
        assert isinstance(result['deployment_guide'], str)
        assert len(result['deployment_guide']) > 0
