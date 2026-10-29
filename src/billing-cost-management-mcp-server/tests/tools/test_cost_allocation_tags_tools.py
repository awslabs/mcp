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
        assert 'note' not in result['data']

    async def test_list_tags_with_all_filters(self, mock_context, mock_ce_client):
        """Test listing tags with all filters combined; max_items sets the page size."""
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
            MaxResults=10,
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


def _tags_client(*tag_keys: str) -> MagicMock:
    """A client whose single page returns UserDefined tags with the given keys."""
    client = MagicMock()
    client.list_cost_allocation_tags.return_value = {
        'CostAllocationTags': [
            {'TagKey': key, 'Type': 'UserDefined', 'Status': 'Active'} for key in tag_keys
        ]
    }
    return client


@pytest.mark.asyncio
class TestListCostAllocationTagsInputs:
    """user:-prefixed tag keys and any-case status and tag_type values."""

    async def test_user_prefixed_key_also_sends_stripped_key(self, mock_context):
        """user:application is sent as given and without the prefix; the note names the match."""
        mod = _reload_with_identity_decorator()
        client = _tags_client('application')

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['user:application'])
            )

        client.list_cost_allocation_tags.assert_called_once_with(
            TagKeys=['user:application', 'application'], MaxResults=1000
        )
        assert result['status'] == 'success'
        assert [t['TagKey'] for t in result['data']['CostAllocationTags']] == ['application']
        note = result['data']['note']
        assert "'user:application' matched tag key 'application'" in note
        assert note.endswith(
            'Cost allocation report and Cost and Usage Report columns add user: to '
            'user-defined tag keys; the stored key normally has no prefix.'
        )

    async def test_key_that_really_starts_with_user_has_no_note(self, mock_context):
        """A stored key that literally starts with user: matches as given, with no note."""
        mod = _reload_with_identity_decorator()
        client = _tags_client('user:application')

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['user:application'])
            )

        client.list_cost_allocation_tags.assert_called_once_with(
            TagKeys=['user:application', 'application'], MaxResults=1000
        )
        assert 'note' not in result['data']

    async def test_expanded_keys_are_deduplicated(self, mock_context):
        """A stripped key the caller also listed is sent once, and its match gets no note."""
        mod = _reload_with_identity_decorator()
        client = _tags_client('Team')

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['user:Team', 'Team', 'Team', 'aws:createdBy'])
            )

        client.list_cost_allocation_tags.assert_called_once_with(
            TagKeys=['user:Team', 'Team', 'aws:createdBy'], MaxResults=1000
        )
        assert 'note' not in result['data']

    async def test_stripped_key_listed_first_is_sent_once_without_note(self, mock_context):
        """Team before user:Team: Team is the caller's own key, so it gets no note."""
        mod = _reload_with_identity_decorator()
        client = _tags_client('Team')

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['Team', 'user:Team'])
            )

        client.list_cost_allocation_tags.assert_called_once_with(
            TagKeys=['Team', 'user:Team'], MaxResults=1000
        )
        assert 'note' not in result['data']

    async def test_only_one_leading_user_prefix_is_stripped(self, mock_context):
        """user:user:x adds user:x only; a bare user: adds no empty key."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()

        with patch.object(mod, 'create_aws_client', return_value=client):
            await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['user:user:x', 'user:', 'User:Y'])
            )

        client.list_cost_allocation_tags.assert_called_once_with(
            TagKeys=['user:user:x', 'user:x', 'user:', 'User:Y'], MaxResults=1000
        )

    async def test_expansion_up_to_100_keys_is_sent(self, mock_context):
        """50 user: keys expand to exactly 100 keys, which the API accepts."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()
        keys = [f'user:k{i}' for i in range(50)]

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys=json.dumps(keys))

        assert result['status'] == 'success'
        assert len(client.list_cost_allocation_tags.call_args.kwargs['TagKeys']) == 100
        assert 'note' not in result['data']

    async def test_expansion_over_100_keys_falls_back_to_keys_as_given(self, mock_context):
        """51 user: keys would expand to 102, so the caller's keys are sent unexpanded."""
        mod = _reload_with_identity_decorator()
        client = _tags_client('user:k3')
        keys = [f'user:k{i}' for i in range(51)]

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys=json.dumps(keys))

        client.list_cost_allocation_tags.assert_called_once_with(TagKeys=keys, MaxResults=1000)
        assert result['status'] == 'success'
        assert [t['TagKey'] for t in result['data']['CostAllocationTags']] == ['user:k3']
        assert result['data']['note'] == (
            'Sent the keys only as given: adding the unprefixed form of 51 user: keys would '
            "make 102 keys, over the API's limit of 100. To look those up, pass them without "
            'user:, or split tag_keys across calls.'
        )

    async def test_fallback_still_sends_repeated_keys_once(self, mock_context):
        """The fallback sends the caller's distinct keys in order; the API rejects repeats."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()
        keys = [f'user:k{i}' for i in range(60)] + ['user:k0', 'Team', 'Team']

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys=json.dumps(keys))

        client.list_cost_allocation_tags.assert_called_once_with(
            TagKeys=[f'user:k{i}' for i in range(60)] + ['Team'], MaxResults=1000
        )
        assert result['status'] == 'success'
        assert result['data']['note'].startswith(
            'Sent the keys only as given: adding the unprefixed form of 60 user: keys would '
            'make 121 keys'
        )

    async def test_fallback_note_counts_only_keys_whose_unprefixed_form_was_dropped(
        self, mock_context
    ):
        """user:k0-39 already have k0-39 listed and a bare user: has no unprefixed form."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()
        keys = [f'user:k{i}' for i in range(60)] + ['user:'] + [f'k{i}' for i in range(39)]

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys=json.dumps(keys))

        client.list_cost_allocation_tags.assert_called_once_with(TagKeys=keys, MaxResults=1000)
        assert result['data']['note'].startswith(
            'Sent the keys only as given: adding the unprefixed form of 21 user: keys would '
            'make 121 keys'
        )

    async def test_fallback_note_singular_for_one_key(self, mock_context):
        """100 keys where only one unprefixed form is missing: the note says 1 key."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()
        keys = [f'k{i}' for i in range(99)] + ['user:x']

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys=json.dumps(keys))

        client.list_cost_allocation_tags.assert_called_once_with(TagKeys=keys, MaxResults=1000)
        assert 'of 1 user: key would make 101 keys' in result['data']['note']

    async def test_over_100_distinct_user_keys_is_rejected(self, mock_context):
        """101 distinct user: keys is rejected locally with the plain over-limit message."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()
        keys = [f'user:k{i}' for i in range(101)]

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys=json.dumps(keys))

        client.list_cost_allocation_tags.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert result['message'].startswith('tag_keys has 101 distinct keys')

    async def test_many_repeats_of_few_keys_are_sent_once_without_note(self, mock_context):
        """150 entries of one key are one distinct key: sent once, no fallback."""
        mod = _reload_with_identity_decorator()
        client = _tags_client('Team')

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['Team'] * 150)
            )

        client.list_cost_allocation_tags.assert_called_once_with(TagKeys=['Team'], MaxResults=1000)
        assert 'note' not in result['data']

    async def test_over_100_plain_keys_is_rejected_without_expansion_text(self, mock_context):
        """101 keys without user: get a plain over-limit message."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()
        keys = [f'k{i}' for i in range(101)]

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys=json.dumps(keys))

        client.list_cost_allocation_tags.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert result['message'].startswith(
            'tag_keys has 101 distinct keys; the API accepts at most 100'
        )
        assert 'expands' not in result['message']

    async def test_empty_tag_keys_array_is_rejected(self, mock_context):
        """An empty array is a validation error rather than a client-side botocore error."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(mock_context, tag_keys='[]')

        client.list_cost_allocation_tags.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert 'at least one key' in result['message']

    async def test_both_forms_returned_keeps_both_and_notes_the_stripped_one(self, mock_context):
        """When user:a and a are both stored keys, both come back and only a is noted."""
        mod = _reload_with_identity_decorator()
        client = _tags_client('user:application', 'application')

        with patch.object(mod, 'create_aws_client', return_value=client):
            result = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=json.dumps(['user:application'])
            )

        assert [t['TagKey'] for t in result['data']['CostAllocationTags']] == [
            'user:application',
            'application',
        ]
        assert result['data']['note'].startswith(
            "'user:application' matched tag key 'application'."
        )

    async def test_expanded_keys_repeat_on_every_page(self, mock_context):
        """Each page and a continuation send the same expanded keys; the note covers all pages."""
        mod = _reload_with_identity_decorator()
        client = MagicMock()
        client.list_cost_allocation_tags.side_effect = [
            {'CostAllocationTags': [{'TagKey': 'user:x'}], 'NextToken': 't1'},
            {'CostAllocationTags': [{'TagKey': 'x'}]},
            {'CostAllocationTags': [{'TagKey': 'x'}]},
        ]
        tag_keys = json.dumps(['user:x'])

        with patch.object(mod, 'create_aws_client', return_value=client):
            first = await mod.list_cost_allocation_tags(mock_context, tag_keys=tag_keys)
            again = await mod.list_cost_allocation_tags(
                mock_context, tag_keys=tag_keys, next_token='t1'
            )

        assert [c.kwargs for c in client.list_cost_allocation_tags.call_args_list] == [
            {'TagKeys': ['user:x', 'x'], 'MaxResults': 1000},
            {'TagKeys': ['user:x', 'x'], 'MaxResults': 1000, 'NextToken': 't1'},
            {'TagKeys': ['user:x', 'x'], 'MaxResults': 1000, 'NextToken': 't1'},
        ]
        assert "'user:x' matched tag key 'x'" in first['data']['note']
        assert "'user:x' matched tag key 'x'" in again['data']['note']

    async def test_tag_keys_must_be_an_array_of_strings(self, mock_context):
        """A JSON value that is not an array of strings is a validation error."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()

        with patch.object(mod, 'create_aws_client', return_value=client):
            for bad in ('"Environment"', '[1, 2]', '{"Key": "Team"}'):
                result = await mod.list_cost_allocation_tags(mock_context, tag_keys=bad)
                assert result['status'] == 'error', bad
                assert result['error_type'] == 'validation_error', bad
                assert 'JSON array of strings' in result['message'], bad

        client.list_cost_allocation_tags.assert_not_called()

    @pytest.mark.parametrize(
        'given,sent',
        [
            ('active', 'Active'),
            ('ACTIVE', 'Active'),
            ('Active', 'Active'),
            ('inactive', 'Inactive'),
            ('INACTIVE', 'Inactive'),
        ],
    )
    async def test_status_any_case(self, mock_context, given, sent):
        """Status is matched case-insensitively and sent in the API's casing."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()

        with patch.object(mod, 'create_aws_client', return_value=client):
            await mod.list_cost_allocation_tags(mock_context, status=given)

        client.list_cost_allocation_tags.assert_called_once_with(Status=sent, MaxResults=1000)

    @pytest.mark.parametrize(
        'given,sent',
        [
            ('awsgenerated', 'AWSGenerated'),
            ('AWSGENERATED', 'AWSGenerated'),
            ('AwsGenerated', 'AWSGenerated'),
            ('userdefined', 'UserDefined'),
            ('USERDEFINED', 'UserDefined'),
            ('UserDefined', 'UserDefined'),
        ],
    )
    async def test_tag_type_any_case(self, mock_context, given, sent):
        """tag_type is matched case-insensitively and sent in the API's casing."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()

        with patch.object(mod, 'create_aws_client', return_value=client):
            await mod.list_cost_allocation_tags(mock_context, tag_type=given)

        client.list_cost_allocation_tags.assert_called_once_with(Type=sent, MaxResults=1000)

    async def test_unknown_enum_values_go_to_the_api_unchanged(self, mock_context):
        """Values that are not a case variant are left for the API to accept or reject."""
        mod = _reload_with_identity_decorator()
        client = _tags_client()

        with patch.object(mod, 'create_aws_client', return_value=client):
            await mod.list_cost_allocation_tags(
                mock_context, status='enabled', tag_type='user_defined'
            )

        client.list_cost_allocation_tags.assert_called_once_with(
            Status='enabled', Type='user_defined', MaxResults=1000
        )


@pytest.mark.asyncio
async def test_list_tags_description_states_key_and_enum_rules():
    """The served description covers the user: prefix, key case, AWSGenerated and enum case."""
    tool = await cost_allocation_tags_server.get_tool('list-cost-allocation-tags')
    assert tool is not None
    description = ' '.join((tool.description or '').split())

    assert 'columns add user: to user-defined keys' in description
    assert 'the stored key normally has no prefix' in description
    assert 'Repeated keys are sent once' in description
    assert 'as given and also without the prefix, and adds a note' in description
    assert (
        'At most 100 distinct keys. If the unprefixed forms would take the total over 100'
        in description
    )
    assert 'At most 100 keys, counting the unprefixed keys the tool adds' not in description
    assert 'Team and team are separate tags' in description
    assert 'AWSGenerated is exactly the keys that start with aws:' in description
    assert 'Active or Inactive (any case)' in description
    assert 'AWSGenerated or UserDefined (any case)' in description
    assert '(max 100, case-sensitive)' not in description
