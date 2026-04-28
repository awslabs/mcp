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
from awslabs.aws_transform_mcp_server.models import ConnectionConfig, OAuthTokens
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
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=False)
    async def test_not_configured(self, mock_configured, mock_boto3, handler, mock_context):
        mock_boto3.Session.return_value.get_credentials.return_value = None

        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['configured'] is False
        assert parsed['sigv4']['configured'] is False
        assert result['isError'] is False

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
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
        mock_boto3,
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
        from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper

        AwsHelper.clear_cache()
        mock_fes_cookie.return_value = {'userId': 'user-1'}
        mock_session = mock_boto3.Session.return_value
        mock_session.get_credentials.return_value = True
        mock_session.region_name = 'us-east-1'
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/test/session',
        }
        mock_session.client.return_value = mock_sts

        result = await handler.get_status(mock_context)

        AwsHelper.clear_cache()
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['configured'] is True
        assert parsed['fes']['authMode'] == 'cookie'
        assert parsed['sigv4']['configured'] is True
        assert parsed['sigv4']['accountId'] == '123456789012'
        assert parsed['sigv4']['arn'] == 'arn:aws:sts::123456789012:assumed-role/test/session'
        assert result['isError'] is False

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
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
        mock_boto3,
        handler,
        mock_context,
    ):
        mock_boto3.Session.return_value.get_credentials.return_value = None
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
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
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
        mock_boto3,
        handler,
        mock_context,
    ):
        mock_boto3.Session.return_value.get_credentials.return_value = None
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

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=False)
    async def test_sigv4_bad_region(self, mock_configured, mock_boto3, handler, mock_context):
        """ValueError from derive_tcp_endpoint shows as region error, not credential error."""
        from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper

        AwsHelper.clear_cache()
        mock_session = mock_boto3.Session.return_value
        mock_session.get_credentials.return_value = True
        mock_session.region_name = 'mars-north-1'
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/test/session',
        }
        mock_session.client.return_value = mock_sts

        with patch.dict('os.environ', {'ATX_STAGE': 'gamma', 'AWS_REGION': 'mars-north-1'}):
            result = await handler.get_status(mock_context)

        AwsHelper.clear_cache()
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['sigv4']['configured'] is False
        assert 'Region configuration error' in parsed['sigv4']['message']

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=False)
    async def test_sigv4_sts_failure(self, mock_configured, mock_boto3, handler, mock_context):
        """STS API error shows as credential validation failure."""
        from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper

        AwsHelper.clear_cache()
        mock_session = mock_boto3.Session.return_value
        mock_session.get_credentials.return_value = True
        mock_session.region_name = 'us-east-1'
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = Exception('ExpiredToken')
        mock_session.client.return_value = mock_sts

        with patch.dict('os.environ', {'ATX_STAGE': 'prod', 'AWS_REGION': 'us-east-1'}):
            result = await handler.get_status(mock_context)

        AwsHelper.clear_cache()
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['sigv4']['configured'] is False
        assert 'credential validation failed' in parsed['sigv4']['message'].lower()


class TestConfigureCookieException:
    """Tests for cookie flow exception handling."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_cookie',
        new_callable=AsyncMock,
    )
    async def test_cookie_flow_exception(self, mock_fes_cookie, handler, mock_context):
        """Exception in cookie flow returns failure_result with hint."""
        mock_fes_cookie.side_effect = RuntimeError('connection refused')

        result = await handler.configure(
            mock_context,
            authMode='cookie',
            stage='prod',
            region='us-east-1',
            sessionCookie='my-session-value',
            origin='https://app.transform.us-east-1.on.aws',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
        assert 'connection refused' in parsed['error']['message']
        assert 'hint' in parsed


class TestConfigureSSOException:
    """Tests for SSO flow exception handling."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.get_scope',
        return_value='transform:read_write',
    )
    async def test_sso_flow_exception(self, mock_scope, mock_oauth, handler, mock_context):
        """Exception in SSO flow returns failure_result with hint."""
        mock_oauth.side_effect = TimeoutError('Authentication timed out')

        result = await handler.configure(
            mock_context,
            authMode='sso',
            stage='prod',
            region='us-east-1',
            startUrl='https://d-xxx.awsapps.com/start',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
        assert 'hint' in parsed


class TestGetStatusConfigNone:
    """Tests for get_status when config is None despite is_configured=True."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config', return_value=None)
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=True)
    async def test_config_none_early_return(
        self, mock_configured, mock_get_config, mock_boto3, handler, mock_context
    ):
        """When is_configured=True but get_config=None, returns not-configured status."""
        mock_boto3.Session.return_value.get_credentials.return_value = None

        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['configured'] is False
        assert result['isError'] is False


class TestGetStatusBearerAuth:
    """Tests for get_status bearer auth path and token expiry."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=True)
    async def test_bearer_status_with_token_expiry(
        self,
        mock_configured,
        mock_fes_bearer,
        mock_get_config,
        mock_boto3,
        handler,
        mock_context,
    ):
        """Bearer auth status includes tokenExpiresIn."""
        import time

        future_expiry = int(time.time()) + 1800
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='bearer',
            stage='prod',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            bearer_token='tok-1',
            token_expiry=future_expiry,
        )
        from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper

        AwsHelper.clear_cache()
        mock_fes_bearer.return_value = {'userId': 'user-bearer'}
        mock_boto3.Session.return_value.get_credentials.return_value = None

        result = await handler.get_status(mock_context)

        AwsHelper.clear_cache()
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['configured'] is True
        assert parsed['fes']['authMode'] == 'bearer'
        assert 'tokenExpiresIn' in parsed['fes']
        assert parsed['fes']['tokenExpiresIn'].endswith('s')

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=True)
    async def test_bearer_status_expired_token(
        self,
        mock_configured,
        mock_fes_bearer,
        mock_get_config,
        mock_boto3,
        handler,
        mock_context,
    ):
        """Bearer auth with expired token shows EXPIRED."""
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='bearer',
            stage='prod',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            bearer_token='tok-1',
            token_expiry=1000000,  # long past
        )
        from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper

        AwsHelper.clear_cache()
        mock_fes_bearer.return_value = {'userId': 'user-bearer'}
        mock_boto3.Session.return_value.get_credentials.return_value = None

        result = await handler.get_status(mock_context)

        AwsHelper.clear_cache()
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['tokenExpiresIn'] == 'EXPIRED'


class TestGetStatusGenericException:
    """Tests for get_status with generic (non-HttpError) exceptions."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_cookie',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=True)
    async def test_generic_exception(
        self,
        mock_configured,
        mock_fes_cookie,
        mock_get_config,
        mock_boto3,
        handler,
        mock_context,
    ):
        """Non-HttpError exception in FES verification shows SESSION_CHECK_FAILED."""
        mock_boto3.Session.return_value.get_credentials.return_value = None
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='cookie',
            stage='prod',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            session_cookie='aws-transform-session=abc',
        )
        mock_fes_cookie.side_effect = ConnectionError('DNS resolution failed')

        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['fes']['configured'] is True
        assert parsed['fes']['error']['code'] == 'SESSION_CHECK_FAILED'
        assert 'DNS resolution failed' in parsed['fes']['error']['message']
        assert result['isError'] is True
