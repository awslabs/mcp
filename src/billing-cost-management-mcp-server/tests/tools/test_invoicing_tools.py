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

"""Unit tests for the invoicing_operations and invoicing_tools modules."""

import asyncio
import botocore.session
import pytest
import re
from awslabs.billing_cost_management_mcp_server.tools.invoicing_operations import (
    list_invoice_summaries,
)
from awslabs.billing_cost_management_mcp_server.tools.invoicing_tools import invoicing_server
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from fastmcp import Client
from unittest.mock import AsyncMock, MagicMock, patch


CREATE_CLIENT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.invoicing_operations.create_aws_client'
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
def sample_summary():
    """Return a sample InvoiceSummary as the AWS API would return it."""
    return {
        'AccountId': '123456789012',
        'InvoiceId': 'INV-001',
        'InvoiceType': 'INVOICE',
        'IssuedDate': datetime(2026, 5, 1, tzinfo=timezone.utc),
        'DueDate': datetime(2026, 6, 15, tzinfo=timezone.utc),
        'BillingPeriod': {'Month': 5, 'Year': 2026},
        'Entity': {'InvoicingEntity': 'Amazon Web Services, Inc.'},
        'BaseCurrencyAmount': {
            'TotalAmount': '1500.00',
            'TotalAmountBeforeTax': '1400.00',
            'CurrencyCode': 'USD',
        },
    }


def _client_factory(mock_client, mock_sts):
    """Build a create_aws_client side_effect returning per-service mocks."""

    def _factory(service_name, **kwargs):
        return mock_sts if service_name == 'sts' else mock_client

    return _factory


def _assert_validation_error(result):
    """Local validation failures carry the same top-level classification as AWS errors."""
    assert result['error_type'] == 'validation_error'
    assert result['operation'] == 'ListInvoiceSummaries'
    assert result['service'] == 'Invoicing'
    # The text lives in data['message'] at the call site; it must also be top level.
    assert result['message'] == result['data']['message']


class TestListInvoiceSummariesSelector:
    """Selector resolution and account auto-detection."""

    @pytest.mark.asyncio
    async def test_billing_period_auto_detects_account(self, mock_context, sample_summary):
        """A billing_period query auto-detects the account via STS."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, mock_sts)
            result = await list_invoice_summaries(mock_context, billing_period='2026-05')

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Selector'] == {'ResourceType': 'ACCOUNT_ID', 'Value': '123456789012'}
        assert call['Filter']['BillingPeriod'] == {'Month': 5, 'Year': 2026}
        mock_sts.get_caller_identity.assert_called_once()

    @pytest.mark.asyncio
    async def test_explicit_account_id_skips_sts(self, mock_context, sample_summary):
        """An explicit account_id is used directly without an STS call."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}
        mock_sts = MagicMock()

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, mock_sts)
            result = await list_invoice_summaries(
                mock_context, account_id='999888777666', billing_period='2026-05'
            )

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Selector']['Value'] == '999888777666'
        mock_sts.get_caller_identity.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoice_id_selector(self, mock_context, sample_summary):
        """An invoice_id builds an INVOICE_ID selector and skips STS."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}
        mock_sts = MagicMock()

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, mock_sts)
            result = await list_invoice_summaries(mock_context, invoice_id='INV-001')

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Selector'] == {'ResourceType': 'INVOICE_ID', 'Value': 'INV-001'}
        mock_sts.get_caller_identity.assert_not_called()

    @pytest.mark.asyncio
    async def test_account_and_invoice_both_provided(self, mock_context):
        """Providing both account_id and invoice_id returns an error."""
        result = await list_invoice_summaries(
            mock_context, account_id='123456789012', invoice_id='INV-001'
        )

        assert result['status'] == 'error'
        assert 'not both' in result['data']['message']
        _assert_validation_error(result)

    @pytest.mark.asyncio
    async def test_selector_conflict_reported_before_time_filter(self, mock_context):
        """account_id plus invoice_id plus a time filter reports the selector conflict first."""
        result = await list_invoice_summaries(
            mock_context,
            account_id='123456789012',
            invoice_id='INV-001',
            billing_period='2026-05',
        )

        assert result['status'] == 'error'
        assert 'not both' in result['data']['message']
        _assert_validation_error(result)

    @pytest.mark.asyncio
    async def test_sts_exception_returns_error(self, mock_context):
        """When account_id is omitted and STS get_caller_identity raises, status is error."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {'Error': {'Code': 'ExpiredTokenException', 'Message': 'Token expired'}},
            'GetCallerIdentity',
        )

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_sts
            result = await list_invoice_summaries(mock_context, billing_period='2026-05')

        assert result['status'] == 'error'


