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

"""Translation Service for Amazon Translate MCP Server.

This module provides real-time text translation operations including text translation,
language detection, and translation validation with comprehensive error handling and retry logic.
"""

import logging
import random
import time
from .aws_client import AWSClientManager
from .models import (
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
from botocore.exceptions import BotoCoreError, ClientError
from typing import Any, Dict, List, NoReturn, Optional


logger = logging.getLogger(__name__)


class TranslationService:
    """Service for real-time translation operations using Amazon Translate.

    This service provides methods for text translation, language detection,
    and translation validation with comprehensive error handling, retry logic,
    and terminology support.
    """

    def __init__(
        self,
        aws_client_manager: AWSClientManager,
        max_text_length: int = 10000,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        """Initialize the Translation Service.

        Args:
            aws_client_manager: AWS client manager instance
            max_text_length: Maximum allowed text length for translation
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay for exponential backoff (seconds)
            jitter: Whether to add random jitter to retry delays

        """
        self._aws_client_manager = aws_client_manager
        self._max_text_length = max_text_length
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._jitter = jitter

        logger.info(
            'Translation service initialized. Max text length: %d, Max retries: %d',
            max_text_length,
            max_retries,
        )

    def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
        terminology_names: Optional[List[str]] = None,
        settings: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        """Translate text from source language to target language.

        Args:
            text: Text to translate
            source_language: Source language code (e.g., 'en', 'es', 'auto' for detection)
            target_language: Target language code (e.g., 'es', 'fr')
            terminology_names: List of custom terminology names to apply
            settings: Optional translation settings (formality, profanity, brevity)

        Returns:
            TranslationResult with translated text and metadata

        Raises:
            ValidationError: If input parameters are invalid
            TranslationError: If translation operation fails
            RateLimitError: If rate limits are exceeded
            ServiceUnavailableError: If service is unavailable
            AuthenticationError: If authentication fails

        """
        # Validate input parameters
        self._validate_translation_input(text, source_language, target_language)

        # Auto-detect source language if needed
        if source_language.lower() == 'auto':
            detection_result = self.detect_language(text)
            source_language = detection_result.detected_language
            logger.debug('Auto-detected source language: %s', source_language)

        # Prepare translation request
        translate_request: Dict[str, Any] = {
            'Text': text,
            'SourceLanguageCode': source_language,
            'TargetLanguageCode': target_language,
        }

        # Add terminology if specified
        if terminology_names:
            translate_request['TerminologyNames'] = terminology_names

        # Add settings if specified
        if settings:
            translate_request['Settings'] = settings

        # Execute translation with retry logic
        try:
            response = self._execute_with_retry(
                lambda: self._aws_client_manager.get_translate_client().translate_text(
                    **translate_request
                )
            )

            # Extract translation result
            translated_text = response['TranslatedText']
            applied_terminologies = response.get('AppliedTerminologies', [])

            # Create result object
            result = TranslationResult(
                translated_text=translated_text,
                source_language=source_language,
                target_language=target_language,
                applied_terminologies=[term['Name'] for term in applied_terminologies],
            )

            logger.debug(
                'Translation completed. Source: %s, Target: %s, Length: %d -> %d',
                source_language,
                target_language,
                len(text),
                len(translated_text),
            )

            return result

        except ClientError as e:
            self._handle_client_error(e, 'translate_text')
        except (RateLimitError, ServiceUnavailableError, QuotaExceededError, AuthenticationError):
            # Re-raise these specific exceptions without wrapping
            raise
        except Exception as e:
            raise TranslationError(
                f'Unexpected error during translation: {str(e)}',
                source_lang=source_language,
                target_lang=target_language,
                details={'error_type': type(e).__name__},
            )

    def detect_language(self, text: str) -> LanguageDetectionResult:
        """Detect the language of the given text.

        Args:
            text: Text to analyze for language detection

        Returns:
            LanguageDetectionResult with detected language and confidence scores

        Raises:
            ValidationError: If input text is invalid
            TranslationError: If language detection fails
            RateLimitError: If rate limits are exceeded
            ServiceUnavailableError: If service is unavailable
            AuthenticationError: If authentication fails

        """
        # Validate input
        if not text or not text.strip():
            raise ValidationError('Text cannot be empty for language detection', field='text')

        if len(text) > self._max_text_length:
            raise ValidationError(
                f'Text length ({len(text)}) exceeds maximum allowed length ({self._max_text_length})',
                field='text',
            )

        # Execute language detection with retry logic
        # Use AWS Translate's auto-detection feature by translating with source="auto"
        try:
            # Use a dummy translation to detect the language
            # We'll translate to English as it's widely supported
            response = self._execute_with_retry(
                lambda: self._aws_client_manager.get_translate_client().translate_text(
                    Text=text, SourceLanguageCode='auto', TargetLanguageCode='en'
                )
            )

            # Extract the detected source language from the response
            detected_language = response.get('SourceLanguageCode')
            if not detected_language:
                raise TranslationError(
                    'No source language detected in the translation response',
                    details={'text_length': len(text)},
                )

            # AWS Translate doesn't provide confidence scores for auto-detection
            # We'll use a high confidence score since it was successfully detected
            confidence_score = 0.95

            # No alternative languages available from Translate auto-detection
            alternative_languages = []

            result = LanguageDetectionResult(
                detected_language=detected_language,
                confidence_score=confidence_score,
                alternative_languages=alternative_languages,
            )

            logger.debug(
                'Language detection completed. Detected: %s (confidence: %.3f), Alternatives: %d',
                detected_language,
                confidence_score,
                len(alternative_languages),
            )

            return result

        except ClientError as e:
            self._handle_client_error(e, 'detect_language')
        except Exception as e:
            raise TranslationError(
                f'Unexpected error during language detection: {str(e)}',
                details={'error_type': type(e).__name__, 'text_length': len(text)},
            )

    def validate_translation(
        self, original_text: str, translated_text: str, source_language: str, target_language: str
    ) -> ValidationResult:
        """Validate the quality of a translation.

        This method performs basic validation checks on translation quality,
        including length ratio analysis, character set validation, and basic
        consistency checks.

        Args:
            original_text: Original source text
            translated_text: Translated text to validate
            source_language: Source language code
            target_language: Target language code

        Returns:
            ValidationResult with validation status and quality metrics

        Raises:
            ValidationError: If input parameters are invalid

        """
        # Validate input parameters
        if not original_text or not original_text.strip():
            raise ValidationError('Original text cannot be empty', field='original_text')

        if not translated_text or not translated_text.strip():
            raise ValidationError('Translated text cannot be empty', field='translated_text')

        if not source_language:
            raise ValidationError('Source language cannot be empty', field='source_language')

        if not target_language:
            raise ValidationError('Target language cannot be empty', field='target_language')

        issues = []
        suggestions = []
        quality_score = 1.0  # Start with perfect score and deduct for issues

        # Length ratio analysis
        original_length = len(original_text.strip())
        translated_length = len(translated_text.strip())
        length_ratio = translated_length / original_length if original_length > 0 else 0

        # Check for suspicious length ratios
        if length_ratio < 0.3:
            issues.append(
                'Translation is significantly shorter than original (possible truncation)'
            )
            suggestions.append('Review translation for completeness')
            quality_score -= 0.3
        elif length_ratio > 3.0:
            issues.append(
                'Translation is significantly longer than original (possible over-expansion)'
            )
            suggestions.append('Review translation for conciseness')
            quality_score -= 0.2

        # Check for untranslated content (same as original)
        if original_text.strip().lower() == translated_text.strip().lower():
            if source_language != target_language:
                issues.append('Translation appears identical to original text')
                suggestions.append('Verify that translation actually occurred')
                quality_score -= 0.5

        # Check for common translation artifacts
        if '&lt;' in translated_text or '&gt;' in translated_text or '&amp;' in translated_text:
            issues.append('Translation contains HTML entities that may need decoding')
            suggestions.append('Consider post-processing to decode HTML entities')
            quality_score -= 0.1

        # Check for excessive whitespace
        if (
            len(translated_text) - len(translated_text.strip())
            > len(original_text) - len(original_text.strip()) + 10
        ):
            issues.append('Translation contains excessive whitespace')
            suggestions.append('Consider trimming unnecessary whitespace')
            quality_score -= 0.1

        # Check for repeated patterns (possible translation errors)
        words = translated_text.split()
        if len(words) > 5:
            word_counts = {}
            for word in words:
                word_lower = word.lower().strip('.,!?;:')
                word_counts[word_lower] = word_counts.get(word_lower, 0) + 1

            # Check for words that appear too frequently
            max_count = max(word_counts.values()) if word_counts else 0
            if max_count > len(words) * 0.3 and max_count > 3:
                issues.append('Translation contains repetitive patterns')
                suggestions.append('Review translation for accuracy and fluency')
                quality_score -= 0.2

        # Ensure quality score doesn't go below 0
        quality_score = max(0.0, quality_score)

        # Determine overall validity
        is_valid = quality_score >= 0.8 and len(issues) == 0

        result = ValidationResult(
            is_valid=is_valid, quality_score=quality_score, issues=issues, suggestions=suggestions
        )

        logger.debug(
            'Translation validation completed. Valid: %s, Quality: %.3f, Issues: %d',
            is_valid,
            quality_score,
            len(issues),
        )

        return result

    def _validate_translation_input(
        self, text: str, source_language: str, target_language: str
    ) -> None:
        """Validate input parameters for translation.

        Args:
            text: Text to validate
            source_language: Source language to validate
            target_language: Target language to validate

        Raises:
            ValidationError: If any parameter is invalid

        """
        if not text or not text.strip():
            raise ValidationError('Text cannot be empty', field='text')

        if len(text) > self._max_text_length:
            raise ValidationError(
                f'Text length ({len(text)}) exceeds maximum allowed length ({self._max_text_length})',
                field='text',
            )

        if not source_language:
            raise ValidationError('Source language cannot be empty', field='source_language')

        if not target_language:
            raise ValidationError('Target language cannot be empty', field='target_language')

        # Basic language code format validation
        valid_lang_pattern = r'^[a-z]{2}(-[A-Z]{2})?$|^auto$'
        import re

        if not re.match(valid_lang_pattern, source_language):
            raise ValidationError(
                f'Invalid source language code format: {source_language}', field='source_language'
            )

        if not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', target_language):
            raise ValidationError(
                f'Invalid target language code format: {target_language}', field='target_language'
            )

        if source_language == target_language and source_language != 'auto':
            raise ValidationError(
                'Source and target languages cannot be the same', field='target_language'
            )

    def _execute_with_retry(self, operation) -> Dict[str, Any]:
        """Execute an operation with exponential backoff retry logic.

        Args:
            operation: Function to execute

        Returns:
            Operation result

        Raises:
            Various exceptions based on the final failure reason

        """
        last_exception = None

        for attempt in range(self._max_retries + 1):
            try:
                return operation()

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')

                # Don't retry certain errors
                if error_code in [
                    'ValidationException',
                    'InvalidParameterValueException',
                    'AccessDeniedException',
                    'UnauthorizedOperation',
                    'UnsupportedLanguagePairException',
                    'DetectedLanguageLowConfidenceException',
                ]:
                    raise

                # Retry throttling and service errors
                if error_code in ['ThrottlingException', 'TooManyRequestsException']:
                    if attempt < self._max_retries:
                        delay = self._calculate_retry_delay(attempt)
                        logger.warning(
                            'Rate limit exceeded (attempt %d/%d), retrying in %.2f seconds',
                            attempt + 1,
                            self._max_retries + 1,
                            delay,
                        )
                        time.sleep(delay)
                        last_exception = e
                        continue
                    else:
                        # Final attempt failed with rate limiting
                        retry_after = self._extract_retry_after(e)
                        raise RateLimitError(
                            'Rate limit exceeded after maximum retries',
                            retry_after=retry_after,
                            details={'error_code': error_code, 'attempts': attempt + 1},
                        )

                if error_code in ['ServiceUnavailableException', 'InternalServerException']:
                    if attempt < self._max_retries:
                        delay = self._calculate_retry_delay(attempt)
                        logger.warning(
                            'Service unavailable (attempt %d/%d), retrying in %.2f seconds',
                            attempt + 1,
                            self._max_retries + 1,
                            delay,
                        )
                        time.sleep(delay)
                        last_exception = e
                        continue

                # For other client errors, don't retry
                last_exception = e
                break

            except BotoCoreError as e:
                # Network/connection errors - retry
                if attempt < self._max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        'Network error (attempt %d/%d), retrying in %.2f seconds: %s',
                        attempt + 1,
                        self._max_retries + 1,
                        delay,
                        str(e),
                    )
                    time.sleep(delay)
                    last_exception = e
                    continue
                else:
                    last_exception = e
                    break

            except Exception as e:
                # Unexpected errors - don't retry
                last_exception = e
                break

        # If we get here, all retries failed
        if isinstance(last_exception, ClientError):
            self._handle_client_error(last_exception, 'retry_operation')
        elif last_exception is not None:
            raise last_exception
        else:
            raise TranslationError('Operation failed after all retries with no recorded exception')

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay using exponential backoff with optional jitter.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds

        """
        # Exponential backoff: base_delay * (2 ^ attempt)
        delay = self._base_delay * (2**attempt)

        # Cap at maximum delay
        delay = min(delay, self._max_delay)

        # Add jitter to avoid thundering herd
        if self._jitter:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)  # nosec B311 - not security sensitive

        return max(0.1, delay)  # Minimum 100ms delay

    def _extract_retry_after(self, client_error: ClientError) -> Optional[int]:
        """Extract retry-after value from client error response.

        Args:
            client_error: ClientError to examine

        Returns:
            Retry-after value in seconds, or None if not available

        """
        try:
            # Check for Retry-After header
            response_metadata = client_error.response.get('ResponseMetadata', {})
            headers = response_metadata.get('HTTPHeaders', {})

            retry_after = headers.get('Retry-After') or headers.get('retry-after')
            if retry_after:
                return int(retry_after)

        except (ValueError, KeyError):
            pass

        return None

    def _handle_client_error(self, client_error: ClientError, operation: str) -> NoReturn:
        """Handle AWS client errors and convert to appropriate exceptions.

        Args:
            client_error: ClientError to handle
            operation: Name of the operation that failed

        Raises:
            Appropriate exception based on error type

        """
        error_code = client_error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = client_error.response.get('Error', {}).get('Message', str(client_error))

        # Authentication/Authorization errors
        if error_code in [
            'AccessDeniedException',
            'UnauthorizedOperation',
            'InvalidUserID.NotFound',
        ]:
            raise AuthenticationError(
                f'Access denied for {operation}: {error_message}',
                details={'error_code': error_code, 'operation': operation},
            )

        # Validation errors
        if error_code in ['ValidationException', 'InvalidParameterValueException']:
            raise ValidationError(
                f'Invalid parameters for {operation}: {error_message}',
                details={'error_code': error_code, 'operation': operation},
            )

        # Language-specific errors
        if error_code == 'UnsupportedLanguagePairException':
            raise TranslationError(
                f'Unsupported language pair: {error_message}',
                details={'error_code': error_code, 'operation': operation},
            )

        if error_code == 'DetectedLanguageLowConfidenceException':
            raise TranslationError(
                f'Language detection confidence too low: {error_message}',
                details={'error_code': error_code, 'operation': operation},
            )

        # Rate limiting errors
        if error_code in ['ThrottlingException', 'TooManyRequestsException']:
            retry_after = self._extract_retry_after(client_error)
            raise RateLimitError(
                f'Rate limit exceeded for {operation}: {error_message}',
                retry_after=retry_after,
                details={'error_code': error_code, 'operation': operation},
            )

        # Quota errors
        if error_code in ['LimitExceededException', 'ServiceQuotaExceededException']:
            raise QuotaExceededError(
                f'Service quota exceeded for {operation}: {error_message}',
                quota_type=operation,
                details={'error_code': error_code, 'operation': operation},
            )

        # Service availability errors
        if error_code in ['ServiceUnavailableException', 'InternalServerException']:
            raise ServiceUnavailableError(
                f'Service unavailable for {operation}: {error_message}',
                service='translate',
                details={'error_code': error_code, 'operation': operation},
            )

        # Generic translation error for other cases
        raise TranslationError(
            f'Translation operation failed ({operation}): {error_message}',
            details={'error_code': error_code, 'operation': operation},
        )
