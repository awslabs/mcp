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
            sessionCookie='my-session-value',
            origin='https://abc123.transform.us-east-1.on.aws',
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
        'awslabs.aws_transform_mcp_server.tools.configure._discover_profiles',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    async def test_sso_single_profile(
        self,
        mock_oauth,
        mock_discover,
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
        mock_discover.return_value = [
            {
                'profileName': 'default',
                'applicationUrl': 'https://abc123.transform.us-east-1.on.aws/',
                '_region': 'us-east-1',
            }
        ]
        mock_fes_bearer.return_value = {'userId': 'user-sso'}

        result = await handler.configure(
            mock_context,
            authMode='sso',
            startUrl='https://d-xxx.awsapps.com/start',
            idcRegion='us-east-1',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['authMode'] == 'bearer'
        assert parsed['data']['profile'] == 'default'
        assert parsed['data']['session'] == {'userId': 'user-sso'}
        mock_set_config.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure._discover_profiles',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    async def test_sso_no_profiles(self, mock_oauth, mock_discover, handler, mock_context):
        mock_oauth.return_value = OAuthTokens(
            access_token='tok-1',
            refresh_token='ref-1',
            expires_in=3600,
            client_id='cid',
            client_secret='csec',  # pragma: allowlist secret
            client_secret_expires_at=9999999999,
        )
        mock_discover.return_value = []

        result = await handler.configure(
            mock_context,
            authMode='sso',
            idcRegion='us-east-1',
            startUrl='https://d-xxx.awsapps.com/start',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NO_PROFILES'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure._discover_profiles',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    async def test_sso_multiple_profiles_no_selection(
        self, mock_oauth, mock_discover, handler, mock_context
    ):
        mock_oauth.return_value = OAuthTokens(
            access_token='tok-1',
            refresh_token='ref-1',
            expires_in=3600,
            client_id='cid',
            client_secret='csec',  # pragma: allowlist secret
            client_secret_expires_at=9999999999,
        )
        mock_discover.return_value = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa111.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb222.transform.us-west-2.on.aws',
                '_region': 'us-west-2',
            },
        ]

        result = await handler.configure(
            mock_context,
            authMode='sso',
            idcRegion='us-east-1',
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
        'awslabs.aws_transform_mcp_server.tools.configure._discover_profiles',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    async def test_sso_multiple_profiles_with_selection(
        self,
        mock_oauth,
        mock_discover,
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
        mock_discover.return_value = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa111.transform.us-east-1.on.aws/',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb222.transform.us-west-2.on.aws/',
                '_region': 'us-west-2',
            },
        ]
        mock_fes_bearer.return_value = {'userId': 'user-beta'}

        result = await handler.configure(
            mock_context,
            authMode='sso',
            idcRegion='us-east-1',
            startUrl='https://d-xxx.awsapps.com/start',
            profileName='beta',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['profile'] == 'beta'
        config_arg = mock_set_config.call_args[0][0]
        assert config_arg.region == 'us-west-2'
        assert config_arg.idc_region == 'us-east-1'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure._discover_profiles',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.run_oauth_flow',
        new_callable=AsyncMock,
    )
    async def test_sso_profile_not_found(self, mock_oauth, mock_discover, handler, mock_context):
        mock_oauth.return_value = OAuthTokens(
            access_token='tok-1',
            refresh_token='ref-1',
            expires_in=3600,
            client_id='cid',
            client_secret='csec',  # pragma: allowlist secret
            client_secret_expires_at=9999999999,
        )
        mock_discover.return_value = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa111.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb222.transform.us-west-2.on.aws',
                '_region': 'us-west-2',
            },
        ]

        result = await handler.configure(
            mock_context,
            authMode='sso',
            idcRegion='us-east-1',
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


# ── _select_profile fallback ────────────────────────────────────────────


class TestSelectProfileFallback:
    """Tests for _select_profile when client does not support elicitation."""

    @pytest.mark.asyncio
    async def test_fallback_returns_profile_list(self, mock_context):
        """When elicitation is not supported, returns PROFILE_SELECTION_REQUIRED."""
        from awslabs.aws_transform_mcp_server.tools.configure import _select_profile

        # Simulate a client that does NOT support elicitation
        mock_context.session = MagicMock()
        mock_context.session.check_client_capability = MagicMock(return_value=False)

        profiles = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws',
                '_region': 'eu-central-1',
            },
        ]

        result = await _select_profile(mock_context, profiles, None)

        assert 'content' in result
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'PROFILE_SELECTION_REQUIRED'
        assert len(parsed['availableProfiles']) == 2
        assert parsed['availableProfiles'][0]['profileName'] == 'alpha'
        assert parsed['availableProfiles'][1]['profileName'] == 'beta'
        # Verify check_client_capability was actually called
        mock_context.session.check_client_capability.assert_called_once()

    @pytest.mark.asyncio
    async def test_single_profile_auto_selects(self, mock_context):
        """Single profile is auto-selected without elicitation."""
        from awslabs.aws_transform_mcp_server.tools.configure import _select_profile

        profiles = [
            {
                'profileName': 'only',
                'applicationUrl': 'https://aaa.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
        ]

        result = await _select_profile(mock_context, profiles, None)

        assert result == profiles[0]

    @pytest.mark.asyncio
    async def test_profile_name_selects_directly(self, mock_context):
        """When profileName is provided, selects without elicitation."""
        from awslabs.aws_transform_mcp_server.tools.configure import _select_profile

        profiles = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws',
                '_region': 'eu-central-1',
            },
        ]

        result = await _select_profile(mock_context, profiles, 'beta')

        assert result == profiles[1]

    @pytest.mark.asyncio
    async def test_profile_name_not_found(self, mock_context):
        """When profileName doesn't match any of multiple profiles, returns PROFILE_NOT_FOUND."""
        from awslabs.aws_transform_mcp_server.tools.configure import _select_profile

        profiles = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws',
                '_region': 'eu-central-1',
            },
        ]

        result = await _select_profile(mock_context, profiles, 'nonexistent')

        assert 'content' in result
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'PROFILE_NOT_FOUND'


