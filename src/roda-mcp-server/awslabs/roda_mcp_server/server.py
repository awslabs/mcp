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

"""MCP server for Registry of Open Data on AWS (RODA)."""

import asyncio
import hashlib
import httpx
import json
import os
import re
import sys
from awslabs.roda_mcp_server.knowledge_base import DatasetKnowledgeBase
from collections import Counter
from datetime import datetime, timedelta
from fastmcp import FastMCP
from loguru import logger
from typing import Any


# Configure loguru to write to stderr (not stdout which is the JSON-RPC channel)
# and respect the FASTMCP_LOG_LEVEL environment variable
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Initialize FastMCP server
mcp = FastMCP('roda-mcp')

# Data source URL - NDJSON file with all datasets pre-parsed
REGISTRY_NDJSON_URL = 'https://registry.opendata.aws/index.ndjson'
REGISTRY_CHECKSUM_URL = 'https://registry.opendata.aws/index.ndjson.sha256'

# Cache for datasets with expiration
_datasets_cache: list[dict[str, Any]] | None = None
_cache_timestamp: datetime | None = None
CACHE_EXPIRY_HOURS = 24

# Knowledge base instance — swapped atomically on refresh, never mutated in place
_knowledge_base = DatasetKnowledgeBase()

# Lock to prevent concurrent cold-start fetches from racing
_fetch_lock = asyncio.Lock()


class ChecksumValidationError(Exception):
    """Raised when checksum validation fails.

    Checksum validation prevents man-in-the-middle attacks and data corruption.
    This control helps detection of tampered or corrupted downloads.
    """

    pass


async def fetch_datasets() -> list[dict[str, Any]]:
    """Fetch and cache datasets from RODA.

    Uses the official NDJSON index file which contains all datasets pre-parsed.
    Thread-safe: uses asyncio.Lock to prevent concurrent downloads on cold start,
    and builds a fresh knowledge base then swaps the reference atomically so
    readers never observe a half-built index.
    """
    global _datasets_cache, _cache_timestamp, _knowledge_base

    # Fast path: cache is valid, no lock needed
    if _datasets_cache is not None and _cache_timestamp is not None:
        if datetime.now() - _cache_timestamp < timedelta(hours=CACHE_EXPIRY_HOURS):
            return _datasets_cache

    async with _fetch_lock:
        # Re-check cache inside the lock — another coroutine may have populated it
        if _datasets_cache is not None and _cache_timestamp is not None:
            if datetime.now() - _cache_timestamp < timedelta(hours=CACHE_EXPIRY_HOURS):
                return _datasets_cache

        async with httpx.AsyncClient(verify=True, http2=True) as client:
            # Fetch the NDJSON file with all datasets
            # All external API calls require TLS 1.2 or higher with certificate validation enabled
            # Retry up to 2 times to handle CDN propagation delays and transient network errors
            max_retries = 2
            content_bytes = None
            last_network_error: Exception | None = None
            checksum_mismatch_count = 0
            last_expected_checksum: str | None = None
            last_computed_checksum: str | None = None

            for attempt in range(max_retries + 1):
                try:
                    response = await client.get(REGISTRY_NDJSON_URL, timeout=30.0)
                    response.raise_for_status()
                    content_bytes = response.content

                    # Fetch and validate checksum
                    checksum_response = await client.get(REGISTRY_CHECKSUM_URL, timeout=10.0)
                    checksum_response.raise_for_status()
                    checksum_parts = checksum_response.text.strip().split()
                    if not checksum_parts:
                        raise ChecksumValidationError(
                            'Checksum endpoint returned empty or whitespace-only content. '
                            'The registry may be misconfigured or under maintenance.'
                        )
                    last_expected_checksum = checksum_parts[0].lower()

                    last_computed_checksum = hashlib.sha256(content_bytes).hexdigest().lower()
                    if last_computed_checksum == last_expected_checksum:
                        break

                    # Checksum mismatch — log and retry
                    checksum_mismatch_count += 1
                    logger.warning(
                        f'Checksum mismatch on attempt {attempt + 1}/{max_retries + 1}: '
                        f'expected={last_expected_checksum}, '
                        f'computed={last_computed_checksum}'
                    )

                except (
                    httpx.HTTPStatusError,
                    httpx.TimeoutException,
                    httpx.ConnectError,
                ) as e:
                    logger.warning(
                        f'Network error on attempt {attempt + 1}/{max_retries + 1}: '
                        f'{type(e).__name__}: {e}'
                    )
                    last_network_error = e

                if attempt < max_retries:
                    await asyncio.sleep(3)
            else:
                # All retries exhausted — report both failure classes
                if checksum_mismatch_count > 0 and last_network_error is not None:
                    logger.error(
                        f'Fetch failed after {max_retries + 1} attempts: '
                        f'{checksum_mismatch_count} checksum mismatch(es) and '
                        f'network error ({type(last_network_error).__name__}). '
                        f'Last checksum: expected={last_expected_checksum}, '
                        f'computed={last_computed_checksum}'
                    )
                    raise ChecksumValidationError(
                        'Checksum validation failed — the downloaded data does not match '
                        'the expected hash, and network errors also occurred. '
                        'This could indicate data corruption, tampering, or connectivity issues. '
                        f'Expected: {last_expected_checksum}, Got: {last_computed_checksum}'
                    )
                elif last_network_error is not None:
                    # Only network errors — re-raise the last one
                    raise last_network_error
                else:
                    # Only checksum mismatches — possible tampering or corruption
                    logger.error(
                        f'Checksum validation failed after {max_retries + 1} attempts '
                        f'({checksum_mismatch_count} mismatch(es)): '
                        f'expected={last_expected_checksum}, '
                        f'computed={last_computed_checksum}'
                    )
                    raise ChecksumValidationError(
                        'Checksum validation failed — the downloaded data does not match '
                        'the expected hash. This could indicate data corruption or tampering. '
                        f'Expected: {last_expected_checksum}, Got: {last_computed_checksum}'
                    )

            # Parse NDJSON (one JSON object per line). Malformed lines are skipped
            # with a warning; the registry requires specific data attributes to be present.
            datasets = []
            invalid_count = 0
            total_lines = 0
            for line in content_bytes.decode('utf-8').strip().split('\n'):
                if not line:
                    continue
                total_lines += 1
                try:
                    dataset = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning(f'Skipping malformed JSON line: {exc}')
                    invalid_count += 1
                    continue

                # Skip deprecated datasets
                if dataset.get('Deprecated') is True:
                    continue

                datasets.append(dataset)

            if invalid_count:
                logger.warning(
                    f'{invalid_count} malformed line(s) skipped out of {total_lines} total'
                )

            # If a large fraction of lines are malformed, this likely signals an
            # upstream format change rather than a few harmless glitches.
            if total_lines > 0 and invalid_count / total_lines > 0.1:
                raise ValueError(
                    f'Registry data appears corrupt: {invalid_count}/{total_lines} lines '
                    f'({invalid_count * 100 // total_lines}%) failed to parse. '
                    'This may indicate an upstream format change.'
                )

            # Only cache if validation succeeded (or was skipped)
            _datasets_cache = datasets
            _cache_timestamp = datetime.now()

            # Build a fresh knowledge base and swap atomically so readers
            # never observe a partially-built index
            new_kb = DatasetKnowledgeBase()
            new_kb.build_indexes(datasets)
            _knowledge_base = new_kb

            return datasets


