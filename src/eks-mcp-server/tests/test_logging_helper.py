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
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = MagicMock()
    ctx.request_id = 'test-request-id'
    return ctx


@patch('awslabs.eks_mcp_server.logging_helper.logger')
def test_log_with_request_id_debug(mock_logger, mock_context):
    """Test log_with_request_id with DEBUG level."""
    log_with_request_id(mock_context, LogLevel.DEBUG, 'Test debug message')
    mock_logger.debug.assert_called_once_with('[request_id=test-request-id] Test debug message')


@patch('awslabs.eks_mcp_server.logging_helper.logger')
def test_log_with_request_id_info(mock_logger, mock_context):
    """Test log_with_request_id with INFO level."""
    log_with_request_id(mock_context, LogLevel.INFO, 'Test info message')
    mock_logger.info.assert_called_once_with('[request_id=test-request-id] Test info message')


@patch('awslabs.eks_mcp_server.logging_helper.logger')
def test_log_with_request_id_warning(mock_logger, mock_context):
    """Test log_with_request_id with WARNING level."""
    log_with_request_id(mock_context, LogLevel.WARNING, 'Test warning message')
    mock_logger.warning.assert_called_once_with(
        '[request_id=test-request-id] Test warning message'
    )


@patch('awslabs.eks_mcp_server.logging_helper.logger')
def test_log_with_request_id_error(mock_logger, mock_context):
    """Test log_with_request_id with ERROR level."""
    log_with_request_id(mock_context, LogLevel.ERROR, 'Test error message')
    mock_logger.error.assert_called_once_with('[request_id=test-request-id] Test error message')


@patch('awslabs.eks_mcp_server.logging_helper.logger')
def test_log_with_request_id_critical(mock_logger, mock_context):
    """Test log_with_request_id with CRITICAL level."""
    log_with_request_id(mock_context, LogLevel.CRITICAL, 'Test critical message')
    mock_logger.critical.assert_called_once_with(
        '[request_id=test-request-id] Test critical message'
    )


@patch('awslabs.eks_mcp_server.logging_helper.logger')
def test_log_with_request_id_with_kwargs(mock_logger, mock_context):
    """Test log_with_request_id with additional kwargs."""
    log_with_request_id(
        mock_context,
        LogLevel.INFO,
        'Test message with kwargs',
        extra_field='extra_value',
        another_field=123,
    )
    mock_logger.info.assert_called_once_with(
        '[request_id=test-request-id] Test message with kwargs',
        extra_field='extra_value',
        another_field=123,
    )


def test_log_level_enum():
    """Test the LogLevel enum values."""
    assert LogLevel.DEBUG.value == 'debug'
    assert LogLevel.INFO.value == 'info'
    assert LogLevel.WARNING.value == 'warning'
    assert LogLevel.ERROR.value == 'error'
    assert LogLevel.CRITICAL.value == 'critical'
