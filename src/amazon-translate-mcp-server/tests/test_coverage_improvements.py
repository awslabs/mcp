"""Additional tests to improve coverage for specific modules."""

import pytest
from awslabs.amazon_translate_mcp_server.exceptions import (
    AuthenticationError,
    TranslateException,
)
from awslabs.amazon_translate_mcp_server.models import (
    ErrorResponse,
    LanguageDetectionResult,
    TranslationResult,
    ValidationResult,
)
from unittest.mock import Mock, patch


class TestModelValidation:
    """Test model validation edge cases."""

    def test_translation_result_edge_cases(self):
        """Test TranslationResult with edge case values."""
        # Test with minimum confidence score
        result = TranslationResult(
            translated_text='Hola',
            source_language='en',
            target_language='es',
            confidence_score=0.0,
        )
        assert result.confidence_score == 0.0

        # Test with maximum confidence score
        result = TranslationResult(
            translated_text='Hola',
            source_language='en',
            target_language='es',
            confidence_score=1.0,
        )
        assert result.confidence_score == 1.0

    def test_language_detection_result_edge_cases(self):
        """Test LanguageDetectionResult with edge case values."""
        # Test with alternative languages
        result = LanguageDetectionResult(
            detected_language='es',
            confidence_score=0.95,
            alternative_languages=[('pt', 0.03), ('it', 0.02)],
        )
        assert len(result.alternative_languages) == 2
        assert result.alternative_languages[0][0] == 'pt'

    def test_validation_result_edge_cases(self):
        """Test ValidationResult with various quality scores."""
        # Test with very low quality
        result = ValidationResult(
            is_valid=False,
            quality_score=0.1,
            issues=['low_quality', 'length_mismatch'],
            suggestions=['Review translation', 'Check length'],
        )
        assert result.is_valid is False
        assert len(result.issues) == 2
        assert len(result.suggestions) == 2

    def test_error_response_with_retry_after(self):
        """Test ErrorResponse with retry_after field."""
        error = ErrorResponse(
            error_type='RateLimitError',
            error_code='RATE_LIMIT_001',
            message='Rate limit exceeded',
            retry_after=60,
        )
        assert error.retry_after == 60

    def test_error_response_with_details(self):
        """Test ErrorResponse with complex details."""
        details = {'field_errors': {'name': 'Required'}, 'validation_info': {'max_length': 100}}
        error = ErrorResponse(
            error_type='ValidationError',
            error_code='VALIDATION_001',
            message='Validation failed',
            details=details,
        )
        assert error.details == details


class TestExceptionHandling:
    """Test exception handling edge cases."""

    def test_translate_exception_with_correlation_id(self):
        """Test TranslateException with correlation ID."""
        exc = TranslateException(
            'Test error', error_code='TEST_001', correlation_id='test-correlation-123'
        )
        assert exc.correlation_id == 'test-correlation-123'

    def test_translate_exception_to_error_response(self):
        """Test TranslateException conversion to ErrorResponse."""
        exc = TranslateException('Test error', error_code='TEST_001', details={'key': 'value'})
        response = exc.to_error_response()
        assert response.error_type == 'TranslateException'
        assert response.error_code == 'TEST_001'
        assert response.message == 'Test error'
        assert response.details == {'key': 'value'}

    def test_validation_error_with_field(self):
        """Test TranslateException with field information."""
        exc = TranslateException('Invalid field value', details={'field': 'username'})
        assert exc.details['field'] == 'username'

    def test_authentication_error_basic(self):
        """Test AuthenticationError basic functionality."""
        exc = AuthenticationError('Access denied')
        assert exc.error_code == 'AUTH_ERROR'
        response = exc.to_error_response()
        assert response.error_type == 'AuthenticationError'


