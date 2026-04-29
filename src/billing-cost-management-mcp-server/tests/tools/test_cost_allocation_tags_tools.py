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

"""Unit tests for the cost_allocation_tags_tools module.

These tests verify the functionality of the Cost Allocation Tags API tools, including:
- Listing cost allocation tags with various filters
- Listing cost allocation tag backfill history
- Pagination handling
- Error handling for API exceptions and invalid inputs
"""

import fastmcp
import importlib
import json
import pytest
from awslabs.billing_cost_management_mcp_server.tools.cost_allocation_tags_tools import (
    cost_allocation_tags_server,
)
from botocore.exceptions import ClientError
from fastmcp import Context
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


def _reload_with_identity_decorator() -> Any:
    """Reload module with FastMCP.tool patched to return the original function."""
    from awslabs.billing_cost_management_mcp_server.tools import (
        cost_allocation_tags_tools as mod,
    )

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(mod)
        return mod


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def mock_ce_client():
    """Create a mock Cost Explorer boto3 client."""
    mock_client = MagicMock()

    mock_client.list_cost_allocation_tags.return_value = {
        'CostAllocationTags': [
            {
                'TagKey': 'Environment',
                'Type': 'UserDefined',
                'Status': 'Active',
                'LastUpdatedDate': '2024-01-15',
                'LastUsedDate': '2024-03-01',
            },
            {
                'TagKey': 'aws:createdBy',
                'Type': 'AWSGenerated',
                'Status': 'Active',
                'LastUpdatedDate': '2024-02-01',
                'LastUsedDate': '2024-03-01',
            },
        ],
    }

    mock_client.list_cost_allocation_tag_backfill_history.return_value = {
        'BackfillRequests': [
            {
                'BackfillFrom': '2024-01-01T00:00:00Z',
                'RequestedAt': '2024-03-15T10:00:00Z',
                'CompletedAt': '2024-03-15T12:00:00Z',
                'LastUpdatedAt': '2024-03-15T12:00:00Z',
                'BackfillStatus': 'SUCCEEDED',
            },
        ],
    }

    return mock_client


def test_cost_allocation_tags_server_initialization():
    """Test that the cost_allocation_tags_server is properly initialized."""
    assert cost_allocation_tags_server.name == 'cost-allocation-tags-tools'
    instructions = cost_allocation_tags_server.instructions
    assert instructions is not None
    assert 'Cost Allocation Tags' in instructions if instructions else False


