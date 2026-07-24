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

"""Unit tests for the Amazon Connect historical metric tools."""

import pytest
from awslabs.amazon_connect_mcp_server.connect_historical.tools import ConnectHistoricalTools
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


def _make_client(pages, capture=None, calls=None, queue_ids=('q-default',)):
    """Build a fake Connect client that returns the given pages from get_metric_data_v2.

    Args:
        pages: List of response dicts to return in sequence per call.
        capture: Optional dict that will receive the request kwargs of the last call.
        calls: Optional list that will receive the request kwargs of every call.
        queue_ids: Queue IDs returned by the list_queues paginator for the
            default-filter resolution path.
    """
    fake_client = MagicMock()
    fake_client.describe_instance.return_value = {
        'Instance': {'Arn': 'arn:aws:connect:us-east-1:111122223333:instance/inst-1'}
    }

    class _QueuePaginator:
        def paginate(self, **kwargs):
            yield {'QueueSummaryList': [{'Id': qid} for qid in queue_ids]}

    fake_client.get_paginator.return_value = _QueuePaginator()

    call_state = {'index': 0}

    def _get_metric_data_v2(**kwargs):
        if capture is not None:
            capture.update(kwargs)
        if calls is not None:
            calls.append(kwargs)
        index = call_state['index']
        call_state['index'] = min(index + 1, len(pages) - 1) if pages else 0
        return pages[index] if pages else {'MetricResults': []}

    fake_client.get_metric_data_v2.side_effect = _get_metric_data_v2
    return fake_client


@pytest.mark.asyncio
async def test_get_historical_metric_data(ctx):
    """Historical metric results are transformed and the instance ARN resolved."""
    pages = [
        {
            'MetricResults': [
                {
                    'Dimensions': {'QUEUE': 'Sales'},
                    'Collections': [
                        {'Metric': {'Name': 'CONTACTS_HANDLED'}, 'Value': 42.0},
                        {'Metric': {'Name': 'AVG_HANDLE_TIME'}, 'Value': 215.5},
                    ],
                }
            ]
        }
    ]
    fake_client = _make_client(pages)

    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.get_historical_metric_data(
            ctx,
            instance_id='inst-1',
            metrics=['CONTACTS_HANDLED', 'AVG_HANDLE_TIME'],
            groupings=['QUEUE'],
        )

    assert result.resource_arn.endswith('instance/inst-1')
    assert result.interval_count == 1
    assert len(result.results) == 1
    assert result.results[0].dimensions['QUEUE'] == 'Sales'
    assert result.results[0].metrics[0].value == 42.0
    assert result.results[0].interval_start is not None
    assert result.results[0].interval_end is not None


@pytest.mark.asyncio
async def test_wide_range_is_chunked_into_intervals(ctx):
    """A range wider than 24 hours is split into 24-hour requests."""
    calls = []
    page = {
        'MetricResults': [
            {
                'Dimensions': {'QUEUE': 'Sales'},
                'Collections': [{'Metric': {'Name': 'CONTACTS_HANDLED'}, 'Value': 5.0}],
            }
        ]
    }
    fake_client = _make_client([page], calls=calls)

    end = datetime.now(timezone.utc) - timedelta(hours=1)
    start = end - timedelta(hours=72)
    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.get_historical_metric_data(
            ctx,
            instance_id='inst-1',
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            metrics=['CONTACTS_HANDLED'],
            queue_ids=['q1'],
            groupings=['QUEUE'],
        )

    # 72-hour range -> exactly 3 separate 24-hour requests.
    assert len(calls) == 3
    assert result.interval_count == 3
    # Each interval contributed one result row.
    assert len(result.results) == 3
    # Every request honored the 24-hour cap.
    for call in calls:
        window = call['EndTime'] - call['StartTime']
        assert window <= timedelta(hours=24)
    # Rows are tagged with distinct interval bounds.
    starts = {r.interval_start for r in result.results}
    assert len(starts) == 3


@pytest.mark.asyncio
async def test_ninety_day_lookback_allowed(ctx):
    """A start_time within 90 days is accepted (previously capped at 35)."""
    calls = []
    fake_client = _make_client([{'MetricResults': []}], calls=calls)

    start = datetime.now(timezone.utc) - timedelta(days=60)
    end = start + timedelta(hours=24)
    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.get_historical_metric_data(
            ctx,
            instance_id='inst-1',
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            metrics=['CONTACTS_HANDLED'],
            queue_ids=['q1'],
        )

    assert result.interval_count == 1
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_service_level_threshold_applied(ctx):
    """SERVICE_LEVEL gets a default threshold injected into the request."""
    capture = {}
    fake_client = _make_client([{'MetricResults': []}], capture=capture)

    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        await tools.get_historical_metric_data(
            ctx, instance_id='inst-1', metrics=['SERVICE_LEVEL']
        )

    metrics = capture['Metrics']
    assert metrics[0]['Name'] == 'SERVICE_LEVEL'
    assert metrics[0]['Threshold'][0]['ThresholdValue'] == 120.0


@pytest.mark.asyncio
async def test_default_filter_uses_instance_queues(ctx):
    """When no non-channel filter is given, the instance's queues are used."""
    capture = {}
    fake_client = _make_client([{'MetricResults': []}], capture=capture)

    # Wire list_queues paginator for the default-filter resolution path.
    class _Paginator:
        def paginate(self, **kwargs):
            yield {'QueueSummaryList': [{'Id': 'q1'}, {'Id': 'q2'}]}

    fake_client.get_paginator.return_value = _Paginator()

    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        await tools.get_historical_metric_data(
            ctx, instance_id='inst-1', metrics=['CONTACTS_HANDLED']
        )

    filters = capture['Filters']
    queue_filter = next(f for f in filters if f['FilterKey'] == 'QUEUE')
    assert queue_filter['FilterValues'] == ['q1', 'q2']


@pytest.mark.asyncio
async def test_channel_only_filter_is_augmented(ctx):
    """A channel-only filter is augmented with queues to satisfy the API."""
    capture = {}
    fake_client = _make_client([{'MetricResults': []}], capture=capture)

    class _Paginator:
        def paginate(self, **kwargs):
            yield {'QueueSummaryList': [{'Id': 'q1'}]}

    fake_client.get_paginator.return_value = _Paginator()

    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        await tools.get_historical_metric_data(
            ctx, instance_id='inst-1', metrics=['CONTACTS_HANDLED'], channels=['VOICE']
        )

    filter_keys = {f['FilterKey'] for f in capture['Filters']}
    assert 'QUEUE' in filter_keys
    assert 'CHANNEL' in filter_keys
    """An unsupported grouping raises a ValueError."""
    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=_make_client([]),
    ):
        with pytest.raises(ValueError):
            await tools.get_historical_metric_data(
                ctx, instance_id='inst-1', groupings=['NONSENSE']
            )


@pytest.mark.asyncio
async def test_lookback_window_rejected(ctx):
    """A start_time older than 90 days is rejected."""
    old_start = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=_make_client([]),
    ):
        with pytest.raises(ValueError):
            await tools.get_historical_metric_data(ctx, instance_id='inst-1', start_time=old_start)
