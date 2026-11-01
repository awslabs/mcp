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

"""Unit tests for the business_support_operations module (Business Support)."""

import boto3
import pytest
import sqlite3
from awslabs.billing_cost_management_mcp_server.tools.business_support_operations import (
    ACCOUNT_CHARGES_SUMMARY_FIELDS,
    EARLIEST_BILLING_MONTH,
    list_account_charges,
    list_subscription_history,
)
from awslabs.billing_cost_management_mcp_server.utilities import sql_utils
from awslabs.billing_cost_management_mcp_server.utilities.error_contract import add_retry_guidance
from botocore.exceptions import ClientError, EndpointConnectionError
from botocore.stub import Stubber
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


CREATE_CLIENT_PATH = 'awslabs.billing_cost_management_mcp_server.tools.business_support_operations.create_aws_client'
PAGINATE_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.business_support_operations'
    '.paginate_aws_items'
)
CONVERT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.business_support_operations'
    '.convert_response_if_needed'
)

# Both operations share billing-month bounds, so validation tests run against each.
MONTH_VALIDATED_HANDLERS = (
    (list_account_charges, {'billing_month': '2026-06'}),
    (list_subscription_history, {'billing_month': '2026-06'}),
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


def _previous_month() -> str:
    """Return the previous calendar month in ``YYYY-MM``, rolling back the year."""
    now = datetime.now(timezone.utc)
    if now.month == 1:
        return f'{now.year - 1}-12'
    return f'{now.year}-{now.month - 1:02d}'


def _make_client_error(error_code: str, message: str = 'test') -> ClientError:
    """Build a botocore ClientError with the given error code."""
    return ClientError(
        {'Error': {'Code': error_code, 'Message': message}, 'ResponseMetadata': {}},
        'TestOperation',
    )


async def _run_with_paginator(
    mock_context,
    handler,
    paginated_items,
    pagination_info=None,
    pages=None,
    **handler_kwargs,
):
    """Invoke a handler with a mocked paginator returning the given items.

    The paginator and convert_response_if_needed are both mocked so tests
    exercise the handler's logic without reaching AWS or the SQL offloader. The
    fake pagination block uses the same keys the real ``paginate_aws_items``
    emits (``items_returned``, ``has_more``, ``complete_dataset``); tests that
    need the real paginator use ``_run_with_stubbed_pages`` instead.
    """
    if pagination_info is None:
        pagination_info = {
            'complete_dataset': True,
            'items_returned': len(paginated_items),
            'has_more': False,
        }

    async def fake_convert(ctx, response, *args, **kwargs):
        return response

    with (
        patch(CREATE_CLIENT_PATH, return_value=MagicMock()),
        patch(
            PAGINATE_PATH,
            new=AsyncMock(return_value=(paginated_items, pages or [], pagination_info)),
        ),
        patch(CONVERT_PATH, new=AsyncMock(side_effect=fake_convert)),
    ):
        return await handler(mock_context, **handler_kwargs)


async def _run_with_stubbed_pages(mock_context, handler, operation, pages, **handler_kwargs):
    """Run a handler through the REAL paginator against a stubbed billing client.

    Unlike ``_run_with_paginator`` nothing in this module is mocked except the
    client factory, so the request shape, the page walk, the pagination block
    and the profile-wide fields are all produced by production code. botocore's
    Stubber validates every expected request and response against the service
    model.

    Args:
        mock_context: The mock MCP context.
        handler: The operation handler to run.
        operation: The client method name (snake_case) each stubbed page answers.
        pages: ``(expected_params, response)`` pairs, one per request, in order.
        **handler_kwargs: Arguments forwarded to the handler.

    Returns:
        The handler result.
    """
    client = boto3.client('billing', region_name='us-east-1')
    stubber = Stubber(client)
    for expected, response in pages:
        stubber.add_response(operation, response, expected)
    stubber.activate()
    with patch(CREATE_CLIENT_PATH, return_value=client):
        result = await handler(mock_context, **handler_kwargs)
    stubber.assert_no_pending_responses()
    return result


async def _run_with_error(mock_context, handler, error, **handler_kwargs):
    """Invoke a handler where the billing client raises the given error."""
    client = MagicMock()
    # Make any method call on the client raise the error.
    client.list_business_support_account_charges.side_effect = error
    client.list_business_support_subscription_history.side_effect = error

    async def fake_paginate(ctx, op_name, caller, *args, **kwargs):
        # The paginator invokes the caller, which will raise.
        caller()

    with (
        patch(CREATE_CLIENT_PATH, return_value=client),
        patch(PAGINATE_PATH, new=AsyncMock(side_effect=fake_paginate)),
    ):
        return await handler(mock_context, **handler_kwargs)


async def _run_rejected(mock_context, handler, **handler_kwargs):
    """Invoke a handler expecting rejection before any AWS call."""
    create_client = MagicMock()
    with patch(CREATE_CLIENT_PATH, new=create_client):
        result = await handler(mock_context, **handler_kwargs)
    create_client.assert_not_called()
    return result


# ---------------------------------------------------------------------------
# Billing-month validation (shared by both operations)
# ---------------------------------------------------------------------------


class TestBillingMonthValidation:
    """Only billing months with published data reach the API."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'billing_month',
        [
            '',
            '202606',
            '2026-6',
            '2026-1',
            '2025-9',
            '2025-2',
            '26-6',
            '26-06',
            '226-06',
            '2026-006',
            '2026-00',
            '2026-13',
            'June 2026',
            '2026-06-01',
            ' 2026-06',
            '2026-06 ',
        ],
    )
    async def test_malformed_month_is_rejected(self, mock_context, billing_month):
        """A month not in YYYY-MM format fails without calling AWS."""
        result = await _run_rejected(
            mock_context, list_account_charges, billing_month=billing_month
        )

        assert result['status'] == 'error'
        message = result['data']['message']
        assert 'YYYY-MM' in message

    @pytest.mark.asyncio
    async def test_missing_month_is_rejected_for_account_charges(self, mock_context):
        """billing_month is required for list_account_charges."""
        result = await _run_rejected(mock_context, list_account_charges, billing_month=None)

        assert result['status'] == 'error'
        assert 'YYYY-MM' in result['data']['message']

    @pytest.mark.asyncio
    async def test_missing_month_is_accepted_for_subscription_history(self, mock_context):
        """billing_month is optional for list_subscription_history."""
        result = await _run_with_paginator(
            mock_context, list_subscription_history, [], billing_month=None
        )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    @pytest.mark.parametrize('handler,kwargs', MONTH_VALIDATED_HANDLERS)
    async def test_month_before_floor_is_rejected(self, mock_context, handler, kwargs):
        """A month earlier than the data floor fails for every operation."""
        result = await _run_rejected(mock_context, handler, billing_month='2023-12')

        assert result['status'] == 'error'
        assert EARLIEST_BILLING_MONTH in result['data']['message']

    @pytest.mark.asyncio
    @pytest.mark.parametrize('handler,kwargs', MONTH_VALIDATED_HANDLERS)
    async def test_current_month_is_accepted(self, mock_context, handler, kwargs):
        """The current month reaches the API and is accepted.

        Business Support returns it as an estimate (isEstimated=true) that
        refreshes daily, unlike Enterprise Support which rejects the still-open
        current period. Only a future month is rejected.
        """
        current_month = datetime.now(timezone.utc).strftime('%Y-%m')
        result = await _run_with_paginator(mock_context, handler, [], billing_month=current_month)

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_future_month_is_rejected(self, mock_context):
        """A future month fails without calling AWS."""
        now = datetime.now(timezone.utc)
        future_month = f'{now.year + 1}-{now.month:02d}'

        result = await _run_rejected(
            mock_context, list_account_charges, billing_month=future_month
        )

        assert result['status'] == 'error'
        assert future_month in result['data']['message']

    @pytest.mark.asyncio
    async def test_earliest_billing_month_is_accepted(self, mock_context):
        """The floor month itself reaches the API rather than being rejected."""
        result = await _run_with_paginator(
            mock_context, list_account_charges, [], billing_month=EARLIEST_BILLING_MONTH
        )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_previous_month_is_accepted(self, mock_context):
        """The previous calendar month reaches the API as the newest available month."""
        previous = _previous_month()
        result = await _run_with_paginator(
            mock_context, list_account_charges, [], billing_month=previous
        )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_malformed_optional_month_is_rejected_for_subscription_history(
        self, mock_context
    ):
        """An invalid optional billing_month is still rejected for subscription_history."""
        result = await _run_rejected(
            mock_context, list_subscription_history, billing_month='2026-6'
        )

        assert result['status'] == 'error'
        assert 'YYYY-MM' in result['data']['message']


class TestLatestAvailableMonthYearBoundary:
    """Current-month acceptance and future rejection hold across a year boundary."""

    @pytest.mark.asyncio
    async def test_january_current_month_is_accepted(self, mock_context):
        """In January the current month (that January) is still answerable.

        Business Support refreshes daily and serves the open current month as an
        estimate, so there is no roll-back to the prior December the way
        Enterprise Support has. The year boundary must not change that.
        """
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.business_support_operations.datetime'
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2027, 1, 15, tzinfo=timezone.utc)
            mock_datetime.strptime = datetime.strptime
            result = await _run_with_paginator(
                mock_context, list_account_charges, [], billing_month='2027-01'
            )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_next_month_is_rejected_across_year_boundary(self, mock_context):
        """A future month is rejected across the year boundary.

        In December, the following January is a future month and is rejected, and
        the error names the current month (that December) as the newest
        answerable period.
        """
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.business_support_operations.datetime'
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 12, 15, tzinfo=timezone.utc)
            mock_datetime.strptime = datetime.strptime
            result = await _run_rejected(
                mock_context, list_account_charges, billing_month='2027-01'
            )

        assert result['status'] == 'error'
        assert '2026-12' in result['data']['message']


# ---------------------------------------------------------------------------
# Account-id validation
# ---------------------------------------------------------------------------


class TestAccountIdValidation:
    """The optional account_id filter is validated locally."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'account_id',
        [
            '12345',  # too short
            '1234567890123',  # too long
            '12345678901a',  # non-digit  # pragma: allowlist secret
            'abcdefghijkl',  # all alpha  # pragma: allowlist secret
            '123-456-789012',  # dashes
        ],
    )
    async def test_malformed_account_id_is_rejected(self, mock_context, account_id):
        """An account_id that is not 12 digits fails without calling AWS."""
        previous = _previous_month()
        result = await _run_rejected(
            mock_context, list_account_charges, billing_month=previous, account_id=account_id
        )

        assert result['status'] == 'error'
        assert '12-digit' in result['data']['message']

    @pytest.mark.asyncio
    async def test_valid_account_id_is_accepted(self, mock_context):
        """A well-formed 12-digit account_id passes validation."""
        result = await _run_with_paginator(
            mock_context,
            list_account_charges,
            [],
            billing_month=_previous_month(),
            account_id='111122223333',
        )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_absent_account_id_is_accepted(self, mock_context):
        """Omitting account_id sends no filter."""
        result = await _run_with_paginator(
            mock_context,
            list_account_charges,
            [],
            billing_month=_previous_month(),
            account_id=None,
        )

        assert result['status'] == 'success'


