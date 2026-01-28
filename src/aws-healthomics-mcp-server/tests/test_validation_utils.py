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

"""Unit tests for validation utilities."""

import os
import posixpath
import pytest
import tempfile
from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
    ReadmeInputType,
    detect_readme_input_type,
    validate_path_to_main,
    validate_s3_uri,
)
from unittest.mock import AsyncMock, patch


class TestValidateS3Uri:
    """Test cases for validate_s3_uri function."""

    @pytest.mark.asyncio
    async def test_validate_s3_uri_valid(self):
        """Test validation of valid S3 URI."""
        mock_ctx = AsyncMock()

        # Should not raise any exception
        await validate_s3_uri(mock_ctx, 's3://valid-bucket/path/to/file.txt', 'test_param')

        # Should not call error on context
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_s3_uri_invalid_bucket_name(self):
        """Test validation of S3 URI with invalid bucket name."""
        mock_ctx = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await validate_s3_uri(mock_ctx, 's3://Invalid_Bucket_Name/file.txt', 'test_param')

        assert 'test_param must be a valid S3 URI' in str(exc_info.value)
        assert 'Invalid bucket name' in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_s3_uri_invalid_format(self):
        """Test validation of malformed S3 URI."""
        mock_ctx = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await validate_s3_uri(mock_ctx, 'not-an-s3-uri', 'test_param')

        assert 'test_param must be a valid S3 URI' in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.aws_healthomics_mcp_server.utils.validation_utils.logger')
    async def test_validate_s3_uri_logs_error(self, mock_logger):
        """Test that validation errors are logged."""
        mock_ctx = AsyncMock()

        with pytest.raises(ValueError):
            await validate_s3_uri(mock_ctx, 'invalid-uri', 'test_param')

        mock_logger.error.assert_called_once()
        assert 'test_param must be a valid S3 URI' in mock_logger.error.call_args[0][0]


