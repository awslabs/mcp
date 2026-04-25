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

"""Tests for get_resource tool handler."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from awslabs.aws_transform_mcp_server.tools.get_resource import (
    GetResourceHandler,
    GetResourceType,
)
from unittest.mock import AsyncMock, patch


# ── Helpers ────────────────────────────────────────────────────────────────


def _parse_result(result: dict) -> dict:
    """Parse the MCP text result envelope into a Python dict."""
    return json.loads(result['content'][0]['text'])


# ── GetResourceHandler ─────────────────────────────────────────────────────


class TestGetResourceHandler:
    """Tests for the get_resource tool dispatch logic."""

    @pytest.fixture
    def handler(self, mock_mcp):
        return GetResourceHandler(mock_mcp)

    @pytest.fixture
    def ctx(self, mock_context):
        return mock_context

    # ── Auth gating ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=False)
    async def test_not_configured(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.workspace)
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    # ── session ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_session_success(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {'userId': 'user-1', 'tenantId': 'tenant-1'}
        result = await handler.get_resource(ctx, resource=GetResourceType.session)
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['session']['userId'] == 'user-1'
        assert result['isError'] is False

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_session_failure(self, _, mock_fes, handler, ctx):
        mock_fes.side_effect = RuntimeError('session expired')
        result = await handler.get_resource(ctx, resource=GetResourceType.session)
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
        assert result['isError'] is True

    # ── workspace ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_workspace_requires_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.workspace)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_workspace_success(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {'workspaceId': 'ws1', 'name': 'Test'}
        result = await handler.get_resource(
            ctx, resource=GetResourceType.workspace, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['workspaceId'] == 'ws1'
        mock_fes.assert_called_once_with('GetWorkspace', {'id': 'ws1'})

    # ── job ────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_job_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.job)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_job_requires_job_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.job, workspaceId='ws1')
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_job_success(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {'jobId': 'j1', 'status': 'RUNNING'}
        result = await handler.get_resource(
            ctx, resource=GetResourceType.job, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['jobId'] == 'j1'

    # ── connector ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_connector_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.connector)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_connector_requires_connector_id(self, _, handler, ctx):
        result = await handler.get_resource(
            ctx, resource=GetResourceType.connector, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_connector_success(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {'connectorId': 'c1'}
        result = await handler.get_resource(
            ctx,
            resource=GetResourceType.connector,
            workspaceId='ws1',
            connectorId='c1',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        mock_fes.assert_called_once_with(
            'GetConnector', {'workspaceId': 'ws1', 'connectorId': 'c1'}
        )

    # ── task ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_task_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.task)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_task_requires_job_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.task, workspaceId='ws1')
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_task_requires_task_id(self, _, handler, ctx):
        result = await handler.get_resource(
            ctx, resource=GetResourceType.task, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_task_basic_without_hitl_schemas(self, _, mock_fes, handler, ctx):
        """Task works even when hitl_schemas is not importable (guard)."""
        mock_fes.return_value = {
            'task': {'taskId': 't1', 'status': 'PENDING', 'category': 'REGULAR'}
        }
        result = await handler.get_resource(
            ctx,
            resource=GetResourceType.task,
            workspaceId='ws1',
            jobId='j1',
            taskId='t1',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['task']['taskId'] == 't1'
        assert parsed['data']['agentArtifactContent'] is None

    # ── artifact ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_artifact_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.artifact)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_artifact_requires_job_id(self, _, handler, ctx):
        result = await handler.get_resource(
            ctx, resource=GetResourceType.artifact, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_artifact_requires_artifact_id(self, _, handler, ctx):
        result = await handler.get_resource(
            ctx, resource=GetResourceType.artifact, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.download_s3_content',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_artifact_download(self, _, mock_fes, mock_dl, handler, ctx):
        mock_fes.return_value = {'s3PreSignedUrl': 'https://s3.example.com/file.txt'}
        mock_dl.return_value = {'content': 'file contents'}
        result = await handler.get_resource(
            ctx,
            resource=GetResourceType.artifact,
            workspaceId='ws1',
            jobId='j1',
            artifactId='a1',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['artifactId'] == 'a1'
        assert parsed['data']['content'] == 'file contents'
        mock_dl.assert_called_once_with(
            'https://s3.example.com/file.txt',
            save_path=None,
            file_name=None,
            default_name='a1',
        )

    # ── asset ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_asset_requires_all_params(self, _, handler, ctx):
        # Missing workspaceId
        r = await handler.get_resource(ctx, resource=GetResourceType.asset)
        assert _parse_result(r)['error']['code'] == 'VALIDATION_ERROR'

        # Missing jobId
        r = await handler.get_resource(ctx, resource=GetResourceType.asset, workspaceId='ws1')
        assert _parse_result(r)['error']['code'] == 'VALIDATION_ERROR'

        # Missing connectorId
        r = await handler.get_resource(
            ctx, resource=GetResourceType.asset, workspaceId='ws1', jobId='j1'
        )
        assert _parse_result(r)['error']['code'] == 'VALIDATION_ERROR'

        # Missing assetKey
        r = await handler.get_resource(
            ctx,
            resource=GetResourceType.asset,
            workspaceId='ws1',
            jobId='j1',
            connectorId='c1',
        )
        assert _parse_result(r)['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.download_s3_content',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_asset_download(self, _, mock_fes, mock_dl, handler, ctx):
        mock_fes.return_value = {'s3PreSignedUrl': 'https://s3.example.com/asset.bin'}
        mock_dl.return_value = {'content': 'asset data'}
        result = await handler.get_resource(
            ctx,
            resource=GetResourceType.asset,
            workspaceId='ws1',
            jobId='j1',
            connectorId='c1',
            assetKey='path/to/file.bin',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['assetKey'] == 'path/to/file.bin'
        mock_dl.assert_called_once_with(
            'https://s3.example.com/asset.bin',
            save_path=None,
            file_name=None,
            default_name='file.bin',
        )

    # ── messages ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_messages_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.messages)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_messages_requires_message_ids(self, _, handler, ctx):
        result = await handler.get_resource(
            ctx, resource=GetResourceType.messages, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_messages_success(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {'messages': [{'id': 'm1'}]}
        result = await handler.get_resource(
            ctx,
            resource=GetResourceType.messages,
            workspaceId='ws1',
            messageIds=['m1', 'm2'],
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        mock_fes.assert_called_once_with(
            'BatchGetMessage', {'messageIds': ['m1', 'm2'], 'workspaceId': 'ws1'}
        )

    # ── plan ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_plan_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.plan)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_plan_requires_job_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.plan, workspaceId='ws1')
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_plan_success(self, _, mock_fes, handler, ctx):
        async def fes_side_effect(op, body):
            if op == 'ListJobPlanSteps':
                return {'steps': [{'id': 's1'}]}
            return {'updates': [{'id': 'u1'}]}

        mock_fes.side_effect = fes_side_effect
        result = await handler.get_resource(
            ctx, resource=GetResourceType.plan, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert 'planSteps' in parsed['data']
        assert 'planUpdates' in parsed['data']

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_plan_both_fail(self, _, mock_fes, handler, ctx):
        mock_fes.side_effect = RuntimeError('api error')
        result = await handler.get_resource(
            ctx, resource=GetResourceType.plan, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'NOT_FOUND'

    # ── exception handling ─────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.get_resource.is_configured', return_value=True)
    async def test_fes_exception_returns_failure(self, _, mock_fes, handler, ctx):
        mock_fes.side_effect = RuntimeError('unexpected')
        result = await handler.get_resource(
            ctx, resource=GetResourceType.workspace, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
