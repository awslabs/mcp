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

"""Tests for package_workflow output_path support and write_zip_to_local / write_zip_to_s3 utilities.

Covers:
- write_zip_to_local: write, no-overwrite, parent creation, path traversal rejection
- write_zip_to_s3: upload, no-overwrite, missing key, content type
- package_workflow output_path routing: None (base64 inline), local path, S3 URI
- package_workflow expected_bucket_owner sentinel resolution
- package_workflow error handling for all caught exception types
"""

import json
import pytest
import zipfile
from awslabs.aws_healthomics_mcp_server.tools.helper_tools import package_workflow
from botocore.exceptions import ClientError, NoCredentialsError
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch


SAMPLE_WDL = 'version 1.0\nworkflow Test { }'
SAMPLE_ZIP = b'PK\x05\x06' + b'\x00' * 18  # minimal empty zip


# ---------------------------------------------------------------------------
# write_zip_to_local
# ---------------------------------------------------------------------------


class TestWriteZipToLocal:
    """Tests for write_zip_to_local utility."""

    def test_write_and_read_back(self, tmp_path):
        """Written bytes can be read back identically."""
        from awslabs.aws_healthomics_mcp_server.utils.path_utils import write_zip_to_local

        dest = str(tmp_path / 'out.zip')
        data = b'\x00\x01\x02\x03'
        returned = write_zip_to_local(data, dest)

        assert open(returned, 'rb').read() == data

    def test_no_overwrite(self, tmp_path):
        """Raises FileExistsError when file already exists."""
        from awslabs.aws_healthomics_mcp_server.utils.path_utils import write_zip_to_local

        dest = str(tmp_path / 'existing.zip')
        open(dest, 'wb').write(b'old')

        with pytest.raises(FileExistsError):
            write_zip_to_local(b'new', dest)

    def test_creates_parent_directories(self, tmp_path):
        """Parent directories are created automatically."""
        from awslabs.aws_healthomics_mcp_server.utils.path_utils import write_zip_to_local

        dest = str(tmp_path / 'a' / 'b' / 'c' / 'out.zip')
        write_zip_to_local(b'data', dest)

        assert open(dest, 'rb').read() == b'data'

    def test_rejects_path_traversal(self, tmp_path):
        """Paths with traversal sequences are rejected."""
        from awslabs.aws_healthomics_mcp_server.utils.path_utils import write_zip_to_local

        with pytest.raises(ValueError, match='traversal'):
            write_zip_to_local(b'data', str(tmp_path / '..' / 'escape.zip'))

    def test_rejects_null_bytes(self):
        """Paths with null bytes are rejected."""
        from awslabs.aws_healthomics_mcp_server.utils.path_utils import write_zip_to_local

        with pytest.raises(ValueError, match='null bytes'):
            write_zip_to_local(b'data', '/tmp/bad\x00.zip')


# ---------------------------------------------------------------------------
# write_zip_to_s3
# ---------------------------------------------------------------------------


class TestWriteZipToS3:
    """Tests for write_zip_to_s3 utility."""

    def _mock_session(self, s3_client):
        mock_session = MagicMock()
        mock_session.client.return_value = s3_client
        return mock_session

    def test_successful_upload(self):
        """Uploads ZIP bytes with application/zip content type."""
        from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_zip_to_s3

        mock_s3 = MagicMock()
        # head_object 404 means object doesn't exist — expected
        mock_s3.head_object.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}}, 'HeadObject'
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.get_aws_session',
            return_value=self._mock_session(mock_s3),
        ):
            result = write_zip_to_s3(b'zipdata', 's3://my-bucket/workflow.zip')

        assert result == 's3://my-bucket/workflow.zip'
        mock_s3.put_object.assert_called_once_with(
            Bucket='my-bucket',
            Key='workflow.zip',
            Body=b'zipdata',
            ContentType='application/zip',
        )

    def test_no_overwrite(self):
        """Raises FileExistsError when object already exists."""
        from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_zip_to_s3

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {}  # object exists

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.s3_utils.get_aws_session',
                return_value=self._mock_session(mock_s3),
            ),
            pytest.raises(FileExistsError, match='already exists'),
        ):
            write_zip_to_s3(b'zipdata', 's3://my-bucket/workflow.zip')

        mock_s3.put_object.assert_not_called()

    def test_missing_key_raises_value_error(self):
        """Raises ValueError when S3 URI has no object key."""
        from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_zip_to_s3

        mock_s3 = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.s3_utils.get_aws_session',
                return_value=self._mock_session(mock_s3),
            ),
            pytest.raises(ValueError, match='Missing object key'),
        ):
            write_zip_to_s3(b'zipdata', 's3://my-bucket/')

    def test_invalid_uri_raises_value_error(self):
        """Raises ValueError for malformed S3 URIs."""
        from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_zip_to_s3

        with pytest.raises(ValueError):
            write_zip_to_s3(b'zipdata', 's3://')

    def test_bucket_owner_passed_through(self):
        """expected_bucket_owner is forwarded to validate_s3_bucket_for_write."""
        from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_zip_to_s3

        mock_s3 = MagicMock()
        mock_s3.head_object.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}}, 'HeadObject'
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.get_aws_session',
            return_value=self._mock_session(mock_s3),
        ):
            write_zip_to_s3(b'zipdata', 's3://my-bucket/out.zip', expected_bucket_owner='123456')

        # head_bucket should have been called with ExpectedBucketOwner
        mock_s3.head_bucket.assert_called_once_with(
            Bucket='my-bucket', ExpectedBucketOwner='123456'
        )


