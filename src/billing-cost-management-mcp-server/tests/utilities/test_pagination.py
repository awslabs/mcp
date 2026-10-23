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

"""Tests for the shared max_items pagination helper."""

import pytest
from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
    PageSpec,
    first_page_fields,
    handle_aws_error,
    paginate_aws_items,
    partial_data_warning,
    whole_query_in_one_page,
    with_pagination,
)
from awslabs.billing_cost_management_mcp_server.utilities.error_contract import (
    InvalidNextTokenError,
    add_retry_guidance,
)
from botocore.exceptions import ClientError
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def ctx():
    """Create a mock MCP context."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    context.debug = AsyncMock()
    return context


def _client_error(code):
    return ClientError({'Error': {'Code': code, 'Message': 'm'}}, 'Op')


def _pages(*sizes, token_param='nextToken'):
    """Build page responses of the given sizes, each pointing at the next."""
    responses: List[Dict[str, Any]] = []
    for index, size in enumerate(sizes):
        page: Dict[str, Any] = {'items': [f'p{index}-{n}' for n in range(size)]}
        if index < len(sizes) - 1:
            page[token_param] = f't{index + 1}'
        responses.append(page)
    return responses


SIZED = PageSpec(
    result_key='items',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
)
SERVER_SIZED = PageSpec(
    result_key='items', token_param='nextToken', token_key_in_response='nextToken', page_max=5
)


@pytest.mark.asyncio
class TestFetchAll:
    """Without max_items every page is fetched."""

    async def test_fetches_every_page_at_largest_size(self, ctx):
        """All pages come back, each requested at page_max."""
        api = MagicMock(side_effect=_pages(100, 100, 30))

        items, pages, pagination = await paginate_aws_items(ctx, 'op', api, {'filter': 'x'}, SIZED)

        assert len(items) == 230
        assert len(pages) == 3
        assert pagination == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 230,
        }
        assert [call.kwargs.get('nextToken') for call in api.call_args_list] == [None, 't1', 't2']
        assert all(call.kwargs['maxResults'] == 100 for call in api.call_args_list)
        assert all(call.kwargs['filter'] == 'x' for call in api.call_args_list)

    async def test_empty_string_token_means_complete(self, ctx):
        """Some services end with an empty-string token instead of omitting it."""
        api = MagicMock(side_effect=[{'items': ['a'], 'nextToken': ''}])

        _, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

        assert api.call_count == 1
        assert pagination['complete_dataset'] is True
        assert pagination['next_token'] is None

    async def test_empty_page_with_token_keeps_paging(self, ctx):
        """A short or empty page that still carries a token is not the end."""
        api = MagicMock(
            side_effect=[
                {'items': ['a'], 'nextToken': 't1'},
                {'items': [], 'nextToken': 't2'},
                {'items': ['b']},
            ]
        )

        items, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

        assert items == ['a', 'b']
        assert pagination['complete_dataset'] is True

    async def test_repeated_token_stops_as_partial(self, ctx):
        """A service returning the token it was given would loop forever, so stop."""
        api = MagicMock(
            side_effect=[{'items': ['a'], 'nextToken': 't1'}, {'items': ['b'], 'nextToken': 't1'}]
        )

        items, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

        assert items == ['a', 'b']
        assert pagination['complete_dataset'] is False
        assert pagination['next_token'] is None
        assert 'RepeatedNextToken' in pagination['warning']
        assert 'without next_token' in pagination['warning']

    async def test_token_cycle_stops(self, ctx):
        """Tokens alternating A, B, A would never end without a seen-token check."""
        api = MagicMock(
            side_effect=[
                {'items': ['a'], 'nextToken': 'A'},
                {'items': ['b'], 'nextToken': 'B'},
                {'items': ['c'], 'nextToken': 'A'},
            ]
        )

        items, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

        assert api.call_count == 3
        assert items == ['a', 'b', 'c']
        assert pagination['next_token'] is None

    async def test_echoed_caller_token_is_not_handed_back(self, ctx):
        """A service echoing the caller's own token must not be returned as a resume point."""
        api = MagicMock(side_effect=[{'items': ['a'], 'nextToken': 'X'}])

        _, _, pagination = await paginate_aws_items(
            ctx, 'op', api, {}, SERVER_SIZED, next_token='X'
        )

        assert pagination['next_token'] is None
        assert pagination['complete_dataset'] is False

    async def test_nested_result_key_and_awaitable_call(self, ctx):
        """Items can sit at a nested path, and api_call may be async."""
        responses = iter(
            [{'Rec': {'Details': [1, 2]}, 'NextPageToken': 't1'}, {'Rec': {'Details': [3]}}]
        )

        async def api(**_):
            return next(responses)

        spec = PageSpec(
            result_key=('Rec', 'Details'),
            token_param='NextPageToken',
            token_key_in_response='NextPageToken',
            page_max=10,
        )
        items, _, _ = await paginate_aws_items(ctx, 'op', api, {}, spec)

        assert items == [1, 2, 3]

    async def test_nested_result_key_with_missing_parent_counts_no_items(self, ctx):
        """A page without the parent object holds no items, and paging still follows its token."""
        api = MagicMock(
            side_effect=[
                {'Metadata': {}, 'NextPageToken': 't1'},
                {'Rec': None, 'NextPageToken': 't2'},
                {'Rec': {'Details': [1]}},
            ]
        )
        spec = PageSpec(
            result_key=('Rec', 'Details'),
            token_param='NextPageToken',
            token_key_in_response='NextPageToken',
            page_max=10,
        )

        items, pages, pagination = await paginate_aws_items(ctx, 'op', api, {}, spec)

        assert api.call_count == 3
        assert items == [1]
        assert len(pages) == 3
        assert pagination['items_returned'] == 1
        assert pagination['complete_dataset'] is True


