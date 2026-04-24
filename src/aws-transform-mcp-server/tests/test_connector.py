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

"""Tests for connector tool handlers."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from awslabs.aws_transform_mcp_server.models import ConnectionConfig
from awslabs.aws_transform_mcp_server.tools.connector import ConnectorHandler
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def handler(mock_mcp):
    return ConnectorHandler(mock_mcp)


@pytest.fixture
def mock_context():
    ctx = AsyncMock()
    ctx.info = MagicMock(return_value='mock-context')
    return ctx


# ── create_connector ────────────────────────────────────────────────────


class TestCreateConnector:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.get_config')
    @patch('awslabs.aws_transform_mcp_server.tools.connector.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.connector.is_configured', return_value=True)
    async def test_create_connector_prod(
        self, mock_is_configured, mock_call_fes, mock_get_config, handler, mock_context
    ):
        mock_call_fes.side_effect = [
            {'connectorId': 'conn-123'},
            {'connectorId': 'conn-123', 'status': 'PENDING'},
        ]
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='cookie',
            stage='prod',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.transform.us-east-1.on.aws',
            session_cookie='aws-transform-session=abc',
        )

        result = await handler.create_connector(
            mock_context,
            workspaceId='ws-1',
            connectorName='My Connector',
            connectorType='S3',
            configuration={'s3Uri': 's3://bucket/path'},
            awsAccountId='123456789012',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert 'conn-123' in parsed['data']['verificationLink']
        assert 'console.aws.amazon.com' in parsed['data']['verificationLink']
        assert 'awsc-integ' not in parsed['data']['verificationLink']
        assert parsed['data']['nextStep'] is not None

        # Verify FES CreateConnector was called with correct body
        create_call = mock_call_fes.call_args_list[0]
        assert create_call[0][0] == 'CreateConnector'
        body = create_call[0][1]
        assert body['workspaceId'] == 'ws-1'
        assert body['connectorName'] == 'My Connector'
        assert body['connectorType'] == 'S3'
        assert body['configuration'] == {'s3Uri': 's3://bucket/path'}
        assert (
            body['accountConnectionRequest']['awsAccountConnectionRequest']['awsAccountId']
            == '123456789012'
        )
        assert 'idempotencyToken' in body

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.get_config')
    @patch('awslabs.aws_transform_mcp_server.tools.connector.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.connector.is_configured', return_value=True)
    async def test_create_connector_gamma(
        self, mock_is_configured, mock_call_fes, mock_get_config, handler, mock_context
    ):
        mock_call_fes.side_effect = [
            {'connectorId': 'conn-456'},
            {'connectorId': 'conn-456', 'status': 'PENDING'},
        ]
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='cookie',
            stage='gamma',
            region='us-west-2',
            fes_endpoint='https://api.transform-gamma.us-west-2.on.aws/',
            origin='https://app.transform-gamma.us-west-2.on.aws',
            session_cookie='aws-transform-session=abc',
        )

        result = await handler.create_connector(
            mock_context,
            workspaceId='ws-2',
            connectorName='Gamma Conn',
            connectorType='CODE',
            configuration={},
            awsAccountId='111222333444',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        link = parsed['data']['verificationLink']
        assert 'awsc-integ.aws.amazon.com' in link
        assert 'sourceAccount=111222333444' in link
        assert 'workspaceId=ws-2' in link

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.get_config')
    @patch('awslabs.aws_transform_mcp_server.tools.connector.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.connector.is_configured', return_value=True)
    async def test_create_connector_with_description_and_target_regions(
        self, mock_is_configured, mock_call_fes, mock_get_config, handler, mock_context
    ):
        mock_call_fes.side_effect = [
            {'connectorId': 'conn-789'},
            {'connectorId': 'conn-789', 'status': 'PENDING'},
        ]
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='cookie',
            stage='prod',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.transform.us-east-1.on.aws',
            session_cookie='aws-transform-session=abc',
        )

        result = await handler.create_connector(
            mock_context,
            workspaceId='ws-1',
            connectorName='My Connector',
            connectorType='S3',
            configuration={'s3Uri': 's3://bucket/path'},
            awsAccountId='123456789012',
            description='Test connector description',
            targetRegions=['us-east-1', 'us-west-2'],
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True

        body = mock_call_fes.call_args_list[0][0][1]
        assert body['description'] == 'Test connector description'
        assert body['targetRegions'] == ['us-east-1', 'us-west-2']

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.get_config')
    @patch('awslabs.aws_transform_mcp_server.tools.connector.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.connector.is_configured', return_value=True)
    async def test_create_connector_omits_optional_fields_when_none(
        self, mock_is_configured, mock_call_fes, mock_get_config, handler, mock_context
    ):
        mock_call_fes.side_effect = [
            {'connectorId': 'conn-000'},
            {'connectorId': 'conn-000', 'status': 'PENDING'},
        ]
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='cookie',
            stage='prod',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.transform.us-east-1.on.aws',
            session_cookie='aws-transform-session=abc',
        )

        result = await handler.create_connector(
            mock_context,
            workspaceId='ws-1',
            connectorName='Basic',
            connectorType='S3',
            configuration={},
            awsAccountId='123456789012',
            description=None,
            targetRegions=None,
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True

        body = mock_call_fes.call_args_list[0][0][1]
        assert 'description' not in body
        assert 'targetRegions' not in body

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.is_configured', return_value=False)
    async def test_create_connector_not_configured(
        self, mock_is_configured, handler, mock_context
    ):
        result = await handler.create_connector(
            mock_context,
            workspaceId='ws-1',
            connectorName='test',
            connectorType='S3',
            configuration={},
            awsAccountId='123456789012',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


# ── create_profile ──────────────────────────────────────────────────────


class TestCreateProfile:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.call_tcp', new_callable=AsyncMock)
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.is_sigv4_configured', return_value=True
    )
    async def test_create_profile_sso(self, mock_sigv4, mock_call_tcp, handler, mock_context):
        mock_call_tcp.return_value = {'profileId': 'prof-1'}

        result = await handler.create_profile(
            mock_context,
            profileName='my-profile',
            identityType='sso',
            ssoInstanceArn='arn:aws:sso:::instance/ssoins-12345',
            ssoRegion='us-east-1',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['profileId'] == 'prof-1'

        # Verify TCP body
        call_args = mock_call_tcp.call_args
        body = call_args[0][1]
        assert body['profileName'] == 'my-profile'
        assert 'ssoIdentitySource' in body['identitySource']
        assert (
            body['identitySource']['ssoIdentitySource']['instanceArn']
            == 'arn:aws:sso:::instance/ssoins-12345'
        )
        assert 'clientToken' in body

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.call_tcp', new_callable=AsyncMock)
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.is_sigv4_configured', return_value=True
    )
    async def test_create_profile_external_idp(
        self, mock_sigv4, mock_call_tcp, handler, mock_context
    ):
        mock_call_tcp.return_value = {'profileId': 'prof-2'}

        result = await handler.create_profile(
            mock_context,
            profileName='ext-profile',
            identityType='externalIdp',
            clientId='client-123',
            clientSecretArn='arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret',  # pragma: allowlist secret
            authorizationUrl='https://idp.example.com/authorize',
            tokenUrl='https://idp.example.com/token',
            userInfoUrl='https://idp.example.com/userinfo',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True

        body = mock_call_tcp.call_args[0][1]
        ext = body['identitySource']['externalIdpIdentitySource']
        assert ext['clientId'] == 'client-123'
        assert ext['authorizationUrl'] == 'https://idp.example.com/authorize'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.is_sigv4_configured', return_value=True
    )
    async def test_create_profile_invalid_name(self, mock_sigv4, handler, mock_context):
        result = await handler.create_profile(
            mock_context,
            profileName='bad name!',
            identityType='sso',
            ssoInstanceArn='arn:aws:sso:::instance/ssoins-12345',
            ssoRegion='us-east-1',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'profileName' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.is_sigv4_configured', return_value=True
    )
    async def test_create_profile_sso_missing_arn(self, mock_sigv4, handler, mock_context):
        result = await handler.create_profile(
            mock_context,
            profileName='my-profile',
            identityType='sso',
            ssoInstanceArn=None,
            ssoRegion='us-east-1',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert 'ssoInstanceArn' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.is_sigv4_configured', return_value=True
    )
    async def test_create_profile_external_missing_client_id(
        self, mock_sigv4, handler, mock_context
    ):
        result = await handler.create_profile(
            mock_context,
            profileName='my-profile',
            identityType='externalIdp',
            clientId=None,
            clientSecretArn=None,
            authorizationUrl=None,
            tokenUrl=None,
            userInfoUrl=None,
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert 'clientId' in parsed['error']['message']

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.is_sigv4_configured', return_value=False
    )
    async def test_create_profile_sigv4_not_configured(self, mock_sigv4, handler, mock_context):
        result = await handler.create_profile(
            mock_context,
            profileName='my-profile',
            identityType='sso',
            ssoInstanceArn=None,
            ssoRegion=None,
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'SIGV4_NOT_CONFIGURED'


# ── accept_connector ────────────────────────────────────────────────────


class TestAcceptConnector:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.call_fes', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.connector.call_tcp', new_callable=AsyncMock)
    @patch('awslabs.aws_transform_mcp_server.tools.connector.is_configured', return_value=True)
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.is_sigv4_configured', return_value=True
    )
    async def test_accept_connector_success(
        self, mock_sigv4, mock_configured, mock_call_tcp, mock_call_fes, handler, mock_context
    ):
        mock_call_tcp.return_value = {}
        mock_call_fes.return_value = {'connectorId': 'conn-1', 'status': 'ACTIVE'}

        result = await handler.accept_connector(
            mock_context,
            workspaceId='ws-1',
            connectorId='conn-1',
            awsAccountId='123456789012',
            roleArn='arn:aws:iam::123456789012:role/MyRole',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['status'] == 'ACTIVE'

        # Verify TCP call
        tcp_body = mock_call_tcp.call_args[0][1]
        assert tcp_body['connectorId'] == 'conn-1'
        assert tcp_body['resource']['roleArn'] == 'arn:aws:iam::123456789012:role/MyRole'
        assert 'clientToken' in tcp_body

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.is_configured', return_value=True)
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.is_sigv4_configured', return_value=False
    )
    async def test_accept_connector_sigv4_not_configured(
        self, mock_sigv4, mock_configured, handler, mock_context
    ):
        result = await handler.accept_connector(
            mock_context,
            workspaceId='ws-1',
            connectorId='conn-1',
            awsAccountId='123456789012',
            roleArn='arn:aws:iam::123456789012:role/MyRole',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'SIGV4_NOT_CONFIGURED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.connector.is_configured', return_value=False)
    @patch(
        'awslabs.aws_transform_mcp_server.tools.connector.is_sigv4_configured', return_value=True
    )
    async def test_accept_connector_fes_not_configured(
        self, mock_sigv4, mock_configured, handler, mock_context
    ):
        result = await handler.accept_connector(
            mock_context,
            workspaceId='ws-1',
            connectorId='conn-1',
            awsAccountId='123456789012',
            roleArn='arn:aws:iam::123456789012:role/MyRole',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'