# ---------------------------------------------------------------------------
# list_account_charges — success path
# ---------------------------------------------------------------------------


class TestListAccountChargesSuccess:
    """Successful account charges are normalized and shaped correctly."""

    @pytest.fixture
    def sample_charges(self):
        """Return account charges as the paginator would collect them (model shape)."""
        return [
            {
                'accountId': '111122223333',
                'supportPlanName': 'AWSSupportBusiness',
                'totalCharge': '500.00',
                'totalUsageBasis': '10000.00',
                'tierCharges': [
                    {
                        'tierDescription': 'First $10K',
                        'tierRate': '0.10',
                        'usageSlice': '10000.00',
                        'tierCharge': '500.00',
                        'chargePeriodStartDate': datetime(2026, 1, 1, tzinfo=timezone.utc),
                    }
                ],
                'supportEligibleSpendByService': [
                    {
                        'contributingService': 'AmazonEC2',
                        'itemType': 'Usage',
                        'chargeAmount': '8000.00',
                        'currency': 'USD',
                    },
                    {
                        'contributingService': 'AmazonS3',
                        'itemType': 'Usage',
                        'chargeAmount': '2000.00',
                        'currency': 'USD',
                    },
                ],
            }
        ]

    @pytest.mark.asyncio
    async def test_returns_normalized_charges(self, mock_context, sample_charges):
        """Timestamps become ISO strings and monetary strings pass through."""
        result = await _run_with_paginator(
            mock_context,
            list_account_charges,
            sample_charges,
            billing_month=_previous_month(),
        )

        assert result['status'] == 'success'
        charges = result['data']['account_charges']
        assert len(charges) == 1
        assert charges[0]['totalCharge'] == '500.00'
        assert charges[0]['totalUsageBasis'] == '10000.00'
        assert charges[0]['supportPlanName'] == 'AWSSupportBusiness'
        # Datetime normalized to ISO string
        assert charges[0]['tierCharges'][0]['chargePeriodStartDate'] == '2026-01-01T00:00:00'
        spend = charges[0]['supportEligibleSpendByService'][0]
        assert spend['contributingService'] == 'AmazonEC2'
        assert spend['currency'] == 'USD'

    @pytest.mark.asyncio
    async def test_profile_wide_fields_reach_the_caller(self, mock_context, sample_charges):
        """The first page's profile-wide fields are merged into the data verbatim."""
        first_page = {
            'billingMonth': '2026-06',
            'isEstimated': True,
            'totalSupportCharge': '1234.56',
            'totalSupportEligibleSpend': '98765.43',
            'accountCount': 3,
            'accountCharges': sample_charges,
            'nextToken': 'P2',
        }
        result = await _run_with_paginator(
            mock_context,
            list_account_charges,
            sample_charges,
            pages=[first_page, {'accountCharges': [], 'isEstimated': False}],
            billing_month=_previous_month(),
        )

        assert result['status'] == 'success'
        data = result['data']
        for field in ACCOUNT_CHARGES_SUMMARY_FIELDS:
            assert data[field] == first_page[field]
        # Read from the first page only, and the raw token never leaks into data.
        assert data['isEstimated'] is True
        assert 'nextToken' not in data
        assert 'accountCharges' not in data

    @pytest.mark.asyncio
    async def test_pagination_block_is_present(self, mock_context, sample_charges):
        """The pagination metadata accompanies the charges."""
        result = await _run_with_paginator(
            mock_context,
            list_account_charges,
            sample_charges,
            billing_month=_previous_month(),
        )

        assert result['status'] == 'success'
        assert 'pagination' in result['data']
        assert result['data']['pagination']['complete_dataset'] is True
        assert result['data']['pagination']['items_returned'] == 1

    @pytest.mark.asyncio
    async def test_empty_result_is_a_real_answer(self, mock_context):
        """No account charges returns an empty list, not an error."""
        result = await _run_with_paginator(
            mock_context,
            list_account_charges,
            [],
            billing_month=_previous_month(),
        )

        assert result['status'] == 'success'
        assert result['data']['account_charges'] == []
        assert result['data']['pagination']['items_returned'] == 0


