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

"""Additional unit tests for helpers, error paths, pagination, and edge cases.

These cover utility functions and branches across the Amazon Connect MCP Server
modules that the primary per-tool test files do not exercise directly.
"""

import datetime
import pytest
from awslabs.amazon_connect_mcp_server import common
from awslabs.amazon_connect_mcp_server.connect_admin.tools import ConnectAdminTools
from awslabs.amazon_connect_mcp_server.connect_historical.tools import ConnectHistoricalTools
from awslabs.amazon_connect_mcp_server.connect_realtime.tools import ConnectRealtimeTools
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# common.py helpers
# ---------------------------------------------------------------------------


def test_remove_null_values():
    """Keys with None values are dropped; falsy-but-not-None values are kept."""
    result = common.remove_null_values({'a': 1, 'b': None, 'c': 0, 'd': ''})
    assert result == {'a': 1, 'c': 0, 'd': ''}


def test_paginate_with_next_token_follows_tokens():
    """The helper follows NextToken across multiple pages and then stops."""
    pages = [
        {'items': [1], 'NextToken': 't1'},
        {'items': [2], 'NextToken': 't2'},
        {'items': [3]},
    ]
    state = {'i': 0}
    seen_tokens = []

    def op(**kwargs):
        seen_tokens.append(kwargs.get('NextToken'))
        page = pages[state['i']]
        state['i'] += 1
        return page

    out = list(common.paginate_with_next_token(op, {'InstanceId': 'x'}))
    assert len(out) == 3
    # First call has no token, subsequent calls carry the previous page's token.
    assert seen_tokens == [None, 't1', 't2']


def test_paginate_with_next_token_respects_max_pages():
    """max_pages caps the number of fetched pages even if tokens continue."""

    def op(**kwargs):
        return {'items': [1], 'NextToken': 'always'}

    out = list(common.paginate_with_next_token(op, {}, max_pages=2))
    assert len(out) == 2


def test_parse_iso_datetime_naive_assumed_utc():
    """A naive timestamp (no offset) is treated as UTC."""
    parsed = common.parse_iso_datetime('2025-06-08T00:00:00')
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == datetime.timedelta(0)


def test_parse_iso_datetime_handles_z_suffix():
    """A trailing Z suffix is parsed as UTC."""
    parsed = common.parse_iso_datetime('2025-06-08T00:00:00Z')
    assert parsed.utcoffset() == datetime.timedelta(0)


def test_to_utc_iso_naive_input():
    """A naive datetime is assumed UTC and rendered with a +00:00 offset."""
    naive = datetime.datetime(2025, 6, 8, 12, 0, 0)
    out = common.to_utc_iso(naive)
    assert out.endswith('+00:00')


