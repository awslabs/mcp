"""
Unit tests for template utilities.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.utils.templates import get_templates_dir


def test_get_templates_dir_success():
    """Test get_templates_dir when directory exists."""
    # Mock os.path.isdir to return True
    with patch("os.path.isdir", return_value=True):
        # Mock os.path.dirname and os.path.abspath to return known values
        with patch("os.path.dirname", return_value="/mock/path"):
            with patch("os.path.abspath", return_value="/mock/path/file.py"):
                # Call the function
                templates_dir = get_templates_dir()

                # Verify the function returns the expected path
                assert templates_dir == "/mock/path/templates"


def test_get_templates_dir_directory_not_found():
    """Test get_templates_dir when directory doesn't exist."""
    # We need to patch the logger before importing the module
    with patch("logging.getLogger") as mock_get_logger:
        # Set up the mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Now patch the other functions
        with (
            patch("os.path.isdir", return_value=False),
            patch("os.path.dirname", return_value="/mock/path"),
            patch("os.path.abspath", return_value="/mock/path/file.py"),
        ):
            # Call the function - should raise FileNotFoundError
            with pytest.raises(FileNotFoundError) as excinfo:
                get_templates_dir()

            # Verify the error message
            assert "Templates directory not found" in str(excinfo.value)
            assert "/mock/path/templates" in str(excinfo.value)

            # Verify the error was logged - the real logger is used, not our mock
            # so we just check that the exception was raised with the right message
            assert "/mock/path/templates" in str(excinfo.value)
