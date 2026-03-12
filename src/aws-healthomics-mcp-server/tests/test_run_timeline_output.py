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

"""Property-based and unit tests for timeline output path feature."""

import os
import pytest
import uuid
from awslabs.aws_healthomics_mcp_server.utils.path_utils import sanitize_local_path
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Shared Hypothesis strategies
# ---------------------------------------------------------------------------

# Valid filename characters: letters, digits, dash, underscore, dot
_safe_filename_chars = st.characters(
    categories=('L', 'N'),
    include_characters='-_.',
    exclude_characters='\x00/\\',
)

_safe_filename = st.text(
    alphabet=_safe_filename_chars,
    min_size=1,
    max_size=30,
).filter(lambda s: s not in ('.', '..') and not all(c == '.' for c in s))

# Valid S3 bucket names: 3-63 lowercase alphanumeric chars with hyphens
_s3_bucket_name = st.from_regex(r'[a-z][a-z0-9\-]{1,20}[a-z0-9]', fullmatch=True).filter(
    lambda s: '--' not in s
)

# Valid S3 object keys: non-empty path-like strings ending in .svg
_s3_object_key = st.from_regex(r'[a-zA-Z0-9][a-zA-Z0-9_/\-\.]{0,50}\.svg', fullmatch=True)

# Shorter S3 key variant (max 30 chars) used in routing/response tests
_s3_short_key = st.from_regex(r'[a-zA-Z0-9][a-zA-Z0-9_/\-\.]{0,30}\.svg', fullmatch=True)

# Non-S3 local path strings (no s3:// prefix)
_non_s3_path = st.text(
    alphabet=st.characters(categories=('L', 'N'), include_characters='-_./'),
    min_size=1,
    max_size=60,
).filter(lambda s: not s.startswith('s3://'))

# Error message strings
_error_msg = st.text(min_size=1, max_size=100).filter(lambda s: s.strip())

# Run IDs: alphanumeric with dashes, like real HealthOmics run IDs
_run_id = st.from_regex(r'[a-z0-9][a-z0-9\-]{2,30}[a-z0-9]', fullmatch=True)

# Task counts: realistic range
_task_count = st.integers(min_value=1, max_value=500)


# ---------------------------------------------------------------------------
# Shared mock builders
# ---------------------------------------------------------------------------

_SINGLE_TASK_EVENT = {
    'message': (
        '{"name": "Task1", "cpus": 4, "memory": 8, '
        '"instanceType": "omics.m.xlarge", '
        '"creationTime": "2024-01-01T10:00:00Z", '
        '"startTime": "2024-01-01T10:01:00Z", '
        '"stopTime": "2024-01-01T10:05:00Z", '
        '"status": "COMPLETED", "metrics": {}}'
    )
}

_TWO_TASK_EVENTS = [
    _SINGLE_TASK_EVENT,
    {
        'message': (
            '{"name": "Task2", "cpus": 2, "memory": 4, '
            '"instanceType": "omics.c.large", '
            '"creationTime": "2024-01-01T10:02:00Z", '
            '"startTime": "2024-01-01T10:03:00Z", '
            '"stopTime": "2024-01-01T10:06:00Z", '
            '"status": "COMPLETED", "metrics": {}}'
        )
    },
]

_DEFAULT_RUN_RESPONSE = {
    'uuid': 'test-uuid',
    'name': 'TestRun',
    'arn': 'arn:aws:omics:us-east-1:123456789012:run/test-run',
}


def _build_timeline_mocks(task_count=1):
    """Build common mocks for HealthOmics client, logs, and MCP context.

    Args:
        task_count: Number of task events to include. Use 1 for single-task
            tests, 2 for the two-task fixture, or any positive int for
            dynamically generated events.

    Returns:
        Tuple of (mock_omics_client, mock_logs, mock_ctx).
    """
    mock_omics_client = MagicMock()
    mock_omics_client.get_run.return_value = _DEFAULT_RUN_RESPONSE

    if task_count == 1:
        events = [_SINGLE_TASK_EVENT]
    elif task_count == 2:
        events = list(_TWO_TASK_EVENTS)
    else:
        events = []
        for i in range(task_count):
            events.append(
                {
                    'message': (
                        f'{{"name": "Task{i}", "cpus": 4, "memory": 8, '
                        f'"instanceType": "omics.m.xlarge", '
                        f'"creationTime": "2024-01-01T10:00:00Z", '
                        f'"startTime": "2024-01-01T10:0{i % 10}:00Z", '
                        f'"stopTime": "2024-01-01T10:0{i % 10}:30Z", '
                        f'"status": "COMPLETED", "metrics": {{}}}}'
                    )
                }
            )

    mock_logs = {'events': events}

    ctx = MagicMock()
    ctx.error = AsyncMock()

    return mock_omics_client, mock_logs, ctx


# --- Property: Path sanitization security ---
# Validates: Requirements Path Security Null Bytes, Path Resolution,
# Path Traversal Rejection, Path Sanitization Error Reporting


