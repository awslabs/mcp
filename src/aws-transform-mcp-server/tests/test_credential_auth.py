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

"""Tests for AWS credential auth: probe, direct call, and call_transform_api fallback."""

import pytest
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.transform_api_client import ProfileSelectionRequired
from unittest.mock import AsyncMock, MagicMock, patch


_FES_MOD = 'awslabs.aws_transform_mcp_server.transform_api_client'
_SERVER_MOD = 'awslabs.aws_transform_mcp_server.server'


# ── call_fes_direct_sigv4 ─────────────────────────────────────────────────


class TestCallFesSigv4:
    """Tests for call_fes_direct_sigv4."""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import call_fes_direct_sigv4

        with (
            patch(f'{_FES_MOD}._call_boto3', return_value={'items': []}) as mock_call,
            patch(f'{_FES_MOD}._create_sigv4_client') as mock_create,
        ):
            mock_create.return_value = MagicMock()

            result = await call_fes_direct_sigv4(
                'https://api.transform.us-east-1.on.aws/',
                'ListWorkspaces',
                {},
                region='us-east-1',
            )

        assert result == {'items': []}
        mock_create.assert_called_once()
        mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_credentials_raises(self):
        """SigV4 client creation with no credentials raises ClientError at call time."""
        from awslabs.aws_transform_mcp_server.transform_api_client import call_fes_direct_sigv4

        with (
            patch(f'{_FES_MOD}._call_boto3', side_effect=HttpError(403, {}, 'HTTP 403')),
            patch(f'{_FES_MOD}._create_sigv4_client') as mock_create,
        ):
            mock_create.return_value = MagicMock()

            with pytest.raises(HttpError):
                await call_fes_direct_sigv4(
                    'https://api.transform.us-east-1.on.aws/',
                    'ListWorkspaces',
                    region='us-east-1',
                )


# ── call_transform_api SigV4 fallback ───────────────────────────────────────────────


class TestCallFesSigv4Fallback:
    """Tests for the SigV4 fallback path in call_transform_api."""

    @pytest.mark.asyncio
    async def test_sigv4_fallback_success(self):
        from awslabs.aws_transform_mcp_server import config_store
        from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api

        with (
            patch.object(config_store, 'get_config', return_value=None),
            patch.object(config_store, 'is_sigv4_fes_available', return_value=True),
            patch.object(config_store, 'get_sigv4_region', return_value='us-east-1'),
            patch.object(
                config_store, 'derive_transform_api_endpoint', return_value='https://ep/'
            ),
            patch(f'{_FES_MOD}.call_fes_direct_sigv4', new_callable=AsyncMock) as mock_sigv4,
        ):
            mock_sigv4.return_value = {'items': []}

            result = await call_transform_api('ListWorkspaces')

        assert result == {'items': []}
        mock_sigv4.assert_called_once_with(
            'https://ep/',
            'ListWorkspaces',
            {},
            region='us-east-1',
        )

    @pytest.mark.asyncio
    async def test_sigv4_fallback_region_selection_required(self):
        """When region is not set but regions exist, raises ProfileSelectionRequired."""
        from awslabs.aws_transform_mcp_server import config_store
        from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api

        regions = ['us-east-1', 'eu-central-1']

        with (
            patch.object(config_store, 'get_config', return_value=None),
            patch.object(config_store, 'is_sigv4_fes_available', return_value=True),
            patch.object(config_store, 'get_sigv4_region', return_value=None),
            patch.object(config_store, 'get_sigv4_regions', return_value=regions),
        ):
            with pytest.raises(ProfileSelectionRequired) as exc_info:
                await call_transform_api('ListWorkspaces')

        assert exc_info.value.regions == regions

    @pytest.mark.asyncio
    async def test_sigv4_fallback_auth_failure_does_not_disable(self):
        """401/403 should NOT disable sigv4_fes — credentials are transient."""
        from awslabs.aws_transform_mcp_server import config_store
        from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api

        with (
            patch.object(config_store, 'get_config', return_value=None),
            patch.object(config_store, 'is_sigv4_fes_available', return_value=True),
            patch.object(config_store, 'get_sigv4_region', return_value='us-east-1'),
            patch.object(config_store, 'set_sigv4_fes_available') as mock_set,
            patch.object(
                config_store, 'derive_transform_api_endpoint', return_value='https://ep/'
            ),
            patch(
                f'{_FES_MOD}.call_fes_direct_sigv4',
                new_callable=AsyncMock,
                side_effect=HttpError(403, {'message': 'Forbidden'}),
            ),
        ):
            with pytest.raises(HttpError):
                await call_transform_api('ListWorkspaces')

        mock_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_sigv4_fallback_transient_error_does_not_disable(self):
        """500/503 should NOT set sigv4_fes_available to False."""
        from awslabs.aws_transform_mcp_server import config_store
        from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api

        with (
            patch.object(config_store, 'get_config', return_value=None),
            patch.object(config_store, 'is_sigv4_fes_available', return_value=True),
            patch.object(config_store, 'get_sigv4_region', return_value='us-east-1'),
            patch.object(config_store, 'set_sigv4_fes_available') as mock_set,
            patch.object(
                config_store, 'derive_transform_api_endpoint', return_value='https://ep/'
            ),
            patch(
                f'{_FES_MOD}.call_fes_direct_sigv4',
                new_callable=AsyncMock,
                side_effect=HttpError(503, {'message': 'Service Unavailable'}),
            ),
        ):
            with pytest.raises(HttpError):
                await call_transform_api('ListWorkspaces')

        mock_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_sigv4_fallback_non_http_error_does_not_disable(self):
        """Non-HttpError exceptions should NOT disable SigV4."""
        from awslabs.aws_transform_mcp_server import config_store
        from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api

        with (
            patch.object(config_store, 'get_config', return_value=None),
            patch.object(config_store, 'is_sigv4_fes_available', return_value=True),
            patch.object(config_store, 'get_sigv4_region', return_value='us-east-1'),
            patch.object(config_store, 'set_sigv4_fes_available') as mock_set,
            patch.object(
                config_store, 'derive_transform_api_endpoint', return_value='https://ep/'
            ),
            patch(
                f'{_FES_MOD}.call_fes_direct_sigv4',
                new_callable=AsyncMock,
                side_effect=RuntimeError('network timeout'),
            ),
        ):
            with pytest.raises(RuntimeError):
                await call_transform_api('ListWorkspaces')

        mock_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_explicit_config_supersedes_sigv4(self):
        """When SSO/cookie config exists, SigV4 path is never used."""
        from awslabs.aws_transform_mcp_server import config_store
        from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api

        mock_config = MagicMock()
        mock_config.auth_mode = 'bearer'
        mock_config.bearer_token = 'test-token'
        mock_config.token_expiry = int(__import__('time').time()) + 3600
        mock_config.origin = 'https://test.transform.us-east-1.on.aws'
        mock_config.fes_endpoint = 'https://api.transform.us-east-1.on.aws/'
        mock_config.region = 'us-east-1'

        with (
            patch.object(config_store, 'get_config', return_value=mock_config),
            patch.object(config_store, 'is_sigv4_fes_available', return_value=True),
            patch(f'{_FES_MOD}.call_fes_direct_sigv4', new_callable=AsyncMock) as mock_sigv4,
            patch(f'{_FES_MOD}._create_unsigned_client'),
            patch(f'{_FES_MOD}.asyncio.to_thread', new_callable=AsyncMock) as mock_thread,
        ):
            mock_thread.return_value = {'items': []}
            await call_transform_api('ListWorkspaces')

        mock_sigv4.assert_not_called()


