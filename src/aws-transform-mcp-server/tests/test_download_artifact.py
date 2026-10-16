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

"""Tests for DownloadArtifactHandler: streaming download_artifact tool."""
# ruff: noqa: D101, D102, D103

import base64
import json
import pytest
from awslabs.aws_transform_mcp_server.tools.download_artifact import (
    DownloadArtifactHandler,
    _build_artifact_scope,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def handler():
    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return DownloadArtifactHandler(mcp)


@pytest.fixture
def ctx():
    return AsyncMock()


def _parse(result: dict) -> dict:
    return json.loads(result['content'][0]['text'])


def _stream(content=b'', file_name='file.bin', error=None, extra_meta=None):
    meta = None
    if error is None:
        meta = {'fileName': file_name}
        if extra_meta:
            meta.update(extra_meta)
    return {'metadata': meta, 'content': content, 'error': error}


class TestScopeResolution:
    def test_job_scope(self):
        assert _build_artifact_scope('a-1', 'ws-1', 'job-1', None, None) == {
            'jobScope': {'workspaceId': 'ws-1', 'jobId': 'job-1', 'artifactId': 'a-1'}
        }

    def test_workspace_scope_not_supported(self):
        # workspaceId without jobId (workspace-scope) is rejected, not silently
        # downgraded to user-scope.
        with pytest.raises(ValueError, match='Workspace-scope downloads are not supported'):
            _build_artifact_scope('a-1', 'ws-1', None, None, None)

    def test_user_scope(self):
        assert _build_artifact_scope('a-1', None, None, None, None) == {
            'userScope': {'artifactId': 'a-1'}
        }

    def test_connector_scope(self):
        assert _build_artifact_scope(None, 'ws-1', 'job-1', 'c-1', 'k/1') == {
            'connectorScope': {
                'workspaceId': 'ws-1',
                'jobId': 'job-1',
                'connectorId': 'c-1',
                'assetKey': 'k/1',
            }
        }

    def test_connector_missing_fields_raises(self):
        with pytest.raises(ValueError):
            _build_artifact_scope(None, 'ws-1', None, 'c-1', 'k/1')

    def test_no_artifact_id_raises(self):
        with pytest.raises(ValueError):
            _build_artifact_scope(None, 'ws-1', 'job-1', None, None)


class TestDownloadArtifact:
    @patch(
        'awslabs.aws_transform_mcp_server.tools.download_artifact.is_fes_available',
        return_value=True,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.download_artifact.call_transform_api_streaming',
        new_callable=AsyncMock,
    )
    async def test_writes_file_and_returns_metadata(
        self, mock_stream, _cfg, handler, ctx, tmp_path
    ):
        payload = b'hello world bytes'
        mock_stream.return_value = _stream(
            content=payload, file_name='out.txt', extra_meta={'contentLengthBytes': len(payload)}
        )
        dest = str(tmp_path / 'out.txt')

        with patch(
            'awslabs.aws_transform_mcp_server.tools.download_artifact.validate_write_path',
            return_value=dest,
        ):
            result = await handler.download_artifact(
                ctx, artifactId='a-1', workspaceId='ws-1', jobId='job-1', outputPath=dest
            )
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['bytesWritten'] == len(payload)
        assert parsed['data']['fileName'] == 'out.txt'
        assert parsed['data']['contentLengthBytes'] == len(payload)
        # Verify the correct scope was requested.
        body = mock_stream.call_args[0][1]
        assert body == {
            'artifactScope': {
                'jobScope': {'workspaceId': 'ws-1', 'jobId': 'job-1', 'artifactId': 'a-1'}
            }
        }
        # Bytes were written to disk.
        with open(dest, 'rb') as fh:
            assert fh.read() == payload
        # Small payload is echoed inline.
        assert base64.b64decode(parsed['data']['contentBase64']) == payload

    @patch(
        'awslabs.aws_transform_mcp_server.tools.download_artifact.is_fes_available',
        return_value=True,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.download_artifact.call_transform_api_streaming',
        new_callable=AsyncMock,
    )
    async def test_large_payload_not_inlined(self, mock_stream, _cfg, handler, ctx, tmp_path):
        payload = b'x' * (256 * 1024 + 1)
        mock_stream.return_value = _stream(content=payload, file_name='big.bin')
        dest = str(tmp_path / 'big.bin')

        with patch(
            'awslabs.aws_transform_mcp_server.tools.download_artifact.validate_write_path',
            return_value=dest,
        ):
            result = await handler.download_artifact(ctx, artifactId='a-1', outputPath=dest)
        parsed = _parse(result)

        assert parsed['success'] is True
        assert 'contentBase64' not in parsed['data']
        assert body_scope(mock_stream) == {'userScope': {'artifactId': 'a-1'}}

    @patch(
        'awslabs.aws_transform_mcp_server.tools.download_artifact.is_fes_available',
        return_value=True,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.download_artifact.call_transform_api_streaming',
        new_callable=AsyncMock,
    )
    async def test_stream_error_event(self, mock_stream, _cfg, handler, ctx, tmp_path):
        mock_stream.return_value = _stream(
            error={'code': 'CUSTOMER_BUCKET_ACCESS_DENIED', 'message': 'denied'}
        )
        result = await handler.download_artifact(
            ctx,
            artifactId='a-1',
            workspaceId='ws-1',
            jobId='job-1',
            outputPath=str(tmp_path / 'x'),
        )
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'CUSTOMER_BUCKET_ACCESS_DENIED'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.download_artifact.is_fes_available',
        return_value=True,
    )
    async def test_invalid_scope(self, _cfg, handler, ctx):
        result = await handler.download_artifact(ctx, connectorId='c-1')
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'INVALID_SCOPE'

    @patch(
        'awslabs.aws_transform_mcp_server.tools.download_artifact.is_fes_available',
        return_value=False,
    )
    async def test_not_configured(self, _cfg, handler, ctx):
        result = await handler.download_artifact(ctx, artifactId='a-1')
        parsed = _parse(result)
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


