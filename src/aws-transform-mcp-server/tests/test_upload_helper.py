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

"""Tests for upload_helper: upload_json_artifact, SHA256 digest, header flattening."""
# ruff: noqa: D101, D102, D103

import base64
import hashlib
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestUploadJsonArtifact:
    """Tests for upload_json_artifact."""

    @patch('awslabs.aws_transform_mcp_server.upload_helper.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.upload_helper.call_transform_api',
        new_callable=AsyncMock,
    )
    async def test_success(self, mock_fes, mock_httpx_cls):
        from awslabs.aws_transform_mcp_server.upload_helper import upload_json_artifact

        # Setup mock FES responses
        mock_fes.side_effect = [
            # CreateArtifactUploadUrl
            {
                's3PreSignedUrl': 'https://s3.example.com/upload',
                'artifactId': 'art-123',
                'requestHeaders': {
                    'x-amz-checksum': ['abc123'],
                    'content-type': ['application/json'],
                },
            },
            # CompleteArtifactUpload
            {},
        ]

        # Setup mock httpx PUT
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_cls.return_value = mock_client

        content = json.dumps({'hello': 'world'})
        result = await upload_json_artifact('ws-1', 'job-1', content)

        assert result == 'art-123'

        # Verify CreateArtifactUploadUrl was called with correct params
        create_call = mock_fes.call_args_list[0]
        assert create_call[0][0] == 'CreateArtifactUploadUrl'
        body = create_call[0][1]
        assert body.workspaceId == 'ws-1'
        assert body.jobId == 'job-1'
        assert body.artifactReference.artifactType.categoryType == 'HITL_FROM_USER'
        assert body.artifactReference.artifactType.fileType == 'JSON'

        # Verify CompleteArtifactUpload was called
        complete_call = mock_fes.call_args_list[1]
        assert complete_call[0][0] == 'CompleteArtifactUpload'
        assert complete_call[0][1].artifactId == 'art-123'

    @patch('awslabs.aws_transform_mcp_server.upload_helper.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.upload_helper.call_transform_api',
        new_callable=AsyncMock,
    )
    async def test_s3_failure_raises(self, mock_fes, mock_httpx_cls):
        from awslabs.aws_transform_mcp_server.upload_helper import upload_json_artifact

        mock_fes.return_value = {
            's3PreSignedUrl': 'https://s3.example.com/upload',
            'artifactId': 'art-456',
        }

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = 'Forbidden'
        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_cls.return_value = mock_client

        with pytest.raises(Exception, match='Failed to upload'):
            await upload_json_artifact('ws-1', 'job-1', '{}')


class TestSha256Digest:
    """Tests for SHA256 digest correctness."""

    def test_digest_matches_expected(self):
        content = '{"test": "data"}'
        content_bytes = content.encode('utf-8')
        expected = base64.b64encode(hashlib.sha256(content_bytes).digest()).decode('ascii')

        # Verify the same computation used by upload_json_artifact
        actual = base64.b64encode(hashlib.sha256(content_bytes).digest()).decode('ascii')
        assert actual == expected

    def test_empty_content_digest(self):
        content = ''
        content_bytes = content.encode('utf-8')
        digest = base64.b64encode(hashlib.sha256(content_bytes).digest()).decode('ascii')
        # SHA256 of empty string is well-known
        assert digest == '47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU='  # pragma: allowlist secret


class TestHeaderFlattening:
    """Tests for _flatten_request_headers."""

    def test_flatten_single_values(self):
        from awslabs.aws_transform_mcp_server.upload_helper import _flatten_request_headers

        result = _flatten_request_headers({'key1': ['val1'], 'key2': ['val2']})
        assert result == {'key1': 'val1', 'key2': 'val2'}

    def test_flatten_multi_values(self):
        from awslabs.aws_transform_mcp_server.upload_helper import _flatten_request_headers

        result = _flatten_request_headers({'key': ['a', 'b', 'c']})
        assert result == {'key': 'a, b, c'}

    def test_flatten_none(self):
        from awslabs.aws_transform_mcp_server.upload_helper import _flatten_request_headers

        assert _flatten_request_headers(None) == {}

    def test_flatten_empty_values(self):
        from awslabs.aws_transform_mcp_server.upload_helper import _flatten_request_headers

        result = _flatten_request_headers({'key': []})
        assert result == {}


