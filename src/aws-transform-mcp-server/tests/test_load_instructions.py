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

"""Tests for LoadInstructionsHandler."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from awslabs.aws_transform_mcp_server.guidance_nudge import _checked_jobs
from awslabs.aws_transform_mcp_server.tools.load_instructions import LoadInstructionsHandler
from unittest.mock import AsyncMock, MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.tools.load_instructions'


@pytest.fixture(autouse=True)
def reset_checked_jobs():
    _checked_jobs.clear()
    yield
    _checked_jobs.clear()


@pytest.fixture
def handler():
    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return LoadInstructionsHandler(mcp)


@pytest.fixture
def ctx():
    return AsyncMock()


def _parse(result: dict) -> dict:
    return json.loads(result['content'][0]['text'])


class TestLoadInstructions:
    @pytest.mark.asyncio
    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_not_configured(self, _, handler, ctx):
        result = await handler.load_instructions(ctx, workspaceId='ws-1', jobId='j-1')
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_no_instructions_found(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {'artifacts': []}
        result = await handler.load_instructions(ctx, workspaceId='ws-1', jobId='j-1')
        parsed = _parse(result)
        assert parsed['success'] is True
        assert parsed['data']['instructionsFound'] is False
        assert 'j-1' in _checked_jobs

    @pytest.mark.asyncio
    @patch(f'{_MOD}.download_s3_content', new_callable=AsyncMock)
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_instructions_found_and_downloaded(
        self, _, mock_fes, mock_download, handler, ctx
    ):
        mock_fes.side_effect = [
            {'artifacts': [{'artifactId': 'art-1', 'fileMetadata': {'path': 'JOB_INSTRUCTIONS'}}]},
            {'s3PreSignedUrl': 'https://s3.example.com/file'},
        ]
        mock_download.return_value = {'content': '# Steering content'}
        result = await handler.load_instructions(ctx, workspaceId='ws-1', jobId='j-1')
        parsed = _parse(result)
        assert parsed['success'] is True
        assert parsed['data']['instructionsFound'] is True
        assert parsed['data']['artifactId'] == 'art-1'
        assert 'j-1' in _checked_jobs

    @pytest.mark.asyncio
    @patch(
        f'{_MOD}.call_transform_api', new_callable=AsyncMock, side_effect=Exception('API error')
    )
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_does_not_mark_checked_on_error(self, _, mock_fes, handler, ctx):
        result = await handler.load_instructions(ctx, workspaceId='ws-1', jobId='j-1')
        parsed = _parse(result)
        assert parsed['success'] is False
        assert 'j-1' not in _checked_jobs

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_skips_non_matching_artifacts(self, _, mock_fes, handler, ctx):
        mock_fes.return_value = {
            'artifacts': [
                {'artifactId': 'art-1', 'fileMetadata': {'path': 'SOME_OTHER_FILE'}},
                {'artifactId': 'art-2', 'fileMetadata': {'path': 'report.html'}},
            ]
        }
        result = await handler.load_instructions(ctx, workspaceId='ws-1', jobId='j-1')
        parsed = _parse(result)
        assert parsed['data']['instructionsFound'] is False

    @pytest.mark.asyncio
    @patch(f'{_MOD}.download_s3_content', new_callable=AsyncMock)
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_empty_content_returns_error_and_does_not_mark_checked(
        self, _, mock_fes, mock_download, handler, ctx
    ):
        mock_fes.side_effect = [
            {'artifacts': [{'artifactId': 'art-1', 'fileMetadata': {'path': 'JOB_INSTRUCTIONS'}}]},
            {'s3PreSignedUrl': 'https://s3.example.com/file'},
        ]
        mock_download.return_value = {'content': ''}
        result = await handler.load_instructions(ctx, workspaceId='ws-1', jobId='j-1')
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'INSTRUCTIONS_DOWNLOAD_FAILED'
        assert 'j-1' not in _checked_jobs

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_missing_presigned_url_returns_error(self, _, mock_fes, handler, ctx):
        mock_fes.side_effect = [
            {'artifacts': [{'artifactId': 'art-1', 'fileMetadata': {'path': 'JOB_INSTRUCTIONS'}}]},
            {},
        ]
        result = await handler.load_instructions(ctx, workspaceId='ws-1', jobId='j-1')
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'INSTRUCTIONS_DOWNLOAD_FAILED'
        assert 'j-1' not in _checked_jobs


class TestInstructionGateIntegration:
    """Tests that the nudge gate works in other tools."""

    @pytest.fixture(autouse=True)
    def restore_real_nudge(self):
        """Restore the real job_needs_check for gate integration tests."""
        import importlib

        chat_send_mod = importlib.import_module(
            'awslabs.aws_transform_mcp_server.tools.chat.send_message'
        )
        import awslabs.aws_transform_mcp_server.tools.get_resource as get_mod
        import awslabs.aws_transform_mcp_server.tools.hitl as hitl_mod
        import awslabs.aws_transform_mcp_server.tools.list_resources as list_mod
        from awslabs.aws_transform_mcp_server.guidance_nudge import job_needs_check as real_fn

        _saved = {
            'get': get_mod.job_needs_check,
            'list': list_mod.job_needs_check,
            'hitl': hitl_mod.job_needs_check,
            'chat': chat_send_mod.job_needs_check,
        }
        get_mod.job_needs_check = real_fn
        list_mod.job_needs_check = real_fn
        hitl_mod.job_needs_check = real_fn
        chat_send_mod.job_needs_check = real_fn
        _checked_jobs.clear()
        yield
        get_mod.job_needs_check = _saved['get']
        list_mod.job_needs_check = _saved['list']
        hitl_mod.job_needs_check = _saved['hitl']
        chat_send_mod.job_needs_check = _saved['chat']

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_get_resource_blocks_unchecked_job(self, _, mock_mcp, mock_context):
        from awslabs.aws_transform_mcp_server.tools.get_resource import (
            GetResourceHandler,
            GetResourceType,
        )

        h = GetResourceHandler(mock_mcp)
        result = await h.get_resource(
            mock_context,
            resource=GetResourceType.task,
            workspaceId='ws-1',
            jobId='j-unchecked',
            taskId='t-1',
        )
        parsed = _parse(result)
        assert parsed['error']['code'] == 'INSTRUCTIONS_REQUIRED'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.get_resource.is_fes_available', return_value=True
    )
    async def test_get_resource_allows_exempt_resources(self, _, mock_mcp, mock_context):
        from awslabs.aws_transform_mcp_server.tools.get_resource import (
            GetResourceHandler,
            GetResourceType,
        )

        with patch(
            'awslabs.aws_transform_mcp_server.tools.get_resource.get_session',
            new_callable=AsyncMock,
        ) as mock_session:
            mock_session.return_value = {'success': True, 'data': {}}
            h = GetResourceHandler(mock_mcp)
            result = await h.get_resource(mock_context, resource=GetResourceType.session)
            assert result['isError'] is False

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_fes_available', return_value=True
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.call_transform_api',
        new_callable=AsyncMock,
    )
    async def test_list_resources_blocks_unchecked_job(self, mock_fes, _, mock_mcp, mock_context):
        from awslabs.aws_transform_mcp_server.tools.list_resources import (
            ListResourcesHandler,
            ResourceType,
        )

        h = ListResourcesHandler(mock_mcp)
        result = await h.list_resources(
            mock_context, resource=ResourceType.tasks, workspaceId='ws-1', jobId='j-unchecked'
        )
        parsed = _parse(result)
        assert parsed['error']['code'] == 'INSTRUCTIONS_REQUIRED'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_fes_available', return_value=True
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    async def test_list_resources_allows_exempt_resources(
        self, mock_paginate, _, mock_mcp, mock_context
    ):
        from awslabs.aws_transform_mcp_server.tools.list_resources import (
            ListResourcesHandler,
            ResourceType,
        )

        mock_paginate.return_value = {'jobList': []}
        h = ListResourcesHandler(mock_mcp)
        result = await h.list_resources(
            mock_context, resource=ResourceType.jobs, workspaceId='ws-1', jobId='j-unchecked'
        )
        parsed = _parse(result)
        assert parsed['success'] is True

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available', return_value=True)
    async def test_hitl_blocks_unchecked_job(self, _, mock_mcp, mock_context):
        from awslabs.aws_transform_mcp_server.tools.hitl import HitlHandler

        h = HitlHandler(mock_mcp)
        result = await h.complete_task(
            mock_context, workspaceId='ws-1', jobId='j-unchecked', taskId='t-1'
        )
        parsed = _parse(result)
        assert parsed['error']['code'] == 'INSTRUCTIONS_REQUIRED'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.chat.send_message.is_fes_available',
        return_value=True,
    )
    async def test_chat_blocks_unchecked_job(self, _, mock_mcp, mock_context):
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        result = await send_message(
            mock_context, workspaceId='ws-1', text='hello', jobId='j-unchecked'
        )
        parsed = _parse(result)
        assert parsed['error']['code'] == 'INSTRUCTIONS_REQUIRED'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.paginate_all',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.list_resources.is_fes_available', return_value=True
    )
    async def test_gated_tool_proceeds_after_mark_checked(
        self, _, mock_paginate, mock_mcp, mock_context
    ):
        from awslabs.aws_transform_mcp_server.guidance_nudge import mark_job_checked
        from awslabs.aws_transform_mcp_server.tools.list_resources import (
            ListResourcesHandler,
            ResourceType,
        )

        mark_job_checked('j-checked')
        mock_paginate.return_value = {'hitlTasks': []}
        h = ListResourcesHandler(mock_mcp)
        result = await h.list_resources(
            mock_context, resource=ResourceType.tasks, workspaceId='ws-1', jobId='j-checked'
        )
        parsed = _parse(result)
        assert parsed['success'] is True