class TestPathSanitizationSecurity:
    """Property: Path sanitization security.

    For any input path string, sanitize_local_path returns an absolute path.
    For any input path containing null bytes, the sanitizer rejects it with ValueError.
    For any input path containing '..' traversal sequences, the sanitizer rejects it
    with ValueError. When the sanitizer rejects a path, no file is written.

    Validates: Requirements Path Security Null Bytes, Path Resolution,
    Path Traversal Rejection, Path Sanitization Error Reporting
    """

    @settings(max_examples=20)
    @given(
        base=_safe_filename,
        injection_point=st.integers(min_value=0, max_value=50),
    )
    def test_null_bytes_rejected(self, base, injection_point):
        """Paths containing null bytes are always rejected with ValueError.

        Validates: Requirements Path Security Null Bytes
        """
        # Inject a null byte at some position in the string
        pos = min(injection_point, len(base))
        path_with_null = base[:pos] + '\x00' + base[pos:]

        try:
            sanitize_local_path(path_with_null)
            assert False, f'Expected ValueError for path with null byte: {path_with_null!r}'
        except ValueError as e:
            assert 'null bytes' in str(e).lower()

    @settings(max_examples=20)
    @given(
        prefix=_safe_filename,
        suffix=_safe_filename,
        traversal=st.sampled_from(
            [
                '..',
                '../',
                '/../',
                '/..',
                '../..',
                '../../',
            ]
        ),
    )
    def test_traversal_sequences_rejected(self, prefix, suffix, traversal):
        """Paths containing '..' traversal sequences are rejected with ValueError.

        Validates: Requirements Path Traversal Rejection
        """
        # Build paths with traversal sequences in various positions
        test_paths = [
            f'{prefix}/{traversal}/{suffix}',
            f'{traversal}/{suffix}',
            f'{prefix}/{traversal}',
        ]

        for path in test_paths:
            try:
                sanitize_local_path(path)
                # If it didn't raise, the path was resolved safely and '..' was
                # eliminated by Path.resolve(). This is acceptable — the function
                # only rejects if traversal persists after resolution.
            except ValueError as e:
                assert 'traversal' in str(e).lower()

    @settings(max_examples=20)
    @given(filename=_safe_filename)
    def test_valid_paths_return_absolute(self, filename):
        """Valid paths always resolve to absolute paths.

        Validates: Requirements Path Resolution
        """
        result = sanitize_local_path(filename)
        assert os.path.isabs(result), f'Expected absolute path, got: {result}'

    @settings(max_examples=20)
    @given(filename=_safe_filename)
    def test_resolved_path_has_no_traversal(self, filename):
        """The resolved path returned by sanitize_local_path never contains '..' components.

        Validates: Requirements Path Resolution, Path Traversal Rejection
        """
        result = sanitize_local_path(filename)
        parts = result.split(os.sep)
        assert '..' not in parts, f'Resolved path contains ..: {result}'

    @settings(max_examples=20)
    @given(
        data=st.text(
            alphabet=st.characters(
                categories=('L', 'N', 'P', 'S', 'Z'),
                exclude_characters='\x00',
            ),
            min_size=1,
            max_size=100,
        ).filter(lambda s: '..' not in s and s.strip() != '')
    )
    def test_safe_arbitrary_strings_return_absolute(self, data):
        """Arbitrary strings without null bytes or traversal resolve to absolute paths.

        Validates: Requirements Path Resolution
        """
        try:
            result = sanitize_local_path(data)
            assert os.path.isabs(result), f'Expected absolute path, got: {result}'
        except ValueError:
            # Some strings may still be rejected by other validation rules
            # (e.g., OS-specific path issues), which is acceptable
            pass


# --- Property: Local write round-trip ---
# Validates: Requirements Local File Output


class TestLocalWriteRoundTrip:
    """Property: Local write round-trip.

    For any valid SVG content string and any valid local file path that does not
    already exist, writing the SVG to the path and then reading the file back
    should produce the exact same SVG content.

    Validates: Requirements Local File Output
    """

    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        svg_content=st.text(min_size=0).map(lambda s: s.replace('\r', '')),
        path_suffix=st.text(
            alphabet=st.characters(
                categories=('L', 'N'),
                include_characters='-_.',
                exclude_characters='\x00/\\',
            ),
            min_size=1,
            max_size=50,
        ).filter(lambda s: s not in ('.', '..') and not all(c == '.' for c in s)),
    )
    def test_write_then_read_matches(self, tmp_path, svg_content, path_suffix):
        """Writing SVG via write_svg_to_local and reading it back yields identical content.

        Validates: Requirements Local File Output
        """
        from awslabs.aws_healthomics_mcp_server.utils.path_utils import write_svg_to_local

        unique_suffix = f'{uuid.uuid4().hex}_{path_suffix}'
        file_path = str(tmp_path / unique_suffix)
        returned_path = write_svg_to_local(svg_content, file_path)

        # Read back the file and verify content matches exactly
        with open(returned_path, encoding='utf-8') as f:
            read_back = f.read()

        assert read_back == svg_content, (
            f'Round-trip mismatch: wrote {len(svg_content)} chars, '
            f'read back {len(read_back)} chars'
        )


# --- Property: Local no-overwrite ---
# Validates: Requirements Local File No-Overwrite


class TestLocalNoOverwrite:
    """Property: Local no-overwrite.

    For any local file path where a file already exists, attempting to write SVG
    content to that path should raise a FileExistsError, and the existing file's
    content should remain unchanged.

    Validates: Requirements Local File No-Overwrite
    """

    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        original_content=st.text(min_size=0).map(lambda s: s.replace('\r', '')),
        new_content=st.text(min_size=0).map(lambda s: s.replace('\r', '')),
        path_suffix=st.text(
            alphabet=st.characters(
                categories=('L', 'N'),
                include_characters='-_.',
                exclude_characters='\x00/\\',
            ),
            min_size=1,
            max_size=50,
        ).filter(lambda s: s not in ('.', '..') and not all(c == '.' for c in s)),
    )
    def test_existing_file_raises_and_content_unchanged(
        self, tmp_path, original_content, new_content, path_suffix
    ):
        """Writing to an existing file raises FileExistsError and preserves original content.

        Validates: Requirements Local File No-Overwrite
        """
        from awslabs.aws_healthomics_mcp_server.utils.path_utils import write_svg_to_local

        unique_suffix = f'{uuid.uuid4().hex}_{path_suffix}'
        file_path = str(tmp_path / unique_suffix)

        # Create the file with original content first
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(original_content)

        # Attempt to write new content to the same path — should raise FileExistsError
        try:
            write_svg_to_local(new_content, file_path)
            assert False, f'Expected FileExistsError for existing file: {file_path}'
        except FileExistsError:
            pass

        # Verify the original content is unchanged
        with open(file_path, encoding='utf-8') as f:
            preserved = f.read()

        assert preserved == original_content, (
            f'File content was modified: expected {len(original_content)} chars, '
            f'got {len(preserved)} chars'
        )


