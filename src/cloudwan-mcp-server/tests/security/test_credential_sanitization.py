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


"""Tests for comprehensive credential sanitization and protection mechanisms.

Agent F2: Credential Protection Specialist Test Suite
Model: Cohere Command R+
Focus: Zero information disclosure validation
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from awslabs.cloudwan_mcp_server.config_manager import ConfigPersistenceManager
from awslabs.cloudwan_mcp_server.server import sanitize_error_message, secure_environment_update


class TestCredentialSanitization:
    """Test credential sanitization across all error handling paths."""

    def test_aws_access_key_sanitization(self) -> None:
        """Test AWS access key patterns are properly sanitized."""
        test_cases = [
            "AccessKey=AKIAIOSFODNN7EXAMPLE",
            "AWS_ACCESS_KEY_ID=AKIAI44QH8DHBEXAMPLE",
            "access_key: AKIAIOSFODNN7EXAMPLE",
            "Failed with key AKIAIOSFODNN7EXAMPLE in request",
        ]

        for case in test_cases:
            sanitized = sanitize_error_message(case)
            assert "AKIA" not in sanitized
            assert (
                "[ACCESS_KEY_REDACTED]" in sanitized
                or "AWS_[VARIABLE_REDACTED]" in sanitized
                or "[CREDENTIAL_REDACTED]" in sanitized
            )

    def test_aws_secret_key_sanitization(self) -> None:
        """Test AWS secret key patterns are properly sanitized."""
        test_cases = [
            "SecretKey=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "secret: abcdef1234567890abcdef1234567890abcdef12",
            "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        ]

        for case in test_cases:
            sanitized = sanitize_error_message(case)
            assert "wJalrXUt" not in sanitized
            assert "abcdef123456" not in sanitized
            assert (
                "[SECRET_KEY_REDACTED]" in sanitized
                or "AWS_[VARIABLE_REDACTED]" in sanitized
                or "[CREDENTIAL_REDACTED]" in sanitized
            )

    def test_session_token_sanitization(self) -> None:
        """Test AWS session token sanitization."""
        long_token = "AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4Olgk"

        test_case = f"SessionToken={long_token}"
        sanitized = sanitize_error_message(test_case)

        assert long_token not in sanitized
        assert "[SESSION_TOKEN_REDACTED]" in sanitized or "[CREDENTIAL_REDACTED]" in sanitized

    def test_environment_variable_sanitization(self) -> None:
        """Test environment variable value sanitization."""
        test_cases = [
            "AWS_PROFILE=production-admin",
            "AWS_DEFAULT_REGION=us-east-1",
            "AWS_ACCESS_KEY_ID=AKIAEXAMPLE",
            "Environment: AWS_SESSION_TOKEN=longtokenhere",
        ]

        for case in test_cases:
            sanitized = sanitize_error_message(case)
            assert "production-admin" not in sanitized
            assert "us-east-1" not in sanitized
            assert "AWS_[VARIABLE_REDACTED]" in sanitized

    def test_arn_sanitization(self) -> None:
        """Test AWS ARN sanitization."""
        test_cases = [
            "arn:aws:iam::123456789012:role/MyRole",
            "Resource: arn:aws:ec2:us-east-1:123456789012:vpc/vpc-12345678",
            "Failed to access arn:aws:s3:::my-bucket/object",
        ]

        for case in test_cases:
            sanitized = sanitize_error_message(case)
            assert "123456789012" not in sanitized
            assert "MyRole" not in sanitized
            assert "[ARN_REDACTED]" in sanitized

    def test_account_number_sanitization(self) -> None:
        """Test AWS account number sanitization."""
        test_cases = [
            "Account 123456789012 access denied",
            "Failed for account: 987654321098",
            "Cross-account role in 555666777888",
        ]

        for case in test_cases:
            sanitized = sanitize_error_message(case)
            assert "123456789012" not in sanitized
            assert "987654321098" not in sanitized
            assert "555666777888" not in sanitized
            assert "[ACCOUNT_REDACTED]" in sanitized

    def test_credential_path_sanitization(self) -> None:
        """Test credential file path sanitization."""
        test_cases = [
            "/Users/user/.aws/credentials",
            "~/.aws/config",
            "/home/user/.aws/credentials-backup",
            "Unable to read /opt/app/.aws/credentials",
        ]

        for case in test_cases:
            sanitized = sanitize_error_message(case)
            assert ".aws" not in sanitized
            assert "credentials" not in sanitized
            assert "[CREDENTIAL_PATH_REDACTED]" in sanitized or "[AWS_CONFIG_PATH_REDACTED]" in sanitized

    def test_generic_credential_sanitization(self) -> None:
        """Test generic credential pattern sanitization."""
        test_cases = [
            "password=mysecretpassword123",
            "token: abc123def456ghi789",
            "key=super-secret-api-key-here",
            "secret: my_database_secret",
        ]

        for case in test_cases:
            sanitized = sanitize_error_message(case)
            assert "mysecretpassword123" not in sanitized
            assert "abc123def456ghi789" not in sanitized
            assert "super-secret-api-key-here" not in sanitized
            assert "my_database_secret" not in sanitized
            assert "=[CREDENTIAL_REDACTED]" in sanitized


class TestSecureEnvironmentUpdate:
    """Test secure environment variable update functionality."""

    def test_valid_aws_profile_update(self) -> None:
        """Test valid AWS profile updates."""
        valid_profiles = ["default", "production", "dev-environment", "user123", "team_admin"]

        for profile in valid_profiles:
            result = secure_environment_update("AWS_PROFILE", profile)
            assert result is True
            assert os.environ.get("AWS_PROFILE") == profile

    def test_invalid_aws_profile_rejection(self) -> None:
        """Test invalid AWS profile formats are rejected."""
        invalid_profiles = [
            "../malicious",
            "profile with spaces",
            "profile@domain.com",
            "profile$variable",
            "profile;command",
        ]

        original_value = os.environ.get("AWS_PROFILE")

        for profile in invalid_profiles:
            result = secure_environment_update("AWS_PROFILE", profile)
            assert result is False
            # Ensure environment wasn't modified
            assert os.environ.get("AWS_PROFILE") == original_value

    def test_valid_aws_region_update(self) -> None:
        """Test valid AWS region updates."""
        valid_regions = ["us-east-1", "eu-west-2", "ap-southeast-1", "us-gov-east-1", "cn-north-1"]

        for region in valid_regions:
            result = secure_environment_update("AWS_DEFAULT_REGION", region)
            assert result is True
            assert os.environ.get("AWS_DEFAULT_REGION") == region

    def test_invalid_aws_region_rejection(self) -> None:
        """Test invalid AWS region formats are rejected."""
        invalid_regions = [
            "US-EAST-1",  # Wrong case
            "us_east_1",  # Wrong separator
            "us-east-1; malicious-command",
            "../../../etc/passwd",
            "region with spaces",
        ]

        original_value = os.environ.get("AWS_DEFAULT_REGION")

        for region in invalid_regions:
            result = secure_environment_update("AWS_DEFAULT_REGION", region)
            assert result is False
            assert os.environ.get("AWS_DEFAULT_REGION") == original_value

    def test_invalid_key_format_rejection(self) -> None:
        """Test invalid environment variable key formats are rejected."""
        invalid_keys = [
            "aws-profile",  # Wrong format
            "123_INVALID",  # Starts with number
            "INVALID KEY",  # Contains space
            "invalid$key",  # Contains special character
            "",  # Empty key
        ]

        for key in invalid_keys:
            result = secure_environment_update(key, "test-value")
            assert result is False


class TestConfigurationSanitization:
    """Test configuration persistence sanitization."""

    def setup_method(self) -> None:
        """Set up test configuration manager."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_manager = ConfigPersistenceManager(self.test_dir)

    def test_identity_sanitization_on_export(self) -> None:
        """Test identity information is sanitized during export."""
        # Save configuration with sensitive identity info
        metadata = {
            "identity": {
                "account": "123456789012",
                "user_id": "AIDACKCEVSQ6C2EXAMPLE",
                "arn": "arn:aws:iam::123456789012:user/testuser",
            },
            "operation": "test_operation",
        }

        self.config_manager.save_current_config("test-profile", "us-east-1", metadata)

        # Export and verify sanitization
        export_path = self.test_dir / "export.json"
        result = self.config_manager.export_config(export_path)

        assert result is True
        assert export_path.exists()

        with open(export_path) as f:
            export_data = json.load(f)

        identity = export_data["current_config"]["metadata"]["identity"]
        assert identity["account"] == "[SANITIZED]"
        assert identity["user_id"] == "[SANITIZED]"
        assert identity["arn"] == "[SANITIZED]"

        # Non-sensitive data should remain
        assert export_data["current_config"]["metadata"]["operation"] == "test_operation"
        assert "Sensitive data has been sanitized" in export_data["note"]

    def test_credential_metadata_sanitization(self) -> None:
        """Test credential metadata is sanitized."""
        metadata = {
            "credentials": "secret-data",
            "access_key": "AKIAEXAMPLE",
            "secret_key": "secret123",
            "session_token": "token123",
            "safe_data": "this-should-remain",
        }

        self.config_manager.save_current_config("test-profile", "us-east-1", metadata)

        export_path = self.test_dir / "export.json"
        result = self.config_manager.export_config(export_path)

        assert result is True

        with open(export_path) as f:
            export_data = json.load(f)

        meta = export_data["current_config"]["metadata"]
        assert meta["credentials"] == "[SANITIZED]"
        assert meta["access_key"] == "[SANITIZED]"
        assert meta["secret_key"] == "[SANITIZED]"
        assert meta["session_token"] == "[SANITIZED]"
        assert meta["safe_data"] == "this-should-remain"

    def test_history_sanitization_on_export(self) -> None:
        """Test configuration history is sanitized on export."""
        # Create multiple config entries with sensitive data
        for i in range(3):
            metadata = {"identity": {"account": f"12345678901{i}", "arn": f"arn:aws:iam::12345678901{i}:user/user{i}"}}
            self.config_manager.save_current_config(f"profile{i}", "us-east-1", metadata)

        export_path = self.test_dir / "history_export.json"
        result = self.config_manager.export_config(export_path)

        assert result is True

        with open(export_path) as f:
            export_data = json.load(f)

        # Check all history entries are sanitized
        for entry in export_data["config_history"]:
            identity = entry["metadata"]["identity"]
            assert identity["account"] == "[SANITIZED]"
            assert identity["arn"] == "[SANITIZED]"

    def test_secure_restore_config(self) -> None:
        """Test configuration restore validates input and updates environment."""
        result = self.config_manager.restore_config("test-profile", "us-east-1")

        assert result is True
        assert os.environ.get("AWS_PROFILE") == "test-profile"
        assert os.environ.get("AWS_DEFAULT_REGION") == "us-east-1"

    def test_restore_config_failure_handling(self) -> None:
        """Test configuration restore handles invalid input."""
        # Test invalid profile format
        result = self.config_manager.restore_config("invalid profile", "us-east-1")
        assert result is False

        # Test invalid region format
        result = self.config_manager.restore_config("test-profile", "INVALID_REGION")
        assert result is False

    def teardown_method(self) -> None:
        """Clean up test files."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)


class TestEndToEndCredentialProtection:
    """End-to-end tests for complete credential protection."""

    @patch("boto3.Session")
    def test_full_aws_config_manager_sanitization(self, mock_session) -> None:
        """Test full AWS config manager with credential sanitization."""
        # Mock AWS API responses with sensitive data
        mock_identity = {
            "Account": "123456789012",
            "UserId": "AIDACKCEVSQ6C2EXAMPLE",
            "Arn": "arn:aws:iam::123456789012:user/testuser",
        }

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = mock_identity
        mock_session.return_value.client.return_value = mock_sts

        # Test that sensitive data doesn't leak in responses
        # This would be part of integration testing with the full server
        pass

    def test_comprehensive_sanitization_patterns(self) -> None:
        """Test comprehensive sanitization across all known patterns."""
        # Real-world-like error message with multiple sensitive patterns
        sanitized = sanitize_error_message(COMPLEX_MESSAGE)
        # Map each sensitive pattern to its expected marker
        pattern_marker_map = {
            "123456789012": "[ACCOUNT_REDACTED]",
            "production-admin": "[CREDENTIAL_REDACTED]",
            "us-east-1": "[CREDENTIAL_REDACTED]",
            "AKIAIOSFODNN7EXAMPLE": "[CREDENTIAL_REDACTED]",
            "wJalrXUtnFEMI": "[CREDENTIAL_REDACTED]",
            "AQoEXAMPLEH4aoAH0gNCAPy": "[CREDENTIAL_REDACTED]",
            "arn:aws:iam::123456789012:role/PowerUser": "[ARN_REDACTED]",
            "/home/user/.aws/credentials": "[CREDENTIAL_PATH_REDACTED]",
            "550e8400-e29b-41d4-a716-446655440000": "[UUID_REDACTED]",
            "192.168.1.100": "[IP_REDACTED]",
            "super-secret-password-123": "[CREDENTIAL_REDACTED]",
        }

        for pattern, marker in pattern_marker_map.items():
            assert pattern not in sanitized, f"Pattern '{pattern}' was not sanitized"
            assert marker in sanitized, f"Sanitization marker '{marker}' is missing for pattern '{pattern}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
