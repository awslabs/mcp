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

"""Unit tests for helper functions."""

import pytest
from awslabs.aws_appsync_mcp_server.helpers import (
    _sanitize_error_message,
    get_appsync_client,
    handle_exceptions,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


class TestSanitizeErrorMessage:
    """Test error message sanitization."""

    def test_sanitize_account_id(self):
        """Test account ID sanitization."""
        message = 'Access denied for account 123456789012'
        result = _sanitize_error_message(message)
        assert result == 'Access denied for account [ACCOUNT-ID]'

    def test_sanitize_arn(self):
        """Test ARN sanitization."""
        message = 'Resource arn:aws:appsync:us-east-1:123456789012:apis/abc123 not found'
        result = _sanitize_error_message(message)
        assert result == 'Resource [ARN] not found'

    def test_sanitize_access_key(self):
        """Test access key sanitization."""
        message = 'Invalid access key DUMMYDUMMYDUMMYDUMMY'
        result = _sanitize_error_message(message)
        assert result == 'Invalid access key [ACCESS-KEY]'

    def test_sanitize_multiple_patterns(self):
        """Test multiple sensitive patterns in one message."""
        message = (
            'Account 123456789012 cannot access arn:aws:appsync:us-east-1:123456789012:apis/abc123'
        )
        result = _sanitize_error_message(message)
        assert result == 'Account [ACCOUNT-ID] cannot access [ARN]'

    def test_no_sensitive_data(self):
        """Test message with no sensitive data remains unchanged."""
        message = 'Invalid GraphQL schema'
        result = _sanitize_error_message(message)
        assert result == 'Invalid GraphQL schema'


class TestHandleExceptions:
    """Test exception handling decorator."""

    @pytest.mark.asyncio
    async def test_client_error_handling(self):
        """Test ClientError handling with sanitization."""

        @handle_exceptions
        async def mock_func():
            error_response = {
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'Access denied for account 123456789012',
                }
            }
            raise ClientError(error_response, 'GetApi')

        with pytest.raises(Exception) as exc_info:
            await mock_func()

        assert 'AppSync API error [AccessDenied]: Access denied for account [ACCOUNT-ID]' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self):
        """Test generic exception handling."""

        @handle_exceptions
        async def mock_func():
            raise ValueError('Test error')

        with pytest.raises(ValueError):
            await mock_func()

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test successful function execution."""

        @handle_exceptions
        async def mock_func():
            return 'success'

        result = await mock_func()
        assert result == 'success'


class TestGetAppSyncClient:
    """Test AppSync client creation."""

    @patch('awslabs.aws_appsync_mcp_server.helpers.boto3.Session')
    def test_get_appsync_client_success(self, mock_session):
        """Test successful client creation."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client

        result = get_appsync_client()
        assert result == mock_client

    @patch('awslabs.aws_appsync_mcp_server.helpers.boto3.Session')
    def test_get_appsync_client_exception(self, mock_session):
        """Test client creation with exception."""
        mock_session.side_effect = Exception('Test error')

        with pytest.raises(Exception):
            get_appsync_client()
