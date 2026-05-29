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
import re
import stat
import tempfile
import time
from awslabs.aws_transform_mcp_server import oauth
from awslabs.aws_transform_mcp_server.models import ConnectionConfig
from loguru import logger


# Matches: https://{tenantId}.transform.{region}.on.aws
_ORIGIN_REGION_PATTERN = re.compile(
    r'https://[a-z0-9-]+\.transform(?:-[a-z-]+)?\.([a-z]+-[a-z]+-\d+)\.on\.aws$'
)


def extract_region_from_origin(origin: str) -> str | None:
    """Extract the AWS region from a Transform application URL.

    Handles the ``https://{id}.transform.{region}.on.aws`` pattern.

    Args:
        origin: The application URL / origin string.

    Returns:
        The AWS region string, or None if the URL doesn't match the expected pattern.
    """
    match = _ORIGIN_REGION_PATTERN.match(origin.rstrip('/'))
    return match.group(1) if match else None


def derive_transform_api_endpoint(region: str) -> str:
    """Derive the Transform API endpoint for a given region.

    If the ``AWS_TRANSFORM_API_ENDPOINT`` environment variable is set, it is
    used instead. The value may contain ``{region}`` which will be interpolated
    with the provided region.

    Args:
        region: AWS region (e.g. 'us-east-1').

    Returns:
        The Transform API endpoint URL.
    """
    override = os.environ.get('AWS_TRANSFORM_API_ENDPOINT')
    if override:
        return override.replace('{region}', region) if '{region}' in override else override
    return f'https://api.transform.{region}.on.aws/'


def derive_tcp_endpoint(region: str) -> str:
    """Derive the TCP (Transform Control Plane) endpoint for a given region.

    If the ``AWS_TRANSFORM_TCP_ENDPOINT`` environment variable is set, it is
    used instead. The value may contain ``{region}`` which will be interpolated
    with the provided region.

    Args:
        region: AWS region (e.g. 'us-east-1').

    Returns:
        The TCP endpoint URL.
    """
    override = os.environ.get('AWS_TRANSFORM_TCP_ENDPOINT')
    if override:
        return override.replace('{region}', region) if '{region}' in override else override
    return f'https://transform.{region}.api.aws'


def build_cookie_config(
    origin: str,
    session_cookie: str,
    region: str,
) -> ConnectionConfig:
    """Build a ConnectionConfig for cookie-based authentication.

    Args:
        origin: The origin URL (trailing slash is stripped).
        session_cookie: The session cookie value. If it does not start with
            ``aws-transform-session=``, the prefix is prepended automatically.
        region: AWS region.

    Returns:
        A populated ConnectionConfig with auth_mode='cookie'.
    """
    cookie = session_cookie.strip()
    if not cookie.startswith('aws-transform-session='):
        cookie = f'aws-transform-session={cookie}'
    return ConnectionConfig(
        auth_mode='cookie',
        region=region,
        fes_endpoint=derive_transform_api_endpoint(region),
        origin=origin.rstrip('/'),
        session_cookie=cookie,
    )


def build_bearer_config(
    bearer_token: str,
    refresh_token: str | None,
    token_expiry: int | None,
    origin: str,
    start_url: str,
    region: str,
    idc_region: str,
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
        region: AWS region for the Transform service (FES endpoint).
        idc_region: AWS region for the IAM Identity Center instance (for token refresh).
        oidc_client_id: The OIDC client ID from RegisterClient.
        oidc_client_secret: The OIDC client secret from RegisterClient.
        oidc_client_secret_expires_at: Unix timestamp when the client secret expires.

    Returns:
        A populated ConnectionConfig with auth_mode='bearer'.
    """
    return ConnectionConfig(
        auth_mode='bearer',
        region=region,
        fes_endpoint=derive_transform_api_endpoint(region),
        origin=origin.rstrip('/'),
        bearer_token=bearer_token,
        refresh_token=refresh_token,
        token_expiry=token_expiry,
        start_url=start_url,
        idc_region=idc_region,
        oidc_client_id=oidc_client_id,
        oidc_client_secret=oidc_client_secret,
        oidc_client_secret_expires_at=oidc_client_secret_expires_at,
    )


class ConfigStore:
    """Manages FES connection configuration with persistence.

    Holds in-memory config state and handles reading/writing to disk.

    Args:
        config_dir: Directory for persisted config. Defaults to ``~/.aws-transform-mcp``.
    """

    def __init__(self, config_dir: str | None = None) -> None:
        """Initialize the config store."""
        self._config: ConnectionConfig | None = None
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

    def delete_persisted_config(self) -> None:
        """Delete the persisted config file from disk and clear in-memory state."""
        self._config = None
        try:
            os.remove(self._config_file)
        except FileNotFoundError:
            pass

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
                    logger.warning('Auth refresh failed at startup: {}', exc)
                    return False

            return False

        # For cookie auth, validate the session is still active.
        if auth_mode == 'cookie':
            try:
                from awslabs.aws_transform_mcp_server.consts import (
                    STARTUP_MAX_RETRIES,
                    STARTUP_TIMEOUT_SECONDS,
                )
                from awslabs.aws_transform_mcp_server.transform_api_client import (
                    call_fes_direct_cookie,
                )

                await call_fes_direct_cookie(
                    config.fes_endpoint,
                    config.origin,
                    config.session_cookie or '',
                    'VerifySession',
                    timeout_seconds=STARTUP_TIMEOUT_SECONDS,
                    max_retries=STARTUP_MAX_RETRIES,
                )
            except Exception as exc:
                logger.warning('Cookie session validation failed at startup: {}', exc)
                return False

        self._config = config
        return True


_default_store = ConfigStore()

_sigv4_fes_available: bool | None = None
_sigv4_region: str | None = None
_sigv4_regions: list[str] | None = None


def set_sigv4_fes_available(available: bool) -> None:
    """Cache whether SigV4 FES auth is available."""
    global _sigv4_fes_available
    _sigv4_fes_available = available


def is_sigv4_fes_available() -> bool:
    """Return True if SigV4 FES auth was probed and succeeded."""
    return _sigv4_fes_available is True


def set_sigv4_region(region: str | None) -> None:
    """Store the selected SigV4 region, or None to clear it."""
    global _sigv4_region
    _sigv4_region = region


def get_sigv4_region() -> str | None:
    """Return the stored SigV4 region, or None if not selected."""
    return _sigv4_region


def set_sigv4_regions(regions: list[str]) -> None:
    """Store discovered SigV4 regions for deferred selection."""
    global _sigv4_regions
    _sigv4_regions = regions


def get_sigv4_regions() -> list[str] | None:
    """Return discovered SigV4 regions, or None if not discovered."""
    return _sigv4_regions


def is_fes_available() -> bool:
    """Return True if FES is reachable via any auth method."""
    return _default_store.is_configured or is_sigv4_fes_available()


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


def delete_persisted_config() -> None:
    """Delete the persisted config file from disk and clear in-memory state."""
    _default_store.delete_persisted_config()


def persist_config() -> None:
    """Write the current config to disk."""
    _default_store.persist_config()


async def load_persisted_config() -> bool:
    """Load config from disk."""
    return await _default_store.load_persisted_config()
