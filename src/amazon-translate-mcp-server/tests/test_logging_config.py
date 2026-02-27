"""Unit tests for logging configuration in Amazon Translate MCP Server.

Tests logging setup, correlation ID tracking, and structured logging functionality.
"""

import logging
import pytest
import uuid
from awslabs.amazon_translate_mcp_server.logging_config import (
    DEFAULT_LOGGING_CONFIG,
    CorrelationIdFilter,
    LoggerMixin,
    StructuredFormatter,
    clear_correlation_id,
    configure_component_loggers,
    correlation_id_context,
    get_correlation_id,
    set_correlation_id,
    setup_logging,
    with_correlation_id,
)
from io import StringIO
from unittest.mock import Mock, patch


class TestCorrelationIdFilter:
    """Test CorrelationIdFilter functionality."""

    def test_filter_adds_correlation_id_from_record(self):
        """Test filter adds correlation ID from log record."""
        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        record.correlation_id = 'record-correlation-123'

        result = filter_instance.filter(record)

        assert result is True
        assert getattr(record, 'correlation_id', None) == 'record-correlation-123'

    def test_filter_adds_correlation_id_from_context(self):
        """Test filter adds correlation ID from context variable."""
        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None,
        )

        # Set correlation ID in context
        correlation_id_context.set('context-correlation-456')

        try:
            result = filter_instance.filter(record)

            assert result is True
            assert getattr(record, 'correlation_id', None) == 'context-correlation-456'
        finally:
            correlation_id_context.set(None)

    def test_filter_adds_default_correlation_id(self):
        """Test filter adds default correlation ID when none available."""
        filter_instance = CorrelationIdFilter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None,
        )

        result = filter_instance.filter(record)

        assert result is True
        assert getattr(record, 'correlation_id', None) == 'no-correlation-id'


class TestStructuredFormatter:
    """Test StructuredFormatter functionality."""

    def test_basic_formatting(self):
        """Test basic log record formatting."""
        formatter = StructuredFormatter(include_extra=False)
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        record.correlation_id = 'test-correlation-789'

        formatted = formatter.format(record)

        assert 'level=INFO' in formatted
        assert 'logger=test.logger' in formatted
        assert 'message=Test message' in formatted
        assert 'correlation_id=test-correlation-789' in formatted
        assert 'timestamp=' in formatted

    def test_formatting_with_extra_fields(self):
        """Test formatting with extra fields included."""
        formatter = StructuredFormatter(include_extra=True)
        record = logging.LogRecord(
            name='test.logger',
            level=logging.WARNING,
            pathname='',
            lineno=0,
            msg='Warning message',
            args=(),
            exc_info=None,
        )
        record.correlation_id = 'test-correlation-abc'
        record.user_id = 'user-123'
        record.operation = 'translate_text'

        formatted = formatter.format(record)

        assert 'level=WARNING' in formatted
        assert 'message=Warning message' in formatted
        assert 'correlation_id=test-correlation-abc' in formatted
        assert 'user_id=user-123' in formatted
        assert 'operation=translate_text' in formatted

    def test_formatting_with_exception(self):
        """Test formatting with exception information."""
        formatter = StructuredFormatter()

        try:
            raise ValueError('Test exception')
        except ValueError:
            import sys

            record = logging.LogRecord(
                name='test.logger',
                level=logging.ERROR,
                pathname='',
                lineno=0,
                msg='Error occurred',
                args=(),
                exc_info=sys.exc_info(),
            )
            record.correlation_id = 'error-correlation-def'

        formatted = formatter.format(record)

        assert 'level=ERROR' in formatted
        assert 'message=Error occurred' in formatted
        assert 'exception=' in formatted
        assert 'ValueError: Test exception' in formatted

    def test_formatting_without_extra_fields(self):
        """Test formatting excludes extra fields when disabled."""
        formatter = StructuredFormatter(include_extra=False)
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        record.correlation_id = 'test-correlation-ghi'
        record.extra_field = 'should_not_appear'

        formatted = formatter.format(record)

        assert 'correlation_id=test-correlation-ghi' in formatted
        assert 'extra_field' not in formatted


