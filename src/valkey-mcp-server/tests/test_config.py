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

"""Tests for the configuration module."""

import os
from awslabs.valkey_mcp_server.common.config import (
    VALKEY_CFG,
    generate_valkey_uri,
)
from unittest.mock import patch


class TestConfig:
    """Tests for configuration functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        assert VALKEY_CFG['host'] == '127.0.0.1'
        assert VALKEY_CFG['port'] == 6379
        assert VALKEY_CFG['username'] is None
        assert VALKEY_CFG['password'] == ''
        assert VALKEY_CFG['ssl'] is False
        assert VALKEY_CFG['ssl_ca_path'] is None
        assert VALKEY_CFG['ssl_keyfile'] is None
        assert VALKEY_CFG['ssl_certfile'] is None
        assert VALKEY_CFG['ssl_cert_reqs'] == 'required'
        assert VALKEY_CFG['ssl_ca_certs'] is None
        assert VALKEY_CFG['cluster_mode'] is False

    @patch.dict(
        os.environ,
        {
            'VALKEY_HOST': 'test.host',
            'VALKEY_PORT': '6380',
            'VALKEY_USERNAME': 'testuser',
            'VALKEY_PWD': 'testpass',  # pragma: allowlist secret
            'VALKEY_USE_SSL': 'true',
            'VALKEY_SSL_CA_PATH': '/path/to/ca',
            'VALKEY_SSL_KEYFILE': '/path/to/key',
            'VALKEY_SSL_CERTFILE': '/path/to/cert',
            'VALKEY_SSL_CERT_REQS': 'optional',
            'VALKEY_SSL_CA_CERTS': '/path/to/cacerts',
            'VALKEY_CLUSTER_MODE': 'true',
        },
    )
    def test_environment_config(self):
        """Test configuration values from environment variables."""
        # Reload the config module to pick up new environment variables
        with patch('awslabs.valkey_mcp_server.common.config.load_dotenv'):
            import awslabs.valkey_mcp_server.common.config
            import importlib

            importlib.reload(awslabs.valkey_mcp_server.common.config)
            cfg = awslabs.valkey_mcp_server.common.config.VALKEY_CFG

            assert cfg['host'] == 'test.host'
            assert cfg['port'] == 6380
            assert cfg['username'] == 'testuser'
            assert cfg['password'] == 'testpass'  # pragma: allowlist secret
            assert cfg['ssl'] is True
            assert cfg['ssl_ca_path'] == '/path/to/ca'
            assert cfg['ssl_keyfile'] == '/path/to/key'
            assert cfg['ssl_certfile'] == '/path/to/cert'
            assert cfg['ssl_cert_reqs'] == 'optional'
            assert cfg['ssl_ca_certs'] == '/path/to/cacerts'
            assert cfg['cluster_mode'] is True

    @patch.dict(
        os.environ,
        {
            'VALKEY_HOST': '127.0.0.1',
            'VALKEY_PORT': '6379',
            'VALKEY_USERNAME': '',
            'VALKEY_PWD': '',
            'VALKEY_USE_SSL': 'false',
            'VALKEY_SSL_CA_PATH': '',
            'VALKEY_SSL_KEYFILE': '',
            'VALKEY_SSL_CERTFILE': '',
            'VALKEY_SSL_CERT_REQS': '',
            'VALKEY_SSL_CA_CERTS': '',
            'VALKEY_CLUSTER_MODE': 'false',
        },
    )
    def test_generate_valkey_uri_basic(self):
        """Test basic URI generation without authentication or SSL."""
        # Reload the config module to pick up new environment variables
        with patch('awslabs.valkey_mcp_server.common.config.load_dotenv'):
            import awslabs.valkey_mcp_server.common.config
            import importlib

            importlib.reload(awslabs.valkey_mcp_server.common.config)
            uri = generate_valkey_uri()
            assert uri == 'valkey://127.0.0.1:6379'

    def test_generate_valkey_uri_with_auth(self):
        """Test URI generation with authentication."""
        test_cases = [
            # (username, password, expected_uri)
            (None, 'pass', 'valkey://:pass@127.0.0.1:6379'),  # pragma: allowlist secret
            ('user', 'pass', 'valkey://user:pass@127.0.0.1:6379'),  # pragma: allowlist secret
            ('user', '', 'valkey://user:@127.0.0.1:6379'),
            (
                'user:with:colon',
                'pass:with:colon',  # pragma: allowlist secret
                'valkey://user%3Awith%3Acolon:pass%3Awith%3Acolon@127.0.0.1:6379',  # pragma: allowlist secret
            ),
        ]

        for username, password, expected_uri in test_cases:
            env_vars = {
                'VALKEY_HOST': '127.0.0.1',
                'VALKEY_PORT': '6379',
                'VALKEY_USERNAME': username if username is not None else '',
                'VALKEY_PWD': password,
                'VALKEY_USE_SSL': 'false',
                'VALKEY_SSL_CA_PATH': '',
                'VALKEY_SSL_KEYFILE': '',
                'VALKEY_SSL_CERTFILE': '',
                'VALKEY_SSL_CERT_REQS': '',
                'VALKEY_SSL_CA_CERTS': '',
                'VALKEY_CLUSTER_MODE': 'false',
            }
            with patch.dict(os.environ, env_vars):
                with patch('awslabs.valkey_mcp_server.common.config.load_dotenv'):
                    import awslabs.valkey_mcp_server.common.config
                    import importlib

                    importlib.reload(awslabs.valkey_mcp_server.common.config)
                    uri = generate_valkey_uri()
                    assert uri == expected_uri

    def test_generate_valkey_uri_with_ssl(self):
        """Test URI generation with SSL configuration."""
        env_vars = {
            'VALKEY_HOST': '127.0.0.1',
            'VALKEY_PORT': '6379',
            'VALKEY_USERNAME': '',
            'VALKEY_PWD': '',
            'VALKEY_USE_SSL': 'true',
            'VALKEY_SSL_CA_PATH': '/path/to/ca',
            'VALKEY_SSL_KEYFILE': '/path/to/key',
            'VALKEY_SSL_CERTFILE': '/path/to/cert',
            'VALKEY_SSL_CERT_REQS': 'required',
            'VALKEY_SSL_CA_CERTS': '/path/to/cacerts',
            'VALKEY_CLUSTER_MODE': 'false',
        }
        with patch.dict(os.environ, env_vars):
            with patch('awslabs.valkey_mcp_server.common.config.load_dotenv'):
                import awslabs.valkey_mcp_server.common.config
                import importlib

                importlib.reload(awslabs.valkey_mcp_server.common.config)
                uri = generate_valkey_uri()
                assert uri.startswith('valkeys://127.0.0.1:6379?')
                assert 'ssl_cert_reqs=required' in uri
                assert 'ssl_ca_certs=%2Fpath%2Fto%2Fcacerts' in uri
                assert 'ssl_keyfile=%2Fpath%2Fto%2Fkey' in uri
                assert 'ssl_certfile=%2Fpath%2Fto%2Fcert' in uri
                assert 'ssl_ca_path=%2Fpath%2Fto%2Fca' in uri

    def test_generate_valkey_uri_with_partial_ssl(self):
        """Test URI generation with partial SSL configuration."""
        env_vars = {
            'VALKEY_HOST': '127.0.0.1',
            'VALKEY_PORT': '6379',
            'VALKEY_USERNAME': '',
            'VALKEY_PWD': '',
            'VALKEY_USE_SSL': 'true',
            'VALKEY_SSL_CA_PATH': '',
            'VALKEY_SSL_KEYFILE': '',
            'VALKEY_SSL_CERTFILE': '',
            'VALKEY_SSL_CERT_REQS': 'required',
            'VALKEY_SSL_CA_CERTS': '/path/to/cacerts',
            'VALKEY_CLUSTER_MODE': 'false',
        }
        with patch.dict(os.environ, env_vars):
            with patch('awslabs.valkey_mcp_server.common.config.load_dotenv'):
                import awslabs.valkey_mcp_server.common.config
                import importlib

                importlib.reload(awslabs.valkey_mcp_server.common.config)
                uri = generate_valkey_uri()
                assert uri.startswith('valkeys://127.0.0.1:6379?')
                assert 'ssl_cert_reqs=required' in uri
                assert 'ssl_ca_certs=%2Fpath%2Fto%2Fcacerts' in uri
                assert 'ssl_keyfile' not in uri
                assert 'ssl_certfile' not in uri
                assert 'ssl_ca_path' not in uri

    def test_generate_valkey_uri_with_special_chars(self):
        """Test URI generation with special characters that need encoding."""
        env_vars = {
            'VALKEY_HOST': '127.0.0.1',
            'VALKEY_PORT': '6379',
            'VALKEY_USERNAME': 'user@domain',
            'VALKEY_PWD': 'pass word',  # pragma: allowlist secret
            'VALKEY_USE_SSL': 'true',
            'VALKEY_SSL_CA_PATH': '/path with spaces/ca',
            'VALKEY_SSL_KEYFILE': '',
            'VALKEY_SSL_CERTFILE': '',
            'VALKEY_SSL_CERT_REQS': '',
            'VALKEY_SSL_CA_CERTS': '',
            'VALKEY_CLUSTER_MODE': 'false',
        }
        with patch.dict(os.environ, env_vars):
            with patch('awslabs.valkey_mcp_server.common.config.load_dotenv'):
                import awslabs.valkey_mcp_server.common.config
                import importlib

                importlib.reload(awslabs.valkey_mcp_server.common.config)
                uri = generate_valkey_uri()
                assert 'user%40domain:pass%20word@' in uri
                assert 'ssl_ca_path=%2Fpath%20with%20spaces%2Fca' in uri
