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
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.code_interpreter.files import (
    _parse_list_files_response,
)
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


class TestParseListFilesResponse:
    """Test cases for _parse_list_files_response helper."""

    def test_parse_text_content_blocks(self):
        """Text content blocks are parsed into file paths."""
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'text', 'text': 'data.csv\nscripts/run.py\nREADME.md'},
                        ],
                    },
                },
            ],
        }

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert file_paths == ['data.csv', 'scripts/run.py', 'README.md']
        assert 'data.csv' in raw_content

    def test_parse_resource_link_blocks(self):
        """Resource link content blocks are parsed into file paths from URIs."""
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {
                                'type': 'resource_link',
                                'uri': 'file:///home/user/data.csv',
                                'name': 'data.csv',
                            },
                            {
                                'type': 'resource_link',
                                'uri': 'file:///home/user/output.json',
                                'name': 'output.json',
                            },
                        ],
                    },
                },
            ],
        }

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert file_paths == ['/home/user/data.csv', '/home/user/output.json']
        assert raw_content == ''

    def test_parse_resource_link_name_fallback(self):
        """Falls back to name when uri is empty in resource_link blocks."""
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'resource_link', 'uri': '', 'name': 'fallback.txt'},
                        ],
                    },
                },
            ],
        }

        file_paths, _, _ = _parse_list_files_response(response)

        assert file_paths == ['fallback.txt']

    def test_parse_empty_stream(self):
        """Empty stream returns no files."""
        response = {'stream': []}

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert file_paths == []
        assert raw_content == ''

    def test_parse_no_stream_key(self):
        """Response with neither stream nor content returns empty results."""
        response = {'something_else': 'value'}

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert file_paths == []
        assert raw_content == ''
        assert is_error is False

    def test_parse_flat_dict_without_stream(self):
        """Flat dict is parsed if the SDK pre-consumes the stream."""
        response = {'content': [{'type': 'text', 'text': 'a.csv\nb.csv'}]}

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert file_paths == ['a.csv', 'b.csv']
        assert 'a.csv' in raw_content
        assert is_error is False

    def test_parse_flat_dict_is_error(self):
        """An error flag on a flat dict is surfaced."""
        response = {'content': [{'type': 'text', 'text': 'boom'}], 'isError': True}

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert file_paths == []
        assert raw_content == 'boom'
        assert is_error is True

    def test_parse_bare_string_response(self):
        """A bare string response is treated as listing text."""
        file_paths, raw_content, is_error = _parse_list_files_response('a.csv\nb.csv')

        assert file_paths == ['a.csv', 'b.csv']
        assert raw_content == 'a.csv\nb.csv'
        assert is_error is False

    def test_parse_is_error_does_not_become_a_file_path(self):
        """An error response yields no files, so error text cannot be used as a path."""
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'text', 'text': "Error: directory '/nope' does not exist"},
                        ],
                        'isError': True,
                    },
                },
            ],
        }

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert is_error is True
        assert file_paths == []
        assert 'does not exist' in raw_content

    def test_parse_long_format_listing_extracts_names(self):
        """`ls -l` rows yield bare file names, not whole permission lines."""
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {
                                'type': 'text',
                                'text': (
                                    'total 8\n'
                                    '-rw-r--r-- 1 root root   12 Jan  1 00:00 a.csv\n'
                                    'drwxr-xr-x 2 root root 4096 Jan  1 00:00 sub\n'
                                ),
                            },
                        ],
                    },
                },
            ],
        }

        file_paths, _, is_error = _parse_list_files_response(response)

        assert file_paths == ['a.csv', 'sub']
        assert is_error is False

    def test_parse_long_format_preserves_names_with_spaces(self):
        """A long-format name containing spaces is kept whole."""
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {
                                'type': 'text',
                                'text': '-rw-r--r-- 1 root root 12 Jan  1 00:00 my report.csv',
                            },
                        ],
                    },
                },
            ],
        }

        file_paths, _, _ = _parse_list_files_response(response)

        assert file_paths == ['my report.csv']

    def test_parse_text_filters_total_line(self):
        """Text fallback parser filters 'total N' lines from ls-style output."""
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'text', 'text': 'total 12\nfile1.py\nfile2.py'},
                        ],
                    },
                },
            ],
        }

        file_paths, _, _ = _parse_list_files_response(response)

        assert file_paths == ['file1.py', 'file2.py']

    def test_parse_mixed_text_and_resource_link_prefers_resource_link(self):
        """When resource_link blocks exist, text blocks are not used for file paths."""
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'text', 'text': 'data.csv\noutput.json'},
                            {
                                'type': 'resource_link',
                                'uri': 'file:///home/user/data.csv',
                                'name': 'data.csv',
                            },
                        ],
                    },
                },
            ],
        }

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        # resource_link paths take priority; text is still in raw_content
        assert file_paths == ['/home/user/data.csv']
        assert 'data.csv' in raw_content

    def test_parse_long_format_without_date_fields(self):
        """A mode row with no date columns still yields the trailing name.

        Some busybox/minimal `ls -l` variants emit only mode, links, owner,
        group and size before the name.
        """
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'text', 'text': '-rw-r--r-- 1 root root 12 a.csv'},
                        ],
                    },
                },
            ],
        }

        file_paths, _, _ = _parse_list_files_response(response)

        assert file_paths == ['a.csv']

    def test_parse_mode_like_line_too_short_is_kept_verbatim(self):
        """A mode-like first field with too few columns falls back to the raw line.

        Guards against truncating a legitimate 10-character file name that
        happens to start with one of the ls type characters.
        """
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'text', 'text': 'data-1.csv 42'},
                        ],
                    },
                },
            ],
        }

        file_paths, _, _ = _parse_list_files_response(response)

        assert file_paths == ['data-1.csv 42']

    def test_parse_skips_events_without_result(self):
        """Stream events lacking a 'result' key are ignored."""
        response = {
            'stream': [
                {'metadata': {'latencyMs': 3}},
                {'result': {'content': [{'type': 'text', 'text': 'a.csv'}]}},
            ],
        }

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert file_paths == ['a.csv']
        assert raw_content == 'a.csv'
        assert is_error is False

    def test_parse_ignores_unknown_block_types(self):
        """Blocks that are neither text nor resource_link are skipped."""
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'image', 'data': 'ignored'},
                            {'type': 'text', 'text': 'a.csv'},
                        ],
                    },
                },
            ],
        }

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert file_paths == ['a.csv']
        assert 'ignored' not in raw_content

    def test_parse_resource_link_without_uri_or_name_is_skipped(self):
        """A resource_link carrying neither uri nor name adds no entry."""
        response = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'resource_link', 'uri': '', 'name': ''},
                        ],
                    },
                },
            ],
        }

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert file_paths == []
        assert raw_content == ''
        assert is_error is False

    def test_parse_flat_dict_ignores_non_text_blocks(self):
        """Non-text blocks in a flat dict response are skipped."""
        response = {
            'content': [
                {'type': 'resource_link', 'uri': 'file:///w/a.csv'},
                {'type': 'text', 'text': 'a.csv'},
            ],
        }

        file_paths, raw_content, is_error = _parse_list_files_response(response)

        assert file_paths == ['a.csv']
        assert raw_content == 'a.csv'

    def test_parse_unexpected_response_type_returns_empty(self):
        """A response that is neither dict nor str yields empty results."""
        file_paths, raw_content, is_error = _parse_list_files_response(None)

        assert file_paths == []
        assert raw_content == ''
        assert is_error is False


