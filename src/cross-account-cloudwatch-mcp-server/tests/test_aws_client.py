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

"""Tests for aws_client module."""

import pytest
import time
from awslabs.cross_account_cloudwatch_mcp_server.aws_client import (
    _session_cache,
    clear_session_cache,
    get_cross_account_client,
)
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear session cache before each test."""
    clear_session_cache()
    yield
    clear_session_cache()


class TestGetCrossAccountClient:
    """Tests for get_cross_account_client."""

    @patch('awslabs.cross_account_cloudwatch_mcp_server.aws_client.Session')
    def test_assumes_role_and_returns_client(self, mock_session_cls):
        """Test that a new role is assumed and client returned."""
        mock_sts = MagicMock()
        mock_sts.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'AKIA_TEST',
                'SecretAccessKey': 'secret_test',
                'SessionToken': 'token_test',
                'Expiration': datetime(2099, 1, 1, tzinfo=timezone.utc),
            }
        }
        # First Session() call returns STS client, second is the assumed session
        sts_session = MagicMock()
        sts_session.client.return_value = mock_sts

        assumed_session = MagicMock()
        assumed_client = MagicMock()
        assumed_session.client.return_value = assumed_client

        mock_session_cls.side_effect = [sts_session, assumed_session]

        client = get_cross_account_client('logs', '123456789012', 'MyRole', 'us-east-1')

        assert client == assumed_client
        mock_sts.assume_role.assert_called_once()
        call_kwargs = mock_sts.assume_role.call_args[1]
        assert call_kwargs['RoleArn'] == 'arn:aws:iam::123456789012:role/MyRole'

    @patch('awslabs.cross_account_cloudwatch_mcp_server.aws_client.Session')
    def test_uses_cached_session(self, mock_session_cls):
        """Test that cached session is reused when not expired."""
        cached_session = MagicMock()
        cached_client = MagicMock()
        cached_session.client.return_value = cached_client

        _session_cache['123456789012:MyRole:us-east-1'] = {
            'session': cached_session,
            'expiration': datetime(2099, 1, 1, tzinfo=timezone.utc),
        }

        client = get_cross_account_client('logs', '123456789012', 'MyRole', 'us-east-1')

        assert client == cached_client
        # Session() should not be called since we used cache
        mock_session_cls.assert_not_called()

    @patch('awslabs.cross_account_cloudwatch_mcp_server.aws_client.Session')
    def test_refreshes_expiring_session(self, mock_session_cls):
        """Test that an expiring session is refreshed."""
        # Cache a session that expires in 60 seconds (< 300s threshold)
        old_session = MagicMock()
        _session_cache['123456789012:MyRole:us-east-1'] = {
            'session': old_session,
            'expiration': datetime.fromtimestamp(time.time() + 60, tz=timezone.utc),
        }

        mock_sts = MagicMock()
        mock_sts.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'NEW_KEY',
                'SecretAccessKey': 'new_secret',
                'SessionToken': 'new_token',
                'Expiration': datetime(2099, 1, 1, tzinfo=timezone.utc),
            }
        }
        sts_session = MagicMock()
        sts_session.client.return_value = mock_sts
        new_session = MagicMock()
        mock_session_cls.side_effect = [sts_session, new_session]

        get_cross_account_client('logs', '123456789012', 'MyRole', 'us-east-1')

        mock_sts.assume_role.assert_called_once()


class TestClearSessionCache:
    """Tests for clear_session_cache."""

    def test_clears_cache(self):
        """Test that cache is cleared."""
        _session_cache['key'] = {'session': MagicMock(), 'expiration': datetime.now(timezone.utc)}
        clear_session_cache()
        assert len(_session_cache) == 0