# ── get_status ──────────────────────────────────────────────────────────


class TestGetStatus:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=False)
    async def test_not_configured(self, mock_configured, mock_boto3, handler, mock_context):
        mock_boto3.Session.return_value.get_credentials.return_value = None

        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['connection']['configured'] is False
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
        assert parsed['connection']['configured'] is True
        assert parsed['connection']['authMode'] == 'cookie'
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
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            session_cookie='aws-transform-session=expired',
        )
        mock_fes_cookie.side_effect = HttpError(401, {'message': 'Unauthorized'})

        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['connection']['configured'] is False
        assert (
            'expired' in parsed['connection']['message'].lower()
            or 'unauthorized' in parsed['connection']['message'].lower()
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
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            session_cookie='aws-transform-session=abc',
        )
        mock_fes_cookie.side_effect = HttpError(500, {'message': 'Internal error'})

        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['connection']['configured'] is True
        assert parsed['connection']['error']['code'] == 'SESSION_CHECK_FAILED'
        assert result['isError'] is True

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

        with patch.dict('os.environ', {'AWS_REGION': 'us-east-1'}):
            result = await handler.get_status(mock_context)

        AwsHelper.clear_cache()
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['sigv4']['configured'] is False
        assert 'aws credentials not available' in parsed['sigv4']['message'].lower()


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
            sessionCookie='my-session-value',
            origin='https://abc123.transform.us-east-1.on.aws',
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
    async def test_sso_flow_exception(self, mock_oauth, handler, mock_context):
        """Exception in SSO flow returns failure_result with hint."""
        mock_oauth.side_effect = TimeoutError('Authentication timed out')

        result = await handler.configure(
            mock_context,
            authMode='sso',
            idcRegion='us-east-1',
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
        assert parsed['connection']['configured'] is False
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
        assert parsed['connection']['configured'] is True
        assert parsed['connection']['authMode'] == 'bearer'
        assert 'tokenExpiresIn' in parsed['connection']
        assert parsed['connection']['tokenExpiresIn'].endswith('s')

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
        assert parsed['connection']['tokenExpiresIn'] == 'EXPIRED'


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
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            session_cookie='aws-transform-session=abc',
        )
        mock_fes_cookie.side_effect = ConnectionError('DNS resolution failed')

        result = await handler.get_status(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['connection']['configured'] is True
        assert parsed['connection']['error']['code'] == 'SESSION_CHECK_FAILED'
        assert 'DNS resolution failed' in parsed['connection']['error']['message']
        assert result['isError'] is True


# ── _discover_profiles ─────────────────────────────────────────────────


class TestDiscoverProfiles:
    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.FES_REGIONS',
        ['us-east-1', 'eu-central-1'],
    )
    async def test_discovers_across_regions(self, mock_fes_bearer):
        from awslabs.aws_transform_mcp_server.tools.configure import _discover_profiles

        mock_fes_bearer.side_effect = [
            {
                'profiles': [
                    {
                        'profileName': 'alpha',
                        'applicationUrl': 'https://aaa.transform.us-east-1.on.aws',
                    }
                ]
            },
            {
                'profiles': [
                    {
                        'profileName': 'beta',
                        'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws',
                    }
                ]
            },
        ]

        result = await _discover_profiles('tok-1')

        assert len(result) == 2
        assert result[0]['profileName'] == 'alpha'
        assert result[0]['_region'] == 'us-east-1'
        assert result[1]['profileName'] == 'beta'
        assert result[1]['_region'] == 'eu-central-1'
        assert mock_fes_bearer.call_count == 2

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.FES_REGIONS',
        ['us-east-1', 'eu-central-1'],
    )
    async def test_handles_region_failure(self, mock_fes_bearer):
        from awslabs.aws_transform_mcp_server.tools.configure import _discover_profiles

        mock_fes_bearer.side_effect = [
            RuntimeError('connection refused'),
            {
                'profiles': [
                    {
                        'profileName': 'beta',
                        'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws',
                    }
                ]
            },
        ]

        result = await _discover_profiles('tok-1')

        assert len(result) == 1
        assert result[0]['profileName'] == 'beta'
        assert result[0]['_region'] == 'eu-central-1'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.FES_REGIONS',
        ['us-east-1'],
    )
    async def test_non_dict_response(self, mock_fes_bearer):
        from awslabs.aws_transform_mcp_server.tools.configure import _discover_profiles

        mock_fes_bearer.return_value = 'not-a-dict'

        result = await _discover_profiles('tok-1')

        assert result == []

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.FES_REGIONS',
        ['us-east-1', 'eu-central-1'],
    )
    async def test_empty_profiles(self, mock_fes_bearer):
        from awslabs.aws_transform_mcp_server.tools.configure import _discover_profiles

        mock_fes_bearer.return_value = {'profiles': []}

        result = await _discover_profiles('tok-1')

        assert result == []