def test_split_into_intervals_basic():
    """A 50-hour range splits into three intervals capped at 24 hours each."""
    start = datetime.datetime(2025, 6, 1, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(hours=50)
    chunks = list(common.split_into_intervals(start, end, interval_hours=24))
    assert len(chunks) == 3
    for cs, ce in chunks:
        assert ce - cs <= datetime.timedelta(hours=24)
    # The chunks exactly cover the range.
    assert chunks[0][0] == start
    assert chunks[-1][1] == end


# ---------------------------------------------------------------------------
# aws_common.get_aws_client
# ---------------------------------------------------------------------------


def test_get_aws_client_with_explicit_profile():
    """An explicit profile name builds a profile-bound session and client."""
    from awslabs.amazon_connect_mcp_server import aws_common

    fake_session = MagicMock()
    fake_session.region_name = 'us-west-2'
    with patch.object(aws_common, 'Session', return_value=fake_session) as session_cls:
        aws_common.get_aws_client('connect', region_name=None, profile_name='myprofile')

    session_cls.assert_called_once_with(profile_name='myprofile')
    # Region falls back to the session's region when none is supplied.
    _, kwargs = fake_session.client.call_args
    assert kwargs['region_name'] == 'us-west-2'


def test_get_aws_client_profile_from_env(monkeypatch):
    """When no profile is passed, AWS_PROFILE from the environment is used."""
    from awslabs.amazon_connect_mcp_server import aws_common

    monkeypatch.setenv('AWS_PROFILE', 'env-profile')
    fake_session = MagicMock()
    fake_session.region_name = None
    with patch.object(aws_common, 'Session', return_value=fake_session) as session_cls:
        aws_common.get_aws_client('connect', region_name='eu-west-1')

    session_cls.assert_called_once_with(profile_name='env-profile')
    _, kwargs = fake_session.client.call_args
    assert kwargs['region_name'] == 'eu-west-1'


def test_get_aws_client_no_profile_region_fallback(monkeypatch):
    """With no profile and no region anywhere, us-east-1 is used."""
    from awslabs.amazon_connect_mcp_server import aws_common

    monkeypatch.delenv('AWS_PROFILE', raising=False)
    fake_session = MagicMock()
    fake_session.region_name = None
    with patch.object(aws_common, 'Session', return_value=fake_session) as session_cls:
        aws_common.get_aws_client('connect')

    session_cls.assert_called_once_with()
    _, kwargs = fake_session.client.call_args
    assert kwargs['region_name'] == 'us-east-1'


# ---------------------------------------------------------------------------
# connect_admin: success paths, None max_items, error paths
# ---------------------------------------------------------------------------


class _Paginator:
    def __init__(self, pages):
        self._pages = pages

    def paginate(self, **kwargs):
        for page in self._pages:
            yield page


@pytest.mark.asyncio
async def test_list_agents_success_and_none_max_items(ctx):
    """list_agents transforms users and treats max_items=None as the default."""
    fake_client = MagicMock()
    fake_client.get_paginator.return_value = _Paginator(
        [{'UserSummaryList': [{'Id': 'u1', 'Arn': 'arn:u1', 'Username': 'alice'}]}]
    )
    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.list_agents(ctx, instance_id='inst-1', max_items=None)

    assert len(result.agents) == 1
    assert result.agents[0].username == 'alice'
    assert result.has_more_results is False


@pytest.mark.asyncio
async def test_list_queues_empty_message(ctx):
    """An empty queue list returns a helpful message."""
    fake_client = MagicMock()
    fake_client.get_paginator.return_value = _Paginator([{'QueueSummaryList': []}])
    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.list_queues(ctx, instance_id='inst-1')

    assert result.queues == []
    assert result.message == 'No queues found for this instance'


@pytest.mark.asyncio
async def test_list_queues_with_queue_types_filter(ctx):
    """Passing queue_types forwards a QueueTypes kwarg to the paginator."""
    fake_client = MagicMock()
    captured = {}

    class _CapturingPaginator:
        def paginate(self, **kwargs):
            captured.update(kwargs)
            yield {'QueueSummaryList': []}

    fake_client.get_paginator.return_value = _CapturingPaginator()
    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        await tools.list_queues(ctx, instance_id='inst-1', queue_types=['STANDARD'])

    assert captured['QueueTypes'] == ['STANDARD']


@pytest.mark.asyncio
async def test_list_connect_instances_error_path(ctx):
    """Errors in list_connect_instances are reported and re-raised."""
    fake_client = MagicMock()
    fake_client.get_paginator.side_effect = RuntimeError('boom')
    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        with pytest.raises(RuntimeError):
            await tools.list_connect_instances(ctx)
    assert ctx.errors


@pytest.mark.asyncio
async def test_list_queues_error_path(ctx):
    """Errors in list_queues are reported and re-raised."""
    fake_client = MagicMock()
    fake_client.get_paginator.side_effect = RuntimeError('boom')
    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        with pytest.raises(RuntimeError):
            await tools.list_queues(ctx, instance_id='inst-1')
    assert ctx.errors


@pytest.mark.asyncio
async def test_list_routing_profiles_error_path(ctx):
    """Errors in list_routing_profiles are reported and re-raised."""
    fake_client = MagicMock()
    fake_client.get_paginator.side_effect = RuntimeError('boom')
    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        with pytest.raises(RuntimeError):
            await tools.list_routing_profiles(ctx, instance_id='inst-1')
    assert ctx.errors


@pytest.mark.asyncio
async def test_list_routing_profiles_has_more(ctx):
    """has_more_results is True when more profiles exist than max_items."""
    fake_client = MagicMock()
    fake_client.get_paginator.return_value = _Paginator(
        [
            {
                'RoutingProfileSummaryList': [
                    {'Id': 'rp1', 'Arn': 'arn:rp1', 'Name': 'A'},
                    {'Id': 'rp2', 'Arn': 'arn:rp2', 'Name': 'B'},
                ]
            }
        ]
    )
    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.list_routing_profiles(ctx, instance_id='inst-1', max_items=1)
    assert len(result.routing_profiles) == 1
    assert result.has_more_results is True


# ---------------------------------------------------------------------------
# connect_realtime: groupings, error, pagination, transform branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_current_metric_invalid_grouping(ctx):
    """An unsupported grouping raises a ValueError."""
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=MagicMock(),
    ):
        with pytest.raises(ValueError):
            await tools.get_current_metric_data(ctx, instance_id='inst-1', groupings=['NONSENSE'])