class TestListInvoiceSummariesSelectorEcho:
    """The response names the account or invoice the result was read for.

    The request shape is covered above; these assert the echo, which is the
    only place the queried identity appears. A row's ``AccountId`` cannot stand
    in for it: an account query also returns invoices issued to invoice-unit
    receivers billed from that account, and those rows name a different account.
    """

    @pytest.mark.asyncio
    async def test_auto_detected_selector_echoed(self, mock_context, sample_summary):
        """An account resolved from the caller's identity is echoed as auto-detected."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, mock_sts)
            result = await list_invoice_summaries(mock_context, billing_period='2026-05')

        assert result['status'] == 'success'
        assert result['data']['selector'] == {
            'type': 'ACCOUNT_ID',
            'value': '123456789012',
            'auto_detected': True,
        }

    @pytest.mark.asyncio
    async def test_explicit_selector_echoed_not_auto_detected(self, mock_context, sample_summary):
        """An account given in the request is echoed, and not as auto-detected."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}
        mock_sts = MagicMock()

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, mock_sts)
            result = await list_invoice_summaries(
                mock_context, account_id='999888777666', billing_period='2026-05'
            )

        assert result['status'] == 'success'
        assert result['data']['selector'] == {
            'type': 'ACCOUNT_ID',
            'value': '999888777666',
            'auto_detected': False,
        }

    @pytest.mark.asyncio
    async def test_invoice_id_selector_echoed(self, mock_context, sample_summary):
        """An invoice query echoes INVOICE_ID, even when the row names another account."""
        other_account = dict(sample_summary, AccountId='210987654321')
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [other_account]}
        mock_sts = MagicMock()

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, mock_sts)
            result = await list_invoice_summaries(mock_context, invoice_id='INV-001')

        assert result['status'] == 'success'
        assert result['data']['selector'] == {
            'type': 'INVOICE_ID',
            'value': 'INV-001',
            'auto_detected': False,
        }
        # The row's own account differs from the selector, so a reader taking the
        # queried identity from the row would get the wrong answer.
        assert result['data']['invoice_summaries'][0]['AccountId'] == '210987654321'