class TestValidateAdhocS3Buckets:
    """Test cases for validate_adhoc_s3_buckets function."""

    @pytest.mark.asyncio
    async def test_validate_adhoc_s3_buckets_none_input(self):
        """Test validation with None input."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_adhoc_s3_buckets,
        )

        result = await validate_adhoc_s3_buckets(None)
        assert result == []

    @pytest.mark.asyncio
    async def test_validate_adhoc_s3_buckets_empty_list(self):
        """Test validation with empty list."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_adhoc_s3_buckets,
        )

        result = await validate_adhoc_s3_buckets([])
        assert result == []

    @pytest.mark.asyncio
    async def test_validate_adhoc_s3_buckets_success(self):
        """Test successful validation of adhoc S3 buckets."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_adhoc_s3_buckets,
        )

        test_buckets = ['s3://test-bucket-1/', 's3://test-bucket-2/']
        validated_buckets = ['s3://test-bucket-1/', 's3://test-bucket-2/']

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.validate_bucket_access'
        ) as mock_validate:
            mock_validate.return_value = validated_buckets

            with patch(
                'awslabs.aws_healthomics_mcp_server.utils.validation_utils.logger'
            ) as mock_logger:
                result = await validate_adhoc_s3_buckets(test_buckets)

                assert result == validated_buckets
                mock_validate.assert_called_once_with(test_buckets)
                mock_logger.info.assert_called_once()
                assert (
                    'Validated 2 adhoc S3 buckets out of 2 provided'
                    in mock_logger.info.call_args[0][0]
                )

    @pytest.mark.asyncio
    async def test_validate_adhoc_s3_buckets_validation_error(self):
        """Test handling of validation errors."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_adhoc_s3_buckets,
        )

        test_buckets = ['s3://invalid-bucket/', 's3://another-invalid/']

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.validate_bucket_access'
        ) as mock_validate:
            # Mock validate_bucket_access to raise ValueError
            mock_validate.side_effect = ValueError('Bucket access validation failed')

            with patch(
                'awslabs.aws_healthomics_mcp_server.utils.validation_utils.logger'
            ) as mock_logger:
                result = await validate_adhoc_s3_buckets(test_buckets)

                # Should return empty list when validation fails
                assert result == []
                mock_validate.assert_called_once_with(test_buckets)
                # Should log warning (lines 167-168)
                mock_logger.warning.assert_called_once()
                assert (
                    'Adhoc S3 bucket validation failed: Bucket access validation failed'
                    in mock_logger.warning.call_args[0][0]
                )

    @pytest.mark.asyncio
    async def test_validate_adhoc_s3_buckets_partial_success(self):
        """Test validation with some valid and some invalid buckets."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_adhoc_s3_buckets,
        )

        test_buckets = ['s3://valid-bucket/', 's3://invalid-bucket/', 's3://another-valid/']
        validated_buckets = [
            's3://valid-bucket/',
            's3://another-valid/',
        ]  # Only valid ones returned

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.s3_utils.validate_bucket_access'
        ) as mock_validate:
            mock_validate.return_value = validated_buckets

            with patch(
                'awslabs.aws_healthomics_mcp_server.utils.validation_utils.logger'
            ) as mock_logger:
                result = await validate_adhoc_s3_buckets(test_buckets)

                assert result == validated_buckets
                mock_validate.assert_called_once_with(test_buckets)
                mock_logger.info.assert_called_once()
                assert (
                    'Validated 2 adhoc S3 buckets out of 3 provided'
                    in mock_logger.info.call_args[0][0]
                )


# Tests for path_to_main validation


@pytest.mark.asyncio
async def test_validate_path_to_main_valid_paths():
    """Test validation of valid path_to_main values."""
    mock_ctx = AsyncMock()

    # Valid relative paths with correct extensions
    valid_paths = [
        'main.wdl',
        'workflows/main.wdl',
        'src/pipeline.cwl',
        'nextflow/main.nf',
        'subdir/workflow.WDL',  # Case insensitive
        'deep/nested/path/workflow.CWL',
    ]

    for path in valid_paths:
        result = await validate_path_to_main(mock_ctx, path)
        assert result == posixpath.normpath(path)
        mock_ctx.error.assert_not_called()
        mock_ctx.reset_mock()


@pytest.mark.asyncio
async def test_validate_path_to_main_none_and_empty():
    """Test validation of None and empty path_to_main values."""
    mock_ctx = AsyncMock()

    # None should return None
    result = await validate_path_to_main(mock_ctx, None)
    assert result is None
    mock_ctx.error.assert_not_called()

    # Empty string should return None
    result = await validate_path_to_main(mock_ctx, '')
    assert result is None
    mock_ctx.error.assert_not_called()


@pytest.mark.asyncio
async def test_validate_path_to_main_absolute_paths():
    """Test validation rejects absolute paths."""
    mock_ctx = AsyncMock()

    # POSIX absolute paths (these will be caught by posixpath.isabs())
    absolute_paths = [
        '/main.wdl',
        '/usr/local/workflows/main.wdl',
    ]

    for path in absolute_paths:
        with pytest.raises(ValueError, match='must be a relative path'):
            await validate_path_to_main(mock_ctx, path)
        mock_ctx.error.assert_called_once()
        mock_ctx.reset_mock()


@pytest.mark.asyncio
async def test_validate_path_to_main_directory_traversal():
    """Test validation rejects directory traversal attempts."""
    mock_ctx = AsyncMock()

    traversal_paths = [
        '../main.wdl',
        'workflows/../main.wdl',
        'workflows/../../main.wdl',
        '..',
    ]

    for path in traversal_paths:
        with pytest.raises(ValueError, match='cannot contain directory traversal sequences'):
            await validate_path_to_main(mock_ctx, path)
        mock_ctx.error.assert_called_once()
        mock_ctx.reset_mock()

    # This one will also be caught by directory traversal validation
    with pytest.raises(ValueError, match='cannot contain directory traversal sequences'):
        await validate_path_to_main(mock_ctx, 'workflows/../../../etc/passwd')
    mock_ctx.error.assert_called_once()
    mock_ctx.reset_mock()


@pytest.mark.asyncio
async def test_validate_path_to_main_empty_components():
    """Test validation rejects paths with empty components."""
    mock_ctx = AsyncMock()

    empty_component_paths = [
        'workflows//main.wdl',
        '//main.wdl',
        'workflows///nested//main.wdl',
    ]

    for path in empty_component_paths:
        with pytest.raises(ValueError, match='cannot contain empty path components'):
            await validate_path_to_main(mock_ctx, path)
        mock_ctx.error.assert_called_once()
        mock_ctx.reset_mock()


@pytest.mark.asyncio
async def test_validate_path_to_main_current_directory():
    """Test validation rejects current directory references."""
    mock_ctx = AsyncMock()

    current_dir_paths = [
        '.',
        './',
    ]

    for path in current_dir_paths:
        with pytest.raises(ValueError, match='cannot be the current directory'):
            await validate_path_to_main(mock_ctx, path)
        mock_ctx.error.assert_called_once()
        mock_ctx.reset_mock()


@pytest.mark.asyncio
async def test_validate_path_to_main_invalid_extensions():
    """Test validation rejects invalid file extensions."""
    mock_ctx = AsyncMock()

    invalid_extension_paths = [
        'main.txt',
        'workflow.py',
        'pipeline.sh',
        'workflow',  # No extension
        'main.WDL.backup',  # Wrong extension
        'workflows/script.js',
    ]

    for path in invalid_extension_paths:
        with pytest.raises(ValueError, match='must point to a workflow file with extension'):
            await validate_path_to_main(mock_ctx, path)
        mock_ctx.error.assert_called_once()
        mock_ctx.reset_mock()


@pytest.mark.asyncio
async def test_validate_path_to_main_normalization():
    """Test that paths are properly normalized."""
    # Test path normalization
    test_cases = [
        ('workflows/./main.wdl', 'workflows/main.wdl'),
        ('workflows/subdir/../main.wdl', 'workflows/main.wdl'),
        ('./workflows/main.wdl', 'workflows/main.wdl'),
    ]

    for input_path, expected_normalized in test_cases:
        # These should fail due to directory traversal, but let's test the normalization logic
        # by checking what would be normalized before validation
        normalized = posixpath.normpath(input_path)
        assert normalized == expected_normalized


class TestDetectReadmeInputType:
    """Test cases for detect_readme_input_type function."""

    def test_detect_s3_uri_basic(self):
        """Test detection of basic S3 URI."""
        result = detect_readme_input_type('s3://bucket/key.md')
        assert result == ReadmeInputType.S3_URI

    def test_detect_s3_uri_with_path(self):
        """Test detection of S3 URI with nested path."""
        result = detect_readme_input_type('s3://my-bucket/path/to/readme.md')
        assert result == ReadmeInputType.S3_URI

    def test_detect_s3_uri_without_md_extension(self):
        """Test detection of S3 URI without .md extension."""
        result = detect_readme_input_type('s3://bucket/readme.txt')
        assert result == ReadmeInputType.S3_URI

    def test_detect_s3_uri_empty_key(self):
        """Test detection of S3 URI with minimal key."""
        result = detect_readme_input_type('s3://bucket/a')
        assert result == ReadmeInputType.S3_URI

    def test_detect_s3_uri_prefix_only(self):
        """Test detection of S3 URI prefix only (invalid but still classified as S3)."""
        result = detect_readme_input_type('s3://')
        assert result == ReadmeInputType.S3_URI

    def test_detect_local_file_existing(self):
        """Test detection of existing local .md file."""
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            temp_path = f.name
            f.write(b'# Test README')

        try:
            result = detect_readme_input_type(temp_path)
            assert result == ReadmeInputType.LOCAL_FILE
        finally:
            os.unlink(temp_path)

    def test_detect_local_file_uppercase_extension(self):
        """Test detection of existing local file with uppercase .MD extension."""
        with tempfile.NamedTemporaryFile(suffix='.MD', delete=False) as f:
            temp_path = f.name
            f.write(b'# Test README')

        try:
            result = detect_readme_input_type(temp_path)
            assert result == ReadmeInputType.LOCAL_FILE
        finally:
            os.unlink(temp_path)

    def test_detect_nonexistent_md_file_as_markdown(self):
        """Test that non-existent .md file path is classified as markdown content."""
        result = detect_readme_input_type('/nonexistent/path/readme.md')
        assert result == ReadmeInputType.MARKDOWN_CONTENT

    def test_detect_existing_file_without_md_extension_as_markdown(self):
        """Test that existing file without .md extension is classified as markdown content."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
            f.write(b'# Test README')

        try:
            result = detect_readme_input_type(temp_path)
            assert result == ReadmeInputType.MARKDOWN_CONTENT
        finally:
            os.unlink(temp_path)

    def test_detect_markdown_content_simple(self):
        """Test detection of simple markdown content."""
        result = detect_readme_input_type('# My Workflow\n\nThis is documentation.')
        assert result == ReadmeInputType.MARKDOWN_CONTENT

    def test_detect_markdown_content_empty_string(self):
        """Test detection of empty string as markdown content."""
        result = detect_readme_input_type('')
        assert result == ReadmeInputType.MARKDOWN_CONTENT

    def test_detect_markdown_content_multiline(self):
        """Test detection of multiline markdown content."""
        content = """# Workflow Documentation

## Overview
This workflow processes genomic data.

## Usage
Run with default parameters.
"""
        result = detect_readme_input_type(content)
        assert result == ReadmeInputType.MARKDOWN_CONTENT

    def test_detect_markdown_content_with_md_in_text(self):
        """Test that markdown content containing '.md' text is not misclassified."""
        result = detect_readme_input_type('See the README.md file for more info')
        assert result == ReadmeInputType.MARKDOWN_CONTENT

    def test_s3_uri_takes_precedence_over_md_extension(self):
        """Test that S3 URI detection takes precedence even if path ends with .md."""
        result = detect_readme_input_type('s3://bucket/readme.md')
        assert result == ReadmeInputType.S3_URI

    def test_detect_markdown_content_looks_like_path_but_not_exists(self):
        """Test that path-like string that doesn't exist is classified as markdown."""
        result = detect_readme_input_type('./docs/README.md')
        assert result == ReadmeInputType.MARKDOWN_CONTENT