def body_scope(mock_stream):
    """Return the inner artifactScope dict from the mocked streaming call."""
    return mock_stream.call_args[0][1]['artifactScope']


_DL = 'awslabs.aws_transform_mcp_server.tools.download_artifact'


class TestDownloadArtifactExtraPaths:
    @patch(f'{_DL}.is_fes_available', return_value=True)
    @patch(f'{_DL}.call_transform_api_streaming', new_callable=AsyncMock)
    async def test_no_output_path_writes_using_file_name(
        self, mock_stream, _cfg, handler, ctx, tmp_path
    ):
        mock_stream.return_value = _stream(content=b'hi', file_name='out.txt')
        dest = str(tmp_path / 'out.txt')
        # outputPath omitted -> handler calls validate_write_path('.', file_name)
        with patch(f'{_DL}.validate_write_path', return_value=dest) as vwp:
            result = await handler.download_artifact(ctx, artifactId='a-1')
        assert vwp.call_args[0] == ('.', 'out.txt')
        parsed = _parse(result)
        assert parsed['success'] is True
        assert parsed['data']['fileName'] == 'out.txt'
        assert (tmp_path / 'out.txt').read_bytes() == b'hi'

    @patch(f'{_DL}.is_fes_available', return_value=True)
    @patch(f'{_DL}.call_transform_api_streaming', new_callable=AsyncMock)
    async def test_includes_declared_length_and_artifact_metadata(
        self, mock_stream, _cfg, handler, ctx, tmp_path
    ):
        mock_stream.return_value = _stream(
            content=b'xyz',
            extra_meta={'contentLengthBytes': 3, 'artifact': {'artifactId': 'a-1'}},
        )
        dest = str(tmp_path / 'f')
        with patch(f'{_DL}.validate_write_path', return_value=dest):
            result = await handler.download_artifact(
                ctx, artifactId='a-1', workspaceId='w', jobId='j', outputPath=dest
            )
        parsed = _parse(result)
        assert parsed['data']['contentLengthBytes'] == 3
        assert parsed['data']['artifact'] == {'artifactId': 'a-1'}

    @patch(f'{_DL}.is_fes_available', return_value=False)
    async def test_not_configured_returns_error(self, _cfg, handler, ctx):
        result = await handler.download_artifact(ctx, artifactId='a-1')
        assert _parse(result)['success'] is False

    @patch(f'{_DL}.is_fes_available', return_value=True)
    @patch(f'{_DL}.call_transform_api_streaming', new_callable=AsyncMock)
    async def test_unexpected_exception_returns_failure(self, mock_stream, _cfg, handler, ctx):
        mock_stream.side_effect = RuntimeError('boom')
        assert _parse(await handler.download_artifact(ctx, artifactId='a-1'))['success'] is False
