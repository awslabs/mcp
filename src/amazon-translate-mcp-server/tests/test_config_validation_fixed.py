"""Tests for configuration validation functionality."""

from awslabs.amazon_translate_mcp_server.config import (
    ServerConfig,
    print_configuration_summary,
)


class TestPrintConfigurationSummary:
    """Test the print_configuration_summary function."""

    def test_print_configuration_summary_basic(self, capsys):
        """Test printing basic configuration summary."""
        config = ServerConfig()
        config.aws_region = 'us-west-2'
        config.aws_profile = 'test-profile'
        config.log_level = 'DEBUG'
        config.enable_translation_cache = True
        config.enable_pii_detection = False
        config.enable_profanity_filter = True
        config.enable_content_filtering = False
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
        assert 'PII Detection: Disabled' in output
        assert 'Profanity Filter: Enabled' in output
        assert 'Content Filtering: Disabled' in output
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


class TestServerConfigEdgeCases:
    """Test ServerConfig edge cases and validation."""

    def test_server_config_to_security_config(self):
        """Test ServerConfig to SecurityConfig conversion."""
        config = ServerConfig()
        config.enable_pii_detection = True
        config.enable_profanity_filter = True
        config.enable_content_filtering = True
        config.enable_audit_logging = False

        security_config = config.to_security_config()

        assert security_config.enable_pii_detection is True
        assert security_config.enable_profanity_filter is True
        assert security_config.enable_content_filtering is True
        assert security_config.enable_audit_logging is False

    def test_server_config_defaults(self):
        """Test ServerConfig default values."""
        config = ServerConfig()

        # Test that defaults are set properly
        assert config.log_level == 'INFO'
        assert config.max_text_length == 10000
        assert config.batch_timeout == 3600
        assert config.cache_ttl == 3600
        assert config.enable_translation_cache is True
        assert config.enable_pii_detection is False
        assert config.enable_profanity_filter is False
        assert config.enable_content_filtering is False
        assert config.enable_audit_logging is True

    def test_server_config_custom_values(self):
        """Test ServerConfig with custom values."""
        config = ServerConfig()
        config.aws_region = 'eu-west-1'
        config.aws_profile = 'production'
        config.log_level = 'DEBUG'
        config.max_text_length = 50000
        config.enable_pii_detection = True

        assert config.aws_region == 'eu-west-1'
        assert config.aws_profile == 'production'
        assert config.log_level == 'DEBUG'
        assert config.max_text_length == 50000
        assert config.enable_pii_detection is True

    def test_server_config_file_extensions(self):
        """Test ServerConfig file extensions handling."""
        config = ServerConfig()

        # Default extensions should be present
        assert '.txt' in config.allowed_file_extensions
        assert '.csv' in config.allowed_file_extensions
        assert '.tmx' in config.allowed_file_extensions

    def test_server_config_blocked_patterns(self):
        """Test ServerConfig blocked patterns handling."""
        config = ServerConfig()
        config.blocked_patterns = [r'\d{3}-\d{2}-\d{4}', r'[A-Z]{2}\d{6}']

        assert len(config.blocked_patterns) == 2
        assert r'\d{3}-\d{2}-\d{4}' in config.blocked_patterns
