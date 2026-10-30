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

"""Unit tests for the cost_explorer_operations module."""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.cost_explorer_operations import (
    get_cost_and_usage,
    get_cost_and_usage_with_resources,
    get_cost_categories,
    get_cost_forecast,
    get_dimension_values,
    get_savings_plans_utilization,
    get_tags,
    get_usage_forecast,
)
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.debug = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def mock_ce_client():
    """Create a mock Cost Explorer boto3 client."""
    mock_client = MagicMock()

    # Set up mock responses for different operations
    mock_client.get_cost_and_usage.return_value = {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'},
                'Total': {'UnblendedCost': {'Amount': '100.0', 'Unit': 'USD'}},
                'Groups': [],
            }
        ]
    }

    # The API returns DAILY bounds as UTC-midnight timestamps here, unlike get_cost_and_usage.
    mock_client.get_cost_and_usage_with_resources.return_value = {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-01-01T00:00:00Z', 'End': '2023-01-02T00:00:00Z'},
                'Groups': [
                    {
                        'Keys': ['i-1234567890abcdef0'],
                        'Metrics': {'UnblendedCost': {'Amount': '50.0', 'Unit': 'USD'}},
                    }
                ],
            }
        ],
        'DimensionValueAttributes': [],
    }

    mock_client.get_dimension_values.return_value = {
        'DimensionValues': [
            {'Value': 'AWS Lambda', 'Attributes': {}},
            {'Value': 'Amazon S3', 'Attributes': {}},
        ]
    }

    mock_client.get_cost_forecast.return_value = {
        'Total': {'Amount': '150.0', 'Unit': 'USD'},
        'ForecastResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-02-01', 'End': '2023-02-28'},
                'MeanValue': '150.0',
            }
        ],
    }

    mock_client.get_usage_forecast.return_value = {
        'Total': {'Amount': '1500.0', 'Unit': 'GB'},
        'ForecastResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-02-01', 'End': '2023-02-28'},
                'MeanValue': '1500.0',
            }
        ],
    }

    mock_client.get_tags.return_value = {'Tags': ['Environment', 'Project']}
    mock_client.get_tag_values.return_value = {'TagValues': ['dev', 'prod', 'test']}

    mock_client.get_cost_categories.return_value = {'CostCategoryNames': ['Department', 'Team']}

    mock_client.get_savings_plans_utilization.return_value = {
        'SavingsPlansUtilizationsByTime': [
            {
                'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-31'},
                'Utilization': {'Utilization': '0.85'},
            }
        ]
    }

    return mock_client


def _passthrough_store():
    """Patch the result store to return the response unchanged, recording its arguments."""
    return patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_explorer_operations.convert_response_if_needed',
        new=AsyncMock(side_effect=lambda ctx, response, *args, **kwargs: response),
    )


METRICS_CASES = [
    (None, ['UnblendedCost']),
    ('', ['UnblendedCost']),
    ([], ['UnblendedCost']),
    ('["UnblendedCost", "UsageQuantity"]', ['UnblendedCost', 'UsageQuantity']),
    (['AmortizedCost'], ['AmortizedCost']),
]


@pytest.fixture
def sample_billing_view_arn():
    """Sample billing view ARN for testing billing view support."""
    return 'arn:aws:billing::123456789012:billingview/custom-view-abc123'


@pytest.mark.asyncio
class TestBillingViewArnSupport:
    """Tests for billing_view_arn parameter across all supported CE operations."""

    async def test_get_cost_and_usage_with_billing_view_arn(
        self, mock_context, mock_ce_client, sample_billing_view_arn
    ):
        """Test get_cost_and_usage includes BillingViewArn in request."""
        result = await get_cost_and_usage(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            billing_view_arn=sample_billing_view_arn,
        )
        assert result['status'] == 'success'
        call_kwargs = mock_ce_client.get_cost_and_usage.call_args[1]
        assert call_kwargs['BillingViewArn'] == sample_billing_view_arn

    async def test_get_cost_and_usage_without_billing_view_arn(self, mock_context, mock_ce_client):
        """Test get_cost_and_usage omits BillingViewArn when not provided."""
        await get_cost_and_usage(mock_context, mock_ce_client)
        call_kwargs = mock_ce_client.get_cost_and_usage.call_args[1]
        assert 'BillingViewArn' not in call_kwargs

    async def test_get_cost_and_usage_with_resources_with_billing_view_arn(
        self, mock_context, mock_ce_client, sample_billing_view_arn
    ):
        """Test get_cost_and_usage_with_resources includes BillingViewArn."""
        result = await get_cost_and_usage_with_resources(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-07',
            billing_view_arn=sample_billing_view_arn,
        )
        assert result['status'] == 'success'
        call_kwargs = mock_ce_client.get_cost_and_usage_with_resources.call_args[1]
        assert call_kwargs['BillingViewArn'] == sample_billing_view_arn

    async def test_get_dimension_values_with_billing_view_arn(
        self, mock_context, mock_ce_client, sample_billing_view_arn
    ):
        """Test get_dimension_values includes BillingViewArn."""
        result = await get_dimension_values(
            mock_context,
            mock_ce_client,
            dimension='SERVICE',
            billing_view_arn=sample_billing_view_arn,
        )
        assert result['status'] == 'success'
        call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
        assert call_kwargs['BillingViewArn'] == sample_billing_view_arn

    async def test_get_dimension_values_with_context(self, mock_context, mock_ce_client):
        """Test get_dimension_values includes Context."""
        result = await get_dimension_values(
            mock_context,
            mock_ce_client,
            dimension='SAVINGS_PLANS_TYPE',
            context='SAVINGS_PLANS',
        )
        assert result['status'] == 'success'
        call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
        assert call_kwargs['Context'] == 'SAVINGS_PLANS'
        assert call_kwargs['Dimension'] == 'SAVINGS_PLANS_TYPE'

    async def test_get_dimension_values_without_context_omits_it(
        self, mock_context, mock_ce_client
    ):
        """Test get_dimension_values leaves Context out when not supplied.

        The API defaults to COST_AND_USAGE, so sending it explicitly would change
        nothing; omitting it keeps the request minimal.
        """
        result = await get_dimension_values(
            mock_context,
            mock_ce_client,
            dimension='SERVICE',
        )
        assert result['status'] == 'success'
        call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
        assert 'Context' not in call_kwargs

    async def test_get_cost_forecast_with_billing_view_arn(
        self, mock_context, mock_ce_client, sample_billing_view_arn
    ):
        """Test get_cost_forecast includes BillingViewArn."""
        result = await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            start_date='2023-02-01',
            end_date='2023-02-28',
            billing_view_arn=sample_billing_view_arn,
        )
        assert result['status'] == 'success'
        call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
        assert call_kwargs['BillingViewArn'] == sample_billing_view_arn

    async def test_get_usage_forecast_with_billing_view_arn(
        self, mock_context, mock_ce_client, sample_billing_view_arn
    ):
        """Test get_usage_forecast includes BillingViewArn."""
        mock_ce_client.get_usage_forecast.return_value = {
            'Total': {'Amount': '1500.0', 'Unit': 'GB'},
            'ForecastResultsByTime': [],
        }
        result = await get_usage_forecast(
            mock_context,
            mock_ce_client,
            metric='USAGE_QUANTITY',
            start_date='2023-02-01',
            end_date='2023-02-28',
            billing_view_arn=sample_billing_view_arn,
        )
        assert result['status'] == 'success'
        call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
        assert call_kwargs['BillingViewArn'] == sample_billing_view_arn

    async def test_get_tags_with_billing_view_arn(
        self, mock_context, mock_ce_client, sample_billing_view_arn
    ):
        """Test get_tags includes BillingViewArn."""
        result = await get_tags(
            mock_context,
            mock_ce_client,
            billing_view_arn=sample_billing_view_arn,
        )
        assert result['status'] == 'success'
        call_kwargs = mock_ce_client.get_tags.call_args[1]
        assert call_kwargs['BillingViewArn'] == sample_billing_view_arn

    async def test_get_cost_categories_with_billing_view_arn(
        self, mock_context, mock_ce_client, sample_billing_view_arn
    ):
        """Test get_cost_categories includes BillingViewArn."""
        result = await get_cost_categories(
            mock_context,
            mock_ce_client,
            billing_view_arn=sample_billing_view_arn,
        )
        assert result['status'] == 'success'
        call_kwargs = mock_ce_client.get_cost_categories.call_args[1]
        assert call_kwargs['BillingViewArn'] == sample_billing_view_arn


