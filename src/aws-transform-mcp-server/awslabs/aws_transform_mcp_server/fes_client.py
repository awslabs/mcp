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

"""FES (Front End Service) client — boto3-based with cookie or bearer auth.

Uses a vendored botocore C2J model so ``boto3.client("elasticgumbyfrontendservice")``
works without the Brazil-only ElasticGumbyFrontEndServicePythonClient package.
"""

import asyncio
import time
from awslabs.aws_transform_mcp_server import config_store, oauth
from awslabs.aws_transform_mcp_server._service_model import create_session
from awslabs.aws_transform_mcp_server.consts import (
    CLIENT_APP_ID,
    FES_TARGET_BEARER,
    HEADER_CLIENT_APP_ID,
    MAX_RETRIES,
    TIMEOUT_SECONDS,
    TOKEN_REFRESH_BUFFER_SECS,
)
from awslabs.aws_transform_mcp_server.http_utils import HttpError
from awslabs.aws_transform_mcp_server.models import ConnectionConfig
from botocore import UNSIGNED, xform_name
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from loguru import logger
from typing import Any, Dict, Optional


FESOperation = str


def _create_boto3_client(
    endpoint: str,
    region: str = 'us-east-1',
    max_retries: int = MAX_RETRIES,
    timeout: float = TIMEOUT_SECONDS,
):
    """Create a bare boto3 FES client (no auth injected yet)."""
    session = create_session()
    return session.client(
        'elasticgumbyfrontendservice',
        region_name=region,
        endpoint_url=endpoint,
        config=BotoConfig(
            signature_version=UNSIGNED,
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
    method_name = xform_name(operation)
    method = getattr(client, method_name, None)
    if method is None:
        raise ValueError(f'Unknown FES operation: {operation}')
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
    result.pop('ResponseMetadata', None)
    return result


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

    Used by ``configure`` and by ``config_store`` startup validation
    before the config is stored.
    """
    client = _create_boto3_client(endpoint, max_retries=max_retries, timeout=timeout_seconds)
    _inject_cookie_auth(client, origin, cookie)
    return await asyncio.to_thread(_call_boto3, client, operation, body or {})


async def call_fes_direct_bearer(
    endpoint: str,
    token: str,
    operation: FESOperation,
    body: Optional[Dict[str, Any]] = None,
    origin: Optional[str] = None,
) -> Any:
    """Direct FES call with explicit bearer auth.

    Used by ``configure`` SSO path.
    """
    client = _create_boto3_client(endpoint)
    _inject_bearer_auth(client, token, origin)
    return await asyncio.to_thread(_call_boto3, client, operation, body or {})


async def call_fes(operation: FESOperation, body: Optional[Dict[str, Any]] = None) -> Any:
    """Call FES using the stored connection config via boto3 client.

    This is the main entry point used by all tool handlers.
    """
    if body is None:
        body = {}

    config = config_store.get_config()
    if config is None:
        raise RuntimeError('Not configured. Call configure first.')

    if config.auth_mode == 'bearer':
        config = await _ensure_fresh_token(config)

    client = _create_boto3_client(config.fes_endpoint, config.region or 'us-east-1')
    if config.auth_mode == 'cookie':
        _inject_cookie_auth(client, config.origin, config.session_cookie or '')
    else:
        _inject_bearer_auth(client, config.bearer_token or '', config.origin)

    return await asyncio.to_thread(_call_boto3, client, operation, body)


async def _ensure_fresh_token(config: ConnectionConfig) -> ConnectionConfig:
    """Proactively refresh the bearer token if near expiry."""
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
