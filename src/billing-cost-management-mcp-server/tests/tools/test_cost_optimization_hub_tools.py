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

"""Unit tests for the cost_optimization_hub_tools module.

These tests verify the functionality of AWS Cost Optimization Hub tools, including:
- Retrieving optimization recommendations across multiple AWS services
- Getting cost and savings estimates for recommended actions
- Handling recommendation filters by implementation effort and savings potential
- Processing recommendations for EC2, RDS, Lambda, and storage resources
- Error handling for invalid recommendation filters and hub configuration
"""

import fastmcp
import importlib
import json
import pytest
from datetime import date
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


# Create a mock implementation for testing
async def cost_optimization_hub(ctx, operation, **kwargs):
    """Mock implementation of cost_optimization_hub for testing."""
    from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
        format_response,
    )

    if operation == 'list_recommendation_summaries':
        # Check for required group_by parameter
        if 'group_by' not in kwargs or not kwargs['group_by']:
            return format_response(
                'error',
                {},
                'group_by parameter is required for list_recommendation_summaries operation',
            )

        return {
            'status': 'success',
            'data': {
                'summaries': [
                    {
                        'resource_type': 'EC2_INSTANCE',
                        'count': 10,
                        'estimated_monthly_savings': 500.0,
                        'currency': 'USD',
                    },
                    {
                        'resource_type': 'RDS_INSTANCE',
                        'count': 5,
                        'estimated_monthly_savings': 300.0,
                        'currency': 'USD',
                    },
                ],
                'total_recommendations': 15,
                'total_estimated_monthly_savings': 800.0,
            },
        }

    elif operation == 'list_recommendations':
        return {
            'status': 'success',
            'data': {
                'recommendations': [
                    {
                        'id': 'rec-1',
                        'resource_id': 'i-12345',
                        'resource_type': 'EC2_INSTANCE',
                        'current_instance_type': 't3.xlarge',
                        'recommended_instance_type': 't3.large',
                        'estimated_monthly_savings': 50.0,
                    }
                ],
                'total_recommendations': 1,
                'total_estimated_monthly_savings': 50.0,
            },
        }

    elif operation == 'get_recommendation':
        if not kwargs.get('recommendation_id'):
            return format_response(
                'error',
                {},
                'recommendation_id is required for get_recommendation operation',
            )

        return {
            'status': 'success',
            'data': {
                'recommendation_id': kwargs.get('recommendation_id'),
                'resource_id': 'i-12345',
                'current_instance_type': 't3.xlarge',
                'recommended_instance_type': 't3.large',
                'estimated_monthly_savings': 50.0,
            },
        }

    else:
        return format_response('error', {}, f'Unsupported operation: {operation}')


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def mock_coh_client():
    """Create a mock Cost Optimization Hub boto3 client."""
    mock_client = MagicMock()

    # Set up mock responses for different operations
    mock_client.list_recommendation_summaries.return_value = {
        'recommendationSummaries': [
            {
                'summaryValue': 'EC2_INSTANCE',
                'currentMonthEstimatedMonthlySavings': {
                    'amount': 1500.0,
                    'currency': 'USD',
                },
                'recommendationsCount': 25,
                'estimatedSavingsPercentage': 30.0,
            },
            {
                'summaryValue': 'EBS_VOLUME',
                'currentMonthEstimatedMonthlySavings': {
                    'amount': 500.0,
                    'currency': 'USD',
                },
                'recommendationsCount': 10,
                'estimatedSavingsPercentage': 20.0,
            },
        ],
        'nextToken': 'next-token-123',
    }

    mock_client.list_recommendations.return_value = {
        'recommendations': [
            {
                'resourceId': 'i-0abcdef1234567890',
                'resourceType': 'EC2_INSTANCE',
                'accountId': '123456789012',
                'estimatedMonthlySavings': {
                    'amount': 50.0,
                    'currency': 'USD',
                },
                'status': 'ACTIVE',
                'lastRefreshTimestamp': '2023-01-01T00:00:00Z',
            }
        ],
    }

    mock_client.get_recommendation.return_value = {
        'resourceId': 'i-0abcdef1234567890',
        'resourceType': 'EC2_INSTANCE',
        'accountId': '123456789012',
        'estimatedMonthlySavings': {
            'amount': 50.0,
            'currency': 'USD',
        },
        'status': 'ACTIVE',
        'lastRefreshTimestamp': '2023-01-01T00:00:00Z',
        'implementationEffort': 'MEDIUM',
        'currentResource': {
            'ec2Instance': {
                'instanceType': 't3.xlarge',
                'region': 'us-east-1',
            }
        },
        'recommendedResource': {
            'ec2Instance': {
                'instanceType': 't3.large',
                'region': 'us-east-1',
            }
        },
    }

    return mock_client