@pytest.mark.asyncio
class TestMaxItems:
    """With max_items the helper stops before going over it."""

    async def test_exact_stop_with_page_size_param(self, ctx):
        """The last page asks for exactly what is left, and the service token is returned."""
        api = MagicMock(
            side_effect=[
                {'items': list(range(100)), 'nextToken': 't1'},
                {'items': list(range(50)), 'nextToken': 't2'},
            ]
        )

        items, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, SIZED, max_items=150)

        assert len(items) == 150
        assert [call.kwargs['maxResults'] for call in api.call_args_list] == [100, 50]
        assert pagination['next_token'] == 't2'
        assert pagination['complete_dataset'] is False
        assert pagination['warning'] == partial_data_warning(150)

    async def test_server_sized_stops_before_a_page_that_could_overflow(self, ctx):
        """No call is made when one more full page could exceed max_items."""
        api = MagicMock(side_effect=_pages(5, 5, 5))

        items, _, pagination = await paginate_aws_items(
            ctx, 'op', api, {}, SERVER_SIZED, max_items=12
        )

        assert len(items) == 10
        assert api.call_count == 2
        assert pagination['next_token'] == 't2'

    async def test_first_page_always_returned_even_when_larger(self, ctx):
        """The first page comes back whole, so a response is never empty."""
        api = MagicMock(side_effect=_pages(5, 5))

        items, _, pagination = await paginate_aws_items(
            ctx, 'op', api, {}, SERVER_SIZED, max_items=2
        )

        assert len(items) == 5
        assert api.call_count == 1
        assert pagination['next_token'] == 't1'

    async def test_fixed_page_size_is_resent_unchanged(self, ctx):
        """A token bound to the page size always gets the same page size."""
        spec = PageSpec(
            result_key='items',
            token_param='NextPageToken',
            token_key_in_response='NextPageToken',
            page_max=500,
            page_size_param='MaxResults',
            fixed_page_size=True,
        )
        api = MagicMock(
            side_effect=[
                {'items': list(range(500)), 'NextPageToken': 't1'},
                {'items': list(range(500)), 'NextPageToken': 't2'},
            ]
        )

        items, _, pagination = await paginate_aws_items(
            ctx, 'op', api, {}, spec, max_items=10, next_token='t0'
        )

        assert len(items) == 500
        assert api.call_args_list[0].kwargs == {'NextPageToken': 't0', 'MaxResults': 500}
        assert pagination['next_token'] == 't1'

    async def test_page_size_is_at_least_one(self, ctx):
        """Fewer items left than one unit holds still requests a page of 1, never 0."""
        spec = PageSpec(
            result_key='items',
            token_param='NextToken',
            token_key_in_response='NextToken',
            page_max=100,
            page_size_param='MaxResults',
            items_per_page_unit=10,
        )
        api = MagicMock(side_effect=[{'items': list(range(10)), 'NextToken': 't1'}])

        items, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, spec, max_items=5)

        assert api.call_args_list[0].kwargs == {'MaxResults': 1}
        assert len(items) == 10
        assert pagination['next_token'] == 't1'

    async def test_page_size_is_at_least_page_min(self, ctx):
        """A remainder below page_min requests page_min; the stop rule counts that size."""
        spec = PageSpec(
            result_key='items',
            token_param='NextToken',
            token_key_in_response='NextToken',
            page_max=300,
            page_size_param='MaxResults',
            page_min=200,
        )
        api = MagicMock(
            side_effect=[
                {'items': list(range(300)), 'NextToken': 't1'},
                {'items': list(range(200)), 'NextToken': 't2'},
            ]
        )

        items, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, spec, max_items=500)

        assert [call.kwargs['MaxResults'] for call in api.call_args_list] == [300, 200]
        assert len(items) == 500
        assert pagination['next_token'] == 't2'

    async def test_items_per_page_unit(self, ctx):
        """Page size counts parents: request floor(remaining / unit) of them."""
        spec = PageSpec(
            result_key='items',
            token_param='NextToken',
            token_key_in_response='NextToken',
            page_max=10000,
            page_size_param='MaxResults',
            items_per_page_unit=10,
        )
        api = MagicMock(side_effect=[{'items': list(range(30)), 'NextToken': 't1'}])

        await paginate_aws_items(ctx, 'op', api, {}, spec, max_items=55)

        assert api.call_args_list[0].kwargs['MaxResults'] == 5

    async def test_oversized_page_is_kept_and_logged(self, ctx):
        """A page above page_max is kept, since the call is already paid for."""
        api = MagicMock(side_effect=[{'items': list(range(8))}])

        items, _, _ = await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

        assert len(items) == 8
        assert any('above its page_max' in str(c) for c in ctx.warning.call_args_list)

    async def test_custom_item_count(self, ctx):
        """count_items decides what one item is (e.g. CE rows = groups x periods)."""
        spec = PageSpec(
            result_key='ResultsByTime',
            token_param='NextPageToken',
            token_key_in_response='NextPageToken',
            page_max=10,
            count_items=lambda periods: sum(max(1, len(p['Groups'])) for p in periods),
        )
        api = MagicMock(side_effect=[{'ResultsByTime': [{'Groups': [1, 2, 3]}, {'Groups': []}]}])

        _, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, spec)

        assert pagination['items_returned'] == 4


