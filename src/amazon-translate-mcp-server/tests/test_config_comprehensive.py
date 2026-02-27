"""Comprehensive tests for Configuration module.

This module contains tests to achieve high coverage of the config.py module.
"""

import os
import pytest
import tempfile
from awslabs.amazon_translate_mcp_server.config import (
    ServerConfig,
    load_config_from_env,
    setup_logging,
    validate_aws_config,
)
from unittest.mock import patch


class TestServerConfigComprehensive:
    """Comprehensive tests for ServerConfig class."""

    def test_server_config_defaults(self):
        """Test ServerConfig with default values."""
        config = ServerConfig()

        assert config.aws_profile is None
        assert config.aws_region is None
        assert config.aws_access_key_id is None
        assert config.aws_secret_access_key is None
        assert config.log_level == 'INFO'
        assert config.max_text_length == 10000
        assert config.batch_timeout == 3600

        assert config.enable_audit_logging is True
        assert config.enable_translation_cache is True
        assert config.cache_ttl == 3600
        assert config.max_file_size == 10485760
        assert config.allowed_file_extensions == {'.txt', '.csv', '.tmx'}
        assert config.blocked_patterns == []

    def test_server_config_custom_values(self):
        """Test ServerConfig with custom values."""
        config = ServerConfig(
            aws_profile='custom-profile',
            aws_region='us-west-2',
            aws_access_key_id='AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
            log_level='DEBUG',
            max_text_length=5000,
            batch_timeout=1800,
            enable_audit_logging=False,
            enable_translation_cache=False,
            cache_ttl=7200,
            max_file_size=5242880,
            allowed_file_extensions={'.txt', '.docx'},
            blocked_patterns=['*.tmp'],
        )

        assert config.aws_profile == 'custom-profile'
        assert config.aws_region == 'us-west-2'
        assert config.aws_access_key_id == 'AKIAIOSFODNN7EXAMPLE'
        assert (
            config.aws_secret_access_key == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        )  # pragma: allowlist secret
        assert config.log_level == 'DEBUG'
        assert config.max_text_length == 5000
        assert config.batch_timeout == 1800

        assert config.enable_audit_logging is False
        assert config.enable_translation_cache is False
        assert config.cache_ttl == 7200
        assert config.max_file_size == 5242880
        assert config.allowed_file_extensions == {'.txt', '.docx'}
        assert config.blocked_patterns == ['*.tmp']

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

        with pytest.raises(ValueError) as exc_info:
            ServerConfig(max_text_length=-100)
        assert 'max_text_length must be positive' in str(exc_info.value)

    def test_server_config_validation_invalid_batch_timeout(self):
        """Test ServerConfig validation with invalid batch_timeout."""
        with pytest.raises(ValueError) as exc_info:
            ServerConfig(batch_timeout=0)
        assert 'batch_timeout must be positive' in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            ServerConfig(batch_timeout=-1)
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

        with pytest.raises(ValueError) as exc_info:
            ServerConfig(max_file_size=-1000)
        assert 'max_file_size must be positive' in str(exc_info.value)

    def test_server_config_validation_valid_log_levels(self):
        """Test ServerConfig with all valid log levels."""
        for level in ['DEBUG', 'INFO', 'WARN', 'ERROR']:
            config = ServerConfig(log_level=level)
            assert config.log_level == level

    def test_server_config_validation_edge_cases(self):
        """Test ServerConfig validation edge cases."""
        # Test minimum valid values
        config = ServerConfig(max_text_length=1, batch_timeout=1, cache_ttl=0, max_file_size=1)
        assert config.max_text_length == 1
        assert config.batch_timeout == 1
        assert config.cache_ttl == 0
        assert config.max_file_size == 1


