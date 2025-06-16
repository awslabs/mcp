"""Tests for authentication error handling in server.py."""

import pytest
import sys
from unittest.mock import MagicMock, patch
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.server import create_mcp_server


class TestServerAuthErrors:
    """Tests for authentication error handling in server.py."""

    @patch('sys.exit')
    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    def test_bearer_auth_not_configured(self, mock_get_auth, mock_exit):
        """Test handling of bearer auth not configured."""
        # Create a mock auth provider that is not configured
        mock_auth = MagicMock()
        mock_auth.provider_name = 'bearer'
        mock_auth.is_configured.return_value = False
        mock_get_auth.return_value = mock_auth

        # Create config with bearer auth
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
            auth_type='bearer',
            auth_token='',  # Empty token
        )

        # Call create_mcp_server, which should handle the auth error
        create_mcp_server(config)

        # Verify sys.exit was called
        mock_exit.assert_called_once_with(1)

    @patch('sys.exit')
    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    def test_basic_auth_not_configured(self, mock_get_auth, mock_exit):
        """Test handling of basic auth not configured."""
        # Create a mock auth provider that is not configured
        mock_auth = MagicMock()
        mock_auth.provider_name = 'basic'
        mock_auth.is_configured.return_value = False
        mock_get_auth.return_value = mock_auth

        # Create config with basic auth
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
            auth_type='basic',
            auth_username='',  # Empty username
            auth_password='',  # Empty password
        )

        # Call create_mcp_server, which should handle the auth error
        create_mcp_server(config)

        # Verify sys.exit was called
        mock_exit.assert_called_once_with(1)

    @patch('sys.exit')
    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    def test_api_key_auth_not_configured(self, mock_get_auth, mock_exit):
        """Test handling of API key auth not configured."""
        # Create a mock auth provider that is not configured
        mock_auth = MagicMock()
        mock_auth.provider_name = 'api_key'
        mock_auth.is_configured.return_value = False
        mock_get_auth.return_value = mock_auth

        # Create config with API key auth
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
            auth_type='api_key',
            auth_api_key='',  # Empty API key
        )

        # Call create_mcp_server, which should handle the auth error
        create_mcp_server(config)

        # Verify sys.exit was called
        mock_exit.assert_called_once_with(1)

    @patch('sys.exit')
    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    def test_cognito_auth_not_configured(self, mock_get_auth, mock_exit):
        """Test handling of Cognito auth not configured."""
        # Create a mock auth provider that is not configured
        mock_auth = MagicMock()
        mock_auth.provider_name = 'cognito'
        mock_auth.is_configured.return_value = False
        mock_get_auth.return_value = mock_auth

        # Create config with Cognito auth
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
            auth_type='cognito',
            auth_cognito_client_id='',  # Empty client ID
            auth_cognito_username='',  # Empty username
            auth_cognito_password='',  # Empty password
        )

        # Call create_mcp_server, which should handle the auth error
        create_mcp_server(config)

        # Verify sys.exit was called
        mock_exit.assert_called_once_with(1)

    @patch('sys.exit')
    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    def test_unknown_auth_not_configured(self, mock_get_auth, mock_exit):
        """Test handling of unknown auth type not configured."""
        # Create a mock auth provider that is not configured
        mock_auth = MagicMock()
        mock_auth.provider_name = 'unknown'
        mock_auth.is_configured.return_value = False
        mock_get_auth.return_value = mock_auth

        # Create config with unknown auth type
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
            auth_type='unknown',
        )

        # Call create_mcp_server, which should handle the auth error
        create_mcp_server(config)

        # Verify sys.exit was called
        mock_exit.assert_called_once_with(1)
