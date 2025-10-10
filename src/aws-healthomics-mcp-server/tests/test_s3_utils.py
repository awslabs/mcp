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

"""Unit tests for S3 utility functions."""

import pytest
from awslabs.aws_healthomics_mcp_server.utils.s3_utils import (
    ensure_s3_uri_ends_with_slash,
    is_valid_bucket_name,
    parse_s3_path,
    validate_and_normalize_s3_path,
    validate_bucket_access,
)
from botocore.exceptions import ClientError, NoCredentialsError
from unittest.mock import MagicMock, patch


class TestEnsureS3UriEndsWithSlash:
    """Test cases for ensure_s3_uri_ends_with_slash function."""

    def test_ensure_s3_uri_ends_with_slash_already_has_slash(self):
        """Test URI that already ends with a slash."""
        uri = 's3://bucket/path/'
        result = ensure_s3_uri_ends_with_slash(uri)
        assert result == 's3://bucket/path/'

    def test_ensure_s3_uri_ends_with_slash_no_slash(self):
        """Test URI that doesn't end with a slash."""
        uri = 's3://bucket/path'
        result = ensure_s3_uri_ends_with_slash(uri)
        assert result == 's3://bucket/path/'

    def test_ensure_s3_uri_ends_with_slash_root_bucket(self):
        """Test URI for root bucket path."""
        uri = 's3://bucket'
        result = ensure_s3_uri_ends_with_slash(uri)
        assert result == 's3://bucket/'

    def test_ensure_s3_uri_ends_with_slash_root_bucket_with_slash(self):
        """Test URI for root bucket path that already has slash."""
        uri = 's3://bucket/'
        result = ensure_s3_uri_ends_with_slash(uri)
        assert result == 's3://bucket/'

    def test_ensure_s3_uri_ends_with_slash_invalid_scheme(self):
        """Test URI that doesn't start with s3://."""
        uri = 'https://bucket/path'
        with pytest.raises(ValueError, match='URI must start with s3://'):
            ensure_s3_uri_ends_with_slash(uri)

    def test_ensure_s3_uri_ends_with_slash_empty_string(self):
        """Test empty string input."""
        uri = ''
        with pytest.raises(ValueError, match='URI must start with s3://'):
            ensure_s3_uri_ends_with_slash(uri)

    def test_ensure_s3_uri_ends_with_slash_complex_path(self):
        """Test complex S3 path with multiple levels."""
        uri = 's3://my-bucket/data/genomics/samples'
        result = ensure_s3_uri_ends_with_slash(uri)
        assert result == 's3://my-bucket/data/genomics/samples/'


class TestParseS3Path:
    """Test cases for parse_s3_path function."""

    def test_parse_s3_path_valid_bucket_only(self):
        """Test parsing S3 path with bucket only."""
        bucket, prefix = parse_s3_path('s3://my-bucket')
        assert bucket == 'my-bucket'
        assert prefix == ''

    def test_parse_s3_path_valid_bucket_with_slash(self):
        """Test parsing S3 path with bucket and trailing slash."""
        bucket, prefix = parse_s3_path('s3://my-bucket/')
        assert bucket == 'my-bucket'
        assert prefix == ''

    def test_parse_s3_path_valid_with_prefix(self):
        """Test parsing S3 path with bucket and prefix."""
        bucket, prefix = parse_s3_path('s3://my-bucket/data/genomics')
        assert bucket == 'my-bucket'
        assert prefix == 'data/genomics'

    def test_parse_s3_path_valid_with_prefix_and_slash(self):
        """Test parsing S3 path with bucket, prefix, and trailing slash."""
        bucket, prefix = parse_s3_path('s3://my-bucket/data/genomics/')
        assert bucket == 'my-bucket'
        assert prefix == 'data/genomics/'

    def test_parse_s3_path_invalid_no_s3_scheme(self):
        """Test parsing invalid path without s3:// scheme."""
        with pytest.raises(ValueError, match="Invalid S3 path format.*Must start with 's3://'"):
            parse_s3_path('https://my-bucket/data')

    def test_parse_s3_path_invalid_empty_string(self):
        """Test parsing empty string."""
        with pytest.raises(ValueError, match="Invalid S3 path format.*Must start with 's3://'"):
            parse_s3_path('')

    def test_parse_s3_path_invalid_no_bucket(self):
        """Test parsing S3 path without bucket name."""
        with pytest.raises(ValueError, match='Invalid S3 path format.*Missing bucket name'):
            parse_s3_path('s3://')

    def test_parse_s3_path_invalid_only_slash(self):
        """Test parsing S3 path with only slash after scheme."""
        with pytest.raises(ValueError, match='Invalid S3 path format.*Missing bucket name'):
            parse_s3_path('s3:///')

    def test_parse_s3_path_complex_prefix(self):
        """Test parsing S3 path with complex prefix structure."""
        bucket, prefix = parse_s3_path('s3://genomics-data/projects/2024/samples/fastq/')
        assert bucket == 'genomics-data'
        assert prefix == 'projects/2024/samples/fastq/'


