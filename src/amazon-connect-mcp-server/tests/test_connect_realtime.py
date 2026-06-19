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

"""Unit tests for the Amazon Connect realtime metric tools."""

import pytest
from awslabs.amazon_connect_mcp_server.connect_realtime.tools import ConnectRealtimeTools
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_get_current_metric_data_default_metrics(ctx):
    """Default metrics are requested and grouped results are transformed."""
    fake_client = MagicMock()
    fake_client.get_current_metric_data.return_value = {
        'DataSnapshotTime': datetime(2026, 6, 8, tzinfo=timezone.utc),
        'MetricResults': [
            {
                'Dimensions': {'Queue': {'Id': 'q1', 'Arn': 'arn:q1'}},
                'Collections': [
                    {
                        'Metric': {'Name': 'CONTACTS_IN_QUEUE', 'Unit': 'COUNT'},
                        'Value': 3.0,
                    }
                ],
            }
        ],
    }

    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.get_current_metric_data(ctx, instance_id='inst-1')

    assert result.instance_id == 'inst-1'
    assert len(result.results) == 1
    assert result.results[0].dimensions['queue_id'] == 'q1'
    assert result.results[0].collections[0].value == 3.0
    assert result.data_snapshot_time is not None


@pytest.mark.asyncio
async def test_get_current_metric_data_invalid_metric(ctx):
    """An unsupported metric name raises a ValueError."""
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=MagicMock(),
    ):
        with pytest.raises(ValueError):
            await tools.get_current_metric_data(
                ctx, instance_id='inst-1', metrics=['NOT_A_REAL_METRIC']
            )


@pytest.mark.asyncio
async def test_get_current_agent_status_requires_filter(ctx):
    """get_current_agent_status requires at least one filter."""
    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=MagicMock(),
    ):
        with pytest.raises(ValueError):
            await tools.get_current_agent_status(ctx, instance_id='inst-1')


@pytest.mark.asyncio
async def test_get_current_agent_status(ctx):
    """Agent user data is transformed into the response model."""
    fake_client = MagicMock()
    fake_client.get_current_user_data.return_value = {
        'UserDataList': [
            {
                'User': {'Id': 'u1', 'Arn': 'arn:u1'},
                'Status': {
                    'StatusName': 'Available',
                    'StatusStartTimestamp': datetime(2026, 6, 8, tzinfo=timezone.utc),
                },
                'RoutingProfile': {'Name': 'Default'},
                'AvailableSlotsByChannel': {'VOICE': 1},
                'Contacts': [{'ContactId': 'c1'}],
            }
        ]
    }

    tools = ConnectRealtimeTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_realtime.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.get_current_agent_status(ctx, instance_id='inst-1', agent_ids=['u1'])

    assert len(result.agents) == 1
    agent = result.agents[0]
    assert agent.agent_id == 'u1'
    assert agent.status_name == 'Available'
    assert agent.available_slots_by_channel == {'VOICE': 1}
    assert agent.active_contacts == 1
