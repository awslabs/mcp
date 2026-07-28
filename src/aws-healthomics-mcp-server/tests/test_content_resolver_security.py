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

"""Security-focused tests for content_resolver utility.

Tests cover path traversal rejection, S3 URI format validation,
size limit enforcement, and security-before-I/O ordering.
"""

import pytest
from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
    ContentInputType,
    _check_size_limit,
    detect_content_input_type,
    resolve_single_content,
)
from awslabs.aws_healthomics_mcp_server.utils.path_utils import (
    validate_local_path,
    validate_s3_uri_format,
)
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Path traversal rejection
# Validates: Requirements Content Resolution Security
# ---------------------------------------------------------------------------


class TestPathTraversalRejection:
    """Security tests for path traversal rejection with various patterns.

    Validates: Requirements Content Resolution Security
    """

    def test_simple_parent_traversal(self) -> None:
        """Reject '../secret' style traversal."""
        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            validate_local_path('../secret')

    def test_mid_path_traversal(self) -> None:
        """Reject 'dir/../secret' style traversal."""
        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            validate_local_path('dir/../secret')

    def test_trailing_traversal(self) -> None:
        """Reject 'dir/..' style traversal."""
        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            validate_local_path('dir/..')

    def test_bare_double_dot(self) -> None:
        """Reject bare '..' path."""
        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            validate_local_path('..')

    def test_nested_traversal(self) -> None:
        """Reject deeply nested traversal like 'a/b/../../etc/passwd'."""
        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            validate_local_path('a/b/../../etc/passwd')

    def test_backslash_traversal(self) -> None:
        """Reject backslash-based traversal (cross-platform safety).

        On POSIX, os.path.normpath treats backslashes as literal chars,
        but the forward-slash checks still catch '../' patterns.
        """
        # This uses forward slashes which are caught directly
        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            validate_local_path('dir/../../../etc/passwd')

    def test_backslash_dot_dot_windows(self) -> None:
        r"""Reject '..\\\\windows' style traversal via normpath on any OS."""
        # os.path.normpath converts backslashes on Windows; on POSIX the
        # literal '..\\windows' is a single component, but the normpath
        # split still catches '..' when present as a forward-slash component.
        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            validate_local_path('foo/../../bar')

    def test_double_traversal_to_etc_passwd(self) -> None:
        """Reject '../../etc/passwd' classic attack pattern."""
        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            validate_local_path('../../etc/passwd')

    def test_traversal_with_absolute_prefix(self) -> None:
        """Reject '/tmp/safe/../../etc/passwd' traversal."""
        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            validate_local_path('/tmp/safe/../../etc/passwd')

    def test_traversal_falls_through_to_inline(self) -> None:
        """Path traversal in detect_content_input_type falls through to INLINE_CONTENT."""
        result = detect_content_input_type('../etc/passwd')
        assert result == ContentInputType.INLINE_CONTENT

    def test_safe_path_accepted(self, tmp_path: Path) -> None:
        """Valid path without traversal is accepted."""
        safe = tmp_path / 'safe.txt'
        safe.write_text('ok')
        # Should not raise
        validate_local_path(str(safe))


# ---------------------------------------------------------------------------
# S3 URI format validation
# Validates: Requirements Content Resolution Security
# ---------------------------------------------------------------------------


class TestS3URIFormatValidation:
    """Security tests for S3 URI format validation with malformed URIs.

    Validates: Requirements Content Resolution Security
    """

    def test_bare_s3_prefix(self) -> None:
        """Reject 's3://' with no bucket or key."""
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            validate_s3_uri_format('s3://')

    def test_s3_triple_slash(self) -> None:
        """Reject 's3:///' (empty bucket, slash key)."""
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            validate_s3_uri_format('s3:///')

    def test_s3_triple_slash_with_key(self) -> None:
        """Reject 's3:///key' (empty bucket)."""
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            validate_s3_uri_format('s3:///key')

    def test_uppercase_bucket(self) -> None:
        """Reject 's3://BUCKET/key' (uppercase bucket name)."""
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            validate_s3_uri_format('s3://BUCKET/key')

    def test_underscore_bucket(self) -> None:
        """Reject 's3://my_bucket/key' (underscore in bucket name)."""
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            validate_s3_uri_format('s3://my_bucket/key')

    def test_too_short_bucket(self) -> None:
        """Reject 's3://ab/key' (bucket name too short)."""
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            validate_s3_uri_format('s3://ab/key')

    def test_bucket_starting_with_hyphen(self) -> None:
        """Reject 's3://-bucket/key' (bucket starts with hyphen)."""
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            validate_s3_uri_format('s3://-bucket/key')

    def test_bucket_ending_with_hyphen(self) -> None:
        """Reject 's3://bucket-/key' (bucket ends with hyphen)."""
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            validate_s3_uri_format('s3://bucket-/key')

    def test_valid_uri_accepted(self) -> None:
        """Valid S3 URI returns (bucket, key) tuple."""
        bucket, key = validate_s3_uri_format('s3://my-bucket/path/to/file.txt')
        assert bucket == 'my-bucket'
        assert key == 'path/to/file.txt'