@pytest.mark.asyncio
class TestListCostAllocationTags:
    """Tests for list_cost_allocation_tags function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_allocation_tags_tools.create_aws_client'
    )
    async def test_list_tags_no_filters(self, mock_create_client, mock_context, mock_ce_client):
        """Test listing tags with no filters."""
        mod = _reload_with_identity_decorator()
        mock_create_client.return_value = mock_ce_client

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tags(mock_context)

        assert result['status'] == 'success'
        assert len(result['data']['CostAllocationTags']) == 2

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_allocation_tags_tools.create_aws_client'
    )
    async def test_list_tags_with_status_filter(
        self, mock_create_client, mock_context, mock_ce_client
    ):
        """Test listing tags filtered by status."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tags(mock_context, status='Active')

        mock_ce_client.list_cost_allocation_tags.assert_called_once_with(Status='Active')
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_allocation_tags_tools.create_aws_client'
    )
    async def test_list_tags_with_type_filter(
        self, mock_create_client, mock_context, mock_ce_client
    ):
        """Test listing tags filtered by type."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_type='UserDefined')

        mock_ce_client.list_cost_allocation_tags.assert_called_once_with(Type='UserDefined')
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_allocation_tags_tools.create_aws_client'
    )
    async def test_list_tags_with_tag_keys_filter(
        self, mock_create_client, mock_context, mock_ce_client
    ):
        """Test listing tags filtered by specific tag keys."""
        mod = _reload_with_identity_decorator()
        tag_keys = json.dumps(['Environment', 'Team'])

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys=tag_keys)

        mock_ce_client.list_cost_allocation_tags.assert_called_once_with(
            TagKeys=['Environment', 'Team']
        )
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_allocation_tags_tools.create_aws_client'
    )
    async def test_list_tags_with_max_results(
        self, mock_create_client, mock_context, mock_ce_client
    ):
        """Test listing tags with max_results parameter."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tags(mock_context, max_results=50)

        mock_ce_client.list_cost_allocation_tags.assert_called_once_with(MaxResults=50)
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_allocation_tags_tools.create_aws_client'
    )
    async def test_list_tags_with_all_filters(
        self, mock_create_client, mock_context, mock_ce_client
    ):
        """Test listing tags with all filters combined."""
        mod = _reload_with_identity_decorator()
        tag_keys = json.dumps(['Environment'])

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tags(
                mock_context,
                status='Active',
                tag_keys=tag_keys,
                tag_type='UserDefined',
                max_results=10,
            )

        mock_ce_client.list_cost_allocation_tags.assert_called_once_with(
            Status='Active',
            TagKeys=['Environment'],
            Type='UserDefined',
            MaxResults=10,
        )
        assert result['status'] == 'success'

    async def test_list_tags_with_max_pages(self, mock_context, mock_ce_client):
        """Test listing tags with auto-pagination via max_pages."""
        mod = _reload_with_identity_decorator()
        mock_paginate = AsyncMock(
            return_value=(
                [
                    {'TagKey': 'Environment', 'Type': 'UserDefined', 'Status': 'Active'},
                    {'TagKey': 'Team', 'Type': 'UserDefined', 'Status': 'Active'},
                ],
                {'total_results': 2, 'pages_fetched': 1},
            )
        )

        with (
            patch.object(mod, 'create_aws_client', return_value=mock_ce_client),
            patch.object(mod, 'paginate_aws_response', mock_paginate),
        ):
            result = await mod.list_cost_allocation_tags(mock_context, max_pages=5)

        mock_paginate.assert_called_once()
        assert result['status'] == 'success'
        assert len(result['data']['CostAllocationTags']) == 2
        assert result['data']['Pagination']['total_results'] == 2

    async def test_list_tags_with_next_token(self, mock_context, mock_ce_client):
        """Test listing tags with next_token triggers pagination."""
        mod = _reload_with_identity_decorator()
        mock_paginate = AsyncMock(
            return_value=(
                [{'TagKey': 'CostCenter', 'Type': 'UserDefined', 'Status': 'Active'}],
                {'total_results': 1, 'pages_fetched': 1},
            )
        )

        with (
            patch.object(mod, 'create_aws_client', return_value=mock_ce_client),
            patch.object(mod, 'paginate_aws_response', mock_paginate),
        ):
            result = await mod.list_cost_allocation_tags(mock_context, next_token='abc123')

        mock_paginate.assert_called_once()
        assert result['status'] == 'success'

    async def test_list_tags_error(self, mock_context):
        """Test error handling for exceptions."""
        mod = _reload_with_identity_decorator()
        error = ClientError(
            {'Error': {'Code': 'LimitExceededException', 'Message': 'Too many tags'}},
            'ListCostAllocationTags',
        )
        mock_handle = AsyncMock(return_value={'status': 'error', 'message': 'Too many tags'})

        with (
            patch.object(mod, 'create_aws_client', side_effect=error),
            patch.object(mod, 'handle_aws_error', mock_handle),
        ):
            result = await mod.list_cost_allocation_tags(mock_context)

        mock_handle.assert_called_once_with(
            mock_context, error, 'ListCostAllocationTags', 'Cost Explorer'
        )
        assert result['status'] == 'error'

    async def test_list_tags_invalid_tag_keys_json(self, mock_context):
        """Test error handling for invalid JSON in tag_keys."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=MagicMock()):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys='not valid json')

        assert result['status'] == 'error'
        assert 'Invalid JSON for tag_keys parameter' in result['data']['message']


@pytest.mark.asyncio
class TestListCostAllocationTagBackfillHistory:
    """Tests for list_cost_allocation_tag_backfill_history function."""

    async def test_list_backfill_no_filters(self, mock_context, mock_ce_client):
        """Test listing backfill history with no filters."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tag_backfill_history(mock_context)

        mock_ce_client.list_cost_allocation_tag_backfill_history.assert_called_once_with()
        assert result['status'] == 'success'
        assert len(result['data']['BackfillRequests']) == 1

    async def test_list_backfill_with_max_results(self, mock_context, mock_ce_client):
        """Test listing backfill history with max_results."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tag_backfill_history(
                mock_context, max_results=1
            )

        mock_ce_client.list_cost_allocation_tag_backfill_history.assert_called_once_with(
            MaxResults=1
        )
        assert result['status'] == 'success'

    async def test_list_backfill_with_max_pages(self, mock_context, mock_ce_client):
        """Test listing backfill history with auto-pagination."""
        mod = _reload_with_identity_decorator()
        mock_paginate = AsyncMock(
            return_value=(
                [{'BackfillFrom': '2024-01-01T00:00:00Z', 'BackfillStatus': 'SUCCEEDED'}],
                {'total_results': 1, 'pages_fetched': 1},
            )
        )

        with (
            patch.object(mod, 'create_aws_client', return_value=mock_ce_client),
            patch.object(mod, 'paginate_aws_response', mock_paginate),
        ):
            result = await mod.list_cost_allocation_tag_backfill_history(
                mock_context, max_pages=10
            )

        mock_paginate.assert_called_once()
        assert result['status'] == 'success'
        assert len(result['data']['BackfillRequests']) == 1

    async def test_list_backfill_with_next_token(self, mock_context, mock_ce_client):
        """Test listing backfill history with next_token triggers pagination."""
        mod = _reload_with_identity_decorator()
        mock_paginate = AsyncMock(
            return_value=(
                [{'BackfillFrom': '2024-02-01T00:00:00Z', 'BackfillStatus': 'PROCESSING'}],
                {'total_results': 1, 'pages_fetched': 1},
            )
        )

        with (
            patch.object(mod, 'create_aws_client', return_value=mock_ce_client),
            patch.object(mod, 'paginate_aws_response', mock_paginate),
        ):
            result = await mod.list_cost_allocation_tag_backfill_history(
                mock_context, next_token='token123'
            )

        mock_paginate.assert_called_once()
        assert result['status'] == 'success'

    async def test_list_backfill_error(self, mock_context):
        """Test error handling for backfill history."""
        mod = _reload_with_identity_decorator()
        error = Exception('API error')
        mock_handle = AsyncMock(return_value={'status': 'error', 'message': 'API error'})

        with (
            patch.object(mod, 'create_aws_client', side_effect=error),
            patch.object(mod, 'handle_aws_error', mock_handle),
        ):
            result = await mod.list_cost_allocation_tag_backfill_history(mock_context)

        mock_handle.assert_called_once_with(
            mock_context, error, 'ListCostAllocationTagBackfillHistory', 'Cost Explorer'
        )
        assert result['status'] == 'error'