class TestIsValidBucketName:
    """Test cases for is_valid_bucket_name function."""

    def test_is_valid_bucket_name_valid_simple(self):
        """Test valid simple bucket name."""
        assert is_valid_bucket_name('mybucket') is True

    def test_is_valid_bucket_name_valid_with_hyphens(self):
        """Test valid bucket name with hyphens."""
        assert is_valid_bucket_name('my-bucket-name') is True

    def test_is_valid_bucket_name_valid_with_numbers(self):
        """Test valid bucket name with numbers."""
        assert is_valid_bucket_name('bucket123') is True
        assert is_valid_bucket_name('123bucket') is True

    def test_is_valid_bucket_name_valid_with_dots(self):
        """Test valid bucket name with dots."""
        assert is_valid_bucket_name('my.bucket.name') is True

    def test_is_valid_bucket_name_valid_minimum_length(self):
        """Test valid bucket name with minimum length (3 characters)."""
        assert is_valid_bucket_name('abc') is True

    def test_is_valid_bucket_name_valid_maximum_length(self):
        """Test valid bucket name with maximum length (63 characters)."""
        long_name = 'a' * 63
        assert is_valid_bucket_name(long_name) is True

    def test_is_valid_bucket_name_invalid_empty(self):
        """Test invalid empty bucket name."""
        assert is_valid_bucket_name('') is False

    def test_is_valid_bucket_name_invalid_too_short(self):
        """Test invalid bucket name that's too short."""
        assert is_valid_bucket_name('ab') is False

    def test_is_valid_bucket_name_invalid_too_long(self):
        """Test invalid bucket name that's too long."""
        long_name = 'a' * 64
        assert is_valid_bucket_name(long_name) is False

    def test_is_valid_bucket_name_invalid_uppercase(self):
        """Test invalid bucket name with uppercase letters."""
        assert is_valid_bucket_name('MyBucket') is False
        assert is_valid_bucket_name('BUCKET') is False

    def test_is_valid_bucket_name_invalid_special_chars(self):
        """Test invalid bucket name with special characters."""
        assert is_valid_bucket_name('bucket_name') is False
        assert is_valid_bucket_name('bucket@name') is False
        assert is_valid_bucket_name('bucket#name') is False

    def test_is_valid_bucket_name_invalid_starts_with_hyphen(self):
        """Test invalid bucket name starting with hyphen."""
        assert is_valid_bucket_name('-bucket') is False

    def test_is_valid_bucket_name_invalid_ends_with_hyphen(self):
        """Test invalid bucket name ending with hyphen."""
        assert is_valid_bucket_name('bucket-') is False

    def test_is_valid_bucket_name_invalid_starts_with_dot(self):
        """Test invalid bucket name starting with dot."""
        assert is_valid_bucket_name('.bucket') is False

    def test_is_valid_bucket_name_invalid_ends_with_dot(self):
        """Test invalid bucket name ending with dot."""
        assert is_valid_bucket_name('bucket.') is False