@mcp.tool()
async def search_datasets(
    query: str,
    tags: str | None = None,
    organization: str | None = None,
    license_type: str | None = None,
    limit: int = 10,
) -> str:
    """Search RODA datasets by keyword with optional filters.

    Combines free-text search with structured filtering. Use the query
    parameter for general searches, and add filters to narrow results.

    Args:
        query: Search term to find in dataset names, descriptions, or tags
        tags: Comma-separated tags to filter by (e.g., 'climate,genomics')
        organization: Organization name to filter by (e.g., 'NASA', 'NOAA')
        license_type: License type to filter by (e.g., 'creative commons', 'mit')
        limit: Maximum number of results to return (default: 10)

    Returns:
        JSON string with matching datasets including license information.

    Presentation Guidelines:
        - If total_count > returned_count, note that these are the top results and not the full list (e.g., "Showing {returned_count} of {total_count} matching datasets.").
        - Present results as a numbered list with each dataset showing name as the title.
        - For each dataset, include the following as bullet points: description, managed_by, and license.
        - Always mention the license field verbatim, as it's important for data usage compliance. Do not omit it.
        - If total_count > 10, ask a follow-up question to help narrow the search. Vary the question based on context — avoid repeating the same question asked earlier in the conversation. Examples: "To help narrow down the search, what's your specific use case?", "Are you looking for a specific region, time period, or data format?", "Do you have a preferred license type or organization in mind?"
    """
    datasets = await fetch_datasets()
    limit = max(1, min(limit, 20))
    query_lower = query.lower()

    # Split query into individual terms and filter out generic noise words
    IGNORED_TERMS = {'data', 'dataset', 'datasets'}
    query_terms = [term for term in query_lower.split() if term not in IGNORED_TERMS]
    if not query_terms:
        query_terms = [query_lower]

    # Parse optional comma-separated filters
    tag_list = [t.strip().lower() for t in tags.split(',')] if tags else None
    org_lower = organization.lower() if organization else None
    license_lower = license_type.lower() if license_type else None

    def matches_query(text: str) -> bool:
        return any(term in text for term in query_terms)

    def matches_filters(dataset: dict) -> bool:
        """Return True if dataset passes all active filters."""
        if tag_list:
            dataset_tags = [t.lower() for t in (dataset.get('Tags') or [])]
            if not any(ft in dataset_tags for ft in tag_list):
                return False
        if org_lower:
            if org_lower not in (dataset.get('ManagedBy') or '').lower():
                return False
        if license_lower:
            dataset_license = (dataset.get('License') or '').lower()
            if license_lower not in dataset_license:
                return False
        return True

    # Collect matches: must match query AND all active filters
    all_matches = []
    all_tags = []
    for dataset in datasets:
        name = (dataset.get('Name') or '').lower()
        description = (dataset.get('Description') or '').lower()
        dtags = [tag.lower() for tag in (dataset.get('Tags') or [])]

        if not (
            matches_query(name)
            or matches_query(description)
            or any(matches_query(tag) for tag in dtags)
        ):
            continue

        if not matches_filters(dataset):
            continue

        desc = dataset.get('Description') or ''
        all_matches.append(
            {
                'slug': dataset.get('Slug') or '',
                'name': dataset.get('Name') or '',
                'description': desc[:200] + '...' if len(desc) > 200 else desc,
                'tags': dataset.get('Tags') or [],
                'managed_by': dataset.get('ManagedBy') or '',
                'license': dataset.get('License') or 'Not specified',
            }
        )
        all_tags.extend(dataset.get('Tags') or [])

    total_count = len(all_matches)

    # Top 5 categories from matched results
    tag_counts = Counter(all_tags)
    top_categories = [tag for tag, count in tag_counts.most_common(5)]

    # Diversify results by provider — one result per unique provider first,
    # then fill remaining slots. Uses a set of slugs for O(1) dedup.
    results = []
    seen_slugs: set[str] = set()
    provider_counts: dict[str, int] = {}

    for match in all_matches:
        provider = match['managed_by']
        slug = match['slug']
        if provider not in provider_counts and slug not in seen_slugs:
            result_copy = {k: v for k, v in match.items() if k != 'tags'}
            results.append(result_copy)
            seen_slugs.add(slug)
            provider_counts[provider] = 1
            if len(results) >= limit:
                break

    if len(results) < limit:
        for match in all_matches:
            slug = match['slug']
            if slug not in seen_slugs:
                result_copy = {k: v for k, v in match.items() if k != 'tags'}
                results.append(result_copy)
                seen_slugs.add(slug)
                if len(results) >= limit:
                    break

    return json.dumps(
        {
            'status': 'ok',
            'query': query,
            'filters': {
                'tags': tag_list,
                'organization': organization,
                'license_type': license_type,
            }
            if any([tag_list, organization, license_type])
            else None,
            'total_count': total_count,
            'returned_count': len(results),
            'top_categories': top_categories,
            'results': results,
        },
        indent=2,
    )