@pytest.mark.asyncio
class TestPagingLimits:
    """The server-wide time limit stops paging on a page boundary."""

    async def test_time_limit_stops_with_the_service_token(self, ctx, monkeypatch):
        """Past PAGINATION_MAX_SECONDS no further page is fetched; the token resumes it."""
        from awslabs.billing_cost_management_mcp_server.utilities import (
            aws_service_base,
            constants,
        )

        monkeypatch.setattr(constants, 'PAGINATION_MAX_SECONDS', 10)
        clock = iter([0.0, 11.0, 11.0])
        monkeypatch.setattr(aws_service_base.time, 'monotonic', lambda: next(clock))
        api = MagicMock(side_effect=_pages(5, 5, 5))

        items, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

        assert api.call_count == 1
        assert len(items) == 5
        assert pagination['next_token'] == 't1'
        assert pagination['complete_dataset'] is False
        assert '10-second limit' in pagination['warning']
        assert 'Continue with next_token' in pagination['warning']

    async def test_limit_does_not_cut_a_complete_result(self, ctx):
        """A result that ends before the time limit is complete, with no warning."""
        api = MagicMock(side_effect=_pages(5, 5))

        _, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

        assert pagination['complete_dataset'] is True
        assert 'warning' not in pagination


class TestPagingLimitConfig:
    """The limit is env-overridable, and a bad value falls back to the default."""

    @pytest.mark.parametrize(
        'raw, expected', [(None, 7), ('', 7), ('abc', 7), ('0', 7), ('-3', 7), (' 42 ', 42)]
    )
    def test_positive_int_env(self, monkeypatch, raw, expected):
        """Only a positive int overrides the default."""
        from awslabs.billing_cost_management_mcp_server.utilities import constants

        if raw is None:
            monkeypatch.delenv('BCM_MCP_TEST_LIMIT', raising=False)
        else:
            monkeypatch.setenv('BCM_MCP_TEST_LIMIT', raw)

        assert constants._positive_int_env('BCM_MCP_TEST_LIMIT', 7) == expected


