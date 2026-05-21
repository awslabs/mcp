"""Tests for the well-architected-bp-mcp-server."""

import json
import unittest.mock
from pathlib import Path


def test_data_files_exist():
    """Test that data files exist and are valid JSON."""
    data_dir = Path(__file__).parent.parent / 'src' / 'well_architected_bp_mcp_server' / 'data'

    assert data_dir.exists(), f'Data directory not found: {data_dir}'

    json_files = list(data_dir.glob('*.json'))
    assert len(json_files) > 0, 'No JSON data files found'

    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)
            assert isinstance(data, (list, dict)), f'Invalid JSON structure in {json_file}'


def test_best_practices_data_structure():
    """Test that best practices data has expected structure."""
    from well_architected_bp_mcp_server.server import BEST_PRACTICES

    assert isinstance(BEST_PRACTICES, dict)
    assert len(BEST_PRACTICES) > 0

    for pillar, practices in BEST_PRACTICES.items():
        assert isinstance(practices, list)
        assert len(practices) > 0

        if practices:
            practice = practices[0]
            assert 'id' in practice
            assert 'title' in practice


def test_server_imports():
    """Test that server module imports correctly."""
    from well_architected_bp_mcp_server import server

    assert hasattr(server, 'mcp')
    assert hasattr(server, 'BEST_PRACTICES')
    assert hasattr(server, 'V13_SECTIONS')
    assert hasattr(server, 'QUESTIONS_INDEX')


def test_main_function_exists():
    """Test that main function exists."""
    from well_architected_bp_mcp_server.server import main

    assert callable(main)


def test_search_best_practices():
    """Test search_best_practices_impl returns paginated results."""
    from well_architected_bp_mcp_server.server import search_best_practices_impl

    result = search_best_practices_impl()
    assert isinstance(result, dict)
    assert 'results' in result
    assert 'total_count' in result
    assert 'offset' in result
    assert 'has_more' in result
    assert isinstance(result['results'], list)
    assert result['total_count'] > 0

    security_results = search_best_practices_impl(pillar='SECURITY')
    assert security_results['total_count'] > 0
    assert all(bp.get('pillar') == 'SECURITY' for bp in security_results['results'])

    keyword_results = search_best_practices_impl(keyword='access')
    assert isinstance(keyword_results['results'], list)


def test_search_best_practices_pagination():
    """Test pagination in search_best_practices_impl."""
    from well_architected_bp_mcp_server.server import search_best_practices_impl

    page1 = search_best_practices_impl(max_results=5, offset=0)
    assert len(page1['results']) == 5
    assert page1['has_more'] is True

    page2 = search_best_practices_impl(max_results=5, offset=5)
    assert len(page2['results']) == 5
    assert page2['offset'] == 5
    assert page1['results'][0]['id'] != page2['results'][0]['id']

    big_offset = search_best_practices_impl(max_results=5, offset=9999)
    assert len(big_offset['results']) == 0


def test_get_best_practice():
    """Test get_best_practice function."""
    from well_architected_bp_mcp_server.server import (
        get_best_practice_impl,
        search_best_practices_impl,
    )

    results = search_best_practices_impl()
    if results['results']:
        practice_id = results['results'][0]['id']
        practice = get_best_practice_impl(practice_id)
        assert practice is not None
        assert practice['id'] == practice_id

    assert get_best_practice_impl('INVALID-ID') is None


def test_list_pillars():
    """Test list_pillars function returns rich metadata."""
    from well_architected_bp_mcp_server.server import list_pillars_impl

    pillars = list_pillars_impl()
    assert isinstance(pillars, dict)
    assert len(pillars) > 0

    for pillar, data in pillars.items():
        assert 'total' in data
        assert 'risk_distribution' in data
        assert 'areas' in data
        assert 'questions_count' in data
        assert isinstance(data['total'], int)
        assert data['total'] > 0
        assert isinstance(data['areas'], list)
        assert isinstance(data['risk_distribution'], dict)


def test_get_related_practices():
    """Test get_related_practices function."""
    from well_architected_bp_mcp_server.server import (
        get_related_practices_impl,
        search_best_practices_impl,
    )

    results = search_best_practices_impl()
    if results['results']:
        practice_id = results['results'][0]['id']
        related = get_related_practices_impl(practice_id)
        assert isinstance(related, list)

    related = get_related_practices_impl('INVALID-ID')
    assert related == []


