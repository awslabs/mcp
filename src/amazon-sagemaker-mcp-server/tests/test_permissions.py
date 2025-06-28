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

"""Tests for permission utilities."""

import os
from unittest.mock import patch

import pytest

from awslabs.amazon_sagemaker_mcp_server.utils.permissions import (
    PermissionError,
    require_write_access,
    require_sensitive_data_access,
    is_write_access_enabled,
    is_sensitive_data_access_enabled,
    get_permission_summary,
)


class TestPermissionChecks:
    """Test permission checking functions."""

    def setUp(self):
        """Set up test environment."""
        # Clear environment variables
        self.original_write = os.environ.get('ALLOW_WRITE')
        self.original_sensitive = os.environ.get('ALLOW_SENSITIVE_DATA_ACCESS')
        
        if 'ALLOW_WRITE' in os.environ:
            del os.environ['ALLOW_WRITE']
        if 'ALLOW_SENSITIVE_DATA_ACCESS' in os.environ:
            del os.environ['ALLOW_SENSITIVE_DATA_ACCESS']

    def tearDown(self):
        """Clean up test environment."""
        # Restore environment variables
        if self.original_write is not None:
            os.environ['ALLOW_WRITE'] = self.original_write
        elif 'ALLOW_WRITE' in os.environ:
            del os.environ['ALLOW_WRITE']
            
        if self.original_sensitive is not None:
            os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = self.original_sensitive
        elif 'ALLOW_SENSITIVE_DATA_ACCESS' in os.environ:
            del os.environ['ALLOW_SENSITIVE_DATA_ACCESS']

    def test_is_write_access_enabled_default(self):
        """Test write access check with default (disabled) state."""
        result = is_write_access_enabled()
        assert result is False

    def test_is_write_access_enabled_true(self):
        """Test write access check when enabled."""
        os.environ['ALLOW_WRITE'] = 'true'
        result = is_write_access_enabled()
        assert result is True

    def test_is_write_access_enabled_false(self):
        """Test write access check when explicitly disabled."""
        os.environ['ALLOW_WRITE'] = 'false'
        result = is_write_access_enabled()
        assert result is False

    def test_is_write_access_enabled_case_insensitive(self):
        """Test write access check is case insensitive."""
        test_cases = ['TRUE', 'True', 'tRuE', 'TRUE']
        for case in test_cases:
            os.environ['ALLOW_WRITE'] = case
            result = is_write_access_enabled()
            assert result is True

    def test_is_write_access_enabled_invalid_value(self):
        """Test write access check with invalid value."""
        os.environ['ALLOW_WRITE'] = 'invalid'
        result = is_write_access_enabled()
        assert result is False

    def test_is_sensitive_data_access_enabled_default(self):
        """Test sensitive data access check with default (disabled) state."""
        result = is_sensitive_data_access_enabled()
        assert result is False

    def test_is_sensitive_data_access_enabled_true(self):
        """Test sensitive data access check when enabled."""
        os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = 'true'
        result = is_sensitive_data_access_enabled()
        assert result is True

    def test_is_sensitive_data_access_enabled_false(self):
        """Test sensitive data access check when explicitly disabled."""
        os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = 'false'
        result = is_sensitive_data_access_enabled()
        assert result is False

    def test_is_sensitive_data_access_enabled_case_insensitive(self):
        """Test sensitive data access check is case insensitive."""
        test_cases = ['TRUE', 'True', 'tRuE', 'TRUE']
        for case in test_cases:
            os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = case
            result = is_sensitive_data_access_enabled()
            assert result is True


class TestPermissionRequirements:
    """Test permission requirement functions."""

    def setUp(self):
        """Set up test environment."""
        # Clear environment variables
        if 'ALLOW_WRITE' in os.environ:
            del os.environ['ALLOW_WRITE']
        if 'ALLOW_SENSITIVE_DATA_ACCESS' in os.environ:
            del os.environ['ALLOW_SENSITIVE_DATA_ACCESS']

    def test_require_write_access_enabled(self):
        """Test require write access when enabled."""
        os.environ['ALLOW_WRITE'] = 'true'
        # Should not raise an exception
        require_write_access()

    def test_require_write_access_disabled(self):
        """Test require write access when disabled."""
        with pytest.raises(PermissionError) as exc_info:
            require_write_access()
        
        assert "Write access is required" in str(exc_info.value)
        assert "--allow-write flag" in str(exc_info.value)

    def test_require_sensitive_data_access_enabled(self):
        """Test require sensitive data access when enabled."""
        os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = 'true'
        # Should not raise an exception
        require_sensitive_data_access()

    def test_require_sensitive_data_access_disabled(self):
        """Test require sensitive data access when disabled."""
        with pytest.raises(PermissionError) as exc_info:
            require_sensitive_data_access()
        
        assert "Sensitive data access is required" in str(exc_info.value)
        assert "--allow-sensitive-data-access flag" in str(exc_info.value)


