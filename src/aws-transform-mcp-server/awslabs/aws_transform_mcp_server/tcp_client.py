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

"""TCP (Transform Control Plane) client — SigV4-signed RPC-over-HTTP."""

import httpx
import json
from awslabs.aws_transform_mcp_server import config_store
from awslabs.aws_transform_mcp_server.consts import (
    TCP_SERVICE,
    TCP_TARGET_PREFIX,
    TIMEOUT_SECONDS,
)
from awslabs.aws_transform_mcp_server.http_utils import request_with_retry
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from typing import Any, Dict, Literal, Optional
from urllib.parse import urlparse


# ── TCP operations ──────────────────────────────────────────────────────
TCPOperation = Literal[
    'ListConnectors',
    'GetConnector',
    'DeleteConnector',
    'AssociateConnectorResource',
    'ListProfiles',
    'CreateProfile',
    'GetAgent',
    'ListAgents',
    'GetAgentRuntimeConfiguration',
]


def _sign_request(
    endpoint: str,
    headers: Dict[str, str],
    body_bytes: bytes,
    access_key_id: str,
    secret_access_key: str,
    session_token: Optional[str],
    region: str,
) -> Dict[str, str]:
    """Sign an HTTP request using SigV4 and return the signed headers.

    Args:
        endpoint: The full URL to sign against.
        headers: Pre-signing headers.
        body_bytes: The encoded request body.
        access_key_id: AWS access key.
        secret_access_key: AWS secret key.
        session_token: Optional session token.
        region: AWS region.

    Returns:
        A dict of signed headers ready for use with httpx.
    """
    credentials = Credentials(access_key_id, secret_access_key, session_token)
    aws_request = AWSRequest(method='POST', url=endpoint, data=body_bytes, headers=headers)
    SigV4Auth(credentials, TCP_SERVICE, region).add_auth(aws_request)
    return dict(aws_request.headers)


async def call_tcp(operation: TCPOperation, body: Optional[Dict[str, Any]] = None) -> Any:
    """Call a TCP (Transform Control Plane) operation with SigV4 signing and retries.

    Uses awsJson1_0 protocol (POST with X-Amz-Target header).

    Args:
        operation: TCP operation name.
        body: Request body (defaults to empty dict).

    Returns:
        Parsed JSON response.

    Raises:
        HttpError: On non-2xx responses after retries.
    """
    if body is None:
        body = {}

    config = config_store.get_sigv4_config()
    if config is None:
        raise RuntimeError('SigV4 not configured. Call configure_sigv4 first.')
    parsed = urlparse(config.tcp_endpoint)
    hostname = parsed.hostname or ''

    payload = json.dumps(body).encode('utf-8')

    # Build pre-signing headers
    headers: Dict[str, str] = {
        'Content-Type': 'application/x-amz-json-1.0',
        'X-Amz-Target': f'{TCP_TARGET_PREFIX}.{operation}',
        'host': hostname,
    }

    # Sign the request
    signed_headers = _sign_request(
        endpoint=config.tcp_endpoint,
        headers=headers,
        body_bytes=payload,
        access_key_id=config.access_key_id,
        secret_access_key=config.secret_access_key,
        session_token=config.session_token,
        region=config.region,
    )

    async with httpx.AsyncClient() as client:
        response = await request_with_retry(
            client,
            'POST',
            config.tcp_endpoint,
            signed_headers,
            payload,
            timeout_seconds=TIMEOUT_SECONDS,
        )
        return response.json()
