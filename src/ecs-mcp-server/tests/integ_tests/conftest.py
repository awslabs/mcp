"""
Pytest configuration for ECS MCP Server integration tests.
"""

import logging
from pathlib import Path

import pytest

# Configure logging for integration tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@pytest.fixture(scope="session")
def ecs_server_path():
    """Fixture providing the path to the ECS MCP server main.py."""
    return Path(__file__).parent.parent.parent / "awslabs" / "ecs_mcp_server" / "main.py"


@pytest.fixture(scope="session")
def uv_path():
    """Fixture providing the path to the uv binary."""
    return "/opt/homebrew/bin/uv"


@pytest.fixture
def inspector_timeout():
    """Fixture providing the default timeout for inspector commands."""
    return 30


# Pytest markers for different test categories
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (may take more than 5 seconds)")
    config.addinivalue_line("markers", "requires_aws: marks tests that require AWS credentials")
    config.addinivalue_line("markers", "requires_docker: marks tests that require Docker")
    config.addinivalue_line("markers", "tool_call: marks tests that call MCP tools")
