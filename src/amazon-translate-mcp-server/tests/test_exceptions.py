"""Unit tests for exception handling in Amazon Translate MCP Server.

Tests the custom exception hierarchy, error response formatting,
and AWS error mapping functionality.
"""

import pytest
import uuid
from awslabs.amazon_translate_mcp_server.exceptions import (
    AWS_ERROR_MAPPING,
    AuthenticationError,
    BatchJobError,
    ConfigurationError,
    ErrorResponse,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
    TerminologyError,
    TimeoutError,
    TranslateException,
    TranslationError,
    ValidationError,
    map_aws_error,
)
from datetime import datetime
from unittest.mock import Mock


class TestErrorResponse:
    """Test ErrorResponse dataclass functionality."""

    def test_error_response_creation(self):
        """Test basic ErrorResponse creation."""
        response = ErrorResponse(
            error_type='TestError', error_code='TEST_001', message='Test error message'
        )

        assert response.error_type == 'TestError'
        assert response.error_code == 'TEST_001'
        assert response.message == 'Test error message'
        assert response.correlation_id is not None
        assert response.timestamp is not None

    def test_error_response_with_details(self):
        """Test ErrorResponse with additional details."""
        details = {'field': 'value', 'count': 42}
        response = ErrorResponse(
            error_type='ValidationError',
            error_code='VALIDATION_001',
            message='Validation failed',
            details=details,
            retry_after=30,
        )

        assert response.details == details
        assert response.retry_after == 30

    def test_error_response_auto_fields(self):
        """Test automatic generation of correlation_id and timestamp."""
        response = ErrorResponse(
            error_type='TestError', error_code='TEST_001', message='Test message'
        )

        # Check that correlation_id is a valid UUID
        uuid.UUID(response.correlation_id)

        # Check that timestamp is a valid ISO format
        assert response.timestamp is not None
        datetime.fromisoformat(response.timestamp)


class TestTranslateException:
    """Test base TranslateException functionality."""

    def test_basic_exception_creation(self):
        """Test basic exception creation."""
        exc = TranslateException('Test error')

        assert str(exc) == 'Test error'
        assert exc.message == 'Test error'
        assert exc.error_code == 'TRANSLATE_ERROR'
        assert exc.details == {}
        assert exc.retry_after is None
        assert exc.correlation_id is not None
        assert exc.timestamp is not None

    def test_exception_with_all_parameters(self):
        """Test exception creation with all parameters."""
        correlation_id = str(uuid.uuid4())
        details = {'key': 'value'}

        exc = TranslateException(
            message='Custom error',
            error_code='CUSTOM_001',
            details=details,
            retry_after=60,
            correlation_id=correlation_id,
        )

        assert exc.message == 'Custom error'
        assert exc.error_code == 'CUSTOM_001'
        assert exc.details == details
        assert exc.retry_after == 60
        assert exc.correlation_id == correlation_id

    def test_to_error_response(self):
        """Test conversion to ErrorResponse."""
        exc = TranslateException(
            message='Test error', error_code='TEST_001', details={'field': 'value'}
        )

        response = exc.to_error_response()

        assert isinstance(response, ErrorResponse)
        assert response.error_type == 'TranslateException'
        assert response.error_code == 'TEST_001'
        assert response.message == 'Test error'
        assert response.details == {'field': 'value'}
        assert response.correlation_id == exc.correlation_id


