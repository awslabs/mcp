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

"""Unit tests for the credits_operations module."""

import boto3
import pytest
import sqlite3
from awslabs.billing_cost_management_mcp_server.tools.credits_operations import (
    GET_CREDIT_ALLOCATION_HISTORY_PAGE_SPEC,
    MAX_ALLOCATION_HISTORY_SECONDS,
    MAX_CREDITS_LOOKBACK_SECONDS,
    get_credit_allocation_history,
    get_credits,
)
from awslabs.billing_cost_management_mcp_server.utilities import sql_utils
from botocore.exceptions import ClientError
from botocore.stub import ANY, Stubber
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


CREATE_CLIENT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.credits_operations.create_aws_client'
)
CONVERT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.credits_operations.'
    'convert_response_if_needed'
)


@pytest.fixture
def mock_context():
    """Create a mock MCP context with async logging methods."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    context.debug = AsyncMock()
    return context


@pytest.fixture
def sample_credit():
    """Return a sample CreditData item as the AWS API would return it."""
    return {
        'creditId': '4242',
        'accountId': '123456789012',
        'creditType': 'Promotion',
        'description': 'Migration credit',
        'initialAmount': {'currencyCode': 'USD', 'currencyAmount': '1000.00'},
        'remainingAmount': {'currencyCode': 'USD', 'currencyAmount': '250.50'},
        'startDate': datetime(2026, 1, 1, tzinfo=timezone.utc),
        'endDate': datetime(2026, 12, 31, tzinfo=timezone.utc),
        'exhaustDate': datetime(2026, 9, 30, tzinfo=timezone.utc),
        'applicableProductNames': ['AmazonEC2'],
        'creditStatus': 'ENABLED',
    }


@pytest.fixture
def sample_allocation():
    """Return a sample allocation-history row as the AWS API would return it."""
    return {
        'creditId': '4242',
        'creditAmount': {'currencyCode': 'USD', 'currencyAmount': '100.25'},
        'accountId': '123456789012',
        'appliedServiceName': 'AmazonEC2',
        'billingMonth': '2026-06',
        'isEstimatedBill': False,
    }


def _await_call(mock):
    """Return a mock's most recent await, asserting one happened."""
    assert mock.await_args is not None
    return mock.await_args


def _client_factory(mock_client, mock_sts):
    """Build a create_aws_client side_effect returning per-service mocks."""

    def _factory(service_name, **kwargs):
        return mock_sts if service_name == 'sts' else mock_client

    return _factory


def _sts_mock(account_id='123456789012'):
    """Build an STS mock resolving to the given account."""
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {'Account': account_id}
    return mock_sts


def _get_credits_client(credits):
    """Build a billing client mock whose get_credits returns the given list."""
    mock_client = MagicMock()
    mock_client.get_credits.return_value = {'credits': credits}
    return mock_client


def _get_credit_allocation_history_client(pages):
    """Build a billing client mock whose get_credit_allocation_history returns pages in order.

    Args:
        pages: Raw API page dicts to return, one per call.

    Returns:
        A client mock.
    """
    mock_client = MagicMock()
    mock_client.get_credit_allocation_history.side_effect = list(pages)
    return mock_client


def _paginate_call(mock_client, index=0):
    """Return the keyword arguments of one get_credit_allocation_history request."""
    return mock_client.get_credit_allocation_history.call_args_list[index].kwargs


def _offset_date(days):
    """Return a UTC calendar date the given number of days from today.

    Windows for GetCredits are validated against the current date, so tests use
    offsets rather than literals. A literal would silently start exercising the
    clamp once it aged past the one-year lookback.

    Args:
        days: Day offset from today. Negative is in the past.

    Returns:
        Date string in ``YYYY-MM-DD`` format.
    """
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime('%Y-%m-%d')