@pytest.mark.asyncio
async def test_invalid_operation(mock_context):
    """Test invalid operation."""
    result = await cost_optimization_hub(mock_context, operation='invalid_operation')

    assert result['status'] == 'error'
    assert 'Unsupported operation' in result['message']


@pytest.mark.asyncio
async def test_missing_operation(mock_context):
    """Test missing operation parameter."""
    result = await cost_optimization_hub(mock_context, operation='')

    assert result['status'] == 'error'


@pytest.mark.asyncio
async def test_missing_group_by_for_summaries(mock_context):
    """Test missing group_by for list_recommendation_summaries."""
    result = await cost_optimization_hub(mock_context, operation='list_recommendation_summaries')

    assert result['status'] == 'error'
    assert 'group_by parameter is required' in result['message']


@pytest.mark.asyncio
async def test_missing_resource_params_for_get_recommendation(mock_context):
    """Test missing recommendation_id for get_recommendation."""
    result = await cost_optimization_hub(mock_context, operation='get_recommendation')

    assert result['status'] == 'error'
    assert 'recommendation_id is required' in result['message']


@pytest.mark.asyncio
async def test_get_recommendation_summaries_success(mock_context):
    """Test successful list_recommendation_summaries."""
    result = await cost_optimization_hub(
        mock_context, operation='list_recommendation_summaries', group_by='ResourceType'
    )

    assert result['status'] == 'success'
    assert 'summaries' in result['data']
    assert result['data']['total_recommendations'] == 15
    assert result['data']['total_estimated_monthly_savings'] == 800.0


@pytest.mark.asyncio
async def test_list_recommendations_success(mock_context):
    """Test successful list_recommendations."""
    result = await cost_optimization_hub(mock_context, operation='list_recommendations')

    assert result['status'] == 'success'
    assert 'recommendations' in result['data']
    assert len(result['data']['recommendations']) == 1
    assert result['data']['recommendations'][0]['id'] == 'rec-1'


@pytest.mark.asyncio
async def test_get_recommendation_success(mock_context):
    """Test successful get_recommendation with recommendation_id."""
    result = await cost_optimization_hub(
        mock_context,
        operation='get_recommendation',
        recommendation_id='rec-1',
    )

    assert result['status'] == 'success'
    assert result['data']['recommendation_id'] == 'rec-1'


def _reload_coh_with_identity_decorator():
    """Reload cost_optimization_hub_tools with FastMCP.tool patched to return the original function unchanged (identity decorator).

    This exposes a callable 'cost_optimization_hub' we can invoke to cover lines 99–174.
    """
    from awslabs.billing_cost_management_mcp_server.tools import (
        cost_optimization_hub_tools as coh_mod,
    )

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(coh_mod)
        return coh_mod


@pytest.mark.asyncio
async def test_coh_real_summaries_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub summaries with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # now a callable coroutine

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, 'parse_json') as mock_parse_json,
        patch.object(
            coh_mod, 'list_recommendation_summaries', new_callable=AsyncMock
        ) as mock_list_summaries,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client

        filters_str = '{"implementationEffort":["LOW"],"savingsPct":{"gte":10}}'
        parsed = {'implementationEffort': ['LOW'], 'savingsPct': {'gte': 10}}
        mock_parse_json.return_value = parsed
        mock_list_summaries.return_value = {'status': 'success', 'data': {'ok': True}}

        # Mock the context methods to avoid errors
        mock_context.info = AsyncMock()
        mock_context.error = AsyncMock()

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_recommendation_summaries',
            group_by='ResourceType',
            max_results=50,
            filters=filters_str,
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with(
            'cost-optimization-hub', region_name='us-east-1'
        )
        mock_parse_json.assert_called_once_with(filters_str, 'filters')
        mock_list_summaries.assert_awaited_once_with(
            mock_context,
            fake_client,
            group_by='ResourceType',
            max_results=50,
            filters=parsed,
            next_token=None,
            max_pages=None,
        )