class TestSpecificExceptions:
    """Test specific exception types."""

    def test_authentication_error(self):
        """Test AuthenticationError functionality."""
        exc = AuthenticationError('Invalid credentials')

        assert isinstance(exc, TranslateException)
        assert exc.error_code == 'AUTH_ERROR'
        assert exc.message == 'Invalid credentials'

    def test_validation_error_with_field_errors(self):
        """Test ValidationError with field-specific errors."""
        field_errors = {'email': 'Invalid format', 'age': 'Must be positive'}
        exc = ValidationError(message='Validation failed', field_errors=field_errors)

        assert exc.error_code == 'VALIDATION_ERROR'
        assert exc.details['field_errors'] == field_errors

    def test_translation_error_with_languages(self):
        """Test TranslationError with language information."""
        exc = TranslationError(
            message='Unsupported language pair', source_language='xx', target_language='yy'
        )

        assert exc.error_code == 'TRANSLATION_ERROR'
        assert exc.details['source_language'] == 'xx'
        assert exc.details['target_language'] == 'yy'

    def test_terminology_error_with_name(self):
        """Test TerminologyError with terminology name."""
        exc = TerminologyError(message='Terminology not found', terminology_name='my-terminology')

        assert exc.error_code == 'TERMINOLOGY_ERROR'
        assert exc.details['terminology_name'] == 'my-terminology'

    def test_batch_job_error_with_job_info(self):
        """Test BatchJobError with job information."""
        exc = BatchJobError(message='Job failed', job_id='job-123', job_status='FAILED')

        assert exc.error_code == 'BATCH_JOB_ERROR'
        assert exc.details['job_id'] == 'job-123'
        assert exc.details['job_status'] == 'FAILED'

    def test_rate_limit_error_with_retry_after(self):
        """Test RateLimitError with retry_after."""
        exc = RateLimitError(message='Rate limit exceeded', retry_after=30)

        assert exc.error_code == 'RATE_LIMIT_ERROR'
        assert exc.retry_after == 30

    def test_quota_exceeded_error_with_quota_info(self):
        """Test QuotaExceededError with quota information."""
        exc = QuotaExceededError(
            message='Quota exceeded', quota_type='concurrent_jobs', current_usage=10, quota_limit=5
        )

        assert exc.error_code == 'QUOTA_EXCEEDED_ERROR'
        assert exc.details['quota_type'] == 'concurrent_jobs'
        assert exc.details['current_usage'] == 10
        assert exc.details['quota_limit'] == 5

    def test_service_unavailable_error_with_service(self):
        """Test ServiceUnavailableError with service name."""
        exc = ServiceUnavailableError(message='Service unavailable', service_name='translate')

        assert exc.error_code == 'SERVICE_UNAVAILABLE_ERROR'
        assert exc.details['service_name'] == 'translate'

    def test_configuration_error_with_config_key(self):
        """Test ConfigurationError with config key."""
        exc = ConfigurationError(message='Missing configuration', config_key='aws_region')

        assert exc.error_code == 'CONFIGURATION_ERROR'
        assert exc.details['config_key'] == 'aws_region'

    def test_timeout_error_with_timeout_info(self):
        """Test TimeoutError with timeout information."""
        exc = TimeoutError(
            message='Operation timed out', timeout_seconds=30, operation='translate_text'
        )

        assert exc.error_code == 'TIMEOUT_ERROR'
        assert exc.details['timeout_seconds'] == 30
        assert exc.details['operation'] == 'translate_text'


