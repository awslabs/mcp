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
