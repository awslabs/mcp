"""Tests for CloudWatch configuration in config module."""

import os
from unittest.mock import patch


def test_cloudwatch_log_group_name_not_set():
    """Test when EXPERIMENTAL_AWS_API_MCP_LOG_GROUP is not set."""
    with patch.dict(os.environ, {}, clear=True):
        # Reload the config module to get fresh environment variables
        import awslabs.aws_api_mcp_server.core.common.config as config_module
        import importlib

        importlib.reload(config_module)

        assert config_module.CLOUDWATCH_LOG_GROUP_NAME is None


def test_cloudwatch_log_group_name_set():
    """Test when EXPERIMENTAL_AWS_API_MCP_LOG_GROUP is set."""
    test_log_group = '/aws/mcp/aws-api-mcp-server'

    with patch.dict(
        os.environ, {'EXPERIMENTAL_AWS_API_MCP_LOG_GROUP': test_log_group}, clear=True
    ):
        # Reload the config module to get fresh environment variables
        import awslabs.aws_api_mcp_server.core.common.config as config_module
        import importlib

        importlib.reload(config_module)

        assert config_module.CLOUDWATCH_LOG_GROUP_NAME == test_log_group


def test_cloudwatch_log_group_name_empty_string():
    """Test when EXPERIMENTAL_AWS_API_MCP_LOG_GROUP is set to empty string."""
    with patch.dict(os.environ, {'EXPERIMENTAL_AWS_API_MCP_LOG_GROUP': ''}, clear=True):
        # Reload the config module to get fresh environment variables
        import awslabs.aws_api_mcp_server.core.common.config as config_module
        import importlib

        importlib.reload(config_module)

        assert config_module.CLOUDWATCH_LOG_GROUP_NAME == ''


def test_cloudwatch_log_group_name_special_characters():
    """Test when EXPERIMENTAL_AWS_API_MCP_LOG_GROUP contains special characters."""
    test_log_group = '/aws/mcp/test-group-with-dashes_and_underscores'

    with patch.dict(
        os.environ, {'EXPERIMENTAL_AWS_API_MCP_LOG_GROUP': test_log_group}, clear=True
    ):
        # Reload the config module to get fresh environment variables
        import awslabs.aws_api_mcp_server.core.common.config as config_module
        import importlib

        importlib.reload(config_module)

        assert config_module.CLOUDWATCH_LOG_GROUP_NAME == test_log_group


def test_cloudwatch_log_group_name_very_long():
    """Test when EXPERIMENTAL_AWS_API_MCP_LOG_GROUP is very long."""
    test_log_group = '/aws/mcp/' + 'a' * 200  # Very long log group name

    with patch.dict(
        os.environ, {'EXPERIMENTAL_AWS_API_MCP_LOG_GROUP': test_log_group}, clear=True
    ):
        # Reload the config module to get fresh environment variables
        import awslabs.aws_api_mcp_server.core.common.config as config_module
        import importlib

        importlib.reload(config_module)

        assert config_module.CLOUDWATCH_LOG_GROUP_NAME == test_log_group


def test_cloudwatch_log_group_name_with_unicode():
    """Test when EXPERIMENTAL_AWS_API_MCP_LOG_GROUP contains unicode characters."""
    test_log_group = '/aws/mcp/test-group-🚀-with-emoji'

    with patch.dict(
        os.environ, {'EXPERIMENTAL_AWS_API_MCP_LOG_GROUP': test_log_group}, clear=True
    ):
        # Reload the config module to get fresh environment variables
        import awslabs.aws_api_mcp_server.core.common.config as config_module
        import importlib

        importlib.reload(config_module)

        assert config_module.CLOUDWATCH_LOG_GROUP_NAME == test_log_group


def test_cloudwatch_log_group_name_case_sensitive():
    """Test that EXPERIMENTAL_AWS_API_MCP_LOG_GROUP is case sensitive."""
    test_log_group = '/AWS/MCP/TEST-GROUP'

    with patch.dict(
        os.environ, {'EXPERIMENTAL_AWS_API_MCP_LOG_GROUP': test_log_group}, clear=True
    ):
        # Reload the config module to get fresh environment variables
        import awslabs.aws_api_mcp_server.core.common.config as config_module
        import importlib

        importlib.reload(config_module)

        assert config_module.CLOUDWATCH_LOG_GROUP_NAME == test_log_group


def test_cloudwatch_log_group_name_with_numbers():
    """Test when EXPERIMENTAL_AWS_API_MCP_LOG_GROUP contains numbers."""
    test_log_group = '/aws/mcp/test-group-123'

    with patch.dict(
        os.environ, {'EXPERIMENTAL_AWS_API_MCP_LOG_GROUP': test_log_group}, clear=True
    ):
        # Reload the config module to get fresh environment variables
        import awslabs.aws_api_mcp_server.core.common.config as config_module
        import importlib

        importlib.reload(config_module)

        assert config_module.CLOUDWATCH_LOG_GROUP_NAME == test_log_group


def test_cloudwatch_log_group_name_multiple_slashes():
    """Test when EXPERIMENTAL_AWS_API_MCP_LOG_GROUP contains multiple slashes."""
    test_log_group = '/aws/mcp/deeply/nested/log/group'

    with patch.dict(
        os.environ, {'EXPERIMENTAL_AWS_API_MCP_LOG_GROUP': test_log_group}, clear=True
    ):
        # Reload the config module to get fresh environment variables
        import awslabs.aws_api_mcp_server.core.common.config as config_module
        import importlib

        importlib.reload(config_module)

        assert config_module.CLOUDWATCH_LOG_GROUP_NAME == test_log_group
