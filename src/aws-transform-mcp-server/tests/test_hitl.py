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

"""Tests for HitlHandler: complete_task tool."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def handler():
    """Create a HitlHandler with a mock MCP server."""
    from awslabs.aws_transform_mcp_server.tools.hitl import HitlHandler

    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return HitlHandler(mcp)


@pytest.fixture
def ctx():
    """Return a mock MCP context."""
    return AsyncMock()


def _parse(result: dict) -> dict:
    """Extract the parsed JSON payload from an MCP result envelope."""
    return json.loads(result['content'][0]['text'])


class TestCompleteTaskApprove:
    """Tests for complete_task APPROVE flow."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.upload_json_artifact',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_configured',
        return_value=True,
    )
    async def test_approve_standard(self, _mock_cfg, mock_fes, mock_upload, handler, ctx):
        task_data = {
            'taskId': 't-1',
            'uxComponentId': 'TextInput',
            'severity': 'STANDARD',
        }

        mock_fes.side_effect = [
            # GetHitlTask (Step 1)
            {'task': task_data},
            # SubmitStandardHitlTask (Step 7)
            {},
            # GetHitlTask (Step 8)
            {'task': {**task_data, 'status': 'COMPLETED'}},
        ]
        mock_upload.return_value = 'art-resp-1'

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-1',
            content='"hello"',
            filePath=None,
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['status'] == 'COMPLETED'

        # Verify SubmitStandardHitlTask was called
        submit_call = mock_fes.call_args_list[1]
        assert submit_call[0][0] == 'SubmitStandardHitlTask'
        assert submit_call[0][1]['action'] == 'APPROVE'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.upload_json_artifact',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_configured',
        return_value=True,
    )
    async def test_approve_critical(self, _mock_cfg, mock_fes, mock_upload, handler, ctx):
        task_data = {
            'taskId': 't-2',
            'uxComponentId': 'TextInput',
            'severity': 'CRITICAL',
        }

        mock_fes.side_effect = [
            {'task': task_data},
            {},
            {'task': {**task_data, 'status': 'APPROVED'}},
        ]
        mock_upload.return_value = 'art-resp-2'

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-2',
            content='{"data": "test"}',
            filePath=None,
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        # Verify SubmitCriticalHitlTask was called
        submit_call = mock_fes.call_args_list[1]
        assert submit_call[0][0] == 'SubmitCriticalHitlTask'


class TestCompleteTaskSaveDraft:
    """Tests for complete_task SAVE_DRAFT flow."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_configured',
        return_value=True,
    )
    async def test_save_draft_no_content(self, _mock_cfg, mock_fes, handler, ctx):
        """SAVE_DRAFT with no content/filePath should not upload."""
        task_data = {
            'taskId': 't-3',
            'uxComponentId': 'TextInput',
            'severity': 'STANDARD',
        }

        mock_fes.side_effect = [
            {'task': task_data},
            # UpdateHitlTask
            {},
            # GetHitlTask (refetch)
            {'task': {**task_data, 'status': 'IN_PROGRESS'}},
        ]

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-3',
            content=None,
            filePath=None,
            fileType=None,
            action='SAVE_DRAFT',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        # Verify UpdateHitlTask was called
        update_call = mock_fes.call_args_list[1]
        assert update_call[0][0] == 'UpdateHitlTask'
        # No humanArtifact since no content was provided
        assert 'humanArtifact' not in update_call[0][1]

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.upload_json_artifact',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_configured',
        return_value=True,
    )
    async def test_save_draft_with_content(self, _mock_cfg, mock_fes, mock_upload, handler, ctx):
        """SAVE_DRAFT with content should upload."""
        task_data = {
            'taskId': 't-4',
            'uxComponentId': 'TextInput',
            'severity': 'STANDARD',
        }

        mock_fes.side_effect = [
            {'task': task_data},
            {},  # UpdateHitlTask
            {'task': {**task_data, 'status': 'IN_PROGRESS'}},
        ]
        mock_upload.return_value = 'art-draft-1'

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-4',
            content='"draft text"',
            filePath=None,
            fileType=None,
            action='SAVE_DRAFT',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        update_call = mock_fes.call_args_list[1]
        assert update_call[0][1]['humanArtifact'] == {'artifactId': 'art-draft-1'}


class TestCompleteTaskWithFile:
    """Tests for complete_task with file upload."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.upload_json_artifact',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.upload_file_artifact',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.hitl.os.path.exists', return_value=True)
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_configured',
        return_value=True,
    )
    async def test_file_upload(
        self, _mock_cfg, mock_fes, _mock_exists, mock_file_upload, mock_json_upload, handler, ctx
    ):
        task_data = {
            'taskId': 't-5',
            'uxComponentId': 'TextInput',
            'severity': 'STANDARD',
        }

        mock_fes.side_effect = [
            {'task': task_data},
            {},  # SubmitStandardHitlTask
            {'task': {**task_data, 'status': 'COMPLETED'}},
        ]
        mock_file_upload.return_value = 'art-file-1'
        mock_json_upload.return_value = 'art-resp-1'

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-5',
            content=None,
            filePath='/tmp/test.json',
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['uploadedArtifactId'] == 'art-file-1'
        mock_file_upload.assert_called_once()

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_configured',
        return_value=True,
    )
    async def test_file_not_found(self, _mock_cfg, mock_fes, handler, ctx):
        task_data = {
            'taskId': 't-6',
            'uxComponentId': 'TextInput',
            'severity': 'STANDARD',
        }
        mock_fes.return_value = {'task': task_data}

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-6',
            content=None,
            filePath='/nonexistent/file.json',
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'FILE_NOT_FOUND'


