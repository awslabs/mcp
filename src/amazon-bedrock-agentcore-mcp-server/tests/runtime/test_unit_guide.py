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

"""Tests for guide.py — content assertions."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.guide import (
    GuideTools,
)


class TestGetRuntimeGuide:
    """Tests for get_runtime_guide content coverage."""

    @pytest.mark.asyncio
    async def test_returns_content(self, mock_ctx):
        """Guide returns a non-trivial string."""
        tools = GuideTools()
        result = await tools.get_runtime_guide(ctx=mock_ctx)
        assert result.status == 'success'
        assert len(result.guide) > 500

    @pytest.mark.asyncio
    async def test_covers_cli_commands(self, mock_ctx):
        """Guide mentions all key agentcore CLI commands."""
        tools = GuideTools()
        result = await tools.get_runtime_guide(ctx=mock_ctx)
        for cmd in [
            'agentcore create',
            'agentcore deploy',
            'agentcore dev',
            'agentcore invoke',
            'agentcore status',
            'agentcore logs',
        ]:
            assert cmd in result.guide, f'Missing CLI command: {cmd}'

    @pytest.mark.asyncio
    async def test_covers_protocols(self, mock_ctx):
        """Guide mentions all supported protocols."""
        tools = GuideTools()
        result = await tools.get_runtime_guide(ctx=mock_ctx)
        for proto in ['HTTP', 'MCP', 'A2A', 'AGUI']:
            assert proto in result.guide

    @pytest.mark.asyncio
    async def test_covers_iam(self, mock_ctx):
        """Guide includes IAM permission names."""
        tools = GuideTools()
        result = await tools.get_runtime_guide(ctx=mock_ctx)
        assert 'InvokeAgentRuntime' in result.guide
        assert 'StopRuntimeSession' in result.guide

    @pytest.mark.asyncio
    async def test_covers_cost_tiers(self, mock_ctx):
        """Guide documents all cost tiers."""
        tools = GuideTools()
        result = await tools.get_runtime_guide(ctx=mock_ctx)
        assert 'Per-use billable' in result.guide
        assert 'Cost-saving' in result.guide
        assert 'Read-only' in result.guide

    @pytest.mark.asyncio
    async def test_covers_migration(self, mock_ctx):
        """Guide includes migration notes from deprecated toolkit."""
        tools = GuideTools()
        result = await tools.get_runtime_guide(ctx=mock_ctx)
        assert 'deprecated' in result.guide.lower()
        assert '@aws/agentcore' in result.guide

    @pytest.mark.asyncio
    async def test_covers_troubleshooting(self, mock_ctx):
        """Guide includes troubleshooting section."""
        tools = GuideTools()
        result = await tools.get_runtime_guide(ctx=mock_ctx)
        assert 'Troubleshooting' in result.guide
        assert '504' in result.guide

    @pytest.mark.asyncio
    async def test_covers_session_lifecycle(self, mock_ctx):
        """Guide documents session timeout configuration."""
        tools = GuideTools()
        result = await tools.get_runtime_guide(ctx=mock_ctx)
        assert 'idleRuntimeSessionTimeout' in result.guide
        assert '28800' in result.guide

    @pytest.mark.asyncio
    async def test_no_deprecated_toolkit_commands(self, mock_ctx):
        """Guide does not contain literal deprecated command strings."""
        tools = GuideTools()
        result = await tools.get_runtime_guide(ctx=mock_ctx)
        # These exact strings should NOT appear anywhere in the guide
        assert 'agentcore launch' not in result.guide
        assert 'agentcore destroy' not in result.guide
        assert '.bedrock_agentcore.yaml' not in result.guide
