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

"""Tests for logging configuration functionality."""

import os
from awslabs.finch_mcp_server.server import (
    configure_logging,
    get_default_log_path,
)
from pathlib import Path
from unittest.mock import mock_open, patch


class TestLoggingConfiguration:
    """Tests for logging configuration."""

    def setup_method(self):
        """Set up test environment."""
        # Clear any existing environment variables
        for env_var in ['FINCH_DISABLE_FILE_LOGGING', 'FINCH_MCP_LOG_FILE', 'FASTMCP_LOG_LEVEL']:
            if env_var in os.environ:
                del os.environ[env_var]

    @patch('awslabs.finch_mcp_server.server.logger')
    def test_default_logging_configuration(self, mock_logger):
        """Test default logging configuration (stderr + file)."""
        configure_logging()

        # Should have been called twice: once for stderr, once for file
        assert mock_logger.add.call_count == 2

        # First call should be stderr
        first_call = mock_logger.add.call_args_list[0]
        # sys.stderr can be TextIOWrapper or EncodedFile depending on system
        assert first_call[0][0].__class__.__name__ in ['TextIOWrapper', 'EncodedFile']

        # Second call should be file
        second_call = mock_logger.add.call_args_list[1]
        assert isinstance(second_call[0][0], str)  # file path

    @patch.dict(os.environ, {'FINCH_DISABLE_FILE_LOGGING': 'true'})
    @patch('awslabs.finch_mcp_server.server.logger')
    def test_disabled_file_logging_via_env(self, mock_logger):
        """Test that file logging can be disabled via environment variable."""
        configure_logging()

        # Should only have stderr logging
        assert mock_logger.add.call_count == 1

        # Should be stderr
        call_args = mock_logger.add.call_args_list[0]
        # sys.stderr can be TextIOWrapper or EncodedFile depending on system
        assert call_args[0][0].__class__.__name__ in ['TextIOWrapper', 'EncodedFile']

    @patch.dict(os.environ, {'FINCH_MCP_LOG_FILE': 'custom-test-finch.log'})
    @patch('awslabs.finch_mcp_server.server.logger')
    def test_custom_log_file_via_env(self, mock_logger):
        """Test custom log file via environment variable."""
        configure_logging()

        # Should have both stderr and file logging
        assert mock_logger.add.call_count == 2

        # Second call should be our custom file
        second_call = mock_logger.add.call_args_list[1]
        assert second_call[0][0] == 'custom-test-finch.log'

    @patch.dict(os.environ, {'FASTMCP_LOG_LEVEL': 'DEBUG'})
    @patch('awslabs.finch_mcp_server.server.logger')
    def test_custom_log_level(self, mock_logger):
        """Test custom log level via environment variable."""
        configure_logging()

        # Both calls should use DEBUG level
        for call in mock_logger.add.call_args_list:
            assert call[1]['level'] == 'DEBUG'

    @patch.dict(
        os.environ, {'FINCH_DISABLE_FILE_LOGGING': 'true', 'FINCH_MCP_LOG_FILE': 'test.log'}
    )
    @patch('awslabs.finch_mcp_server.server.logger')
    def test_disable_overrides_custom_file(self, mock_logger):
        """Test that disable flag overrides custom file setting."""
        configure_logging()

        # Should only have stderr logging (disable overrides custom file)
        assert mock_logger.add.call_count == 1


