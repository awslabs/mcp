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

"""Tests for configure and get_status tool handlers."""
# ruff: noqa: D101

import json
import pytest
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.models import ConnectionConfig, OAuthTokens, SigV4Config
from awslabs.aws_transform_mcp_server.tools.configure import ConfigureHandler
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def handler(mock_mcp):
    return ConfigureHandler(mock_mcp)


@pytest.fixture
def mock_context():
    ctx = AsyncMock()
    ctx.info = MagicMock(return_value='mock-context')
    return ctx


# ── configure: cookie flow ──────────────────────────────────────────────


class TestConfigureCookie:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.persist_config')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.set_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_cookie',
        new_callable=AsyncMock,
    )
    async def test_cookie_flow_success(
        self, mock_fes_cookie, mock_set_config, mock_persist, handler, mock_context
    ):
        mock_fes_cookie.return_value = {'userId': 'user-1'}

        result = await handler.configure(
            mock_context,
            authMode='cookie',
            stage='prod',
            region='us-east-1',
            sessionCookie='my-session-value',
            origin='https://app.transform.us-east-1.on.aws',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['authMode'] == 'cookie'
        assert parsed['data']['session'] == {'userId': 'user-1'}
        mock_set_config.assert_called_once()
        mock_persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_cookie_flow_missing_cookie(self, handler, mock_context):
        result = await handler.configure(
            mock_context,
            authMode='cookie',
            origin='https://app.transform.us-east-1.on.aws',
            sessionCookie=None,
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'sessionCookie' in parsed['error']['message']

    @pytest.mark.asyncio
    async def test_cookie_flow_missing_origin(self, handler, mock_context):
        result = await handler.configure(
            mock_context,
            authMode='cookie',
            sessionCookie='abc',
            origin=None,
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'origin' in parsed['error']['message']


# ── configure: SSO flow ─────────────────────────────────────────────────


class TestConfigureSSO:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.persist_config')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.set_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.get_scope',
        return_value='transform:read_write',
    )
    async def test_sso_single_profile(
        self,
        mock_scope,
        mock_oauth,
        mock_fes_bearer,
        mock_set_config,
        mock_persist,
        handler,
        mock_context,
    ):
        mock_oauth.return_value = OAuthTokens(
            access_token='tok-1',
            refresh_token='ref-1',
            expires_in=3600,
            client_id='cid',
            client_secret='csec',  # pragma: allowlist secret
            client_secret_expires_at=9999999999,
        )
        mock_fes_bearer.side_effect = [
            # ListAvailableProfiles
            {
                'profiles': [
                    {'profileName': 'default', 'applicationUrl': 'https://app.example.com/'}
                ]
            },
            # VerifySession
            {'userId': 'user-sso'},
        ]

        result = await handler.configure(
            mock_context,
            authMode='sso',
            startUrl='https://d-xxx.awsapps.com/start',
            stage='prod',
            region='us-east-1',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['authMode'] == 'bearer'
        assert parsed['data']['profile'] == 'default'
        assert parsed['data']['session'] == {'userId': 'user-sso'}
        mock_set_config.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.get_scope',
        return_value='transform:read_write',
    )
    async def test_sso_no_profiles(
        self, mock_scope, mock_oauth, mock_fes_bearer, handler, mock_context
    ):
        mock_oauth.return_value = OAuthTokens(
            access_token='tok-1',
            refresh_token='ref-1',
            expires_in=3600,
            client_id='cid',
            client_secret='csec',  # pragma: allowlist secret
            client_secret_expires_at=9999999999,
        )
        mock_fes_bearer.return_value = {'profiles': []}

        result = await handler.configure(
            mock_context,
            authMode='sso',
            stage='prod',
            region='us-east-1',
            startUrl='https://d-xxx.awsapps.com/start',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NO_PROFILES'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.get_scope',
        return_value='transform:read_write',
    )
    async def test_sso_multiple_profiles_no_selection(
        self, mock_scope, mock_oauth, mock_fes_bearer, handler, mock_context
    ):
        mock_oauth.return_value = OAuthTokens(
            access_token='tok-1',
            refresh_token='ref-1',
            expires_in=3600,
            client_id='cid',
            client_secret='csec',  # pragma: allowlist secret
            client_secret_expires_at=9999999999,
        )
        mock_fes_bearer.return_value = {
            'profiles': [
                {'profileName': 'alpha', 'applicationUrl': 'https://alpha.example.com'},
                {'profileName': 'beta', 'applicationUrl': 'https://beta.example.com'},
            ]
        }

        result = await handler.configure(
            mock_context,
            authMode='sso',
            stage='prod',
            region='us-east-1',
            startUrl='https://d-xxx.awsapps.com/start',
            profileName=None,
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'PROFILE_SELECTION_REQUIRED'
        assert len(parsed['availableProfiles']) == 2

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.persist_config')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.set_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.get_scope',
        return_value='transform:read_write',
    )
    async def test_sso_multiple_profiles_with_selection(
        self,
        mock_scope,
        mock_oauth,
        mock_fes_bearer,
        mock_set_config,
        mock_persist,
        handler,
        mock_context,
    ):
        mock_oauth.return_value = OAuthTokens(
            access_token='tok-1',
            refresh_token='ref-1',
            expires_in=3600,
            client_id='cid',
            client_secret='csec',  # pragma: allowlist secret
            client_secret_expires_at=9999999999,
        )
        mock_fes_bearer.side_effect = [
            {
                'profiles': [
                    {'profileName': 'alpha', 'applicationUrl': 'https://alpha.example.com/'},
                    {'profileName': 'beta', 'applicationUrl': 'https://beta.example.com/'},
                ]
            },
            {'userId': 'user-beta'},
        ]

        result = await handler.configure(
            mock_context,
            authMode='sso',
            stage='prod',
            region='us-east-1',
            startUrl='https://d-xxx.awsapps.com/start',
            profileName='beta',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['profile'] == 'beta'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.get_scope',
        return_value='transform:read_write',
    )
    async def test_sso_profile_not_found(
        self, mock_scope, mock_oauth, mock_fes_bearer, handler, mock_context
    ):
        mock_oauth.return_value = OAuthTokens(
            access_token='tok-1',
            refresh_token='ref-1',
            expires_in=3600,
            client_id='cid',
            client_secret='csec',  # pragma: allowlist secret
            client_secret_expires_at=9999999999,
        )
        mock_fes_bearer.return_value = {
            'profiles': [
                {'profileName': 'alpha', 'applicationUrl': 'https://alpha.example.com'},
                {'profileName': 'beta', 'applicationUrl': 'https://beta.example.com'},
            ]
        }

        result = await handler.configure(
            mock_context,
            authMode='sso',
            stage='prod',
            region='us-east-1',
            startUrl='https://d-xxx.awsapps.com/start',
            profileName='nonexistent',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'PROFILE_NOT_FOUND'

    @pytest.mark.asyncio
    async def test_sso_missing_start_url(self, handler, mock_context):
        result = await handler.configure(mock_context, authMode='sso', startUrl=None)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'startUrl' in parsed['error']['message']


# ── get_status ──────────────────────────────────────────────────────────


class TestGetStatus:
    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.is_sigv4_configured', return_value=False
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=False)
    async def test_not_configured(self, mock_configured, mock_sigv4, handler, mock_context):
        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['configured'] is False
        assert parsed['sigv4']['configured'] is False
        assert result['isError'] is False

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_sigv4_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.is_sigv4_configured', return_value=True
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_cookie',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=True)
    async def test_fully_configured(
        self,
        mock_configured,
        mock_fes_cookie,
        mock_get_config,
        mock_sigv4_configured,
        mock_get_sigv4,
        handler,
        mock_context,
    ):
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='cookie',
            stage='prod',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            session_cookie='aws-transform-session=abc',
        )
        mock_fes_cookie.return_value = {'userId': 'user-1'}
        mock_get_sigv4.return_value = SigV4Config(
            account_id='123456789012',
            role='Admin',
            stage='prod',
            region='us-east-1',
            tcp_endpoint='https://transform.us-east-1.api.aws',
            access_key_id='AKID',
            secret_access_key='secret',  # pragma: allowlist secret
            session_token='token',
        )

        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['configured'] is True
        assert parsed['fes']['authMode'] == 'cookie'
        assert parsed['sigv4']['configured'] is True
        assert parsed['sigv4']['accountId'] == '123456789012'
        assert result['isError'] is False

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.is_sigv4_configured', return_value=False
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.clear_config')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_cookie',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=True)
    async def test_expired_session(
        self,
        mock_configured,
        mock_fes_cookie,
        mock_get_config,
        mock_clear,
        mock_sigv4,
        handler,
        mock_context,
    ):
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='cookie',
            stage='prod',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            session_cookie='aws-transform-session=expired',
        )
        mock_fes_cookie.side_effect = HttpError(401, {'message': 'Unauthorized'})

        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['configured'] is False
        assert (
            'expired' in parsed['fes']['message'].lower()
            or 'unauthorized' in parsed['fes']['message'].lower()
        )
        mock_clear.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.is_sigv4_configured', return_value=False
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_cookie',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=True)
    async def test_transient_error(
        self,
        mock_configured,
        mock_fes_cookie,
        mock_get_config,
        mock_sigv4,
        handler,
        mock_context,
    ):
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='cookie',
            stage='prod',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            session_cookie='aws-transform-session=abc',
        )
        mock_fes_cookie.side_effect = HttpError(500, {'message': 'Internal error'})

        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['configured'] is True
        assert parsed['fes']['error']['code'] == 'SESSION_CHECK_FAILED'
        assert result['isError'] is True
