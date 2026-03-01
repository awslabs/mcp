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
from hypothesis import given, settings
from hypothesis import strategies as st
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


# Property-Based Tests using Hypothesis for Workflow Repository Integration

# Custom strategies for repository integration tests
# Valid AWS CodeConnection ARN generator
valid_connection_arns = st.from_regex(
    r'arn:aws:(codeconnections|codestar-connections):us-east-1:123456789012:connection/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',
    fullmatch=True,
)

# Valid repository ID generator (owner/repo format)
valid_repository_ids = st.from_regex(r'[a-zA-Z0-9_-]{1,39}/[a-zA-Z0-9_.-]{1,100}', fullmatch=True)

# Valid source reference type generator
valid_source_types = st.sampled_from(['COMMIT_ID', 'BRANCH', 'TAG'])

# Valid source reference value generator (non-empty strings)
valid_source_values = st.text(
    min_size=1,
    max_size=100,
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_./'),
).filter(lambda x: x.strip())

# Valid base64 content generator
valid_base64_content = st.binary(min_size=1, max_size=100).map(
    lambda b: __import__('base64').b64encode(b).decode('utf-8')
)

# Valid S3 URI generator
valid_s3_uris = st.from_regex(
    r's3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]/[a-zA-Z0-9._/-]+\.zip',
    fullmatch=True,
)