class TestListInvoiceSummariesReceiverRole:
    """``receiver_role`` reaches the API, and changes the span cap but nothing else.

    The parameter is worth its own class because two parts of its behavior are
    counter-intuitive and a regression in either is silent: it raises the span
    cap only when set, and it is not a superset of the same query without it.
    """

    @pytest.mark.asyncio
    async def test_receiver_role_sent_as_filter(self, mock_context, sample_summary):
        """receiver_role reaches boto3 as Filter.ReceiverRole."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, MagicMock())
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                billing_period='2026-09',
                receiver_role='BUYER',
            )

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Filter']['ReceiverRole'] == 'BUYER'
        assert call['Filter']['BillingPeriod'] == {'Month': 9, 'Year': 2026}

    @pytest.mark.asyncio
    async def test_receiver_role_lifts_one_month_cap(self, mock_context, sample_summary):
        """A 92-day range is accepted with a receiver role and sent whole."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, MagicMock())
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-06-01',
                end_date='2026-09-01',
                receiver_role='BUYER',
            )

        assert result['status'] == 'success'
        assert 'suggested_date_ranges' not in result['data']
        interval = mock_client.list_invoice_summaries.call_args.kwargs['Filter']['TimeInterval']
        assert interval == {
            'StartDate': int(datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp()),
            'EndDate': int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp()),
        }

    @pytest.mark.asyncio
    async def test_without_receiver_role_cap_and_suggestions_unchanged(self, mock_context):
        """The same range without a role is still rejected, with the per-month split."""
        with patch(CREATE_CLIENT_PATH) as mock_create:
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-06-01',
                end_date='2026-09-01',
            )

        _assert_validation_error(result)
        assert len(result['data']['suggested_date_ranges']) == 3
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_receiver_role_start_before_the_estimate_era_reaches_the_api(
        self, mock_context, sample_summary
    ):
        """No local floor is imposed on how far back a receiver_role range may start.

        A range starting well before the feature's first data is accepted by the
        service, so rejecting it locally would refuse a request that works.
        """
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, MagicMock())
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2025-03-01',
                end_date='2025-08-01',
                receiver_role='BUYER',
            )

        assert result['status'] == 'success'
        mock_client.list_invoice_summaries.assert_called_once()

    @pytest.mark.asyncio
    async def test_receiver_role_span_over_five_years_rejected_locally(self, mock_context):
        """A span past five years is refused before any AWS call, naming the bound."""
        with patch(CREATE_CLIENT_PATH) as mock_create:
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2020-01-01',
                end_date='2026-01-02',
                receiver_role='BUYER',
            )

        _assert_validation_error(result)
        assert 'five years' in result['data']['message']
        # The per-month split is meaningless at this scale and is not offered.
        assert 'suggested_date_ranges' not in result['data']
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_exactly_five_years_is_rejected(self, mock_context):
        """The service requires LESS than five years, so an exact span is refused.

        Verified live: a start of 2021-10-01 with an end of exactly 2026-10-01
        and ReceiverRole=BUYER is rejected with "TimePeriod must be less than
        5 years". Allowing it locally would send a request that cannot succeed.
        """
        with patch(CREATE_CLIENT_PATH) as mock_create:
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2021-10-01',
                end_date='2026-10-01',
                receiver_role='BUYER',
            )

        _assert_validation_error(result)
        assert 'less than five years' in result['data']['message']
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_one_day_under_five_years_is_allowed(self, mock_context, sample_summary):
        """One day short of the bound reaches the API, as it does live."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, MagicMock())
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2021-10-02',
                end_date='2026-10-01',
                receiver_role='BUYER',
            )

        assert result['status'] == 'success'
        mock_client.list_invoice_summaries.assert_called_once()

    @pytest.mark.asyncio
    async def test_one_second_over_five_years_is_rejected(self, mock_context):
        """The bound is compared on instants, not on whole days.

        Together with the two tests above this pins the boundary: a bound of
        six years, or one floored to whole days, fails at least one of them.
        A day-floored check would admit this range, because five years plus
        23:59:59 floors to exactly five years in days.
        """
        with patch(CREATE_CLIENT_PATH) as mock_create:
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2021-10-01',
                end_date='2026-10-01T00:00:01',
                receiver_role='BUYER',
            )

        _assert_validation_error(result)
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_leap_day_start_resolves_forward_to_1_march(self, mock_context, sample_summary):
        """A 29 February start has no counterpart five years on.

        The service resolves it FORWARD to 1 March, not back to 28 February.
        Verified live with ReceiverRole=BUYER from a 2024-02-29 start: an end
        of 2029-02-28T23:59:59 is accepted and 2029-03-01 is rejected with
        "TimePeriod must be less than 5 years". Clamping to 28 February, as
        this did before, refused a whole day of ranges the service accepts.
        """
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        for end in ('2029-02-27', '2029-02-28', '2029-02-28T23:59:59'):
            with patch(CREATE_CLIENT_PATH) as mock_create:
                mock_create.side_effect = _client_factory(mock_client, MagicMock())
                accepted = await list_invoice_summaries(
                    mock_context,
                    account_id='123456789012',
                    start_date='2024-02-29',
                    end_date=end,
                    receiver_role='BUYER',
                )
            assert accepted['status'] == 'success', end

        with patch(CREATE_CLIENT_PATH) as mock_create:
            refused = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2024-02-29',
                end_date='2029-03-01',
                receiver_role='BUYER',
            )
        _assert_validation_error(refused)
        mock_create.assert_not_called()
        # The bound named in the message is the one the service enforces.
        assert '2029-03-01' in refused['data']['message']

    @pytest.mark.asyncio
    async def test_leap_day_bound_keeps_the_start_time_of_day(self, mock_context, sample_summary):
        """The 1 March bound carries the start's time of day, not midnight.

        Verified live from a 2024-02-29T12:00:00 start: 2029-03-01T11:59:59 is
        accepted and 2029-03-01T12:00:00 is rejected. Flooring the bound to
        midnight on 1 March would refuse half a day the service accepts.
        """
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, MagicMock())
            accepted = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2024-02-29T12:00:00',
                end_date='2029-03-01T11:59:59',
                receiver_role='BUYER',
            )
        assert accepted['status'] == 'success'

        with patch(CREATE_CLIENT_PATH) as mock_create:
            refused = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2024-02-29T12:00:00',
                end_date='2029-03-01T12:00:00',
                receiver_role='BUYER',
            )
        _assert_validation_error(refused)
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_receiver_role_with_invoice_id_is_rejected(self, mock_context):
        """A role makes the service read the request as an account query.

        Verified live with a real invoice id: the role alone is rejected
        ("BillingPeriod and TimePeriod cannot both be null when retrieve
        invoice summary by account ID"), and the role plus a billing period
        returns 0 rows for an invoice that exists -- which reads as "not
        found". Refusing locally is the only outcome that says what is wrong.
        """
        with patch(CREATE_CLIENT_PATH) as mock_create:
            result = await list_invoice_summaries(
                mock_context, invoice_id='INV-001', receiver_role='BUYER'
            )

        _assert_validation_error(result)
        assert 'account queries only' in result['data']['message']
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_receiver_role_still_requires_a_time_filter(self, mock_context):
        """A role lifts the span cap but does not remove the filter requirement.

        The message must name the role's own bound, not the one-month rule it
        replaces, or it advises a per-month split that is no longer needed.
        """
        with patch(CREATE_CLIENT_PATH) as mock_create:
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', receiver_role='BUYER'
            )

        _assert_validation_error(result)
        message = result['data']['message']
        assert 'less than five years' in message
        assert 'one call per month' not in message
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_receiver_role_survives_a_continuation(self, mock_context, sample_summary):
        """A continuation keeps the role, or page two answers a different query."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, MagicMock())
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                billing_period='2026-09',
                receiver_role='BUYER',
                next_token='page-2',
            )

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Filter']['ReceiverRole'] == 'BUYER'
        assert call['NextToken'] == 'page-2'


