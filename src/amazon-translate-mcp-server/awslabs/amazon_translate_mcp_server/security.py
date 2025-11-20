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

"""Security and compliance features for Amazon Translate MCP Server.

This module provides comprehensive security features including input validation,
PII detection and masking, content filtering, audit logging, and secure file handling.
"""

import hashlib
import logging
import mimetypes
import os
import re
import tempfile
import uuid
from .exceptions import SecurityError, ValidationError
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Security Configuration
@dataclass
class SecurityConfig:
    """Configuration for security features."""

    enable_pii_detection: bool = False
    enable_profanity_filter: bool = False
    enable_content_filtering: bool = False
    enable_audit_logging: bool = True
    max_text_length: int = 10000
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_extensions: Set[str] = field(default_factory=lambda: {'.csv', '.tmx', '.txt'})
    blocked_patterns: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate security configuration."""
        if self.max_text_length <= 0:
            raise ValueError('max_text_length must be positive')
        if self.max_file_size <= 0:
            raise ValueError('max_file_size must be positive')


# Input Validation
class InputValidator:
    """Comprehensive input validation for all tool parameters."""

    # Language code patterns
    LANGUAGE_CODE_PATTERN = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$')

    # S3 URI pattern
    S3_URI_PATTERN = re.compile(r'^s3://[a-z0-9][a-z0-9\-]*[a-z0-9](/.*)?$')

    # ARN pattern
    ARN_PATTERN = re.compile(r'^arn:aws:iam::\d{12}:role/.+$')

    # Job name pattern (alphanumeric, hyphens, underscores)
    JOB_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\-_]+$')

    # Terminology name pattern
    TERMINOLOGY_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\-_]+$')

    def __init__(self, config: SecurityConfig):
        """Initialize the input validator.

        Args:
            config: Security configuration settings

        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def validate_text_input(self, text: str, field_name: str = 'text') -> str:
        """Validate text input with length and content checks."""
        if not isinstance(text, str):
            raise ValidationError(f'{field_name} must be a string', field_name)

        if not text.strip():
            raise ValidationError(f'{field_name} cannot be empty', field_name)

        if len(text) > self.config.max_text_length:
            raise ValidationError(
                f'{field_name} exceeds maximum length of {self.config.max_text_length} characters',
                field_name,
            )

        # Check for blocked patterns
        for pattern in self.config.blocked_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise SecurityError('Text contains blocked content pattern')

        return text.strip()

    def validate_language_code(self, language_code: str, field_name: str = 'language_code') -> str:
        """Validate language code format."""
        if not isinstance(language_code, str):
            raise ValidationError(f'{field_name} must be a string', field_name)

        if not self.LANGUAGE_CODE_PATTERN.match(language_code):
            raise ValidationError(
                f"Invalid {field_name} format. Expected format: 'xx' or 'xx-XX'", field_name
            )

        return language_code

    def validate_language_codes(
        self, language_codes: List[str], field_name: str = 'language_codes'
    ) -> List[str]:
        """Validate a list of language codes."""
        if not isinstance(language_codes, list):
            raise ValidationError(f'{field_name} must be a list', field_name)

        if not language_codes:
            raise ValidationError(f'{field_name} cannot be empty', field_name)

        if len(language_codes) > 10:
            raise ValidationError(
                f'{field_name} cannot contain more than 10 languages', field_name
            )

        validated_codes = []
        for i, code in enumerate(language_codes):
            try:
                validated_codes.append(self.validate_language_code(code, f'{field_name}[{i}]'))
            except ValidationError as e:
                raise ValidationError(
                    f'Invalid language code at index {i}: {e.message}', field_name
                )

        return validated_codes

    def validate_s3_uri(self, s3_uri: str, field_name: str = 's3_uri') -> str:
        """Validate S3 URI format."""
        if not isinstance(s3_uri, str):
            raise ValidationError(f'{field_name} must be a string', field_name)

        if not self.S3_URI_PATTERN.match(s3_uri):
            raise ValidationError(
                f"Invalid {field_name} format. Expected format: 's3://bucket-name/path'",
                field_name,
            )

        return s3_uri

    def validate_arn(self, arn: str, field_name: str = 'arn') -> str:
        """Validate AWS ARN format."""
        if not isinstance(arn, str):
            raise ValidationError(f'{field_name} must be a string', field_name)

        if not self.ARN_PATTERN.match(arn):
            raise ValidationError(
                f'Invalid {field_name} format. Expected IAM role ARN', field_name
            )

        return arn

    def validate_job_name(self, job_name: str, field_name: str = 'job_name') -> str:
        """Validate job name format."""
        if not isinstance(job_name, str):
            raise ValidationError(f'{field_name} must be a string', field_name)

        if not job_name.strip():
            raise ValidationError(f'{field_name} cannot be empty', field_name)

        if len(job_name) > 256:
            raise ValidationError(f'{field_name} cannot exceed 256 characters', field_name)

        if not self.JOB_NAME_PATTERN.match(job_name):
            raise ValidationError(
                f'Invalid {field_name} format. Only alphanumeric characters, hyphens, and underscores allowed',
                field_name,
            )

        return job_name

    def validate_terminology_name(
        self, terminology_name: str, field_name: str = 'terminology_name'
    ) -> str:
        """Validate terminology name format."""
        if not isinstance(terminology_name, str):
            raise ValidationError(f'{field_name} must be a string', field_name)

        if not terminology_name.strip():
            raise ValidationError(f'{field_name} cannot be empty', field_name)

        if len(terminology_name) > 256:
            raise ValidationError(f'{field_name} cannot exceed 256 characters', field_name)

        if not self.TERMINOLOGY_NAME_PATTERN.match(terminology_name):
            raise ValidationError(
                f'Invalid {field_name} format. Only alphanumeric characters, hyphens, and underscores allowed',
                field_name,
            )

        return terminology_name

    def validate_terminology_names(
        self, terminology_names: List[str], field_name: str = 'terminology_names'
    ) -> List[str]:
        """Validate a list of terminology names."""
        if not isinstance(terminology_names, list):
            raise ValidationError(f'{field_name} must be a list', field_name)

        validated_names = []
        for i, name in enumerate(terminology_names):
            try:
                validated_names.append(self.validate_terminology_name(name, f'{field_name}[{i}]'))
            except ValidationError as e:
                raise ValidationError(
                    f'Invalid terminology name at index {i}: {e.message}', field_name
                )

        return validated_names

    def validate_confidence_score(
        self, score: Optional[float], field_name: str = 'confidence_score'
    ) -> Optional[float]:
        """Validate confidence score range."""
        if score is None:
            return None

        if not isinstance(score, (int, float)):
            raise ValidationError(f'{field_name} must be a number', field_name)

        if not (0.0 <= score <= 1.0):
            raise ValidationError(f'{field_name} must be between 0.0 and 1.0', field_name)

        return float(score)

    def validate_file_path(self, file_path: str, field_name: str = 'file_path') -> str:
        """Validate file path for security."""
        if not isinstance(file_path, str):
            raise ValidationError(f'{field_name} must be a string', field_name)

        if not file_path.strip():
            raise ValidationError(f'{field_name} cannot be empty', field_name)

        # Check for path traversal attempts
        if '..' in file_path or file_path.startswith('/'):
            raise SecurityError('Invalid file path: path traversal detected')

        # Validate file extension
        path = Path(file_path)
        if path.suffix.lower() not in self.config.allowed_file_extensions:
            raise ValidationError(
                f"File extension '{path.suffix}' not allowed. Allowed extensions: {', '.join(self.config.allowed_file_extensions)}",
                field_name,
            )

        return file_path


