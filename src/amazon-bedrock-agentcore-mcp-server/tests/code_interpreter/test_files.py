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

"""Tests for file operation tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter import files
from unittest.mock import MagicMock, patch


MODULE_PATH = 'awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.files'


class TestUploadFile:
    """Test cases for upload_file."""

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_upload_file_happy_path(self, mock_get_session, mock_ctx):
        """Test uploading a file returns correct response."""
        mock_client = MagicMock()
        mock_client.upload_file.return_value = {}
        mock_get_session.return_value = mock_client

        result = await files.upload_file(
            mock_ctx,
            session_id='session-123',
            path='data/input.csv',
            content='col1,col2\n1,2\n3,4',
        )

        assert result.path == 'data/input.csv'
        assert 'successfully' in result.message
        mock_get_session.assert_called_once_with('session-123')
        mock_client.upload_file.assert_called_once_with(
            path='data/input.csv',
            content='col1,col2\n1,2\n3,4',
        )

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_upload_file_with_description(self, mock_get_session, mock_ctx):
        """Test uploading a file with description."""
        mock_client = MagicMock()
        mock_client.upload_file.return_value = {}
        mock_get_session.return_value = mock_client

        await files.upload_file(
            mock_ctx,
            session_id='session-123',
            path='scripts/run.py',
            content='print("hello")',
            description='A test script',
        )

        mock_client.upload_file.assert_called_once_with(
            path='scripts/run.py',
            content='print("hello")',
            description='A test script',
        )

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_upload_file_absolute_path_rejected(self, mock_get_session, mock_ctx):
        """Test SDK raises ValueError for absolute paths."""
        mock_client = MagicMock()
        mock_client.upload_file.side_effect = ValueError('Path must be relative')
        mock_get_session.return_value = mock_client

        with pytest.raises(ValueError, match='Path must be relative'):
            await files.upload_file(
                mock_ctx,
                session_id='session-123',
                path='/tmp/data.csv',
                content='col1,col2\n1,2',
            )

        mock_ctx.error.assert_called_once()

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_upload_file_sdk_exception(self, mock_get_session, mock_ctx):
        """Test SDK exception raises as infrastructure error."""
        mock_client = MagicMock()
        mock_client.upload_file.side_effect = Exception('Storage limit exceeded')
        mock_get_session.return_value = mock_client

        with pytest.raises(Exception, match='Storage limit exceeded'):
            await files.upload_file(
                mock_ctx,
                session_id='session-123',
                path='data/big_file.bin',
                content='x' * 1000,
            )

        mock_ctx.error.assert_called_once()

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_upload_file_unregistered_session_raises(self, mock_get_session, mock_ctx):
        """Test uploading to unregistered session raises KeyError."""
        mock_get_session.side_effect = KeyError('No active session client for session unknown')

        with pytest.raises(KeyError, match='No active session client'):
            await files.upload_file(
                mock_ctx,
                session_id='unknown',
                path='test.txt',
                content='data',
            )

        mock_ctx.error.assert_called_once()


class TestDownloadFile:
    """Test cases for download_file."""

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_download_file_string_response(self, mock_get_session, mock_ctx):
        """Test downloading a file with string response (SDK returns Union[str, bytes])."""
        mock_client = MagicMock()
        mock_client.download_file.return_value = 'raw file content'
        mock_get_session.return_value = mock_client

        result = await files.download_file(
            mock_ctx,
            session_id='session-123',
            path='output/result.txt',
        )

        assert result.path == 'output/result.txt'
        assert result.content == 'raw file content'
        mock_get_session.assert_called_once_with('session-123')
        mock_client.download_file.assert_called_once_with(path='output/result.txt')

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_download_file_bytes_response_base64_encoded(self, mock_get_session, mock_ctx):
        """Test downloading binary file returns base64-encoded content.

        The SDK only returns bytes when UTF-8 decoding has already failed,
        so bytes always means binary content that must be base64-encoded.
        """
        binary_data = b'\x89PNG\r\n\x1a\n'
        mock_client = MagicMock()
        mock_client.download_file.return_value = binary_data
        mock_get_session.return_value = mock_client

        result = await files.download_file(
            mock_ctx,
            session_id='session-123',
            path='output/image.png',
        )

        import base64

        assert result.content == base64.b64encode(binary_data).decode('ascii')
        assert 'base64-encoded binary' in result.message

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_download_file_not_found(self, mock_get_session, mock_ctx):
        """Test SDK raises FileNotFoundError for missing files."""
        mock_client = MagicMock()
        mock_client.download_file.side_effect = FileNotFoundError('nonexistent.txt')
        mock_get_session.return_value = mock_client

        with pytest.raises(FileNotFoundError):
            await files.download_file(
                mock_ctx,
                session_id='session-123',
                path='nonexistent.txt',
            )

        mock_ctx.error.assert_called_once()

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_download_file_sdk_exception(self, mock_get_session, mock_ctx):
        """Test SDK exception raises as infrastructure error."""
        mock_client = MagicMock()
        mock_client.download_file.side_effect = Exception('Connection error')
        mock_get_session.return_value = mock_client

        with pytest.raises(Exception, match='Connection error'):
            await files.download_file(
                mock_ctx,
                session_id='session-123',
                path='output/file.txt',
            )

        mock_ctx.error.assert_called_once()

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_download_file_unregistered_session_raises(self, mock_get_session, mock_ctx):
        """Test downloading from unregistered session raises KeyError."""
        mock_get_session.side_effect = KeyError('No active session client for session unknown')

        with pytest.raises(KeyError, match='No active session client'):
            await files.download_file(
                mock_ctx,
                session_id='unknown',
                path='test.txt',
            )

        mock_ctx.error.assert_called_once()