class TestGetDefaultLogPath:
    """Tests for get_default_log_path function."""

    def test_unix_default_path(self):
        """Test default log path on Unix systems."""
        mock_home = Path('mock-home-dir')
        with (
            patch('os.name', 'posix'),
            patch('pathlib.Path.home', return_value=mock_home),
            patch('os.makedirs') as mock_makedirs,
            patch('builtins.open', mock_open()),
            patch('os.remove'),
        ):
            path = get_default_log_path()

            expected_path = os.path.join(
                str(mock_home), '.finch', 'finch-mcp-server', 'finch_mcp_server.log'
            )
            assert path == expected_path
            expected_dir = os.path.join(str(mock_home), '.finch', 'finch-mcp-server')
            mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)

    def test_windows_default_path(self):
        """Test default log path on Windows systems."""
        mock_appdata = 'mock-appdata-dir'
        with (
            patch('os.name', 'nt'),
            patch.dict(os.environ, {'LOCALAPPDATA': mock_appdata}),
            patch('os.makedirs') as mock_makedirs,
            patch('builtins.open', mock_open()),
            patch('os.remove'),
        ):
            path = get_default_log_path()

            # Use os.path.join to handle path separators correctly
            expected_path = os.path.join(mock_appdata, 'finch-mcp-server', 'finch_mcp_server.log')
            assert path == expected_path
            expected_dir = os.path.join(mock_appdata, 'finch-mcp-server')
            mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)

    def test_windows_no_localappdata(self):
        """Test Windows path when no LOCALAPPDATA environment variable."""
        with (
            patch('os.name', 'nt'),
            patch.dict(os.environ, {}, clear=True),
        ):
            path = get_default_log_path()

            assert path is None

    def test_fallback_to_none_on_permission_error(self):
        """Test fallback to None when permission denied."""
        with (
            patch('pathlib.Path.home', return_value=Path('mock-home-dir')),
            patch('os.makedirs', side_effect=PermissionError('Permission denied')),
        ):
            path = get_default_log_path()

            assert path is None

    def test_fallback_to_none_when_no_home(self):
        """Test fallback to None when no HOME environment variable."""
        with patch.dict(os.environ, {}, clear=True):
            path = get_default_log_path()

            assert path is None


class TestIntegrationLogging:
    """Integration tests for logging functionality."""

    @patch('awslabs.finch_mcp_server.server.logger')
    def test_actual_file_creation_default(self, mock_logger):
        """Test that log file is created when default path is available."""
        test_log_file = 'mock-test-finch.log'

        with patch(
            'awslabs.finch_mcp_server.server.get_default_log_path',
            return_value=test_log_file,
        ):
            configure_logging()

            # Should have both stderr and file logging
            assert mock_logger.add.call_count == 2

            # Second call should be our test file
            second_call = mock_logger.add.call_args_list[1]
            assert second_call[0][0] == test_log_file

    @patch.dict(os.environ, {'FINCH_DISABLE_FILE_LOGGING': 'true'})
    @patch('awslabs.finch_mcp_server.server.logger')
    def test_actual_file_creation_disabled(self, mock_logger):
        """Test that no log file is created when disabled."""
        test_log_file = 'mock-test-finch.log'

        with patch(
            'awslabs.finch_mcp_server.server.get_default_log_path',
            return_value=test_log_file,
        ):
            configure_logging()

            # Should only have stderr logging
            assert mock_logger.add.call_count == 1

    @patch.dict(os.environ, {'FINCH_MCP_LOG_FILE': 'custom-finch.log'})
    @patch('awslabs.finch_mcp_server.server.logger')
    def test_actual_custom_file_creation(self, mock_logger):
        """Test that custom log file is used when specified."""
        configure_logging()

        # Should have both stderr and file logging
        assert mock_logger.add.call_count == 2

        # Second call should be our custom file
        second_call = mock_logger.add.call_args_list[1]
        assert second_call[0][0] == 'custom-finch.log'

    def test_configure_logging_file_permission_error(self):
        """Test configure_logging handles file permission errors gracefully."""
        with (
            patch(
                'awslabs.finch_mcp_server.server.get_default_log_path',
                return_value='/test/path.log',
            ),
            patch('awslabs.finch_mcp_server.server.logger') as mock_logger,
        ):
            mock_logger.add.side_effect = [None, PermissionError('Permission denied')]
            configure_logging()
            mock_logger.warning.assert_called_with(
                'Could not create log file at /test/path.log: Permission denied. Logging to stderr only.'
            )

    def test_configure_logging_no_suitable_location(self):
        """Test configure_logging when no suitable log location is found."""
        with (
            patch('awslabs.finch_mcp_server.server.get_default_log_path', return_value=None),
            patch('awslabs.finch_mcp_server.server.logger') as mock_logger,
        ):
            configure_logging()
            mock_logger.warning.assert_called_with(
                'Could not find suitable location for log file. Logging to stderr only.'
            )

    def test_configure_logging_file_success_message(self):
        """Test that successful file logging logs initialization message."""
        test_log_file = '/test/success.log'

        with (
            patch(
                'awslabs.finch_mcp_server.server.get_default_log_path',
                return_value=test_log_file,
            ),
            patch('awslabs.finch_mcp_server.server.logger') as mock_logger,
        ):
            configure_logging()
            mock_logger.info.assert_any_call('File logging initialized successfully')