class TestSendForApproval:
    """Tests for SEND_FOR_APPROVAL action."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_configured',
        return_value=True,
    )
    async def test_non_critical_fails(self, _mock_cfg, mock_fes, handler, ctx):
        """SEND_FOR_APPROVAL with non-CRITICAL severity should fail."""
        task_data = {
            'taskId': 't-7',
            'uxComponentId': 'TextInput',
            'severity': 'STANDARD',
        }
        mock_fes.return_value = {'task': task_data}

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-7',
            content='"{}"',
            filePath=None,
            fileType=None,
            action='SEND_FOR_APPROVAL',
        )
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'CRITICAL' in parsed['error']['message']


class TestValidationError:
    """Tests for validation error propagation."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_fes',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_configured',
        return_value=True,
    )
    async def test_invalid_json_content(self, _mock_cfg, mock_fes, handler, ctx):
        task_data = {
            'taskId': 't-8',
            'uxComponentId': 'TextInput',
            'severity': 'STANDARD',
        }
        mock_fes.return_value = {'task': task_data}

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-8',
            content='not valid json',
            filePath=None,
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'JSON' in parsed['error']['message']


class TestNotConfigured:
    """Tests for not-configured state."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_configured',
        return_value=False,
    )
    async def test_not_configured(self, _mock_cfg, handler, ctx):
        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-9',
            content=None,
            filePath=None,
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


class TestContentCoercion:
    """Tests for the _coerce_to_json_string BeforeValidator on the `content` param."""

    @pytest.mark.parametrize(
        'raw,expected',
        [
            (None, None),
            ('"hello"', '"hello"'),
            ('{"a": 1}', '{"a": 1}'),
            ({'CONNECTOR_TYPE': 'x'}, '{"CONNECTOR_TYPE": "x"}'),
            ([{'artifactId': 'a'}], '[{"artifactId": "a"}]'),
            (True, 'true'),
            (42, '42'),
        ],
    )
    def test_coercer_direct(self, raw, expected):
        from awslabs.aws_transform_mcp_server.tools.hitl import _coerce_to_json_string

        assert _coerce_to_json_string(raw) == expected

    @pytest.mark.parametrize(
        'raw,expected',
        [
            (None, None),
            ('"hello"', '"hello"'),
            ({'CONNECTOR_TYPE': 'x'}, '{"CONNECTOR_TYPE": "x"}'),
            ([{'artifactId': 'a'}], '[{"artifactId": "a"}]'),
        ],
    )
    def test_coercer_via_pydantic_validator(self, raw, expected):
        """Ensure the Annotated type actually wires BeforeValidator into Pydantic."""
        from awslabs.aws_transform_mcp_server.tools.hitl import JsonContent
        from pydantic import TypeAdapter

        adapter = TypeAdapter(JsonContent)
        assert adapter.validate_python(raw) == expected
