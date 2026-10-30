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

"""Tests that each paged operation maps its service's bad-token code to invalid_next_token.

Services outside Cost Explorer, Budgets and Price List report a bad next_token with a
generic code (ValidationException or InvalidParameterValueException) instead of
InvalidNextTokenException. Each operation's PageSpec names that code, so a rejected caller
token gets the restart hint, while the same code without a caller token stays an ordinary
error. Because those codes also report other invalid arguments, the message must name
the token too, except for the billing group cost report, whose expired-token error may not.
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools import (
    bcm_pricing_calculator_tools,
    billing_conductor_operations,
    billing_preferences_operations,
    business_support_operations,
    bvs_operations,
    compute_optimizer_automation_operations,
    cost_optimization_hub_helpers,
    credits_operations,
    enterprise_support_operations,
    free_tier_usage_tools,
    invoice_units_operations,
    invoicing_operations,
    procurement_preferences_operations,
    sp_explorer_tools,
)
from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
    handle_aws_error,
    paginate_aws_items,
)
from awslabs.billing_cost_management_mcp_server.utilities.error_contract import (
    InvalidNextTokenError,
    add_retry_guidance,
)
from botocore.exceptions import ClientError
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock


VALIDATION = 'ValidationException'
INVALID_PARAMETER = 'InvalidParameterValueException'

SPECS = [
    pytest.param(
        bcm_pricing_calculator_tools.LIST_WORKLOAD_ESTIMATES_PAGE_SPEC,
        VALIDATION,
        id='LIST_WORKLOAD_ESTIMATES_PAGE_SPEC',
    ),
    pytest.param(
        bcm_pricing_calculator_tools.LIST_WORKLOAD_ESTIMATE_USAGE_PAGE_SPEC,
        VALIDATION,
        id='LIST_WORKLOAD_ESTIMATE_USAGE_PAGE_SPEC',
    ),
    pytest.param(
        billing_conductor_operations.BC_LIST_BILLING_GROUPS,
        VALIDATION,
        id='BC_LIST_BILLING_GROUPS',
    ),
    pytest.param(
        billing_conductor_operations.BC_LIST_ACCOUNT_ASSOCIATIONS,
        VALIDATION,
        id='BC_LIST_ACCOUNT_ASSOCIATIONS',
    ),
    pytest.param(
        billing_conductor_operations.BC_LIST_BILLING_GROUP_COST_REPORTS,
        VALIDATION,
        id='BC_LIST_BILLING_GROUP_COST_REPORTS',
    ),
    pytest.param(
        billing_conductor_operations.BC_LIST_CUSTOM_LINE_ITEMS,
        VALIDATION,
        id='BC_LIST_CUSTOM_LINE_ITEMS',
    ),
    pytest.param(
        billing_conductor_operations.BC_LIST_CUSTOM_LINE_ITEM_VERSIONS,
        VALIDATION,
        id='BC_LIST_CUSTOM_LINE_ITEM_VERSIONS',
    ),
    pytest.param(
        billing_conductor_operations.BC_LIST_RESOURCES_ASSOCIATED_TO_CUSTOM_LINE_ITEM,
        VALIDATION,
        id='BC_LIST_RESOURCES_ASSOCIATED_TO_CUSTOM_LINE_ITEM',
    ),
    pytest.param(
        billing_conductor_operations.BC_LIST_PRICING_RULES,
        VALIDATION,
        id='BC_LIST_PRICING_RULES',
    ),
    pytest.param(
        billing_conductor_operations.BC_LIST_PRICING_PLANS,
        VALIDATION,
        id='BC_LIST_PRICING_PLANS',
    ),
    pytest.param(
        billing_conductor_operations.BC_LIST_PRICING_RULES_FOR_PLAN,
        VALIDATION,
        id='BC_LIST_PRICING_RULES_FOR_PLAN',
    ),
    pytest.param(
        billing_conductor_operations.BC_LIST_PRICING_PLANS_FOR_RULE,
        VALIDATION,
        id='BC_LIST_PRICING_PLANS_FOR_RULE',
    ),
    pytest.param(
        billing_preferences_operations.BILLING_GET_BILLING_PREFERENCES,
        VALIDATION,
        id='BILLING_GET_BILLING_PREFERENCES',
    ),
    pytest.param(
        bvs_operations.BVS_LIST_SOURCE_VIEWS_FOR_BILLING_VIEW,
        VALIDATION,
        id='BVS_LIST_SOURCE_VIEWS_FOR_BILLING_VIEW',
    ),
    pytest.param(bvs_operations.BVS_LIST_BILLING_VIEWS, VALIDATION, id='BVS_LIST_BILLING_VIEWS'),
    pytest.param(
        bvs_operations.BVS_LIST_BILLING_VIEW_SEGMENTS,
        VALIDATION,
        id='BVS_LIST_BILLING_VIEW_SEGMENTS',
    ),
    pytest.param(
        compute_optimizer_automation_operations.COA_LIST_AUTOMATION_EVENTS,
        INVALID_PARAMETER,
        id='COA_LIST_AUTOMATION_EVENTS',
    ),
    pytest.param(
        compute_optimizer_automation_operations.COA_LIST_AUTOMATION_EVENT_STEPS,
        INVALID_PARAMETER,
        id='COA_LIST_AUTOMATION_EVENT_STEPS',
    ),
    pytest.param(
        compute_optimizer_automation_operations.COA_LIST_AUTOMATION_EVENT_SUMMARIES,
        INVALID_PARAMETER,
        id='COA_LIST_AUTOMATION_EVENT_SUMMARIES',
    ),
    pytest.param(
        compute_optimizer_automation_operations.COA_LIST_AUTOMATION_RULES,
        INVALID_PARAMETER,
        id='COA_LIST_AUTOMATION_RULES',
    ),
    pytest.param(
        compute_optimizer_automation_operations.COA_LIST_RECOMMENDED_ACTIONS,
        INVALID_PARAMETER,
        id='COA_LIST_RECOMMENDED_ACTIONS',
    ),
    pytest.param(
        compute_optimizer_automation_operations.COA_LIST_RECOMMENDED_ACTION_SUMMARIES,
        INVALID_PARAMETER,
        id='COA_LIST_RECOMMENDED_ACTION_SUMMARIES',
    ),
    pytest.param(
        compute_optimizer_automation_operations.COA_LIST_AUTOMATION_RULE_PREVIEW,
        INVALID_PARAMETER,
        id='COA_LIST_AUTOMATION_RULE_PREVIEW',
    ),
    pytest.param(
        getattr(
            compute_optimizer_automation_operations, 'COA_LIST_AUTOMATION_RULE_PREVIEW_SUMMARIES'
        ),
        INVALID_PARAMETER,
        id='COA_LIST_AUTOMATION_RULE_PREVIEW_SUMMARIES',
    ),
    pytest.param(
        cost_optimization_hub_helpers.COH_LIST_RECOMMENDATIONS,
        VALIDATION,
        id='COH_LIST_RECOMMENDATIONS',
    ),
    pytest.param(
        cost_optimization_hub_helpers.COH_LIST_RECOMMENDATION_SUMMARIES,
        VALIDATION,
        id='COH_LIST_RECOMMENDATION_SUMMARIES',
    ),
    pytest.param(
        cost_optimization_hub_helpers.COH_LIST_EFFICIENCY_METRICS,
        VALIDATION,
        id='COH_LIST_EFFICIENCY_METRICS',
    ),
    pytest.param(
        business_support_operations.LIST_ACCOUNT_CHARGES_PAGE_SPEC,
        VALIDATION,
        id='LIST_ACCOUNT_CHARGES_PAGE_SPEC',
    ),
    pytest.param(
        business_support_operations.LIST_SUBSCRIPTION_HISTORY_PAGE_SPEC,
        VALIDATION,
        id='LIST_SUBSCRIPTION_HISTORY_PAGE_SPEC',
    ),
    pytest.param(
        credits_operations.GET_CREDIT_ALLOCATION_HISTORY_PAGE_SPEC,
        VALIDATION,
        id='GET_CREDIT_ALLOCATION_HISTORY_PAGE_SPEC',
    ),
    pytest.param(
        enterprise_support_operations.LIST_LINKED_ACCOUNT_CHARGES_PAGE_SPEC,
        VALIDATION,
        id='LIST_LINKED_ACCOUNT_CHARGES_PAGE_SPEC',
    ),
    pytest.param(
        free_tier_usage_tools.GET_FREE_TIER_USAGE_PAGE_SPEC,
        VALIDATION,
        id='GET_FREE_TIER_USAGE_PAGE_SPEC',
    ),
    pytest.param(
        invoice_units_operations.LIST_INVOICE_UNITS_PAGE_SPEC,
        VALIDATION,
        id='LIST_INVOICE_UNITS_PAGE_SPEC',
    ),
    pytest.param(
        invoicing_operations.LIST_INVOICE_SUMMARIES_PAGE_SPEC,
        VALIDATION,
        id='LIST_INVOICE_SUMMARIES_PAGE_SPEC',
    ),
    pytest.param(
        getattr(
            procurement_preferences_operations, 'LIST_PROCUREMENT_PORTAL_PREFERENCES_PAGE_SPEC'
        ),
        VALIDATION,
        id='LIST_PROCUREMENT_PORTAL_PREFERENCES_PAGE_SPEC',
    ),
    pytest.param(
        sp_explorer_tools.SP_DESCRIBE_SAVINGS_PLANS,
        VALIDATION,
        id='SP_DESCRIBE_SAVINGS_PLANS',
    ),
    pytest.param(
        sp_explorer_tools.SP_DESCRIBE_SAVINGS_PLAN_RATES,
        VALIDATION,
        id='SP_DESCRIBE_SAVINGS_PLAN_RATES',
    ),
    pytest.param(
        sp_explorer_tools.SP_DESCRIBE_SAVINGS_PLANS_OFFERINGS,
        VALIDATION,
        id='SP_DESCRIBE_SAVINGS_PLANS_OFFERINGS',
    ),
    pytest.param(
        sp_explorer_tools.SP_DESCRIBE_SAVINGS_PLANS_OFFERING_RATES,
        VALIDATION,
        id='SP_DESCRIBE_SAVINGS_PLANS_OFFERING_RATES',
    ),
]


@pytest.fixture
def ctx():
    """Create a mock MCP context."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    context.debug = AsyncMock()
    return context


