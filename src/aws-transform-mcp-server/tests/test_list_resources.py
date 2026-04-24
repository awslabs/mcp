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

"""Tests for list_resources tool handler."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from awslabs.aws_transform_mcp_server.tools.list_resources import (
    AgentConfigAvailEnum,
    AgentTypeEnum,
    CategoryEnum,
    ListResourcesHandler,
    OwnerTypeEnum,
    ResourceType,
    SourceEnum,
    paginated_fes,
    with_pagination,
)
from unittest.mock import AsyncMock, patch


# ── Helpers ────────────────────────────────────────────────────────────────


def _parse_result(result: dict) -> dict:
    """Parse the MCP text result envelope into a Python dict."""
    return json.loads(result['content'][0]['text'])


# ── with_pagination ────────────────────────────────────────────────────────


class TestWithPagination:
    def test_adds_both_fields(self):
        body: dict = {'key': 'val'}
        result = with_pagination(body, max_results=10, next_token='abc')
        assert result['maxResults'] == 10
        assert result['nextToken'] == 'abc'
        assert result['key'] == 'val'

    def test_skips_none_values(self):
        body: dict = {'key': 'val'}
        result = with_pagination(body)
        assert 'maxResults' not in result
        assert 'nextToken' not in result

    def test_adds_only_max_results(self):
        body: dict = {}
        result = with_pagination(body, max_results=5)
        assert result['maxResults'] == 5
        assert 'nextToken' not in result


# ── paginated_fes ──────────────────────────────────────────────────────────


class TestPaginatedFes:
    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    async def test_basic_call(self, mock_fes):
        mock_fes.return_value = {'items': [1, 2], 'nextToken': 'tok'}
        result = await paginated_fes('ListWorkspaces', {}, max_results=10)
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['items'] == [1, 2]
        mock_fes.assert_called_once_with('ListWorkspaces', {'maxResults': 10})

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    async def test_token_remap(self, mock_fes):
        mock_fes.return_value = {'items': [], 'outputToken': 'xyz'}
        result = await paginated_fes('ListWorklogs', {}, token_remap={'outputToken': 'nextToken'})
        parsed = _parse_result(result)
        assert parsed['data']['nextToken'] == 'xyz'
        assert 'outputToken' not in parsed['data']

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    async def test_transform(self, mock_fes):
        mock_fes.return_value = {'count': 3}
        result = await paginated_fes(
            'ListWorkspaces', {}, transform=lambda d: {**d, 'doubled': d['count'] * 2}
        )
        parsed = _parse_result(result)
        assert parsed['data']['doubled'] == 6

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    async def test_non_dict_response(self, mock_fes):
        mock_fes.return_value = [1, 2, 3]
        result = await paginated_fes('ListWorkspaces', {})
        parsed = _parse_result(result)
        assert parsed['data'] == [1, 2, 3]

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    async def test_none_response(self, mock_fes):
        mock_fes.return_value = None
        result = await paginated_fes('ListWorkspaces', {})
        parsed = _parse_result(result)
        assert parsed['data'] is None


# ── ListResourcesHandler ──────────────────────────────────────────────────


class TestListResourcesHandler:
    """Tests for the main list_resources dispatch logic."""

    @pytest.fixture
    def handler(self, mock_mcp):
        return ListResourcesHandler(mock_mcp)

    @pytest.fixture
    def ctx(self, mock_context):
        return mock_context

    # ── Auth gating ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_sigv4_configured',
        return_value=False,
    )
    async def test_account_connectors_requires_sigv4(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.account_connectors)
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'SIGV4_NOT_CONFIGURED'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_sigv4_configured',
        return_value=False,
    )
    async def test_profiles_requires_sigv4(self, _, handler, ctx):
        result = await handler.list_resources(
            ctx, resource=ResourceType.profiles, awsAccountId='123456789012'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'SIGV4_NOT_CONFIGURED'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=False
    )
    async def test_fes_resources_require_configured(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.workspaces)
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    # ── account_connectors ─────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_tcp', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_sigv4_configured',
        return_value=True,
    )
    async def test_account_connectors_success(self, _, mock_tcp, handler, ctx):
        mock_tcp.return_value = {'sourceConnectors': [], 'targetConnectors': []}
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.account_connectors,
            sourceNextToken='s-tok',
            targetNextToken='t-tok',
            maxResults=5,
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        mock_tcp.assert_called_once_with(
            'ListConnectors',
            {'sourceNextToken': 's-tok', 'targetNextToken': 't-tok', 'maxResults': 5},
        )

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_tcp', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_sigv4_configured',
        return_value=True,
    )
    async def test_account_connectors_failure(self, _, mock_tcp, handler, ctx):
        mock_tcp.side_effect = RuntimeError('network error')
        result = await handler.list_resources(ctx, resource=ResourceType.account_connectors)
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'

    # ── profiles ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_sigv4_configured',
        return_value=True,
    )
    async def test_profiles_requires_account_id(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.profiles)
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_tcp', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_sigv4_configured',
        return_value=True,
    )
    async def test_profiles_success(self, _, mock_tcp, handler, ctx):
        mock_tcp.return_value = {'profiles': [{'name': 'default'}]}
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.profiles,
            awsAccountId='123456789012',
            maxResults=10,
            nextToken='page2',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        mock_tcp.assert_called_once_with(
            'ListProfiles',
            {
                'retrieveDetails': True,
                'awsAccountId': '123456789012',
                'maxResults': 10,
                'nextToken': 'page2',
            },
        )

    # ── workspaces ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_workspaces(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'items': []}
        result = await handler.list_resources(ctx, resource=ResourceType.workspaces)
        parsed = _parse_result(result)
        assert parsed['success'] is True
        mock_paginate.assert_called_once_with('ListWorkspaces', {}, 'items')

    # ── jobs ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_jobs_requires_workspace_id(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.jobs)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_jobs_success(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'jobList': [{'jobId': 'j1'}]}
        result = await handler.list_resources(ctx, resource=ResourceType.jobs, workspaceId='ws1')
        parsed = _parse_result(result)
        assert parsed['success'] is True

    # ── connectors ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_connectors_requires_workspace_id(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.connectors)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_connectors_success(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'connectors': []}
        result = await handler.list_resources(
            ctx, resource=ResourceType.connectors, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True

    # ── tasks ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_tasks_requires_workspace_id(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.tasks)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_tasks_requires_job_id(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.tasks, workspaceId='ws1')
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_tasks_default_task_type(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'hitlTasks': []}
        result = await handler.list_resources(
            ctx, resource=ResourceType.tasks, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        call_body = mock_paginate.call_args[0][1]
        assert call_body['taskType'] == 'NORMAL'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_tasks_with_category_filter(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'hitlTasks': []}
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.tasks,
            workspaceId='ws1',
            jobId='j1',
            category=CategoryEnum.TOOL_APPROVAL,
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        call_body = mock_paginate.call_args[0][1]
        assert call_body['taskFilter'] == {'categories': ['TOOL_APPROVAL']}

    # ── artifacts ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_artifacts_requires_workspace_id(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.artifacts)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_artifacts_mainframe_requires_source(self, _, mock_fes, handler, ctx):
        # First call returns the job info (mainframe), second would be ListArtifacts
        mock_fes.return_value = {'jobType': 'MAINFRAME_MODERNIZATION'}
        result = await handler.list_resources(
            ctx, resource=ResourceType.artifacts, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'SOURCE_REQUIRED'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_artifacts_mainframe_connector_auto_prefix(
        self, _, mock_fes, mock_paginate, handler, ctx
    ):
        mock_fes.return_value = {'jobType': 'MAINFRAME_MODERNIZATION'}
        mock_paginate.return_value = {'artifacts': []}
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.artifacts,
            workspaceId='ws1',
            jobId='j1',
            source=SourceEnum.connector,
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        paginate_body = mock_paginate.call_args[0][1]
        assert paginate_body['pathPrefix'] == 'transform-output/j1/'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_artifacts_non_mainframe_ignores_source(
        self, _, mock_fes, mock_paginate, handler, ctx
    ):
        mock_fes.return_value = {'jobType': 'STANDARD'}
        mock_paginate.return_value = {'artifacts': [{'id': 'a1'}]}
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.artifacts,
            workspaceId='ws1',
            jobId='j1',
            source=SourceEnum.connector,
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        paginate_body = mock_paginate.call_args[0][1]
        assert 'pathPrefix' not in paginate_body

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_artifacts_with_path_prefix_skips_get_job(
        self, _, mock_fes, mock_paginate, handler, ctx
    ):
        mock_paginate.return_value = {'artifacts': []}
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.artifacts,
            workspaceId='ws1',
            jobId='j1',
            pathPrefix='custom/prefix/',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        mock_fes.assert_not_called()
        paginate_body = mock_paginate.call_args[0][1]
        assert paginate_body['pathPrefix'] == 'custom/prefix/'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_artifacts_with_plan_step_filter(self, _, mock_fes, mock_paginate, handler, ctx):
        mock_fes.return_value = {'jobType': 'STANDARD'}
        mock_paginate.return_value = {'artifacts': []}
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.artifacts,
            workspaceId='ws1',
            jobId='j1',
            planStepId='step-1',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        paginate_body = mock_paginate.call_args[0][1]
        assert paginate_body['jobFilter'] == {'jobId': 'j1', 'planStepId': 'step-1'}

    # ── messages ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_messages_requires_workspace_id(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.messages)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_messages_with_job_filter(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {'messages': []}
        result = await handler.list_resources(
            ctx, resource=ResourceType.messages, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        call_body = mock_fes.call_args[0][1]
        workspace = call_body['metadata']['resourcesOnScreen']['workspace']
        assert workspace['jobs'] == [{'jobId': 'j1', 'focusState': 'ACTIVE'}]

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_messages_with_start_timestamp(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {'messages': []}
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.messages,
            workspaceId='ws1',
            startTimestamp='2024-01-01T00:00:00Z',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        call_body = mock_fes.call_args[0][1]
        assert call_body['startTimestamp'] == '2024-01-01T00:00:00Z'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_messages_hydrates_full_content(self, _, mock_fes, handler, ctx):
        """ListMessages + BatchGetMessage called internally, returns full messages."""
        mock_fes.side_effect = [
            {'messageIds': ['msg-1', 'msg-2']},
            {
                'messages': [
                    {'messageId': 'msg-1', 'text': 'Hello', 'messageOrigin': 'USER'},
                    {'messageId': 'msg-2', 'text': 'Hi there', 'messageOrigin': 'SYSTEM'},
                ],
            },
        ]
        result = await handler.list_resources(
            ctx, resource=ResourceType.messages, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert len(parsed['data']['messages']) == 2
        assert parsed['data']['messages'][0]['text'] == 'Hello'
        assert mock_fes.call_count == 2
        assert mock_fes.call_args_list[0][0][0] == 'ListMessages'
        assert mock_fes.call_args_list[1][0][0] == 'BatchGetMessage'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_messages_empty_ids_skips_batch_get(self, _, mock_fes, handler, ctx):
        """When ListMessages returns no IDs, BatchGetMessage is not called."""
        mock_fes.return_value = {'messageIds': []}
        result = await handler.list_resources(
            ctx, resource=ResourceType.messages, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['messages'] == []
        assert 'messageIds' not in parsed['data']
        assert mock_fes.call_count == 1
        assert mock_fes.call_args[0][0] == 'ListMessages'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_messages_preserves_pagination_token(self, _, mock_fes, handler, ctx):
        """NextToken from ListMessages is included in the result."""
        mock_fes.side_effect = [
            {'messageIds': ['msg-1'], 'nextToken': 'page-2-token'},
            {'messages': [{'messageId': 'msg-1', 'text': 'Hi'}]},
        ]
        result = await handler.list_resources(
            ctx, resource=ResourceType.messages, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert parsed['data']['nextToken'] == 'page-2-token'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_messages_forwards_max_results(self, _, mock_fes, handler, ctx):
        """MaxResults is forwarded to the ListMessages call."""
        mock_fes.return_value = {'messageIds': []}
        await handler.list_resources(
            ctx, resource=ResourceType.messages, workspaceId='ws1', maxResults=25
        )
        call_body = mock_fes.call_args[0][1]
        assert call_body['maxResults'] == 25

    # ── worklogs ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_worklogs_requires_workspace_id(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.worklogs)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_worklogs_requires_job_id(self, _, handler, ctx):
        result = await handler.list_resources(
            ctx, resource=ResourceType.worklogs, workspaceId='ws1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_worklogs_with_step_id_filter(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'worklogs': []}
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.worklogs,
            workspaceId='ws1',
            jobId='j1',
            stepId='step-1',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        call_body = mock_paginate.call_args[0][1]
        assert call_body['worklogFilter'] == {'stepIdFilter': {'stepId': 'step-1'}}

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_worklogs_with_time_filter(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'worklogs': []}
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.worklogs,
            workspaceId='ws1',
            jobId='j1',
            startTime='2024-01-01T00:00:00Z',
            endTime='2024-01-02T00:00:00Z',
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        call_body = mock_paginate.call_args[0][1]
        assert call_body['worklogFilter'] == {
            'timeFilter': {
                'startTime': '2024-01-01T00:00:00Z',
                'endTime': '2024-01-02T00:00:00Z',
            }
        }

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_worklogs_invalid_time_range(self, _, handler, ctx):
        result = await handler.list_resources(
            ctx,
            resource=ResourceType.worklogs,
            workspaceId='ws1',
            jobId='j1',
            startTime='2024-01-02T00:00:00Z',
            endTime='2024-01-01T00:00:00Z',
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'startTime must be before endTime' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_worklogs_auto_paginates(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'worklogs': [{'id': 'w1'}, {'id': 'w2'}]}
        result = await handler.list_resources(
            ctx, resource=ResourceType.worklogs, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert len(parsed['data']['worklogs']) == 2
        mock_paginate.assert_called_once_with(
            'ListWorklogs',
            {'workspaceId': 'ws1', 'jobId': 'j1'},
            'worklogs',
            token_key='outputToken',
        )

    # ── plan ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_plan_requires_workspace_id(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.plan)
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_plan_requires_job_id(self, _, handler, ctx):
        result = await handler.list_resources(ctx, resource=ResourceType.plan, workspaceId='ws1')
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'VALIDATION_ERROR'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_plan_merges_results(self, _, mock_fes, handler, ctx):
        async def fes_side_effect(op, body):
            if op == 'ListJobPlanSteps':
                return {'steps': [{'id': 's1'}], 'nextToken': 'steps-tok'}
            return {'updates': [{'id': 'u1'}], 'nextToken': 'updates-tok'}

        mock_fes.side_effect = fes_side_effect
        result = await handler.list_resources(
            ctx, resource=ResourceType.plan, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert 'planSteps' in parsed['data']
        assert 'planUpdates' in parsed['data']
        assert parsed['data']['stepsNextToken'] == 'steps-tok'
        assert parsed['data']['updatesNextToken'] == 'updates-tok'
        # Nested nextToken should be stripped
        assert 'nextToken' not in parsed['data']['planSteps']
        assert 'nextToken' not in parsed['data']['planUpdates']

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_plan_both_fail(self, _, mock_fes, handler, ctx):
        mock_fes.side_effect = RuntimeError('api down')
        result = await handler.list_resources(
            ctx, resource=ResourceType.plan, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['error']['code'] == 'NOT_FOUND'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_fes', new_callable=AsyncMock
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_plan_partial_failure(self, _, mock_fes, handler, ctx):
        """When one of the two plan calls fails, result includes the other."""
        call_count = 0

        async def fes_side_effect(op, body):
            nonlocal call_count
            call_count += 1
            if op == 'ListJobPlanSteps':
                raise RuntimeError('steps failed')
            return {'updates': [{'id': 'u1'}]}

        mock_fes.side_effect = fes_side_effect
        result = await handler.list_resources(
            ctx, resource=ResourceType.plan, workspaceId='ws1', jobId='j1'
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert 'planSteps' not in parsed['data']
        assert 'planUpdates' in parsed['data']

    # ── agents ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_agents_no_filter(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'items': []}
        result = await handler.list_resources(ctx, resource=ResourceType.agents)
        parsed = _parse_result(result)
        assert parsed['success'] is True
        mock_paginate.assert_called_once_with('ListAgents', {}, 'items')

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_agents_type_filter(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'items': []}
        result = await handler.list_resources(
            ctx, resource=ResourceType.agents, agentType=AgentTypeEnum.ORCHESTRATOR_AGENT
        )
        parsed = _parse_result(result)
        assert parsed['success'] is True
        call_body = mock_paginate.call_args[0][1]
        assert call_body['agentFilter'] == {'agentTypeFilter': {'agentType': 'ORCHESTRATOR_AGENT'}}

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_agents_owner_filter(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'items': []}
        await handler.list_resources(
            ctx, resource=ResourceType.agents, ownerType=OwnerTypeEnum.DIRECT_AGENT
        )
        call_body = mock_paginate.call_args[0][1]
        assert call_body['agentFilter'] == {'ownerTypeFilter': {'ownerType': 'DIRECT_AGENT'}}

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_agents_job_orchestrator_filter(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'items': []}
        await handler.list_resources(ctx, resource=ResourceType.agents, jobOrchestrator=True)
        call_body = mock_paginate.call_args[0][1]
        assert call_body['agentFilter'] == {'jobOrchestratorFilter': {'jobOrchestrator': True}}

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_agents_config_availability(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {'items': []}
        await handler.list_resources(
            ctx,
            resource=ResourceType.agents,
            agentConfigurationAvailability=AgentConfigAvailEnum.NEEDS_RUNTIME_CONFIGURATION,
        )
        call_body = mock_paginate.call_args[0][1]
        assert call_body['agentConfigurationAvailability'] == 'NEEDS_RUNTIME_CONFIGURATION'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_agents_returns_all_pages(self, _, mock_paginate, handler, ctx):
        mock_paginate.return_value = {
            'items': [
                {'name': 'agent-1', 'type': 'ORCHESTRATOR_AGENT'},
                {'name': 'agent-2', 'type': 'SUB_AGENT'},
                {'name': 'agent-3', 'type': 'ORCHESTRATOR_AGENT'},
            ]
        }
        result = await handler.list_resources(ctx, resource=ResourceType.agents)
        parsed = _parse_result(result)
        assert parsed['success'] is True
        assert len(parsed['data']['items']) == 3

    # ── exception handling ─────────────────────────────────────────────

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_configured', return_value=True
    )
    async def test_fes_exception_returns_failure(self, _, mock_paginate, handler, ctx):
        mock_paginate.side_effect = RuntimeError('unexpected error')
        result = await handler.list_resources(ctx, resource=ResourceType.workspaces)
        parsed = _parse_result(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
