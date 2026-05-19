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
1. call_transform_api / call_tcp raise RuntimeError when config is None
2. download_agent_artifact is called with snake_case parameter names
3. get_status works correctly with Optional attribute access after None guards
4. paginated_fes passes correct FESOperation type to call_transform_api
"""
# ruff: noqa: D101, D102, D103

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Category 1: None-config guards in call_transform_api / call_tcp ────────────


class TestCallFesNoneConfig:
    """call_transform_api must raise RuntimeError when get_config() returns None."""

    @pytest.mark.asyncio
    async def test_call_fes_raises_on_none_config(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api

        with patch('awslabs.aws_transform_mcp_server.config_store.get_config', return_value=None):
            with pytest.raises(RuntimeError, match='[Nn]ot configured'):
                await call_transform_api('ListWorkspaces')

    @pytest.mark.asyncio
    async def test_call_tcp_raises_on_none_config(self):
        from awslabs.aws_transform_mcp_server.tcp_client import call_tcp

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None
        with patch('awslabs.aws_transform_mcp_server.aws_helper.boto3') as mock_boto3:
            mock_boto3.Session.return_value = mock_session
            with pytest.raises(RuntimeError, match='[Nn]o AWS credentials'):
                await call_tcp('ListConnectors')

    @pytest.mark.asyncio
    async def test_call_tcp_happy_path(self):
        """call_tcp resolves creds, signs, and sends request."""
        from awslabs.aws_transform_mcp_server.tcp_client import call_tcp

        mock_creds = MagicMock()
        mock_creds.get_frozen_credentials.return_value = MagicMock(
            access_key='AKID',
            secret_key='SECRET',  # pragma: allowlist secret
            token='TOKEN',
        )
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = mock_creds
        mock_session.region_name = 'us-east-1'

        mock_response = MagicMock()
        mock_response.json.return_value = {'connectors': []}

        with (
            patch('awslabs.aws_transform_mcp_server.aws_helper.boto3') as mock_boto3,
            patch(
                'awslabs.aws_transform_mcp_server.tcp_client.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_response,
            ) as mock_retry,
        ):
            mock_boto3.Session.return_value = mock_session
            result = await call_tcp('ListConnectors')

        assert result == {'connectors': []}
        mock_retry.assert_called_once()


# ── Category 1a: AwsHelper.create_boto3_client cache ────────────────────


class TestAwsHelperCache:
    """Verify create_boto3_client caches clients by service:region key."""

    def test_cache_hit(self):
        from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper

        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        with patch('awslabs.aws_transform_mcp_server.aws_helper.boto3') as mock_boto3:
            mock_boto3.Session.return_value = mock_session
            AwsHelper.clear_cache()
            first = AwsHelper.create_boto3_client('sts', region_name='us-east-1')
            second = AwsHelper.create_boto3_client('sts', region_name='us-east-1')

        assert first is second
        mock_session.client.assert_called_once()
        AwsHelper.clear_cache()


# ── Category 1b: get_status None-guard on get_config / boto3 credentials ──


class TestGetStatusConfigAccess:
    """get_status accesses attributes on get_config() results and boto3 credentials.

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
        """Verify get_status correctly accesses auth_mode, region, origin on cookie config."""
        from awslabs.aws_transform_mcp_server.models import ConnectionConfig

        config = ConnectionConfig(
            auth_mode='cookie',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://example.transform.us-east-1.on.aws',
            session_cookie='aws-transform-session=abc',
        )
        mock_fes_cookie.return_value = {'userId': 'u1'}

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None
        with (
            patch(
                'awslabs.aws_transform_mcp_server.tools.configure.get_config',
                return_value=config,
            ),
            patch(
                'awslabs.aws_transform_mcp_server.aws_helper.boto3.Session',
                return_value=mock_session,
            ),
        ):
            result = await handler.get_status(ctx)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['connection']['configured'] is True
        assert parsed['connection']['authMode'] == 'cookie'
        assert parsed['connection']['region'] == 'us-east-1'

    @pytest.mark.asyncio
    async def test_get_status_sigv4_config_attributes(self, handler, ctx):
        """Verify get_status correctly accesses sigv4 fields when credentials are detected."""
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = True
        mock_session.region_name = 'us-east-1'
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/test/session',
        }
        mock_session.client.return_value = mock_sts

        with (
            patch(
                'awslabs.aws_transform_mcp_server.tools.configure.is_configured',
                return_value=False,
            ),
            patch(
                'awslabs.aws_transform_mcp_server.aws_helper.boto3.Session',
                return_value=mock_session,
            ),
            patch.dict('os.environ', {'AWS_REGION': 'us-east-1'}),
        ):
            result = await handler.get_status(ctx)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['sigv4']['configured'] is True
        assert parsed['sigv4']['accountId'] == '123456789012'
        assert parsed['sigv4']['arn'] == 'arn:aws:sts::123456789012:assumed-role/test/session'
        assert parsed['sigv4']['region'] == 'us-east-1'
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
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
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
    """paginated_fes must pass a valid FESOperation literal to call_transform_api."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_transform_api',
        new_callable=AsyncMock,
    )
    async def test_paginated_fes_passes_valid_operation(self, mock_fes):
        """The api argument to paginated_fes flows through to call_transform_api as-is."""
        from awslabs.aws_transform_mcp_server.tools.list_resources import paginated_fes

        mock_fes.return_value = {'workspaces': []}

        await paginated_fes(api='ListWorkspaces', body={})

        mock_fes.assert_called_once()
        actual_operation = mock_fes.call_args[0][0]
        assert actual_operation == 'ListWorkspaces'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_transform_api',
        new_callable=AsyncMock,
    )
    async def test_paginated_fes_passes_operation_string_directly(self, mock_fes):
        """Ensure the operation string type matches what call_transform_api expects."""
        from awslabs.aws_transform_mcp_server.tools.list_resources import paginated_fes

        mock_fes.return_value = {'jobs': []}

        await paginated_fes(api='ListJobs', body={'workspaceId': 'ws1'})

        actual_operation = mock_fes.call_args[0][0]
        # FESOperation is str — verify the value is a string
        assert isinstance(actual_operation, str)
        assert actual_operation == 'ListJobs'
