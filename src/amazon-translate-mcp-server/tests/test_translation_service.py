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

"""Unit tests for Translation Service.

This module contains comprehensive unit tests for the TranslationService class,
including tests for text translation, language detection, translation validation,
error handling, and retry logic.
"""

import pytest
from awslabs.amazon_translate_mcp_server.aws_client import AWSClientManager
from awslabs.amazon_translate_mcp_server.models import (
    AuthenticationError,
    LanguageDetectionResult,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
    TranslationError,
    TranslationResult,
    ValidationError,
    ValidationResult,
)
from awslabs.amazon_translate_mcp_server.translation_service import TranslationService
from botocore.exceptions import BotoCoreError, ClientError
from unittest.mock import Mock, call, patch


class TestTranslationService:
    """Test cases for TranslationService class."""

    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create a mock AWS client manager."""
        manager = Mock(spec=AWSClientManager)
        translate_client = Mock()
        manager.get_translate_client.return_value = translate_client
        return manager

    @pytest.fixture
    def translation_service(self, mock_aws_client_manager):
        """Create a TranslationService instance with mocked dependencies."""
        return TranslationService(
            aws_client_manager=mock_aws_client_manager,
            max_text_length=1000,
            max_retries=2,
            base_delay=0.1,
            max_delay=1.0,
            jitter=False,  # Disable jitter for predictable tests
        )

    def test_init(self, mock_aws_client_manager):
        """Test TranslationService initialization."""
        service = TranslationService(
            aws_client_manager=mock_aws_client_manager,
            max_text_length=5000,
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0,
            jitter=True,
        )

        assert service._aws_client_manager == mock_aws_client_manager
        assert service._max_text_length == 5000
        assert service._max_retries == 5
        assert service._base_delay == 2.0
        assert service._max_delay == 30.0
        assert service._jitter is True

    def test_translate_text_success(self, translation_service, mock_aws_client_manager):
        """Test successful text translation."""
        # Mock successful translation response
        mock_response = {
            'TranslatedText': 'Hola mundo',
            'SourceLanguageCode': 'en',
            'TargetLanguageCode': 'es',
            'AppliedTerminologies': [{'Name': 'tech-terms'}],
            'AppliedSettings': {'Formality': 'FORMAL'},
        }

        translate_client = mock_aws_client_manager.get_translate_client.return_value
        translate_client.translate_text.return_value = mock_response

        # Execute translation
        result = translation_service.translate_text(
            text='Hello world',
            source_language='en',
            target_language='es',
            terminology_names=['tech-terms'],
            settings={'Formality': 'FORMAL'},
        )

        # Verify result
        assert isinstance(result, TranslationResult)
        assert result.translated_text == 'Hola mundo'
        assert result.source_language == 'en'
        assert result.target_language == 'es'
        assert result.applied_terminologies == ['tech-terms']

        # Verify API call
        translate_client.translate_text.assert_called_once_with(
            Text='Hello world',
            SourceLanguageCode='en',
            TargetLanguageCode='es',
            TerminologyNames=['tech-terms'],
            Settings={'Formality': 'FORMAL'},
        )

    def test_translate_text_auto_detect(self, translation_service, mock_aws_client_manager):
        """Test text translation with automatic language detection."""
        translate_client = mock_aws_client_manager.get_translate_client.return_value

        # Mock language detection response (using dummy translation for detection)
        detect_response = {
            'TranslatedText': 'Hello world',
            'SourceLanguageCode': 'en',
            'TargetLanguageCode': 'en',
            'AppliedTerminologies': [],
            'AppliedSettings': {},
        }

        # Mock actual translation response
        translate_response = {
            'TranslatedText': 'Hola mundo',
            'SourceLanguageCode': 'en',
            'TargetLanguageCode': 'es',
            'AppliedTerminologies': [],
            'AppliedSettings': {},
        }

        # Set up side_effect to return different responses for different calls
        translate_client.translate_text.side_effect = [detect_response, translate_response]

        # Execute translation with auto-detection
        result = translation_service.translate_text(
            text='Hello world', source_language='auto', target_language='es'
        )

        # Verify language detection was called (first call with auto->en for detection)
        expected_calls = [
            call(Text='Hello world', SourceLanguageCode='auto', TargetLanguageCode='en'),
            call(Text='Hello world', SourceLanguageCode='en', TargetLanguageCode='es'),
        ]
        translate_client.translate_text.assert_has_calls(expected_calls)

        # Verify result
        assert result.source_language == 'en'
        assert result.target_language == 'es'
        assert result.translated_text == 'Hola mundo'

    def test_translate_text_validation_errors(self, translation_service):
        """Test translation input validation errors."""
        # Empty text
        with pytest.raises(ValidationError) as exc_info:
            translation_service.translate_text('', 'en', 'es')
        assert 'Text cannot be empty' in str(exc_info.value)
        assert exc_info.value.details.get('field') == 'text'

        # Text too long
        long_text = 'a' * 1001  # Exceeds max_text_length of 1000
        with pytest.raises(ValidationError) as exc_info:
            translation_service.translate_text(long_text, 'en', 'es')
        assert 'exceeds maximum allowed length' in str(exc_info.value)

        # Empty source language
        with pytest.raises(ValidationError) as exc_info:
            translation_service.translate_text('Hello', '', 'es')
        assert 'Source language cannot be empty' in str(exc_info.value)

        # Empty target language
        with pytest.raises(ValidationError) as exc_info:
            translation_service.translate_text('Hello', 'en', '')
        assert 'Target language cannot be empty' in str(exc_info.value)

        # Invalid language code format
        with pytest.raises(ValidationError) as exc_info:
            translation_service.translate_text('Hello', 'english', 'es')
        assert 'Invalid source language code format' in str(exc_info.value)

        # Same source and target language
        with pytest.raises(ValidationError) as exc_info:
            translation_service.translate_text('Hello', 'en', 'en')
        assert 'Source and target languages cannot be the same' in str(exc_info.value)

    def test_detect_language_success(self, translation_service, mock_aws_client_manager):
        """Test successful language detection."""
        # Mock detection response (using dummy translation for detection)
        mock_response = {
            'TranslatedText': 'Hello world',
            'SourceLanguageCode': 'en',
            'TargetLanguageCode': 'en',
            'AppliedTerminologies': [],
            'AppliedSettings': {},
        }

        translate_client = mock_aws_client_manager.get_translate_client.return_value
        translate_client.translate_text.return_value = mock_response

        # Execute detection
        result = translation_service.detect_language('Hello world')

        # Verify result
        assert isinstance(result, LanguageDetectionResult)
        assert result.detected_language == 'en'
        assert result.confidence_score == 0.95
        assert len(result.alternative_languages) == 0  # No alternatives from translate method

        # Verify API call (using dummy translation for detection)
        translate_client.translate_text.assert_called_once_with(
            Text='Hello world', SourceLanguageCode='auto', TargetLanguageCode='en'
        )

    def test_detect_language_validation_errors(self, translation_service):
        """Test language detection input validation errors."""
        # Empty text
        with pytest.raises(ValidationError) as exc_info:
            translation_service.detect_language('')
        assert 'Text cannot be empty' in str(exc_info.value)

        # Text too long
        long_text = 'a' * 1001
        with pytest.raises(ValidationError) as exc_info:
            translation_service.detect_language(long_text)
        assert 'exceeds maximum allowed length' in str(exc_info.value)

    def test_detect_language_no_languages_detected(
        self, translation_service, mock_aws_client_manager
    ):
        """Test language detection when no languages are detected."""
        # Mock response without SourceLanguageCode
        mock_response = {
            'TranslatedText': 'Hello world',
            'TargetLanguageCode': 'en',
            'AppliedTerminologies': [],
            'AppliedSettings': {},
            # Missing SourceLanguageCode to simulate detection failure
        }

        translate_client = mock_aws_client_manager.get_translate_client.return_value
        translate_client.translate_text.return_value = mock_response

        # Execute detection
        with pytest.raises(TranslationError) as exc_info:
            translation_service.detect_language('Hello world')

        assert 'No source language detected' in str(exc_info.value)

    def test_validate_translation_success(self, translation_service):
        """Test successful translation validation."""
        result = translation_service.validate_translation(
            original_text='Hello world',
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
        )

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.quality_score == 1.0
        assert len(result.issues) == 0
        assert len(result.suggestions) == 0

    def test_validate_translation_length_issues(self, translation_service):
        """Test translation validation with length issues."""
        # Test very short translation
        result = translation_service.validate_translation(
            original_text='This is a very long sentence with many words',
            translated_text='Short',
            source_language='en',
            target_language='es',
        )

        assert result.is_valid is False
        assert result.quality_score < 1.0
        assert any('significantly shorter' in issue for issue in result.issues)
        assert any('completeness' in suggestion for suggestion in result.suggestions)

        # Test very long translation
        result = translation_service.validate_translation(
            original_text='Short',
            translated_text='This is a very very very very very very very very very very long translation',
            source_language='en',
            target_language='es',
        )

        assert result.is_valid is False
        assert result.quality_score < 1.0
        assert any('significantly longer' in issue for issue in result.issues)

    def test_validate_translation_identical_text(self, translation_service):
        """Test validation when translation is identical to original."""
        result = translation_service.validate_translation(
            original_text='Hello world',
            translated_text='Hello world',
            source_language='en',
            target_language='es',
        )

        assert result.is_valid is False
        assert result.quality_score <= 0.5
        assert any('identical to original' in issue for issue in result.issues)

    def test_validate_translation_html_entities(self, translation_service):
        """Test validation with HTML entities."""
        result = translation_service.validate_translation(
            original_text='Hello world',
            translated_text='Hola &lt;mundo&gt; &amp; amigos',
            source_language='en',
            target_language='es',
        )

        assert any('HTML entities' in issue for issue in result.issues)
        assert any('decode HTML entities' in suggestion for suggestion in result.suggestions)

    def test_validate_translation_repetitive_patterns(self, translation_service):
        """Test validation with repetitive patterns."""
        result = translation_service.validate_translation(
            original_text='Hello world and friends',
            translated_text='mundo mundo mundo mundo mundo mundo mundo mundo',
            source_language='en',
            target_language='es',
        )

        assert result.is_valid is False
        assert any('repetitive patterns' in issue for issue in result.issues)

    def test_validate_translation_input_validation(self, translation_service):
        """Test validation input parameter validation."""
        # Empty original text
        with pytest.raises(ValidationError):
            translation_service.validate_translation('', 'translated', 'en', 'es')

        # Empty translated text
        with pytest.raises(ValidationError):
            translation_service.validate_translation('original', '', 'en', 'es')

        # Empty source language
        with pytest.raises(ValidationError):
            translation_service.validate_translation('original', 'translated', '', 'es')

        # Empty target language
        with pytest.raises(ValidationError):
            translation_service.validate_translation('original', 'translated', 'en', '')

    def test_retry_logic_success_after_failure(self, translation_service, mock_aws_client_manager):
        """Test retry logic succeeds after initial failures."""
        translate_client = mock_aws_client_manager.get_translate_client.return_value

        # Mock first call fails with throttling, second succeeds
        throttling_error = ClientError(
            error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            operation_name='translate_text',
        )

        success_response = {
            'TranslatedText': 'Hola mundo',
            'SourceLanguageCode': 'en',
            'TargetLanguageCode': 'es',
            'AppliedTerminologies': [],
            'AppliedSettings': {},
        }

        translate_client.translate_text.side_effect = [throttling_error, success_response]

        # Execute with retry
        with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
            result = translation_service.translate_text('Hello world', 'en', 'es')

        # Verify retry occurred
        assert translate_client.translate_text.call_count == 2
        mock_sleep.assert_called_once()

        # Verify successful result
        assert result.translated_text == 'Hola mundo'

    def test_retry_logic_max_retries_exceeded(self, translation_service, mock_aws_client_manager):
        """Test retry logic when max retries are exceeded."""
        translate_client = mock_aws_client_manager.get_translate_client.return_value

        # Mock all calls fail with throttling
        throttling_error = ClientError(
            error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            operation_name='translate_text',
        )
        translate_client.translate_text.side_effect = throttling_error

        # Execute and expect RateLimitError
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(RateLimitError) as exc_info:
                translation_service.translate_text('Hello world', 'en', 'es')

        # Verify all retries were attempted (initial + 2 retries = 3 total)
        assert translate_client.translate_text.call_count == 3
        assert 'Rate limit exceeded after maximum retries' in str(exc_info.value)

    def test_retry_logic_non_retryable_error(self, translation_service, mock_aws_client_manager):
        """Test that non-retryable errors are not retried."""
        translate_client = mock_aws_client_manager.get_translate_client.return_value

        # Mock validation error (non-retryable)
        validation_error = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter'}
            },
            operation_name='translate_text',
        )
        translate_client.translate_text.side_effect = validation_error

        # Execute and expect ValidationError immediately
        with pytest.raises(ValidationError):
            translation_service.translate_text('Hello world', 'en', 'es')

        # Verify no retries occurred
        assert translate_client.translate_text.call_count == 1

    def test_calculate_retry_delay(self, translation_service):
        """Test retry delay calculation."""
        # Test exponential backoff without jitter
        delay_0 = translation_service._calculate_retry_delay(0)
        delay_1 = translation_service._calculate_retry_delay(1)
        delay_2 = translation_service._calculate_retry_delay(2)

        assert delay_0 == 0.1  # base_delay
        assert delay_1 == 0.2  # base_delay * 2
        assert delay_2 == 0.4  # base_delay * 4

        # Test max delay cap
        delay_large = translation_service._calculate_retry_delay(10)
        assert delay_large == 1.0  # max_delay

    def test_handle_client_error_authentication(self, translation_service):
        """Test client error handling for authentication errors."""
        auth_error = ClientError(
            error_response={
                'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}
            },
            operation_name='translate_text',
        )

        with pytest.raises(AuthenticationError) as exc_info:
            translation_service._handle_client_error(auth_error, 'test_operation')

        assert 'Access denied' in str(exc_info.value)
        assert exc_info.value.details['error_code'] == 'AccessDeniedException'

    def test_handle_client_error_validation(self, translation_service):
        """Test client error handling for validation errors."""
        validation_error = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter'}
            },
            operation_name='translate_text',
        )

        with pytest.raises(ValidationError) as exc_info:
            translation_service._handle_client_error(validation_error, 'test_operation')

        assert 'Invalid parameters' in str(exc_info.value)

    def test_handle_client_error_unsupported_language_pair(self, translation_service):
        """Test client error handling for unsupported language pairs."""
        lang_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'UnsupportedLanguagePairException',
                    'Message': 'Language pair not supported',
                }
            },
            operation_name='translate_text',
        )

        with pytest.raises(TranslationError) as exc_info:
            translation_service._handle_client_error(lang_error, 'test_operation')

        assert 'Unsupported language pair' in str(exc_info.value)

    def test_handle_client_error_quota_exceeded(self, translation_service):
        """Test client error handling for quota exceeded errors."""
        quota_error = ClientError(
            error_response={
                'Error': {'Code': 'LimitExceededException', 'Message': 'Quota exceeded'}
            },
            operation_name='translate_text',
        )

        with pytest.raises(QuotaExceededError) as exc_info:
            translation_service._handle_client_error(quota_error, 'test_operation')

        assert 'Service quota exceeded' in str(exc_info.value)

    def test_handle_client_error_service_unavailable(self, translation_service):
        """Test client error handling for service unavailable errors."""
        service_error = ClientError(
            error_response={
                'Error': {'Code': 'ServiceUnavailableException', 'Message': 'Service unavailable'}
            },
            operation_name='translate_text',
        )

        with pytest.raises(ServiceUnavailableError) as exc_info:
            translation_service._handle_client_error(service_error, 'test_operation')

        assert 'Service unavailable' in str(exc_info.value)

    def test_extract_retry_after(self, translation_service):
        """Test extraction of retry-after header from client error."""
        # Mock client error with retry-after header
        client_error = ClientError(
            error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            operation_name='translate_text',
        )
        # Type ignore for test mock assignment
        client_error.response['ResponseMetadata'] = {'HTTPHeaders': {'Retry-After': '30'}}  # type: ignore

        retry_after = translation_service._extract_retry_after(client_error)
        assert retry_after == 30

        # Test without retry-after header
        client_error_no_header = ClientError(
            error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            operation_name='translate_text',
        )

        retry_after_none = translation_service._extract_retry_after(client_error_no_header)
        assert retry_after_none is None

    def test_network_error_retry(self, translation_service, mock_aws_client_manager):
        """Test retry logic for network/BotoCore errors."""
        translate_client = mock_aws_client_manager.get_translate_client.return_value

        # Mock network error followed by success
        network_error = BotoCoreError()
        success_response = {
            'TranslatedText': 'Hola mundo',
            'SourceLanguageCode': 'en',
            'TargetLanguageCode': 'es',
            'AppliedTerminologies': [],
            'AppliedSettings': {},
        }

        translate_client.translate_text.side_effect = [network_error, success_response]

        # Execute with retry
        with patch('time.sleep'):
            result = translation_service.translate_text('Hello world', 'en', 'es')

        # Verify retry occurred and succeeded
        assert translate_client.translate_text.call_count == 2
        assert result.translated_text == 'Hola mundo'

    def test_unexpected_error_no_retry(self, translation_service, mock_aws_client_manager):
        """Test that unexpected errors are not retried."""
        translate_client = mock_aws_client_manager.get_translate_client.return_value

        # Mock unexpected error
        unexpected_error = ValueError('Unexpected error')
        translate_client.translate_text.side_effect = unexpected_error

        # Execute and expect TranslationError
        with pytest.raises(TranslationError) as exc_info:
            translation_service.translate_text('Hello world', 'en', 'es')

        # Verify no retries occurred
        assert translate_client.translate_text.call_count == 1
        assert 'Unexpected error during translation' in str(exc_info.value)
