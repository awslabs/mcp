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

"""Tests for SigV4 FES auth: probe, direct call, and call_fes fallback."""

import pytest
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from unittest.mock import AsyncMock, MagicMock, patch


_FES_MOD = 'awslabs.aws_transform_mcp_server.fes_client'
_SERVER_MOD = 'awslabs.aws_transform_mcp_server.server'


# ── call_fes_direct_sigv4 ─────────────────────────────────────────────────


class TestCallFesSigv4:
    """Tests for call_fes_direct_sigv4."""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        from awslabs.aws_transform_mcp_server.fes_client import call_fes_direct_sigv4

        mock_creds = MagicMock()
        mock_creds.get_frozen_credentials.return_value = MagicMock(
            access_key='AKID',
            secret_key='SECRET',  # pragma: allowlist secret
            token='TOKEN',
        )
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = mock_creds
        mock_session.region_name = 'us-east-1'

        mock_response = MagicMock()
        mock_response.json.return_value = {'items': []}

        with (
            patch(f'{_FES_MOD}.AwsHelper') as mock_helper,
            patch(f'{_FES_MOD}.request_with_retry', new_callable=AsyncMock) as mock_retry,
        ):
            mock_helper.create_session.return_value = mock_session
            mock_helper.resolve_region.return_value = 'us-east-1'
            mock_helper.sign_request.return_value = {'Authorization': 'AWS4-HMAC-SHA256 ...'}
            mock_retry.return_value = mock_response

            result = await call_fes_direct_sigv4(
                'https://api.transform.us-east-1.on.aws/',
                'ListWorkspaces',
                {},
                region='us-east-1',
            )

        assert result == {'items': []}
        mock_helper.sign_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_credentials_raises(self):
        from awslabs.aws_transform_mcp_server.fes_client import call_fes_direct_sigv4

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None

        with patch(f'{_FES_MOD}.AwsHelper') as mock_helper:
            mock_helper.create_session.return_value = mock_session
            mock_helper.resolve_region.return_value = 'us-east-1'

            with pytest.raises(RuntimeError, match='No AWS credentials'):
                await call_fes_direct_sigv4(
                    'https://api.transform.us-east-1.on.aws/', 'ListWorkspaces'
                )


# ── call_fes SigV4 fallback ───────────────────────────────────────────────


class TestCallFesSigv4Fallback:
    """Tests for the SigV4 fallback path in call_fes."""

    @pytest.mark.asyncio
    async def test_sigv4_fallback_success(self):
        from awslabs.aws_transform_mcp_server import config_store
        from awslabs.aws_transform_mcp_server.fes_client import call_fes

        with (
            patch.object(config_store, 'get_config', return_value=None),
            patch.object(config_store, 'is_sigv4_fes_available', return_value=True),
            patch.object(config_store, 'derive_fes_endpoint', return_value='https://ep/'),
            patch(f'{_FES_MOD}.AwsHelper') as mock_helper,
            patch(f'{_FES_MOD}.call_fes_direct_sigv4', new_callable=AsyncMock) as mock_sigv4,
        ):
            mock_helper.create_session.return_value = MagicMock(region_name='us-east-1')
            mock_helper.resolve_region.return_value = 'us-east-1'
            mock_sigv4.return_value = {'items': []}

            result = await call_fes('ListWorkspaces')

        assert result == {'items': []}
        mock_sigv4.assert_called_once()

    @pytest.mark.asyncio
    async def test_sigv4_fallback_auth_failure_disables(self):
        """401/403 should set sigv4_fes_available to False."""
        from awslabs.aws_transform_mcp_server import config_store
        from awslabs.aws_transform_mcp_server.fes_client import call_fes

        with (
            patch.object(config_store, 'get_config', return_value=None),
            patch.object(config_store, 'is_sigv4_fes_available', return_value=True),
            patch.object(config_store, 'set_sigv4_fes_available') as mock_set,
            patch.object(config_store, 'derive_fes_endpoint', return_value='https://ep/'),
            patch(f'{_FES_MOD}.AwsHelper') as mock_helper,
            patch(
                f'{_FES_MOD}.call_fes_direct_sigv4',
                new_callable=AsyncMock,
                side_effect=HttpError(403, {'message': 'Forbidden'}),
            ),
        ):
            mock_helper.create_session.return_value = MagicMock(region_name='us-east-1')
            mock_helper.resolve_region.return_value = 'us-east-1'

            with pytest.raises(HttpError):
                await call_fes('ListWorkspaces')

        mock_set.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_sigv4_fallback_transient_error_does_not_disable(self):
        """500/503 should NOT set sigv4_fes_available to False."""
        from awslabs.aws_transform_mcp_server import config_store
        from awslabs.aws_transform_mcp_server.fes_client import call_fes

        with (
            patch.object(config_store, 'get_config', return_value=None),
            patch.object(config_store, 'is_sigv4_fes_available', return_value=True),
            patch.object(config_store, 'set_sigv4_fes_available') as mock_set,
            patch.object(config_store, 'derive_fes_endpoint', return_value='https://ep/'),
            patch(f'{_FES_MOD}.AwsHelper') as mock_helper,
            patch(
                f'{_FES_MOD}.call_fes_direct_sigv4',
                new_callable=AsyncMock,
                side_effect=HttpError(503, {'message': 'Service Unavailable'}),
            ),
        ):
            mock_helper.create_session.return_value = MagicMock(region_name='us-east-1')
            mock_helper.resolve_region.return_value = 'us-east-1'

            with pytest.raises(HttpError):
                await call_fes('ListWorkspaces')

        mock_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_sigv4_fallback_non_http_error_does_not_disable(self):
        """Non-HttpError exceptions should NOT disable SigV4."""
        from awslabs.aws_transform_mcp_server import config_store
        from awslabs.aws_transform_mcp_server.fes_client import call_fes

        with (
            patch.object(config_store, 'get_config', return_value=None),
            patch.object(config_store, 'is_sigv4_fes_available', return_value=True),
            patch.object(config_store, 'set_sigv4_fes_available') as mock_set,
            patch.object(config_store, 'derive_fes_endpoint', return_value='https://ep/'),
            patch(f'{_FES_MOD}.AwsHelper') as mock_helper,
            patch(
                f'{_FES_MOD}.call_fes_direct_sigv4',
                new_callable=AsyncMock,
                side_effect=RuntimeError('network timeout'),
            ),
        ):
            mock_helper.create_session.return_value = MagicMock(region_name='us-east-1')
            mock_helper.resolve_region.return_value = 'us-east-1'

            with pytest.raises(RuntimeError):
                await call_fes('ListWorkspaces')

        mock_set.assert_not_called()