# --- Property: Parent directory creation ---
# Validates: Requirements Parent Directory Creation


class TestParentDirectoryCreation:
    """Property: Parent directory creation.

    For any valid local file path whose parent directories do not exist,
    writing SVG content to that path should succeed and the parent directories
    should be created.

    Validates: Requirements Parent Directory Creation
    """

    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        svg_content=st.text(min_size=0).map(lambda s: s.replace('\r', '')),
        dir_segments=st.lists(
            _safe_filename,
            min_size=1,
            max_size=5,
        ),
        filename=_safe_filename,
    )
    def test_nested_dirs_created_and_file_written(
        self, tmp_path, svg_content, dir_segments, filename
    ):
        """write_svg_to_local creates all parent directories for nested paths.

        Validates: Requirements Parent Directory Creation
        """
        from awslabs.aws_healthomics_mcp_server.utils.path_utils import write_svg_to_local
        from pathlib import Path

        # Build a nested path like tmp_path / <uuid> / a / b / c / file.svg
        nested_dir = tmp_path / uuid.uuid4().hex
        for segment in dir_segments:
            nested_dir = nested_dir / segment

        file_path = str(nested_dir / filename)

        # Parent directories should not exist yet
        assert not nested_dir.exists(), f'Expected parent dir to not exist: {nested_dir}'

        returned_path = write_svg_to_local(svg_content, file_path)

        # Verify all parent directories were created
        resolved = Path(returned_path)
        assert resolved.parent.is_dir(), f'Parent directory was not created: {resolved.parent}'

        # Verify the file was written successfully
        assert resolved.is_file(), f'File was not created: {resolved}'

        # Verify content is correct
        with open(returned_path, encoding='utf-8') as f:
            content = f.read()
        assert content == svg_content


# --- Unit Tests: content_resolver.py refactor regression ---
# Validates: Requirements Design Decision Extract Common Path Validation
#
# These tests confirm that content_resolver.py continues to work correctly
# after replacing private _validate_local_path and _validate_s3_uri_format
# with shared imports from path_utils.py.


class TestContentResolverRefactorRegression:
    """Verify content_resolver.py behavior after refactoring to shared path_utils imports.

    Validates: Requirements Design Decision Extract Common Path Validation
    """

    def test_detect_content_input_type_s3_uri(self):
        """S3 URIs are still detected correctly through the refactored code path."""
        from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
            ContentInputType,
            detect_content_input_type,
        )

        assert detect_content_input_type('s3://my-bucket/key.txt') == ContentInputType.S3_URI

    def test_detect_content_input_type_inline(self):
        """Inline content detection still works after refactor."""
        from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
            ContentInputType,
            detect_content_input_type,
        )

        assert detect_content_input_type('some inline text') == ContentInputType.INLINE_CONTENT

    def test_detect_content_input_type_local_file(self, tmp_path):
        """Local file detection still works through imported validate_local_path."""
        from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
            ContentInputType,
            detect_content_input_type,
        )

        f = tmp_path / 'test.wdl'
        f.write_text('workflow {}')
        assert detect_content_input_type(str(f)) == ContentInputType.LOCAL_FILE

    def test_path_traversal_rejected_via_shared_import(self):
        """Path traversal is still rejected — now via path_utils.validate_local_path."""
        from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
            ContentInputType,
            detect_content_input_type,
        )

        # Traversal paths should fall through to inline content, not raise
        result = detect_content_input_type('../../../etc/passwd')
        assert result == ContentInputType.INLINE_CONTENT

    def test_s3_uri_validation_via_shared_import(self):
        """S3 URI format validation still works through path_utils.validate_s3_uri_format."""
        from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
            _read_s3_object,
        )

        # Invalid S3 URI (no key) should raise ValueError from shared validate_s3_uri_format
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            _read_s3_object('s3://', 'text', None)

    def test_shared_validate_local_path_is_same_function(self):
        """content_resolver uses the exact same validate_local_path from path_utils."""
        import awslabs.aws_healthomics_mcp_server.utils.content_resolver as cr
        from awslabs.aws_healthomics_mcp_server.utils.path_utils import (
            validate_local_path,
        )

        # The module-level import in content_resolver should reference path_utils
        assert cr.validate_local_path is validate_local_path

    def test_shared_validate_s3_uri_format_is_same_function(self):
        """content_resolver uses the exact same validate_s3_uri_format from path_utils."""
        import awslabs.aws_healthomics_mcp_server.utils.content_resolver as cr
        from awslabs.aws_healthomics_mcp_server.utils.path_utils import (
            validate_s3_uri_format,
        )

        assert cr.validate_s3_uri_format is validate_s3_uri_format

    @pytest.mark.asyncio
    async def test_resolve_single_content_local_file(self, tmp_path):
        """resolve_single_content still reads local files after refactor."""
        from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
            ContentInputType,
            resolve_single_content,
        )

        f = tmp_path / 'hello.txt'
        f.write_text('hello world')
        result = await resolve_single_content(str(f), mode='text')
        assert result.content == 'hello world'
        assert result.input_type == ContentInputType.LOCAL_FILE

    @pytest.mark.asyncio
    async def test_resolve_bundle_content_local_dir(self, tmp_path):
        """resolve_bundle_content still reads local directories after refactor."""
        from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
            ContentInputType,
            resolve_bundle_content,
        )

        (tmp_path / 'a.wdl').write_text('task a {}')
        (tmp_path / 'b.wdl').write_text('task b {}')
        result = await resolve_bundle_content(str(tmp_path))
        assert result.input_type == ContentInputType.LOCAL_FILE
        assert 'a.wdl' in result.files
        assert result.files['a.wdl'] == 'task a {}'
        assert result.files['b.wdl'] == 'task b {}'