@pytest.mark.asyncio
async def test_current_metric_with_groupings_and_channel_dim(ctx):
    """Groupings are forwarded and channel/routing-profile dimensions transform."""
    fake_client = MagicMock()
    fake_client.get_current_metric_data.return_value = {
        'MetricResults': [
            {
                'Dimensions': {
                    'Channel': 'VOICE',
                    'RoutingProfile': {'Id': 'rp1'},
                },
                'Collections': [
                    {'Metric': {'Name': 'AGENTS_ONLINE', 'Unit': 'COUNT'}, 'Value': 7.0}
                ],
            }
        ]
    }
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.get_current_metric_data(
            ctx,
            instance_id='inst-1',
            queue_ids=['q1'],
            channels=['VOICE'],
            groupings=['CHANNEL'],
        )

    dims = result.results[0].dimensions
    assert dims['channel'] == 'VOICE'
    assert dims['routing_profile_id'] == 'rp1'


@pytest.mark.asyncio
async def test_current_metric_has_more_results(ctx):
    """Returning more results than max_items sets has_more_results."""
    fake_client = MagicMock()
    fake_client.get_current_metric_data.return_value = {
        'MetricResults': [
            {'Dimensions': {'Queue': {'Id': 'q1', 'Arn': 'arn:q1'}}, 'Collections': []},
            {'Dimensions': {'Queue': {'Id': 'q2', 'Arn': 'arn:q2'}}, 'Collections': []},
        ]
    }
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.get_current_metric_data(ctx, instance_id='inst-1', max_items=1)
    assert len(result.results) == 1
    assert result.has_more_results is True


@pytest.mark.asyncio
async def test_current_metric_error_path(ctx):
    """Errors in get_current_metric_data are reported and re-raised."""
    fake_client = MagicMock()
    fake_client.get_current_metric_data.side_effect = RuntimeError('boom')
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        with pytest.raises(RuntimeError):
            await tools.get_current_metric_data(ctx, instance_id='inst-1')
    assert ctx.errors


@pytest.mark.asyncio
async def test_agent_status_has_more_and_empty_message(ctx):
    """has_more_results is set when agents exceed max_items."""
    fake_client = MagicMock()
    fake_client.get_current_user_data.return_value = {
        'UserDataList': [
            {'User': {'Id': 'u1', 'Arn': 'arn:u1'}, 'Status': {}, 'RoutingProfile': {}},
            {'User': {'Id': 'u2', 'Arn': 'arn:u2'}, 'Status': {}, 'RoutingProfile': {}},
        ]
    }
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.get_current_agent_status(
            ctx, instance_id='inst-1', queue_ids=['q1'], max_items=1
        )
    assert len(result.agents) == 1
    assert result.has_more_results is True
    # The second agent had no status timestamp -> None is tolerated.
    assert result.agents[0].status_start_timestamp is None


@pytest.mark.asyncio
async def test_agent_status_error_path(ctx):
    """Errors in get_current_agent_status are reported and re-raised."""
    fake_client = MagicMock()
    fake_client.get_current_user_data.side_effect = RuntimeError('boom')
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        with pytest.raises(RuntimeError):
            await tools.get_current_agent_status(ctx, instance_id='inst-1', agent_ids=['u1'])
    assert ctx.errors


# ---------------------------------------------------------------------------
# connect_historical: helpers and edge cases
# ---------------------------------------------------------------------------


def test_historical_resolve_arn_passthrough():
    """An instance value that is already an ARN is returned unchanged."""
    tools = ConnectHistoricalTools()
    arn = 'arn:aws:connect:us-east-1:111122223333:instance/abc'
    # No describe_instance call should be needed for an ARN.
    assert tools._resolve_instance_arn(MagicMock(), arn) == arn


