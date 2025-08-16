"""Tests for validation functions."""

from awslabs.healthlake_mcp_server.server import MAX_SEARCH_COUNT


def test_max_search_count_constant():
    """Test that MAX_SEARCH_COUNT is properly defined."""
    assert MAX_SEARCH_COUNT == 100