# ── _probe_sigv4_transform_api ──────────────────────────────────────────────────────


class TestProbeSigv4Fes:
    """Tests for the startup SigV4 FES probe with region discovery."""

    @pytest.mark.asyncio
    async def test_no_credentials(self):
        from awslabs.aws_transform_mcp_server.server import _probe_sigv4_transform_api

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None

        with (
            patch(f'{_SERVER_MOD}.AwsHelper') as mock_helper,
            patch(f'{_SERVER_MOD}.set_sigv4_fes_available') as mock_set,
        ):
            mock_helper.create_session.return_value = mock_session
            await _probe_sigv4_transform_api()

        mock_set.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_single_region_auto_selects(self):
        from awslabs.aws_transform_mcp_server.server import _probe_sigv4_transform_api

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = MagicMock()

        with (
            patch(f'{_SERVER_MOD}.AwsHelper') as mock_helper,
            patch(f'{_SERVER_MOD}.set_sigv4_fes_available') as mock_set_available,
            patch(f'{_SERVER_MOD}.set_sigv4_region') as mock_set_region,
            patch(f'{_SERVER_MOD}._discover_sigv4_regions', new_callable=AsyncMock) as mock_disc,
        ):
            mock_helper.create_session.return_value = mock_session
            mock_disc.return_value = ['us-east-1']
            await _probe_sigv4_transform_api()

        mock_set_available.assert_called_once_with(True)
        mock_set_region.assert_called_once_with('us-east-1')

    @pytest.mark.asyncio
    async def test_multiple_regions_stores_list(self):
        from awslabs.aws_transform_mcp_server.server import _probe_sigv4_transform_api

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = MagicMock()

        with (
            patch(f'{_SERVER_MOD}.AwsHelper') as mock_helper,
            patch(f'{_SERVER_MOD}.set_sigv4_fes_available') as mock_set_available,
            patch(f'{_SERVER_MOD}.set_sigv4_region') as mock_set_region,
            patch(f'{_SERVER_MOD}.set_sigv4_regions') as mock_set_regions,
            patch(f'{_SERVER_MOD}._discover_sigv4_regions', new_callable=AsyncMock) as mock_disc,
        ):
            mock_helper.create_session.return_value = mock_session
            mock_disc.return_value = ['us-east-1', 'eu-central-1']
            await _probe_sigv4_transform_api()

        mock_set_available.assert_called_once_with(True)
        mock_set_region.assert_called_once_with(None)
        mock_set_regions.assert_called_once_with(['us-east-1', 'eu-central-1'])

    @pytest.mark.asyncio
    async def test_no_regions_disables(self):
        from awslabs.aws_transform_mcp_server.server import _probe_sigv4_transform_api

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = MagicMock()

        with (
            patch(f'{_SERVER_MOD}.AwsHelper') as mock_helper,
            patch(f'{_SERVER_MOD}.set_sigv4_fes_available') as mock_set,
            patch(f'{_SERVER_MOD}._discover_sigv4_regions', new_callable=AsyncMock) as mock_disc,
        ):
            mock_helper.create_session.return_value = mock_session
            mock_disc.return_value = []
            await _probe_sigv4_transform_api()

        mock_set.assert_called_once_with(False)