@mcp.tool()
async def list_datasets(tag: str | None = None, limit: int = 20) -> str:
    """List RODA datasets with optional tag filtering.

    Args:
        tag: Optional tag to filter by (e.g., 'climate', 'genomics', 'satellite imagery')
        limit: Maximum number of results to return (default: 20)

    Returns:
        JSON string with dataset list

    Presentation Guidelines:
        - For each dataset listed, always display the license field verbatim. Do not omit it.
    """
    datasets = await fetch_datasets()
    limit = max(1, min(limit, 20))

    results = []
    for dataset in datasets:
        if tag:
            tags = [t.lower() for t in (dataset.get('Tags') or [])]
            if tag.lower() not in tags:
                continue

        desc = dataset.get('Description') or ''
        results.append(
            {
                'slug': dataset.get('Slug') or '',
                'name': dataset.get('Name') or '',
                'description': desc[:150] + '...' if len(desc) > 150 else desc,
                'tags': (dataset.get('Tags') or [])[:5],
                'managed_by': dataset.get('ManagedBy') or '',
                'license': dataset.get('License') or 'Not specified',
            }
        )

        if len(results) >= limit:
            break

    return json.dumps(
        {
            'status': 'ok',
            'total': len(datasets),
            'filtered': len(results),
            'tag_filter': tag,
            'datasets': results,
        },
        indent=2,
    )


@mcp.tool()
async def get_dataset_details(slug: str) -> str:
    """Get detailed information about a specific dataset.

    Args:
        slug: Dataset slug/identifier (e.g., 'nasa-nex')

    Returns:
        JSON string with complete dataset information including Resources section with access instructions.

    Presentation Guidelines:
        - Always display the license field verbatim. Do not omit it.
        - Check whether any of the dataset's Resources have a non-empty
          "ControlledAccess" field. If so, do NOT offer a preview option —
          instead inform the user that this dataset has controlled access and
          provide the ControlledAccess URL so they can request access directly.
        - Otherwise, after presenting dataset details, offer these choices:
          "Would you like to preview what's available, sample a file, or get access instructions?"
        - If user chooses "preview": Call preview_dataset.
        - If user chooses "instructions": Show the Resources section from the dataset JSON, which contains:
          * S3 bucket ARNs and regions
          * Access methods (STAC endpoints, APIs, etc.)
          * Any special access requirements
    """
    datasets = await fetch_datasets()

    for dataset in datasets:
        if (dataset.get('Slug') or '') == slug:
            return json.dumps({'status': 'ok', **dataset}, indent=2)

    return json.dumps(
        {
            'status': 'error',
            'error': f'Dataset not found: {slug}',
            'suggestion': 'Use search_datasets or list_datasets to find available datasets',
        },
        indent=2,
    )