class TestPermissionSummary:
    """Test permission summary function."""

    def setUp(self):
        """Set up test environment."""
        # Clear environment variables
        if 'ALLOW_WRITE' in os.environ:
            del os.environ['ALLOW_WRITE']
        if 'ALLOW_SENSITIVE_DATA_ACCESS' in os.environ:
            del os.environ['ALLOW_SENSITIVE_DATA_ACCESS']

    def test_get_permission_summary_default(self):
        """Test permission summary with default settings."""
        summary = get_permission_summary()
        
        expected = {
            'write_access': False,
            'sensitive_data_access': False,
            'read_only_mode': True
        }
        
        assert summary == expected

    def test_get_permission_summary_write_enabled(self):
        """Test permission summary with write access enabled."""
        os.environ['ALLOW_WRITE'] = 'true'
        
        summary = get_permission_summary()
        
        expected = {
            'write_access': True,
            'sensitive_data_access': False,
            'read_only_mode': False
        }
        
        assert summary == expected

    def test_get_permission_summary_sensitive_enabled(self):
        """Test permission summary with sensitive data access enabled."""
        os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = 'true'
        
        summary = get_permission_summary()
        
        expected = {
            'write_access': False,
            'sensitive_data_access': True,
            'read_only_mode': True
        }
        
        assert summary == expected

    def test_get_permission_summary_all_enabled(self):
        """Test permission summary with all permissions enabled."""
        os.environ['ALLOW_WRITE'] = 'true'
        os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = 'true'
        
        summary = get_permission_summary()
        
        expected = {
            'write_access': True,
            'sensitive_data_access': True,
            'read_only_mode': False
        }
        
        assert summary == expected


class TestPermissionError:
    """Test custom PermissionError exception."""

    def test_permission_error_inheritance(self):
        """Test that PermissionError inherits from Exception."""
        error = PermissionError("Test message")
        assert isinstance(error, Exception)

    def test_permission_error_message(self):
        """Test PermissionError message handling."""
        message = "Test permission error message"
        error = PermissionError(message)
        assert str(error) == message

    def test_permission_error_empty_message(self):
        """Test PermissionError with empty message."""
        error = PermissionError("")
        assert str(error) == ""


class TestEnvironmentVariableHandling:
    """Test environment variable handling edge cases."""

    def test_environment_variable_whitespace(self):
        """Test handling of environment variables with whitespace."""
        os.environ['ALLOW_WRITE'] = ' true '
        result = is_write_access_enabled()
        # The current implementation doesn't strip whitespace, so this should be False
        assert result is False

    def test_environment_variable_numeric(self):
        """Test handling of numeric environment variables."""
        os.environ['ALLOW_WRITE'] = '1'
        result = is_write_access_enabled()
        assert result is False  # Only 'true' (case insensitive) should work

    def test_environment_variable_empty_string(self):
        """Test handling of empty string environment variables."""
        os.environ['ALLOW_WRITE'] = ''
        result = is_write_access_enabled()
        assert result is False

    def test_multiple_permission_checks(self):
        """Test multiple permission checks in sequence."""
        # Test write access multiple times
        assert is_write_access_enabled() is False
        assert is_write_access_enabled() is False
        
        os.environ['ALLOW_WRITE'] = 'true'
        assert is_write_access_enabled() is True
        assert is_write_access_enabled() is True
        
        # Test sensitive data access multiple times
        assert is_sensitive_data_access_enabled() is False
        assert is_sensitive_data_access_enabled() is False
        
        os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = 'true'
        assert is_sensitive_data_access_enabled() is True
        assert is_sensitive_data_access_enabled() is True


class TestIntegration:
    """Integration tests for permission utilities."""

    def test_permission_workflow(self):
        """Test a complete permission workflow."""
        # Start with no permissions
        summary = get_permission_summary()
        assert summary['read_only_mode'] is True
        
        # Enable write access
        os.environ['ALLOW_WRITE'] = 'true'
        require_write_access()  # Should not raise
        
        summary = get_permission_summary()
        assert summary['write_access'] is True
        assert summary['read_only_mode'] is False
        
        # Enable sensitive data access
        os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = 'true'
        require_sensitive_data_access()  # Should not raise
        
        summary = get_permission_summary()
        assert summary['sensitive_data_access'] is True
        
        # Disable write access
        os.environ['ALLOW_WRITE'] = 'false'
        with pytest.raises(PermissionError):
            require_write_access()
        
        summary = get_permission_summary()
        assert summary['write_access'] is False
        assert summary['read_only_mode'] is True
