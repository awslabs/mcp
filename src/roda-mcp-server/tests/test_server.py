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

"""Tests for additional server.py coverage.

Covers: fetch_datasets malformed-line and deprecated-dataset filtering,
search_datasets diversification and ignored terms,
discover_by_organization, discover_by_license, find_related_datasets,
get_knowledge_base_stats, search_stac_endpoints, preview_dataset
edge cases, and sample_dataset error paths.

Run: uv run python -m pytest tests/test_server.py -v
"""

import awslabs.roda_mcp_server.server as server_module
import json
import pytest
from awslabs.roda_mcp_server.server import (
    discover_by_license,
    discover_by_organization,
    fetch_datasets,
    find_related_datasets,
    get_knowledge_base_stats,
    preview_dataset,
    sample_dataset,
    search_datasets,
    search_stac_endpoints,
)
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# fetch_datasets tests
# ---------------------------------------------------------------------------


class TestFetchDatasets:
    """Tests for fetch_datasets parsing logic not covered by test_checksum_validation."""

    async def test_malformed_json_lines_skipped(self):
        """Malformed JSON lines are skipped with a warning when under the threshold."""
        import hashlib

        # 10 good lines + 1 bad line = ~9% malformed (under 10% threshold)
        lines = [f'{{"Slug":"ds-{i}","Name":"Dataset {i}","Tags":[]}}' for i in range(10)]
        lines.append('not-json')
        content = ('\n'.join(lines) + '\n').encode('utf-8')
        checksum = hashlib.sha256(content).hexdigest()

        mock_response = MagicMock()
        mock_response.content = content
        mock_response.raise_for_status = MagicMock()

        mock_checksum_response = MagicMock()
        mock_checksum_response.text = f'{checksum}  file.ndjson'
        mock_checksum_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_response, mock_checksum_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await fetch_datasets()

        assert len(result) == 10
        assert result[0]['Slug'] == 'ds-0'

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

    async def test_high_malformed_ratio_raises(self):
        """When >10% of lines are malformed, raises ValueError signaling format change."""
        import hashlib

        # 1 good line + 2 bad lines = 67% malformed (over 10% threshold)
        content = b'{"Slug":"good","Name":"Good","Tags":[]}\nnot-json-1\nnot-json-2\n'
        checksum = hashlib.sha256(content).hexdigest()

        mock_response = MagicMock()
        mock_response.content = content
        mock_response.raise_for_status = MagicMock()

        mock_checksum_response = MagicMock()
        mock_checksum_response.text = f'{checksum}  file.ndjson'
        mock_checksum_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_response, mock_checksum_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(ValueError, match='corrupt'):
                await fetch_datasets()

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

    async def test_deprecated_datasets_skipped(self):
        """Deprecated datasets are filtered out."""
        import hashlib

        content = (
            b'{"Slug":"active","Name":"Active","Tags":[]}\n'
            b'{"Slug":"old","Name":"Old","Tags":[],"Deprecated":true}\n'
        )
        checksum = hashlib.sha256(content).hexdigest()

        mock_response = MagicMock()
        mock_response.content = content
        mock_response.raise_for_status = MagicMock()

        mock_checksum_response = MagicMock()
        mock_checksum_response.text = f'{checksum}  file.ndjson'
        mock_checksum_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_response, mock_checksum_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await fetch_datasets()

        assert len(result) == 1
        assert result[0]['Slug'] == 'active'

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

    async def test_cache_hit_returns_cached_data(self):
        """Second call within cache TTL returns cached data without network call."""
        import hashlib

        content = b'{"Slug":"cached","Name":"Cached Dataset","Tags":[]}\n'
        checksum = hashlib.sha256(content).hexdigest()

        mock_response = MagicMock()
        mock_response.content = content
        mock_response.raise_for_status = MagicMock()

        mock_checksum_response = MagicMock()
        mock_checksum_response.text = f'{checksum}  file.ndjson'
        mock_checksum_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_response, mock_checksum_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

        with patch('httpx.AsyncClient', return_value=mock_client):
            # First call — fetches from network
            result1 = await fetch_datasets()
            # Second call — should use cache, no additional network call
            result2 = await fetch_datasets()

        assert result1 == result2
        assert len(result1) == 1
        assert result1[0]['Slug'] == 'cached'
        # Only 2 get() calls total (ndjson + checksum), not 4
        assert mock_client.get.call_count == 2

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

    async def test_empty_checksum_response_raises(self):
        """Empty or whitespace-only checksum body raises ChecksumValidationError."""
        from awslabs.roda_mcp_server.server import ChecksumValidationError

        content = b'{"Slug":"test","Name":"Test","Tags":[]}\n'

        mock_response = MagicMock()
        mock_response.content = content
        mock_response.raise_for_status = MagicMock()

        mock_checksum_response = MagicMock()
        mock_checksum_response.text = '   \n'  # whitespace-only
        mock_checksum_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_response, mock_checksum_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(ChecksumValidationError, match='empty'):
                await fetch_datasets()

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

    async def test_network_error_retried_then_succeeds(self):
        """Transient network error on first attempt is retried and succeeds."""
        import hashlib
        import httpx

        content = b'{"Slug":"retry-ok","Name":"Retry OK","Tags":[]}\n'
        checksum = hashlib.sha256(content).hexdigest()

        mock_response = MagicMock()
        mock_response.content = content
        mock_response.raise_for_status = MagicMock()

        mock_checksum_response = MagicMock()
        mock_checksum_response.text = f'{checksum}  file.ndjson'
        mock_checksum_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        # First attempt: timeout on ndjson fetch. Second attempt: success.
        mock_client.get = AsyncMock(
            side_effect=[
                httpx.TimeoutException('timed out'),  # attempt 1 fails
                mock_response,
                mock_checksum_response,  # attempt 2 succeeds
            ]
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

        with patch('httpx.AsyncClient', return_value=mock_client):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await fetch_datasets()

        assert len(result) == 1
        assert result[0]['Slug'] == 'retry-ok'

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

    async def test_concurrent_fetch_only_downloads_once(self):
        """Multiple concurrent cold calls share a single download via asyncio.Lock."""
        import asyncio
        import hashlib

        content = b'{"Slug":"concurrent","Name":"Concurrent Test","Tags":[]}\n'
        checksum = hashlib.sha256(content).hexdigest()

        call_count = 0

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            # Simulate network latency so concurrent calls overlap
            await asyncio.sleep(0.01)
            if 'sha256' in url:
                resp = MagicMock()
                resp.text = f'{checksum}  file.ndjson'
                resp.raise_for_status = MagicMock()
                return resp
            resp = MagicMock()
            resp.content = content
            resp.raise_for_status = MagicMock()
            return resp

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

        with patch('httpx.AsyncClient', return_value=mock_client):
            # Launch 5 concurrent fetch calls
            results = await asyncio.gather(
                fetch_datasets(),
                fetch_datasets(),
                fetch_datasets(),
                fetch_datasets(),
                fetch_datasets(),
            )

        # All 5 calls should return the same data
        for result in results:
            assert len(result) == 1
            assert result[0]['Slug'] == 'concurrent'

        # Only 2 HTTP calls (ndjson + checksum) — not 10 (5 × 2)
        # The lock ensures only one coroutine does the actual fetch
        assert call_count == 2

        server_module._datasets_cache = None
        server_module._cache_timestamp = None

    async def test_stale_cache_triggers_refetch(self):
        """Expired cache timestamp causes a fresh download."""
        import hashlib
        from datetime import datetime, timedelta

        # Pre-populate cache with stale data (expired 25 hours ago)
        server_module._datasets_cache = [{'Slug': 'stale', 'Name': 'Stale', 'Tags': []}]
        server_module._cache_timestamp = datetime.now() - timedelta(hours=25)

        # New data from the server
        content = b'{"Slug":"fresh","Name":"Fresh Dataset","Tags":[]}\n'
        checksum = hashlib.sha256(content).hexdigest()

        mock_response = MagicMock()
        mock_response.content = content
        mock_response.raise_for_status = MagicMock()

        mock_checksum_response = MagicMock()
        mock_checksum_response.text = f'{checksum}  file.ndjson'
        mock_checksum_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_response, mock_checksum_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await fetch_datasets()

        # Should have fetched fresh data, not returned stale cache
        assert len(result) == 1
        assert result[0]['Slug'] == 'fresh'

        server_module._datasets_cache = None
        server_module._cache_timestamp = None


# ---------------------------------------------------------------------------
# search_datasets tests
# ---------------------------------------------------------------------------


class TestSearchDatasets:
    """Tests for search_datasets edge cases."""

    async def test_ignored_terms_fallback(self, setup_server, patch_fetch):
        """Query with only ignored terms (e.g., 'data') falls back to full query."""
        result = await search_datasets('data')
        data = json.loads(result)
        # 'data' is in IGNORED_TERMS, so it falls back to using 'data' as-is
        assert 'query' in data
        assert data['query'] == 'data'

    async def test_diversification_by_provider(self, setup_server, patch_fetch):
        """Results are diversified by provider when limit is smaller than matches."""
        # Both nasa-nex and landsat-8 are managed by NASA; noaa-ghcn by NOAA
        result = await search_datasets('satellite', limit=2)
        data = json.loads(result)
        assert data['returned_count'] <= 2

    async def test_long_description_truncation(self, setup_server, patch_fetch):
        """Descriptions longer than 200 chars are truncated with ellipsis."""
        # Add a dataset with a very long description
        long_ds = {
            'Slug': 'long-desc',
            'Name': 'Long Description Test',
            'Description': 'climate ' + 'x' * 300,
            'ManagedBy': '[Test](https://test.com/)',
            'License': 'MIT',
            'Tags': ['climate'],
            'Resources': [],
        }
        server_module._datasets_cache.append(long_ds)  # type: ignore[union-attr]
        server_module._knowledge_base.build_indexes(server_module._datasets_cache)  # type: ignore[arg-type]

        result = await search_datasets('climate')
        data = json.loads(result)

        # Find the long-desc result
        long_result = next((r for r in data['results'] if r['slug'] == 'long-desc'), None)
        assert long_result is not None
        assert long_result['description'].endswith('...')
        assert len(long_result['description']) <= 204  # 200 + '...'


# ---------------------------------------------------------------------------
# discover_by_organization tests
# ---------------------------------------------------------------------------


class TestDiscoverByOrganization:
    """Tests for discover_by_organization."""

    async def test_find_nasa_datasets(self, setup_server, patch_fetch):
        """Search by organization returns matching datasets."""
        result = await discover_by_organization('NASA')
        data = json.loads(result)

        assert data['organization'] == 'NASA'
        assert data['count'] >= 1
        slugs = {d['slug'] for d in data['datasets']}
        assert 'nasa-nex' in slugs or 'landsat-8' in slugs

    async def test_no_matches(self, setup_server, patch_fetch):
        """Non-matching org returns empty results."""
        result = await discover_by_organization('NonexistentOrg')
        data = json.loads(result)
        assert data['count'] == 0

    async def test_limit_respected(self, setup_server, patch_fetch):
        """Limit caps the number of results."""
        result = await discover_by_organization('NASA', limit=1)
        data = json.loads(result)
        assert len(data['datasets']) <= 1


# ---------------------------------------------------------------------------
# discover_by_license tests
# ---------------------------------------------------------------------------


class TestDiscoverByLicense:
    """Tests for discover_by_license."""

    async def test_find_public_domain(self, setup_server, patch_fetch):
        """Search by public domain license returns matching datasets."""
        result = await discover_by_license('public domain')
        data = json.loads(result)

        assert data['license_type'] == 'public domain'
        assert data['count'] >= 1

    async def test_find_creative_commons(self, setup_server, patch_fetch):
        """Search by creative commons returns matching datasets."""
        result = await discover_by_license('creative commons')
        data = json.loads(result)
        assert data['count'] >= 1

    async def test_no_matches(self, setup_server, patch_fetch):
        """Non-matching license returns empty results."""
        result = await discover_by_license('proprietary')
        data = json.loads(result)
        assert data['count'] == 0


# ---------------------------------------------------------------------------
# find_related_datasets tests
# ---------------------------------------------------------------------------


class TestFindRelatedDatasets:
    """Tests for find_related_datasets."""

    async def test_find_related_by_tags(self, setup_server, patch_fetch):
        """Finds datasets sharing tags with the given dataset."""
        result = await find_related_datasets('nasa-nex')
        data = json.loads(result)

        assert data['source_dataset'] == 'nasa-nex'
        # nasa-nex shares 'climate' with noaa-ghcn, 'satellite' with landsat-8
        assert data['count'] >= 1

    async def test_nonexistent_dataset(self, setup_server, patch_fetch):
        """Non-existent slug returns empty results."""
        result = await find_related_datasets('nonexistent-slug')
        data = json.loads(result)
        assert data['count'] == 0

    async def test_limit_respected(self, setup_server, patch_fetch):
        """Limit caps related results."""
        result = await find_related_datasets('nasa-nex', limit=1)
        data = json.loads(result)
        assert len(data['related_datasets']) <= 1


# ---------------------------------------------------------------------------
# get_knowledge_base_stats tests
# ---------------------------------------------------------------------------


class TestGetKnowledgeBaseStats:
    """Tests for get_knowledge_base_stats."""

    async def test_returns_stats(self, setup_server, patch_fetch):
        """Returns comprehensive statistics."""
        result = await get_knowledge_base_stats()
        data = json.loads(result)

        assert data['total_datasets'] >= 4
        assert 'total_tags' in data
        assert 'total_organizations' in data
        assert 'top_tags' in data
        assert 'top_organizations' in data
        assert 'resource_types' in data
        assert 'license_types' in data


# ---------------------------------------------------------------------------
# search_stac_endpoints tests
# ---------------------------------------------------------------------------


STAC_DATASETS = [
    {
        'Slug': 'sentinel-stac',
        'Name': 'Sentinel STAC Data',
        'Description': 'Sentinel satellite imagery with STAC catalog',
        'ManagedBy': '[ESA](https://www.esa.int/)',
        'Tags': ['satellite', 'stac', 'imagery'],
        'Resources': [
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::sentinel-stac',
                'Region': 'eu-central-1',
                'Explore': ['https://earth-search.aws.element84.com/v1 (STAC API)'],
            }
        ],
    },
    {
        'Slug': 'landsat-stac',
        'Name': 'Landsat STAC Collection',
        'Description': 'Landsat satellite data with STAC endpoints',
        'ManagedBy': '[NASA](https://www.nasa.gov/)',
        'Tags': ['satellite', 'stac'],
        'Resources': [
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::landsat-stac',
                'Region': 'us-west-2',
                'Description': 'STAC catalog at https://landsatlook.usgs.gov/stac-server',
            }
        ],
    },
    {
        'Slug': 'no-stac',
        'Name': 'Regular Dataset',
        'Description': 'Just a normal dataset without STAC',
        'ManagedBy': '[NOAA](https://www.noaa.gov/)',
        'Tags': ['climate', 'weather'],
        'Resources': [
            {
                'Type': 'S3 Bucket',
                'ARN': 'arn:aws:s3:::regular-data',
                'Region': 'us-east-1',
            }
        ],
    },
    {
        'Slug': 'stac-tools',
        'Name': 'Dataset with STAC Tools',
        'Description': 'A dataset referenced in STAC tools section',
        'ManagedBy': '[NASA](https://www.nasa.gov/)',
        'Tags': ['geospatial'],
        'Resources': [],
        'DataAtWork': {
            'Tools & Applications': [
                {
                    'Title': 'STAC Browser',
                    'URL': 'https://radiantearth.github.io/stac-browser/',
                }
            ],
            'Tutorials': [
                {
                    'Title': 'Using STAC with Python',
                    'URL': 'https://example.com/stac-tutorial',
                }
            ],
        },
    },
]