def _client_error(code, message='Invalid pagination token.'):
    return ClientError({'Error': {'Code': code, 'Message': message}}, 'Op')


@pytest.mark.parametrize('spec, code', SPECS)
async def test_rejected_caller_token_is_invalid_next_token(ctx, spec, code):
    """The service's bad-token code on the caller's next_token gives the restart hint."""
    api = MagicMock(side_effect=_client_error(code))

    with pytest.raises(InvalidNextTokenError) as raised:
        await paginate_aws_items(ctx, 'op', api, {}, spec, next_token='bogus')

    response = add_retry_guidance(await handle_aws_error(ctx, raised.value, 'op', 'svc'))
    assert response['error_type'] == 'invalid_next_token'
    assert 'without next_token' in response['hint']


@pytest.mark.parametrize('spec, code', SPECS)
async def test_same_code_without_caller_token_is_unchanged(ctx, spec, code):
    """Without a caller next_token the code is the service's own error, raised unchanged."""
    api = MagicMock(side_effect=_client_error(code))

    with pytest.raises(ClientError) as raised:
        await paginate_aws_items(ctx, 'op', api, {}, spec)

    assert raised.value.response['Error']['Code'] == code


@pytest.mark.parametrize('spec, code', SPECS)
async def test_same_code_on_a_later_page_keeps_the_retry_token(ctx, spec, code):
    """On a later page the code is an ordinary failure: the result is partial and resumable."""
    page: Dict[str, Any] = {spec.result_key: [], spec.token_key_in_response: 't1'}
    api = MagicMock(side_effect=[page, _client_error(code)])

    _, _, pagination = await paginate_aws_items(ctx, 'op', api, {}, spec, next_token='t0')

    assert pagination['complete_dataset'] is False
    assert pagination['next_token'] == 't1'


