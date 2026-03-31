"""Shared test fixtures for aws-api-mcp-server."""

import pytest
from awslabs.aws_api_mcp_server.core.common.helpers import get_requests_session
from awslabs.aws_api_mcp_server.core.parser.interpretation import clear_client_cache
from awslabs.aws_api_mcp_server.core.parser.parser import _service_command_table_cache


@pytest.fixture(autouse=True)
def _reset_caches():
    """Reset module-level caches between tests."""
    clear_client_cache()
    get_requests_session.cache_clear()
    yield
    clear_client_cache()
    get_requests_session.cache_clear()
    _service_command_table_cache.clear()
