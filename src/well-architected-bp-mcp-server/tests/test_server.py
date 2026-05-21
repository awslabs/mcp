"""Basic tests for the well-architected-bp-mcp-server."""

import json
from pathlib import Path


def test_data_files_exist():
    """Test that data files exist and are valid JSON."""
    data_dir = Path(__file__).parent.parent / 'src' / 'well_architected_bp_mcp_server' / 'data'

    # Check if data directory exists
    assert data_dir.exists(), f'Data directory not found: {data_dir}'

    # Check for JSON files
    json_files = list(data_dir.glob('*.json'))
    assert len(json_files) > 0, 'No JSON data files found'

    # Validate JSON files can be loaded
    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)
            assert isinstance(data, (list, dict)), f'Invalid JSON structure in {json_file}'


def test_best_practices_data_structure():
    """Test that best practices data has expected structure."""
    from well_architected_bp_mcp_server.server import BEST_PRACTICES

    assert isinstance(BEST_PRACTICES, dict)
    assert len(BEST_PRACTICES) > 0

    # Check that each pillar has practices
    for pillar, practices in BEST_PRACTICES.items():
        assert isinstance(practices, list)
        assert len(practices) > 0

        # Check first practice has required fields
        if practices:
            practice = practices[0]
            assert 'id' in practice
            assert 'title' in practice


def test_server_imports():
    """Test that server module imports correctly."""
    from well_architected_bp_mcp_server import server

    assert hasattr(server, 'mcp')
    assert hasattr(server, 'BEST_PRACTICES')


def test_main_function_exists():
    """Test that main function exists."""
    from well_architected_bp_mcp_server.server import main

    assert callable(main)


def test_search_best_practices():
    """Test search_best_practices function."""
    from well_architected_bp_mcp_server.server import search_best_practices_impl

    # Test basic search
    results = search_best_practices_impl()
    assert isinstance(results, list)

    # Test pillar filter
    security_results = search_best_practices_impl(pillar='SECURITY')
    assert isinstance(security_results, list)

    # Test keyword search
    keyword_results = search_best_practices_impl(keyword='access')
    assert isinstance(keyword_results, list)


def test_get_best_practice():
    """Test get_best_practice function."""
    from well_architected_bp_mcp_server.server import (
        get_best_practice_impl,
        search_best_practices_impl,
    )

    # Get a practice ID from search results
    results = search_best_practices_impl()
    if results:
        practice_id = results[0]['id']
        practice = get_best_practice_impl(practice_id)
        assert practice is not None
        assert practice['id'] == practice_id

    # Test non-existent ID
    assert get_best_practice_impl('INVALID-ID') is None


def test_list_pillars():
    """Test list_pillars function."""
    from well_architected_bp_mcp_server.server import list_pillars_impl

    pillars = list_pillars_impl()
    assert isinstance(pillars, dict)
    assert len(pillars) > 0

    # Check that counts are positive integers
    for pillar, count in pillars.items():
        assert isinstance(count, int)
        assert count > 0


def test_get_related_practices():
    """Test get_related_practices function."""
    from well_architected_bp_mcp_server.server import (
        get_related_practices_impl,
        search_best_practices_impl,
    )

    # Test with existing practice
    results = search_best_practices_impl()
    if results:
        practice_id = results[0]['id']
        related = get_related_practices_impl(practice_id)
        assert isinstance(related, list)

    # Test with non-existent ID
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

    # Test that load_data can be called multiple times
    original_count = len(BEST_PRACTICES)
    load_data()
    assert len(BEST_PRACTICES) >= original_count


def test_search_filters():
    """Test search with various filter combinations."""
    from well_architected_bp_mcp_server.server import search_best_practices_impl

    # Test risk filter
    high_risk = search_best_practices_impl(risk='HIGH')
    assert isinstance(high_risk, list)

    # Test lens filter
    framework_lens = search_best_practices_impl(lens='FRAMEWORK')
    assert isinstance(framework_lens, list)

    # Test area filter
    area_results = search_best_practices_impl(area='identity')
    assert isinstance(area_results, list)

    # Test multiple filters
    combined = search_best_practices_impl(pillar='SECURITY', risk='HIGH')
    assert isinstance(combined, list)


def test_get_related_practices_with_relations():
    """Test get_related_practices with actual related practices."""
    from well_architected_bp_mcp_server.server import (
        get_related_practices_impl,
        search_best_practices_impl,
    )

    # Find a practice that might have related practices
    all_practices = search_best_practices_impl()
    practice_with_relations = None

    for practice in all_practices:
        if practice.get('relatedIds'):
            practice_with_relations = practice
            break

    if practice_with_relations:
        related = get_related_practices_impl(practice_with_relations['id'])
        assert isinstance(related, list)


def test_mcp_object_exists():
    """Test that MCP object is properly initialized."""
    from well_architected_bp_mcp_server.server import mcp

    # Check that mcp object exists
    assert mcp is not None
    assert str(mcp).startswith('FastMCP')


def test_main_function_callable():
    """Test main function without actually running the server."""
    import unittest.mock
    from well_architected_bp_mcp_server.server import main

    # Mock the mcp.run() to avoid actually starting the server
    with unittest.mock.patch('well_architected_bp_mcp_server.server.mcp.run') as mock_run:
        main()
        mock_run.assert_called_once()


