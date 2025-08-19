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

"""Tests for the create_api operation."""

import pytest
from awslabs.aws_appsync_mcp_server.decorators import set_write_allowed, write_operation
from awslabs.aws_appsync_mcp_server.operations.create_api import create_api_operation
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_api():
    """Test create_api tool."""
    mock_client = MagicMock()
    mock_response = {
        'api': {
            'apiId': 'test-api-id',
            'name': 'test-api',
            'ownerContact': 'test@example.com',
            'tags': {'Environment': 'test'},
            'apiArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id',
            'created': '2024-01-01T00:00:00Z',
        }
    }
    mock_client.create_api.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_operation(
            name='test-api', owner_contact='test@example.com', tags={'Environment': 'test'}
        )

        mock_client.create_api.assert_called_once_with(
            name='test-api', ownerContact='test@example.com', tags={'Environment': 'test'}
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_minimal():
    """Test create_api tool with minimal parameters."""
    mock_client = MagicMock()
    mock_response = {
        'api': {
            'apiId': 'test-api-id',
            'name': 'test-api',
            'apiArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id',
        }
    }
    mock_client.create_api.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_operation(name='test-api')

        mock_client.create_api.assert_called_once_with(name='test-api')
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_write_operation_blocked():
    """Test that create_api is blocked when write operations are disabled."""
    # Disable write operations
    set_write_allowed(False)

    @write_operation
    async def mock_create_api():
        return 'should not execute'

    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await mock_create_api()


@pytest.mark.asyncio
async def test_create_api_write_operation_allowed():
    """Test that create_api works when write operations are enabled."""
    # Enable write operations
    set_write_allowed(True)

    @write_operation
    async def mock_create_api():
        return 'success'

    result = await mock_create_api()
    assert result == 'success'
