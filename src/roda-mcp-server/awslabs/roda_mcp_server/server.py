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
import re
from awslabs.roda_mcp_server.knowledge_base import DatasetKnowledgeBase
from datetime import datetime, timedelta
from fastmcp import FastMCP
from typing import Any


# Initialize FastMCP server
mcp = FastMCP('roda-mcp')

# Data source URL - NDJSON file with all datasets pre-parsed
REGISTRY_NDJSON_URL = 'https://registry.opendata.aws/index.ndjson'
REGISTRY_CHECKSUM_URL = 'https://registry.opendata.aws/index.ndjson.sha256'

# Cache for datasets with expiration
_datasets_cache: list[dict[str, Any]] | None = None
_cache_timestamp: datetime | None = None
CACHE_EXPIRY_HOURS = 24

# Knowledge base instance
_knowledge_base = DatasetKnowledgeBase()


class ChecksumValidationError(Exception):
    """Raised when checksum validation fails.

    Checksum validation prevents man-in-the-middle attacks and data corruption.
    This control helps detection of tampered or corrupted downloads.
    """

    pass


async def fetch_datasets() -> list[dict[str, Any]]:
    """Fetch and cache datasets from RODA.

    Uses the official NDJSON index file which contains all datasets pre-parsed.
    """
    global _datasets_cache, _cache_timestamp

    # Check if cache is valid
    if _datasets_cache is not None and _cache_timestamp is not None:
        if datetime.now() - _cache_timestamp < timedelta(hours=CACHE_EXPIRY_HOURS):
            return _datasets_cache

    async with httpx.AsyncClient(verify=True, http2=True) as client:
        # Fetch the NDJSON file with all datasets
        # All external API calls require TLS 1.2 or higher with certificate validation enabled
        # Retry up to 2 times to handle brief CDN propagation delays
        max_retries = 2
        content_bytes = None
        for attempt in range(max_retries + 1):
            response = await client.get(REGISTRY_NDJSON_URL, timeout=30.0)
            response.raise_for_status()
            content_bytes = response.content

            # Fetch and validate checksum
            checksum_response = await client.get(REGISTRY_CHECKSUM_URL, timeout=10.0)
            checksum_response.raise_for_status()
            expected_checksum = checksum_response.text.strip().split()[0].lower()

            computed_checksum = hashlib.sha256(content_bytes).hexdigest().lower()
            if computed_checksum == expected_checksum:
                break

            if attempt < max_retries:
                await asyncio.sleep(3)
        else:
            raise ChecksumValidationError(
                'Unable to verify this dataset. '
                'This can happen during a brief window when the registry is updating. '
                'Please try again in a few minutes.'
            )

        # Parse NDJSON (one JSON object per line). Malformed lines are skipped
        # with a warning; the registry requires specific data attributes to be present.
        datasets = []
        invalid_count = 0
        for line in content_bytes.decode('utf-8').strip().split('\n'):
            if not line:
                continue
            try:
                dataset = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f'Warning: skipping malformed JSON line: {exc}')
                invalid_count += 1
                continue

            # Skip deprecated datasets
            if dataset.get('Deprecated') is True:
                continue

            datasets.append(dataset)

        if invalid_count:
            print(f'Warning: {invalid_count} malformed line(s) skipped')

        # Only cache if validation succeeded (or was skipped)
        _datasets_cache = datasets
        _cache_timestamp = datetime.now()

        # Build knowledge base indexes
        _knowledge_base.build_indexes(datasets)

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
            dataset_tags = [t.lower() for t in dataset.get('Tags', [])]
            if not any(ft in dataset_tags for ft in tag_list):
                return False
        if org_lower:
            if org_lower not in dataset.get('ManagedBy', '').lower():
                return False
        if license_lower:
            dataset_license = dataset.get('License', '').lower()
            if license_lower not in dataset_license:
                return False
        return True

    # Collect matches: must match query AND all active filters
    all_matches = []
    all_tags = []
    for dataset in datasets:
        name = dataset.get('Name', '').lower()
        description = dataset.get('Description', '').lower()
        dtags = [tag.lower() for tag in dataset.get('Tags', [])]

        if not (
            matches_query(name)
            or matches_query(description)
            or any(matches_query(tag) for tag in dtags)
        ):
            continue

        if not matches_filters(dataset):
            continue

        all_matches.append(
            {
                'slug': dataset.get('Slug', ''),
                'name': dataset.get('Name', ''),
                'description': dataset.get('Description', '')[:200] + '...'
                if len(dataset.get('Description', '')) > 200
                else dataset.get('Description', ''),
                'tags': dataset.get('Tags', []),
                'managed_by': dataset.get('ManagedBy', ''),
                'license': dataset.get('License', 'Not specified'),
            }
        )
        all_tags.extend(dataset.get('Tags', []))

    total_count = len(all_matches)

    # Top 5 categories from matched results
    from collections import Counter

    tag_counts = Counter(all_tags)
    top_categories = [tag for tag, count in tag_counts.most_common(5)]

    # Diversify results by provider
    results = []
    provider_counts = {}

    for match in all_matches:
        provider = match['managed_by']
        if provider not in provider_counts:
            result_copy = {k: v for k, v in match.items() if k != 'tags'}
            results.append(result_copy)
            provider_counts[provider] = 1
            if len(results) >= limit:
                break

    if len(results) < limit:
        for match in all_matches:
            result_copy = {k: v for k, v in match.items() if k != 'tags'}
            if result_copy not in results:
                results.append(result_copy)
                if len(results) >= limit:
                    break

    return json.dumps(
        {
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
        limit: Maximum number of results to return (default: 10)

    Returns:
        JSON string with dataset list

    Presentation Guidelines:
        - For each dataset listed, always display the license field verbatim. Do not omit it.
    """
    datasets = await fetch_datasets()

    results = []
    for dataset in datasets:
        if tag:
            tags = [t.lower() for t in dataset.get('Tags', [])]
            if tag.lower() not in tags:
                continue

        results.append(
            {
                'slug': dataset.get('Slug', ''),
                'name': dataset.get('Name', ''),
                'description': dataset.get('Description', '')[:150] + '...'
                if len(dataset.get('Description', '')) > 150
                else dataset.get('Description', ''),
                'tags': dataset.get('Tags', [])[:5],
                'managed_by': dataset.get('ManagedBy', ''),
                'license': dataset.get('License', 'Not specified'),
            }
        )

        if len(results) >= limit:
            break

    return json.dumps(
        {'total': len(datasets), 'filtered': len(results), 'tag_filter': tag, 'datasets': results},
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
        if dataset.get('Slug', '') == slug:
            return json.dumps(dataset, indent=2)

    return json.dumps(
        {
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

    results = _knowledge_base.search_by_organization(organization)[:limit]

    return json.dumps(
        {
            'organization': organization,
            'count': len(results),
            'datasets': [
                {
                    'slug': d.get('Slug', ''),
                    'name': d.get('Name', ''),
                    'description': d.get('Description', '')[:200] + '...'
                    if len(d.get('Description', '')) > 200
                    else d.get('Description', ''),
                    'managed_by': d.get('ManagedBy', ''),
                    'license': d.get('License', 'Not specified'),
                    'tags': d.get('Tags', [])[:5],
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
        license_type: License type (e.g., 'creative commons', 'mit', 'apache', 'public domain')
        limit: Maximum number of results to return (default: 10)

    Returns:
        JSON string with matching datasets
    """
    await fetch_datasets()  # Verify KB is built

    results = _knowledge_base.search_by_license(license_type)[:limit]

    return json.dumps(
        {
            'license_type': license_type,
            'count': len(results),
            'datasets': [
                {
                    'slug': d.get('Slug', ''),
                    'name': d.get('Name', ''),
                    'license': d.get('License', ''),
                    'managed_by': d.get('ManagedBy', ''),
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

    related = _knowledge_base.find_related_datasets(slug, limit)

    return json.dumps(
        {
            'source_dataset': slug,
            'count': len(related),
            'related_datasets': [
                {
                    'slug': d.get('Slug', ''),
                    'name': d.get('Name', ''),
                    'description': d.get('Description', '')[:150] + '...'
                    if len(d.get('Description', '')) > 150
                    else d.get('Description', ''),
                    'tags': d.get('Tags', [])[:5],
                    'managed_by': d.get('ManagedBy', ''),
                    'license': d.get('License', 'Not specified'),
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

    return json.dumps(stats, indent=2)


@mcp.tool()
async def preview_dataset(slug: str, bucket_arn: str | None = None) -> str:
    """Show the S3 bucket structure for a public dataset (no AWS account required).

    Lists the first 10 files in the dataset's S3 bucket using anonymous access.
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
        the first 10 objects (key, size, last_modified), and ready-to-use
        CLI commands. The response always includes the license field.

    Presentation Guidelines:
        - Always display the license field verbatim. Do not omit it.
        - If the response contains "available_buckets", present them to the user
          and ask which one they'd like to preview. Then call this tool again with
          the chosen ARN as bucket_arn.
        - After presenting the bucket structure, offer to use sample_dataset
          to read the content of any listed file.
    """
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    from botocore.exceptions import ClientError

    datasets = await fetch_datasets()
    dataset = next((d for d in datasets if d.get('Slug', '') == slug), None)
    if not dataset:
        return json.dumps(
            {
                'error': f'Dataset not found: {slug}',
                'suggestion': 'Use search_datasets or list_datasets to find available datasets',
            },
            indent=2,
        )

    # Only surface public, non-requester-pays, non-controlled-access S3 buckets
    s3_resources = [
        r
        for r in dataset.get('Resources', [])
        if 's3 bucket' in r.get('Type', '').lower()
        and not r.get('RequesterPays', False)
        and not r.get('ControlledAccess')
    ]

    if not s3_resources:
        all_types = [r.get('Type', '') for r in dataset.get('Resources', [])]
        has_rp = any(
            's3 bucket' in r.get('Type', '').lower() and r.get('RequesterPays', False)
            for r in dataset.get('Resources', [])
        )
        controlled_urls = [
            r['ControlledAccess']
            for r in dataset.get('Resources', [])
            if r.get('ControlledAccess')
        ]
        if controlled_urls and not has_rp:
            msg = 'All S3 buckets for this dataset have controlled access.'
        elif has_rp:
            msg = (
                'This dataset uses requester-pays S3 buckets — '
                'use the AWS CLI with your credentials to access it.'
            )
        else:
            msg = 'No publicly accessible S3 bucket found for this dataset.'
        result = {
            'dataset': dataset.get('Name', ''),
            'slug': slug,
            'message': msg,
            'available_resource_types': all_types,
        }
        if controlled_urls:
            result['access_request_url'] = controlled_urls[0]
        return json.dumps(result, indent=2)

    # If multiple buckets and none selected, ask the user to choose
    if len(s3_resources) > 1 and not bucket_arn:
        return json.dumps(
            {
                'dataset': dataset.get('Name', ''),
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
                    'dataset': dataset.get('Name', ''),
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
                'dataset': dataset.get('Name', ''),
                'slug': slug,
                'error': 'Could not parse S3 bucket name from ARN',
                'arn': arn,
            },
            indent=2,
        )

    # Anonymous LIST only — no data downloaded.
    try:
        s3 = boto3.client(
            's3',
            config=Config(signature_version=UNSIGNED, s3={'use_ssl': True}),
            region_name=s3_resource.get('Region', 'us-east-1'),
            verify=True,
        )
        list_kwargs = {'Bucket': bucket_name, 'MaxKeys': 10}
        if prefix:
            list_kwargs['Prefix'] = prefix
        response = s3.list_objects_v2(**list_kwargs)

        if 'Contents' not in response:
            return json.dumps(
                {
                    'dataset': dataset.get('Name', ''),
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
            for obj in sorted(
                response['Contents'],
                key=lambda obj: obj['LastModified'],
                reverse=True,
            )
        ]

        return json.dumps(
            {
                'dataset': dataset.get('Name', ''),
                'slug': slug,
                'license': dataset.get('License', ''),
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
                    'dataset': dataset.get('Name', ''),
                    'slug': slug,
                    'error': 'Access denied — this dataset requires AWS credentials.',
                    'note': 'Use sample_dataset with your credentials, or contact the dataset provider.',
                    'dataset_contact': dataset.get('Contact', 'See dataset documentation'),
                },
                indent=2,
            )
        return json.dumps(
            {
                'dataset': dataset.get('Name', ''),
                'slug': slug,
                'error': f'AWS error: {error_code}',
                'message': str(e),
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {
                'dataset': dataset.get('Name', ''),
                'slug': slug,
                'error': 'Unexpected error listing bucket',
                'message': str(e),
            },
            indent=2,
        )


@mcp.tool()
async def sample_dataset(slug: str, file_key: str, bucket_arn: str | None = None) -> str:
    """Read the first 100KB of a specific file from a public dataset's S3 bucket.

    Downloads a byte-range of a single file using anonymous access (no AWS
    account required). Use preview_dataset first to discover available file keys.

    Only works for datasets that are publicly accessible without credentials.

    Args:
        slug: Dataset slug/identifier (e.g., 'nasa-nex')
        file_key: S3 object key to sample (e.g., 'data/2020/file.csv').
                  Obtain this from preview_dataset output.
        bucket_arn: ARN of the specific bucket to sample from. Required when
                    the dataset has multiple public S3 buckets — use the same
                    ARN the user selected in preview_dataset.

    Returns:
        JSON string with file content (text) or a binary notice, plus the
        full file size, a CLI command to download the complete file, and
        the license field.

    Presentation Guidelines:
        - Always display the license field verbatim. Do not omit it.
    """
    max_bytes = 102400  # Fixed 100KB download

    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    from botocore.exceptions import ClientError

    datasets = await fetch_datasets()
    dataset = next((d for d in datasets if d.get('Slug', '') == slug), None)
    if not dataset:
        return json.dumps(
            {
                'error': f'Dataset not found: {slug}',
                'suggestion': 'Use search_datasets or list_datasets to find available datasets',
            },
            indent=2,
        )

    # Only surface public, non-requester-pays, non-controlled-access S3 buckets
    s3_resources = [
        r
        for r in dataset.get('Resources', [])
        if 's3 bucket' in r.get('Type', '').lower()
        and not r.get('RequesterPays', False)
        and not r.get('ControlledAccess')
    ]

    if not s3_resources:
        return json.dumps(
            {
                'dataset': dataset.get('Name', ''),
                'slug': slug,
                'error': 'No publicly accessible S3 bucket found for this dataset.',
            },
            indent=2,
        )

    # Use the user-specified bucket if provided, otherwise default to first
    if bucket_arn:
        s3_resource = next(
            (r for r in s3_resources if r.get('ARN', '') == bucket_arn),
            None,
        )
        if not s3_resource:
            return json.dumps(
                {
                    'dataset': dataset.get('Name', ''),
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
                'dataset': dataset.get('Name', ''),
                'slug': slug,
                'error': 'Could not parse S3 bucket name from ARN',
                'arn': arn,
            },
            indent=2,
        )

    try:
        s3 = boto3.client(
            's3',
            config=Config(signature_version=UNSIGNED, s3={'use_ssl': True}),
            region_name=s3_resource.get('Region', 'us-east-1'),
            verify=True,
        )
        # HEAD first to get file size without downloading
        head = s3.head_object(Bucket=bucket_name, Key=file_key)
        file_size = head['ContentLength']

        bytes_to_read = min(file_size, max_bytes)
        obj = s3.get_object(
            Bucket=bucket_name,
            Key=file_key,
            Range=f'bytes=0-{bytes_to_read - 1}',
        )
        content = obj['Body'].read()
        is_partial = file_size > max_bytes

        try:
            text = content.decode('utf-8')
            if len(text) > 2000:
                text = text[:2000] + '\n... (truncated at 2000 chars)'
            content_result = {
                'encoding': 'utf-8',
                'content': text,
            }
        except UnicodeDecodeError:
            content_result = {
                'encoding': 'binary',
                'content': '[Binary file — cannot display as text]',
                'note': 'Use the CLI command below to download the full file.',
            }

        return json.dumps(
            {
                'dataset': dataset.get('Name', ''),
                'slug': slug,
                'license': dataset.get('License', ''),
                'bucket': bucket_name,
                'file_key': file_key,
                'file_size_bytes': file_size,
                'bytes_read': len(content),
                'is_partial': is_partial,
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
                    'dataset': dataset.get('Name', ''),
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
                'dataset': dataset.get('Name', ''),
                'slug': slug,
                'error': f'AWS error: {error_code}',
                'message': str(e),
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {
                'dataset': dataset.get('Name', ''),
                'slug': slug,
                'error': 'Unexpected error reading file',
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
    limit = max(1, min(limit, 100))

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
                'slug': dataset.get('Slug', ''),
                'name': dataset.get('Name', ''),
                'managed_by': dataset.get('ManagedBy', ''),
                'has_stac_tag': has_stac_tag,
                'stac_endpoints': unique,
            }
        )

        if len(results) >= limit:
            break

    return json.dumps(
        {
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
