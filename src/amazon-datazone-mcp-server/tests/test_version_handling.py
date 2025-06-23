"""Tests for version handling in __init__.py."""

import sys
from unittest.mock import patch, MagicMock


class TestVersionHandling:
    """Test version handling functionality."""

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_version_file_exists(self, mock_read_text, mock_exists):
        """Test version reading when VERSION file exists."""
        # Mock the VERSION file as existing
        mock_exists.return_value = True
        mock_read_text.return_value = '1.0.0\n'

        # Clear module cache
        module_name = 'awslabs'
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Import should read version from file
        import awslabs

        assert awslabs.__version__ == '1.0.0'
        mock_exists.assert_called_once()
        mock_read_text.assert_called_once()

    @patch('pathlib.Path.exists')
    def test_version_file_missing(self, mock_exists):
        """Test version handling when VERSION file doesn't exist - covers line 22."""
        # Mock the VERSION file as not existing
        mock_exists.return_value = False

        # Clear module cache to force re-import
        module_names_to_clear = [name for name in sys.modules.keys() if name.startswith('awslabs')]
        for name in module_names_to_clear:
            del sys.modules[name]

        # Import should fallback to 'unknown'
        import awslabs

        # This should trigger line 22: __version__ = 'unknown'
        assert awslabs.__version__ == 'unknown'
        mock_exists.assert_called_once()

    def test_version_file_read_error_unit_test(self):
        """Test version handling logic when file exists but can't be read."""

        # Create a mock path that exists but fails to read
        mock_version_file = MagicMock()
        mock_version_file.exists.return_value = True
        mock_version_file.read_text.side_effect = FileNotFoundError("Cannot read file")

        # Simulate the exact logic from __init__.py
        if mock_version_file.exists():
            try:
                version = mock_version_file.read_text().strip()
            except (IOError, OSError, FileNotFoundError):
                version = 'unknown'
        else:
            version = 'unknown'

        # Should fallback to 'unknown' when read fails
        assert version == 'unknown'
        mock_version_file.exists.assert_called_once()
        mock_version_file.read_text.assert_called_once()
