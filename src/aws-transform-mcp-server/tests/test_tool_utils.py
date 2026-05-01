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

"""Tests for tool_utils result builders and download_s3_content."""
# ruff: noqa: D101, D102, D103

import httpx
import json
import os
import pytest
from awslabs.aws_transform_mcp_server.tool_utils import (
    CREATE,
    DELETE,
    DELETE_IDEMPOTENT,
    MUTATE,
    READ_ONLY,
    SUBMIT,
    download_s3_content,
    error_result,
    failure_result,
    format_connector_summary,
    format_job_response,
    format_message_summary,
    format_task_summary,
    format_worklog,
    success_result,
    text_result,
)
from unittest.mock import AsyncMock, patch


# ── Annotation dicts ─────────────────────────────────────────────────────


class TestAnnotations:
    """Verify MCP annotation dicts have correct values."""

    def test_read_only(self):
        assert READ_ONLY == {
            'readOnlyHint': True,
            'destructiveHint': False,
            'idempotentHint': True,
        }

    def test_create(self):
        assert CREATE == {'readOnlyHint': False, 'destructiveHint': False, 'idempotentHint': True}

    def test_mutate(self):
        assert MUTATE == {
            'readOnlyHint': False,
            'destructiveHint': False,
            'idempotentHint': False,
        }

    def test_delete(self):
        assert DELETE == {
            'readOnlyHint': False,
            'destructiveHint': True,
            'idempotentHint': False,
        }

    def test_submit(self):
        assert SUBMIT == {
            'readOnlyHint': False,
            'destructiveHint': True,
            'idempotentHint': False,
        }

    def test_delete_idempotent(self):
        assert DELETE_IDEMPOTENT == {
            'readOnlyHint': False,
            'destructiveHint': True,
            'idempotentHint': True,
        }


# ── text_result ──────────────────────────────────────────────────────────


class TestTextResult:
    """Tests for text_result."""

    def test_success_envelope(self):
        result = text_result({'key': 'value'}, is_error=False)
        assert result['isError'] is False
        assert len(result['content']) == 1
        assert result['content'][0]['type'] == 'text'
        parsed = json.loads(result['content'][0]['text'])
        assert parsed == {'key': 'value'}

    def test_error_envelope(self):
        result = text_result({'err': True}, is_error=True)
        assert result['isError'] is True

    def test_default_is_not_error(self):
        result = text_result({})
        assert result['isError'] is False


# ── success_result ───────────────────────────────────────────────────────


class TestSuccessResult:
    """Tests for success_result."""

    def test_wraps_data(self):
        result = success_result({'id': '123'})
        parsed = json.loads(result['content'][0]['text'])
        assert parsed == {'success': True, 'data': {'id': '123'}}
        assert result['isError'] is False

    def test_with_list_data(self):
        result = success_result([1, 2, 3])
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['data'] == [1, 2, 3]

    def test_with_none_data(self):
        result = success_result(None)
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['data'] is None


# ── error_result ─────────────────────────────────────────────────────────


class TestErrorResult:
    """Tests for error_result."""

    def test_basic_error(self):
        result = error_result('NOT_FOUND', 'Resource not found')
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_FOUND'
        assert parsed['error']['message'] == 'Resource not found'
        assert 'suggestedAction' not in parsed['error']
        assert result['isError'] is True

    def test_with_suggested_action(self):
        result = error_result('AUTH_ERR', 'Token expired', 'Run configure again')
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['error']['suggestedAction'] == 'Run configure again'


# ── failure_result ───────────────────────────────────────────────────────


class TestFailureResult:
    """Tests for failure_result."""

    def test_basic_exception(self):
        err = RuntimeError('something broke')
        result = failure_result(err)
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
        assert 'something broke' in parsed['error']['message']
        assert result['isError'] is True

    def test_with_hint(self):
        err = ValueError('bad input')
        result = failure_result(err, hint='Check your parameters')
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['hint'] == 'Check your parameters'

    def test_with_http_error_attributes(self):
        """Errors with status_code and body attributes get extra fields."""

        class HttpError(Exception):
            def __init__(self, status_code, body, message):
                super().__init__(message)
                self.status_code = status_code
                self.body = body

        err = HttpError(429, {'message': 'Rate limited'}, 'HTTP 429')
        result = failure_result(err)
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['error']['httpStatus'] == 429
        assert parsed['error']['details'] == {'message': 'Rate limited'}


