"""Tests for AWS session creation in the lambda-tool MCP server."""

import os
import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.lambda_tool_mcp_server.server import create_boto3_session


def _env_without_profile(**updates):
    """Copy the environment, drop AWS_PROFILE, and apply optional updates."""
    env = {key: value for key, value in os.environ.items() if key != 'AWS_PROFILE'}
    env.update(updates)
    return env


@patch('awslabs.lambda_tool_mcp_server.server.boto3.Session')
def test_create_boto3_session_uses_named_profile(mock_session):
    """Honor AWS_PROFILE when it is set."""
    with patch.dict(os.environ, _env_without_profile(AWS_PROFILE='my-profile'), clear=True):
        create_boto3_session('us-west-2')

    mock_session.assert_called_once_with(profile_name='my-profile', region_name='us-west-2')


@patch('awslabs.lambda_tool_mcp_server.server.boto3.Session')
def test_create_boto3_session_without_profile(mock_session):
    """Use the default credential chain when AWS_PROFILE is not set."""
    with patch.dict(os.environ, _env_without_profile(), clear=True):
        create_boto3_session('us-east-1')

    mock_session.assert_called_once_with(region_name='us-east-1')


@patch('awslabs.lambda_tool_mcp_server.server.boto3.Session')
def test_create_boto3_session_ignores_empty_profile(mock_session):
    """Treat an empty AWS_PROFILE as unset so env/OIDC/container creds still work."""
    with patch.dict(os.environ, _env_without_profile(AWS_PROFILE=''), clear=True):
        create_boto3_session('eu-west-1')

    mock_session.assert_called_once_with(region_name='eu-west-1')