class TestValidateAndNormalizeS3Path:
    """Test cases for validate_and_normalize_s3_path function."""

    def test_validate_and_normalize_s3_path_valid_simple(self):
        """Test validation and normalization of simple valid S3 path."""
        result = validate_and_normalize_s3_path('s3://mybucket')
        assert result == 's3://mybucket/'

    def test_validate_and_normalize_s3_path_valid_with_prefix(self):
        """Test validation and normalization of S3 path with prefix."""
        result = validate_and_normalize_s3_path('s3://mybucket/data')
        assert result == 's3://mybucket/data/'

    def test_validate_and_normalize_s3_path_already_normalized(self):
        """Test validation and normalization of already normalized path."""
        result = validate_and_normalize_s3_path('s3://mybucket/data/')
        assert result == 's3://mybucket/data/'

    def test_validate_and_normalize_s3_path_invalid_scheme(self):
        """Test validation with invalid scheme."""
        with pytest.raises(ValueError, match="S3 path must start with 's3://'"):
            validate_and_normalize_s3_path('https://mybucket/data')

    def test_validate_and_normalize_s3_path_invalid_bucket_name(self):
        """Test validation with invalid bucket name."""
        with pytest.raises(ValueError, match='Invalid bucket name'):
            validate_and_normalize_s3_path('s3://MyBucket/data')

    def test_validate_and_normalize_s3_path_empty_string(self):
        """Test validation with empty string."""
        with pytest.raises(ValueError, match="S3 path must start with 's3://'"):
            validate_and_normalize_s3_path('')

    def test_validate_and_normalize_s3_path_complex_valid(self):
        """Test validation and normalization of complex valid path."""
        result = validate_and_normalize_s3_path('s3://genomics-data-2024/projects/sample-123')
        assert result == 's3://genomics-data-2024/projects/sample-123/'


