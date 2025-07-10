import asyncio
import os
import pytest
from awslabs.aws_finops_mcp_server.boto3_tools import Boto3ToolRegistry
from awslabs.aws_finops_mcp_server.server import create_tool_function


TEMP_ENV_VARS = {'AWS_REGION': 'us-east-1'}  # Set default region for testing


@pytest.fixture(scope='session', autouse=True)
def tests_setup_and_teardown():
    """Mock environment and module variables for testing."""
    global TEMP_ENV_VARS
    # Will be executed before the first test
    old_environ = dict(os.environ)
    os.environ.update(TEMP_ENV_VARS)

    yield
    # Will be executed after the last test
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def registry():
    """Fixture that provides a configured Boto3ToolRegistry."""
    registry = Boto3ToolRegistry()
    registry.register_all_tools()
    return registry


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tool_function_factory(registry):
    """Fixture that provides a factory for creating tool functions."""

    def _create_tool_function(tool_name):
        return create_tool_function(registry, tool_name)

    return _create_tool_function