FIXED = PageSpec(
    result_key='items',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=500,
    page_size_param='MaxResults',
    fixed_page_size=True,
)


@pytest.mark.asyncio
class TestMaxPages:
    """With max_pages the helper fetches at most that many whole pages."""

    async def test_one_page(self, ctx):
        """max_pages=1 fetches one page at the spec's size and returns the service token."""
        api = MagicMock(side_effect=_pages(500, 500, token_param='NextPageToken'))

        items, pages, pagination = await paginate_aws_items(ctx, 'op', api, {}, FIXED, max_pages=1)

        assert len(items) == 500
        assert len(pages) == 1
        assert api.call_args_list[0].kwargs == {'MaxResults': 500}
        assert pagination['next_token'] == 't1'
        assert pagination['complete_dataset'] is False
        assert pagination['has_more'] is True

    async def test_two_pages_return_every_item(self, ctx):
        """max_pages=2 fetches two pages, both at the same size, and keeps every item."""
        api = MagicMock(side_effect=_pages(500, 500, 500, token_param='NextPageToken'))

        items, _, pagination = await paginate_aws_items(
            ctx, 'op', api, {}, FIXED, max_pages=2, next_token='t0'
        )

        assert len(items) == 1000
        assert [call.kwargs for call in api.call_args_list] == [
            {'NextPageToken': 't0', 'MaxResults': 500},
            {'NextPageToken': 't1', 'MaxResults': 500},
        ]
        assert pagination['next_token'] == 't2'
        assert pagination['items_returned'] == 1000

    async def test_data_ending_first_is_complete(self, ctx):
        """When the data ends before max_pages the result is complete."""
        api = MagicMock(side_effect=_pages(500, 20, token_param='NextPageToken'))

        items, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, FIXED, max_pages=5)

        assert len(items) == 520
        assert api.call_count == 2
        assert pagination['complete_dataset'] is True
        assert pagination['next_token'] is None
        assert 'warning' not in pagination

    async def test_warning_names_max_pages(self, ctx):
        """A result cut by max_pages tells the caller to raise max_pages, not max_items."""
        api = MagicMock(side_effect=_pages(500, 500, token_param='NextPageToken'))

        _, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, FIXED, max_pages=1)

        assert pagination['warning'] == partial_data_warning(500, 'max_pages')
        assert (
            'Call again with a larger max_pages, continue with next_token'
            in (pagination['warning'])
        )
        assert 'max_items' not in pagination['warning']

    async def test_default_warning_names_max_items(self):
        """Without a parameter name the warning keeps pointing at max_items."""
        assert 'Call again with a larger max_items,' in partial_data_warning(3)

    async def test_with_max_items_is_rejected(self, ctx):
        """max_pages and max_items are mutually exclusive."""
        api = MagicMock()

        with pytest.raises(ValueError, match='max_pages and max_items'):
            await paginate_aws_items(ctx, 'op', api, {}, FIXED, max_items=10, max_pages=1)

        api.assert_not_called()

    @pytest.mark.parametrize('max_pages', [0, -1])
    async def test_below_one_is_rejected(self, ctx, max_pages):
        """A max_pages below 1 is a validation error, before any call is made."""
        api = MagicMock()

        with pytest.raises(
            ValueError, match='max_pages must be at least 1. Omit it to fetch every page.'
        ):
            await paginate_aws_items(ctx, 'op', api, {}, FIXED, max_pages=max_pages)

        api.assert_not_called()


