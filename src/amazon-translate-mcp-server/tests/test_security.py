"""Unit tests for security and compliance features.

This module tests all security features including input validation,
PII detection and masking, content filtering, audit logging, and
secure file handling.
"""

import os
import pytest
import tempfile
from awslabs.amazon_translate_mcp_server.exceptions import SecurityError, ValidationError
from awslabs.amazon_translate_mcp_server.security import (
    AuditLogEntry,
    AuditLogger,
    ContentFilter,
    InputValidator,
    PIIDetector,
    SecureFileHandler,
    SecurityConfig,
    SecurityManager,
)
from datetime import datetime
from unittest.mock import Mock, patch


class TestSecurityConfig:
    """Test security configuration."""

    def test_default_config(self):
        """Test default security configuration."""
        config = SecurityConfig()

        assert config.enable_pii_detection is False
        assert config.enable_profanity_filter is False
        assert config.enable_content_filtering is False
        assert config.enable_audit_logging is True
        assert config.max_text_length == 10000
        assert config.max_file_size == 10 * 1024 * 1024
        assert '.csv' in config.allowed_file_extensions
        assert '.tmx' in config.allowed_file_extensions
        assert '.txt' in config.allowed_file_extensions

    def test_custom_config(self):
        """Test custom security configuration."""
        config = SecurityConfig(
            enable_pii_detection=True,
            enable_profanity_filter=True,
            max_text_length=5000,
            max_file_size=1024,
            allowed_file_extensions={'.csv'},
            blocked_patterns=['test_pattern'],
        )

        assert config.enable_pii_detection is True
        assert config.enable_profanity_filter is True
        assert config.max_text_length == 5000
        assert config.max_file_size == 1024
        assert config.allowed_file_extensions == {'.csv'}
        assert 'test_pattern' in config.blocked_patterns

    def test_invalid_config(self):
        """Test invalid security configuration."""
        with pytest.raises(ValueError, match='max_text_length must be positive'):
            SecurityConfig(max_text_length=0)

        with pytest.raises(ValueError, match='max_file_size must be positive'):
            SecurityConfig(max_file_size=-1)