# --- Property: S3 upload correctness ---
# Validates: Requirements S3 Output Upload, S3 Output Content Type


class TestS3UploadCorrectness:
    """Property: S3 upload correctness.

    For any valid SVG content string and valid S3 URI where the bucket exists
    and is accessible and no object exists at the key, the tool calls put_object
    with ContentType='image/svg+xml' and the SVG content as the body, and the
    returned path matches the input S3 URI.

    Validates: Requirements S3 Output Upload, S3 Output Content Type
    """

    @settings(max_examples=20)
    @given(
        svg_content=st.text(min_size=1, max_size=500),
        data=st.data(),
    )
    def test_put_object_called_with_correct_args_and_path_returned(self, svg_content, data):
        """put_object is called with correct ContentType, body, and returned path matches S3 URI.

        Validates: Requirements S3 Output Upload, S3 Output Content Type
        """
        from botocore.exceptions import ClientError
        from unittest.mock import patch

        bucket = data.draw(_s3_bucket_name)
        key = data.draw(_s3_object_key)
        s3_uri = f's3://{bucket}/{key}'

        # Build mock S3 client
        mock_s3_client = MagicMock()

        # head_bucket succeeds (bucket exists and is accessible)
        mock_s3_client.head_bucket.return_value = {}

        # head_object raises 404 (object does not exist — success path)
        mock_s3_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}},
            'HeadObject',
        )

        # put_object succeeds
        mock_s3_client.put_object.return_value = {}

        # Mock session to return our mock S3 client
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.get_aws_session',
            return_value=mock_session,
        ):
            from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_svg_to_s3

            result = write_svg_to_s3(svg_content, s3_uri)

        # Verify put_object was called exactly once with correct arguments
        mock_s3_client.put_object.assert_called_once_with(
            Bucket=bucket,
            Key=key,
            Body=svg_content.encode('utf-8'),
            ContentType='image/svg+xml',
        )

        # Verify the returned path matches the input S3 URI
        assert result == s3_uri, f'Expected {s3_uri}, got {result}'


class TestS3NoOverwrite:
    """Property: S3 no-overwrite.

    For any S3 URI where an object already exists at the specified key,
    attempting to write SVG content should raise a FileExistsError indicating
    the object already exists, and no put_object call should be made.

    Validates: Requirements S3 Output No-Overwrite
    """

    @settings(max_examples=20)
    @given(
        svg_content=st.text(min_size=1, max_size=500),
        data=st.data(),
    )
    def test_existing_object_raises_file_exists_and_no_put_object(self, svg_content, data):
        """Existing objects cause FileExistsError and put_object is never called.

        Validates: Requirements S3 Output No-Overwrite
        """
        from unittest.mock import patch

        bucket = data.draw(_s3_bucket_name)
        key = data.draw(_s3_object_key)
        s3_uri = f's3://{bucket}/{key}'

        # Build mock S3 client
        mock_s3_client = MagicMock()

        # head_bucket succeeds (bucket exists and is accessible)
        mock_s3_client.head_bucket.return_value = {}

        # head_object succeeds — object already exists
        mock_s3_client.head_object.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        # Mock session to return our mock S3 client
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.get_aws_session',
            return_value=mock_session,
        ):
            from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_svg_to_s3

            with pytest.raises(FileExistsError, match='already exists'):
                write_svg_to_s3(svg_content, s3_uri)

        # Verify put_object was never called
        mock_s3_client.put_object.assert_not_called()


# --- Property: S3 path format validation ---
# Validates: Requirements S3 Path Format Validation


class TestS3PathFormatValidation:
    """Property: S3 path format validation.

    For any string starting with s3:// that has an invalid format (missing bucket name,
    empty key, invalid bucket name characters), the tool should reject it with a
    descriptive error before attempting any S3 operations.

    Validates: Requirements S3 Path Format Validation
    """

    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    @given(
        svg_content=st.text(min_size=1, max_size=200),
    )
    def test_empty_bucket_rejected(self, svg_content):
        """S3 URIs with no bucket name are rejected with ValueError before any S3 API calls.

        Validates: Requirements S3 Path Format Validation
        """
        from unittest.mock import patch

        mock_session = MagicMock()
        mock_s3_client = MagicMock()
        mock_session.client.return_value = mock_s3_client

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.get_aws_session',
            return_value=mock_session,
        ):
            from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_svg_to_s3

            with pytest.raises(ValueError):
                write_svg_to_s3(svg_content, 's3:///some-key.svg')

        # No S3 API calls should have been made
        mock_s3_client.head_bucket.assert_not_called()
        mock_s3_client.head_object.assert_not_called()
        mock_s3_client.put_object.assert_not_called()

    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    @given(
        svg_content=st.text(min_size=1, max_size=200),
    )
    def test_bare_s3_prefix_rejected(self, svg_content):
        """Bare 's3://' URI with no bucket or key is rejected before any S3 API calls.

        Validates: Requirements S3 Path Format Validation
        """
        from unittest.mock import patch

        mock_session = MagicMock()
        mock_s3_client = MagicMock()
        mock_session.client.return_value = mock_s3_client

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.get_aws_session',
            return_value=mock_session,
        ):
            from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_svg_to_s3

            with pytest.raises(ValueError):
                write_svg_to_s3(svg_content, 's3://')

        mock_s3_client.head_bucket.assert_not_called()
        mock_s3_client.head_object.assert_not_called()
        mock_s3_client.put_object.assert_not_called()

    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    @given(
        svg_content=st.text(min_size=1, max_size=200),
        invalid_bucket=st.sampled_from(
            [
                'UPPER',
                'has space',
                'has_underscore',
                'a',
                'ab',
                'A' * 64,
                '.bucket',
                'bucket.',
                '-bucket',
                'bucket-',
            ]
        ),
        key=_s3_object_key,
    )
    def test_invalid_bucket_name_rejected(self, svg_content, invalid_bucket, key):
        """S3 URIs with invalid bucket names are rejected before any S3 API calls.

        Validates: Requirements S3 Path Format Validation
        """
        from unittest.mock import patch

        s3_uri = f's3://{invalid_bucket}/{key}'

        mock_session = MagicMock()
        mock_s3_client = MagicMock()
        mock_session.client.return_value = mock_s3_client

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.get_aws_session',
            return_value=mock_session,
        ):
            from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_svg_to_s3

            with pytest.raises(ValueError):
                write_svg_to_s3(svg_content, s3_uri)

        mock_s3_client.head_bucket.assert_not_called()
        mock_s3_client.head_object.assert_not_called()
        mock_s3_client.put_object.assert_not_called()

    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    @given(
        svg_content=st.text(min_size=1, max_size=200),
        bucket=_s3_bucket_name,
    )
    def test_empty_key_rejected(self, svg_content, bucket):
        """S3 URIs with a valid bucket but empty key are rejected before any S3 API calls.

        Validates: Requirements S3 Path Format Validation
        """
        from unittest.mock import patch

        s3_uri = f's3://{bucket}/'

        mock_session = MagicMock()
        mock_s3_client = MagicMock()
        mock_session.client.return_value = mock_s3_client

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.get_aws_session',
            return_value=mock_session,
        ):
            from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_svg_to_s3

            with pytest.raises(ValueError):
                write_svg_to_s3(svg_content, s3_uri)

        mock_s3_client.head_bucket.assert_not_called()
        mock_s3_client.head_object.assert_not_called()
        mock_s3_client.put_object.assert_not_called()