# ── download_s3_content ──────────────────────────────────────────────────


class TestDownloadS3Content:
    """Tests for download_s3_content (httpx mocked)."""

    @pytest.mark.asyncio
    async def test_returns_text_content(self):
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = 'file contents here'
        mock_response.raise_for_status = lambda: None

        with patch('awslabs.aws_transform_mcp_server.tool_utils.httpx.AsyncClient') as MockClient:
            instance = AsyncMock()
            instance.get.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await download_s3_content('https://s3.example.com/file.txt')
            assert result == {'content': 'file contents here'}

    @pytest.mark.asyncio
    async def test_saves_to_disk(self, tmp_path):
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b'binary data here'
        mock_response.raise_for_status = lambda: None

        with patch('awslabs.aws_transform_mcp_server.tool_utils.httpx.AsyncClient') as MockClient:
            instance = AsyncMock()
            instance.get.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            save_dir = str(tmp_path) + '/'
            result = await download_s3_content(
                'https://s3.example.com/data.bin',
                save_path=save_dir,
                file_name='output.bin',
            )
            assert result['savedTo'] == os.path.join(str(tmp_path), 'output.bin')
            assert result['sizeBytes'] == len(b'binary data here')
            # Verify the file was actually written
            with open(result['savedTo'], 'rb') as fh:
                assert fh.read() == b'binary data here'

    @pytest.mark.asyncio
    async def test_uses_default_name(self, tmp_path):
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b'data'
        mock_response.raise_for_status = lambda: None

        with patch('awslabs.aws_transform_mcp_server.tool_utils.httpx.AsyncClient') as MockClient:
            instance = AsyncMock()
            instance.get.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            save_dir = str(tmp_path) + '/'
            result = await download_s3_content(
                'https://s3.example.com/obj',
                save_path=save_dir,
                default_name='fallback.txt',
            )
            assert result['savedTo'].endswith('fallback.txt')

    @pytest.mark.asyncio
    async def test_http_error_raises(self):
        with patch('awslabs.aws_transform_mcp_server.tool_utils.httpx.AsyncClient') as MockClient:
            instance = AsyncMock()
            instance.get.side_effect = httpx.HTTPStatusError(
                'Not Found',
                request=httpx.Request('GET', 'https://s3.example.com/missing'),
                response=httpx.Response(404),
            )
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with pytest.raises(httpx.HTTPStatusError):
                await download_s3_content('https://s3.example.com/missing')


# ── New test classes covering uncovered lines ────────────────────────────


class TestFormatJobResponse:
    def test_non_dict_returns_as_is(self):
        assert format_job_response('string') == 'string'
        assert format_job_response(42) == 42
        assert format_job_response(None) is None

    def test_job_value_not_dict(self):
        result = format_job_response({'job': 'not-a-dict'})
        assert result == 'not-a-dict'

    def test_nested_job_dict(self):
        response = {
            'job': {
                'jobId': 'j-1',
                'jobName': 'test-job',
                'statusDetails': 'RUNNING',
                'workspaceId': 'ws-1',
                'restartable': True,
                'extraField': 'ignored',
            }
        }
        result = format_job_response(response)
        assert result == {
            'jobId': 'j-1',
            'jobName': 'test-job',
            'statusDetails': 'RUNNING',
            'workspaceId': 'ws-1',
            'restartable': True,
        }
        assert isinstance(result, dict) and 'extraField' not in result

    def test_jobInfo_key(self):
        response = {
            'jobInfo': {
                'jobId': 'j-2',
                'jobName': 'info-job',
            }
        }
        result = format_job_response(response)
        assert result == {'jobId': 'j-2', 'jobName': 'info-job'}

    def test_fallback_to_response_itself(self):
        response = {
            'jobId': 'j-3',
            'jobName': 'direct-job',
            'extraField': 'ignored',
        }
        result = format_job_response(response)
        assert result == {'jobId': 'j-3', 'jobName': 'direct-job'}