# ---------------------------------------------------------------------------
# list_account_charges — parameter forwarding
# ---------------------------------------------------------------------------


class TestListAccountChargesParameterForwarding:
    """Parameters reach the paginator call correctly."""

    @pytest.mark.asyncio
    async def test_account_id_reaches_request_params(self, mock_context):
        """An explicit account_id filter appears in the request."""
        previous = _previous_month()

        async def fake_convert(ctx, response, *args, **kwargs):
            return response

        with (
            patch(CREATE_CLIENT_PATH, return_value=MagicMock()) as _client,
            patch(
                PAGINATE_PATH,
                new=AsyncMock(
                    return_value=(
                        [],
                        [],
                        {
                            'complete_dataset': True,
                            'items_returned': 0,
                            'has_more': False,
                        },
                    )
                ),
            ) as mock_paginate,
            patch(CONVERT_PATH, new=AsyncMock(side_effect=fake_convert)),
        ):
            await list_account_charges(
                mock_context, billing_month=previous, account_id='111122223333'
            )

        call_args = mock_paginate.await_args
        assert call_args is not None
        request_params = (
            call_args.args[3]
            if len(call_args.args) > 3
            else call_args.kwargs.get('request_params', {})
        )
        assert request_params['accountId'] == '111122223333'

    @pytest.mark.asyncio
    async def test_account_id_omitted_when_not_given(self, mock_context):
        """No account filter is sent when the caller did not ask for one."""
        previous = _previous_month()

        async def fake_convert(ctx, response, *args, **kwargs):
            return response

        with (
            patch(CREATE_CLIENT_PATH, return_value=MagicMock()),
            patch(
                PAGINATE_PATH,
                new=AsyncMock(
                    return_value=(
                        [],
                        [],
                        {
                            'complete_dataset': True,
                            'items_returned': 0,
                            'has_more': False,
                        },
                    )
                ),
            ) as mock_paginate,
            patch(CONVERT_PATH, new=AsyncMock(side_effect=fake_convert)),
        ):
            await list_account_charges(mock_context, billing_month=previous)

        call_args = mock_paginate.await_args
        assert call_args is not None
        request_params = (
            call_args.args[3]
            if len(call_args.args) > 3
            else call_args.kwargs.get('request_params', {})
        )
        assert 'accountId' not in request_params

    @pytest.mark.asyncio
    async def test_max_items_forwarded_to_paginator(self, mock_context):
        """An explicit max_items is forwarded to the paginator, not the request params."""
        previous = _previous_month()

        async def fake_convert(ctx, response, *args, **kwargs):
            return response

        with (
            patch(CREATE_CLIENT_PATH, return_value=MagicMock()),
            patch(
                PAGINATE_PATH,
                new=AsyncMock(
                    return_value=(
                        [],
                        [],
                        {
                            'complete_dataset': True,
                            'items_returned': 0,
                            'has_more': False,
                        },
                    )
                ),
            ) as mock_paginate,
            patch(CONVERT_PATH, new=AsyncMock(side_effect=fake_convert)),
        ):
            await list_account_charges(mock_context, billing_month=previous, max_items=50)

        call_args = mock_paginate.await_args
        assert call_args is not None
        # max_items is a paginator kwarg; it must not be baked into the request params.
        assert call_args.kwargs['max_items'] == 50
        request_params = (
            call_args.args[3]
            if len(call_args.args) > 3
            else call_args.kwargs.get('request_params', {})
        )
        assert 'maxResults' not in request_params

    @pytest.mark.asyncio
    async def test_next_token_reaches_request_params(self, mock_context):
        """A caller-supplied token resumes the walk."""
        previous = _previous_month()

        async def fake_convert(ctx, response, *args, **kwargs):
            return response

        with (
            patch(CREATE_CLIENT_PATH, return_value=MagicMock()),
            patch(
                PAGINATE_PATH,
                new=AsyncMock(
                    return_value=(
                        [],
                        [],
                        {
                            'complete_dataset': True,
                            'items_returned': 0,
                            'has_more': False,
                        },
                    )
                ),
            ) as mock_paginate,
            patch(CONVERT_PATH, new=AsyncMock(side_effect=fake_convert)),
        ):
            await list_account_charges(
                mock_context, billing_month=previous, next_token='resume-here'
            )

        call_args = mock_paginate.await_args
        assert call_args is not None
        # next_token resumes the walk via the paginator kwarg, not the request params.
        assert call_args.kwargs['next_token'] == 'resume-here'
        request_params = (
            call_args.args[3]
            if len(call_args.args) > 3
            else call_args.kwargs.get('request_params', {})
        )
        assert 'nextToken' not in request_params