# ---------------------------------------------------------------------------
# package_workflow output_path integration
# ---------------------------------------------------------------------------


class TestPackageWorkflowOutputPath:
    """Tests for package_workflow output_path and expected_bucket_owner parameters."""

    @pytest.mark.asyncio
    async def test_none_output_path_returns_base64(self):
        """When output_path is None, returns base64-encoded ZIP inline (existing behavior)."""
        ctx = AsyncMock()
        result = await package_workflow(
            ctx=ctx,
            main_file_content=SAMPLE_WDL,
            main_file_name='main.wdl',
            additional_files=None,
            output_path=None,
        )

        assert isinstance(result, str)
        # Should be valid base64 that decodes to a ZIP
        import base64

        zip_bytes = base64.b64decode(result)
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            assert 'main.wdl' in zf.namelist()

    @pytest.mark.asyncio
    async def test_local_output_path_writes_zip(self, tmp_path):
        """Local output_path writes ZIP to disk and returns JSON summary."""
        ctx = AsyncMock()
        dest = str(tmp_path / 'workflow.zip')

        result = await package_workflow(
            ctx=ctx,
            main_file_content=SAMPLE_WDL,
            main_file_name='main.wdl',
            additional_files=None,
            output_path=dest,
        )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed['status'] == 'success'
        assert parsed['file_count'] == 1
        assert parsed['files'] == ['main.wdl']
        assert 'output_path' in parsed

        # Verify the file was actually written and is a valid ZIP
        with zipfile.ZipFile(parsed['output_path']) as zf:
            assert 'main.wdl' in zf.namelist()
            assert zf.read('main.wdl').decode('utf-8') == SAMPLE_WDL

    @pytest.mark.asyncio
    async def test_local_output_path_with_additional_files(self, tmp_path):
        """Local output_path includes all files in the summary and ZIP."""
        ctx = AsyncMock()
        dest = str(tmp_path / 'multi.zip')

        result = await package_workflow(
            ctx=ctx,
            main_file_content=SAMPLE_WDL,
            main_file_name='main.wdl',
            additional_files={'tasks.wdl': 'task T { }'},
            output_path=dest,
        )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed['file_count'] == 2
        assert set(parsed['files']) == {'main.wdl', 'tasks.wdl'}

        with zipfile.ZipFile(parsed['output_path']) as zf:
            assert set(zf.namelist()) == {'main.wdl', 'tasks.wdl'}

    @pytest.mark.asyncio
    async def test_s3_output_path_calls_write_zip_to_s3(self):
        """S3 URI output_path routes to write_zip_to_s3 and returns JSON summary."""
        ctx = AsyncMock()
        s3_path = 's3://my-bucket/workflows/out.zip'

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_s3',
            return_value=s3_path,
        ) as mock_s3_write:
            result = await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files=None,
                output_path=s3_path,
                expected_bucket_owner=None,
            )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed['status'] == 'success'
        assert parsed['output_path'] == s3_path
        assert parsed['file_count'] == 1
        assert parsed['files'] == ['main.wdl']

        mock_s3_write.assert_called_once()
        call_args = mock_s3_write.call_args
        assert call_args[0][1] == s3_path  # s3_path arg
        assert call_args[0][2] is None  # expected_bucket_owner=None

    @pytest.mark.asyncio
    async def test_s3_output_path_sentinel_resolves_account_id(self):
        """Sentinel __DEFAULT__ expected_bucket_owner resolves to caller account ID."""
        ctx = AsyncMock()
        s3_path = 's3://my-bucket/out.zip'

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_s3',
                return_value=s3_path,
            ) as mock_s3_write,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.helper_tools.get_account_id',
                return_value='111122223333',
            ) as mock_get_account_id,
        ):
            result = await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files=None,
                output_path=s3_path,
                expected_bucket_owner='__DEFAULT__',
            )

        mock_get_account_id.assert_called_once()
        call_args = mock_s3_write.call_args
        assert call_args[0][2] == '111122223333'

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed['status'] == 'success'

    @pytest.mark.asyncio
    async def test_s3_output_path_explicit_owner(self):
        """Explicit expected_bucket_owner is passed through without calling get_account_id."""
        ctx = AsyncMock()
        s3_path = 's3://my-bucket/out.zip'

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_s3',
                return_value=s3_path,
            ) as mock_s3_write,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.helper_tools.get_account_id',
            ) as mock_get_account_id,
        ):
            await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files=None,
                output_path=s3_path,
                expected_bucket_owner='999988887777',
            )

        mock_get_account_id.assert_not_called()
        call_args = mock_s3_write.call_args
        assert call_args[0][2] == '999988887777'

    @pytest.mark.asyncio
    async def test_local_path_does_not_call_s3(self, tmp_path):
        """Local output_path does not invoke write_zip_to_s3."""
        ctx = AsyncMock()
        dest = str(tmp_path / 'local.zip')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_s3',
        ) as mock_s3_write:
            await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files=None,
                output_path=dest,
            )

        mock_s3_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_s3_path_does_not_call_local(self):
        """S3 output_path does not invoke write_zip_to_local."""
        ctx = AsyncMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_s3',
                return_value='s3://b/k.zip',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_local',
            ) as mock_local_write,
        ):
            await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files=None,
                output_path='s3://b/k.zip',
                expected_bucket_owner=None,
            )

        mock_local_write.assert_not_called()

    # --- Error handling for each caught exception type ---

    @pytest.mark.asyncio
    async def test_error_value_error_on_write(self, tmp_path):
        """ValueError from write is caught and returns JSON error."""
        ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_local',
            side_effect=ValueError('bad path'),
        ):
            result = await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files=None,
                output_path='/some/path.zip',
            )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'bad path' in parsed['error']

    @pytest.mark.asyncio
    async def test_error_file_exists(self, tmp_path):
        """FileExistsError from write is caught and returns JSON error."""
        ctx = AsyncMock()
        dest = str(tmp_path / 'exists.zip')
        open(dest, 'wb').write(b'old')

        result = await package_workflow(
            ctx=ctx,
            main_file_content=SAMPLE_WDL,
            main_file_name='main.wdl',
            additional_files=None,
            output_path=dest,
        )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'already exists' in parsed['error']

    @pytest.mark.asyncio
    async def test_error_os_error(self):
        """OSError from write is caught and returns JSON error."""
        ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_local',
            side_effect=OSError('disk full'),
        ):
            result = await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files=None,
                output_path='/some/path.zip',
            )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'disk full' in parsed['error']

    @pytest.mark.asyncio
    async def test_error_permission_error(self):
        """PermissionError from write is caught and returns JSON error."""
        ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_local',
            side_effect=PermissionError('access denied'),
        ):
            result = await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files=None,
                output_path='/some/path.zip',
            )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'access denied' in parsed['error']

    @pytest.mark.asyncio
    async def test_error_client_error_s3(self):
        """ClientError from S3 write is caught and returns JSON error."""
        ctx = AsyncMock()
        error = ClientError({'Error': {'Code': '403', 'Message': 'Forbidden'}}, 'PutObject')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_s3',
            side_effect=error,
        ):
            result = await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files=None,
                output_path='s3://bucket/out.zip',
                expected_bucket_owner=None,
            )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'Forbidden' in parsed['error']

    @pytest.mark.asyncio
    async def test_error_no_credentials_s3(self):
        """NoCredentialsError from S3 write is caught and returns JSON error."""
        ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.helper_tools.write_zip_to_s3',
            side_effect=NoCredentialsError(),
        ):
            result = await package_workflow(
                ctx=ctx,
                main_file_content=SAMPLE_WDL,
                main_file_name='main.wdl',
                additional_files=None,
                output_path='s3://bucket/out.zip',
                expected_bucket_owner=None,
            )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'credentials' in parsed['error'].lower() or 'Credentials' in parsed['error']
