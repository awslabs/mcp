"""
Pytest configuration for unit tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


# Configure pytest to handle async tests
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Configure anyio to only use asyncio backend
@pytest.fixture
def anyio_backend():
    """Configure anyio to only use asyncio backend."""
    return "asyncio"


# Async test utilities from ECS server pattern
class AsyncTestUtils:
    """Utilities for async testing."""
    
    @staticmethod
    def create_mock_ec2_client():
        """Create a comprehensive mock EC2 client for unit tests."""
        mock_client = MagicMock()
        
        # Configure common responses
        mock_client.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-test123",
                            "State": {"Name": "running", "Code": 16},
                            "InstanceType": "t2.micro"
                        }
                    ]
                }
            ]
        }
        
        return mock_client
    
    @staticmethod
    def create_mock_context():
        """Create a mock MCP context for unit tests."""
        context = AsyncMock()
        context.session = AsyncMock()
        return context


@pytest.fixture
def async_test_utils():
    """Provide async test utilities."""
    return AsyncTestUtils