# ---------------------------------------------------------------------------
# list_subscription_history — success path
# ---------------------------------------------------------------------------


class TestListSubscriptionHistorySuccess:
    """Successful subscription history is normalized and shaped correctly."""

    @pytest.fixture
    def sample_contracts(self):
        """Return subscription contracts as the paginator would collect them."""
        return [
            {
                'accountId': '111122223333',
                'planName': 'AWSSupportBusiness',
                'contractStartDate': datetime(2025, 6, 1, tzinfo=timezone.utc),
                'contractEndDate': datetime(2026, 6, 1, tzinfo=timezone.utc),
            }
        ]

    @pytest.mark.asyncio
    async def test_returns_normalized_contracts(self, mock_context, sample_contracts):
        """Timestamps become ISO strings and fields pass through."""
        result = await _run_with_paginator(
            mock_context,
            list_subscription_history,
            sample_contracts,
        )

        assert result['status'] == 'success'
        contracts = result['data']['subscription_contracts']
        assert len(contracts) == 1
        assert contracts[0]['planName'] == 'AWSSupportBusiness'
        assert contracts[0]['contractStartDate'] == '2025-06-01T00:00:00'
        assert contracts[0]['contractEndDate'] == '2026-06-01T00:00:00'

    @pytest.mark.asyncio
    async def test_pagination_block_is_present(self, mock_context, sample_contracts):
        """The pagination metadata accompanies the contracts."""
        result = await _run_with_paginator(
            mock_context,
            list_subscription_history,
            sample_contracts,
        )

        assert result['status'] == 'success'
        assert 'pagination' in result['data']
        assert result['data']['pagination']['items_returned'] == 1

    @pytest.mark.asyncio
    async def test_empty_result_is_a_real_answer(self, mock_context):
        """No contracts returns an empty list, not an error."""
        result = await _run_with_paginator(mock_context, list_subscription_history, [])

        assert result['status'] == 'success'
        assert result['data']['subscription_contracts'] == []

    @pytest.mark.asyncio
    async def test_all_filters_omitted_is_accepted(self, mock_context):
        """With no filters the call is accepted (the API then defaults to the current month)."""
        result = await _run_with_paginator(
            mock_context,
            list_subscription_history,
            [],
            billing_month=None,
            account_id=None,
            start_date=None,
            end_date=None,
        )

        assert result['status'] == 'success'


# ---------------------------------------------------------------------------
# list_subscription_history — parameter forwarding
# ---------------------------------------------------------------------------


class TestListSubscriptionHistoryParameterForwarding:
    """Parameters reach the paginator call correctly."""

    @pytest.mark.asyncio
    async def test_all_optional_params_forwarded(self, mock_context):
        """billing_month, account_id, start_date, end_date all reach the request."""
        previous = _previous_month()

        async def fake_convert(ctx, response, *args, **kwargs):
            return response

        with (
            patch(CREATE_CLIENT_PATH, return_value=MagicMock()),
            patch(
                PAGINATE_PATH,
                new=AsyncMock(
                    return_value=(
                        [],
                        [],
                        {
                            'complete_dataset': True,
                            'items_returned': 0,
                            'has_more': False,
                        },
                    )
                ),
            ) as mock_paginate,
            patch(CONVERT_PATH, new=AsyncMock(side_effect=fake_convert)),
        ):
            await list_subscription_history(
                mock_context,
                billing_month=previous,
                account_id='111122223333',
                start_date='2025-01-01T00:00:00Z',
                end_date='2026-06-01T00:00:00Z',
                max_items=25,
                next_token='page2',
            )

        call_args = mock_paginate.await_args
        assert call_args is not None
        request_params = (
            call_args.args[3]
            if len(call_args.args) > 3
            else call_args.kwargs.get('request_params', {})
        )
        assert request_params['billingMonth'] == previous
        assert request_params['accountId'] == '111122223333'
        assert request_params['startDate'] == '2025-01-01T00:00:00Z'
        assert request_params['endDate'] == '2026-06-01T00:00:00Z'
        # Paging controls go to the paginator, not into the request params.
        assert 'maxResults' not in request_params
        assert 'nextToken' not in request_params
        assert call_args.kwargs['max_items'] == 25
        assert call_args.kwargs['next_token'] == 'page2'

    @pytest.mark.asyncio
    async def test_omitted_params_not_in_request(self, mock_context):
        """Omitted optional parameters do not appear in the request."""

        async def fake_convert(ctx, response, *args, **kwargs):
            return response

        with (
            patch(CREATE_CLIENT_PATH, return_value=MagicMock()),
            patch(
                PAGINATE_PATH,
                new=AsyncMock(
                    return_value=(
                        [],
                        [],
                        {
                            'complete_dataset': True,
                            'items_returned': 0,
                            'has_more': False,
                        },
                    )
                ),
            ) as mock_paginate,
            patch(CONVERT_PATH, new=AsyncMock(side_effect=fake_convert)),
        ):
            await list_subscription_history(mock_context)

        call_args = mock_paginate.await_args
        assert call_args is not None
        request_params = (
            call_args.args[3]
            if len(call_args.args) > 3
            else call_args.kwargs.get('request_params', {})
        )
        assert request_params == {}


