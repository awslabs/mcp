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
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
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
        assert submit_call[0][1].action == 'APPROVE'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.upload_json_artifact',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
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
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
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
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
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
        assert update_call[0][1].humanArtifact.artifactId == 'art-draft-1'


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
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
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
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
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
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
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
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
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
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
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


class TestDownloadAgentArtifact:
    """Tests for download_agent_artifact standalone function."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    async def test_success_json(self, mock_fes):
        """Successful download returns parsed JSON content and rawText."""
        from awslabs.aws_transform_mcp_server.tools.hitl import download_agent_artifact

        mock_fes.return_value = {'s3PreSignedUrl': 'https://s3.example.com/artifact.json'}

        mock_stream = MagicMock()
        mock_stream.status_code = 200
        mock_stream.headers = {'content-length': '16'}
        mock_stream.aread = AsyncMock(return_value=b'{"key": "value"}')
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        with patch('awslabs.aws_transform_mcp_server.tools.hitl.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            instance = mock_client.return_value.__aenter__.return_value
            instance.stream = MagicMock(return_value=mock_stream)

            result = await download_agent_artifact('ws-1', 'job-1', 'art-1')

        assert result['content'] == {'key': 'value'}
        assert result['rawText'] == '{"key": "value"}'
        assert 'warning' not in result

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    async def test_success_non_json(self, mock_fes):
        """Non-JSON artifact returns rawText and a warning."""
        from awslabs.aws_transform_mcp_server.tools.hitl import download_agent_artifact

        mock_fes.return_value = {'s3PreSignedUrl': 'https://s3.example.com/artifact.txt'}

        mock_stream = MagicMock()
        mock_stream.status_code = 200
        mock_stream.headers = {'content-length': '18'}
        mock_stream.aread = AsyncMock(return_value=b'not valid json <<<')
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        with patch('awslabs.aws_transform_mcp_server.tools.hitl.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            instance = mock_client.return_value.__aenter__.return_value
            instance.stream = MagicMock(return_value=mock_stream)

            result = await download_agent_artifact('ws-1', 'job-1', 'art-1')

        assert 'content' not in result
        assert result['rawText'] == 'not valid json <<<'
        assert 'not JSON' in result['warning']

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    async def test_s3_http_error(self, mock_fes):
        """S3 download returns HTTP error -> warning about download failure."""
        from awslabs.aws_transform_mcp_server.tools.hitl import download_agent_artifact

        mock_fes.return_value = {'s3PreSignedUrl': 'https://s3.example.com/artifact.json'}

        mock_stream = MagicMock()
        mock_stream.status_code = 403
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        with patch('awslabs.aws_transform_mcp_server.tools.hitl.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            instance = mock_client.return_value.__aenter__.return_value
            instance.stream = MagicMock(return_value=mock_stream)

            result = await download_agent_artifact('ws-1', 'job-1', 'art-1')

        assert 'warning' in result
        assert 'HTTP 403' in result['warning']

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    async def test_general_exception(self, mock_fes):
        """Any exception during download returns a warning."""
        from awslabs.aws_transform_mcp_server.tools.hitl import download_agent_artifact

        mock_fes.side_effect = RuntimeError('network failure')

        result = await download_agent_artifact('ws-1', 'job-1', 'art-1')

        assert 'warning' in result
        assert 'network failure' in result['warning']

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    async def test_large_artifact_not_downloaded(self, mock_fes):
        """Large artifact returns size warning without downloading content."""
        from awslabs.aws_transform_mcp_server.tools.hitl import download_agent_artifact

        mock_fes.return_value = {'s3PreSignedUrl': 'https://s3.example.com/artifact.json'}

        mock_stream = MagicMock()
        mock_stream.status_code = 200
        mock_stream.headers = {'content-length': '200000'}  # 200 KB > threshold
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        with patch('awslabs.aws_transform_mcp_server.tools.hitl.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            instance = mock_client.return_value.__aenter__.return_value
            instance.stream = MagicMock(return_value=mock_stream)

            result = await download_agent_artifact('ws-1', 'job-1', 'art-1')

        assert result['sizeBytes'] == 200000
        assert 'large' in result['warning']
        assert 'Ask the user' in result['warning']
        assert 'content' not in result


class TestSendForApprovalToolApproval:
    """Tests for SEND_FOR_APPROVAL with TOOL_APPROVAL category."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
        return_value=True,
    )
    async def test_tool_approval_category_rejected(self, _mock_cfg, mock_fes, handler, ctx):
        """SEND_FOR_APPROVAL with TOOL_APPROVAL category should fail."""
        task_data = {
            'taskId': 't-ta',
            'uxComponentId': 'TextInput',
            'severity': 'CRITICAL',
            'category': 'TOOL_APPROVAL',
        }
        mock_fes.return_value = {'task': task_data}

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-ta',
            content='{}',
            filePath=None,
            fileType=None,
            action='SEND_FOR_APPROVAL',
        )
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'TOOL_APPROVAL' in parsed['error']['message']


