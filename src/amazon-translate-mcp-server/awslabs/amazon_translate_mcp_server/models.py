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

"""Data models for Amazon Translate MCP Server.

This module contains all the data models used throughout the server,
including request/response models, configuration models, and error models.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class JobStatus(Enum):
    """Translation job status enumeration."""

    SUBMITTED = 'SUBMITTED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    STOPPED = 'STOPPED'


class ContentType(Enum):
    """Supported content types for batch translation."""

    TEXT_PLAIN = 'text/plain'
    TEXT_HTML = 'text/html'
    APPLICATION_DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    APPLICATION_PPTX = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    APPLICATION_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class TerminologyFormat(Enum):
    """Supported terminology file formats."""

    CSV = 'CSV'
    TMX = 'TMX'


# Core Translation Models


@dataclass
class TranslationResult:
    """Result of a text translation operation."""

    translated_text: str
    source_language: str
    target_language: str
    applied_terminologies: List[str] = field(default_factory=list)
    confidence_score: Optional[float] = None

    def __post_init__(self):
        """Validate the translation result."""
        if not self.translated_text:
            raise ValueError('translated_text cannot be empty')
        if not self.source_language:
            raise ValueError('source_language cannot be empty')
        if not self.target_language:
            raise ValueError('target_language cannot be empty')
        if self.confidence_score is not None and not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError('confidence_score must be between 0.0 and 1.0')


@dataclass
class LanguageDetectionResult:
    """Result of language detection operation."""

    detected_language: str
    confidence_score: float
    alternative_languages: List[Tuple[str, float]] = field(default_factory=list)

    def __post_init__(self):
        """Validate the language detection result."""
        if not self.detected_language:
            raise ValueError('detected_language cannot be empty')
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError('confidence_score must be between 0.0 and 1.0')
        for lang, score in self.alternative_languages:
            if not lang:
                raise ValueError('Alternative language code cannot be empty')
            if not (0.0 <= score <= 1.0):
                raise ValueError(
                    'Alternative language confidence score must be between 0.0 and 1.0'
                )


@dataclass
class ValidationResult:
    """Result of translation validation."""

    is_valid: bool
    quality_score: Optional[float] = None
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate the validation result."""
        if self.quality_score is not None and not (0.0 <= self.quality_score <= 1.0):
            raise ValueError('quality_score must be between 0.0 and 1.0')


# Batch Translation Models


@dataclass
class BatchInputConfig:
    """Configuration for batch translation input."""

    s3_uri: str
    content_type: str
    data_access_role_arn: str

    def __post_init__(self):
        """Validate the batch input configuration."""
        if not self.s3_uri:
            raise ValueError('s3_uri cannot be empty')
        if not self.s3_uri.startswith('s3://'):
            raise ValueError("s3_uri must start with 's3://'")
        if not self.content_type:
            raise ValueError('content_type cannot be empty')
        if not self.data_access_role_arn:
            raise ValueError('data_access_role_arn cannot be empty')
        if not self._is_valid_arn(self.data_access_role_arn):
            raise ValueError('data_access_role_arn must be a valid IAM role ARN')

    @staticmethod
    def _is_valid_arn(arn: str) -> bool:
        """Validate ARN format."""
        arn_pattern = r'^arn:aws:iam::\d{12}:role/.+'
        return bool(re.match(arn_pattern, arn))


@dataclass
class BatchOutputConfig:
    """Configuration for batch translation output."""

    s3_uri: str
    data_access_role_arn: str

    def __post_init__(self):
        """Validate the batch output configuration."""
        if not self.s3_uri:
            raise ValueError('s3_uri cannot be empty')
        if not self.s3_uri.startswith('s3://'):
            raise ValueError("s3_uri must start with 's3://'")
        if not self.data_access_role_arn:
            raise ValueError('data_access_role_arn cannot be empty')
        if not BatchInputConfig._is_valid_arn(self.data_access_role_arn):
            raise ValueError('data_access_role_arn must be a valid IAM role ARN')


@dataclass
class TranslationSettings:
    """Settings for translation operations."""

    formality: Optional[str] = None  # FORMAL, INFORMAL
    profanity: Optional[str] = None  # MASK
    brevity: Optional[str] = None  # ON

    def __post_init__(self):
        """Validate translation settings."""
        if self.formality and self.formality not in ['FORMAL', 'INFORMAL']:
            raise ValueError("formality must be 'FORMAL' or 'INFORMAL'")
        if self.profanity and self.profanity != 'MASK':
            raise ValueError("profanity must be 'MASK'")
        if self.brevity and self.brevity != 'ON':
            raise ValueError("brevity must be 'ON'")


