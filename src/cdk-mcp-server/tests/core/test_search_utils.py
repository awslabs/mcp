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

"""Tests for search utilities."""

from awslabs.cdk_mcp_server.core.search_utils import (
    calculate_match_score,
    expand_search_terms,
    get_term_variations,
    normalize_term,
    search_items_with_terms,
)


def test_normalize_term():
    """Test normalizing terms for consistent matching."""
    # Test basic normalization
    assert normalize_term('TestTerm') == 'testterm'

    # Test with special characters and spacing
    assert normalize_term('test-term_example') == 'test term example'

    # Test with URL encoding
    assert normalize_term('test%20term') == 'test term'

    # Test with mixed case and multiple spaces
    assert normalize_term('  Test   TERM  ') == 'test term'

    # Test with other special characters
    assert normalize_term('test!@#$%^&*()term') == 'testterm'


def test_get_term_variations():
    """Test getting variations of terms."""
    # Test with a term that has known variations
    variations = get_term_variations('knowledgebase')
    assert 'knowledgebases' in variations
    assert 'knowledge-base' in variations

    # Test with singular/plural variations
    variations = get_term_variations('agent')
    assert 'agents' in variations

    # Test with a term that has no specific variations (should return at least the original)
    variations = get_term_variations('uniqueterm')
    assert 'uniqueterm' in variations
    assert len(variations) == 1

    # Test with AWS service abbreviations
    variations = get_term_variations('s3')
    assert 's3-bucket' in variations
    assert 'simple storage service' in variations


def test_expand_search_terms():
    """Test expanding a list of search terms with variations."""
    # Test with a single term
    expanded = expand_search_terms(['agent'])
    assert 'agent' in expanded
    assert 'agents' in expanded

    # Test with multiple terms, including some with variations
    expanded = expand_search_terms(['lambda', 's3'])
    assert 'lambda' in expanded
    assert 'lambdas' in expanded
    assert 'lambda function' in expanded
    assert 's3' in expanded
    assert 's3 bucket' in expanded  # Note: hyphens are converted to spaces in normalize_term

    # Test with terms that might have overlapping variations
    expanded = expand_search_terms(['knowledgebase', 'knowledge-base'])
    # Should deduplicate the variations
    assert expanded.count('knowledgebase') == 1
    assert expanded.count('knowledge base') == 1  # Hyphens are normalized to spaces

    # Test with URL encoded terms
    expanded = expand_search_terms(['lambda%20function'])
    assert 'lambda function' in expanded


def test_calculate_match_score_basic():
    """Test calculating match score with basic text matching."""
    # Test with exact match in text
    result = calculate_match_score('this is a test description', ['test'])
    assert result['score'] == 5
    assert 'test' in result['matched_terms']
    assert result['has_match'] is True

    # Test with multiple matches
    result = calculate_match_score(
        'test description with multiple test words', ['test', 'multiple']
    )
    assert result['score'] > 10  # Base score + bonus for multiple terms
    assert 'test' in result['matched_terms']
    assert 'multiple' in result['matched_terms']
    assert result['has_match'] is True

    # Test with no match
    result = calculate_match_score('this is a description', ['nonexistent'])
    assert result['score'] == 0
    assert len(result['matched_terms']) == 0
    assert result['has_match'] is False


def test_calculate_match_score_with_name_parts():
    """Test calculating match score with name parts for higher-weight matching."""
    # Test with match in name parts (higher weight)
    result = calculate_match_score(
        'this is a description', ['test'], name_parts=['test', 'component']
    )
    assert result['score'] == 10  # Higher weight for name part match
    assert 'test' in result['matched_terms']

    # Test with match in both name parts and text
    result = calculate_match_score(
        'this is a test description with component',
        ['test', 'component'],
        name_parts=['test', 'module'],
    )
    assert result['score'] >= 10  # Name part match + text match + bonus
    assert 'test' in result['matched_terms']
    assert 'component' in result['matched_terms']

    # Test with no match in name parts but match in text
    result = calculate_match_score(
        'this is a test description', ['test'], name_parts=['other', 'component']
    )
    assert result['score'] == 5  # Normal weight for text match
    assert 'test' in result['matched_terms']


def test_search_items_with_terms():
    """Test searching items with search terms."""
    # Create test items
    items = [
        {'id': 1, 'name': 'Lambda Function', 'description': 'AWS Lambda function integration'},
        {'id': 2, 'name': 'S3 Bucket', 'description': 'Simple storage service bucket'},
        {'id': 3, 'name': 'DynamoDB Table', 'description': 'NoSQL database service'},
    ]

    # Define extraction functions
    def get_text(item):
        return f'{item["name"]} {item["description"]}'

    def get_name_parts(item):
        return item['name'].split()

    # Test basic search
    results = search_items_with_terms(items, ['lambda'], get_text, get_name_parts)
    assert len(results) == 1
    assert results[0]['item']['id'] == 1

    # Test search with multiple terms
    results = search_items_with_terms(items, ['storage', 'bucket'], get_text, get_name_parts)
    assert len(results) == 1
    assert results[0]['item']['id'] == 2

    # Test search with term variations
    results = search_items_with_terms(items, ['s3'], get_text, get_name_parts)
    assert len(results) == 1
    assert results[0]['item']['id'] == 2

    # Test search with multiple matches, sorted by score
    results = search_items_with_terms(items, ['aws', 'service'], get_text, get_name_parts)
    assert len(results) > 1
    # Check sorting (highest score first)
    assert results[0]['score'] >= results[1]['score']

    # Test search with no matches
    results = search_items_with_terms(items, ['nonexistent'], get_text, get_name_parts)
    assert len(results) == 0


def test_search_items_without_name_parts():
    """Test searching items without name parts function."""
    # Create test items
    items = [
        {'id': 1, 'name': 'Lambda Function', 'description': 'AWS Lambda function integration'},
        {'id': 2, 'name': 'S3 Bucket', 'description': 'Simple storage service bucket'},
    ]

    # Define text extraction function
    def get_text(item):
        return f'{item["name"]} {item["description"]}'

    # Test search without name_parts_fn
    results = search_items_with_terms(items, ['lambda'], get_text)
    assert len(results) == 1
    assert results[0]['item']['id'] == 1

    # Ensure score calculation works properly without name parts
    assert results[0]['score'] > 0  # Ensure there is a positive score