# ── _select_profile elicitation paths ──────────────────────────────────


class TestSelectProfileElicitation:
    @pytest.mark.asyncio
    async def test_elicitation_accept_match(self, mock_context):
        from awslabs.aws_transform_mcp_server.tools.configure import _select_profile

        profiles = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws',
                '_region': 'eu-central-1',
            },
        ]

        mock_context.session = MagicMock()
        mock_context.session.check_client_capability = MagicMock(return_value=True)

        mock_result = MagicMock()
        mock_result.action = 'accept'
        mock_result.data = MagicMock()
        mock_result.data.profile = 'beta (eu-central-1)'

        with patch(
            'mcp.server.elicitation.elicit_with_validation',
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await _select_profile(mock_context, profiles, None)

        assert result == profiles[1]

    @pytest.mark.asyncio
    async def test_elicitation_accept_no_match(self, mock_context):
        from awslabs.aws_transform_mcp_server.tools.configure import _select_profile

        profiles = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws',
                '_region': 'eu-central-1',
            },
        ]

        mock_context.session = MagicMock()
        mock_context.session.check_client_capability = MagicMock(return_value=True)

        mock_result = MagicMock()
        mock_result.action = 'accept'
        mock_result.data = MagicMock()
        mock_result.data.profile = 'nonexistent (us-west-2)'

        with patch(
            'mcp.server.elicitation.elicit_with_validation',
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await _select_profile(mock_context, profiles, None)

        assert 'content' in result
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'CANCELLED'

    @pytest.mark.asyncio
    async def test_elicitation_cancelled(self, mock_context):
        from awslabs.aws_transform_mcp_server.tools.configure import _select_profile

        profiles = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws',
                '_region': 'eu-central-1',
            },
        ]

        mock_context.session = MagicMock()
        mock_context.session.check_client_capability = MagicMock(return_value=True)

        mock_result = MagicMock()
        mock_result.action = 'decline'

        with patch(
            'mcp.server.elicitation.elicit_with_validation',
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await _select_profile(mock_context, profiles, None)

        assert 'content' in result
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'CANCELLED'

    @pytest.mark.asyncio
    async def test_elicitation_exception_falls_back(self, mock_context):
        from awslabs.aws_transform_mcp_server.tools.configure import _select_profile

        profiles = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws',
                '_region': 'eu-central-1',
            },
        ]

        mock_context.session = MagicMock()
        mock_context.session.check_client_capability = MagicMock(return_value=True)

        with patch(
            'mcp.server.elicitation.elicit_with_validation',
            new_callable=AsyncMock,
            side_effect=RuntimeError('elicitation unavailable'),
        ):
            result = await _select_profile(mock_context, profiles, None)

        assert 'content' in result
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'PROFILE_SELECTION_REQUIRED'
        assert len(parsed['availableProfiles']) == 2