def test_historical_build_filters_all_dimensions():
    """All four filter dimensions are emitted with the correct FilterKeys."""
    tools = ConnectHistoricalTools()
    filters = tools._build_filters(
        queue_ids=['q1'],
        channels=['VOICE'],
        agent_ids=['a1'],
        routing_profile_ids=['rp1'],
    )
    keys = {f['FilterKey'] for f in filters}
    assert keys == {'QUEUE', 'CHANNEL', 'AGENT', 'ROUTING_PROFILE'}


def test_historical_list_queue_ids_respects_limit():
    """_list_queue_ids stops once the limit is reached."""
    tools = ConnectHistoricalTools()
    fake_client = MagicMock()

    class _P:
        def paginate(self, **kwargs):
            yield {'QueueSummaryList': [{'Id': 'q1'}, {'Id': 'q2'}, {'Id': 'q3'}]}

    fake_client.get_paginator.return_value = _P()
    ids = tools._list_queue_ids(fake_client, 'inst-1', limit=2)
    assert ids == ['q1', 'q2']


@pytest.mark.asyncio
async def test_historical_start_after_end_rejected(ctx):
    """start_time later than end_time raises a ValueError."""
    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=MagicMock(),
    ):
        with pytest.raises(ValueError):
            await tools.get_historical_metric_data(
                ctx,
                instance_id='inst-1',
                start_time='2025-06-08T10:00:00Z',
                end_time='2025-06-08T09:00:00Z',
            )


@pytest.mark.asyncio
async def test_historical_no_default_queues_raises(ctx):
    """If no filter is given and the instance has no queues, a ValueError is raised."""
    fake_client = MagicMock()
    fake_client.describe_instance.return_value = {'Instance': {'Arn': 'arn:inst'}}

    class _EmptyP:
        def paginate(self, **kwargs):
            yield {'QueueSummaryList': []}

    fake_client.get_paginator.return_value = _EmptyP()
    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        with pytest.raises(ValueError):
            await tools.get_historical_metric_data(
                ctx, instance_id='inst-1', metrics=['CONTACTS_HANDLED']
            )
    assert ctx.errors


@pytest.mark.asyncio
async def test_historical_has_more_results(ctx):
    """More result rows than max_items sets has_more_results."""
    fake_client = MagicMock()
    fake_client.describe_instance.return_value = {'Instance': {'Arn': 'arn:inst'}}
    fake_client.get_metric_data_v2.return_value = {
        'MetricResults': [
            {'Dimensions': {'QUEUE': 'A'}, 'Collections': []},
            {'Dimensions': {'QUEUE': 'B'}, 'Collections': []},
        ]
    }
    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.get_historical_metric_data(
            ctx,
            instance_id='inst-1',
            metrics=['CONTACTS_HANDLED'],
            queue_ids=['q1'],
            max_items=1,
        )
    assert len(result.results) == 1
    assert result.has_more_results is True


# ---------------------------------------------------------------------------
# None max_items defaults across all tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_none_max_items_defaults(ctx):
    """max_items=None falls back to the default in every admin tool."""
    fake_client = MagicMock()
    fake_client.get_paginator.return_value = _Paginator(
        [
            {'InstanceSummaryList': [{'Id': 'i1', 'Arn': 'arn:i1'}]},
        ]
    )
    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        res = await tools.list_connect_instances(ctx, max_items=None)
    assert len(res.instances) == 1

    fake_client.get_paginator.return_value = _Paginator([{'QueueSummaryList': []}])
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        res = await tools.list_queues(ctx, instance_id='i1', max_items=None)
    assert res.queues == []

    fake_client.get_paginator.return_value = _Paginator([{'RoutingProfileSummaryList': []}])
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        res = await tools.list_routing_profiles(ctx, instance_id='i1', max_items=None)
    assert res.routing_profiles == []


