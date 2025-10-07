"""Tests for config.py module."""

import pytest
from awslabs.aws_dms_mcp_server.config import DMSServerConfig
from pydantic import ValidationError


class TestDMSServerConfig:
    """Test DMSServerConfig model."""

    def test_default_config(self):
        """Test config with defaults."""
        config = DMSServerConfig()
        assert config.aws_region == 'us-east-1'
        assert config.read_only_mode is False
        assert config.log_level == 'INFO'

    def test_custom_config(self):
        """Test config with custom values."""
        config = DMSServerConfig(aws_region='us-west-2', read_only_mode=True, log_level='DEBUG')
        assert config.aws_region == 'us-west-2'
        assert config.read_only_mode is True
        assert config.log_level == 'DEBUG'

    def test_invalid_region(self):
        """Test validation error for invalid region."""
        with pytest.raises(ValidationError):
            DMSServerConfig(aws_region='invalid-region')

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeout
        config = DMSServerConfig(default_timeout=300)
        assert config.default_timeout == 300

        # TODO: Test invalid timeout (< 30 or > 3600)


# TODO: Add tests for environment variable loading
# TODO: Add tests for all configuration fields
# TODO: Add tests for field validators