# PII Detection and Masking
class PIIDetector:
    """Detect and mask personally identifiable information."""

    # PII patterns
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')

    def __init__(self, enabled: bool = False):
        """Initialize the PII detector.

        Args:
            enabled: Whether PII detection is enabled

        """
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)

    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """Detect PII in text and return findings."""
        if not self.enabled:
            return []

        findings = []

        # Email detection
        for match in self.EMAIL_PATTERN.finditer(text):
            findings.append(
                {
                    'type': 'EMAIL',
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.9,
                }
            )

        # Phone number detection
        for match in self.PHONE_PATTERN.finditer(text):
            findings.append(
                {
                    'type': 'PHONE',
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.8,
                }
            )

        # SSN detection
        for match in self.SSN_PATTERN.finditer(text):
            findings.append(
                {
                    'type': 'SSN',
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.95,
                }
            )

        # Credit card detection
        for match in self.CREDIT_CARD_PATTERN.finditer(text):
            findings.append(
                {
                    'type': 'CREDIT_CARD',
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.85,
                }
            )

        return findings

    def mask_pii(self, text: str, mask_char: str = '*') -> Tuple[str, List[Dict[str, Any]]]:
        """Mask PII in text and return masked text with findings."""
        if not self.enabled:
            return text, []

        findings = self.detect_pii(text)
        masked_text = text

        # Sort findings by position (reverse order to maintain positions)
        findings.sort(key=lambda x: x['start'], reverse=True)

        for finding in findings:
            start, end = finding['start'], finding['end']
            original_text = finding['text']

            # Create mask based on PII type
            if finding['type'] == 'EMAIL':
                # Mask everything except domain
                parts = original_text.split('@')
                if len(parts) == 2:
                    masked = mask_char * len(parts[0]) + '@' + parts[1]
                else:
                    masked = mask_char * len(original_text)
            elif finding['type'] == 'PHONE':
                # Mask middle digits
                masked = re.sub(r'\d', mask_char, original_text)
            elif finding['type'] == 'SSN':
                # Mask first 5 digits
                masked = mask_char * 7 + original_text[-4:]
            elif finding['type'] == 'CREDIT_CARD':
                # Mask all but last 4 digits
                digits_only = re.sub(r'[^\d]', '', original_text)
                if len(digits_only) >= 4:
                    masked_digits = mask_char * (len(digits_only) - 4) + digits_only[-4:]
                    # Preserve original formatting
                    masked = original_text
                    digit_pos = 0
                    for i, char in enumerate(original_text):
                        if char.isdigit():
                            masked = masked[:i] + masked_digits[digit_pos] + masked[i + 1 :]
                            digit_pos += 1
                else:
                    masked = mask_char * len(original_text)
            else:
                masked = mask_char * len(original_text)

            masked_text = masked_text[:start] + masked + masked_text[end:]
            finding['masked_text'] = masked

        return masked_text, findings