class TestSearchStacEndpoints:
    """Tests for search_stac_endpoints."""

    @pytest.fixture(autouse=True)
    def setup_stac_data(self):
        """Set up STAC test data."""
        server_module._datasets_cache = STAC_DATASETS
        yield
        server_module._datasets_cache = None
        server_module._cache_timestamp = None

    @pytest.fixture
    def patch_fetch_stac(self):
        """Mock fetch_datasets to return STAC sample data."""
        with patch(
            'awslabs.roda_mcp_server.server.fetch_datasets', new_callable=AsyncMock
        ) as mock:
            mock.return_value = STAC_DATASETS
            yield mock

    async def test_find_all_stac_datasets(self, patch_fetch_stac):
        """Without a query, returns all datasets with STAC endpoints or tags."""
        result = await search_stac_endpoints()
        data = json.loads(result)

        assert data['count'] >= 2
        slugs = {r['slug'] for r in data['results']}
        assert 'sentinel-stac' in slugs
        assert 'landsat-stac' in slugs
        assert 'no-stac' not in slugs

    async def test_filter_by_query(self, patch_fetch_stac):
        """Query filters results by name/description/tags."""
        result = await search_stac_endpoints(query='sentinel')
        data = json.loads(result)

        assert data['query'] == 'sentinel'
        assert data['count'] == 1
        assert data['results'][0]['slug'] == 'sentinel-stac'

    async def test_no_matches(self, patch_fetch_stac):
        """Query that doesn't match any STAC dataset returns empty."""
        result = await search_stac_endpoints(query='nonexistent')
        data = json.loads(result)
        assert data['count'] == 0

    async def test_limit_respected(self, patch_fetch_stac):
        """Limit caps number of results."""
        result = await search_stac_endpoints(limit=1)
        data = json.loads(result)
        assert len(data['results']) <= 1

    async def test_stac_from_data_at_work(self, patch_fetch_stac):
        """Finds STAC endpoints from DataAtWork sections."""
        result = await search_stac_endpoints()
        data = json.loads(result)

        slugs = {r['slug'] for r in data['results']}
        assert 'stac-tools' in slugs

    async def test_stac_tag_detected(self, patch_fetch_stac):
        """Datasets with 'stac' tag are flagged as has_stac_tag."""
        result = await search_stac_endpoints()
        data = json.loads(result)

        sentinel_result = next(r for r in data['results'] if r['slug'] == 'sentinel-stac')
        assert sentinel_result['has_stac_tag'] is True

    async def test_endpoints_deduplicated(self, patch_fetch_stac):
        """Duplicate URLs in endpoints are deduplicated."""
        result = await search_stac_endpoints()
        data = json.loads(result)

        for r in data['results']:
            urls = [ep['url'] for ep in r.get('stac_endpoints', [])]
            assert len(urls) == len(set(urls))


