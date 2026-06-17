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
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.call_transform_api',
        new_callable=AsyncMock,
    )
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
            mock_helper.create_boto3_client.return_value = mock_sts
            result = await handler.accept_connector(
                ctx, workspaceId='ws-1', connectorId='c-1', roleArn='arn:aws:iam::123:role/r'
            )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        mock_tcp.assert_called_once()
        tcp_body = mock_tcp.call_args[0][1]
        assert tcp_body['sourceAccount'] == '123456789012'


class TestBuildVerificationLink:
    """Tests for _build_verification_link."""

    def test_prod_link(self):
        from awslabs.aws_transform_mcp_server.tools.connector import _build_verification_link

        link = _build_verification_link('c-1', 'us-east-1')
        assert link == (
            'https://us-east-1.console.aws.amazon.com/transform/connector/'
            'c-1/configure?region=us-east-1'
        )


class TestCreateConnector:
    """Tests for the create_connector handler."""

    @pytest.mark.asyncio
    @patch(f'{_MOD}.is_fes_available', return_value=False)
    async def test_not_configured(self, _, handler, ctx):
        result = await handler.create_connector(
            ctx,
            workspaceId='ws-1',
            connectorName='test-conn',
            connectorType='S3',
            configuration={'s3Uri': 's3://bucket/path'},
            awsAccountId='123456789012',
        )
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    @pytest.mark.asyncio
    @patch(f'{_MOD}.get_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_happy_path(self, _, mock_fes, mock_config, handler, ctx):
        mock_cfg = MagicMock()
        mock_cfg.region = 'us-east-1'
        mock_config.return_value = mock_cfg

        mock_fes.side_effect = [
            # CreateConnector
            {'connectorId': 'c-new'},
            # GetConnector
            {'connectorId': 'c-new', 'status': 'PENDING'},
        ]

        result = await handler.create_connector(
            ctx,
            workspaceId='ws-1',
            connectorName='test-conn',
            connectorType='S3',
            configuration={'s3Uri': 's3://bucket/path'},
            awsAccountId='123456789012',
        )
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['connectorId'] == 'c-new'
        assert 'verificationLink' in parsed['data']
        assert 'nextStep' in parsed['data']

    @pytest.mark.asyncio
    @patch(f'{_MOD}.get_config', return_value=None)
    @patch(f'{_MOD}.AwsHelper')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_happy_path_no_config_fallback(
        self, _, mock_fes, mock_helper, mock_config, handler, ctx
    ):
        mock_helper.resolve_region.return_value = 'us-west-2'
        mock_helper.create_session.return_value = MagicMock()

        mock_fes.side_effect = [
            {'connectorId': 'c-new'},
            {'connectorId': 'c-new', 'status': 'PENDING'},
        ]

        result = await handler.create_connector(
            ctx,
            workspaceId='ws-1',
            connectorName='test-conn',
            connectorType='S3',
            configuration={'s3Uri': 's3://bucket/path'},
            awsAccountId='123456789012',
        )
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.call_transform_api',
        new_callable=AsyncMock,
        side_effect=Exception('API error'),
    )
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_fes_error_returns_failure(self, _, mock_fes, handler, ctx):
        result = await handler.create_connector(
            ctx,
            workspaceId='ws-1',
            connectorName='test-conn',
            connectorType='S3',
            configuration={'s3Uri': 's3://bucket/path'},
            awsAccountId='123456789012',
        )
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert 'API error' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(f'{_MOD}.get_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.call_transform_api',
        new_callable=AsyncMock,
    )
    @patch(f'{_MOD}.is_fes_available', return_value=True)
    async def test_optional_description_and_target_regions(
        self, _, mock_fes, mock_config, handler, ctx
    ):
        mock_cfg = MagicMock()
        mock_cfg.region = 'us-east-1'
        mock_config.return_value = mock_cfg

        mock_fes.side_effect = [
            {'connectorId': 'c-opt'},
            {'connectorId': 'c-opt', 'status': 'PENDING'},
        ]

        result = await handler.create_connector(
            ctx,
            workspaceId='ws-1',
            connectorName='test-conn',
            connectorType='S3',
            configuration={'s3Uri': 's3://bucket/path'},
            awsAccountId='123456789012',
            description='My connector',
            targetRegions=['us-east-1', 'us-west-2'],
        )
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True

        # Verify description and targetRegions were in the payload
        create_call = mock_fes.call_args_list[0]
        body = create_call[0][1]
        assert body.description == 'My connector'
        assert body.targetRegions == ['us-east-1', 'us-west-2']