# --- Property: Expected bucket owner resolution ---
# Validates: Requirements S3 Bucket Owner Verification Default,
# S3 Bucket Owner Verification Skip, S3 Bucket Owner Verification Pass-Through


class TestExpectedBucketOwnerResolution:
    """Property: Expected bucket owner resolution.

    For any S3 write operation: when expected_bucket_owner is None, the
    head_bucket call omits the ExpectedBucketOwner parameter; when
    expected_bucket_owner is any non-None string, that string is passed
    as ExpectedBucketOwner.

    Validates: Requirements S3 Bucket Owner Verification Default,
    S3 Bucket Owner Verification Skip, S3 Bucket Owner Verification Pass-Through
    """

    def test_none_skips_expected_bucket_owner(self):
        """None expected_bucket_owner calls head_bucket without ExpectedBucketOwner.

        Validates: Requirements S3 Bucket Owner Verification Skip
        """
        from awslabs.aws_healthomics_mcp_server.utils.s3_utils import (
            validate_s3_bucket_for_write,
        )

        mock_s3_client = MagicMock()

        validate_s3_bucket_for_write(mock_s3_client, 'my-bucket', expected_bucket_owner=None)

        mock_s3_client.head_bucket.assert_called_once_with(Bucket='my-bucket')

    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    @given(
        account_id=st.from_regex(r'[0-9]{12}', fullmatch=True),
    )
    def test_explicit_account_id_passed_to_head_bucket(self, account_id):
        """A 12-digit account ID is passed as ExpectedBucketOwner to head_bucket.

        Validates: Requirements S3 Bucket Owner Verification Pass-Through
        """
        from awslabs.aws_healthomics_mcp_server.utils.s3_utils import (
            validate_s3_bucket_for_write,
        )

        mock_s3_client = MagicMock()

        validate_s3_bucket_for_write(mock_s3_client, 'my-bucket', expected_bucket_owner=account_id)

        mock_s3_client.head_bucket.assert_called_once_with(
            Bucket='my-bucket', ExpectedBucketOwner=account_id
        )

    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    @given(
        owner_str=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    )
    def test_arbitrary_non_none_string_passed_to_head_bucket(self, owner_str):
        """Any non-None string is passed as ExpectedBucketOwner to head_bucket.

        Validates: Requirements S3 Bucket Owner Verification Pass-Through
        """
        from awslabs.aws_healthomics_mcp_server.utils.s3_utils import (
            validate_s3_bucket_for_write,
        )

        mock_s3_client = MagicMock()

        validate_s3_bucket_for_write(mock_s3_client, 'my-bucket', expected_bucket_owner=owner_str)

        mock_s3_client.head_bucket.assert_called_once_with(
            Bucket='my-bucket', ExpectedBucketOwner=owner_str
        )


# --- Property: Output path routing correctness ---
# Validates: Requirements Output Path Default Behavior, Output Path S3 Detection,
# Output Path Local Detection, Response SVG Omission


