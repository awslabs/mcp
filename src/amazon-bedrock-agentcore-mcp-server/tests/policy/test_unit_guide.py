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

"""Unit tests for Policy guide tool."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.guide import (
    POLICY_GUIDE,
    GuideTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.models import (
    PolicyGuideResponse,
)


class TestGetPolicyGuide:
    """Tests for get_policy_guide tool."""

    @pytest.mark.asyncio
    async def test_returns_pydantic_model(self, mock_ctx):
        """Returns a PolicyGuideResponse with substantial content."""
        tools = GuideTools()
        result = await tools.get_policy_guide(ctx=mock_ctx)
        assert isinstance(result, PolicyGuideResponse)
        assert len(result.guide) > 100

    @pytest.mark.asyncio
    async def test_guide_contains_cli_commands(self, mock_ctx):
        """Guide includes agentcore CLI commands."""
        tools = GuideTools()
        result = await tools.get_policy_guide(ctx=mock_ctx)
        guide = result.guide
        assert 'agentcore add gateway' in guide
        assert 'agentcore deploy' in guide
        assert 'agentcore status' in guide
        assert '--policy-engine' in guide
        assert '--policy-engine-mode' in guide

    @pytest.mark.asyncio
    async def test_guide_contains_schema(self, mock_ctx):
        """Guide includes agentcore.json schema details."""
        assert 'policyEngines' in POLICY_GUIDE
        assert 'policies' in POLICY_GUIDE
        assert 'statement' in POLICY_GUIDE
        assert 'validationMode' in POLICY_GUIDE
        assert 'FAIL_ON_ANY_FINDINGS' in POLICY_GUIDE
        assert 'IGNORE_ALL_FINDINGS' in POLICY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_enforcement_modes(self, mock_ctx):
        """Guide documents LOG_ONLY and ENFORCE enforcement modes."""
        assert 'LOG_ONLY' in POLICY_GUIDE
        assert 'ENFORCE' in POLICY_GUIDE
        assert 'policyEngineConfiguration' in POLICY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_iam(self, mock_ctx):
        """Guide includes IAM permission references."""
        assert 'bedrock-agentcore:CreatePolicyEngine' in POLICY_GUIDE
        assert 'bedrock-agentcore:CreatePolicy' in POLICY_GUIDE
        assert 'bedrock-agentcore:StartPolicyGeneration' in POLICY_GUIDE
        assert 'bedrock-agentcore:ListPolicyGenerationAssets' in POLICY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_cost_tiers(self, mock_ctx):
        """Guide documents cost tiers for tools."""
        assert 'Read-only tools' in POLICY_GUIDE
        assert 'billable resources' in POLICY_GUIDE
        assert 'Destructive tools' in POLICY_GUIDE
        assert 'COST WARNING' not in POLICY_GUIDE  # that's in docstrings, not the guide
        assert 'policy_generation_start' in POLICY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_troubleshooting(self, mock_ctx):
        """Guide includes troubleshooting section."""
        assert 'Troubleshooting' in POLICY_GUIDE
        assert 'AccessDeniedException' in POLICY_GUIDE
        assert 'CREATE_FAILED' in POLICY_GUIDE
        assert 'ConflictException' in POLICY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_migration(self, mock_ctx):
        """Guide includes migration notes from starter toolkit."""
        assert 'Migration' in POLICY_GUIDE
        assert 'starter-toolkit' in POLICY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_prerequisites(self, mock_ctx):
        """Guide documents prerequisites and CLI installation."""
        assert 'Prerequisites' in POLICY_GUIDE
        assert 'agentcore-cli' in POLICY_GUIDE or 'agentcore' in POLICY_GUIDE
        assert 'do NOT need the CLI' in POLICY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_generation_workflow(self, mock_ctx):
        """Guide documents the AI-powered generation workflow."""
        assert 'policy_generation_start' in POLICY_GUIDE
        assert 'policyGeneration' in POLICY_GUIDE
        assert 'VALID' in POLICY_GUIDE
        assert 'NOT_TRANSLATABLE' in POLICY_GUIDE
        assert '7 days' in POLICY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_delete_order(self, mock_ctx):
        """Guide documents the engine-delete ordering constraint."""
        # Engine deletion requires deleting all policies first
        assert 'policy_delete' in POLICY_GUIDE
        assert 'policy_engine_delete' in POLICY_GUIDE
        assert 'zero associated policies' in POLICY_GUIDE or 'associated policies' in POLICY_GUIDE
