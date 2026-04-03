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
"""Test exception handling in server.py get_all_counts function."""

import pytest
from awslabs.openapi_mcp_server.server import get_all_counts
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_get_all_counts_attribute_error_handling():
    """Test that AttributeError in get_resource_templates is handled properly."""
    # Create a mock server with get_resource_templates that raises AttributeError
    mock_server = MagicMock()
    mock_server.get_prompts = AsyncMock(return_value=[])
    mock_server.get_tools = AsyncMock(return_value=[])
    mock_server.get_resources = AsyncMock(return_value=[])

    # Mock hasattr to return True, but get_resource_templates raises AttributeError
    mock_server.get_resource_templates = AsyncMock(
        side_effect=AttributeError('Method not implemented')
    )

    # Mock the main function's get_all_counts function
    with patch('awslabs.openapi_mcp_server.server.logger') as mock_logger:
        # Execute the function
        result = await get_all_counts(mock_server)

        # Verify the result
        assert result == (0, 0, 0, 0)

        # Verify that the debug log was called for AttributeError
        mock_logger.debug.assert_called_once()
        assert 'get_resource_templates exists but not implemented' in str(
            mock_logger.debug.call_args
        )


@pytest.mark.asyncio
async def test_get_all_counts_general_exception_handling():
    """Test that general Exception in get_resource_templates is handled properly."""
    # Create a mock server with get_resource_templates that raises a general Exception
    mock_server = MagicMock()
    mock_server.get_prompts = AsyncMock(return_value=[])
    mock_server.get_tools = AsyncMock(return_value=[])
    mock_server.get_resources = AsyncMock(return_value=[])

    # Mock hasattr to return True, but get_resource_templates raises a general Exception
    mock_server.get_resource_templates = AsyncMock(side_effect=RuntimeError('Unexpected error'))

    # Mock the main function's get_all_counts function
    with patch('awslabs.openapi_mcp_server.server.logger') as mock_logger:
        # Execute the function
        result = await get_all_counts(mock_server)

        # Verify the result
        assert result == (0, 0, 0, 0)

        # Verify that the warning log was called for general Exception
        mock_logger.warning.assert_called_once()
        assert 'Error retrieving resource templates' in str(mock_logger.warning.call_args)
