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

"""Config store: endpoint derivation, persistence, and module-level state."""

import json
import os
import stat
import tempfile
import time
from awslabs.aws_transform_mcp_server import oauth
from awslabs.aws_transform_mcp_server.consts import REGION_AIRPORT_CODES
from awslabs.aws_transform_mcp_server.models import ConnectionConfig, SigV4Config
from loguru import logger


def derive_fes_endpoint(stage: str, region: str) -> str:
    """Derive the FES (Front End Service) endpoint for a given stage and region.

    Args:
        stage: Deployment stage (e.g. 'prod', 'gamma').
        region: AWS region (e.g. 'us-east-1').

    Returns:
        The FES endpoint URL.
    """
    if stage == 'prod':
        return f'https://api.transform.{region}.on.aws/'
    return f'https://api.transform-{stage}.{region}.on.aws/'


def derive_tcp_endpoint(stage: str, region: str) -> str:
    """Derive the TCP (Transform Control Plane) endpoint for a given stage and region.

    Args:
        stage: Deployment stage (e.g. 'prod', 'gamma').
        region: AWS region (e.g. 'us-east-1').

    Returns:
        The TCP endpoint URL.

    Raises:
        ValueError: If the region is not supported for non-prod stages.
    """
    if stage == 'prod':
        return f'https://transform.{region}.api.aws'
    airport_code = REGION_AIRPORT_CODES.get(region)
    if not airport_code:
        supported = ', '.join(sorted(REGION_AIRPORT_CODES.keys()))
        raise ValueError(f'Unknown region "{region}". Supported: {supported}')
    return f'https://{airport_code}.{stage}.transform-cp.elastic-gumby.ai.aws.dev'


def build_cookie_config(
    origin: str,
    session_cookie: str,
    stage: str,
    region: str,
) -> ConnectionConfig:
    """Build a ConnectionConfig for cookie-based authentication.

    Args:
        origin: The origin URL (trailing slash is stripped).
        session_cookie: The session cookie value. If it does not start with
            ``aws-transform-session=``, the prefix is prepended automatically.
        stage: Deployment stage.
        region: AWS region.

    Returns:
        A populated ConnectionConfig with auth_mode='cookie'.
    """
    cookie = session_cookie.strip()
    if not cookie.startswith('aws-transform-session='):
        cookie = f'aws-transform-session={cookie}'
    return ConnectionConfig(
        auth_mode='cookie',
        stage=stage,
        region=region,
        fes_endpoint=derive_fes_endpoint(stage, region),
        origin=origin.rstrip('/'),
        session_cookie=cookie,
    )


def build_bearer_config(
    bearer_token: str,
    refresh_token: str | None,
    token_expiry: int | None,
    origin: str,
    start_url: str,
    stage: str,
    region: str,
    oidc_client_id: str | None = None,
    oidc_client_secret: str | None = None,
    oidc_client_secret_expires_at: int | None = None,
) -> ConnectionConfig:
    """Build a ConnectionConfig for bearer-token authentication.

    Args:
        bearer_token: The OAuth access token.
        refresh_token: The OAuth refresh token.
        token_expiry: Unix timestamp (seconds) when the access token expires.
        origin: The origin URL (trailing slash is stripped).
        start_url: The IAM Identity Center start URL.
        stage: Deployment stage.
        region: AWS region.
        oidc_client_id: The OIDC client ID from RegisterClient.
        oidc_client_secret: The OIDC client secret from RegisterClient.
        oidc_client_secret_expires_at: Unix timestamp when the client secret expires.

    Returns:
        A populated ConnectionConfig with auth_mode='bearer'.
    """
    return ConnectionConfig(
        auth_mode='bearer',
        stage=stage,
        region=region,
        fes_endpoint=derive_fes_endpoint(stage, region),
        origin=origin.rstrip('/'),
        bearer_token=bearer_token,
        refresh_token=refresh_token,
        token_expiry=token_expiry,
        start_url=start_url,
        idc_region=region,
        oidc_client_id=oidc_client_id,
        oidc_client_secret=oidc_client_secret,
        oidc_client_secret_expires_at=oidc_client_secret_expires_at,
    )


