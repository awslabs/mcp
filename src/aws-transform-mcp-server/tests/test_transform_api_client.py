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

"""Tests for transform_api_client: cookie/bearer modes, token refresh, errors (boto3-based)."""
# ruff: noqa: D101, D102, D103

import pytest
import time
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.models import ConnectionConfig, RefreshedTokens
from awslabs.aws_transform_mcp_server.transform_api_client import (
    call_fes_direct_bearer,
    call_fes_direct_cookie,
    call_transform_api,
)
from unittest.mock import AsyncMock, MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.transform_api_client'


# ── call_fes_direct_cookie ─────────────────────────────────────────────


class TestCallFesDirectCookie:
    @patch(f'{_MOD}._call_boto3', return_value={'result': 'ok'})
    @patch(f'{_MOD}._inject_cookie_auth')
    @patch(f'{_MOD}._create_unsigned_client')
    async def test_cookie_headers(self, mock_create, mock_inject, mock_call):
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        result = await call_fes_direct_cookie(
            endpoint='https://fes.example.com',
            origin='https://origin.example.com',
            cookie='session=abc123',
            operation='VerifySession',
            body={'key': 'value'},
        )

        assert result == {'result': 'ok'}
        mock_create.assert_called_once()
        mock_inject.assert_called_once_with(
            mock_client, 'https://origin.example.com', 'session=abc123'
        )
        mock_call.assert_called_once_with(mock_client, 'VerifySession', {'key': 'value'})


# ── call_fes_direct_bearer ─────────────────────────────────────────────


class TestCallFesDirectBearer:
    @patch(f'{_MOD}._call_boto3', return_value={'profiles': []})
    @patch(f'{_MOD}._inject_bearer_auth')
    @patch(f'{_MOD}._create_unsigned_client')
    async def test_bearer_with_origin(self, mock_create, mock_inject, mock_call):
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        result = await call_fes_direct_bearer(
            endpoint='https://fes.example.com',
            token='my-bearer-token',
            operation='ListWorkspaces',
            body={},
            origin='https://origin.example.com',
        )

        assert result == {'profiles': []}
        mock_inject.assert_called_once_with(
            mock_client, 'my-bearer-token', 'https://origin.example.com'
        )

    @patch(f'{_MOD}._call_boto3', return_value={'profiles': []})
    @patch(f'{_MOD}._inject_bearer_auth')
    @patch(f'{_MOD}._create_unsigned_client')
    async def test_bearer_no_origin(self, mock_create, mock_inject, mock_call):
        mock_create.return_value = MagicMock()

        await call_fes_direct_bearer(
            endpoint='https://fes.example.com',
            token='tok',
            operation='GetWorkspace',
        )

        mock_inject.assert_called_once_with(mock_create.return_value, 'tok', None)


# ── call_transform_api (with config routing and token refresh) ──────────────────


