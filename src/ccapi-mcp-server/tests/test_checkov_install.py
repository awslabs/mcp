"""Tests for Checkov availability check."""

import subprocess
from awslabs.ccapi_mcp_server.impl.tools.security_scanning import _check_checkov_installed
from unittest.mock import MagicMock, patch


class TestCheckovCheck:
    """Test Checkov availability check (now that it's a declared dependency)."""

    def test_checkov_available(self):
        """Test when Checkov is available (normal case)."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _check_checkov_installed()

            assert result['installed'] is True
            assert result['message'] == 'Checkov is available'
            assert result['needs_user_action'] is False
            mock_run.assert_called_once_with(
                ['checkov', '--version'],
                capture_output=True,
                text=True,
                check=True,
                shell=False,
            )

    def test_checkov_not_found(self):
        """Test when Checkov is not found (should not happen with proper dependency)."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = _check_checkov_installed()

            assert result['installed'] is False
            assert 'not available' in result['message']
            assert 'declared dependency' in result['message']
            assert result['needs_user_action'] is True

    def test_checkov_command_fails(self):
        """Test when Checkov command fails."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'checkov')
            result = _check_checkov_installed()

            assert result['installed'] is False
            assert 'not available' in result['message']
            assert result['needs_user_action'] is True