# ---------------------------------------------------------------------------
# preview_dataset edge cases
# ---------------------------------------------------------------------------


class TestPreviewEdgeCases:
    """Additional preview_dataset edge cases."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Set up test data."""
        datasets = [
            {
                'Slug': 'bad-arn',
                'Name': 'Bad ARN Dataset',
                'Description': 'Has an unparseable ARN',
                'License': 'MIT',
                'ManagedBy': '[Test](https://test.com/)',
                'Tags': [],
                'Resources': [
                    {
                        'Type': 'S3 Bucket',
                        'ARN': 'not-a-valid-arn',
                        'Region': 'us-east-1',
                    }
                ],
            },
            {
                'Slug': 'generic-error',
                'Name': 'Generic Error Dataset',
                'Description': 'Will cause a non-ClientError exception',
                'License': 'MIT',
                'ManagedBy': '[Test](https://test.com/)',
                'Tags': [],
                'Resources': [
                    {
                        'Type': 'S3 Bucket',
                        'ARN': 'arn:aws:s3:::error-bucket',
                        'Region': 'us-east-1',
                    }
                ],
            },
        ]
        server_module._datasets_cache = datasets
        yield
        server_module._datasets_cache = None
        server_module._cache_timestamp = None

    @pytest.fixture
    def patch_fetch_edge(self):
        """Mock fetch_datasets to return preview edge-case data without network calls."""
        with patch(
            'awslabs.roda_mcp_server.server.fetch_datasets', new_callable=AsyncMock
        ) as mock:
            mock.return_value = server_module._datasets_cache
            yield mock

    async def test_unparseable_arn(self, patch_fetch_edge):
        """ARN without ':::' returns a parse error."""
        result = await preview_dataset('bad-arn')
        data = json.loads(result)
        assert 'error' in data
        assert 'parse' in data['error'].lower() or 'Could not parse' in data['error']

    async def test_generic_exception(self, patch_fetch_edge):
        """Non-ClientError exception is caught and returned."""
        with patch('boto3.client') as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.return_value = mock_s3
            mock_s3.list_objects_v2.side_effect = RuntimeError('Network timeout')

            result = await preview_dataset('generic-error')
            data = json.loads(result)

            assert 'error' in data
            assert 'Unexpected' in data['error'] or 'Network timeout' in data.get('message', '')


