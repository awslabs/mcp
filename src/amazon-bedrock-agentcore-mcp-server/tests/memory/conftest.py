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

"""Shared fixtures for AgentCore Memory tool tests.

This file must be placed at tests/memory/conftest.py — NOT inside
the tools/memory/ source package.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_ctx():
    """Create a mock MCP Context."""
    ctx = MagicMock()
    ctx.error = AsyncMock()
    ctx.info = AsyncMock()
    return ctx


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 client for Memory APIs."""
    return MagicMock()


@pytest.fixture
def client_factory(mock_boto3_client):
    """Create a client factory that returns the mock boto3 client."""
    return lambda: mock_boto3_client
