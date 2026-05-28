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

from awslabs.well_architected_mcp_server.server import (
    get_anti_patterns,
    get_best_practice,
    get_best_practice_full,
    get_practices_for_question,
    get_related_practices,
    list_pillars,
    list_questions,
    search_best_practices,
    search_content,
    well_architected_framework_review,
)


def test_search_best_practices_wrapper():
    """Test search_best_practices MCP wrapper function."""
    result = search_best_practices()
    assert isinstance(result, dict)
    assert 'results' in result
    assert 'total_count' in result

    result = search_best_practices(pillar='SECURITY')
    assert result['total_count'] > 0

    result = search_best_practices(risk='HIGH')
    assert result['total_count'] > 0

    result = search_best_practices(lens='FRAMEWORK')
    assert result['total_count'] > 0

    result = search_best_practices(keyword='identity')
    assert result['total_count'] > 0

    result = search_best_practices(area='access')
    assert isinstance(result, dict)

    result = search_best_practices(max_results=3, offset=0)
    assert len(result['results']) <= 3


def test_search_content_wrapper():
    """Test search_content MCP wrapper function."""
    result = search_content('CloudTrail')
    assert isinstance(result, list)
    assert len(result) > 0

    result = search_content('Lambda', pillar='SECURITY')
    assert isinstance(result, list)

    result = search_content('backup', section='implementation_steps')
    assert isinstance(result, list)


def test_get_best_practice_wrapper():
    """Test get_best_practice MCP wrapper function."""
    practices = search_best_practices()
    if practices['results']:
        practice_id = practices['results'][0]['id']
        result = get_best_practice(practice_id)
        assert result is not None

    result = get_best_practice('INVALID-ID')
    assert result is None


def test_get_best_practice_full_wrapper():
    """Test get_best_practice_full MCP wrapper function."""
    result = get_best_practice_full('SEC01-BP01')
    assert result is not None
    assert result['id'] == 'SEC01-BP01'
    assert 'content' in result

    result = get_best_practice_full('SEC01-BP01', section='resources')
    assert result is not None

    result = get_best_practice_full('INVALID-BP99')
    assert result is None


def test_list_questions_wrapper():
    """Test list_questions MCP wrapper function."""
    result = list_questions()
    assert isinstance(result, list)
    assert len(result) == 57

    result = list_questions(pillar='SECURITY')
    assert len(result) > 0


def test_get_practices_for_question_wrapper():
    """Test get_practices_for_question MCP wrapper function."""
    result = get_practices_for_question('securely operate')
    assert isinstance(result, list)
    assert len(result) > 0

    result = get_practices_for_question('zzznomatchzzz')
    assert result == []


def test_get_anti_patterns_wrapper():
    """Test get_anti_patterns MCP wrapper function."""
    result = get_anti_patterns(id='SEC01-BP01')
    assert isinstance(result, list)
    assert len(result) == 1

    result = get_anti_patterns(pillar='SECURITY', risk='HIGH')
    assert len(result) > 0


def test_list_pillars_wrapper():
    """Test list_pillars MCP wrapper function."""
    result = list_pillars()
    assert isinstance(result, dict)
    assert len(result) > 0
    for pillar, data in result.items():
        assert 'total' in data
        assert 'risk_distribution' in data


def test_get_related_practices_wrapper():
    """Test get_related_practices MCP wrapper function."""
    practices = search_best_practices()
    for practice in practices['results']:
        if practice.get('relatedIds'):
            result = get_related_practices(practice['id'])
            assert isinstance(result, list)
            break

    result = get_related_practices('INVALID-ID')
    assert isinstance(result, list)
    assert len(result) == 0


def test_well_architected_framework_review_wrapper():
    """Test well_architected_framework_review MCP wrapper function."""
    result = well_architected_framework_review()
    assert isinstance(result, dict)
    assert 'framework' in result
    assert 'pillars' in result
    assert 'total_practices' in result
