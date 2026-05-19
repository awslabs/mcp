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

"""Tests for ArtifactHandler: upload_artifact tool."""
# ruff: noqa: D101, D102, D103

import base64
import json
import os
import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def handler():
    """Create an ArtifactHandler with a mock MCP server."""
    from awslabs.aws_transform_mcp_server.tools.artifact import ArtifactHandler

    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return ArtifactHandler(mcp)


@pytest.fixture
def ctx():
    """Return a mock MCP context."""
    return AsyncMock()


def _parse(result: dict) -> dict:
    """Extract the parsed JSON payload from an MCP result envelope."""
    return json.loads(result['content'][0]['text'])


class TestUploadArtifactFromFile:
    """Tests for upload_artifact with a file path."""

    @patch('awslabs.aws_transform_mcp_server.tools.artifact.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.is_fes_available',
        return_value=True,
    )
    async def test_upload_from_file(self, _mock_cfg, mock_fes, mock_httpx_cls, handler, ctx):
        # Create a temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"test": "data"}')
            temp_path = f.name

        try:
            mock_fes.side_effect = [
                # CreateArtifactUploadUrl
                {
                    's3PreSignedUrl': 'https://s3.example.com/upload',
                    'artifactId': 'art-file-1',
                },
                # CompleteArtifactUpload
                {},
            ]

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx_cls.return_value = mock_client

            result = await handler.upload_artifact(
                ctx,
                workspaceId='ws-1',
                jobId='job-1',
                content=temp_path,
                encoding='utf-8',
                categoryType='CUSTOMER_INPUT',
                fileType='JSON',
                fileName=None,
                planStepId=None,
            )
            parsed = _parse(result)

            assert parsed['success'] is True
            assert parsed['data']['artifactId'] == 'art-file-1'

            # Verify fileMetadata was sent
            create_call = mock_fes.call_args_list[0]
            body = create_call[0][1]
            assert body.fileMetadata.path == os.path.basename(temp_path)
        finally:
            os.unlink(temp_path)


