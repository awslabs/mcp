"""Additional tests for auth_protocol module to improve coverage."""

from awslabs.openapi_mcp_server.auth.auth_protocol import AuthProviderProtocol


class TestAuthProviderProtocol:
    """Tests for AuthProviderProtocol."""

    def test_auth_provider_protocol_implementation(self):
        """Test implementation of AuthProviderProtocol."""

        # Create a class that implements the protocol
        class TestAuthProvider:
            @property
            def provider_name(self):
                return 'test_provider'

            def is_configured(self):
                return True

            def get_auth_headers(self):
                return {'Authorization': 'Bearer token'}

            def get_auth_params(self):
                return {'api_key': 'key'}

            def get_auth_cookies(self):
                return {'session': 'cookie'}

            def get_httpx_auth(self):
                return None

        # Create an instance
        provider = TestAuthProvider()

        # Check if it implements the protocol
        assert isinstance(provider, AuthProviderProtocol)

        # Test the methods
        assert provider.provider_name == 'test_provider'
        assert provider.is_configured() is True
        assert provider.get_auth_headers() == {'Authorization': 'Bearer token'}
        assert provider.get_auth_params() == {'api_key': 'key'}
        assert provider.get_auth_cookies() == {'session': 'cookie'}
        assert provider.get_httpx_auth() is None
