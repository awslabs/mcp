"""Unit tests for ElastiCache connection management."""

import os
import pytest
from awslabs.elasticache_mcp_server.common.connection import ElastiCacheConnectionManager
from botocore.config import Config
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def reset_connection():
    """Reset the connection before and after each test."""
    ElastiCacheConnectionManager._client = None
    yield
    ElastiCacheConnectionManager._client = None


def test_get_connection_default_settings():
    """Test connection creation with default settings."""
    with patch('boto3.Session') as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        client = ElastiCacheConnectionManager.get_connection()

        mock_session.assert_called_once_with(profile_name='default', region_name='us-east-1')
        mock_session.return_value.client.assert_called_once()

        # Verify the config passed to client creation
        client_args = mock_session.return_value.client.call_args[1]
        assert client_args['service_name'] == 'elasticache'
        config = client_args['config']
        assert isinstance(config, Config)
        # Access config attributes using dict-style access to avoid type checking issues
        assert config._user_provided_options['retries']['max_attempts'] == 3
        assert config._user_provided_options['retries']['mode'] == 'standard'
        assert config._user_provided_options['connect_timeout'] == 5
        assert config._user_provided_options['read_timeout'] == 10

        assert client == mock_client


def test_get_connection_custom_settings():
    """Test connection creation with custom environment settings."""
    env_vars = {
        'AWS_PROFILE': 'test-profile',
        'AWS_REGION': 'us-west-2',
        'ELASTICACHE_MAX_RETRIES': '5',
        'ELASTICACHE_RETRY_MODE': 'adaptive',
        'ELASTICACHE_CONNECT_TIMEOUT': '10',
        'ELASTICACHE_READ_TIMEOUT': '20',
    }

    with patch.dict(os.environ, env_vars), patch('boto3.Session') as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        client = ElastiCacheConnectionManager.get_connection()

        mock_session.assert_called_once_with(profile_name='test-profile', region_name='us-west-2')
        mock_session.return_value.client.assert_called_once()

        # Verify custom config
        client_args = mock_session.return_value.client.call_args[1]
        config = client_args['config']
        # Access config attributes using dict-style access to avoid type checking issues
        assert config._user_provided_options['retries']['max_attempts'] == 5
        assert config._user_provided_options['retries']['mode'] == 'adaptive'
        assert config._user_provided_options['connect_timeout'] == 10
        assert config._user_provided_options['read_timeout'] == 20

        assert client == mock_client


def test_connection_reuse():
    """Test that the connection is reused rather than recreated."""
    with patch('boto3.Session') as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Get connection twice
        client1 = ElastiCacheConnectionManager.get_connection()
        client2 = ElastiCacheConnectionManager.get_connection()

        # Verify Session was only created once
        mock_session.assert_called_once()
        assert client1 == client2


def test_close_connection():
    """Test that close_connection properly closes and clears the client."""
    with patch('boto3.Session') as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create and then close connection
        ElastiCacheConnectionManager.get_connection()
        ElastiCacheConnectionManager.close_connection()

        # Verify client was closed
        mock_client.close.assert_called_once()
        assert ElastiCacheConnectionManager._client is None


def test_close_connection_no_client():
    """Test close_connection when no client exists."""
    # Should not raise any errors
    ElastiCacheConnectionManager.close_connection()
    assert ElastiCacheConnectionManager._client is None


def test_get_connection_after_close():
    """Test getting a new connection after closing the previous one."""
    with patch('boto3.Session') as mock_session:
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_session.return_value.client.side_effect = [mock_client1, mock_client2]

        # Get initial connection
        client1 = ElastiCacheConnectionManager.get_connection()
        assert client1 == mock_client1

        # Close connection
        ElastiCacheConnectionManager.close_connection()

        # Get new connection
        client2 = ElastiCacheConnectionManager.get_connection()
        assert client2 == mock_client2
        assert client1 != client2

        # Verify Session was created twice
        assert mock_session.call_count == 2
