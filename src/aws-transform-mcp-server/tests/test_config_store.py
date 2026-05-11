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

"""Tests for config_store module."""

import json
import os
import pytest
import time
from awslabs.aws_transform_mcp_server import config_store
from awslabs.aws_transform_mcp_server.config_store import (
    build_bearer_config,
    build_cookie_config,
    clear_config,
    derive_tcp_endpoint,
    derive_transform_api_endpoint,
    extract_region_from_origin,
    get_config,
    is_configured,
    load_persisted_config,
    persist_config,
    set_config,
)
from awslabs.aws_transform_mcp_server.models import RefreshedTokens
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset default store state before each test."""
    store = config_store._default_store
    store._config = None
    yield
    store._config = None


# ── derive_fes_endpoint ─────────────────────────────────────────────────


class TestDeriveFesEndpoint:
    """Tests for derive_fes_endpoint."""

    def test_us_east_1(self):
        url = derive_transform_api_endpoint('us-east-1')
        assert url == 'https://api.transform.us-east-1.on.aws/'

    def test_us_west_2(self):
        url = derive_transform_api_endpoint('us-west-2')
        assert url == 'https://api.transform.us-west-2.on.aws/'

    def test_eu_west_1(self):
        url = derive_transform_api_endpoint('eu-west-1')
        assert url == 'https://api.transform.eu-west-1.on.aws/'


# ── derive_tcp_endpoint ─────────────────────────────────────────────────


class TestDeriveTcpEndpoint:
    """Tests for derive_tcp_endpoint."""

    def test_us_east_1(self):
        url = derive_tcp_endpoint('us-east-1')
        assert url == 'https://transform.us-east-1.api.aws'

    def test_us_west_2(self):
        url = derive_tcp_endpoint('us-west-2')
        assert url == 'https://transform.us-west-2.api.aws'


# ── extract_region_from_origin ──────────────────────────────────────────


class TestExtractRegionFromOrigin:
    """Tests for extract_region_from_origin."""

    def test_prod_url(self):
        assert (
            extract_region_from_origin('https://abc123.transform.us-east-1.on.aws') == 'us-east-1'
        )

    def test_prod_url_trailing_slash(self):
        assert (
            extract_region_from_origin('https://72236b7f3fa56e503.transform.us-east-1.on.aws/')
            == 'us-east-1'
        )

    def test_legacy_suffixed_url(self):
        assert (
            extract_region_from_origin('https://abc123.transform-gamma.us-west-2.on.aws')
            == 'us-west-2'
        )

    def test_alpha_intg_url(self):
        assert (
            extract_region_from_origin('https://abc123.transform-alpha-intg.us-west-2.on.aws')
            == 'us-west-2'
        )

    def test_different_region(self):
        assert (
            extract_region_from_origin('https://abc123.transform.eu-central-1.on.aws')
            == 'eu-central-1'
        )

    def test_non_matching_url(self):
        assert extract_region_from_origin('https://app.example.com') is None

    def test_empty_string(self):
        assert extract_region_from_origin('') is None


# ── build_cookie_config ─────────────────────────────────────────────────


class TestBuildCookieConfig:
    """Tests for build_cookie_config."""

    def test_cookie_without_prefix(self):
        cfg = build_cookie_config(
            origin='https://example.com/',
            session_cookie='abc123',
            region='us-east-1',
        )
        assert cfg.session_cookie == 'aws-transform-session=abc123'
        assert cfg.auth_mode == 'cookie'
        assert cfg.origin == 'https://example.com'  # trailing slash stripped

    def test_cookie_with_prefix(self):
        cfg = build_cookie_config(
            origin='https://example.com',
            session_cookie='aws-transform-session=abc123',
            region='us-west-2',
        )
        assert cfg.session_cookie == 'aws-transform-session=abc123'

    def test_origin_trailing_slash_stripped(self):
        cfg = build_cookie_config(
            origin='https://example.com/',
            session_cookie='tok',
            region='us-east-1',
        )
        assert cfg.origin == 'https://example.com'

    def test_fes_endpoint_set(self):
        cfg = build_cookie_config(
            origin='https://example.com',
            session_cookie='tok',
            region='eu-west-1',
        )
        assert cfg.fes_endpoint == derive_transform_api_endpoint('eu-west-1')


# ── build_bearer_config ─────────────────────────────────────────────────


class TestBuildBearerConfig:
    """Tests for build_bearer_config."""

    def test_all_fields(self):
        cfg = build_bearer_config(
            bearer_token='tok',
            refresh_token='ref',
            token_expiry=9999999999,
            origin='https://example.com/',
            start_url='https://my-sso.awsapps.com/start',
            region='us-east-1',
            idc_region='us-east-1',
            oidc_client_id='cid',
            oidc_client_secret='csec',  # pragma: allowlist secret
            oidc_client_secret_expires_at=9999999999,
        )
        assert cfg.auth_mode == 'bearer'
        assert cfg.bearer_token == 'tok'
        assert cfg.refresh_token == 'ref'
        assert cfg.token_expiry == 9999999999
        assert cfg.origin == 'https://example.com'
        assert cfg.start_url == 'https://my-sso.awsapps.com/start'
        assert cfg.idc_region == 'us-east-1'
        assert cfg.oidc_client_id == 'cid'
        assert cfg.oidc_client_secret == 'csec'  # pragma: allowlist secret
        assert cfg.oidc_client_secret_expires_at == 9999999999
        assert cfg.fes_endpoint == derive_transform_api_endpoint('us-east-1')


# ── State management ────────────────────────────────────────────────────


class TestStateManagement:
    """Tests for config state management functions."""

    def test_initial_state(self):
        assert get_config() is None
        assert is_configured() is False

    def test_set_get_clear(self):
        cfg = build_cookie_config(
            origin='https://example.com',
            session_cookie='tok',
            region='us-east-1',
        )
        set_config(cfg)
        assert is_configured() is True
        assert get_config() is cfg
        clear_config()
        assert is_configured() is False
        assert get_config() is None


# ── Persistence ─────────────────────────────────────────────────────────


class TestPersistence:
    """Tests for config persistence (save/load)."""

    def test_persist_and_load_roundtrip(self, tmp_path):
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
        ):
            cfg = build_cookie_config(
                origin='https://example.com',
                session_cookie='abc',
                region='us-east-1',
            )
            set_config(cfg)
            persist_config()

            # File should exist with valid JSON including sensitive fields
            data = json.loads(config_file.read_text())
            assert data['auth_mode'] == 'cookie'
            assert data['session_cookie'] == 'aws-transform-session=abc'

            # Directory permissions should be 0o700 (owner only)
            dir_mode = os.stat(str(tmp_path)).st_mode
            assert dir_mode & 0o777 == 0o700

            # File permissions should be 0o600 (owner read/write only)
            file_mode = os.stat(str(config_file)).st_mode
            assert file_mode & 0o777 == 0o600

            # Load it back
            clear_config()
            assert get_config() is None

    @pytest.mark.asyncio
    async def test_load_persisted_cookie(self, tmp_path):
        """Cookie config loads and validates session via VerifySession."""
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        cfg = build_cookie_config(
            origin='https://example.com',
            session_cookie='abc',
            region='us-east-1',
        )
        config_file.write_text(json.dumps(cfg.model_dump(), indent=2))
        os.chmod(str(config_file), 0o600)

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
            patch(
                'awslabs.aws_transform_mcp_server.transform_api_client.call_fes_direct_cookie',
                new_callable=AsyncMock,
                return_value={'userId': 'user-1'},
            ),
        ):
            result = await load_persisted_config()
            assert result is True
            loaded = get_config()
            assert loaded is not None
            assert loaded.auth_mode == 'cookie'
            assert loaded.session_cookie == 'aws-transform-session=abc'

    @pytest.mark.asyncio
    async def test_load_persisted_cookie_stale_session(self, tmp_path):
        """A persisted cookie that fails VerifySession must return False."""
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        cfg = build_cookie_config(
            origin='https://example.com',
            session_cookie='expired-cookie',
            region='us-east-1',
        )
        config_file.write_text(json.dumps(cfg.model_dump(), indent=2))
        os.chmod(str(config_file), 0o600)

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
            patch(
                'awslabs.aws_transform_mcp_server.transform_api_client.call_fes_direct_cookie',
                new_callable=AsyncMock,
                side_effect=Exception('401 Unauthorized'),
            ),
        ):
            result = await load_persisted_config()
            assert result is False

    @pytest.mark.asyncio
    async def test_load_persisted_missing_file(self, tmp_path):
        store = config_store._default_store
        config_file = tmp_path / 'nonexistent.json'
        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
        ):
            result = await load_persisted_config()
            assert result is False

    @pytest.mark.asyncio
    async def test_load_expired_bearer_triggers_refresh(self, tmp_path):
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        expired_cfg = build_bearer_config(
            bearer_token='old-token',
            refresh_token='ref-tok',
            token_expiry=1000,  # long expired
            origin='https://example.com',
            start_url='https://sso.example.com/start',
            region='us-east-1',
            idc_region='us-east-1',
            oidc_client_id='cid',
            oidc_client_secret='csec',  # pragma: allowlist secret
            oidc_client_secret_expires_at=9999999999,
        )
        config_file.write_text(json.dumps(expired_cfg.model_dump(), indent=2))
        os.chmod(str(config_file), 0o600)

        mock_refresh = AsyncMock(
            return_value=RefreshedTokens(
                access_token='new-token',
                refresh_token='new-ref',
                expires_in=3600,
            )
        )

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
            patch(
                'awslabs.aws_transform_mcp_server.oauth.refresh_access_token',
                mock_refresh,
            ),
        ):
            result = await load_persisted_config()
            assert result is True
            loaded = get_config()
            assert loaded is not None
            assert loaded.bearer_token == 'new-token'
            assert loaded.refresh_token == 'new-ref'
            assert loaded.token_expiry is not None
            assert loaded.token_expiry > int(time.time()) - 10

            mock_refresh.assert_called_once_with(
                idc_region='us-east-1',
                client_id='cid',
                client_secret='csec',  # pragma: allowlist secret
                refresh_token='ref-tok',
            )

    @pytest.mark.asyncio
    async def test_load_expired_bearer_no_refresh_fields(self, tmp_path):
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        expired_cfg = build_bearer_config(
            bearer_token='old-token',
            refresh_token=None,
            token_expiry=1000,
            origin='https://example.com',
            start_url='https://sso.example.com/start',
            region='us-east-1',
            idc_region='us-east-1',
        )
        config_file.write_text(json.dumps(expired_cfg.model_dump(), indent=2))
        os.chmod(str(config_file), 0o600)

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
        ):
            result = await load_persisted_config()
            assert result is False

    @pytest.mark.asyncio
    async def test_load_expired_client_secret(self, tmp_path):
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        expired_cfg = build_bearer_config(
            bearer_token='old-token',
            refresh_token='ref-tok',
            token_expiry=1000,
            origin='https://example.com',
            start_url='https://sso.example.com/start',
            region='us-east-1',
            idc_region='us-east-1',
            oidc_client_id='cid',
            oidc_client_secret='csec',  # pragma: allowlist secret
            oidc_client_secret_expires_at=1000,  # also expired
        )
        config_file.write_text(json.dumps(expired_cfg.model_dump(), indent=2))
        os.chmod(str(config_file), 0o600)

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
        ):
            result = await load_persisted_config()
            assert result is False

    @pytest.mark.asyncio
    async def test_load_valid_bearer_not_expired(self, tmp_path):
        """A persisted bearer token that has not expired loads successfully."""
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        cfg = build_bearer_config(
            bearer_token='valid-token',
            refresh_token='ref-tok',
            token_expiry=int(time.time()) + 3600,  # expires in 1 hour
            origin='https://example.com',
            start_url='https://sso.example.com/start',
            region='us-east-1',
            idc_region='us-east-1',
            oidc_client_id='cid',
            oidc_client_secret='csec',  # pragma: allowlist secret
            oidc_client_secret_expires_at=9999999999,
        )
        config_file.write_text(json.dumps(cfg.model_dump(), indent=2))
        os.chmod(str(config_file), 0o600)

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
        ):
            result = await load_persisted_config()
            assert result is True
            loaded = get_config()
            assert loaded is not None
            assert loaded.bearer_token == 'valid-token'
            assert loaded.auth_mode == 'bearer'

    @pytest.mark.asyncio
    async def test_load_corrupt_json(self, tmp_path):
        """Corrupt JSON in config file must return False."""
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        config_file.write_text('{not valid json!!!}')
        os.chmod(str(config_file), 0o600)

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
        ):
            result = await load_persisted_config()
            assert result is False
            assert get_config() is None

    @pytest.mark.asyncio
    async def test_load_missing_required_fields(self, tmp_path):
        """Config file missing required fields (fes_endpoint, origin, auth_mode) must return False."""
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        config_file.write_text(json.dumps({'stage': 'prod', 'region': 'us-east-1'}))
        os.chmod(str(config_file), 0o600)

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
        ):
            result = await load_persisted_config()
            assert result is False

    @pytest.mark.asyncio
    async def test_load_cookie_without_session_cookie(self, tmp_path):
        """Cookie config missing session_cookie field must return False."""
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        config_file.write_text(
            json.dumps(
                {
                    'auth_mode': 'cookie',
                    'fes_endpoint': 'https://api.transform.us-east-1.on.aws/',
                    'origin': 'https://example.com',
                    'stage': 'prod',
                    'region': 'us-east-1',
                }
            )
        )
        os.chmod(str(config_file), 0o600)

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
        ):
            result = await load_persisted_config()
            assert result is False

    @pytest.mark.asyncio
    async def test_load_bearer_without_token(self, tmp_path):
        """Bearer config missing bearer_token field must return False."""
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        config_file.write_text(
            json.dumps(
                {
                    'auth_mode': 'bearer',
                    'fes_endpoint': 'https://api.transform.us-east-1.on.aws/',
                    'origin': 'https://example.com',
                    'stage': 'prod',
                    'region': 'us-east-1',
                }
            )
        )
        os.chmod(str(config_file), 0o600)

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
        ):
            result = await load_persisted_config()
            assert result is False

    @pytest.mark.asyncio
    async def test_load_expired_bearer_refresh_fails(self, tmp_path):
        """If bearer token is expired and refresh raises, must return False."""
        store = config_store._default_store
        config_file = tmp_path / 'config.json'
        expired_cfg = build_bearer_config(
            bearer_token='old-token',
            refresh_token='ref-tok',
            token_expiry=1000,
            origin='https://example.com',
            start_url='https://sso.example.com/start',
            region='us-east-1',
            idc_region='us-east-1',
            oidc_client_id='cid',
            oidc_client_secret='csec',  # pragma: allowlist secret
            oidc_client_secret_expires_at=9999999999,
        )
        config_file.write_text(json.dumps(expired_cfg.model_dump(), indent=2))
        os.chmod(str(config_file), 0o600)

        mock_refresh = AsyncMock(side_effect=Exception('refresh failed'))

        with (
            patch.object(store, '_config_dir', str(tmp_path)),
            patch.object(store, '_config_file', str(config_file)),
            patch(
                'awslabs.aws_transform_mcp_server.oauth.refresh_access_token',
                mock_refresh,
            ),
        ):
            result = await load_persisted_config()
            assert result is False