class TestListInvoiceSummariesFilter:
    """Filter construction and validation."""

    @pytest.mark.asyncio
    async def test_time_interval_uses_epoch_seconds(self, mock_context, sample_summary):
        """A start/end range builds a TimeInterval with epoch-second values."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-06-01',
                end_date='2026-06-30',
            )

        assert result['status'] == 'success'
        interval = mock_client.list_invoice_summaries.call_args.kwargs['Filter']['TimeInterval']
        assert interval['StartDate'] == int(datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp())
        assert interval['EndDate'] == int(datetime(2026, 6, 30, tzinfo=timezone.utc).timestamp())

    @pytest.mark.asyncio
    async def test_invoicing_entity_filter(self, mock_context, sample_summary):
        """The invoicing_entity value is passed through to the Filter."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                billing_period='2026-05',
                invoicing_entity='Amazon Web Services, Inc.',
            )

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Filter']['InvoicingEntity'] == 'Amazon Web Services, Inc.'

    @pytest.mark.asyncio
    async def test_billing_period_and_dates_mutually_exclusive(self, mock_context):
        """billing_period together with a date range returns an error."""
        result = await list_invoice_summaries(
            mock_context,
            account_id='123456789012',
            billing_period='2026-05',
            start_date='2026-01-01',
            end_date='2026-06-30',
        )

        assert result['status'] == 'error'
        assert 'mutually' in result['data']['message'].lower()
        _assert_validation_error(result)

    @pytest.mark.asyncio
    async def test_start_date_without_end_date(self, mock_context):
        """start_date without end_date returns an error."""
        result = await list_invoice_summaries(
            mock_context, account_id='123456789012', start_date='2026-01-01'
        )

        assert result['status'] == 'error'
        assert 'together' in result['data']['message'].lower()
        _assert_validation_error(result)

    @pytest.mark.asyncio
    async def test_invalid_billing_period_format(self, mock_context):
        """A malformed billing_period returns a YYYY-MM error."""
        result = await list_invoice_summaries(mock_context, billing_period='2026')

        assert result['status'] == 'error'
        assert 'YYYY-MM' in result['data']['message']
        _assert_validation_error(result)

    @pytest.mark.asyncio
    async def test_non_numeric_billing_period(self, mock_context):
        """A billing_period with non-numeric parts returns a YYYY-MM error."""
        result = await list_invoice_summaries(mock_context, billing_period='2026-ab')

        assert result['status'] == 'error'
        assert 'YYYY-MM' in result['data']['message']
        _assert_validation_error(result)

    @pytest.mark.asyncio
    async def test_invalid_billing_period_month(self, mock_context):
        """An out-of-range month returns an error."""
        result = await list_invoice_summaries(mock_context, billing_period='2026-13')

        assert result['status'] == 'error'
        assert 'month' in result['data']['message'].lower()
        _assert_validation_error(result)

    @pytest.mark.asyncio
    async def test_invalid_date_format(self, mock_context):
        """A malformed start_date returns a format error."""
        result = await list_invoice_summaries(
            mock_context,
            account_id='123456789012',
            start_date='not-a-date',
            end_date='2026-06-30',
        )

        assert result['status'] == 'error'
        assert 'YYYY-MM-DD' in result['data']['message']
        _assert_validation_error(result)

    @pytest.mark.asyncio
    async def test_account_selector_requires_time_filter(self, mock_context):
        """An account query with no time filter errors before calling the API.

        The service rejects an ACCOUNT_ID selector carrying neither
        BillingPeriod nor TimeInterval, so the call is refused locally.
        """
        with patch(CREATE_CLIENT_PATH) as mock_create:
            result = await list_invoice_summaries(mock_context, account_id='123456789012')

        assert result['status'] == 'error'
        assert 'time filter is required' in result['data']['message']
        assert 'one call per month' in result['data']['message']
        _assert_validation_error(result)
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoice_id_selector_needs_no_time_filter(self, mock_context, sample_summary):
        """An invoice_id query is still valid without any time filter."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(mock_context, invoice_id='INV-001')

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'time_filter',
        [
            {'billing_period': '2026-01'},
            {'start_date': '2026-01-01', 'end_date': '2026-02-01'},
            {'start_date': '2026-01-01'},
            {'end_date': '2026-02-01'},
        ],
    )
    async def test_invoice_id_with_time_filter_is_rejected(self, mock_context, time_filter):
        """invoice_id plus any time filter errors before calling the API.

        The INVOICE_ID selector returns that one invoice whatever its billing
        period or issued date, so forwarding the filter would hand back an
        invoice for a period the caller did not ask for.
        """
        with patch(CREATE_CLIENT_PATH) as mock_create:
            result = await list_invoice_summaries(
                mock_context, invoice_id='INV-001', **time_filter
            )

        assert result['status'] == 'error'
        _assert_validation_error(result)
        message = result['data']['message']
        assert 'invoice_id cannot be combined' in message
        assert 'BillingPeriod' in message
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoice_id_with_invoicing_entity_is_forwarded(
        self, mock_context, sample_summary
    ):
        """invoicing_entity still applies with invoice_id, so it is sent unchanged."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, invoice_id='INV-001', invoicing_entity='Amazon Web Services, Inc.'
            )

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Selector'] == {'ResourceType': 'INVOICE_ID', 'Value': 'INV-001'}
        assert call['Filter'] == {'InvoicingEntity': 'Amazon Web Services, Inc.'}

    @pytest.mark.asyncio
    async def test_range_longer_than_a_month_is_rejected(self, mock_context):
        """An over-long range errors locally and names the sub-ranges to call.

        The suggestions stay expressed as dates, not billing periods: a
        TimeInterval selects on issued date while a BillingPeriod selects on
        billing month, so swapping them would answer a different question.
        """
        with patch(CREATE_CLIENT_PATH) as mock_create:
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-05-14',
                end_date='2026-08-14',
            )

        assert result['status'] == 'error'
        assert 'at most one month' in result['data']['message']
        _assert_validation_error(result)
        assert result['data']['suggested_date_ranges'] == [
            {'start_date': '2026-05-14', 'end_date': '2026-06-01'},
            {'start_date': '2026-06-01', 'end_date': '2026-07-01'},
            {'start_date': '2026-07-01', 'end_date': '2026-08-01'},
            {'start_date': '2026-08-01', 'end_date': '2026-08-14'},
        ]
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_suggested_sub_ranges_are_each_within_the_service_limit(self, mock_context):
        """Every suggested sub-range must itself be accepted if replayed.

        A suggestion the service would reject in turn would send the caller into
        a loop, so each pair is fed back through the same validation.
        """
        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = MagicMock(
                list_invoice_summaries=MagicMock(return_value={'InvoiceSummaries': []})
            )
            rejected = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                # Starts in February, the shortest month, and ends mid-March.
                start_date='2026-02-15',
                end_date='2026-03-20',
            )

            assert rejected['status'] == 'error'
            sub_ranges = rejected['data']['suggested_date_ranges']
            assert sub_ranges == [
                {'start_date': '2026-02-15', 'end_date': '2026-03-01'},
                {'start_date': '2026-03-01', 'end_date': '2026-03-20'},
            ]

            for sub_range in sub_ranges:
                replayed = await list_invoice_summaries(
                    mock_context, account_id='123456789012', **sub_range
                )
                assert replayed['status'] == 'success', sub_range

    @pytest.mark.asyncio
    async def test_span_limit_follows_the_start_months_length(self, mock_context, sample_summary):
        """The cap is the start month's length, not a flat 31 days.

        Verified against the live API: a range starting 2026-02-15 is accepted
        at 28 days (February's length) and rejected at 29, so a flat 31-day cap
        would wave through a request the service refuses.
        """
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            allowed = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-02-15',
                end_date='2026-03-15',
            )
            rejected = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-02-15',
                end_date='2026-03-16',
            )

        assert allowed['status'] == 'success'
        assert rejected['status'] == 'error'
        assert '28 here' in rejected['data']['message']
        _assert_validation_error(rejected)

    @pytest.mark.asyncio
    async def test_long_start_month_allows_a_31_day_span(self, mock_context, sample_summary):
        """A 31-day span starting in a 31-day month is accepted.

        Verified against the live API: 2026-01-31 to 2026-03-03 succeeds. The
        cap tracks the start month's length rather than clamping to the same day
        of the next month, so this must not be rejected.
        """
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-01-31',
                end_date='2026-03-03',
            )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_partial_day_over_the_limit_is_not_rejected(self, mock_context, sample_summary):
        """A span of 28 days plus a few hours from a February start is allowed.

        The service truncates the span to whole days -- 2026-02-15 to
        2026-03-15T23:59:59 succeeds against the live API -- so the local check
        must truncate the same way instead of rounding up into a false rejection.
        """
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-02-15',
                end_date='2026-03-15T23:59:59',
            )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_reversed_range_is_rejected(self, mock_context):
        """An empty or reversed range errors locally.

        The service rejects both with "End date ... cannot be before start
        date", and a negative span would otherwise slip past the span check.
        """
        with patch(CREATE_CLIENT_PATH) as mock_create:
            reversed_range = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-03-01',
                end_date='2026-02-01',
            )
            empty_range = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-03-01',
                end_date='2026-03-01',
            )

        for result in (reversed_range, empty_range):
            assert result['status'] == 'error'
            assert 'later than start_date' in result['data']['message']
            _assert_validation_error(result)
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_mid_month_range_within_a_month_is_allowed(self, mock_context, sample_summary):
        """A 30-day range that crosses a month boundary is still accepted.

        The service caps the span, not the alignment, so a mid-month range must
        not be rejected.
        """
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-05-14',
                end_date='2026-06-13',
            )

        assert result['status'] == 'success'


