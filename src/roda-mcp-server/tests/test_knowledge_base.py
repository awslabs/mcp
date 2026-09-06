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

"""Tests for knowledge base functionality.

This file tests two layers:

1. DatasetKnowledgeBase class (unit tests)
   - Tests the in-memory indexing, search, and statistics logic directly.
   - No network calls, no async — pure data structure validation.

2. MCP tool wrappers (integration tests)
   - Tests the server's tool functions (discover_by_organization, etc.)
   - These are async functions that call fetch_datasets() internally,
     so we mock fetch_datasets to avoid network calls and use sample data.
   - Validates the JSON response structure returned to MCP clients.

Run: uv run python -m pytest tests/test_knowledge_base.py -v
"""

import awslabs.roda_mcp_server.server as server_module
import json
import pytest
from awslabs.roda_mcp_server.knowledge_base import DatasetKnowledgeBase
from awslabs.roda_mcp_server.server import (
    discover_by_license,
    discover_by_organization,
    find_related_datasets,
    get_knowledge_base_stats,
)


# Sample dataset fixtures representing different scenarios:
# - Two NASA datasets (tests org search returning multiple results)
# - Different license types (Creative Commons, Public Domain, MIT, Apache)
# - Overlapping tags (tests related dataset discovery)
# - Some with Documentation field, some without (tests statistics)
SAMPLE_DATASETS = [
    {
        'Slug': 'nasa-nex',
        'Name': 'NASA NEX',
        'Description': 'NASA Earth Exchange climate projections',
        'ManagedBy': '[NASA](https://www.nasa.gov/)',
        'License': 'Creative Commons Attribution 4.0',
        'Tags': ['climate', 'earth observation', 'satellite'],
        'Resources': [{'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::nasanex'}],
        'Documentation': 'https://example.com/docs',
    },
    {
        'Slug': 'noaa-ghcn',
        'Name': 'NOAA GHCN',
        'Description': 'Global Historical Climatology Network',
        'ManagedBy': '[NOAA](https://www.noaa.gov/)',
        'License': 'Public Domain',
        'Tags': ['climate', 'weather', 'historical'],
        'Resources': [{'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::noaa-ghcn'}],
        'Documentation': 'https://example.com/noaa',
    },
    {
        'Slug': 'genomics-data',
        'Name': 'Genomics Dataset',
        'Description': 'Human genome sequencing data',
        'ManagedBy': '[NIH](https://www.nih.gov/)',
        'License': 'MIT License',
        'Tags': ['genomics', 'health', 'biology'],
        'Resources': [{'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::genomics'}],
    },
    {
        'Slug': 'nasa-modis',
        'Name': 'NASA MODIS',
        'Description': 'MODIS satellite imagery',
        'ManagedBy': '[NASA](https://www.nasa.gov/)',
        'License': 'Apache License 2.0',
        'Tags': ['satellite', 'earth observation', 'imagery'],
        'Resources': [{'Type': 'S3 Bucket', 'ARN': 'arn:aws:s3:::modis'}],
    },
]


@pytest.fixture(autouse=True)
def setup_knowledge_base():
    """Pre-populate the server's knowledge base with sample data before each test.

    This avoids network calls during the class-level tests and ensures a clean
    state between tests by resetting the cache afterward.
    """
    server_module._datasets_cache = SAMPLE_DATASETS
    server_module._knowledge_base.build_indexes(SAMPLE_DATASETS)
    yield
    server_module._datasets_cache = None
    server_module._cache_timestamp = None


# =============================================================================
# DatasetKnowledgeBase class tests (unit tests)
#
# These test the indexing and search logic directly on the class,
# independent of the server or async machinery.
# =============================================================================


def test_build_indexes():
    """Verify that build_indexes creates correct tag, org, and license indexes."""
    kb = DatasetKnowledgeBase()
    kb.build_indexes(SAMPLE_DATASETS)

    assert len(kb.datasets) == 4
    assert 'climate' in kb.tag_index
    # nasa-nex and noaa-ghcn both have the 'climate' tag
    assert len(kb.tag_index['climate']) == 2


def test_search_by_organization():
    """Partial org name match should return all datasets managed by that org."""
    kb = DatasetKnowledgeBase()
    kb.build_indexes(SAMPLE_DATASETS)

    results = kb.search_by_organization('NASA')
    assert len(results) == 2
    slugs = {d['Slug'] for d in results}
    assert 'nasa-nex' in slugs
    assert 'nasa-modis' in slugs


def test_search_by_organization_no_match():
    """Searching for a nonexistent org should return an empty list."""
    kb = DatasetKnowledgeBase()
    kb.build_indexes(SAMPLE_DATASETS)

    results = kb.search_by_organization('nonexistent-org')
    assert results == []


