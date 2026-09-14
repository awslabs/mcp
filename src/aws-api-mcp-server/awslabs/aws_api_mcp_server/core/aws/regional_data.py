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

"""Regional availability data provider backed by S3.

Reads Capability Insights for AWS data from a user-specified S3 bucket or
access point and exposes query methods used by the get_regional_availability
MCP tool.
"""

import json
import time
from typing import Any, Optional
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from loguru import logger

from ..common.config import AWS_API_MCP_PROFILE_NAME


class RegionalDataProvider:
    """Loads and caches regional availability data from an S3 location.

    The S3 URI can be:
      - ``s3://bucket-name/optional-prefix``
      - An S3 access point ARN (``arn:aws:s3:region:account:accesspoint/name/prefix``)

    Data layout expected under the prefix::

        <prefix>/
          services.json          # index: {"services": [{"service": "...", "features": [...]}]}
          <service>/
            <feature>.json       # {"regions": {"us-east-1": "AVAILABLE", ...}}

    Attributes:
        cache_ttl: Seconds before cached data is considered stale.
    """

    def __init__(self, s3_uri: str, cache_ttl: int = 300) -> None:
        """Initialise the provider.

        Args:
            s3_uri: S3 URI (``s3://…``) or access-point ARN pointing to the data root.
            cache_ttl: Number of seconds to cache the data in memory.
        """
        self._s3_uri = s3_uri
        self._bucket, self._prefix = self._parse_s3_uri(s3_uri)
        self.cache_ttl = cache_ttl
        self._cache: dict[str, Any] = {}
        self._cache_timestamp: float = 0.0
        session = boto3.Session(profile_name=AWS_API_MCP_PROFILE_NAME)
        self._s3_client = session.client('s3')

    # ------------------------------------------------------------------
    # URI parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_s3_uri(uri: str) -> tuple[str, str]:
        """Return ``(bucket_or_arn, prefix)`` from an S3 URI or access-point ARN.

        Supports:
          - ``s3://my-bucket/some/prefix``
          - ``arn:aws:s3:us-east-1:123456789012:accesspoint/my-ap/some/prefix``
        """
        if uri.startswith('arn:'):
            # Access-point ARN – split ARN from the object prefix.
            parts = uri.split('/', 1)
            arn = parts[0]
            prefix = parts[1].rstrip('/') if len(parts) > 1 else ''
            return arn, prefix

        parsed = urlparse(uri)
        if parsed.scheme != 's3':
            raise ValueError(
                f"Invalid S3 URI '{uri}'. Expected 's3://bucket/prefix' or an S3 access-point ARN."
            )
        bucket = parsed.netloc
        prefix = parsed.path.lstrip('/').rstrip('/')
        return bucket, prefix

    # ------------------------------------------------------------------
    # S3 helpers
    # ------------------------------------------------------------------

    def _s3_key(self, *parts: str) -> str:
        """Build a full S3 key from the configured prefix and additional path parts."""
        segments = [self._prefix] + list(parts) if self._prefix else list(parts)
        return '/'.join(segments)

    def _get_object_json(self, key: str) -> Any:
        """Download an S3 object and parse it as JSON."""
        response = self._s3_client.get_object(Bucket=self._bucket, Key=key)
        body = response['Body'].read().decode('utf-8')
        return json.loads(body)

    # ------------------------------------------------------------------
    # Data loading & caching
    # ------------------------------------------------------------------

    def _is_cache_valid(self) -> bool:
        return bool(self._cache) and (time.monotonic() - self._cache_timestamp) < self.cache_ttl

    def _load_data(self) -> dict[str, Any]:
        """Load the service index and all per-service feature data from S3.

        Returns a dict keyed by ``service_name`` whose values are dicts keyed by
        ``feature_name`` mapping to region availability dicts.
        """
        if self._is_cache_valid():
            return self._cache

        logger.info('Loading regional availability data from {}', self._s3_uri)

        try:
            index = self._get_object_json(self._s3_key('services.json'))
        except ClientError as exc:
            error_code = exc.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(
                    'services.json not found at {}. '
                    'Attempting to list objects directly.',
                    self._s3_uri,
                )
                index = self._build_index_from_listing()
            else:
                raise

        data: dict[str, Any] = {}
        for svc in index.get('services', []):
            svc_name = svc.get('service', svc) if isinstance(svc, dict) else svc
            features = svc.get('features', []) if isinstance(svc, dict) else []
            svc_data: dict[str, Any] = {}

            if features:
                for feat in features:
                    feat_name = feat.get('feature', feat) if isinstance(feat, dict) else feat
                    try:
                        feat_data = self._get_object_json(
                            self._s3_key(svc_name, f'{feat_name}.json')
                        )
                        svc_data[feat_name] = feat_data.get('regions', feat_data)
                    except ClientError:
                        logger.debug(
                            'Could not load feature data for {}/{}', svc_name, feat_name
                        )
            else:
                # No explicit features – try loading a single service-level file.
                try:
                    svc_level = self._get_object_json(self._s3_key(f'{svc_name}.json'))
                    svc_data['_service'] = svc_level.get('regions', svc_level)
                except ClientError:
                    logger.debug('Could not load service-level data for {}', svc_name)

            if svc_data:
                data[svc_name] = svc_data

        self._cache = data
        self._cache_timestamp = time.monotonic()
        logger.info('Loaded regional data for {} services', len(data))
        return data

    def _build_index_from_listing(self) -> dict[str, Any]:
        """Fallback: build an index by listing objects under the prefix."""
        paginator = self._s3_client.get_paginator('list_objects_v2')
        prefix = self._prefix + '/' if self._prefix else ''
        services: dict[str, list[str]] = {}

        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                relative = key[len(prefix):]
                parts = relative.split('/')
                if len(parts) == 2 and parts[1].endswith('.json'):
                    svc = parts[0]
                    feat = parts[1].removesuffix('.json')
                    services.setdefault(svc, []).append(feat)
                elif len(parts) == 1 and parts[0].endswith('.json'):
                    svc = parts[0].removesuffix('.json')
                    services.setdefault(svc, [])

        return {
            'services': [
                {'service': svc, 'features': [{'feature': f} for f in feats]}
                for svc, feats in services.items()
            ]
        }

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def get_availability(
        self,
        service_name: str,
        feature_name: Optional[str] = None,
        regions: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Query regional availability for a service/feature.

        Args:
            service_name: AWS service identifier (e.g. ``ec2``).
            feature_name: Optional feature within the service.
            regions: Optional list of region codes to filter results.

        Returns:
            Dict with ``service``, ``feature``, and ``regions`` keys.
        """
        data = self._load_data()

        svc_data = data.get(service_name)
        if not svc_data:
            return {
                'service': service_name,
                'feature': feature_name,
                'regions': {},
                'error': f"No data available for service '{service_name}'.",
            }

        if feature_name:
            region_map = svc_data.get(feature_name, {})
            if not region_map:
                return {
                    'service': service_name,
                    'feature': feature_name,
                    'regions': {},
                    'error': f"No data available for feature '{feature_name}' of service '{service_name}'.",
                }
        else:
            # Return first available feature or the _service level data.
            first_key = next(iter(svc_data))
            region_map = svc_data[first_key]
            feature_name = first_key if first_key != '_service' else None

        if regions:
            region_map = {r: region_map.get(r, 'UNKNOWN') for r in regions}

        return {
            'service': service_name,
            'feature': feature_name,
            'regions': region_map,
        }

    def list_services(self) -> list[dict[str, Any]]:
        """Return a list of available services and their features."""
        data = self._load_data()
        result = []
        for svc_name, svc_data in data.items():
            features = [f for f in svc_data if f != '_service']
            result.append({'service': svc_name, 'features': features})
        return result