class TestLoggingSetup:
    """Test logging setup functionality."""

    def setUp(self):
        """Reset logging configuration before each test."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_setup_logging_default_config(self):
        """Test setup_logging with default configuration."""
        import os

        self.setUp()

        # Temporarily remove FASTMCP_LOG_LEVEL to test default behavior
        original_log_level = os.environ.get('FASTMCP_LOG_LEVEL')
        if 'FASTMCP_LOG_LEVEL' in os.environ:
            del os.environ['FASTMCP_LOG_LEVEL']

        try:
            setup_logging()

            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO
        finally:
            # Restore original log level
            if original_log_level is not None:
                os.environ['FASTMCP_LOG_LEVEL'] = original_log_level
        assert len(root_logger.handlers) >= 1

        # Test that correlation ID filter is applied
        handler = root_logger.handlers[0]
        assert any(isinstance(f, CorrelationIdFilter) for f in handler.filters)

    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom log level."""
        self.setUp()

        setup_logging(log_level='DEBUG')

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_invalid_level(self):
        """Test setup_logging with invalid log level defaults to INFO."""
        self.setUp()

        setup_logging(log_level='INVALID_LEVEL')

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    @patch.dict('os.environ', {'FASTMCP_LOG_LEVEL': 'WARNING'})
    def test_setup_logging_from_environment(self):
        """Test setup_logging reads level from environment."""
        self.setUp()

        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_setup_logging_with_file_handler(self):
        """Test setup_logging with file output."""
        self.setUp()

        with patch('logging.FileHandler') as mock_file_handler:
            mock_handler = Mock()
            mock_handler.level = logging.INFO  # Set level attribute for comparison
            mock_file_handler.return_value = mock_handler

            import os
            import tempfile

            temp_log_file = os.path.join(tempfile.gettempdir(), 'test.log')

            setup_logging(log_file=temp_log_file)

            mock_file_handler.assert_called_once_with(temp_log_file)
            mock_handler.setLevel.assert_called()
            mock_handler.setFormatter.assert_called()

    def test_setup_logging_file_handler_error(self):
        """Test setup_logging handles file handler creation errors."""
        self.setUp()

        with patch('logging.FileHandler', side_effect=OSError('Permission denied')):
            # Should not raise exception
            setup_logging(log_file='/invalid/path/test.log')

            # Should still have console handler
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) >= 1


class TestCorrelationIdManagement:
    """Test correlation ID management functions."""

    def test_get_correlation_id_generates_new(self):
        """Test get_correlation_id generates new ID when none exists."""
        clear_correlation_id()

        correlation_id = get_correlation_id()

        assert correlation_id is not None
        # Should be a valid UUID
        uuid.UUID(correlation_id)

    def test_get_correlation_id_returns_existing(self):
        """Test get_correlation_id returns existing ID from context."""
        test_id = 'existing-correlation-123'
        set_correlation_id(test_id)

        correlation_id = get_correlation_id()

        assert correlation_id == test_id

    def test_set_correlation_id(self):
        """Test set_correlation_id updates context."""
        test_id = 'new-correlation-456'

        set_correlation_id(test_id)

        assert correlation_id_context.get() == test_id

    def test_clear_correlation_id(self):
        """Test clear_correlation_id removes ID from context."""
        set_correlation_id('test-id')

        clear_correlation_id()

        assert correlation_id_context.get() is None

    def test_with_correlation_id_decorator(self):
        """Test with_correlation_id decorator functionality."""

        @with_correlation_id('decorator-test-789')
        def test_function():
            return get_correlation_id()

        result = test_function()

        assert result == 'decorator-test-789'

    def test_with_correlation_id_decorator_generates_id(self):
        """Test with_correlation_id decorator generates ID when none provided."""

        @with_correlation_id()
        def test_function():
            return get_correlation_id()

        result = test_function()

        assert result is not None
        # Should be a valid UUID
        uuid.UUID(result)

    def test_with_correlation_id_decorator_isolation(self):
        """Test with_correlation_id decorator isolates context."""
        set_correlation_id('outer-context')

        @with_correlation_id('inner-context')
        def inner_function():
            return get_correlation_id()

        inner_result = inner_function()
        outer_result = get_correlation_id()

        assert inner_result == 'inner-context'
        assert outer_result == 'outer-context'