class TestCallFes:
    def _make_cookie_config(self) -> ConnectionConfig:
        return ConnectionConfig(
            auth_mode='cookie',
            region='us-west-2',
            fes_endpoint='https://fes.example.com',
            origin='https://origin.example.com',
            session_cookie='session=abc',
        )

    def _make_bearer_config(
        self,
        token_expiry=None,
        refresh_token='refresh-tok',
        oidc_client_id='client-id',
        oidc_client_secret='client-secret',  # pragma: allowlist secret
        oidc_client_secret_expires_at=None,
        idc_region='us-east-1',
    ) -> ConnectionConfig:
        return ConnectionConfig(
            auth_mode='bearer',
            region='us-west-2',
            fes_endpoint='https://fes.example.com',
            origin='https://origin.example.com',
            bearer_token='current-token',
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            oidc_client_id=oidc_client_id,
            oidc_client_secret=oidc_client_secret,
            oidc_client_secret_expires_at=oidc_client_secret_expires_at,
            idc_region=idc_region,
        )

    @patch(f'{_MOD}._call_boto3', return_value={'data': 'ok'})
    @patch(f'{_MOD}._inject_cookie_auth')
    @patch(f'{_MOD}._create_unsigned_client')
    async def test_cookie_mode(self, mock_create, mock_inject, mock_call):
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        config = self._make_cookie_config()

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config
        ):
            result = await call_transform_api('ListWorkspaces')

        assert result == {'data': 'ok'}
        mock_inject.assert_called_once_with(
            mock_client, 'https://origin.example.com', 'session=abc'
        )

    @patch(f'{_MOD}._call_boto3', return_value={'data': 'ok'})
    @patch(f'{_MOD}._inject_bearer_auth')
    @patch(f'{_MOD}._create_unsigned_client')
    async def test_bearer_mode_no_refresh_needed(self, mock_create, mock_inject, mock_call):
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        config = self._make_bearer_config(token_expiry=int(time.time()) + 3600)

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config
        ):
            result = await call_transform_api('GetJob', {'jobId': '123'})

        assert result == {'data': 'ok'}
        mock_inject.assert_called_once_with(
            mock_client, 'current-token', 'https://origin.example.com'
        )

    @patch(f'{_MOD}._call_boto3', return_value={'data': 'refreshed'})
    @patch(f'{_MOD}._inject_bearer_auth')
    @patch(f'{_MOD}._create_unsigned_client')
    async def test_bearer_token_refresh_triggered(self, mock_create, mock_inject, mock_call):
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        config = self._make_bearer_config(token_expiry=int(time.time()) + 60)

        mock_refresh = AsyncMock(
            return_value=RefreshedTokens(
                access_token='new-token',
                refresh_token='new-refresh',
                expires_in=3600,
            )
        )

        with (
            patch('awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config),
            patch('awslabs.aws_transform_mcp_server.config_store.set_config') as mock_set,
            patch('awslabs.aws_transform_mcp_server.config_store.persist_config') as mock_persist,
            patch('awslabs.aws_transform_mcp_server.oauth.refresh_access_token', mock_refresh),
        ):
            result = await call_transform_api('ListJobs')

        assert result == {'data': 'refreshed'}
        mock_refresh.assert_called_once()
        mock_set.assert_called_once()
        mock_persist.assert_called_once()
        # Updated token should be used
        mock_inject.assert_called_once_with(mock_client, 'new-token', 'https://origin.example.com')

    async def test_bearer_client_registration_expired(self):
        config = self._make_bearer_config(
            token_expiry=int(time.time()) + 60,
            oidc_client_secret_expires_at=int(time.time()) - 100,
        )

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config
        ):
            with pytest.raises(RuntimeError, match='Client registration expired'):
                await call_transform_api('ListJobs')

    @patch(f'{_MOD}._call_boto3', side_effect=HttpError(400, {'message': 'bad'}, 'HTTP 400: bad'))
    @patch(f'{_MOD}._inject_cookie_auth')
    @patch(f'{_MOD}._create_unsigned_client')
    async def test_http_error_400(self, mock_create, mock_inject, mock_call):
        mock_create.return_value = MagicMock()
        config = self._make_cookie_config()

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config
        ):
            with pytest.raises(HttpError) as exc_info:
                await call_transform_api('CreateJob', {'name': 'test'})
            assert exc_info.value.status_code == 400

    @patch(
        f'{_MOD}._call_boto3', side_effect=HttpError(401, {'message': 'unauthorized'}, 'HTTP 401')
    )
    @patch(f'{_MOD}._inject_bearer_auth')
    @patch(f'{_MOD}._create_unsigned_client')
    async def test_http_error_401(self, mock_create, mock_inject, mock_call):
        mock_create.return_value = MagicMock()
        config = self._make_bearer_config(token_expiry=int(time.time()) + 3600)

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config
        ):
            with pytest.raises(HttpError) as exc_info:
                await call_transform_api('GetWorkspace', {'workspaceId': '123'})
            assert exc_info.value.status_code == 401


# ── Retry behavior (botocore handles retries internally) ────────────────


class TestFesRetry:
    @patch(f'{_MOD}._call_boto3', return_value={'ok': True})
    @patch(f'{_MOD}._inject_cookie_auth')
    @patch(f'{_MOD}._create_unsigned_client')
    async def test_retry_delegated_to_botocore(self, mock_create, mock_inject, mock_call):
        """Verify botocore adaptive retry is configured via _create_unsigned_client."""
        mock_create.return_value = MagicMock()

        result = await call_fes_direct_cookie(
            endpoint='https://fes.example.com',
            origin='https://origin.example.com',
            cookie='session=abc',
            operation='VerifySession',
        )

        assert result == {'ok': True}
        # Retry is handled by botocore config, not by our code
        mock_call.assert_called_once()