@pytest.mark.asyncio
async def test_realtime_none_max_items_defaults(ctx):
    """max_items=None falls back to the default in the realtime tools."""
    fake_client = MagicMock()
    fake_client.get_current_metric_data.return_value = {'MetricResults': []}
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        res = await tools.get_current_metric_data(ctx, instance_id='i1', max_items=None)
    assert res.results == []

    fake_client.get_current_user_data.return_value = {'UserDataList': []}
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        res = await tools.get_current_agent_status(
            ctx, instance_id='i1', agent_ids=['a1'], max_items=None
        )
    assert res.agents == []


@pytest.mark.asyncio
async def test_historical_none_max_items_default(ctx):
    """max_items=None falls back to the default in the historical tool."""
    fake_client = MagicMock()
    fake_client.describe_instance.return_value = {'Instance': {'Arn': 'arn:inst'}}
    fake_client.get_metric_data_v2.return_value = {'MetricResults': []}
    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        res = await tools.get_historical_metric_data(
            ctx, instance_id='i1', metrics=['CONTACTS_HANDLED'], queue_ids=['q1'], max_items=None
        )
    assert res.results == []


# ---------------------------------------------------------------------------
# NextToken + max_items break paths (pagination short-circuit)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_realtime_metric_nexttoken_with_full_results(ctx):
    """A page with a NextToken once max_items is reached sets has_more_results."""
    fake_client = MagicMock()
    fake_client.get_current_metric_data.return_value = {
        'MetricResults': [{'Dimensions': {'Queue': {'Id': 'q1', 'Arn': 'a'}}, 'Collections': []}],
        'NextToken': 'more',
    }
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        res = await tools.get_current_metric_data(ctx, instance_id='i1', max_items=1)
    assert res.has_more_results is True


@pytest.mark.asyncio
async def test_agent_status_nexttoken_with_full_results(ctx):
    """A page with a NextToken once max_items is reached sets has_more_results."""
    fake_client = MagicMock()
    fake_client.get_current_user_data.return_value = {
        'UserDataList': [{'User': {'Id': 'u1', 'Arn': 'a'}, 'Status': {}, 'RoutingProfile': {}}],
        'NextToken': 'more',
    }
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        res = await tools.get_current_agent_status(
            ctx, instance_id='i1', agent_ids=['u1'], max_items=1
        )
    assert res.has_more_results is True


@pytest.mark.asyncio
async def test_historical_nexttoken_with_full_results(ctx):
    """A page with a NextToken once max_items is reached sets has_more_results."""
    fake_client = MagicMock()
    fake_client.describe_instance.return_value = {'Instance': {'Arn': 'arn:inst'}}
    fake_client.get_metric_data_v2.return_value = {
        'MetricResults': [{'Dimensions': {'QUEUE': 'A'}, 'Collections': []}],
        'NextToken': 'more',
    }
    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        res = await tools.get_historical_metric_data(
            ctx, instance_id='i1', metrics=['CONTACTS_HANDLED'], queue_ids=['q1'], max_items=1
        )
    assert res.has_more_results is True


# ---------------------------------------------------------------------------
# historical: budget-exceeded partial-results path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_historical_budget_exceeded_returns_partial(ctx, monkeypatch):
    """When the wall-clock fetch budget is exceeded, partial results are returned."""
    from awslabs.amazon_connect_mcp_server.connect_historical import tools as hist_tools

    fake_client = MagicMock()
    fake_client.describe_instance.return_value = {'Instance': {'Arn': 'arn:inst'}}
    fake_client.get_metric_data_v2.return_value = {'MetricResults': []}

    # monotonic() advances far past the deadline on the first interval check so
    # the loop breaks immediately with budget_exceeded=True.
    ticks = iter([1000.0, 1000.0, 999999.0, 999999.0, 999999.0])

    def fake_monotonic():
        try:
            return next(ticks)
        except StopIteration:
            return 999999.0

    monkeypatch.setattr(hist_tools, 'monotonic', fake_monotonic)

    from datetime import datetime, timedelta, timezone

    end = datetime.now(timezone.utc) - timedelta(hours=1)
    start = end - timedelta(hours=72)
    tools = ConnectHistoricalTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_historical.tools.get_aws_client',
        return_value=fake_client,
    ):
        res = await tools.get_historical_metric_data(
            ctx,
            instance_id='i1',
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            metrics=['CONTACTS_HANDLED'],
            queue_ids=['q1'],
        )
    assert res.has_more_results is True
    assert res.message is not None and 'partial' in res.message.lower()
