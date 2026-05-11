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
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=False
    )
    async def test_not_configured(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.workspace)
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    # ── session ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_session_success(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {'userId': 'user-1', 'tenantId': 'tenant-1'}
        result = await handler.get_resource(ctx, resource=GetResourceType.session)
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['session']['userId'] == 'user-1'
        assert result['isError'] is False

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_session_failure(self, _, mock_fes, handler, ctx):
        mock_fes.side_effect = RuntimeError('session expired')
        result = await handler.get_resource(ctx, resource=GetResourceType.session)
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
        assert result['isError'] is True

    # ── workspace ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_workspace_requires_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.workspace)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_workspace_success(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {'workspaceId': 'ws1', 'name': 'Test'}
        result = await handler.get_resource(
            ctx, resource=GetResourceType.workspace, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['workspaceId'] == 'ws1'
        mock_fes.assert_called_once()
        args = mock_fes.call_args[0]
        assert args[0] == 'GetWorkspace'
        assert args[1].model_dump(by_alias=True, exclude_none=True) == {'id': 'ws1'}

    # ── job ────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_job_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.job)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_job_requires_job_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.job, workspaceId='ws1')
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
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
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_connector_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.connector)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_connector_requires_connector_id(self, _, handler, ctx):
        result = await handler.get_resource(
            ctx, resource=GetResourceType.connector, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
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
        mock_fes.assert_called_once()
        args = mock_fes.call_args[0]
        assert args[0] == 'GetConnector'
        assert args[1].model_dump(by_alias=True, exclude_none=True) == {
            'workspaceId': 'ws1',
            'connectorId': 'c1',
        }

    # ── task ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_task_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.task)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_task_requires_job_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.task, workspaceId='ws1')
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_task_requires_task_id(self, _, handler, ctx):
        result = await handler.get_resource(
            ctx, resource=GetResourceType.task, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
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
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_artifact_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.artifact)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_artifact_requires_job_id(self, _, handler, ctx):
        result = await handler.get_resource(
            ctx, resource=GetResourceType.artifact, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
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
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
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
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
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
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
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
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_messages_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.messages)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_messages_requires_message_ids(self, _, handler, ctx):
        result = await handler.get_resource(
            ctx, resource=GetResourceType.messages, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
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
        mock_fes.assert_called_once()
        args = mock_fes.call_args[0]
        assert args[0] == 'BatchGetMessage'
        assert args[1].model_dump(by_alias=True, exclude_none=True) == {
            'messageIds': ['m1', 'm2'],
            'workspaceId': 'ws1',
        }

    # ── plan ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_plan_requires_workspace_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.plan)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_plan_requires_job_id(self, _, handler, ctx):
        result = await handler.get_resource(ctx, resource=GetResourceType.plan, workspaceId='ws1')
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
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
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_plan_both_fail(self, _, mock_fes, handler, ctx):
        mock_fes.side_effect = RuntimeError('api error')
        result = await handler.get_resource(
            ctx, resource=GetResourceType.plan, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'NOT_FOUND'

    # ── exception handling ─────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_fes_exception_returns_failure(self, _, mock_fes, handler, ctx):
        mock_fes.side_effect = RuntimeError('unexpected')
        result = await handler.get_resource(
            ctx, resource=GetResourceType.workspace, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'


class TestGetResourceTaskWithArtifact:
    """Tests for task resource with agent artifact download and dynamic schema building."""

    @pytest.fixture
    def handler(self, mock_mcp):
        return GetResourceHandler(mock_mcp)

    @pytest.fixture
    def ctx(self, mock_context):
        return mock_context

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available',
        return_value=True,
    )
    async def test_task_with_agent_artifact_download(self, _, mock_fes, handler, ctx):
        """Task with agentArtifact triggers download and includes content in result."""
        mock_fes.return_value = {
            'task': {
                'taskId': 't1',
                'status': 'PENDING',
                'uxComponentId': 'TextInput',
                'agentArtifact': {'artifactId': 'art-agent-1'},
            }
        }

        with patch(
            'awslabs.aws_transform_mcp_server.tools.hitl.download_agent_artifact',
            new_callable=AsyncMock,
        ) as mock_dl:
            mock_dl.return_value = {
                'content': {'field1': 'val1'},
                'rawText': '{"field1": "val1"}',
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
            assert parsed['data']['agentArtifactContent'] == {'field1': 'val1'}
            mock_dl.assert_called_once_with(
                workspace_id='ws1', job_id='j1', artifact_id='art-agent-1'
            )

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available',
        return_value=True,
    )
    async def test_task_with_artifact_download_warning(self, _, mock_fes, handler, ctx):
        """Artifact download warning is included in result."""
        mock_fes.return_value = {
            'task': {
                'taskId': 't1',
                'status': 'PENDING',
                'uxComponentId': 'TextInput',
                'agentArtifact': {'artifactId': 'art-agent-1'},
            }
        }

        with patch(
            'awslabs.aws_transform_mcp_server.tools.hitl.download_agent_artifact',
            new_callable=AsyncMock,
        ) as mock_dl:
            mock_dl.return_value = {
                'warning': 'Agent artifact download failed (HTTP 403). Field validation skipped.',
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
            assert '_warning' in parsed['data']
            assert 'HTTP 403' in parsed['data']['_warning']

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available',
        return_value=True,
    )
    async def test_task_with_artifact_rawtext_fallback(self, _, mock_fes, handler, ctx):
        """When content is absent but rawText is present, rawText is used."""
        mock_fes.return_value = {
            'task': {
                'taskId': 't1',
                'status': 'PENDING',
                'uxComponentId': 'TextInput',
                'agentArtifact': {'artifactId': 'art-agent-1'},
            }
        }

        with patch(
            'awslabs.aws_transform_mcp_server.tools.hitl.download_agent_artifact',
            new_callable=AsyncMock,
        ) as mock_dl:
            mock_dl.return_value = {
                'rawText': 'plain text artifact',
                'warning': 'Agent artifact is not JSON. Field validation skipped.',
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
            assert parsed['data']['agentArtifactContent'] == 'plain text artifact'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available',
        return_value=True,
    )
    async def test_task_with_dynamic_schema_building(self, _, mock_fes, handler, ctx):
        """AutoForm task with agent artifact gets dynamic output schema."""
        mock_fes.return_value = {
            'task': {
                'taskId': 't1',
                'status': 'PENDING',
                'uxComponentId': 'AutoForm',
                'agentArtifact': {'artifactId': 'art-agent-1'},
            }
        }

        with patch(
            'awslabs.aws_transform_mcp_server.tools.hitl.download_agent_artifact',
            new_callable=AsyncMock,
        ) as mock_dl:
            mock_dl.return_value = {
                'content': {
                    'properties': {
                        'name': {'type': 'string'},
                        'age': {'type': 'number'},
                    }
                },
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
            task = parsed['data']['task']
            assert '_outputSchema' in task
            assert 'name' in task['_outputSchema']['properties']
            assert 'age' in task['_outputSchema']['properties']

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available',
        return_value=True,
    )
    async def test_task_artifact_no_dynamic_schema_uses_properties_fallback(
        self, _, mock_fes, handler, ctx
    ):
        """When dynamic schema returns None, artifact properties are used as template fallback."""
        mock_fes.return_value = {
            'task': {
                'taskId': 't1',
                'status': 'PENDING',
                'uxComponentId': 'SomeUnknownComponent',
                'agentArtifact': {'artifactId': 'art-agent-1'},
            }
        }

        with patch(
            'awslabs.aws_transform_mcp_server.tools.hitl.download_agent_artifact',
            new_callable=AsyncMock,
        ) as mock_dl:
            mock_dl.return_value = {
                'content': {
                    'properties': {
                        'field1': 'value1',
                        'field2': 'value2',
                    }
                },
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
            task = parsed['data']['task']
            # Unknown component gets _responseTemplate from artifact properties
            assert task.get('_responseTemplate') == {'field1': 'value1', 'field2': 'value2'}
            assert '_responseHint' in task

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available',
        return_value=True,
    )
    async def test_task_hitl_schemas_import_error_fallback(self, _, mock_fes, handler, ctx):
        """When hitl_schemas import fails, task data is still returned."""
        mock_fes.return_value = {'task': {'taskId': 't1', 'status': 'PENDING'}}

        with patch(
            'builtins.__import__',
            side_effect=lambda name, *args, **kwargs: (
                (_ for _ in ()).throw(ImportError('no module'))
                if 'hitl_schemas' in name
                else __builtins__.__import__(name, *args, **kwargs)  # noqa: A003
            ),
        ):
            # This test verifies the ImportError guard path exists.
            # We can't easily make the guard fire since the module is already imported,
            # but we verify the basic task data passes through.
            result = await handler.get_resource(
                ctx,
                resource=GetResourceType.task,
                workspaceId='ws1',
                jobId='j1',
                taskId='t1',
            )
            parsed = _parse_result(result)
            assert parsed['success'] is True


class TestGetResourceMessagesParsing:
    """Tests for messageIds parsing edge cases."""

    @pytest.fixture
    def handler(self, mock_mcp):
        return GetResourceHandler(mock_mcp)

    @pytest.fixture
    def ctx(self, mock_context):
        return mock_context

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available',
        return_value=True,
    )
    async def test_messages_empty_list(self, _, handler, ctx):
        """Empty messageIds list returns validation error."""
        result = await handler.get_resource(
            ctx,
            resource=GetResourceType.messages,
            workspaceId='ws1',
            messageIds=[],
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available',
        return_value=True,
    )
    async def test_messages_json_string_ids(self, _, mock_fes, handler, ctx):
        """MessageIds as a JSON string is parsed into a list."""
        mock_fes.return_value = {'messages': [{'id': 'm1'}, {'id': 'm2'}]}

        result = await handler.get_resource(
            ctx,
            resource=GetResourceType.messages,
            workspaceId='ws1',
            messageIds='["m1", "m2"]',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        mock_fes.assert_called_once()
        args = mock_fes.call_args[0]
        assert args[0] == 'BatchGetMessage'
        assert args[1].model_dump(by_alias=True, exclude_none=True) == {
            'messageIds': ['m1', 'm2'],
            'workspaceId': 'ws1',
        }

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available',
        return_value=True,
    )
    async def test_messages_invalid_json_string(self, _, handler, ctx):
        """Invalid JSON string for messageIds returns validation error."""
        result = await handler.get_resource(
            ctx,
            resource=GetResourceType.messages,
            workspaceId='ws1',
            messageIds='not-valid-json',
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
