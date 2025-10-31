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
# ruff: noqa: D101, D102, D103
"""Tests for the logging_helper module."""

import pytest
from awslabs.sagemaker_hyperpod_mcp_server.logging_helper import LogLevel, log_with_request_id
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


class TestLogLevel:
    """Tests for the LogLevel enum."""

    def test_log_level_values(self):
        """Test that the LogLevel enum has the expected values."""
        assert LogLevel.DEBUG.value == 'debug'
        assert LogLevel.INFO.value == 'info'
        assert LogLevel.WARNING.value == 'warning'
        assert LogLevel.ERROR.value == 'error'
        assert LogLevel.CRITICAL.value == 'critical'


class TestLogWithRequestId:
    """Tests for the log_with_request_id function."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock MCP context with a request ID."""
        ctx = MagicMock(spec=Context)
        ctx.request_id = 'test-request-id'
        return ctx

    @patch('awslabs.sagemaker_hyperpod_mcp_server.logging_helper.logger')
    def test_log_debug(self, mock_logger, mock_ctx):
        """Test that log_with_request_id logs at DEBUG level."""
        message = 'Test debug message'
        log_with_request_id(mock_ctx, LogLevel.DEBUG, message)
        mock_logger.debug.assert_called_once_with(f'[request_id={mock_ctx.request_id}] {message}')

    @patch('awslabs.sagemaker_hyperpod_mcp_server.logging_helper.logger')
    def test_log_info(self, mock_logger, mock_ctx):
        """Test that log_with_request_id logs at INFO level."""
        message = 'Test info message'
        log_with_request_id(mock_ctx, LogLevel.INFO, message)
        mock_logger.info.assert_called_once_with(f'[request_id={mock_ctx.request_id}] {message}')

    @patch('awslabs.sagemaker_hyperpod_mcp_server.logging_helper.logger')
    def test_log_warning(self, mock_logger, mock_ctx):
        """Test that log_with_request_id logs at WARNING level."""
        message = 'Test warning message'
        log_with_request_id(mock_ctx, LogLevel.WARNING, message)
        mock_logger.warning.assert_called_once_with(
            f'[request_id={mock_ctx.request_id}] {message}'
        )

    @patch('awslabs.sagemaker_hyperpod_mcp_server.logging_helper.logger')
    def test_log_error(self, mock_logger, mock_ctx):
        """Test that log_with_request_id logs at ERROR level."""
        message = 'Test error message'
        log_with_request_id(mock_ctx, LogLevel.ERROR, message)
        mock_logger.error.assert_called_once_with(f'[request_id={mock_ctx.request_id}] {message}')

    @patch('awslabs.sagemaker_hyperpod_mcp_server.logging_helper.logger')
    def test_log_critical(self, mock_logger, mock_ctx):
        """Test that log_with_request_id logs at CRITICAL level."""
        message = 'Test critical message'
        log_with_request_id(mock_ctx, LogLevel.CRITICAL, message)
        mock_logger.critical.assert_called_once_with(
            f'[request_id={mock_ctx.request_id}] {message}'
        )

    @patch('awslabs.sagemaker_hyperpod_mcp_server.logging_helper.logger')
    def test_log_with_additional_kwargs(self, mock_logger, mock_ctx):
        """Test that log_with_request_id passes additional kwargs to the logger."""
        message = 'Test message with kwargs'
        additional_kwargs = {'key1': 'value1', 'key2': 'value2'}
        log_with_request_id(mock_ctx, LogLevel.INFO, message, **additional_kwargs)
        mock_logger.info.assert_called_once_with(
            f'[request_id={mock_ctx.request_id}] {message}', **additional_kwargs
        )
