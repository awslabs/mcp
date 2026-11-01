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

import fastmcp
import pytest
import re
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
from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
    partial_data_warning,
)
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
    'has_more': False,
    'next_token': None,
    'items_returned': 1,
}


PAGINATION_MORE = {
    'complete_dataset': False,
    'has_more': True,
    'next_token': 'next-page-token',
    'items_returned': 3,
    'warning': partial_data_warning(3),
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

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_basic(self, mock_paginate, mock_context, mock_sp_client, sample_savings_plan):
        """Inventory comes back under the API's own key, with pagination metadata."""
        mock_paginate.return_value = ([sample_savings_plan], [], PAGINATION_COMPLETE)

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None
        )

        call_args = mock_paginate.call_args[0]
        assert call_args[1] == 'DescribeSavingsPlans'
        assert call_args[4].result_key == 'savingsPlans'
        # The Savings Plans service uses a lowercase token; Cost Explorer does not.
        assert call_args[4].token_param == 'nextToken'
        assert call_args[4].token_key_in_response == 'nextToken'
        assert call_args[3] == {}

        assert result['status'] == 'success'
        assert result['data']['savingsPlans'] == [sample_savings_plan]
        assert result['data']['pagination']['complete_dataset'] is True

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_states_and_filters_are_json_decoded(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """List parameters are passed through to boto3 unchanged."""
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)

        await describe_savings_plans(
            mock_context,
            mock_sp_client,
            ['arn:aws:savingsplans::123456789012:savingsplan/abc'],
            ['577d4a65'],
            ['active', 'queued', 'payment-failed'],
            [{'name': 'savings-plan-type', 'values': ['Compute']}],
            50,
            'token-from-caller',
        )

        request_params = mock_paginate.call_args[0][3]
        assert request_params['states'] == ['active', 'queued', 'payment-failed']
        assert request_params['savingsPlanIds'] == ['577d4a65']
        assert request_params['savingsPlanArns'] == [
            'arn:aws:savingsplans::123456789012:savingsplan/abc'
        ]
        assert request_params['filters'] == [{'name': 'savings-plan-type', 'values': ['Compute']}]
        # The token and page size are the helper's to set, so request_params stays
        # identical across a continuation.
        assert 'nextToken' not in request_params
        assert 'maxResults' not in request_params
        assert mock_paginate.call_args[1] == {'max_items': 50, 'next_token': 'token-from-caller'}

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_small_result_is_returned_inline(
        self, mock_paginate, mock_context, mock_sp_client, sample_savings_plan
    ):
        """Below the SQL threshold, inventory stays inline with no offload."""
        mock_paginate.return_value = ([sample_savings_plan], [], PAGINATION_COMPLETE)

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None
        )

        # The small-response shape is unchanged by the offload gate.
        assert result['data']['savingsPlans'] == [sample_savings_plan]
        assert result['data']['pagination'] == PAGINATION_COMPLETE
        assert 'data_stored' not in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.convert_response_if_needed'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_large_result_is_offloaded_to_sql(
        self, mock_paginate, mock_convert, mock_context, mock_sp_client, sample_savings_plan
    ):
        """A large inventory is offloaded to session SQL instead of inline."""
        plans = [sample_savings_plan]
        mock_paginate.return_value = (plans, [], PAGINATION_COMPLETE)
        mock_convert.return_value = {
            'data_stored': True,
            'table_name': 'sp_explorer_describe_savings_plans_abcd1234',
            'row_count': 1,
        }

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None
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

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection')
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_large_result_offload_real_path_stores_rows_and_pagination(
        self, mock_paginate, mock_get_conn, mock_context, mock_sp_client
    ):
        """The unpatched offload path stores one row per plan and keeps pagination.

        Runs convert_response_if_needed for real (threshold lowered to force the
        offload) so the plan items (each with a productTypes list and a tags dict)
        land in a session-SQL table and the has_more/next_token markers survive on
        the sentinel via the derived pagination envelope.
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
        mock_paginate.return_value = (plans, [], PAGINATION_MORE)

        conn = _in_memory_session_db()
        mock_get_conn.return_value = (conn, conn.cursor())

        # Threshold lowered to 0 so the real convert_response_if_needed path runs
        # instead of returning the small result inline.
        with patch.object(sql_utils, 'SQL_CONVERSION_THRESHOLD', 0):
            result = await describe_savings_plans(
                mock_context, mock_sp_client, None, None, None, None, None, None
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

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_error(self, mock_paginate, mock_context, mock_sp_client):
        """A client failure is reported rather than raised."""
        mock_paginate.side_effect = Exception('AccessDeniedException')

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestDescribeSavingsPlanRates:
    """Tests for describe_savings_plan_rates."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_basic(self, mock_paginate, mock_context, mock_sp_client):
        """Rates page through searchResults and keep the plan id on the result."""
        rates = mock_sp_client.describe_savings_plan_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, [], PAGINATION_COMPLETE)

        result = await describe_savings_plan_rates(
            mock_context, mock_sp_client, '577d4a65', None, None, None
        )

        call_args = mock_paginate.call_args[0]
        assert call_args[1] == 'DescribeSavingsPlanRates'
        assert call_args[4].result_key == 'searchResults'
        assert call_args[4].token_param == 'nextToken'
        assert call_args[3]['savingsPlanId'] == '577d4a65'

        # Each page echoes savingsPlanId at the top level; the merged result has to
        # carry it too, or the rates lose the plan they belong to.
        assert result['data']['savingsPlanId'] == '577d4a65'
        assert result['data']['searchResults'] == rates

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_with_filters(self, mock_paginate, mock_context, mock_sp_client):
        """This operation's filter names are camelCase, unlike describe_savings_plans."""
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)

        await describe_savings_plan_rates(
            mock_context,
            mock_sp_client,
            '577d4a65',
            [{'name': 'instanceType', 'values': ['c6i.large']}],
            5,
            'resume-here',
        )

        request_params = mock_paginate.call_args[0][3]
        assert request_params['filters'] == [{'name': 'instanceType', 'values': ['c6i.large']}]
        assert 'maxResults' not in request_params
        assert mock_paginate.call_args[1] == {'max_items': 5, 'next_token': 'resume-here'}

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_small_result_is_returned_inline(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Below the SQL threshold, rates stay inline with the plan id and no offload."""
        rates = mock_sp_client.describe_savings_plan_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, [], PAGINATION_COMPLETE)

        result = await describe_savings_plan_rates(
            mock_context, mock_sp_client, '577d4a65', None, None, None
        )

        # The small-response shape is unchanged by the offload gate.
        assert result['data']['savingsPlanId'] == '577d4a65'
        assert result['data']['searchResults'] == rates
        assert result['data']['pagination'] == PAGINATION_COMPLETE
        assert 'data_stored' not in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.convert_response_if_needed'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_large_result_is_offloaded_to_sql(
        self, mock_paginate, mock_convert, mock_context, mock_sp_client
    ):
        """A large rate list is offloaded to session SQL instead of inline."""
        rates = mock_sp_client.describe_savings_plan_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, [], PAGINATION_COMPLETE)
        mock_convert.return_value = {
            'data_stored': True,
            'table_name': 'sp_explorer_describe_savings_plan_rates_abcd1234',
            'row_count': 1,
            'savingsPlanId': '577d4a65',
        }

        result = await describe_savings_plan_rates(
            mock_context, mock_sp_client, '577d4a65', None, None, None
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
        assert mock_convert.call_args[1]['savingsPlanId'] == '577d4a65'

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection')
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
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
        mock_paginate.return_value = (rates, [], PAGINATION_MORE)

        conn = _in_memory_session_db()
        mock_get_conn.return_value = (conn, conn.cursor())

        # Threshold lowered to 0 so the real convert_response_if_needed path runs
        # instead of returning the small result inline.
        with patch.object(sql_utils, 'SQL_CONVERSION_THRESHOLD', 0):
            result = await describe_savings_plan_rates(
                mock_context, mock_sp_client, '9355d9d7', None, None, None
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

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_error(self, mock_paginate, mock_context, mock_sp_client):
        """A client failure is reported rather than raised."""
        mock_paginate.side_effect = Exception('ResourceNotFoundException')

        result = await describe_savings_plan_rates(
            mock_context, mock_sp_client, 'missing', None, None, None
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestDescribeSavingsPlansOfferings:
    """Tests for describe_savings_plans_offerings."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_basic(self, mock_paginate, mock_context, mock_sp_client):
        """Offerings page through searchResults."""
        offerings = mock_sp_client.describe_savings_plans_offerings.return_value['searchResults']
        mock_paginate.return_value = (offerings, [], PAGINATION_COMPLETE)

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
            max_items=None,
            next_token=None,
        )

        call_args = mock_paginate.call_args[0]
        assert call_args[1] == 'DescribeSavingsPlansOfferings'
        assert call_args[4].result_key == 'searchResults'
        assert result['data']['searchResults'] == offerings

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_small_result_is_returned_inline(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Below the SQL threshold, offerings stay inline with no offload."""
        offerings = mock_sp_client.describe_savings_plans_offerings.return_value['searchResults']
        mock_paginate.return_value = (offerings, [], PAGINATION_COMPLETE)

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
            max_items=None,
            next_token=None,
        )

        # The small-response shape is unchanged by the offload gate.
        assert result['data']['searchResults'] == offerings
        assert result['data']['pagination'] == PAGINATION_COMPLETE
        assert 'data_stored' not in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.convert_response_if_needed'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_large_result_is_offloaded_to_sql(
        self, mock_paginate, mock_convert, mock_context, mock_sp_client
    ):
        """A large offerings result is offloaded to session SQL instead of inline."""
        offerings = mock_sp_client.describe_savings_plans_offerings.return_value['searchResults']
        mock_paginate.return_value = (offerings, [], PAGINATION_COMPLETE)
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
            max_items=None,
            next_token=None,
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

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection')
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
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
        mock_paginate.return_value = (offerings, [], PAGINATION_MORE)

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
                max_items=None,
                next_token=None,
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

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_savings_plans_vocabulary_passes_through_unchanged(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Payment options keep their spaces, plan types have no _SP, terms are seconds."""
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)

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
            10,
            'resume-here',
        )

        request_params = mock_paginate.call_args[0][3]
        assert mock_paginate.call_args[1] == {'max_items': 10, 'next_token': 'resume-here'}
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

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
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
            max_items=None,
            next_token=None,
        )

        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestDescribeSavingsPlansOfferingRates:
    """Tests for describe_savings_plans_offering_rates."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_basic(self, mock_paginate, mock_context, mock_sp_client):
        """Offering rates page through searchResults."""
        rates = mock_sp_client.describe_savings_plans_offering_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, [], PAGINATION_COMPLETE)

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
        )

        call_args = mock_paginate.call_args[0]
        assert call_args[1] == 'DescribeSavingsPlansOfferingRates'
        assert call_args[4].result_key == 'searchResults'
        assert result['data']['searchResults'] == rates

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_small_result_is_returned_inline(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Below the SQL threshold, offering rates stay inline with no offload."""
        rates = mock_sp_client.describe_savings_plans_offering_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, [], PAGINATION_COMPLETE)

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
        )

        # The small-response shape is unchanged by the offload gate.
        assert result['data']['searchResults'] == rates
        assert result['data']['pagination'] == PAGINATION_COMPLETE
        assert 'data_stored' not in result['data']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.convert_response_if_needed'
    )
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_large_result_is_offloaded_to_sql(
        self, mock_paginate, mock_convert, mock_context, mock_sp_client
    ):
        """A large offering-rate result is offloaded to session SQL instead of inline."""
        rates = mock_sp_client.describe_savings_plans_offering_rates.return_value['searchResults']
        mock_paginate.return_value = (rates, [], PAGINATION_COMPLETE)
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

    @patch('awslabs.billing_cost_management_mcp_server.utilities.sql_utils.get_db_connection')
    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_large_result_offload_real_path_stores_rows_and_pagination(
        self, mock_paginate, mock_get_conn, mock_context, mock_sp_client
    ):
        """The unpatched offload path stores one row per rate and keeps pagination.

        Runs convert_response_if_needed for real (threshold lowered to force the
        offload) so the nested rate items (each with a savingsPlanOffering dict and
        a properties list) land in a session-SQL table and the has_more/next_token
        markers survive on the sentinel via the derived pagination envelope.
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
        mock_paginate.return_value = (rates, [], PAGINATION_MORE)

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

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_shared_parameters_map_to_the_prefixed_api_fields(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """The tool's shared parameter names land on this API's prefixed field names."""
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)

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
            20,
            'resume-here',
        )

        request_params = mock_paginate.call_args[0][3]
        assert mock_paginate.call_args[1] == {'max_items': 20, 'next_token': 'resume-here'}
        assert request_params['savingsPlanOfferingIds'] == ['005305de']
        assert request_params['savingsPlanPaymentOptions'] == ['No Upfront']
        assert request_params['savingsPlanTypes'] == ['Compute']
        assert request_params['products'] == ['EC2', 'Lambda']
        assert request_params['serviceCodes'] == ['AmazonEC2']
        assert 'maxResults' not in request_params

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
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
            max_items=2,
        )

        assert result['status'] == 'success'
        # The Savings Plans service is a separate client from Cost Explorer, and it
        # has to be on create_aws_client's allowlist to be built at all.
        mock_create_client.assert_called_once_with('savingsplans', region_name='us-east-1')
        args = mock_impl.await_args[0]
        assert args[4] == ['active']
        assert args[6] == 2

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


# The four operations, as (operation, boto3 method, result key, extra tool arguments).
PAGED_OPERATIONS = [
    ('describe_savings_plans', 'describe_savings_plans', 'savingsPlans', {}),
    (
        'describe_savings_plan_rates',
        'describe_savings_plan_rates',
        'searchResults',
        {'savings_plan_id': '577d4a65'},
    ),
    ('describe_savings_plans_offerings', 'describe_savings_plans_offerings', 'searchResults', {}),
    (
        'describe_savings_plans_offering_rates',
        'describe_savings_plans_offering_rates',
        'searchResults',
        {},
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize('operation,method,result_key,extra', PAGED_OPERATIONS)
class TestSpExplorerPagination:
    """The real pagination helper drives every operation through the tool."""

    async def _run(self, mock_context, client, operation, extra, **kwargs):
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.create_aws_client',
            return_value=client,
        ):
            return await sp_explorer(mock_context, operation=operation, **extra, **kwargs)

    async def test_no_max_items_fetches_every_page(
        self, mock_context, operation, method, result_key, extra
    ):
        """Without max_items every page is fetched at the largest page size."""
        client = MagicMock()
        getattr(client, method).side_effect = [
            {result_key: [{'id': 1}, {'id': 2}], 'nextToken': 't1'},
            {result_key: [{'id': 3}]},
        ]

        result = await self._run(mock_context, client, operation, extra)

        data = result['data']
        assert result['status'] == 'success'
        assert data[result_key] == [{'id': 1}, {'id': 2}, {'id': 3}]
        assert 'complete_dataset' not in data
        assert data['pagination'] == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 3,
        }
        calls = getattr(client, method).call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs['maxResults'] == 1000
        assert 'nextToken' not in calls[0].kwargs
        assert calls[1].kwargs['nextToken'] == 't1'

    async def test_max_items_stops_before_exceeding_it(
        self, mock_context, operation, method, result_key, extra
    ):
        """max_items sizes the page and stops once it is reached, returning the token."""
        client = MagicMock()
        getattr(client, method).return_value = {
            result_key: [{'id': 1}, {'id': 2}],
            'nextToken': 'more',
        }

        result = await self._run(mock_context, client, operation, extra, max_items=2)

        data = result['data']
        assert data['complete_dataset'] is False
        assert 'Partial data' in data['warning']
        assert data['pagination']['next_token'] == 'more'
        assert data['pagination']['items_returned'] == 2
        getattr(client, method).assert_called_once()
        assert getattr(client, method).call_args.kwargs['maxResults'] == 2

    async def test_continuation_sends_caller_token_and_identical_params(
        self, mock_context, operation, method, result_key, extra
    ):
        """A continuation repeats the first call's parameters plus the caller's token."""
        client = MagicMock()
        getattr(client, method).return_value = {result_key: []}

        await self._run(mock_context, client, operation, extra, filters=[{'name': 'region'}])
        first = dict(getattr(client, method).call_args.kwargs)
        await self._run(
            mock_context,
            client,
            operation,
            extra,
            filters=[{'name': 'region'}],
            next_token='caller-token',
        )
        second = dict(getattr(client, method).call_args.kwargs)

        assert second.pop('nextToken') == 'caller-token'
        assert second == first


@pytest.mark.asyncio
class TestDescribeSavingsPlansScope:
    """DescribeSavingsPlans is scoped to the calling account, and the tool says so.

    From a management account whose plans were bought in member accounts the API
    returns none of them, even when asked for by id or ARN, and its response shape
    carries no owner field to say otherwise. A caller that reads the empty list as
    "owns none" sizes a fresh commitment over usage existing plans already cover,
    so the scope has to be stated where the caller will see it.
    """

    @staticmethod
    async def _description() -> str:
        """The sp-explorer description as published to MCP clients."""
        async with fastmcp.Client(sp_explorer_server) as client:
            tools = await client.list_tools()
        description = next(t for t in tools if t.name == 'sp-explorer').description
        assert description is not None, 'sp-explorer is served with no description'
        return description

    async def test_description_states_calling_account_scope(self):
        """The scope is named: the calling account only, management account included."""
        description = await self._description()

        assert 'The plans the account owns' not in description
        assert re.search(r'calling account only', description, re.I)
        assert re.search(r'management account', description, re.I)

    async def test_description_points_to_org_wide_sources(self):
        """The org-wide alternatives are named, with the owner read from the ARN."""
        description = await self._description()

        assert 'get_savings_plans_utilization_details' in description
        assert 'SAVINGS_PLAN_ARN' in description
        assert 'SAVINGS_PLANS' in description
        assert re.search(r"ARN'?s? account", description, re.I)

    async def test_description_states_the_window_the_org_wide_source_needs(self):
        """Both alternatives read Cost Explorer, which defaults to 30 days.

        get_savings_plans_utilization_details resolves its window through
        get_date_range, whose default is 30 days ago, and Cost Explorer lists a plan
        only where it has utilization records inside the window. Pointing a caller
        there without saying so swaps one silent under-report for a narrower one: a
        retired or currently idle member-owned plan still displaces a new purchase.
        """
        description = await self._description()

        assert re.search(r'12-month', description, re.I)
        assert re.search(r'start_date and end_date', description)

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_member_owned_plan_ids_return_empty_success_not_error(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Member-owned ids are passed through, and the empty result is a success.

        Pins the live passthrough: the ids reach boto3 unchanged and the empty list
        is not turned into an error, so nothing downstream has to special-case it.
        """
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)
        member_plan = '11111111-2222-4333-8444-555555555555'

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, [member_plan], None, None, None, None
        )

        assert mock_paginate.call_args[0][3] == {'savingsPlanIds': [member_plan]}
        assert result['status'] == 'success'
        assert result['data']['savingsPlans'] == []
        assert result['data']['pagination'] == PAGINATION_COMPLETE

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_empty_inventory_explains_the_scope_in_the_result(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """An empty result carries the scope, as sp-performance's empty results do.

        The description only helps a caller that re-reads it. This puts the same
        statement in the response a caller consumes at runtime.
        """
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None
        )

        message = result['data']['message']
        assert re.search(r'calling account', message, re.I)
        assert re.search(r'does not mean the organization owns none', message, re.I)
        assert 'get_savings_plans_utilization_details' in message
        assert 'SAVINGS_PLAN_ARN' in message

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_a_non_empty_inventory_carries_no_message(
        self, mock_paginate, mock_context, mock_sp_client, sample_savings_plan
    ):
        """The message is the empty case only; a populated result keeps its shape."""
        mock_paginate.return_value = ([sample_savings_plan], [], PAGINATION_COMPLETE)

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None
        )

        assert 'message' not in result['data']


