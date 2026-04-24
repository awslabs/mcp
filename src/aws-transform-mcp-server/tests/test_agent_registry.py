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

"""Tests for agent registry tool handlers."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from awslabs.aws_transform_mcp_server.tools.agent_registry import AgentRegistryHandler
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def handler(mock_mcp):
    return AgentRegistryHandler(mock_mcp)


@pytest.fixture
def mock_context():
    ctx = AsyncMock()
    ctx.info = MagicMock(return_value='mock-context')
    return ctx


# ── get_agent ───────────────────────────────────────────────────────────


class TestGetAgent:
    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.call_tcp', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.is_sigv4_configured',
        return_value=True,
    )
    async def test_get_agent_success(self, mock_sigv4, mock_call_tcp, handler, mock_context):
        mock_call_tcp.return_value = {'agentName': 'my-agent', 'version': '1.0.0'}

        result = await handler.get_agent(mock_context, agentName='my-agent')

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['agentName'] == 'my-agent'

        mock_call_tcp.assert_called_once_with('GetAgent', {'agentName': 'my-agent'})

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.is_sigv4_configured',
        return_value=False,
    )
    async def test_get_agent_sigv4_not_configured(self, mock_sigv4, handler, mock_context):
        result = await handler.get_agent(mock_context, agentName='my-agent')

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'SIGV4_NOT_CONFIGURED'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.is_sigv4_configured',
        return_value=True,
    )
    async def test_get_agent_invalid_name(self, mock_sigv4, handler, mock_context):
        result = await handler.get_agent(mock_context, agentName='bad name!')

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.is_sigv4_configured',
        return_value=True,
    )
    async def test_get_agent_empty_name(self, mock_sigv4, handler, mock_context):
        result = await handler.get_agent(mock_context, agentName='')

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'


# ── get_agent_runtime_configuration ─────────────────────────────────────


class TestGetAgentRuntimeConfiguration:
    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.call_tcp', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.is_sigv4_configured',
        return_value=True,
    )
    async def test_without_version(self, mock_sigv4, mock_call_tcp, handler, mock_context):
        mock_call_tcp.return_value = {'config': 'data'}

        result = await handler.get_agent_runtime_configuration(
            mock_context, agentName='my-agent', version=None
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True

        mock_call_tcp.assert_called_once_with(
            'GetAgentRuntimeConfiguration', {'agentName': 'my-agent'}
        )

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.call_tcp', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.is_sigv4_configured',
        return_value=True,
    )
    async def test_with_version(self, mock_sigv4, mock_call_tcp, handler, mock_context):
        mock_call_tcp.return_value = {'config': 'versioned-data'}

        result = await handler.get_agent_runtime_configuration(
            mock_context, agentName='my-agent', version='2.1.0'
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True

        mock_call_tcp.assert_called_once_with(
            'GetAgentRuntimeConfiguration', {'agentName': 'my-agent', 'version': '2.1.0'}
        )

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.is_sigv4_configured',
        return_value=True,
    )
    async def test_invalid_version(self, mock_sigv4, handler, mock_context):
        result = await handler.get_agent_runtime_configuration(
            mock_context, agentName='my-agent', version='not-semver'
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'semver' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.is_sigv4_configured',
        return_value=True,
    )
    async def test_invalid_agent_name(self, mock_sigv4, handler, mock_context):
        result = await handler.get_agent_runtime_configuration(
            mock_context, agentName='invalid name!'
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.agent_registry.is_sigv4_configured',
        return_value=False,
    )
    async def test_sigv4_not_configured(self, mock_sigv4, handler, mock_context):
        result = await handler.get_agent_runtime_configuration(mock_context, agentName='my-agent')

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'SIGV4_NOT_CONFIGURED'