class TestUploadArtifactRawContent:
    """Tests for upload_artifact with raw content."""

    @patch('awslabs.aws_transform_mcp_server.tools.artifact.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.is_fes_available',
        return_value=True,
    )
    async def test_upload_raw_utf8(self, _mock_cfg, mock_fes, mock_httpx_cls, handler, ctx):
        mock_fes.side_effect = [
            {
                's3PreSignedUrl': 'https://s3.example.com/upload',
                'artifactId': 'art-raw-1',
            },
            {},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_cls.return_value = mock_client

        result = await handler.upload_artifact(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            content='{"key": "value"}',
            encoding='utf-8',
            categoryType='CUSTOMER_INPUT',
            fileType='JSON',
            fileName='data.json',
            planStepId=None,
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['artifactId'] == 'art-raw-1'


class TestUploadArtifactBase64:
    """Tests for upload_artifact with base64 encoding."""

    @patch('awslabs.aws_transform_mcp_server.tools.artifact.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.is_fes_available',
        return_value=True,
    )
    async def test_upload_base64(self, _mock_cfg, mock_fes, mock_httpx_cls, handler, ctx):
        original_data = b'binary data here'
        b64_content = base64.b64encode(original_data).decode('ascii')

        mock_fes.side_effect = [
            {
                's3PreSignedUrl': 'https://s3.example.com/upload',
                'artifactId': 'art-b64-1',
            },
            {},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_cls.return_value = mock_client

        result = await handler.upload_artifact(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            content=b64_content,
            encoding='base64',
            categoryType='CUSTOMER_INPUT',
            fileType='TXT',
            fileName='binary.bin',
            planStepId=None,
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['artifactId'] == 'art-b64-1'

        # Verify the correct bytes were uploaded
        put_call = mock_client.put.call_args
        uploaded_bytes = put_call.kwargs.get('content') or put_call[1].get('content')
        assert uploaded_bytes == original_data


class TestUploadArtifactNotConfigured:
    """Tests for not-configured state."""

    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.is_fes_available',
        return_value=False,
    )
    async def test_not_configured(self, _mock_cfg, handler, ctx):
        result = await handler.upload_artifact(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            content='{}',
            encoding='utf-8',
            categoryType='CUSTOMER_INPUT',
            fileType='JSON',
            fileName=None,
            planStepId=None,
        )
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


class TestUploadArtifactEdgeCases:
    @pytest.fixture
    def handler(self, mock_mcp):
        from awslabs.aws_transform_mcp_server.tools.artifact import ArtifactHandler

        return ArtifactHandler(mock_mcp)

    @pytest.fixture
    def mock_mcp(self):
        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
        return mcp

    @pytest.fixture
    def ctx(self):
        return AsyncMock()

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.artifact.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.artifact.is_fes_available', return_value=True)
    async def test_s3_upload_failure(self, _, mock_fes, mock_httpx, handler, ctx):
        mock_fes.return_value = {
            'artifactId': 'a-1',
            's3PreSignedUrl': 'https://s3.example.com/upload',
            'requestHeaders': {'x-amz-header': ['val']},
        }
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client
        result = await handler.upload_artifact(
            ctx,
            workspaceId='ws-1',
            jobId='j-1',
            content='{"key": "val"}',
            encoding='utf-8',
            categoryType='GENERAL',
            fileType='JSON',
            fileName=None,
            planStepId=None,
        )
        parsed = _parse(result)
        assert parsed['error']['code'] == 'UPLOAD_FAILED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.artifact.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.artifact.is_fes_available', return_value=True)
    async def test_upload_with_plan_step_id(self, _, mock_fes, mock_httpx, handler, ctx):
        mock_fes.side_effect = [
            {
                'artifactId': 'a-1',
                's3PreSignedUrl': 'https://s3.example.com/upload',
                'requestHeaders': None,
            },
            None,
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client
        result = await handler.upload_artifact(
            ctx,
            workspaceId='ws-1',
            jobId='j-1',
            content='{"key": "val"}',
            encoding='utf-8',
            categoryType='GENERAL',
            fileType='JSON',
            fileName=None,
            planStepId='step-1',
        )
        parsed = _parse(result)
        assert parsed['success'] is True
        create_body = mock_fes.call_args_list[0][0][1]
        assert create_body.planStepId == 'step-1'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.call_transform_api',
        new_callable=AsyncMock,
        side_effect=Exception('fail'),
    )
    @patch('awslabs.aws_transform_mcp_server.tools.artifact.is_fes_available', return_value=True)
    async def test_upload_fes_error(self, _, mock_fes, handler, ctx):
        result = await handler.upload_artifact(
            ctx,
            workspaceId='ws-1',
            jobId='j-1',
            content='{"key": "val"}',
            encoding='utf-8',
            categoryType='GENERAL',
            fileType='JSON',
            fileName=None,
            planStepId=None,
        )
        parsed = _parse(result)
        assert parsed['success'] is False


class TestUploadArtifactConnector:
    """Tests for upload_artifact with connectorId (connector-based upload)."""

    @pytest.fixture
    def handler(self):
        from awslabs.aws_transform_mcp_server.tools.artifact import ArtifactHandler

        mcp = MagicMock()
        mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
        return ArtifactHandler(mcp)

    @pytest.fixture
    def ctx(self):
        return AsyncMock()

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.artifact.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.artifact.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.artifact.is_fes_available', return_value=True)
    async def test_connector_upload_skips_complete(self, _, mock_fes, mock_httpx, handler, ctx):
        """Connector upload skips CompleteArtifactUpload and returns different shape."""
        mock_fes.return_value = {
            's3PreSignedUrl': 'https://bucket.s3.amazonaws.com/path/file.json',
            'requestHeaders': {'Host': ['bucket.s3.amazonaws.com']},
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_client

        result = await handler.upload_artifact(
            ctx,
            workspaceId='ws-1',
            jobId='job-1',
            content='{"data": true}',
            encoding='utf-8',
            categoryType='CUSTOMER_INPUT',
            fileType='JSON',
            fileName='test.json',
            planStepId=None,
            connectorId='conn-123',
        )
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['uploaded'] is True
        assert parsed['data']['fileName'] == 'test.json'
        assert parsed['data']['connectorId'] == 'conn-123'
        assert 'artifactId' not in parsed['data']

        # Verify CompleteArtifactUpload was NOT called (only 1 FES call: CreateArtifactUploadUrl)
        assert mock_fes.call_count == 1
        assert mock_fes.call_args_list[0][0][0] == 'CreateArtifactUploadUrl'