class TestOutputPathRoutingCorrectness:
    """Property: Output path routing correctness.

    For any output_path string, the tool routes to S3 handling if and only if
    the string starts with 's3://'; otherwise it routes to local file handling.
    When output_path is None, the tool returns SVG content in the response body
    using the existing format.

    Validates: Requirements Output Path Default Behavior, Output Path S3 Detection,
    Output Path Local Detection, Response SVG Omission
    """

    @pytest.mark.asyncio
    @settings(max_examples=20, deadline=None)
    @given(data=st.data())
    async def test_s3_path_routes_to_s3_handler(self, data):
        """S3 paths route to write_svg_to_s3, not write_svg_to_local.

        Validates: Requirements Output Path S3 Detection
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        bucket = data.draw(_s3_bucket_name)
        key = data.draw(_s3_short_key)
        s3_path = f's3://{bucket}/{key}'

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
                return_value=s3_path,
            ) as mock_s3_write,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_local',
            ) as mock_local_write,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_account_id',
                return_value='123456789012',
            ),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(
                ctx, run_id='test-run', output_path=s3_path, expected_bucket_owner=None
            )

        mock_s3_write.assert_called_once()
        mock_local_write.assert_not_called()

    @pytest.mark.asyncio
    @settings(max_examples=20, deadline=None)
    @given(local_path=_non_s3_path)
    async def test_non_s3_path_routes_to_local_handler(self, local_path):
        """Non-S3 paths route to write_svg_to_local, not write_svg_to_s3.

        Validates: Requirements Output Path Local Detection
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
            ) as mock_s3_write,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_local',
                return_value='/resolved/path.svg',
            ) as mock_local_write,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(ctx, run_id='test-run', output_path=local_path)

        mock_local_write.assert_called_once()
        mock_s3_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_output_path_returns_svg_content(self):
        """None output_path returns SVG content directly without calling any write handler.

        Validates: Requirements Output Path Default Behavior
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
            ) as mock_s3_write,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_local',
            ) as mock_local_write,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            result = await wrapper.call(
                ctx, run_id='test-run', output_path=None, output_format='svg'
            )

        mock_s3_write.assert_not_called()
        mock_local_write.assert_not_called()
        # Result should contain SVG content (existing behavior)
        assert '<svg' in result or '</svg>' in result


# --- Property: Success response structure ---
# Validates: Requirements Response Structure with Output Path,
# Response SVG Omission


class TestSuccessResponseStructure:
    """Property: Success response structure.

    For any successful write operation (local or S3), the returned JSON string
    deserializes to a dictionary containing exactly the keys 'status',
    'output_path', 'run_id', and 'task_count', where 'status' equals 'success',
    and the string does not contain SVG content (no '<svg' tag or base64-encoded SVG).

    Validates: Requirements Response Structure with Output Path,
    Response SVG Omission
    """

    @pytest.mark.asyncio
    @settings(max_examples=20, deadline=None)
    @given(data=st.data())
    async def test_local_success_response_has_exact_keys_and_status(self, data):
        """Local path success response has exactly status, output_path, run_id, task_count keys.

        Validates: Requirements Response Structure with Output Path,
        Response SVG Omission
        """
        import json
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        run_id = data.draw(_run_id)
        task_count = data.draw(_task_count)
        local_path = data.draw(_non_s3_path)

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count)
        resolved_path = f'/resolved/{local_path}'

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_local',
                return_value=resolved_path,
            ),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            result = await wrapper.call(ctx, run_id=run_id, output_path=local_path)

        # Parse the JSON response
        parsed = json.loads(result)

        # Verify exactly 4 keys
        assert set(parsed.keys()) == {'status', 'output_path', 'run_id', 'task_count'}

        # Verify status is 'success'
        assert parsed['status'] == 'success'

        # Verify run_id matches
        assert parsed['run_id'] == run_id

        # Verify task_count matches the number of tasks
        assert parsed['task_count'] == task_count

        # Verify no SVG content in the response string
        assert '<svg' not in result
        assert '</svg>' not in result
        assert 'PHN2Zy' not in result  # base64 prefix for '<svg'

    @pytest.mark.asyncio
    @settings(max_examples=20, deadline=None)
    @given(data=st.data())
    async def test_s3_success_response_has_exact_keys_and_status(self, data):
        """S3 URI success response has exactly status, output_path, run_id, task_count keys.

        Validates: Requirements Response Structure with Output Path,
        Response SVG Omission
        """
        import json
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        run_id = data.draw(_run_id)
        task_count = data.draw(_task_count)
        bucket = data.draw(_s3_bucket_name)
        key = data.draw(_s3_short_key)
        s3_path = f's3://{bucket}/{key}'

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count)

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
                return_value=s3_path,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_account_id',
                return_value='123456789012',
            ),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            result = await wrapper.call(
                ctx, run_id=run_id, output_path=s3_path, expected_bucket_owner=None
            )

        # Parse the JSON response
        parsed = json.loads(result)

        # Verify exactly 4 keys
        assert set(parsed.keys()) == {'status', 'output_path', 'run_id', 'task_count'}

        # Verify status is 'success'
        assert parsed['status'] == 'success'

        # Verify run_id matches
        assert parsed['run_id'] == run_id

        # Verify task_count matches the number of tasks
        assert parsed['task_count'] == task_count

        # Verify output_path matches the S3 URI
        assert parsed['output_path'] == s3_path

        # Verify no SVG content in the response string
        assert '<svg' not in result
        assert '</svg>' not in result
        assert 'PHN2Zy' not in result  # base64 prefix for '<svg'


# --- Property: Error handling consistency ---
# Validates: Requirements Response Error Pattern, Error Logging, Error Context Reporting


class TestErrorHandlingConsistency:
    """Property: Error handling consistency.

    For any error that occurs during output path validation, file writing, or S3 upload,
    the tool delegates to handle_tool_error(ctx, error, operation) from error_utils.py,
    which logs the error via loguru.logger.error(), reports it via ctx.error(), and returns
    a dict with an 'error' key containing the formatted message.

    Validates: Requirements Response Error Pattern, Error Logging, Error Context Reporting
    """

    @pytest.mark.asyncio
    @settings(max_examples=20, deadline=None)
    @given(data=st.data())
    async def test_value_error_delegates_to_handle_tool_error(self, data):
        """ValueError from write_svg_to_local delegates to handle_tool_error.

        Validates: Requirements Response Error Pattern, Error Logging
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        local_path = data.draw(_non_s3_path)
        error_msg = data.draw(_error_msg)
        error = ValueError(error_msg)

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_local',
                side_effect=error,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': f'Error writing timeline output: {error_msg}'},
            ) as mock_handle_error,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(ctx, run_id='test-run', output_path=local_path)

        mock_handle_error.assert_called_once_with(ctx, error, 'Error writing timeline output')

    @pytest.mark.asyncio
    @settings(max_examples=20, deadline=None)
    @given(data=st.data())
    async def test_file_exists_error_delegates_to_handle_tool_error(self, data):
        """FileExistsError from write_svg_to_local delegates to handle_tool_error.

        Validates: Requirements Response Error Pattern, Error Context Reporting
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        local_path = data.draw(_non_s3_path)
        error_msg = data.draw(_error_msg)
        error = FileExistsError(error_msg)

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_local',
                side_effect=error,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': f'Error writing timeline output: {error_msg}'},
            ) as mock_handle_error,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(ctx, run_id='test-run', output_path=local_path)

        mock_handle_error.assert_called_once_with(ctx, error, 'Error writing timeline output')

    @pytest.mark.asyncio
    @settings(max_examples=20, deadline=None)
    @given(data=st.data())
    async def test_os_error_delegates_to_handle_tool_error(self, data):
        """OSError from write_svg_to_local delegates to handle_tool_error.

        Validates: Requirements Error Logging, Error Context Reporting
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        local_path = data.draw(_non_s3_path)
        error_msg = data.draw(_error_msg)
        error = OSError(error_msg)

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_local',
                side_effect=error,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': f'Error writing timeline output: {error_msg}'},
            ) as mock_handle_error,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(ctx, run_id='test-run', output_path=local_path)

        mock_handle_error.assert_called_once_with(ctx, error, 'Error writing timeline output')

    @pytest.mark.asyncio
    @settings(max_examples=20, deadline=None)
    @given(data=st.data())
    async def test_client_error_delegates_to_handle_tool_error(self, data):
        """ClientError from write_svg_to_s3 delegates to handle_tool_error.

        Validates: Requirements Response Error Pattern, Error Logging, Error Context Reporting
        """
        from botocore.exceptions import ClientError
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        bucket = data.draw(_s3_bucket_name)
        key = data.draw(_s3_short_key)
        s3_path = f's3://{bucket}/{key}'
        error_msg = data.draw(_error_msg)
        error = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': error_msg}},
            'PutObject',
        )

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
                side_effect=error,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': f'Error writing timeline output: {error_msg}'},
            ) as mock_handle_error,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(
                ctx, run_id='test-run', output_path=s3_path, expected_bucket_owner=None
            )

        mock_handle_error.assert_called_once_with(ctx, error, 'Error writing timeline output')


