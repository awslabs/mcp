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

"""Shared pytest fixtures for aws-transform-mcp-server tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def bypass_instruction_gate(monkeypatch):
    """Bypass the load_instructions gate for all tests by default.

    Tests that need the real gate (test_guidance_nudge.py, test_load_instructions.py)
    override this by patching at the tool module level in their own fixtures.
    """
    _noop = lambda job_id: None  # noqa: E731
    monkeypatch.setattr(
        'awslabs.aws_transform_mcp_server.tools.get_resource.job_needs_check', _noop
    )
    monkeypatch.setattr(
        'awslabs.aws_transform_mcp_server.tools.list_resources.job_needs_check', _noop
    )
    monkeypatch.setattr('awslabs.aws_transform_mcp_server.tools.hitl.job_needs_check', _noop)
    monkeypatch.setattr('awslabs.aws_transform_mcp_server.tools.job_status.job_needs_check', _noop)
    import importlib

    chat_send_mod = importlib.import_module(
        'awslabs.aws_transform_mcp_server.tools.chat.send_message'
    )
    monkeypatch.setattr(chat_send_mod, 'job_needs_check', _noop)


@pytest.fixture
def mock_mcp():
    """Return a mock MCP server instance."""
    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return mcp


@pytest.fixture
def mock_context():
    """Return a mock MCP request context."""
    ctx = AsyncMock()
    ctx.info = MagicMock(return_value='mock-context')
    return ctx
