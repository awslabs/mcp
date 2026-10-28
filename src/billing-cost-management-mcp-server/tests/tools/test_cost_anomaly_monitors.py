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

"""Tests for the cost-anomaly-monitors tool (anomaly monitors and alert subscriptions)."""

import fastmcp
import pytest
from awslabs.billing_cost_management_mcp_server.tools.cost_anomaly_tools import (
    cost_anomaly_server,
)
from botocore.exceptions import ClientError
from fastmcp import Context
from fastmcp.tools import FunctionTool
from mcp.types import TextContent
from unittest.mock import AsyncMock, MagicMock, patch


CLIENT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.cost_anomaly_tools.create_aws_client'
)
MONITOR_ARN = 'arn:aws:ce::123456789012:anomalymonitor/11111111-2222-3333-4444-555555555555'

DIMENSIONAL_MONITOR = {
    'MonitorArn': MONITOR_ARN,
    'MonitorName': 'Services',
    'CreationDate': '2024-01-01',
    'LastUpdatedDate': '2024-02-01',
    'LastEvaluatedDate': '2024-03-01',
    'MonitorType': 'DIMENSIONAL',
    'MonitorDimension': 'SERVICE',
    'DimensionalValueCount': 54,
}
CUSTOM_MONITOR = {
    'MonitorArn': 'arn:aws:ce::123456789012:anomalymonitor/custom',
    'MonitorName': 'Team tag',
    'MonitorType': 'CUSTOM',
    'MonitorSpecification': {'Tags': {'Key': 'team', 'Values': ['a']}},
    'DimensionalValueCount': 0,
}
SUBSCRIPTION = {
    'SubscriptionArn': 'arn:aws:ce::123456789012:anomalysubscription/sub-1',
    'SubscriptionName': 'Daily digest',
    'AccountId': '123456789012',
    'MonitorArnList': [MONITOR_ARN],
    'Subscribers': [{'Address': 'ops@example.com', 'Type': 'EMAIL', 'Status': 'CONFIRMED'}],
    'Threshold': 100.0,
    'Frequency': 'DAILY',
    'ThresholdExpression': {
        'Dimensions': {
            'Key': 'ANOMALY_TOTAL_IMPACT_ABSOLUTE',
            'Values': ['100'],
            'MatchOptions': ['GREATER_THAN_OR_EQUAL'],
        }
    },
}


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


async def _tool() -> FunctionTool:
    tool = await cost_anomaly_server.get_tool('cost-anomaly-monitors')
    assert isinstance(tool, FunctionTool)
    return tool


async def _call(mock_context, client, **kwargs):
    tool = await _tool()
    with patch(CLIENT_PATH, return_value=client) as create_client:
        result = await tool.fn(mock_context, **kwargs)
    return result, create_client


