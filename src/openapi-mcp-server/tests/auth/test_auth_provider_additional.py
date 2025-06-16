"""Additional tests for auth_provider module to improve coverage."""

import pytest
from unittest.mock import MagicMock, patch
import httpx

from awslabs.openapi_mcp_server.auth.auth_provider import NullAuthProvider


class TestNullAuthProvider:
    """Tests for NullAuthProvider class."""

    def test_null_auth_provider_methods(self):
        """Test NullAuthProvider methods."""
        # Create an instance
        provider = NullAuthProvider()
        
        # Test the methods
        assert provider.provider_name == "none"
        assert provider.is_configured() is True
        assert provider.get_auth_headers() == {}
        assert provider.get_auth_params() == {}
        assert provider.get_auth_cookies() == {}
        assert provider.get_httpx_auth() is None
        
        # Test with config
        config = MagicMock()
        provider_with_config = NullAuthProvider(config)
        assert provider_with_config.is_configured() is True
