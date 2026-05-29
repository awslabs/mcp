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

"""Tests for AgentCore management tools.

This file contains smoke tests for each primitive's guide tool.
Primitives whose sub-packages have not yet been merged are detected
at import time and their tests are skipped automatically.
"""

import importlib
import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.guide import (
    MEMORY_GUIDE,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.guide import (
    GuideTools as MemoryGuideTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.models import (
    MemoryGuideResponse,
)
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Detect which sub-packages are installed
# ---------------------------------------------------------------------------

_PKG = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools'

_HAS_IDENTITY = False
try:
    importlib.import_module(f'{_PKG}.identity.guide')
    _HAS_IDENTITY = True
except (ImportError, ModuleNotFoundError):
    pass

_HAS_GATEWAY_SUB = False
try:
    importlib.import_module(f'{_PKG}.gateway.guide')
    _HAS_GATEWAY_SUB = True
except (ImportError, ModuleNotFoundError, AttributeError):
    pass

_HAS_POLICY = False
try:
    importlib.import_module(f'{_PKG}.policy.guide')
    _HAS_POLICY = True
except (ImportError, ModuleNotFoundError):
    pass


class TestMemoryTool:
    """Test cases for the memory guide tool."""

    @pytest.mark.asyncio
    async def test_get_memory_guide_returns_guide(self):
        """Test that get_memory_guide returns a MemoryGuideResponse."""
        tools = MemoryGuideTools()
        result = await tools.get_memory_guide(ctx=MagicMock())
        assert isinstance(result, MemoryGuideResponse)
        assert len(result.guide) > 0

    def test_memory_guide_constant_is_populated(self):
        """Test that MEMORY_GUIDE constant has substantial content."""
        assert isinstance(MEMORY_GUIDE, str)
        assert len(MEMORY_GUIDE) > 100
        assert 'AgentCore Memory' in MEMORY_GUIDE


@pytest.mark.skipif(
    not _HAS_IDENTITY,
    reason='Identity sub-package not yet installed',
)
class TestIdentityTool:
    """Test cases for the identity guide tool."""

    @pytest.mark.asyncio
    async def test_get_identity_guide_returns_guide(self):
        """Test that get_identity_guide returns guide response."""
        mod_guide = importlib.import_module(f'{_PKG}.identity.guide')
        mod_models = importlib.import_module(f'{_PKG}.identity.models')

        ctx = MagicMock()
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()
        tools = mod_guide.GuideTools()
        result = await tools.get_identity_guide(ctx=ctx)
        assert isinstance(result, mod_models.IdentityGuideResponse)
        assert result.status == 'success'
        assert len(result.guide) > 0

    def test_guide_constant_is_populated(self):
        """Test that IDENTITY_GUIDE has substantial content."""
        mod = importlib.import_module(f'{_PKG}.identity.guide')
        assert isinstance(mod.IDENTITY_GUIDE, str)
        assert len(mod.IDENTITY_GUIDE) > 100


@pytest.mark.skipif(
    not _HAS_GATEWAY_SUB,
    reason='Gateway sub-package not yet installed',
)
class TestGatewayTool:
    """Test cases for the gateway guide tool."""

    @pytest.mark.asyncio
    async def test_get_gateway_guide_returns_guide(self):
        """Test that guide tool returns a GatewayGuideResponse."""
        mod_guide = importlib.import_module(f'{_PKG}.gateway.guide')
        mod_models = importlib.import_module(f'{_PKG}.gateway.models')

        tools = mod_guide.GuideTools()
        result = await tools.get_gateway_guide(ctx=MagicMock())
        assert isinstance(result, mod_models.GatewayGuideResponse)
        assert result.status == 'success'
        assert len(result.guide) > 0

    def test_guide_constant_is_populated(self):
        """Test that GATEWAY_GUIDE has substantial content."""
        mod = importlib.import_module(f'{_PKG}.gateway.guide')
        assert isinstance(mod.GATEWAY_GUIDE, str)
        assert len(mod.GATEWAY_GUIDE) > 100


@pytest.mark.skipif(
    not _HAS_POLICY,
    reason='Policy sub-package not yet installed',
)
class TestPolicyTool:
    """Test cases for the policy guide tool."""

    @pytest.mark.asyncio
    async def test_get_policy_guide_returns_guide(self):
        """Test that policy guide tool returns a PolicyGuideResponse."""
        mod_guide = importlib.import_module(f'{_PKG}.policy.guide')
        mod_models = importlib.import_module(f'{_PKG}.policy.models')

        tools = mod_guide.GuideTools()
        result = await tools.get_policy_guide(ctx=MagicMock())
        assert isinstance(result, mod_models.PolicyGuideResponse)
        assert len(result.guide) > 0

    def test_guide_constant_is_populated(self):
        """Test that POLICY_GUIDE has substantial content."""
        mod = importlib.import_module(f'{_PKG}.policy.guide')
        assert isinstance(mod.POLICY_GUIDE, str)
        assert len(mod.POLICY_GUIDE) > 100
