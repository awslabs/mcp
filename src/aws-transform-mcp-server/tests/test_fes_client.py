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

"""Tests for fes_client: cookie/bearer modes, token refresh, errors (boto3-based)."""
# ruff: noqa: D101, D102, D103

import pytest
import time
from awslabs.aws_transform_mcp_server.fes_client import (
    call_fes,
    call_fes_direct_bearer,
    call_fes_direct_cookie,
)
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.models import ConnectionConfig, RefreshedTokens
from unittest.mock import AsyncMock, MagicMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.fes_client'


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


# ── call_fes (with config routing and token refresh) ──────────────────


class TestCallFes:
    def _make_cookie_config(self) -> ConnectionConfig:
        return ConnectionConfig(
            auth_mode='cookie',
            stage='prod',
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
            stage='prod',
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
            result = await call_fes('ListWorkspaces')

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
            result = await call_fes('GetJob', {'jobId': '123'})

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
            result = await call_fes('ListJobs')

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
                await call_fes('ListJobs')

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
                await call_fes('CreateJob', {'name': 'test'})
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
                await call_fes('GetWorkspace', {'workspaceId': '123'})
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