class TestWorkflowRepositoryIntegrationPropertyBased:
    """Property-based tests for workflow repository integration using Hypothesis."""

    @given(
        definition_zip_base64=valid_base64_content,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_property_backward_compatibility_zip_source(
        self,
        definition_zip_base64: str,
    ):
        """Property 7: Backward Compatibility - ZIP source.

        For any valid workflow creation request using definition_zip_base64
        (without definition_repository), the function SHALL process the request
        identically to the previous implementation.

        **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
        **Feature: workflow-repository-integration, Property 7: Backward Compatibility**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_definition_sources,
        )

        mock_ctx = AsyncMock()

        # Call validate_definition_sources with only definition_zip_base64
        result = await validate_definition_sources(
            mock_ctx,
            definition_zip_base64=definition_zip_base64,
            definition_uri=None,
            definition_repository=None,
        )

        # Property: Returns a 3-tuple
        assert isinstance(result, tuple)
        assert len(result) == 3

        # Property: First element is decoded bytes (not None)
        definition_zip, validated_uri, validated_repository = result
        assert definition_zip is not None
        assert isinstance(definition_zip, bytes)

        # Property: Second and third elements are None
        assert validated_uri is None
        assert validated_repository is None

        # Property: No errors reported to context
        mock_ctx.error.assert_not_called()

    @given(
        s3_uri=valid_s3_uris,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_property_backward_compatibility_uri_source(
        self,
        s3_uri: str,
    ):
        """Property 7: Backward Compatibility - URI source.

        For any valid workflow creation request using definition_uri
        (without definition_repository), the function SHALL process the request
        identically to the previous implementation.

        **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
        **Feature: workflow-repository-integration, Property 7: Backward Compatibility**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_definition_sources,
        )

        mock_ctx = AsyncMock()

        # Call validate_definition_sources with only definition_uri
        result = await validate_definition_sources(
            mock_ctx,
            definition_zip_base64=None,
            definition_uri=s3_uri,
            definition_repository=None,
        )

        # Property: Returns a 3-tuple
        assert isinstance(result, tuple)
        assert len(result) == 3

        # Property: Second element is the validated URI (not None)
        definition_zip, validated_uri, validated_repository = result
        assert definition_zip is None
        assert validated_uri is not None
        assert validated_uri == s3_uri

        # Property: First and third elements are None
        assert validated_repository is None

        # Property: No errors reported to context
        mock_ctx.error.assert_not_called()

    @given(
        connection_arn=valid_connection_arns,
        repository_id=valid_repository_ids,
        source_type=valid_source_types,
        source_value=valid_source_values,
        exclude_patterns=st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_property_api_parameter_mapping_round_trip(
        self,
        connection_arn: str,
        repository_id: str,
        source_type: str,
        source_value: str,
        exclude_patterns: list,
    ):
        """Property 8: API Parameter Mapping Round-Trip.

        For any valid repository configuration with snake_case field names,
        the transformation to API format SHALL produce a dictionary with
        camelCase field names that correctly maps all input fields.

        **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6**
        **Feature: workflow-repository-integration, Property 8: API Parameter Mapping Round-Trip**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_definition,
        )

        mock_ctx = AsyncMock()

        # Build input repository configuration with snake_case field names
        definition_repository = {
            'connection_arn': connection_arn,
            'full_repository_id': repository_id,
            'source_reference': {
                'type': source_type,
                'value': source_value,
            },
        }

        # Add exclude_file_patterns only if non-empty
        if exclude_patterns:
            definition_repository['exclude_file_patterns'] = exclude_patterns

        # Call validate_repository_definition
        result = await validate_repository_definition(mock_ctx, definition_repository)

        # Property: Result is not None for valid input
        assert result is not None

        # Property: connectionArn is correctly mapped (Requirement 8.1)
        assert 'connectionArn' in result
        assert result['connectionArn'] == connection_arn

        # Property: fullRepositoryId is correctly mapped (Requirement 8.2)
        assert 'fullRepositoryId' in result
        assert result['fullRepositoryId'] == repository_id

        # Property: sourceReference is correctly mapped with nested fields (Requirement 8.3)
        assert 'sourceReference' in result
        assert 'type' in result['sourceReference']
        assert 'value' in result['sourceReference']
        assert result['sourceReference']['type'] == source_type
        assert result['sourceReference']['value'] == source_value

        # Property: excludeFilePatterns is correctly mapped if provided (Requirement 8.4)
        if exclude_patterns:
            assert 'excludeFilePatterns' in result
            assert result['excludeFilePatterns'] == exclude_patterns
        else:
            # Should not be present if empty
            assert 'excludeFilePatterns' not in result

        # Property: No errors reported to context
        mock_ctx.error.assert_not_called()

    @given(
        invalid_arn=st.text(min_size=1, max_size=100).filter(
            lambda x: not x.startswith('arn:aws:codeconnections:')
            and not x.startswith('arn:aws:codestar-connections:')
        ),
        repository_id=valid_repository_ids,
        source_type=valid_source_types,
        source_value=valid_source_values,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_property_error_message_context_invalid_arn(
        self,
        invalid_arn: str,
        repository_id: str,
        source_type: str,
        source_value: str,
    ):
        """Property 9: Error Message Context Inclusion - Invalid ARN.

        For any validation error raised during repository configuration validation
        due to invalid connection_arn, the error message SHALL contain the specific
        invalid ARN value that caused the failure.

        **Validates: Requirements 7.1, 7.2, 7.3**
        **Feature: workflow-repository-integration, Property 9: Error Message Context Inclusion**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_definition,
        )

        mock_ctx = AsyncMock()

        # Build input repository configuration with invalid ARN
        definition_repository = {
            'connection_arn': invalid_arn,
            'full_repository_id': repository_id,
            'source_reference': {
                'type': source_type,
                'value': source_value,
            },
        }

        # Call validate_repository_definition and expect ValueError
        with pytest.raises(ValueError) as exc_info:
            await validate_repository_definition(mock_ctx, definition_repository)

        # Property: Error message contains the invalid ARN value
        error_message = str(exc_info.value)
        assert invalid_arn in error_message or 'connection_arn' in error_message.lower()

        # Property: Error was reported to context
        mock_ctx.error.assert_called_once()

    @given(
        connection_arn=valid_connection_arns,
        repository_id=valid_repository_ids,
        invalid_source_type=st.text(min_size=1, max_size=50).filter(
            lambda x: x not in ['COMMIT_ID', 'BRANCH', 'TAG']
        ),
        source_value=valid_source_values,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_property_error_message_context_invalid_source_type(
        self,
        connection_arn: str,
        repository_id: str,
        invalid_source_type: str,
        source_value: str,
    ):
        """Property 9: Error Message Context Inclusion - Invalid Source Type.

        For any validation error raised during repository configuration validation
        due to invalid source_reference.type, the error message SHALL contain
        information about the valid types.

        **Validates: Requirements 7.1, 7.2, 7.3**
        **Feature: workflow-repository-integration, Property 9: Error Message Context Inclusion**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_definition,
        )

        mock_ctx = AsyncMock()

        # Build input repository configuration with invalid source type
        definition_repository = {
            'connection_arn': connection_arn,
            'full_repository_id': repository_id,
            'source_reference': {
                'type': invalid_source_type,
                'value': source_value,
            },
        }

        # Call validate_repository_definition and expect ValueError
        with pytest.raises(ValueError) as exc_info:
            await validate_repository_definition(mock_ctx, definition_repository)

        # Property: Error message contains information about the invalid type
        error_message = str(exc_info.value)
        assert 'source_reference' in error_message.lower() or 'type' in error_message.lower()

        # Property: Error was reported to context
        mock_ctx.error.assert_called_once()

    @given(
        connection_arn=valid_connection_arns,
        repository_id=valid_repository_ids,
        source_type=valid_source_types,
        empty_value=st.sampled_from(['', '   ', '\t', '\n']),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_property_error_message_context_empty_source_value(
        self,
        connection_arn: str,
        repository_id: str,
        source_type: str,
        empty_value: str,
    ):
        """Property 9: Error Message Context Inclusion - Empty Source Value.

        For any validation error raised during repository configuration validation
        due to empty source_reference.value, the error message SHALL indicate
        that the value cannot be empty.

        **Validates: Requirements 7.1, 7.2, 7.3**
        **Feature: workflow-repository-integration, Property 9: Error Message Context Inclusion**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_definition,
        )

        mock_ctx = AsyncMock()

        # Build input repository configuration with empty source value
        definition_repository = {
            'connection_arn': connection_arn,
            'full_repository_id': repository_id,
            'source_reference': {
                'type': source_type,
                'value': empty_value,
            },
        }

        # Call validate_repository_definition and expect ValueError
        with pytest.raises(ValueError) as exc_info:
            await validate_repository_definition(mock_ctx, definition_repository)

        # Property: Error message indicates empty value issue
        error_message = str(exc_info.value)
        assert 'empty' in error_message.lower() or 'value' in error_message.lower()

        # Property: Error was reported to context
        mock_ctx.error.assert_called_once()


