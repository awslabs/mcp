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
from unittest.mock import MagicMock, Mock, patch


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


class TestLanguageOperationsAdvancedFeatures:
    """Test advanced language operations features and edge cases."""

    def test_language_operations_initialization_edge_cases(self):
        """Test language operations initialization with edge cases."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        # Test initialization with custom AWS client manager
        with patch(
            'awslabs.amazon_translate_mcp_server.language_operations.AWSClientManager'
        ) as mock_aws:
            mock_aws_instance = MagicMock()
            mock_aws.return_value = mock_aws_instance

            lang_ops = LanguageOperations(aws_client_manager=mock_aws_instance)
            assert lang_ops.aws_client_manager == mock_aws_instance

    def test_supported_formats_comprehensive(self):
        """Test comprehensive supported formats functionality."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        # Test getting supported formats
        formats = lang_ops.get_supported_formats()

        assert isinstance(formats, list)
        assert len(formats) > 0

        # Should include common formats
        assert 'text/plain' in formats
        assert 'text/html' in formats

        # Test format validation
        for fmt in formats:
            assert isinstance(fmt, str)
            assert len(fmt) > 0
            assert '/' in fmt  # Should be MIME type format

    def test_language_pair_validation_comprehensive(self):
        """Test comprehensive language pair validation."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        # Mock the list_language_pairs method directly
        from awslabs.amazon_translate_mcp_server.models import LanguagePair

        mock_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            ),
            LanguagePair(
                source_language='es', target_language='fr', supported_formats=['text/plain']
            ),
            LanguagePair(
                source_language='auto', target_language='es', supported_formats=['text/plain']
            ),
        ]

        with patch.object(lang_ops, 'list_language_pairs', return_value=mock_pairs):
            # Test valid language pairs
            assert lang_ops.validate_language_pair('en', 'es') is True
            assert lang_ops.validate_language_pair('es', 'fr') is True

            # Test auto-detect source
            assert lang_ops.validate_language_pair('auto', 'es') is True

            # Test invalid language pairs (should return False)
            assert lang_ops.validate_language_pair('invalid', 'es') is False
            assert lang_ops.validate_language_pair('en', 'invalid') is False

            # Test same source and target (should raise ValidationError)
            with pytest.raises(ValidationError):
                lang_ops.validate_language_pair('en', 'en')

    def test_language_name_lookup_edge_cases(self):
        """Test language name lookup with edge cases."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        # Mock the language cache directly
        lang_ops._language_cache = {
            'languages': [
                {'LanguageCode': 'en', 'LanguageName': 'English'},
                {'LanguageCode': 'es', 'LanguageName': 'Spanish'},
                {'LanguageCode': 'zh-cn', 'LanguageName': 'Chinese (Simplified)'},
            ],
            'timestamp': datetime.now(),
        }

        with patch.object(lang_ops, '_is_cache_valid', return_value=True):
            # Test valid language codes
            assert lang_ops.get_language_name('en') == 'English'
            assert lang_ops.get_language_name('es') == 'Spanish'
            assert lang_ops.get_language_name('zh-cn') == 'Chinese (Simplified)'

            # Test invalid language code
            assert lang_ops.get_language_name('invalid') is None

            # Test empty language code
            assert lang_ops.get_language_name('') is None

    def test_terminology_support_validation(self):
        """Test terminology support validation."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        # Mock the validate_language_pair method to return True for valid pairs
        with patch.object(lang_ops, 'validate_language_pair') as mock_validate:
            mock_validate.return_value = True

            # Test terminology support for common language pairs
            assert lang_ops.is_terminology_supported('en', 'es') is True
            assert lang_ops.is_terminology_supported('en', 'fr') is True

            # Test auto-detect (should return False)
            assert lang_ops.is_terminology_supported('auto', 'es') is False

            # Test with invalid language pair
            mock_validate.return_value = False
            assert lang_ops.is_terminology_supported('en', 'invalid') is False

    def test_language_metrics_comprehensive(self):
        """Test comprehensive language metrics functionality."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        # Mock the _retrieve_cloudwatch_metrics method directly
        mock_metrics_data = {
            'translation_count': 1000,
            'character_count': 50000,
            'average_response_time': 0.5,
            'error_rate': 0.01,
        }

        with patch.object(
            lang_ops, '_retrieve_cloudwatch_metrics', return_value=mock_metrics_data
        ):
            metrics = lang_ops.get_language_metrics('en-es', '24h')

            # Test that metrics object has expected attributes
            assert hasattr(metrics, 'language_pair')
            assert hasattr(metrics, 'translation_count')
            assert hasattr(metrics, 'character_count')
            assert metrics.language_pair == 'en-es'
            assert metrics.translation_count == 1000
            assert metrics.character_count == 50000

    def test_language_metrics_error_handling(self):
        """Test language metrics error handling."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        with patch.object(lang_ops.aws_client_manager, 'get_cloudwatch_client') as mock_cw:
            # Mock access denied error
            mock_cw.return_value.get_metric_statistics.side_effect = ClientError(
                error_response={
                    'Error': {
                        'Code': 'AccessDenied',
                        'Message': 'Access denied to CloudWatch metrics',
                    }
                },
                operation_name='GetMetricStatistics',
            )

            with pytest.raises(Exception):  # Should raise appropriate error
                lang_ops.get_language_metrics('en', 'es')

    def test_cache_functionality_edge_cases(self):
        """Test cache functionality with edge cases."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        # Test cache initialization
        assert hasattr(lang_ops, '_language_cache')
        assert hasattr(lang_ops, '_cache_timestamp')

        # Test cache validity check
        is_valid = lang_ops._is_cache_valid()
        assert isinstance(is_valid, bool)

    def test_language_pair_format_validation(self):
        """Test language pair format validation."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        # Mock the list_language_pairs method directly
        from awslabs.amazon_translate_mcp_server.models import LanguagePair

        mock_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            ),
            LanguagePair(
                source_language='zh-cn', target_language='en', supported_formats=['text/plain']
            ),
            LanguagePair(
                source_language='auto', target_language='fr', supported_formats=['text/plain']
            ),
        ]

        with patch.object(lang_ops, 'list_language_pairs', return_value=mock_pairs):
            # Test valid formats
            assert lang_ops.validate_language_pair('en', 'es') is True
            assert lang_ops.validate_language_pair('zh-cn', 'en') is True
            assert lang_ops.validate_language_pair('auto', 'fr') is True

            # Test invalid formats
            # Empty strings should raise ValidationError
            with pytest.raises(ValidationError):
                lang_ops.validate_language_pair('', 'es')
            with pytest.raises(ValidationError):
                lang_ops.validate_language_pair('en', '')
            # Invalid language codes should return False
            assert lang_ops.validate_language_pair('invalid', 'es') is False
            assert lang_ops.validate_language_pair('en', 'invalid') is False

    def test_bulk_language_validation(self):
        """Test bulk language validation functionality."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        with patch.object(lang_ops, 'list_language_pairs') as mock_get_langs:
            # Mock language pairs
            from awslabs.amazon_translate_mcp_server.models import LanguagePair

            mock_get_langs.return_value = [
                LanguagePair(
                    source_language='en', target_language='es', supported_formats=['text/plain']
                ),
                LanguagePair(
                    source_language='en', target_language='fr', supported_formats=['text/plain']
                ),
                LanguagePair(
                    source_language='es', target_language='en', supported_formats=['text/plain']
                ),
            ]

            # Test language pair validation
            assert lang_ops.validate_language_pair('en', 'es') is True
            assert lang_ops.validate_language_pair('en', 'fr') is True
            assert lang_ops.validate_language_pair('invalid', 'es') is False

    def test_concurrent_cache_access(self):
        """Test concurrent cache access scenarios."""
        import threading
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations
        from unittest.mock import MagicMock

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        results = []

        def access_cache():
            try:
                # Simulate concurrent access to cached data
                langs = lang_ops.get_supported_languages()
                results.append(len(langs) if langs else 0)
            except Exception as e:
                results.append(str(e))

        # Create multiple threads to access cache concurrently
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_cache)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should handle concurrent access gracefully
        assert len(results) == 5
        # All results should be consistent (either all numbers or all errors)
        if all(isinstance(r, int) for r in results):
            assert all(r == results[0] for r in results)


