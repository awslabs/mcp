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

"""Tests for the AWS AppSync MCP Server helpers."""

import os
import pytest
from awslabs.aws_appsync_mcp_server.helpers import (
    get_appsync_client,
    handle_exceptions,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


def test_get_appsync_client_default():
    """Test get_appsync_client with default settings."""
    with patch('boto3.Session') as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        client = get_appsync_client()

        mock_session.assert_called_once_with(profile_name=None, region_name='us-east-1')
        # Verify client is called with appsync and config parameter
        args, kwargs = mock_session.return_value.client.call_args
        assert args[0] == 'appsync'
        assert 'config' in kwargs
        assert client == mock_client


def test_get_appsync_client_with_profile():
    """Test get_appsync_client with AWS_PROFILE and AWS_REGION set."""
    with patch('boto3.Session') as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile', 'AWS_REGION': 'us-west-2'}):
            client = get_appsync_client()

            mock_session.assert_called_once_with(
                profile_name='test-profile', region_name='us-west-2'
            )
            # Verify client is called with appsync and config parameter
            args, kwargs = mock_session.return_value.client.call_args
            assert args[0] == 'appsync'
            assert 'config' in kwargs
            assert client == mock_client


def test_get_appsync_client_exception():
    """Test get_appsync_client when boto3 raises an exception."""
    with patch('boto3.Session', side_effect=Exception('AWS error')):
        with pytest.raises(Exception, match='AWS error'):
            get_appsync_client()


@pytest.mark.asyncio
async def test_handle_exceptions_decorator_success():
    """Test handle_exceptions decorator with successful function."""

    @handle_exceptions
    async def test_func():
        return 'success'

    result = await test_func()
    assert result == 'success'


@pytest.mark.asyncio
async def test_handle_exceptions_decorator_client_error():
    """Test handle_exceptions decorator with ClientError."""

    @handle_exceptions
    async def error_func():
        raise ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid API name'}
            },
            operation_name='CreateApi',
        )

    with pytest.raises(Exception, match='AppSync API error: Invalid API name'):
        await error_func()


@pytest.mark.asyncio
async def test_handle_exceptions_decorator_generic_error():
    """Test handle_exceptions decorator with generic exception."""

    @handle_exceptions
    async def error_func():
        raise RuntimeError('Test error')

    with pytest.raises(RuntimeError, match='Test error'):
        await error_func()


def test_get_appsync_client_config_user_agent():
    """Test that get_appsync_client creates config with correct user agent."""
    with (
        patch('boto3.Session') as mock_session,
        patch('awslabs.aws_appsync_mcp_server.__version__', '1.0.0'),
    ):
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        get_appsync_client()

        # Verify config parameter contains user agent
        args, kwargs = mock_session.return_value.client.call_args
        config = kwargs['config']
        assert hasattr(config, 'user_agent_extra')
        assert 'awslabs/mcp/aws-appsync-mcp-server/1.0.0' in config.user_agent_extra


def test_get_appsync_client_no_env_vars():
    """Test get_appsync_client with no environment variables set."""
    with patch('boto3.Session') as mock_session, patch.dict(os.environ, {}, clear=True):
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        client = get_appsync_client()

        mock_session.assert_called_once_with(profile_name=None, region_name='us-east-1')
        assert client == mock_client