class TestListInvoiceSummariesResponse:
    """Response normalization, pagination, and error handling."""

    @pytest.mark.asyncio
    async def test_timestamps_normalized_to_iso(self, mock_context, sample_summary):
        """Epoch/datetime timestamp fields are converted to ISO 8601 strings."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2026-05'
            )

        summary = result['data']['invoice_summaries'][0]
        assert summary['IssuedDate'] == '2026-05-01T00:00:00'
        assert summary['DueDate'] == '2026-06-15T00:00:00'

    @pytest.mark.asyncio
    async def test_epoch_int_timestamps_normalized_to_iso(self, mock_context):
        """Epoch INTEGER seconds for IssuedDate/DueDate are normalized to ISO 8601 strings."""
        # 1746144000 == 2025-05-02T00:00:00 UTC
        # 1748822400 == 2025-06-02T00:00:00 UTC
        epoch_summary = {
            'AccountId': '123456789012',
            'InvoiceId': 'INV-EPOCH',
            'InvoiceType': 'INVOICE',
            'IssuedDate': 1746144000,
            'DueDate': 1748822400,
            'BillingPeriod': {'Month': 5, 'Year': 2025},
            'Entity': {'InvoicingEntity': 'Amazon Web Services, Inc.'},
            'BaseCurrencyAmount': {
                'TotalAmount': '500.00',
                'TotalAmountBeforeTax': '450.00',
                'CurrencyCode': 'USD',
            },
        }
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [epoch_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2025-05'
            )

        assert result['status'] == 'success'
        summary = result['data']['invoice_summaries'][0]
        assert summary['IssuedDate'] == '2025-05-02T00:00:00'
        assert summary['DueDate'] == '2025-06-02T00:00:00'

    @staticmethod
    async def _list(mock_client, mock_context, **kwargs):
        """Call list_invoice_summaries for one account and billing period."""
        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            return await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2026-05', **kwargs
            )

    @pytest.mark.asyncio
    async def test_no_max_items_fetches_every_page(self, mock_context, sample_summary):
        """Without max_items every page is fetched at the largest page size."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.side_effect = [
            {'InvoiceSummaries': [sample_summary], 'NextToken': 'page-2'},
            {'InvoiceSummaries': [sample_summary], 'NextToken': 'page-3'},
            {'InvoiceSummaries': [sample_summary]},
        ]

        result = await self._list(mock_client, mock_context)

        assert result['status'] == 'success'
        calls = mock_client.list_invoice_summaries.call_args_list
        assert len(calls) == 3
        assert all(call.kwargs['MaxResults'] == 100 for call in calls)
        assert [call.kwargs.get('NextToken') for call in calls] == [None, 'page-2', 'page-3']
        assert len(result['data']['invoice_summaries']) == 3
        assert result['data']['pagination'] == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 3,
        }
        assert 'warning' not in result['data']

    @pytest.mark.asyncio
    async def test_max_items_stops_before_exceeding(self, mock_context, sample_summary):
        """max_items sizes the page and stops once reached, returning the service token."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {
            'InvoiceSummaries': [sample_summary] * 3,
            'NextToken': 'always-more',
        }

        result = await self._list(mock_client, mock_context, max_items=3)

        assert result['status'] == 'success'
        assert mock_client.list_invoice_summaries.call_count == 1
        assert mock_client.list_invoice_summaries.call_args.kwargs['MaxResults'] == 3
        data = result['data']
        assert list(data)[:2] == ['complete_dataset', 'warning']
        assert data['complete_dataset'] is False
        assert data['pagination']['has_more'] is True
        assert data['pagination']['next_token'] == 'always-more'
        assert data['pagination']['items_returned'] == 3

    @pytest.mark.asyncio
    async def test_continuation_sends_token_and_identical_params(
        self, mock_context, sample_summary
    ):
        """A continuation sends the caller's token and otherwise the same request."""
        first = MagicMock()
        first.list_invoice_summaries.return_value = {
            'InvoiceSummaries': [sample_summary],
            'NextToken': 'page-2',
        }
        await self._list(first, mock_context, max_items=1, invoicing_entity='AWS Inc')
        resumed = MagicMock()
        resumed.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}
        result = await self._list(
            resumed, mock_context, max_items=1, invoicing_entity='AWS Inc', next_token='page-2'
        )

        first_call = first.list_invoice_summaries.call_args.kwargs
        resumed_call = resumed.list_invoice_summaries.call_args.kwargs
        assert resumed_call['NextToken'] == 'page-2'
        assert 'NextToken' not in first_call
        assert {k: v for k, v in resumed_call.items() if k != 'NextToken'} == first_call
        assert result['data']['pagination']['complete_dataset'] is True

    @pytest.mark.asyncio
    async def test_failure_after_first_page_is_partial(self, mock_context, sample_summary):
        """A later page failing keeps the earlier rows and returns the retry token."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.side_effect = [
            {'InvoiceSummaries': [sample_summary], 'NextToken': 'page-2'},
            ClientError({'Error': {'Code': 'ThrottlingException'}}, 'ListInvoiceSummaries'),
        ]

        result = await self._list(mock_client, mock_context)

        assert result['status'] == 'success'
        assert result['data']['complete_dataset'] is False
        assert 'ThrottlingException' in result['data']['warning']
        assert result['data']['pagination']['next_token'] == 'page-2'

    @pytest.mark.asyncio
    async def test_rejected_token_is_invalid_next_token(self, mock_context):
        """A token the service rejects maps to invalid_next_token."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.side_effect = ClientError(
            {'Error': {'Code': 'InvalidNextTokenException', 'Message': 'bad'}},
            'ListInvoiceSummaries',
        )

        result = await self._list(mock_client, mock_context, next_token='stale')

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_context):
        """An empty result set returns success with zero items_returned."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': []}

        result = await self._list(mock_client, mock_context)

        assert result['status'] == 'success'
        assert result['data']['invoice_summaries'] == []
        assert result['data']['pagination']['items_returned'] == 0
        assert result['data']['pagination']['complete_dataset'] is True

    @pytest.mark.asyncio
    async def test_api_client_error(self, mock_context):
        """A ClientError from the API is handled and returns an error status."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'}},
            'ListInvoiceSummaries',
        )

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2026-05'
            )

        assert result['status'] == 'error'
        assert result['error_type'] == 'AccessDeniedException'
        assert result['operation'] == 'ListInvoiceSummaries'
        assert result['service'] == 'Invoicing'


