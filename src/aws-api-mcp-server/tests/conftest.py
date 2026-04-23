"""Shared test fixtures for aws-api-mcp-server."""

import pytest
from awslabs.aws_api_mcp_server.core.common.helpers import get_requests_session
from awslabs.aws_api_mcp_server.core.parser.interpretation import clear_client_cache
from awslabs.aws_api_mcp_server.core.parser.parser import _service_command_table_cache


def _drop_cached_session():
    if get_requests_session.cache_info().currsize:
        get_requests_session().close()
    get_requests_session.cache_clear()


@pytest.fixture(autouse=True)
def _reset_caches():
    """Reset module-level caches between tests."""
    clear_client_cache()
    _drop_cached_session()
    _service_command_table_cache.clear()
    yield
    clear_client_cache()
    _drop_cached_session()
    _service_command_table_cache.clear()