@mcp.tool()
async def discover_by_organization(organization: str, limit: int = 10) -> str:
    """Discover datasets managed by a specific organization.

    Args:
        organization: Organization name or partial name (e.g., 'NASA', 'NOAA', 'NIH')
        limit: Maximum number of results to return (default: 10)

    Returns:
        JSON string with matching datasets
    """
    await fetch_datasets()  # Verify KB is built
    limit = max(1, min(limit, 20))

    results = _knowledge_base.search_by_organization(organization)[:limit]

    return json.dumps(
        {
            'status': 'ok',
            'organization': organization,
            'count': len(results),
            'datasets': [
                {
                    'slug': d.get('Slug') or '',
                    'name': d.get('Name') or '',
                    'description': (d.get('Description') or '')[:200] + '...'
                    if len(d.get('Description') or '') > 200
                    else (d.get('Description') or ''),
                    'managed_by': d.get('ManagedBy') or '',
                    'license': d.get('License') or 'Not specified',
                    'tags': (d.get('Tags') or [])[:5],
                }
                for d in results
            ],
        },
        indent=2,
    )


@mcp.tool()
async def discover_by_license(license_type: str, limit: int = 10) -> str:
    """Discover datasets by license type.

    Args:
        license_type: License type to search for. Supported values:
                      'creative commons', 'mit', 'apache', 'public domain'.
                      Other values will return zero results with a hint showing
                      the available license types.
        limit: Maximum number of results to return (default: 10)

    Returns:
        JSON string with matching datasets
    """
    await fetch_datasets()  # Verify KB is built
    limit = max(1, min(limit, 20))

    results = _knowledge_base.search_by_license(license_type)[:limit]

    if not results:
        return json.dumps(
            {
                'status': 'info',
                'license_type': license_type,
                'count': 0,
                'datasets': [],
                'hint': f'No datasets found for license type: {license_type!r}.',
                'supported_license_types': DatasetKnowledgeBase.SUPPORTED_LICENSE_TYPES,
            },
            indent=2,
        )

    return json.dumps(
        {
            'status': 'ok',
            'license_type': license_type,
            'count': len(results),
            'datasets': [
                {
                    'slug': d.get('Slug') or '',
                    'name': d.get('Name') or '',
                    'license': d.get('License') or '',
                    'managed_by': d.get('ManagedBy') or '',
                }
                for d in results
            ],
        },
        indent=2,
    )


@mcp.tool()
async def find_related_datasets(slug: str, limit: int = 5) -> str:
    """Find datasets related to a specific dataset based on shared tags.

    Args:
        slug: Dataset slug/identifier
        limit: Maximum number of related datasets to return (default: 5)

    Returns:
        JSON string with related datasets
    """
    await fetch_datasets()  # Verify KB is built
    limit = max(1, min(limit, 20))

    related = _knowledge_base.find_related_datasets(slug, limit)

    return json.dumps(
        {
            'status': 'ok',
            'source_dataset': slug,
            'count': len(related),
            'related_datasets': [
                {
                    'slug': d.get('Slug') or '',
                    'name': d.get('Name') or '',
                    'description': (d.get('Description') or '')[:150] + '...'
                    if len(d.get('Description') or '') > 150
                    else (d.get('Description') or ''),
                    'tags': (d.get('Tags') or [])[:5],
                    'managed_by': d.get('ManagedBy') or '',
                    'license': d.get('License') or 'Not specified',
                }
                for d in related
            ],
        },
        indent=2,
    )


@mcp.tool()
async def get_knowledge_base_stats() -> str:
    """Get statistics about the RODA knowledge base.

    Returns:
        JSON string with comprehensive statistics
    """
    await fetch_datasets()  # Verify KB is built

    stats = _knowledge_base.get_statistics()

    return json.dumps({'status': 'ok', **stats}, indent=2)


