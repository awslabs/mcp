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

import pytest
from awslabs.aws_healthomics_mcp_server.utils.validation_utils import validate_s3_uri
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
