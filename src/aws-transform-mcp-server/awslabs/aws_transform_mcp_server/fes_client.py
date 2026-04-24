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

"""FES (Front End Service) client — RPC-over-HTTP with cookie or bearer auth."""

import httpx
import json
import time
from awslabs.aws_transform_mcp_server import config_store, oauth
from awslabs.aws_transform_mcp_server.consts import (
    CLIENT_APP_ID,
    FES_TARGET_BEARER,
    FES_TARGET_COOKIE,
    HEADER_CLIENT_APP_ID,
    MAX_RETRIES,
    TIMEOUT_SECONDS,
    TOKEN_REFRESH_BUFFER_SECS,
)
from awslabs.aws_transform_mcp_server.http_utils import (
    request_with_retry,
)
from loguru import logger
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional


if TYPE_CHECKING:
    from awslabs.aws_transform_mcp_server.models import ConnectionConfig


# ── FES operations ──────────────────────────────────────────────────────
FESOperation = Literal[
    'VerifySession',
    'ListAvailableProfiles',
    'ListWorkspaces',
    'CreateWorkspace',
    'GetWorkspace',
    'CreateJob',
    'GetJob',
    'ListJobs',
    'StartJob',
    'StopJob',
    'DeleteJob',
    'GetHitlTask',
    'ListHitlTasks',
    'UpdateHitlTask',
    'SubmitStandardHitlTask',
    'SubmitCriticalHitlTask',
    'CreateArtifactUploadUrl',
    'CompleteArtifactUpload',
    'CreateArtifactDownloadUrl',
    'CreateAssetDownloadUrl',
    'ListArtifacts',
    'ListJobPlanSteps',
    'ListPlanUpdates',
    'ListConnectors',
    'CreateConnector',
    'GetConnector',
    'SendMessage',
    'ListMessages',
    'BatchGetMessage',
    'DeleteWorkspace',
    'ListWorklogs',
    'ListAgents',
    'SearchUsersTypeahead',
    'BatchGetUserDetails',
    'ListUserRoleMappings',
    'PutUserRoleMappings',
    'DeleteUserRoleMappings',
    'DeleteSelfRoleMappings',
]


def _build_cookie_headers(
    operation: str,
    origin: str,
    cookie: str,
) -> Dict[str, str]:
    """Build headers for cookie-authenticated FES calls."""
    return {
        'Content-Type': 'application/x-amz-json-1.0',
        'X-Amz-Target': f'{FES_TARGET_COOKIE}.{operation}',
        'Origin': origin,
        'Cookie': cookie,
    }


def _build_bearer_headers(
    operation: str,
    token: str,
    origin: Optional[str] = None,
) -> Dict[str, str]:
    """Build headers for bearer-token-authenticated FES calls."""
    headers: Dict[str, str] = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Content-Encoding': 'amz-1.0',
        'X-Amz-Target': f'{FES_TARGET_BEARER}.{operation}',
        'Authorization': f'Bearer {token}',
        HEADER_CLIENT_APP_ID: CLIENT_APP_ID,
    }
    # Origin is needed for tenant-scoped operations, not for ListAvailableProfiles
    if origin and operation != 'ListAvailableProfiles':
        headers['Origin'] = origin
    return headers