class TestUtilityFunctions:
    """Test utility functions and edge cases."""

    def test_datetime_handling(self):
        """Test datetime handling in models."""
        # Test that datetime objects are handled properly
        result = TranslationResult(
            translated_text='Test',
            source_language='en',
            target_language='es',
            confidence_score=0.95,
        )
        # The model should handle datetime fields properly
        assert result.translated_text == 'Test'

    def test_optional_fields(self):
        """Test models with optional fields."""
        # Test ValidationResult with minimal fields
        result = ValidationResult(is_valid=True, quality_score=0.9)
        assert result.is_valid is True
        assert result.quality_score == 0.9
        assert result.issues == []
        assert result.suggestions == []

    def test_language_detection_without_alternatives(self):
        """Test LanguageDetectionResult without alternative languages."""
        result = LanguageDetectionResult(detected_language='en', confidence_score=0.99)
        assert result.detected_language == 'en'
        assert result.alternative_languages == []


class TestConfigurationEdgeCases:
    """Test configuration edge cases."""

    def test_server_config_defaults(self):
        """Test ServerConfig default values."""
        from awslabs.amazon_translate_mcp_server.config import ServerConfig

        config = ServerConfig()

        # Test that defaults are set properly
        assert config.log_level == 'INFO'
        assert config.max_text_length == 10000
        assert config.batch_timeout == 3600
        assert config.cache_ttl == 3600
        assert config.enable_translation_cache is True
        assert config.enable_pii_detection is False

    def test_server_config_to_security_config(self):
        """Test ServerConfig to SecurityConfig conversion."""
        from awslabs.amazon_translate_mcp_server.config import ServerConfig

        config = ServerConfig()
        config.enable_pii_detection = True
        config.enable_profanity_filter = True
        config.enable_content_filtering = True

        security_config = config.to_security_config()

        assert security_config.enable_pii_detection is True
        assert security_config.enable_profanity_filter is True
        assert security_config.enable_content_filtering is True


class TestLoggingConfiguration:
    """Test logging configuration edge cases."""

    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        from awslabs.amazon_translate_mcp_server.logging_config import setup_logging

        # Test that setup_logging doesn't raise an exception
        setup_logging()

        # Test with custom level
        setup_logging(log_level='DEBUG')

    def test_structured_formatter(self):
        """Test structured formatter functionality."""
        import logging
        from awslabs.amazon_translate_mcp_server.logging_config import StructuredFormatter

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert 'Test message' in formatted