class ConfigStore:
    """Manages FES and SigV4 connection configuration with persistence.

    Holds in-memory config state and handles reading/writing to disk.

    Args:
        config_dir: Directory for persisted config. Defaults to ``~/.aws-transform-mcp``.
    """

    def __init__(self, config_dir: str | None = None) -> None:
        """Initialize the config store."""
        self._config: ConnectionConfig | None = None
        self._sigv4_config: SigV4Config | None = None
        self._config_dir = config_dir or os.path.join(
            os.path.expanduser('~'), '.aws-transform-mcp'
        )
        self._config_file = os.path.join(self._config_dir, 'config.json')

    # ── FES config ──────────────────────────────────────────────────────

    @property
    def config(self) -> ConnectionConfig | None:
        """The current FES connection config, or None if not configured."""
        return self._config

    @config.setter
    def config(self, value: ConnectionConfig | None) -> None:
        self._config = value

    @property
    def is_configured(self) -> bool:
        """True if a FES connection config has been set."""
        return self._config is not None

    def clear_config(self) -> None:
        """Clear the current FES connection config."""
        self._config = None

    # ── SigV4 config ────────────────────────────────────────────────────

    @property
    def sigv4_config(self) -> SigV4Config | None:
        """The current SigV4 config, or None if not configured."""
        return self._sigv4_config

    @sigv4_config.setter
    def sigv4_config(self, value: SigV4Config | None) -> None:
        self._sigv4_config = value

    @property
    def is_sigv4_configured(self) -> bool:
        """True if a SigV4 config has been set."""
        return self._sigv4_config is not None

    # ── Persistence ─────────────────────────────────────────────────────

    def persist_config(self) -> None:
        """Write the current config to disk.

        All fields are written to the config JSON file. The file is written
        atomically (tmpfile + rename) and created with 0o600 permissions.
        """
        if self._config is None:
            return
        os.makedirs(self._config_dir, exist_ok=True)
        os.chmod(self._config_dir, stat.S_IRWXU)  # 0o700 — owner only

        data = self._config.model_dump()

        old_umask = os.umask(0o077)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=self._config_dir, suffix='.tmp')
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
            os.replace(tmp_path, self._config_file)  # atomic on POSIX
        finally:
            os.umask(old_umask)

    async def load_persisted_config(self) -> bool:
        """Load config from disk and set it as the current config.

        All fields are read from the config JSON file.

        The file is rejected if its permissions are too open (group/other bits set).

        For bearer auth with an expired token, an automatic refresh is attempted
        when the required OIDC fields (refresh_token, oidc_client_id,
        oidc_client_secret) are present.

        For cookie auth, the session is validated via a VerifySession call.

        Returns:
            True if a valid config was loaded, False otherwise.
        """
        if not os.path.exists(self._config_file):
            return False

        # Reject if permissions have been tampered with
        file_mode = os.stat(self._config_file).st_mode
        if file_mode & 0o077:
            logger.warning(
                'Config file %s has insecure permissions %o, refusing to load',
                self._config_file,
                file_mode,
            )
            return False

        try:
            with open(self._config_file) as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False

        # Validate required fields
        if not raw.get('fes_endpoint') or not raw.get('origin') or not raw.get('auth_mode'):
            return False

        auth_mode = raw['auth_mode']
        if auth_mode == 'cookie' and not raw.get('session_cookie'):
            return False
        if auth_mode == 'bearer' and not raw.get('bearer_token'):
            return False

        config = ConnectionConfig(**raw)
        now = int(time.time())
        bearer_expired = auth_mode == 'bearer' and (
            not config.token_expiry or now >= config.token_expiry
        )

        if bearer_expired:
            # Load into memory so get_status can show context even if refresh fails
            self._config = config

            # Client registration expired — refresh would fail
            if (
                config.oidc_client_secret_expires_at
                and now >= config.oidc_client_secret_expires_at
            ):
                return False

            # Attempt refresh if we have the required fields
            if (
                config.refresh_token
                and config.oidc_client_id
                and config.oidc_client_secret
                and config.idc_region
            ):
                try:
                    tokens = await oauth.refresh_access_token(
                        idc_region=config.idc_region,
                        client_id=config.oidc_client_id,
                        client_secret=config.oidc_client_secret,
                        refresh_token=config.refresh_token,
                    )
                    config.bearer_token = tokens.access_token
                    config.refresh_token = tokens.refresh_token or config.refresh_token
                    config.token_expiry = int(time.time()) + tokens.expires_in
                    self._config = config
                    self.persist_config()
                    return True
                except Exception as exc:
                    logger.warning('Bearer token refresh failed at startup: %s', exc)
                    return False

            return False

        # For cookie auth, validate the session is still active.
        if auth_mode == 'cookie':
            try:
                from awslabs.aws_transform_mcp_server.consts import (
                    STARTUP_MAX_RETRIES,
                    STARTUP_TIMEOUT_SECONDS,
                )
                from awslabs.aws_transform_mcp_server.fes_client import call_fes_direct_cookie

                await call_fes_direct_cookie(
                    config.fes_endpoint,
                    config.origin,
                    config.session_cookie or '',
                    'VerifySession',
                    timeout_seconds=STARTUP_TIMEOUT_SECONDS,
                    max_retries=STARTUP_MAX_RETRIES,
                )
            except Exception as exc:
                logger.warning('Cookie session validation failed at startup: %s', exc)
                return False

        self._config = config
        return True


_default_store = ConfigStore()


def set_config(config: ConnectionConfig) -> None:
    """Set the current FES connection config."""
    _default_store.config = config


def get_config() -> ConnectionConfig | None:
    """Return the current FES connection config, or None if not configured."""
    return _default_store.config


def is_configured() -> bool:
    """Return True if a FES connection config has been set."""
    return _default_store.is_configured


def clear_config() -> None:
    """Clear the current FES connection config."""
    _default_store.clear_config()


def set_sigv4_config(config: SigV4Config) -> None:
    """Set the current SigV4 (TCP) config."""
    _default_store.sigv4_config = config


def get_sigv4_config() -> SigV4Config | None:
    """Return the current SigV4 config, or None if not configured."""
    return _default_store.sigv4_config


def is_sigv4_configured() -> bool:
    """Return True if a SigV4 config has been set."""
    return _default_store.is_sigv4_configured


def persist_config() -> None:
    """Write the current config to disk."""
    _default_store.persist_config()


async def load_persisted_config() -> bool:
    """Load config from disk."""
    return await _default_store.load_persisted_config()
