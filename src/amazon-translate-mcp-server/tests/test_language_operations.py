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

"""Unit tests for Language Operations."""

import pytest
from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations
from awslabs.amazon_translate_mcp_server.models import (
    AuthenticationError,
    LanguageMetrics,
    LanguagePair,
    ServiceUnavailableError,
    ValidationError,
)
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta
from unittest.mock import Mock


class TestLanguageOperations:
    """Test cases for LanguageOperations class."""

    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create a mock AWS client manager."""
        return Mock()

    @pytest.fixture
    def language_operations(self, mock_aws_client_manager):
        """Create LanguageOperations instance with mocked dependencies."""
        return LanguageOperations(mock_aws_client_manager)

    @pytest.fixture
    def sample_languages_response(self):
        """Sample response from list_languages API."""
        return {
            'Languages': [
                {'LanguageCode': 'en', 'LanguageName': 'English'},
                {'LanguageCode': 'es', 'LanguageName': 'Spanish'},
                {'LanguageCode': 'fr', 'LanguageName': 'French'},
            ]
        }

    def test_init(self, mock_aws_client_manager):
        """Test LanguageOperations initialization."""
        lang_ops = LanguageOperations(mock_aws_client_manager)

        assert lang_ops.aws_client_manager == mock_aws_client_manager
        assert lang_ops._language_cache is None
        assert lang_ops._cache_timestamp is None
        assert lang_ops._cache_ttl == timedelta(hours=24)

    def test_list_language_pairs_success(
        self, language_operations, mock_aws_client_manager, sample_languages_response
    ):
        """Test successful language pairs listing."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = sample_languages_response
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # Execute
        result = language_operations.list_language_pairs()

        # Verify
        assert isinstance(result, list)
        assert len(result) > 0

        # Check that we have pairs for each language combination
        language_codes = ['en', 'es', 'fr']
        expected_pairs = len(language_codes) * (len(language_codes) - 1) + len(
            language_codes
        )  # +auto pairs
        assert len(result) == expected_pairs

        # Verify some specific pairs exist
        pair_tuples = [(p.source_language, p.target_language) for p in result]
        assert ('en', 'es') in pair_tuples
        assert ('es', 'en') in pair_tuples
        assert ('auto', 'en') in pair_tuples

        # Verify first few LanguagePair properties (don't check all to avoid performance issues)
        for pair in result[:5]:
            assert isinstance(pair, LanguagePair)
            assert pair.source_language != pair.target_language
            assert len(pair.supported_formats) > 0
            assert isinstance(pair.custom_terminology_supported, bool)

        # Verify API call
        mock_translate_client.list_languages.assert_called_once_with(
            DisplayLanguageCode='en', MaxResults=500
        )

    def test_list_language_pairs_uses_cache(
        self, language_operations, mock_aws_client_manager, sample_languages_response
    ):
        """Test that language pairs listing uses cache when available."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = sample_languages_response
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # First call - should hit API
        result1 = language_operations.list_language_pairs()

        # Second call - should use cache
        result2 = language_operations.list_language_pairs()

        # Verify
        assert len(result1) == len(result2)
        assert mock_translate_client.list_languages.call_count == 1  # Only called once

    def test_list_language_pairs_cache_expiry(
        self, language_operations, mock_aws_client_manager, sample_languages_response
    ):
        """Test that cache expires after TTL."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = sample_languages_response
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # First call
        language_operations.list_language_pairs()

        # Simulate cache expiry
        language_operations._cache_timestamp = datetime.utcnow() - timedelta(hours=25)

        # Second call - should hit API again
        language_operations.list_language_pairs()

        # Verify
        assert mock_translate_client.list_languages.call_count == 2

    def test_list_language_pairs_access_denied(self, language_operations, mock_aws_client_manager):
        """Test language pairs listing with access denied error."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListLanguages'
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # Execute and verify
        with pytest.raises(AuthenticationError) as exc_info:
            language_operations.list_language_pairs()

        assert 'Access denied when listing languages' in str(exc_info.value)
        assert exc_info.value.details['error_code'] == 'AccessDenied'

    def test_list_language_pairs_service_unavailable(
        self, language_operations, mock_aws_client_manager
    ):
        """Test language pairs listing with service unavailable error."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'ListLanguages',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # Execute and verify
        with pytest.raises(ServiceUnavailableError) as exc_info:
            language_operations.list_language_pairs()

        assert 'Amazon Translate service unavailable' in str(exc_info.value)
        assert exc_info.value.details['error_code'] == 'ServiceUnavailable'

    def test_list_language_pairs_botocore_error(
        self, language_operations, mock_aws_client_manager
    ):
        """Test language pairs listing with BotoCore error."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.side_effect = BotoCoreError()
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # Execute and verify
        with pytest.raises(ServiceUnavailableError) as exc_info:
            language_operations.list_language_pairs()

        assert 'BotoCore error listing languages' in str(exc_info.value)

    def test_get_language_metrics_success(self, language_operations, mock_aws_client_manager):
        """Test successful language metrics retrieval."""
        # Setup mocks
        mock_cloudwatch_client = Mock()
        mock_aws_client_manager.get_cloudwatch_client.return_value = mock_cloudwatch_client

        # Execute
        result = language_operations.get_language_metrics(language_pair='en-es', time_range='24h')

        # Verify
        assert isinstance(result, LanguageMetrics)
        assert result.language_pair == 'en-es'
        assert result.time_range == '24h'
        assert result.translation_count >= 0
        assert result.character_count >= 0

    def test_get_language_metrics_invalid_time_range(self, language_operations):
        """Test language metrics with invalid time range."""
        with pytest.raises(ValidationError) as exc_info:
            language_operations.get_language_metrics(time_range='invalid')

        assert "Invalid time range 'invalid'" in str(exc_info.value)
        assert exc_info.value.details['field'] == 'time_range'

    def test_get_language_metrics_invalid_language_pair(self, language_operations):
        """Test language metrics with invalid language pair format."""
        with pytest.raises(ValidationError) as exc_info:
            language_operations.get_language_metrics(language_pair='invalid_format')

        assert 'Invalid language pair format' in str(exc_info.value)
        assert exc_info.value.details['field'] == 'language_pair'

    def test_get_language_metrics_access_denied(
        self, language_operations, mock_aws_client_manager
    ):
        """Test language metrics with access denied error."""
        # Setup mocks - simulate error during client creation
        mock_aws_client_manager.get_cloudwatch_client.side_effect = AuthenticationError(
            'Access denied when retrieving metrics: Access denied',
            details={'error_code': 'AccessDenied'},
        )

        # Execute and verify
        with pytest.raises(AuthenticationError) as exc_info:
            language_operations.get_language_metrics()

        assert 'Access denied when retrieving metrics' in str(exc_info.value)

    def test_get_supported_formats(self, language_operations):
        """Test getting supported formats."""
        result = language_operations.get_supported_formats()

        assert isinstance(result, list)
        assert len(result) > 0
        assert 'text/plain' in result
        assert 'text/html' in result
        assert 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in result

    def test_validate_language_pair_success(
        self, language_operations, mock_aws_client_manager, sample_languages_response
    ):
        """Test successful language pair validation."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = sample_languages_response
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # Execute
        result = language_operations.validate_language_pair('en', 'es')

        # Verify
        assert result is True

    def test_validate_language_pair_auto_detect(
        self, language_operations, mock_aws_client_manager, sample_languages_response
    ):
        """Test language pair validation with auto-detect."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = sample_languages_response
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # Execute
        result = language_operations.validate_language_pair('auto', 'es')

        # Verify
        assert result is True

    def test_validate_language_pair_unsupported(
        self, language_operations, mock_aws_client_manager, sample_languages_response
    ):
        """Test language pair validation with unsupported pair."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = sample_languages_response
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # Execute
        result = language_operations.validate_language_pair('xx', 'yy')

        # Verify
        assert result is False

    def test_validate_language_pair_empty_languages(self, language_operations):
        """Test language pair validation with empty language codes."""
        with pytest.raises(ValidationError) as exc_info:
            language_operations.validate_language_pair('', 'es')

        assert 'Source and target language codes cannot be empty' in str(exc_info.value)

    def test_validate_language_pair_same_languages(self, language_operations):
        """Test language pair validation with same source and target."""
        with pytest.raises(ValidationError) as exc_info:
            language_operations.validate_language_pair('en', 'en')

        assert 'Source and target languages cannot be the same' in str(exc_info.value)

    def test_is_terminology_supported_true(
        self, language_operations, mock_aws_client_manager, sample_languages_response
    ):
        """Test terminology support check for supported pair."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = sample_languages_response
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # Execute
        result = language_operations.is_terminology_supported('en', 'es')

        # Verify
        assert result is True

    def test_is_terminology_supported_auto_detect(self, language_operations):
        """Test terminology support check with auto-detect (should be False)."""
        result = language_operations.is_terminology_supported('auto', 'es')

        # Verify
        assert result is False

    def test_get_language_name_success(
        self, language_operations, mock_aws_client_manager, sample_languages_response
    ):
        """Test successful language name retrieval."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = sample_languages_response
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # Populate cache
        language_operations.list_language_pairs()

        # Execute
        result = language_operations.get_language_name('en')

        # Verify
        assert result == 'English'

    def test_get_language_name_not_found(
        self, language_operations, mock_aws_client_manager, sample_languages_response
    ):
        """Test language name retrieval for unknown language."""
        # Setup mocks
        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = sample_languages_response
        mock_aws_client_manager.get_translate_client.return_value = mock_translate_client

        # Populate cache
        language_operations.list_language_pairs()

        # Execute
        result = language_operations.get_language_name('xx')

        # Verify
        assert result is None

    def test_is_valid_language_pair_format_valid(self, language_operations):
        """Test valid language pair format validation."""
        assert language_operations._is_valid_language_pair_format('en-es') is True
        assert (
            language_operations._is_valid_language_pair_format('zh-CN-en') is False
        )  # Too many parts

    def test_is_valid_language_pair_format_invalid(self, language_operations):
        """Test invalid language pair format validation."""
        assert language_operations._is_valid_language_pair_format('invalid') is False
        assert language_operations._is_valid_language_pair_format('') is False
        assert language_operations._is_valid_language_pair_format('en-') is False
        assert language_operations._is_valid_language_pair_format('-es') is False

    def test_calculate_start_time(self, language_operations):
        """Test start time calculation for different ranges."""
        end_time = datetime(2023, 1, 1, 12, 0, 0)

        # Test 1 hour
        start_time = language_operations._calculate_start_time(end_time, '1h')
        assert start_time == datetime(2023, 1, 1, 11, 0, 0)

        # Test 24 hours
        start_time = language_operations._calculate_start_time(end_time, '24h')
        assert start_time == datetime(2022, 12, 31, 12, 0, 0)

        # Test 7 days
        start_time = language_operations._calculate_start_time(end_time, '7d')
        assert start_time == datetime(2022, 12, 25, 12, 0, 0)

        # Test 30 days
        start_time = language_operations._calculate_start_time(end_time, '30d')
        assert start_time == datetime(2022, 12, 2, 12, 0, 0)

        # Test invalid range (defaults to 24h)
        start_time = language_operations._calculate_start_time(end_time, 'invalid')
        assert start_time == datetime(2022, 12, 31, 12, 0, 0)

    def test_calculate_supported_pairs(self, language_operations):
        """Test supported pairs calculation."""
        languages = [
            {'LanguageCode': 'en', 'LanguageName': 'English'},
            {'LanguageCode': 'es', 'LanguageName': 'Spanish'},
            {'LanguageCode': 'fr', 'LanguageName': 'French'},
        ]

        result = language_operations._calculate_supported_pairs(languages)

        # Should have all combinations except same-language pairs, plus auto pairs
        expected_pairs = [
            ('en', 'es'),
            ('en', 'fr'),
            ('es', 'en'),
            ('es', 'fr'),
            ('fr', 'en'),
            ('fr', 'es'),
            ('auto', 'en'),
            ('auto', 'es'),
            ('auto', 'fr'),
        ]

        assert len(result) == len(expected_pairs)
        for pair in expected_pairs:
            assert pair in result

    def test_retrieve_cloudwatch_metrics_placeholder(self, language_operations):
        """Test CloudWatch metrics retrieval (placeholder implementation)."""
        mock_client = Mock()
        start_time = datetime.utcnow() - timedelta(hours=24)
        end_time = datetime.utcnow()

        result = language_operations._retrieve_cloudwatch_metrics(
            mock_client, 'en-es', start_time, end_time
        )

        # Verify placeholder response
        assert isinstance(result, dict)
        assert 'translation_count' in result
        assert 'character_count' in result
        assert 'average_response_time' in result
        assert 'error_rate' in result
        assert result['translation_count'] == 0  # Placeholder value
        assert result['character_count'] == 0  # Placeholder value