@pytest.mark.asyncio
async def test_coh_real_list_recommendations_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub list_recommendations with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, 'parse_json') as mock_parse_json,
        patch.object(coh_mod, 'list_recommendations', new_callable=AsyncMock) as mock_list_recs,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client

        filters_str = '{"savings":{"gte":25},"service":["EC2_INSTANCE"]}'
        parsed = {'savings': {'gte': 25}, 'service': ['EC2_INSTANCE']}
        mock_parse_json.return_value = parsed
        mock_list_recs.return_value = {'status': 'success', 'data': {'items': []}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_recommendations',
            max_results=25,
            filters=filters_str,
            include_all_recommendations=True,
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with(
            'cost-optimization-hub', region_name='us-east-1'
        )
        mock_parse_json.assert_called_once_with(filters_str, 'filters')
        mock_list_recs.assert_awaited_once_with(
            mock_context,
            fake_client,
            25,
            parsed,
            True,
            next_token=None,
            max_pages=None,
            order_by=None,
        )


@pytest.mark.asyncio
async def test_coh_real_get_recommendation_success_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub get_recommendation success with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, 'get_recommendation', new_callable=AsyncMock) as mock_get_rec,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_get_rec.return_value = {'status': 'success', 'data': {'id': 'rec-123'}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='get_recommendation',
            recommendation_id='i-abc',
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with(
            'cost-optimization-hub', region_name='us-east-1'
        )
        mock_get_rec.assert_awaited_once_with(mock_context, fake_client, 'i-abc')


@pytest.mark.asyncio
async def test_coh_real_get_recommendation_missing_params_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub get_recommendation missing params with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    res = await real_fn(  # type: ignore
        mock_context,
        operation='get_recommendation',
        # missing recommendation_id
    )
    assert res['status'] == 'error'
    blob = json.dumps(res)
    assert 'recommendation_id' in blob


@pytest.mark.asyncio
async def test_coh_real_unsupported_operation_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub unsupported operation with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    res = await real_fn(mock_context, operation='definitely_not_supported')  # type: ignore
    assert res['status'] == 'error'
    blob = json.dumps(res)
    assert 'list_recommendation_summaries' in blob
    assert 'list_recommendations' in blob
    assert 'get_recommendation' in blob


@pytest.mark.asyncio
async def test_coh_real_summaries_default_group_by_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub summaries default group_by with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    res = await real_fn(  # type: ignore
        mock_context,
        operation='list_recommendation_summaries',
        # group_by intentionally omitted
    )

    assert res['status'] == 'error'
    # Verify the validation message mentions group_by
    assert 'group_by' in json.dumps(res).lower()


@pytest.mark.asyncio
async def test_coh_real_list_recommendations_no_filters_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub list_recommendations no filters with identity decorator."""
    # Covers list_recommendations branch without filters/parse_json and with default include_all_recommendations=None
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, 'list_recommendations', new_callable=AsyncMock) as mock_list_recs,
        patch.object(coh_mod, 'parse_json') as mock_parse_json,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_list_recs.return_value = {'status': 'success', 'data': {'items': ['x']}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_recommendations',
            # No filters, no max_results, no next_token, no include_all_recommendations
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with(
            'cost-optimization-hub', region_name='us-east-1'
        )
        # parse_json should not be called when filters and order_by are None
        mock_parse_json.assert_not_called()
        mock_list_recs.assert_awaited_once_with(
            mock_context,
            fake_client,
            None,  # max_results
            None,  # filters
            None,  # include_all_recommendations
            next_token=None,
            max_pages=None,
            order_by=None,
        )


@pytest.mark.asyncio
async def test_coh_real_invalid_group_by_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub invalid group_by with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    res = await real_fn(  # type: ignore
        mock_context,
        operation='list_recommendation_summaries',
        group_by='INVALID_GROUP_BY',
    )

    assert res['status'] == 'error'
    assert 'Invalid group_by value' in res['message']


@pytest.mark.asyncio
async def test_coh_real_summaries_exception_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub summaries exception with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(
            coh_mod, 'list_recommendation_summaries', new_callable=AsyncMock
        ) as mock_list_summaries,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_list_summaries.side_effect = Exception('Test exception')

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_recommendation_summaries',
            group_by='ResourceType',
        )

        assert res['status'] == 'error'
        assert 'Error fetching recommendation summaries' in res['message']


@pytest.mark.asyncio
async def test_coh_real_list_recommendations_exception_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub list_recommendations exception with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, 'list_recommendations', new_callable=AsyncMock) as mock_list_recs,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_list_recs.side_effect = Exception('Test exception')

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_recommendations',
        )

        assert res['status'] == 'error'
        assert 'Error fetching recommendations' in res['message']


@pytest.mark.asyncio
async def test_coh_real_get_recommendation_missing_resource_id_reload_identity_decorator(
    mock_context,
):
    """Test real cost_optimization_hub get_recommendation missing resource_id with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    res = await real_fn(  # type: ignore
        mock_context,
        operation='get_recommendation',
        # missing recommendation_id
    )

    assert res['status'] == 'error'
    assert 'recommendation_id is required' in res['message']


@pytest.mark.asyncio
async def test_coh_real_main_exception_reload_identity_decorator(mock_context):
    """Test real cost_optimization_hub main exception with identity decorator."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle_error,
    ):
        mock_create_client.side_effect = Exception('Client creation failed')
        mock_handle_error.return_value = {'status': 'error', 'message': 'Handled error'}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_recommendations',
        )

        assert res['status'] == 'error'
        mock_handle_error.assert_awaited_once()


@pytest.mark.asyncio
async def test_coh_real_list_recommendations_order_by_reload_identity_decorator(mock_context):
    """list_recommendations forwards a parsed order_by to the helper."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, 'parse_json') as mock_parse_json,
        patch.object(coh_mod, 'list_recommendations', new_callable=AsyncMock) as mock_list_recs,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        order_by_str = '{"dimension":"EstimatedMonthlySavings","order":"Desc"}'
        parsed_order_by = {'dimension': 'EstimatedMonthlySavings', 'order': 'Desc'}
        mock_parse_json.return_value = parsed_order_by
        mock_list_recs.return_value = {'status': 'success', 'data': {'items': []}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_recommendations',
            order_by=order_by_str,
        )

        assert res['status'] == 'success'
        # filters is None so parse_json is only invoked for order_by.
        mock_parse_json.assert_called_once_with(order_by_str, 'order_by')
        mock_list_recs.assert_awaited_once_with(
            mock_context,
            fake_client,
            None,
            None,
            None,
            next_token=None,
            max_pages=None,
            order_by=parsed_order_by,
        )


@pytest.mark.asyncio
async def test_coh_real_list_recommendations_invalid_order_by_reload_identity_decorator(
    mock_context,
):
    """list_recommendations rejects an unsupported order_by dimension before the API call."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(coh_mod, 'parse_json', return_value={'dimension': 'Nope', 'order': 'Desc'}),
        patch.object(coh_mod, 'list_recommendations', new_callable=AsyncMock) as mock_list_recs,
    ):
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_recommendations',
            order_by='{"dimension":"Nope","order":"Desc"}',
        )

    assert res['status'] == 'error'
    assert 'Invalid order_by dimension' in res['message']
    # Validation short-circuits before the helper is invoked.
    mock_list_recs.assert_not_awaited()


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_reload_identity_decorator(mock_context):
    """Real dispatcher wires list_efficiency_metrics with parsed/validated params."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, '_today', return_value=date(2026, 9, 4)),
        patch.object(coh_mod, 'parse_json') as mock_parse_json,
        patch.object(coh_mod, 'list_efficiency_metrics', new_callable=AsyncMock) as mock_list_eff,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        order_by_str = '{"dimension":"Score","order":"Desc"}'
        parsed_order_by = {'dimension': 'Score', 'order': 'Desc'}
        mock_parse_json.return_value = parsed_order_by
        mock_list_eff.return_value = {'status': 'success', 'data': {'groups': []}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
            group_by='Region',
            order_by=order_by_str,
            max_results=25,
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with(
            'cost-optimization-hub', region_name='us-east-1'
        )
        mock_parse_json.assert_called_once_with(order_by_str, 'order_by')
        mock_list_eff.assert_awaited_once_with(
            mock_context,
            fake_client,
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
            group_by='Region',
            order_by=parsed_order_by,
            max_results=25,
            next_token=None,
            max_pages=None,
        )


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_defaults_reload_identity_decorator(mock_context):
    """Omitted granularity/dates default to Monthly + a coerced lookback window."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        # today matches the mocked lookback end so the default window is within
        # range and is not clamped.
        patch.object(coh_mod, '_today', return_value=date(2026, 8, 23)),
        patch.object(
            coh_mod, 'get_date_range', return_value=('2026-05-25', '2026-08-23')
        ) as mock_dr,
        patch.object(coh_mod, 'list_efficiency_metrics', new_callable=AsyncMock) as mock_list_eff,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_list_eff.return_value = {'status': 'success', 'data': {'groups': []}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
        )

        assert res['status'] == 'success'
        mock_dr.assert_called_once_with(None, None, default_days_ago=90)
        # Monthly granularity truncates the YYYY-MM-DD lookback bounds to YYYY-MM.
        mock_list_eff.assert_awaited_once_with(
            mock_context,
            fake_client,
            granularity='Monthly',
            start_date='2026-05',
            end_date='2026-08',
            group_by=None,
            order_by=None,
            max_results=None,
            next_token=None,
            max_pages=None,
        )


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_invalid_granularity_reload_identity_decorator(
    mock_context,
):
    """An unsupported granularity is rejected before any API call."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()):
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Weekly',
        )

    assert res['status'] == 'error'
    assert 'Invalid granularity' in res['message']


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_invalid_group_by_reload_identity_decorator(
    mock_context,
):
    """Efficiency metrics reject group_by values other than AccountId/Region."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()):
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Monthly',
            group_by='Service',
        )

    assert res['status'] == 'error'
    assert 'Invalid group_by for list_efficiency_metrics' in res['message']


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_invalid_order_by_reload_identity_decorator(
    mock_context,
):
    """An out-of-range order_by dimension is rejected."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(coh_mod, 'parse_json', return_value={'dimension': 'Nope', 'order': 'Desc'}),
    ):
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
            order_by='{"dimension":"Nope","order":"Desc"}',
        )

    assert res['status'] == 'error'
    assert 'Invalid order_by dimension' in res['message']


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_exception_reload_identity_decorator(mock_context):
    """A helper exception is caught and surfaced as a friendly error."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(coh_mod, 'list_efficiency_metrics', new_callable=AsyncMock) as mock_list_eff,
    ):
        mock_list_eff.side_effect = Exception('boom')

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
        )

    assert res['status'] == 'error'
    assert 'Error fetching efficiency metrics' in res['message']


@pytest.mark.asyncio
async def test_coh_real_unsupported_operation_lists_efficiency_metrics(mock_context):
    """The unsupported-operation error advertises list_efficiency_metrics."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()):
        res = await real_fn(mock_context, operation='definitely_not_supported')  # type: ignore

    assert res['status'] == 'error'
    assert 'list_efficiency_metrics' in json.dumps(res)


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_daily_passthrough_reload_identity_decorator(
    mock_context,
):
    """Daily granularity keeps full YYYY-MM-DD dates (no month truncation)."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, '_today', return_value=date(2026, 9, 4)),
        patch.object(coh_mod, 'list_efficiency_metrics', new_callable=AsyncMock) as mock_list_eff,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_list_eff.return_value = {'status': 'success', 'data': {'groups': []}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Daily',
            start_date='2026-05-01',
            end_date='2026-05-31',
        )

        assert res['status'] == 'success'
        mock_list_eff.assert_awaited_once_with(
            mock_context,
            fake_client,
            granularity='Daily',
            start_date='2026-05-01',
            end_date='2026-05-31',
            group_by=None,
            order_by=None,
            max_results=None,
            next_token=None,
            max_pages=None,
        )


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_invalid_date_reload_identity_decorator(mock_context):
    """A malformed date is rejected before any API call."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()):
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Daily',
            start_date='05/01/2026',
            end_date='2026-05-31',
        )

    assert res['status'] == 'error'
    assert 'Invalid start_date' in res['message']


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_daily_rejects_monthly_format_date(mock_context):
    """Daily granularity with a YYYY-MM date is rejected locally, not forwarded.

    A month-only date is only valid for Monthly; validating against the resolved
    granularity catches the mismatch before the API call and names the expected
    format.
    """
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(coh_mod, 'list_efficiency_metrics', new_callable=AsyncMock) as mock_list_eff,
    ):
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Daily',
            start_date='2026-06',
            end_date='2026-08-31',
        )

    assert res['status'] == 'error'
    assert 'Invalid start_date' in res['message']
    assert 'YYYY-MM-DD' in res['message']
    mock_list_eff.assert_not_awaited()


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_rejects_unpadded_date(mock_context):
    """A non-zero-padded date is rejected locally, not forwarded.

    strptime alone is lenient (it accepts '2026-6-5'), but COH requires strict
    zero-padded yyyy-MM-dd and rejects unpadded values with a ValidationException.
    The strftime round-trip in _is_valid_efficiency_date catches it locally.
    """
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(coh_mod, 'list_efficiency_metrics', new_callable=AsyncMock) as mock_list_eff,
    ):
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Daily',
            start_date='2026-6-5',
            end_date='2026-08-31',
        )

    assert res['status'] == 'error'
    assert 'Invalid start_date' in res['message']
    mock_list_eff.assert_not_awaited()


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_monthly_truncates_daily_format_date(mock_context):
    """Monthly granularity accepts a YYYY-MM-DD date by truncating it to YYYY-MM."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, '_today', return_value=date(2026, 9, 4)),
        patch.object(coh_mod, 'list_efficiency_metrics', new_callable=AsyncMock) as mock_list_eff,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_list_eff.return_value = {'status': 'success', 'data': {'groups': []}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Monthly',
            start_date='2026-06-15',
            end_date='2026-08-20',
        )

    assert res['status'] == 'success'
    mock_list_eff.assert_awaited_once_with(
        mock_context,
        fake_client,
        granularity='Monthly',
        start_date='2026-06',
        end_date='2026-08',
        group_by=None,
        order_by=None,
        max_results=None,
        next_token=None,
        max_pages=None,
    )


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_order_by_not_dict_reload_identity_decorator(
    mock_context,
):
    """A non-object order_by JSON is rejected."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(coh_mod, 'parse_json', return_value=['Score']),
    ):
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
            order_by='["Score"]',
        )

    assert res['status'] == 'error'
    assert 'order_by must be a JSON object' in res['message']


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_invalid_order_value_reload_identity_decorator(
    mock_context,
):
    """An order value outside Asc/Desc is rejected."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(
            coh_mod, 'parse_json', return_value={'dimension': 'Score', 'order': 'Sideways'}
        ),
    ):
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-08',
            order_by='{"dimension":"Score","order":"Sideways"}',
        )

    assert res['status'] == 'error'
    assert 'Invalid order_by order' in res['message']


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_clamps_daily_over_90_days(mock_context):
    """A Daily start older than 90 days before today is clamped forward with a range_note."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, '_today', return_value=date(2026, 9, 4)),
        patch.object(coh_mod, 'list_efficiency_metrics', new_callable=AsyncMock) as mock_list_eff,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_list_eff.return_value = {'status': 'success', 'data': {'groups': []}}

        # today=2026-09-04 -> earliest allowed start = today-90d = 2026-06-06.
        # start 2026-01-01 predates it -> clamp start to 2026-06-06.
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Daily',
            start_date='2026-01-01',
            end_date='2026-09-01',
        )

        assert res['status'] == 'success'
        call_kwargs = mock_list_eff.call_args[1]
        assert call_kwargs['start_date'] == '2026-06-06'
        assert call_kwargs['end_date'] == '2026-09-01'
        # The effective (moved-forward) start is surfaced via operation_parameters.
        assert res['data']['operation_parameters']['start_date'] == '2026-06-06'


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_clamps_monthly_over_3_months(mock_context):
    """A Monthly start older than 3 months before this month is clamped forward with a note."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, '_today', return_value=date(2026, 9, 4)),
        patch.object(coh_mod, 'list_efficiency_metrics', new_callable=AsyncMock) as mock_list_eff,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_list_eff.return_value = {'status': 'success', 'data': {'groups': []}}

        # today=2026-09 -> earliest allowed start month = 2026-06.
        # start 2026-01 predates it -> clamp start to 2026-06.
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Monthly',
            start_date='2026-01',
            end_date='2026-09',
        )

        assert res['status'] == 'success'
        call_kwargs = mock_list_eff.call_args[1]
        assert call_kwargs['start_date'] == '2026-06'
        assert call_kwargs['end_date'] == '2026-09'
        assert res['data']['operation_parameters']['start_date'] == '2026-06'


@pytest.mark.asyncio
async def test_coh_real_efficiency_metrics_no_clamp_within_limit(mock_context):
    """A window inside the API span is passed through unchanged with no range_note."""
    coh_mod = _reload_coh_with_identity_decorator()
    real_fn = coh_mod.cost_optimization_hub  # type: ignore

    with (
        patch.object(coh_mod, 'create_aws_client') as mock_create_client,
        patch.object(coh_mod, '_today', return_value=date(2026, 9, 4)),
        patch.object(coh_mod, 'list_efficiency_metrics', new_callable=AsyncMock) as mock_list_eff,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_list_eff.return_value = {'status': 'success', 'data': {'groups': []}}

        # today=2026-09; start 2026-06 is exactly 3 months back -> boundary, NOT clamped.
        res = await real_fn(  # type: ignore
            mock_context,
            operation='list_efficiency_metrics',
            granularity='Monthly',
            start_date='2026-06',
            end_date='2026-09',
        )

        assert res['status'] == 'success'
        call_kwargs = mock_list_eff.call_args[1]
        assert call_kwargs['start_date'] == '2026-06'


def test_clamp_efficiency_time_span_unit():
    """Direct unit coverage of the clamp helper (start-to-now limit) across edges."""
    coh_mod = _reload_coh_with_identity_decorator()
    clamp = coh_mod._clamp_efficiency_time_span  # type: ignore

    # Pin 'now' so the start-to-now limit is deterministic: today=2026-09-04 ->
    # earliest Daily start = 2026-06-06, earliest Monthly month = 2026-06.
    with patch.object(coh_mod, '_today', return_value=date(2026, 9, 4)):
        # Daily start older than the 90-day window -> moved to earliest.
        assert clamp('2026-01-01', '2026-09-01', 'Daily') == '2026-06-06'

        # Daily start exactly at the boundary -> unchanged.
        assert clamp('2026-06-06', '2026-09-01', 'Daily') == '2026-06-06'

        # Daily window entirely older than the range -> passthrough (service rejects).
        assert clamp('2026-01-01', '2026-05-01', 'Daily') == '2026-01-01'

        # Monthly start older than 3 months back -> moved to earliest month.
        assert clamp('2026-01', '2026-09', 'Monthly') == '2026-06'

        # Monthly start exactly 3 months back -> unchanged.
        assert clamp('2026-06', '2026-09', 'Monthly') == '2026-06'

        # Unparseable date passes through untouched (upstream validation guards this).
        assert clamp('not-a-date', '2026-09-01', 'Daily') == 'not-a-date'
