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

"""Tests for the Savings Plans explorer tools.

The Savings Plans service does not share Cost Explorer's vocabulary, and these
tests fix the differences that are easy to get wrong: request parameters are
camelCase, the pagination token is lowercase `nextToken`, payment options carry
spaces, plan types are not suffixed with _SP, and terms are durations in seconds.
They also fix the two offering operations sharing one set of tool parameter names
while the API spells three of its fields differently for each.
"""

import pytest
import sqlite3
from awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools import (
    describe_savings_plan_rates,
    describe_savings_plans,
    describe_savings_plans_offering_rates,
    describe_savings_plans_offerings,
    sp_explorer,
    sp_explorer_server,
)
from awslabs.billing_cost_management_mcp_server.utilities import sql_utils
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.debug = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def sample_savings_plan():
    """One active Savings Plan, shaped as the Savings Plans API returns it."""
    return {
        'offeringId': '7fb303ac-60fa-44c3-bb28-e847aa8073ac',
        'savingsPlanId': '577d4a65-34e7-4b2e-92d7-5e845ba5e55d',
        'savingsPlanArn': 'arn:aws:savingsplans::123456789012:savingsplan/577d4a65',
        'description': '1 year All Upfront Compute Savings Plan',
        'start': '2025-12-19T12:12:12.000Z',
        'end': '2026-12-19T12:12:11.000Z',
        'state': 'active',
        'savingsPlanType': 'Compute',
        'paymentOption': 'All Upfront',
        'productTypes': ['Fargate', 'EC2', 'Lambda'],
        'currency': 'USD',
        'commitment': '0.00100000',
        'upfrontPaymentAmount': '8.76000000',
        'recurringPaymentAmount': '0.00000000',
        'termDurationInSeconds': 31536000,
        'tags': {},
        'returnableUntil': '2025-12-26T12:12:12.000Z',
    }


@pytest.fixture
def mock_sp_client(sample_savings_plan):
    """Create a mock Savings Plans boto3 client."""
    client = MagicMock()
    client.describe_savings_plans.return_value = {
        'savingsPlans': [sample_savings_plan],
    }
    client.describe_savings_plan_rates.return_value = {
        'savingsPlanId': '577d4a65-34e7-4b2e-92d7-5e845ba5e55d',
        'searchResults': [
            {
                'rate': '0.0464',
                'currency': 'USD',
                'unit': 'Hrs',
                'productType': 'EC2',
                'serviceCode': 'AmazonEC2',
                'usageType': 'APN1-DedicatedUsage:c6i.large',
                'operation': 'RunInstances',
                'properties': [{'name': 'instanceType', 'value': 'c6i.large'}],
            }
        ],
    }
    client.describe_savings_plans_offerings.return_value = {
        'searchResults': [
            {
                'offeringId': '005305de-48ea-405e-bae3-8b764b913a8e',
                'productTypes': ['EC2'],
                'planType': 'Compute',
                'description': '1 year No Upfront Compute Savings Plan',
                'paymentOption': 'No Upfront',
                'durationSeconds': 31536000,
                'currency': 'USD',
                'serviceCode': 'AmazonEC2',
                'usageType': 'APN1-DedicatedUsage:c6i.large',
                'operation': 'RunInstances',
                'properties': [{'name': 'region', 'value': 'ap-northeast-1'}],
            }
        ],
    }
    client.describe_savings_plans_offering_rates.return_value = {
        'searchResults': [
            {
                'savingsPlanOffering': {
                    'offeringId': '005305de-48ea-405e-bae3-8b764b913a8e',
                    'paymentOption': 'No Upfront',
                    'planType': 'Compute',
                    'durationSeconds': 31536000,
                    'currency': 'USD',
                    'planDescription': '1 year No Upfront Compute Savings Plan',
                },
                'rate': '0.0464',
                'unit': 'Hrs',
                'productType': 'EC2',
                'serviceCode': 'AmazonEC2',
                'usageType': 'APN1-DedicatedUsage:c6i.large',
                'operation': 'RunInstances',
                'properties': [{'name': 'instanceType', 'value': 'c6i.large'}],
            }
        ],
    }
    return client


PAGINATION_COMPLETE = {
    'complete_dataset': True,
    'pages_fetched': 1,
    'total_results': 1,
    'has_more': False,
    'next_token': None,
    'duration_ms': 1,
}


PAGINATION_MORE = {
    'complete_dataset': False,
    'pages_fetched': 3,
    'total_results': 3,
    'has_more': True,
    'next_token': 'next-page-token',
    'duration_ms': 2,
}


