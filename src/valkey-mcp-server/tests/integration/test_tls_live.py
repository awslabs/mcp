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

"""Live integration tests for TLS and authenticated connections.

Requires:
    VALKEY_HOST — Valkey instance hostname
    VALKEY_TLS_PORT — TLS-enabled Valkey port (default: 6480)
    VALKEY_SSL_CA_CERTS — Path to CA certificate (optional, for CA-verified TLS)
    VALKEY_PWD — Password (optional, for authenticated connections)

Run:
    VALKEY_TLS_PORT=6480 uv run pytest tests/test_tls_live.py -m live -v
"""

from __future__ import annotations

import asyncio
import os
import pytest


pytestmark = [pytest.mark.live, pytest.mark.asyncio, pytest.mark.timeout(15)]


@pytest.fixture()
async def tls_client():
    """Create a GLIDE client with TLS enabled."""
    host = os.environ.get('VALKEY_HOST')
    port = int(os.environ.get('VALKEY_TLS_PORT', '6480'))
    if not host:
        pytest.skip('VALKEY_HOST not set')

    from glide import (
        GlideClient,
        GlideClientConfiguration,
        NodeAddress,
        ServerCredentials,
    )

    kwargs: dict = {
        'addresses': [NodeAddress(host, port)],
        'use_tls': True,
        'request_timeout': 5000,
    }

    # Optional CA cert
    ca_path = os.environ.get('VALKEY_SSL_CA_CERTS')
    if ca_path:
        from glide import AdvancedGlideClientConfiguration
        from glide_shared.config import TlsAdvancedConfiguration

        with open(ca_path, 'rb') as f:
            ca_cert = f.read()
        kwargs['advanced_config'] = AdvancedGlideClientConfiguration(
            tls_config=TlsAdvancedConfiguration(root_pem_cacerts=ca_cert),
        )
    else:
        # Self-signed / insecure TLS for testing
        from glide import AdvancedGlideClientConfiguration
        from glide_shared.config import TlsAdvancedConfiguration

        kwargs['advanced_config'] = AdvancedGlideClientConfiguration(
            tls_config=TlsAdvancedConfiguration(use_insecure_tls=True),
        )

    # Optional auth
    password = os.environ.get('VALKEY_PWD', '')
    username = os.environ.get('VALKEY_USERNAME')
    if password:
        kwargs['credentials'] = (
            ServerCredentials(password, username) if username else ServerCredentials(password)
        )

    try:
        c = await asyncio.wait_for(
            GlideClient.create(GlideClientConfiguration(**kwargs)), timeout=10
        )
    except Exception as e:
        pytest.skip(f'Cannot connect to TLS Valkey at {host}:{port}: {e}')
    yield c
    await c.close()


class TestTlsConnection:
    async def test_ping(self, tls_client):
        """Basic connectivity test over TLS."""
        result = await tls_client.ping()
        assert result == b'PONG'

    async def test_set_get(self, tls_client):
        """Read/write over TLS."""
        await tls_client.set('tls_test_key', 'tls_value')
        result = await tls_client.get('tls_test_key')
        assert result == b'tls_value' or result == 'tls_value'
        await tls_client.delete(['tls_test_key'])

    async def test_info(self, tls_client):
        """Server info over TLS — verifies full command roundtrip."""
        result = await tls_client.custom_command(['INFO', 'server'])
        decoded = result.decode() if isinstance(result, bytes) else result
        assert 'valkey_version' in decoded or 'redis_version' in decoded