@pytest.mark.asyncio
class TestGetCostAndUsage:
    """Tests for get_cost_and_usage function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_cost_and_usage."""
        result = await get_cost_and_usage(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            granularity='DAILY',
        )

        mock_ce_client.get_cost_and_usage.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_and_usage.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-01-31'
        assert call_kwargs['Granularity'] == 'DAILY'
        assert call_kwargs['Metrics'] == ['UnblendedCost']  # Default metric

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_with_json_parameters(self, mock_context, mock_ce_client):
        """Test with JSON parameters for metrics, group_by, and filters."""
        metrics_json = '["UnblendedCost", "UsageQuantity"]'
        group_by_json = '[{"Type": "DIMENSION", "Key": "SERVICE"}]'
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'

        await get_cost_and_usage(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            granularity='DAILY',
            metrics=metrics_json,
            group_by=group_by_json,
            filter_expr=filter_json,
        )

        # The JSON arguments are parsed and sent as given.
        call_kwargs = mock_ce_client.get_cost_and_usage.call_args[1]
        assert call_kwargs['Metrics'] == ['UnblendedCost', 'UsageQuantity']
        assert call_kwargs['GroupBy'] == [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        assert call_kwargs['Filter'] == {
            'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}
        }

    @pytest.mark.parametrize('metrics, expected', METRICS_CASES)
    async def test_sends_and_stores_parsed_metrics(
        self, mock_context, mock_ce_client, metrics, expected
    ):
        """The parsed metrics, default applied, are sent to the API and stored with the result."""
        with _passthrough_store() as store:
            result = await get_cost_and_usage(
                mock_context,
                mock_ce_client,
                start_date='2023-01-01',
                end_date='2023-01-07',
                metrics=metrics,
            )

        assert result['status'] == 'success'
        assert mock_ce_client.get_cost_and_usage.call_args.kwargs['Metrics'] == expected
        assert store.call_args.kwargs['metrics'] == expected

    @pytest.mark.parametrize(
        'metrics', ['["UnblendedCost", 1]', '{"a": 1}', [''], 5, 'UnblendedCost']
    )
    async def test_invalid_metrics_is_a_validation_error(
        self, mock_context, mock_ce_client, metrics
    ):
        """Invalid metrics are rejected before any API call."""
        result = await get_cost_and_usage(mock_context, mock_ce_client, metrics=metrics)

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        mock_ce_client.get_cost_and_usage.assert_not_called()

    async def test_with_pagination(self, mock_context, mock_ce_client):
        """Test pagination handling in get_cost_and_usage."""
        # Setup paginated responses
        mock_ce_client.get_cost_and_usage.side_effect = [
            {
                'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'}}],
                'NextPageToken': 'page2token',
            },
            {
                'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-02', 'End': '2023-01-03'}}],
                'NextPageToken': None,
            },
        ]

        # Test actual pagination handling in the code
        result = await get_cost_and_usage(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            next_token='initial_token',
        )

        # Every page is fetched, starting from the caller's token.
        assert result['status'] == 'success'
        calls = mock_ce_client.get_cost_and_usage.call_args_list
        assert [c.kwargs.get('NextPageToken') for c in calls] == ['initial_token', 'page2token']
        assert len(result['data']['ResultsByTime']) == 2

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_cost_and_usage."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_cost_and_usage.side_effect = error

        # Don't mock handle_aws_error since we want to test the actual error path
        result = await get_cost_and_usage(mock_context, mock_ce_client)

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result

    async def test_caller_next_token_is_used_on_first_request(self, mock_context, mock_ce_client):
        """Caller-supplied next_token must be injected into the first boto3 call."""
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-02', 'End': '2023-01-03'}}],
        }

        await get_cost_and_usage(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            next_token='resume-from-here',
        )

        first_call_kwargs = mock_ce_client.get_cost_and_usage.call_args_list[0][1]
        assert first_call_kwargs.get('NextPageToken') == 'resume-from-here'

    async def test_max_items_stops_before_a_page_that_could_exceed_it(
        self, mock_context, mock_ce_client
    ):
        """max_items stops once another full page could pass it; the token leads the result."""
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'}}],
            'NextPageToken': 'continue-here',
        }

        result = await get_cost_and_usage(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            max_items=10,
        )

        assert result['status'] == 'success'
        # One page holds up to 5,000 rows, so a second could take 1 row past 10.
        assert mock_ce_client.get_cost_and_usage.call_count == 1
        data = result['data']
        assert data['pagination'] == {
            'complete_dataset': False,
            'has_more': True,
            'next_token': 'continue-here',
            'items_returned': 1,
        }
        assert list(data)[:2] == ['complete_dataset', 'warning']
        assert data['complete_dataset'] is False
        assert 'max_items' in data['warning']
        # Cost Explorer sets the page size; neither a size nor the caller's limit is sent.
        assert 'MaxResults' not in mock_ce_client.get_cost_and_usage.call_args.kwargs

    @pytest.mark.parametrize(
        'metrics, expected_calls',
        [
            ('["UnblendedCost"]', 1),  # 5,000-row pages: 100 + 5,000 > 2,600
            ('["UnblendedCost", "UsageQuantity"]', 2),  # 2,500-row pages: 100 + 2,500 <= 2,600
            ('["UnblendedCost", "UnblendedCost"]', 1),  # duplicates count once
        ],
    )
    async def test_page_max_shrinks_with_the_number_of_metrics(
        self, mock_context, mock_ce_client, metrics, expected_calls
    ):
        """The worst-case page is ceil(5000 / distinct metrics) rows."""
        page = {
            'ResultsByTime': [{'Groups': [{'Keys': [str(i)]} for i in range(100)]}],
            'NextPageToken': 'more',
        }
        mock_ce_client.get_cost_and_usage.return_value = page

        result = await get_cost_and_usage(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            metrics=metrics,
            max_items=2600,
        )

        assert mock_ce_client.get_cost_and_usage.call_count == expected_calls
        assert result['data']['pagination']['items_returned'] == 100 * expected_calls

    async def test_rows_count_groups_and_empty_periods(self, mock_context, mock_ce_client):
        """A row is one group in one period; a period without groups counts as one row."""
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {'Groups': [{'Keys': ['a']}, {'Keys': ['b']}, {'Keys': ['c']}]},
                {'Groups': []},
                {'Total': {}},
            ],
        }

        result = await get_cost_and_usage(
            mock_context, mock_ce_client, start_date='2023-01-01', end_date='2023-01-31'
        )

        assert result['data']['pagination']['items_returned'] == 5

    async def test_continuation_resends_identical_params_with_the_callers_token(
        self, mock_context, mock_ce_client
    ):
        """A continuation call sends the caller's token and otherwise the same request."""
        mock_ce_client.get_cost_and_usage.side_effect = [
            {'ResultsByTime': [{'Groups': [{'Keys': ['a']}]}], 'NextPageToken': 'tok-1'},
            {'ResultsByTime': [{'Groups': [{'Keys': ['b']}]}]},
        ]
        args = {
            'start_date': '2023-01-01',
            'end_date': '2023-01-31',
            'granularity': 'MONTHLY',
            'metrics': '["UnblendedCost"]',
            'group_by': '[{"Type": "DIMENSION", "Key": "SERVICE"}]',
            'filter_expr': '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}',
            'billing_view_arn': 'arn:aws:billing::123456789012:billingview/primary',
        }

        first = await get_cost_and_usage(mock_context, mock_ce_client, max_items=1, **args)
        token = first['data']['pagination']['next_token']
        second = await get_cost_and_usage(
            mock_context, mock_ce_client, max_items=1, next_token=token, **args
        )

        first_call, second_call = mock_ce_client.get_cost_and_usage.call_args_list
        assert token == 'tok-1'
        assert 'NextPageToken' not in first_call.kwargs
        assert second_call.kwargs.pop('NextPageToken') == 'tok-1'
        assert second_call.kwargs == first_call.kwargs
        assert second['data']['pagination']['complete_dataset'] is True
        assert 'warning' not in second['data']

    async def test_fetches_all_pages_by_default(self, mock_context, mock_ce_client):
        """With no max_items, every page is fetched and the dataset is complete."""
        mock_ce_client.get_cost_and_usage.side_effect = [
            {
                'ResultsByTime': [{'TimePeriod': {'Start': f'2023-01-0{i}'}}],
                'NextPageToken': f'page{i + 1}' if i < 3 else None,
            }
            for i in (1, 2, 3)
        ]

        result = await get_cost_and_usage(
            mock_context, mock_ce_client, start_date='2023-01-01', end_date='2023-01-31'
        )

        data = result['data']
        assert mock_ce_client.get_cost_and_usage.call_count == 3
        assert [r['TimePeriod']['Start'] for r in data['ResultsByTime']] == [
            '2023-01-01',
            '2023-01-02',
            '2023-01-03',
        ]
        assert data['pagination'] == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 3,
        }
        assert 'complete_dataset' not in data
        assert 'warning' not in data
        assert 'NextPageToken' not in data
        second_call = mock_ce_client.get_cost_and_usage.call_args_list[1].kwargs
        assert second_call['NextPageToken'] == 'page2'

    async def test_merges_page_metadata(self, mock_context, mock_ce_client):
        """Pages keep one GroupDefinitions and concatenate DimensionValueAttributes."""
        group_definitions = [{'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'}]
        mock_ce_client.get_cost_and_usage.side_effect = [
            {
                'GroupDefinitions': group_definitions,
                'ResultsByTime': [{'Groups': [{'Keys': ['111']}]}],
                'DimensionValueAttributes': [{'Value': '111', 'Attributes': {'description': 'a'}}],
                'NextPageToken': 'page2',
            },
            {
                'GroupDefinitions': group_definitions,
                'ResultsByTime': [{'Groups': [{'Keys': ['222']}]}],
                'DimensionValueAttributes': [{'Value': '222', 'Attributes': {'description': 'b'}}],
            },
        ]

        result = await get_cost_and_usage(
            mock_context, mock_ce_client, start_date='2023-01-01', end_date='2023-01-31'
        )

        data = result['data']
        assert data['GroupDefinitions'] == group_definitions
        assert [d['Value'] for d in data['DimensionValueAttributes']] == ['111', '222']
        assert len(data['ResultsByTime']) == 2

    async def test_repeated_dimension_value_attributes_are_deduplicated(
        self, mock_context, mock_ce_client
    ):
        """An account named on every page is listed once in the merged response."""
        attribute = {'Value': '111', 'Attributes': {'description': 'a'}}
        mock_ce_client.get_cost_and_usage.side_effect = [
            {
                'ResultsByTime': [{'Groups': [{'Keys': ['111']}]}],
                'DimensionValueAttributes': [attribute],
                'NextPageToken': 'page2',
            },
            {
                'ResultsByTime': [{'Groups': [{'Keys': ['111']}]}],
                'DimensionValueAttributes': [attribute],
            },
        ]

        result = await get_cost_and_usage(
            mock_context, mock_ce_client, start_date='2023-01-01', end_date='2023-01-31'
        )

        assert result['data']['DimensionValueAttributes'] == [attribute]

    async def test_dimension_value_attributes_without_value_are_all_kept(
        self, mock_context, mock_ce_client
    ):
        """Only entries with a Value are deduplicated; entries without one are kept as is."""
        unnamed = {'Attributes': {'description': 'no value'}}
        mock_ce_client.get_cost_and_usage.side_effect = [
            {
                'ResultsByTime': [{'Groups': [{'Keys': ['111']}]}],
                'DimensionValueAttributes': [unnamed, 'raw'],
                'NextPageToken': 'page2',
            },
            {
                'ResultsByTime': [{'Groups': [{'Keys': ['222']}]}],
                'DimensionValueAttributes': [unnamed, 'raw'],
            },
        ]

        result = await get_cost_and_usage(
            mock_context, mock_ce_client, start_date='2023-01-01', end_date='2023-01-31'
        )

        assert result['data']['DimensionValueAttributes'] == [unnamed, 'raw', unnamed, 'raw']

    async def test_partial_offload_flags_partial_ahead_of_preview(
        self, mock_context, mock_ce_client
    ):
        """A result stopped by max_items offloads with the partial signal before the data."""
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'},
                    'Groups': [
                        {
                            'Keys': ['Amazon EC2'],
                            'Metrics': {'UnblendedCost': {'Amount': '1.0', 'Unit': 'USD'}},
                        }
                    ],
                }
            ],
            'NextPageToken': 'more',
        }

        # Force SQL offload so we can inspect the offload sentinel.
        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.should_convert_to_sql',
            return_value=True,
        ):
            result = await get_cost_and_usage(
                mock_context,
                mock_ce_client,
                start_date='2023-01-01',
                end_date='2023-01-31',
                max_items=100,
            )

        data = result['data']
        keys = list(data)
        assert mock_ce_client.get_cost_and_usage.call_count == 1
        assert data['data_stored'] is True
        assert data['complete_dataset'] is False
        assert 'max_items' in data['warning']
        assert keys.index('warning') < keys.index('preview')
        assert keys.index('complete_dataset') < keys.index('sample_queries')
        assert data['pagination']['has_more'] is True
        assert data['pagination']['next_token'] == 'more'
        assert data['pagination']['items_returned'] == 1
        assert all(q['description'].startswith('PARTIAL DATA') for q in data['sample_queries'])

    async def test_complete_offload_has_no_warning(self, mock_context, mock_ce_client):
        """A complete offloaded result reports complete_dataset without a warning."""
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'}}],
        }

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.sql_utils.should_convert_to_sql',
            return_value=True,
        ):
            result = await get_cost_and_usage(
                mock_context, mock_ce_client, start_date='2023-01-01', end_date='2023-01-31'
            )

        data = result['data']
        assert data['pagination']['complete_dataset'] is True
        assert data['pagination']['has_more'] is False
        assert 'warning' not in data
        assert 'rows_retrieved' not in data
        assert not any(q['description'].startswith('PARTIAL DATA') for q in data['sample_queries'])


