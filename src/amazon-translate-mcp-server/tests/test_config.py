"""Unit tests for configuration management.

This module tests configuration loading, validation, and environment
variable parsing for the Amazon Translate MCP Server.
"""

import logging
import os
import pytest
from awslabs.amazon_translate_mcp_server.config import (
    ServerConfig,
    get_config,
    load_config_from_env,
    reset_config,
    set_config,
    setup_logging,
    validate_aws_config,
)
from awslabs.amazon_translate_mcp_server.security import SecurityConfig
from unittest.mock import Mock, patch


class TestServerConfig:
    """Test server configuration."""

    def test_default_config(self):
        """Test default server configuration."""
        config = ServerConfig()

        assert config.aws_profile is None
        assert config.aws_region is None
        assert config.log_level == 'INFO'
        assert config.max_text_length == 10000
        assert config.batch_timeout == 3600
        assert config.enable_pii_detection is False
        assert config.enable_profanity_filter is False
        assert config.enable_audit_logging is True
        assert config.cache_ttl == 3600
        assert config.max_file_size == 10 * 1024 * 1024
        assert '.csv' in config.allowed_file_extensions

    def test_custom_config(self):
        """Test custom server configuration."""
        config = ServerConfig(
            aws_profile='test-profile',
            aws_region='us-west-2',
            log_level='DEBUG',
            max_text_length=5000,
            enable_pii_detection=True,
            enable_profanity_filter=True,
            cache_ttl=1800,
            blocked_patterns=['secret', 'confidential'],
        )

        assert config.aws_profile == 'test-profile'
        assert config.aws_region == 'us-west-2'
        assert config.log_level == 'DEBUG'
        assert config.max_text_length == 5000
        assert config.enable_pii_detection is True
        assert config.enable_profanity_filter is True
        assert config.cache_ttl == 1800
        assert 'secret' in config.blocked_patterns

    def test_invalid_config(self):
        """Test invalid server configuration."""
        with pytest.raises(ValueError, match='Invalid log_level'):
            ServerConfig(log_level='INVALID')

        with pytest.raises(ValueError, match='max_text_length must be positive'):
            ServerConfig(max_text_length=0)

        with pytest.raises(ValueError, match='batch_timeout must be positive'):
            ServerConfig(batch_timeout=-1)

        with pytest.raises(ValueError, match='cache_ttl cannot be negative'):
            ServerConfig(cache_ttl=-1)

        with pytest.raises(ValueError, match='max_file_size must be positive'):
            ServerConfig(max_file_size=0)

    def test_to_security_config(self):
        """Test conversion to SecurityConfig."""
        config = ServerConfig(
            enable_pii_detection=True,
            enable_profanity_filter=True,
            enable_content_filtering=True,
            max_text_length=5000,
            max_file_size=1024,
            blocked_patterns=['test'],
        )

        security_config = config.to_security_config()

        assert isinstance(security_config, SecurityConfig)
        assert security_config.enable_pii_detection is True
        assert security_config.enable_profanity_filter is True
        assert security_config.enable_content_filtering is True
        assert security_config.max_text_length == 5000
        assert security_config.max_file_size == 1024
        assert 'test' in security_config.blocked_patterns