# ---------------------------------------------------------------------------
# Real paginator against a stubbed client
# ---------------------------------------------------------------------------

CHARGE_ROW = {
    'accountId': '111122223333',
    'supportPlanName': 'AWSSupportBusiness',
    'totalCharge': '500.00',
    'totalUsageBasis': '10000.00',
}

CHARGES_SUMMARY = {
    'billingMonth': '2026-06',
    'isEstimated': True,
    'totalSupportCharge': '1000.00',
    'totalSupportEligibleSpend': '20000.00',
    'accountCount': 2,
}


class TestRealPaginator:
    """Production paging code runs end to end; only the HTTP layer is stubbed."""

    @pytest.mark.asyncio
    async def test_account_charges_two_pages(self, mock_context):
        """Both pages are walked, rows are combined and the totals come from page one."""
        result = await _run_with_stubbed_pages(
            mock_context,
            list_account_charges,
            'list_business_support_account_charges',
            [
                (
                    {'billingMonth': '2026-06', 'maxResults': 100},
                    {**CHARGES_SUMMARY, 'accountCharges': [CHARGE_ROW], 'nextToken': 'P2'},
                ),
                (
                    {'billingMonth': '2026-06', 'maxResults': 100, 'nextToken': 'P2'},
                    {
                        **CHARGES_SUMMARY,
                        'accountCharges': [{**CHARGE_ROW, 'accountId': '444455556666'}],
                    },
                ),
            ],
            billing_month='2026-06',
        )

        assert result['status'] == 'success'
        data = result['data']
        assert [row['accountId'] for row in data['account_charges']] == [
            '111122223333',
            '444455556666',
        ]
        assert data['isEstimated'] is True
        assert data['totalSupportCharge'] == '1000.00'
        assert data['totalSupportEligibleSpend'] == '20000.00'
        assert data['accountCount'] == 2
        assert data['billingMonth'] == '2026-06'
        assert data['pagination']['items_returned'] == 2
        assert data['pagination']['has_more'] is False
        assert data['pagination']['complete_dataset'] is True
        assert 'total_results' not in data['pagination']

    @pytest.mark.asyncio
    async def test_account_charges_max_items_stops_early(self, mock_context):
        """max_items sizes the page and a remaining token is reported, not followed."""
        result = await _run_with_stubbed_pages(
            mock_context,
            list_account_charges,
            'list_business_support_account_charges',
            [
                (
                    {'billingMonth': '2026-06', 'maxResults': 1},
                    {**CHARGES_SUMMARY, 'accountCharges': [CHARGE_ROW], 'nextToken': 'P2'},
                ),
            ],
            billing_month='2026-06',
            max_items=1,
        )

        assert result['status'] == 'success'
        pagination = result['data']['pagination']
        assert pagination['items_returned'] == 1
        assert pagination['has_more'] is True
        assert pagination['complete_dataset'] is False
        # The profile totals still describe the whole query.
        assert result['data']['totalSupportCharge'] == '1000.00'

    @pytest.mark.asyncio
    async def test_subscription_history_with_window(self, mock_context):
        """The date window is sent as given and contract dates are normalized."""
        result = await _run_with_stubbed_pages(
            mock_context,
            list_subscription_history,
            'list_business_support_subscription_history',
            [
                (
                    {
                        'startDate': '2025-01-01',
                        'endDate': '2026-06-30',
                        'maxResults': 100,
                    },
                    {
                        'subscriptionContracts': [
                            {
                                'accountId': '111122223333',
                                'planName': 'AWSSupportBusiness',
                                'contractStartDate': datetime(2025, 6, 1, tzinfo=timezone.utc),
                                'contractEndDate': datetime(2026, 6, 1, tzinfo=timezone.utc),
                            }
                        ]
                    },
                ),
            ],
            start_date='2025-01-01',
            end_date='2026-06-30',
        )

        assert result['status'] == 'success'
        contracts = result['data']['subscription_contracts']
        assert contracts[0]['planName'] == 'AWSSupportBusiness'
        assert contracts[0]['contractStartDate'].startswith('2025-06-01T00:00:00')
        assert result['data']['pagination']['items_returned'] == 1


# The service rejects a bad caller token with ValidationException (HTTP 400) for
# both operations: "Invalid nextToken" for a well-formed token, a constraint
# message naming nextToken for a malformed one. The PageSpecs must name the code.
INVALID_TOKEN_CASES = (
    (list_account_charges, 'list_business_support_account_charges', {'billing_month': '2026-06'}),
    (list_subscription_history, 'list_business_support_subscription_history', {}),
)


async def _run_with_stubbed_error(mock_context, handler, operation, message, **handler_kwargs):
    """Run a handler through the real paginator against a client that raises ValidationException."""
    client = boto3.client('billing', region_name='us-east-1')
    stubber = Stubber(client)
    stubber.add_client_error(
        operation,
        service_error_code='ValidationException',
        service_message=message,
        http_status_code=400,
    )
    stubber.activate()
    with patch(CREATE_CLIENT_PATH, return_value=client):
        result = await handler(mock_context, **handler_kwargs)
    stubber.assert_no_pending_responses()
    return result