class TestSendForApprovalCritical:
    """Tests for the SEND_FOR_APPROVAL action route for CRITICAL tasks."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.upload_json_artifact',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
        return_value=True,
    )
    async def test_send_for_approval_critical(
        self, _mock_cfg, mock_fes, mock_upload, handler, ctx
    ):
        """SEND_FOR_APPROVAL on CRITICAL task routes to UpdateHitlTask with postUpdateAction."""
        task_data = {
            'taskId': 't-crit',
            'uxComponentId': 'TextInput',
            'severity': 'CRITICAL',
        }

        mock_fes.side_effect = [
            {'task': task_data},
            {},  # UpdateHitlTask with SEND_FOR_APPROVAL
            {'task': {**task_data, 'status': 'PENDING_APPROVAL'}},
        ]
        mock_upload.return_value = 'art-resp-crit'

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-crit',
            content='"text"',
            filePath=None,
            fileType=None,
            action='SEND_FOR_APPROVAL',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        # Verify UpdateHitlTask was called with postUpdateAction
        update_call = mock_fes.call_args_list[1]
        assert update_call[0][0] == 'UpdateHitlTask'
        assert update_call[0][1].postUpdateAction == 'SEND_FOR_APPROVAL'


class TestAgentArtifactDownloadInCompleteTask:
    """Tests for the agent artifact download step inside complete_task."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.upload_json_artifact',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.download_agent_artifact',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
        return_value=True,
    )
    async def test_artifact_download_with_warning(
        self, _mock_cfg, mock_fes, mock_download, mock_upload, handler, ctx
    ):
        """When agent artifact download has a warning, it appears in the result."""
        task_data = {
            'taskId': 't-art',
            'uxComponentId': 'TextInput',
            'severity': 'STANDARD',
            'agentArtifact': {'artifactId': 'agent-art-1'},
        }

        mock_fes.side_effect = [
            {'task': task_data},
            {},  # SubmitStandardHitlTask
            {'task': {**task_data, 'status': 'COMPLETED'}},
        ]
        mock_download.return_value = {
            'content': {'key': 'val'},
            'warning': 'Agent artifact is not JSON. Field validation skipped.',
        }
        mock_upload.return_value = 'art-resp-1'

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-art',
            content='"hello"',
            filePath=None,
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        assert (
            parsed['data']['_warning'] == 'Agent artifact is not JSON. Field validation skipped.'
        )
        mock_download.assert_called_once_with(
            workspace_id='ws-1', job_id='job-1', artifact_id='agent-art-1'
        )


