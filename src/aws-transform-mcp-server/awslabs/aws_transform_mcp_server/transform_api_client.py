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

"""Transform API client — boto3-based with cookie, bearer, or AWS credential auth.

Uses a vendored botocore C2J model so ``boto3.client("elasticgumbyfrontendservice")``
works without the internal SDK package.
"""

import asyncio
import boto3
import botocore.session
import os
import time
from awslabs.aws_transform_mcp_server import config_store, oauth
from awslabs.aws_transform_mcp_server._service_model import create_session
from awslabs.aws_transform_mcp_server.aws_helper import USER_AGENT, AwsHelper
from awslabs.aws_transform_mcp_server.consts import (
    CLIENT_APP_ID,
    FES_TARGET_BEARER,
    HEADER_CLIENT_APP_ID,
    MAX_RETRIES,
    TIMEOUT_SECONDS,
    TOKEN_REFRESH_BUFFER_SECS,
)
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.transform_api_models import FESRequest
from botocore import UNSIGNED, xform_name
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from loguru import logger
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Tuple, Union


if TYPE_CHECKING:
    from awslabs.aws_transform_mcp_server.models import ConnectionConfig


FESOperation = str


class ProfileSelectionRequired(Exception):
    """Raised when SigV4 FES has multiple regions and none is selected."""

    def __init__(self, regions: list) -> None:  # noqa: D107
        self.regions = regions
        super().__init__('Multiple regions available. Please choose one.')


# ── boto3 client helpers ────────────────────────────────────────────────


def _create_unsigned_client(
    endpoint: str,
    region: str = 'us-east-1',
    max_retries: int = MAX_RETRIES,
    timeout: float = TIMEOUT_SECONDS,
):
    """Create a boto3 FES client with UNSIGNED config (no SigV4)."""
    session = create_session()
    return session.client(
        'elasticgumbyfrontendservice',
        region_name=region,
        endpoint_url=endpoint,
        config=BotoConfig(
            signature_version=UNSIGNED,
            user_agent_extra=USER_AGENT,
            retries={'mode': 'adaptive', 'max_attempts': max_retries + 1},
            connect_timeout=timeout,
            read_timeout=timeout,
        ),
    )


def _create_sigv4_client(
    endpoint: str,
    region: str = 'us-east-1',
    max_retries: int = MAX_RETRIES,
    timeout: float = TIMEOUT_SECONDS,
):
    """Create a boto3 FES client with SigV4 signing from default credentials.

    Creates a fresh botocore session with the user's profile and region so that
    credential providers (e.g., LoginProvider) can resolve internal clients.
    """
    from awslabs.aws_transform_mcp_server._service_model import _MODEL_DIR

    profile = (os.environ.get('AWS_PROFILE') or '').strip() or None
    core = botocore.session.get_session()
    core.set_config_variable('profile', profile)
    core.set_config_variable('region', region)
    loader = core.get_component('data_loader')
    if _MODEL_DIR not in loader.search_paths:
        loader.search_paths.insert(0, _MODEL_DIR)

    session = boto3.Session(botocore_session=core)
    return session.client(
        'elasticgumbyfrontendservice',
        region_name=region,
        endpoint_url=endpoint,
        config=BotoConfig(
            user_agent_extra=USER_AGENT,
            retries={'mode': 'adaptive', 'max_attempts': max_retries + 1},
            connect_timeout=timeout,
            read_timeout=timeout,
        ),
    )


def _inject_cookie_auth(client, origin: str, cookie: str):
    """Register event handler to inject cookie auth headers on every request."""

    def add_headers(params, **kwargs):
        params['headers']['Origin'] = origin
        params['headers']['Cookie'] = cookie

    client.meta.events.register('before-call.elasticgumbyfrontend.*', add_headers)


def _inject_bearer_auth(client, token: str, origin: Optional[str] = None):
    """Register event handler to inject bearer auth headers on every request."""

    def add_headers(params, model, **kwargs):
        params['headers']['Authorization'] = f'Bearer {token}'
        params['headers'][HEADER_CLIENT_APP_ID] = CLIENT_APP_ID
        params['headers']['Content-Encoding'] = 'amz-1.0'
        params['headers']['X-Amz-Target'] = f'{FES_TARGET_BEARER}.{model.name}'
        if origin and model.name != 'ListAvailableProfiles':
            params['headers']['Origin'] = origin

    client.meta.events.register('before-call.elasticgumbyfrontend.*', add_headers)


def _call_boto3(client, operation: str, body: Dict[str, Any]) -> Any:
    """Invoke a boto3 FES operation synchronously."""
    method_name = xform_name(operation)
    method = getattr(client, method_name, None)
    if method is None:
        raise ValueError(f'Unknown operation: {operation}')
    try:
        result = method(**body)
    except ClientError as exc:
        error = exc.response.get('Error', {})
        status = exc.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)
        raise HttpError(
            status_code=status,
            body=error,
            message=f'HTTP {status}: {error.get("Message", str(exc))}',
        ) from exc
    metadata = result.pop('ResponseMetadata', None)
    if metadata:
        logger.debug('FES %s requestId=%s', operation, metadata.get('RequestId'))
    return result


# ── Direct call functions (used by configure/get_status before config is stored) ──


async def call_fes_direct_sigv4(
    endpoint: str,
    operation: FESOperation,
    body: Optional[Dict[str, Any]] = None,
    timeout_seconds: float = TIMEOUT_SECONDS,
    max_retries: int = MAX_RETRIES,
    region: Optional[str] = None,
) -> Any:
    """Direct FES call with SigV4 auth from boto3 credentials."""
    if region is None:
        session = AwsHelper.create_session()
        region = AwsHelper.resolve_region(session)
    client = _create_sigv4_client(
        endpoint, region=region, max_retries=max_retries, timeout=timeout_seconds
    )
    return await asyncio.to_thread(_call_boto3, client, operation, body or {})


