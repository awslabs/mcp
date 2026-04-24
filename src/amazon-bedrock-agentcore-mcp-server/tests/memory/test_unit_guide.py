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

"""Unit tests for Memory guide tool."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.guide import (
    MEMORY_GUIDE,
    GuideTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.models import (
    MemoryGuideResponse,
)


class TestGetMemoryGuide:
    """Tests for get_memory_guide tool."""

    @pytest.mark.asyncio
    async def test_returns_guide(self, mock_ctx):
        """Returns a MemoryGuideResponse with substantial content."""
        tools = GuideTools()
        result = await tools.get_memory_guide(ctx=mock_ctx)
        assert isinstance(result, MemoryGuideResponse)
        assert len(result.guide) > 100

    @pytest.mark.asyncio
    async def test_guide_contains_cli_commands(self, mock_ctx):
        """Guide includes agentcore CLI commands."""
        tools = GuideTools()
        result = await tools.get_memory_guide(ctx=mock_ctx)
        assert isinstance(result, MemoryGuideResponse)
        assert 'agentcore add memory' in result.guide
        assert 'agentcore create' in result.guide
        assert 'agentcore deploy' in result.guide

    @pytest.mark.asyncio
    async def test_guide_contains_schema(self, mock_ctx):
        """Guide includes agentcore.json schema details."""
        assert 'eventExpiryDuration' in MEMORY_GUIDE
        assert 'strategies' in MEMORY_GUIDE
        assert 'SEMANTIC' in MEMORY_GUIDE
        assert 'SUMMARIZATION' in MEMORY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_iam(self, mock_ctx):
        """Guide includes IAM permission references."""
        assert 'bedrock-agentcore:CreateMemory' in MEMORY_GUIDE
        assert 'bedrock-agentcore:CreateEvent' in MEMORY_GUIDE
        assert 'bedrock-agentcore:RetrieveMemoryRecords' in MEMORY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_cost_tiers(self, mock_ctx):
        """Guide documents cost tiers for tools."""
        assert 'Read-only tools' in MEMORY_GUIDE
        assert 'billable resources' in MEMORY_GUIDE
        assert 'Destructive tools' in MEMORY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_troubleshooting(self, mock_ctx):
        """Guide includes troubleshooting section."""
        assert 'Troubleshooting' in MEMORY_GUIDE
        assert 'AccessDeniedException' in MEMORY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_migration(self, mock_ctx):
        """Guide includes migration notes from starter toolkit."""
        assert 'Migration' in MEMORY_GUIDE
        assert 'starter-toolkit' in MEMORY_GUIDE

    @pytest.mark.asyncio
    async def test_guide_contains_prerequisites(self, mock_ctx):
        """Guide documents prerequisites and CLI installation."""
        assert 'Prerequisites' in MEMORY_GUIDE
        assert 'agentcore-cli' in MEMORY_GUIDE or 'agentcore' in MEMORY_GUIDE
        assert 'do NOT need the CLI' in MEMORY_GUIDE