@pytest.mark.asyncio
class TestGetCostAndUsageWithResources:
    """Tests for get_cost_and_usage_with_resources function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_cost_and_usage_with_resources."""
        # We need to mock get_date_range to ensure our dates are used as is
        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.get_date_range',
            return_value=('2023-01-01', '2023-01-07'),
        ):
            result = await get_cost_and_usage_with_resources(
                mock_context,
                mock_ce_client,
                start_date='2023-01-01',
                end_date='2023-01-07',
                granularity='DAILY',
            )

            # Just verify that the function was called and returned success
            mock_ce_client.get_cost_and_usage_with_resources.assert_called_once()
            assert result['status'] == 'success'
            assert result['data'] is not None

    async def test_start_date_older_than_14_days_is_sent_unchanged(
        self, mock_context, mock_ce_client
    ):
        """A start date past the 14-day window is not clamped; the service validates it."""
        today = datetime.now()
        old_date = (today - timedelta(days=20)).strftime('%Y-%m-%d')

        await get_cost_and_usage_with_resources(
            mock_context,
            mock_ce_client,
            start_date=old_date,
            end_date=today.strftime('%Y-%m-%d'),
        )

        mock_ce_client.get_cost_and_usage_with_resources.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_and_usage_with_resources.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == old_date

    async def test_with_json_parameters(self, mock_context, mock_ce_client):
        """Test with JSON parameters for metrics, group_by, and filters."""
        metrics_json = '["UnblendedCost"]'
        group_by_json = '[{"Type": "RESOURCE", "Key": "RESOURCE_ID"}]'
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'

        await get_cost_and_usage_with_resources(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-07',
            granularity='DAILY',
            metrics=metrics_json,
            group_by=group_by_json,
            filter_expr=filter_json,
        )

        # The JSON arguments are parsed and sent as given.
        call_kwargs = mock_ce_client.get_cost_and_usage_with_resources.call_args[1]
        assert call_kwargs['Metrics'] == ['UnblendedCost']
        assert call_kwargs['GroupBy'] == [{'Type': 'RESOURCE', 'Key': 'RESOURCE_ID'}]
        assert call_kwargs['Filter'] == {
            'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}
        }

    @pytest.mark.parametrize('metrics, expected', METRICS_CASES)
    async def test_sends_and_stores_parsed_metrics(
        self, mock_context, mock_ce_client, metrics, expected
    ):
        """The parsed metrics, default applied, are sent to the API and stored with the result."""
        with _passthrough_store() as store:
            result = await get_cost_and_usage_with_resources(
                mock_context,
                mock_ce_client,
                start_date='2023-01-01',
                end_date='2023-01-07',
                metrics=metrics,
            )

        assert result['status'] == 'success'
        assert (
            mock_ce_client.get_cost_and_usage_with_resources.call_args.kwargs['Metrics']
            == expected
        )
        assert store.call_args.kwargs['metrics'] == expected

    @pytest.mark.parametrize(
        'metrics', ['["UnblendedCost", 1]', '{"a": 1}', [''], 5, 'UnblendedCost']
    )
    async def test_invalid_metrics_is_a_validation_error(
        self, mock_context, mock_ce_client, metrics
    ):
        """Invalid metrics are rejected before any API call."""
        result = await get_cost_and_usage_with_resources(
            mock_context, mock_ce_client, metrics=metrics
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        mock_ce_client.get_cost_and_usage_with_resources.assert_not_called()

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_cost_and_usage_with_resources."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_cost_and_usage_with_resources.side_effect = error

        # Test the actual error handling path
        result = await get_cost_and_usage_with_resources(mock_context, mock_ce_client)

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetDimensionValues:
    """Tests for get_dimension_values function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_dimension_values."""
        result = await get_dimension_values(
            mock_context,
            mock_ce_client,
            dimension='SERVICE',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        mock_ce_client.get_dimension_values.assert_called_once()
        call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-01-31'
        assert call_kwargs['Dimension'] == 'SERVICE'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_with_search_string(self, mock_context, mock_ce_client):
        """Test get_dimension_values with search string."""
        await get_dimension_values(
            mock_context,
            mock_ce_client,
            dimension='SERVICE',
            search_string='AWS',
        )

        call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
        assert 'SearchString' in call_kwargs
        assert call_kwargs['SearchString'] == 'AWS'

    async def test_with_filter(self, mock_context, mock_ce_client):
        """Test get_dimension_values with filter expression."""
        filter_json = '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}'
        filter_dict = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}

        # Mock the parse_json function to return our dictionary
        original_parse_json = __import__(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base',
            fromlist=['parse_json'],
        ).parse_json

        def mock_parse_json(json_string, label):
            if json_string == filter_json and label == 'filter':
                return filter_dict
            return original_parse_json(json_string, label)

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json',
            side_effect=mock_parse_json,
        ):
            await get_dimension_values(
                mock_context,
                mock_ce_client,
                dimension='SERVICE',
                filter_expr=filter_json,
            )

            # Verify the client was called with parsed filter
            call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
            assert 'Filter' in call_kwargs

    async def test_never_sends_max_results(self, mock_context, mock_ce_client):
        """MaxResults is ignored without SortBy, so max_items is not sent as a page size."""
        await get_dimension_values(
            mock_context,
            mock_ce_client,
            dimension='SERVICE',
            max_items=50,
        )

        call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
        assert 'MaxResults' not in call_kwargs

    async def test_fetches_every_page_without_max_items(self, mock_context, mock_ce_client):
        """Without max_items every page is fetched and merged."""
        mock_ce_client.get_dimension_values.side_effect = [
            {'DimensionValues': [{'Value': 'a'}], 'NextPageToken': 'p2'},
            {'DimensionValues': [{'Value': 'b'}], 'NextPageToken': 'p3'},
            {'DimensionValues': [{'Value': 'c'}]},
        ]

        result = await get_dimension_values(mock_context, mock_ce_client, dimension='SERVICE')

        data = result['data']
        assert [v['Value'] for v in data['DimensionValues']] == ['a', 'b', 'c']
        assert data['pagination']['complete_dataset'] is True
        assert 'warning' not in data

    async def test_max_items_stops_before_a_5000_value_page(self, mock_context, mock_ce_client):
        """Pages hold up to 5,000 values, so max_items below that stops after one page."""
        mock_ce_client.get_dimension_values.return_value = {
            'DimensionValues': [{'Value': 'a'}, {'Value': 'b'}],
            'NextPageToken': 'p2',
        }

        result = await get_dimension_values(
            mock_context, mock_ce_client, dimension='SERVICE', max_items=5001
        )

        assert mock_ce_client.get_dimension_values.call_count == 1
        assert result['data']['pagination']['next_token'] == 'p2'
        assert result['data']['complete_dataset'] is False

    async def test_max_items_allows_a_further_full_page(self, mock_context, mock_ce_client):
        """A second page is fetched when even a full one cannot pass max_items."""
        mock_ce_client.get_dimension_values.side_effect = [
            {'DimensionValues': [{'Value': 'a'}], 'NextPageToken': 'p2'},
            {'DimensionValues': [{'Value': 'b'}], 'NextPageToken': 'p3'},
        ]

        result = await get_dimension_values(
            mock_context, mock_ce_client, dimension='SERVICE', max_items=5001
        )

        assert mock_ce_client.get_dimension_values.call_count == 2
        assert result['data']['pagination']['next_token'] == 'p3'

    async def test_continuation_resends_identical_params(self, mock_context, mock_ce_client):
        """A continuation sends the caller's token and otherwise the same request."""
        mock_ce_client.get_dimension_values.return_value = {'DimensionValues': []}
        args = {
            'dimension': 'LINKED_ACCOUNT',
            'start_date': '2023-01-01',
            'end_date': '2023-01-31',
            'search_string': 'prod',
            'context': 'COST_AND_USAGE',
        }

        await get_dimension_values(mock_context, mock_ce_client, max_items=10, **args)
        await get_dimension_values(
            mock_context, mock_ce_client, max_items=10, next_token='tok', **args
        )

        first_call, second_call = mock_ce_client.get_dimension_values.call_args_list
        assert second_call.kwargs.pop('NextPageToken') == 'tok'
        assert second_call.kwargs == first_call.kwargs

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_dimension_values."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_dimension_values.side_effect = error

        # Test the actual error handling path
        result = await get_dimension_values(mock_context, mock_ce_client, dimension='SERVICE')

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result

    async def test_size_fields_describe_merged_pages(self, mock_context, mock_ce_client):
        """ReturnSize counts every merged value; TotalSize is kept from the first page."""
        mock_ce_client.get_dimension_values.side_effect = [
            {
                'DimensionValues': [{'Value': 'a'}],
                'ReturnSize': 1,
                'TotalSize': 2,
                'NextPageToken': 'page2',
            },
            {'DimensionValues': [{'Value': 'b'}], 'ReturnSize': 1, 'TotalSize': 2},
        ]

        result = await get_dimension_values(mock_context, mock_ce_client, 'SERVICE')

        assert result['data']['ReturnSize'] == 2
        assert result['data']['TotalSize'] == 2
        assert [v['Value'] for v in result['data']['DimensionValues']] == ['a', 'b']


