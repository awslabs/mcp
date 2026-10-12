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

import asyncio
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
    IamAuthConfig,
    NodeAddress,
    ServerCredentials,
    ServiceType,
)


logger = logging.getLogger(__name__)

GlideClientType = GlideClient | GlideClusterClient

_client: GlideClientType | None = None


def _resolve_region() -> str:
    """Resolve the AWS region used to sign ElastiCache IAM auth tokens.

    Uses AWS_REGION / AWS_DEFAULT_REGION (captured in VALKEY_CFG['region']) and falls
    back to the boto3 default session (shared config, AWS_PROFILE, and so on).
    """
    region = VALKEY_CFG.get('region')
    if not region:
        import boto3.session

        region = boto3.session.Session().region_name
    if not region:
        raise ValueError(
            'AWS_REGION is required when VALKEY_IAM_AUTH is enabled '
            '(set AWS_REGION to the region of the ElastiCache cache)'
        )
    return region


def _build_credentials() -> ServerCredentials | None:
    """Build GLIDE server credentials from VALKEY_CFG.

    Two modes:
    - IAM authentication (VALKEY_IAM_AUTH=true): required for Amazon ElastiCache serverless
      caches with a public endpoint. GLIDE generates the SigV4 IAM auth token from the
      default AWS credential chain and refreshes it before the 15-minute expiry, so no token
      handling is needed here. VALKEY_PWD is ignored in this mode.
    - Password authentication (default): VALKEY_PWD with optional VALKEY_USERNAME.
    """
    username = VALKEY_CFG.get('username')

    if VALKEY_CFG.get('iam_auth', False):
        cache_name = VALKEY_CFG.get('cache_name')
        if not username:
            raise ValueError(
                'VALKEY_USERNAME (the IAM-enabled ElastiCache user id, e.g. default.iam-user) '
                'is required when VALKEY_IAM_AUTH is enabled'
            )
        if not cache_name:
            raise ValueError(
                'VALKEY_CACHE_NAME (the ElastiCache cache name the IAM token is signed for) '
                'is required when VALKEY_IAM_AUTH is enabled'
            )
        if '.' in cache_name:
            raise ValueError(
                'Invalid VALKEY_CACHE_NAME: expected the cache name, not an endpoint address'
            )
        if VALKEY_CFG.get('password'):
            logger.warning('VALKEY_PWD is ignored because VALKEY_IAM_AUTH is enabled')
        return ServerCredentials(
            username=username,
            iam_config=IamAuthConfig(
                cluster_name=cache_name.lower(),
                service=ServiceType.ELASTICACHE,
                region=_resolve_region(),
            ),
        )

    password = VALKEY_CFG.get('password', '')
    if password:
        return ServerCredentials(password, username) if username else ServerCredentials(password)
    return None


def _build_config() -> GlideClientConfiguration | GlideClusterClientConfiguration:
    """Build GLIDE client configuration from VALKEY_CFG."""
    addresses = [NodeAddress(VALKEY_CFG['host'], VALKEY_CFG['port'])]

    credentials = _build_credentials()
    iam_auth = VALKEY_CFG.get('iam_auth', False)
    use_tls = bool(VALKEY_CFG.get('ssl', False)) or iam_auth
    if iam_auth and not VALKEY_CFG.get('ssl', False):
        logger.info('TLS enabled automatically because VALKEY_IAM_AUTH is enabled')

    reconnect = BackoffStrategy(num_of_retries=10, factor=500, exponent_base=2, jitter_percent=20)

    kwargs: dict = {
        'addresses': addresses,
        'use_tls': use_tls,
        'request_timeout': 5000,
        'reconnect_strategy': reconnect,
        'client_name': 'valkey-mcp-server',
    }
    if credentials:
        kwargs['credentials'] = credentials

    # Wire TLS certificate config if CA certs path is provided
    if use_tls and VALKEY_CFG.get('ssl_ca_certs'):
        from glide_shared.config import TlsAdvancedConfiguration

        ca_path = VALKEY_CFG['ssl_ca_certs']
        try:
            with open(ca_path, 'rb') as f:
                ca_cert = f.read()
        except (FileNotFoundError, PermissionError) as e:
            raise ValueError(f'Failed to read TLS CA certificate at {ca_path}: {e}') from e
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


_client_lock = asyncio.Lock()


async def get_client() -> GlideClientType:
    """Get or create the GLIDE client singleton (thread-safe via asyncio.Lock)."""
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:  # double-check after acquiring lock
                config = _build_config()
                # Configure GLIDE's internal logger (Rust core)
                from glide import Logger as GlideLogger
                from glide.logger import Level as GlideLogLevel

                level_map = {
                    'ERROR': GlideLogLevel.ERROR,
                    'WARN': GlideLogLevel.WARN,
                    'INFO': GlideLogLevel.INFO,
                    'DEBUG': GlideLogLevel.DEBUG,
                    'TRACE': GlideLogLevel.TRACE,
                    'OFF': GlideLogLevel.OFF,
                }
                glide_level = level_map.get(
                    VALKEY_CFG.get('glide_log_level', 'WARN'), GlideLogLevel.WARN
                )
                GlideLogger.init(glide_level)
                if isinstance(config, GlideClusterClientConfiguration):
                    _client = await GlideClusterClient.create(config)
                    logger.info(
                        'GLIDE cluster client connected to %s:%s',
                        VALKEY_CFG['host'],
                        VALKEY_CFG['port'],
                    )
                else:
                    _client = await GlideClient.create(config)
                    logger.info(
                        'GLIDE standalone client connected to %s:%s',
                        VALKEY_CFG['host'],
                        VALKEY_CFG['port'],
                    )
    return _client


async def close_client() -> None:
    """Close the GLIDE client if open."""
    await reset_client()


async def reset_client() -> None:
    """Close and reset client reference (for testing)."""
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.close()
        _client = None
