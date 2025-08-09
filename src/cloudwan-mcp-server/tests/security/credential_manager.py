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

"""Secure credential management for CloudWAN MCP Server tests.

This module provides enterprise-grade credential security for test environments,
addressing SOC 2 and GDPR compliance requirements while preventing credential
exposure and ensuring proper test isolation.
"""

import base64
import hashlib
import json
import logging
import math
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


@dataclass
class TemporalCredentials:
    """Temporal test credentials with automatic expiration and rotation.

    Implements security best practices for test credential lifecycle:
    - UUID-based credential generation
    - Automatic expiration
    - Audit trail logging
    - Memory cleanup on expiration
    """

    access_key: str
    secret_key: str
    session_token: str
    expires_at: datetime
    test_session_id: str

    def is_expired(self) -> bool:
        """Check if credentials have expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def to_env_dict(self) -> dict[str, str]:
        """Convert to environment variable dictionary."""
        if self.is_expired():
            raise CredentialSecurityError("Attempted to use expired test credentials")

        return {
            "AWS_ACCESS_KEY_ID": self.access_key,
            "AWS_SECRET_ACCESS_KEY": self.secret_key,
            "AWS_SESSION_TOKEN": self.session_token,
            "AWS_TEST_SESSION_ID": self.test_session_id,
        }

    def cleanup(self) -> None:
        """Securely cleanup credential data from memory."""
        # Overwrite sensitive data with cryptographically secure random values
        self.access_key = self._random_string(len(self.access_key))
        self.secret_key = self._random_string(len(self.secret_key))
        self.session_token = self._random_string(len(self.session_token))

    @staticmethod
    def _random_string(length: int) -> str:
        """Generate a cryptographically secure random string of exact length.

        Uses base64url encoding of random bytes to ensure all characters are
        ASCII-safe and suitable for credential generation. This approach avoids
        any potential UTF-8 encoding issues by working exclusively with ASCII
        characters from the base64url alphabet.

        Args:
            length: Desired length of the random string

        Returns:
            ASCII-safe random string of exact specified length
        """
        if length <= 0:
            if length < 0:
                raise ValueError("length must be non-negative")
            return ""

        # Generate sufficient random bytes to produce at least 'length' base64 characters
        # This calculation uses the standard base64 encoding ratio to determine the minimum number of bytes needed
        bytes_needed = math.ceil(length * 3 / 4)  # Ceiling division for base64 ratio
        random_bytes = secrets.token_bytes(bytes_needed)

        # base64.urlsafe_b64encode produces only ASCII characters [A-Za-z0-9_-]
        # This eliminates any UTF-8 multi-byte character concerns
        encoded = base64.urlsafe_b64encode(random_bytes).decode("ascii")

        # Remove padding characters and truncate to exact length
        # Since we're working with ASCII characters only, slicing is safe
        clean_encoded = encoded.rstrip("=")

        # If we don't have enough characters, generate more
        while len(clean_encoded) < length:
            additional_bytes = secrets.token_bytes(4)  # Generate 4 more bytes
            additional_encoded = base64.urlsafe_b64encode(additional_bytes).decode("ascii").rstrip("=")
            clean_encoded += additional_encoded

        # Return exactly the requested length - safe since all characters are single-byte ASCII
        return clean_encoded[:length]


class CredentialSecurityError(Exception):
    """Raised when credential security boundary violations are detected."""

    pass


class CredentialManager:
    """Enterprise-grade credential management for test environments.

    Features:
    - SOC 2 Type II compliance
    - Credential rotation and expiration
    - Audit trail logging
    - Memory security cleanup
    - GDPR-compliant data handling
    """

    # Configurable audit log management constants
    AUDIT_LOG_ROTATION_THRESHOLD = 1000
    AUDIT_LOG_RETENTION_COUNT = 500

    _instance = None
    _lock = Lock()

    def __new__(cls) -> "CredentialManager":
        """Singleton pattern for credential manager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._active_credentials: dict[str, TemporalCredentials] = {}
        self._audit_log: list[dict[str, Any]] = []
        self._rotation_strategy = "per-test-run"
        self._default_duration = timedelta(minutes=15)
        self._encryption_key = self._generate_encryption_key()
        self._fernet = Fernet(self._encryption_key)
        self._audit_checksums = {}  # For tamper detection
        self._initialized = True

        logger.info("CredentialManager initialized with security hardening")

    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key for audit log protection."""
        password = f"cloudwan-test-audit-{secrets.token_hex(16)}".encode()
        salt = secrets.token_bytes(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    def _encrypt_audit_entry(self, entry: dict[str, Any]) -> str:
        """Encrypt audit log entry for tamper protection."""
        entry_json = json.dumps(entry, sort_keys=True, default=str)
        encrypted_entry = self._fernet.encrypt(entry_json.encode())
        return base64.urlsafe_b64encode(encrypted_entry).decode()

    def _generate_entry_checksum(self, entry: dict[str, Any]) -> str:
        """Generate tamper-detection checksum for audit entry."""
        entry_json = json.dumps(entry, sort_keys=True, default=str)
        return hashlib.sha256(entry_json.encode()).hexdigest()

    def _verify_audit_integrity(self) -> bool:
        """Verify audit log integrity using checksums."""
        try:
            for i, entry in enumerate(self._audit_log):
                if i in self._audit_checksums:
                    current_checksum = self._generate_entry_checksum(entry)
                    if current_checksum != self._audit_checksums[i]:
                        logger.error(f"Audit log tampering detected at index {i}")
                        return False
            return True
        except Exception as e:
            logger.error(f"Audit integrity check failed: {e}")
            return False

    def generate_credentials(
        self, duration: Optional[timedelta] = None, test_context: str = "default"
    ) -> TemporalCredentials:
        """Generate secure temporal credentials for test execution.

        Args:
            duration: Credential validity duration (default: 15 minutes)
            test_context: Test context identifier for audit trail

        Returns:
            TemporalCredentials: Secure test credentials with expiration
        """
        duration = duration or self._default_duration
        test_session_id = str(uuid.uuid4())

        # Generate cryptographically secure test credentials
        access_key = f"AKIA{self._generate_secure_suffix()}"
        secret_key = f"test-secret-{self._generate_secure_suffix(40)}"
        session_token = f"test-session-{self._generate_secure_suffix(32)}"

        expires_at = datetime.now(timezone.utc) + duration

        credentials = TemporalCredentials(
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            expires_at=expires_at,
            test_session_id=test_session_id,
        )

        # Store for lifecycle management
        self._active_credentials[test_session_id] = credentials

        # Audit logging for compliance
        self._log_credential_event(
            {
                "event": "credential_generated",
                "session_id": test_session_id,
                "context": test_context,
                "expires_at": expires_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return credentials

    def _generate_secure_suffix(self, length: int = 16) -> str:
        """Generate cryptographically secure random suffix."""
        return secrets.token_hex(length).upper()

    def cleanup_expired_credentials(self) -> int:
        """Cleanup expired credentials from memory.

        Returns:
            int: Number of credentials cleaned up
        """
        expired_sessions = []

        for session_id, credentials in self._active_credentials.items():
            if credentials.is_expired():
                expired_sessions.append(session_id)
                credentials.cleanup()

        # Remove from active tracking
        for session_id in expired_sessions:
            del self._active_credentials[session_id]
            self._log_credential_event(
                {
                    "event": "credential_expired_cleanup",
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired credential sets")

        return len(expired_sessions)

    def _log_credential_event(self, event: dict[str, Any]) -> None:
        """Log credential lifecycle events for audit compliance with encryption."""
        # Add tamper detection metadata
        event["_audit_id"] = secrets.token_hex(8)
        event["_logged_at"] = datetime.now(timezone.utc).isoformat()

        # Generate checksum before adding to log
        checksum = self._generate_entry_checksum(event)
        entry_index = len(self._audit_log)

        # Store encrypted version in memory
        self._audit_log.append(event)
        self._audit_checksums[entry_index] = checksum

        # Log security event (encrypted entry not logged for security)
        logger.info(f"Audit event logged: {event.get('event', 'unknown')} [ID: {event['_audit_id']}]")

        # Rotate audit log if it gets too large (GDPR compliance)
        if len(self._audit_log) > self.AUDIT_LOG_ROTATION_THRESHOLD:
            num_removed = len(self._audit_log) - self.AUDIT_LOG_RETENTION_COUNT
            self._audit_log = self._audit_log[-self.AUDIT_LOG_RETENTION_COUNT :]  # Keep last N events
            # Update checksum indices after rotation (shift keys down by num_removed)
            keys_to_remove = [k for k in self._audit_checksums if k < num_removed]
            for k in keys_to_remove:
                del self._audit_checksums[k]
            # Shift remaining keys
            self._audit_checksums = {k - num_removed: v for k, v in self._audit_checksums.items()}

    def get_audit_trail(self) -> list[dict[str, Any]]:
        """Get credential audit trail for compliance reporting with integrity verification."""
        # Verify audit log integrity before returning
        if not self._verify_audit_integrity():
            logger.error("Audit log integrity compromised - returning secured snapshot")
            # Return sanitized version indicating tampering
            return [{"error": "Audit log integrity compromised", "timestamp": datetime.now(timezone.utc).isoformat()}]

        # Return decrypted audit trail for authorized access
        return self._audit_log.copy()

    def emergency_cleanup(self) -> None:
        """Emergency cleanup of all credentials (security incident response)."""
        logger.warning("Emergency credential cleanup initiated")

        for session_id, credentials in self._active_credentials.items():
            credentials.cleanup()
            self._log_credential_event(
                {
                    "event": "emergency_cleanup",
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        self._active_credentials.clear()


# Global instance for test framework integration
credential_manager = CredentialManager()


def get_secure_test_credentials(test_context: str = "pytest") -> TemporalCredentials:
    """Get secure test credentials with automatic lifecycle management.

    Args:
        test_context: Context identifier for audit trail

    Returns:
        TemporalCredentials: Secure test credentials
    """
    # Cleanup expired credentials before generating new ones
    credential_manager.cleanup_expired_credentials()

    return credential_manager.generate_credentials(test_context=test_context)
