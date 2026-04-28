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

"""Tests for fes_client: cookie/bearer modes, retry, token refresh, errors."""
# ruff: noqa: D101, D102, D103

import httpx
import pytest
import time
from awslabs.aws_transform_mcp_server.consts import (
    FES_TARGET_BEARER,
    FES_TARGET_COOKIE,
)
from awslabs.aws_transform_mcp_server.fes_client import (
    call_fes,
    call_fes_direct_bearer,
    call_fes_direct_cookie,
)
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.models import ConnectionConfig, RefreshedTokens
from unittest.mock import AsyncMock, patch


def _mock_response(status_code: int, json_data: dict | None = None) -> httpx.Response:
    """Build a minimal httpx.Response for testing."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request('POST', 'https://fes.example.com'),
    )


# ── call_fes_direct_cookie ─────────────────────────────────────────────


class TestCallFesDirectCookie:
    """Tests for call_fes_direct_cookie."""

    @patch(
        'awslabs.aws_transform_mcp_server.fes_client.request_with_retry', new_callable=AsyncMock
    )
    async def test_cookie_headers(self, mock_retry: AsyncMock):
        mock_retry.return_value = _mock_response(200, {'result': 'ok'})

        result = await call_fes_direct_cookie(
            endpoint='https://fes.example.com',
            origin='https://origin.example.com',
            cookie='session=abc123',
            operation='VerifySession',
            body={'key': 'value'},
        )

        assert result == {'result': 'ok'}
        mock_retry.assert_called_once()
        call_args = mock_retry.call_args
        # Positional: client, method, url, headers, body
        headers = call_args[0][3]
        assert headers['Content-Type'] == 'application/x-amz-json-1.0'
        assert headers['X-Amz-Target'] == f'{FES_TARGET_COOKIE}.VerifySession'
        assert headers['Origin'] == 'https://origin.example.com'
        assert headers['Cookie'] == 'session=abc123'


# ── call_fes_direct_bearer ─────────────────────────────────────────────


class TestCallFesDirectBearer:
    """Tests for call_fes_direct_bearer."""

    @patch(
        'awslabs.aws_transform_mcp_server.fes_client.request_with_retry', new_callable=AsyncMock
    )
    async def test_bearer_headers_with_origin(self, mock_retry: AsyncMock):
        mock_retry.return_value = _mock_response(200, {'profiles': []})

        result = await call_fes_direct_bearer(
            endpoint='https://fes.example.com',
            token='my-bearer-token',
            operation='ListWorkspaces',
            body={},
            origin='https://origin.example.com',
        )

        assert result == {'profiles': []}
        headers = mock_retry.call_args[0][3]
        assert headers['Content-Type'] == 'application/json; charset=UTF-8'
        assert headers['Content-Encoding'] == 'amz-1.0'
        assert headers['X-Amz-Target'] == f'{FES_TARGET_BEARER}.ListWorkspaces'
        assert headers['Authorization'] == 'Bearer my-bearer-token'
        assert headers['Origin'] == 'https://origin.example.com'

    @patch(
        'awslabs.aws_transform_mcp_server.fes_client.request_with_retry', new_callable=AsyncMock
    )
    async def test_bearer_headers_without_origin_for_list_profiles(self, mock_retry: AsyncMock):
        mock_retry.return_value = _mock_response(200, {'profiles': []})

        await call_fes_direct_bearer(
            endpoint='https://fes.example.com',
            token='my-bearer-token',
            operation='ListAvailableProfiles',
            origin='https://origin.example.com',
        )

        headers = mock_retry.call_args[0][3]
        assert 'Origin' not in headers

    @patch(
        'awslabs.aws_transform_mcp_server.fes_client.request_with_retry', new_callable=AsyncMock
    )
    async def test_bearer_no_origin(self, mock_retry: AsyncMock):
        mock_retry.return_value = _mock_response(200, {})

        await call_fes_direct_bearer(
            endpoint='https://fes.example.com',
            token='tok',
            operation='GetWorkspace',
        )

        headers = mock_retry.call_args[0][3]
        assert 'Origin' not in headers


# ── call_fes (with config routing and token refresh) ──────────────────


class TestCallFes:
    """Tests for call_fes with config routing and token refresh."""

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
        token_expiry: int | None = None,
        refresh_token: str | None = 'refresh-tok',
        oidc_client_id: str | None = 'client-id',
        oidc_client_secret: str | None = 'client-secret',
        oidc_client_secret_expires_at: int | None = None,
        idc_region: str | None = 'us-east-1',
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

    @patch(
        'awslabs.aws_transform_mcp_server.fes_client.request_with_retry', new_callable=AsyncMock
    )
    async def test_cookie_mode(self, mock_retry: AsyncMock):
        mock_retry.return_value = _mock_response(200, {'data': 'ok'})
        config = self._make_cookie_config()

        with (
            patch('awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config),
        ):
            result = await call_fes('ListWorkspaces')

        assert result == {'data': 'ok'}
        headers = mock_retry.call_args[0][3]
        assert headers['Cookie'] == 'session=abc'
        assert headers['X-Amz-Target'] == f'{FES_TARGET_COOKIE}.ListWorkspaces'

    @patch(
        'awslabs.aws_transform_mcp_server.fes_client.request_with_retry', new_callable=AsyncMock
    )
    async def test_bearer_mode_no_refresh_needed(self, mock_retry: AsyncMock):
        mock_retry.return_value = _mock_response(200, {'data': 'ok'})
        # Token expires far in the future
        config = self._make_bearer_config(token_expiry=int(time.time()) + 3600)

        with (
            patch('awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config),
        ):
            result = await call_fes('GetJob', {'jobId': '123'})

        assert result == {'data': 'ok'}
        headers = mock_retry.call_args[0][3]
        assert headers['Authorization'] == 'Bearer current-token'

    @patch(
        'awslabs.aws_transform_mcp_server.fes_client.request_with_retry', new_callable=AsyncMock
    )
    async def test_bearer_token_refresh_triggered(self, mock_retry: AsyncMock):
        mock_retry.return_value = _mock_response(200, {'data': 'refreshed'})
        # Token expires in 60 seconds (< TOKEN_REFRESH_BUFFER_SECS=300)
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
        # Updated token should be used in the request
        headers = mock_retry.call_args[0][3]
        assert headers['Authorization'] == 'Bearer new-token'

    @patch(
        'awslabs.aws_transform_mcp_server.fes_client.request_with_retry', new_callable=AsyncMock
    )
    async def test_bearer_client_registration_expired(self, mock_retry: AsyncMock):
        # Token near expiry AND client registration already expired
        config = self._make_bearer_config(
            token_expiry=int(time.time()) + 60,
            oidc_client_secret_expires_at=int(time.time()) - 100,
        )

        with (
            patch('awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config),
        ):
            with pytest.raises(RuntimeError, match='Client registration expired'):
                await call_fes('ListJobs')

    @patch(
        'awslabs.aws_transform_mcp_server.fes_client.request_with_retry', new_callable=AsyncMock
    )
    async def test_http_error_400(self, mock_retry: AsyncMock):
        mock_retry.side_effect = HttpError(400, {'message': 'bad'}, 'HTTP 400: bad')

        config = self._make_cookie_config()

        with (
            patch('awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config),
        ):
            with pytest.raises(HttpError) as exc_info:
                await call_fes('CreateJob', {'name': 'test'})
            assert exc_info.value.status_code == 400

    @patch(
        'awslabs.aws_transform_mcp_server.fes_client.request_with_retry', new_callable=AsyncMock
    )
    async def test_http_error_401(self, mock_retry: AsyncMock):
        mock_retry.side_effect = HttpError(401, {'message': 'unauthorized'}, 'HTTP 401')

        config = self._make_bearer_config(token_expiry=int(time.time()) + 3600)

        with (
            patch('awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config),
        ):
            with pytest.raises(HttpError) as exc_info:
                await call_fes('GetWorkspace', {'workspaceId': '123'})
            assert exc_info.value.status_code == 401


# ── Retry behavior (via request_with_retry integration) ────────────────


class TestFesRetry:
    """Tests for FES retry behavior via real request_with_retry."""

    @patch('awslabs.aws_transform_mcp_server.http_utils.asyncio.sleep', new_callable=AsyncMock)
    async def test_retry_on_429_via_direct_cookie(self, mock_sleep: AsyncMock):
        """Verify that call_fes_direct_cookie retries on 429 with appropriate delay."""
        responses = [
            _mock_response(429, {'message': 'throttled'}),
            _mock_response(200, {'ok': True}),
        ]

        # Use the real request_with_retry with a mock client
        with patch('awslabs.aws_transform_mcp_server.fes_client.httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(side_effect=responses)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await call_fes_direct_cookie(
                endpoint='https://fes.example.com',
                origin='https://origin.example.com',
                cookie='session=abc',
                operation='VerifySession',
            )

            assert result == {'ok': True}
            assert mock_client.request.call_count == 2
            mock_sleep.assert_called_once()
            # 429 delay should be in [1.0, 1.1] range
            delay = mock_sleep.call_args[0][0]
            assert 1.0 <= delay <= 1.1