@mcp.tool()
async def preview_dataset(slug: str, bucket_arn: str | None = None) -> str:
    """Show the S3 bucket structure for a public dataset (no AWS account required).

    Returns up to 10 objects from the dataset's S3 bucket (in S3's default
    lexicographic key order). Note: these are NOT necessarily the most recent
    files — S3 lists keys alphabetically, not by modification time.
    Only works for datasets that are publicly accessible without credentials.
    No data is downloaded — this is a structure/inventory view only.

    If the dataset has more than one public S3 bucket, the tool returns a list
    of available buckets and asks the user to pick one. Pass the chosen ARN as
    bucket_arn to preview that specific bucket.

    Use sample_dataset to read the content of a specific file.

    Args:
        slug: Dataset slug/identifier (e.g., 'nasa-nex')
        bucket_arn: ARN of the specific bucket to preview (optional). Required
                    when the dataset has multiple public S3 buckets.

    Returns:
        JSON string with bucket structure: bucket name, region, prefix,
        up to 10 objects (key, size, last_modified) in lexicographic order,
        and ready-to-use CLI commands. The response always includes the license field.

    Presentation Guidelines:
        - Always display the license field verbatim. Do not omit it.
        - If the response contains "available_buckets", present them to the user
          and ask which one they'd like to preview. Then call this tool again with
          the chosen ARN as bucket_arn.
        - After presenting the bucket structure, offer to use sample_dataset
          to read the content of any listed file.
    """
    from awslabs.roda_mcp_server.aws_client import get_s3_client
    from botocore.exceptions import (
        ClientError,
        ConnectionClosedError,
        ConnectTimeoutError,
        EndpointConnectionError,
        ReadTimeoutError,
    )

    datasets = await fetch_datasets()
    dataset = next((d for d in datasets if (d.get('Slug') or '') == slug), None)
    if not dataset:
        return json.dumps(
            {
                'status': 'error',
                'error': f'Dataset not found: {slug}',
                'suggestion': 'Use search_datasets or list_datasets to find available datasets',
            },
            indent=2,
        )

    # Only surface public, non-requester-pays, non-controlled-access S3 buckets
    s3_resources = [
        r
        for r in dataset.get('Resources', [])
        if 's3 bucket' in (r.get('Type') or '').lower()
        and not r.get('RequesterPays', False)
        and not r.get('ControlledAccess')
    ]

    if not s3_resources:
        all_types = [r.get('Type', '') for r in dataset.get('Resources', [])]
        has_rp = any(
            's3 bucket' in (r.get('Type') or '').lower() and r.get('RequesterPays', False)
            for r in dataset.get('Resources', [])
        )
        controlled_urls = [
            r['ControlledAccess']
            for r in dataset.get('Resources', [])
            if r.get('ControlledAccess') and isinstance(r.get('ControlledAccess'), str)
        ]
        has_controlled_access = any(
            r.get('ControlledAccess') for r in dataset.get('Resources', [])
        )
        if has_controlled_access and not has_rp:
            msg = 'All S3 buckets for this dataset have controlled access.'
        elif has_rp:
            msg = (
                'This dataset uses requester-pays S3 buckets — '
                'use the AWS CLI with your credentials to access it.'
            )
        else:
            msg = 'No publicly accessible S3 bucket found for this dataset.'
        result = {
            'status': 'info',
            'dataset': dataset.get('Name') or '',
            'slug': slug,
            'message': msg,
            'available_resource_types': all_types,
        }
        if controlled_urls:
            result['access_request_url'] = controlled_urls[0]
        elif has_controlled_access:
            result['access_request_url'] = 'Contact the dataset provider for access instructions.'
        return json.dumps(result, indent=2)

    # If multiple buckets and none selected, ask the user to choose
    if len(s3_resources) > 1 and not bucket_arn:
        return json.dumps(
            {
                'status': 'info',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'message': (
                    f'This dataset has {len(s3_resources)} public S3 buckets. '
                    'Please choose one to preview.'
                ),
                'available_buckets': [
                    {
                        'arn': r.get('ARN', ''),
                        'region': r.get('Region', ''),
                        'description': r.get('Description', ''),
                    }
                    for r in s3_resources
                ],
            },
            indent=2,
        )

    # Resolve which bucket to use
    if bucket_arn:
        s3_resource = next(
            (r for r in s3_resources if r.get('ARN', '') == bucket_arn),
            None,
        )
        if not s3_resource:
            return json.dumps(
                {
                    'status': 'error',
                    'dataset': dataset.get('Name') or '',
                    'slug': slug,
                    'error': f'Bucket ARN not found among public buckets for this dataset: {bucket_arn}',
                    'available_arns': [r.get('ARN', '') for r in s3_resources],
                },
                indent=2,
            )
    else:
        s3_resource = s3_resources[0]

    arn = s3_resource.get('ARN', '')

    # Parse bucket name and optional prefix from ARN
    bucket_name = None
    prefix = ''
    if ':::' in arn:
        path = arn.split(':::')[1]
        parts = path.split('/', 1)
        bucket_name = parts[0]
        if len(parts) > 1 and parts[1]:
            prefix = parts[1].rstrip('/') + '/'

    if not bucket_name:
        return json.dumps(
            {
                'status': 'error',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'error': 'Could not parse S3 bucket name from ARN',
                'arn': arn,
            },
            indent=2,
        )

    # Anonymous LIST only — no data downloaded.
    try:
        s3 = get_s3_client(region=s3_resource.get('Region', 'us-east-1'))
        list_kwargs = {'Bucket': bucket_name, 'MaxKeys': 10}
        if prefix:
            list_kwargs['Prefix'] = prefix
        response = s3.list_objects_v2(**list_kwargs)

        if 'Contents' not in response:
            return json.dumps(
                {
                    'status': 'info',
                    'dataset': dataset.get('Name') or '',
                    'slug': slug,
                    'bucket': bucket_name,
                    'region': s3_resource.get('Region', 'us-east-1'),
                    'message': 'Bucket appears empty or access is restricted.',
                },
                indent=2,
            )

        objects = [
            {
                'key': obj['Key'],
                'size_bytes': obj['Size'],
                'last_modified': obj['LastModified'].isoformat(),
            }
            for obj in response['Contents']
        ]

        return json.dumps(
            {
                'status': 'ok',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'license': dataset.get('License') or '',
                'bucket': bucket_name,
                'region': s3_resource.get('Region', 'us-east-1'),
                'prefix': prefix or None,
                'truncated': response.get('IsTruncated', False),
                'object_count': len(objects),
                'objects': objects,
                'cli_commands': {
                    'list': f'aws s3 ls s3://{bucket_name}/{prefix} --no-sign-request',
                    'list_recursive': f'aws s3 ls s3://{bucket_name}/{prefix} --recursive --no-sign-request',
                },
            },
            indent=2,
        )

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'AccessDenied':
            return json.dumps(
                {
                    'status': 'error',
                    'dataset': dataset.get('Name') or '',
                    'slug': slug,
                    'error': 'Access denied — this dataset requires AWS credentials.',
                    'note': 'Use the AWS CLI with your own credentials to access this bucket (e.g., aws s3 ls s3://<bucket>).',
                    'dataset_contact': dataset.get('Contact', 'See dataset documentation'),
                },
                indent=2,
            )
        return json.dumps(
            {
                'status': 'error',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'error': f'AWS error: {error_code}',
                'message': str(e),
            },
            indent=2,
        )

    except (
        EndpointConnectionError,
        ConnectTimeoutError,
        ReadTimeoutError,
        ConnectionClosedError,
        OSError,
    ) as e:
        return json.dumps(
            {
                'status': 'error',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'error': 'Network error listing bucket',
                'message': str(e),
            },
            indent=2,
        )

    except Exception as e:
        logger.error(
            f'Unexpected error in preview_dataset: {type(e).__name__}: {e} '
            f'(slug={slug}, bucket={bucket_name}, region={s3_resource.get("Region", "us-east-1")}, prefix={prefix!r})'
        )
        return json.dumps(
            {
                'status': 'error',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'error': f'Unexpected error listing bucket: {type(e).__name__}',
                'message': str(e),
            },
            indent=2,
        )