# Content Filtering
class ContentFilter:
    """Filter inappropriate content and profanity."""

    # Basic profanity list (expandable)
    PROFANITY_WORDS = {'damn', 'hell', 'crap', 'shit', 'fuck', 'bitch', 'ass', 'bastard'}

    def __init__(self, enabled: bool = False):
        """Initialize the content filter.

        Args:
            enabled: Whether content filtering is enabled

        """
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)

    def contains_profanity(self, text: str) -> bool:
        """Check if text contains profanity."""
        if not self.enabled:
            return False

        words = re.findall(r'\b\w+\b', text.lower())
        return any(word in self.PROFANITY_WORDS for word in words)

    def filter_profanity(self, text: str, replacement: str = '***') -> str:
        """Filter profanity from text."""
        if not self.enabled:
            return text

        filtered_text = text
        for word in self.PROFANITY_WORDS:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            filtered_text = pattern.sub(replacement, filtered_text)

        return filtered_text


# Audit Logging
@dataclass
class AuditLogEntry:
    """Audit log entry for translation operations."""

    timestamp: datetime
    operation: str
    user_id: Optional[str]
    session_id: str
    source_language: Optional[str]
    target_language: Optional[str]
    text_length: Optional[int]
    terminology_used: List[str]
    success: bool
    error_code: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'operation': self.operation,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'source_language': self.source_language,
            'target_language': self.target_language,
            'text_length': self.text_length,
            'terminology_used': self.terminology_used,
            'success': self.success,
            'error_code': self.error_code,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_id': self.request_id,
        }