class TestLoggerMixin:
    """Test LoggerMixin functionality."""

    def test_logger_property(self):
        """Test logger property creates logger with correct name."""

        class TestClass(LoggerMixin):
            pass

        instance = TestClass()
        logger = instance.logger

        assert isinstance(logger, logging.Logger)
        expected_name = f'{TestClass.__module__}.{TestClass.__name__}'
        assert logger.name == expected_name

    def test_logger_property_caching(self):
        """Test logger property caches logger instance."""

        class TestClass(LoggerMixin):
            pass

        instance = TestClass()
        logger1 = instance.logger
        logger2 = instance.logger

        assert logger1 is logger2

    def test_log_with_correlation_methods(self):
        """Test correlation-aware logging methods."""

        class TestClass(LoggerMixin):
            pass

        instance = TestClass()

        # Capture log output
        with patch.object(instance.logger, 'log') as mock_log:
            correlation_id = 'test-correlation-xyz'

            instance.debug('Debug message', correlation_id=correlation_id, extra_field='value')
            instance.info('Info message', correlation_id=correlation_id)
            instance.warning('Warning message', correlation_id=correlation_id)
            instance.error('Error message', correlation_id=correlation_id)
            instance.critical('Critical message', correlation_id=correlation_id)

            # Verify all methods were called with correct parameters
            assert mock_log.call_count == 5

            # Check debug call
            debug_call = mock_log.call_args_list[0]
            assert debug_call[0] == (logging.DEBUG, 'Debug message')
            assert debug_call[1]['extra']['correlation_id'] == correlation_id
            assert debug_call[1]['extra']['extra_field'] == 'value'

            # Check info call
            info_call = mock_log.call_args_list[1]
            assert info_call[0] == (logging.INFO, 'Info message')
            assert info_call[1]['extra']['correlation_id'] == correlation_id


class TestComponentLoggerConfiguration:
    """Test component logger configuration."""

    def test_configure_component_loggers(self):
        """Test configure_component_loggers sets appropriate levels."""
        configure_component_loggers(logging.DEBUG)

        # AWS SDK loggers should be at WARNING or higher
        assert logging.getLogger('boto3').level >= logging.WARNING
        assert logging.getLogger('botocore').level >= logging.WARNING
        assert logging.getLogger('urllib3').level >= logging.WARNING

        # Application loggers should be at DEBUG
        app_logger = logging.getLogger('awslabs.amazon_translate_mcp_server.translation_service')
        assert app_logger.level == logging.DEBUG

    def test_configure_component_loggers_respects_base_level(self):
        """Test configure_component_loggers respects base level for AWS loggers."""
        configure_component_loggers(logging.CRITICAL)

        # AWS SDK loggers should be at CRITICAL (higher than WARNING)
        assert logging.getLogger('boto3').level == logging.CRITICAL
        assert logging.getLogger('botocore').level == logging.CRITICAL


class TestDefaultLoggingConfig:
    """Test default logging configuration."""

    def test_default_config_structure(self):
        """Test default logging configuration has required structure."""
        config = DEFAULT_LOGGING_CONFIG

        assert config['version'] == 1
        assert 'formatters' in config
        assert 'filters' in config
        assert 'handlers' in config
        assert 'root' in config
        assert 'loggers' in config

        # Check formatters
        assert 'structured' in config['formatters']
        assert 'simple' in config['formatters']

        # Check filters
        assert 'correlation_id' in config['filters']

        # Check handlers
        assert 'console' in config['handlers']

        # Check AWS logger configuration
        assert 'boto3' in config['loggers']
        assert 'botocore' in config['loggers']


class TestLoggingIntegration:
    """Test logging integration scenarios."""

    def test_end_to_end_logging_with_correlation_id(self):
        """Test complete logging flow with correlation ID."""
        # Setup logging
        setup_logging(log_level='DEBUG')

        # Create a string buffer to capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.addFilter(CorrelationIdFilter())
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger('test.integration')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Set correlation ID and log message
        correlation_id = 'integration-test-123'
        set_correlation_id(correlation_id)

        logger.info('Integration test message', extra={'operation': 'test'})

        # Check log output
        log_output = log_capture.getvalue()
        assert f'correlation_id={correlation_id}' in log_output
        assert 'message=Integration test message' in log_output
        assert 'operation=test' in log_output

        # Cleanup
        logger.removeHandler(handler)
        clear_correlation_id()


if __name__ == '__main__':
    pytest.main([__file__])