@dataclass
class JobConfig:
    """Configuration for batch translation jobs."""

    job_name: str
    source_language_code: str
    target_language_codes: List[str]
    terminology_names: List[str] = field(default_factory=list)
    parallel_data_names: List[str] = field(default_factory=list)
    settings: Optional[TranslationSettings] = None

    def __post_init__(self):
        """Validate the job configuration."""
        if not self.job_name:
            raise ValueError('job_name cannot be empty')
        if not self.source_language_code:
            raise ValueError('source_language_code cannot be empty')
        if not self.target_language_codes:
            raise ValueError('target_language_codes cannot be empty')
        if len(self.target_language_codes) > 10:
            raise ValueError('Cannot specify more than 10 target languages')

        # Validate language codes format (basic validation)
        lang_pattern = r'^[a-z]{2}(-[A-Z]{2})?$'
        if not re.match(lang_pattern, self.source_language_code):
            raise ValueError(f'Invalid source language code format: {self.source_language_code}')

        for lang in self.target_language_codes:
            if not re.match(lang_pattern, lang):
                raise ValueError(f'Invalid target language code format: {lang}')


@dataclass
class TranslationJobStatus:
    """Status information for a translation job."""

    job_id: str
    job_name: str
    status: str
    progress: Optional[float] = None
    input_config: Optional[BatchInputConfig] = None
    output_config: Optional[BatchOutputConfig] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_details: Optional[str] = None

    def __post_init__(self):
        """Validate the job status."""
        if not self.job_id:
            raise ValueError('job_id cannot be empty')
        if not self.job_name:
            raise ValueError('job_name cannot be empty')
        if not self.status:
            raise ValueError('status cannot be empty')
        if self.progress is not None and not (0.0 <= self.progress <= 100.0):
            raise ValueError('progress must be between 0.0 and 100.0')


@dataclass
class TranslationJobSummary:
    """Summary information for translation jobs."""

    job_id: str
    job_name: str
    status: str
    source_language_code: str
    target_language_codes: List[str]
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate the job summary."""
        if not self.job_id:
            raise ValueError('job_id cannot be empty')
        if not self.job_name:
            raise ValueError('job_name cannot be empty')
        if not self.status:
            raise ValueError('status cannot be empty')
        if not self.source_language_code:
            raise ValueError('source_language_code cannot be empty')
        if not self.target_language_codes:
            raise ValueError('target_language_codes cannot be empty')


# Terminology Models


@dataclass
class TerminologyData:
    """Data for creating terminology."""

    terminology_data: bytes
    format: str
    directionality: str = 'UNI'  # UNI or MULTI

    def __post_init__(self):
        """Validate terminology data."""
        if not self.terminology_data:
            raise ValueError('terminology_data cannot be empty')
        if self.format not in ['CSV', 'TMX']:
            raise ValueError("format must be 'CSV' or 'TMX'")
        if self.directionality not in ['UNI', 'MULTI']:
            raise ValueError("directionality must be 'UNI' or 'MULTI'")


@dataclass
class TerminologyDetails:
    """Detailed information about a terminology."""

    name: str
    description: str
    source_language: str
    target_languages: List[str]
    term_count: int
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    size_bytes: Optional[int] = None
    format: Optional[str] = None

    def __post_init__(self):
        """Validate terminology details."""
        if not self.name:
            raise ValueError('name cannot be empty')
        if not self.source_language:
            raise ValueError('source_language cannot be empty')
        if not self.target_languages:
            raise ValueError('target_languages cannot be empty')
        if self.term_count < 0:
            raise ValueError('term_count cannot be negative')
        if self.size_bytes is not None and self.size_bytes < 0:
            raise ValueError('size_bytes cannot be negative')


@dataclass
class TerminologySummary:
    """Summary information about a terminology."""

    name: str
    description: str
    source_language: str
    target_languages: List[str]
    term_count: int
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate terminology summary."""
        if not self.name:
            raise ValueError('name cannot be empty')
        if not self.source_language:
            raise ValueError('source_language cannot be empty')
        if not self.target_languages:
            raise ValueError('target_languages cannot be empty')
        if self.term_count < 0:
            raise ValueError('term_count cannot be negative')


# Language Models


@dataclass
class LanguagePair:
    """Information about a supported language pair."""

    source_language: str
    target_language: str
    supported_formats: List[str] = field(default_factory=list)
    custom_terminology_supported: bool = True

    def __post_init__(self):
        """Validate language pair."""
        if not self.source_language:
            raise ValueError('source_language cannot be empty')
        if not self.target_language:
            raise ValueError('target_language cannot be empty')
        if self.source_language == self.target_language:
            raise ValueError('source_language and target_language cannot be the same')


