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

"""Regression tests for pyright type-safety fixes.

These tests verify:
1. call_fes / call_tcp raise RuntimeError when config is None
2. download_agent_artifact is called with snake_case parameter names
3. get_status works correctly with Optional attribute access after None guards
4. paginated_fes passes correct FESOperation type to call_fes
"""
# ruff: noqa: D101, D102, D103

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Category 1: None-config guards in call_fes / call_tcp ────────────


class TestCallFesNoneConfig:
    """call_fes must raise RuntimeError when get_config() returns None."""

    @pytest.mark.asyncio
    async def test_call_fes_raises_on_none_config(self):
        from awslabs.aws_transform_mcp_server.fes_client import call_fes

        with patch('awslabs.aws_transform_mcp_server.config_store.get_config', return_value=None):
            with pytest.raises(RuntimeError, match='[Nn]ot configured'):
                await call_fes('ListWorkspaces')

    @pytest.mark.asyncio
    async def test_call_tcp_raises_on_none_config(self):
        from awslabs.aws_transform_mcp_server.tcp_client import call_tcp

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_sigv4_config', return_value=None
        ):
            with pytest.raises(RuntimeError, match='[Nn]ot configured'):
                await call_tcp('ListConnectors')


# ── Category 1b: get_status None-guard on get_config / get_sigv4_config ──


class TestGetStatusConfigAccess:
    """get_status accesses attributes on get_config() / get_sigv4_config() results.

    When config IS present, attribute access must work without error.
    """

    @pytest.fixture
    def handler(self, mock_mcp):
        from awslabs.aws_transform_mcp_server.tools.configure import ConfigureHandler

        return ConfigureHandler(mock_mcp)

    @pytest.fixture
    def mock_mcp(self):
        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
        return mcp

    @pytest.fixture
    def ctx(self):
        ctx = AsyncMock()
        ctx.info = MagicMock(return_value='mock-context')
        return ctx

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_cookie',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=True)
    async def test_get_status_cookie_config_attributes(self, _, mock_fes_cookie, handler, ctx):
        """Verify get_status correctly accesses auth_mode, stage, region, origin on cookie config."""
        from awslabs.aws_transform_mcp_server.models import ConnectionConfig

        config = ConnectionConfig(
            auth_mode='cookie',
            stage='prod',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://example.transform.us-east-1.on.aws',
            session_cookie='aws-transform-session=abc',
        )
        mock_fes_cookie.return_value = {'userId': 'u1'}

        with (
            patch(
                'awslabs.aws_transform_mcp_server.tools.configure.get_config',
                return_value=config,
            ),
            patch(
                'awslabs.aws_transform_mcp_server.tools.configure.is_sigv4_configured',
                return_value=False,
            ),
        ):
            result = await handler.get_status(ctx)

        # text_result returns {'content': [{'type': 'text', 'text': ...}]}
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['configured'] is True
        assert parsed['fes']['authMode'] == 'cookie'
        assert parsed['fes']['stage'] == 'prod'
        assert parsed['fes']['region'] == 'us-east-1'

    @pytest.mark.asyncio
    async def test_get_status_sigv4_config_attributes(self, handler, ctx):
        """Verify get_status correctly accesses account_id, role, stage, region, tcp_endpoint."""
        from awslabs.aws_transform_mcp_server.models import SigV4Config

        sigv4 = SigV4Config(
            account_id='123456789012',
            role='TestRole',
            stage='prod',
            region='us-east-1',
            tcp_endpoint='https://transform.us-east-1.api.aws',
            access_key_id='AKID',
            secret_access_key='secret',  # pragma: allowlist secret
        )

        with (
            patch(
                'awslabs.aws_transform_mcp_server.tools.configure.is_configured',
                return_value=False,
            ),
            patch(
                'awslabs.aws_transform_mcp_server.tools.configure.is_sigv4_configured',
                return_value=True,
            ),
            patch(
                'awslabs.aws_transform_mcp_server.tools.configure.get_sigv4_config',
                return_value=sigv4,
            ),
        ):
            result = await handler.get_status(ctx)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['sigv4']['configured'] is True
        assert parsed['sigv4']['accountId'] == '123456789012'
        assert parsed['sigv4']['role'] == 'TestRole'
        assert parsed['sigv4']['tcpEndpoint'] == 'https://transform.us-east-1.api.aws'


# ── Category 2: download_agent_artifact parameter names ───────────────


class TestDownloadAgentArtifactParamNames:
    """get_resource must call download_agent_artifact with snake_case kwargs."""

    @pytest.fixture
    def handler(self, mock_mcp):
        from awslabs.aws_transform_mcp_server.tools.get_resource import GetResourceHandler

        return GetResourceHandler(mock_mcp)

    @pytest.fixture
    def mock_mcp(self):
        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
        return mcp

    @pytest.fixture
    def ctx(self):
        ctx = AsyncMock()
        ctx.info = MagicMock(return_value='mock-context')
        return ctx

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_task_with_artifact_uses_snake_case_params(self, _, mock_fes, handler, ctx):
        """Verify download_agent_artifact is called with snake_case kwargs, not camelCase."""
        mock_fes.return_value = {
            'task': {
                'taskId': 't1',
                'category': 'REGULAR',
                'agentArtifact': {'artifactId': 'art-123'},
            }
        }

        mock_download = AsyncMock(return_value={'content': {'key': 'value'}})

        # download_agent_artifact is lazily imported from hitl module inside a try/except,
        # so we patch it on the hitl module itself.
        with patch(
            'awslabs.aws_transform_mcp_server.tools.hitl.download_agent_artifact',
            mock_download,
        ):
            await handler.get_resource(
                ctx,
                resource='task',
                workspaceId='ws1',
                jobId='j1',
                taskId='t1',
            )

        mock_download.assert_called_once_with(
            workspace_id='ws1',
            job_id='j1',
            artifact_id='art-123',
        )


# ── Category 3: FESOperation type in paginated_fes ────────────────────


class TestPaginatedFesOperationType:
    """paginated_fes must pass a valid FESOperation literal to call_fes."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    async def test_paginated_fes_passes_valid_operation(self, mock_fes):
        """The api argument to paginated_fes flows through to call_fes as-is."""
        from awslabs.aws_transform_mcp_server.tools.list_resources import paginated_fes

        mock_fes.return_value = {'workspaces': []}

        await paginated_fes(api='ListWorkspaces', body={})

        mock_fes.assert_called_once()
        actual_operation = mock_fes.call_args[0][0]
        assert actual_operation == 'ListWorkspaces'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    async def test_paginated_fes_passes_operation_string_directly(self, mock_fes):
        """Ensure the operation string type matches what call_fes expects."""
        from awslabs.aws_transform_mcp_server.fes_client import FESOperation
        from awslabs.aws_transform_mcp_server.tools.list_resources import paginated_fes

        mock_fes.return_value = {'jobs': []}

        await paginated_fes(api='ListJobs', body={'workspaceId': 'ws1'})

        actual_operation = mock_fes.call_args[0][0]
        # Verify the value is a valid FESOperation literal
        assert actual_operation in FESOperation.__args__