class TestValidateBucketAccess:
    """Test cases for validate_bucket_access function."""

    def test_validate_bucket_access_empty_paths(self):
        """Test bucket access validation with empty bucket paths."""
        with pytest.raises(ValueError) as exc_info:
            validate_bucket_access([])

        assert 'No S3 bucket paths provided' in str(exc_info.value)

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_validate_bucket_access_all_accessible(self, mock_get_session):
        """Test bucket access validation when all buckets are accessible."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_get_session.return_value = mock_session

        # Mock successful head_bucket calls
        mock_s3_client.head_bucket.return_value = {}

        bucket_paths = ['s3://bucket1/', 's3://bucket2/data/']
        result = validate_bucket_access(bucket_paths)

        assert result == bucket_paths
        assert mock_s3_client.head_bucket.call_count == 2
        mock_s3_client.head_bucket.assert_any_call(Bucket='bucket1')
        mock_s3_client.head_bucket.assert_any_call(Bucket='bucket2')

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_validate_bucket_access_some_inaccessible(self, mock_get_session):
        """Test bucket access validation when some buckets are inaccessible."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_get_session.return_value = mock_session

        # Mock head_bucket calls - first succeeds, second fails
        def head_bucket_side_effect(Bucket):
            if Bucket == 'bucket1':
                return {}
            else:
                raise ClientError({'Error': {'Code': '404', 'Message': 'Not Found'}}, 'HeadBucket')

        mock_s3_client.head_bucket.side_effect = head_bucket_side_effect

        bucket_paths = ['s3://bucket1/', 's3://bucket2/']
        result = validate_bucket_access(bucket_paths)

        assert result == ['s3://bucket1/']
        assert mock_s3_client.head_bucket.call_count == 2

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_validate_bucket_access_all_inaccessible(self, mock_get_session):
        """Test bucket access validation when all buckets are inaccessible."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_get_session.return_value = mock_session

        # Mock head_bucket calls to always fail
        mock_s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': 'Not Found'}}, 'HeadBucket'
        )

        bucket_paths = ['s3://bucket1/', 's3://bucket2/']

        with pytest.raises(ValueError, match='No S3 buckets are accessible'):
            validate_bucket_access(bucket_paths)

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_validate_bucket_access_no_credentials(self, mock_get_session):
        """Test bucket access validation with no AWS credentials."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_get_session.return_value = mock_session

        # Mock head_bucket to raise NoCredentialsError
        mock_s3_client.head_bucket.side_effect = NoCredentialsError()

        bucket_paths = ['s3://bucket1/']

        with pytest.raises(ValueError, match='No S3 buckets are accessible'):
            validate_bucket_access(bucket_paths)

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_validate_bucket_access_access_denied(self, mock_get_session):
        """Test bucket access validation with access denied."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_get_session.return_value = mock_session

        # Mock head_bucket to raise access denied error
        mock_s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '403', 'Message': 'Forbidden'}}, 'HeadBucket'
        )

        bucket_paths = ['s3://bucket1/']

        with pytest.raises(ValueError, match='No S3 buckets are accessible'):
            validate_bucket_access(bucket_paths)

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_validate_bucket_access_mixed_results(self, mock_get_session):
        """Test bucket access validation with mixed success and failure."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_get_session.return_value = mock_session

        # Mock head_bucket calls with different outcomes
        def head_bucket_side_effect(Bucket):
            if Bucket == 'accessible-bucket':
                return {}
            elif Bucket == 'not-found-bucket':
                raise ClientError({'Error': {'Code': '404', 'Message': 'Not Found'}}, 'HeadBucket')
            else:  # forbidden-bucket
                raise ClientError({'Error': {'Code': '403', 'Message': 'Forbidden'}}, 'HeadBucket')

        mock_s3_client.head_bucket.side_effect = head_bucket_side_effect

        bucket_paths = [
            's3://accessible-bucket/',
            's3://not-found-bucket/',
            's3://forbidden-bucket/',
        ]
        result = validate_bucket_access(bucket_paths)

        assert result == ['s3://accessible-bucket/']
        assert mock_s3_client.head_bucket.call_count == 3

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_validate_bucket_access_unexpected_error(self, mock_get_session):
        """Test bucket access validation with unexpected error."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_get_session.return_value = mock_session

        # Mock head_bucket to raise unexpected error
        mock_s3_client.head_bucket.side_effect = Exception('Unexpected error')

        bucket_paths = ['s3://bucket1/']

        with pytest.raises(ValueError, match='No S3 buckets are accessible'):
            validate_bucket_access(bucket_paths)

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_validate_bucket_access_duplicate_buckets(self, mock_get_session):
        """Test bucket access validation with duplicate bucket names."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_get_session.return_value = mock_session

        # Mock successful head_bucket calls
        mock_s3_client.head_bucket.return_value = {}

        bucket_paths = ['s3://bucket1/', 's3://bucket1/data/', 's3://bucket1/results/']
        result = validate_bucket_access(bucket_paths)

        assert result == bucket_paths
        # Should only call head_bucket once for the unique bucket (optimized implementation)
        assert mock_s3_client.head_bucket.call_count == 1
        mock_s3_client.head_bucket.assert_called_with(Bucket='bucket1')

    def test_validate_bucket_access_invalid_s3_path(self):
        """Test bucket access validation with invalid S3 path."""
        bucket_paths = ['invalid-path']

        with pytest.raises(ValueError, match="Invalid S3 path format.*Must start with 's3://'"):
            validate_bucket_access(bucket_paths)

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_validate_bucket_access_mixed_valid_invalid_paths(self, mock_get_session):
        """Test bucket access validation with mix of valid and invalid paths."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_get_session.return_value = mock_session

        # Mock successful head_bucket calls
        mock_s3_client.head_bucket.return_value = {}

        bucket_paths = ['s3://valid-bucket/', 'invalid-path', 's3://another-valid-bucket/data/']
        result = validate_bucket_access(bucket_paths)

        # Should return only the valid paths
        assert result == ['s3://valid-bucket/', 's3://another-valid-bucket/data/']
        # Should call head_bucket for each unique valid bucket
        assert mock_s3_client.head_bucket.call_count == 2
        mock_s3_client.head_bucket.assert_any_call(Bucket='valid-bucket')
        mock_s3_client.head_bucket.assert_any_call(Bucket='another-valid-bucket')

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_validate_bucket_access_other_client_error(self, mock_get_session):
        """Test bucket access validation with other ClientError codes."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3_client
        mock_get_session.return_value = mock_session

        # Mock head_bucket to raise other error code
        mock_s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Internal server error'}}, 'HeadBucket'
        )

        bucket_paths = ['s3://bucket1/']

        with pytest.raises(ValueError, match='No S3 buckets are accessible'):
            validate_bucket_access(bucket_paths)