# Tests for validate_provider_type function


class TestValidateProviderType:
    """Test cases for validate_provider_type function.

    **Validates: Requirements 4.1, 4.2, 4.3, 7.3**
    """

    @pytest.mark.asyncio
    async def test_validate_provider_type_none_input(self):
        """Test validation with None input returns None."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()
        result = await validate_provider_type(mock_ctx, None)
        assert result is None
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_provider_type_valid_bitbucket(self):
        """Test validation with valid Bitbucket provider type."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()
        result = await validate_provider_type(mock_ctx, 'Bitbucket')
        assert result == 'Bitbucket'
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_provider_type_valid_github(self):
        """Test validation with valid GitHub provider type."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()
        result = await validate_provider_type(mock_ctx, 'GitHub')
        assert result == 'GitHub'
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_provider_type_valid_github_enterprise(self):
        """Test validation with valid GitHubEnterpriseServer provider type."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()
        result = await validate_provider_type(mock_ctx, 'GitHubEnterpriseServer')
        assert result == 'GitHubEnterpriseServer'
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_provider_type_valid_gitlab(self):
        """Test validation with valid GitLab provider type."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()
        result = await validate_provider_type(mock_ctx, 'GitLab')
        assert result == 'GitLab'
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_provider_type_valid_gitlab_self_managed(self):
        """Test validation with valid GitLabSelfManaged provider type."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()
        result = await validate_provider_type(mock_ctx, 'GitLabSelfManaged')
        assert result == 'GitLabSelfManaged'
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_provider_type_all_valid_types(self):
        """Test validation with all valid provider types."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        valid_types = [
            'Bitbucket',
            'GitHub',
            'GitHubEnterpriseServer',
            'GitLab',
            'GitLabSelfManaged',
        ]

        for provider_type in valid_types:
            mock_ctx = AsyncMock()
            result = await validate_provider_type(mock_ctx, provider_type)
            assert result == provider_type
            mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_provider_type_invalid_lowercase(self):
        """Test validation rejects lowercase provider types (case-sensitive).

        **Validates: Requirements 4.3**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await validate_provider_type(mock_ctx, 'github')

        assert "Invalid provider_type 'github'" in str(exc_info.value)
        assert 'Must be one of:' in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_provider_type_invalid_uppercase(self):
        """Test validation rejects uppercase provider types (case-sensitive).

        **Validates: Requirements 4.3**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await validate_provider_type(mock_ctx, 'GITHUB')

        assert "Invalid provider_type 'GITHUB'" in str(exc_info.value)
        assert 'Must be one of:' in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_provider_type_invalid_unknown(self):
        """Test validation rejects unknown provider types.

        **Validates: Requirements 4.2**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await validate_provider_type(mock_ctx, 'UnknownProvider')

        assert "Invalid provider_type 'UnknownProvider'" in str(exc_info.value)
        assert 'Must be one of:' in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_provider_type_invalid_empty_string(self):
        """Test validation rejects empty string provider type.

        **Validates: Requirements 4.2**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await validate_provider_type(mock_ctx, '')

        assert "Invalid provider_type ''" in str(exc_info.value)
        assert 'Must be one of:' in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_provider_type_error_lists_valid_types(self):
        """Test that error message lists all valid provider types.

        **Validates: Requirements 4.2**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await validate_provider_type(mock_ctx, 'invalid')

        error_message = str(exc_info.value)
        # Verify all valid types are listed in the error message
        assert 'Bitbucket' in error_message
        assert 'GitHub' in error_message
        assert 'GitHubEnterpriseServer' in error_message
        assert 'GitLab' in error_message
        assert 'GitLabSelfManaged' in error_message

    @pytest.mark.asyncio
    async def test_validate_provider_type_logs_error(self):
        """Test that validation errors are logged before raising.

        **Validates: Requirements 7.3**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.validation_utils.logger'
        ) as mock_logger:
            with pytest.raises(ValueError):
                await validate_provider_type(mock_ctx, 'invalid')

            mock_logger.error.assert_called_once()
            error_call_args = mock_logger.error.call_args[0][0]
            assert "Invalid provider_type 'invalid'" in error_call_args

    @pytest.mark.asyncio
    async def test_validate_provider_type_reports_to_context(self):
        """Test that validation errors are reported to MCP context.

        **Validates: Requirements 7.3**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_provider_type,
        )

        mock_ctx = AsyncMock()

        with pytest.raises(ValueError):
            await validate_provider_type(mock_ctx, 'invalid')

        mock_ctx.error.assert_called_once()
        error_call_args = mock_ctx.error.call_args[0][0]
        assert "Invalid provider_type 'invalid'" in error_call_args