# ── _create_unsigned_client / _create_sigv4_client ────────────────────


class TestCreateClients:
    @patch(f'{_MOD}.create_session')
    def test_create_unsigned_client(self, mock_create_session):
        from awslabs.aws_transform_mcp_server.transform_api_client import _create_unsigned_client

        mock_session = MagicMock()
        mock_create_session.return_value = mock_session

        client = _create_unsigned_client('https://fes.example.com', region='us-west-2')

        mock_session.client.assert_called_once()
        call_kwargs = mock_session.client.call_args
        assert call_kwargs[0][0] == 'elasticgumbyfrontendservice'
        assert call_kwargs[1]['region_name'] == 'us-west-2'
        assert call_kwargs[1]['endpoint_url'] == 'https://fes.example.com'
        assert client == mock_session.client.return_value

    @patch(f'{_MOD}.boto3')
    @patch(f'{_MOD}.botocore.session')
    def test_create_sigv4_client(self, mock_bc_session, mock_boto3):
        from awslabs.aws_transform_mcp_server.transform_api_client import _create_sigv4_client

        mock_core = MagicMock()
        mock_bc_session.get_session.return_value = mock_core
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session

        client = _create_sigv4_client('https://fes.example.com', region='eu-central-1')

        mock_core.set_config_variable.assert_any_call('region', 'eu-central-1')
        mock_session.client.assert_called_once()
        call_kwargs = mock_session.client.call_args
        assert call_kwargs[0][0] == 'elasticgumbyfrontendservice'
        assert call_kwargs[1]['region_name'] == 'eu-central-1'
        assert client == mock_session.client.return_value


# ── _inject_cookie_auth / _inject_bearer_auth ─────────────────────────