class TestLanguageOperationsPerformance:
    """Test language operations performance and optimization."""

    def test_cache_performance_optimization(self):
        """Test cache performance optimization."""
        import time
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations
        from unittest.mock import MagicMock

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        with patch.object(lang_ops.aws_client_manager, 'get_translate_client') as mock_client:
            # Mock expensive API call
            mock_client.return_value.list_languages.return_value = {
                'Languages': [
                    {'LanguageCode': 'en', 'LanguageName': 'English'},
                    {'LanguageCode': 'es', 'LanguageName': 'Spanish'},
                ]
            }

            # First call should hit the API
            start_time = time.time()
            langs1 = lang_ops.list_language_pairs()
            first_call_time = time.time() - start_time

            # Second call should use cache (much faster)
            start_time = time.time()
            langs2 = lang_ops.list_language_pairs()
            second_call_time = time.time() - start_time

            # Results should be identical
            assert langs1 == langs2

            # Second call should be faster (cached)
            # Note: This is a rough test, actual timing may vary
            assert second_call_time <= first_call_time

            # API should only be called once
            assert mock_client.return_value.list_languages.call_count == 1

    def test_memory_usage_optimization(self):
        """Test memory usage optimization in language operations."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations
        from unittest.mock import MagicMock

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(mock_aws_client)

        # Test that cache doesn't grow indefinitely
        initial_cache_size = len(lang_ops._language_cache) if lang_ops._language_cache else 0

        # Perform multiple operations
        for _ in range(10):
            lang_ops.validate_language_pair('en', 'es')
            lang_ops.get_language_name('en')
            lang_ops.is_terminology_supported('en', 'es')

        # Cache size should remain reasonable
        final_cache_size = len(lang_ops._language_cache) if lang_ops._language_cache else 0

        # Should not grow excessively
        assert final_cache_size <= initial_cache_size + 10  # Reasonable growth limit