class TestInvoicingServer:
    """FastMCP sub-server registration."""

    def test_server_name(self):
        """The invoicing sub-server is created with the expected name."""
        from awslabs.billing_cost_management_mcp_server.tools.invoicing_tools import (
            invoicing_server,
        )

        assert invoicing_server.name == 'invoicing-tools'


class TestInvoicingRouting:
    """Operation routing for the top-level ``invoicing`` tool."""

    @pytest.mark.asyncio
    async def test_routes_list_invoice_summaries(self, mock_context, sample_summary):
        """operation=list_invoice_summaries dispatches to the handler."""
        from awslabs.billing_cost_management_mcp_server.tools.invoicing_tools import _invoicing

        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await _invoicing(
                mock_context,
                'list_invoice_summaries',
                account_id='123456789012',
                billing_period='2026-05',
            )

        assert result['status'] == 'success'
        assert result['data']['invoice_summaries'][0]['InvoiceId'] == 'INV-001'

    @pytest.mark.asyncio
    async def test_unknown_operation_returns_error(self, mock_context):
        """An unsupported operation returns a standardized error."""
        from awslabs.billing_cost_management_mcp_server.tools.invoicing_tools import _invoicing

        result = await _invoicing(mock_context, 'not_a_real_operation')

        assert result['status'] == 'error'
        assert 'not_a_real_operation' in result['data']['message']


