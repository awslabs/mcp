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

"""Tests for the adaptive_poll tool."""
# ruff: noqa: D101

import json
import pytest
from awslabs.aws_transform_mcp_server.tools.adaptive_poll import (
    MAX_SLEEP_SECONDS,
    AdaptivePollHandler,
)
from unittest.mock import AsyncMock, patch


def _parse(result: dict) -> dict:
    return json.loads(result['content'][0]['text'])


@pytest.fixture
def handler(mock_mcp):
    return AdaptivePollHandler(mock_mcp)


@pytest.fixture
def ctx():
    return AsyncMock()


class TestAdaptivePollRegistration:
    def test_registers_tool(self, mock_mcp):
        AdaptivePollHandler(mock_mcp)
        mock_mcp.tool.assert_called_once()
        kwargs = mock_mcp.tool.call_args[1]
        assert kwargs['name'] == 'adaptive_poll'


class TestAdaptivePoll:
    @patch(
        'awslabs.aws_transform_mcp_server.tools.adaptive_poll.asyncio.sleep',
        new_callable=AsyncMock,
    )
    async def test_returns_follow_up(self, mock_sleep, handler, ctx):
        result = await handler.adaptive_poll(ctx, seconds=30, follow_up='check job status')
        parsed = _parse(result)
        assert parsed['success'] is True
        assert parsed['data']['waited'] == 30
        assert parsed['data']['follow_up'] == 'check job status'
        mock_sleep.assert_awaited_once_with(30)

    @patch(
        'awslabs.aws_transform_mcp_server.tools.adaptive_poll.asyncio.sleep',
        new_callable=AsyncMock,
    )
    async def test_clamps_below_minimum(self, mock_sleep, handler, ctx):
        result = await handler.adaptive_poll(ctx, seconds=0, follow_up='msg')
        parsed = _parse(result)
        assert parsed['data']['waited'] == 1
        mock_sleep.assert_awaited_once_with(1)

    @patch(
        'awslabs.aws_transform_mcp_server.tools.adaptive_poll.asyncio.sleep',
        new_callable=AsyncMock,
    )
    async def test_clamps_above_maximum(self, mock_sleep, handler, ctx):
        result = await handler.adaptive_poll(ctx, seconds=4000, follow_up='msg')
        parsed = _parse(result)
        assert parsed['data']['waited'] == MAX_SLEEP_SECONDS
        mock_sleep.assert_awaited_once_with(MAX_SLEEP_SECONDS)

    @patch(
        'awslabs.aws_transform_mcp_server.tools.adaptive_poll.asyncio.sleep',
        new_callable=AsyncMock,
    )
    async def test_is_not_error(self, mock_sleep, handler, ctx):
        result = await handler.adaptive_poll(ctx, seconds=10, follow_up='next')
        assert result['isError'] is False