class TestInjectAuth:
    def test_inject_cookie_auth_sets_headers(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import _inject_cookie_auth

        mock_client = MagicMock()
        handlers = []
        mock_client.meta.events.register = lambda event, handler: handlers.append(handler)

        _inject_cookie_auth(mock_client, 'https://origin.example.com', 'session=abc')

        assert len(handlers) == 1
        params = {'headers': {}}
        handlers[0](params)
        assert params['headers']['Origin'] == 'https://origin.example.com'
        assert params['headers']['Cookie'] == 'session=abc'

    def test_inject_bearer_auth_sets_headers(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import _inject_bearer_auth

        mock_client = MagicMock()
        handlers = []
        mock_client.meta.events.register = lambda event, handler: handlers.append(handler)

        _inject_bearer_auth(mock_client, 'my-token', 'https://origin.example.com')

        assert len(handlers) == 1
        params = {'headers': {}}
        model = MagicMock()
        model.name = 'GetWorkspace'
        handlers[0](params, model=model)
        assert params['headers']['Authorization'] == 'Bearer my-token'
        assert params['headers']['Origin'] == 'https://origin.example.com'
        assert 'X-Amz-Target' in params['headers']

    def test_inject_bearer_auth_skips_origin_for_list_profiles(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import _inject_bearer_auth

        mock_client = MagicMock()
        handlers = []
        mock_client.meta.events.register = lambda event, handler: handlers.append(handler)

        _inject_bearer_auth(mock_client, 'my-token', 'https://origin.example.com')

        params = {'headers': {}}
        model = MagicMock()
        model.name = 'ListAvailableProfiles'
        handlers[0](params, model=model)
        assert 'Origin' not in params['headers']
        assert params['headers']['Authorization'] == 'Bearer my-token'


# ── _call_boto3 ───────────────────────────────────────────────────────


class TestCallBoto3:
    def test_success_with_metadata(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import _call_boto3

        mock_client = MagicMock()
        mock_client.verify_session.return_value = {
            'userId': 'user-1',
            'ResponseMetadata': {'RequestId': 'req-123'},
        }

        result = _call_boto3(mock_client, 'VerifySession', {})

        assert result == {'userId': 'user-1'}
        mock_client.verify_session.assert_called_once_with()

    def test_unknown_operation_raises(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import _call_boto3

        mock_client = MagicMock(spec=[])

        with pytest.raises(ValueError, match='Unknown operation'):
            _call_boto3(mock_client, 'NonexistentOp', {})

    def test_client_error_raises_http_error(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import _call_boto3
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.get_job.side_effect = ClientError(
            {
                'Error': {'Code': 'NotFound', 'Message': 'Job not found'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetJob',
        )

        with pytest.raises(HttpError) as exc_info:
            _call_boto3(mock_client, 'GetJob', {'jobId': '123'})
        assert exc_info.value.status_code == 404


# ── call_fes_direct_sigv4 ─────────────────────────────────────────────


class TestCallFesDirectSigv4:
    @patch(f'{_MOD}._call_boto3', return_value={'ok': True})
    @patch(f'{_MOD}._create_sigv4_client')
    @patch(f'{_MOD}.AwsHelper')
    async def test_resolves_region_when_none(self, mock_helper, mock_create, mock_call):
        from awslabs.aws_transform_mcp_server.transform_api_client import call_fes_direct_sigv4

        mock_session = MagicMock()
        mock_helper.create_session.return_value = mock_session
        mock_helper.resolve_region.return_value = 'us-west-2'
        mock_create.return_value = MagicMock()

        result = await call_fes_direct_sigv4('https://fes.example.com', 'VerifySession')

        assert result == {'ok': True}
        mock_helper.resolve_region.assert_called_once_with(mock_session)
        mock_create.assert_called_once()
        assert mock_create.call_args[1]['region'] == 'us-west-2'

    @patch(f'{_MOD}._call_boto3', return_value={'ok': True})
    @patch(f'{_MOD}._create_sigv4_client')
    async def test_uses_provided_region(self, mock_create, mock_call):
        from awslabs.aws_transform_mcp_server.transform_api_client import call_fes_direct_sigv4

        mock_create.return_value = MagicMock()

        await call_fes_direct_sigv4('https://fes.example.com', 'VerifySession', region='eu-west-1')

        assert mock_create.call_args[1]['region'] == 'eu-west-1'


# ── call_transform_api with FESRequest body ─────────────────────────────────────


class TestCallFesWithPydanticBody:
    @patch(f'{_MOD}._call_boto3', return_value={'data': 'ok'})
    @patch(f'{_MOD}._inject_bearer_auth')
    @patch(f'{_MOD}._create_unsigned_client')
    async def test_fes_request_model_serialized(self, mock_create, mock_inject, mock_call):
        from awslabs.aws_transform_mcp_server.transform_api_models import FESRequest

        mock_create.return_value = MagicMock()
        config = ConnectionConfig(
            auth_mode='bearer',
            region='us-east-1',
            fes_endpoint='https://fes.example.com',
            origin='https://origin.example.com',
            bearer_token='tok-1',
            token_expiry=int(time.time()) + 3600,
        )

        class TestRequest(FESRequest):
            job_id: str

            class Config:
                populate_by_name = True

        req = TestRequest(job_id='j-123')

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config
        ):
            result = await call_transform_api('GetJob', req)

        assert result == {'data': 'ok'}
        call_body = mock_call.call_args[0][2]
        assert isinstance(call_body, dict)


# ── _ensure_fresh_token missing fields ────────────────────────────────


class TestEnsureFreshTokenMissingFields:
    async def test_returns_unchanged_when_no_refresh_token(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import _ensure_fresh_token

        config = ConnectionConfig(
            auth_mode='bearer',
            region='us-east-1',
            fes_endpoint='https://fes.example.com',
            origin='https://origin.example.com',
            bearer_token='tok-1',
            token_expiry=int(time.time()) + 60,
            refresh_token=None,
            oidc_client_id='cid',
            oidc_client_secret='csec',  # pragma: allowlist secret
            idc_region='us-east-1',
        )

        result = await _ensure_fresh_token(config)

        assert result is config
        assert result.bearer_token == 'tok-1'

    async def test_returns_unchanged_when_no_client_id(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import _ensure_fresh_token

        config = ConnectionConfig(
            auth_mode='bearer',
            region='us-east-1',
            fes_endpoint='https://fes.example.com',
            origin='https://origin.example.com',
            bearer_token='tok-1',
            token_expiry=int(time.time()) + 60,
            refresh_token='ref',
            oidc_client_id=None,
            oidc_client_secret='csec',  # pragma: allowlist secret
            idc_region='us-east-1',
        )

        result = await _ensure_fresh_token(config)

        assert result is config