class TestAWSErrorMapping:
    """Test AWS error mapping functionality."""

    def test_map_known_aws_error(self):
        """Test mapping of known AWS error codes."""
        # Mock AWS error
        aws_error = Mock()
        aws_error.response = {
            'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'},
            'ResponseMetadata': {'RequestId': 'req-123', 'HTTPStatusCode': 403},
        }

        mapped_error = map_aws_error(aws_error)

        assert isinstance(mapped_error, AuthenticationError)
        assert mapped_error.error_code == 'AccessDeniedException'
        assert mapped_error.details['aws_error_code'] == 'AccessDeniedException'
        assert mapped_error.details['aws_request_id'] == 'req-123'
        assert mapped_error.details['aws_http_status'] == 403

    def test_map_throttling_error_with_retry_after(self):
        """Test mapping of throttling error with retry_after."""
        aws_error = Mock()
        aws_error.response = {
            'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'},
            'ResponseMetadata': {'RequestId': 'req-456', 'HTTPHeaders': {'Retry-After': '60'}},
        }

        mapped_error = map_aws_error(aws_error)

        assert isinstance(mapped_error, RateLimitError)
        assert mapped_error.retry_after == 60

    def test_map_unknown_aws_error(self):
        """Test mapping of unknown AWS error codes."""
        aws_error = Mock()
        aws_error.response = {'Error': {'Code': 'UnknownException', 'Message': 'Unknown error'}}

        mapped_error = map_aws_error(aws_error)

        assert isinstance(mapped_error, TranslateException)
        assert mapped_error.error_code == 'UnknownException'

    def test_map_error_without_response(self):
        """Test mapping of error without response attribute."""
        aws_error = Exception('Generic error')

        mapped_error = map_aws_error(aws_error)

        assert isinstance(mapped_error, TranslateException)
        assert mapped_error.error_code == 'UnknownError'
        assert 'Generic error' in mapped_error.message

    def test_map_error_with_correlation_id(self):
        """Test mapping with provided correlation ID."""
        correlation_id = str(uuid.uuid4())
        aws_error = Mock()
        aws_error.response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}}

        mapped_error = map_aws_error(aws_error, correlation_id)

        assert mapped_error.correlation_id == correlation_id

    def test_aws_error_mapping_completeness(self):
        """Test that all AWS error codes are mapped to appropriate exception types."""
        expected_mappings = {
            'AccessDeniedException': AuthenticationError,
            'UnauthorizedOperation': AuthenticationError,
            'InvalidParameterException': ValidationError,
            'InvalidParameterValueException': ValidationError,
            'ValidationException': ValidationError,
            'ThrottlingException': RateLimitError,
            'TooManyRequestsException': RateLimitError,
            'LimitExceededException': QuotaExceededError,
            'ServiceQuotaExceededException': QuotaExceededError,
            'ServiceUnavailableException': ServiceUnavailableError,
            'InternalServiceException': ServiceUnavailableError,
            'UnsupportedLanguagePairException': TranslationError,
            'DetectedLanguageLowConfidenceException': TranslationError,
            'TextSizeLimitExceededException': ValidationError,
            'ResourceNotFoundException': TerminologyError,
            'ConflictException': TerminologyError,
            'ConcurrentModificationException': BatchJobError,
            'InvalidRequestException': ValidationError,
        }

        for error_code, expected_type in expected_mappings.items():
            assert AWS_ERROR_MAPPING[error_code] == expected_type


class TestErrorResponseIntegration:
    """Test integration between exceptions and error responses."""

    def test_exception_to_response_conversion(self):
        """Test complete exception to response conversion."""
        exc = ValidationError(
            message='Invalid input data',
            error_code='VALIDATION_001',
            field_errors={'name': 'Required field'},
            correlation_id='test-correlation-id',
        )

        response = exc.to_error_response()

        assert response.error_type == 'ValidationError'
        assert response.error_code == 'VALIDATION_001'
        assert response.message == 'Invalid input data'
        assert (
            response.details is not None
            and response.details['field_errors']['name'] == 'Required field'
        )
        assert response.correlation_id == 'test-correlation-id'
        assert response.retry_after is None

    def test_rate_limit_response_with_retry_after(self):
        """Test rate limit error response includes retry_after."""
        exc = RateLimitError(message='Too many requests', retry_after=120)

        response = exc.to_error_response()

        assert response.error_type == 'RateLimitError'
        assert response.retry_after == 120

    def test_nested_error_details(self):
        """Test error response with nested details."""
        details = {
            'validation_errors': {
                'source_language': 'Invalid language code',
                'target_language': 'Unsupported language',
            },
            'request_info': {'method': 'translate_text', 'timestamp': '2023-01-01T00:00:00Z'},
        }

        exc = ValidationError(message='Multiple validation errors', details=details)

        response = exc.to_error_response()

        assert response.details == details
        assert (
            response.details is not None
            and response.details['validation_errors']['source_language'] == 'Invalid language code'
        )
        assert (
            response.details is not None
            and response.details['request_info']['method'] == 'translate_text'
        )


if __name__ == '__main__':
    pytest.main([__file__])
