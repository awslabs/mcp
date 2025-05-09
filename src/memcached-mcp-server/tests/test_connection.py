"""Unit tests for connection management."""

import os
import ssl
import unittest
from awslabs.memcached_mcp_server.common.connection import MemcachedConnectionManager
from pymemcache.exceptions import MemcacheError
from unittest.mock import MagicMock, patch


class TestMemcachedConnectionManager(unittest.TestCase):
    """Test cases for MemcachedConnectionManager."""

    def setUp(self):
        """Reset the connection before each test."""
        MemcachedConnectionManager._client = None

    def tearDown(self):
        """Clean up after each test."""
        MemcachedConnectionManager._client = None

    @patch('awslabs.memcached_mcp_server.common.connection.Client')
    @patch('awslabs.memcached_mcp_server.common.connection.RetryingClient')
    def test_get_connection_default_values(self, mock_retrying_client, mock_client):
        """Test get_connection with default environment values."""
        # Setup mock
        mock_instance = MagicMock()
        mock_retrying_client.return_value = mock_instance

        # Get connection
        client = MemcachedConnectionManager.get_connection()

        # Verify Client constructor called with default values
        mock_client.assert_called_once_with(
            server=('127.0.0.1', 11211),
            timeout=1.0,
            connect_timeout=5.0,
            no_delay=True,
        )

        # Verify RetryingClient constructor called with default values
        mock_retrying_client.assert_called_once()
        args, kwargs = mock_retrying_client.call_args
        self.assertEqual(kwargs['attempts'], 3)
        self.assertEqual(kwargs['retry_delay'], 1.0)
        self.assertEqual(kwargs['retry_for'], [MemcacheError])

        # Verify same instance returned
        self.assertEqual(client, mock_instance)

    @patch('awslabs.memcached_mcp_server.common.connection.Client')
    @patch('awslabs.memcached_mcp_server.common.connection.RetryingClient')
    def test_get_connection_custom_values(self, mock_retrying_client, mock_client):
        """Test get_connection with custom environment values."""
        # Set custom environment variables
        env_vars = {
            'MEMCACHED_HOST': 'localhost',
            'MEMCACHED_PORT': '11212',
            'MEMCACHED_TIMEOUT': '2.0',
            'MEMCACHED_CONNECT_TIMEOUT': '10.0',
            'MEMCACHED_RETRY_TIMEOUT': '3.0',
            'MEMCACHED_MAX_RETRIES': '5',
        }

        with patch.dict(os.environ, env_vars):
            # Get connection
            MemcachedConnectionManager.get_connection()

            # Verify Client constructor called with custom values
            mock_client.assert_called_once_with(
                server=('localhost', 11212),
                timeout=2.0,
                connect_timeout=10.0,
                no_delay=True,
            )

            # Verify RetryingClient constructor called with custom values
            mock_retrying_client.assert_called_once()
            args, kwargs = mock_retrying_client.call_args
            self.assertEqual(kwargs['attempts'], 5)
            self.assertEqual(kwargs['retry_delay'], 3.0)
            self.assertEqual(kwargs['retry_for'], [MemcacheError])

    @patch('awslabs.memcached_mcp_server.common.connection.Client')
    @patch('awslabs.memcached_mcp_server.common.connection.RetryingClient')
    def test_get_connection_singleton(self, mock_retrying_client, mock_client):
        """Test get_connection returns same instance on multiple calls."""
        # Setup mock
        mock_instance = MagicMock()
        mock_retrying_client.return_value = mock_instance

        # Get connection multiple times
        client1 = MemcachedConnectionManager.get_connection()
        client2 = MemcachedConnectionManager.get_connection()

        # Verify Client and RetryingClient only called once
        mock_client.assert_called_once()
        mock_retrying_client.assert_called_once()

        # Verify same instance returned
        self.assertEqual(client1, client2)
        self.assertEqual(client1, mock_instance)

    @patch('awslabs.memcached_mcp_server.common.connection.RetryingClient')
    def test_close_connection_existing(self, mock_retrying_client):
        """Test close_connection with existing connection."""
        # Setup mock
        mock_instance = MagicMock()
        mock_retrying_client.return_value = mock_instance

        # Create and close connection
        MemcachedConnectionManager.get_connection()
        MemcachedConnectionManager.close_connection()

        # Verify close was called
        mock_instance.close.assert_called_once()
        self.assertIsNone(MemcachedConnectionManager._client)

    def test_close_connection_no_connection(self):
        """Test close_connection with no existing connection."""
        # Verify no error when closing non-existent connection
        MemcachedConnectionManager.close_connection()
        self.assertIsNone(MemcachedConnectionManager._client)

    @patch('awslabs.memcached_mcp_server.common.connection.Client')
    @patch('awslabs.memcached_mcp_server.common.connection.ssl.create_default_context')
    def test_get_connection_with_tls_default(self, mock_ssl_context, mock_client):
        """Test get_connection with TLS enabled using default settings."""
        # Setup mock SSL context
        mock_context = MagicMock()
        mock_ssl_context.return_value = mock_context

        env_vars = {'MEMCACHED_USE_TLS': 'true'}

        with patch.dict(os.environ, env_vars):
            MemcachedConnectionManager.get_connection()

            # Verify SSL context created with default settings
            mock_ssl_context.assert_called_once_with(cafile=None)
            self.assertEqual(mock_context.check_hostname, True)
            self.assertEqual(mock_context.verify_mode, ssl.CERT_REQUIRED)
            mock_context.load_cert_chain.assert_not_called()

            # Verify client created with SSL context
            mock_client.assert_called_once_with(
                server=('127.0.0.1', 11211),
                timeout=1.0,
                connect_timeout=5.0,
                no_delay=True,
                tls_context=mock_context,
            )

    @patch('awslabs.memcached_mcp_server.common.connection.Client')
    @patch('awslabs.memcached_mcp_server.common.connection.ssl.create_default_context')
    def test_get_connection_with_tls_custom_certs(self, mock_ssl_context, mock_client):
        """Test get_connection with TLS enabled using custom certificates."""
        # Setup mock SSL context
        mock_context = MagicMock()
        mock_ssl_context.return_value = mock_context

        env_vars = {
            'MEMCACHED_USE_TLS': 'true',
            'MEMCACHED_TLS_CERT_PATH': '/path/to/cert.pem',
            'MEMCACHED_TLS_KEY_PATH': '/path/to/key.pem',
            'MEMCACHED_TLS_CA_CERT_PATH': '/path/to/ca.pem',
        }

        with patch.dict(os.environ, env_vars):
            MemcachedConnectionManager.get_connection()

            # Verify SSL context created with CA cert
            mock_ssl_context.assert_called_once_with(cafile='/path/to/ca.pem')
            mock_context.load_cert_chain.assert_called_once_with(
                '/path/to/cert.pem', '/path/to/key.pem'
            )

            # Verify client created with SSL context
            mock_client.assert_called_once_with(
                server=('127.0.0.1', 11211),
                timeout=1.0,
                connect_timeout=5.0,
                no_delay=True,
                tls_context=mock_context,
            )

    @patch('awslabs.memcached_mcp_server.common.connection.Client')
    @patch('awslabs.memcached_mcp_server.common.connection.ssl.create_default_context')
    def test_get_connection_with_tls_no_verify(self, mock_ssl_context, mock_client):
        """Test get_connection with TLS enabled but verification disabled."""
        # Setup mock SSL context
        mock_context = MagicMock()
        mock_ssl_context.return_value = mock_context

        env_vars = {'MEMCACHED_USE_TLS': 'true', 'MEMCACHED_TLS_VERIFY': 'false'}

        with patch.dict(os.environ, env_vars):
            MemcachedConnectionManager.get_connection()

            # Verify SSL context created with verification disabled
            mock_ssl_context.assert_called_once_with(cafile=None)
            self.assertEqual(mock_context.check_hostname, False)
            self.assertEqual(mock_context.verify_mode, ssl.CERT_NONE)

            # Verify client created with SSL context
            mock_client.assert_called_once_with(
                server=('127.0.0.1', 11211),
                timeout=1.0,
                connect_timeout=5.0,
                no_delay=True,
                tls_context=mock_context,
            )


if __name__ == '__main__':
    unittest.main()
