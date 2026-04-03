# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Pytest utilities and fixtures for MCP testing framework."""

import asyncio
import logging
import os
import pytest
from .mcp_test_client import StdioMcpClient
from .mcp_test_runner import MCPTestRunner, TestResult
from .types import TestType
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


def setup_logging(level: str = 'INFO'):
    """Setup logging configuration for tests."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(), logging.FileHandler('mcp_test.log')],
    )


@pytest.fixture(scope='session')
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mcp_client_factory():
    """Factory fixture for creating MCP test clients."""

    def _create_client(command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        return StdioMcpClient(command, args, env or {})

    return _create_client


@pytest.fixture
async def mcp_runner_factory():
    """Factory fixture for creating MCP test runners."""

    def _create_runner(client: StdioMcpClient):
        return MCPTestRunner(client)

    return _create_runner


class MCPTestBase:
    """Base class for MCP integration tests."""

    def __init__(
        self,
        server_path: str,
        command: str = 'uv',
        args: List[str] = None,
        env: Dict[str, str] = None,
    ):
        """Initialize the MCP test base."""
        self.server_path = server_path
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.client: Optional[StdioMcpClient] = None
        self.runner: Optional[MCPTestRunner] = None

    async def setup(self):
        """Setup the test environment."""
        # Add server path to args if not already present
        if '--directory' not in self.args:
            self.args.extend(['--directory', self.server_path])

        # Set default environment variables
        default_env = {'FASTMCP_LOG_LEVEL': 'ERROR', 'PYTHONPATH': self.server_path}
        default_env.update(self.env)

        self.client = StdioMcpClient(self.command, self.args, default_env)
        self.runner = MCPTestRunner(self.client)

    async def teardown(self):
        """Cleanup the test environment."""
        if self.client:
            await self.client.disconnect()

    async def run_basic_tests(self, expected_config: Dict[str, Any]) -> List[TestResult]:
        """Run basic protocol tests."""
        if not self.runner:
            raise RuntimeError('Test not set up. Call setup() first.')

        return await self.runner.run_tests(expected_config)

    async def run_custom_test(self, test_config: Dict[str, Any]) -> TestResult:
        """Run a single custom test."""
        if not self.client:
            raise RuntimeError('Test not set up. Call setup() first.')

        try:
            await self.client.connect()

            test_type = test_config.get('type')
            if test_type == TestType.TOOL_CALL.value:
                result = await self.client.call_tool(
                    test_config['tool_name'], test_config.get('arguments', {})
                )
            elif test_type == TestType.RESOURCE_READ.value:
                result = await self.client.read_resource(test_config['uri'])
            elif test_type == TestType.PROMPT_GET.value:
                result = await self.client.get_prompt(
                    test_config['prompt_name'], test_config.get('arguments', {})
                )
            else:
                return TestResult('custom_test', False, f'Unknown test type: {test_type}')

            return TestResult(
                'custom_test',
                True,
                details={
                    'result': result.model_dump() if hasattr(result, 'model_dump') else str(result)
                },
            )

        except Exception as e:
            return TestResult('custom_test', False, str(e))
        finally:
            await self.client.disconnect()


def create_test_config(
    expected_tools: Optional[Dict[str, Any]] = None,
    expected_resources: Optional[Dict[str, Any]] = None,
    expected_prompts: Optional[Dict[str, Any]] = None,
    custom_tests: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Helper function to create test configuration."""
    config = {}

    if expected_tools:
        config['expected_tools'] = expected_tools
    if expected_resources:
        config['expected_resources'] = expected_resources
    if expected_prompts:
        config['expected_prompts'] = expected_prompts
    if custom_tests:
        config['custom_tests'] = custom_tests

    return config


def create_validation_rule(
    rule_type: str, pattern: str, field: Optional[str] = None
) -> Dict[str, Any]:
    """Helper function to create validation rules."""
    rule = {'type': rule_type, 'pattern': pattern}
    if field:
        rule['field'] = field
    return rule


def create_tool_test_config(
    tool_name: str,
    arguments: Dict[str, Any],
    validation_rules: Optional[List[Dict[str, Any]]] = None,
    test_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper function to create tool call test configuration."""
    config = {'type': TestType.TOOL_CALL.value, 'tool_name': tool_name, 'arguments': arguments}

    if validation_rules:
        config['validation'] = validation_rules

    if test_name:
        config['name'] = test_name

    return config


def create_resource_test_config(
    uri: str,
    validation_rules: Optional[List[Dict[str, Any]]] = None,
    test_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper function to create resource read test configuration."""
    config = {'type': TestType.RESOURCE_READ.value, 'uri': uri}

    if validation_rules:
        config['validation'] = validation_rules

    if test_name:
        config['name'] = test_name

    return config


def create_prompt_test_config(
    prompt_name: str,
    arguments: Dict[str, Any],
    validation_rules: Optional[List[Dict[str, Any]]] = None,
    test_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper function to create prompt get test configuration."""
    config = {
        'type': TestType.PROMPT_GET.value,
        'prompt_name': prompt_name,
        'arguments': arguments,
    }

    if validation_rules:
        config['validation'] = validation_rules

    if test_name:
        config['name'] = test_name

    return config


def assert_test_results(results: List[TestResult], expected_success_count: Optional[int] = None):
    """Assert test results meet expectations."""
    if expected_success_count is not None:
        success_count = sum(1 for result in results if result.success)
        assert success_count == expected_success_count, (
            f'Expected {expected_success_count} successful tests, got {success_count}'
        )

    # Check for any failed tests
    failed_tests = [result for result in results if not result.success]
    if failed_tests:
        error_messages = [f'{result.name}: {result.error_message}' for result in failed_tests]
        raise AssertionError('Some tests failed:\n' + '\n'.join(error_messages))


def get_server_path(server_name: str) -> str:
    """Get the absolute path to a server directory."""
    # Assuming we're running from the root of the mcp repository
    current_dir = os.getcwd()
    server_path = os.path.join(current_dir, 'src', server_name)

    if not os.path.exists(server_path):
        raise ValueError(f'Server path does not exist: {server_path}')

    return os.path.abspath(server_path)
