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

"""Custom exception hierarchy for Amazon Translate MCP Server.

This module defines a comprehensive exception hierarchy that provides structured
error handling for all translation operations, AWS service interactions, and
MCP protocol communications.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ErrorResponse:
    """Structured error response format for MCP tools."""

    error_type: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None  # For rate limiting
    correlation_id: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        """Initialize correlation ID and timestamp if not provided."""
        if self.correlation_id is None:
            self.correlation_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class TranslateException(Exception):
    """Base exception for Amazon Translate MCP Server.

    All custom exceptions inherit from this base class to provide
    consistent error handling and structured error responses.
    """

    def __init__(
        self,
        message: str,
        error_code: str = 'TRANSLATE_ERROR',
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
        correlation_id: Optional[str] = None,
    ):
        """Initialize the base exception.

        Args:
            message: Error message
            error_code: Error code for categorization
            details: Additional error details
            retry_after: Seconds to wait before retry
            correlation_id: Request correlation ID

        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.retry_after = retry_after
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()

    def to_error_response(self) -> ErrorResponse:
        """Convert exception to structured error response."""
        return ErrorResponse(
            error_type=self.__class__.__name__,
            error_code=self.error_code,
            message=self.message,
            details=self.details,
            retry_after=self.retry_after,
            correlation_id=self.correlation_id,
            timestamp=self.timestamp,
        )


