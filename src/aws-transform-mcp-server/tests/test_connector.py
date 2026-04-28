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

"""Tests for accept_connector handler."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.tools.connector'


@pytest.fixture
def handler():
    """Create a ConnectorHandler with a mock MCP server."""
    from awslabs.aws_transform_mcp_server.tools.connector import ConnectorHandler

    mcp = MagicMock()
    mcp.tool = MagicMock(side_effect=lambda **kwargs: lambda fn: fn)
    return ConnectorHandler(mcp)


@pytest.fixture
def ctx():
    """Create a mock MCP context."""
    ctx = AsyncMock()
    ctx.info = MagicMock(return_value='mock-context')
    return ctx


class TestAcceptConnector:
    """Tests for the accept_connector handler."""

    @pytest.mark.asyncio
    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_not_configured(self, _, handler, ctx):
        result = await handler.accept_connector(
            ctx, workspaceId='ws-1', connectorId='c-1', roleArn='arn:aws:iam::123:role/r'
        )
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    @pytest.mark.asyncio
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_no_aws_credentials(self, _, handler, ctx):
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None

        with patch(f'{_MOD}.AwsHelper') as mock_helper:
            mock_helper.create_session.return_value = mock_session
            result = await handler.accept_connector(
                ctx, workspaceId='ws-1', connectorId='c-1', roleArn='arn:aws:iam::123:role/r'
            )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NO_AWS_CREDENTIALS'

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_fes', new_callable=AsyncMock)
    @patch(f'{_MOD}.call_tcp', new_callable=AsyncMock)
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_happy_path(self, _, mock_tcp, mock_fes, handler, ctx):
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = MagicMock()
        mock_session.region_name = 'us-east-1'
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}
        mock_session.client.return_value = mock_sts

        mock_tcp.return_value = {}
        mock_fes.return_value = {'connectorId': 'c-1', 'status': 'ACTIVE'}

        with patch(f'{_MOD}.AwsHelper') as mock_helper:
            mock_helper.create_session.return_value = mock_session
            mock_helper.resolve_region.return_value = 'us-east-1'
            result = await handler.accept_connector(
                ctx, workspaceId='ws-1', connectorId='c-1', roleArn='arn:aws:iam::123:role/r'
            )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        mock_tcp.assert_called_once()
        tcp_body = mock_tcp.call_args[0][1]
        assert tcp_body['sourceAccount'] == '123456789012'