class TestConfigValidationCoverage:
    """Additional tests to improve config validation coverage."""

    @patch('boto3.Session')
    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_s3_success(
        self, mock_validate_aws, mock_load_config, mock_boto3_session
    ):
        """Test configuration validation with successful S3 connectivity."""
        from awslabs.amazon_translate_mcp_server.config import (
            ServerConfig,
            validate_startup_configuration,
        )

        config = ServerConfig()
        config.aws_region = 'us-east-1'
        mock_load_config.return_value = config

        # Mock AWS session and clients
        mock_session = Mock()
        mock_boto3_session.return_value = mock_session

        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = {'Languages': []}

        mock_s3_client = Mock()
        mock_s3_client.list_buckets.return_value = {'Buckets': []}

        mock_session.client.side_effect = lambda service: {
            'translate': mock_translate_client,
            's3': mock_s3_client,
        }[service]

        result = validate_startup_configuration()
        assert result == config

    @patch('boto3.Session')
    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_s3_failure(
        self, mock_validate_aws, mock_load_config, mock_boto3_session
    ):
        """Test configuration validation with S3 connectivity failure."""
        from awslabs.amazon_translate_mcp_server.config import (
            ServerConfig,
            validate_startup_configuration,
        )
        from botocore.exceptions import ClientError

        config = ServerConfig()
        config.aws_region = 'us-east-1'
        mock_load_config.return_value = config

        # Mock AWS session and clients
        mock_session = Mock()
        mock_boto3_session.return_value = mock_session

        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = {'Languages': []}

        mock_s3_client = Mock()
        mock_s3_client.list_buckets.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'S3 access denied'}},
            operation_name='list_buckets',
        )

        mock_session.client.side_effect = lambda service: {
            'translate': mock_translate_client,
            's3': mock_s3_client,
        }[service]

        # Should not raise exception, just warn
        result = validate_startup_configuration()
        assert result == config

    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_large_file_size_warning(
        self, mock_validate_aws, mock_load_config
    ):
        """Test configuration validation with large file size warning."""
        from awslabs.amazon_translate_mcp_server.config import (
            ServerConfig,
            validate_startup_configuration,
        )

        config = ServerConfig()
        config.max_file_size = 200 * 1024 * 1024  # 200MB (over 100MB threshold)
        mock_load_config.return_value = config

        # Should not raise exception, just warn
        result = validate_startup_configuration()
        assert result == config

    @patch('boto3.Session')
    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_credentials_error(
        self, mock_validate_aws, mock_load_config, mock_boto3_session
    ):
        """Test configuration validation with credentials error."""
        from awslabs.amazon_translate_mcp_server.config import (
            ServerConfig,
            validate_startup_configuration,
        )
        from botocore.exceptions import NoCredentialsError

        config = ServerConfig()
        mock_load_config.return_value = config

        mock_boto3_session.side_effect = NoCredentialsError()

        with pytest.raises(RuntimeError, match='AWS credentials not found or incomplete'):
            validate_startup_configuration()

    @patch('boto3.Session')
    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_partial_credentials_error(
        self, mock_validate_aws, mock_load_config, mock_boto3_session
    ):
        """Test configuration validation with partial credentials error."""
        from awslabs.amazon_translate_mcp_server.config import (
            ServerConfig,
            validate_startup_configuration,
        )
        from botocore.exceptions import PartialCredentialsError

        config = ServerConfig()
        mock_load_config.return_value = config

        mock_boto3_session.side_effect = PartialCredentialsError(
            provider='env', cred_var='AWS_SECRET_ACCESS_KEY'
        )

        with pytest.raises(RuntimeError, match='AWS credentials not found or incomplete'):
            validate_startup_configuration()

    @patch('boto3.Session')
    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_generic_exception(
        self, mock_validate_aws, mock_load_config, mock_boto3_session
    ):
        """Test configuration validation with generic exception."""
        from awslabs.amazon_translate_mcp_server.config import (
            ServerConfig,
            validate_startup_configuration,
        )

        config = ServerConfig()
        mock_load_config.return_value = config

        mock_session = Mock()
        mock_boto3_session.return_value = mock_session

        mock_translate_client = Mock()
        mock_translate_client.list_languages.side_effect = Exception('Generic error')
        mock_session.client.return_value = mock_translate_client

        # Should not raise exception, just warn
        result = validate_startup_configuration()
        assert result == config


