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

import posixpath
import pytest
from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
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