class AuditLogger:
    """Audit logger for translation operations."""

    def __init__(self, enabled: bool = True):
        """Initialize the audit logger.

        Args:
            enabled: Whether audit logging is enabled

        """
        self.enabled = enabled
        self.logger = logging.getLogger('audit')

        # Configure audit logger
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - AUDIT - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_translation(
        self,
        operation: str,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        text_length: Optional[int] = None,
        terminology_used: Optional[List[str]] = None,
        success: bool = True,
        error_code: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log a translation operation."""
        if not self.enabled:
            return

        entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            operation=operation,
            user_id=user_id,
            session_id=str(uuid.uuid4()),
            source_language=source_language,
            target_language=target_language,
            text_length=text_length,
            terminology_used=terminology_used or [],
            success=success,
            error_code=error_code,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=str(uuid.uuid4()),
        )

        self.logger.info(f'AUDIT: {entry.to_dict()}')


# Secure File Handling
class SecureFileHandler:
    """Secure file handling for terminology imports."""

    def __init__(self, config: SecurityConfig):
        """Initialize the secure file handler.

        Args:
            config: Security configuration settings

        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """Validate file for security and format."""
        if not os.path.exists(file_path):
            raise ValidationError(f'File does not exist: {file_path}')

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.config.max_file_size:
            raise ValidationError(
                f'File size ({file_size} bytes) exceeds maximum allowed size ({self.config.max_file_size} bytes)'
            )

        # Check file extension
        path = Path(file_path)
        if path.suffix.lower() not in self.config.allowed_file_extensions:
            raise ValidationError(f"File extension '{path.suffix}' not allowed")

        # Check MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        allowed_mime_types = {'text/csv', 'text/plain', 'application/xml', 'text/xml'}

        if mime_type and mime_type not in allowed_mime_types:
            raise ValidationError(f"MIME type '{mime_type}' not allowed")

        # Calculate file hash for integrity
        file_hash = self._calculate_file_hash(file_path)

        return {
            'file_path': file_path,
            'file_size': file_size,
            'mime_type': mime_type,
            'file_hash': file_hash,
            'extension': path.suffix.lower(),
        }

    def create_secure_temp_file(self, content: bytes, extension: str = '.tmp') -> str:
        """Create a secure temporary file."""
        if extension not in self.config.allowed_file_extensions:
            raise ValidationError(f"Extension '{extension}' not allowed")

        # Create temporary file with secure permissions
        fd, temp_path = tempfile.mkstemp(suffix=extension, prefix='translate_')

        try:
            with os.fdopen(fd, 'wb') as temp_file:
                temp_file.write(content)

            # Set secure permissions (owner read/write only)
            os.chmod(temp_path, 0o600)

            return temp_path
        except Exception:
            # Clean up on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def cleanup_temp_file(self, file_path: str):
        """Securely delete temporary file."""
        try:
            if os.path.exists(file_path):
                # Overwrite file content before deletion (basic secure delete)
                file_size = os.path.getsize(file_path)
                with open(file_path, 'wb') as f:
                    f.write(b'\x00' * file_size)

                os.unlink(file_path)
        except OSError as e:
            self.logger.warning(f'Failed to cleanup temp file {file_path}: {e}')

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


# Security Manager
class SecurityManager:
    """Main security manager that coordinates all security features."""

    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize the security manager.

        Args:
            config: Security configuration settings

        """
        self.config = config or SecurityConfig()
        self.validator = InputValidator(self.config)
        self.pii_detector = PIIDetector(self.config.enable_pii_detection)
        self.content_filter = ContentFilter(self.config.enable_profanity_filter)
        self.audit_logger = AuditLogger(self.config.enable_audit_logging)
        self.file_handler = SecureFileHandler(self.config)
        self.logger = logging.getLogger(__name__)

    def validate_and_sanitize_text(
        self, text: str, field_name: str = 'text'
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Validate and sanitize text input."""
        # Basic validation
        validated_text = self.validator.validate_text_input(text, field_name)

        # PII detection and masking
        if self.config.enable_pii_detection:
            validated_text, pii_findings = self.pii_detector.mask_pii(validated_text)
        else:
            pii_findings = []

        # Content filtering
        if self.config.enable_profanity_filter:
            if self.content_filter.contains_profanity(validated_text):
                validated_text = self.content_filter.filter_profanity(validated_text)

        return validated_text, pii_findings

    def log_operation(self, operation: str, success: bool = True, **kwargs):
        """Log an operation for audit purposes."""
        self.audit_logger.log_translation(operation=operation, success=success, **kwargs)

    def handle_file_upload(self, file_content: bytes, filename: str) -> str:
        """Handle secure file upload for terminology."""
        # Validate filename
        self.validator.validate_file_path(filename)

        # Get file extension
        extension = Path(filename).suffix.lower()

        # Create secure temporary file
        temp_path = self.file_handler.create_secure_temp_file(file_content, extension)

        # Validate the created file
        file_info = self.file_handler.validate_file(temp_path)

        self.logger.info(f'Secure file created: {file_info}')

        return temp_path

    def cleanup_file(self, file_path: str):
        """Clean up temporary file."""
        self.file_handler.cleanup_temp_file(file_path)
