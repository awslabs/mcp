"""Unit tests for FileUtils class."""

import json
import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.file_utils import FileUtils
from pathlib import Path
from unittest.mock import patch


@pytest.mark.unit
class TestFileUtils:
    """Unit tests for FileUtils class."""

    def test_load_json_file_success(self, tmp_path):
        """Test successful JSON file loading."""
        test_data = {'key': 'value', 'number': 42}
        json_file = tmp_path / 'test.json'
        json_file.write_text(json.dumps(test_data))

        result = FileUtils.load_json_file(str(json_file), 'test')
        assert result == test_data

    def test_load_json_file_file_not_found(self):
        """Test FileNotFoundError when file doesn't exist."""
        with pytest.raises(FileNotFoundError, match='Test file not found'):
            FileUtils.load_json_file('/nonexistent/file.json', 'Test')

    def test_load_json_file_invalid_json(self, tmp_path):
        """Test ValueError for invalid JSON."""
        json_file = tmp_path / 'invalid.json'
        json_file.write_text('{ invalid json }')

        with pytest.raises(ValueError, match='Invalid JSON in Test file'):
            FileUtils.load_json_file(str(json_file), 'Test')

    def test_load_json_file_permission_error(self):
        """Test ValueError for permission errors."""
        with patch('builtins.open', side_effect=PermissionError('Permission denied')):
            with patch('pathlib.Path.exists', return_value=True):
                with pytest.raises(ValueError, match='Error reading Test file'):
                    FileUtils.load_json_file('test.json', 'Test')

    def test_validate_and_resolve_path_valid_file(self, tmp_path):
        """Test successful path validation for existing file."""
        test_file = tmp_path / 'test.txt'
        test_file.write_text('test content')

        result = FileUtils.validate_and_resolve_path(test_file)
        assert result == test_file.resolve()

    def test_validate_and_resolve_path_file_not_found(self, tmp_path):
        """Test FileNotFoundError for non-existent file."""
        test_file = tmp_path / 'nonexistent.txt'

        with pytest.raises(FileNotFoundError, match='Test file not found'):
            FileUtils.validate_and_resolve_path(test_file, file_name='Test')

    def test_validate_and_resolve_path_directory_not_file(self, tmp_path):
        """Test ValueError when path is a directory."""
        test_dir = tmp_path / 'test_dir'
        test_dir.mkdir()

        with pytest.raises(ValueError, match='Test path must be a file, not a directory'):
            FileUtils.validate_and_resolve_path(test_dir, file_name='Test')

    def test_validate_and_resolve_path_absolute_path_disallowed(self, tmp_path):
        """Test ValueError when absolute paths are disallowed."""
        test_file = tmp_path / 'test.txt'
        test_file.write_text('test content')

        with pytest.raises(ValueError, match='Absolute paths are not allowed'):
            FileUtils.validate_and_resolve_path(test_file, allow_absolute_paths=False)

    def test_validate_and_resolve_path_path_traversal_detection(self, tmp_path):
        """Test path traversal detection."""
        # Create a file outside the base directory
        outside_dir = tmp_path.parent / 'outside'
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / 'test.txt'
        outside_file.write_text('test content')

        # Try to access it with a relative path that escapes the base directory
        relative_path = Path('../outside/test.txt')

        with pytest.raises(ValueError, match='Path traversal detected'):
            FileUtils.validate_and_resolve_path(
                relative_path, allow_absolute_paths=False, base_dir=tmp_path
            )

    def test_validate_and_resolve_path_relative_path_within_base(self, tmp_path):
        """Test successful validation of relative path within base directory."""
        # Create a subdirectory and file
        sub_dir = tmp_path / 'subdir'
        sub_dir.mkdir()
        test_file = sub_dir / 'test.txt'
        test_file.write_text('test content')

        # Create a relative path from tmp_path to the file
        relative_path = Path('subdir/test.txt')

        # Change to tmp_path directory for relative path resolution
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = FileUtils.validate_and_resolve_path(
                relative_path, allow_absolute_paths=False, base_dir=tmp_path
            )
            assert result == test_file.resolve()
        finally:
            os.chdir(original_cwd)

    def test_validate_and_resolve_path_with_custom_base_dir(self, tmp_path):
        """Test path validation with custom base directory."""
        # Create a file in a subdirectory
        sub_dir = tmp_path / 'allowed'
        sub_dir.mkdir()
        test_file = sub_dir / 'test.txt'
        test_file.write_text('test content')

        # Validate with custom base directory
        result = FileUtils.validate_and_resolve_path(
            test_file, allow_absolute_paths=True, base_dir=sub_dir
        )
        assert result == test_file.resolve()

    def test_validate_and_resolve_path_os_error_handling(self):
        """Test handling of OS errors during path resolution."""
        with patch('pathlib.Path.resolve', side_effect=OSError('OS Error')):
            test_path = Path('test.txt')
            with pytest.raises(ValueError, match='Invalid File path'):
                FileUtils.validate_and_resolve_path(test_path)

    def test_validate_and_resolve_path_custom_file_type_errors(self, tmp_path):
        """Test that file_name parameter is used in error messages."""
        # Test file not found with custom file name
        test_file = tmp_path / 'nonexistent.json'
        with pytest.raises(FileNotFoundError, match='Schema file not found'):
            FileUtils.validate_and_resolve_path(test_file, file_name='Schema')

        # Test directory error with custom file name
        test_dir = tmp_path / 'test_dir'
        test_dir.mkdir()
        with pytest.raises(ValueError, match='Usage Data path must be a file, not a directory'):
            FileUtils.validate_and_resolve_path(test_dir, file_name='Usage Data')

        # Test invalid path with custom file name
        with patch('pathlib.Path.resolve', side_effect=OSError('OS Error')):
            test_path = Path('test.txt')
            with pytest.raises(ValueError, match='Invalid Schema path'):
                FileUtils.validate_and_resolve_path(test_path, file_name='Schema')

    def test_load_json_file_with_encoding(self, tmp_path):
        """Test JSON loading with UTF-8 encoding."""
        test_data = {'unicode': '测试', 'emoji': '🚀'}
        json_file = tmp_path / 'unicode.json'
        json_file.write_text(json.dumps(test_data, ensure_ascii=False), encoding='utf-8')

        result = FileUtils.load_json_file(str(json_file), 'Unicode test')
        assert result == test_data

    def test_load_json_file_empty_file(self, tmp_path):
        """Test handling of empty JSON file."""
        json_file = tmp_path / 'empty.json'
        json_file.write_text('')

        with pytest.raises(ValueError, match='Invalid JSON'):
            FileUtils.load_json_file(str(json_file), 'Empty')

    def test_validate_and_resolve_path_symlink_handling(self, tmp_path):
        """Test handling of symbolic links."""
        # Create a real file
        real_file = tmp_path / 'real.txt'
        real_file.write_text('real content')

        # Create a symlink to it
        symlink_file = tmp_path / 'symlink.txt'
        try:
            symlink_file.symlink_to(real_file)

            # Should resolve to the real file
            result = FileUtils.validate_and_resolve_path(symlink_file)
            assert result == real_file.resolve()
        except OSError:
            # Skip test if symlinks are not supported on this system
            pytest.skip('Symlinks not supported on this system')

    def test_validate_and_resolve_path_case_sensitivity(self, tmp_path):
        """Test path validation with different case (on case-insensitive systems)."""
        test_file = tmp_path / 'Test.txt'
        test_file.write_text('test content')

        # This should work regardless of case sensitivity
        result = FileUtils.validate_and_resolve_path(test_file)
        assert result.exists()
        assert result.is_file()
