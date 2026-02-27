"""Extended unit tests for Configuration Management.

This module contains additional comprehensive unit tests for the configuration
system to improve coverage of uncovered areas.
"""

import logging
import os
import pytest
from awslabs.amazon_translate_mcp_server.config import (
    ServerConfig,
    load_config_from_env,
    setup_logging,
    validate_aws_config,
)
from unittest.mock import patch


class TestServerConfigExtended:
    """Extended tests for ServerConfig class."""

    def test_server_config_with_all_fields(self):
        """Test ServerConfig with all fields set."""
        config = ServerConfig(
            aws_profile='test-profile',
            aws_region='us-west-2',
            aws_access_key_id='AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
            log_level='DEBUG',
            max_text_length=5000,
            batch_timeout=7200,
            enable_audit_logging=True,
            enable_translation_cache=True,
            cache_ttl=7200,
            max_file_size=20 * 1024 * 1024,
            allowed_file_extensions={'.txt', '.csv', '.tmx', '.docx'},
            blocked_patterns=['pattern1', 'pattern2'],
        )

        assert config.aws_profile == 'test-profile'
        assert config.aws_region == 'us-west-2'
        assert config.aws_access_key_id == 'AKIAIOSFODNN7EXAMPLE'  # pragma: allowlist secret
        assert config.log_level == 'DEBUG'
        assert config.max_text_length == 5000
        assert config.batch_timeout == 7200

        assert config.cache_ttl == 7200
        assert config.max_file_size == 20 * 1024 * 1024
        assert '.docx' in config.allowed_file_extensions
        assert len(config.blocked_patterns) == 2

    def test_server_config_validation_invalid_log_level(self):
        """Test ServerConfig validation with invalid log level."""
        with pytest.raises(ValueError) as exc_info:
            ServerConfig(log_level='INVALID')
        assert 'Invalid log_level: INVALID' in str(exc_info.value)

    def test_server_config_validation_invalid_max_text_length(self):
        """Test ServerConfig validation with invalid max_text_length."""
        with pytest.raises(ValueError) as exc_info:
            ServerConfig(max_text_length=0)
        assert 'max_text_length must be positive' in str(exc_info.value)

    def test_server_config_validation_invalid_batch_timeout(self):
        """Test ServerConfig validation with invalid batch_timeout."""
        with pytest.raises(ValueError) as exc_info:
            ServerConfig(batch_timeout=0)
        assert 'batch_timeout must be positive' in str(exc_info.value)

    def test_server_config_validation_invalid_cache_ttl(self):
        """Test ServerConfig validation with invalid cache_ttl."""
        with pytest.raises(ValueError) as exc_info:
            ServerConfig(cache_ttl=-1)
        assert 'cache_ttl cannot be negative' in str(exc_info.value)

    def test_server_config_validation_invalid_max_file_size(self):
        """Test ServerConfig validation with invalid max_file_size."""
        with pytest.raises(ValueError) as exc_info:
            ServerConfig(max_file_size=0)
        assert 'max_file_size must be positive' in str(exc_info.value)


class TestSetupLogging:
    """Test logging setup functionality."""

    def test_setup_logging_debug_level(self):
        """Test logging setup with DEBUG level."""
        config = ServerConfig(log_level='DEBUG', enable_audit_logging=True)

        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(config)

            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args[1]
            assert call_args['level'] == logging.DEBUG

    def test_setup_logging_invalid_level_defaults_to_info(self):
        """Test logging setup with invalid level defaults to INFO."""
        # Create config with valid level first, then modify it to bypass validation
        config = ServerConfig(log_level='INFO', enable_audit_logging=False)
        # Directly set invalid level to bypass validation
        object.__setattr__(config, 'log_level', 'INVALID')

        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(config)

            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args[1]
            assert call_args['level'] == logging.INFO  # Should default to INFO


class TestValidateAWSConfig:
    """Test AWS configuration validation."""

    def test_validate_aws_config_with_explicit_credentials(self):
        """Test AWS config validation with explicit credentials."""
        config = ServerConfig(
            aws_access_key_id='AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
        )

        result = validate_aws_config(config)
        assert result is True  # Should be valid

    def test_validate_aws_config_with_profile(self):
        """Test AWS config validation with profile."""
        config = ServerConfig(aws_profile='test-profile')

        result = validate_aws_config(config)
        assert result is True  # Should be valid

    def test_validate_aws_config_with_env_vars(self):
        """Test AWS config validation with environment variables."""
        config = ServerConfig()

        with patch.dict(
            os.environ,
            {
                'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
                'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
            },
        ):
            result = validate_aws_config(config)
            assert result is True  # Should be valid

    def test_validate_aws_config_no_credentials(self):
        """Test AWS config validation with no credentials."""
        config = ServerConfig()

        with patch.dict(os.environ, {}, clear=True):
            result = validate_aws_config(config)
            # Should still return True as it assumes IAM role is available
            assert result is True


class TestEnvironmentVariableLoading:
    """Test loading configuration from environment variables."""

    def test_load_config_from_env_comprehensive(self):
        """Test comprehensive environment variable loading."""
        env_vars = {
            'AWS_REGION': 'ap-southeast-1',
            'AWS_PROFILE': 'test-profile',
            'FASTMCP_LOG_LEVEL': 'DEBUG',
            'TRANSLATE_MAX_TEXT_LENGTH': '7500',
            'TRANSLATE_BATCH_TIMEOUT': '7200',
            'ENABLE_AUDIT_LOGGING': 'true',
            'ENABLE_TRANSLATION_CACHE': 'false',
            'TRANSLATE_CACHE_TTL': '1800',
            'TRANSLATE_MAX_FILE_SIZE': '20971520',  # 20MB
            'TRANSLATE_ALLOWED_EXTENSIONS': '.txt,.csv,.docx',
            'TRANSLATE_BLOCKED_PATTERNS': 'pattern1,pattern2',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()

            assert config.aws_region == 'ap-southeast-1'
            assert config.aws_profile == 'test-profile'
            assert config.log_level == 'DEBUG'
            assert config.max_text_length == 7500
            assert config.batch_timeout == 7200

            assert config.enable_audit_logging is True
            assert config.enable_translation_cache is False
            assert config.cache_ttl == 1800
            assert config.max_file_size == 20971520
            assert '.docx' in config.allowed_file_extensions
            assert len(config.blocked_patterns) == 2

    def test_load_config_from_env_defaults(self):
        """Test environment variable loading with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config_from_env()

            # Check defaults
            assert config.log_level == 'INFO'
            assert config.max_text_length == 10000
            assert config.batch_timeout == 3600

            assert config.enable_audit_logging is True
            assert config.enable_translation_cache is True
            assert config.cache_ttl == 3600
            assert config.max_file_size == 10 * 1024 * 1024  # 10MB
            assert '.csv' in config.allowed_file_extensions
            assert len(config.blocked_patterns) == 0