class TestRejectedCallerToken:
    """A rejected caller next_token is reported as invalid_next_token, not a generic error."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize('handler,operation,kwargs', INVALID_TOKEN_CASES)
    @pytest.mark.parametrize(
        'message',
        [
            'Invalid nextToken',
            "1 validation error detected: Value at 'nextToken' failed to satisfy constraint: "
            'Member must satisfy regular expression pattern: [-a-zA-Z0-9+=/_]+',
        ],
    )
    async def test_rejected_caller_token_is_invalid_next_token(
        self, mock_context, handler, operation, kwargs, message
    ):
        """A ValidationException naming the caller's token maps to invalid_next_token."""
        result = await _run_with_stubbed_error(
            mock_context, handler, operation, message, next_token='stale', **kwargs
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'
        # The server's error middleware adds the hint the caller sees.
        assert 'without next_token' in add_retry_guidance(result)['hint']

    @pytest.mark.asyncio
    @pytest.mark.parametrize('handler,operation,kwargs', INVALID_TOKEN_CASES)
    async def test_validation_error_without_caller_token_is_unchanged(
        self, mock_context, handler, operation, kwargs
    ):
        """Without a caller next_token the same code stays the service's validation error."""
        result = await _run_with_stubbed_error(
            mock_context, handler, operation, 'Invalid nextToken', **kwargs
        )

        assert result['status'] == 'error'
        assert result['error_type'] != 'invalid_next_token'


# ---------------------------------------------------------------------------
# Real SQL offload (convert_response_if_needed is NOT mocked)
# ---------------------------------------------------------------------------


def _stored_table(table_name: str):
    """Return the column names and row count of an offloaded session table."""
    with sqlite3.connect(sql_utils.get_session_db_path()) as conn:
        columns = [row[1] for row in conn.execute(f'PRAGMA table_info("{table_name}")')]
        (count,) = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
    return columns, count


class TestSqlOffload:
    """With MCP_FORCE_SQL on, results are stored as real rows and keep their totals."""

    @pytest.fixture(autouse=True)
    def force_sql(self, tmp_path):
        """Force every response through the SQL offloader into a temporary database.

        MCP_FORCE_SQL is read once at import into FORCE_SQL_CONVERSION, so the flag
        itself is patched; the session database is pointed at tmp_path so the test
        can read the stored table back without touching the shared sessions folder.
        """
        with (
            patch.object(sql_utils, 'FORCE_SQL_CONVERSION', True),
            patch.object(sql_utils, '_SESSION_DB_PATH', str(tmp_path / 'session.db')),
        ):
            yield

    @pytest.mark.asyncio
    async def test_account_charges_offload_keeps_summary_and_rows(self, mock_context):
        """The totals stay on the sentinel and each charge is its own row."""
        result = await _run_with_stubbed_pages(
            mock_context,
            list_account_charges,
            'list_business_support_account_charges',
            [
                (
                    {'billingMonth': '2026-06', 'maxResults': 100},
                    {
                        **CHARGES_SUMMARY,
                        'accountCharges': [
                            CHARGE_ROW,
                            {**CHARGE_ROW, 'accountId': '444455556666'},
                        ],
                    },
                ),
            ],
            billing_month='2026-06',
        )

        assert result['status'] == 'success'
        data = result['data']
        assert data['data_stored'] is True
        assert data['isEstimated'] is True
        assert data['totalSupportCharge'] == '1000.00'
        assert data['totalSupportEligibleSpend'] == '20000.00'
        assert data['accountCount'] == 2
        assert data['billingMonth'] == '2026-06'

        columns, count = _stored_table(data['table_name'])
        assert count == 2
        assert 'accountId' in columns
        assert 'totalCharge' in columns
        assert columns != ['key', 'value']

    @pytest.mark.asyncio
    async def test_subscription_history_offload_stores_one_row_per_contract(self, mock_context):
        """Each subscription contract is its own row, not one JSON string."""
        contract = {
            'accountId': '111122223333',
            'planName': 'AWSSupportBusiness',
            'contractStartDate': datetime(2025, 6, 1, tzinfo=timezone.utc),
            'contractEndDate': datetime(2026, 6, 1, tzinfo=timezone.utc),
        }
        result = await _run_with_stubbed_pages(
            mock_context,
            list_subscription_history,
            'list_business_support_subscription_history',
            [
                (
                    {'billingMonth': '2026-06', 'maxResults': 100},
                    {
                        'subscriptionContracts': [
                            contract,
                            {**contract, 'accountId': '444455556666'},
                        ]
                    },
                ),
            ],
            billing_month='2026-06',
        )

        assert result['status'] == 'success'
        data = result['data']
        assert data['data_stored'] is True

        columns, count = _stored_table(data['table_name'])
        assert count == 2
        assert 'planName' in columns
        assert 'contractEndDate' in columns
        assert columns != ['key', 'value']


# ---------------------------------------------------------------------------
# Validation error contract
# ---------------------------------------------------------------------------


class TestValidationErrorContract:
    """Local rejections carry error_type and operation like service errors do."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'handler,kwargs,operation',
        [
            (list_account_charges, {'billing_month': None}, 'ListBusinessSupportAccountCharges'),
            (
                list_account_charges,
                {'billing_month': '2026-6'},
                'ListBusinessSupportAccountCharges',
            ),
            (
                list_account_charges,
                {'billing_month': '2023-12'},
                'ListBusinessSupportAccountCharges',
            ),
            (
                list_account_charges,
                {'billing_month': '2026-06', 'account_id': '12345'},
                'ListBusinessSupportAccountCharges',
            ),
            (
                list_subscription_history,
                {'billing_month': '2026-6'},
                'ListBusinessSupportSubscriptionHistory',
            ),
            (
                list_subscription_history,
                {'start_date': 'yesterday'},
                'ListBusinessSupportSubscriptionHistory',
            ),
        ],
    )
    async def test_rejection_carries_error_type_and_operation(
        self, mock_context, handler, kwargs, operation
    ):
        """Every validation failure names its type and the operation it was for."""
        result = await _run_rejected(mock_context, handler, **kwargs)

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == operation
        assert result['message'] == result['data']['message']

    @pytest.mark.asyncio
    async def test_future_month_rejection_carries_contract(self, mock_context):
        """The future-month rejection uses the same contract."""
        now = datetime.now(timezone.utc)
        result = await _run_rejected(
            mock_context, list_account_charges, billing_month=f'{now.year + 1}-01'
        )

        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'ListBusinessSupportAccountCharges'


# ---------------------------------------------------------------------------
# Subscription history date-window validation
# ---------------------------------------------------------------------------


class TestDateRangeValidation:
    """start_date and end_date are checked locally before any call."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize('field', ['start_date', 'end_date'])
    @pytest.mark.parametrize('value', ['yesterday', '2026/01/01', '2026-13-01', '01-02-2026', ''])
    async def test_malformed_bound_is_rejected(self, mock_context, field, value):
        """A bound that is not ISO-8601 fails without calling AWS and names the field."""
        result = await _run_rejected(mock_context, list_subscription_history, **{field: value})

        assert result['status'] == 'error'
        assert field in result['data']['message']
        assert 'ISO-8601' in result['data']['message']

    @pytest.mark.asyncio
    async def test_reversed_range_is_rejected(self, mock_context):
        """start_date after end_date fails without calling AWS."""
        result = await _run_rejected(
            mock_context,
            list_subscription_history,
            start_date='2026-06-01',
            end_date='2026-01-01',
        )

        assert result['status'] == 'error'
        assert 'after end_date' in result['data']['message']

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'start_date,end_date',
        [
            ('2025-01-01', '2026-06-30'),
            ('2025-01-01T00:00:00Z', '2026-06-30T23:59:59+00:00'),
            ('2025-01-01', '2025-01-01T00:00:00Z'),  # naive vs aware, same instant
            ('2026-06-01', None),
            (None, '2026-06-01'),
        ],
    )
    async def test_valid_window_is_accepted(self, mock_context, start_date, end_date):
        """Dates, timestamps, a trailing Z, equal bounds and a single bound all pass."""
        result = await _run_with_paginator(
            mock_context,
            list_subscription_history,
            [],
            start_date=start_date,
            end_date=end_date,
        )

        assert result['status'] == 'success'


