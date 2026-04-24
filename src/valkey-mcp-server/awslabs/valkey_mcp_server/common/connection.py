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

"""Valkey GLIDE connection manager."""

from __future__ import annotations

import logging
from awslabs.valkey_mcp_server.common.config import VALKEY_CFG
from glide import (
    AdvancedGlideClientConfiguration,
    AdvancedGlideClusterClientConfiguration,
    BackoffStrategy,
    GlideClient,
    GlideClientConfiguration,
    GlideClusterClient,
    GlideClusterClientConfiguration,
    NodeAddress,
    ServerCredentials,
)
from typing import Union


logger = logging.getLogger(__name__)

GlideClientType = Union[GlideClient, GlideClusterClient]

_client: GlideClientType | None = None


def _build_config() -> GlideClientConfiguration | GlideClusterClientConfiguration:
    """Build GLIDE client configuration from VALKEY_CFG."""
    addresses = [NodeAddress(VALKEY_CFG['host'], VALKEY_CFG['port'])]

    password = VALKEY_CFG.get('password', '')
    username = VALKEY_CFG.get('username')
    credentials = None
    if password:
        credentials = (
            ServerCredentials(password, username) if username else ServerCredentials(password)
        )

    reconnect = BackoffStrategy(num_of_retries=10, factor=500, exponent_base=2)

    kwargs: dict = {
        'addresses': addresses,
        'use_tls': VALKEY_CFG.get('ssl', False),
        'request_timeout': 5000,
        'reconnect_strategy': reconnect,
        'client_name': 'valkey-mcp-server',
    }
    if credentials:
        kwargs['credentials'] = credentials

    # Wire TLS certificate config if CA certs path is provided
    if VALKEY_CFG.get('ssl', False) and VALKEY_CFG.get('ssl_ca_certs'):
        from glide_shared.config import TlsAdvancedConfiguration

        ca_path = VALKEY_CFG['ssl_ca_certs']
        with open(ca_path, 'rb') as f:
            ca_cert = f.read()
        if VALKEY_CFG['cluster_mode']:
            kwargs['advanced_config'] = AdvancedGlideClusterClientConfiguration(
                tls_config=TlsAdvancedConfiguration(root_pem_cacerts=ca_cert),
            )
        else:
            kwargs['advanced_config'] = AdvancedGlideClientConfiguration(
                tls_config=TlsAdvancedConfiguration(root_pem_cacerts=ca_cert),
            )

    if VALKEY_CFG['cluster_mode']:
        return GlideClusterClientConfiguration(**kwargs)
    return GlideClientConfiguration(**kwargs)


async def get_client() -> GlideClientType:
    """Get or create the GLIDE client singleton."""
    global _client
    if _client is None:
        config = _build_config()
        if isinstance(config, GlideClusterClientConfiguration):
            _client = await GlideClusterClient.create(config)
        else:
            _client = await GlideClient.create(config)
        logger.info('GLIDE client connected to %s:%s', VALKEY_CFG['host'], VALKEY_CFG['port'])
    return _client


async def close_client() -> None:
    """Close the GLIDE client if open."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


def reset_client() -> None:
    """Reset client reference (for testing)."""
    global _client
    _client = None