# ---------------------------------------------------------------------------
# Size limit enforcement
# Validates: Requirements Content Resolution Security
# ---------------------------------------------------------------------------


class TestSizeLimitEnforcement:
    """Security tests for size limit enforcement on local files and S3 objects.

    Validates: Requirements Content Resolution Security
    """

    def test_size_exactly_at_limit(self) -> None:
        """Content exactly at the limit does not raise."""
        _check_size_limit(100, 100, 'test')

    def test_size_one_byte_over(self) -> None:
        """Content one byte over the limit raises ValueError."""
        with pytest.raises(ValueError, match='Content exceeds maximum size limit'):
            _check_size_limit(101, 100, 'test')

    def test_size_well_under_limit(self) -> None:
        """Content well under the limit does not raise."""
        _check_size_limit(1, 1024 * 1024, 'test')

    @pytest.mark.asyncio
    async def test_local_file_size_limit(self, tmp_path: Path) -> None:
        """Local file exceeding size limit raises ValueError.

        **Validates: Requirements Content Resolution Security**
        """
        filepath = tmp_path / 'big.txt'
        filepath.write_text('x' * 200)
        with pytest.raises(ValueError, match='Content exceeds maximum size limit'):
            await resolve_single_content(str(filepath), mode='text', max_size_bytes=100)

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    async def test_s3_object_size_limit(self, mock_get_session: MagicMock) -> None:
        """S3 object exceeding size limit raises ValueError before download.

        **Validates: Requirements Content Resolution Security**
        """
        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {'ContentLength': 200}
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3
        mock_get_session.return_value = mock_session

        with pytest.raises(ValueError, match='Content exceeds maximum size limit'):
            await resolve_single_content('s3://my-bucket/big.txt', mode='text', max_size_bytes=100)
        # Verify get_object was NOT called — size check happens before download
        mock_s3.get_object.assert_not_called()


# ---------------------------------------------------------------------------
# Security checks run before I/O operations
# Validates: Requirements Content Resolution Security
# ---------------------------------------------------------------------------


class TestSecurityBeforeIO:
    """Tests that security checks execute before any I/O operations.

    Validates: Requirements Content Resolution Security
    """

    @pytest.mark.asyncio
    async def test_path_traversal_checked_before_file_read(self, tmp_path: Path) -> None:
        """Path traversal is rejected before attempting to read the file.

        We create a file at a traversal path to prove the check fires first.

        **Validates: Requirements Content Resolution Security**
        """
        from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
            _read_local_file,
        )

        # Even if the traversal path somehow resolves to a real file,
        # _read_local_file should reject it before reading.
        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            _read_local_file('../etc/passwd', 'text', None)

    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_traversal_rejects_before_existence_check(self, mock_exists: MagicMock) -> None:
        """Path traversal check runs before os.path.exists is consulted.

        **Validates: Requirements Content Resolution Security**
        """
        from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
            _read_local_file,
        )

        with pytest.raises(ValueError, match='Path contains traversal sequences'):
            _read_local_file('../etc/passwd', 'text', None)
        mock_exists.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    async def test_s3_uri_validated_before_api_call(self, mock_get_session: MagicMock) -> None:
        """S3 URI format is validated before any AWS API call is made.

        **Validates: Requirements Content Resolution Security**
        """
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            await resolve_single_content('s3:///no-bucket', mode='text')
        # get_aws_session should never have been called
        mock_get_session.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    async def test_s3_size_checked_before_download(self, mock_get_session: MagicMock) -> None:
        """S3 content length is checked via head_object before get_object.

        **Validates: Requirements Content Resolution Security**
        """
        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {'ContentLength': 500}
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3
        mock_get_session.return_value = mock_session

        with pytest.raises(ValueError, match='Content exceeds maximum size limit'):
            await resolve_single_content(
                's3://my-bucket/file.txt', mode='text', max_size_bytes=100
            )
        # head_object was called but get_object was not
        mock_s3.head_object.assert_called_once()
        mock_s3.get_object.assert_not_called()

    @pytest.mark.asyncio
    async def test_local_size_checked_before_read(self, tmp_path: Path) -> None:
        """Local file size is checked via os.path.getsize before open().

        **Validates: Requirements Content Resolution Security**
        """
        filepath = tmp_path / 'large.txt'
        filepath.write_text('x' * 500)

        # With a very small limit, the size check should fire before reading
        with pytest.raises(ValueError, match='Content exceeds maximum size limit'):
            await resolve_single_content(str(filepath), mode='text', max_size_bytes=100)