def _in_memory_session_db():
    """An in-memory SQLite connection carrying the schema_info bookkeeping table.

    Mirrors the real session database closely enough to exercise the unpatched
    offload path (convert_response_if_needed -> convert_api_response_to_table)
    without touching disk.
    """
    conn = sqlite3.connect(':memory:')
    conn.execute(
        'CREATE TABLE IF NOT EXISTS schema_info '
        '(table_name TEXT PRIMARY KEY, created_at TEXT, operation TEXT, '
        'query TEXT, row_count INTEGER)'
    )
    return conn


@pytest.mark.asyncio
class TestDescribeSavingsPlans:
    """Tests for describe_savings_plans."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_basic(self, mock_paginate, mock_context, mock_sp_client, sample_savings_plan):
        """Inventory comes back under the API's own key, with pagination metadata."""
        mock_paginate.return_value = ([sample_savings_plan], PAGINATION_COMPLETE)

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None, None
        )

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs['operation_name'] == 'DescribeSavingsPlans'
        assert call_kwargs['result_key'] == 'savingsPlans'
        # The Savings Plans service uses a lowercase token; Cost Explorer does not.
        assert call_kwargs['token_param'] == 'nextToken'
        assert call_kwargs['token_key'] == 'nextToken'
        assert call_kwargs['request_params'] == {}

        assert result['status'] == 'success'
        assert result['data']['savingsPlans'] == [sample_savings_plan]
        assert result['data']['pagination']['complete_dataset'] is True

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_states_and_filters_are_json_decoded(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """List parameters are passed through to boto3 unchanged."""
        mock_paginate.return_value = ([], PAGINATION_COMPLETE)

        await describe_savings_plans(
            mock_context,
            mock_sp_client,
            ['arn:aws:savingsplans::123456789012:savingsplan/abc'],
            ['577d4a65'],
            ['active', 'queued', 'payment-failed'],
            [{'name': 'savings-plan-type', 'values': ['Compute']}],
            'token-from-caller',
            50,
            3,
        )

        request_params = mock_paginate.call_args[1]['request_params']
        assert request_params['states'] == ['active', 'queued', 'payment-failed']
        assert request_params['savingsPlanIds'] == ['577d4a65']
        assert request_params['savingsPlanArns'] == [
            'arn:aws:savingsplans::123456789012:savingsplan/abc'
        ]
        assert request_params['filters'] == [{'name': 'savings-plan-type', 'values': ['Compute']}]
        assert request_params['nextToken'] == 'token-from-caller'
        assert request_params['maxResults'] == 50
        assert mock_paginate.call_args[1]['max_pages'] == 3

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_small_result_is_returned_inline(
        self, mock_paginate, mock_context, mock_sp_client, sample_savings_plan
    ):
        """Below the SQL threshold, inventory stays inline with no offload."""
        mock_paginate.return_value = ([sample_savings_plan], PAGINATION_COMPLETE)

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None, None
        )

        # The small-response shape is unchanged by the offload gate.
        assert result['data']['savingsPlans'] == [sample_savings_plan]
        assert result['data']['pagination'] == PAGINATION_COMPLETE
        assert 'data_stored' not in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.convert_response_if_needed'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_large_result_is_offloaded_to_sql(
        self, mock_paginate, mock_convert, mock_context, mock_sp_client, sample_savings_plan
    ):
        """A large inventory is offloaded to session SQL instead of inline."""
        plans = [sample_savings_plan]
        mock_paginate.return_value = (plans, PAGINATION_COMPLETE)
        mock_convert.return_value = {
            'data_stored': True,
            'table_name': 'sp_explorer_describe_savings_plans_abcd1234',
            'row_count': 1,
        }

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None, None
        )

        assert result['status'] == 'success'
        assert result['data']['data_stored'] is True
        assert 'table_name' in result['data']
        assert 'savingsPlans' not in result['data']

        mock_convert.assert_called_once()
        call_args = mock_convert.call_args[0]
        # The inline shape is handed to the offloader, and the api_name routes it
        # to the per-row 'records' converter registered in sql_utils.
        assert call_args[1] == {'savingsPlans': plans, 'pagination': PAGINATION_COMPLETE}
        assert call_args[2] == 'sp_explorer_describe_savings_plans'
        # Pagination is passed explicitly so has_more/next_token survive the
        # offload and reach the stored-table sentinel.
        assert mock_convert.call_args[1]['pagination'] == PAGINATION_COMPLETE

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_large_result_offload_real_path_stores_rows_and_pagination(
        self, mock_paginate, mock_get_conn, mock_context, mock_sp_client
    ):
        """The unpatched offload path stores one row per plan and keeps pagination.

        Runs convert_response_if_needed for real (threshold lowered to force the
        offload) so the plan items (each with a productTypes list and a tags dict)
        land in a session-SQL table and the has_more/next_token markers survive on
        the sentinel via the explicit pagination kwarg from the fix.
        """
        plans = [
            {
                'savingsPlanId': f'577d4a65-{i}',
                'savingsPlanArn': f'arn:aws:savingsplans::123456789012:savingsplan/577d4a65-{i}',
                'offeringId': '7fb303ac-60fa-44c3-bb28-e847aa8073ac',
                'start': '2025-12-19T12:12:12.000Z',
                'end': '2026-12-19T12:12:11.000Z',
                'state': 'active',
                'region': 'us-east-1',
                'ec2InstanceFamily': 'm5',
                'savingsPlanType': 'Compute',
                'paymentOption': 'All Upfront',
                'productTypes': ['Fargate', 'EC2', 'Lambda'],
                'currency': 'USD',
                'commitment': '0.00100000',
                'upfrontPaymentAmount': '8.76000000',
                'recurringPaymentAmount': '0.00000000',
                'termDurationInSeconds': 31536000,
                'tags': {'team': 'infra'},
            }
            for i in range(3)
        ]
        mock_paginate.return_value = (plans, PAGINATION_MORE)

        conn = _in_memory_session_db()
        mock_get_conn.return_value = (conn, conn.cursor())

        # Threshold lowered to 0 so the real convert_response_if_needed path runs
        # instead of returning the small result inline.
        with patch.object(sql_utils, 'SQL_CONVERSION_THRESHOLD', 0):
            result = await describe_savings_plans(
                mock_context, mock_sp_client, None, None, None, None, None, None, None
            )

        data = result['data']
        assert result['status'] == 'success'
        # The plan items were stored one row each, not returned inline.
        assert data['data_stored'] is True
        assert data['table_name'].startswith('sp_explorer_describe_savings_plans_')
        assert data['row_count'] == len(plans)
        assert 'savingsPlans' not in data
        # has_more/next_token survive the offload on the sentinel.
        assert data['pagination']['has_more'] is True
        assert data['pagination']['next_token'] == 'next-page-token'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_error(self, mock_paginate, mock_context, mock_sp_client):
        """A client failure is reported rather than raised."""
        mock_paginate.side_effect = Exception('AccessDeniedException')

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None, None
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestDescribeSavingsPlanRates:
    """Tests for describe_savings_plan_rates."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_basic(self, mock_paginate, mock_context, mock_sp_client):
        """Rates page through searchResults and keep the plan id on the result."""
        rates = mock_sp_client.describe_savings_plan_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, PAGINATION_COMPLETE)

        result = await describe_savings_plan_rates(
            mock_context, mock_sp_client, '577d4a65', None, None, None, None
        )

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs['operation_name'] == 'DescribeSavingsPlanRates'
        assert call_kwargs['result_key'] == 'searchResults'
        assert call_kwargs['token_param'] == 'nextToken'
        assert call_kwargs['request_params']['savingsPlanId'] == '577d4a65'

        # Each page echoes savingsPlanId at the top level; the merged result has to
        # carry it too, or the rates lose the plan they belong to.
        assert result['data']['savingsPlanId'] == '577d4a65'
        assert result['data']['searchResults'] == rates

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_with_filters(self, mock_paginate, mock_context, mock_sp_client):
        """This operation's filter names are camelCase, unlike describe_savings_plans."""
        mock_paginate.return_value = ([], PAGINATION_COMPLETE)

        await describe_savings_plan_rates(
            mock_context,
            mock_sp_client,
            '577d4a65',
            [{'name': 'instanceType', 'values': ['c6i.large']}],
            'resume-here',
            5,
            None,
        )

        request_params = mock_paginate.call_args[1]['request_params']
        assert request_params['filters'] == [{'name': 'instanceType', 'values': ['c6i.large']}]
        assert request_params['maxResults'] == 5
        assert request_params['nextToken'] == 'resume-here'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_small_result_is_returned_inline(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Below the SQL threshold, rates stay inline with the plan id and no offload."""
        rates = mock_sp_client.describe_savings_plan_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, PAGINATION_COMPLETE)

        result = await describe_savings_plan_rates(
            mock_context, mock_sp_client, '577d4a65', None, None, None, None
        )

        # The small-response shape is unchanged by the offload gate.
        assert result['data']['savingsPlanId'] == '577d4a65'
        assert result['data']['searchResults'] == rates
        assert result['data']['pagination'] == PAGINATION_COMPLETE
        assert 'data_stored' not in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.convert_response_if_needed'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_large_result_is_offloaded_to_sql(
        self, mock_paginate, mock_convert, mock_context, mock_sp_client
    ):
        """A large rate list is offloaded to session SQL instead of inline."""
        rates = mock_sp_client.describe_savings_plan_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, PAGINATION_COMPLETE)
        mock_convert.return_value = {
            'data_stored': True,
            'table_name': 'sp_explorer_describe_savings_plan_rates_abcd1234',
            'row_count': 1,
            'savingsPlanId': '577d4a65',
        }

        result = await describe_savings_plan_rates(
            mock_context, mock_sp_client, '577d4a65', None, None, None, None
        )

        assert result['status'] == 'success'
        assert result['data']['data_stored'] is True
        assert 'table_name' in result['data']
        assert 'searchResults' not in result['data']

        mock_convert.assert_called_once()
        call_args = mock_convert.call_args[0]
        # The inline shape is handed to the offloader, and the api_name routes it
        # to the per-row 'records' converter registered in sql_utils.
        assert call_args[1] == {
            'savingsPlanId': '577d4a65',
            'searchResults': rates,
            'pagination': PAGINATION_COMPLETE,
        }
        assert call_args[2] == 'sp_explorer_describe_savings_plan_rates'
        # Pagination is passed explicitly so has_more/next_token survive the
        # offload. savingsPlanId rides along as metadata because the records
        # converter keeps only the first list field (searchResults).
        assert mock_convert.call_args[1]['pagination'] == PAGINATION_COMPLETE
        assert mock_convert.call_args[1]['savingsPlanId'] == '577d4a65'

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_large_result_offload_real_path_stores_rows_and_keeps_plan_id(
        self, mock_paginate, mock_get_conn, mock_context, mock_sp_client
    ):
        """The unpatched offload path stores one row per rate and keeps plan id + pagination.

        Runs convert_response_if_needed for real (threshold lowered to force the
        offload) so the nested rate items (each with a properties list) land in a
        session-SQL table. savingsPlanId and the has_more/next_token markers survive
        on the sentinel via the explicit metadata kwargs from the fix.
        """
        rates = [
            {
                'rate': f'0.0646{i}',
                'currency': 'USD',
                'unit': 'Hrs',
                'productType': 'EC2',
                'serviceCode': 'AmazonEC2',
                'usageType': 'USE1-BoxUsage:m5.large',
                'operation': 'RunInstances',
                'properties': [
                    {'name': 'region', 'value': 'us-east-1'},
                    {'name': 'instanceType', 'value': 'm5.large'},
                    {'name': 'productDescription', 'value': 'Linux/UNIX'},
                    {'name': 'tenancy', 'value': 'shared'},
                ],
            }
            for i in range(3)
        ]
        mock_paginate.return_value = (rates, PAGINATION_MORE)

        conn = _in_memory_session_db()
        mock_get_conn.return_value = (conn, conn.cursor())

        # Threshold lowered to 0 so the real convert_response_if_needed path runs
        # instead of returning the small result inline.
        with patch.object(sql_utils, 'SQL_CONVERSION_THRESHOLD', 0):
            result = await describe_savings_plan_rates(
                mock_context, mock_sp_client, '9355d9d7', None, None, None, None
            )

        data = result['data']
        assert result['status'] == 'success'
        # The nested rate items were stored one row each, not returned inline.
        assert data['data_stored'] is True
        assert data['table_name'].startswith('sp_explorer_describe_savings_plan_rates_')
        assert data['row_count'] == len(rates)
        assert 'searchResults' not in data
        # The records converter keeps only the first list field, so the plan id
        # has to survive as metadata on the sentinel.
        assert data['savingsPlanId'] == '9355d9d7'
        # has_more/next_token survive the offload on the sentinel.
        assert data['pagination']['has_more'] is True
        assert data['pagination']['next_token'] == 'next-page-token'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_error(self, mock_paginate, mock_context, mock_sp_client):
        """A client failure is reported rather than raised."""
        mock_paginate.side_effect = Exception('ResourceNotFoundException')

        result = await describe_savings_plan_rates(
            mock_context, mock_sp_client, 'missing', None, None, None, None
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestDescribeSavingsPlansOfferings:
    """Tests for describe_savings_plans_offerings."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_basic(self, mock_paginate, mock_context, mock_sp_client):
        """Offerings page through searchResults."""
        offerings = mock_sp_client.describe_savings_plans_offerings.return_value['searchResults']
        mock_paginate.return_value = (offerings, PAGINATION_COMPLETE)

        result = await describe_savings_plans_offerings(
            mock_context,
            mock_sp_client,
            offering_ids=None,
            payment_options=None,
            product_type=None,
            plan_types=None,
            durations=None,
            currencies=None,
            descriptions=None,
            service_codes=None,
            usage_types=None,
            operations=None,
            filters=None,
            next_token=None,
            max_results=None,
            max_pages=None,
        )

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs['operation_name'] == 'DescribeSavingsPlansOfferings'
        assert call_kwargs['result_key'] == 'searchResults'
        assert result['data']['searchResults'] == offerings

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_small_result_is_returned_inline(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Below the SQL threshold, offerings stay inline with no offload."""
        offerings = mock_sp_client.describe_savings_plans_offerings.return_value['searchResults']
        mock_paginate.return_value = (offerings, PAGINATION_COMPLETE)

        result = await describe_savings_plans_offerings(
            mock_context,
            mock_sp_client,
            offering_ids=None,
            payment_options=None,
            product_type=None,
            plan_types=None,
            durations=None,
            currencies=None,
            descriptions=None,
            service_codes=None,
            usage_types=None,
            operations=None,
            filters=None,
            next_token=None,
            max_results=None,
            max_pages=None,
        )

        # The small-response shape is unchanged by the offload gate.
        assert result['data']['searchResults'] == offerings
        assert result['data']['pagination'] == PAGINATION_COMPLETE
        assert 'data_stored' not in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.convert_response_if_needed'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_large_result_is_offloaded_to_sql(
        self, mock_paginate, mock_convert, mock_context, mock_sp_client
    ):
        """A large offerings result is offloaded to session SQL instead of inline."""
        offerings = mock_sp_client.describe_savings_plans_offerings.return_value['searchResults']
        mock_paginate.return_value = (offerings, PAGINATION_COMPLETE)
        mock_convert.return_value = {
            'data_stored': True,
            'table_name': 'sp_explorer_describe_savings_plans_offerings_abcd1234',
            'row_count': 1,
        }

        result = await describe_savings_plans_offerings(
            mock_context,
            mock_sp_client,
            offering_ids=None,
            payment_options=None,
            product_type=None,
            plan_types=None,
            durations=None,
            currencies=None,
            descriptions=None,
            service_codes=None,
            usage_types=None,
            operations=None,
            filters=None,
            next_token=None,
            max_results=None,
            max_pages=None,
        )

        assert result['status'] == 'success'
        assert result['data']['data_stored'] is True
        assert 'table_name' in result['data']
        assert 'searchResults' not in result['data']

        mock_convert.assert_called_once()
        call_args = mock_convert.call_args[0]
        # The inline shape is handed to the offloader, and the api_name routes it
        # to the per-row 'records' converter registered in sql_utils.
        assert call_args[1] == {'searchResults': offerings, 'pagination': PAGINATION_COMPLETE}
        assert call_args[2] == 'sp_explorer_describe_savings_plans_offerings'
        # Pagination is passed explicitly so has_more/next_token survive the
        # offload and reach the stored-table sentinel.
        assert mock_convert.call_args[1]['pagination'] == PAGINATION_COMPLETE

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_large_result_offload_real_path_stores_rows_and_pagination(
        self, mock_paginate, mock_get_conn, mock_context, mock_sp_client
    ):
        """The unpatched offload path stores one row per offering and keeps pagination.

        Runs convert_response_if_needed for real (threshold lowered to force the
        offload) so the nested offering items land in a session-SQL table and the
        has_more/next_token markers survive on the sentinel via the explicit
        pagination kwarg from the fix.
        """
        offerings = [
            {
                'offeringId': f'005305de-{i}',
                'productTypes': ['EC2'],
                'planType': 'Compute',
                'description': '1 year No Upfront Compute Savings Plan',
                'paymentOption': 'No Upfront',
                'durationSeconds': 31536000,
                'currency': 'USD',
                'serviceCode': 'AmazonEC2',
                'usageType': 'APN1-DedicatedUsage:c6i.large',
                'operation': 'RunInstances',
                'properties': [{'name': 'region', 'value': 'ap-northeast-1'}],
            }
            for i in range(3)
        ]
        mock_paginate.return_value = (offerings, PAGINATION_MORE)

        conn = _in_memory_session_db()
        mock_get_conn.return_value = (conn, conn.cursor())

        # Threshold lowered to 0 so the real convert_response_if_needed path runs
        # instead of returning the small result inline.
        with patch.object(sql_utils, 'SQL_CONVERSION_THRESHOLD', 0):
            result = await describe_savings_plans_offerings(
                mock_context,
                mock_sp_client,
                offering_ids=None,
                payment_options=None,
                product_type=None,
                plan_types=None,
                durations=None,
                currencies=None,
                descriptions=None,
                service_codes=None,
                usage_types=None,
                operations=None,
                filters=None,
                next_token=None,
                max_results=None,
                max_pages=None,
            )

        data = result['data']
        assert result['status'] == 'success'
        # The nested offering items were stored one row each, not returned inline.
        assert data['data_stored'] is True
        assert data['table_name'].startswith('sp_explorer_describe_savings_plans_offerings_')
        assert data['row_count'] == len(offerings)
        assert 'searchResults' not in data
        # has_more/next_token survive the offload on the sentinel.
        assert data['pagination']['has_more'] is True
        assert data['pagination']['next_token'] == 'next-page-token'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_savings_plans_vocabulary_passes_through_unchanged(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Payment options keep their spaces, plan types have no _SP, terms are seconds."""
        mock_paginate.return_value = ([], PAGINATION_COMPLETE)

        await describe_savings_plans_offerings(
            mock_context,
            mock_sp_client,
            ['005305de'],
            ['No Upfront', 'All Upfront'],
            'EC2',
            ['Compute', 'EC2Instance'],
            [31536000, 94608000],
            ['USD'],
            ['1 year No Upfront Compute Savings Plan'],
            ['AmazonEC2'],
            ['APN1-DedicatedUsage:c6i.large'],
            ['RunInstances'],
            [{'name': 'instanceFamily', 'values': ['c6i']}],
            'resume-here',
            10,
            None,
        )

        request_params = mock_paginate.call_args[1]['request_params']
        assert request_params['nextToken'] == 'resume-here'
        assert request_params['paymentOptions'] == ['No Upfront', 'All Upfront']
        assert request_params['planTypes'] == ['Compute', 'EC2Instance']
        assert request_params['durations'] == [31536000, 94608000]
        assert request_params['currencies'] == ['USD']
        assert request_params['serviceCodes'] == ['AmazonEC2']
        assert request_params['offeringIds'] == ['005305de']
        assert request_params['usageTypes'] == ['APN1-DedicatedUsage:c6i.large']
        assert request_params['operations'] == ['RunInstances']
        assert request_params['filters'] == [{'name': 'instanceFamily', 'values': ['c6i']}]
        # productType is the one scalar in this operation; the rates operation takes a
        # list called products instead.
        assert request_params['productType'] == 'EC2'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_error(self, mock_paginate, mock_context, mock_sp_client):
        """A client failure is reported rather than raised."""
        mock_paginate.side_effect = Exception('ValidationException')

        result = await describe_savings_plans_offerings(
            mock_context,
            mock_sp_client,
            offering_ids=None,
            payment_options=None,
            product_type=None,
            plan_types=None,
            durations=None,
            currencies=None,
            descriptions=None,
            service_codes=None,
            usage_types=None,
            operations=None,
            filters=None,
            next_token=None,
            max_results=None,
            max_pages=None,
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestDescribeSavingsPlansOfferingRates:
    """Tests for describe_savings_plans_offering_rates."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_basic(self, mock_paginate, mock_context, mock_sp_client):
        """Offering rates page through searchResults."""
        rates = mock_sp_client.describe_savings_plans_offering_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, PAGINATION_COMPLETE)

        result = await describe_savings_plans_offering_rates(
            mock_context,
            mock_sp_client,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs['operation_name'] == 'DescribeSavingsPlansOfferingRates'
        assert call_kwargs['result_key'] == 'searchResults'
        assert result['data']['searchResults'] == rates

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_small_result_is_returned_inline(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Below the SQL threshold, offering rates stay inline with no offload."""
        rates = mock_sp_client.describe_savings_plans_offering_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, PAGINATION_COMPLETE)

        result = await describe_savings_plans_offering_rates(
            mock_context,
            mock_sp_client,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        # The small-response shape is unchanged by the offload gate.
        assert result['data']['searchResults'] == rates
        assert result['data']['pagination'] == PAGINATION_COMPLETE
        assert 'data_stored' not in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.convert_response_if_needed'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_large_result_is_offloaded_to_sql(
        self, mock_paginate, mock_convert, mock_context, mock_sp_client
    ):
        """A large offering-rate result is offloaded to session SQL instead of inline."""
        rates = mock_sp_client.describe_savings_plans_offering_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, PAGINATION_COMPLETE)
        mock_convert.return_value = {
            'data_stored': True,
            'table_name': 'sp_explorer_describe_savings_plans_offering_rates_abcd1234',
            'row_count': 1,
        }

        result = await describe_savings_plans_offering_rates(
            mock_context,
            mock_sp_client,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        assert result['status'] == 'success'
        assert result['data']['data_stored'] is True
        assert 'table_name' in result['data']
        assert 'searchResults' not in result['data']

        mock_convert.assert_called_once()
        call_args = mock_convert.call_args[0]
        # The inline shape is handed to the offloader, and the api_name routes it
        # to the per-row 'records' converter registered in sql_utils.
        assert call_args[1] == {'searchResults': rates, 'pagination': PAGINATION_COMPLETE}
        assert call_args[2] == 'sp_explorer_describe_savings_plans_offering_rates'
        # Pagination is passed explicitly so has_more/next_token survive the
        # offload and reach the stored-table sentinel.
        assert mock_convert.call_args[1]['pagination'] == PAGINATION_COMPLETE

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_large_result_offload_real_path_stores_rows_and_pagination(
        self, mock_paginate, mock_get_conn, mock_context, mock_sp_client
    ):
        """The unpatched offload path stores one row per rate and keeps pagination.

        Runs convert_response_if_needed for real (threshold lowered to force the
        offload) so the nested rate items (each with a savingsPlanOffering dict and
        a properties list) land in a session-SQL table and the has_more/next_token
        markers survive on the sentinel via the explicit pagination kwarg from the fix.
        """
        rates = [
            {
                'savingsPlanOffering': {
                    'offeringId': f'005305de-{i}',
                    'paymentOption': 'No Upfront',
                    'planType': 'Compute',
                    'durationSeconds': 31536000,
                    'currency': 'USD',
                    'planDescription': '1 year No Upfront Compute Savings Plan',
                },
                'rate': '0.0464',
                'unit': 'Hrs',
                'productType': 'EC2',
                'serviceCode': 'AmazonEC2',
                'usageType': 'APN1-DedicatedUsage:c6i.large',
                'operation': 'RunInstances',
                'properties': [{'name': 'instanceType', 'value': 'c6i.large'}],
            }
            for i in range(3)
        ]
        mock_paginate.return_value = (rates, PAGINATION_MORE)

        conn = _in_memory_session_db()
        mock_get_conn.return_value = (conn, conn.cursor())

        # Threshold lowered to 0 so the real convert_response_if_needed path runs
        # instead of returning the small result inline.
        with patch.object(sql_utils, 'SQL_CONVERSION_THRESHOLD', 0):
            result = await describe_savings_plans_offering_rates(
                mock_context,
                mock_sp_client,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )

        data = result['data']
        assert result['status'] == 'success'
        # The nested rate items were stored one row each, not returned inline.
        assert data['data_stored'] is True
        assert data['table_name'].startswith('sp_explorer_describe_savings_plans_offering_rates_')
        assert data['row_count'] == len(rates)
        assert 'searchResults' not in data
        # has_more/next_token survive the offload on the sentinel.
        assert data['pagination']['has_more'] is True
        assert data['pagination']['next_token'] == 'next-page-token'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_shared_parameters_map_to_the_prefixed_api_fields(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """The tool's shared parameter names land on this API's prefixed field names."""
        mock_paginate.return_value = ([], PAGINATION_COMPLETE)

        await describe_savings_plans_offering_rates(
            mock_context,
            mock_sp_client,
            ['005305de'],
            ['No Upfront'],
            ['Compute'],
            ['EC2', 'Lambda'],
            ['AmazonEC2'],
            ['APN1-DedicatedUsage:c6i.large'],
            ['RunInstances'],
            [{'name': 'instanceType', 'values': ['c6i.large']}],
            'resume-here',
            20,
            None,
        )

        request_params = mock_paginate.call_args[1]['request_params']
        assert request_params['nextToken'] == 'resume-here'
        assert request_params['savingsPlanOfferingIds'] == ['005305de']
        assert request_params['savingsPlanPaymentOptions'] == ['No Upfront']
        assert request_params['savingsPlanTypes'] == ['Compute']
        assert request_params['products'] == ['EC2', 'Lambda']
        assert request_params['serviceCodes'] == ['AmazonEC2']
        assert request_params['maxResults'] == 20

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_response'
    )
    async def test_error(self, mock_paginate, mock_context, mock_sp_client):
        """A client failure is reported rather than raised."""
        mock_paginate.side_effect = Exception('ValidationException')

        result = await describe_savings_plans_offering_rates(
            mock_context,
            mock_sp_client,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestSpExplorerDispatch:
    """Tests for the sp_explorer dispatcher."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.create_aws_client')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.describe_savings_plans'
    )
    async def test_routes_to_describe_savings_plans(
        self, mock_impl, mock_create_client, mock_context
    ):
        """describe_savings_plans receives the inventory parameters."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        result = await sp_explorer(
            mock_context,
            operation='describe_savings_plans',
            states=['active'],
            max_pages=2,
        )

        assert result['status'] == 'success'
        # The Savings Plans service is a separate client from Cost Explorer, and it
        # has to be on create_aws_client's allowlist to be built at all.
        mock_create_client.assert_called_once_with('savingsplans', region_name='us-east-1')
        args = mock_impl.await_args[0]
        assert args[4] == ['active']
        assert args[8] == 2

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.create_aws_client')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.describe_savings_plan_rates'
    )
    async def test_routes_to_describe_savings_plan_rates(
        self, mock_impl, mock_create_client, mock_context
    ):
        """describe_savings_plan_rates receives the plan id."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_explorer(
            mock_context,
            operation='describe_savings_plan_rates',
            savings_plan_id='577d4a65',
        )

        assert mock_impl.await_args[0][2] == '577d4a65'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.create_aws_client')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.describe_savings_plans_offerings'
    )
    async def test_routes_to_describe_savings_plans_offerings(
        self, mock_impl, mock_create_client, mock_context
    ):
        """describe_savings_plans_offerings receives the offering filters."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_explorer(
            mock_context,
            operation='describe_savings_plans_offerings',
            product_type='Lambda',
            payment_options=['No Upfront'],
            plan_types=['Compute'],
        )

        args = mock_impl.await_args[0]
        assert args[3] == ['No Upfront']
        assert args[4] == 'Lambda'
        assert args[5] == ['Compute']

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.create_aws_client')
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.describe_savings_plans_offering_rates'
    )
    async def test_routes_to_describe_savings_plans_offering_rates(
        self, mock_impl, mock_create_client, mock_context
    ):
        """describe_savings_plans_offering_rates receives the rate filters."""
        mock_impl.return_value = {'status': 'success', 'data': {}}

        await sp_explorer(
            mock_context,
            operation='describe_savings_plans_offering_rates',
            usage_types=['APN1-DedicatedUsage:c6i.large'],
            payment_options=['No Upfront'],
            plan_types=['Compute'],
        )

        args = mock_impl.await_args[0]
        assert args[3] == ['No Upfront']
        assert args[4] == ['Compute']
        assert args[7] == ['APN1-DedicatedUsage:c6i.large']

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.create_aws_client')
    async def test_unsupported_operation_lists_the_valid_ones(
        self, mock_create_client, mock_context
    ):
        """An unknown operation names the four that exist."""
        result = await sp_explorer(mock_context, operation='list_tags_for_resource')

        assert result['status'] == 'error'
        message = result['message']
        assert 'describe_savings_plans' in message
        assert 'describe_savings_plan_rates' in message
        assert 'describe_savings_plans_offerings' in message
        assert 'describe_savings_plans_offering_rates' in message

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.create_aws_client')
    async def test_client_creation_failure_is_reported(self, mock_create_client, mock_context):
        """A service that is not on the allowlist surfaces as an error, not a crash."""
        mock_create_client.side_effect = ValueError("Service 'savingsplans' is not allowed")

        result = await sp_explorer(mock_context, operation='describe_savings_plans')

        assert result['status'] == 'error'


def test_sp_explorer_server_initialization():
    """The server is named and carries instructions."""
    assert sp_explorer_server.name == 'sp-explorer-tools'
    assert sp_explorer_server.instructions is not None