class TestCompleteTaskException:
    """Tests for exception handling in complete_task."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
        return_value=True,
    )
    async def test_fes_exception_returns_failure(self, _mock_cfg, mock_fes, handler, ctx):
        """An exception during the flow returns failure_result."""
        mock_fes.side_effect = RuntimeError('unexpected server error')

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-err',
            content='{}',
            filePath=None,
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
        assert 'unexpected server error' in parsed['error']['message']


# ── TOOL_APPROVAL via complete_task (ported from test_approve_hitl.py) ────


class TestCompleteTaskToolApproval:
    """Tests for TOOL_APPROVAL tasks handled through complete_task."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
        return_value=True,
    )
    async def test_approve_skips_artifact_upload(self, _mock_cfg, mock_fes, handler, ctx):
        """TOOL_APPROVAL + APPROVE calls SubmitCriticalHitlTask without humanArtifact."""
        task_data = {
            'taskId': 't-ta-1',
            'uxComponentId': 'ToolApproval',
            'severity': 'CRITICAL',
            'category': 'TOOL_APPROVAL',
            'status': 'AWAITING_APPROVAL',
        }
        mock_fes.side_effect = [
            {'task': task_data},
            {},  # SubmitCriticalHitlTask
            {'task': {**task_data, 'status': 'SUBMITTED', 'action': 'APPROVE'}},
        ]

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-ta-1',
            content=None,
            filePath=None,
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['status'] == 'SUBMITTED'
        assert parsed['data']['action'] == 'APPROVE'

        # Verify SubmitCriticalHitlTask called without humanArtifact
        submit_call = mock_fes.call_args_list[1]
        assert submit_call[0][0] == 'SubmitCriticalHitlTask'
        assert submit_call[0][1].action == 'APPROVE'
        assert submit_call[0][1].humanArtifact is None

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
        return_value=True,
    )
    async def test_reject_skips_artifact_upload(self, _mock_cfg, mock_fes, handler, ctx):
        """TOOL_APPROVAL + REJECT calls SubmitCriticalHitlTask with action=REJECT."""
        task_data = {
            'taskId': 't-ta-2',
            'uxComponentId': 'ToolApproval',
            'severity': 'CRITICAL',
            'category': 'TOOL_APPROVAL',
            'status': 'AWAITING_APPROVAL',
        }
        mock_fes.side_effect = [
            {'task': task_data},
            {},  # SubmitCriticalHitlTask
            {'task': {**task_data, 'status': 'SUBMITTED', 'action': 'REJECT'}},
        ]

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-ta-2',
            content=None,
            filePath=None,
            fileType=None,
            action='REJECT',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['action'] == 'REJECT'

        submit_call = mock_fes.call_args_list[1]
        assert submit_call[0][0] == 'SubmitCriticalHitlTask'
        assert submit_call[0][1].action == 'REJECT'
        assert submit_call[0][1].humanArtifact is None

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
        return_value=True,
    )
    async def test_save_draft_rejected(self, _mock_cfg, mock_fes, handler, ctx):
        """SAVE_DRAFT is not valid for TOOL_APPROVAL tasks."""
        mock_fes.return_value = {
            'task': {
                'taskId': 't-ta-3',
                'uxComponentId': 'ToolApproval',
                'severity': 'CRITICAL',
                'category': 'TOOL_APPROVAL',
            }
        }

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-ta-3',
            content=None,
            filePath=None,
            fileType=None,
            action='SAVE_DRAFT',
        )
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'SAVE_DRAFT' in parsed['error']['message']

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
        return_value=True,
    )
    async def test_content_ignored_for_tool_approval(self, _mock_cfg, mock_fes, handler, ctx):
        """Even if content is provided, TOOL_APPROVAL skips artifact upload."""
        task_data = {
            'taskId': 't-ta-4',
            'uxComponentId': 'ToolApproval',
            'severity': 'CRITICAL',
            'category': 'TOOL_APPROVAL',
            'status': 'AWAITING_APPROVAL',
        }
        mock_fes.side_effect = [
            {'task': task_data},
            {},
            {'task': {**task_data, 'status': 'SUBMITTED'}},
        ]

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-ta-4',
            content='{"some": "data"}',
            filePath=None,
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        # Only 3 FES calls: GetHitlTask, SubmitCriticalHitlTask, GetHitlTask
        assert mock_fes.call_count == 3
        submit_call = mock_fes.call_args_list[1]
        assert submit_call[0][1].humanArtifact is None

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
        return_value=True,
    )
    async def test_wrong_status_rejected(self, _mock_cfg, mock_fes, handler, ctx):
        """TOOL_APPROVAL task not in AWAITING_APPROVAL returns WRONG_STATUS."""
        mock_fes.return_value = {
            'task': {
                'taskId': 't-ta-6',
                'uxComponentId': 'ToolApproval',
                'severity': 'CRITICAL',
                'category': 'TOOL_APPROVAL',
                'status': 'SUBMITTED',
            }
        }

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-ta-6',
            content=None,
            filePath=None,
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'WRONG_STATUS'
        assert 'SUBMITTED' in parsed['error']['message']

    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.hitl.is_fes_available',
        return_value=True,
    )
    async def test_fes_error_returns_failure(self, _mock_cfg, mock_fes, handler, ctx):
        """FES exception during TOOL_APPROVAL submit returns failure."""
        mock_fes.side_effect = [
            {
                'task': {
                    'taskId': 't-ta-5',
                    'uxComponentId': 'ToolApproval',
                    'severity': 'CRITICAL',
                    'category': 'TOOL_APPROVAL',
                    'status': 'AWAITING_APPROVAL',
                }
            },
            RuntimeError('connection failed'),
        ]

        result = await handler.complete_task(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            taskId='t-ta-5',
            content=None,
            filePath=None,
            fileType=None,
            action='APPROVE',
        )
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