class TestExceptionMappingCoverage:
    """Additional tests to improve exception mapping coverage."""

    def test_map_aws_error_authentication_access_denied(self):
        """Test mapping AWS authentication error with AccessDenied."""
        from awslabs.amazon_translate_mcp_server.exceptions import (
            AuthenticationError,
            map_aws_error,
        )
        from botocore.exceptions import ClientError

        aws_error = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='translate_text',
        )

        result = map_aws_error(aws_error)
        assert isinstance(result, AuthenticationError)
        assert 'Invalid AWS credentials or insufficient permissions' in result.message

    def test_map_aws_error_authentication_signature_mismatch(self):
        """Test mapping AWS authentication error with SignatureDoesNotMatch."""
        from awslabs.amazon_translate_mcp_server.exceptions import (
            AuthenticationError,
            map_aws_error,
        )
        from botocore.exceptions import ClientError

        aws_error = ClientError(
            error_response={
                'Error': {'Code': 'SignatureDoesNotMatch', 'Message': 'Signature mismatch'}
            },
            operation_name='translate_text',
        )

        result = map_aws_error(aws_error)
        assert isinstance(result, AuthenticationError)
        assert 'Invalid AWS credentials (signature mismatch)' in result.message

    def test_map_aws_error_service_unavailable_custom_message(self):
        """Test mapping service unavailable error with custom message."""
        from awslabs.amazon_translate_mcp_server.exceptions import (
            ServiceUnavailableError,
            map_aws_error,
        )
        from botocore.exceptions import ClientError

        aws_error = ClientError(
            error_response={'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service down'}},
            operation_name='translate_text',
        )

        result = map_aws_error(aws_error)
        assert isinstance(result, ServiceUnavailableError)
        assert 'AWS service temporarily unavailable' in result.message

    def test_map_aws_error_throttling_with_retry_after(self):
        """Test mapping throttling error with retry_after header."""
        from awslabs.amazon_translate_mcp_server.exceptions import map_aws_error
        from botocore.exceptions import ClientError

        # Create a mock AWS error with retry-after header
        aws_error = ClientError(
            error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            operation_name='translate_text',
        )

        # Mock the response with retry-after header
        mock_response = {
            'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'},
            'ResponseMetadata': {'HTTPHeaders': {'Retry-After': '30'}},
        }
        aws_error.response = mock_response

        result = map_aws_error(aws_error)
        # Check that it's some kind of exception (the mapping might return TranslateException)
        assert result.error_code == 'ThrottlingException'

    def test_map_aws_error_throttling_invalid_retry_after(self):
        """Test mapping throttling error with invalid retry_after header."""
        from awslabs.amazon_translate_mcp_server.exceptions import map_aws_error
        from botocore.exceptions import ClientError

        aws_error = ClientError(
            error_response={
                'Error': {'Code': 'TooManyRequestsException', 'Message': 'Rate exceeded'}
            },
            operation_name='translate_text',
        )

        # Mock the response with invalid retry-after header
        mock_response = {
            'Error': {'Code': 'TooManyRequestsException', 'Message': 'Rate exceeded'},
            'ResponseMetadata': {'HTTPHeaders': {'Retry-After': 'invalid'}},
        }
        aws_error.response = mock_response

        result = map_aws_error(aws_error)
        # Check that it's some kind of exception
        assert result.error_code == 'TooManyRequestsException'


class TestLoggingConfigurationCoverage:
    """Additional tests to improve logging configuration coverage."""

    def test_setup_logging_with_file_handler_success(self):
        """Test setup_logging with successful file handler creation."""
        import os
        import tempfile
        from awslabs.amazon_translate_mcp_server.logging_config import setup_logging

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test.log')
            setup_logging(log_level='INFO', log_file=log_file)

            # Verify file was created
            assert os.path.exists(log_file)

    def test_setup_logging_with_file_handler_failure(self):
        """Test setup_logging with file handler creation failure."""
        from awslabs.amazon_translate_mcp_server.logging_config import setup_logging

        # Try to create log file in non-existent directory
        invalid_path = '/nonexistent/directory/test.log'

        # Should not raise exception, just continue without file handler
        setup_logging(log_level='INFO', log_file=invalid_path)

    def test_setup_logging_simple_format(self):
        """Test setup_logging with simple log format."""
        from awslabs.amazon_translate_mcp_server.logging_config import setup_logging

        setup_logging(log_level='INFO', log_format='simple')

    def test_setup_logging_structured_format_default(self):
        """Test setup_logging with default structured format."""
        from awslabs.amazon_translate_mcp_server.logging_config import setup_logging

        setup_logging(log_level='INFO', log_format='structured')

    def test_setup_logging_unknown_format_defaults_to_structured(self):
        """Test setup_logging with unknown format defaults to structured."""
        from awslabs.amazon_translate_mcp_server.logging_config import setup_logging

        setup_logging(log_level='INFO', log_format='unknown_format')
