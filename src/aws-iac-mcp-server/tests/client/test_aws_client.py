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
from awslabs.aws_iac_mcp_server.client.aws_client import ClientError, get_aws_client
from unittest.mock import MagicMock, patch


@patch('awslabs.aws_iac_mcp_server.client.aws_client.Session')
def test_get_aws_client_success(mock_session_class):
    """Test successful client creation."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client
    mock_session_class.return_value = mock_session

    result = get_aws_client('s3', 'us-west-2')

    mock_session.client.assert_called_once()
    assert result == mock_client


@patch('awslabs.aws_iac_mcp_server.client.aws_client.Session')
def test_get_aws_client_expired_token(mock_session_class):
    """Test ExpiredToken error handling."""
    mock_session = MagicMock()
    mock_session.client.side_effect = Exception('ExpiredToken')
    mock_session_class.return_value = mock_session

    with pytest.raises(ClientError, match='credentials have expired'):
        get_aws_client('s3', 'us-west-2')


@patch('awslabs.aws_iac_mcp_server.client.aws_client.Session')
def test_get_aws_client_no_credentials(mock_session_class):
    """Test NoCredentialProviders error handling."""
    mock_session = MagicMock()
    mock_session.client.side_effect = Exception('NoCredentialProviders')
    mock_session_class.return_value = mock_session

    with pytest.raises(ClientError, match='No AWS credentials found'):
        get_aws_client('s3', 'us-west-2')


@patch('awslabs.aws_iac_mcp_server.client.aws_client.Session')
def test_get_aws_client_generic_error(mock_session_class):
    """Test generic error handling."""
    mock_session = MagicMock()
    mock_session.client.side_effect = Exception('Some other error')
    mock_session_class.return_value = mock_session

    with pytest.raises(ClientError, match='Error creating AWS client'):
        get_aws_client('s3', 'us-west-2')