def _epoch_of(date_string):
    """Convert a ``YYYY-MM-DD`` date to epoch seconds without the module's converter.

    Computing the expected value independently keeps the conversion assertion
    from merely restating the implementation.

    Args:
        date_string: Date in ``YYYY-MM-DD`` format.

    Returns:
        Epoch seconds at UTC midnight on that date.
    """
    parsed = datetime.strptime(date_string, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


async def _call_get_credits(ctx, mock_client, **kwargs):
    """Invoke get_credits with the billing and STS clients patched."""
    with patch(CREATE_CLIENT_PATH) as mock_create:
        mock_create.side_effect = _client_factory(mock_client, _sts_mock())
        return await get_credits(ctx, **kwargs)


async def _call_get_credit_allocation_history(ctx, mock_client, **kwargs):
    """Invoke get_credit_allocation_history with the clients patched."""
    with patch(CREATE_CLIENT_PATH) as mock_create:
        mock_create.side_effect = _client_factory(mock_client, _sts_mock())
        return await get_credit_allocation_history(ctx, **kwargs)


class TestGetCredits:
    """Successful GetCredits calls and response shaping."""

    @pytest.mark.asyncio
    async def test_converts_dates_to_epoch(self, mock_context, sample_credit):
        """Calendar dates are converted to epoch seconds for the API."""
        client = _get_credits_client([sample_credit])
        start, end = _offset_date(-200), _offset_date(-10)

        result = await _call_get_credits(mock_context, client, start_date=start, end_date=end)

        assert result['status'] == 'success'
        call = client.get_credits.call_args.kwargs
        assert call['startDate'] == _epoch_of(start)
        assert call['endDate'] == _epoch_of(end)

    @pytest.mark.asyncio
    async def test_normalizes_timestamp_fields(self, mock_context, sample_credit):
        """startDate, endDate and exhaustDate become readable strings."""
        client = _get_credits_client([sample_credit])

        result = await _call_get_credits(mock_context, client, start_date=_offset_date(-180))

        credit = result['data']['credits'][0]
        assert credit['startDate'] == '2026-01-01T00:00:00'
        assert credit['endDate'] == '2026-12-31T00:00:00'
        assert credit['exhaustDate'] == '2026-09-30T00:00:00'

    @pytest.mark.asyncio
    async def test_monetary_amounts_untouched(self, mock_context, sample_credit):
        """Monetary structures are returned exactly as the API provided them."""
        client = _get_credits_client([sample_credit])

        result = await _call_get_credits(mock_context, client, start_date=_offset_date(-180))

        credit = result['data']['credits'][0]
        assert credit['remainingAmount'] == {'currencyCode': 'USD', 'currencyAmount': '250.50'}
        assert credit['initialAmount']['currencyAmount'] == '1000.00'

    @pytest.mark.asyncio
    async def test_auto_detects_account_id(self, mock_context, sample_credit):
        """The caller's account is resolved via STS when none is supplied."""
        client = _get_credits_client([sample_credit])

        result = await _call_get_credits(mock_context, client, start_date=_offset_date(-180))

        assert result['status'] == 'success'
        assert client.get_credits.call_args.kwargs['accountId'] == '123456789012'

    @pytest.mark.asyncio
    async def test_explicit_account_id_is_used(self, mock_context, sample_credit):
        """An explicit account_id is passed through unchanged."""
        client = _get_credits_client([sample_credit])

        await _call_get_credits(
            mock_context, client, start_date=_offset_date(-180), account_id='999888777666'
        )

        assert client.get_credits.call_args.kwargs['accountId'] == '999888777666'

    @pytest.mark.asyncio
    async def test_payer_account_flag_passthrough(self, mock_context, sample_credit):
        """payer_account_flag is forwarded to the API when supplied."""
        client = _get_credits_client([sample_credit])

        await _call_get_credits(
            mock_context, client, start_date=_offset_date(-180), payer_account_flag=True
        )

        assert client.get_credits.call_args.kwargs['payerAccountFlag'] is True

    @pytest.mark.asyncio
    async def test_omits_unset_optional_parameters(self, mock_context, sample_credit):
        """Unset optional parameters are absent from the request."""
        client = _get_credits_client([sample_credit])

        await _call_get_credits(mock_context, client, start_date=_offset_date(-180))

        call = client.get_credits.call_args.kwargs
        assert 'endDate' not in call
        assert 'payerAccountFlag' not in call

    @pytest.mark.asyncio
    async def test_open_ended_window_reports_null_end(self, mock_context, sample_credit):
        """An omitted end_date is reported as a null end in the time range."""
        client = _get_credits_client([sample_credit])

        result = await _call_get_credits(mock_context, client, start_date=_offset_date(-180))

        assert result['data']['time_range']['end_date'] is None

    @pytest.mark.asyncio
    async def test_empty_credits_is_success(self, mock_context):
        """An account with no credits returns success with an empty list."""
        client = _get_credits_client([])

        result = await _call_get_credits(mock_context, client, start_date=_offset_date(-180))

        assert result['status'] == 'success'
        assert result['data']['credits'] == []


class TestGetCreditsValidation:
    """Input validation for GetCredits, before any API call."""

    @pytest.mark.asyncio
    async def test_missing_start_date(self, mock_context):
        """start_date is required."""
        client = _get_credits_client([])

        result = await _call_get_credits(mock_context, client)

        assert result['status'] == 'error'
        assert 'start_date is required' in result['data']['message']
        client.get_credits.assert_not_called()

    @pytest.mark.asyncio
    async def test_unparseable_date(self, mock_context):
        """A date that cannot be parsed is rejected without calling the API."""
        client = _get_credits_client([])

        result = await _call_get_credits(mock_context, client, start_date='not-a-date')

        assert result['status'] == 'error'
        client.get_credits.assert_not_called()

    @pytest.mark.asyncio
    async def test_end_before_start(self, mock_context):
        """An end date preceding the start is rejected."""
        client = _get_credits_client([])

        result = await _call_get_credits(
            mock_context, client, start_date=_offset_date(-30), end_date=_offset_date(-60)
        )

        assert result['status'] == 'error'
        assert 'must not precede' in result['data']['message']
        client.get_credits.assert_not_called()


class TestGetCreditsWindow:
    """Lookback clamping and window rejection for GetCredits.

    GetCredits accepts a start date no more than one year before the current
    date and no future end date, a tighter limit than the allocation ledger's
    24-month range.
    """

    @pytest.mark.asyncio
    async def test_start_beyond_one_year_is_narrowed(self, mock_context, sample_credit):
        """A start date older than the lookback is pulled forward to the limit."""
        client = _get_credits_client([sample_credit])
        requested = _offset_date(-3 * 365)

        result = await _call_get_credits(mock_context, client, start_date=requested)

        expected_floor = int(datetime.now(timezone.utc).timestamp()) - MAX_CREDITS_LOOKBACK_SECONDS
        sent = client.get_credits.call_args.kwargs['startDate']
        assert sent > _epoch_of(requested)
        assert abs(sent - expected_floor) <= 60
        assert result['data']['time_range']['limited_from_request'] is True

    @pytest.mark.asyncio
    async def test_narrowing_preserves_requested_window(self, mock_context, sample_credit):
        """The requested start is reported alongside the effective one."""
        client = _get_credits_client([sample_credit])
        requested = _offset_date(-3 * 365)

        result = await _call_get_credits(mock_context, client, start_date=requested)

        time_range = result['data']['time_range']
        assert time_range['requested_start_date'].startswith(requested)
        assert time_range['start_date'] != time_range['requested_start_date']
        assert time_range['requested_end_date'] is None
        assert time_range['max_lookback_months'] == 12

    @pytest.mark.asyncio
    async def test_in_range_window_is_not_narrowed(self, mock_context, sample_credit):
        """A start date inside the lookback is passed through untouched."""
        client = _get_credits_client([sample_credit])
        requested = _offset_date(-180)

        result = await _call_get_credits(mock_context, client, start_date=requested)

        assert client.get_credits.call_args.kwargs['startDate'] == _epoch_of(requested)
        assert result['data']['time_range']['limited_from_request'] is False

    @pytest.mark.asyncio
    async def test_future_end_date_is_clamped(self, mock_context, sample_credit):
        """An end date in the future is pulled back to now."""
        client = _get_credits_client([sample_credit])

        result = await _call_get_credits(
            mock_context, client, start_date=_offset_date(-30), end_date=_offset_date(90)
        )

        now_epoch = int(datetime.now(timezone.utc).timestamp())
        assert abs(client.get_credits.call_args.kwargs['endDate'] - now_epoch) <= 60
        assert result['data']['time_range']['limited_from_request'] is True

    @pytest.mark.asyncio
    async def test_window_start_never_exceeds_end(self, mock_context, sample_credit):
        """Clamping a window that straddles the lookback cannot invert it."""
        client = _get_credits_client([sample_credit])

        await _call_get_credits(
            mock_context, client, start_date=_offset_date(-2 * 365), end_date=_offset_date(-30)
        )

        call = client.get_credits.call_args.kwargs
        assert call['startDate'] < call['endDate']

    @pytest.mark.asyncio
    async def test_future_window_is_rejected(self, mock_context):
        """A window that has not started yet is refused without an API call."""
        client = _get_credits_client([])

        result = await _call_get_credits(
            mock_context, client, start_date=_offset_date(10), end_date=_offset_date(40)
        )

        assert result['status'] == 'error'
        assert 'starts in the future' in result['data']['message']
        client.get_credits.assert_not_called()

    @pytest.mark.asyncio
    async def test_window_entirely_before_lookback_is_rejected(self, mock_context):
        """A window ending before the lookback is refused rather than inverted.

        Clamping the start forward would push it past the end, so a window with
        no answerable overlap is an error instead of a narrowed result.
        """
        client = _get_credits_client([])

        result = await _call_get_credits(
            mock_context,
            client,
            start_date=_offset_date(-3 * 365),
            end_date=_offset_date(-2 * 365),
        )

        assert result['status'] == 'error'
        assert 'within the last year' in result['data']['message']
        client.get_credits.assert_not_called()


class TestGetCreditAllocationHistoryWindow:
    """Window selection, billing_period expansion and the 24-month clamp."""

    @pytest.mark.asyncio
    async def test_billing_period_expands_to_month(self, mock_context, sample_allocation):
        """A YYYY-MM billing period covers the whole calendar month."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06'
        )

        time_range = result['data']['time_range']
        assert time_range['start_date'].startswith('2026-06-01')
        assert time_range['end_date'].startswith('2026-06-30')

    @pytest.mark.asyncio
    async def test_billing_period_handles_leap_year(self, mock_context, sample_allocation):
        """February in a leap year ends on the 29th."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2024-02'
        )

        assert result['data']['time_range']['end_date'].startswith('2024-02-29')

    @pytest.mark.asyncio
    async def test_billing_period_handles_non_leap_year(self, mock_context, sample_allocation):
        """February in a non-leap year ends on the 28th."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-02'
        )

        assert result['data']['time_range']['end_date'].startswith('2026-02-28')

    @pytest.mark.asyncio
    async def test_billing_period_and_dates_are_mutually_exclusive(self, mock_context):
        """Supplying both window forms is rejected."""
        client = _get_credit_allocation_history_client([])

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06', start_date='2026-01-01'
        )

        assert result['status'] == 'error'
        assert 'mutually exclusive' in result['data']['message']
        client.get_credit_allocation_history.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize('value', ['2026-13', '2026', 'june', '2026-00', ''])
    async def test_invalid_billing_period(self, mock_context, value):
        """A malformed billing period is rejected without calling the API."""
        client = _get_credit_allocation_history_client([])

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period=value
        )

        assert result['status'] == 'error'
        assert 'YYYY-MM' in result['message']
        client.get_credit_allocation_history.assert_not_called()

    @pytest.mark.asyncio
    async def test_both_dates_required(self, mock_context):
        """The date-pair form requires start_date and end_date together."""
        client = _get_credit_allocation_history_client([])

        result = await _call_get_credit_allocation_history(
            mock_context, client, start_date='2026-01-01'
        )

        assert result['status'] == 'error'
        client.get_credit_allocation_history.assert_not_called()

    @pytest.mark.asyncio
    async def test_range_over_24_months_is_narrowed(self, mock_context, sample_allocation):
        """A range longer than 24 months is narrowed to the enforced window."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, start_date='2018-01-01', end_date='2030-01-01'
        )

        call = _paginate_call(client)
        assert call['endDate'] - call['startDate'] == MAX_ALLOCATION_HISTORY_SECONDS
        assert result['data']['time_range']['limited_from_request'] is True

    @pytest.mark.asyncio
    async def test_narrowing_preserves_requested_window(self, mock_context, sample_allocation):
        """The requested range is reported alongside the effective one."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, start_date='2018-01-01', end_date='2030-01-01'
        )

        time_range = result['data']['time_range']
        assert time_range['requested_start_date'].startswith('2018-01-01')
        assert time_range['requested_end_date'].startswith('2030-01-01')
        assert time_range['max_range_months'] == 24

    @pytest.mark.asyncio
    async def test_future_end_date_is_clamped(self, mock_context, sample_allocation):
        """An end date in the future is clamped to now."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, start_date='2026-01-01', end_date='2099-01-01'
        )

        now_epoch = int(datetime.now(timezone.utc).timestamp())
        assert _paginate_call(client)['endDate'] <= now_epoch
        assert result['data']['time_range']['limited_from_request'] is True

    @pytest.mark.asyncio
    async def test_future_billing_period_is_rejected(self, mock_context):
        """A billing period that has not started yet is rejected, not clamped."""
        client = _get_credit_allocation_history_client([])

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2099-01'
        )

        assert result['status'] == 'error'
        assert 'starts in the future' in result['data']['message']
        client.get_credit_allocation_history.assert_not_called()

    @pytest.mark.asyncio
    async def test_future_date_pair_is_rejected(self, mock_context):
        """A fully future date range is rejected rather than inverted by clamping."""
        client = _get_credit_allocation_history_client([])

        result = await _call_get_credit_allocation_history(
            mock_context, client, start_date='2099-01-01', end_date='2099-06-30'
        )

        assert result['status'] == 'error'
        client.get_credit_allocation_history.assert_not_called()

    @pytest.mark.asyncio
    async def test_window_start_never_exceeds_end(self, mock_context, sample_allocation):
        """Clamping a future end date can never produce an inverted range."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        await _call_get_credit_allocation_history(
            mock_context, client, start_date='2026-01-01', end_date='2099-01-01'
        )

        call = _paginate_call(client)
        assert call['startDate'] < call['endDate']

    @pytest.mark.asyncio
    async def test_in_range_window_is_not_narrowed(self, mock_context, sample_allocation):
        """A window inside the limit is passed through unchanged."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06'
        )

        assert result['data']['time_range']['limited_from_request'] is False