class TestListFiles:
    """Test cases for list_files."""

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_list_files_reports_sandbox_error(self, mock_get_session, mock_ctx):
        """An isError response is reported as a failure, not as a file named after the error."""
        mock_client = MagicMock()
        mock_client.invoke.return_value = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'text', 'text': "Error: directory '/nope' does not exist"},
                        ],
                        'isError': True,
                    },
                },
            ],
        }
        mock_get_session.return_value = mock_client

        result = await files.list_files(
            mock_ctx,
            session_id='session-123',
            directory_path='/nope',
        )

        assert result.is_error is True
        assert result.files == []
        assert 'Found' not in result.message
        assert 'does not exist' in result.content
        mock_ctx.error.assert_awaited_once()

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_list_files_long_format_output(self, mock_get_session, mock_ctx):
        """`ls -l` style output yields bare file names."""
        mock_client = MagicMock()
        mock_client.invoke.return_value = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {
                                'type': 'text',
                                'text': (
                                    'total 8\n'
                                    '-rw-r--r-- 1 root root 12 Jan  1 00:00 a.csv\n'
                                    'drwxr-xr-x 2 root root 40 Jan  1 00:00 sub\n'
                                ),
                            },
                        ],
                    },
                },
            ],
        }
        mock_get_session.return_value = mock_client

        result = await files.list_files(mock_ctx, session_id='session-123')

        assert result.files == ['a.csv', 'sub']
        assert result.is_error is False

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_list_files_happy_path(self, mock_get_session, mock_ctx):
        """Test listing files returns correct response with text content blocks."""
        mock_client = MagicMock()
        mock_client.invoke.return_value = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'text', 'text': 'data.csv\nscripts/run.py'},
                        ],
                    },
                },
            ],
        }
        mock_get_session.return_value = mock_client

        result = await files.list_files(
            mock_ctx,
            session_id='session-123',
        )

        assert result.files == ['data.csv', 'scripts/run.py']
        assert 'Found 2 file(s)' in result.message
        mock_get_session.assert_called_once_with('session-123')
        mock_client.invoke.assert_called_once_with('listFiles', {})

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_list_files_with_directory_path(self, mock_get_session, mock_ctx):
        """Test listing files with a specific directory path."""
        mock_client = MagicMock()
        mock_client.invoke.return_value = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {'type': 'text', 'text': 'output.json'},
                        ],
                    },
                },
            ],
        }
        mock_get_session.return_value = mock_client

        result = await files.list_files(
            mock_ctx,
            session_id='session-123',
            directory_path='/home/user/project',
        )

        assert result.files == ['output.json']
        assert '/home/user/project' in result.message
        mock_client.invoke.assert_called_once_with(
            'listFiles', {'directoryPath': '/home/user/project'}
        )

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_list_files_empty_directory(self, mock_get_session, mock_ctx):
        """Test listing files in an empty directory returns no files."""
        mock_client = MagicMock()
        mock_client.invoke.return_value = {
            'stream': [
                {
                    'result': {
                        'content': [],
                    },
                },
            ],
        }
        mock_get_session.return_value = mock_client

        result = await files.list_files(
            mock_ctx,
            session_id='session-123',
        )

        assert result.files == []
        assert 'No files found' in result.message

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_list_files_with_resource_links(self, mock_get_session, mock_ctx):
        """Test listing files when API returns resource_link content blocks."""
        mock_client = MagicMock()
        mock_client.invoke.return_value = {
            'stream': [
                {
                    'result': {
                        'content': [
                            {
                                'type': 'resource_link',
                                'uri': 'file:///workspace/app.py',
                                'name': 'app.py',
                            },
                            {
                                'type': 'resource_link',
                                'uri': 'file:///workspace/config.yaml',
                                'name': 'config.yaml',
                            },
                        ],
                    },
                },
            ],
        }
        mock_get_session.return_value = mock_client

        result = await files.list_files(
            mock_ctx,
            session_id='session-123',
        )

        assert result.files == ['/workspace/app.py', '/workspace/config.yaml']
        assert 'Found 2 file(s)' in result.message

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_list_files_sdk_exception(self, mock_get_session, mock_ctx):
        """Test SDK exception raises and signals ctx.error."""
        mock_client = MagicMock()
        mock_client.invoke.side_effect = Exception('Service unavailable')
        mock_get_session.return_value = mock_client

        with pytest.raises(Exception, match='Service unavailable'):
            await files.list_files(
                mock_ctx,
                session_id='session-123',
            )

        mock_ctx.error.assert_called_once()

    @patch(f'{MODULE_PATH}.get_session_client')
    async def test_list_files_unregistered_session_raises(self, mock_get_session, mock_ctx):
        """Test listing files from unregistered session raises KeyError."""
        mock_get_session.side_effect = KeyError('No active session client for session unknown')

        with pytest.raises(KeyError, match='No active session client'):
            await files.list_files(
                mock_ctx,
                session_id='unknown',
            )

        mock_ctx.error.assert_called_once()
