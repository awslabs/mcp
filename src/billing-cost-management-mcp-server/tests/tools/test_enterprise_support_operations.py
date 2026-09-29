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

"""Unit tests for the enterprise_support_operations module."""

import boto3
import pytest
from awslabs.billing_cost_management_mcp_server.tools.enterprise_support_operations import (
    EARLIEST_BILLING_MONTH,
    get_charge_summary,
    get_contract_details,
    list_linked_account_charges,
)
from botocore.exceptions import EndpointConnectionError
from botocore.stub import Stubber
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


CREATE_CLIENT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.enterprise_support_operations'
    '.create_aws_client'
)
CHARGE_SUMMARY_OP = 'get_enterprise_support_charge_summary'
CONTRACT_DETAILS_OP = 'get_enterprise_support_contract_details'
LINKED_CHARGES_OP = 'list_enterprise_support_linked_account_charges'

# Every operation shares the same billing-month bounds, so the validation tests
# run against each handler rather than trusting one to stand in for the others.
MONTH_VALIDATED_HANDLERS = (
    (get_charge_summary, CHARGE_SUMMARY_OP),
    (get_contract_details, CONTRACT_DETAILS_OP),
    (list_linked_account_charges, LINKED_CHARGES_OP),
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
def sample_charge_summary():
    """Return a charge summary as the AWS API returns it, timestamps included."""
    return {
        'payerAccountId': '123456789012',
        'billingMonth': '2026-06',
        'billingPeriodStartDate': datetime(2026, 6, 1, tzinfo=timezone.utc),
        'billingPeriodEndDate': datetime(2026, 7, 1, tzinfo=timezone.utc),
        'billDate': datetime(2026, 7, 3, tzinfo=timezone.utc),
        'isEstimated': False,
        'supportCharge': '15000.00',
        'totalSupportCharge': '18000.00',
        'supportDiscount': '0.00',
        'totalSupportEligibleSpend': '220000.00',
        'totalSupportEligibleUsageSpend': '180000.00',
        'totalSupportEligibleReservedInstanceSpend': '25000.00',
        'totalSupportEligibleSavingsPlanSpend': '15000.00',
        'supportChargePercentage': '6.82',
        'supportEffectivePricingPlan': {
            'pricingPlanId': 'plan-1',
            'name': 'Enterprise Support',
            'startDate': datetime(2024, 1, 1, tzinfo=timezone.utc),
            'planDiscountPercent': '5.0',
            'minimumCharge': '15000.00',
            'tiered': 'true',
            'tiers': [
                {
                    'tierMinimum': '0',
                    'baseCharge': '15000.00',
                    'additionalPercentageOfAggregateCharges': '7',
                    'aggregateChargesAdjustment': '0',
                    'incremental': True,
                }
            ],
        },
    }


@pytest.fixture
def sample_contract_details():
    """Return contract details as the AWS API returns them, timestamps included."""
    return {
        'isContractActive': True,
        'supportAllocationMethod': 'Proportional',
        'supportReservedInstanceTreatmentMethod': 'AmortizedCustom',
        'supportReservedInstanceAmortizationStartDate': datetime(2024, 1, 1, tzinfo=timezone.utc),
        'supportSavingsPlansTreatmentMethod': 'None',
        'supportProrateStartDate': datetime(2026, 6, 15, tzinfo=timezone.utc),
        'contractPayerAccountIds': [
            {'accountId': '123456789012', 'isGdn': False},
            {'accountId': '210987654321', 'isGdn': True},
        ],
        'chargedPayerAccountIds': [{'accountId': '123456789012', 'chargePercentage': '100.0'}],
        'additionalSupportCharge': [
            {'description': 'Dedicated TAM', 'amount': '5000.00', 'chargeType': 'RECURRING'}
        ],
        'pricingPlans': [
            {
                'pricingPlanId': 'plan-1',
                'name': 'Enterprise Support',
                'startDate': datetime(2024, 1, 1, tzinfo=timezone.utc),
                'minimumCharge': '15000.00',
                'tiers': [
                    {
                        'tierMinimum': '0',
                        'baseCharge': '15000.00',
                        'additionalPercentageOfAggregateCharges': '7',
                        'aggregateChargesAdjustment': '0',
                        'incremental': True,
                    }
                ],
            }
        ],
    }


async def _run_operation(
    mock_context,
    handler,
    api_method,
    billing_month,
    response=None,
    error_code=None,
    expected_params=None,
    **handler_kwargs,
):
    """Invoke get_charge_summary for one billing month against a stubbed client.

    Every case that reaches AWS shares this shape, so it lives here rather than
    in each test. A real boto3 client is stubbed so botocore validates both the
    request parameters and the stubbed response against the shipped service
    model, which means sending a parameter the API does not accept fails the test
    instead of passing silently. Success cases assert the request carried only
    the billing month and that the stubbed call was actually consumed.

    Args:
        mock_context: The mock MCP context.
        handler: The operation handler to invoke.
        api_method: The boto3 method the handler is expected to call.
        billing_month: The billing month to request.
        response: The API response to return on success.
        error_code: When set, stub a client error with this code instead.
        expected_params: Overrides the request the call must send. Defaults to
            the billing month alone.
        **handler_kwargs: Extra arguments forwarded to the handler.

    Returns:
        The operation result.
    """
    client = boto3.client('billing', region_name='us-east-1')
    stubber = Stubber(client)
    if error_code:
        stubber.add_client_error(api_method, service_error_code=error_code, http_status_code=400)
    else:
        stubber.add_response(
            api_method, response or {}, expected_params or {'billingMonth': billing_month}
        )
    stubber.activate()

    with patch(CREATE_CLIENT_PATH, return_value=client):
        result = await handler(mock_context, billing_month=billing_month, **handler_kwargs)

    if not error_code:
        stubber.assert_no_pending_responses()
    return result


async def _run_rejected(mock_context, handler, billing_month):
    """Invoke get_charge_summary expecting rejection before any AWS call.

    Asserts no client was created, which is the property every validation test
    cares about, so the tests themselves only assert on the error content.

    Args:
        mock_context: The mock MCP context.
        handler: The operation handler to invoke.
        billing_month: The billing month to request.

    Returns:
        The operation result.
    """
    create_client = MagicMock()
    with patch(CREATE_CLIENT_PATH, new=create_client):
        result = await handler(mock_context, billing_month=billing_month)

    create_client.assert_not_called()
    return result


def _previous_month() -> str:
    """Return the previous calendar month in ``YYYY-MM``, rolling back the year.

    Derived here rather than imported so the boundary is checked against an
    independent calculation.

    Returns:
        The previous calendar month.
    """
    now = datetime.now(timezone.utc)
    if now.month == 1:
        return f'{now.year - 1}-12'
    return f'{now.year}-{now.month - 1:02d}'


class TestGetChargeSummarySuccess:
    """A successful charge summary is normalized without losing fidelity."""

    @pytest.mark.asyncio
    async def test_returns_normalized_charge_summary(self, mock_context, sample_charge_summary):
        """Timestamps become ISO strings and monetary strings pass through."""
        result = await _run_operation(
            mock_context,
            get_charge_summary,
            CHARGE_SUMMARY_OP,
            '2026-06',
            response=sample_charge_summary,
        )

        assert result['status'] == 'success'
        summary = result['data']['charge_summary']
        assert summary['billingPeriodStartDate'] == '2026-06-01T00:00:00'
        assert summary['billDate'] == '2026-07-03T00:00:00'
        assert summary['supportEffectivePricingPlan']['startDate'] == '2024-01-01T00:00:00'
        assert summary['supportCharge'] == '15000.00'
        assert summary['totalSupportEligibleSpend'] == '220000.00'
        assert summary['supportEffectivePricingPlan']['tiers'][0]['baseCharge'] == '15000.00'

    @pytest.mark.asyncio
    async def test_response_metadata_is_stripped(self, mock_context, sample_charge_summary):
        """Botocore's transport metadata is not surfaced to the agent."""
        result = await _run_operation(
            mock_context,
            get_charge_summary,
            CHARGE_SUMMARY_OP,
            '2026-06',
            response=sample_charge_summary,
        )

        assert 'ResponseMetadata' not in result['data']['charge_summary']


class TestBillingMonthValidation:
    """Only billing months with published data reach the API."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'billing_month',
        [
            None,
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
    async def test_missing_or_malformed_month_is_rejected(self, mock_context, billing_month):
        """A month that is absent or not YYYY-MM fails without calling AWS.

        Only a four-digit year with a zero-padded month is accepted, so every
        other spelling is refused here rather than being sent to AWS. The message
        must name the format rather than data availability: an unpadded month such
        as ``2025-9`` used to pass validation entirely because ``strptime``
        accepts it and it sits inside the valid range, while ``2026-6`` was
        refused by a string comparison that reported it as an unavailable period
        instead of a malformed one.
        """
        result = await _run_rejected(mock_context, get_charge_summary, billing_month)

        assert result['status'] == 'error'
        message = result['data']['message']
        assert 'YYYY-MM' in message
        assert 'only published' not in message

    @pytest.mark.asyncio
    @pytest.mark.parametrize('handler,api_method', MONTH_VALIDATED_HANDLERS)
    async def test_month_before_floor_is_rejected(self, mock_context, handler, api_method):
        """A month earlier than the available data floor fails for every operation."""
        result = await _run_rejected(mock_context, handler, '2024-12')

        assert result['status'] == 'error'
        assert EARLIEST_BILLING_MONTH in result['data']['message']

    @pytest.mark.asyncio
    @pytest.mark.parametrize('handler,api_method', MONTH_VALIDATED_HANDLERS)
    async def test_current_month_is_rejected(self, mock_context, handler, api_method):
        """The current month is rejected for every operation, its period has not closed."""
        current_month = datetime.now(timezone.utc).strftime('%Y-%m')

        result = await _run_rejected(mock_context, handler, current_month)

        assert result['status'] == 'error'
        assert current_month in result['data']['message']

    @pytest.mark.asyncio
    async def test_future_month_is_rejected(self, mock_context):
        """A future month fails without calling AWS."""
        now = datetime.now(timezone.utc)
        future_month = f'{now.year + 1}-{now.month:02d}'

        result = await _run_rejected(mock_context, get_charge_summary, future_month)

        assert result['status'] == 'error'
        assert future_month in result['data']['message']

    @pytest.mark.asyncio
    async def test_earliest_billing_month_is_accepted(self, mock_context, sample_charge_summary):
        """The floor month itself reaches the API rather than being rejected."""
        response = {**sample_charge_summary, 'billingMonth': EARLIEST_BILLING_MONTH}

        result = await _run_operation(
            mock_context,
            get_charge_summary,
            CHARGE_SUMMARY_OP,
            EARLIEST_BILLING_MONTH,
            response=response,
        )

        assert result['status'] == 'success'
        assert result['data']['charge_summary']['billingMonth'] == EARLIEST_BILLING_MONTH

    @pytest.mark.asyncio
    async def test_previous_month_is_accepted(self, mock_context, sample_charge_summary):
        """The previous calendar month reaches the API as the newest available month."""
        previous = _previous_month()
        response = {**sample_charge_summary, 'billingMonth': previous}

        result = await _run_operation(
            mock_context,
            get_charge_summary,
            CHARGE_SUMMARY_OP,
            previous,
            response=response,
        )

        assert result['status'] == 'success'


class TestGetChargeSummaryErrors:
    """API failures return actionable standardized errors."""

    @pytest.mark.asyncio
    async def test_access_denied_names_permission_and_payer_requirement(self, mock_context):
        """AccessDenied is reported as authorization, never as an absence of charges."""
        result = await _run_operation(
            mock_context,
            get_charge_summary,
            CHARGE_SUMMARY_OP,
            '2026-06',
            error_code='AccessDeniedException',
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'access_denied'
        assert result['operation'] == 'GetEnterpriseSupportChargeSummary'
        assert 'billing:GetEnterpriseSupportChargeSummary' in result['resolution']
        assert 'payer account' in result['resolution']
        assert 'not an absence of Enterprise Support charges' in result['message']


class TestGetContractDetailsSuccess:
    """Contract details normalize dates and keep the account lists distinct."""

    @pytest.mark.asyncio
    async def test_returns_normalized_contract_details(
        self, mock_context, sample_contract_details
    ):
        """Timestamps become ISO strings and the documented value sets pass through."""
        result = await _run_operation(
            mock_context,
            get_contract_details,
            CONTRACT_DETAILS_OP,
            '2026-06',
            response=sample_contract_details,
        )

        assert result['status'] == 'success'
        details = result['data']['contract_details']
        assert details['supportAllocationMethod'] == 'Proportional'
        assert details['supportReservedInstanceTreatmentMethod'] == 'AmortizedCustom'
        assert details['supportReservedInstanceAmortizationStartDate'] == '2024-01-01T00:00:00'
        assert details['supportProrateStartDate'] == '2026-06-15T00:00:00'
        assert details['pricingPlans'][0]['startDate'] == '2024-01-01T00:00:00'
        assert details['pricingPlans'][0]['minimumCharge'] == '15000.00'
        assert 'ResponseMetadata' not in details

    @pytest.mark.asyncio
    async def test_contract_and_charged_account_lists_stay_distinct(
        self, mock_context, sample_contract_details
    ):
        """The covered and billed account lists are reported separately.

        The two lists carry different members and different fields, so collapsing
        them would misreport who is charged for Enterprise Support.
        """
        result = await _run_operation(
            mock_context,
            get_contract_details,
            CONTRACT_DETAILS_OP,
            '2026-06',
            response=sample_contract_details,
        )

        details = result['data']['contract_details']
        assert [a['accountId'] for a in details['contractPayerAccountIds']] == [
            '123456789012',
            '210987654321',
        ]
        assert details['contractPayerAccountIds'][1]['isGdn'] is True
        assert details['chargedPayerAccountIds'] == [
            {'accountId': '123456789012', 'chargePercentage': '100.0'}
        ]

    @pytest.mark.asyncio
    async def test_absent_optional_fields_are_tolerated(self, mock_context):
        """A minimal contract response shapes without inventing fields."""
        minimal = {
            'supportAllocationMethod': 'Fixed_Percentage',
            'contractPayerAccountIds': [],
            'chargedPayerAccountIds': [],
            'pricingPlans': [],
        }

        result = await _run_operation(
            mock_context, get_contract_details, CONTRACT_DETAILS_OP, '2026-06', response=minimal
        )

        assert result['status'] == 'success'
        details = result['data']['contract_details']
        assert details['supportAllocationMethod'] == 'Fixed_Percentage'
        assert 'isContractActive' not in details
        assert 'additionalSupportCharge' not in details


class TestGetContractDetailsErrors:
    """Contract details failures name the same authorization requirement."""

    @pytest.mark.asyncio
    async def test_access_denied_names_its_own_iam_action(self, mock_context):
        """The error names the contract-details action, not the charge-summary one."""
        result = await _run_operation(
            mock_context,
            get_contract_details,
            CONTRACT_DETAILS_OP,
            '2026-06',
            error_code='AccessDeniedException',
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'access_denied'
        assert result['operation'] == 'GetEnterpriseSupportContractDetails'
        assert 'billing:GetEnterpriseSupportContractDetails' in result['resolution']


@pytest.fixture
def sample_linked_account():
    """Return one LinkedAccountCharge as the AWS API returns it."""
    return {
        'accountId': '111122223333',
        'payerAccountId': '123456789012',
        'accountType': 'LINKED',
        'billableSeconds': 1296000,
        'totalSeconds': 2592000,
        'totalSupportEligibleSpend': '50000.00',
        'proratedTotalSupportEligibleSpend': '25000.00',
        'linkedTimePeriods': [
            {
                'beginDate': datetime(2026, 6, 1, tzinfo=timezone.utc),
                'endDate': datetime(2026, 7, 1, tzinfo=timezone.utc),
            }
        ],
        'subscriptionTimePeriods': [{'beginDate': datetime(2026, 6, 16, tzinfo=timezone.utc)}],
        'totalSupportEligibleReservedInstanceSpend': '10000.00',
        'totalSupportEligibleSavingsPlanSpend': '5000.00',
        'supportEligibleSpendByService': [
            {'serviceCode': 'AmazonEC2', 'totalSupportEligibleSpend': '30000.00'},
            {'serviceCode': 'AmazonS3', 'totalSupportEligibleSpend': '20000.00'},
        ],
    }


class TestListLinkedAccountCharges:
    """Linked account charges normalize, paginate and filter correctly."""

    @pytest.mark.asyncio
    async def test_returns_normalized_charges_and_pagination(
        self, mock_context, sample_linked_account
    ):
        """Nested time-period dates normalize and the pagination block is reported."""
        result = await _run_operation(
            mock_context,
            list_linked_account_charges,
            LINKED_CHARGES_OP,
            '2026-06',
            response={'linkedAccount': [sample_linked_account]},
        )

        assert result['status'] == 'success'
        charges = result['data']['linked_account_charges']
        assert len(charges) == 1
        assert charges[0]['linkedTimePeriods'][0]['beginDate'] == '2026-06-01T00:00:00'
        assert charges[0]['subscriptionTimePeriods'][0]['beginDate'] == '2026-06-16T00:00:00'
        assert 'endDate' not in charges[0]['subscriptionTimePeriods'][0]
        assert charges[0]['proratedTotalSupportEligibleSpend'] == '25000.00'
        assert charges[0]['supportEligibleSpendByService'][0]['serviceCode'] == 'AmazonEC2'
        assert result['data']['pagination']['complete_dataset'] is True
        assert result['data']['pagination']['total_results'] == 1

    @pytest.mark.asyncio
    async def test_account_id_is_omitted_when_not_requested(
        self, mock_context, sample_linked_account
    ):
        """No account filter is sent when the caller did not ask for one.

        Defaulting the filter to the caller would reduce an organization-wide
        breakdown to a single row, so its absence is the behaviour to protect.
        """
        result = await _run_operation(
            mock_context,
            list_linked_account_charges,
            LINKED_CHARGES_OP,
            '2026-06',
            response={'linkedAccount': [sample_linked_account]},
            expected_params={'billingMonth': '2026-06'},
        )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_account_id_filter_is_forwarded(self, mock_context, sample_linked_account):
        """An explicit account filter reaches the API."""
        result = await _run_operation(
            mock_context,
            list_linked_account_charges,
            LINKED_CHARGES_OP,
            '2026-06',
            response={'linkedAccount': [sample_linked_account]},
            expected_params={'billingMonth': '2026-06', 'accountId': '111122223333'},
            account_id='111122223333',
        )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_max_results_is_forwarded(self, mock_context, sample_linked_account):
        """An explicit page size reaches the API."""
        result = await _run_operation(
            mock_context,
            list_linked_account_charges,
            LINKED_CHARGES_OP,
            '2026-06',
            response={'linkedAccount': [sample_linked_account]},
            expected_params={'billingMonth': '2026-06', 'maxResults': 50},
            max_results=50,
        )

        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_empty_result_is_a_real_answer(self, mock_context):
        """No linked accounts returns an empty list rather than an error."""
        result = await _run_operation(
            mock_context,
            list_linked_account_charges,
            LINKED_CHARGES_OP,
            '2026-06',
            response={'linkedAccount': []},
        )

        assert result['status'] == 'success'
        assert result['data']['linked_account_charges'] == []
        assert result['data']['pagination']['total_results'] == 0

    @pytest.mark.asyncio
    async def test_access_denied_names_its_own_iam_action(self, mock_context):
        """The error names the linked-account-charges action."""
        result = await _run_operation(
            mock_context,
            list_linked_account_charges,
            LINKED_CHARGES_OP,
            '2026-06',
            error_code='AccessDeniedException',
        )

        assert result['status'] == 'error'
        assert result['operation'] == 'ListEnterpriseSupportLinkedAccountCharges'
        assert 'billing:ListEnterpriseSupportLinkedAccountCharges' in result['resolution']


class TestSharedErrorClassification:
    """Failures that mislead are classified the same way for every operation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(('handler', 'api_method'), MONTH_VALIDATED_HANDLERS)
    async def test_missing_data_is_not_reported_as_a_denial(
        self, mock_context, handler, api_method
    ):
        """An account with no Enterprise Support data reads as not_found.

        The API raises ResourceNotFoundException for any account or billing period
        without Enterprise Support data, which is the common case for an account
        that is not an Enterprise Support customer. Classifying it separately keeps
        it from being reported as a permission failure and from being retried.
        """
        result = await _run_operation(
            mock_context,
            handler,
            api_method,
            '2026-07',
            error_code='ResourceNotFoundException',
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'not_found'
        assert 'not a permission problem' in result['message']
        assert 'do not retry the same period' in result['resolution']
        assert 'aws_message' in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize(('handler', 'api_method'), MONTH_VALIDATED_HANDLERS)
    async def test_access_denied_is_not_reported_as_missing_data(
        self, mock_context, handler, api_method
    ):
        """A denial reads as access_denied for every operation."""
        result = await _run_operation(
            mock_context,
            handler,
            api_method,
            '2026-07',
            error_code='AccessDeniedException',
        )

        assert result['error_type'] == 'access_denied'
        assert 'not an absence of Enterprise Support charges' in result['message']

    @pytest.mark.asyncio
    async def test_other_client_errors_fall_through(self, mock_context):
        """An unclassified error keeps the AWS error code from the shared handler.

        Only the two misleading failures are explained here; anything else must
        reach the shared handler unaltered rather than being given guidance that
        does not apply to it.
        """
        result = await _run_operation(
            mock_context,
            get_charge_summary,
            CHARGE_SUMMARY_OP,
            '2026-07',
            error_code='ThrottlingException',
        )

        assert result['status'] == 'error'
        assert result.get('error_type') != 'access_denied'
        assert result.get('error_type') != 'not_found'

    @pytest.mark.asyncio
    async def test_non_client_errors_fall_through(self, mock_context):
        """A transport failure reaches the shared handler rather than being classified.

        Only ``ClientError`` carries an AWS error code, so a connection failure has
        nothing to classify and must pass through untouched. Without this the
        module would need the caller to distinguish transport from service errors.
        """
        client = MagicMock()
        client.get_enterprise_support_charge_summary.side_effect = EndpointConnectionError(
            endpoint_url='https://billing.us-east-1.amazonaws.com'
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_charge_summary(mock_context, billing_month='2026-06')

        assert result['status'] == 'error'
        assert 'error_type' not in result or result['error_type'] not in (
            'access_denied',
            'not_found',
        )


class TestListLinkedAccountChargesPaging:
    """Paging inputs reach the API and the year boundary is handled."""

    @pytest.mark.asyncio
    async def test_next_token_is_forwarded(self, mock_context):
        """A caller-supplied token resumes the walk rather than restarting it."""
        result = await _run_operation(
            mock_context,
            list_linked_account_charges,
            LINKED_CHARGES_OP,
            '2026-06',
            response={'linkedAccount': []},
            expected_params={'billingMonth': '2026-06', 'nextToken': 'resume-here'},
            next_token='resume-here',
        )

        assert result['status'] == 'success'


class TestLatestAvailableMonthYearBoundary:
    """The newest answerable period rolls back across a year boundary."""

    @pytest.mark.asyncio
    async def test_january_rolls_back_to_previous_december(self, mock_context):
        """In January the newest answerable period is the prior December.

        Frozen to a January date because the rollback branch is unreachable for
        eleven months of the year, and getting it wrong would reject the only
        period a caller can actually ask for each January.
        """
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools'
            '.enterprise_support_operations.datetime'
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2027, 1, 15, tzinfo=timezone.utc)
            mock_datetime.strptime = datetime.strptime
            result = await _run_rejected(mock_context, get_charge_summary, '2027-01')

        assert result['status'] == 'error'
        assert '2026-12' in result['data']['message']