@pytest.mark.parametrize('spec, code', SPECS)
async def test_same_code_about_another_argument_is_unchanged(ctx, spec, code):
    """With a caller next_token, the code stays the service's error when it names another argument."""
    api = MagicMock(side_effect=_client_error(code, 'maxResults must be between 1 and 100.'))

    with pytest.raises(ClientError) as raised:
        await paginate_aws_items(ctx, 'op', api, {}, spec, next_token='bogus')

    assert raised.value.response['Error']['Code'] == code


@pytest.mark.parametrize('code', ['ValidationException', 'InternalServerException'])
async def test_cost_report_maps_its_codes_without_a_token_message(ctx, code):
    """The cost report's expired token need not name the token, so its codes map by code alone."""
    api = MagicMock(side_effect=_client_error(code, 'An internal error occurred.'))

    with pytest.raises(InvalidNextTokenError):
        await paginate_aws_items(
            ctx,
            'op',
            api,
            {},
            billing_conductor_operations.BC_GET_BILLING_GROUP_COST_REPORT,
            next_token='bogus',
        )


@pytest.mark.parametrize('spec, code', SPECS)
async def test_unlisted_code_with_caller_token_is_unchanged(ctx, spec, code):
    """A code the spec does not list stays the service's error, even when it names the token."""
    api = MagicMock(
        side_effect=_client_error('AccessDeniedException', 'Not authorized to use token.')
    )

    with pytest.raises(ClientError) as raised:
        await paginate_aws_items(ctx, 'op', api, {}, spec, next_token='bogus')

    assert raised.value.response['Error']['Code'] == 'AccessDeniedException'