class TestInputValidator:
    """Test input validation functionality."""

    @pytest.fixture
    def validator(self):
        """Create input validator with default config."""
        config = SecurityConfig()
        return InputValidator(config)

    @pytest.fixture
    def strict_validator(self):
        """Create input validator with strict config."""
        config = SecurityConfig(max_text_length=100, blocked_patterns=[r'blocked_word'])
        return InputValidator(config)

    def test_validate_text_input_valid(self, validator):
        """Test valid text input validation."""
        text = 'Hello, world!'
        result = validator.validate_text_input(text)
        assert result == 'Hello, world!'

    def test_validate_text_input_empty(self, validator):
        """Test empty text input validation."""
        with pytest.raises(ValidationError, match='text cannot be empty'):
            validator.validate_text_input('')

        with pytest.raises(ValidationError, match='text cannot be empty'):
            validator.validate_text_input('   ')

    def test_validate_text_input_non_string(self, validator):
        """Test non-string text input validation."""
        with pytest.raises(ValidationError, match='text must be a string'):
            validator.validate_text_input(123)

    def test_validate_text_input_too_long(self, strict_validator):
        """Test text input that exceeds maximum length."""
        long_text = 'a' * 101
        with pytest.raises(ValidationError, match='exceeds maximum length'):
            strict_validator.validate_text_input(long_text)

    def test_validate_text_input_blocked_pattern(self, strict_validator):
        """Test text input with blocked patterns."""
        with pytest.raises(SecurityError, match='blocked content pattern'):
            strict_validator.validate_text_input('This contains blocked_word')

    def test_validate_language_code_valid(self, validator):
        """Test valid language code validation."""
        assert validator.validate_language_code('en') == 'en'
        assert validator.validate_language_code('en-US') == 'en-US'
        assert validator.validate_language_code('zh-CN') == 'zh-CN'

    def test_validate_language_code_invalid(self, validator):
        """Test invalid language code validation."""
        invalid_codes = ['', 'e', 'eng', 'en-us', 'EN', '123', 'en-USA']

        for code in invalid_codes:
            with pytest.raises(ValidationError, match='Invalid.*format'):
                validator.validate_language_code(code)

    def test_validate_language_codes_valid(self, validator):
        """Test valid language codes list validation."""
        codes = ['en', 'es', 'fr-FR']
        result = validator.validate_language_codes(codes)
        assert result == codes

    def test_validate_language_codes_empty(self, validator):
        """Test empty language codes list validation."""
        with pytest.raises(ValidationError, match='cannot be empty'):
            validator.validate_language_codes([])

    def test_validate_language_codes_too_many(self, validator):
        """Test too many language codes validation."""
        codes = [f'l{i}' for i in range(11)]  # 11 codes
        with pytest.raises(ValidationError, match='cannot contain more than 10'):
            validator.validate_language_codes(codes)

    def test_validate_s3_uri_valid(self, validator):
        """Test valid S3 URI validation."""
        valid_uris = [
            's3://bucket-name',
            's3://bucket-name/path',
            's3://bucket-name/path/to/file.txt',
            's3://my-bucket-123/folder/subfolder/',
        ]

        for uri in valid_uris:
            result = validator.validate_s3_uri(uri)
            assert result == uri

    def test_validate_s3_uri_invalid(self, validator):
        """Test invalid S3 URI validation."""
        invalid_uris = [
            '',
            'http://bucket/path',
            's3://',
            's3://Bucket-Name',  # uppercase
            's3://bucket_name',  # underscore
            'bucket/path',
        ]

        for uri in invalid_uris:
            with pytest.raises(ValidationError, match='Invalid.*format'):
                validator.validate_s3_uri(uri)

    def test_validate_arn_valid(self, validator):
        """Test valid ARN validation."""
        valid_arns = [
            'arn:aws:iam::123456789012:role/MyRole',
            'arn:aws:iam::123456789012:role/service-role/MyRole',
            'arn:aws:iam::123456789012:role/path/to/MyRole',
        ]

        for arn in valid_arns:
            result = validator.validate_arn(arn)
            assert result == arn

    def test_validate_arn_invalid(self, validator):
        """Test invalid ARN validation."""
        invalid_arns = [
            '',
            'arn:aws:iam::123456789012:user/MyUser',
            'arn:aws:iam::invalid:role/MyRole',
            'not-an-arn',
        ]

        for arn in invalid_arns:
            with pytest.raises(ValidationError, match='Invalid.*format'):
                validator.validate_arn(arn)

    def test_validate_job_name_valid(self, validator):
        """Test valid job name validation."""
        valid_names = ['MyJob', 'my-job', 'my_job', 'job123', 'Job-Name_123']

        for name in valid_names:
            result = validator.validate_job_name(name)
            assert result == name

    def test_validate_job_name_invalid(self, validator):
        """Test invalid job name validation."""
        with pytest.raises(ValidationError, match='cannot be empty'):
            validator.validate_job_name('')

        with pytest.raises(ValidationError, match='Invalid.*format'):
            validator.validate_job_name('job with spaces')

        with pytest.raises(ValidationError, match='Invalid.*format'):
            validator.validate_job_name('job@special')

        # Test too long name
        long_name = 'a' * 257
        with pytest.raises(ValidationError, match='cannot exceed 256 characters'):
            validator.validate_job_name(long_name)

    def test_validate_confidence_score_valid(self, validator):
        """Test valid confidence score validation."""
        assert validator.validate_confidence_score(0.0) == 0.0
        assert validator.validate_confidence_score(0.5) == 0.5
        assert validator.validate_confidence_score(1.0) == 1.0
        assert validator.validate_confidence_score(None) is None

    def test_validate_confidence_score_invalid(self, validator):
        """Test invalid confidence score validation."""
        with pytest.raises(ValidationError, match='must be a number'):
            validator.validate_confidence_score('0.5')

        with pytest.raises(ValidationError, match='must be between 0.0 and 1.0'):
            validator.validate_confidence_score(-0.1)

        with pytest.raises(ValidationError, match='must be between 0.0 and 1.0'):
            validator.validate_confidence_score(1.1)

    def test_validate_file_path_valid(self, validator):
        """Test valid file path validation."""
        valid_paths = ['file.csv', 'data/file.tmx', 'folder/subfolder/file.txt']

        for path in valid_paths:
            result = validator.validate_file_path(path)
            assert result == path

    def test_validate_file_path_invalid(self, validator):
        """Test invalid file path validation."""
        with pytest.raises(ValidationError, match='cannot be empty'):
            validator.validate_file_path('')

        with pytest.raises(SecurityError, match='path traversal detected'):
            validator.validate_file_path('../file.csv')

        with pytest.raises(SecurityError, match='path traversal detected'):
            validator.validate_file_path('/absolute/path.csv')

        with pytest.raises(ValidationError, match='not allowed'):
            validator.validate_file_path('file.exe')


