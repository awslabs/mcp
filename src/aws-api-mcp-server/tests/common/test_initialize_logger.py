"""Unit tests for initialize_logger function."""

import pytest
import sys
import tempfile
from awslabs.aws_api_mcp_server.core.common import initialize_logger
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def mock_loguru():
    """Mock loguru logger."""
    with patch('awslabs.aws_api_mcp_server.core.common.logger') as mock_logger:
        yield mock_logger


@pytest.fixture
def mock_config():
    """Mock config module."""
    with (
        patch('awslabs.aws_api_mcp_server.core.common.FASTMCP_LOG_LEVEL', 'INFO'),
        patch('awslabs.aws_api_mcp_server.core.common.DEFAULT_REGION', 'us-east-1'),
        patch('awslabs.aws_api_mcp_server.core.common.get_server_directory') as mock_get_dir,
    ):
        temp_dir = Path(tempfile.mkdtemp())
        mock_get_dir.return_value = temp_dir
        yield mock_get_dir


@pytest.fixture
def mock_cloudwatch_sink():
    """Mock CloudWatchLogSink."""
    with patch('awslabs.aws_api_mcp_server.core.common.CloudWatchLogSink') as mock_sink:
        mock_instance = Mock()
        mock_sink.return_value = mock_instance
        yield mock_sink


def test_initialize_logger_without_cloudwatch(mock_loguru, mock_config, mock_cloudwatch_sink):
    """Test initialize_logger when CLOUDWATCH_LOG_GROUP_NAME is not set."""
    with patch('awslabs.aws_api_mcp_server.core.common.CLOUDWATCH_LOG_GROUP_NAME', None):
        initialize_logger()

    # Verify logger.remove() was called
    mock_loguru.remove.assert_called_once()

    # Verify stderr sink was added
    mock_loguru.add.assert_any_call(sys.stderr, level='INFO')

    # Verify file sink was added
    mock_loguru.add.assert_any_call(
        mock_config.return_value / 'aws-api-mcp-server.log', rotation='10 MB', retention='7 days'
    )

    # Verify CloudWatch sink was NOT added
    assert mock_cloudwatch_sink.call_count == 0

    # Verify only 2 sinks were added (stderr + file)
    assert mock_loguru.add.call_count == 2


def test_initialize_logger_with_cloudwatch(mock_loguru, mock_config, mock_cloudwatch_sink):
    """Test initialize_logger when CLOUDWATCH_LOG_GROUP_NAME is set."""
    with patch(
        'awslabs.aws_api_mcp_server.core.common.CLOUDWATCH_LOG_GROUP_NAME', '/test/log-group'
    ):
        initialize_logger()

    # Verify logger.remove() was called
    mock_loguru.remove.assert_called_once()

    # Verify stderr sink was added
    mock_loguru.add.assert_any_call(sys.stderr, level='INFO')

    # Verify file sink was added
    mock_loguru.add.assert_any_call(
        mock_config.return_value / 'aws-api-mcp-server.log', rotation='10 MB', retention='7 days'
    )

    # Verify CloudWatch sink was created
    mock_cloudwatch_sink.assert_called_once_with(
        log_group_name='/test/log-group', region_name='us-east-1'
    )

    # Verify CloudWatch sink was added to logger
    mock_loguru.add.assert_any_call(
        mock_cloudwatch_sink.return_value,
        level='INFO',
        enqueue=True,
        colorize=False,
        catch=True,
        backtrace=False,
        diagnose=False,
        format='{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} | {message}',
    )

    # Verify 3 sinks were added (stderr + file + cloudwatch)
    assert mock_loguru.add.call_count == 3


def test_initialize_logger_cloudwatch_exception(mock_loguru, mock_config, mock_cloudwatch_sink):
    """Test initialize_logger when CloudWatch sink initialization fails."""
    # Make CloudWatchLogSink raise an exception
    mock_cloudwatch_sink.side_effect = Exception('CloudWatch connection failed')

    with patch(
        'awslabs.aws_api_mcp_server.core.common.CLOUDWATCH_LOG_GROUP_NAME', '/test/log-group'
    ):
        initialize_logger()

    # Verify logger.remove() was called
    mock_loguru.remove.assert_called_once()

    # Verify stderr sink was added
    mock_loguru.add.assert_any_call(sys.stderr, level='INFO')

    # Verify file sink was added
    mock_loguru.add.assert_any_call(
        mock_config.return_value / 'aws-api-mcp-server.log', rotation='10 MB', retention='7 days'
    )

    # Verify warning was logged about CloudWatch failure
    mock_loguru.warning.assert_called_once_with(
        'CloudWatch Logs sink not initialized: {}', 'CloudWatch connection failed'
    )

    # Verify only 2 sinks were added (stderr + file, cloudwatch failed)
    assert mock_loguru.add.call_count == 2
