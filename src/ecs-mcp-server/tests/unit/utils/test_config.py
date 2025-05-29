"""
Unit tests for the configuration module.
"""

import unittest
from unittest.mock import patch

from awslabs.ecs_mcp_server.utils.config import get_config


class TestConfig(unittest.TestCase):
    """Test cases for the configuration module."""

    @patch("os.environ")
    def test_get_config_defaults(self, mock_environ):
        """Test that default configuration values are set correctly."""
        # Set up mock environment with no security flags
        mock_environ.get.side_effect = lambda key, default=None: {
            "AWS_REGION": "us-west-2",
            "AWS_PROFILE": "test-profile",
            "FASTMCP_LOG_LEVEL": "DEBUG",
            "ALLOW_WRITE": "",
            "ALLOW_SENSITIVE_DATA": "",
        }.get(key, default)

        config = get_config()

        # Check default values
        self.assertEqual(config["aws_region"], "us-west-2")
        self.assertEqual(config["aws_profile"], "test-profile")
        self.assertEqual(config["log_level"], "DEBUG")
        self.assertFalse(config["allow-write"])
        self.assertFalse(config["allow-sensitive-data"])

    @patch("os.environ")
    def test_get_config_with_security_flags_enabled(self, mock_environ):
        """Test that security flags are properly parsed when enabled."""
        # Set up mock environment with security flags enabled
        mock_environ.get.side_effect = lambda key, default=None: {
            "AWS_REGION": "us-east-1",
            "AWS_PROFILE": "prod-profile",
            "FASTMCP_LOG_LEVEL": "INFO",
            "ALLOW_WRITE": "true",
            "ALLOW_SENSITIVE_DATA": "true",
        }.get(key, default)

        config = get_config()

        # Check that flags are enabled
        self.assertTrue(config["allow-write"])
        self.assertTrue(config["allow-sensitive-data"])

    @patch("os.environ")
    def test_get_config_with_security_flags_disabled(self, mock_environ):
        """Test that security flags are properly parsed when explicitly disabled."""
        # Set up mock environment with security flags disabled
        mock_environ.get.side_effect = lambda key, default=None: {
            "AWS_REGION": "eu-west-1",
            "AWS_PROFILE": "dev-profile",
            "FASTMCP_LOG_LEVEL": "WARNING",
            "ALLOW_WRITE": "false",
            "ALLOW_SENSITIVE_DATA": "false",
        }.get(key, default)

        config = get_config()

        # Check that flags are disabled
        self.assertFalse(config["allow-write"])
        self.assertFalse(config["allow-sensitive-data"])

    @patch("os.environ")
    def test_get_config_with_alternative_true_values(self, mock_environ):
        """Test that alternative true values are properly parsed."""
        # Set up mock environment with alternative true values
        mock_environ.get.side_effect = lambda key, default=None: {
            "AWS_REGION": "ap-southeast-1",
            "AWS_PROFILE": "alt-profile",
            "FASTMCP_LOG_LEVEL": "ERROR",
            "ALLOW_WRITE": "1",
            "ALLOW_SENSITIVE_DATA": "yes",
        }.get(key, default)

        config = get_config()

        # Check that flags are enabled
        self.assertTrue(config["allow-write"])
        self.assertTrue(config["allow-sensitive-data"])


if __name__ == "__main__":
    unittest.main()