class TestFormatTaskSummary:
    def test_non_dict_returns_as_is(self):
        assert format_task_summary('string') == 'string'
        assert format_task_summary(42) == 42
        assert format_task_summary(None) is None

    def test_dict_extracts_fields(self):
        task = {
            'taskId': 't-1',
            'title': 'Test task',
            'status': 'OPEN',
            'uxComponentId': 'TextInput',
            'extraField': 'ignored',
        }
        result = format_task_summary(task)
        assert result == {
            'taskId': 't-1',
            'title': 'Test task',
            'status': 'OPEN',
            'uxComponentId': 'TextInput',
        }
        assert isinstance(result, dict) and 'extraField' not in result


class TestFormatWorklog:
    def test_non_dict_returns_as_is(self):
        assert format_worklog('string') == 'string'
        assert format_worklog(42) == 42
        assert format_worklog(None) is None

    def test_dict_extracts_fields(self):
        worklog = {
            'description': 'Did something',
            'timestamp': '2025-01-01T00:00:00Z',
            'worklogType': 'INFO',
            'extraField': 'ignored',
        }
        result = format_worklog(worklog)
        assert result == {
            'description': 'Did something',
            'timestamp': '2025-01-01T00:00:00Z',
            'worklogType': 'INFO',
        }
        assert isinstance(result, dict) and 'extraField' not in result


class TestFormatConnectorSummary:
    def test_non_dict_returns_as_is(self):
        assert format_connector_summary('string') == 'string'
        assert format_connector_summary(42) == 42
        assert format_connector_summary(None) is None

    def test_dict_extracts_fields(self):
        connector = {
            'connectorId': 'c-1',
            'connectorName': 'My Connector',
            'connectorType': 'GITHUB',
            'accountConnection': 'linked',
            'extraField': 'ignored',
        }
        result = format_connector_summary(connector)
        assert result == {
            'connectorId': 'c-1',
            'connectorName': 'My Connector',
            'connectorType': 'GITHUB',
            'accountConnection': 'linked',
        }
        assert isinstance(result, dict) and 'extraField' not in result


class TestFormatMessageSummary:
    def test_non_dict_returns_as_is(self):
        assert format_message_summary('string') == 'string'
        assert format_message_summary(42) == 42
        assert format_message_summary(None) is None

    def test_dict_extracts_fields(self):
        message = {
            'messageId': 'm-1',
            'text': 'Hello',
            'messageOrigin': 'USER',
            'createdAt': '2025-01-01T00:00:00Z',
            'parentMessageId': None,
            'processingInfo': {},
            'interactions': [],
            'extraField': 'ignored',
        }
        result = format_message_summary(message)
        assert result == {
            'messageId': 'm-1',
            'text': 'Hello',
            'messageOrigin': 'USER',
            'createdAt': '2025-01-01T00:00:00Z',
            'parentMessageId': None,
            'processingInfo': {},
            'interactions': [],
        }
        assert isinstance(result, dict) and 'extraField' not in result


class TestDownloadS3ContentWithFilePath:
    @pytest.mark.asyncio
    async def test_save_path_with_extension_uses_directly(self, tmp_path):
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b'file data'
        mock_response.raise_for_status = lambda: None

        with patch('awslabs.aws_transform_mcp_server.tool_utils.httpx.AsyncClient') as MockClient:
            instance = AsyncMock()
            instance.get.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            full_path = os.path.join(str(tmp_path), 'specific-file.txt')
            result = await download_s3_content(
                'https://s3.example.com/data.bin',
                save_path=full_path,
            )
            assert result['savedTo'] == full_path
            assert result['sizeBytes'] == len(b'file data')
            with open(full_path, 'rb') as fh:
                assert fh.read() == b'file data'
