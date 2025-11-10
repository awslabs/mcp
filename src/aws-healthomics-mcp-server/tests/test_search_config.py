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

"""Tests for search configuration utilities."""

import os
import pytest
from awslabs.aws_healthomics_mcp_server.models import SearchConfig
from awslabs.aws_healthomics_mcp_server.utils.search_config import (
    get_enable_healthomics_search,
    get_enable_s3_tag_search,
    get_genomics_search_config,
    get_max_concurrent_searches,
    get_max_tag_batch_size,
    get_result_cache_ttl,
    get_s3_bucket_paths,
    get_search_timeout_seconds,
    get_tag_cache_ttl,
    validate_bucket_access_permissions,
)
from unittest.mock import patch


class TestSearchConfig:
    """Test cases for search configuration utilities."""

    def setup_method(self):
        """Set up test environment."""
        # Clear environment variables before each test
        env_vars_to_clear = [
            'GENOMICS_SEARCH_S3_BUCKETS',
            'GENOMICS_SEARCH_MAX_CONCURRENT',
            'GENOMICS_SEARCH_TIMEOUT_SECONDS',
            'GENOMICS_SEARCH_ENABLE_HEALTHOMICS',
            'GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH',
            'GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE',
            'GENOMICS_SEARCH_RESULT_CACHE_TTL',
            'GENOMICS_SEARCH_TAG_CACHE_TTL',
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]

    def test_get_s3_bucket_paths_valid_single_bucket(self):
        """Test getting S3 bucket paths with single valid bucket."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.search_config.validate_and_normalize_s3_path'
        ) as mock_validate:
            mock_validate.return_value = 's3://test-bucket/'
            os.environ['GENOMICS_SEARCH_S3_BUCKETS'] = 's3://test-bucket'

            paths = get_s3_bucket_paths()

            assert paths == ['s3://test-bucket/']
            mock_validate.assert_called_once_with('s3://test-bucket')

    def test_get_s3_bucket_paths_valid_multiple_buckets(self):
        """Test getting S3 bucket paths with multiple valid buckets."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.search_config.validate_and_normalize_s3_path'
        ) as mock_validate:
            mock_validate.side_effect = ['s3://bucket1/', 's3://bucket2/data/']
            os.environ['GENOMICS_SEARCH_S3_BUCKETS'] = 's3://bucket1, s3://bucket2/data'

            paths = get_s3_bucket_paths()

            assert paths == ['s3://bucket1/', 's3://bucket2/data/']
            assert mock_validate.call_count == 2

    def test_get_s3_bucket_paths_empty_env_var(self):
        """Test getting S3 bucket paths with empty environment variable."""
        os.environ['GENOMICS_SEARCH_S3_BUCKETS'] = ''

        with pytest.raises(ValueError, match='No S3 bucket paths configured'):
            get_s3_bucket_paths()

    def test_get_s3_bucket_paths_missing_env_var(self):
        """Test getting S3 bucket paths with missing environment variable."""
        # Environment variable not set
        with pytest.raises(ValueError, match='No S3 bucket paths configured'):
            get_s3_bucket_paths()

    def test_get_s3_bucket_paths_whitespace_only(self):
        """Test getting S3 bucket paths with whitespace-only environment variable."""
        os.environ['GENOMICS_SEARCH_S3_BUCKETS'] = '   ,  ,   '

        with pytest.raises(ValueError, match='No S3 bucket paths configured'):
            get_s3_bucket_paths()

    def test_get_s3_bucket_paths_invalid_path(self):
        """Test getting S3 bucket paths with invalid path."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.search_config.validate_and_normalize_s3_path'
        ) as mock_validate:
            mock_validate.side_effect = ValueError('Invalid S3 path')
            os.environ['GENOMICS_SEARCH_S3_BUCKETS'] = 'invalid-path'

            with pytest.raises(ValueError, match='Invalid S3 bucket path'):
                get_s3_bucket_paths()

    def test_get_max_concurrent_searches_valid_value(self):
        """Test getting max concurrent searches with valid value."""
        os.environ['GENOMICS_SEARCH_MAX_CONCURRENT'] = '15'

        result = get_max_concurrent_searches()

        assert result == 15

    def test_get_max_concurrent_searches_default_value(self):
        """Test getting max concurrent searches with default value."""
        # Environment variable not set
        result = get_max_concurrent_searches()

        assert result == 10  # DEFAULT_GENOMICS_SEARCH_MAX_CONCURRENT

    def test_get_max_concurrent_searches_invalid_value(self):
        """Test getting max concurrent searches with invalid value."""
        os.environ['GENOMICS_SEARCH_MAX_CONCURRENT'] = 'invalid'

        result = get_max_concurrent_searches()

        assert result == 10  # Should return default

    def test_get_max_concurrent_searches_zero_value(self):
        """Test getting max concurrent searches with zero value."""
        os.environ['GENOMICS_SEARCH_MAX_CONCURRENT'] = '0'

        result = get_max_concurrent_searches()

        assert result == 10  # Should return default for invalid value

    def test_get_max_concurrent_searches_negative_value(self):
        """Test getting max concurrent searches with negative value."""
        os.environ['GENOMICS_SEARCH_MAX_CONCURRENT'] = '-5'

        result = get_max_concurrent_searches()

        assert result == 10  # Should return default for invalid value

    def test_get_search_timeout_seconds_valid_value(self):
        """Test getting search timeout with valid value."""
        os.environ['GENOMICS_SEARCH_TIMEOUT_SECONDS'] = '600'

        result = get_search_timeout_seconds()

        assert result == 600

    def test_get_search_timeout_seconds_default_value(self):
        """Test getting search timeout with default value."""
        # Environment variable not set
        result = get_search_timeout_seconds()

        assert result == 300  # DEFAULT_GENOMICS_SEARCH_TIMEOUT

    def test_get_search_timeout_seconds_invalid_value(self):
        """Test getting search timeout with invalid value."""
        os.environ['GENOMICS_SEARCH_TIMEOUT_SECONDS'] = 'invalid'

        result = get_search_timeout_seconds()

        assert result == 300  # Should return default

    def test_get_search_timeout_seconds_zero_value(self):
        """Test getting search timeout with zero value."""
        os.environ['GENOMICS_SEARCH_TIMEOUT_SECONDS'] = '0'

        result = get_search_timeout_seconds()

        assert result == 300  # Should return default for invalid value

    def test_get_search_timeout_seconds_negative_value(self):
        """Test getting search timeout with negative value."""
        os.environ['GENOMICS_SEARCH_TIMEOUT_SECONDS'] = '-100'

        result = get_search_timeout_seconds()

        assert result == 300  # Should return default for invalid value

    def test_get_enable_healthomics_search_true_values(self):
        """Test getting HealthOmics search enablement with various true values."""
        true_values = ['true', 'True', 'TRUE', '1', 'yes', 'YES', 'on', 'ON', 'enabled', 'ENABLED']

        for value in true_values:
            os.environ['GENOMICS_SEARCH_ENABLE_HEALTHOMICS'] = value
            result = get_enable_healthomics_search()
            assert result is True, f'Failed for value: {value}'

    def test_get_enable_healthomics_search_false_values(self):
        """Test getting HealthOmics search enablement with various false values."""
        false_values = [
            'false',
            'False',
            'FALSE',
            '0',
            'no',
            'NO',
            'off',
            'OFF',
            'disabled',
            'DISABLED',
        ]

        for value in false_values:
            os.environ['GENOMICS_SEARCH_ENABLE_HEALTHOMICS'] = value
            result = get_enable_healthomics_search()
            assert result is False, f'Failed for value: {value}'

    def test_get_enable_healthomics_search_default_value(self):
        """Test getting HealthOmics search enablement with default value."""
        # Environment variable not set
        result = get_enable_healthomics_search()

        assert result is True  # DEFAULT_GENOMICS_SEARCH_ENABLE_HEALTHOMICS

    def test_get_enable_healthomics_search_invalid_value(self):
        """Test getting HealthOmics search enablement with invalid value."""
        os.environ['GENOMICS_SEARCH_ENABLE_HEALTHOMICS'] = 'maybe'

        result = get_enable_healthomics_search()

        assert result is True  # Should return default

    def test_get_enable_s3_tag_search_true_values(self):
        """Test getting S3 tag search enablement with various true values."""
        true_values = ['true', 'True', 'TRUE', '1', 'yes', 'YES', 'on', 'ON', 'enabled', 'ENABLED']

        for value in true_values:
            os.environ['GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH'] = value
            result = get_enable_s3_tag_search()
            assert result is True, f'Failed for value: {value}'

    def test_get_enable_s3_tag_search_false_values(self):
        """Test getting S3 tag search enablement with various false values."""
        false_values = [
            'false',
            'False',
            'FALSE',
            '0',
            'no',
            'NO',
            'off',
            'OFF',
            'disabled',
            'DISABLED',
        ]

        for value in false_values:
            os.environ['GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH'] = value
            result = get_enable_s3_tag_search()
            assert result is False, f'Failed for value: {value}'

    def test_get_enable_s3_tag_search_default_value(self):
        """Test getting S3 tag search enablement with default value."""
        # Environment variable not set
        result = get_enable_s3_tag_search()

        assert result is True  # DEFAULT_GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH

    def test_get_enable_s3_tag_search_invalid_value(self):
        """Test getting S3 tag search enablement with invalid value."""
        os.environ['GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH'] = 'maybe'

        result = get_enable_s3_tag_search()

        assert result is True  # Should return default

    def test_get_max_tag_batch_size_valid_value(self):
        """Test getting max tag batch size with valid value."""
        os.environ['GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE'] = '200'

        result = get_max_tag_batch_size()

        assert result == 200

    def test_get_max_tag_batch_size_default_value(self):
        """Test getting max tag batch size with default value."""
        # Environment variable not set
        result = get_max_tag_batch_size()

        assert result == 100  # DEFAULT_GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE

    def test_get_max_tag_batch_size_invalid_value(self):
        """Test getting max tag batch size with invalid value."""
        os.environ['GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE'] = 'invalid'

        result = get_max_tag_batch_size()

        assert result == 100  # Should return default

    def test_get_max_tag_batch_size_zero_value(self):
        """Test getting max tag batch size with zero value."""
        os.environ['GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE'] = '0'

        result = get_max_tag_batch_size()

        assert result == 100  # Should return default for invalid value

    def test_get_result_cache_ttl_valid_value(self):
        """Test getting result cache TTL with valid value."""
        os.environ['GENOMICS_SEARCH_RESULT_CACHE_TTL'] = '1200'

        result = get_result_cache_ttl()

        assert result == 1200

    def test_get_result_cache_ttl_default_value(self):
        """Test getting result cache TTL with default value."""
        # Environment variable not set
        result = get_result_cache_ttl()

        assert result == 600  # DEFAULT_GENOMICS_SEARCH_RESULT_CACHE_TTL

    def test_get_result_cache_ttl_invalid_value(self):
        """Test getting result cache TTL with invalid value."""
        os.environ['GENOMICS_SEARCH_RESULT_CACHE_TTL'] = 'invalid'

        result = get_result_cache_ttl()

        assert result == 600  # Should return default

    def test_get_result_cache_ttl_negative_value(self):
        """Test getting result cache TTL with negative value."""
        os.environ['GENOMICS_SEARCH_RESULT_CACHE_TTL'] = '-100'

        result = get_result_cache_ttl()

        assert result == 600  # Should return default for invalid value

    def test_get_result_cache_ttl_zero_value(self):
        """Test getting result cache TTL with zero value (valid)."""
        os.environ['GENOMICS_SEARCH_RESULT_CACHE_TTL'] = '0'

        result = get_result_cache_ttl()

        assert result == 0  # Zero is valid for cache TTL (disables caching)

    def test_get_tag_cache_ttl_valid_value(self):
        """Test getting tag cache TTL with valid value."""
        os.environ['GENOMICS_SEARCH_TAG_CACHE_TTL'] = '900'

        result = get_tag_cache_ttl()

        assert result == 900

    def test_get_tag_cache_ttl_default_value(self):
        """Test getting tag cache TTL with default value."""
        # Environment variable not set
        result = get_tag_cache_ttl()

        assert result == 300  # DEFAULT_GENOMICS_SEARCH_TAG_CACHE_TTL

    def test_get_tag_cache_ttl_invalid_value(self):
        """Test getting tag cache TTL with invalid value."""
        os.environ['GENOMICS_SEARCH_TAG_CACHE_TTL'] = 'invalid'

        result = get_tag_cache_ttl()

        assert result == 300  # Should return default

    def test_get_tag_cache_ttl_negative_value(self):
        """Test getting tag cache TTL with negative value."""
        os.environ['GENOMICS_SEARCH_TAG_CACHE_TTL'] = '-50'

        result = get_tag_cache_ttl()

        assert result == 300  # Should return default for invalid value

    def test_get_tag_cache_ttl_zero_value(self):
        """Test getting tag cache TTL with zero value (valid)."""
        os.environ['GENOMICS_SEARCH_TAG_CACHE_TTL'] = '0'

        result = get_tag_cache_ttl()

        assert result == 0  # Zero is valid for cache TTL (disables caching)

    @patch('awslabs.aws_healthomics_mcp_server.utils.search_config.validate_and_normalize_s3_path')
    def test_get_genomics_search_config_complete(self, mock_validate):
        """Test getting complete genomics search configuration."""
        mock_validate.return_value = 's3://test-bucket/'

        # Set all environment variables
        os.environ['GENOMICS_SEARCH_S3_BUCKETS'] = 's3://test-bucket'
        os.environ['GENOMICS_SEARCH_MAX_CONCURRENT'] = '15'
        os.environ['GENOMICS_SEARCH_TIMEOUT_SECONDS'] = '600'
        os.environ['GENOMICS_SEARCH_ENABLE_HEALTHOMICS'] = 'true'
        os.environ['GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH'] = 'false'
        os.environ['GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE'] = '200'
        os.environ['GENOMICS_SEARCH_RESULT_CACHE_TTL'] = '1200'
        os.environ['GENOMICS_SEARCH_TAG_CACHE_TTL'] = '900'

        config = get_genomics_search_config()

        assert isinstance(config, SearchConfig)
        assert config.s3_bucket_paths == ['s3://test-bucket/']
        assert config.max_concurrent_searches == 15
        assert config.search_timeout_seconds == 600
        assert config.enable_healthomics_search is True
        assert config.enable_s3_tag_search is False
        assert config.max_tag_retrieval_batch_size == 200
        assert config.result_cache_ttl_seconds == 1200
        assert config.tag_cache_ttl_seconds == 900

    @patch('awslabs.aws_healthomics_mcp_server.utils.search_config.validate_and_normalize_s3_path')
    def test_get_genomics_search_config_defaults(self, mock_validate):
        """Test getting genomics search configuration with default values."""
        mock_validate.return_value = 's3://test-bucket/'
        os.environ['GENOMICS_SEARCH_S3_BUCKETS'] = 's3://test-bucket'

        config = get_genomics_search_config()

        assert isinstance(config, SearchConfig)
        assert config.s3_bucket_paths == ['s3://test-bucket/']
        assert config.max_concurrent_searches == 10
        assert config.search_timeout_seconds == 300
        assert config.enable_healthomics_search is True
        assert config.enable_s3_tag_search is True
        assert config.max_tag_retrieval_batch_size == 100
        assert config.result_cache_ttl_seconds == 600
        assert config.tag_cache_ttl_seconds == 300

    def test_get_genomics_search_config_missing_buckets(self):
        """Test getting genomics search configuration with missing S3 buckets."""
        # No S3 buckets configured
        with pytest.raises(ValueError, match='No S3 bucket paths configured'):
            get_genomics_search_config()

    @patch('awslabs.aws_healthomics_mcp_server.utils.search_config.get_genomics_search_config')
    @patch('awslabs.aws_healthomics_mcp_server.utils.search_config.validate_bucket_access')
    def test_validate_bucket_access_permissions_success(
        self, mock_validate_access, mock_get_config
    ):
        """Test successful bucket access validation."""
        # Mock configuration
        mock_config = SearchConfig(
            s3_bucket_paths=['s3://bucket1/', 's3://bucket2/'],
            max_concurrent_searches=10,
            search_timeout_seconds=300,
            enable_healthomics_search=True,
            enable_s3_tag_search=True,
            max_tag_retrieval_batch_size=100,
            result_cache_ttl_seconds=600,
            tag_cache_ttl_seconds=300,
        )
        mock_get_config.return_value = mock_config
        mock_validate_access.return_value = ['s3://bucket1/', 's3://bucket2/']

        result = validate_bucket_access_permissions()

        assert result == ['s3://bucket1/', 's3://bucket2/']
        mock_validate_access.assert_called_once_with(['s3://bucket1/', 's3://bucket2/'])

    @patch('awslabs.aws_healthomics_mcp_server.utils.search_config.get_genomics_search_config')
    def test_validate_bucket_access_permissions_config_error(self, mock_get_config):
        """Test bucket access validation with configuration error."""
        mock_get_config.side_effect = ValueError('Configuration error')

        with pytest.raises(ValueError, match='Configuration error'):
            validate_bucket_access_permissions()

    @patch('awslabs.aws_healthomics_mcp_server.utils.search_config.get_genomics_search_config')
    @patch('awslabs.aws_healthomics_mcp_server.utils.search_config.validate_bucket_access')
    def test_validate_bucket_access_permissions_access_error(
        self, mock_validate_access, mock_get_config
    ):
        """Test bucket access validation with access error."""
        # Mock configuration
        mock_config = SearchConfig(
            s3_bucket_paths=['s3://bucket1/'],
            max_concurrent_searches=10,
            search_timeout_seconds=300,
            enable_healthomics_search=True,
            enable_s3_tag_search=True,
            max_tag_retrieval_batch_size=100,
            result_cache_ttl_seconds=600,
            tag_cache_ttl_seconds=300,
        )
        mock_get_config.return_value = mock_config
        mock_validate_access.side_effect = ValueError('No accessible buckets')

        with pytest.raises(ValueError, match='No accessible buckets'):
            validate_bucket_access_permissions()

    def test_integration_workflow(self):
        """Test complete integration workflow with realistic configuration."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.search_config.validate_and_normalize_s3_path'
        ) as mock_validate:
            with patch(
                'awslabs.aws_healthomics_mcp_server.utils.search_config.validate_bucket_access'
            ) as mock_access:
                # Setup mocks
                mock_validate.side_effect = [
                    's3://genomics-data/',
                    's3://results-bucket/output/',
                    's3://genomics-data/',
                    's3://results-bucket/output/',
                ]
                mock_access.return_value = ['s3://genomics-data/', 's3://results-bucket/output/']

                # Set realistic environment variables
                os.environ['GENOMICS_SEARCH_S3_BUCKETS'] = (
                    's3://genomics-data, s3://results-bucket/output'
                )
                os.environ['GENOMICS_SEARCH_MAX_CONCURRENT'] = '20'
                os.environ['GENOMICS_SEARCH_TIMEOUT_SECONDS'] = '900'
                os.environ['GENOMICS_SEARCH_ENABLE_HEALTHOMICS'] = 'yes'
                os.environ['GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH'] = 'on'
                os.environ['GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE'] = '150'
                os.environ['GENOMICS_SEARCH_RESULT_CACHE_TTL'] = '1800'
                os.environ['GENOMICS_SEARCH_TAG_CACHE_TTL'] = '600'

                # Test complete workflow
                config = get_genomics_search_config()
                accessible_buckets = validate_bucket_access_permissions()

                # Verify configuration
                assert config.s3_bucket_paths == [
                    's3://genomics-data/',
                    's3://results-bucket/output/',
                ]
                assert config.max_concurrent_searches == 20
                assert config.search_timeout_seconds == 900
                assert config.enable_healthomics_search is True
                assert config.enable_s3_tag_search is True
                assert config.max_tag_retrieval_batch_size == 150
                assert config.result_cache_ttl_seconds == 1800
                assert config.tag_cache_ttl_seconds == 600

                # Verify bucket access validation
                assert accessible_buckets == ['s3://genomics-data/', 's3://results-bucket/output/']