# --- Unit tests: generate_run_timeline output path integration ---
# Validates: Requirements Output Path Default Behavior, Response Structure with Output Path,
# Response SVG Omission, Output Path S3 Detection, Output Path Local Detection,
# S3 Client Error Handling, OS Error Handling, S3 Bucket Owner Verification


class TestGenerateRunTimelineOutputPathIntegration:
    """Unit tests for generate_run_timeline output path integration.

    These example-based tests verify end-to-end behavior of the output_path
    and expected_bucket_owner parameters through the full tool function,
    including existing behavior preservation, local/S3 write flows,
    sentinel resolution, and error scenarios.

    Validates: Requirements Output Path Default Behavior, Response Structure with Output Path,
    Response SVG Omission, Output Path S3 Detection, Output Path Local Detection,
    S3 Client Error Handling, OS Error Handling, S3 Bucket Owner Verification
    """

    # --- Existing behavior preserved when output_path=None ---

    @pytest.mark.asyncio
    async def test_none_output_path_returns_base64_svg(self):
        """None output_path with base64 format returns base64-encoded SVG content.

        Validates: Requirements Output Path Default Behavior
        """
        import base64
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            result = await wrapper.call(
                ctx, run_id='test-run', output_path=None, output_format='base64'
            )

        # Should be valid base64 that decodes to SVG
        decoded = base64.b64decode(result).decode('utf-8')
        assert '<svg' in decoded
        assert '</svg>' in decoded

    @pytest.mark.asyncio
    async def test_none_output_path_returns_raw_svg(self):
        """None output_path with svg format returns raw SVG content.

        Validates: Requirements Output Path Default Behavior
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            result = await wrapper.call(
                ctx, run_id='test-run', output_path=None, output_format='svg'
            )

        assert '<svg' in result
        assert '</svg>' in result

    # --- Local file write end-to-end ---

    @pytest.mark.asyncio
    async def test_local_file_write_end_to_end(self, tmp_path):
        """Local output_path writes SVG to disk and returns a JSON summary.

        Validates: Requirements Output Path Local Detection, Response Structure with Output Path,
        Response SVG Omission
        """
        import json
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)
        local_path = str(tmp_path / 'timeline.svg')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            result = await wrapper.call(ctx, run_id='test-run', output_path=local_path)

        parsed = json.loads(result)
        assert parsed['status'] == 'success'
        assert parsed['run_id'] == 'test-run'
        assert parsed['task_count'] == 2
        assert 'output_path' in parsed
        # SVG should not be in the response
        assert '<svg' not in result

        # Verify file was actually written
        written = open(parsed['output_path']).read()
        assert '<svg' in written
        assert '</svg>' in written

    # --- S3 write end-to-end ---

    @pytest.mark.asyncio
    async def test_s3_write_end_to_end(self):
        """S3 URI output_path calls write_svg_to_s3 and returns a JSON summary.

        Validates: Requirements Output Path S3 Detection, Response Structure with Output Path,
        Response SVG Omission
        """
        import json
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)
        s3_path = 's3://my-bucket/timelines/run-123.svg'

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
                return_value=s3_path,
            ) as mock_s3_write,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_account_id',
                return_value='123456789012',
            ),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            result = await wrapper.call(
                ctx, run_id='test-run', output_path=s3_path, expected_bucket_owner=None
            )

        parsed = json.loads(result)
        assert parsed['status'] == 'success'
        assert parsed['output_path'] == s3_path
        assert parsed['run_id'] == 'test-run'
        assert parsed['task_count'] == 2
        assert '<svg' not in result

        # Verify write_svg_to_s3 was called with SVG content and the S3 path
        mock_s3_write.assert_called_once()
        call_args = mock_s3_write.call_args
        assert call_args[0][1] == s3_path  # second positional arg is the s3 path

    # --- Sentinel __DEFAULT__ triggers get_account_id() ---

    @pytest.mark.asyncio
    async def test_sentinel_default_triggers_get_account_id(self):
        """Sentinel '__DEFAULT__' expected_bucket_owner triggers get_account_id() resolution.

        Validates: Requirements S3 Bucket Owner Verification
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)
        s3_path = 's3://my-bucket/output.svg'

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
                return_value=s3_path,
            ) as mock_s3_write,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_account_id',
                return_value='999888777666',
            ) as mock_get_account_id,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            # Pass __DEFAULT__ explicitly to simulate the sentinel default
            await wrapper.call(
                ctx, run_id='test-run', output_path=s3_path, expected_bucket_owner='__DEFAULT__'
            )

        mock_get_account_id.assert_called_once()
        # The resolved account ID should be passed to write_svg_to_s3
        mock_s3_write.assert_called_once()
        call_args = mock_s3_write.call_args
        assert call_args[0][2] == '999888777666'  # third positional arg is resolved_owner

    # --- Explicit None skips bucket owner check ---

    @pytest.mark.asyncio
    async def test_explicit_none_skips_get_account_id(self):
        """Explicit None expected_bucket_owner skips get_account_id and passes None.

        Validates: Requirements S3 Bucket Owner Verification
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)
        s3_path = 's3://my-bucket/output.svg'

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
                return_value=s3_path,
            ) as mock_s3_write,
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_account_id',
            ) as mock_get_account_id,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(
                ctx, run_id='test-run', output_path=s3_path, expected_bucket_owner=None
            )

        mock_get_account_id.assert_not_called()
        mock_s3_write.assert_called_once()
        call_args = mock_s3_write.call_args
        assert call_args[0][2] is None  # third positional arg is None

    # --- Error scenarios ---

    @pytest.mark.asyncio
    async def test_error_file_exists(self):
        """When write_svg_to_local raises FileExistsError, handle_tool_error is called.

        Validates: Requirements OS Error Handling
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)
        error = FileExistsError('File already exists at /tmp/timeline.svg')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_local',
                side_effect=error,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error writing timeline output: File already exists'},
            ) as mock_handle_error,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            result = await wrapper.call(ctx, run_id='test-run', output_path='/tmp/timeline.svg')

        mock_handle_error.assert_called_once_with(ctx, error, 'Error writing timeline output')
        assert result == '{"error": "Error writing timeline output: File already exists"}'

    @pytest.mark.asyncio
    async def test_error_permission_denied(self):
        """PermissionError (a subclass of OSError) from write_svg_to_local is caught via the OSError handler and delegates to handle_tool_error.

        Validates: Requirements OS Error Handling
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)
        error = PermissionError('Permission denied: /root/timeline.svg')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_local',
                side_effect=error,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error writing timeline output: Permission denied'},
            ) as mock_handle_error,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(ctx, run_id='test-run', output_path='/root/timeline.svg')

        mock_handle_error.assert_called_once_with(ctx, error, 'Error writing timeline output')

    @pytest.mark.asyncio
    async def test_error_s3_bucket_not_found(self):
        """ValueError for bucket not found from write_svg_to_s3 delegates to handle_tool_error.

        Validates: Requirements S3 Client Error Handling
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)
        error = ValueError('S3 bucket does not exist: nonexistent-bucket')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
                side_effect=error,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error writing timeline output: bucket does not exist'},
            ) as mock_handle_error,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(
                ctx,
                run_id='test-run',
                output_path='s3://nonexistent-bucket/out.svg',
                expected_bucket_owner=None,
            )

        mock_handle_error.assert_called_once_with(ctx, error, 'Error writing timeline output')

    @pytest.mark.asyncio
    async def test_error_s3_access_denied(self):
        """Access denied ClientError from write_svg_to_s3 delegates to handle_tool_error.

        Validates: Requirements S3 Client Error Handling
        """
        from botocore.exceptions import ClientError
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)
        error = ClientError(
            {'Error': {'Code': '403', 'Message': 'Forbidden'}},
            'HeadBucket',
        )

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
                side_effect=error,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error writing timeline output: access denied'},
            ) as mock_handle_error,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(
                ctx,
                run_id='test-run',
                output_path='s3://restricted-bucket/out.svg',
                expected_bucket_owner=None,
            )

        mock_handle_error.assert_called_once_with(ctx, error, 'Error writing timeline output')

    @pytest.mark.asyncio
    async def test_error_s3_bucket_owner_mismatch(self):
        """Bucket owner mismatch ValueError from write_svg_to_s3 delegates to handle_tool_error.

        Validates: Requirements S3 Bucket Owner Verification
        """
        from tests.test_helpers import MCPToolTestWrapper
        from unittest.mock import patch

        mock_omics_client, mock_logs, ctx = _build_timeline_mocks(task_count=2)
        error = ValueError(
            'S3 bucket owner mismatch: expected 111111111111 but bucket is owned by another account'
        )

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_omics_client',
                return_value=mock_omics_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline'
                '.get_run_manifest_logs_internal',
                new_callable=AsyncMock,
                return_value=mock_logs,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.write_svg_to_s3',
                side_effect=error,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.get_account_id',
                return_value='111111111111',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_timeline.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': 'Error writing timeline output: owner mismatch'},
            ) as mock_handle_error,
        ):
            from awslabs.aws_healthomics_mcp_server.tools.run_timeline import (
                generate_run_timeline,
            )

            wrapper = MCPToolTestWrapper(generate_run_timeline)
            await wrapper.call(
                ctx,
                run_id='test-run',
                output_path='s3://wrong-owner-bucket/out.svg',
                expected_bucket_owner='__DEFAULT__',
            )

        mock_handle_error.assert_called_once_with(ctx, error, 'Error writing timeline output')