@pytest.mark.asyncio
class TestGetCostForecast:
    """Tests for get_cost_forecast function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_cost_forecast."""
        result = await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            start_date='2023-02-01',
            end_date='2023-02-28',
        )

        mock_ce_client.get_cost_forecast.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-02-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-02-28'
        assert call_kwargs['Metric'] == 'UNBLENDED_COST'
        assert call_kwargs['Granularity'] == 'MONTHLY'  # Default
        assert call_kwargs['PredictionIntervalLevel'] == 80  # Default

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_default_future_dates(self, mock_context, mock_ce_client):
        """Test default future dates for forecasting."""
        await get_cost_forecast(mock_context, mock_ce_client, metric='UNBLENDED_COST')

        # Verify API was called with future dates
        mock_ce_client.get_cost_forecast.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
        assert 'TimePeriod' in call_kwargs
        assert 'Start' in call_kwargs['TimePeriod']
        assert 'End' in call_kwargs['TimePeriod']

        # Start date should be tomorrow or later
        start_date = datetime.strptime(call_kwargs['TimePeriod']['Start'], '%Y-%m-%d')
        today = datetime.now()
        assert start_date > today  # Start date should be in the future

    async def test_with_filter(self, mock_context, mock_ce_client):
        """Test get_cost_forecast with filter expression."""
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'
        filter_dict = {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}}

        # Mock the parse_json function to return our dictionary
        original_parse_json = __import__(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base',
            fromlist=['parse_json'],
        ).parse_json

        def mock_parse_json(json_string, label):
            if json_string == filter_json and label == 'filter':
                return filter_dict
            return original_parse_json(json_string, label)

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json',
            side_effect=mock_parse_json,
        ):
            await get_cost_forecast(
                mock_context,
                mock_ce_client,
                metric='UNBLENDED_COST',
                filter_expr=filter_json,
            )

            # Verify the client was called with parsed filter
            call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
            assert 'Filter' in call_kwargs

    async def test_with_custom_prediction_interval(self, mock_context, mock_ce_client):
        """Test get_cost_forecast with custom prediction interval."""
        await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            prediction_interval_level=95,
        )

        call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
        assert call_kwargs['PredictionIntervalLevel'] == 95

    async def test_with_different_granularity(self, mock_context, mock_ce_client):
        """Test get_cost_forecast with different granularity."""
        await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            granularity='DAILY',
        )

        call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
        assert call_kwargs['Granularity'] == 'DAILY'

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_cost_forecast."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_cost_forecast.side_effect = error

        # Test the actual error handling path
        result = await get_cost_forecast(mock_context, mock_ce_client, metric='UNBLENDED_COST')

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetUsageForecast:
    """Tests for get_usage_forecast function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_usage_forecast."""
        result = await get_usage_forecast(
            mock_context,
            mock_ce_client,
            metric='STORAGE_FORECAST',
            start_date='2023-02-01',
            end_date='2023-02-28',
        )

        mock_ce_client.get_usage_forecast.assert_called_once()
        call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-02-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-02-28'
        assert call_kwargs['Metric'] == 'STORAGE_FORECAST'
        assert call_kwargs['Granularity'] == 'MONTHLY'  # Default
        assert call_kwargs['PredictionIntervalLevel'] == 80  # Default

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_default_future_dates(self, mock_context, mock_ce_client):
        """Test default future dates for forecasting."""
        await get_usage_forecast(mock_context, mock_ce_client, metric='STORAGE_FORECAST')

        # Verify API was called with future dates
        mock_ce_client.get_usage_forecast.assert_called_once()
        call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
        assert 'TimePeriod' in call_kwargs
        assert 'Start' in call_kwargs['TimePeriod']
        assert 'End' in call_kwargs['TimePeriod']

        # Start date should be tomorrow or later
        start_date = datetime.strptime(call_kwargs['TimePeriod']['Start'], '%Y-%m-%d')
        today = datetime.now()
        assert start_date > today  # Start date should be in the future

    async def test_with_filter(self, mock_context, mock_ce_client):
        """Test get_usage_forecast with filter expression."""
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon S3"]}}'
        filter_dict = {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon S3']}}

        # Mock the parse_json function to return our dictionary
        original_parse_json = __import__(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base',
            fromlist=['parse_json'],
        ).parse_json

        def mock_parse_json(json_string, label):
            if json_string == filter_json and label == 'filter':
                return filter_dict
            return original_parse_json(json_string, label)

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json',
            side_effect=mock_parse_json,
        ):
            await get_usage_forecast(
                mock_context,
                mock_ce_client,
                metric='STORAGE_FORECAST',
                filter_expr=filter_json,
            )

            # Verify the client was called with parsed filter
            call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
            assert 'Filter' in call_kwargs

    async def test_with_custom_prediction_interval(self, mock_context, mock_ce_client):
        """Test get_usage_forecast with custom prediction interval."""
        await get_usage_forecast(
            mock_context,
            mock_ce_client,
            metric='STORAGE_FORECAST',
            prediction_interval_level=90,
        )

        call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
        assert call_kwargs['PredictionIntervalLevel'] == 90

    async def test_with_different_granularity(self, mock_context, mock_ce_client):
        """Test get_usage_forecast with different granularity."""
        await get_usage_forecast(
            mock_context,
            mock_ce_client,
            metric='STORAGE_FORECAST',
            granularity='DAILY',
        )

        call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
        assert call_kwargs['Granularity'] == 'DAILY'

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_usage_forecast."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_usage_forecast.side_effect = error

        # Test the actual error handling path
        result = await get_usage_forecast(mock_context, mock_ce_client, metric='STORAGE_FORECAST')

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