def _served_tool():
    """The ``invoicing`` tool as published to a client, not as written in source."""

    async def _get():
        async with Client(invoicing_server) as client:
            return next(t for t in await client.list_tools() if t.name == 'invoicing')

    return asyncio.run(_get())


def _served_description() -> str:
    """The served description, narrowed to ``str``.

    ``Tool.description`` is typed ``str | None``, so a bare membership test on
    it fails type checking. A served tool with no description is a defect in
    its own right, so assert rather than defaulting to an empty string -- that
    would turn every description assertion below into a silent pass.
    """
    description = _served_tool().description
    assert description is not None, 'the invoicing tool is served with no description'
    return description


def _input_schema(tool):
    """The served input schema, under whichever field name this FastMCP uses.

    MCP SDK v2 renamed ``inputSchema`` to ``input_schema``, and this package is
    built against both.
    """
    schema = getattr(tool, 'input_schema', None)
    return tool.inputSchema if schema is None else schema


def _schema_enum(schema):
    """The enum of a parameter, through the anyOf an Optional type renders as."""
    if 'enum' in schema:
        return set(schema['enum'])
    for branch in schema.get('anyOf', []):
        if 'enum' in branch:
            return set(branch['enum'])
    return set()


def _documented(name, description):
    """Whether a field or enum name appears in its own right, not inside another."""
    return re.search(rf'\b{re.escape(name)}\b', description) is not None


def _invoicing_shape(name):
    """A shape from the live botocore ``invoicing`` model."""
    return botocore.session.get_session().get_service_model('invoicing').shape_for(name)


class TestInvoicingSchemaContract:
    """The served schema matches the API it wraps."""

    def test_receiver_role_enum_matches_the_api(self):
        """The parameter offers exactly the roles the API accepts, and no others."""
        schema = _input_schema(_served_tool())['properties']['receiver_role']

        assert _schema_enum(schema) == set(_invoicing_shape('ReceiverRole').enum)

    @pytest.mark.asyncio
    async def test_receiver_role_invalid_value_rejected_by_schema(self):
        """A role outside the enum fails before the handler runs."""
        async with Client(invoicing_server) as client:
            result = await client.call_tool(
                'invoicing',
                {
                    'operation': 'list_invoice_summaries',
                    'account_id': '123456789012',
                    'billing_period': '2026-09',
                    'receiver_role': 'PAYER',
                },
                raise_on_error=False,
            )

        assert result.is_error


