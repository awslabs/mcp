import pytest
import tempfile
from awslabs.aws_api_mcp_server.core.agent_scripts.manager import AgentScriptsManager
from awslabs.aws_api_mcp_server.core.agent_scripts.models import Script
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def test_registry_dir():
    """Fixture for test registry directory."""
    return Path(__file__).parent / 'test_registry'


def test_get_script_existing(test_registry_dir):
    """Test getting an existing script."""
    manager = AgentScriptsManager(scripts_dir=test_registry_dir)

    script = manager.get_script('test_script')
    assert script is not None
    assert script.name == 'test_script'
    assert script.description == 'This is a test script.'
    assert script.content == '# Test Script 1\n\n<Agent Script Content>'


def test_get_script_another_valid(test_registry_dir):
    """Test getting another valid script."""
    manager = AgentScriptsManager(scripts_dir=test_registry_dir)

    script = manager.get_script('valid_script')
    assert script is not None
    assert script.name == 'valid_script'
    assert script.description == 'A valid test script with proper frontmatter'
    assert 'This is a valid script with proper frontmatter' in script.content


def test_initialization_with_valid_scripts(test_registry_dir):
    """Test initialization with valid scripts directory containing multiple scripts."""
    manager = AgentScriptsManager(scripts_dir=test_registry_dir)

    # Should load all valid scripts
    assert 'test_script' in manager.scripts
    assert 'valid_script' in manager.scripts
    assert 'another_valid_script' in manager.scripts


def test_initialization_with_non_existent_directory():
    """Test initialization with non-existent scripts directory."""
    non_existent_dir = Path(__file__).parent / 'non_existent_registry'

    with pytest.raises(RuntimeError, match=f'Scripts directory {non_existent_dir} does not exist'):
        AgentScriptsManager(scripts_dir=non_existent_dir)


def test_initialization_with_empty_directory():
    """Test initialization with empty scripts directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        empty_dir = Path(temp_dir)
        manager = AgentScriptsManager(scripts_dir=empty_dir)
        assert manager.scripts == {}


def test_initialization_with_script_missing_description():
    """Test initialization with script missing description metadata."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)

        script_content = """---
title: Script without description
---
# Script Content
"""

        script_file = test_dir / 'missing_desc.script.md'
        script_file.write_text(script_content)

        with pytest.raises(RuntimeError, match='has no "description" metadata in front matter'):
            AgentScriptsManager(scripts_dir=test_dir)


def test_initialization_with_malformed_frontmatter():
    """Test initialization with script having malformed frontmatter."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)

        script_content = """---
description: This script has malformed frontmatter
invalid: yaml: syntax: error
---
# Script Content
"""

        script_file = test_dir / 'malformed.script.md'
        script_file.write_text(script_content)

        with pytest.raises(Exception):
            AgentScriptsManager(scripts_dir=test_dir)


def test_script_name_extraction(test_registry_dir):
    """Test that script names are correctly extracted from filenames."""
    manager = AgentScriptsManager(scripts_dir=test_registry_dir)

    assert 'test_script' in manager.scripts
    assert 'valid_script' in manager.scripts
    assert 'another_valid_script' in manager.scripts


def test_script_content_parsing(test_registry_dir):
    """Test that script content is correctly parsed from frontmatter."""
    manager = AgentScriptsManager(scripts_dir=test_registry_dir)

    script = manager.get_script('test_script')
    assert script is not None
    assert script.content == '# Test Script 1\n\n<Agent Script Content>'

    script = manager.get_script('valid_script')
    assert script is not None
    assert 'This is a valid script with proper frontmatter' in script.content
    assert '## Steps' in script.content


def test_pretty_print_scripts(test_registry_dir):
    """Test pretty printing of scripts."""
    manager = AgentScriptsManager(scripts_dir=test_registry_dir)

    result = manager.pretty_print_scripts()

    assert '* test_script : This is a test script.' in result
    assert '* valid_script : A valid test script with proper frontmatter' in result
    assert (
        '* another_valid_script : Another valid test script for multiple script testing' in result
    )


def test_pretty_print_scripts_empty(test_registry_dir):
    """Test pretty printing with empty scripts."""
    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('pathlib.Path.glob', return_value=[]),
    ):
        manager = AgentScriptsManager(scripts_dir=test_registry_dir)
        result = manager.pretty_print_scripts()
        assert result == ''


def test_pretty_print_scripts_single(test_registry_dir):
    """Test pretty printing with single script."""
    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('pathlib.Path.glob', return_value=[]),
    ):
        manager = AgentScriptsManager(scripts_dir=test_registry_dir)
        manager.scripts = {
            'single_script': Script(
                name='single_script', description='Single script description', content='Content'
            )
        }

        result = manager.pretty_print_scripts()
        expected = '* single_script : Single script description\n'
        assert result == expected


def test_manager_scripts_property(test_registry_dir):
    """Test that scripts property is accessible and contains expected data."""
    manager = AgentScriptsManager(scripts_dir=test_registry_dir)

    assert isinstance(manager.scripts, dict)
    assert len(manager.scripts) == 3

    for script_name, script in manager.scripts.items():
        assert isinstance(script, Script)
        assert script.name == script_name
        assert script.description is not None
        assert script.content is not None


def test_script_with_complex_content(test_registry_dir):
    """Test loading script with complex markdown content."""
    manager = AgentScriptsManager(scripts_dir=test_registry_dir)

    script = manager.get_script('valid_script')
    assert script is not None
    assert '## Steps' in script.content
    assert '1. First step' in script.content
    assert '2. Second step' in script.content
    assert '3. Third step' in script.content


def test_script_with_multiline_description():
    """Test handling of script with multiline description."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)

        script_content = """---
description: |
  This is a multiline description
  that spans multiple lines
  for testing purposes
---
# Script Content
"""

        script_file = test_dir / 'multiline_desc.script.md'
        script_file.write_text(script_content)

        manager = AgentScriptsManager(scripts_dir=test_dir)
        script = manager.get_script('multiline_desc')
        assert script is not None
        assert (
            'This is a multiline description\nthat spans multiple lines\nfor testing purposes'
            in script.description
        )


