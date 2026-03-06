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

"""Test MCP wrapper functions directly for patch coverage."""

from well_architected_bp_mcp_server.server import (
    get_best_practice,
    get_related_practices,
    list_pillars,
    search_best_practices,
    well_architected_framework_review,
)


def test_search_best_practices_wrapper():
    """Test search_best_practices MCP wrapper function."""
    result = search_best_practices.fn()
    assert isinstance(result, list)

    result = search_best_practices.fn(pillar='SECURITY')
    assert isinstance(result, list)

    result = search_best_practices.fn(risk='HIGH')
    assert isinstance(result, list)

    result = search_best_practices.fn(lens='FRAMEWORK')
    assert isinstance(result, list)

    result = search_best_practices.fn(keyword='identity')
    assert isinstance(result, list)

    result = search_best_practices.fn(area='access')
    assert isinstance(result, list)


def test_get_best_practice_wrapper():
    """Test get_best_practice MCP wrapper function."""
    # Get a valid ID first
    practices = search_best_practices.fn()
    if practices:
        practice_id = practices[0]['id']
        result = get_best_practice.fn(practice_id)
        assert result is not None

    # Test with invalid ID
    result = get_best_practice.fn('INVALID-ID')
    assert result is None


def test_list_pillars_wrapper():
    """Test list_pillars MCP wrapper function."""
    result = list_pillars.fn()
    assert isinstance(result, dict)
    assert len(result) > 0


def test_get_related_practices_wrapper():
    """Test get_related_practices MCP wrapper function."""
    # Find a practice with relations
    practices = search_best_practices.fn()
    for practice in practices:
        if practice.get('relatedIds'):
            result = get_related_practices.fn(practice['id'])
            assert isinstance(result, list)
            break

    # Test with invalid ID
    result = get_related_practices.fn('INVALID-ID')
    assert isinstance(result, list)
    assert len(result) == 0


def test_well_architected_framework_review_wrapper():
    """Test well_architected_framework_review MCP wrapper function."""
    result = well_architected_framework_review.fn()
    assert isinstance(result, dict)
    assert 'framework' in result
    assert 'pillars' in result
    assert 'total_practices' in result
