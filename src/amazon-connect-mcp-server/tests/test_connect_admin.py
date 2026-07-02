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

"""Unit tests for the Amazon Connect administration / discovery tools."""

import pytest
from awslabs.amazon_connect_mcp_server.connect_admin.tools import ConnectAdminTools
from unittest.mock import MagicMock, patch


class FakePaginator:
    """Fake boto3 paginator that yields the provided pages."""

    def __init__(self, pages):
        """Store the pages to yield on pagination."""
        self._pages = pages

    def paginate(self, **kwargs):
        """Yield each stored page."""
        for page in self._pages:
            yield page


@pytest.mark.asyncio
async def test_list_connect_instances(ctx):
    """list_connect_instances returns transformed instance summaries."""
    fake_client = MagicMock()
    fake_client.get_paginator.return_value = FakePaginator(
        [
            {
                'InstanceSummaryList': [
                    {
                        'Id': 'inst-1',
                        'Arn': 'arn:aws:connect:us-east-1:111122223333:instance/inst-1',
                        'InstanceAlias': 'my-cc',
                        'InstanceStatus': 'ACTIVE',
                    }
                ]
            }
        ]
    )

    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.list_connect_instances(ctx)

    assert len(result.instances) == 1
    assert result.instances[0].instance_id == 'inst-1'
    assert result.instances[0].instance_alias == 'my-cc'
    assert result.message is None


@pytest.mark.asyncio
async def test_list_instances_empty(ctx):
    """An empty instance list returns a helpful message."""
    fake_client = MagicMock()
    fake_client.get_paginator.return_value = FakePaginator([{'InstanceSummaryList': []}])

    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.list_connect_instances(ctx)

    assert result.instances == []
    assert result.message == 'No Amazon Connect instances found'


@pytest.mark.asyncio
async def test_list_queues_has_more_results(ctx):
    """list_queues reports has_more_results when more items exist than max_items."""
    fake_client = MagicMock()
    fake_client.get_paginator.return_value = FakePaginator(
        [
            {
                'QueueSummaryList': [
                    {'Id': 'q1', 'Arn': 'arn:q1', 'Name': 'Sales', 'QueueType': 'STANDARD'},
                    {'Id': 'q2', 'Arn': 'arn:q2', 'Name': 'Support', 'QueueType': 'STANDARD'},
                ]
            }
        ]
    )

    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.list_queues(ctx, instance_id='inst-1', max_items=1)

    assert len(result.queues) == 1
    assert result.has_more_results is True


@pytest.mark.asyncio
async def test_list_agents_error_path(ctx):
    """Errors are surfaced to the context and re-raised."""
    fake_client = MagicMock()
    fake_client.get_paginator.side_effect = RuntimeError('boom')

    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        with pytest.raises(RuntimeError):
            await tools.list_agents(ctx, instance_id='inst-1')

    assert ctx.errors


@pytest.mark.asyncio
async def test_list_routing_profiles(ctx):
    """list_routing_profiles returns transformed routing profile summaries."""
    fake_client = MagicMock()
    fake_client.get_paginator.return_value = FakePaginator(
        [
            {
                'RoutingProfileSummaryList': [
                    {'Id': 'rp1', 'Arn': 'arn:rp1', 'Name': 'Default'},
                ]
            }
        ]
    )

    tools = ConnectAdminTools()
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.get_aws_client',
        return_value=fake_client,
    ):
        result = await tools.list_routing_profiles(ctx, instance_id='inst-1')

    assert len(result.routing_profiles) == 1
    assert result.routing_profiles[0].name == 'Default'