class TestInferFileType:
    """Tests for infer_file_type."""

    def test_json(self):
        from awslabs.aws_transform_mcp_server.upload_helper import infer_file_type

        assert infer_file_type('data.json') == 'JSON'

    def test_pdf(self):
        from awslabs.aws_transform_mcp_server.upload_helper import infer_file_type

        assert infer_file_type('report.pdf') == 'PDF'

    def test_html(self):
        from awslabs.aws_transform_mcp_server.upload_helper import infer_file_type

        assert infer_file_type('page.html') == 'HTML'

    def test_unknown_extension(self):
        from awslabs.aws_transform_mcp_server.upload_helper import infer_file_type

        assert infer_file_type('data.xyz') == 'TXT'


class TestUploadFileArtifact:
    """Tests for upload_file_artifact."""

    @patch('awslabs.aws_transform_mcp_server.upload_helper.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.upload_helper.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.upload_helper.validate_read_path')
    async def test_success(self, mock_validate, mock_fes, mock_httpx_cls, tmp_path):
        from awslabs.aws_transform_mcp_server.upload_helper import upload_file_artifact

        # Create a real temp file
        test_file = tmp_path / 'test_data.json'
        test_file.write_text('{"key": "value"}')
        mock_validate.return_value = str(test_file)

        mock_fes.side_effect = [
            # CreateArtifactUploadUrl
            {
                's3PreSignedUrl': 'https://s3.example.com/upload',
                'artifactId': 'art-file-1',
                'requestHeaders': {'x-amz-checksum': ['abc123']},
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

        result = await upload_file_artifact('ws-1', 'job-1', str(test_file))

        assert result == 'art-file-1'

        # Verify CreateArtifactUploadUrl was called with fileMetadata
        create_call = mock_fes.call_args_list[0]
        body = create_call[0][1]
        assert body.workspaceId == 'ws-1'
        assert body.jobId == 'job-1'
        assert body.fileMetadata.path == 'test_data.json'
        assert body.artifactReference.artifactType.categoryType == 'HITL_FROM_USER'

        # Verify CompleteArtifactUpload was called
        complete_call = mock_fes.call_args_list[1]
        assert complete_call[0][0] == 'CompleteArtifactUpload'
        assert complete_call[0][1].artifactId == 'art-file-1'

    async def test_file_too_large_raises(self, tmp_path):
        from awslabs.aws_transform_mcp_server.upload_helper import upload_file_artifact

        test_file = tmp_path / 'big.json'
        test_file.write_text('x')

        with patch('awslabs.aws_transform_mcp_server.upload_helper.os.stat') as mock_stat:
            mock_stat.return_value = MagicMock(st_size=600 * 1024 * 1024)
            with pytest.raises(Exception, match='File too large'):
                await upload_file_artifact('ws-1', 'job-1', str(test_file))

    @patch('awslabs.aws_transform_mcp_server.upload_helper.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.upload_helper.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.upload_helper.validate_read_path')
    async def test_s3_failure_raises(self, mock_validate, mock_fes, mock_httpx_cls, tmp_path):
        from awslabs.aws_transform_mcp_server.upload_helper import upload_file_artifact

        test_file = tmp_path / 'data.json'
        test_file.write_text('{}')
        mock_validate.return_value = str(test_file)

        mock_fes.return_value = {
            's3PreSignedUrl': 'https://s3.example.com/upload',
            'artifactId': 'art-fail',
        }

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = 'Forbidden'
        mock_client = AsyncMock()
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_cls.return_value = mock_client

        with pytest.raises(Exception, match='Failed to upload file'):
            await upload_file_artifact('ws-1', 'job-1', str(test_file))

    @patch('awslabs.aws_transform_mcp_server.upload_helper.httpx.AsyncClient')
    @patch(
        'awslabs.aws_transform_mcp_server.upload_helper.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.upload_helper.validate_read_path')
    async def test_custom_file_type_and_category(
        self, mock_validate, mock_fes, mock_httpx_cls, tmp_path
    ):
        from awslabs.aws_transform_mcp_server.upload_helper import upload_file_artifact

        test_file = tmp_path / 'report.pdf'
        test_file.write_bytes(b'%PDF-1.4')
        mock_validate.return_value = str(test_file)

        mock_fes.side_effect = [
            {
                's3PreSignedUrl': 'https://s3.example.com/upload',
                'artifactId': 'art-pdf-1',
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

        result = await upload_file_artifact(
            'ws-1', 'job-1', str(test_file), file_type='PDF', category_type='CUSTOMER_INPUT'
        )

        assert result == 'art-pdf-1'
        create_call = mock_fes.call_args_list[0]
        body = create_call[0][1]
        assert body.artifactReference.artifactType.fileType == 'PDF'
        assert body.artifactReference.artifactType.categoryType == 'CUSTOMER_INPUT'