def _forecast_response(*periods):
    """Build a forecast response with one MeanValue per (start, end) period."""
    return {
        'Total': {'Amount': str(100.0 * len(periods)), 'Unit': 'USD'},
        'ForecastResultsByTime': [
            {'TimePeriod': {'Start': start, 'End': end}, 'MeanValue': '100.0'}
            for start, end in periods
        ],
    }


def _today_is(day):
    """Patch the operations module's clock so the UTC date is ``day`` (YYYY-MM-DD)."""
    fixed = datetime.strptime(day, '%Y-%m-%d').replace(hour=12, tzinfo=timezone.utc)

    class _Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            # A local clock a day behind UTC, so a check that ignores UTC fails.
            return fixed if tz else fixed.replace(tzinfo=None) - timedelta(days=1)

    return patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_explorer_operations.datetime',
        _Clock,
    )


@pytest.mark.asyncio
class TestForecastPeriodNote:
    """MONTHLY forecasts widen a partial-month request to whole calendar months."""

    @pytest.mark.parametrize(
        'operation, api, measure, metric',
        [
            (get_cost_forecast, 'get_cost_forecast', 'costs', 'UNBLENDED_COST'),
            (get_usage_forecast, 'get_usage_forecast', 'usage', 'USAGE_QUANTITY'),
        ],
    )
    async def test_mid_month_start_in_current_month_flags_actuals(
        self, mock_context, mock_ce_client, operation, api, measure, metric
    ):
        """A start moved back to a 1st before today puts month-to-date actuals in the result."""
        getattr(mock_ce_client, api).return_value = _forecast_response(
            ('2026-02-01', '2026-03-01'), ('2026-03-01', '2026-04-01')
        )

        with _today_is('2026-02-19'):
            result = await operation(
                mock_context,
                mock_ce_client,
                metric=metric,
                start_date='2026-02-20',
                end_date='2026-04-01',
            )

        data = result['data']
        assert list(data)[0] == 'period_note'
        note = data['period_note']
        assert '2026-02-01 to 2026-04-01' in note
        assert 'not the requested 2026-02-20 to 2026-04-01' in note
        assert f'include actual {measure} from 2026-02-01 to date' in note
        assert 'use DAILY granularity' in note
        # The API's own periods and total are returned unchanged.
        assert data['ForecastResultsByTime'][0]['TimePeriod']['Start'] == '2026-02-01'
        assert data['Total']['Amount'] == '200.0'

    @pytest.mark.parametrize(
        'today, has_actuals',
        [
            ('2026-05-02', True),  # first period starts before today
            ('2026-05-01', False),  # first period starts today: nothing has happened yet
            ('2026-04-20', False),  # future mid-month start moved back: all forecast
        ],
    )
    async def test_actuals_clause_only_when_first_period_starts_before_today(
        self, mock_context, mock_ce_client, today, has_actuals
    ):
        """The actuals clause depends on the covered start versus today's UTC date."""
        mock_ce_client.get_cost_forecast.return_value = _forecast_response(
            ('2026-05-01', '2026-06-01')
        )

        with _today_is(today):
            result = await get_cost_forecast(
                mock_context,
                mock_ce_client,
                metric='UNBLENDED_COST',
                start_date='2026-05-10',
                end_date='2026-06-01',
            )

        note = result['data']['period_note']
        assert ('include actual costs' in note) is has_actuals

    async def test_end_rounded_up_in_future_month_has_no_actuals_clause(
        self, mock_context, mock_ce_client
    ):
        """A widened period that starts after today is all forecast, so no actuals clause."""
        mock_ce_client.get_cost_forecast.return_value = _forecast_response(
            ('2099-05-01', '2099-06-01')
        )

        result = await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            start_date='2099-05-01',
            end_date='2099-05-15',
        )

        note = result['data']['period_note']
        assert '2099-05-01 to 2099-06-01' in note
        assert 'not the requested 2099-05-01 to 2099-05-15' in note
        assert 'actual costs' not in note

    async def test_whole_month_request_has_no_note(self, mock_context, mock_ce_client):
        """A request on month boundaries comes back as asked, so nothing is added."""
        mock_ce_client.get_cost_forecast.return_value = _forecast_response(
            ('2099-05-01', '2099-06-01')
        )

        result = await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            start_date='2099-05-01',
            end_date='2099-06-01',
        )

        assert 'period_note' not in result['data']

    async def test_daily_request_has_no_note(self, mock_context, mock_ce_client):
        """DAILY periods match the request, so nothing is added."""
        mock_ce_client.get_cost_forecast.return_value = _forecast_response(
            ('2099-05-14', '2099-05-15'), ('2099-05-15', '2099-05-16')
        )

        result = await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            start_date='2099-05-14',
            end_date='2099-05-16',
            granularity='DAILY',
        )

        assert 'period_note' not in result['data']

    async def test_daily_mismatch_has_no_note(self, mock_context, mock_ce_client):
        """Only MONTHLY is widened to months, so a DAILY response that differs gets no note."""
        mock_ce_client.get_cost_forecast.return_value = _forecast_response(
            ('2099-05-15', '2099-05-16')
        )

        result = await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            start_date='2099-05-14',
            end_date='2099-05-16',
            granularity='DAILY',
        )

        assert 'period_note' not in result['data']

    async def test_period_without_dates_has_no_note(self, mock_context, mock_ce_client):
        """A period missing its dates is returned as is, not turned into an error."""
        mock_ce_client.get_cost_forecast.return_value = {
            'ForecastResultsByTime': [{'MeanValue': '1.0'}]
        }

        result = await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            start_date='2099-05-14',
            end_date='2099-06-01',
        )

        assert result['status'] == 'success'
        assert 'period_note' not in result['data']

    async def test_no_periods_has_no_note(self, mock_context, mock_ce_client):
        """An empty result has no covered period to compare."""
        mock_ce_client.get_usage_forecast.return_value = {'ForecastResultsByTime': []}

        result = await get_usage_forecast(
            mock_context,
            mock_ce_client,
            metric='USAGE_QUANTITY',
            start_date='2099-05-14',
            end_date='2099-06-01',
        )

        assert 'period_note' not in result['data']

    async def test_note_is_kept_when_offloaded(self, mock_context, mock_ce_client):
        """The note is passed to the offload so a stored result still carries it."""
        mock_ce_client.get_cost_forecast.return_value = _forecast_response(
            ('2023-02-01', '2023-03-01')
        )

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.cost_explorer_operations.convert_response_if_needed',
            new_callable=AsyncMock,
            return_value={'data_stored': True},
        ) as convert:
            await get_cost_forecast(
                mock_context,
                mock_ce_client,
                metric='UNBLENDED_COST',
                start_date='2023-02-20',
                end_date='2023-03-01',
            )

        assert '2023-02-01 to 2023-03-01' in convert.call_args.kwargs['period_note']