def test_well_architected_framework_review():
    """Test well_architected_framework_review function."""
    from well_architected_bp_mcp_server.server import well_architected_framework_review_impl

    review = well_architected_framework_review_impl()
    assert isinstance(review, dict)
    assert 'framework' in review
    assert 'pillars' in review
    assert 'total_practices' in review
    assert review['framework'] == 'AWS Well-Architected Framework'
    assert isinstance(review['total_practices'], int)
    assert review['total_practices'] > 0


def test_load_data_function():
    """Test load_data function and data loading edge cases."""
    from well_architected_bp_mcp_server.server import BEST_PRACTICES, load_data

    original_count = len(BEST_PRACTICES)
    load_data()
    assert len(BEST_PRACTICES) >= original_count


def test_search_filters():
    """Test search with various filter combinations."""
    from well_architected_bp_mcp_server.server import search_best_practices_impl

    high_risk = search_best_practices_impl(risk='HIGH')
    assert isinstance(high_risk['results'], list)

    framework_lens = search_best_practices_impl(lens='FRAMEWORK')
    assert isinstance(framework_lens['results'], list)

    area_results = search_best_practices_impl(area='identity')
    assert isinstance(area_results['results'], list)

    combined = search_best_practices_impl(pillar='SECURITY', risk='HIGH')
    assert isinstance(combined['results'], list)


def test_get_related_practices_with_relations():
    """Test get_related_practices with actual related practices."""
    from well_architected_bp_mcp_server.server import (
        get_related_practices_impl,
        search_best_practices_impl,
    )

    all_practices = search_best_practices_impl(max_results=50)
    practice_with_relations = None

    for practice in all_practices['results']:
        if practice.get('relatedIds'):
            practice_with_relations = practice
            break

    if practice_with_relations:
        related = get_related_practices_impl(practice_with_relations['id'])
        assert isinstance(related, list)


def test_mcp_object_exists():
    """Test that MCP object is properly initialized."""
    from well_architected_bp_mcp_server.server import mcp

    assert mcp is not None
    assert str(mcp).startswith('FastMCP')


def test_main_function_callable():
    """Test main function without actually running the server."""
    from well_architected_bp_mcp_server.server import main

    with unittest.mock.patch('well_architected_bp_mcp_server.server.mcp.run') as mock_run:
        main()
        mock_run.assert_called_once()


def test_load_data_edge_cases():
    """Test load_data function with file system edge cases."""
    from well_architected_bp_mcp_server.server import BEST_PRACTICES, load_data

    with unittest.mock.patch('pathlib.Path.exists', return_value=False):
        load_data()
        assert isinstance(BEST_PRACTICES, dict)

    with unittest.mock.patch('pathlib.Path.glob', return_value=[]):
        load_data()
        assert isinstance(BEST_PRACTICES, dict)


def test_main_module_execution():
    """Test module execution path."""
    import sys

    with unittest.mock.patch.object(sys, 'argv', ['server.py']):
        with unittest.mock.patch('well_architected_bp_mcp_server.server.mcp.run') as mock_run:
            from well_architected_bp_mcp_server.server import main

            main()
            mock_run.assert_called_once()


def test_data_dir_path():
    """Test DATA_DIR path construction."""
    from well_architected_bp_mcp_server.server import DATA_DIR

    assert isinstance(DATA_DIR, Path)
    assert DATA_DIR.name == 'data'


def test_v13_dir_path():
    """Test V13_DIR path construction."""
    from well_architected_bp_mcp_server.server import V13_DIR

    assert isinstance(V13_DIR, Path)
    assert V13_DIR.name == 'v13'
    assert V13_DIR.exists()


# --- Tests for new tools ---


def test_search_content():
    """Test search_content_impl full-text search."""
    from well_architected_bp_mcp_server.server import search_content_impl

    results = search_content_impl('DynamoDB')
    assert isinstance(results, list)
    assert len(results) > 0
    assert 'id' in results[0]
    assert 'matched_section' in results[0]
    assert 'snippet' in results[0]
    assert 'DynamoDB' in results[0]['snippet'] or 'dynamodb' in results[0]['snippet'].lower()


def test_search_content_with_pillar_filter():
    """Test search_content_impl with pillar filter."""
    from well_architected_bp_mcp_server.server import search_content_impl

    results = search_content_impl('CloudTrail', pillar='SECURITY')
    assert isinstance(results, list)
    for r in results:
        assert r['pillar'] == 'SECURITY'


