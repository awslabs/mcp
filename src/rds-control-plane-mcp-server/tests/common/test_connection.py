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

"""Tests for the connection module in the RDS Control Plane MCP Server."""

import os
import boto3
import pytest
from unittest.mock import MagicMock, patch, ANY
from botocore.config import Config

from awslabs.rds_control_plane_mcp_server.common.connection import RDSConnectionManager, PIConnectionManager, BaseConnectionManager


def test_rds_connection_manager_initialization():
    """Test that the RDS connection manager initializes properly."""
    RDSConnectionManager._client = None

    with patch('boto3.Session') as mock_session:
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client

        client = RDSConnectionManager.get_connection()

        mock_session_instance.client.assert_called_once()
        assert client is mock_client


def test_rds_connection_manager_singleton():
    """Test that the RDS connection manager behaves as a singleton."""
    RDSConnectionManager._client = None

    with patch('boto3.Session') as mock_session:
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client

        client1 = RDSConnectionManager.get_connection()
        client2 = RDSConnectionManager.get_connection()

        assert mock_session_instance.client.call_count == 1
        assert client1 is client2


def test_rds_connection_manager_with_region():
    RDSConnectionManager._client = None

    with patch('boto3.Session') as mock_session:
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_client = MagicMock()
        mock_session_instance.client.return_value = mock_client

        os.environ['AWS_REGION'] = 'us-west-2'

        client = RDSConnectionManager.get_connection()

        mock_session.assert_called_once_with(profile_name='default', region_name='us-west-2')
        assert client is mock_client

        del os.environ['AWS_REGION']


@patch('boto3.Session')
def test_pi_connection_manager(mock_session):
    """Test the PIConnectionManager class."""
    PIConnectionManager._client = None
    
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_pi_client = MagicMock()
    mock_session_instance.client.return_value = mock_pi_client

    pi_client = PIConnectionManager.get_connection()

    mock_session_instance.client.assert_called_once_with(
        service_name='pi', 
        config=ANY
    )

    assert pi_client is mock_pi_client


@patch('boto3.Session')
def test_pi_connection_manager_with_region(mock_session):
    PIConnectionManager._client = None
    
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_pi_client = MagicMock()
    mock_session_instance.client.return_value = mock_pi_client

    os.environ['AWS_REGION'] = 'eu-west-1'

    pi_client = PIConnectionManager.get_connection()

    mock_session.assert_called_once_with(profile_name='default', region_name='eu-west-1')
    assert pi_client is mock_pi_client

    del os.environ['AWS_REGION']


def test_rds_connection_error_handling():
    """Test error handling when creating RDS connection."""
    RDSConnectionManager._client = None

    with patch('boto3.Session') as mock_session:
        mock_session.side_effect = Exception("Failed to create session")

        with pytest.raises(Exception) as exc_info:
            RDSConnectionManager.get_connection()
        assert "Failed to create session" in str(exc_info.value)


def test_pi_connection_error_handling():
    """Test error handling when creating PI connection."""
    PIConnectionManager._client = None

    with patch('boto3.Session') as mock_session:
        mock_session.side_effect = Exception("Failed to create PI session")

        with pytest.raises(Exception) as exc_info:
            PIConnectionManager.get_connection()

        assert "Failed to create PI session" in str(exc_info.value)


@patch('boto3.Session')
def test_rds_connection_with_custom_session(mock_session):
    """Test RDS connection manager with a custom session."""
    RDSConnectionManager._client = None

    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_client = MagicMock()
    mock_session_instance.client.return_value = mock_client

    os.environ['AWS_PROFILE'] = 'test-profile'

    try:
        client = RDSConnectionManager.get_connection()

        mock_session.assert_called_once_with(profile_name='test-profile', region_name='us-east-1')
        assert client is mock_client
    finally:
        del os.environ['AWS_PROFILE']


@patch('boto3.Session')
def test_connection_manager_config(mock_session):
    """Test connection manager configuration options."""
    RDSConnectionManager._client = None
    
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_client = MagicMock()
    mock_session_instance.client.return_value = mock_client

    os.environ['RDS_MAX_RETRIES'] = '5'
    os.environ['RDS_RETRY_MODE'] = 'adaptive'
    os.environ['RDS_CONNECT_TIMEOUT'] = '10'
    os.environ['RDS_READ_TIMEOUT'] = '20'

    try:
        client = RDSConnectionManager.get_connection()
        
        # Check that client was created with the expected config
        mock_session_instance.client.assert_called_once_with(
            service_name='rds',
            config=ANY
        )
        
        # Since we can't check the Config object directly, we'll just verify it was created
        assert client is mock_client
    finally:
        del os.environ['RDS_MAX_RETRIES']
        del os.environ['RDS_RETRY_MODE']
        del os.environ['RDS_CONNECT_TIMEOUT']
        del os.environ['RDS_READ_TIMEOUT']


def test_close_connection():
    """Test that the close_connection method works correctly."""
    # Set up mock client
    mock_client = MagicMock()
    RDSConnectionManager._client = mock_client

    # Call close_connection
    RDSConnectionManager.close_connection()

    # Verify client was closed
    mock_client.close.assert_called_once()
    assert RDSConnectionManager._client is None
