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

"""AWS client utilities via bedrock-agentcore SDK."""

import time
from bedrock_agentcore.tools import BrowserClient
from loguru import logger
from os import getenv


# Cached BrowserClient instances keyed by region, with the monotonic
# timestamp at which each entry was created. Entries older than the
# configured TTL are discarded and recreated so that refreshed AWS
# credentials (e.g. after `ada credentials update` or IAM role rotation)
# are picked up without restarting the process.
_browser_clients: dict[str, BrowserClient] = {}
_browser_client_created_at: dict[str, float] = {}

MCP_INTEGRATION_SOURCE = 'awslabs-agentcore-mcp-server'

# How long a cached BrowserClient may be reused before it is recreated.
# A BrowserClient wraps boto3 clients whose credential providers resolve and
# cache credentials at construction time; caching the wrapper indefinitely
# means rotated credentials are never observed until the process restarts.
# The TTL bounds that staleness window. Overridable via the
# AGENTCORE_BROWSER_CLIENT_TTL_SECONDS environment variable.
DEFAULT_BROWSER_CLIENT_TTL_SECONDS = 300


def _get_ttl_seconds() -> float:
    """Resolve the client cache TTL from the environment, with a safe default."""
    raw = getenv('AGENTCORE_BROWSER_CLIENT_TTL_SECONDS')
    if raw is None:
        return DEFAULT_BROWSER_CLIENT_TTL_SECONDS
    try:
        ttl = float(raw)
    except ValueError:
        logger.warning(
            f'Invalid AGENTCORE_BROWSER_CLIENT_TTL_SECONDS={raw!r}; '
            f'falling back to {DEFAULT_BROWSER_CLIENT_TTL_SECONDS}s'
        )
        return DEFAULT_BROWSER_CLIENT_TTL_SECONDS
    # A non-positive TTL disables caching entirely (always recreate).
    return max(ttl, 0.0)


def get_browser_client(
    region_name: str | None = None,
) -> BrowserClient:
    """Get a BrowserClient for the specified region, recreating stale ones.

    Uses the bedrock-agentcore SDK to manage boto3 clients, endpoint
    resolution, and user-agent tagging. Credentials are resolved from
    the environment (AWS_PROFILE, AWS_ACCESS_KEY_ID, IAM role, etc.).

    Clients are cached per region for performance, but each cache entry
    expires after a TTL (see ``DEFAULT_BROWSER_CLIENT_TTL_SECONDS``). Once
    an entry expires it is rebuilt on the next call, which forces the
    underlying boto3 clients to re-resolve credentials. Without this the
    cache would serve a client bound to credentials captured at first use
    forever, so a credential refresh (``ada credentials update``, IAM role
    rotation, expired STS session) would not take effect until the process
    was restarted.

    Args:
        region_name: AWS region. Defaults to AWS_REGION env var or us-east-1.

    Returns:
        A BrowserClient instance for the region (cached when still fresh).
    """
    region = region_name or getenv('AWS_REGION') or 'us-east-1'

    ttl = _get_ttl_seconds()
    now = time.monotonic()

    cached = _browser_clients.get(region)
    if cached is not None:
        age = now - _browser_client_created_at.get(region, 0.0)
        if ttl > 0 and age < ttl:
            return cached
        # Expired (or caching disabled): drop it and rebuild below so that
        # refreshed credentials are picked up.
        logger.info(
            f'BrowserClient for region={region} expired after {age:.0f}s '
            f'(ttl={ttl:.0f}s); recreating to refresh credentials'
        )
        _browser_clients.pop(region, None)
        _browser_client_created_at.pop(region, None)

    client = BrowserClient(region=region, integration_source=MCP_INTEGRATION_SOURCE)

    if ttl > 0:
        _browser_clients[region] = client
        _browser_client_created_at[region] = now

    logger.info(f'Created BrowserClient for region={region}')
    return client