class TestConfigLoading:
    """Test configuration loading from environment."""

    def test_load_config_defaults(self):
        """Test loading config with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config_from_env()

            assert config.aws_profile is None
            assert config.aws_region is None
            assert config.log_level == 'INFO'
            assert config.max_text_length == 10000
            assert config.enable_pii_detection is False
            assert config.enable_audit_logging is True

    def test_load_config_from_env_vars(self):
        """Test loading config from environment variables."""
        env_vars = {
            'AWS_PROFILE': 'test-profile',
            'AWS_REGION': 'eu-west-1',
            'FASTMCP_LOG_LEVEL': 'debug',
            'TRANSLATE_MAX_TEXT_LENGTH': '5000',
            'TRANSLATE_BATCH_TIMEOUT': '1800',
            'ENABLE_PII_DETECTION': 'true',
            'ENABLE_PROFANITY_FILTER': '1',
            'ENABLE_CONTENT_FILTERING': 'yes',
            'ENABLE_AUDIT_LOGGING': 'false',
            'ENABLE_TRANSLATION_CACHE': 'no',
            'TRANSLATE_CACHE_TTL': '7200',
            'TRANSLATE_MAX_FILE_SIZE': '5242880',
            'TRANSLATE_ALLOWED_EXTENSIONS': '.csv,.tmx,.xml',
            'TRANSLATE_BLOCKED_PATTERNS': 'secret,confidential,private',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()

            assert config.aws_profile == 'test-profile'
            assert config.aws_region == 'eu-west-1'
            assert config.log_level == 'DEBUG'
            assert config.max_text_length == 5000
            assert config.batch_timeout == 1800
            assert config.enable_pii_detection is True
            assert config.enable_profanity_filter is True
            assert config.enable_content_filtering is True
            assert config.enable_audit_logging is False
            assert config.enable_translation_cache is False
            assert config.cache_ttl == 7200
            assert config.max_file_size == 5242880
            assert '.xml' in config.allowed_file_extensions
            assert 'secret' in config.blocked_patterns

    def test_load_config_aws_default_region(self):
        """Test loading AWS region from AWS_DEFAULT_REGION."""
        env_vars = {'AWS_DEFAULT_REGION': 'ap-southeast-1'}

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()
            assert config.aws_region == 'ap-southeast-1'

    def test_load_config_invalid_values(self):
        """Test loading config with invalid environment values."""
        env_vars = {'TRANSLATE_MAX_TEXT_LENGTH': 'invalid', 'TRANSLATE_CACHE_TTL': 'not-a-number'}

        with patch.dict(os.environ, env_vars, clear=True):
            with patch(
                'awslabs.amazon_translate_mcp_server.config.logging.warning'
            ) as mock_warning:
                config = load_config_from_env()

                # Should use defaults for invalid values
                assert config.max_text_length == 10000
                assert config.cache_ttl == 3600

                # Should log warnings
                assert mock_warning.call_count == 2

    def test_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        true_values = ['true', '1', 'yes', 'on', 'TRUE', 'Yes', 'ON']
        false_values = ['false', '0', 'no', 'off', 'FALSE', 'No', 'OFF', '']

        for true_val in true_values:
            with patch.dict(os.environ, {'ENABLE_PII_DETECTION': true_val}, clear=True):
                config = load_config_from_env()
                assert config.enable_pii_detection is True, f'Failed for value: {true_val}'

        for false_val in false_values:
            with patch.dict(os.environ, {'ENABLE_PII_DETECTION': false_val}, clear=True):
                config = load_config_from_env()
                assert config.enable_pii_detection is False, f'Failed for value: {false_val}'


class TestLoggingSetup:
    """Test logging configuration."""

    def test_setup_logging_info(self):
        """Test logging setup with INFO level."""
        config = ServerConfig(log_level='INFO')

        with patch('awslabs.amazon_translate_mcp_server.config.logging.basicConfig') as mock_basic:
            with patch(
                'awslabs.amazon_translate_mcp_server.config.logging.getLogger'
            ) as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                setup_logging(config)

                mock_basic.assert_called_once()
                call_kwargs = mock_basic.call_args[1]
                assert call_kwargs['level'] == logging.INFO

    def test_setup_logging_debug(self):
        """Test logging setup with DEBUG level."""
        config = ServerConfig(log_level='DEBUG')

        with patch('awslabs.amazon_translate_mcp_server.config.logging.basicConfig') as mock_basic:
            with patch(
                'awslabs.amazon_translate_mcp_server.config.logging.getLogger'
            ) as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                setup_logging(config)

                mock_basic.assert_called_once()
                call_kwargs = mock_basic.call_args[1]
                assert call_kwargs['level'] == logging.DEBUG

    def test_setup_logging_audit_enabled(self):
        """Test logging setup with audit logging enabled."""
        config = ServerConfig(enable_audit_logging=True)

        with patch('awslabs.amazon_translate_mcp_server.config.logging.basicConfig'):
            with patch(
                'awslabs.amazon_translate_mcp_server.config.logging.getLogger'
            ) as mock_get_logger:
                mock_audit_logger = Mock()
                mock_main_logger = Mock()

                def get_logger_side_effect(name):
                    if name == 'audit':
                        return mock_audit_logger
                    return mock_main_logger

                mock_get_logger.side_effect = get_logger_side_effect

                setup_logging(config)

                mock_audit_logger.setLevel.assert_called_with(logging.INFO)

    def test_setup_logging_audit_disabled(self):
        """Test logging setup with audit logging disabled."""
        config = ServerConfig(enable_audit_logging=False)

        with patch('awslabs.amazon_translate_mcp_server.config.logging.basicConfig'):
            with patch(
                'awslabs.amazon_translate_mcp_server.config.logging.getLogger'
            ) as mock_get_logger:
                mock_audit_logger = Mock()
                mock_main_logger = Mock()

                def get_logger_side_effect(name):
                    if name == 'audit':
                        return mock_audit_logger
                    return mock_main_logger

                mock_get_logger.side_effect = get_logger_side_effect

                setup_logging(config)

                mock_audit_logger.setLevel.assert_called_with(logging.CRITICAL)


class TestAWSConfigValidation:
    """Test AWS configuration validation."""

    def test_validate_aws_config_with_explicit_creds(self):
        """Test validation with explicit credentials."""
        config = ServerConfig(
            aws_access_key_id='AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
            aws_region='us-east-1',
        )

        result = validate_aws_config(config)
        assert result is True
        assert config.aws_region == 'us-east-1'

    def test_validate_aws_config_with_profile(self):
        """Test validation with AWS profile."""
        config = ServerConfig(aws_profile='test-profile', aws_region='eu-west-1')

        result = validate_aws_config(config)
        assert result is True
        assert config.aws_region == 'eu-west-1'

    def test_validate_aws_config_with_env_creds(self):
        """Test validation with environment credentials."""
        config = ServerConfig()

        env_vars = {
            'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
            'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
        }

        with patch.dict(os.environ, env_vars):
            result = validate_aws_config(config)
            assert result is True

    def test_validate_aws_config_no_creds(self):
        """Test validation with no explicit credentials."""
        config = ServerConfig()

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                'awslabs.amazon_translate_mcp_server.config.logging.warning'
            ) as mock_warning:
                result = validate_aws_config(config)

                assert result is True
                mock_warning.assert_called_once()
                assert 'No explicit AWS credentials found' in mock_warning.call_args[0][0]

    def test_validate_aws_config_no_region(self):
        """Test validation with no region specified."""
        config = ServerConfig(aws_region=None)

        with patch('awslabs.amazon_translate_mcp_server.config.logging.info') as mock_info:
            result = validate_aws_config(config)

            assert result is True
            assert config.aws_region == 'us-east-1'
            mock_info.assert_called_once()
            assert 'using default' in mock_info.call_args[0][0]


class TestGlobalConfig:
    """Test global configuration management."""

    def teardown_method(self):
        """Reset global config after each test."""
        reset_config()

    def test_get_config_first_time(self):
        """Test getting config for the first time."""
        with patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env') as mock_load:
            with patch(
                'awslabs.amazon_translate_mcp_server.config.validate_aws_config'
            ) as mock_validate:
                with patch(
                    'awslabs.amazon_translate_mcp_server.config.setup_logging'
                ) as mock_setup:
                    mock_config = ServerConfig()
                    mock_load.return_value = mock_config
                    mock_validate.return_value = True

                    config = get_config()

                    assert config is mock_config
                    mock_load.assert_called_once()
                    mock_validate.assert_called_once_with(mock_config)
                    mock_setup.assert_called_once_with(mock_config)

    def test_get_config_cached(self):
        """Test getting cached config."""
        test_config = ServerConfig(log_level='DEBUG')
        set_config(test_config)

        with patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env') as mock_load:
            config = get_config()

            assert config is test_config
            mock_load.assert_not_called()

    def test_set_config(self):
        """Test setting global config."""
        test_config = ServerConfig(log_level='DEBUG')

        with patch('awslabs.amazon_translate_mcp_server.config.setup_logging') as mock_setup:
            set_config(test_config)

            config = get_config()
            assert config is test_config
            mock_setup.assert_called_once_with(test_config)

    def test_reset_config(self):
        """Test resetting global config."""
        test_config = ServerConfig(log_level='DEBUG')
        set_config(test_config)

        # Verify config is set
        config = get_config()
        assert config is test_config

        # Reset and verify it's cleared
        reset_config()

        with patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env') as mock_load:
            with patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config'):
                with patch('awslabs.amazon_translate_mcp_server.config.setup_logging'):
                    mock_load.return_value = ServerConfig()

                    new_config = get_config()

                    assert new_config is not test_config
                    mock_load.assert_called_once()


class TestConfigIntegration:
    """Test configuration integration scenarios."""

    def teardown_method(self):
        """Reset global config after each test."""
        reset_config()

    def test_full_config_workflow(self):
        """Test complete configuration workflow."""
        env_vars = {
            'AWS_PROFILE': 'production',
            'AWS_REGION': 'us-west-2',
            'FASTMCP_LOG_LEVEL': 'INFO',
            'ENABLE_PII_DETECTION': 'true',
            'ENABLE_AUDIT_LOGGING': 'true',
            'TRANSLATE_MAX_TEXT_LENGTH': '8000',
            'TRANSLATE_BLOCKED_PATTERNS': 'secret,confidential',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('awslabs.amazon_translate_mcp_server.config.logging.basicConfig'):
                with patch(
                    'awslabs.amazon_translate_mcp_server.config.logging.getLogger'
                ) as mock_get_logger:
                    mock_logger = Mock()
                    mock_get_logger.return_value = mock_logger

                    config = get_config()

                    # Verify configuration loaded correctly
                    assert config.aws_profile == 'production'
                    assert config.aws_region == 'us-west-2'
                    assert config.log_level == 'INFO'
                    assert config.enable_pii_detection is True
                    assert config.enable_audit_logging is True
                    assert config.max_text_length == 8000
                    assert 'secret' in config.blocked_patterns

                    # Verify security config conversion
                    security_config = config.to_security_config()
                    assert security_config.enable_pii_detection is True
                    assert security_config.max_text_length == 8000
                    assert 'confidential' in security_config.blocked_patterns

    def test_config_error_handling(self):
        """Test configuration error handling."""
        # Test with invalid log level in environment
        env_vars = {'FASTMCP_LOG_LEVEL': 'INVALID_LEVEL'}

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match='Invalid log_level'):
                get_config()

    def test_config_with_security_features(self):
        """Test configuration with all security features enabled."""
        env_vars = {
            'ENABLE_PII_DETECTION': 'true',
            'ENABLE_PROFANITY_FILTER': 'true',
            'ENABLE_CONTENT_FILTERING': 'true',
            'ENABLE_AUDIT_LOGGING': 'true',
            'TRANSLATE_BLOCKED_PATTERNS': 'secret,confidential,private,internal',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('awslabs.amazon_translate_mcp_server.config.logging.basicConfig'):
                with patch(
                    'awslabs.amazon_translate_mcp_server.config.logging.getLogger'
                ) as mock_get_logger:
                    mock_logger = Mock()
                    mock_get_logger.return_value = mock_logger

                    config = get_config()

                    assert config.enable_pii_detection is True
                    assert config.enable_profanity_filter is True
                    assert config.enable_content_filtering is True
                    assert config.enable_audit_logging is True
                    assert len(config.blocked_patterns) == 4

                    # Test security config conversion
                    security_config = config.to_security_config()
                    assert security_config.enable_pii_detection is True
                    assert security_config.enable_profanity_filter is True
                    assert security_config.enable_content_filtering is True
                    assert security_config.enable_audit_logging is True
