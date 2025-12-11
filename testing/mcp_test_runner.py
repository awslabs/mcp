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
"""MCP Test Runner for orchestrating test execution and lifecycle management."""

import logging
import re
from .mcp_test_client import StdioMcpClient
from .types import TestType
from dataclasses import dataclass
from mcp import types
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Represents the result of a test execution."""

    name: str
    success: bool
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationRule:
    """Represents a validation rule for test responses."""

    type: str  # "exact", "contains", "regex"
    pattern: str
    field: Optional[str] = None  # If None, validates the entire response


class MCPTestRunner:
    """Runner for executing MCP server tests."""

    def __init__(self, client: StdioMcpClient):
        """Initialize the MCP test runner."""
        self.client = client
        self.test_results: List[TestResult] = []

    async def run_tests(self, test_config: Dict[str, Any]) -> List[TestResult]:
        """Run the complete test pipeline."""
        try:
            # Connect to the server
            logger.info('Connecting to MCP server...')
            await self.client.connect()
            self.test_results.append(TestResult('connection', True))

            # Run basic protocol tests
            await self._run_protocol_tests(test_config)

            # Run custom tests if specified
            if 'custom_tests' in test_config:
                await self._run_custom_tests(test_config['custom_tests'])

            return self.test_results

        except Exception as e:
            logger.error(f'Test execution failed: {e}')
            self.test_results.append(TestResult('test_execution', False, str(e)))
            return self.test_results
        finally:
            await self.client.disconnect()

    async def _run_protocol_tests(self, test_config: Dict[str, Any]):
        """Run basic MCP protocol tests."""
        # Test ping
        logger.info('Testing ping...')
        ping_success = await self.client.ping()
        self.test_results.append(TestResult('ping', ping_success))

        # Test capabilities discovery
        logger.info('Testing capabilities discovery...')
        capabilities = self.client.capabilities
        capabilities_success = capabilities is not None
        self.test_results.append(TestResult('capabilities_discovery', capabilities_success))

        # Test tools listing
        logger.info('Testing tools listing...')
        tools = await self.client.list_tools()
        tools_success = await self._validate_tools(tools, test_config.get('expected_tools', {}))
        self.test_results.append(TestResult('tools_listing', tools_success))

        # Test resources listing
        logger.info('Testing resources listing...')
        resources = await self.client.list_resources()
        resources_success = await self._validate_resources(
            resources, test_config.get('expected_resources', {})
        )
        self.test_results.append(TestResult('resources_listing', resources_success))

        # Test prompts listing
        logger.info('Testing prompts listing...')
        prompts = await self.client.list_prompts()
        prompts_success = await self._validate_prompts(
            prompts, test_config.get('expected_prompts', {})
        )
        self.test_results.append(TestResult('prompts_listing', prompts_success))

    async def _validate_tools(self, tools: List[types.Tool], expected: Dict[str, Any]) -> bool:
        """Validate tools against expected configuration."""
        try:
            # Check count if specified
            if 'count' in expected:
                if len(tools) != expected['count']:
                    logger.error(f'Expected {expected["count"]} tools, got {len(tools)}')
                    return False

            # Check names if specified
            if 'names' in expected:
                actual_names = {tool.name for tool in tools}
                expected_names = set(expected['names'])

                # Check for missing tools
                missing = expected_names - actual_names
                if missing:
                    logger.error(f'Missing expected tools: {missing}')
                    return False

                # Check for unexpected tools
                unexpected = actual_names - expected_names
                if unexpected:
                    logger.warning(f'Unexpected tools found: {unexpected}')

            # Validate tool names length
            for tool in tools:
                if len(tool.name) >= 64:
                    logger.error(f"Tool name '{tool.name}' is too long (>= 64 characters)")
                    return False

            return True

        except Exception as e:
            logger.error(f'Tool validation failed: {e}')
            return False

    async def _validate_resources(
        self, resources: List[types.Resource], expected: Dict[str, Any]
    ) -> bool:
        """Validate resources against expected configuration."""
        try:
            # Check count if specified
            if 'count' in expected:
                if len(resources) != expected['count']:
                    logger.error(f'Expected {expected["count"]} resources, got {len(resources)}')
                    return False

            # Check names if specified
            if 'names' in expected:
                actual_names = {resource.name for resource in resources}
                expected_names = set(expected['names'])

                # Check for missing resources
                missing = expected_names - actual_names
                if missing:
                    logger.error(f'Missing expected resources: {missing}')
                    return False

                # Check for unexpected resources
                unexpected = actual_names - expected_names
                if unexpected:
                    logger.warning(f'Unexpected resources found: {unexpected}')

            # Validate resource names length
            for resource in resources:
                if len(resource.name) >= 64:
                    logger.error(f"Resource name '{resource.name}' is too long (>= 64 characters)")
                    return False

            return True

        except Exception as e:
            logger.error(f'Resource validation failed: {e}')
            return False

    async def _validate_prompts(
        self, prompts: List[types.Prompt], expected: Dict[str, Any]
    ) -> bool:
        """Validate prompts against expected configuration."""
        try:
            # Check count if specified
            if 'count' in expected:
                if len(prompts) != expected['count']:
                    logger.error(f'Expected {expected["count"]} prompts, got {len(prompts)}')
                    return False

            # Check names if specified
            if 'names' in expected:
                actual_names = {prompt.name for prompt in prompts}
                expected_names = set(expected['names'])

                # Check for missing prompts
                missing = expected_names - actual_names
                if missing:
                    logger.error(f'Missing expected prompts: {missing}')
                    return False

                # Check for unexpected prompts
                unexpected = actual_names - expected_names
                if unexpected:
                    logger.warning(f'Unexpected prompts found: {unexpected}')

            # Validate prompt names length
            for prompt in prompts:
                if len(prompt.name) >= 64:
                    logger.error(f"Prompt name '{prompt.name}' is too long (>= 64 characters)")
                    return False

            return True

        except Exception as e:
            logger.error(f'Prompt validation failed: {e}')
            return False

    async def _run_custom_tests(self, custom_tests: List[Dict[str, Any]]):
        """Run custom tests defined in the configuration."""
        for test in custom_tests:
            test_name = test.get('name', 'custom_test')
            logger.info(f'Running custom test: {test_name}')

            try:
                test_type = test.get('type')
                if test_type == TestType.TOOL_CALL.value:
                    result = await self._run_tool_test(test)
                elif test_type == TestType.RESOURCE_READ.value:
                    result = await self._run_resource_test(test)
                elif test_type == TestType.PROMPT_GET.value:
                    result = await self._run_prompt_test(test)
                else:
                    result = TestResult(test_name, False, f'Unknown test type: {test_type}')

                self.test_results.append(result)

            except Exception as e:
                logger.error(f'Custom test {test_name} failed: {e}')
                self.test_results.append(TestResult(test_name, False, str(e)))

    async def _run_tool_test(self, test: Dict[str, Any]) -> TestResult:
        """Run a tool call test."""
        try:
            tool_name = test['tool_name']
            arguments = test.get('arguments', {})

            result = await self.client.call_tool(tool_name, arguments)

            # Validate response if validation rules are provided
            if 'validation' in test:
                validation_success = await self._validate_response(result, test['validation'])
                return TestResult(
                    f'tool_call_{tool_name}',
                    validation_success,
                    details={
                        'result': result.model_dump()
                        if hasattr(result, 'model_dump')
                        else str(result)
                    },
                )

            return TestResult(
                f'tool_call_{tool_name}',
                True,
                details={
                    'result': result.model_dump() if hasattr(result, 'model_dump') else str(result)
                },
            )

        except Exception as e:
            return TestResult(f'tool_call_{test.get("tool_name", "unknown")}', False, str(e))

    async def _run_resource_test(self, test: Dict[str, Any]) -> TestResult:
        """Run a resource read test."""
        try:
            uri = test['uri']

            result = await self.client.read_resource(uri)

            # Validate response if validation rules are provided
            if 'validation' in test:
                validation_success = await self._validate_response(result, test['validation'])
                return TestResult(
                    f'resource_read_{uri}',
                    validation_success,
                    details={
                        'result': result.model_dump()
                        if hasattr(result, 'model_dump')
                        else str(result)
                    },
                )

            return TestResult(
                f'resource_read_{uri}',
                True,
                details={
                    'result': result.model_dump() if hasattr(result, 'model_dump') else str(result)
                },
            )

        except Exception as e:
            return TestResult(f'resource_read_{test.get("uri", "unknown")}', False, str(e))

    async def _run_prompt_test(self, test: Dict[str, Any]) -> TestResult:
        """Run a prompt get test."""
        try:
            prompt_name = test['prompt_name']
            arguments = test.get('arguments', {})

            result = await self.client.get_prompt(prompt_name, arguments)

            # Validate response if validation rules are provided
            if 'validation' in test:
                validation_success = await self._validate_response(result, test['validation'])
                return TestResult(
                    f'prompt_get_{prompt_name}',
                    validation_success,
                    details={
                        'result': result.model_dump()
                        if hasattr(result, 'model_dump')
                        else str(result)
                    },
                )

            return TestResult(
                f'prompt_get_{prompt_name}',
                True,
                details={
                    'result': result.model_dump() if hasattr(result, 'model_dump') else str(result)
                },
            )

        except Exception as e:
            return TestResult(f'prompt_get_{test.get("prompt_name", "unknown")}', False, str(e))

    async def _validate_response(
        self, response: Any, validation_rules: List[Dict[str, Any]]
    ) -> bool:
        """Validate response against validation rules."""
        try:
            for rule in validation_rules:
                validation_rule = ValidationRule(**rule)

                # Get the value to validate
                if validation_rule.field:
                    # Try to get the field from the response
                    if hasattr(response, validation_rule.field):
                        value = getattr(response, validation_rule.field)
                    elif isinstance(response, dict):
                        value = response.get(validation_rule.field, '')
                    else:
                        value = str(response)
                else:
                    value = str(response)

                # Apply validation based on type
                if validation_rule.type == 'exact':
                    if value != validation_rule.pattern:
                        logger.error(
                            f"Exact match failed: expected '{validation_rule.pattern}', got '{value}'"
                        )
                        return False

                elif validation_rule.type == 'contains':
                    if validation_rule.pattern not in value:
                        logger.error(
                            f"Contains validation failed: '{validation_rule.pattern}' not found in '{value}'"
                        )
                        return False

                elif validation_rule.type == 'regex':
                    if not re.search(validation_rule.pattern, value):
                        logger.error(
                            f"Regex validation failed: pattern '{validation_rule.pattern}' not found in '{value}'"
                        )
                        return False

                else:
                    logger.error(f'Unknown validation type: {validation_rule.type}')
                    return False

            return True

        except Exception as e:
            logger.error(f'Response validation failed: {e}')
            return False
