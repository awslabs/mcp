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

"""Additional server coverage tests."""


def test_search_with_all_filters():
    """Test search with all possible filter combinations."""
    from well_architected_bp_mcp_server.server import search_best_practices_impl

    # Test all filter combinations to hit more code paths
    result = search_best_practices_impl(
        pillar='SECURITY', risk='HIGH', lens='FRAMEWORK', keyword='access', area='identity'
    )
    assert isinstance(result, list)

    result = search_best_practices_impl(pillar='RELIABILITY', risk='MEDIUM')
    assert isinstance(result, list)

    result = search_best_practices_impl(lens='GENERATIVE_AI')
    assert isinstance(result, list)


def test_get_best_practice_edge_cases():
    """Test get_best_practice with various IDs."""
    from well_architected_bp_mcp_server.server import get_best_practice_impl

    # Test with empty string
    result = get_best_practice_impl('')
    assert result is None

    # Test with non-existent ID
    result = get_best_practice_impl('NONEXISTENT-ID')
    assert result is None


def test_get_related_practices_edge_cases():
    """Test get_related_practices with various scenarios."""
    from well_architected_bp_mcp_server.server import get_related_practices_impl

    # Test with empty string
    result = get_related_practices_impl('')
    assert isinstance(result, list)
    assert len(result) == 0

    # Test with non-existent ID
    result = get_related_practices_impl('NONEXISTENT-ID')
    assert isinstance(result, list)
    assert len(result) == 0


def test_framework_review_structure():
    """Test framework review structure in detail."""
    from well_architected_bp_mcp_server.server import well_architected_framework_review_impl

    result = well_architected_framework_review_impl()

    # Test all expected keys exist
    assert 'framework' in result
    assert 'pillars' in result
    assert 'total_practices' in result
    assert 'key_areas' in result
    assert 'assessment_guidance' in result

    # Test pillar structure
    assert isinstance(result['pillars'], dict)
    for pillar_name, pillar_data in result['pillars'].items():
        assert 'practice_count' in pillar_data
        assert 'high_risk_practices' in pillar_data
        assert 'key_practices' in pillar_data

    # Test key areas
    assert isinstance(result['key_areas'], list)
    assert len(result['key_areas']) > 0

    # Test assessment guidance
    assert isinstance(result['assessment_guidance'], list)
    assert len(result['assessment_guidance']) > 0