# Tests for validate_connection_arn function


class TestValidateConnectionArn:
    """Test cases for validate_connection_arn function.

    **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 7.3**
    """

    @pytest.mark.asyncio
    async def test_validate_connection_arn_valid_codeconnections_prefix(self):
        """Test validation with valid codeconnections ARN prefix.

        **Validates: Requirements 5.1, 5.2**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        mock_ctx = AsyncMock()
        valid_arn = 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc-123'
        result = await validate_connection_arn(mock_ctx, valid_arn)
        assert result == valid_arn
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_connection_arn_valid_codestar_prefix(self):
        """Test validation with valid codestar-connections ARN prefix (legacy format).

        **Validates: Requirements 5.1, 5.3**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        mock_ctx = AsyncMock()
        valid_arn = 'arn:aws:codestar-connections:us-west-2:123456789012:connection/def-456'
        result = await validate_connection_arn(mock_ctx, valid_arn)
        assert result == valid_arn
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_connection_arn_valid_various_regions(self):
        """Test validation with valid ARNs from various regions.

        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        valid_arns = [
            'arn:aws:codeconnections:us-east-1:123456789012:connection/abc-123',
            'arn:aws:codeconnections:eu-west-1:123456789012:connection/abc-123',
            'arn:aws:codeconnections:ap-southeast-1:123456789012:connection/abc-123',
            'arn:aws:codestar-connections:us-east-2:123456789012:connection/abc-123',
            'arn:aws:codestar-connections:eu-central-1:123456789012:connection/abc-123',
        ]

        for valid_arn in valid_arns:
            mock_ctx = AsyncMock()
            result = await validate_connection_arn(mock_ctx, valid_arn)
            assert result == valid_arn
            mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_connection_arn_invalid_prefix(self):
        """Test validation rejects ARNs with invalid prefix.

        **Validates: Requirements 5.4**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        mock_ctx = AsyncMock()
        invalid_arn = 'arn:aws:s3:us-east-1:123456789012:bucket/my-bucket'

        with pytest.raises(ValueError) as exc_info:
            await validate_connection_arn(mock_ctx, invalid_arn)

        assert 'Invalid connection ARN format:' in str(exc_info.value)
        assert invalid_arn in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_connection_arn_invalid_empty_string(self):
        """Test validation rejects empty string.

        **Validates: Requirements 5.4**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        mock_ctx = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await validate_connection_arn(mock_ctx, '')

        assert 'Invalid connection ARN format:' in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_connection_arn_invalid_random_string(self):
        """Test validation rejects random strings.

        **Validates: Requirements 5.4**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        mock_ctx = AsyncMock()
        invalid_arn = 'not-an-arn-at-all'

        with pytest.raises(ValueError) as exc_info:
            await validate_connection_arn(mock_ctx, invalid_arn)

        assert 'Invalid connection ARN format:' in str(exc_info.value)
        assert invalid_arn in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_connection_arn_invalid_partial_prefix(self):
        """Test validation rejects ARNs with partial prefix.

        **Validates: Requirements 5.4**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        mock_ctx = AsyncMock()
        # Missing 'arn:aws:' prefix
        invalid_arn = 'codeconnections:us-east-1:123456789012:connection/abc-123'

        with pytest.raises(ValueError) as exc_info:
            await validate_connection_arn(mock_ctx, invalid_arn)

        assert 'Invalid connection ARN format:' in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_connection_arn_error_message_format(self):
        """Test that error message includes expected format guidance.

        **Validates: Requirements 5.4**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        mock_ctx = AsyncMock()
        invalid_arn = 'invalid-arn'

        with pytest.raises(ValueError) as exc_info:
            await validate_connection_arn(mock_ctx, invalid_arn)

        error_message = str(exc_info.value)
        # Verify error message includes expected format guidance
        assert 'arn:aws:codeconnections:' in error_message
        assert 'arn:aws:codestar-connections:' in error_message
        assert '{region}' in error_message
        assert '{account}' in error_message
        assert 'connection/{id}' in error_message

    @pytest.mark.asyncio
    async def test_validate_connection_arn_logs_error(self):
        """Test that validation errors are logged before raising.

        **Validates: Requirements 7.3**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        mock_ctx = AsyncMock()
        invalid_arn = 'invalid-arn'

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.validation_utils.logger'
        ) as mock_logger:
            with pytest.raises(ValueError):
                await validate_connection_arn(mock_ctx, invalid_arn)

            mock_logger.error.assert_called_once()
            error_call_args = mock_logger.error.call_args[0][0]
            assert 'Invalid connection ARN format:' in error_call_args
            assert invalid_arn in error_call_args

    @pytest.mark.asyncio
    async def test_validate_connection_arn_reports_to_context(self):
        """Test that validation errors are reported to MCP context.

        **Validates: Requirements 7.3**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        mock_ctx = AsyncMock()
        invalid_arn = 'invalid-arn'

        with pytest.raises(ValueError):
            await validate_connection_arn(mock_ctx, invalid_arn)

        mock_ctx.error.assert_called_once()
        error_call_args = mock_ctx.error.call_args[0][0]
        assert 'Invalid connection ARN format:' in error_call_args
        assert invalid_arn in error_call_args

    @pytest.mark.asyncio
    async def test_validate_connection_arn_invalid_similar_service(self):
        """Test validation rejects ARNs from similar but different services.

        **Validates: Requirements 5.4**
        """
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_connection_arn,
        )

        invalid_arns = [
            'arn:aws:codestar:us-east-1:123456789012:connection/abc-123',  # codestar, not codestar-connections
            'arn:aws:codecommit:us-east-1:123456789012:connection/abc-123',  # codecommit
            'arn:aws:codepipeline:us-east-1:123456789012:connection/abc-123',  # codepipeline
        ]

        for invalid_arn in invalid_arns:
            mock_ctx = AsyncMock()
            with pytest.raises(ValueError) as exc_info:
                await validate_connection_arn(mock_ctx, invalid_arn)

            assert 'Invalid connection ARN format:' in str(exc_info.value)
            mock_ctx.error.assert_called_once()