@pytest.mark.asyncio
class TestFailures:
    """Token rejections and failures partway through."""

    @pytest.mark.parametrize('max_items', [0, -5])
    async def test_max_items_below_one_is_rejected(self, ctx, max_items):
        """A max_items below 1 is a validation error, before any call is made."""
        api = MagicMock()

        with pytest.raises(ValueError, match='at least 1'):
            await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED, max_items=max_items)

        api.assert_not_called()

    @pytest.mark.parametrize('next_token', ['', '  '])
    async def test_empty_next_token_is_rejected(self, ctx, next_token):
        """An empty token must not silently restart from page 1 as if it continued."""
        api = MagicMock()

        with pytest.raises(ValueError, match='non-empty token'):
            await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED, next_token=next_token)

        api.assert_not_called()

    async def test_rejected_caller_token_raises_invalid_next_token(self, ctx):
        """A token error on the caller's token maps to invalid_next_token."""
        api = MagicMock(side_effect=_client_error('BillExpirationException'))

        with pytest.raises(InvalidNextTokenError) as raised:
            await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED, next_token='old')

        assert raised.value.error_code == 'BillExpirationException'

    async def test_token_error_without_caller_token_is_raised_unchanged(self, ctx):
        """Without a caller token the same code is a plain service error."""
        api = MagicMock(side_effect=_client_error('InvalidNextTokenException'))

        with pytest.raises(ClientError):
            await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

    async def test_spec_can_add_token_error_codes(self, ctx):
        """An operation can widen the codes that mean a rejected token."""
        spec = PageSpec(
            result_key='items',
            token_param='NextToken',
            token_key_in_response='NextToken',
            page_max=5,
            token_error_codes=frozenset({'InternalServerException'}),
        )
        api = MagicMock(side_effect=_client_error('InternalServerException'))

        with pytest.raises(InvalidNextTokenError):
            await paginate_aws_items(ctx, 'op', api, {}, spec, next_token='old')

    async def test_failure_after_first_page_returns_partial_with_retry_token(self, ctx):
        """Kept pages come back, with the token that fetched the failed page."""
        api = MagicMock(
            side_effect=[{'items': ['a'], 'nextToken': 't1'}, _client_error('ThrottlingException')]
        )

        items, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

        assert items == ['a']
        assert pagination['complete_dataset'] is False
        assert pagination['next_token'] == 't1'
        assert 'ThrottlingException' in pagination['warning']
        assert 'retry from the failed page' in pagination['warning']

    async def test_token_failure_after_first_page_says_restart(self, ctx):
        """A mid-run token rejection drops the token and says to restart."""
        api = MagicMock(
            side_effect=[
                {'items': ['a'], 'nextToken': 't1'},
                _client_error('BillExpirationException'),
            ]
        )

        _, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

        assert pagination['next_token'] is None
        assert pagination['has_more'] is False
        assert pagination['complete_dataset'] is False
        assert pagination['warning'] == (
            'Partial data: returned 1 items, then the service failed with '
            'BillExpirationException. Totals and counts computed from this result undercount '
            'the real data. The continuation token is no longer valid. Call again without '
            'next_token to restart from the first page, and use only the new result: it repeats '
            'the items in this one, so do not combine them.'
        )

    async def test_expired_next_token_is_a_token_error(self, ctx):
        """AWS Pricing's ExpiredNextTokenException maps to invalid_next_token."""
        api = MagicMock(side_effect=_client_error('ExpiredNextTokenException'))

        with pytest.raises(InvalidNextTokenError):
            await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED, next_token='old')

    async def test_caller_codes_only_apply_to_the_callers_token(self, ctx):
        """A transient 500 on a later page keeps the retry token.

        The 500 only means a rejected token when it answers the caller's own next_token.
        """
        spec = PageSpec(
            result_key='items',
            token_param='NextToken',
            token_key_in_response='NextToken',
            page_max=5,
            caller_token_error_codes=frozenset({'InternalServerException'}),
        )
        api = MagicMock(
            side_effect=[
                {'items': ['a'], 'NextToken': 't1'},
                _client_error('InternalServerException'),
            ]
        )

        _, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, spec)

        assert pagination['next_token'] == 't1'
        assert 'retry from the failed page' in pagination['warning']

    async def test_first_page_failure_is_raised(self, ctx):
        """A first-page failure is the tool's error, as before."""
        api = MagicMock(side_effect=_client_error('AccessDeniedException'))

        with pytest.raises(ClientError):
            await paginate_aws_items(ctx, 'op', api, {}, SERVER_SIZED)

    async def test_handle_aws_error_maps_invalid_next_token(self, ctx):
        """The tool error carries invalid_next_token and the restart hint."""
        response = add_retry_guidance(
            await handle_aws_error(ctx, InvalidNextTokenError('op', 'X'), 'op', 'svc')
        )

        assert response['error_type'] == 'invalid_next_token'
        assert response['retry_strategy'] == 'modify_request'
        assert 'without next_token' in response['hint']