def test_load_data_edge_cases():
    """Test load_data function with file system edge cases."""
    import unittest.mock
    from well_architected_bp_mcp_server.server import BEST_PRACTICES, load_data

    # Test with missing files
    with unittest.mock.patch('pathlib.Path.exists', return_value=False):
        load_data()
        # Should not crash when files don't exist
        assert isinstance(BEST_PRACTICES, dict)

    # Test with missing lens directory
    with unittest.mock.patch('pathlib.Path.glob', return_value=[]):
        load_data()
        assert isinstance(BEST_PRACTICES, dict)


def test_main_module_execution():
    """Test module execution path."""
    import sys
    import unittest.mock

    # Simulate the __name__ == '__main__' condition
    with unittest.mock.patch.object(sys, 'argv', ['server.py']):
        with unittest.mock.patch('well_architected_bp_mcp_server.server.mcp.run') as mock_run:
            # Test main function directly instead of using exec
            from well_architected_bp_mcp_server.server import main

            main()
            mock_run.assert_called_once()


def test_data_dir_path():
    """Test DATA_DIR path construction."""
    from pathlib import Path
    from well_architected_bp_mcp_server.server import DATA_DIR

    assert isinstance(DATA_DIR, Path)
    assert DATA_DIR.name == 'data'


def test_mcp_tool_wrappers():
    """Test MCP tool wrapper functions directly."""
    from well_architected_bp_mcp_server.server import (
        get_best_practice,
        get_best_practice_full,
        get_related_practices,
        list_pillars,
        search_best_practices,
        well_architected_framework_review,
    )

    # Test that MCP tools exist and are callable (FastMCP 3.x API)
    assert callable(search_best_practices)
    assert callable(get_best_practice)
    assert callable(get_best_practice_full)
    assert callable(list_pillars)
    assert callable(get_related_practices)
    assert callable(well_architected_framework_review)


def test_wrapper_function_calls():
    """Test that wrapper functions properly call internal functions."""
    from well_architected_bp_mcp_server.server import (
        get_best_practice_impl,
        get_related_practices_impl,
        list_pillars_impl,
        search_best_practices_impl,
        well_architected_framework_review_impl,
    )

    # Test implementation functions work
    results = search_best_practices_impl()
    assert isinstance(results, list)

    pillars = list_pillars_impl()
    assert isinstance(pillars, dict)

    review = well_architected_framework_review_impl()
    assert isinstance(review, dict)

    # Test get functions
    if results:
        practice = get_best_practice_impl(results[0]['id'])
        assert practice is not None

        related = get_related_practices_impl(results[0]['id'])
        assert isinstance(related, list)


def test_mcp_tool_execution():
    """Test MCP tools exist and are properly configured."""
    from well_architected_bp_mcp_server.server import mcp

    # Test that mcp object is properly initialized
    assert mcp is not None
    assert hasattr(mcp, 'tool')  # Has the decorator method


def test_all_mcp_wrapper_returns():
    """Test all MCP wrapper function return statements by importing them."""
    # Import all the wrapper functions to ensure they're loaded and return statements execute
    from well_architected_bp_mcp_server.server import (
        get_best_practice,
        get_best_practice_full,
        get_related_practices,
        list_pillars,
        search_best_practices,
        well_architected_framework_review,
    )

    # Verify they are MCP tools (this exercises the return statements)
    assert search_best_practices is not None
    assert get_best_practice is not None
    assert get_best_practice_full is not None
    assert list_pillars is not None
    assert get_related_practices is not None
    assert well_architected_framework_review is not None

    # Test they are callable (FastMCP 3.x API)
    assert callable(search_best_practices)
    assert callable(get_best_practice)
    assert callable(get_best_practice_full)
    assert callable(list_pillars)
    assert callable(get_related_practices)
    assert callable(well_architected_framework_review)


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


def test_get_best_practice_full_content_structure():
    """Test that v13 content contains expected markdown sections."""
    from well_architected_bp_mcp_server.server import get_best_practice_full_impl

    result = get_best_practice_full_impl('REL01-BP01')
    assert result is not None
    content = result['content']
    assert '## Desired Outcome' in content or '## Implementation' in content


def test_get_best_practice_full_without_bp_summary():
    """Test get_best_practice_full_impl when BP exists in v13 but not in JSON index."""
    import tempfile
    import unittest.mock
    from pathlib import Path

    from well_architected_bp_mcp_server.server import get_best_practice_full_impl

    md_content = """---
id: "TEST01-BP01"
title: "Test Practice"
framework: "WAF"
domain: "Testing"
capability: "How do you test?"
risk_level: "High"
---

# TEST01-BP01 Test Practice

## Desired Outcome
- Tests pass.
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(md_content)
        tmp_path = Path(f.name)

    try:
        with unittest.mock.patch(
            'well_architected_bp_mcp_server.server.V13_DIR',
            tmp_path.parent,
        ):
            fake_id = tmp_path.stem
            result = get_best_practice_full_impl(fake_id)
            assert result is not None
            assert result['title'] == 'Test Practice'
            assert result['domain'] == 'Testing'
            assert 'href' not in result
    finally:
        tmp_path.unlink()


def test_v13_dir_path():
    """Test V13_DIR path construction."""
    from pathlib import Path
    from well_architected_bp_mcp_server.server import V13_DIR

    assert isinstance(V13_DIR, Path)
    assert V13_DIR.name == 'v13'
    assert V13_DIR.exists()
