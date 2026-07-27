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

"""Basic integration test for aws-transform-mcp-server using the official MCP SDK."""

import asyncio
import logging
import os
import pytest
import sys


# Add the testing framework to the path
testing_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'testing')
sys.path.insert(0, testing_path)
parent_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.insert(0, parent_path)

from testing.pytest_utils import (  # noqa: E402
    MCPTestBase,
    assert_test_results,
    create_test_config,
    create_tool_test_config,
    create_validation_rule,
    setup_logging,
)


# Setup constants
SERVER_PY = 'awslabs/aws_transform_mcp_server/server.py'
EXPECTED_TOOL_NAMES = [
    'configure',
    'get_status',
    'switch_profile',
    'create_workspace',
    'delete_workspace',
    'create_job',
    'control_job',
    'delete_job',
    'complete_task',
    'upload_artifact',
    'send_message',
    'load_instructions',
    'create_connector',
    'accept_connector',
    'list_resources',
    'get_resource',
    'manage_collaborator',
    'get_job_status',
    'adaptive_poll',
]
NUMBER_OF_TOOLS = len(EXPECTED_TOOL_NAMES)

# Setup logging
setup_logging('INFO')
logger = logging.getLogger(__name__)


class TestAWSTransformMCPServer:
    """Basic integration tests for AWS Transform MCP Server."""

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Setup test environment."""
        self.server_path = os.path.join(os.path.dirname(__file__), '..')
        self.test_instance = None
        yield
        if self.test_instance:
            asyncio.run(self.test_instance.teardown())

    def _make_args(self):
        return ['--directory', self.server_path, 'run', '--frozen', SERVER_PY]

    @pytest.mark.asyncio
    async def test_basic_protocol(self):
        """Test basic MCP protocol functionality — server starts and registers all tools."""
        self.test_instance = MCPTestBase(
            server_path=self.server_path,
            command='uv',
            args=self._make_args(),
            env={'FASTMCP_LOG_LEVEL': 'ERROR'},
        )
        await self.test_instance.setup()

        expected_config = create_test_config(
            expected_tools={
                'count': NUMBER_OF_TOOLS,
                'names': EXPECTED_TOOL_NAMES,
            },
            expected_resources={'count': 0},
            expected_prompts={'count': 0},
        )

        results = await self.test_instance.run_basic_tests(expected_config)
        assert_test_results(results, expected_success_count=6)

    @pytest.mark.asyncio
    async def test_get_status_tool(self):
        """Test get_status tool — works without auth and returns version info."""
        self.test_instance = MCPTestBase(
            server_path=self.server_path,
            command='uv',
            args=self._make_args(),
            env={'FASTMCP_LOG_LEVEL': 'ERROR'},
        )
        await self.test_instance.setup()

        test_config = create_tool_test_config(
            tool_name='get_status',
            arguments={},
            validation_rules=[
                create_validation_rule('contains', 'version', 'content'),
            ],
        )

        result = await self.test_instance.run_custom_test(test_config)
        assert result.success, f'get_status test failed: {result.error_message}'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
