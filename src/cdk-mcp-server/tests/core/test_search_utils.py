# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
from awslabs.cdk_mcp_server.core import search_utils


def test_normalize_term():
    """Test term normalization."""
    assert search_utils.normalize_term('Test-Term') == 'test term'
    assert search_utils.normalize_term('Test_Term') == 'test term'
    assert search_utils.normalize_term('Test Term') == 'test term'
    assert search_utils.normalize_term('Test%20Term') == 'test term'


def test_get_term_variations():
    """Test getting term variations."""
    variations = search_utils.get_term_variations('knowledgebase')
    assert 'knowledgebases' in variations
    assert 'knowledge-base' in variations
    assert 'knowledge-bases' in variations

    variations = search_utils.get_term_variations('agent')
    assert 'agents' in variations

    variations = search_utils.get_term_variations('actiongroup')
    assert 'actiongroups' in variations
    assert 'action-group' in variations
    assert 'action-groups' in variations


def test_expand_search_terms():
    """Test expanding search terms."""
    terms = ['knowledgebase', 'agent']
    expanded = search_utils.expand_search_terms(terms)
    assert 'knowledgebase' in expanded
    assert 'knowledgebases' in expanded
    assert 'agent' in expanded
    assert 'agents' in expanded


def test_calculate_match_score():
    """Test calculating match score."""
    item_text = 'This is a test item with some content'
    search_terms = ['test', 'content']
    name_parts = ['TestItem']

    result = search_utils.calculate_match_score(item_text, search_terms, name_parts)
    assert result['score'] > 0
    assert len(result['matched_terms']) > 0
    assert result['has_match'] is True


def test_search_items_with_terms():
    """Test searching items with terms."""
    items = [
        {'name': 'TestItem1', 'description': 'This is a test item'},
        {'name': 'TestItem2', 'description': 'This is another test item'},
    ]

    def get_text_fn(item):
        return item['description']

    def get_name_parts_fn(item):
        return [item['name']]

    results = search_utils.search_items_with_terms(items, ['test'], get_text_fn, get_name_parts_fn)

    assert len(results) == 2
    assert results[0]['score'] >= results[1]['score']
    assert 'test' in results[0]['matched_terms']
