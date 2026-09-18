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
from awslabs.roda_mcp_server.server import (
    _relevance_score,
    _word_match,
    search_datasets,
)


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


async def test_search_ranks_by_relevance(setup_server, patch_fetch):
    """A dataset matching more query terms ranks above one matching fewer."""
    result = await search_datasets('climate weather')
    data = json.loads(result)

    # noaa-ghcn has both 'climate' and 'weather' tags; nasa-nex has only
    # 'climate'. The more complete match should rank first.
    assert data['total_count'] == 2
    assert data['results'][0]['slug'] == 'noaa-ghcn'


async def test_search_ignores_stop_words(setup_server, patch_fetch):
    """Filler/stop words do not widen the match set."""
    result = await search_datasets('find the climate data')
    data = json.loads(result)

    # Only 'climate' is meaningful; it matches nasa-nex and noaa-ghcn.
    assert data['total_count'] == 2
    assert {r['slug'] for r in data['results']} == {'nasa-nex', 'noaa-ghcn'}


async def test_search_result_omits_internal_score(setup_server, patch_fetch):
    """The internal relevance score is not leaked in the response."""
    result = await search_datasets('climate')
    data = json.loads(result)

    assert data['results']
    assert all('score' not in r for r in data['results'])


# --- Direct unit tests for the relevance scorer -------------------------------
# The tests above exercise scoring through search_datasets; these pin each
# scoring tier of _relevance_score (and _word_match) directly so every branch
# is covered and the weighting is documented by example.


def test_word_match_whole_word_vs_substring():
    """_word_match is True only on a whole-word hit, not a bare substring."""
    assert _word_match('ocean', 'ocean temperature') is True
    assert _word_match('cean', 'ocean') is False


def test_score_exact_tag_match():
    """An exact tag match scores 6.0, plus 1 coverage bonus for the term."""
    assert _relevance_score('x', 'y', ['climate'], ['climate']) == 7.0


def test_score_partial_tag_match():
    """A substring of a tag (not an exact tag) scores 3.0 (+1)."""
    assert _relevance_score('x', 'y', ['climate'], ['clim']) == 4.0


def test_score_whole_word_name_match():
    """A whole-word hit in the name scores 5.0 (+1)."""
    assert _relevance_score('ocean temperature', 'y', [], ['ocean']) == 6.0


def test_score_substring_name_match():
    """A substring of the name that is not a whole word scores 2.5 (+1)."""
    assert _relevance_score('ocean', 'y', [], ['cean']) == 3.5


def test_score_whole_word_description_match():
    """A whole-word hit only in the description scores 1.5 (+1)."""
    assert _relevance_score('x', 'sea salinity levels', [], ['salinity']) == 2.5


def test_score_substring_description_match():
    """A substring of the description that is not a whole word scores 0.5 (+1)."""
    assert _relevance_score('x', 'salinity', [], ['alin']) == 1.5


def test_score_no_match_is_zero():
    """A term appearing nowhere contributes nothing and is not counted."""
    assert _relevance_score('x', 'y', ['tag'], ['zzz']) == 0.0


def test_score_stronger_field_wins_via_max():
    """A whole-word name hit (5.0) supersedes a weaker substring tag hit (3.0)."""
    assert _relevance_score('climate data', 'y', ['climatology'], ['climate']) == 6.0


def test_score_coverage_bonus_rewards_more_terms():
    """Two matched terms (6.0 tag + 5.0 name) earn a +2 coverage bonus = 13.0."""
    assert _relevance_score('ocean', 'y', ['climate'], ['climate', 'ocean']) == 13.0