# ---------------------------------------------------------------------------
# Error handling (shared by both operations)
# ---------------------------------------------------------------------------


class TestSharedErrorClassification:
    """Failures that mislead are classified the same way for every operation."""

    @pytest.mark.asyncio
    async def test_access_denied_is_classified_for_account_charges(self, mock_context):
        """AccessDenied is reported as authorization, not absence of charges."""
        error = _make_client_error('AccessDeniedException')
        result = await _run_with_error(
            mock_context, list_account_charges, error, billing_month=_previous_month()
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'access_denied'
        assert result['operation'] == 'ListBusinessSupportAccountCharges'
        assert 'billing:ListBusinessSupportAccountCharges' in result['resolution']
        assert 'payer account' in result['resolution']
        assert 'not an absence of Business Support charges' in result['message']

    @pytest.mark.asyncio
    async def test_access_denied_is_classified_for_subscription_history(self, mock_context):
        """AccessDenied names its own IAM action for subscription_history."""
        error = _make_client_error('AccessDeniedException')
        result = await _run_with_error(
            mock_context, list_subscription_history, error, billing_month=_previous_month()
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'access_denied'
        assert result['operation'] == 'ListBusinessSupportSubscriptionHistory'
        assert 'billing:ListBusinessSupportSubscriptionHistory' in result['resolution']

    @pytest.mark.asyncio
    async def test_access_denied_alt_code_is_classified(self, mock_context):
        """The shorter 'AccessDenied' code is also classified."""
        error = _make_client_error('AccessDenied')
        result = await _run_with_error(
            mock_context, list_account_charges, error, billing_month=_previous_month()
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'access_denied'

    @pytest.mark.asyncio
    async def test_resource_not_found_classified_as_not_found(self, mock_context):
        """ResourceNotFoundException reads as not_found, not a permission failure."""
        error = _make_client_error('ResourceNotFoundException')
        result = await _run_with_error(
            mock_context, list_account_charges, error, billing_month=_previous_month()
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'not_found'
        assert 'not a permission problem' in result['message']
        assert 'do not retry the same period' in result['resolution']
        assert 'aws_message' in result

    @pytest.mark.asyncio
    async def test_resource_not_found_for_subscription_history(self, mock_context):
        """ResourceNotFoundException is classified for subscription_history too."""
        error = _make_client_error('ResourceNotFoundException')
        result = await _run_with_error(
            mock_context, list_subscription_history, error, billing_month=_previous_month()
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'not_found'

    @pytest.mark.asyncio
    async def test_access_denied_is_logged_as_error(self, mock_context):
        """A classified access denial still reaches the context logger."""
        error = _make_client_error('AccessDeniedException')
        await _run_with_error(
            mock_context, list_account_charges, error, billing_month=_previous_month()
        )

        mock_context.error.assert_awaited_once()
        logged = mock_context.error.await_args.args[0]
        assert 'ListBusinessSupportAccountCharges' in logged
        assert 'access_denied' in logged

    @pytest.mark.asyncio
    async def test_not_found_is_logged_as_warning(self, mock_context):
        """A classified not-found is logged at warning level, not error."""
        error = _make_client_error('ResourceNotFoundException')
        await _run_with_error(
            mock_context, list_subscription_history, error, billing_month=_previous_month()
        )

        mock_context.warning.assert_awaited_once()
        mock_context.error.assert_not_awaited()
        logged = mock_context.warning.await_args.args[0]
        assert 'ListBusinessSupportSubscriptionHistory' in logged
        assert 'not_found' in logged

    @pytest.mark.asyncio
    async def test_throttling_falls_through_to_shared_handler(self, mock_context):
        """An unclassified error keeps the AWS error code from the shared handler."""
        error = _make_client_error('ThrottlingException')
        result = await _run_with_error(
            mock_context, list_account_charges, error, billing_month=_previous_month()
        )

        assert result['status'] == 'error'
        assert result.get('error_type') != 'access_denied'
        assert result.get('error_type') != 'not_found'

    @pytest.mark.asyncio
    async def test_connection_error_falls_through(self, mock_context):
        """A transport failure passes through without being classified."""
        error = EndpointConnectionError(endpoint_url='https://billing.us-east-1.amazonaws.com')
        result = await _run_with_error(
            mock_context, list_account_charges, error, billing_month=_previous_month()
        )

        assert result['status'] == 'error'
        assert 'error_type' not in result or result['error_type'] not in (
            'access_denied',
            'not_found',
        )

    @pytest.mark.asyncio
    async def test_client_creation_failure(self, mock_context):
        """A failure to create the billing client returns an error."""
        with patch(CREATE_CLIENT_PATH, side_effect=Exception('No credentials')):
            result = await list_account_charges(mock_context, billing_month=_previous_month())

        assert result['status'] == 'error'

    @pytest.mark.asyncio
    async def test_unknown_operation_error_code(self, mock_context):
        """An unknown ClientError code does not get classified as access_denied or not_found."""
        error = _make_client_error('ValidationException')
        result = await _run_with_error(
            mock_context, list_account_charges, error, billing_month=_previous_month()
        )

        assert result['status'] == 'error'
        assert result.get('error_type') not in ('access_denied', 'not_found')


# ---------------------------------------------------------------------------
# Tool schema (FastMCP registration)
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """The business-support tool is registered correctly on its server."""

    @pytest.mark.asyncio
    async def test_tool_is_registered(self):
        """The business-support tool exists on the server."""
        from awslabs.billing_cost_management_mcp_server.tools.business_support_tools import (
            business_support_server,
        )

        tool = await business_support_server.get_tool('business-support')
        assert tool is not None

    @pytest.mark.asyncio
    async def test_description_documents_operations(self):
        """The description names both operations."""
        from awslabs.billing_cost_management_mcp_server.tools.business_support_tools import (
            business_support_server,
        )

        tool = await business_support_server.get_tool('business-support')
        assert tool is not None
        desc = tool.description or ''
        assert 'list_account_charges' in desc
        assert 'list_subscription_history' in desc

    @pytest.mark.asyncio
    async def test_description_documents_tier_charges(self):
        """The description names tierCharges so the agent knows about incremental tiers."""
        from awslabs.billing_cost_management_mcp_server.tools.business_support_tools import (
            business_support_server,
        )

        tool = await business_support_server.get_tool('business-support')
        assert tool is not None
        assert 'tierCharges' in (tool.description or '')

    @pytest.mark.asyncio
    async def test_description_documents_subscription_history_per_month(self):
        """The UTC default month, not_found for an empty month, and per-month contract rows are stated."""
        from awslabs.billing_cost_management_mcp_server.tools.business_support_tools import (
            business_support_server,
        )

        tool = await business_support_server.get_tool('business-support')
        assert tool is not None
        desc = tool.description or ''
        assert 'the API defaults to the CURRENT month (UTC)' in desc
        assert 'returns a not_found error, not an empty list' in desc
        assert 'the contract period as recorded for that billing month' in desc
        assert 'merge back-to-back rows for the same account and plan' in desc
        assert 'Both are required by the API, so both are always present' not in desc
        assert 'HTTP 500' not in desc


# ---------------------------------------------------------------------------
# Router (_business_support) — operation routing
# ---------------------------------------------------------------------------


class TestBusinessSupportRouter:
    """The router dispatches to the correct handler."""

    @pytest.mark.asyncio
    async def test_list_account_charges_routes_correctly(self, mock_context):
        """operation=list_account_charges calls the charges handler."""
        from awslabs.billing_cost_management_mcp_server.tools.business_support_tools import (
            _business_support,
        )

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.business_support_tools'
            '._list_account_charges',
            new=AsyncMock(return_value={'status': 'success'}),
        ) as mock_handler:
            result = await _business_support(
                mock_context, 'list_account_charges', billing_month='2026-06'
            )

        assert result['status'] == 'success'
        mock_handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_subscription_history_routes_correctly(self, mock_context):
        """operation=list_subscription_history calls the history handler."""
        from awslabs.billing_cost_management_mcp_server.tools.business_support_tools import (
            _business_support,
        )

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.business_support_tools'
            '._list_subscription_history',
            new=AsyncMock(return_value={'status': 'success'}),
        ) as mock_handler:
            result = await _business_support(mock_context, 'list_subscription_history')

        assert result['status'] == 'success'
        mock_handler.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'operation',
        [
            'list_charges',
            'ListBusinessSupportAccountCharges',
            'account_charges',
            '',
            'delete_charges',
        ],
    )
    async def test_unknown_operation_is_rejected(self, mock_context, operation):
        """An unrecognized operation returns an error."""
        from awslabs.billing_cost_management_mcp_server.tools.business_support_tools import (
            _business_support,
        )

        result = await _business_support(mock_context, operation)

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_operation'
        assert 'Unsupported operation' in result['data']['message']

    @pytest.mark.asyncio
    async def test_unknown_operation_lists_supported_operations(self, mock_context):
        """The error names every supported operation."""
        from awslabs.billing_cost_management_mcp_server.tools.business_support_tools import (
            _business_support,
        )

        result = await _business_support(mock_context, 'nope')

        message = result['data']['message']
        assert 'list_account_charges' in message
        assert 'list_subscription_history' in message


# ---------------------------------------------------------------------------
# Wrapper delegation
# ---------------------------------------------------------------------------


class TestWrapperDelegation:
    """The decorated tool delegates to the testable router."""

    @pytest.mark.asyncio
    async def test_wrapper_forwards_all_params(self, mock_context):
        """The FastMCP wrapper passes all parameters through."""
        from awslabs.billing_cost_management_mcp_server.tools.business_support_tools import (
            business_support,
        )

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.business_support_tools'
            '._list_subscription_history',
            new=AsyncMock(return_value={'status': 'success'}),
        ) as mock_handler:
            await business_support(
                mock_context,
                'list_subscription_history',
                billing_month='2026-06',
                account_id='111122223333',
                start_date='2025-01-01',
                end_date='2026-06-01',
                max_items=25,
                next_token='token',
            )

        assert mock_handler.await_args is not None
        kwargs = mock_handler.await_args.kwargs
        assert kwargs['billing_month'] == '2026-06'
        assert kwargs['account_id'] == '111122223333'
        assert kwargs['start_date'] == '2025-01-01'
        assert kwargs['end_date'] == '2026-06-01'
        assert kwargs['max_items'] == 25
        assert kwargs['next_token'] == 'token'