@pytest.mark.asyncio
class TestDescribeSavingsPlansFilterValues:
    """A filter or state value spelled differently from the API's matches nothing.

    DescribeSavingsPlans returns an empty list, not a ValidationException, for an
    enum value such as savings-plan-type ComputeSavingsPlans or payment-option
    PARTIAL_UPFRONT. The served filters description has to give the accepted
    values, and the empty result has to name a filter mismatch as a cause, or the
    caller reads the account-scope text and concludes the account owns no plans.
    """

    @staticmethod
    async def _filters_description() -> str:
        """The filters parameter description as published to MCP clients."""
        async with fastmcp.Client(sp_explorer_server) as client:
            tools = await client.list_tools()
        tool = next(t for t in tools if t.name == 'sp-explorer')
        description = tool.input_schema['properties']['filters'].get('description')
        assert description, 'filters is served with no description'
        return description

    async def test_filters_description_gives_describe_savings_plans_value_formats(self):
        """Each describe_savings_plans filter name is served with its value format."""
        description = ' '.join((await self._filters_description()).split())

        assert re.search(r'case-sensitive', description, re.I)
        assert re.search(r'empty list, not an error', description)
        for value in ('Compute', 'EC2Instance', 'SageMaker', 'Database'):
            assert value in description
        for value in ("'All Upfront'", "'Partial Upfront'", "'No Upfront'"):
            assert value in description
        assert re.search(r'are strings, numbers included', description)
        assert re.search(r'term is the duration in seconds as a string, "31536000"', description)
        assert re.search(r'decimal strings such as "4.38", with no currency sign', description)
        assert '"2025-01-01T00:00:00.000Z"' in description
        assert re.search(r'matched to the millisecond', description)

    async def test_filters_description_gives_rate_pricing_vocabulary(self):
        """Rate filters take pricing values; Cost Explorer's spellings match nothing.

        DescribeSavingsPlanRates and DescribeSavingsPlansOfferingRates return an
        empty list for tenancy Shared or productDescription Linux, the values a
        caller carries over from Cost Explorer.
        """
        description = ' '.join((await self._filters_description()).split())

        assert re.search(r'rate operations use the pricing vocabulary', description)
        assert re.search(r'tenancy is lower case, shared or dedicated', description)
        assert re.search(r"Cost Explorer's Shared matches nothing", description)
        assert 'Linux/UNIX' in description
        assert re.search(r'Linux alone matches nothing', description)

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_empty_filtered_result_names_a_filter_mismatch(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """With filters passed, the message names a mismatch and keeps the scope text."""
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)
        filters = [{'name': 'savings-plan-type', 'values': ['ComputeSavingsPlans']}]

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, filters, None, None
        )

        message = result['data']['message']
        assert re.search(r'narrowed by filters', message)
        assert re.search(r'case-sensitive', message)
        assert "payment-option 'Partial Upfront'" in message
        assert re.search(r'does not mean the organization owns none', message, re.I)
        assert result['status'] == 'success'

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_empty_result_with_only_states_has_no_filter_note(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """The API rejects a misspelled state, so an empty states-only result is real."""
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, ['queued'], None, None, None
        )

        assert 'narrowed by filters' not in result['data']['message']

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_empty_unfiltered_result_has_no_filter_note(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Without filters or states only the account scope can explain the empty list."""
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)

        result = await describe_savings_plans(
            mock_context, mock_sp_client, None, None, None, None, None, None
        )

        message = result['data']['message']
        assert 'narrowed by filters' not in message
        assert message.startswith('No Savings Plans found for the calling account. This')


@pytest.mark.asyncio
class TestDescribeSavingsPlanRatesRequiredParameter:
    """savingsPlanId is required, so an unset one is omitted rather than sent as None."""

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_unset_savings_plan_id_is_omitted(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """Botocore names a missing field; a None value it reports as a type error."""
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)

        await describe_savings_plan_rates(mock_context, mock_sp_client, None, None, None, None)

        assert 'savingsPlanId' not in mock_paginate.call_args[0][3]

    @patch('awslabs.billing_cost_management_mcp_server.tools.sp_explorer_tools.paginate_aws_items')
    async def test_a_given_savings_plan_id_is_still_sent(
        self, mock_paginate, mock_context, mock_sp_client
    ):
        """The ordinary path is unchanged."""
        mock_paginate.return_value = ([], [], PAGINATION_COMPLETE)

        await describe_savings_plan_rates(
            mock_context, mock_sp_client, '577d4a65', None, None, None
        )

        assert mock_paginate.call_args[0][3]['savingsPlanId'] == '577d4a65'


@pytest.mark.asyncio
class TestOfferingFilterVocabulary:
    """Each offering operation's arg docs give the values that operation accepts."""

    RATES = 'describe_savings_plans_offering_rates takes'

    @staticmethod
    async def _arg_doc(name: str) -> str:
        """One sp-explorer argument description as published to MCP clients."""
        async with fastmcp.Client(sp_explorer_server) as client:
            tools = await client.list_tools()
        props = next(t for t in tools if t.name == 'sp-explorer').input_schema['properties']
        return ' '.join((props[name].get('description') or '').split())

    async def test_offering_rate_filters_omit_product_id(self):
        """The offering-rate filter names are the five the service accepts."""
        doc = await self._arg_doc('filters')

        assert self.RATES in doc
        rate_filters = doc.split(self.RATES, 1)[1]
        assert 'productId' not in rate_filters
        for name in ('region', 'instanceFamily', 'instanceType', 'productDescription', 'tenancy'):
            assert name in rate_filters

    async def test_service_codes_give_offering_codes_apart_from_rate_codes(self):
        """Offering codes come before the rate operation, rate codes after it."""
        doc = await self._arg_doc('service_codes')

        assert self.RATES in doc
        offerings, rates = doc.split(self.RATES, 1)
        for code in ('ComputeSavingsPlans', 'MachineLearningSavingsPlans', 'DatabaseSavingsPlans'):
            assert code in offerings
            assert code not in rates
        assert 'EC2Instance' in offerings
        for code in ('AmazonEC2', 'AmazonRDS', 'AmazonES'):
            assert code in rates

    async def test_service_codes_say_other_offering_codes_return_empty(self):
        """On offerings an EC2-containing code fails the call; any other code returns empty."""
        offerings = (await self._arg_doc('service_codes')).split(self.RATES, 1)[0]

        assert 'Rate codes do not work there' not in offerings
        assert re.search(r'Any other value.*empty result, not an error', offerings)
        assert 'AmazonEC2 alone' not in offerings
        assert re.search(r'containing EC2 in upper or lower case', offerings)
        assert 'EC2InstanceSavingsPlans' in offerings
        assert re.search(r'fails the whole request', offerings)
        assert re.search(
            r'ValidationException whose message lists AmazonEC2 as allowed', offerings
        )
        assert re.search(r'For EC2Instance plans use ComputeSavingsPlans', offerings)

    async def test_usage_types_give_both_formats(self):
        """Offering and rate usage types are shown, region prefix and empty match included."""
        doc = await self._arg_doc('usage_types')

        for example in (
            'ComputeSP:1yrNoUpfront',
            'EC2SP:m5.1yrNoUpfront',
            'AFS1-EC2SP:c5.1yrAllUpfront',
            'BoxUsage:m5.large',
            'USW2-BoxUsage:m5.large',
        ):
            assert example in doc
        assert re.search(r'matches nothing', doc)
        assert re.search(r'empty result', doc)

    async def test_usage_types_say_some_us_east_1_rates_are_prefixed(self):
        """Some us-east-1 rate usage types carry USE1-, so a bare value is not always right."""
        doc = await self._arg_doc('usage_types')

        assert 'USE1-Fargate-GB-Hours' in doc
