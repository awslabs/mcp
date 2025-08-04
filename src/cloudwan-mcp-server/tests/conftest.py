# pytest fixtures for AWS client mocking
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_get_aws_client():
    """Mock get_aws_client with service/region tracking."""
    clients = {}

    def _get_client(service, region=None):
        key = (service, region or "us-east-1")
        if key not in clients:
            clients[key] = Mock()
        return clients[key]

    with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock:
        mock.side_effect = _get_client
        yield _get_client

    # Clear LRU cache after tests
    from awslabs.cloudwan_mcp_server.server import _create_client
    _create_client.cache_clear()