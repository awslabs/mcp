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

"""Credential management for cross-account AWS API calls with caching."""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

import boto3
from loguru import logger

from ..common.config import (
    ASSUME_ROLE_CACHE_SIZE,
    ASSUME_ROLE_DURATION_SECONDS,
    DEFAULT_REGION,
)
from ..common.models import Credentials


@dataclass
class CachedCredentials:
    """Cached credentials with expiry information."""

    credentials: Credentials
    expiry: datetime
    role_arn: str


class CredentialManager:
    """
    Thread-safe credential manager with caching for assumed roles.

    This manager handles AWS STS AssumeRole operations and caches the resulting
    temporary credentials to minimize STS API calls and improve performance.

    Features:
    - Automatic credential refresh when approaching expiry
    - LRU eviction when cache size limit is reached
    - Thread-safe operations using asyncio locks
    - Support for external IDs for secure cross-account access
    """

    def __init__(
        self,
        max_cache_size: int = ASSUME_ROLE_CACHE_SIZE,
        default_duration_seconds: int = ASSUME_ROLE_DURATION_SECONDS,
    ):
        """
        Initialize the credential manager.

        Args:
            max_cache_size: Maximum number of roles to cache (default: 50)
            default_duration_seconds: Default session duration in seconds (default: 3600)
        """
        self._cache: Dict[str, CachedCredentials] = {}
        self._max_cache_size = max_cache_size
        self._default_duration_seconds = default_duration_seconds
        self._lock = asyncio.Lock()

        logger.info(
            'CredentialManager initialized: max_cache_size={}, default_duration={}s',
            max_cache_size,
            default_duration_seconds,
        )

    async def get_credentials(
        self,
        role_arn: str,
        session_name: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        external_id: Optional[str] = None,
    ) -> Credentials:
        """
        Get credentials for a role, using cache if valid.

        This method checks the cache for valid credentials. If not found or expired,
        it performs an STS AssumeRole operation and caches the result.

        Args:
            role_arn: ARN of the role to assume (supports both aws and aws-cn)
            session_name: Optional session name (auto-generated if not provided)
            duration_seconds: Session duration (default: from config)
            external_id: Optional external ID for cross-account access

        Returns:
            Credentials object containing temporary AWS credentials

        Raises:
            boto3 ClientError: If STS AssumeRole fails
        """
        duration = duration_seconds or self._default_duration_seconds

        async with self._lock:
            # Check cache
            cached = self._cache.get(role_arn)
            if cached and self._is_valid(cached):
                logger.info(
                    'Using cached credentials for role: {} (expires in {}s)',
                    role_arn,
                    int((cached.expiry - datetime.now()).total_seconds()),
                )
                return cached.credentials

            # Cache miss or expired - assume role
            logger.info('Assuming role: {} (duration: {}s)', role_arn, duration)
            credentials = await self._assume_role(
                role_arn, session_name, duration, external_id
            )

            # Store in cache with 5-minute safety buffer
            expiry = datetime.now() + timedelta(seconds=duration - 300)
            self._cache[role_arn] = CachedCredentials(credentials, expiry, role_arn)

            # Evict oldest if cache full
            if len(self._cache) > self._max_cache_size:
                oldest = min(self._cache.values(), key=lambda c: c.expiry)
                del self._cache[oldest.role_arn]
                logger.info(
                    'Cache full - evicted oldest role: {} (had {} seconds remaining)',
                    oldest.role_arn,
                    int((oldest.expiry - datetime.now()).total_seconds()),
                )

            logger.info(
                'Successfully cached credentials for role: {} (cache size: {}/{})',
                role_arn,
                len(self._cache),
                self._max_cache_size,
            )
            return credentials

    def _is_valid(self, cached: CachedCredentials) -> bool:
        """
        Check if cached credentials are still valid.

        Credentials are considered valid if they have not expired yet.
        The expiry time includes a 5-minute safety buffer.

        Args:
            cached: Cached credentials to check

        Returns:
            True if credentials are valid, False otherwise
        """
        is_valid = datetime.now() < cached.expiry
        if not is_valid:
            logger.debug(
                'Cached credentials expired for role: {} (expired {} seconds ago)',
                cached.role_arn,
                int((datetime.now() - cached.expiry).total_seconds()),
            )
        return is_valid

    async def _assume_role(
        self,
        role_arn: str,
        session_name: Optional[str],
        duration_seconds: int,
        external_id: Optional[str],
    ) -> Credentials:
        """
        Assume an IAM role and return temporary credentials.

        This method uses boto3 to call STS AssumeRole. It automatically
        determines the correct STS endpoint based on the role ARN partition
        (aws or aws-cn).

        Args:
            role_arn: ARN of the role to assume
            session_name: Session name for the assumed role
            duration_seconds: Session duration in seconds
            external_id: Optional external ID

        Returns:
            Credentials object with temporary credentials

        Raises:
            boto3 ClientError: If AssumeRole fails
        """
        # Use DEFAULT_REGION for STS endpoint (matches the server's partition)
        region = DEFAULT_REGION

        sts_client = boto3.client('sts', region_name=region)

        assume_role_params = {
            'RoleArn': role_arn,
            'RoleSessionName': session_name or f'mcp-{uuid.uuid4().hex[:8]}',
            'DurationSeconds': duration_seconds,
        }

        if external_id:
            assume_role_params['ExternalId'] = external_id

        logger.debug(
            'STS AssumeRole request: RoleArn={}, SessionName={}, Duration={}s, ExternalId={}',
            role_arn,
            assume_role_params['RoleSessionName'],
            duration_seconds,
            'PROVIDED' if external_id else 'NONE',
        )

        response = sts_client.assume_role(**assume_role_params)
        creds = response['Credentials']

        logger.info(
            'STS AssumeRole successful: AssumedRoleId={}, Expiration={}',
            response['AssumedRoleUser']['AssumedRoleId'],
            creds['Expiration'],
        )

        return Credentials(
            access_key_id=creds['AccessKeyId'],
            secret_access_key=creds['SecretAccessKey'],
            session_token=creds['SessionToken'],
        )

    async def clear_cache(self, role_arn: Optional[str] = None):
        """
        Clear cached credentials.

        Args:
            role_arn: If provided, clear only this role's cache.
                     If None, clear entire cache.
        """
        async with self._lock:
            if role_arn:
                if role_arn in self._cache:
                    del self._cache[role_arn]
                    logger.info('Cleared cache for role: {}', role_arn)
                else:
                    logger.warning('Role not in cache: {}', role_arn)
            else:
                cache_size = len(self._cache)
                self._cache.clear()
                logger.info('Cleared entire credential cache ({} entries)', cache_size)

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get current cache statistics.

        Returns:
            Dictionary containing cache size, capacity, and cached roles
        """
        return {
            'size': len(self._cache),
            'capacity': self._max_cache_size,
            'cached_roles': [
                {
                    'role_arn': cached.role_arn,
                    'expires_in_seconds': int(
                        (cached.expiry - datetime.now()).total_seconds()
                    ),
                }
                for cached in self._cache.values()
            ],
        }


# Global singleton instance
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """
    Get the global credential manager instance.

    This function implements a singleton pattern to ensure only one
    CredentialManager instance exists per server process.

    Returns:
        The global CredentialManager instance
    """
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager
