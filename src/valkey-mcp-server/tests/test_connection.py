import unittest
from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.version import __version__
from unittest.mock import patch
from valkey import exceptions


class TestValkeyConnectionManager(unittest.TestCase):
    """Test cases for the ValkeyConnectionManager class."""

    def setUp(self):
        """Reset the singleton instance before each test."""
        ValkeyConnectionManager._instance = None

    def test_basic_connection(self):
        """Test basic connection creation without cluster mode or SSL."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.Valkey') as mock_valkey,
        ):
            # Configure mock
            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': False,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.side_effect = lambda key, default=None: {
                'username': None,
                'password': '',
                'ssl': False,
            }.get(key, default)

            # Get connection
            conn = ValkeyConnectionManager.get_connection()

            # Verify Valkey was instantiated with correct parameters
            mock_valkey.assert_called_once_with(
                host='localhost',
                port=6379,
                username=None,
                password='',
                ssl=False,
                ssl_ca_path=None,
                ssl_keyfile=None,
                ssl_certfile=None,
                ssl_cert_reqs=None,
                ssl_ca_certs=None,
                decode_responses=True,
                max_connections=10,
                lib_name=f'valkey-py(mcp-server_v{__version__})',
            )

            # Verify connection is returned
            self.assertEqual(conn, mock_valkey.return_value)

    def test_cluster_mode_connection(self):
        """Test connection creation in cluster mode."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.ValkeyCluster') as mock_cluster,
        ):
            # Configure mock
            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': True,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.side_effect = lambda key, default=None: {
                'username': None,
                'password': '',
                'ssl': False,
            }.get(key, default)

            # Get connection
            conn = ValkeyConnectionManager.get_connection()

            # Verify ValkeyCluster was instantiated with correct parameters
            mock_cluster.assert_called_once_with(
                host='localhost',
                port=6379,
                username=None,
                password='',
                ssl=False,
                ssl_ca_path=None,
                ssl_keyfile=None,
                ssl_certfile=None,
                ssl_cert_reqs=None,
                ssl_ca_certs=None,
                decode_responses=True,
                max_connections_per_node=10,
                lib_name=f'valkey-py(mcp-server_v{__version__})',
            )

            # Verify connection is returned
            self.assertEqual(conn, mock_cluster.return_value)

    def test_ssl_connection(self):
        """Test connection creation with SSL enabled."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.Valkey') as mock_valkey,
        ):
            # Configure mock
            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': False,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.side_effect = lambda key, default=None: {
                'username': None,
                'password': '',
                'ssl': True,
                'ssl_ca_path': '/path/to/ca',
                'ssl_keyfile': '/path/to/key',
                'ssl_certfile': '/path/to/cert',
                'ssl_ca_certs': '/path/to/certs',
            }.get(key, default)

            # Get connection and verify Valkey was instantiated with correct SSL parameters
            ValkeyConnectionManager.get_connection()
            mock_valkey.assert_called_once_with(
                host='localhost',
                port=6379,
                username=None,
                password='',
                ssl=True,
                ssl_ca_path='/path/to/ca',
                ssl_keyfile='/path/to/key',
                ssl_certfile='/path/to/cert',
                ssl_cert_reqs='required',
                ssl_ca_certs='/path/to/certs',
                decode_responses=True,
                max_connections=10,
                lib_name=f'valkey-py(mcp-server_v{__version__})',
            )

    def test_connection_reuse(self):
        """Test that the same connection instance is reused."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.Valkey') as mock_valkey,
        ):
            # Configure mock
            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': False,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.side_effect = lambda key, default=None: {
                'username': None,
                'password': '',
                'ssl': False,
            }.get(key, default)

            # Get connection twice
            conn1 = ValkeyConnectionManager.get_connection()
            conn2 = ValkeyConnectionManager.get_connection()

            # Verify Valkey was instantiated only once
            mock_valkey.assert_called_once()

            # Verify both calls return same instance
            self.assertEqual(conn1, conn2)

    def test_authentication_error(self):
        """Test handling of authentication errors."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.Valkey') as mock_valkey,
        ):
            # Configure mock to raise AuthenticationError
            mock_valkey.side_effect = exceptions.AuthenticationError()

            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': False,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.return_value = None

            # Verify AuthenticationError is raised
            with self.assertRaises(exceptions.AuthenticationError):
                ValkeyConnectionManager.get_connection()

    def test_connection_error(self):
        """Test handling of connection errors."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.Valkey') as mock_valkey,
        ):
            # Configure mock to raise ConnectionError
            mock_valkey.side_effect = exceptions.ConnectionError()

            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': False,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.return_value = None

            # Verify ConnectionError is raised
            with self.assertRaises(exceptions.ConnectionError):
                ValkeyConnectionManager.get_connection()

    def test_timeout_error(self):
        """Test handling of timeout errors."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.Valkey') as mock_valkey,
        ):
            # Configure mock to raise TimeoutError
            mock_valkey.side_effect = exceptions.TimeoutError()

            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': False,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.return_value = None

            # Verify TimeoutError is raised
            with self.assertRaises(exceptions.TimeoutError):
                ValkeyConnectionManager.get_connection()

    def test_response_error(self):
        """Test handling of response errors."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.Valkey') as mock_valkey,
        ):
            # Configure mock to raise ResponseError
            mock_valkey.side_effect = exceptions.ResponseError('test error')

            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': False,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.return_value = None

            # Verify ResponseError is raised
            with self.assertRaises(exceptions.ResponseError):
                ValkeyConnectionManager.get_connection()

    def test_cluster_error(self):
        """Test handling of cluster errors."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.ValkeyCluster') as mock_cluster,
        ):
            # Configure mock to raise ClusterError
            mock_cluster.side_effect = exceptions.ClusterError('test error')

            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': True,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.return_value = None

            # Verify ClusterError is raised
            with self.assertRaises(exceptions.ClusterError):
                ValkeyConnectionManager.get_connection()

    def test_valkey_error(self):
        """Test handling of general Valkey errors."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.Valkey') as mock_valkey,
        ):
            # Configure mock to raise ValkeyError
            mock_valkey.side_effect = exceptions.ValkeyError('test error')

            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': False,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.return_value = None

            # Verify ValkeyError is raised
            with self.assertRaises(exceptions.ValkeyError):
                ValkeyConnectionManager.get_connection()

    def test_unexpected_error(self):
        """Test handling of unexpected errors."""
        with (
            patch('awslabs.valkey_mcp_server.common.connection.VALKEY_CFG') as mock_cfg,
            patch('awslabs.valkey_mcp_server.common.connection.Valkey') as mock_valkey,
        ):
            # Configure mock to raise unexpected error
            mock_valkey.side_effect = Exception('unexpected error')

            mock_cfg.__getitem__.side_effect = {
                'cluster_mode': False,
                'host': 'localhost',
                'port': 6379,
            }.__getitem__
            mock_cfg.get.return_value = None

            # Verify Exception is raised
            with self.assertRaises(Exception):
                ValkeyConnectionManager.get_connection()


if __name__ == '__main__':
    unittest.main()
