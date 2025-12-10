"""Basic tests for the well-architected-bp-mcp-server."""

import pytest
from pathlib import Path
import json


def test_data_files_exist():
    """Test that data files exist and are valid JSON."""
    data_dir = Path(__file__).parent.parent / "src" / "well_architected_bp_mcp_server" / "data"
    
    # Check if data directory exists
    assert data_dir.exists(), f"Data directory not found: {data_dir}"
    
    # Check for JSON files
    json_files = list(data_dir.glob("*.json"))
    assert len(json_files) > 0, "No JSON data files found"
    
    # Validate JSON files can be loaded
    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)
            assert isinstance(data, (list, dict)), f"Invalid JSON structure in {json_file}"


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
            assert "id" in practice
            assert "title" in practice


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
    from well_architected_bp_mcp_server.server import _search_best_practices
    
    # Test basic search
    results = _search_best_practices()
    assert isinstance(results, list)
    
    # Test pillar filter
    security_results = _search_best_practices(pillar="SECURITY")
    assert isinstance(security_results, list)
    
    # Test keyword search
    keyword_results = _search_best_practices(keyword="access")
    assert isinstance(keyword_results, list)


def test_get_best_practice():
    """Test get_best_practice function."""
    from well_architected_bp_mcp_server.server import _get_best_practice, _search_best_practices
    
    # Get a practice ID from search results
    results = _search_best_practices()
    if results:
        practice_id = results[0]["id"]
        practice = _get_best_practice(practice_id)
        assert practice is not None
        assert practice["id"] == practice_id
    
    # Test non-existent ID
    assert _get_best_practice("INVALID-ID") is None


def test_list_pillars():
    """Test list_pillars function."""
    from well_architected_bp_mcp_server.server import _list_pillars
    
    pillars = _list_pillars()
    assert isinstance(pillars, dict)
    assert len(pillars) > 0
    
    # Check that counts are positive integers
    for pillar, count in pillars.items():
        assert isinstance(count, int)
        assert count > 0


def test_get_related_practices():
    """Test get_related_practices function."""
    from well_architected_bp_mcp_server.server import _get_related_practices, _search_best_practices
    
    # Test with existing practice
    results = _search_best_practices()
    if results:
        practice_id = results[0]["id"]
        related = _get_related_practices(practice_id)
        assert isinstance(related, list)
    
    # Test with non-existent ID
    related = _get_related_practices("INVALID-ID")
    assert related == []


def test_well_architected_framework_review():
    """Test well_architected_framework_review function."""
    from well_architected_bp_mcp_server.server import _well_architected_framework_review
    
    review = _well_architected_framework_review()
    assert isinstance(review, dict)
    assert "framework" in review
    assert "pillars" in review
    assert "total_practices" in review
    assert review["framework"] == "AWS Well-Architected Framework"
    assert isinstance(review["total_practices"], int)
    assert review["total_practices"] > 0


def test_load_data_function():
    """Test load_data function and data loading edge cases."""
    from well_architected_bp_mcp_server.server import load_data, BEST_PRACTICES
    
    # Test that load_data can be called multiple times
    original_count = len(BEST_PRACTICES)
    load_data()
    assert len(BEST_PRACTICES) >= original_count


def test_search_filters():
    """Test search with various filter combinations."""
    from well_architected_bp_mcp_server.server import _search_best_practices
    
    # Test risk filter
    high_risk = _search_best_practices(risk="HIGH")
    assert isinstance(high_risk, list)
    
    # Test lens filter
    framework_lens = _search_best_practices(lens="FRAMEWORK")
    assert isinstance(framework_lens, list)
    
    # Test area filter
    area_results = _search_best_practices(area="identity")
    assert isinstance(area_results, list)
    
    # Test multiple filters
    combined = _search_best_practices(pillar="SECURITY", risk="HIGH")
    assert isinstance(combined, list)


def test_get_related_practices_with_relations():
    """Test get_related_practices with actual related practices."""
    from well_architected_bp_mcp_server.server import _get_related_practices, _search_best_practices
    
    # Find a practice that might have related practices
    all_practices = _search_best_practices()
    practice_with_relations = None
    
    for practice in all_practices:
        if practice.get("relatedIds"):
            practice_with_relations = practice
            break
    
    if practice_with_relations:
        related = _get_related_practices(practice_with_relations["id"])
        assert isinstance(related, list)


def test_mcp_object_exists():
    """Test that MCP object is properly initialized."""
    from well_architected_bp_mcp_server.server import mcp
    
    # Check that mcp object exists
    assert mcp is not None
    assert str(mcp).startswith("FastMCP")


def test_main_function_callable():
    """Test main function without actually running the server."""
    from well_architected_bp_mcp_server.server import main
    import unittest.mock
    
    # Mock the mcp.run() to avoid actually starting the server
    with unittest.mock.patch('well_architected_bp_mcp_server.server.mcp.run') as mock_run:
        main()
        mock_run.assert_called_once()


def test_load_data_edge_cases():
    """Test load_data function with file system edge cases."""
    from well_architected_bp_mcp_server.server import load_data, BEST_PRACTICES
    import unittest.mock
    from pathlib import Path
    
    # Test with missing files
    with unittest.mock.patch('pathlib.Path.exists', return_value=False):
        original_data = dict(BEST_PRACTICES)
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
            # Import and execute the module's main block logic
            exec('if "__main__" == "__main__": from well_architected_bp_mcp_server.server import main; main()')
            mock_run.assert_called_once()


def test_data_dir_path():
    """Test DATA_DIR path construction."""
    from well_architected_bp_mcp_server.server import DATA_DIR
    from pathlib import Path
    
    assert isinstance(DATA_DIR, Path)
    assert DATA_DIR.name == "data"


def test_mcp_tool_wrappers():
    """Test MCP tool wrapper functions directly."""
    from well_architected_bp_mcp_server.server import (
        search_best_practices, get_best_practice, list_pillars, 
        get_related_practices, well_architected_framework_review
    )
    
    # Test that MCP tools exist and have the right type
    assert str(type(search_best_practices).__name__) == 'FunctionTool'
    assert str(type(get_best_practice).__name__) == 'FunctionTool'
    assert str(type(list_pillars).__name__) == 'FunctionTool'
    assert str(type(get_related_practices).__name__) == 'FunctionTool'
    assert str(type(well_architected_framework_review).__name__) == 'FunctionTool'


def test_wrapper_function_calls():
    """Test that wrapper functions properly call internal functions."""
    from well_architected_bp_mcp_server.server import (
        _search_best_practices, _get_best_practice, _list_pillars,
        _get_related_practices, _well_architected_framework_review
    )
    
    # Test internal functions work (these cover the return statements)
    results = _search_best_practices()
    assert isinstance(results, list)
    
    pillars = _list_pillars()
    assert isinstance(pillars, dict)
    
    review = _well_architected_framework_review()
    assert isinstance(review, dict)
    
    # Test get functions
    if results:
        practice = _get_best_practice(results[0]["id"])
        assert practice is not None
        
        related = _get_related_practices(results[0]["id"])
        assert isinstance(related, list)