class TestInvoicingDescriptionContract:
    """The description states what the API does, and no more.

    A description is the only account of the API a model gets, so a claim
    missing from it is a claim the model cannot act on, and one that contradicts
    the API is a defect in every answer built on it.
    """

    def test_receiver_role_documented_as_not_a_superset(self):
        """The surprising parts of receiver_role are all stated."""
        description = _served_description()

        assert 'receiver_role' in description
        assert 'LESS THAN five years' in description
        assert 'NOT a superset' in description
        assert 'de-duplicate on InvoiceId' in description
        assert 'ACCOUNT QUERIES ONLY' in description

    def test_a_time_filter_is_documented_as_refused_for_invoice_id(self):
        """The word optional implied the filter narrows the result. It never did.

        Verified live against a real invoice id: a TimeInterval covering 2019,
        and a BillingPeriod of 2019-01, each returned the invoice issued in
        2026 anyway. So a caller who passed a window and got a row back could
        not tell the window was disregarded.

        This PR first documented the filter as ignored. #4894 then landed the
        stronger fix -- the tool refuses the combination outright -- so the
        description states the refusal rather than the indifference, and this
        test pins that wording instead.
        """
        description = _served_description()

        assert 'not allowed with invoice_id' in description
        assert 'Takes NO time filter' in description
        assert 'rejected with a validation_error' in description
        assert 'optional for invoice_id' not in description
        assert 'IGNORED for invoice_id' not in description

    def test_estimates_documented_as_indistinguishable_by_type(self):
        """The prefix is the only marker, and estimates outlive the open month.

        Both claims are live-verified, and both break the rule that only
        InvoiceType INVOICE is money owed: estimates report that type, and a
        closed month returns its issued invoices and its estimates together.
        """
        description = _served_description()

        assert 'THE PREFIX IS THE ONLY MARKER' in description
        assert 'NOT limited to billing periods that are still open' in description
        assert 'NEVER add an estimate to the issued invoices of the same month' in description
        assert 'excluding rows whose InvoiceId starts with "Estimate-"' in description

    def test_invoicing_entity_documented_as_exact(self):
        """A misspelled entity errors; a valid one with no invoices returns empty."""
        description = _served_description()

        assert 'must match EXACTLY' in description
        assert 'Input invoice entity is not supported' in description

    def test_no_local_date_floor_claimed_for_receiver_role(self):
        """No claim that early start dates are refused: the service accepts them."""
        description = _served_description()

        assert '2025-06-01' not in description

    def test_every_invoice_type_and_bill_type_value_is_named(self):
        """A value the API can return and the description omits is a value a reader mishandles."""
        description = _served_description()

        missing = [
            f'{shape}.{value}'
            for shape in ('InvoiceType', 'BillType', 'InvoiceFrequency')
            for value in _invoicing_shape(shape).enum
            if not _documented(value, description)
        ]

        assert missing == [], f'enum values the description does not name: {missing}'

    def test_every_invoice_summary_member_is_named(self):
        """Every field the result can carry is named, nested entity members included."""
        description = _served_description()

        missing = [
            member
            for shape in ('InvoiceSummary', 'Entity')
            for member in _invoicing_shape(shape).members
            if not _documented(member, description)
        ]

        assert missing == [], f'response members the description does not name: {missing}'

    def test_credit_memo_sign_convention_is_stated(self):
        """A positive CREDIT_MEMO summed as owed overstates the amount due."""
        description = _served_description()

        assert 'CREDIT_MEMO' in description
        assert 'POSITIVE' in description
        assert 'OriginalInvoiceId' in description
        assert 'PAYMENT_RECEIPT' in description

    def test_no_aws_error_text_quoted_for_a_local_check(self):
        """The span and time-filter checks run here, so AWS's wording never reaches a caller."""
        description = _served_description()

        assert 'TimePeriod cannot last more than a month' not in description
        assert 'cannot both be null' not in description
        assert 'validation_error' in description
        assert 'suggested_date_ranges' in description

    @pytest.mark.asyncio
    async def test_unlisted_fields_pass_through_unchanged(self, mock_context, sample_summary):
        """A field the description does not name still reaches the caller untouched."""
        row = dict(
            sample_summary,
            BillSourceAccounts=['123456789012'],
            BillSourceAccountsTotalCount=1,
            ReceiverRole='BUYER',
            TaxAuthorityStatus='ISSUED',
            Entity={'InvoicingEntity': 'Amazon Web Services, Inc.', 'BillingEntity': 'AWS'},
        )
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [row]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, MagicMock())
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2026-09'
            )

        returned = result['data']['invoice_summaries'][0]
        assert returned['BillSourceAccounts'] == ['123456789012']
        assert returned['BillSourceAccountsTotalCount'] == 1
        assert returned['ReceiverRole'] == 'BUYER'
        assert returned['TaxAuthorityStatus'] == 'ISSUED'
        assert returned['Entity']['BillingEntity'] == 'AWS'
