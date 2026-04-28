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

import pytest
import time
from awslabs.aws_transform_mcp_server.fes_client import (
    call_fes,
    call_fes_direct_bearer,
    call_fes_direct_cookie,
)
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.models import ConnectionConfig, RefreshedTokens
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_boto3_client(response: dict | None = None, side_effect=None) -> MagicMock:
    """Build a mock boto3 FES client."""
    client = MagicMock()
    client._endpoint = MagicMock()
    client._endpoint.make_request = MagicMock()

    if response is not None:
        full_response = {**response, 'ResponseMetadata': {'HTTPStatusCode': 200}}
        # Explicitly set common methods
        for method_name in [
            'list_workspaces',
            'create_workspace',
            'get_workspace',
            'delete_workspace',
            'create_job',
            'get_job',
            'list_jobs',
            'start_job',
            'stop_job',
            'delete_job',
            'get_hitl_task',
            'list_hitl_tasks',
            'update_hitl_task',
            'submit_standard_hitl_task',
            'submit_critical_hitl_task',
            'create_artifact_upload_url',
            'complete_artifact_upload',
            'create_artifact_download_url',
            'create_asset_download_url',
            'list_artifacts',
            'list_job_plan_steps',
            'list_plan_updates',
            'list_connectors',
            'create_connector',
            'get_connector',
            'send_message',
            'list_messages',
            'batch_get_message',
            'list_worklogs',
            'list_agents',
            'search_users_typeahead',
            'batch_get_user_details',
            'list_user_role_mappings',
            'put_user_role_mappings',
            'delete_user_role_mappings',
            'delete_self_role_mappings',
            'verify_session',
            'list_available_profiles',
        ]:
            getattr(client, method_name).return_value = full_response

    if side_effect is not None:
        for method_name in [
            'list_workspaces',
            'create_job',
            'get_workspace',
            'get_job',
            'list_jobs',
            'verify_session',
        ]:
            getattr(client, method_name).side_effect = side_effect

    return client


# ── call_fes_direct_cookie ─────────────────────────────────────────────


class TestCallFesDirectCookie:
    """Tests for call_fes_direct_cookie via boto3."""

    @patch('awslabs.aws_transform_mcp_server.fes_client._create_boto3_client')
    async def test_cookie_call(self, mock_create: MagicMock):
        mock_client = _mock_boto3_client({'result': 'ok'})
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
        mock_client.verify_session.assert_called_once_with(key='value')

    @patch('awslabs.aws_transform_mcp_server.fes_client._create_boto3_client')
    async def test_cookie_error_maps_to_http_error(self, mock_create: MagicMock):
        error_response = {
            'Error': {'Code': 'AccessDeniedException', 'Message': 'expired'},
            'ResponseMetadata': {'HTTPStatusCode': 401},
        }
        mock_client = _mock_boto3_client(side_effect=ClientError(error_response, 'VerifySession'))
        mock_create.return_value = mock_client

        with pytest.raises(HttpError) as exc_info:
            await call_fes_direct_cookie(
                endpoint='https://fes.example.com',
                origin='https://origin.example.com',
                cookie='session=abc',
                operation='VerifySession',
            )
        assert exc_info.value.status_code == 401


# ── call_fes_direct_bearer ─────────────────────────────────────────────


class TestCallFesDirectBearer:
    """Tests for call_fes_direct_bearer via boto3."""

    @patch('awslabs.aws_transform_mcp_server.fes_client._create_boto3_client')
    async def test_bearer_call(self, mock_create: MagicMock):
        mock_client = _mock_boto3_client({'profiles': []})
        mock_create.return_value = mock_client

        result = await call_fes_direct_bearer(
            endpoint='https://fes.example.com',
            token='my-bearer-token',
            operation='ListWorkspaces',
            body={},
            origin='https://origin.example.com',
        )

        assert result == {'profiles': []}
        mock_client.list_workspaces.assert_called_once_with()

    @patch('awslabs.aws_transform_mcp_server.fes_client._create_boto3_client')
    async def test_bearer_no_body(self, mock_create: MagicMock):
        mock_client = _mock_boto3_client({})
        mock_create.return_value = mock_client

        await call_fes_direct_bearer(
            endpoint='https://fes.example.com',
            token='tok',
            operation='GetWorkspace',
        )

        mock_client.get_workspace.assert_called_once_with()


# ── call_fes (with config routing and token refresh) ──────────────────


class TestCallFes:
    """Tests for call_fes with boto3 client, config routing, and token refresh."""

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

    @patch('awslabs.aws_transform_mcp_server.fes_client._create_boto3_client')
    async def test_cookie_mode(self, mock_create: MagicMock):
        mock_client = _mock_boto3_client({'data': 'ok'})
        mock_create.return_value = mock_client
        config = self._make_cookie_config()

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config
        ):
            result = await call_fes('ListWorkspaces')

        assert result == {'data': 'ok'}
        mock_client.list_workspaces.assert_called_once_with()

    @patch('awslabs.aws_transform_mcp_server.fes_client._create_boto3_client')
    async def test_bearer_mode_no_refresh_needed(self, mock_create: MagicMock):
        mock_client = _mock_boto3_client({'data': 'ok'})
        mock_create.return_value = mock_client
        config = self._make_bearer_config(token_expiry=int(time.time()) + 3600)

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config
        ):
            result = await call_fes('GetJob', {'jobId': '123'})

        assert result == {'data': 'ok'}
        mock_client.get_job.assert_called_once_with(jobId='123')

    @patch('awslabs.aws_transform_mcp_server.fes_client._create_boto3_client')
    async def test_bearer_token_refresh_triggered(self, mock_create: MagicMock):
        mock_client = _mock_boto3_client({'data': 'refreshed'})
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

    @patch('awslabs.aws_transform_mcp_server.fes_client._create_boto3_client')
    async def test_http_error_400(self, mock_create: MagicMock):
        error_response = {
            'Error': {'Code': 'ValidationException', 'Message': 'bad'},
            'ResponseMetadata': {'HTTPStatusCode': 400},
        }
        mock_client = _mock_boto3_client(side_effect=ClientError(error_response, 'CreateJob'))
        mock_create.return_value = mock_client
        config = self._make_cookie_config()

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config
        ):
            with pytest.raises(HttpError) as exc_info:
                await call_fes('CreateJob', {'name': 'test'})
            assert exc_info.value.status_code == 400

    @patch('awslabs.aws_transform_mcp_server.fes_client._create_boto3_client')
    async def test_http_error_401(self, mock_create: MagicMock):
        error_response = {
            'Error': {'Code': 'AccessDeniedException', 'Message': 'unauthorized'},
            'ResponseMetadata': {'HTTPStatusCode': 401},
        }
        mock_client = _mock_boto3_client(side_effect=ClientError(error_response, 'GetWorkspace'))
        mock_create.return_value = mock_client
        config = self._make_bearer_config(token_expiry=int(time.time()) + 3600)

        with patch(
            'awslabs.aws_transform_mcp_server.config_store.get_config', return_value=config
        ):
            with pytest.raises(HttpError) as exc_info:
                await call_fes('GetWorkspace', {'workspaceId': '123'})
            assert exc_info.value.status_code == 401
