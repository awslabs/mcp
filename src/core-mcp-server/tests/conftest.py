# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Configuration for pytest."""

import inspect
import pytest
import sys
from unittest.mock import MagicMock


class MockFunctionTool:
    """Mock implementation of the FunctionTool class for testing purposes."""

    def __init__(self, func):
        """Initialize the MockFunctionTool with a function."""
        self.func = func

    async def run(self, arguments=None):
        """Execute the function with the provided arguments."""
        if arguments is None:
            arguments = {}
        if callable(self.func):
            if inspect.iscoroutinefunction(self.func):
                return await self.func(**arguments)
            else:
                return self.func(**arguments)
        else:
            return self.func


class MockFastMCP:
    """Mock implementation of the FastMCP class for testing purposes."""

    def __init__(self, description=None, dependencies=None):
        """Initialize the MockFastMCP with a description and dependencies."""
        self.description = description
        self.dependencies = dependencies or []
        self.tools = {}
        self.imported_servers = {}

    def tool(self, name=None):
        """Decorator to register a tool function."""

        def decorator(func):
            tool_name = name or func.__name__
            tool_instance = MockFunctionTool(func)
            self.tools[tool_name] = tool_instance
            return tool_instance

        return decorator

    def run(self):
        """Run the MCP server."""
        pass

    async def import_server(self, proxy, prefix=None):
        """Import a server with the given prefix."""
        if prefix:
            self.imported_servers[prefix] = proxy
        return True

    @staticmethod
    def as_proxy(client):
        """Create a proxy for the given client."""
        return client


# Create a mock for MCP servers
def create_mock_server():
    """Create a mock server with a mcp attribute."""
    mock_server = MagicMock()
    mock_server.mcp = MagicMock()
    return mock_server


# Only mock the MCP server modules, not the core FastMCP functionality
mock_modules = {
    # MCP servers (mocked so imports don't fail)
    'awslabs.amazon_keyspaces_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.amazon_mq_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.amazon_neptune_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.amazon_sns_sqs_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.aurora_dsql_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.aws_api_mcp_server.server': MagicMock(server=MagicMock()),
    'awslabs.aws_dataprocessing_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.aws_diagram_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.aws_healthomics_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.aws_pricing_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.aws_serverless_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.aws_support_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.cdk_mcp_server.core.server': MagicMock(mcp=MagicMock()),
    'awslabs.cfn_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.cloudwatch_appsignals_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.cloudwatch_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.code_doc_gen_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.cost_explorer_mcp_server.server': MagicMock(app=MagicMock()),
    'awslabs.documentdb_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.dynamodb_mcp_server.server': MagicMock(app=MagicMock()),
    'awslabs.ecs_mcp_server.main': MagicMock(mcp=MagicMock()),
    'awslabs.eks_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.elasticache_mcp_server.main': MagicMock(mcp=MagicMock()),
    'awslabs.finch_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.frontend_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.git_repo_research_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.iam_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.lambda_tool_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.memcached_mcp_server.main': MagicMock(mcp=MagicMock()),
    'awslabs.mysql_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.nova_canvas_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.postgres_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.prometheus_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.redshift_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.s3_tables_mcp_server.server': MagicMock(app=MagicMock()),
    'awslabs.stepfunctions_tool_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.syntheticdata_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.timestream_for_influxdb_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.billing_cost_management_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.cloudtrail_mcp_server.server': MagicMock(mcp=MagicMock()),
    'awslabs.well_architected_security_mcp_server.server': MagicMock(mcp=MagicMock()),
}

# Create a mock for the ProxyClient class
mock_proxy_client = MagicMock()

# Set up the FastMCP mock with our implementation
fastmcp_mock = MagicMock()
fastmcp_mock.FastMCP = MockFastMCP
fastmcp_mock.server = MagicMock()
fastmcp_mock.server.proxy = MagicMock()
fastmcp_mock.server.proxy.ProxyClient = mock_proxy_client

# Update the mock modules with our FastMCP implementation
mock_modules.update(
    {
        'fastmcp': fastmcp_mock,
        'fastmcp.server': fastmcp_mock.server,
        'fastmcp.server.proxy': fastmcp_mock.server.proxy,
    }
)

# Inject mocks globally
sys.modules.update(mock_modules)


def pytest_addoption(parser):
    """Add command-line options to pytest."""
    parser.addoption(
        '--run-live',
        action='store_true',
        default=False,
        help='Run tests that make live API calls',
    )


def pytest_collection_modifyitems(config, items):
    """Skip live tests unless --run-live is specified."""
    if not config.getoption('--run-live'):
        skip_live = pytest.mark.skip(reason='need --run-live option to run')
        for item in items:
            if 'live' in item.keywords:
                item.add_marker(skip_live)


@pytest.fixture
def mock_fastmcp():
    """Fixture to provide a MockFastMCP instance."""
    return MockFastMCP('Test MCP Server', ['loguru'])


@pytest.fixture
def mock_proxy_client():
    """Fixture to provide a mock ProxyClient."""
    return mock_proxy_client