# ── _probe_sigv4_fes ──────────────────────────────────────────────────────


_HELPER_MOD = 'awslabs.aws_transform_mcp_server.aws_helper'
_CONSTS_MOD = 'awslabs.aws_transform_mcp_server.consts'
_CONFIG_MOD = 'awslabs.aws_transform_mcp_server.config_store'


class TestProbeSigv4Fes:
    """Tests for the startup SigV4 FES probe."""

    @pytest.mark.asyncio
    async def test_disabled_by_flag(self):
        from awslabs.aws_transform_mcp_server.server import _probe_sigv4_fes

        with (
            patch(f'{_CONSTS_MOD}.SIGV4_FES_ENABLED', False),
            patch(f'{_CONFIG_MOD}.set_sigv4_fes_available') as mock_set,
        ):
            await _probe_sigv4_fes()

        mock_set.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_no_credentials(self):
        from awslabs.aws_transform_mcp_server.server import _probe_sigv4_fes

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None

        with (
            patch(f'{_CONSTS_MOD}.SIGV4_FES_ENABLED', True),
            patch(f'{_HELPER_MOD}.AwsHelper.create_session', return_value=mock_session),
            patch(f'{_CONFIG_MOD}.set_sigv4_fes_available') as mock_set,
        ):
            await _probe_sigv4_fes()

        mock_set.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_probe_success(self):
        from awslabs.aws_transform_mcp_server.server import _probe_sigv4_fes

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = MagicMock()
        mock_session.region_name = 'us-east-1'

        with (
            patch(f'{_CONSTS_MOD}.SIGV4_FES_ENABLED', True),
            patch(f'{_HELPER_MOD}.AwsHelper.create_session', return_value=mock_session),
            patch(f'{_HELPER_MOD}.AwsHelper.resolve_region', return_value='us-east-1'),
            patch(f'{_CONFIG_MOD}.set_sigv4_fes_available') as mock_set,
            patch(f'{_CONFIG_MOD}.derive_fes_endpoint', return_value='https://ep/'),
            patch(f'{_FES_MOD}.call_fes_direct_sigv4', new_callable=AsyncMock) as mock_call,
            patch.dict('os.environ', {'ATX_STAGE': 'prod'}),
        ):
            mock_call.return_value = {'items': []}
            await _probe_sigv4_fes()

        mock_set.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_probe_failure(self):
        from awslabs.aws_transform_mcp_server.server import _probe_sigv4_fes

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = MagicMock()
        mock_session.region_name = 'us-east-1'

        with (
            patch(f'{_CONSTS_MOD}.SIGV4_FES_ENABLED', True),
            patch(f'{_HELPER_MOD}.AwsHelper.create_session', return_value=mock_session),
            patch(f'{_HELPER_MOD}.AwsHelper.resolve_region', return_value='us-east-1'),
            patch(f'{_CONFIG_MOD}.set_sigv4_fes_available') as mock_set,
            patch(f'{_CONFIG_MOD}.derive_fes_endpoint', return_value='https://ep/'),
            patch(
                f'{_FES_MOD}.call_fes_direct_sigv4',
                new_callable=AsyncMock,
                side_effect=Exception('connection refused'),
            ),
            patch.dict('os.environ', {'ATX_STAGE': 'prod'}),
        ):
            await _probe_sigv4_fes()

        mock_set.assert_called_once_with(False)


# ── derive_fes_endpoint stage validation ───────────────────────────────────


class TestDeriveFesEndpointValidation:
    """Tests for stage validation in derive_fes_endpoint."""

    def test_valid_stages(self):
        from awslabs.aws_transform_mcp_server.config_store import derive_fes_endpoint

        assert 'prod' not in derive_fes_endpoint('prod', 'us-east-1').split('transform-')
        assert 'gamma' in derive_fes_endpoint('gamma', 'us-east-1')
        assert 'alpha-intg' in derive_fes_endpoint('alpha-intg', 'us-west-2')

    def test_invalid_stage_raises(self):
        from awslabs.aws_transform_mcp_server.config_store import derive_fes_endpoint

        with pytest.raises(ValueError, match='Invalid stage'):
            derive_fes_endpoint('prod.evil.com/', 'us-east-1')

    def test_empty_stage_raises(self):
        from awslabs.aws_transform_mcp_server.config_store import derive_fes_endpoint

        with pytest.raises(ValueError, match='Invalid stage'):
            derive_fes_endpoint('', 'us-east-1')