@mcp.tool()
async def sample_dataset(slug: str, file_key: str, bucket_arn: str | None = None) -> str:
    """Read a sample of a specific file from a public dataset's S3 bucket.

    Downloads up to 100KB of raw bytes using anonymous access (no AWS account
    required). For text files, the displayed content is further capped at
    2000 characters to keep responses concise.

    Use preview_dataset first to discover available file keys.
    Only works for datasets that are publicly accessible without credentials.

    Args:
        slug: Dataset slug/identifier (e.g., 'nasa-nex')
        file_key: S3 object key to sample (e.g., 'data/2020/file.csv').
                  Obtain this from preview_dataset output.
        bucket_arn: ARN of the specific bucket to sample from. Required when
                    the dataset has multiple public S3 buckets — use the same
                    ARN the user selected in preview_dataset.

    Returns:
        JSON string with:
        - file content (text, capped at 2000 chars) or a binary notice
        - file_size_bytes: total file size on S3
        - bytes_read: how many bytes were downloaded (up to 100KB)
        - is_partial: True if file_size exceeds 100KB OR text was truncated
        - content_truncated: True if text display was capped at 2000 chars
        - a CLI command to download the complete file
        - the license field

    Presentation Guidelines:
        - Always display the license field verbatim. Do not omit it.
    """
    max_bytes = 102400  # Fixed 100KB download

    from awslabs.roda_mcp_server.aws_client import get_s3_client
    from botocore.exceptions import (
        ClientError,
        ConnectionClosedError,
        ConnectTimeoutError,
        EndpointConnectionError,
        ReadTimeoutError,
    )

    datasets = await fetch_datasets()
    dataset = next((d for d in datasets if (d.get('Slug') or '') == slug), None)
    if not dataset:
        return json.dumps(
            {
                'status': 'error',
                'error': f'Dataset not found: {slug}',
                'suggestion': 'Use search_datasets or list_datasets to find available datasets',
            },
            indent=2,
        )

    # Only surface public, non-requester-pays, non-controlled-access S3 buckets
    s3_resources = [
        r
        for r in dataset.get('Resources', [])
        if 's3 bucket' in (r.get('Type') or '').lower()
        and not r.get('RequesterPays', False)
        and not r.get('ControlledAccess')
    ]

    if not s3_resources:
        return json.dumps(
            {
                'status': 'info',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'error': 'No publicly accessible S3 bucket found for this dataset.',
            },
            indent=2,
        )

    # If multiple buckets and none selected, ask the user to choose (consistent
    # with preview_dataset behavior to avoid sampling the wrong bucket)
    if len(s3_resources) > 1 and not bucket_arn:
        return json.dumps(
            {
                'status': 'info',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'message': (
                    f'This dataset has {len(s3_resources)} public S3 buckets. '
                    'Please specify bucket_arn to indicate which bucket to sample from.'
                ),
                'available_buckets': [
                    {
                        'arn': r.get('ARN', ''),
                        'region': r.get('Region', ''),
                        'description': r.get('Description', ''),
                    }
                    for r in s3_resources
                ],
            },
            indent=2,
        )

    # Use the user-specified bucket if provided, otherwise use the single available one
    if bucket_arn:
        s3_resource = next(
            (r for r in s3_resources if r.get('ARN', '') == bucket_arn),
            None,
        )
        if not s3_resource:
            return json.dumps(
                {
                    'status': 'error',
                    'dataset': dataset.get('Name') or '',
                    'slug': slug,
                    'error': f'Bucket ARN not found among public buckets for this dataset: {bucket_arn}',
                    'available_arns': [r.get('ARN', '') for r in s3_resources],
                },
                indent=2,
            )
    else:
        s3_resource = s3_resources[0]

    arn = s3_resource.get('ARN', '')

    bucket_name = None
    if ':::' in arn:
        bucket_name = arn.split(':::')[1].split('/')[0]

    if not bucket_name:
        return json.dumps(
            {
                'status': 'error',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'error': 'Could not parse S3 bucket name from ARN',
                'arn': arn,
            },
            indent=2,
        )

    try:
        s3 = get_s3_client(region=s3_resource.get('Region', 'us-east-1'))
        # HEAD first to get file size without downloading
        head = s3.head_object(Bucket=bucket_name, Key=file_key)
        file_size = head['ContentLength']

        if file_size == 0:
            return json.dumps(
                {
                    'status': 'info',
                    'dataset': dataset.get('Name') or '',
                    'slug': slug,
                    'license': dataset.get('License') or '',
                    'bucket': bucket_name,
                    'file_key': file_key,
                    'file_size_bytes': 0,
                    'message': 'File is empty (0 bytes).',
                },
                indent=2,
            )

        bytes_to_read = min(file_size, max_bytes)
        obj = s3.get_object(
            Bucket=bucket_name,
            Key=file_key,
            Range=f'bytes=0-{bytes_to_read - 1}',
        )
        content = obj['Body'].read()
        is_partial = file_size > max_bytes

        try:
            # Byte-range reads can split a multibyte UTF-8 character at the boundary.
            # Strip up to 3 trailing bytes (max continuation bytes in UTF-8) to avoid
            # mislabeling valid text files as binary.
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            # Trim trailing incomplete multibyte sequence and retry
            for trim in range(1, 4):
                try:
                    text = content[:-trim].decode('utf-8')
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # Genuinely binary content
                content_truncated = False
                content_result = {
                    'encoding': 'binary',
                    'content': '[Binary file — cannot display as text]',
                    'content_truncated': False,
                    'note': 'Use the CLI command below to download the full file.',
                }
                return json.dumps(
                    {
                        'status': 'ok',
                        'dataset': dataset.get('Name') or '',
                        'slug': slug,
                        'license': dataset.get('License') or '',
                        'bucket': bucket_name,
                        'file_key': file_key,
                        'file_size_bytes': file_size,
                        'bytes_read': len(content),
                        'is_partial': is_partial,
                        **content_result,
                        'cli_command': (
                            f'aws s3 cp s3://{bucket_name}/{file_key} . --no-sign-request'
                        ),
                    },
                    indent=2,
                )

        content_truncated = len(text) > 2000
        if content_truncated:
            # Truncate at the last complete line before the limit
            cut = text[:2000].rfind('\n')
            if cut > 0:
                text = text[:cut]
            else:
                # No newline found (single long line) — hard cut
                text = text[:2000]
            text += '\n... (truncated for display)'
        content_result = {
            'encoding': 'utf-8',
            'content': text,
            'content_truncated': content_truncated,
        }

        return json.dumps(
            {
                'status': 'ok',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'license': dataset.get('License') or '',
                'bucket': bucket_name,
                'file_key': file_key,
                'file_size_bytes': file_size,
                'bytes_read': len(content),
                'is_partial': is_partial or content_truncated,
                **content_result,
                'cli_command': (f'aws s3 cp s3://{bucket_name}/{file_key} . --no-sign-request'),
            },
            indent=2,
        )

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code in ('AccessDenied', 'NoSuchKey'):
            return json.dumps(
                {
                    'status': 'error',
                    'dataset': dataset.get('Name') or '',
                    'slug': slug,
                    'error': (
                        'File not found.'
                        if error_code == 'NoSuchKey'
                        else 'Access denied — this file requires AWS credentials.'
                    ),
                    'file_key': file_key,
                },
                indent=2,
            )
        return json.dumps(
            {
                'status': 'error',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'error': f'AWS error: {error_code}',
                'message': str(e),
            },
            indent=2,
        )

    except (
        EndpointConnectionError,
        ConnectTimeoutError,
        ReadTimeoutError,
        ConnectionClosedError,
        OSError,
    ) as e:
        return json.dumps(
            {
                'status': 'error',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'error': 'Network error reading file',
                'file_key': file_key,
                'message': str(e),
            },
            indent=2,
        )

    except Exception as e:
        logger.error(
            f'Unexpected error in sample_dataset: {type(e).__name__}: {e} '
            f'(slug={slug}, bucket={bucket_name}, file_key={file_key!r})'
        )
        return json.dumps(
            {
                'status': 'error',
                'dataset': dataset.get('Name') or '',
                'slug': slug,
                'error': f'Unexpected error reading file: {type(e).__name__}',
                'message': str(e),
            },
            indent=2,
        )