class TestResponseShape:
    """with_pagination and first_page_fields."""

    def test_partial_result_leads_with_flag_and_warning(self):
        """complete_dataset and warning are the first two keys of a partial result."""
        pagination = {
            'complete_dataset': False,
            'has_more': True,
            'next_token': 't',
            'items_returned': 3,
            'warning': 'w',
        }

        result = with_pagination({'items': [1, 2, 3]}, pagination)

        # The pagination block comes before the data, so a trimmed tail never loses it.
        assert list(result) == ['complete_dataset', 'warning', 'pagination', 'items']
        assert result['pagination'] == {
            'complete_dataset': False,
            'has_more': True,
            'next_token': 't',
            'items_returned': 3,
        }

    def test_complete_result_has_no_top_level_flag(self):
        """A complete result only carries the pagination block."""
        pagination = {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 1,
        }

        result = with_pagination({'items': [1]}, pagination)

        assert list(result) == ['pagination', 'items']
        assert 'warning' not in result
        assert 'complete_dataset' not in result
        assert result['pagination'] == pagination

    def test_first_page_fields(self):
        """Only the requested keys of page one are returned."""
        pages = [{'Total': 1, 'GroupDefinitions': ['g']}, {'Total': 2}]

        assert first_page_fields(pages, ['Total', 'Missing']) == {'Total': 1}
        assert first_page_fields([], ['Total']) == {}

    @pytest.mark.parametrize(
        'pages,next_token,complete,expected',
        [
            ([{}], None, True, True),
            ([{}, {}], None, True, False),
            ([{}], None, False, False),
            ([{}], 'caller-token', True, False),
            ([], None, True, False),
        ],
        ids=['one-complete-page', 'two-pages', 'partial', 'continuation', 'no-pages'],
    )
    def test_whole_query_in_one_page(self, pages, next_token, complete, expected):
        """Only a single, complete, non-continuation page is the whole query."""
        pagination = {'complete_dataset': complete}

        assert whole_query_in_one_page(pages, next_token, pagination) is expected
