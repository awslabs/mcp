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

"""Language Operations for Amazon Translate MCP Server.

This module provides language-related utilities including supported language pairs,
usage metrics, format capabilities, and language validation functionality.
"""

import logging
from .aws_client import AWSClientManager
from .models import (
    AuthenticationError,
    LanguageMetrics,
    LanguagePair,
    ServiceUnavailableError,
    TranslateException,
    ValidationError,
)
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


class LanguageOperations:
    """Handles language-related operations for Amazon Translate.

    This class provides methods for listing supported language pairs,
    retrieving usage metrics, checking format capabilities, and validating
    language compatibility for translation operations.
    """

    # Supported content types for different language pairs
    SUPPORTED_FORMATS = [
        'text/plain',
        'text/html',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ]

    # Languages that don't support custom terminology
    NO_TERMINOLOGY_LANGUAGES = {
        'auto'  # Auto-detect doesn't support terminology
    }

    def __init__(self, aws_client_manager: AWSClientManager):
        """Initialize the Language Operations.

        Args:
            aws_client_manager: AWS client manager instance

        """
        self.aws_client_manager = aws_client_manager
        self._language_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=24)  # Cache language data for 24 hours

    def list_language_pairs(self) -> List[LanguagePair]:
        """List all supported language pairs for translation.

        Returns:
            List of LanguagePair objects showing all supported combinations

        Raises:
            AuthenticationError: If AWS credentials are invalid
            ServiceUnavailableError: If Amazon Translate service is unavailable
            TranslateException: For other translation service errors

        """
        try:
            logger.debug('Retrieving supported language pairs')

            # Get cached data if available and fresh
            if self._is_cache_valid():
                logger.debug('Using cached language data')
                return self._build_language_pairs_from_cache()

            # Fetch fresh language data
            translate_client = self.aws_client_manager.get_translate_client()

            # Get supported languages
            response = translate_client.list_languages(
                DisplayLanguageCode='en',
                MaxResults=500,  # Maximum allowed
            )

            languages = response.get('Languages', [])

            # Update cache
            self._language_cache = {
                'languages': languages,
                'supported_pairs': self._calculate_supported_pairs(languages),
            }
            self._cache_timestamp = datetime.utcnow()

            logger.info('Retrieved %d supported languages', len(languages))

            return self._build_language_pairs_from_cache()

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code in ['AccessDenied', 'UnauthorizedOperation']:
                raise AuthenticationError(
                    f'Access denied when listing languages: {error_message}',
                    details={'error_code': error_code},
                )
            elif error_code in ['ServiceUnavailable', 'InternalFailure']:
                raise ServiceUnavailableError(
                    f'Amazon Translate service unavailable: {error_message}',
                    service='translate',
                    details={'error_code': error_code},
                )
            else:
                raise TranslateException(
                    f'Failed to list language pairs: {error_message}',
                    error_code=error_code,
                    details={'aws_error_code': error_code},
                )

        except BotoCoreError as e:
            raise ServiceUnavailableError(
                f'BotoCore error listing languages: {str(e)}',
                service='translate',
                details={'error_type': type(e).__name__},
            )

        except Exception as e:
            raise TranslateException(
                f'Unexpected error listing language pairs: {str(e)}',
                details={'error_type': type(e).__name__},
            )

    def get_language_metrics(
        self, language_pair: Optional[str] = None, time_range: str = '24h'
    ) -> LanguageMetrics:
        """Get usage metrics for language operations.

        Args:
            language_pair: Specific language pair (e.g., "en-es") or None for all
            time_range: Time range for metrics ("1h", "24h", "7d", "30d")

        Returns:
            LanguageMetrics object with usage statistics

        Raises:
            ValidationError: If parameters are invalid
            AuthenticationError: If AWS credentials are invalid
            ServiceUnavailableError: If CloudWatch service is unavailable
            TranslateException: For other service errors

        """
        try:
            logger.debug(
                'Retrieving language metrics for pair: %s, range: %s', language_pair, time_range
            )

            # Validate time range
            valid_ranges = ['1h', '24h', '7d', '30d']
            if time_range not in valid_ranges:
                raise ValidationError(
                    f"Invalid time range '{time_range}'. Must be one of: {', '.join(valid_ranges)}",
                    field='time_range',
                )

            # Validate language pair format if provided
            if language_pair and not self._is_valid_language_pair_format(language_pair):
                raise ValidationError(
                    f"Invalid language pair format '{language_pair}'. Expected format: 'source-target' (e.g., 'en-es')",
                    field='language_pair',
                )

            # Calculate time range
            end_time = datetime.utcnow()
            start_time = self._calculate_start_time(end_time, time_range)

            # Get CloudWatch client
            cloudwatch_client = self.aws_client_manager.get_cloudwatch_client()

            # Retrieve metrics from CloudWatch
            metrics_data = self._retrieve_cloudwatch_metrics(
                cloudwatch_client, language_pair, start_time, end_time
            )

            # Build metrics response
            metrics = LanguageMetrics(
                language_pair=language_pair,
                translation_count=metrics_data.get('translation_count', 0),
                character_count=metrics_data.get('character_count', 0),
                average_response_time=metrics_data.get('average_response_time'),
                error_rate=metrics_data.get('error_rate'),
                time_range=time_range,
            )

            logger.debug(
                'Retrieved metrics: %d translations, %d characters',
                metrics.translation_count,
                metrics.character_count,
            )

            return metrics

        except (ValidationError, AuthenticationError, ServiceUnavailableError):
            # Re-raise these exceptions without modification
            raise

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code in ['AccessDenied', 'UnauthorizedOperation']:
                raise AuthenticationError(
                    f'Access denied when retrieving metrics: {error_message}',
                    details={'error_code': error_code},
                )
            elif error_code in ['ServiceUnavailable', 'InternalFailure']:
                raise ServiceUnavailableError(
                    f'CloudWatch service unavailable: {error_message}',
                    service='cloudwatch',
                    details={'error_code': error_code},
                )
            else:
                raise TranslateException(
                    f'Failed to retrieve language metrics: {error_message}',
                    error_code=error_code,
                    details={'aws_error_code': error_code},
                )

        except BotoCoreError as e:
            raise ServiceUnavailableError(
                f'BotoCore error retrieving metrics: {str(e)}',
                service='cloudwatch',
                details={'error_type': type(e).__name__},
            )

        except Exception as e:
            raise TranslateException(
                f'Unexpected error retrieving language metrics: {str(e)}',
                details={'error_type': type(e).__name__},
            )

    def get_supported_formats(self) -> List[str]:
        """Get list of supported content formats for translation.

        Returns:
            List of supported MIME types/content formats

        """
        logger.debug('Returning supported content formats')
        return self.SUPPORTED_FORMATS.copy()

    def validate_language_pair(self, source_language: str, target_language: str) -> bool:
        """Validate if a language pair is supported for translation.

        Args:
            source_language: Source language code
            target_language: Target language code

        Returns:
            True if the language pair is supported, False otherwise

        Raises:
            ValidationError: If language codes are invalid
            TranslateException: For service errors during validation

        """
        try:
            logger.debug('Validating language pair: %s -> %s', source_language, target_language)

            # Basic validation
            if not source_language or not target_language:
                raise ValidationError('Source and target language codes cannot be empty')

            if source_language == target_language:
                raise ValidationError('Source and target languages cannot be the same')

            # Get supported language pairs
            supported_pairs = self.list_language_pairs()

            # Check if the pair is supported
            for pair in supported_pairs:
                if (
                    pair.source_language == source_language
                    and pair.target_language == target_language
                ):
                    logger.debug('Language pair is supported')
                    return True

            # Also check if source is 'auto' (auto-detect)
            if source_language == 'auto':
                # Check if target language is supported as a target
                for pair in supported_pairs:
                    if pair.target_language == target_language:
                        logger.debug('Auto-detect to target language is supported')
                        return True

            logger.debug('Language pair is not supported')
            return False

        except (ValidationError, TranslateException):
            # Re-raise these exceptions without modification
            raise

        except Exception as e:
            raise TranslateException(
                f'Unexpected error validating language pair: {str(e)}',
                details={'error_type': type(e).__name__},
            )

    def is_terminology_supported(self, source_language: str, target_language: str) -> bool:
        """Check if custom terminology is supported for a language pair.

        Args:
            source_language: Source language code
            target_language: Target language code

        Returns:
            True if custom terminology is supported, False otherwise

        """
        logger.debug(
            'Checking terminology support for: %s -> %s', source_language, target_language
        )

        # Auto-detect doesn't support terminology
        if source_language in self.NO_TERMINOLOGY_LANGUAGES:
            return False

        # For now, assume all other valid language pairs support terminology
        # This could be enhanced with more specific rules if needed
        try:
            return self.validate_language_pair(source_language, target_language)
        except Exception:
            return False

    def get_language_name(self, language_code: str) -> Optional[str]:
        """Get the display name for a language code.

        Args:
            language_code: Language code (e.g., 'en', 'es')

        Returns:
            Display name of the language or None if not found

        """
        try:
            # Ensure we have cached language data
            if not self._is_cache_valid():
                self.list_language_pairs()  # This will populate the cache

            if self._language_cache:
                for lang in self._language_cache.get('languages', []):
                    if lang.get('LanguageCode') == language_code:
                        return lang.get('LanguageName')

            return None

        except Exception as e:
            logger.warning("Failed to get language name for '%s': %s", language_code, str(e))
            return None

    def _is_cache_valid(self) -> bool:
        """Check if the language cache is valid and not expired."""
        if not self._language_cache or not self._cache_timestamp:
            return False

        return datetime.utcnow() - self._cache_timestamp < self._cache_ttl

    def _calculate_supported_pairs(self, languages: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
        """Calculate all supported language pairs from the language list.

        Args:
            languages: List of language dictionaries from AWS API

        Returns:
            List of (source, target) language code tuples

        """
        pairs = []
        language_codes = [lang['LanguageCode'] for lang in languages]

        # Create all possible pairs (excluding same language pairs)
        for source in language_codes:
            for target in language_codes:
                if source != target:
                    pairs.append((source, target))

        # Add auto-detect as source for all targets (except auto itself)
        for target in language_codes:
            if target != 'auto':  # Don't create auto->auto pairs
                pairs.append(('auto', target))

        return pairs

    def _build_language_pairs_from_cache(self) -> List[LanguagePair]:
        """Build LanguagePair objects from cached data."""
        if not self._language_cache:
            return []

        pairs = []
        supported_pairs = self._language_cache.get('supported_pairs', [])

        for source, target in supported_pairs:
            # Determine supported formats (all formats for most pairs)
            supported_formats = self.SUPPORTED_FORMATS.copy()

            # Check if terminology is supported (simple check without recursion)
            terminology_supported = source not in self.NO_TERMINOLOGY_LANGUAGES

            pairs.append(
                LanguagePair(
                    source_language=source,
                    target_language=target,
                    supported_formats=supported_formats,
                    custom_terminology_supported=terminology_supported,
                )
            )

        return pairs

    def _is_valid_language_pair_format(self, language_pair: str) -> bool:
        """Validate language pair format (e.g., 'en-es').

        Args:
            language_pair: Language pair string

        Returns:
            True if format is valid, False otherwise

        """
        if not language_pair or '-' not in language_pair:
            return False

        parts = language_pair.split('-')
        if len(parts) != 2:
            return False

        source, target = parts
        return bool(source.strip() and target.strip())

    def _calculate_start_time(self, end_time: datetime, time_range: str) -> datetime:
        """Calculate start time based on time range.

        Args:
            end_time: End time for the range
            time_range: Time range string

        Returns:
            Start time for the range

        """
        if time_range == '1h':
            return end_time - timedelta(hours=1)
        elif time_range == '24h':
            return end_time - timedelta(hours=24)
        elif time_range == '7d':
            return end_time - timedelta(days=7)
        elif time_range == '30d':
            return end_time - timedelta(days=30)
        else:
            # Default to 24h
            return end_time - timedelta(hours=24)

    def _retrieve_cloudwatch_metrics(
        self,
        cloudwatch_client: Any,
        language_pair: Optional[str],
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """Retrieve metrics from CloudWatch.

        Args:
            cloudwatch_client: CloudWatch client
            language_pair: Language pair filter
            start_time: Start time for metrics
            end_time: End time for metrics

        Returns:
            Dictionary with metric values

        """
        # This is a placeholder implementation since CloudWatch metrics
        # for Amazon Translate would need to be set up separately
        # In a real implementation, you would query actual CloudWatch metrics

        logger.debug('Retrieving CloudWatch metrics (placeholder implementation)')

        # Return placeholder metrics
        # In production, this would query actual CloudWatch metrics
        return {
            'translation_count': 0,
            'character_count': 0,
            'average_response_time': None,
            'error_rate': None,
        }