class TestPIIDetector:
    """Test PII detection and masking functionality."""

    @pytest.fixture
    def detector(self):
        """Create PII detector with detection enabled."""
        return PIIDetector(enabled=True)

    @pytest.fixture
    def disabled_detector(self):
        """Create PII detector with detection disabled."""
        return PIIDetector(enabled=False)

    def test_detect_email(self, detector):
        """Test email detection."""
        text = 'Contact me at john.doe@example.com for more info.'
        findings = detector.detect_pii(text)

        assert len(findings) == 1
        assert findings[0]['type'] == 'EMAIL'
        assert findings[0]['text'] == 'john.doe@example.com'
        assert findings[0]['confidence'] == 0.9

    def test_detect_phone(self, detector):
        """Test phone number detection."""
        text = 'Call me at (555) 123-4567 or 555.123.4567'
        findings = detector.detect_pii(text)

        assert len(findings) == 2
        assert all(f['type'] == 'PHONE' for f in findings)
        assert findings[0]['confidence'] == 0.8

    def test_detect_ssn(self, detector):
        """Test SSN detection."""
        text = 'My SSN is 123-45-6789'
        findings = detector.detect_pii(text)

        assert len(findings) == 1
        assert findings[0]['type'] == 'SSN'
        assert findings[0]['text'] == '123-45-6789'
        assert findings[0]['confidence'] == 0.95

    def test_detect_credit_card(self, detector):
        """Test credit card detection."""
        text = 'Card number: 1234 5678 9012 3456'
        findings = detector.detect_pii(text)

        assert len(findings) == 1
        assert findings[0]['type'] == 'CREDIT_CARD'
        assert findings[0]['confidence'] == 0.85

    def test_mask_email(self, detector):
        """Test email masking."""
        text = 'Contact john.doe@example.com'
        masked_text, findings = detector.mask_pii(text)

        assert '********@example.com' in masked_text
        assert len(findings) == 1
        assert findings[0]['masked_text'] == '********@example.com'

    def test_mask_ssn(self, detector):
        """Test SSN masking."""
        text = 'SSN: 123-45-6789'
        masked_text, findings = detector.mask_pii(text)

        assert '*******6789' in masked_text
        assert len(findings) == 1

    def test_mask_credit_card(self, detector):
        """Test credit card masking."""
        text = 'Card: 1234-5678-9012-3456'
        masked_text, findings = detector.mask_pii(text)

        assert '****-****-****-3456' in masked_text
        assert len(findings) == 1

    def test_disabled_detector(self, disabled_detector):
        """Test disabled PII detector."""
        text = 'Email: john@example.com, Phone: 555-1234'

        findings = disabled_detector.detect_pii(text)
        assert len(findings) == 0

        masked_text, findings = disabled_detector.mask_pii(text)
        assert masked_text == text
        assert len(findings) == 0


class TestContentFilter:
    """Test content filtering functionality."""

    @pytest.fixture
    def filter(self):
        """Create content filter with filtering enabled."""
        return ContentFilter(enabled=True)

    @pytest.fixture
    def disabled_filter(self):
        """Create content filter with filtering disabled."""
        return ContentFilter(enabled=False)

    def test_contains_profanity(self, filter):
        """Test profanity detection."""
        assert filter.contains_profanity('This is damn good!')
        assert filter.contains_profanity('What the hell?')
        assert not filter.contains_profanity('This is a clean sentence.')

    def test_filter_profanity(self, filter):
        """Test profanity filtering."""
        text = 'This is damn good, but hell no!'
        filtered = filter.filter_profanity(text)

        assert 'damn' not in filtered
        assert 'hell' not in filtered
        assert '***' in filtered

    def test_disabled_filter(self, disabled_filter):
        """Test disabled content filter."""
        text = 'This is damn good!'

        assert not disabled_filter.contains_profanity(text)
        assert disabled_filter.filter_profanity(text) == text