def _ledger_page(row, token=None, **extra):
    """Build one GetCreditAllocationHistory page."""
    page = {'creditAllocationHistoryList': [row], **extra}
    if token is not None:
        page['nextToken'] = token
    return page


class TestGetCreditAllocationHistoryPagination:
    """Paging through the shared helper and the pagination block."""

    @pytest.mark.asyncio
    async def test_no_max_items_fetches_every_page(self, mock_context, sample_allocation):
        """Without max_items every page is fetched at the largest page size."""
        client = _get_credit_allocation_history_client(
            [
                _ledger_page(sample_allocation, 'page-2'),
                _ledger_page(sample_allocation, 'page-3'),
                _ledger_page(sample_allocation),
            ]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06'
        )

        data = result['data']
        assert len(data['credit_allocation_history']) == 3
        assert data['pagination'] == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 3,
        }
        assert 'warning' not in data
        assert 'complete_dataset' not in data
        assert client.get_credit_allocation_history.call_count == 3
        assert all(
            call.kwargs['maxResults'] == 500
            for call in client.get_credit_allocation_history.call_args_list
        )

    @pytest.mark.asyncio
    async def test_empty_string_token_on_last_page_reports_complete(
        self, mock_context, sample_allocation
    ):
        """An empty-string token on the last page reads as complete, not as more pages."""
        client = _get_credit_allocation_history_client(
            [_ledger_page(sample_allocation, 'page-2'), _ledger_page(sample_allocation, '')]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06'
        )

        pagination = result['data']['pagination']
        assert pagination['has_more'] is False
        assert pagination['next_token'] is None
        assert pagination['complete_dataset'] is True
        assert client.get_credit_allocation_history.call_count == 2

    def test_page_max_is_the_service_clamp(self):
        """The service clamps a page to 500 rows, so 500 is the largest page requested."""
        assert GET_CREDIT_ALLOCATION_HISTORY_PAGE_SPEC.page_max == 500

    @pytest.mark.asyncio
    async def test_page_past_max_results_at_a_bill_boundary_is_kept(
        self, mock_context, sample_allocation
    ):
        """A page ends only at a bill boundary, so rows beyond maxResults are kept."""
        client = _get_credit_allocation_history_client(
            [
                {
                    'creditAllocationHistoryList': [sample_allocation] * 520,
                    'nextToken': 'page-2',
                }
            ]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06', max_items=500
        )

        assert _paginate_call(client)['maxResults'] == 500
        data = result['data']
        assert data['pagination']['items_returned'] == 520
        assert data['pagination']['next_token'] == 'page-2'

    @pytest.mark.asyncio
    async def test_max_items_stops_before_exceeding(self, mock_context, sample_allocation):
        """max_items sizes the page and stops once it is reached, returning the token."""
        page = {
            'creditAllocationHistoryList': [sample_allocation] * 5,
            'nextToken': 'page-2',
        }
        client = _get_credit_allocation_history_client([page])

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06', max_items=5
        )

        data = result['data']
        assert _paginate_call(client)['maxResults'] == 5
        assert client.get_credit_allocation_history.call_count == 1
        assert data['complete_dataset'] is False
        assert 'Partial data' in data['warning']
        assert list(data)[:2] == ['complete_dataset', 'warning']
        assert data['pagination'] == {
            'complete_dataset': False,
            'has_more': True,
            'next_token': 'page-2',
            'items_returned': 5,
        }

    @pytest.mark.asyncio
    async def test_continuation_sends_token_and_identical_params(
        self, mock_context, sample_allocation
    ):
        """A continuation sends the caller's token and otherwise the same request."""
        first = _get_credit_allocation_history_client([_ledger_page(sample_allocation, 'page-2')])
        await _call_get_credit_allocation_history(
            mock_context, first, billing_period='2026-06', credit_id='42', max_items=1
        )
        resumed = _get_credit_allocation_history_client([_ledger_page(sample_allocation)])
        result = await _call_get_credit_allocation_history(
            mock_context,
            resumed,
            billing_period='2026-06',
            credit_id='42',
            max_items=1,
            next_token='page-2',
        )

        first_call = _paginate_call(first)
        resumed_call = _paginate_call(resumed)
        assert resumed_call['nextToken'] == 'page-2'
        assert 'nextToken' not in first_call
        assert {k: v for k, v in resumed_call.items() if k != 'nextToken'} == first_call
        assert result['data']['pagination']['complete_dataset'] is True

    @pytest.mark.asyncio
    async def test_rejected_token_is_invalid_next_token(self, mock_context):
        """A token the service rejects maps to invalid_next_token."""
        client = MagicMock()
        client.get_credit_allocation_history.side_effect = ClientError(
            {'Error': {'Code': 'InvalidNextTokenException', 'Message': 'bad token'}},
            'GetCreditAllocationHistory',
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06', next_token='stale'
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'


class TestGetCreditAllocationHistoryRealClient:
    """Request shape verified against a real billing client with stubbed responses."""

    @staticmethod
    def _stubbed_client(page_tokens):
        """Build a real billing client with stubbed pages.

        Args:
            page_tokens: Continuation token for each page, None on the last.

        Returns:
            Tuple of (client, stubber) with responses queued.
        """
        client = boto3.Session(
            aws_access_key_id='a', aws_secret_access_key='b', region_name='us-east-1'
        ).client('billing')
        stubber = Stubber(client)
        stubber.activate()
        row = {
            'creditId': '1',
            'creditAmount': {'currencyCode': 'USD', 'currencyAmount': '1.00'},
            'accountId': '123456789012',
            'appliedServiceName': 'AmazonEC2',
            'billingMonth': '2026-06',
            'isEstimatedBill': False,
        }
        expected = {
            'accountId': '123456789012',
            'startDate': ANY,
            'endDate': ANY,
            'maxResults': 500,
        }
        previous = None
        for token in page_tokens:
            response = {'creditAllocationHistoryList': [row], 'partialResults': False}
            if token:
                response['nextToken'] = token
            params = dict(expected)
            if previous:
                params['nextToken'] = previous
            stubber.add_response('get_credit_allocation_history', response, params)
            previous = token
        return client, stubber

    @pytest.mark.asyncio
    async def test_exhausted_run_reports_complete(self, mock_context):
        """Consuming every page reports a complete dataset with no token."""
        client, stubber = self._stubbed_client(['P2', 'P3', None])

        try:
            result = await _call_get_credit_allocation_history(
                mock_context, client, account_id='123456789012', billing_period='2026-06'
            )
            stubber.assert_no_pending_responses()
        finally:
            stubber.deactivate()

        pagination = result['data']['pagination']
        assert pagination['items_returned'] == 3
        assert pagination['has_more'] is False
        assert pagination['next_token'] is None
        assert pagination['complete_dataset'] is True


class TestGetCreditAllocationHistoryCompleteness:
    """partialResults and failedMonths reporting."""

    @pytest.mark.asyncio
    async def test_defaults_to_complete(self, mock_context, sample_allocation):
        """A clean response reports complete results and no failed months."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06'
        )

        assert result['data']['completeness'] == {
            'partial_results': False,
            'failed_months': [],
        }

    @pytest.mark.asyncio
    async def test_partial_results_from_any_page(self, mock_context, sample_allocation):
        """A partial flag on any page marks the whole result partial."""
        client = _get_credit_allocation_history_client(
            [
                {'creditAllocationHistoryList': [sample_allocation], 'nextToken': 'page-2'},
                {
                    'creditAllocationHistoryList': [sample_allocation],
                    'partialResults': True,
                    'failedMonths': ['2026-03'],
                },
            ]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06'
        )

        assert result['data']['completeness']['partial_results'] is True
        assert result['data']['completeness']['failed_months'] == ['2026-03']

    @pytest.mark.asyncio
    async def test_failed_months_are_unioned_without_duplicates(
        self, mock_context, sample_allocation
    ):
        """Failed months from every page are combined and de-duplicated."""
        client = _get_credit_allocation_history_client(
            [
                {
                    'creditAllocationHistoryList': [sample_allocation],
                    'partialResults': True,
                    'failedMonths': ['2026-03', '2026-04'],
                    'nextToken': 'page-2',
                },
                {
                    'creditAllocationHistoryList': [sample_allocation],
                    'partialResults': True,
                    'failedMonths': ['2026-04', '2026-05'],
                },
            ]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06'
        )

        assert result['data']['completeness']['failed_months'] == [
            '2026-03',
            '2026-04',
            '2026-05',
        ]


class TestCreditIdConversion:
    """creditId type handling between the two operations."""

    @pytest.mark.asyncio
    async def test_string_credit_id_becomes_integer(self, mock_context, sample_allocation):
        """The string creditId returned by GetCredits is converted to an integer."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06', credit_id='4242'
        )

        assert _paginate_call(client)['creditId'] == 4242

    @pytest.mark.asyncio
    async def test_integer_credit_id_passes_through(self, mock_context, sample_allocation):
        """An integer creditId is forwarded unchanged."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06', credit_id=4242
        )

        assert _paginate_call(client)['creditId'] == 4242

    @pytest.mark.asyncio
    async def test_omitted_credit_id_is_absent(self, mock_context, sample_allocation):
        """No creditId parameter is sent when the caller omits it."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        await _call_get_credit_allocation_history(mock_context, client, billing_period='2026-06')

        assert 'creditId' not in _paginate_call(client)

    @pytest.mark.asyncio
    async def test_non_numeric_credit_id_is_rejected(self, mock_context):
        """A non-numeric creditId is rejected with a pointer to get_credits."""
        client = _get_credit_allocation_history_client([])

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06', credit_id='abc'
        )

        assert result['status'] == 'error'
        assert 'must be numeric' in result['data']['message']
        assert 'get_credits' in result['data']['message']
        client.get_credit_allocation_history.assert_not_called()