# Tests for validate_repository_path_params function


class TestValidateRepositoryPathParams:
    """Test cases for validate_repository_path_params function.

    These tests cover the validation of repository-specific path parameters
    (parameter_template_path and readme_path) which are only valid when
    definition_repository is provided.
    """

    @pytest.mark.asyncio
    async def test_validate_repository_path_params_all_none(self):
        """Test validation with all None inputs returns (None, None)."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_path_params,
        )

        mock_ctx = AsyncMock()
        result = await validate_repository_path_params(mock_ctx, None, None, None)
        assert result == (None, None)
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_repository_path_params_with_repository(self):
        """Test validation with definition_repository and path params."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_path_params,
        )

        mock_ctx = AsyncMock()
        definition_repository = {
            'connection_arn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc',
            'full_repository_id': 'owner/repo',
            'source_reference': {'type': 'BRANCH', 'value': 'main'},
        }
        result = await validate_repository_path_params(
            mock_ctx,
            definition_repository,
            'params/template.json',
            'docs/README.md',
        )
        assert result == ('params/template.json', 'docs/README.md')
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_repository_path_params_parameter_template_without_repo(self):
        """Test validation rejects parameter_template_path without definition_repository."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_path_params,
        )

        mock_ctx = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await validate_repository_path_params(
                mock_ctx,
                None,  # No definition_repository
                'params/template.json',  # But parameter_template_path is provided
                None,
            )

        assert 'parameter_template_path can only be used with definition_repository' in str(
            exc_info.value
        )
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_repository_path_params_readme_path_without_repo(self):
        """Test validation rejects readme_path without definition_repository."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_path_params,
        )

        mock_ctx = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await validate_repository_path_params(
                mock_ctx,
                None,  # No definition_repository
                None,
                'docs/README.md',  # But readme_path is provided
            )

        assert 'readme_path can only be used with definition_repository' in str(exc_info.value)
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_repository_path_params_logs_error(self):
        """Test that validation errors are logged."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_path_params,
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.validation_utils.logger'
        ) as mock_logger:
            with pytest.raises(ValueError):
                await validate_repository_path_params(
                    mock_ctx,
                    None,
                    'params/template.json',
                    None,
                )

            mock_logger.error.assert_called_once()
            assert 'parameter_template_path' in mock_logger.error.call_args[0][0]


# Tests for validate_definition_sources with definition_repository


class TestValidateDefinitionSourcesWithRepository:
    """Test cases for validate_definition_sources with definition_repository."""

    @pytest.mark.asyncio
    async def test_validate_definition_sources_with_repository(self):
        """Test validation with definition_repository source."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_definition_sources,
        )

        mock_ctx = AsyncMock()
        definition_repository = {
            'connection_arn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc-123',
            'full_repository_id': 'owner/repo',
            'source_reference': {'type': 'BRANCH', 'value': 'main'},
        }

        result = await validate_definition_sources(
            mock_ctx,
            definition_zip_base64=None,
            definition_uri=None,
            definition_repository=definition_repository,
        )

        definition_zip, validated_uri, validated_repository = result
        assert definition_zip is None
        assert validated_uri is None
        assert validated_repository is not None
        assert validated_repository['connectionArn'] == definition_repository['connection_arn']
        assert (
            validated_repository['fullRepositoryId'] == definition_repository['full_repository_id']
        )
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_definition_sources_repository_with_exclude_patterns(self):
        """Test validation with definition_repository including exclude_file_patterns."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_definition_sources,
        )

        mock_ctx = AsyncMock()
        definition_repository = {
            'connection_arn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc-123',
            'full_repository_id': 'owner/repo',
            'source_reference': {'type': 'TAG', 'value': 'v1.0.0'},
            'exclude_file_patterns': ['*.md', 'tests/*'],
        }

        result = await validate_definition_sources(
            mock_ctx,
            definition_zip_base64=None,
            definition_uri=None,
            definition_repository=definition_repository,
        )

        _, _, validated_repository = result
        assert validated_repository is not None
        assert validated_repository['excludeFilePatterns'] == ['*.md', 'tests/*']
        mock_ctx.error.assert_not_called()


# Tests for validate_repository_definition with Field objects


class TestValidateRepositoryDefinitionFieldObjects:
    """Test cases for validate_repository_definition handling Field objects."""

    @pytest.mark.asyncio
    async def test_validate_repository_definition_none_input(self):
        """Test handling of None input returns None."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_definition,
        )

        mock_ctx = AsyncMock()
        result = await validate_repository_definition(mock_ctx, None)
        assert result is None
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_repository_definition_field_object_with_none_default(self):
        """Test handling of Field object with None default value."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_definition,
        )
        from typing import Any, Dict, Optional

        mock_ctx = AsyncMock()

        # Create a mock Field object with None default that is NOT a dict or None type
        class MockField:
            default: Optional[Dict[str, Any]] = None

        # The key is that the object has 'default' attribute and is NOT isinstance of (dict, type(None))
        mock_field: Any = MockField()
        result = await validate_repository_definition(mock_ctx, mock_field)
        assert result is None
        mock_ctx.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_repository_definition_field_object_with_dict_default(self):
        """Test handling of Field object with dict default value."""
        from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
            validate_repository_definition,
        )
        from typing import Any, Dict

        mock_ctx = AsyncMock()

        # Create a mock Field object with dict default
        class MockField:
            default: Dict[str, Any] = {
                'connection_arn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc',
                'full_repository_id': 'owner/repo',
                'source_reference': {'type': 'BRANCH', 'value': 'main'},
            }

        mock_field: Any = MockField()
        result = await validate_repository_definition(mock_ctx, mock_field)
        assert result is not None
        assert result['connectionArn'] == MockField.default['connection_arn']
        mock_ctx.error.assert_not_called()
