# ruff: noqa: D100, D101, D102, D103
import asyncio
import httpx
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
@patch('awslabs.aws_transform_mcp_server.upload_helper.httpx.AsyncClient')
@patch('awslabs.aws_transform_mcp_server.upload_helper.call_transform_api', new_callable=AsyncMock)
async def test_upload_json_artifact_uses_timeout(mock_call_api, mock_httpx_cls):
    from awslabs.aws_transform_mcp_server.upload_helper import upload_json_artifact, S3_HTTP_TIMEOUT_SECONDS

    mock_call_api.side_effect = [
        {'s3PreSignedUrl': 'https://s3.example.com/upload', 'artifactId': 'a-1', 'requestHeaders': {}},
        {},
    ]
    mock_resp = MagicMock(status_code=200, text='OK')
    mock_client = AsyncMock()
    mock_client.put = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_cls.return_value = mock_client

    res = await upload_json_artifact('ws', 'job', json.dumps({'k': 'v'}))
    assert res == 'a-1'

    assert mock_httpx_cls.call_args is not None
    kwargs = mock_httpx_cls.call_args.kwargs
    assert 'timeout' in kwargs
    to = kwargs['timeout']
    assert isinstance(to, httpx.Timeout)
    # httpx.Timeout(total) propagates to per-phase values
    assert to.read == pytest.approx(S3_HTTP_TIMEOUT_SECONDS)
    assert to.connect == pytest.approx(S3_HTTP_TIMEOUT_SECONDS)


@pytest.mark.asyncio
@patch('awslabs.aws_transform_mcp_server.upload_helper.httpx.AsyncClient')
@patch('awslabs.aws_transform_mcp_server.upload_helper.call_transform_api', new_callable=AsyncMock)
@patch('awslabs.aws_transform_mcp_server.upload_helper.validate_read_path')
async def test_upload_file_artifact_uses_timeout(mock_validate, mock_call_api, mock_httpx_cls, tmp_path):
    from awslabs.aws_transform_mcp_server.upload_helper import upload_file_artifact, S3_HTTP_TIMEOUT_SECONDS

    test_file = tmp_path / 'data.json'
    test_file.write_text('{"a":1}')
    mock_validate.return_value = str(test_file)

    mock_call_api.side_effect = [
        {'s3PreSignedUrl': 'https://s3.example.com/upload', 'artifactId': 'a-2', 'requestHeaders': {}},
        {},
    ]

    mock_resp = MagicMock(status_code=200, text='OK')
    mock_client = AsyncMock()
    mock_client.put = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_cls.return_value = mock_client

    res = await upload_file_artifact('ws', 'job', str(test_file))
    assert res == 'a-2'

    assert mock_httpx_cls.call_args is not None
    kwargs = mock_httpx_cls.call_args.kwargs
    assert 'timeout' in kwargs
    to = kwargs['timeout']
    assert isinstance(to, httpx.Timeout)
    assert to.read == pytest.approx(S3_HTTP_TIMEOUT_SECONDS)
    assert to.connect == pytest.approx(S3_HTTP_TIMEOUT_SECONDS)


@pytest.mark.asyncio
@patch('awslabs.aws_transform_mcp_server.tool_utils.httpx.AsyncClient')
async def test_download_s3_content_uses_timeout(mock_httpx_cls, tmp_path):
    from awslabs.aws_transform_mcp_server.tool_utils import download_s3_content, DEFAULT_S3_GET_TIMEOUT_SECONDS

    mock_resp = MagicMock()
    mock_resp.text = 'ok'
    mock_resp.content = b'ok'
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_cls.return_value = mock_client

    res = await download_s3_content('https://s3.example.com/file')
    assert res == {'content': 'ok'}

    assert mock_httpx_cls.call_args is not None
    kwargs = mock_httpx_cls.call_args.kwargs
    assert 'timeout' in kwargs
    to = kwargs['timeout']
    assert isinstance(to, httpx.Timeout)
    assert to.read == pytest.approx(DEFAULT_S3_GET_TIMEOUT_SECONDS)
    assert to.connect == pytest.approx(DEFAULT_S3_GET_TIMEOUT_SECONDS)
