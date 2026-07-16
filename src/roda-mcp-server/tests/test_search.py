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

"""Tests for the search_datasets tool.

Covers keyword matching, filtering by tags/org/license, limit,
and response structure.

Run: uv run python -m pytest tests/test_search.py -v
"""

import json
from awslabs.roda_mcp_server.server import search_datasets


async def test_search_by_keyword(setup_server, patch_fetch):
    """Basic keyword search matches against name, description, and tags."""
    result = await search_datasets('climate')
    data = json.loads(result)

    assert data['query'] == 'climate'
    assert data['total_count'] == 2  # nasa-nex and noaa-ghcn
    assert data['returned_count'] == 2


async def test_search_by_keyword_no_results(setup_server, patch_fetch):
    """Search for a term that doesn't match anything returns zero results."""
    result = await search_datasets('nonexistent-topic')
    data = json.loads(result)

    assert data['total_count'] == 0
    assert data['returned_count'] == 0
    assert data['results'] == []


async def test_search_with_tag_filter(setup_server, patch_fetch):
    """Tag filter narrows results to only datasets with that tag."""
    result = await search_datasets('climate', tags='weather')
    data = json.loads(result)

    # Only noaa-ghcn has both 'climate' in description and 'weather' tag
    assert data['total_count'] == 1
    assert data['results'][0]['slug'] == 'noaa-ghcn'


async def test_search_with_organization_filter(setup_server, patch_fetch):
    """Organization filter narrows results to datasets managed by that org."""
    result = await search_datasets('satellite', organization='NASA')
    data = json.loads(result)

    slugs = {r['slug'] for r in data['results']}
    assert 'landsat-8' in slugs


async def test_search_with_license_filter(setup_server, patch_fetch):
    """License filter narrows results to datasets with that license type."""
    result = await search_datasets('climate', license_type='public domain')
    data = json.loads(result)

    assert data['total_count'] == 1
    assert data['results'][0]['slug'] == 'noaa-ghcn'


async def test_search_with_limit(setup_server, patch_fetch):
    """Limit caps the number of returned results."""
    result = await search_datasets('satellite', limit=1)
    data = json.loads(result)

    assert data['returned_count'] == 1
    assert len(data['results']) == 1


async def test_search_response_structure(setup_server, patch_fetch):
    """Verify the JSON response contains all expected fields."""
    result = await search_datasets('genome')
    data = json.loads(result)

    assert 'query' in data
    assert 'total_count' in data
    assert 'returned_count' in data
    assert 'results' in data

    if data['results']:
        r = data['results'][0]
        assert 'slug' in r
        assert 'name' in r
        assert 'description' in r
        assert 'managed_by' in r
        assert 'license' in r
