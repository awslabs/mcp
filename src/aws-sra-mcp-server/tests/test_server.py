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
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)
from mcp import McpError


@pytest.mark.asyncio
async def test_get_github_token_from_env():
    """Test get_github_token when token is in environment."""
    from awslabs.aws_sra_mcp_server.server import get_github_token

    mock_ctx = MagicMock()

    with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
        token = await get_github_token(mock_ctx)
        assert token == "test-token"


@pytest.mark.asyncio
async def test_get_github_token_accepted_elicitation():
    """Test get_github_token when user provides token via elicitation."""
    from awslabs.aws_sra_mcp_server.server import get_github_token

    mock_ctx = AsyncMock()
    mock_ctx.elicit.return_value = AcceptedElicitation(data="user-provided-token")

    with patch.dict(os.environ, {}, clear=True):
        token = await get_github_token(mock_ctx)
        assert token == "user-provided-token"
        mock_ctx.warning.assert_called_once()


@pytest.mark.asyncio
async def test_get_github_token_declined_elicitation():
    """Test get_github_token when user declines to provide token."""
    from awslabs.aws_sra_mcp_server.server import get_github_token

    mock_ctx = AsyncMock()
    mock_ctx.elicit.return_value = DeclinedElicitation()

    with patch.dict(os.environ, {}, clear=True):
        token = await get_github_token(mock_ctx)
        assert token == ""
        mock_ctx.warning.assert_called_once()


@pytest.mark.asyncio
async def test_get_github_token_cancelled_elicitation():
    """Test get_github_token when user cancels elicitation."""
    from awslabs.aws_sra_mcp_server.server import get_github_token

    mock_ctx = AsyncMock()
    mock_ctx.elicit.return_value = CancelledElicitation()

    with patch.dict(os.environ, {}, clear=True):
        token = await get_github_token(mock_ctx)
        assert token is None
        mock_ctx.warning.assert_called_once()


@pytest.mark.asyncio
async def test_get_github_token_mcp_error():
    """Test get_github_token when McpError occurs."""
    from mcp.types import ErrorData

    from awslabs.aws_sra_mcp_server.server import get_github_token

    mock_ctx = AsyncMock()
    error_data = ErrorData(code=-1, message="Elicitation not supported")
    mock_ctx.elicit.side_effect = McpError(error_data)

    with patch.dict(os.environ, {}, clear=True):
        token = await get_github_token(mock_ctx)
        assert token is None
        mock_ctx.warning.assert_called_once()


@pytest.mark.asyncio
async def test_get_github_token_other_mcp_error():
    """Test get_github_token when other McpError occurs."""
    from mcp.types import ErrorData

    from awslabs.aws_sra_mcp_server.server import get_github_token

    mock_ctx = AsyncMock()
    error_data = ErrorData(code=-1, message="Other error")
    mock_ctx.elicit.side_effect = McpError(error_data)

    with patch.dict(os.environ, {}, clear=True):
        token = await get_github_token(mock_ctx)
        assert token is None
        mock_ctx.warning.assert_called_once()
        mock_ctx.error.assert_called_once()


# Note: The MCP tool functions are decorated and not directly testable
# They are tested through integration tests in other test files


def test_main():
    """Test main function."""
    from awslabs.aws_sra_mcp_server.server import MCP

    with patch.object(MCP, "run") as mock_run:
        from awslabs.aws_sra_mcp_server.server import main

        main()
        mock_run.assert_called_once()
