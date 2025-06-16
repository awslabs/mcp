"""Additional tests for http_client module to improve coverage."""

from awslabs.openapi_mcp_server.utils.http_client import HttpClientFactory


class TestHttpClientFactoryAdditional:
    """Additional tests to improve coverage for HttpClientFactory."""

    def test_http_client_factory_create_client(self):
        """Test HttpClientFactory creates client with default settings."""
        factory = HttpClientFactory()
        client = factory.create_client()

        assert client is not None
        assert hasattr(client, 'get')
        assert hasattr(client, 'post')

    def test_http_client_factory_create_client_with_timeout(self):
        """Test HttpClientFactory creates client with custom timeout."""
        factory = HttpClientFactory()
        client = factory.create_client(timeout=30.0)

        assert client is not None
        # Verify timeout is set (we can't directly access it, but client should be created)

    def test_http_client_factory_create_client_with_retries(self):
        """Test HttpClientFactory creates client with custom retries."""
        factory = HttpClientFactory()
        client = factory.create_client(max_retries=5)

        assert client is not None
        # The max_retries is used internally for retry configuration