class TestAuditLogger:
    """Test audit logging functionality."""

    @pytest.fixture
    def audit_logger(self):
        """Create audit logger with logging enabled."""
        return AuditLogger(enabled=True)

    @pytest.fixture
    def disabled_audit_logger(self):
        """Create audit logger with logging disabled."""
        return AuditLogger(enabled=False)

    def test_audit_log_entry(self):
        """Test audit log entry creation."""
        entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            operation='translate_text',
            user_id='user123',
            session_id='session456',
            source_language='en',
            target_language='es',
            text_length=100,
            terminology_used=['medical'],
            success=True,
            error_code=None,
            ip_address='192.168.1.1',
            user_agent='TestAgent',
            request_id='req123',
        )

        entry_dict = entry.to_dict()
        assert entry_dict['operation'] == 'translate_text'
        assert entry_dict['user_id'] == 'user123'
        assert entry_dict['success'] is True
        assert entry_dict['terminology_used'] == ['medical']

    @patch('awslabs.amazon_translate_mcp_server.security.logging.getLogger')
    def test_log_translation(self, mock_get_logger, audit_logger):
        """Test translation operation logging."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        audit_logger.logger = mock_logger

        audit_logger.log_translation(
            operation='translate_text',
            source_language='en',
            target_language='es',
            text_length=50,
            success=True,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert 'AUDIT:' in call_args
        assert 'translate_text' in call_args

    def test_disabled_audit_logger(self, disabled_audit_logger):
        """Test disabled audit logger."""
        # Should not raise any exceptions
        disabled_audit_logger.log_translation('test_operation')


class TestSecureFileHandler:
    """Test secure file handling functionality."""

    @pytest.fixture
    def file_handler(self):
        """Create secure file handler with default config."""
        config = SecurityConfig()
        return SecureFileHandler(config)

    @pytest.fixture
    def temp_file(self):
        """Create temporary test file."""
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'w') as f:
            f.write('source,target\nhello,hola\n')
        yield path
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_validate_file_valid(self, file_handler, temp_file):
        """Test valid file validation."""
        file_info = file_handler.validate_file(temp_file)

        assert file_info['file_path'] == temp_file
        assert file_info['file_size'] > 0
        assert file_info['extension'] == '.csv'
        assert 'file_hash' in file_info

    def test_validate_file_not_exists(self, file_handler):
        """Test validation of non-existent file."""
        with pytest.raises(ValidationError, match='File does not exist'):
            file_handler.validate_file('nonexistent.csv')

    def test_validate_file_too_large(self, file_handler):
        """Test validation of oversized file."""
        # Create handler with very small max size
        config = SecurityConfig(max_file_size=1)
        handler = SecureFileHandler(config)

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            f.write(b'a' * 10)  # 10 bytes
            temp_path = f.name

        try:
            with pytest.raises(ValidationError, match='exceeds maximum allowed size'):
                handler.validate_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validate_file_invalid_extension(self, file_handler):
        """Test validation of file with invalid extension."""
        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValidationError, match='not allowed'):
                file_handler.validate_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_create_secure_temp_file(self, file_handler):
        """Test secure temporary file creation."""
        content = b'test,content\nhello,world\n'
        temp_path = file_handler.create_secure_temp_file(content, '.csv')

        try:
            assert os.path.exists(temp_path)
            assert temp_path.endswith('.csv')

            # Check file permissions (owner read/write only)
            stat_info = os.stat(temp_path)
            assert stat_info.st_mode & 0o777 == 0o600

            # Check content
            with open(temp_path, 'rb') as f:
                assert f.read() == content
        finally:
            file_handler.cleanup_temp_file(temp_path)

    def test_create_secure_temp_file_invalid_extension(self, file_handler):
        """Test secure temp file creation with invalid extension."""
        with pytest.raises(ValidationError, match='not allowed'):
            file_handler.create_secure_temp_file(b'content', '.exe')

    def test_cleanup_temp_file(self, file_handler):
        """Test secure file cleanup."""
        content = b'sensitive data'
        temp_path = file_handler.create_secure_temp_file(content, '.txt')

        assert os.path.exists(temp_path)
        file_handler.cleanup_temp_file(temp_path)
        assert not os.path.exists(temp_path)

    def test_cleanup_nonexistent_file(self, file_handler):
        """Test cleanup of non-existent file."""
        # Should not raise exception
        file_handler.cleanup_temp_file('nonexistent.txt')


class TestSecurityManager:
    """Test security manager integration."""

    @pytest.fixture
    def security_manager(self):
        """Create security manager with default config."""
        return SecurityManager()

    @pytest.fixture
    def strict_security_manager(self):
        """Create security manager with strict config."""
        config = SecurityConfig(
            enable_pii_detection=True, enable_profanity_filter=True, enable_audit_logging=True
        )
        return SecurityManager(config)

    def test_validate_and_sanitize_text_clean(self, security_manager):
        """Test validation and sanitization of clean text."""
        text = 'Hello, world!'
        sanitized, findings = security_manager.validate_and_sanitize_text(text)

        assert sanitized == 'Hello, world!'
        assert len(findings) == 0

    def test_validate_and_sanitize_text_with_pii(self, strict_security_manager):
        """Test validation and sanitization with PII."""
        text = 'Contact me at john@example.com'
        sanitized, findings = strict_security_manager.validate_and_sanitize_text(text)

        assert 'john@example.com' not in sanitized
        assert '****@example.com' in sanitized
        assert len(findings) == 1
        assert findings[0]['type'] == 'EMAIL'

    def test_validate_and_sanitize_text_with_profanity(self, strict_security_manager):
        """Test validation and sanitization with profanity."""
        text = 'This is damn good!'
        sanitized, findings = strict_security_manager.validate_and_sanitize_text(text)

        assert 'damn' not in sanitized
        assert '***' in sanitized

    @patch('awslabs.amazon_translate_mcp_server.security.AuditLogger.log_translation')
    def test_log_operation(self, mock_log, security_manager):
        """Test operation logging."""
        security_manager.log_operation(
            operation='translate_text', source_language='en', target_language='es', success=True
        )

        mock_log.assert_called_once_with(
            operation='translate_text', success=True, source_language='en', target_language='es'
        )

    def test_handle_file_upload(self, security_manager):
        """Test secure file upload handling."""
        content = b'source,target\nhello,hola\n'
        filename = 'terminology.csv'

        temp_path = security_manager.handle_file_upload(content, filename)

        try:
            assert os.path.exists(temp_path)
            assert temp_path.endswith('.csv')

            with open(temp_path, 'rb') as f:
                assert f.read() == content
        finally:
            security_manager.cleanup_file(temp_path)

    def test_handle_file_upload_invalid_filename(self, security_manager):
        """Test file upload with invalid filename."""
        content = b'content'

        with pytest.raises(ValidationError):
            security_manager.handle_file_upload(content, 'file.exe')

        with pytest.raises(SecurityError):
            security_manager.handle_file_upload(content, '../file.csv')


class TestSecurityIntegration:
    """Test security feature integration scenarios."""

    @pytest.fixture
    def full_security_manager(self):
        """Create security manager with all features enabled."""
        config = SecurityConfig(
            enable_pii_detection=True,
            enable_profanity_filter=True,
            enable_content_filtering=True,
            enable_audit_logging=True,
            max_text_length=1000,
            blocked_patterns=[r'confidential', r'secret'],
        )
        return SecurityManager(config)

    def test_comprehensive_text_processing(self, full_security_manager):
        """Test comprehensive text processing with all security features."""
        text = 'This damn message contains john@example.com and is confidential'

        with pytest.raises(SecurityError, match='blocked content pattern'):
            full_security_manager.validate_and_sanitize_text(text)

    def test_secure_translation_workflow(self, full_security_manager):
        """Test secure translation workflow simulation."""
        # Step 1: Validate input text
        text = 'Please contact me at john.doe@example.com for more information'
        sanitized_text, pii_findings = full_security_manager.validate_and_sanitize_text(text)

        # Verify PII was masked
        assert 'john.doe@example.com' not in sanitized_text
        assert len(pii_findings) == 1

        # Step 2: Log the operation
        full_security_manager.log_operation(
            operation='translate_text',
            source_language='en',
            target_language='es',
            text_length=len(text),
            success=True,
        )

        # Step 3: Handle terminology file
        terminology_content = b'source,target\nemail,correo\ncontact,contacto\n'
        temp_file = full_security_manager.handle_file_upload(
            terminology_content, 'terminology.csv'
        )

        try:
            assert os.path.exists(temp_file)
        finally:
            full_security_manager.cleanup_file(temp_file)

    def test_error_handling_with_security(self, full_security_manager):
        """Test error handling in security context."""
        # Test various validation errors
        test_cases = [
            ('', 'cannot be empty'),
            ('a' * 1001, 'exceeds maximum length'),
            (123, 'must be a string'),
        ]

        for invalid_input, expected_error in test_cases:
            with pytest.raises(ValidationError, match=expected_error):
                full_security_manager.validate_and_sanitize_text(invalid_input)

    def test_security_logging(self, full_security_manager):
        """Test security-related logging."""
        with patch.object(full_security_manager.audit_logger, 'log_translation') as mock_log:
            # Test successful operation logging
            full_security_manager.log_operation(
                operation='translate_text',
                source_language='en',
                target_language='es',
                success=True,
            )

            # Test error operation logging
            full_security_manager.log_operation(
                operation='translate_text', success=False, error_code='VALIDATION_ERROR'
            )

            # Verify logging calls were made
            assert mock_log.call_count == 2