# ── regions_for_profile_discovery / _discover_sigv4_regions ──────────────


class TestRegionsForProfileDiscovery:
    def test_uses_aws_region_when_supported(self, monkeypatch):
        from awslabs.aws_transform_mcp_server.consts import regions_for_profile_discovery

        monkeypatch.setenv('AWS_REGION', 'eu-central-1')
        assert regions_for_profile_discovery() == ['eu-central-1']

    def test_falls_back_to_all_regions_when_unset(self, monkeypatch):
        from awslabs.aws_transform_mcp_server.consts import FES_REGIONS, regions_for_profile_discovery

        monkeypatch.delenv('AWS_REGION', raising=False)
        assert regions_for_profile_discovery() == list(FES_REGIONS)

    def test_falls_back_when_aws_region_not_supported(self, monkeypatch):
        from awslabs.aws_transform_mcp_server.consts import FES_REGIONS, regions_for_profile_discovery

        monkeypatch.setenv('AWS_REGION', 'us-west-2')
        assert regions_for_profile_discovery() == list(FES_REGIONS)


class TestDiscoverSigv4Regions:
    @pytest.mark.asyncio
    async def test_probes_only_configured_aws_region(self, monkeypatch):
        from awslabs.aws_transform_mcp_server.server import _discover_sigv4_regions

        monkeypatch.setenv('AWS_REGION', 'us-east-1')

        with patch(f'{_SERVER_MOD}.call_fes_direct_sigv4', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {'workspaces': []}
            regions = await _discover_sigv4_regions()

        assert regions == ['us-east-1']
        assert mock_call.call_count == 1
        assert mock_call.call_args[1]['region'] == 'us-east-1'

    @pytest.mark.asyncio
    async def test_client_creation_runs_in_worker_thread(self):
        from awslabs.aws_transform_mcp_server.transform_api_client import call_fes_direct_sigv4

        async def _run_worker(fn):
            return fn()

        with (
            patch(f'{_FES_MOD}.asyncio.to_thread', side_effect=_run_worker) as mock_to_thread,
            patch(f'{_FES_MOD}._create_sigv4_client') as mock_create,
            patch(f'{_FES_MOD}._call_boto3', return_value={'items': []}) as mock_call,
        ):
            mock_create.return_value = MagicMock()

            result = await call_fes_direct_sigv4(
                'https://api.transform.us-east-1.on.aws/',
                'ListWorkspaces',
                region='us-east-1',
            )

        assert result == {'items': []}
        mock_to_thread.assert_awaited_once()
        mock_create.assert_called_once()
        mock_call.assert_called_once()


# ── _startup clears stale config ─────────────────────────────────────────


class TestStartup:
    """Tests for _startup clearing stale config."""

    @pytest.mark.asyncio
    async def test_clears_config_on_failed_load(self):
        from awslabs.aws_transform_mcp_server.server import _startup

        with (
            patch(f'{_SERVER_MOD}.load_persisted_config', new_callable=AsyncMock) as mock_load,
            patch(f'{_SERVER_MOD}.clear_config') as mock_clear,
            patch(
                f'{_SERVER_MOD}._probe_sigv4_transform_api', new_callable=AsyncMock
            ) as mock_probe,
        ):
            mock_load.return_value = False
            await _startup()

        mock_clear.assert_called_once()
        mock_probe.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_clear_on_successful_load(self):
        from awslabs.aws_transform_mcp_server.server import _startup

        with (
            patch(f'{_SERVER_MOD}.load_persisted_config', new_callable=AsyncMock) as mock_load,
            patch(f'{_SERVER_MOD}.clear_config') as mock_clear,
            patch(
                f'{_SERVER_MOD}._probe_sigv4_transform_api', new_callable=AsyncMock
            ) as mock_probe,
        ):
            mock_load.return_value = True
            await _startup()

        mock_clear.assert_not_called()
        mock_probe.assert_called_once()


# ── derive_transform_api_endpoint validation ───────────────────────────────────────


class TestDeriveFesEndpointValidation:
    """Tests for derive_transform_api_endpoint."""

    def test_returns_correct_url(self):
        from awslabs.aws_transform_mcp_server.config_store import derive_transform_api_endpoint

        assert (
            derive_transform_api_endpoint('us-east-1') == 'https://api.transform.us-east-1.on.aws/'
        )
        assert (
            derive_transform_api_endpoint('us-west-2') == 'https://api.transform.us-west-2.on.aws/'
        )