@pytest.mark.asyncio
class TestGetTags:
    """Tests for get_tags function."""

    async def test_get_tags_basic(self, mock_context, mock_ce_client):
        """Test basic call to get_tags."""
        result = await get_tags(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        mock_ce_client.get_tags.assert_called_once()
        call_kwargs = mock_ce_client.get_tags.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-01-31'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_get_tag_values(self, mock_context, mock_ce_client):
        """Test get_tags with tag_key to get tag values."""
        result = await get_tags(
            mock_context,
            mock_ce_client,
            tag_key='Environment',
        )

        mock_ce_client.get_tags.assert_called_once()
        call_kwargs = mock_ce_client.get_tags.call_args[1]
        assert 'TagKey' in call_kwargs
        assert call_kwargs['TagKey'] == 'Environment'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_paginated_tag_values_are_collected_from_tags(
        self, mock_context, mock_ce_client
    ):
        """Paginated tag values come back under 'Tags' (CE GetTags), not 'TagValues'."""
        mock_ce_client.get_tags.side_effect = [
            {'Tags': ['dev', 'prod'], 'NextPageToken': 'page-2'},
            {'Tags': ['test']},
        ]

        result = await get_tags(
            mock_context,
            mock_ce_client,
            tag_key='Environment',
        )

        assert result['status'] == 'success'
        assert result['data']['Tags'] == ['dev', 'prod', 'test']
        assert 'TagValues' not in result['data']
        assert mock_ce_client.get_tags.call_count == 2
        second_call = mock_ce_client.get_tags.call_args_list[1][1]
        assert second_call['TagKey'] == 'Environment'
        assert second_call['NextPageToken'] == 'page-2'

    async def test_paginated_tag_keys_are_collected_from_tags(self, mock_context, mock_ce_client):
        """Paginated tag keys (no TagKey) are still read from 'Tags'."""
        mock_ce_client.get_tags.return_value = {'Tags': ['Environment', 'Project']}

        result = await get_tags(mock_context, mock_ce_client)

        assert result['data']['Tags'] == ['Environment', 'Project']
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_max_items_stops_and_continuation_matches(self, mock_context, mock_ce_client):
        """max_items stops after a page; the continuation resends the request with the token."""
        mock_ce_client.get_tags.return_value = {'Tags': ['a', 'b'], 'NextPageToken': 'p2'}

        first = await get_tags(mock_context, mock_ce_client, tag_key='Env', max_items=100)
        await get_tags(mock_context, mock_ce_client, tag_key='Env', max_items=100, next_token='p2')

        assert first['data']['complete_dataset'] is False
        assert first['data']['pagination']['next_token'] == 'p2'
        first_call, second_call = mock_ce_client.get_tags.call_args_list
        assert second_call.kwargs.pop('NextPageToken') == 'p2'
        assert second_call.kwargs == first_call.kwargs
        assert 'MaxResults' not in first_call.kwargs

    async def test_paginated_tag_values_from_next_token(self, mock_context, mock_ce_client):
        """Resuming with next_token sends the token and reads values from 'Tags'."""
        mock_ce_client.get_tags.return_value = {'Tags': ['staging']}

        result = await get_tags(
            mock_context,
            mock_ce_client,
            tag_key='Environment',
            next_token='resume-token',
        )

        call_kwargs = mock_ce_client.get_tags.call_args[1]
        assert call_kwargs['NextPageToken'] == 'resume-token'
        assert result['data']['Tags'] == ['staging']

    async def test_paginated_tag_values_empty_page(self, mock_context, mock_ce_client):
        """A tag key with no values yields an empty list, not an error."""
        mock_ce_client.get_tags.return_value = {'Tags': []}

        result = await get_tags(mock_context, mock_ce_client, tag_key='Unused')

        assert result['status'] == 'success'
        assert result['data']['Tags'] == []

    async def test_with_search_string(self, mock_context, mock_ce_client):
        """Test get_tags with search string."""
        await get_tags(
            mock_context,
            mock_ce_client,
            search_string='Env',
        )

        call_kwargs = mock_ce_client.get_tags.call_args[1]
        assert 'SearchString' in call_kwargs
        assert call_kwargs['SearchString'] == 'Env'

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_tags."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_tags.side_effect = error

        # Test the actual error handling path
        result = await get_tags(mock_context, mock_ce_client)

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetCostCategories:
    """Tests for get_cost_categories function."""

    async def test_get_cost_categories_basic(self, mock_context, mock_ce_client):
        """Test basic call to get_cost_categories."""
        result = await get_cost_categories(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        mock_ce_client.get_cost_categories.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_categories.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-01-31'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_category_names_collected_across_pages(self, mock_context, mock_ce_client):
        """Paged names are read from CostCategoryNames, the key the API returns."""
        mock_ce_client.get_cost_categories.side_effect = [
            {'CostCategoryNames': ['Department'], 'NextPageToken': 'page2'},
            {'CostCategoryNames': ['Team']},
        ]

        result = await get_cost_categories(mock_context, mock_ce_client)

        assert result['data']['CostCategoryNames'] == ['Department', 'Team']
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_category_values_max_items_stop_and_continuation(
        self, mock_context, mock_ce_client
    ):
        """Values are read from CostCategoryValues; max_items stops, continuation matches."""
        mock_ce_client.get_cost_categories.return_value = {
            'CostCategoryValues': ['eng', 'ops'],
            'ReturnSize': 2,
            'TotalSize': 9000,
            'NextPageToken': 'p2',
        }

        first = await get_cost_categories(
            mock_context, mock_ce_client, cost_category_name='Team', max_items=10
        )
        await get_cost_categories(
            mock_context, mock_ce_client, cost_category_name='Team', max_items=10, next_token='p2'
        )

        data = first['data']
        assert data['CostCategoryValues'] == ['eng', 'ops']
        assert data['TotalSize'] == 9000
        assert data['complete_dataset'] is False
        assert data['pagination']['next_token'] == 'p2'
        first_call, second_call = mock_ce_client.get_cost_categories.call_args_list
        assert second_call.kwargs.pop('NextPageToken') == 'p2'
        assert second_call.kwargs == first_call.kwargs

    async def test_category_name_is_not_logged(self, mock_context, mock_ce_client):
        """The cost category name is customer content and stays out of log messages."""
        await get_cost_categories(mock_context, mock_ce_client, cost_category_name='SecretProject')

        logged = ' '.join(str(c) for c in mock_context.info.call_args_list)
        assert 'SecretProject' not in logged

    async def test_get_cost_category_values(self, mock_context, mock_ce_client):
        """Test get_cost_categories with cost_category_name to get values.

        AWS GetCostCategories is a single API: passing CostCategoryName makes
        it return CostCategoryValues from the same get_cost_categories method.
        """
        result = await get_cost_categories(
            mock_context,
            mock_ce_client,
            cost_category_name='Department',
        )

        mock_ce_client.get_cost_categories.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_categories.call_args[1]
        assert 'CostCategoryName' in call_kwargs
        assert call_kwargs['CostCategoryName'] == 'Department'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_with_search_string(self, mock_context, mock_ce_client):
        """Test get_cost_categories with search string."""
        await get_cost_categories(
            mock_context,
            mock_ce_client,
            search_string='Dep',
        )

        call_kwargs = mock_ce_client.get_cost_categories.call_args[1]
        assert 'SearchString' in call_kwargs
        assert call_kwargs['SearchString'] == 'Dep'

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_cost_categories."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_cost_categories.side_effect = error

        # Test the actual error handling path
        result = await get_cost_categories(mock_context, mock_ce_client)

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetSavingsPlansUtilization:
    """Tests for get_savings_plans_utilization function."""

    async def test_monthly_entries_wider_than_request_get_period_note(self, mock_context):
        """MONTHLY entries labelled with whole months that the window cuts are flagged."""
        client = MagicMock()
        entries = [
            {'TimePeriod': {'Start': '2026-08-01', 'End': '2026-09-01'}},
            {'TimePeriod': {'Start': '2026-09-01', 'End': '2026-10-01'}},
        ]
        client.get_savings_plans_utilization.return_value = {
            'SavingsPlansUtilizationsByTime': entries,
            'Total': {},
        }

        result = await get_savings_plans_utilization(
            mock_context, client, '2026-08-17', '2026-09-10', 'MONTHLY'
        )

        data = result['data']
        assert data['SavingsPlansUtilizationsByTime'] == entries
        assert (
            'first entry, labelled 2026-08-01 to 2026-09-01, covers only 2026-08-17'
            in (data['period_note'])
        )
        assert (
            'last entry, labelled 2026-09-01 to 2026-10-01, covers only the days before'
            in (data['period_note'])
        )

    async def test_whole_month_request_has_no_period_note(self, mock_context):
        """Labels that match the request need no note."""
        client = MagicMock()
        client.get_savings_plans_utilization.return_value = {
            'SavingsPlansUtilizationsByTime': [
                {'TimePeriod': {'Start': '2026-08-01', 'End': '2026-09-01'}}
            ],
        }

        result = await get_savings_plans_utilization(
            mock_context, client, '2026-08-01', '2026-09-01', 'MONTHLY'
        )

        assert 'period_note' not in result['data']

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_savings_plans_utilization."""
        result = await get_savings_plans_utilization(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            granularity='MONTHLY',
        )

        mock_ce_client.get_savings_plans_utilization.assert_called_once()
        call_kwargs = mock_ce_client.get_savings_plans_utilization.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-01-31'
        assert call_kwargs['Granularity'] == 'MONTHLY'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_with_filter(self, mock_context, mock_ce_client):
        """Test get_savings_plans_utilization with filter expression."""
        filter_json = '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}'
        filter_dict = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}

        # Mock the parse_json function to return our dictionary
        original_parse_json = __import__(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base',
            fromlist=['parse_json'],
        ).parse_json

        def mock_parse_json(json_string, label):
            if json_string == filter_json and label == 'filter':
                return filter_dict
            return original_parse_json(json_string, label)

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json',
            side_effect=mock_parse_json,
        ):
            await get_savings_plans_utilization(
                mock_context,
                mock_ce_client,
                filter_expr=filter_json,
            )

            # Verify the client was called with parsed filter
            call_kwargs = mock_ce_client.get_savings_plans_utilization.call_args[1]
            assert 'Filter' in call_kwargs

    async def test_is_a_single_call_without_a_token(self, mock_context, mock_ce_client):
        """GetSavingsPlansUtilization is not paginated: one call, no token parameter."""
        mock_ce_client.get_savings_plans_utilization.return_value = {
            'SavingsPlansUtilizationsByTime': [],
            'Total': {},
        }

        result = await get_savings_plans_utilization(mock_context, mock_ce_client)

        mock_ce_client.get_savings_plans_utilization.assert_called_once()
        call_kwargs = mock_ce_client.get_savings_plans_utilization.call_args.kwargs
        assert 'NextToken' not in call_kwargs
        assert 'pagination' not in result['data']

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_savings_plans_utilization."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_savings_plans_utilization.side_effect = error

        # Test the actual error handling path
        result = await get_savings_plans_utilization(mock_context, mock_ce_client)

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


# Pagination contract — agent-supplied next_token must be injected into the
# first boto3 request for every paginated CE operation. Pre-fix, only its
# truthiness was used (as a flag to enable paginate-mode); the value was lost.


@pytest.mark.parametrize(
    'op_func, ce_method, result_key, token_key, kwargs',
    [
        (
            get_cost_and_usage,
            'get_cost_and_usage',
            'ResultsByTime',
            'NextPageToken',
            {'start_date': '2023-01-01', 'end_date': '2023-01-31'},
        ),
        (
            get_cost_and_usage_with_resources,
            'get_cost_and_usage_with_resources',
            'ResultsByTime',
            'NextPageToken',
            {'start_date': '2023-01-01', 'end_date': '2023-01-07'},
        ),
        (
            get_dimension_values,
            'get_dimension_values',
            'DimensionValues',
            'NextPageToken',
            {'dimension': 'SERVICE', 'start_date': '2023-01-01', 'end_date': '2023-01-31'},
        ),
        (
            get_tags,
            'get_tags',
            'Tags',
            'NextPageToken',
            {'start_date': '2023-01-01', 'end_date': '2023-01-31'},
        ),
        (
            get_cost_categories,
            'get_cost_categories',
            'CostCategoryNames',
            'NextPageToken',
            {'start_date': '2023-01-01', 'end_date': '2023-01-31'},
        ),
    ],
)
@pytest.mark.asyncio
async def test_caller_next_token_injected_into_first_request(
    mock_context, mock_ce_client, op_func, ce_method, result_key, token_key, kwargs
):
    """Caller's next_token reaches the first boto3 call for every paginated CE op."""
    getattr(mock_ce_client, ce_method).return_value = {result_key: []}

    await op_func(
        mock_context,
        mock_ce_client,
        next_token='resume-from-here',
        **kwargs,
    )

    first_call_kwargs = getattr(mock_ce_client, ce_method).call_args_list[0][1]
    assert first_call_kwargs.get(token_key) == 'resume-from-here'


@pytest.mark.parametrize(
    'op_func, ce_method, result_key, token_key, kwargs',
    [
        (
            get_cost_and_usage,
            'get_cost_and_usage',
            'ResultsByTime',
            'NextPageToken',
            {'start_date': '2023-01-01', 'end_date': '2023-01-31'},
        ),
        (
            get_cost_and_usage_with_resources,
            'get_cost_and_usage_with_resources',
            'ResultsByTime',
            'NextPageToken',
            {'start_date': '2023-01-01', 'end_date': '2023-01-07'},
        ),
        (
            get_dimension_values,
            'get_dimension_values',
            'DimensionValues',
            'NextPageToken',
            {'dimension': 'SERVICE', 'start_date': '2023-01-01', 'end_date': '2023-01-31'},
        ),
        (
            get_tags,
            'get_tags',
            'Tags',
            'NextPageToken',
            {'start_date': '2023-01-01', 'end_date': '2023-01-31'},
        ),
        (
            get_cost_categories,
            'get_cost_categories',
            'CostCategoryNames',
            'NextPageToken',
            {'start_date': '2023-01-01', 'end_date': '2023-01-31'},
        ),
    ],
)
@pytest.mark.asyncio
async def test_max_items_without_next_token_omits_token_from_first_request(
    mock_context, mock_ce_client, op_func, ce_method, result_key, token_key, kwargs
):
    """With max_items but no next_token, the first request carries no token or page size."""
    getattr(mock_ce_client, ce_method).return_value = {result_key: []}

    await op_func(
        mock_context,
        mock_ce_client,
        next_token=None,
        max_items=1,
        **kwargs,
    )

    first_call_kwargs = getattr(mock_ce_client, ce_method).call_args_list[0][1]
    assert token_key not in first_call_kwargs
    assert 'MaxResults' not in first_call_kwargs
