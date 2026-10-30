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

import asyncio
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


@pytest.fixture(scope='module', autouse=True)
def _restore_real_tool_module():
    """Reload the module with the real FastMCP.tool after this file's tests.

    _reload_with_identity_decorator() leaves the module's server with no registered tools;
    restoring it keeps later test files from seeing that state.
    """
    yield
    from awslabs.billing_cost_management_mcp_server.tools import (
        cost_allocation_tags_tools as module,
    )

    importlib.reload(module)


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
    context.warning = AsyncMock()
    context.debug = AsyncMock()
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
        assert result['data']['pagination'] == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 2,
        }

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

        mock_ce_client.list_cost_allocation_tags.assert_called_once_with(
            Status='Active', MaxResults=1000
        )
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

        mock_ce_client.list_cost_allocation_tags.assert_called_once_with(
            Type='UserDefined', MaxResults=1000
        )
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
            TagKeys=['Environment', 'Team'], MaxResults=1000
        )
        assert result['status'] == 'success'

    async def test_list_tags_with_all_filters(self, mock_context, mock_ce_client):
        """All filters are sent together; a key lookup always asks for a full page."""
        mod = _reload_with_identity_decorator()
        tag_keys = json.dumps(['Environment'])

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tags(
                mock_context,
                status='Active',
                tag_keys=tag_keys,
                tag_type='UserDefined',
                max_items=10,
            )

        mock_ce_client.list_cost_allocation_tags.assert_called_once_with(
            Status='Active',
            TagKeys=['Environment'],
            Type='UserDefined',
            MaxResults=1000,
        )
        assert result['status'] == 'success'

    async def test_list_tags_without_max_items_fetches_every_page(self, mock_context):
        """Without max_items every page is fetched at the largest page size."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_allocation_tags.side_effect = [
            {'CostAllocationTags': [{'TagKey': 'A'}], 'NextToken': 't1'},
            {'CostAllocationTags': [{'TagKey': 'B'}], 'NextToken': 't2'},
            {'CostAllocationTags': [{'TagKey': 'C'}]},
        ]

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, status='Active')

        assert [t['TagKey'] for t in result['data']['CostAllocationTags']] == ['A', 'B', 'C']
        assert 'complete_dataset' not in result['data']
        assert result['data']['pagination']['complete_dataset'] is True
        calls = client.list_cost_allocation_tags.call_args_list
        assert [c.kwargs for c in calls] == [
            {'Status': 'Active', 'MaxResults': 1000},
            {'Status': 'Active', 'MaxResults': 1000, 'NextToken': 't1'},
            {'Status': 'Active', 'MaxResults': 1000, 'NextToken': 't2'},
        ]

    async def test_list_tags_max_items_stops_with_token(self, mock_context):
        """max_items stops after the requested total and returns the service token."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_allocation_tags.side_effect = [
            {'CostAllocationTags': [{'TagKey': 'A'}, {'TagKey': 'B'}], 'NextToken': 't1'},
        ]

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, max_items=2)

        client.list_cost_allocation_tags.assert_called_once_with(MaxResults=2)
        data = result['data']
        assert list(data)[:2] == ['complete_dataset', 'warning']
        assert data['complete_dataset'] is False
        assert data['pagination'] == {
            'complete_dataset': False,
            'has_more': True,
            'next_token': 't1',
            'items_returned': 2,
        }

    async def test_list_tags_continuation_sends_caller_token(self, mock_context):
        """A continuation sends the caller's token and otherwise identical params."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_allocation_tags.return_value = {'CostAllocationTags': [{'TagKey': 'C'}]}

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_type='UserDefined', max_items=2, next_token='t1'
            )

        client.list_cost_allocation_tags.assert_called_once_with(
            Type='UserDefined', MaxResults=2, NextToken='t1'
        )
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_list_tags_invalid_next_token(self, mock_context):
        """A rejected caller token maps to invalid_next_token."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_allocation_tags.side_effect = ClientError(
            {'Error': {'Code': 'InvalidNextTokenException', 'Message': 'bad'}},
            'ListCostAllocationTags',
        )

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, next_token='stale')

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'

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
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'ListCostAllocationTags'
        assert result['service'] == 'Cost Explorer'

    async def test_tag_keys_lookup_fetches_every_match_in_one_request(self, mock_context):
        """max_items applies locally to a key lookup; the request asks for a full page."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_allocation_tags.return_value = {
            'CostAllocationTags': [{'TagKey': 'A'}, {'TagKey': 'B'}, {'TagKey': 'C'}]
        }

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['A', 'B', 'C']), max_items=1
            )

        client.list_cost_allocation_tags.assert_called_once_with(
            TagKeys=['A', 'B', 'C'], MaxResults=1000
        )
        data = result['data']
        assert [t['TagKey'] for t in data['CostAllocationTags']] == ['A']
        assert data['complete_dataset'] is False
        assert data['pagination'] == {
            'complete_dataset': False,
            'has_more': False,
            'next_token': None,
            'items_returned': 1,
        }
        assert 'returned 1 of the 3 tags that match tag_keys' in data['warning']
        assert 'larger max_items' in data['warning']
        assert 'continue with next_token' not in data['warning']

    async def test_tag_keys_lookup_within_max_items_is_complete(self, mock_context):
        """A key lookup with max_items at or above the match count is complete."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_allocation_tags.return_value = {
            'CostAllocationTags': [{'TagKey': 'A'}, {'TagKey': 'B'}]
        }

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['A', 'B', 'Unknown']), max_items=2
            )

        client.list_cost_allocation_tags.assert_called_once_with(
            TagKeys=['A', 'B', 'Unknown'], MaxResults=1000
        )
        data = result['data']
        assert 'complete_dataset' not in data
        assert data['pagination'] == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 2,
        }

    async def test_tag_keys_lookup_returns_each_tag_once(self, mock_context):
        """A key lookup never hands out the service's token, so no tag comes back twice.

        The fake mirrors the service: its token is an offset into TagKeys that advances by
        the number of tags returned, and each page loads the remaining keys in an
        arbitrary order (here reversed). Following that token at MaxResults=1 returns C
        three times, which is what a caller got by following next_token before the fix.
        """
        mod = _reload_with_identity_decorator()
        stored = {'A', 'B', 'C'}

        def list_tags(TagKeys, MaxResults, NextToken=None):
            offset = int(NextToken or 0)
            loaded = [{'TagKey': k} for k in reversed(TagKeys[offset:]) if k in stored]
            if len(loaded) <= MaxResults:
                return {'CostAllocationTags': loaded}
            return {
                'CostAllocationTags': loaded[:MaxResults],
                'NextToken': str(offset + MaxResults),
            }

        client = MagicMock()
        client.list_cost_allocation_tags.side_effect = list_tags
        keys = json.dumps(['A', 'B', 'C'])
        returned = []
        token = None
        with patch.object(mod, 'create_aws_client', return_value=client):
            for _ in range(5):
                result = await mod.list_cost_allocation_tags(
                    mock_context, tag_keys=keys, max_items=1, next_token=token
                )
                returned += [t['TagKey'] for t in result['data']['CostAllocationTags']]
                token = result['data']['pagination']['next_token']
                if token is None:
                    break

        assert len(returned) == len(set(returned))
        assert client.list_cost_allocation_tags.call_count == 1
        assert [
            c.kwargs['MaxResults'] for c in client.list_cost_allocation_tags.call_args_list
        ] == [1000]
        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys=keys)
        assert sorted(t['TagKey'] for t in result['data']['CostAllocationTags']) == [
            'A',
            'B',
            'C',
        ]
        assert result['data']['pagination']['complete_dataset'] is True

    @pytest.mark.parametrize('max_items, kept', [(None, ['A', 'B']), (5, ['A', 'B']), (1, ['A'])])
    async def test_tag_keys_lookup_drops_an_unexpected_service_token(
        self, mock_context, max_items, kept
    ):
        """A token on a key lookup is not followed or returned; the result says it is partial."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_allocation_tags.side_effect = [
            {'CostAllocationTags': [{'TagKey': 'A'}, {'TagKey': 'B'}], 'NextToken': '2'},
            {'CostAllocationTags': [{'TagKey': 'B'}]},
        ]

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['A', 'B']), max_items=max_items
            )

        client.list_cost_allocation_tags.assert_called_once_with(
            TagKeys=['A', 'B'], MaxResults=1000
        )
        data = result['data']
        assert [t['TagKey'] for t in data['CostAllocationTags']] == kept
        assert data['pagination'] == {
            'complete_dataset': False,
            'has_more': False,
            'next_token': None,
            'items_returned': len(kept),
        }
        assert (
            f'returned {len(kept)} tags, and the service returned a continuation'
            in (data['warning'])
        )
        assert 'Split tag_keys across smaller calls' in data['warning']

    async def test_tag_keys_with_next_token_is_rejected(self, mock_context):
        """A key lookup has no continuation, so a caller's next_token is a local error."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['A']), next_token='t1'
            )

        client.list_cost_allocation_tags.assert_not_called()
        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'ListCostAllocationTags'
        assert 'next_token cannot be used with tag_keys' in result['data']['message']

    async def test_tag_keys_lookup_rejects_max_items_below_one(self, mock_context):
        """max_items below 1 is still rejected before any call on a key lookup."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['A']), max_items=0
            )

        client.list_cost_allocation_tags.assert_not_called()
        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert 'max_items must be at least 1' in result['message']


def test_list_tags_description_states_tag_keys_paging():
    """The served description says a key lookup returns every match with no next_token."""
    tool = asyncio.run(cost_allocation_tags_server.get_tool('list-cost-allocation-tags'))
    assert tool is not None
    description = ' '.join((tool.description or '').split())
    assert 'With tag_keys, one call returns every matching tag' in description
    assert 'there is no next_token' in description


@pytest.mark.asyncio
class TestListCostAllocationTagBackfillHistory:
    """Tests for list_cost_allocation_tag_backfill_history function."""

    async def test_list_backfill_no_filters(self, mock_context, mock_ce_client):
        """Test listing backfill history with no filters."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tag_backfill_history(mock_context)

        mock_ce_client.list_cost_allocation_tag_backfill_history.assert_called_once_with(
            MaxResults=1000
        )
        assert result['status'] == 'success'
        assert len(result['data']['BackfillRequests']) == 1

    async def test_list_backfill_with_max_items(self, mock_context, mock_ce_client):
        """max_items=1 requests one item per page."""
        mod = _reload_with_identity_decorator()

        with patch.object(mod, 'create_aws_client', return_value=mock_ce_client):
            result = await mod.list_cost_allocation_tag_backfill_history(mock_context, max_items=1)

        mock_ce_client.list_cost_allocation_tag_backfill_history.assert_called_once_with(
            MaxResults=1
        )
        assert result['status'] == 'success'

    async def test_list_backfill_without_max_items_fetches_every_page(self, mock_context):
        """Without max_items every page is fetched."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_allocation_tag_backfill_history.side_effect = [
            {'BackfillRequests': [{'BackfillStatus': 'SUCCEEDED'}], 'NextToken': 't1'},
            {'BackfillRequests': [{'BackfillStatus': 'FAILED'}]},
        ]

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tag_backfill_history(mock_context)

        assert len(result['data']['BackfillRequests']) == 2
        assert result['data']['pagination']['complete_dataset'] is True
        assert [
            c.kwargs for c in client.list_cost_allocation_tag_backfill_history.call_args_list
        ] == [
            {'MaxResults': 1000},
            {'MaxResults': 1000, 'NextToken': 't1'},
        ]

    async def test_list_backfill_max_items_stop_and_continue(self, mock_context):
        """max_items stops with the service token; the continuation sends it back."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_allocation_tag_backfill_history.side_effect = [
            {'BackfillRequests': [{'BackfillStatus': 'SUCCEEDED'}], 'NextToken': 't1'},
            {'BackfillRequests': [{'BackfillStatus': 'FAILED'}]},
        ]

        with patch.object(mod, 'create_aws_client', return_value=client):
            first = await mod.list_cost_allocation_tag_backfill_history(mock_context, max_items=1)
            token = first['data']['pagination']['next_token']
            second = await mod.list_cost_allocation_tag_backfill_history(
                mock_context, max_items=1, next_token=token
            )

        assert first['data']['complete_dataset'] is False
        assert token == 't1'
        assert second['data']['pagination']['complete_dataset'] is True
        assert [
            c.kwargs for c in client.list_cost_allocation_tag_backfill_history.call_args_list
        ] == [
            {'MaxResults': 1},
            {'MaxResults': 1, 'NextToken': 't1'},
        ]

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


class TestBackfillHistoryDescription:
    """The served backfill-history description lists only the API's statuses."""

    @pytest.mark.asyncio
    async def test_states_match_the_api_enum(self):
        """No SCHEDULED state; the listed states equal CostAllocationTagBackfillStatus."""
        import botocore.session
        from awslabs.billing_cost_management_mcp_server.tools import (
            cost_allocation_tags_tools as mod,
        )

        # Other tests reload the module with an identity decorator; reload it normally
        # so the server registers its tools again.
        mod = importlib.reload(mod)
        tool = await mod.cost_allocation_tags_server.get_tool(
            'list-cost-allocation-tag-backfill-history'
        )
        assert tool is not None
        description = tool.description or ''
        enum = set(
            botocore.session.get_session()
            .get_service_model('ce')
            .shape_for('CostAllocationTagBackfillStatus')
            .enum
        )
        listed = {
            state
            for state in ('SCHEDULED', 'PROCESSING', 'SUCCEEDED', 'FAILED')
            if f'- {state}:' in description
        }

        assert 'SCHEDULED' not in description
        assert listed == enum