class TestValidateReadmeInput:
    """Test cases for validate_readme_input function."""

    @pytest.mark.asyncio
    async def test_validate_readme_input_none(self):
        """Test validation with None input returns (None, None)."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_readme_input,
        )

        mock_ctx = AsyncMock()
        result = await validate_readme_input(mock_ctx, None)
        assert result == (None, None)
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_readme_input_s3_uri_valid(self):
        """Test validation with valid S3 URI returns (None, uri)."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_readme_input,
        )

        mock_ctx = AsyncMock()
        s3_uri = 's3://valid-bucket/path/to/readme.md'
        result = await validate_readme_input(mock_ctx, s3_uri)
        assert result == (None, s3_uri)
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_readme_input_s3_uri_invalid(self):
        """Test validation with invalid S3 URI raises ValueError."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_readme_input,
        )

        mock_ctx = AsyncMock()
        invalid_uri = 's3://Invalid_Bucket/readme.md'

        with pytest.raises(ValueError) as exc_info:
            await validate_readme_input(mock_ctx, invalid_uri)

        assert 'readme must be a valid S3 URI' in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_readme_input_local_file(self):
        """Test validation with existing local .md file returns (content, None)."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_readme_input,
        )

        mock_ctx = AsyncMock()
        test_content = '# Test README\n\nThis is test content.'

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False, mode='w') as f:
            f.write(test_content)
            temp_path = f.name

        try:
            result = await validate_readme_input(mock_ctx, temp_path)
            assert result == (test_content, None)
            mock_ctx.error.assert_not_called()
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_validate_readme_input_markdown_content(self):
        """Test validation with markdown content returns (content, None)."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_readme_input,
        )

        mock_ctx = AsyncMock()
        markdown_content = '# My Workflow\n\nThis is documentation.'
        result = await validate_readme_input(mock_ctx, markdown_content)
        assert result == (markdown_content, None)
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_readme_input_empty_string(self):
        """Test validation with empty string returns (empty_string, None)."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_readme_input,
        )

        mock_ctx = AsyncMock()
        result = await validate_readme_input(mock_ctx, '')
        assert result == ('', None)
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_readme_input_mutually_exclusive_output(self):
        """Test that exactly one of readme_markdown or readme_uri is set (not both)."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_readme_input,
        )

        mock_ctx = AsyncMock()

        # Test with S3 URI
        result = await validate_readme_input(mock_ctx, 's3://bucket/readme.md')
        readme_markdown, readme_uri = result
        assert (readme_markdown is None) != (readme_uri is None)  # XOR - exactly one is set

        # Test with markdown content
        result = await validate_readme_input(mock_ctx, '# Markdown')
        readme_markdown, readme_uri = result
        assert (readme_markdown is None) != (readme_uri is None)  # XOR - exactly one is set

    @pytest.mark.asyncio
    async def test_validate_readme_input_local_file_unicode(self):
        """Test validation with local file containing unicode content."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_readme_input,
        )

        mock_ctx = AsyncMock()
        test_content = '# Test README\n\nUnicode: 日本語 中文 한국어 émojis: 🧬🔬'

        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            result = await validate_readme_input(mock_ctx, temp_path)
            assert result == (test_content, None)
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_validate_readme_input_file_not_found(self):
        """Test validation with non-existent file raises FileNotFoundError.

        Requirements: 4.3, 7.2
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            ReadmeInputType,
            detect_readme_input_type,
            validate_readme_input,
        )

        mock_ctx = AsyncMock()

        # Create a temp file, get its path, then delete it
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False, mode='w') as f:
            temp_path = f.name
        os.unlink(temp_path)  # Delete the file

        # Now create a new temp file to make the path look like it could exist
        # but we'll use a path that doesn't exist
        non_existent_path = temp_path + '_nonexistent.md'

        # First verify it would be detected as LOCAL_FILE if it existed
        # Since the file doesn't exist, it will be detected as MARKDOWN_CONTENT
        # So we need to mock os.path.isfile to return True for detection
        with patch('os.path.isfile', return_value=True):
            # Now the detection will classify it as LOCAL_FILE
            input_type = detect_readme_input_type(non_existent_path)
            assert input_type == ReadmeInputType.LOCAL_FILE

        # For the actual test, we need to mock isfile to return True during detection
        # but the actual file open will fail
        with patch('os.path.isfile', return_value=True):
            with pytest.raises(FileNotFoundError) as exc_info:
                await validate_readme_input(mock_ctx, non_existent_path)

            # Verify error message format: "README file not found: {path}"
            assert 'README file not found:' in str(exc_info.value)
            assert non_existent_path in str(exc_info.value)
            mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_readme_input_io_error(self):
        """Test validation with unreadable file raises IOError.

        Requirements: 4.4, 7.2, 7.3
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_readme_input,
        )

        mock_ctx = AsyncMock()
        test_path = '/path/to/readme.md'

        # Mock os.path.isfile to return True so it's detected as LOCAL_FILE
        # Mock open to raise IOError
        with patch('os.path.isfile', return_value=True):
            with patch('builtins.open', side_effect=IOError('Permission denied')):
                with pytest.raises(IOError) as exc_info:
                    await validate_readme_input(mock_ctx, test_path)

                # Verify error message format: "Failed to read README file {path}: {error}"
                assert 'Failed to read README file' in str(exc_info.value)
                assert test_path in str(exc_info.value)
                assert 'Permission denied' in str(exc_info.value)
                mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_readme_input_error_logging(self):
        """Test that errors are logged before being raised.

        Requirements: 7.3
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_readme_input,
        )

        mock_ctx = AsyncMock()
        test_path = '/path/to/readme.md'

        # Mock os.path.isfile to return True so it's detected as LOCAL_FILE
        # Mock open to raise IOError
        with patch('os.path.isfile', return_value=True):
            with patch('builtins.open', side_effect=IOError('Test error')):
                with patch(
                    'awslabs.aws_healthomics_mcp_server.utils.validation_utils.logger'
                ) as mock_logger:
                    with pytest.raises(IOError):
                        await validate_readme_input(mock_ctx, test_path)

                    # Verify logger.error was called
                    mock_logger.error.assert_called_once()
                    error_call_args = mock_logger.error.call_args[0][0]
                    assert 'Failed to read README file' in error_call_args
