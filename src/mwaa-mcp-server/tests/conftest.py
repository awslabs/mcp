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

"""Shared test fixtures for the MWAA MCP Server tests."""

import pytest
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_ctx():
    """Create a mock MCP Context with async methods."""
    ctx = MagicMock(spec=Context)
    ctx.error = AsyncMock()
    ctx.info = AsyncMock()
    ctx.warning = AsyncMock()
    return ctx


@pytest.fixture
def mock_mwaa_client():
    """Create a mock MWAA boto3 client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server instance."""
    mcp = MagicMock()
    return mcp
