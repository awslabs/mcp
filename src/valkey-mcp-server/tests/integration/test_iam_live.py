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

"""Live integration tests for IAM authentication against an Amazon ElastiCache public endpoint.

These go through the server's own connection module (VALKEY_CFG -> _build_config -> get_client)
so they exercise the real configuration path, not a hand-built client.

Requires (all read by awslabs.valkey_mcp_server.common.config at import time):
    VALKEY_IAM_AUTH=true
    VALKEY_HOST        — public endpoint address (Endpoint.Address from describe-serverless-caches)
    VALKEY_USERNAME    — IAM-enabled ElastiCache user, e.g. default.iam-user
    VALKEY_CACHE_NAME  — serverless cache name (lowercase)
    AWS_REGION         — region of the cache
    VALKEY_CLUSTER_MODE=true (recommended for serverless)
    AWS credentials with elasticache:Connect on the cache and user ARNs

Run:
    uv run --frozen pytest tests/integration/test_iam_live.py -m live -v
"""

from __future__ import annotations

import asyncio
import os
import pytest
import uuid
from unittest.mock import patch


pytestmark = [pytest.mark.live, pytest.mark.asyncio, pytest.mark.timeout(30)]

MODULE = 'awslabs.valkey_mcp_server.common.connection'


def _iam_env_present() -> bool:
    return os.environ.get('VALKEY_IAM_AUTH', '').lower() in ('true', '1', 't') and bool(
        os.environ.get('VALKEY_HOST')
    )


@pytest.fixture()
async def iam_client():
    """GLIDE client created by the server's get_client() using IAM auth from the environment."""
    if not _iam_env_present():
        pytest.skip('VALKEY_IAM_AUTH / VALKEY_HOST not set')
    from awslabs.valkey_mcp_server.common.connection import get_client, reset_client

    await reset_client()
    client = await asyncio.wait_for(get_client(), timeout=20)
    yield client
    await reset_client()


class TestIamAuthLive:
    async def test_config_uses_iam_and_tls(self):
        if not _iam_env_present():
            pytest.skip('VALKEY_IAM_AUTH / VALKEY_HOST not set')
        from awslabs.valkey_mcp_server.common.connection import _build_config

        config = _build_config()
        assert config.use_tls is True
        assert config.credentials is not None
        assert config.credentials.is_iam_auth()

    async def test_ping(self, iam_client):
        result = await iam_client.ping()
        assert result == b'PONG'

    async def test_set_get_del(self, iam_client):
        key = f'mcp-iam-live:{uuid.uuid4()}'
        try:
            await iam_client.set(key, 'value')
            assert await iam_client.get(key) == b'value'
        finally:
            await iam_client.delete([key])

    async def test_wrong_username_is_rejected(self):
        """A username that is not in the cache's user group must fail authentication."""
        if not _iam_env_present():
            pytest.skip('VALKEY_IAM_AUTH / VALKEY_HOST not set')
        from awslabs.valkey_mcp_server.common import connection
        from glide import GlideClient, GlideClusterClient, GlideClusterClientConfiguration
        from glide_shared.exceptions import ClosingError

        bad_cfg = dict(connection.VALKEY_CFG, username=f'no-such-user-{uuid.uuid4().hex[:8]}')
        with patch(f'{MODULE}.VALKEY_CFG', bad_cfg):
            config = connection._build_config()

        with pytest.raises(ClosingError):
            if isinstance(config, GlideClusterClientConfiguration):
                client = await asyncio.wait_for(GlideClusterClient.create(config), timeout=20)
            else:
                client = await asyncio.wait_for(GlideClient.create(config), timeout=20)
            await client.close()
