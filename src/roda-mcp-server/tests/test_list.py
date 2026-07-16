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

"""Tests for the list_datasets tool.

Covers tag filtering, limit, and response structure.

Run: uv run python -m pytest tests/test_list.py -v
"""

import json
from awslabs.roda_mcp_server.server import list_datasets


async def test_list_all_datasets(setup_server, patch_fetch):
    """Listing without a tag filter returns all datasets up to the limit."""
    result = await list_datasets()
    data = json.loads(result)

    assert data['total'] == 4
    assert data['filtered'] == 4
    assert data['tag_filter'] is None


async def test_list_with_tag_filter(setup_server, patch_fetch):
    """Tag filter returns only datasets that have that tag."""
    result = await list_datasets(tag='climate')
    data = json.loads(result)

    assert data['tag_filter'] == 'climate'
    assert data['filtered'] == 2
    slugs = {d['slug'] for d in data['datasets']}
    assert 'nasa-nex' in slugs
    assert 'noaa-ghcn' in slugs


async def test_list_with_tag_no_match(setup_server, patch_fetch):
    """Tag filter that matches nothing returns empty results."""
    result = await list_datasets(tag='nonexistent-tag')
    data = json.loads(result)

    assert data['filtered'] == 0
    assert data['datasets'] == []


async def test_list_with_limit(setup_server, patch_fetch):
    """Limit caps the number of returned datasets."""
    result = await list_datasets(limit=2)
    data = json.loads(result)

    assert data['filtered'] == 2
    assert len(data['datasets']) == 2


async def test_list_response_structure(setup_server, patch_fetch):
    """Verify the JSON response contains all expected fields."""
    result = await list_datasets(limit=1)
    data = json.loads(result)

    assert 'total' in data
    assert 'filtered' in data
    assert 'tag_filter' in data
    assert 'datasets' in data

    d = data['datasets'][0]
    assert 'slug' in d
    assert 'name' in d
    assert 'description' in d
    assert 'tags' in d
    assert 'managed_by' in d
    assert 'license' in d