@mcp.tool()
async def search_stac_endpoints(query: str | None = None, limit: int = 20) -> str:
    """Search for STAC (SpatioTemporal Asset Catalog) endpoints across all datasets.

    Scans dataset Resources (Explore links, descriptions), DataAtWork
    (Tools & Applications, Tutorials), and Tags to find STAC API endpoints
    and catalogs.

    Args:
        query: Optional keyword to filter results (e.g., 'sentinel', 'landsat').
               When omitted, returns all datasets with STAC endpoints.
        limit: Maximum number of datasets to return (default: 20)

    Returns:
        JSON string with datasets and their discovered STAC endpoints
    """
    datasets = await fetch_datasets()
    limit = max(1, min(limit, 20))

    url_re = re.compile(r'https?://[^\s\)\]>"]+')
    stac_kw = re.compile(r'stac', re.IGNORECASE)

    results: list[dict[str, Any]] = []

    for dataset in datasets:
        endpoints: list[dict[str, str]] = []

        # 1. Resources -> Explore links & descriptions
        for resource in dataset.get('Resources', []) or []:
            for explore in resource.get('Explore', []) or []:
                if stac_kw.search(explore):
                    for url in url_re.findall(explore):
                        endpoints.append({'url': url, 'source': 'Resource Explore'})
            desc = resource.get('Description', '') or ''
            if stac_kw.search(desc):
                for url in url_re.findall(desc):
                    endpoints.append({'url': url, 'source': 'Resource Description'})

        # 2. DataAtWork -> Tools & Applications / Tutorials
        data_at_work = dataset.get('DataAtWork', {}) or {}
        for section_key in ('Tools & Applications', 'Tutorials'):
            for item in data_at_work.get(section_key, []) or []:
                title = item.get('Title', '') or ''
                url = item.get('URL', '') or ''
                if stac_kw.search(title) or stac_kw.search(url):
                    if url:
                        endpoints.append(
                            {
                                'url': url,
                                'title': title,
                                'source': f'DataAtWork/{section_key}',
                            }
                        )

        # 3. Tags containing "stac"
        has_stac_tag = any(stac_kw.search(t) for t in (dataset.get('Tags', []) or []))

        if not endpoints and not has_stac_tag:
            continue

        # Optional keyword filter
        if query:
            q = query.lower()
            name = (dataset.get('Name') or '').lower()
            description = (dataset.get('Description') or '').lower()
            tags = [t.lower() for t in (dataset.get('Tags', []) or [])]
            if not (q in name or q in description or any(q in t for t in tags)):
                continue

        # Deduplicate endpoints by URL
        seen: set[str] = set()
        unique: list[dict[str, str]] = []
        for ep in endpoints:
            if ep['url'] not in seen:
                seen.add(ep['url'])
                unique.append(ep)

        results.append(
            {
                'slug': dataset.get('Slug') or '',
                'name': dataset.get('Name') or '',
                'managed_by': dataset.get('ManagedBy') or '',
                'has_stac_tag': has_stac_tag,
                'stac_endpoints': unique,
            }
        )

        if len(results) >= limit:
            break

    return json.dumps(
        {
            'status': 'ok',
            'query': query,
            'count': len(results),
            'results': results,
        },
        indent=2,
    )


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