class TestListMonitors:
    """list_monitors wraps GetAnomalyMonitors."""

    async def test_formats_both_monitor_types(self, mock_context):
        """Each monitor keeps its type, dimension or specification and dates."""
        client = MagicMock()
        client.get_anomaly_monitors.return_value = {
            'AnomalyMonitors': [DIMENSIONAL_MONITOR, CUSTOM_MONITOR]
        }

        result, create_client = await _call(mock_context, client, operation='list_monitors')

        create_client.assert_called_once_with('ce', region_name='us-east-1')
        client.get_anomaly_monitors.assert_called_once_with(MaxResults=100)
        assert result['status'] == 'success'
        assert result['data']['monitors'] == [
            {
                'monitor_arn': MONITOR_ARN,
                'monitor_name': 'Services',
                'monitor_type': 'DIMENSIONAL',
                'monitor_dimension': 'SERVICE',
                'monitor_specification': None,
                'dimensional_value_count': 54,
                'creation_date': '2024-01-01',
                'last_updated_date': '2024-02-01',
                'last_evaluated_date': '2024-03-01',
            },
            {
                'monitor_arn': 'arn:aws:ce::123456789012:anomalymonitor/custom',
                'monitor_name': 'Team tag',
                'monitor_type': 'CUSTOM',
                'monitor_dimension': None,
                'monitor_specification': {'Tags': {'Key': 'team', 'Values': ['a']}},
                'dimensional_value_count': 0,
                'creation_date': None,
                'last_updated_date': None,
                'last_evaluated_date': None,
            },
        ]
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_operation_is_required_in_schema(self):
        """Operation has no default: the served schema lists it as required."""
        tool = await _tool()

        assert 'operation' in tool.parameters['required']
        assert 'default' not in tool.parameters['properties']['operation']

    @pytest.mark.parametrize('arguments', [{}, {'operation': None}, {'operation': 5}])
    async def test_missing_or_non_string_operation_fails_without_aws_call(self, arguments):
        """Over MCP, a missing or non-string operation fails argument validation; no client."""
        with patch(CLIENT_PATH) as create_client:
            async with fastmcp.Client(cost_anomaly_server) as client:
                result = await client.call_tool(
                    'cost-anomaly-monitors', arguments, raise_on_error=False
                )

        assert result.is_error
        content = result.content[0]
        assert isinstance(content, TextContent)
        assert 'operation' in content.text
        create_client.assert_not_called()

    @pytest.mark.parametrize(
        'operation',
        ['', ' list_monitors', 'list_monitors ', 'LIST_MONITORS', 'List_Subscriptions', None],
    )
    async def test_only_exact_operation_values_succeed(self, mock_context, operation):
        """Empty, padded, wrong-case and None values are a validation_error; no AWS call."""
        client = MagicMock()

        result, create_client = await _call(mock_context, client, operation=operation)

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['data']['invalid_parameter'] == 'operation'
        assert 'list_monitors' in result['message']
        assert 'list_subscriptions' in result['message']
        create_client.assert_not_called()

    async def test_bad_operation_is_reported_before_bad_monitor_arn(self, mock_context):
        """With both an invalid operation and an empty monitor_arn, the operation is reported."""
        result, create_client = await _call(
            mock_context, MagicMock(), operation='x', monitor_arn=' '
        )

        assert result['error_type'] == 'validation_error'
        assert result['data']['invalid_parameter'] == 'operation'
        create_client.assert_not_called()

    async def test_monitor_arn_filters_to_one_monitor(self, mock_context):
        """monitor_arn is sent as a one-item MonitorArnList."""
        client = MagicMock()
        client.get_anomaly_monitors.return_value = {'AnomalyMonitors': [DIMENSIONAL_MONITOR]}

        await _call(mock_context, client, operation='list_monitors', monitor_arn=MONITOR_ARN)

        client.get_anomaly_monitors.assert_called_once_with(
            MonitorArnList=[MONITOR_ARN], MaxResults=100
        )

    async def test_pages_until_no_token(self, mock_context):
        """Without max_items every page is fetched."""
        client = MagicMock()
        client.get_anomaly_monitors.side_effect = [
            {'AnomalyMonitors': [DIMENSIONAL_MONITOR], 'NextPageToken': 't2'},
            {'AnomalyMonitors': [CUSTOM_MONITOR]},
        ]

        result, _ = await _call(mock_context, client, operation='list_monitors')

        assert client.get_anomaly_monitors.call_args_list[1].kwargs == {
            'MaxResults': 100,
            'NextPageToken': 't2',
        }
        assert len(result['data']['monitors']) == 2

    async def test_max_items_and_next_token(self, mock_context):
        """max_items sizes the page; a remaining token marks the result partial."""
        client = MagicMock()
        client.get_anomaly_monitors.return_value = {
            'AnomalyMonitors': [DIMENSIONAL_MONITOR],
            'NextPageToken': 't3',
        }

        result, _ = await _call(
            mock_context, client, operation='list_monitors', max_items=1, next_token='t2'
        )

        client.get_anomaly_monitors.assert_called_once_with(MaxResults=1, NextPageToken='t2')
        assert result['data']['complete_dataset'] is False
        assert result['data']['pagination']['next_token'] == 't3'

    async def test_service_error_is_reported(self, mock_context):
        """A service error comes back as an error with the AWS code."""
        client = MagicMock()
        client.get_anomaly_monitors.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid MonitorArn specified'}},
            'GetAnomalyMonitors',
        )

        result, _ = await _call(
            mock_context, client, operation='list_monitors', monitor_arn='not-an-arn'
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'ValidationException'

    async def test_rejected_token_is_invalid_next_token(self, mock_context):
        """InvalidNextTokenException on the caller's token maps to invalid_next_token."""
        client = MagicMock()
        client.get_anomaly_monitors.side_effect = ClientError(
            {'Error': {'Code': 'InvalidNextTokenException', 'Message': 'bad token'}},
            'GetAnomalyMonitors',
        )

        result, _ = await _call(
            mock_context, client, operation='list_monitors', next_token='stale'
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'


class TestListSubscriptions:
    """list_subscriptions wraps GetAnomalySubscriptions."""

    async def test_formats_subscription(self, mock_context):
        """Each subscription keeps its monitors, threshold, frequency and subscribers."""
        client = MagicMock()
        client.get_anomaly_subscriptions.return_value = {'AnomalySubscriptions': [SUBSCRIPTION]}

        result, _ = await _call(mock_context, client, operation='list_subscriptions')

        client.get_anomaly_subscriptions.assert_called_once_with(MaxResults=100)
        assert result['status'] == 'success'
        assert result['data']['subscriptions'] == [
            {
                'subscription_arn': 'arn:aws:ce::123456789012:anomalysubscription/sub-1',
                'subscription_name': 'Daily digest',
                'account_id': '123456789012',
                'monitor_arn_list': [MONITOR_ARN],
                'frequency': 'DAILY',
                'threshold_expression': SUBSCRIPTION['ThresholdExpression'],
                'threshold': 100.0,
                'subscribers': [
                    {'address': 'ops@example.com', 'type': 'EMAIL', 'status': 'CONFIRMED'}
                ],
            }
        ]

    async def test_monitor_arn_filters_subscriptions(self, mock_context):
        """monitor_arn is sent as MonitorArn."""
        client = MagicMock()
        client.get_anomaly_subscriptions.return_value = {'AnomalySubscriptions': []}

        result, _ = await _call(
            mock_context, client, operation='list_subscriptions', monitor_arn=MONITOR_ARN
        )

        client.get_anomaly_subscriptions.assert_called_once_with(
            MonitorArn=MONITOR_ARN, MaxResults=100
        )
        assert result['data']['subscriptions'] == []

    async def test_subscription_without_monitors(self, mock_context):
        """A subscription with an empty MonitorArnList keeps the empty list."""
        client = MagicMock()
        client.get_anomaly_subscriptions.return_value = {
            'AnomalySubscriptions': [dict(SUBSCRIPTION, MonitorArnList=[])]
        }

        result, _ = await _call(mock_context, client, operation='list_subscriptions')

        assert result['data']['subscriptions'][0]['monitor_arn_list'] == []


class TestEdgeCases:
    """Error paths and argument checks shared by both operations."""

    async def test_subscriptions_page_until_no_token(self, mock_context):
        """list_subscriptions follows NextPageToken across pages."""
        client = MagicMock()
        client.get_anomaly_subscriptions.side_effect = [
            {'AnomalySubscriptions': [SUBSCRIPTION], 'NextPageToken': 't2'},
            {'AnomalySubscriptions': [dict(SUBSCRIPTION, SubscriptionArn='sub-2')]},
        ]

        result, _ = await _call(mock_context, client, operation='list_subscriptions')

        assert client.get_anomaly_subscriptions.call_args_list[1].kwargs == {
            'MaxResults': 100,
            'NextPageToken': 't2',
        }
        assert [s['subscription_arn'] for s in result['data']['subscriptions']] == [
            SUBSCRIPTION['SubscriptionArn'],
            'sub-2',
        ]
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_subscriptions_service_error_is_reported(self, mock_context):
        """A list_subscriptions service error comes back as an error with the AWS code."""
        client = MagicMock()
        client.get_anomaly_subscriptions.side_effect = ClientError(
            {'Error': {'Code': 'LimitExceededException', 'Message': 'Too many requests'}},
            'GetAnomalySubscriptions',
        )

        result, _ = await _call(mock_context, client, operation='list_subscriptions')

        assert result['status'] == 'error'
        assert result['error_type'] == 'LimitExceededException'

    async def test_client_creation_failure_is_reported(self, mock_context):
        """A failure creating the client is handled, not raised."""
        tool = await _tool()
        with patch(CLIENT_PATH, side_effect=ValueError('no credentials')):
            result = await tool.fn(mock_context, operation='list_monitors')

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'

    @pytest.mark.parametrize('monitor_arn', ['', '   '])
    async def test_empty_monitor_arn_is_rejected(self, mock_context, monitor_arn):
        """An empty monitor_arn is refused instead of silently listing everything."""
        client = MagicMock()

        result, create_client = await _call(
            mock_context, client, operation='list_subscriptions', monitor_arn=monitor_arn
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        create_client.assert_not_called()

    async def test_monitor_arn_is_stripped(self, mock_context):
        """Surrounding spaces are removed before the ARN is sent."""
        client = MagicMock()
        client.get_anomaly_monitors.return_value = {'AnomalyMonitors': []}

        await _call(
            mock_context, client, operation='list_monitors', monitor_arn=f'  {MONITOR_ARN} '
        )

        client.get_anomaly_monitors.assert_called_once_with(
            MonitorArnList=[MONITOR_ARN], MaxResults=100
        )

    async def test_max_items_zero_is_rejected_before_any_call(self, mock_context):
        """max_items below 1 is a validation error and no request is sent."""
        client = MagicMock()

        result, _ = await _call(mock_context, client, operation='list_monitors', max_items=0)

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        client.get_anomaly_monitors.assert_not_called()

    async def test_tag_monitor_keeps_its_specification(self, mock_context):
        """A TAG dimensional monitor returns the tag key from MonitorSpecification."""
        client = MagicMock()
        tag_monitor = dict(
            DIMENSIONAL_MONITOR,
            MonitorDimension='TAG',
            MonitorSpecification={'Tags': {'Key': 'team'}},
        )
        client.get_anomaly_monitors.return_value = {'AnomalyMonitors': [tag_monitor]}

        result, _ = await _call(mock_context, client, operation='list_monitors')

        monitor = result['data']['monitors'][0]
        assert monitor['monitor_dimension'] == 'TAG'
        assert monitor['monitor_specification'] == {'Tags': {'Key': 'team'}}


async def test_unsupported_operation(mock_context):
    """An unknown operation is a validation error naming the valid ones; no AWS call."""
    client = MagicMock()

    result, create_client = await _call(mock_context, client, operation='delete_monitor')

    assert result['status'] == 'error'
    assert result['error_type'] == 'validation_error'
    assert 'list_monitors' in result['message']
    assert 'list_subscriptions' in result['message']
    create_client.assert_not_called()


async def test_description_documents_monitors_and_subscriptions():
    """The served description explains monitor types and what subscriptions decide."""
    tool = await _tool()
    description = ' '.join((tool.description or '').split())

    for text in (
        'list_monitors',
        'list_subscriptions',
        'DIMENSIONAL',
        'CUSTOM',
        'monitor_dimension',
        'monitor_specification',
        'ANOMALY_TOTAL_IMPACT_ABSOLUTE',
        'ANOMALY_TOTAL_IMPACT_PERCENTAGE',
        'not what is detected',
        'monitor_arn_list',
        'read-only',
        'On either operation, a monitor ARN in this account that matches no monitor returns an empty list',
        'a malformed ARN is a ValidationException',
        "another account's ARN is an AccessDeniedException",
        'status DECLINED means the subscriber has declined',
        'read threshold_expression',
    ):
        assert text in description, text
    properties = tool.parameters['properties']
    assert set(properties) >= {'operation', 'monitor_arn', 'max_items', 'next_token'}


async def test_cost_anomaly_tool_is_unchanged():
    """The existing cost-anomaly tool keeps its name and required date parameters."""
    tool = await cost_anomaly_server.get_tool('cost-anomaly')
    assert isinstance(tool, FunctionTool)
    assert set(tool.parameters['required']) == {'start_date', 'end_date'}