def test_search_content_with_section_filter():
    """Test search_content_impl with section filter."""
    from well_architected_bp_mcp_server.server import search_content_impl

    results = search_content_impl('automat', section='implementation_steps')
    assert isinstance(results, list)
    for r in results:
        assert r['matched_section'] == 'Implementation Steps'


def test_search_content_no_results():
    """Test search_content_impl with query that has no matches."""
    from well_architected_bp_mcp_server.server import search_content_impl

    results = search_content_impl('zzznomatchxyzzzz')
    assert results == []


def test_search_content_max_results():
    """Test search_content_impl respects max_results."""
    from well_architected_bp_mcp_server.server import search_content_impl

    results = search_content_impl('AWS', max_results=3)
    assert len(results) <= 3


def test_list_questions():
    """Test list_questions_impl returns WAR questions."""
    from well_architected_bp_mcp_server.server import list_questions_impl

    questions = list_questions_impl()
    assert isinstance(questions, list)
    assert len(questions) == 57

    for q in questions:
        assert 'pillar' in q
        assert 'question' in q
        assert 'practice_count' in q
        assert q['practice_count'] > 0


def test_list_questions_with_pillar():
    """Test list_questions_impl filtered by pillar."""
    from well_architected_bp_mcp_server.server import list_questions_impl

    security_qs = list_questions_impl(pillar='SECURITY')
    assert len(security_qs) > 0
    for q in security_qs:
        assert q['pillar'] == 'Security'

    reliability_qs = list_questions_impl(pillar='RELIABILITY')
    assert len(reliability_qs) > 0
    for q in reliability_qs:
        assert q['pillar'] == 'Reliability'


def test_get_practices_for_question():
    """Test get_practices_for_question_impl returns BPs ordered by risk."""
    from well_architected_bp_mcp_server.server import get_practices_for_question_impl

    results = get_practices_for_question_impl('operate your workload')
    assert isinstance(results, list)
    assert len(results) > 0

    for r in results:
        assert 'id' in r
        assert 'title' in r
        assert 'risk' in r
        assert 'area' in r

    risk_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    for i in range(len(results) - 1):
        assert risk_order.get(results[i]['risk'], 9) <= risk_order.get(results[i + 1]['risk'], 9)


def test_get_practices_for_question_no_match():
    """Test get_practices_for_question_impl with no matching question."""
    from well_architected_bp_mcp_server.server import get_practices_for_question_impl

    results = get_practices_for_question_impl('zzznoquestionmatchzzz')
    assert results == []


def test_get_anti_patterns_by_id():
    """Test get_anti_patterns_impl for a specific BP."""
    from well_architected_bp_mcp_server.server import get_anti_patterns_impl

    results = get_anti_patterns_impl(id='SEC01-BP01')
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]['id'] == 'SEC01-BP01'
    assert isinstance(results[0]['anti_patterns'], list)
    assert len(results[0]['anti_patterns']) > 0


def test_get_anti_patterns_by_pillar():
    """Test get_anti_patterns_impl filtered by pillar."""
    from well_architected_bp_mcp_server.server import get_anti_patterns_impl

    results = get_anti_patterns_impl(pillar='SECURITY')
    assert isinstance(results, list)
    assert len(results) > 0


def test_get_anti_patterns_by_risk():
    """Test get_anti_patterns_impl filtered by risk."""
    from well_architected_bp_mcp_server.server import get_anti_patterns_impl

    results = get_anti_patterns_impl(risk='HIGH')
    assert isinstance(results, list)
    assert len(results) > 0
    for r in results:
        assert r['risk'] == 'HIGH'


def test_get_anti_patterns_combined_filters():
    """Test get_anti_patterns_impl with pillar and risk filters."""
    from well_architected_bp_mcp_server.server import get_anti_patterns_impl

    results = get_anti_patterns_impl(pillar='RELIABILITY', risk='HIGH')
    assert isinstance(results, list)
    assert len(results) > 0


def test_get_anti_patterns_no_match():
    """Test get_anti_patterns_impl for BP without anti-patterns section."""
    from well_architected_bp_mcp_server.server import get_anti_patterns_impl

    results = get_anti_patterns_impl(id='NONEXISTENT-BP99')
    assert results == []