# ── switch_profile ─────────────────────────────────────────────────────


class TestSwitchProfile:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config', return_value=None)
    async def test_not_configured(self, mock_get_config, handler, mock_context):
        result = await handler.switch_profile(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    async def test_cookie_mode_rejected(self, mock_get_config, handler, mock_context):
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='cookie',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            session_cookie='aws-transform-session=abc',
        )

        result = await handler.switch_profile(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    async def test_token_expired(self, mock_get_config, handler, mock_context):
        mock_get_config.return_value = ConnectionConfig(
            auth_mode='bearer',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            bearer_token='tok-1',
            token_expiry=1000000,
        )

        result = await handler.switch_profile(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'TOKEN_EXPIRED'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure._discover_profiles',
        new_callable=AsyncMock,
        return_value=[],
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    async def test_no_profiles_found(self, mock_get_config, mock_discover, handler, mock_context):
        import time

        mock_get_config.return_value = ConnectionConfig(
            auth_mode='bearer',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            bearer_token='tok-1',
            token_expiry=int(time.time()) + 3600,
        )

        result = await handler.switch_profile(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NO_PROFILES'

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure._select_profile',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure._discover_profiles',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    async def test_profile_selection_returned(
        self, mock_get_config, mock_discover, mock_select, handler, mock_context
    ):
        import time

        mock_get_config.return_value = ConnectionConfig(
            auth_mode='bearer',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            bearer_token='tok-1',
            token_expiry=int(time.time()) + 3600,
        )
        mock_discover.return_value = [
            {
                'profileName': 'alpha',
                'applicationUrl': 'https://aaa.transform.us-east-1.on.aws',
                '_region': 'us-east-1',
            },
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws',
                '_region': 'eu-central-1',
            },
        ]
        mock_select.return_value = {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(
                        {
                            'success': False,
                            'error': {'code': 'PROFILE_SELECTION_REQUIRED'},
                        }
                    ),
                }
            ],
            'isError': True,
        }

        result = await handler.switch_profile(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'PROFILE_SELECTION_REQUIRED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.persist_config')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.set_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure._select_profile',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure._discover_profiles',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    async def test_success(
        self,
        mock_get_config,
        mock_discover,
        mock_select,
        mock_fes_bearer,
        mock_set_config,
        mock_persist,
        handler,
        mock_context,
    ):
        import time

        config = ConnectionConfig(
            auth_mode='bearer',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            bearer_token='tok-1',
            token_expiry=int(time.time()) + 3600,
        )
        mock_get_config.return_value = config
        mock_discover.return_value = [
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws/',
                '_region': 'eu-central-1',
            },
        ]
        mock_select.return_value = {
            'profileName': 'beta',
            'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws/',
            '_region': 'eu-central-1',
        }
        mock_fes_bearer.return_value = {'userId': 'user-beta'}

        result = await handler.switch_profile(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['profile'] == 'beta'
        assert parsed['data']['region'] == 'eu-central-1'
        assert parsed['data']['session'] == {'userId': 'user-beta'}
        mock_set_config.assert_called_once()
        mock_persist.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure._select_profile',
        new_callable=AsyncMock,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure._discover_profiles',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    async def test_verify_session_failure(
        self,
        mock_get_config,
        mock_discover,
        mock_select,
        mock_fes_bearer,
        handler,
        mock_context,
    ):
        import time

        mock_get_config.return_value = ConnectionConfig(
            auth_mode='bearer',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            bearer_token='tok-1',
            token_expiry=int(time.time()) + 3600,
        )
        mock_discover.return_value = [
            {
                'profileName': 'beta',
                'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws/',
                '_region': 'eu-central-1',
            },
        ]
        mock_select.return_value = {
            'profileName': 'beta',
            'applicationUrl': 'https://bbb.transform.eu-central-1.on.aws/',
            '_region': 'eu-central-1',
        }
        mock_fes_bearer.side_effect = RuntimeError('FES unavailable')

        result = await handler.switch_profile(mock_context)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REQUEST_FAILED'
        assert 'FES unavailable' in parsed['error']['message']