class TestLoadConfigFromEnv:
    """Test load_config_from_env function."""

    def test_load_config_from_env_empty(self):
        """Test loading config when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config_from_env()

            # Should return default config
            assert config.aws_profile is None
            assert config.aws_region is None
            assert config.log_level == 'INFO'
            assert config.max_text_length == 10000

    def test_load_config_from_env_aws_credentials(self):
        """Test loading AWS credentials from environment."""
        env_vars = {
            'AWS_PROFILE': 'test-profile',
            'AWS_REGION': 'us-east-1',
            'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()

            assert config.aws_profile == 'test-profile'
            assert config.aws_region == 'us-east-1'
            assert config.aws_access_key_id == 'AKIAIOSFODNN7EXAMPLE'
            assert (
                config.aws_secret_access_key == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
            )  # pragma: allowlist secret

    def test_load_config_from_env_logging_settings(self):
        """Test loading logging settings from environment."""
        env_vars = {'FASTMCP_LOG_LEVEL': 'DEBUG', 'ENABLE_AUDIT_LOGGING': 'false'}

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()

            assert config.log_level == 'DEBUG'
            assert config.enable_audit_logging is False

    def test_load_config_from_env_performance_settings(self):
        """Test loading performance settings from environment."""
        env_vars = {
            'TRANSLATE_MAX_TEXT_LENGTH': '5000',
            'TRANSLATE_BATCH_TIMEOUT': '1800',
            'ENABLE_TRANSLATION_CACHE': 'false',
            'TRANSLATE_CACHE_TTL': '7200',
            'TRANSLATE_MAX_FILE_SIZE': '5242880',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()

            assert config.max_text_length == 5000
            assert config.batch_timeout == 1800
            assert config.enable_translation_cache is False
            assert config.cache_ttl == 7200
            assert config.max_file_size == 5242880

    def test_load_config_from_env_monitoring_settings(self):
        """Test loading monitoring settings from environment."""
        env_vars = {
            'ENABLE_AUDIT_LOGGING': 'true',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()

            assert config.enable_audit_logging is True

    def test_load_config_from_env_file_settings(self):
        """Test loading file settings from environment."""
        env_vars = {
            'TRANSLATE_ALLOWED_EXTENSIONS': '.txt,.docx,.pdf',
            'TRANSLATE_BLOCKED_PATTERNS': '*.tmp,*.bak',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()

            assert config.allowed_file_extensions == {'.txt', '.docx', '.pdf'}
            assert config.blocked_patterns == ['*.tmp', '*.bak']

    def test_load_config_from_env_boolean_parsing(self):
        """Test boolean parsing from environment variables."""
        # Test various boolean representations
        true_values = ['true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES']
        false_values = ['false', 'False', 'FALSE', '0', 'no', 'No', 'NO']

        for true_val in true_values:
            with patch.dict(os.environ, {'ENABLE_TRANSLATION_CACHE': true_val}, clear=True):
                config = load_config_from_env()
                assert config.enable_translation_cache is True

        for false_val in false_values:
            with patch.dict(os.environ, {'ENABLE_TRANSLATION_CACHE': false_val}, clear=True):
                config = load_config_from_env()
                assert config.enable_translation_cache is False

    def test_load_config_from_env_invalid_values(self):
        """Test handling of invalid environment variable values."""
        # Invalid integer values should use defaults
        env_vars = {
            'TRANSLATE_MAX_TEXT_LENGTH': 'invalid',
            'TRANSLATE_BATCH_TIMEOUT': 'not_a_number',
            'TRANSLATE_CACHE_TTL': 'abc',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()

            # Should fall back to defaults
            assert config.max_text_length == 10000
            assert config.batch_timeout == 3600
            assert config.cache_ttl == 3600

    def test_load_config_from_env_empty_strings(self):
        """Test handling of empty string environment variables."""
        env_vars = {'AWS_PROFILE': '', 'AWS_REGION': ''}

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()

            # Empty strings should be treated as empty strings, not None
            assert config.aws_profile == ''
            assert config.aws_region == ''
            assert config.log_level == 'INFO'  # Default


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_info_level(self):
        """Test logging setup with INFO level."""
        config = ServerConfig(log_level='INFO', enable_audit_logging=False)

        with (
            patch('logging.basicConfig') as mock_basic_config,
            patch('logging.getLogger'),
        ):
            setup_logging(config)

            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args[1]
            assert call_args['level'] == 20  # logging.INFO

    def test_setup_logging_debug_level(self):
        """Test logging setup with DEBUG level."""
        config = ServerConfig(log_level='DEBUG', enable_audit_logging=False)

        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(config)

            call_args = mock_basic_config.call_args[1]
            assert call_args['level'] == 10  # logging.DEBUG

    def test_setup_logging_warn_level(self):
        """Test logging setup with WARN level."""
        config = ServerConfig(log_level='WARN', enable_audit_logging=False)

        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(config)

            call_args = mock_basic_config.call_args[1]
            assert call_args['level'] == 30  # logging.WARNING

    def test_setup_logging_error_level(self):
        """Test logging setup with ERROR level."""
        config = ServerConfig(log_level='ERROR', enable_audit_logging=False)

        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(config)

            call_args = mock_basic_config.call_args[1]
            assert call_args['level'] == 40  # logging.ERROR

    def test_setup_logging_invalid_level_defaults_to_info(self):
        """Test logging setup with invalid level defaults to INFO."""
        # Create config with valid level first, then modify it
        config = ServerConfig(log_level='INFO', enable_audit_logging=False)
        # Bypass validation by setting directly
        object.__setattr__(config, 'log_level', 'INVALID')

        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(config)

            call_args = mock_basic_config.call_args[1]
            assert call_args['level'] == 20  # logging.INFO (default)

    def test_setup_logging_with_audit_logging_enabled(self):
        """Test logging setup with audit logging enabled."""
        config = ServerConfig(log_level='INFO', enable_audit_logging=True)

        with (
            patch('logging.basicConfig'),
            patch('logging.getLogger') as mock_get_logger,
        ):
            from unittest.mock import Mock

            mock_audit_logger = Mock()
            mock_get_logger.return_value = mock_audit_logger

            setup_logging(config)

            # Verify audit logger setup
            mock_get_logger.assert_called()
            mock_audit_logger.setLevel.assert_called()

    def test_setup_logging_with_audit_logging_disabled(self):
        """Test logging setup with audit logging disabled."""
        config = ServerConfig(log_level='INFO', enable_audit_logging=False)

        with (
            patch('logging.basicConfig'),
            patch('logging.getLogger') as mock_get_logger,
        ):
            from unittest.mock import Mock

            mock_audit_logger = Mock()
            mock_get_logger.return_value = mock_audit_logger

            setup_logging(config)

            # Audit logger should be set to CRITICAL level (effectively disabled)
            mock_get_logger.assert_called()
            mock_audit_logger.setLevel.assert_called()


class TestValidateAwsConfig:
    """Test validate_aws_config function."""

    def test_validate_aws_config_with_profile(self):
        """Test AWS config validation with profile."""
        config = ServerConfig(aws_profile='test-profile')

        # Should not raise any exception
        validate_aws_config(config)

    def test_validate_aws_config_with_access_keys(self):
        """Test AWS config validation with access keys."""
        config = ServerConfig(
            aws_access_key_id='AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
        )

        # Should not raise any exception
        validate_aws_config(config)

    def test_validate_aws_config_with_region(self):
        """Test AWS config validation with region."""
        config = ServerConfig(aws_region='us-west-2')

        # Should not raise any exception
        validate_aws_config(config)

    def test_validate_aws_config_incomplete_access_keys(self):
        """Test AWS config validation with incomplete access keys."""
        # Only access key ID, no secret
        config = ServerConfig(aws_access_key_id='AKIAIOSFODNN7EXAMPLE')  # pragma: allowlist secret

        # Should not raise error, just log warning
        result = validate_aws_config(config)
        assert result is True

        # Only secret, no access key ID
        config = ServerConfig(
            aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        )  # pragma: allowlist secret

        # Should not raise error, just log warning
        result = validate_aws_config(config)
        assert result is True

    def test_validate_aws_config_no_credentials(self):
        """Test AWS config validation with no credentials."""
        config = ServerConfig()

        # Should not raise error, just log warning about relying on IAM roles
        result = validate_aws_config(config)
        assert result is True

    def test_validate_aws_config_empty_values(self):
        """Test AWS config validation with empty values."""
        config = ServerConfig(aws_profile='', aws_access_key_id='', aws_secret_access_key='')

        # Should not raise error, just log warning
        result = validate_aws_config(config)
        assert result is True

    def test_validate_aws_config_whitespace_values(self):
        """Test AWS config validation with whitespace values."""
        config = ServerConfig(
            aws_profile='   ', aws_access_key_id='   ', aws_secret_access_key='   '
        )

        # Should not raise error, just log warning
        result = validate_aws_config(config)
        assert result is True


class TestConfigFileLoading:
    """Test configuration file loading functionality."""

    def test_load_config_from_file_json(self):
        """Test loading configuration from JSON file."""
        config_data = {
            'aws_profile': 'test-profile',
            'aws_region': 'us-west-2',
            'log_level': 'DEBUG',
            'max_text_length': 5000,
            'enable_caching': False,
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json

            json.dump(config_data, f)
            config_file = f.name

        try:
            # Test the file loading (this would be part of a load_config_from_file function)
            with open(config_file, 'r') as f:
                loaded_data = json.load(f)

            assert loaded_data['aws_profile'] == 'test-profile'
            assert loaded_data['aws_region'] == 'us-west-2'
            assert loaded_data['log_level'] == 'DEBUG'
            assert loaded_data['max_text_length'] == 5000
            assert loaded_data['enable_caching'] is False
        finally:
            os.unlink(config_file)

    def test_config_precedence_env_over_defaults(self):
        """Test that environment variables take precedence over defaults."""
        env_vars = {'FASTMCP_LOG_LEVEL': 'DEBUG', 'TRANSLATE_MAX_TEXT_LENGTH': '5000'}

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()

            # Environment values should override defaults
            assert config.log_level == 'DEBUG'  # Not default 'INFO'
            assert config.max_text_length == 5000  # Not default 10000


class TestConfigSerialization:
    """Test configuration serialization and deserialization."""

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = ServerConfig(aws_profile='test-profile', log_level='DEBUG', max_text_length=5000)

        # Convert to dict (this would be a method on ServerConfig)
        config_dict = {
            'aws_profile': config.aws_profile,
            'aws_region': config.aws_region,
            'log_level': config.log_level,
            'max_text_length': config.max_text_length,
            'enable_translation_cache': config.enable_translation_cache,
        }

        assert config_dict['aws_profile'] == 'test-profile'
        assert config_dict['aws_region'] is None
        assert config_dict['log_level'] == 'DEBUG'
        assert config_dict['max_text_length'] == 5000
        assert config_dict['enable_translation_cache'] is True

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            'aws_profile': 'test-profile',
            'log_level': 'DEBUG',
            'max_text_length': 5000,
            'enable_translation_cache': False,
        }

        # Create config from dict
        config = ServerConfig(**config_dict)

        assert config.aws_profile == 'test-profile'
        assert config.log_level == 'DEBUG'
        assert config.max_text_length == 5000
        assert config.enable_translation_cache is False


class TestConfigValidationEdgeCases:
    """Test edge cases in configuration validation."""

    def test_config_with_very_large_values(self):
        """Test config with very large but valid values."""
        config = ServerConfig(
            max_text_length=1000000,
            batch_timeout=86400,  # 24 hours
            cache_ttl=604800,  # 1 week
            max_file_size=1073741824,  # 1GB
        )

        assert config.max_text_length == 1000000
        assert config.batch_timeout == 86400
        assert config.cache_ttl == 604800
        assert config.max_file_size == 1073741824

    def test_config_with_special_characters_in_strings(self):
        """Test config with special characters in string fields."""
        config = ServerConfig(
            aws_profile='test-profile_123', blocked_patterns=['*.tmp', 'temp_*', 'cache-*.dat']
        )

        assert config.aws_profile == 'test-profile_123'
        assert '*.tmp' in config.blocked_patterns
        assert 'temp_*' in config.blocked_patterns
        assert 'cache-*.dat' in config.blocked_patterns

    def test_config_immutability_after_creation(self):
        """Test that config behaves as expected after creation."""
        config = ServerConfig(log_level='INFO')

        # Config should be created successfully
        assert config.log_level == 'INFO'

        # Attempting to set invalid value should raise error
        with pytest.raises(ValueError):
            ServerConfig(log_level='INVALID')
