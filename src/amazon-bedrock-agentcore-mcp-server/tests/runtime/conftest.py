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

"""Shared fixtures for AgentCore Runtime unit tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_ctx():
    """Create a mock MCP context."""
    ctx = MagicMock()
    ctx.error = AsyncMock()
    ctx.info = AsyncMock()
    return ctx


@pytest.fixture
def mock_control_client():
    """Create a mock bedrock-agentcore-control boto3 client."""
    return MagicMock()


@pytest.fixture
def mock_data_client():
    """Create a mock bedrock-agentcore boto3 client."""
    return MagicMock()


@pytest.fixture
def control_factory(mock_control_client):
    """Create a factory returning the mock control client."""
    return lambda: mock_control_client


@pytest.fixture
def data_factory(mock_data_client):
    """Create a factory returning the mock data client."""
    return lambda: mock_data_client