async def call_fes_direct_cookie(
    endpoint: str,
    origin: str,
    cookie: str,
    operation: FESOperation,
    body: Optional[Dict[str, Any]] = None,
    timeout_seconds: float = TIMEOUT_SECONDS,
    max_retries: int = MAX_RETRIES,
) -> Any:
    """Direct FES call with explicit cookie auth.

    Used by ``configure`` and ``get_status`` before config is stored.

    Args:
        endpoint: FES endpoint URL.
        origin: Origin header value.
        cookie: Session cookie string.
        operation: FES operation name.
        body: Request body (defaults to empty dict).
        timeout_seconds: Per-request timeout in seconds.
        max_retries: Maximum number of retries.

    Returns:
        Parsed JSON response.

    Raises:
        HttpError: On non-2xx response.
    """
    if body is None:
        body = {}
    headers = _build_cookie_headers(operation, origin, cookie)
    payload = json.dumps(body).encode('utf-8')

    async with httpx.AsyncClient() as client:
        response = await request_with_retry(
            client,
            'POST',
            endpoint,
            headers,
            payload,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        return response.json()


async def call_fes_direct_bearer(
    endpoint: str,
    token: str,
    operation: FESOperation,
    body: Optional[Dict[str, Any]] = None,
    origin: Optional[str] = None,
) -> Any:
    """Direct FES call with explicit bearer auth.

    Used by ``configure`` SSO path.

    Args:
        endpoint: FES endpoint URL.
        token: Bearer access token.
        operation: FES operation name.
        body: Request body (defaults to empty dict).
        origin: Origin header (omitted for ListAvailableProfiles).

    Returns:
        Parsed JSON response.

    Raises:
        HttpError: On non-2xx response.
    """
    if body is None:
        body = {}
    headers = _build_bearer_headers(operation, token, origin)
    payload = json.dumps(body).encode('utf-8')

    async with httpx.AsyncClient() as client:
        response = await request_with_retry(
            client, 'POST', endpoint, headers, payload, timeout_seconds=TIMEOUT_SECONDS
        )
        return response.json()


_MAX_PAGES = 100


async def paginate_all(
    operation: FESOperation,
    body: Dict[str, Any],
    items_key: str,
    token_key: str = 'nextToken',
) -> Dict[str, Any]:
    """Auto-paginate a FES list call, collecting all items.

    Args:
        operation: FES operation name.
        body: Base request body (filters etc.). Not mutated.
        items_key: Key in the response that holds the list of items.
        token_key: Key in the response that holds the pagination token.

    Returns:
        Dict with all items under *items_key*.
    """
    all_items: list = []
    next_token: Optional[str] = None
    for _page in range(_MAX_PAGES):
        req = {**body}
        if next_token:
            req['nextToken'] = next_token
        result = await call_fes(operation, req)
        if not isinstance(result, dict):
            logger.warning(
                'paginate_all(%s): non-dict response on page with %d items collected: %s',
                operation,
                len(all_items),
                type(result),
            )
            break
        all_items.extend(result.get(items_key, []))
        next_token = result.get(token_key)
        if not next_token:
            break
    else:
        logger.warning(
            'paginate_all(%s): hit %d-page safety limit, returning partial results',
            operation,
            _MAX_PAGES,
        )
    return {items_key: all_items}


async def call_fes(operation: FESOperation, body: Optional[Dict[str, Any]] = None) -> Any:
    """Call FES using the stored connection config, with retry and token refresh.

    This is the main entry point used by all tool handlers.

    Routes to cookie or bearer mode based on the persisted config. For bearer
    mode, proactively refreshes the access token when it is within
    TOKEN_REFRESH_BUFFER_SECS of expiry.

    Args:
        operation: FES operation name.
        body: Request body (defaults to empty dict).

    Returns:
        Parsed JSON response.

    Raises:
        HttpError: On non-2xx responses after retries.
        RuntimeError: When client registration has expired.
    """
    if body is None:
        body = {}

    config = config_store.get_config()
    if config is None:
        raise RuntimeError('Not configured. Call configure first.')

    # ── Token refresh (bearer mode only) ────────────────────────────────
    if config.auth_mode == 'bearer':
        config = await _ensure_fresh_token(config)

    # ── Build headers based on auth mode ────────────────────────────────
    if config.auth_mode == 'cookie':
        headers = _build_cookie_headers(operation, config.origin, config.session_cookie or '')
    else:
        headers = _build_bearer_headers(operation, config.bearer_token or '', config.origin)

    payload = json.dumps(body).encode('utf-8')

    async with httpx.AsyncClient() as client:
        response = await request_with_retry(
            client, 'POST', config.fes_endpoint, headers, payload, timeout_seconds=TIMEOUT_SECONDS
        )
        return response.json()


async def _ensure_fresh_token(config: 'ConnectionConfig') -> 'ConnectionConfig':
    """Proactively refresh the bearer token if near expiry.

    Args:
        config: The current ConnectionConfig.

    Returns:
        Updated config (may be the same object if no refresh was needed).
    """
    if (
        not config.token_expiry
        or not config.refresh_token
        or not config.oidc_client_id
        or not config.oidc_client_secret
        or not config.idc_region
    ):
        return config

    now = int(time.time())

    if config.token_expiry - now >= TOKEN_REFRESH_BUFFER_SECS:
        return config

    # Client registration expired — refresh would fail
    if config.oidc_client_secret_expires_at and now >= config.oidc_client_secret_expires_at:
        raise RuntimeError(
            'Client registration expired. Re-run configure with authMode "sso" to re-authenticate.'
        )

    logger.info('Bearer token near expiry, refreshing...')
    tokens = await oauth.refresh_access_token(
        idc_region=config.idc_region,
        client_id=config.oidc_client_id,
        client_secret=config.oidc_client_secret,
        refresh_token=config.refresh_token,
    )

    config.bearer_token = tokens.access_token
    config.refresh_token = tokens.refresh_token or config.refresh_token
    config.token_expiry = int(time.time()) + tokens.expires_in
    config_store.set_config(config)
    config_store.persist_config()
    return config