def test_search_by_license():
    """License search should match datasets indexed under that license category."""
    kb = DatasetKnowledgeBase()
    kb.build_indexes(SAMPLE_DATASETS)

    results = kb.search_by_license('creative commons')
    assert len(results) == 1
    assert results[0]['Slug'] == 'nasa-nex'


def test_search_by_license_public_domain():
    """Public domain license search should find the correct dataset."""
    kb = DatasetKnowledgeBase()
    kb.build_indexes(SAMPLE_DATASETS)

    results = kb.search_by_license('public domain')
    assert len(results) == 1
    assert results[0]['Slug'] == 'noaa-ghcn'


def test_find_related_datasets():
    """Related datasets are ranked by number of shared tags."""
    kb = DatasetKnowledgeBase()
    kb.build_indexes(SAMPLE_DATASETS)

    # nasa-nex has tags: climate, earth observation, satellite
    # nasa-modis shares: satellite, earth observation (2 tags) — should rank highest
    related = kb.find_related_datasets('nasa-nex', limit=5)
    assert len(related) >= 1
    slugs = [d['Slug'] for d in related]
    assert 'nasa-modis' in slugs


def test_find_related_datasets_not_found():
    """Searching for related datasets with a nonexistent slug returns empty."""
    kb = DatasetKnowledgeBase()
    kb.build_indexes(SAMPLE_DATASETS)

    related = kb.find_related_datasets('nonexistent')
    assert related == []


def test_get_statistics():
    """Statistics should reflect the indexed sample data accurately."""
    kb = DatasetKnowledgeBase()
    kb.build_indexes(SAMPLE_DATASETS)

    stats = kb.get_statistics()
    assert stats['total_datasets'] == 4
    assert stats['total_tags'] > 0
    assert stats['total_organizations'] == 3  # NASA, NOAA, NIH
    assert stats['datasets_with_resources'] == 4
    assert stats['datasets_with_documentation'] == 2  # only nasa-nex and noaa-ghcn


# =============================================================================
# MCP tool wrapper tests (integration tests)
#
# These test the actual tool functions that MCP clients call.
# fetch_datasets is mocked to prevent network calls and ensure the knowledge
# base uses our sample data. Validates JSON response structure and content.
# =============================================================================


@pytest.fixture
def patch_fetch_datasets():
    """Mock fetch_datasets so tool functions don't hit the network.

    The tool functions call `await fetch_datasets()` to ensure the knowledge
    base is built. This fixture short-circuits that call and returns sample data.
    """
    from unittest.mock import AsyncMock, patch

    with patch('awslabs.roda_mcp_server.server.fetch_datasets', new_callable=AsyncMock) as mock:
        mock.return_value = SAMPLE_DATASETS
        yield mock


async def test_tool_discover_by_organization(patch_fetch_datasets):
    """Tool should return JSON with matching datasets for a given org."""
    result = await discover_by_organization('NASA', limit=10)
    data = json.loads(result)

    assert data['organization'] == 'NASA'
    assert data['count'] == 2
    slugs = {d['slug'] for d in data['datasets']}
    assert 'nasa-nex' in slugs
    assert 'nasa-modis' in slugs


async def test_tool_discover_by_organization_with_limit(patch_fetch_datasets):
    """The limit parameter should cap the number of returned datasets."""
    result = await discover_by_organization('NASA', limit=1)
    data = json.loads(result)

    assert data['count'] == 1
    assert len(data['datasets']) == 1


async def test_tool_discover_by_license(patch_fetch_datasets):
    """Tool should return datasets matching the specified license type."""
    result = await discover_by_license('mit')
    data = json.loads(result)

    assert data['license_type'] == 'mit'
    assert data['count'] == 1
    assert data['datasets'][0]['slug'] == 'genomics-data'


async def test_tool_find_related_datasets(patch_fetch_datasets):
    """Tool should find datasets that share tags with the given dataset."""
    result = await find_related_datasets('nasa-nex', limit=5)
    data = json.loads(result)

    assert data['source_dataset'] == 'nasa-nex'
    assert data['count'] >= 1
    slugs = [d['slug'] for d in data['related_datasets']]
    assert 'nasa-modis' in slugs


async def test_tool_find_related_datasets_not_found(patch_fetch_datasets):
    """Tool should return empty results for a nonexistent dataset slug."""
    result = await find_related_datasets('nonexistent')
    data = json.loads(result)

    assert data['source_dataset'] == 'nonexistent'
    assert data['count'] == 0
    assert data['related_datasets'] == []


async def test_tool_get_knowledge_base_stats(patch_fetch_datasets):
    """Tool should return comprehensive statistics about the knowledge base."""
    result = await get_knowledge_base_stats()
    data = json.loads(result)

    assert data['total_datasets'] == 4
    assert data['total_tags'] > 0
    assert data['total_organizations'] == 3
    assert 'top_tags' in data
    assert 'top_organizations' in data
