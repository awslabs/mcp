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

from typing import List, Tuple

import pytest
from fastmcp import Client

from awslabs.aws_sra_mcp_server.server import MCP


@pytest.fixture
def mock_context():
    """Create a mock MCP context for testing."""

    class MockContext:
        def __init__(self):
            self.errors: List[str] = []
            self.info_messages: List[str] = []
            self.debug_messages: List[str] = []
            self.warning_messages: List[str] = []
            self.progress_reports: List[Tuple[int, int]] = []

        async def error(self, message: str) -> None:
            self.errors.append(message)

        async def info(self, message: str) -> None:
            self.info_messages.append(message)

        async def debug(self, message: str) -> None:
            self.debug_messages.append(message)

        async def warning(self, message: str) -> None:
            self.warning_messages.append(message)

        async def report_progress(self, current: int, total: int) -> None:
            self.progress_reports.append((current, total))

    return MockContext()


@pytest.fixture
def client():
    """Create a FastMCP client for testing."""
    return Client(MCP)


@pytest.fixture
async def call_tool():
    """Helper function to call an MCP tool as an integration test"""

    async def _call_tool(client, tool_name, **kwargs):
        params = {}
        for key, value in kwargs.items():
            params[key] = value
        return await client.call_tool(tool_name, params)

    return _call_tool
