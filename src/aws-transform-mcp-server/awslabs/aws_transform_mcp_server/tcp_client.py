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

"""TCP (Transform Control Plane) client — SigV4-signed RPC-over-HTTP.

Credentials are resolved from boto3's standard credential chain on every call.
boto3 handles credential refresh automatically.
"""

import httpx
import json
from awslabs.aws_transform_mcp_server.aws_helper import AwsHelper
from awslabs.aws_transform_mcp_server.config_store import derive_tcp_endpoint, get_sigv4_region
from awslabs.aws_transform_mcp_server.consts import (
    TCP_SERVICE,
    TCP_TARGET_PREFIX,
    TIMEOUT_SECONDS,
)
from awslabs.aws_transform_mcp_server.http_utils import request_with_retry
from botocore.credentials import ReadOnlyCredentials
from typing import Any, Dict, Literal, NamedTuple, Optional
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


class TcpConfig(NamedTuple):
    """Resolved TCP connection parameters."""

    endpoint: str
    region: str
    credentials: ReadOnlyCredentials


def _resolve_tcp_config() -> TcpConfig:
    """Resolve TCP endpoint and credentials from environment and boto3.

    Region resolution: discovered profile region → AWS_REGION env → profile region → 'us-east-1'.
    Credentials come from boto3's standard chain (AWS_PROFILE, env vars,
    ~/.aws/credentials, instance profile).

    Raises:
        RuntimeError: If no AWS credentials are available.
    """
    session = AwsHelper.create_session()
    region = get_sigv4_region() or AwsHelper.resolve_region(session)
    endpoint = derive_tcp_endpoint(region)
    credentials = session.get_credentials()
    if credentials is None:
        raise RuntimeError(
            'No AWS credentials found. Set AWS_PROFILE in your MCP client config, '
            'or configure credentials via aws configure, environment variables, '
            'or instance profile.'
        )
    return TcpConfig(
        endpoint=endpoint, region=region, credentials=credentials.get_frozen_credentials()
    )


async def call_tcp(operation: TCPOperation, body: Optional[Dict[str, Any]] = None) -> Any:
    """Call a TCP (Transform Control Plane) operation with SigV4 signing and retries.

    Credentials are resolved from boto3's standard chain on every call, so they
    auto-refresh when STS temporary credentials expire.

    Uses awsJson1_0 protocol (POST with X-Amz-Target header).

    Args:
        operation: TCP operation name.
        body: Request body (defaults to empty dict).

    Returns:
        Parsed JSON response.

    Raises:
        RuntimeError: If no AWS credentials are available.
        HttpError: On non-2xx responses after retries.
    """
    if body is None:
        body = {}

    config = _resolve_tcp_config()
    parsed = urlparse(config.endpoint)
    hostname = parsed.hostname or ''

    payload = json.dumps(body).encode('utf-8')

    headers: Dict[str, str] = {
        'Content-Type': 'application/x-amz-json-1.0',
        'X-Amz-Target': f'{TCP_TARGET_PREFIX}.{operation}',
        'host': hostname,
    }

    signed_headers = AwsHelper.sign_request(
        endpoint=config.endpoint,
        headers=headers,
        body_bytes=payload,
        credentials=config.credentials,
        service=TCP_SERVICE,
        region=config.region,
    )

    async with httpx.AsyncClient() as client:
        response = await request_with_retry(
            client,
            'POST',
            config.endpoint,
            signed_headers,
            payload,
            timeout_seconds=TIMEOUT_SECONDS,
        )
        return response.json()