def test_get_best_practice_full_with_v13():
    """Test get_best_practice_full_impl returns full markdown content from v13."""
    from well_architected_bp_mcp_server.server import get_best_practice_full_impl

    result = get_best_practice_full_impl('SEC01-BP01')
    assert result is not None
    assert result['id'] == 'SEC01-BP01'
    assert result['title'] == 'Separate workloads using accounts'
    assert result['domain'] == 'Security'
    assert result['capability'] != ''
    assert result['risk_level'] == 'High'
    assert '## Implementation' in result['content']
    assert result['href'] != ''
    assert result['pillar'] == 'SECURITY'
    assert isinstance(result['area'], list)
    assert isinstance(result['relatedIds'], list)


def test_get_best_practice_full_section_filter():
    """Test get_best_practice_full_impl with section filter."""
    from well_architected_bp_mcp_server.server import get_best_practice_full_impl

    result = get_best_practice_full_impl('SEC01-BP01', section='implementation_steps')
    assert result is not None
    assert '## ' not in result['content']
    assert len(result['content']) < 5000

    result_ap = get_best_practice_full_impl('SEC01-BP01', section='anti_patterns')
    assert result_ap is not None
    assert result_ap['content'] != result['content']


def test_get_best_practice_full_invalid_section():
    """Test get_best_practice_full_impl with invalid section."""
    from well_architected_bp_mcp_server.server import get_best_practice_full_impl

    result = get_best_practice_full_impl('SEC01-BP01', section='nonexistent_section')
    assert result is not None
    assert 'not found' in result['content']


def test_get_best_practice_full_nonexistent_id():
    """Test get_best_practice_full_impl falls back for IDs not in v13."""
    from well_architected_bp_mcp_server.server import get_best_practice_full_impl

    result = get_best_practice_full_impl('NONEXISTENT-BP99')
    assert result is None


def test_get_best_practice_full_falls_back_to_json():
    """Test get_best_practice_full_impl falls back to JSON for lens BPs without v13."""
    from well_architected_bp_mcp_server.server import get_best_practice_full_impl

    result = get_best_practice_full_impl('GENOPS01-BP01')
    assert result is not None
    assert result['id'] == 'GENOPS01-BP01'
    assert 'content' not in result


def test_get_best_practice_full_frontmatter_parsing():
    """Test that frontmatter is correctly parsed from v13 markdown."""
    from well_architected_bp_mcp_server.server import get_best_practice_full_impl

    result = get_best_practice_full_impl('OPS01-BP01')
    assert result is not None
    assert result['id'] == 'OPS01-BP01'
    assert result['domain'] == 'Operational Excellence'
    assert 'content' in result
    assert not result['content'].startswith('---')


def test_v13_index_built():
    """Test that V13 index was built at startup."""
    from well_architected_bp_mcp_server.server import QUESTIONS_INDEX, V13_SECTIONS

    assert len(V13_SECTIONS) == 307
    assert len(QUESTIONS_INDEX) == 57

    sample = V13_SECTIONS.get('SEC01-BP01', {})
    assert '_full' in sample
    assert 'Anti-Patterns' in sample or 'Implementation Steps' in sample


def test_build_v13_index_missing_dir():
    """Test _build_v13_index handles missing directory."""
    from well_architected_bp_mcp_server.server import _build_v13_index

    with unittest.mock.patch(
        'well_architected_bp_mcp_server.server.V13_DIR',
        Path('/nonexistent/path'),
    ):
        _build_v13_index()


def test_mcp_tool_wrappers():
    """Test MCP tool wrapper functions directly."""
    from well_architected_bp_mcp_server.server import (
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

    assert callable(search_best_practices)
    assert callable(search_content)
    assert callable(get_best_practice)
    assert callable(get_best_practice_full)
    assert callable(list_questions)
    assert callable(get_practices_for_question)
    assert callable(get_anti_patterns)
    assert callable(list_pillars)
    assert callable(get_related_practices)
    assert callable(well_architected_framework_review)


def test_wrapper_function_calls():
    """Test that wrapper functions properly call internal functions."""
    from well_architected_bp_mcp_server.server import (
        get_best_practice_impl,
        get_related_practices_impl,
        list_pillars_impl,
        list_questions_impl,
        search_best_practices_impl,
        well_architected_framework_review_impl,
    )

    results = search_best_practices_impl()
    assert isinstance(results, dict)

    pillars = list_pillars_impl()
    assert isinstance(pillars, dict)

    review = well_architected_framework_review_impl()
    assert isinstance(review, dict)

    questions = list_questions_impl()
    assert isinstance(questions, list)

    if results['results']:
        practice = get_best_practice_impl(results['results'][0]['id'])
        assert practice is not None

        related = get_related_practices_impl(results['results'][0]['id'])
        assert isinstance(related, list)