class AuthenticationError(TranslateException):
    """AWS authentication or authorization errors.

    Raised when AWS credentials are invalid, expired, or insufficient
    permissions exist for the requested operation.
    """

    def __init__(
        self,
        message: str,
        error_code: str = 'AUTH_ERROR',
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Initialize the authentication error.

        Args:
            message: Error message
            error_code: Error code for categorization
            details: Additional error details
            **kwargs: Additional keyword arguments

        """
        super().__init__(message, error_code, details, **kwargs)


class ValidationError(TranslateException):
    """Input validation errors.

    Raised when input parameters fail validation checks,
    including missing required fields, invalid formats, or
    constraint violations.
    """

    def __init__(
        self,
        message: str,
        error_code: str = 'VALIDATION_ERROR',
        field_errors: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        """Initialize the validation error.

        Args:
            message: Error message
            error_code: Error code for categorization
            field_errors: Field-specific validation errors
            **kwargs: Additional keyword arguments

        """
        details = kwargs.pop('details', {})
        if field_errors:
            details['field_errors'] = field_errors
        super().__init__(message, error_code, details, **kwargs)


class TranslationError(TranslateException):
    """Translation operation errors.

    Raised when translation operations fail due to service issues,
    unsupported language pairs, or content-related problems.
    """

    def __init__(
        self,
        message: str,
        error_code: str = 'TRANSLATION_ERROR',
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the translation error.

        Args:
            message: Error message
            error_code: Error code for categorization
            source_language: Source language code
            target_language: Target language code
            **kwargs: Additional keyword arguments

        """
        details = kwargs.pop('details', {})
        if source_language:
            details['source_language'] = source_language
        if target_language:
            details['target_language'] = target_language
        super().__init__(message, error_code, details, **kwargs)


class TerminologyError(TranslateException):
    """Terminology management errors.

    Raised when terminology operations fail, including creation,
    import, or retrieval of custom terminology sets.
    """

    def __init__(
        self,
        message: str,
        error_code: str = 'TERMINOLOGY_ERROR',
        terminology_name: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the terminology error.

        Args:
            message: Error message
            error_code: Error code for categorization
            terminology_name: Name of the terminology
            **kwargs: Additional keyword arguments

        """
        details = kwargs.pop('details', {})
        if terminology_name:
            details['terminology_name'] = terminology_name
        super().__init__(message, error_code, details, **kwargs)


class BatchJobError(TranslateException):
    """Batch job operation errors.

    Raised when batch translation jobs fail to start, complete,
    or when job status operations encounter issues.
    """

    def __init__(
        self,
        message: str,
        error_code: str = 'BATCH_JOB_ERROR',
        job_id: Optional[str] = None,
        job_status: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the batch job error.

        Args:
            message: Error message
            error_code: Error code for categorization
            job_id: Batch job identifier
            job_status: Current job status
            **kwargs: Additional keyword arguments

        """
        details = kwargs.pop('details', {})
        if job_id:
            details['job_id'] = job_id
        if job_status:
            details['job_status'] = job_status
        super().__init__(message, error_code, details, **kwargs)


class RateLimitError(TranslateException):
    """Rate limiting errors.

    Raised when AWS service rate limits are exceeded.
    Includes retry_after information for exponential backoff.
    """

    def __init__(
        self, message: str, retry_after: int, error_code: str = 'RATE_LIMIT_ERROR', **kwargs
    ):
        """Initialize the rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            error_code: Error code for categorization
            **kwargs: Additional keyword arguments

        """
        super().__init__(message, error_code, retry_after=retry_after, **kwargs)


class QuotaExceededError(TranslateException):
    """AWS service quota exceeded errors.

    Raised when AWS service quotas or limits are exceeded,
    such as maximum concurrent jobs or character limits.
    """

    def __init__(
        self,
        message: str,
        error_code: str = 'QUOTA_EXCEEDED_ERROR',
        quota_type: Optional[str] = None,
        current_usage: Optional[int] = None,
        quota_limit: Optional[int] = None,
        **kwargs,
    ):
        """Initialize the quota exceeded error.

        Args:
            message: Error message
            error_code: Error code for categorization
            quota_type: Type of quota exceeded
            current_usage: Current usage amount
            quota_limit: Quota limit
            **kwargs: Additional keyword arguments

        """
        details = kwargs.pop('details', {})
        if quota_type:
            details['quota_type'] = quota_type
        if current_usage is not None:
            details['current_usage'] = current_usage
        if quota_limit is not None:
            details['quota_limit'] = quota_limit
        super().__init__(message, error_code, details, **kwargs)

        # Store as attributes for backward compatibility with tests
        self.quota_type = quota_type
        self.current_usage = current_usage
        self.quota_limit = quota_limit


class ServiceUnavailableError(TranslateException):
    """AWS service unavailability errors.

    Raised when AWS services are temporarily unavailable
    or experiencing outages.
    """

    def __init__(
        self,
        message: str,
        error_code: str = 'SERVICE_UNAVAILABLE_ERROR',
        service_name: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the service unavailable error.

        Args:
            message: Error message
            error_code: Error code for categorization
            service_name: Name of the unavailable service
            **kwargs: Additional keyword arguments

        """
        details = kwargs.pop('details', {})
        if service_name:
            details['service_name'] = service_name
        super().__init__(message, error_code, details, **kwargs)

        # Store as attribute for backward compatibility with tests
        self.service = service_name


class ConfigurationError(TranslateException):
    """Configuration and setup errors.

    Raised when server configuration is invalid or
    required environment variables are missing.
    """

    def __init__(
        self,
        message: str,
        error_code: str = 'CONFIGURATION_ERROR',
        config_key: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the configuration error.

        Args:
            message: Error message
            error_code: Error code for categorization
            config_key: Configuration key that caused the error
            **kwargs: Additional keyword arguments

        """
        details = kwargs.pop('details', {})
        if config_key:
            details['config_key'] = config_key
        super().__init__(message, error_code, details, **kwargs)


class TimeoutError(TranslateException):
    """Operation timeout errors.

    Raised when operations exceed configured timeout limits.
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: int,
        error_code: str = 'TIMEOUT_ERROR',
        operation: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the timeout error.

        Args:
            message: Error message
            timeout_seconds: Timeout duration in seconds
            error_code: Error code for categorization
            operation: Operation that timed out
            **kwargs: Additional keyword arguments

        """
        details = kwargs.pop('details', {})
        details['timeout_seconds'] = timeout_seconds
        if operation:
            details['operation'] = operation
        super().__init__(message, error_code, details, **kwargs)


class SecurityError(TranslateException):
    """Security-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = 'SECURITY_ERROR',
        security_type: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the security error.

        Args:
            message: Error message
            error_code: Error code for categorization
            security_type: Type of security violation
            **kwargs: Additional keyword arguments

        """
        details = kwargs.pop('details', {})
        if security_type:
            details['security_type'] = security_type
        super().__init__(message, error_code, details, **kwargs)


# Exception mapping for AWS service errors
AWS_ERROR_MAPPING = {
    'AccessDeniedException': AuthenticationError,
    'AccessDenied': AuthenticationError,  # STS specific error code
    'SignatureDoesNotMatch': AuthenticationError,  # STS specific error code
    'UnauthorizedOperation': AuthenticationError,
    'InvalidParameterException': ValidationError,
    'InvalidParameterValueException': ValidationError,
    'ValidationException': ValidationError,
    'ThrottlingException': RateLimitError,
    'TooManyRequestsException': RateLimitError,
    'LimitExceededException': QuotaExceededError,
    'ServiceQuotaExceededException': QuotaExceededError,
    'ServiceUnavailableException': ServiceUnavailableError,
    'ServiceUnavailable': ServiceUnavailableError,  # Alternative error code
    'InternalServiceException': ServiceUnavailableError,
    'UnsupportedLanguagePairException': TranslationError,
    'DetectedLanguageLowConfidenceException': TranslationError,
    'TextSizeLimitExceededException': ValidationError,
    'ResourceNotFoundException': TerminologyError,
    'ConflictException': TerminologyError,
    'ConcurrentModificationException': BatchJobError,
    'InvalidRequestException': ValidationError,
    'InvalidRegion': ServiceUnavailableError,  # Client creation error
}


def map_aws_error(
    aws_error: Exception, correlation_id: Optional[str] = None
) -> TranslateException:
    """Map AWS service errors to custom exception types.

    Args:
        aws_error: The original AWS service error
        correlation_id: Optional correlation ID for tracking

    Returns:
        Mapped custom exception with structured error information

    """
    # Handle BotoCoreError specifically
    from botocore.exceptions import BotoCoreError

    if isinstance(aws_error, BotoCoreError):
        return ServiceUnavailableError(
            message=f'BotoCore error: {str(aws_error)}', correlation_id=correlation_id
        )

    error_code = getattr(aws_error, 'response', {}).get('Error', {}).get('Code', 'UnknownError')
    error_message = str(aws_error)

    # Extract additional error details from AWS response
    from botocore.exceptions import ClientError

    details = {}
    # Check if it's a ClientError or has response attribute (for Mock objects in tests)
    if isinstance(aws_error, ClientError) or hasattr(aws_error, 'response'):
        response = getattr(aws_error, 'response', {})
        if 'Error' in response:
            error_info = response['Error']
            details.update(
                {
                    'error_code': error_info.get('Code'),  # For backward compatibility with tests
                    'aws_error_code': error_info.get('Code'),
                    'aws_request_id': response.get('ResponseMetadata', {}).get('RequestId'),
                    'aws_http_status': response.get('ResponseMetadata', {}).get('HTTPStatusCode'),
                }
            )

    # Map to appropriate exception type
    exception_class = AWS_ERROR_MAPPING.get(error_code, TranslateException)

    # Customize error messages for better user experience
    if exception_class == AuthenticationError:
        if error_code in ['AccessDenied', 'AccessDeniedException']:
            error_message = f'Invalid AWS credentials or insufficient permissions: {error_message}'
        elif error_code == 'SignatureDoesNotMatch':
            error_message = f'Invalid AWS credentials (signature mismatch): {error_message}'
        else:
            error_message = f'AWS authentication failed: {error_message}'
    elif exception_class == ServiceUnavailableError:
        error_message = f'AWS service temporarily unavailable: {error_message}'

    # Handle rate limiting with retry_after
    retry_after = None
    if error_code in ['ThrottlingException', 'TooManyRequestsException']:
        # Extract retry_after from headers if available
        if hasattr(aws_error, 'response'):
            response = getattr(aws_error, 'response', {})
            headers = response.get('ResponseMetadata', {}).get('HTTPHeaders', {})
            retry_after = headers.get('Retry-After')
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except (ValueError, TypeError):
                    retry_after = None

    return exception_class(
        message=error_message,
        error_code=error_code,
        details=details,
        retry_after=retry_after,
        correlation_id=correlation_id,
    )


class WorkflowError(TranslateException):
    """Workflow orchestration errors."""

    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        workflow_step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the workflow error.

        Args:
            message: Error message
            workflow_id: Workflow identifier
            workflow_step: Current workflow step
            details: Additional error details

        """
        details = details or {}
        if workflow_id:
            details['workflow_id'] = workflow_id
        if workflow_step:
            details['workflow_step'] = workflow_step
        super().__init__(message, 'WORKFLOW_ERROR', details)
