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


import logging
import threading
import time
from typing import Any

import boto3
from botocore.client import BaseClient


class ThreadSafeAWSClientCache:
    def __init__(
        self,
        max_size: int = 50,
        max_age: float = 3600.0,  # 1 hour default expiry
        prune_interval: float = 300.0,  # Prune every 5 minutes
    ) -> None:
        """Thread-safe AWS client cache with configurable size and expiry.

        Args:
            max_size: Maximum number of cached clients
            max_age: Maximum age of cached clients before eviction (seconds)
            prune_interval: How often to run cache pruning (seconds)
        """
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._max_age = max_age
        self._prune_interval = prune_interval
        self._last_prune = time.time()
        self.logger = logging.getLogger(__name__)

    def _generate_cache_key(self, service: str, region: str | None = None, profile: str | None = None) -> str:
        """Generate a unique cache key based on service parameters."""
        return f"{service}:{region or 'default'}:{profile or 'default'}"

    def _prune_cache(self) -> None:
        """Remove expired or excess cache entries."""
        current_time = time.time()

        with self._lock:
            # Remove expired entries
            self._cache = {
                key: entry for key, entry in self._cache.items() if current_time - entry["timestamp"] < self._max_age
            }

            # Remove excess entries if over max size
            if len(self._cache) > self._max_size:
                sorted_entries = sorted(self._cache.items(), key=lambda x: x[1]["timestamp"])
                for key, _ in sorted_entries[: len(self._cache) - self._max_size]:
                    del self._cache[key]

            self._last_prune = current_time

    def get_client(self, service: str, region: str | None = None, profile: str | None = None) -> BaseClient:
        """Thread-safe method to retrieve or create AWS client.

        Args:
            service: AWS service name (e.g. 's3', 'ec2')
            region: Optional AWS region
            profile: Optional AWS profile name

        Returns:
            Boto3 client instance
        """
        cache_key = self._generate_cache_key(service, region, profile)
        current_time = time.time()

        # Periodic cache pruning
        if current_time - self._last_prune > self._prune_interval:
            self._prune_cache()

        with self._lock:
            # Check existing cache
            if cache_key in self._cache:
                cached_entry = self._cache[cache_key]
                if current_time - cached_entry["timestamp"] < self._max_age:
                    return cached_entry["client"]

            # Create new client
            try:
                session_kwargs = {}
                if profile:
                    session_kwargs["profile_name"] = profile

                session = boto3.Session(**session_kwargs)
                client_kwargs = {"service_name": service}

                if region:
                    client_kwargs["region_name"] = region

                new_client = session.client(**client_kwargs)

                # Store in cache
                self._cache[cache_key] = {"client": new_client, "timestamp": current_time}

                return new_client

            except Exception as e:
                self.logger.error(f"Failed to create AWS client: {e}")
                raise

    def clear(self) -> None:
        """Clear entire client cache."""
        with self._lock:
            self._cache.clear()

    def cache_stats(self) -> dict[str, Any]:
        """Return cache performance statistics."""
        with self._lock:
            return {"total_entries": len(self._cache), "max_size": self._max_size, "max_age": self._max_age}


# Global thread-safe client cache instance
aws_client_cache = ThreadSafeAWSClientCache()
