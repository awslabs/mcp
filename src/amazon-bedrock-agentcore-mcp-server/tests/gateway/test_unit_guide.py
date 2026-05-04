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

"""Unit tests for Gateway guide tool."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.gateway.guide import (
    GATEWAY_GUIDE,
    GuideTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.gateway.models import (
    GatewayGuideResponse,
)


class TestGetGatewayGuide:
    """Tests for get_gateway_guide tool."""

    @pytest.mark.asyncio
    async def test_returns_guide(self, mock_ctx):
        """Returns a GatewayGuideResponse with substantial content."""
        tools = GuideTools()
        result = await tools.get_gateway_guide(ctx=mock_ctx)
        assert isinstance(result, GatewayGuideResponse)
        assert result.status == 'success'
        assert len(result.guide) > 100

    @pytest.mark.asyncio
    async def test_guide_contains_cli_commands(self, mock_ctx):
        """Guide includes agentcore CLI commands."""
        tools = GuideTools()
        result = await tools.get_gateway_guide(ctx=mock_ctx)
        guide = result.guide
        assert 'agentcore add gateway' in guide
        assert 'agentcore add gateway-target' in guide
        assert 'agentcore deploy' in guide

    @pytest.mark.asyncio
    async def test_guide_contains_schema(self, mock_ctx):
        """Guide includes agentcore.json schema details."""
        assert 'agentCoreGateways' in GATEWAY_GUIDE
        assert 'targetType' in GATEWAY_GUIDE
        assert 'mcpServer' in GATEWAY_GUIDE
        assert 'lambdaFunctionArn' in GATEWAY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_iam(self, mock_ctx):
        """Guide includes IAM permission references."""
        assert 'bedrock-agentcore:CreateGateway' in GATEWAY_GUIDE
        assert 'bedrock-agentcore:CreateGatewayTarget' in GATEWAY_GUIDE
        assert 'bedrock-agentcore:SynchronizeGatewayTargets' in GATEWAY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_cost_tiers(self, mock_ctx):
        """Guide documents cost tiers for tools."""
        assert 'Read-only tools' in GATEWAY_GUIDE
        assert 'billable resources' in GATEWAY_GUIDE
        assert 'Destructive tools' in GATEWAY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_troubleshooting(self, mock_ctx):
        """Guide includes troubleshooting section."""
        assert 'Troubleshooting' in GATEWAY_GUIDE
        assert 'AccessDeniedException' in GATEWAY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_migration(self, mock_ctx):
        """Guide includes migration notes from starter toolkit."""
        assert 'Migration' in GATEWAY_GUIDE
        assert 'starter-toolkit' in GATEWAY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_prerequisites(self, mock_ctx):
        """Guide documents prerequisites and CLI installation."""
        assert 'Prerequisites' in GATEWAY_GUIDE
        assert 'do NOT need the CLI' in GATEWAY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_excluded_operations(self, mock_ctx):
        """Guide documents excluded operations with reasoning."""
        assert 'Excluded Operations' in GATEWAY_GUIDE
        assert 'InvokeGateway' in GATEWAY_GUIDE
        assert 'MCP Inspector' in GATEWAY_GUIDE
        assert 'Credential material' in GATEWAY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_target_types(self, mock_ctx):
        """Guide documents all five target types."""
        for ttype in ('lambda', 'mcpServer', 'openApiSchema', 'smithyModel', 'apiGateway'):
            assert ttype in GATEWAY_GUIDE
