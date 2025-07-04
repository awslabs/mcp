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

"""Tests for the logging_helper module."""

import pytest
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from unittest.mock import MagicMock, patch


class TestLoggingHelper:
    """Tests for the logging_helper module."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Context with a request ID."""
        mock = MagicMock()
        mock.request_id = 'test-request-id'
        return mock

    def test_log_level_enum(self):
        """Test that the LogLevel enum has the expected values."""
        assert LogLevel.DEBUG.value == 'debug'
        assert LogLevel.INFO.value == 'info'
        assert LogLevel.WARNING.value == 'warning'
        assert LogLevel.ERROR.value == 'error'
        assert LogLevel.CRITICAL.value == 'critical'

    @patch('awslabs.aws_dataprocessing_mcp_server.utils.logging_helper.logger')
    def test_log_with_request_id_debug(self, mock_logger):
        """Test that log_with_request_id logs at the DEBUG level with the request ID."""
        mock_ctx = MagicMock()
        mock_ctx.request_id = 'test-request-id'
        log_with_request_id(mock_ctx, LogLevel.DEBUG, 'Debug message')
        mock_logger.debug.assert_called_once_with('[request_id=test-request-id] Debug message')

    @patch('awslabs.aws_dataprocessing_mcp_server.utils.logging_helper.logger')
    def test_log_with_request_id_info(self, mock_logger):
        """Test that log_with_request_id logs at the INFO level with the request ID."""
        mock_ctx = MagicMock()
        mock_ctx.request_id = 'test-request-id'
        log_with_request_id(mock_ctx, LogLevel.INFO, 'Info message')
        mock_logger.info.assert_called_once_with('[request_id=test-request-id] Info message')

    @patch('awslabs.aws_dataprocessing_mcp_server.utils.logging_helper.logger')
    def test_log_with_request_id_warning(self, mock_logger):
        """Test that log_with_request_id logs at the WARNING level with the request ID."""
        mock_ctx = MagicMock()
        mock_ctx.request_id = 'test-request-id'
        log_with_request_id(mock_ctx, LogLevel.WARNING, 'Warning message')
        mock_logger.warning.assert_called_once_with('[request_id=test-request-id] Warning message')

    @patch('awslabs.aws_dataprocessing_mcp_server.utils.logging_helper.logger')
    def test_log_with_request_id_error(self, mock_logger):
        """Test that log_with_request_id logs at the ERROR level with the request ID."""
        mock_ctx = MagicMock()
        mock_ctx.request_id = 'test-request-id'
        log_with_request_id(mock_ctx, LogLevel.ERROR, 'Error message')
        mock_logger.error.assert_called_once_with('[request_id=test-request-id] Error message')

    @patch('awslabs.aws_dataprocessing_mcp_server.utils.logging_helper.logger')
    def test_log_with_request_id_critical(self, mock_logger):
        """Test that log_with_request_id logs at the CRITICAL level with the request ID."""
        mock_ctx = MagicMock()
        mock_ctx.request_id = 'test-request-id'
        log_with_request_id(mock_ctx, LogLevel.CRITICAL, 'Critical message')
        mock_logger.critical.assert_called_once_with(
            '[request_id=test-request-id] Critical message'
        )

    @patch('awslabs.aws_dataprocessing_mcp_server.utils.logging_helper.logger')
    def test_log_with_request_id_with_kwargs(self, mock_logger):
        """Test that log_with_request_id passes kwargs to the logger."""
        mock_ctx = MagicMock()
        mock_ctx.request_id = 'test-request-id'
        log_with_request_id(
            mock_ctx, LogLevel.INFO, 'Message with kwargs', extra_field='extra_value'
        )
        mock_logger.info.assert_called_once_with(
            '[request_id=test-request-id] Message with kwargs', extra_field='extra_value'
        )
