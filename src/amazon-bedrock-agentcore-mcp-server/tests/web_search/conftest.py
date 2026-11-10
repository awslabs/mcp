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

"""Shared fixtures for AgentCore Web Search tool tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_ctx():
    """Create a mock MCP Context."""
    ctx = MagicMock()
    ctx.error = AsyncMock()
    ctx.info = AsyncMock()
    return ctx


@pytest.fixture
def mock_boto3_client():
    """Patch the web search client with a mock boto3 client."""
    client = MagicMock()
    with patch(
        'awslabs.amazon_bedrock_agentcore_mcp_server.tools.web_search.search.get_web_search_client',
        return_value=client,
    ):
        yield client