# ---------------------------------------------------------------------------
# sample_dataset edge cases
# ---------------------------------------------------------------------------


class TestSampleEdgeCases:
    """Additional sample_dataset error paths."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Create mock dataset."""
        datasets = [
            {
                'Slug': 'sample-test',
                'Name': 'Sample Test Dataset',
                'Description': 'For testing sample_dataset errors',
                'License': 'MIT',
                'ManagedBy': '[Test](https://test.com/)',
                'Tags': [],
                'Resources': [
                    {
                        'Type': 'S3 Bucket',
                        'ARN': 'arn:aws:s3:::sample-bucket',
                        'Region': 'us-east-1',
                    }
                ],
            },
        ]
        server_module._datasets_cache = datasets
        yield
        server_module._datasets_cache = None
        server_module._cache_timestamp = None

    @pytest.fixture
    def patch_fetch_sample(self):
        """Mock fetch_datasets to return sample test data without network calls."""
        with patch(
            'awslabs.roda_mcp_server.server.fetch_datasets', new_callable=AsyncMock
        ) as mock:
            mock.return_value = server_module._datasets_cache
            yield mock

    async def test_generic_exception(self, patch_fetch_sample):
        """Non-ClientError exception in sample_dataset is caught."""
        with patch('boto3.client') as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.return_value = mock_s3
            mock_s3.head_object.side_effect = RuntimeError('Connection reset')

            result = await sample_dataset('sample-test', 'some/file.csv')
            data = json.loads(result)

            assert 'error' in data
            assert 'Unexpected' in data['error'] or 'Connection reset' in data.get('message', '')

    async def test_non_access_denied_client_error(self, patch_fetch_sample):
        """Non-AccessDenied ClientError returns generic AWS error."""
        from botocore.exceptions import ClientError

        with patch('boto3.client') as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.return_value = mock_s3
            mock_s3.head_object.side_effect = ClientError(
                {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}},
                'HeadObject',
            )

            result = await sample_dataset('sample-test', 'some/file.csv')
            data = json.loads(result)

            assert 'error' in data
            assert 'NoSuchBucket' in data['error'] or 'AWS error' in data['error']