@dataclass
class LanguageMetrics:
    """Usage metrics for language operations."""

    language_pair: Optional[str] = None
    translation_count: int = 0
    character_count: int = 0
    average_response_time: Optional[float] = None
    error_rate: Optional[float] = None
    time_range: str = '24h'

    def __post_init__(self):
        """Validate language metrics."""
        if self.translation_count < 0:
            raise ValueError('translation_count cannot be negative')
        if self.character_count < 0:
            raise ValueError('character_count cannot be negative')
        if self.average_response_time is not None and self.average_response_time < 0:
            raise ValueError('average_response_time cannot be negative')
        if self.error_rate is not None and not (0.0 <= self.error_rate <= 1.0):
            raise ValueError('error_rate must be between 0.0 and 1.0')


# Error Models


@dataclass
class ErrorResponse:
    """Structured error response."""

    error_type: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None

    def __post_init__(self):
        """Validate error response."""
        if not self.error_type:
            raise ValueError('error_type cannot be empty')
        if not self.error_code:
            raise ValueError('error_code cannot be empty')
        if not self.message:
            raise ValueError('message cannot be empty')
        if self.retry_after is not None and self.retry_after < 0:
            raise ValueError('retry_after cannot be negative')


# Exception Hierarchy


class TranslateException(Exception):
    """Base exception for Amazon Translate MCP Server."""

    def __init__(
        self,
        message: str,
        error_code: str = 'TRANSLATE_ERROR',
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the translate exception.

        Args:
            message: Error message
            error_code: Error code for categorization
            details: Additional error details

        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_error_response(self) -> ErrorResponse:
        """Convert exception to error response."""
        return ErrorResponse(
            error_type=self.__class__.__name__,
            error_code=self.error_code,
            message=self.message,
            details=self.details,
        )


class AuthenticationError(TranslateException):
    """AWS authentication or authorization errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the authentication error.

        Args:
            message: Error message
            details: Additional error details

        """
        super().__init__(message, 'AUTH_ERROR', details)


class ValidationError(TranslateException):
    """Input validation errors."""

    def __init__(
        self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the validation error.

        Args:
            message: Error message
            field: Field name that failed validation
            details: Additional error details

        """
        details = details or {}
        if field:
            details['field'] = field
        super().__init__(message, 'VALIDATION_ERROR', details)


class TranslationError(TranslateException):
    """Translation operation errors."""

    def __init__(
        self,
        message: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the translation error.

        Args:
            message: Error message
            source_lang: Source language code
            target_lang: Target language code
            details: Additional error details

        """
        details = details or {}
        if source_lang:
            details['source_language'] = source_lang
        if target_lang:
            details['target_language'] = target_lang
        super().__init__(message, 'TRANSLATION_ERROR', details)


class TerminologyError(TranslateException):
    """Terminology management errors."""

    def __init__(
        self,
        message: str,
        terminology_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the terminology error.

        Args:
            message: Error message
            terminology_name: Name of the terminology
            details: Additional error details

        """
        details = details or {}
        if terminology_name:
            details['terminology_name'] = terminology_name
        super().__init__(message, 'TERMINOLOGY_ERROR', details)


class BatchJobError(TranslateException):
    """Batch job operation errors."""

    def __init__(
        self, message: str, job_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the batch job error.

        Args:
            message: Error message
            job_id: Batch job identifier
            details: Additional error details

        """
        details = details or {}
        if job_id:
            details['job_id'] = job_id
        super().__init__(message, 'BATCH_JOB_ERROR', details)


class RateLimitError(TranslateException):
    """Rate limiting errors."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            details: Additional error details

        """
        super().__init__(message, 'RATE_LIMIT_ERROR', details)
        self.retry_after = retry_after

    def to_error_response(self) -> ErrorResponse:
        """Convert exception to error response with retry_after."""
        response = super().to_error_response()
        response.retry_after = self.retry_after
        return response


class ServiceUnavailableError(TranslateException):
    """Service unavailability errors."""

    def __init__(
        self, message: str, service: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the service unavailable error.

        Args:
            message: Error message
            service: Name of the unavailable service
            details: Additional error details

        """
        details = details or {}
        if service:
            details['service'] = service
        super().__init__(message, 'SERVICE_UNAVAILABLE', details)


class QuotaExceededError(TranslateException):
    """AWS service quota exceeded errors."""

    def __init__(
        self,
        message: str,
        quota_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the quota exceeded error.

        Args:
            message: Error message
            quota_type: Type of quota exceeded
            details: Additional error details

        """
        details = details or {}
        if quota_type:
            details['quota_type'] = quota_type
        super().__init__(message, 'QUOTA_EXCEEDED', details)
