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
    MUTATE,
    READ_ONLY,
    SUBMIT,
    download_s3_content,
    error_result,
    failure_result,
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
