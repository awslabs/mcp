"""Tests for configuration validation functionality."""

import pytest
from awslabs.amazon_translate_mcp_server.config import (
    ServerConfig,
    print_configuration_summary,
    validate_startup_configuration,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


class TestValidateStartupConfiguration:
    """Test the validate_startup_configuration function."""

    @patch('boto3.Session')
    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_success(
        self, mock_validate_aws, mock_load_config, mock_boto3_session
    ):
        """Test successful configuration validation."""
        # Setup mocks
        config = ServerConfig()
        config.aws_region = 'us-east-1'
        config.aws_profile = 'default'
        config.enable_translation_cache = True
        config.cache_ttl = 3600
        config.max_file_size = 10 * 1024 * 1024  # 10MB
        config.blocked_patterns = [r'\d{3}-\d{2}-\d{4}']  # SSN pattern

        mock_load_config.return_value = config

        # Mock AWS clients
        mock_session = Mock()
        mock_boto3_session.return_value = mock_session

        mock_translate_client = Mock()
        mock_translate_client.list_languages.return_value = {'Languages': [{'LanguageCode': 'en'}]}

        # Mock S3 client
        mock_s3_client = Mock()
        mock_s3_client.list_buckets.return_value = {'Buckets': []}

        mock_session.client.side_effect = lambda service: {
            'translate': mock_translate_client,
            's3': mock_s3_client,
        }[service]

        # Test
        result = validate_startup_configuration()

        # Assertions
        assert result == config
        mock_load_config.assert_called_once()
        mock_validate_aws.assert_called_once_with(config)
        mock_boto3_session.assert_called_once_with(profile_name='default', region_name='us-east-1')

    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    def test_validate_startup_configuration_load_config_failure(self, mock_load_config):
        """Test configuration validation when config loading fails."""
        mock_load_config.side_effect = ValueError('Invalid configuration')

        with pytest.raises(ValueError, match='Invalid configuration'):
            validate_startup_configuration()

    @patch('boto3.Session')
    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_translate_access_denied(
        self, mock_validate_aws, mock_load_config, mock_boto3_session
    ):
        """Test configuration validation when Translate access is denied."""
        config = ServerConfig()
        config.aws_region = 'us-east-1'
        mock_load_config.return_value = config

        # Mock AWS session and client
        mock_session = Mock()
        mock_boto3_session.return_value = mock_session

        mock_translate_client = Mock()
        mock_translate_client.list_languages.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='list_languages',
        )
        mock_session.client.return_value = mock_translate_client

        # Should not raise exception, just warn
        result = validate_startup_configuration()
        assert result == config

    @patch('boto3.Session')
    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_invalid_region(
        self, mock_validate_aws, mock_load_config, mock_boto3_session
    ):
        """Test configuration validation with invalid region."""
        config = ServerConfig()
        config.aws_region = 'invalid-region'
        mock_load_config.return_value = config

        # Mock AWS session and client
        mock_session = Mock()
        mock_boto3_session.return_value = mock_session

        mock_translate_client = Mock()
        mock_translate_client.list_languages.side_effect = ClientError(
            error_response={'Error': {'Code': 'InvalidRegion', 'Message': 'Invalid region'}},
            operation_name='list_languages',
        )
        mock_session.client.return_value = mock_translate_client

        # Should not raise exception, just warn
        result = validate_startup_configuration()
        assert result == config

    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_invalid_cache_config(
        self, mock_validate_aws, mock_load_config
    ):
        """Test configuration validation with invalid cache configuration."""
        config = ServerConfig()
        config.enable_translation_cache = True
        config.cache_ttl = -1  # Invalid negative TTL
        mock_load_config.return_value = config

        with pytest.raises(ValueError, match='Cache TTL must be positive when caching is enabled'):
            validate_startup_configuration()

    @patch('awslabs.amazon_translate_mcp_server.config.load_config_from_env')
    @patch('awslabs.amazon_translate_mcp_server.config.validate_aws_config')
    def test_validate_startup_configuration_invalid_regex_pattern(
        self, mock_validate_aws, mock_load_config
    ):
        """Test configuration validation with invalid regex pattern."""
        config = ServerConfig()
        config.blocked_patterns = ['[invalid regex']  # Invalid regex
        mock_load_config.return_value = config

        with pytest.raises(ValueError, match='Invalid regex pattern'):
            validate_startup_configuration()


class TestPrintConfigurationSummary:
    """Test the print_configuration_summary function."""

    def test_print_configuration_summary_basic(self, capsys):
        """Test printing basic configuration summary."""
        config = ServerConfig()
        config.aws_region = 'us-west-2'
        config.aws_profile = 'test-profile'
        config.log_level = 'DEBUG'
        config.enable_translation_cache = True

        config.enable_audit_logging = True
        config.max_text_length = 10000
        config.max_file_size = 5 * 1024 * 1024  # 5MB
        config.batch_timeout = 3600
        config.cache_ttl = 1800
        config.allowed_file_extensions = {'.txt', '.docx', '.pdf'}
        config.blocked_patterns = ['pattern1', 'pattern2']

        print_configuration_summary(config)

        captured = capsys.readouterr()
        output = captured.out

        # Check that key information is present
        assert 'Amazon Translate MCP Server Configuration Summary' in output
        assert 'AWS Region: us-west-2' in output
        assert 'AWS Profile: test-profile' in output
        assert 'Log Level: DEBUG' in output
        assert 'Translation Cache: Enabled' in output

        assert 'Audit Logging: Enabled' in output
        assert 'Max Text Length: 10,000 characters' in output
        assert 'Max File Size: 5,242,880 bytes (5.0 MB)' in output
        assert 'Batch Timeout: 3600 seconds' in output
        assert 'Cache TTL: 1800 seconds' in output
        assert '.docx, .pdf, .txt' in output  # Should be sorted
        assert 'Blocked Patterns: 2 configured' in output

    def test_print_configuration_summary_default_profile(self, capsys):
        """Test printing configuration summary with default profile."""
        config = ServerConfig()
        config.aws_profile = None  # Default profile

        print_configuration_summary(config)

        captured = capsys.readouterr()
        output = captured.out

        assert 'AWS Profile: Default' in output

    def test_print_configuration_summary_no_blocked_patterns(self, capsys):
        """Test printing configuration summary without blocked patterns."""
        config = ServerConfig()
        config.blocked_patterns = []

        print_configuration_summary(config)

        captured = capsys.readouterr()
        output = captured.out

        # Should not mention blocked patterns if none are configured
        assert 'Blocked Patterns:' not in output