class TestAccessDenied:
    """Permission failures name the missing IAM action."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize('error_code', ['AccessDeniedException', 'AccessDenied'])
    async def test_get_credits_names_permission(self, mock_context, error_code):
        """A denied GetCredits call names billing:GetCredits."""
        client = MagicMock()
        client.get_credits.side_effect = ClientError(
            {
                'Error': {'Code': error_code, 'Message': 'denied'},
                'ResponseMetadata': {'RequestId': 'req-1', 'HTTPStatusCode': 403},
            },
            'GetCredits',
        )

        result = await _call_get_credits(mock_context, client, start_date=_offset_date(-180))

        assert result['error_type'] == 'access_denied'
        assert 'billing:GetCredits' in result['message']
        assert result['request_id'] == 'req-1'
        assert result['http_status'] == 403

    @pytest.mark.asyncio
    async def test_get_credit_allocation_history_names_permission(self, mock_context):
        """A denied allocation-history call names its own action."""
        client = _get_credit_allocation_history_client([])
        client.get_credit_allocation_history.side_effect = ClientError(
            {
                'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'},
                'ResponseMetadata': {'RequestId': 'req-2', 'HTTPStatusCode': 403},
            },
            'GetCreditAllocationHistory',
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06'
        )

        assert result['error_type'] == 'access_denied'
        assert 'billing:GetCreditAllocationHistory' in result['message']
        assert 'resolution' in result

    @pytest.mark.asyncio
    async def test_denial_is_not_reported_as_missing_data(self, mock_context):
        """The message distinguishes a permission failure from having no credits."""
        client = MagicMock()
        client.get_credits.side_effect = ClientError(
            {
                'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'},
                'ResponseMetadata': {'RequestId': 'req-3', 'HTTPStatusCode': 403},
            },
            'GetCredits',
        )

        result = await _call_get_credits(mock_context, client, start_date=_offset_date(-180))

        assert 'not an absence of credits' in result['message']

    @pytest.mark.asyncio
    async def test_other_client_errors_fall_through(self, mock_context):
        """A non-permission error keeps the AWS error code from the shared handler."""
        client = MagicMock()
        client.get_credits.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad range'},
                'ResponseMetadata': {'RequestId': 'req-4', 'HTTPStatusCode': 400},
            },
            'GetCredits',
        )

        result = await _call_get_credits(mock_context, client, start_date=_offset_date(-180))

        assert result['error_type'] == 'ValidationException'
        assert result['status'] == 'error'


class TestSessionSqlOffload:
    """Oversized responses offload to a queryable table, not a single JSON cell."""

    @pytest.mark.asyncio
    async def test_ledger_offloads_one_row_per_record(self, mock_context, sample_allocation):
        """A large ledger becomes a table with one row per allocation record."""
        rows = [dict(sample_allocation, appliedServiceName=f'Service{i}') for i in range(40)]
        client = _get_credit_allocation_history_client([{'creditAllocationHistoryList': rows}])

        with patch.object(sql_utils, 'SQL_CONVERSION_THRESHOLD', 1):
            result = await _call_get_credit_allocation_history(
                mock_context, client, billing_period='2026-06'
            )

        data = result['data']
        assert data['data_stored'] is True
        connection = sqlite3.connect(data['session_db'])
        try:
            columns = [
                row[1] for row in connection.execute(f'PRAGMA table_info({data["table_name"]})')
            ]
            count = connection.execute(f'SELECT COUNT(*) FROM {data["table_name"]}').fetchone()[0]
        finally:
            connection.close()

        assert count == 40
        assert 'appliedServiceName' in columns
        assert 'billingMonth' in columns

    @pytest.mark.asyncio
    async def test_offload_preserves_guardrail_blocks(self, mock_context, sample_allocation):
        """time_range and completeness survive an offload."""
        rows = [dict(sample_allocation) for _ in range(40)]
        client = _get_credit_allocation_history_client(
            [
                {
                    'creditAllocationHistoryList': rows,
                    'partialResults': True,
                    'failedMonths': ['2026-03'],
                }
            ]
        )

        with patch.object(sql_utils, 'SQL_CONVERSION_THRESHOLD', 1):
            result = await _call_get_credit_allocation_history(
                mock_context, client, billing_period='2026-06'
            )

        data = result['data']
        assert data['completeness'] == {'partial_results': True, 'failed_months': ['2026-03']}
        assert data['time_range']['start_date'].startswith('2026-06-01')
        assert data['pagination']['complete_dataset'] is True
        assert data['pagination']['items_returned'] == 40

    @pytest.mark.asyncio
    async def test_credits_offload_preserves_time_range(self, mock_context, sample_credit):
        """A large credit portfolio keeps its time_range after an offload."""
        credits = [dict(sample_credit, creditId=str(i)) for i in range(40)]
        client = _get_credits_client(credits)
        start = _offset_date(-180)

        with patch.object(sql_utils, 'SQL_CONVERSION_THRESHOLD', 1):
            result = await _call_get_credits(mock_context, client, start_date=start)

        data = result['data']
        assert data['data_stored'] is True
        assert data['time_range']['start_date'].startswith(start)

    @pytest.mark.asyncio
    async def test_small_response_stays_inline(self, mock_context, sample_allocation):
        """A response under the threshold keeps its rows inline."""
        client = _get_credit_allocation_history_client(
            [{'creditAllocationHistoryList': [sample_allocation]}]
        )

        result = await _call_get_credit_allocation_history(
            mock_context, client, billing_period='2026-06'
        )

        assert result['data']['credit_allocation_history'] == [sample_allocation]
        assert 'data_stored' not in result['data']