def test_script_with_special_characters_in_name():
    """Test handling of script with special characters in filename."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)

        script_content = """---
description: Script with special characters in name
---
# Script Content
"""

        script_file = test_dir / 'special-chars_123.script.md'
        script_file.write_text(script_content)

        manager = AgentScriptsManager(scripts_dir=test_dir)
        script = manager.get_script('special-chars_123')
        assert script is not None
        assert script.name == 'special-chars_123'


def test_custom_scripts_dir_valid():
    """Test initialization with valid custom scripts directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        scripts_dir = Path(temp_dir) / 'scripts'
        custom_dir = Path(temp_dir) / 'custom'
        scripts_dir.mkdir()
        custom_dir.mkdir()

        # Create script in main directory
        main_script = scripts_dir / 'main.script.md'
        main_script.write_text("""---
description: Main script
---
# Main Script""")

        # Create script in custom directory
        custom_script = custom_dir / 'custom.script.md'
        custom_script.write_text("""---
description: Custom script
---
# Custom Script""")

        manager = AgentScriptsManager(scripts_dir=scripts_dir, custom_scripts_dir=custom_dir)

        assert 'main' in manager.scripts
        assert 'custom' in manager.scripts

        main_script = manager.get_script('main')
        assert main_script is not None
        assert main_script.description == 'Main script'

        custom_script = manager.get_script('custom')
        assert custom_script is not None
        assert custom_script.description == 'Custom script'


def test_custom_scripts_dir_nonexistent():
    """Test initialization with non-existent custom scripts directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        scripts_dir = Path(temp_dir) / 'scripts'
        custom_dir = Path(temp_dir) / 'nonexistent'
        scripts_dir.mkdir()

        with pytest.raises(
            RuntimeError, match=f'User scripts directory {custom_dir} does not exist'
        ):
            AgentScriptsManager(scripts_dir=scripts_dir, custom_scripts_dir=custom_dir)


def test_custom_scripts_dir_no_read_permission():
    """Test initialization with custom scripts directory without read permission."""
    with tempfile.TemporaryDirectory() as temp_dir:
        scripts_dir = Path(temp_dir) / 'scripts'
        custom_dir = Path(temp_dir) / 'custom'
        scripts_dir.mkdir()
        custom_dir.mkdir()

        with patch('os.access', return_value=False):
            with pytest.raises(
                RuntimeError, match=f'No read permission for user scripts directory {custom_dir}'
            ):
                AgentScriptsManager(scripts_dir=scripts_dir, custom_scripts_dir=custom_dir)


def test_custom_scripts_dir_none():
    """Test initialization with None custom scripts directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        scripts_dir = Path(temp_dir) / 'scripts'
        scripts_dir.mkdir()

        script_file = scripts_dir / 'test.script.md'
        script_file.write_text("""---
description: Test script
---
# Test Script""")

        manager = AgentScriptsManager(scripts_dir=scripts_dir, custom_scripts_dir=None)

        assert len(manager.scripts_dirs) == 1
        assert manager.scripts_dirs[0] == scripts_dir
        assert 'test' in manager.scripts
