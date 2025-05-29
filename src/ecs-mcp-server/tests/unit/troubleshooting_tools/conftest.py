"""
Pytest configuration for troubleshooting_tools tests.
"""

import pytest


# Configure pytest to handle async tests
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Configure anyio to only use asyncio backend
@pytest.fixture
def anyio_backend():
    """Configure anyio to only use asyncio backend."""
    return "asyncio"