# ── configure: missing idcRegion ───────────────────────────────────────


class TestConfigureMissingIdcRegion:
    @pytest.mark.asyncio
    async def test_sso_missing_idc_region(self, handler, mock_context):
        result = await handler.configure(
            mock_context,
            authMode='sso',
            startUrl='https://d-xxx.awsapps.com/start',
            idcRegion=None,
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'VALIDATION_ERROR'
        assert 'idcRegion' in parsed['error']['message']


# ── get_status: bearer with profile_name ───────────────────────────────


class TestGetStatusProfileName:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.aws_helper.boto3')
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config')
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.call_fes_direct_bearer',
        new_callable=AsyncMock,
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.is_configured', return_value=True)
    async def test_bearer_status_with_profile_name(
        self,
        mock_configured,
        mock_fes_bearer,
        mock_get_config,
        mock_boto3,
        handler,
        mock_context,
    ):
        import time

        mock_get_config.return_value = ConnectionConfig(
            auth_mode='bearer',
            region='us-east-1',
            fes_endpoint='https://api.transform.us-east-1.on.aws/',
            origin='https://app.example.com',
            bearer_token='tok-1',
            token_expiry=int(time.time()) + 1800,
            profile_name='my-profile',
        )
        from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper

        AwsHelper.clear_cache()
        mock_fes_bearer.return_value = {'userId': 'user-bearer'}
        mock_boto3.Session.return_value.get_credentials.return_value = None

        result = await handler.get_status(mock_context)

        AwsHelper.clear_cache()
        parsed = json.loads(result['content'][0]['text'])
        assert parsed['connection']['configured'] is True
        assert parsed['connection']['profile'] == 'my-profile'


# ── configure: cookie invalid origin format ────────────────────────────


class TestCookieInvalidOrigin:
    @pytest.mark.asyncio
    async def test_cookie_invalid_origin_format(self, handler, mock_context):
        result = await handler.configure(
            mock_context,
            authMode='cookie',
            sessionCookie='my-session-value',
            origin='https://not-a-transform-url.example.com',
        )

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'INVALID_APPLICATION_URL'


# ── switch_profile: SigV4 region parameter ─────────────────────────────


class TestSwitchProfileSigv4Region:
    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config', return_value=None)
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.is_sigv4_fes_available',
        return_value=True,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.get_sigv4_regions',
        return_value=['us-east-1', 'eu-central-1'],
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_sigv4_region', return_value=None)
    @patch('awslabs.aws_transform_mcp_server.tools.configure.set_sigv4_region')
    async def test_select_valid_region(
        self,
        mock_set,
        mock_get_region,
        mock_get_regions,
        mock_available,
        mock_get_config,
        handler,
        mock_context,
    ):
        result = await handler.switch_profile(mock_context, region='us-east-1')

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is True
        assert parsed['data']['region'] == 'us-east-1'
        mock_set.assert_called_once_with('us-east-1')

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config', return_value=None)
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.is_sigv4_fes_available',
        return_value=True,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.get_sigv4_regions',
        return_value=['us-east-1', 'eu-central-1'],
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_sigv4_region', return_value=None)
    async def test_select_invalid_region(
        self,
        mock_get_region,
        mock_get_regions,
        mock_available,
        mock_get_config,
        handler,
        mock_context,
    ):
        result = await handler.switch_profile(mock_context, region='ap-southeast-2')

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'INVALID_REGION'

    @pytest.mark.asyncio
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_config', return_value=None)
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.is_sigv4_fes_available',
        return_value=True,
    )
    @patch(
        'awslabs.aws_transform_mcp_server.tools.configure.get_sigv4_regions',
        return_value=['us-east-1', 'eu-central-1'],
    )
    @patch('awslabs.aws_transform_mcp_server.tools.configure.get_sigv4_region', return_value=None)
    async def test_no_region_returns_list(
        self,
        mock_get_region,
        mock_get_regions,
        mock_available,
        mock_get_config,
        handler,
        mock_context,
    ):
        mock_context.elicit = AsyncMock(side_effect=Exception('elicitation not supported'))
        result = await handler.switch_profile(mock_context, region=None)

        parsed = json.loads(result['content'][0]['text'])
        assert parsed['success'] is False
        assert parsed['error']['code'] == 'REGION_SELECTION_REQUIRED'
        assert len(parsed['availableRegions']) == 2