async def call_fes_direct_cookie(
    endpoint: str,
    origin: str,
    cookie: str,
    operation: FESOperation,
    body: Optional[Dict[str, Any]] = None,
    timeout_seconds: float = TIMEOUT_SECONDS,
    max_retries: int = MAX_RETRIES,
) -> Any:
    """Direct FES call with explicit cookie auth."""
    client = _create_unsigned_client(endpoint, max_retries=max_retries, timeout=timeout_seconds)
    _inject_cookie_auth(client, origin, cookie)
    return await asyncio.to_thread(_call_boto3, client, operation, body or {})


async def call_fes_direct_bearer(
    endpoint: str,
    token: str,
    operation: FESOperation,
    body: Optional[Dict[str, Any]] = None,
    origin: Optional[str] = None,
) -> Any:
    """Direct FES call with explicit bearer auth."""
    client = _create_unsigned_client(endpoint)
    _inject_bearer_auth(client, token, origin)
    return await asyncio.to_thread(_call_boto3, client, operation, body or {})


# ── Pagination helper ───────────────────────────────────────────────────

_MAX_PAGES = 100


async def paginate_all(
    operation: FESOperation,
    body: Dict[str, Any],
    items_key: str,
    token_key: str = 'nextToken',
    extra_list_keys: Tuple[str, ...] = (),
    scalar_keys: Tuple[str, ...] = (),
) -> Dict[str, Any]:
    """Auto-paginate a FES list call, collecting all items.

    Args:
        operation: FES operation name.
        body: Request body (not mutated).
        items_key: Response field holding the primary list to accumulate.
        token_key: Response field holding the pagination token.
        extra_list_keys: Additional response lists to accumulate alongside
            ``items_key`` (e.g. ``('folders', 'assets')`` for ``ListArtifacts``).
        scalar_keys: Response scalars to preserve from the first page only
            (e.g. ``('connectorId',)``).

    Returns:
        A dict containing the aggregated primary list, any extra lists, and
        any preserved scalars.
    """
    all_items: list = []
    extras: Dict[str, list] = {k: [] for k in extra_list_keys}
    scalars: Dict[str, Any] = {}
    next_token: Optional[str] = None
    saw_first_page = False
    for _page in range(_MAX_PAGES):
        req = {**body}
        if next_token:
            req['nextToken'] = next_token
        result = await call_transform_api(operation, req)
        if not isinstance(result, dict):
            logger.warning(
                'paginate_all(%s): non-dict response on page with %d items collected: %s',
                operation,
                len(all_items),
                type(result),
            )
            break
        all_items.extend(result.get(items_key, []) or [])
        for k in extra_list_keys:
            extras[k].extend(result.get(k, []) or [])
        if not saw_first_page:
            for k in scalar_keys:
                if k in result and result[k] is not None:
                    scalars[k] = result[k]
            saw_first_page = True
        next_token = result.get(token_key)
        if not next_token:
            break
    else:
        logger.warning(
            'paginate_all(%s): hit %d-page safety limit, returning partial results',
            operation,
            _MAX_PAGES,
        )
    return {items_key: all_items, **extras, **scalars}


# ── Main entry point ───────────────────────────────────────────────────


async def call_transform_api(
    operation: FESOperation,
    body: Union[FESRequest, Mapping[str, Any], None] = None,
) -> Any:
    """Call FES using the stored connection config via boto3 client.

    Accepts a FESRequest Pydantic model, a plain mapping, or None.
    Pydantic models are serialised via model_dump(by_alias=True, exclude_none=True).
    """
    if isinstance(body, FESRequest):
        body = body.model_dump(by_alias=True, exclude_none=True)
    elif body is None:
        body = {}
    else:
        body = dict(body)

    config = config_store.get_config()
    if config is None:
        if config_store.is_sigv4_fes_available():
            region = config_store.get_sigv4_region()
            logger.info('call_fes SigV4 path: region={}', region)
            if region is None:
                regions = config_store.get_sigv4_regions()
                raise ProfileSelectionRequired(regions or [])
            endpoint = config_store.derive_transform_api_endpoint(region)
            return await call_fes_direct_sigv4(
                endpoint,
                operation,
                body,
                region=region,
            )
        raise RuntimeError('Not configured. Call configure first.')

    # Token refresh (bearer mode only)
    if config.auth_mode == 'bearer':
        config = await _ensure_fresh_token(config)

    endpoint = config_store.derive_transform_api_endpoint(config.region or 'us-east-1')
    client = _create_unsigned_client(endpoint, config.region or 'us-east-1')
    if config.auth_mode == 'cookie':
        _inject_cookie_auth(client, config.origin, config.session_cookie or '')
    else:
        _inject_bearer_auth(client, config.bearer_token or '', config.origin)

    return await asyncio.to_thread(_call_boto3, client, operation, body)


async def _ensure_fresh_token(config: 'ConnectionConfig') -> 'ConnectionConfig':
    """Proactively refresh the bearer token if near expiry."""
    if (
        not config.token_expiry
        or not config.refresh_token
        or not config.oidc_client_id
        or not config.oidc_client_secret
        or not config.idc_region
    ):
        if config.token_expiry and int(time.time()) >= config.token_expiry:
            raise RuntimeError(
                'SSO session expired. Run configure with authMode "sso" to re-authenticate.'
            )
        return config

    now = int(time.time())

    if config.token_expiry - now >= TOKEN_REFRESH_BUFFER_SECS:
        return config

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
