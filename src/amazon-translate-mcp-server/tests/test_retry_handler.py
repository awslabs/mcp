"""Unit tests for retry handler functionality in Amazon Translate MCP Server.

Tests retry logic, exponential backoff, and error handling scenarios.
"""

import pytest
import time
from awslabs.amazon_translate_mcp_server.exceptions import (
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
    ValidationError,
)
from awslabs.amazon_translate_mcp_server.retry_handler import (
    BATCH_RETRY_CONFIG,
    DEFAULT_RETRY_CONFIG,
    TERMINOLOGY_RETRY_CONFIG,
    TRANSLATION_RETRY_CONFIG,
    RetryConfig,
    RetryHandler,
    with_async_retry,
    with_retry,
)
from unittest.mock import Mock


class TestRetryConfig:
    """Test RetryConfig functionality."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert RateLimitError in config.retryable_exceptions
        assert ServiceUnavailableError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
            retryable_exceptions=[RateLimitError],
        )

        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert config.retryable_exceptions == [RateLimitError]

    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=60.0, jitter=False)

        # Test exponential progression
        assert config.calculate_delay(0) == 1.0  # 1.0 * 2^0
        assert config.calculate_delay(1) == 2.0  # 1.0 * 2^1
        assert config.calculate_delay(2) == 4.0  # 1.0 * 2^2
        assert config.calculate_delay(3) == 8.0  # 1.0 * 2^3

    def test_calculate_delay_with_max_limit(self):
        """Test delay calculation respects max_delay."""
        config = RetryConfig(base_delay=10.0, exponential_base=2.0, max_delay=15.0, jitter=False)

        # Should be capped at max_delay
        assert config.calculate_delay(5) == 15.0

    def test_calculate_delay_with_retry_after(self):
        """Test delay calculation with server-specified retry_after."""
        config = RetryConfig(jitter=False)

        delay = config.calculate_delay(0, retry_after=30)
        assert delay == 30.0

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation includes jitter."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=True)

        # With jitter, delay should vary slightly
        delays = [config.calculate_delay(1) for _ in range(10)]

        # All delays should be around 2.0 but with some variation
        assert all(1.8 <= delay <= 2.2 for delay in delays)
        assert len(set(delays)) > 1  # Should have variation

    def test_should_retry_retryable_exceptions(self):
        """Test retry decision for retryable exceptions."""
        config = RetryConfig(max_attempts=3)

        # Should retry retryable exceptions within attempt limit
        assert config.should_retry(RateLimitError('Rate limit', retry_after=30), 0) is True
        assert config.should_retry(ServiceUnavailableError('Unavailable'), 1) is True
        assert config.should_retry(TimeoutError('Timeout', 30), 2) is True

    def test_should_retry_non_retryable_exceptions(self):
        """Test retry decision for non-retryable exceptions."""
        config = RetryConfig(max_attempts=3)

        # Should not retry non-retryable exceptions
        assert config.should_retry(ValidationError('Invalid'), 0) is False
        assert config.should_retry(ValueError('Generic error'), 0) is False

    def test_should_retry_attempt_limit(self):
        """Test retry decision respects attempt limit."""
        config = RetryConfig(max_attempts=3)

        # Should not retry when at attempt limit
        assert config.should_retry(RateLimitError('Rate limit', retry_after=30), 3) is False
        assert config.should_retry(RateLimitError('Rate limit', retry_after=30), 5) is False

    def test_should_retry_aws_errors(self):
        """Test retry decision for AWS service errors."""
        config = RetryConfig(max_attempts=3)

        # Mock AWS errors
        throttling_error = Mock()
        throttling_error.response = {'Error': {'Code': 'ThrottlingException'}}

        service_error = Mock()
        service_error.response = {'Error': {'Code': 'ServiceUnavailableException'}}

        validation_error = Mock()
        validation_error.response = {'Error': {'Code': 'ValidationException'}}

        # Should retry throttling and service errors
        assert config.should_retry(throttling_error, 0) is True
        assert config.should_retry(service_error, 0) is True

        # Should not retry validation errors
        assert config.should_retry(validation_error, 0) is False


class TestRetryHandler:
    """Test RetryHandler functionality."""

    def test_successful_execution_no_retry(self):
        """Test successful function execution without retries."""
        config = RetryConfig(max_attempts=3)
        handler = RetryHandler(config)

        def success_func():
            return 'success'

        result = handler.retry(success_func)
        assert result == 'success'

    def test_retry_on_retryable_error(self):
        """Test retry behavior on retryable errors."""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        handler = RetryHandler(config)

        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError('Rate limit', retry_after=1)
            return 'success'

        start_time = time.time()
        result = handler.retry(failing_func)
        end_time = time.time()

        assert result == 'success'
        assert call_count == 3
        # Should have some delay between retries
        assert end_time - start_time >= 0.02  # At least 2 delays of 0.01s

    def test_retry_exhaustion(self):
        """Test behavior when all retry attempts are exhausted."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        handler = RetryHandler(config)

        call_count = 0

        def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise RateLimitError('Always fails', retry_after=1)

        with pytest.raises(RateLimitError):
            handler.retry(always_failing_func)

        assert call_count == 2  # Should try max_attempts times

    def test_non_retryable_error_immediate_failure(self):
        """Test immediate failure on non-retryable errors."""
        config = RetryConfig(max_attempts=3)
        handler = RetryHandler(config)

        call_count = 0

        def validation_error_func():
            nonlocal call_count
            call_count += 1
            raise ValidationError('Invalid input')

        with pytest.raises(ValidationError):
            handler.retry(validation_error_func)

        assert call_count == 1  # Should not retry

    def test_aws_error_mapping(self):
        """Test AWS error mapping during retry."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        handler = RetryHandler(config)

        def aws_error_func():
            # Simulate AWS throttling error
            from botocore.exceptions import ClientError

            aws_error = ClientError(
                error_response={
                    'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}
                },
                operation_name='TestOperation',
            )
            raise aws_error

        with pytest.raises(RateLimitError) as exc_info:
            handler.retry(aws_error_func)

        # Should be mapped to RateLimitError
        assert exc_info.value.error_code == 'ThrottlingException'

    def test_retry_with_correlation_id(self):
        """Test retry with correlation ID tracking."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        handler = RetryHandler(config)

        correlation_id = 'test-correlation-123'

        def failing_func():
            raise RateLimitError('Rate limit', retry_after=1, correlation_id=correlation_id)

        with pytest.raises(RateLimitError) as exc_info:
            handler.retry(failing_func, correlation_id=correlation_id)

        # Correlation ID should be preserved
        assert exc_info.value.correlation_id == correlation_id


class TestAsyncRetryHandler:
    """Test async retry handler functionality."""

    @pytest.mark.asyncio
    async def test_async_successful_execution(self):
        """Test successful async function execution."""
        config = RetryConfig(max_attempts=3)
        handler = RetryHandler(config)

        async def async_success_func():
            return 'async_success'

        result = await handler.async_retry(async_success_func)
        assert result == 'async_success'

    @pytest.mark.asyncio
    async def test_async_retry_on_error(self):
        """Test async retry behavior on retryable errors."""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        handler = RetryHandler(config)

        call_count = 0

        async def async_failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ServiceUnavailableError('Service down')
            return 'async_success'

        start_time = time.time()
        result = await handler.async_retry(async_failing_func)
        end_time = time.time()

        assert result == 'async_success'
        assert call_count == 3
        # Should have some delay between retries
        assert end_time - start_time >= 0.02

    @pytest.mark.asyncio
    async def test_async_retry_exhaustion(self):
        """Test async retry exhaustion."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        handler = RetryHandler(config)

        async def async_always_failing():
            raise TimeoutError('Always times out', 30)

        with pytest.raises(TimeoutError):
            await handler.async_retry(async_always_failing)


class TestRetryDecorators:
    """Test retry decorators."""

    def test_with_retry_decorator(self):
        """Test with_retry decorator functionality."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)

        call_count = 0

        @with_retry(config)
        def decorated_func(correlation_id=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError('Rate limit', retry_after=1)
            return 'decorated_success'

        result = decorated_func(correlation_id='test-123')
        assert result == 'decorated_success'
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_async_retry_decorator(self):
        """Test with_async_retry decorator functionality."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)

        call_count = 0

        @with_async_retry(config)
        async def async_decorated_func(correlation_id=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ServiceUnavailableError('Service down')
            return 'async_decorated_success'

        result = await async_decorated_func(correlation_id='test-456')
        assert result == 'async_decorated_success'
        assert call_count == 2

    def test_decorator_with_custom_correlation_param(self):
        """Test decorator with custom correlation ID parameter name."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)

        @with_retry(config, correlation_id_param='request_id')
        def func_with_custom_param(request_id=None):
            raise RateLimitError('Rate limit', retry_after=1)

        with pytest.raises(RateLimitError):
            func_with_custom_param(request_id='custom-123')


class TestPredefinedConfigs:
    """Test predefined retry configurations."""

    def test_default_retry_config(self):
        """Test default retry configuration values."""
        assert DEFAULT_RETRY_CONFIG.max_attempts == 3
        assert DEFAULT_RETRY_CONFIG.base_delay == 1.0
        assert DEFAULT_RETRY_CONFIG.max_delay == 60.0

    def test_batch_retry_config(self):
        """Test batch operation retry configuration."""
        assert BATCH_RETRY_CONFIG.max_attempts == 5
        assert BATCH_RETRY_CONFIG.base_delay == 2.0
        assert BATCH_RETRY_CONFIG.max_delay == 300.0  # 5 minutes

    def test_terminology_retry_config(self):
        """Test terminology operation retry configuration."""
        assert TERMINOLOGY_RETRY_CONFIG.max_attempts == 3
        assert TERMINOLOGY_RETRY_CONFIG.base_delay == 1.0
        assert TERMINOLOGY_RETRY_CONFIG.max_delay == 30.0

    def test_translation_retry_config(self):
        """Test translation operation retry configuration."""
        assert TRANSLATION_RETRY_CONFIG.max_attempts == 3
        assert TRANSLATION_RETRY_CONFIG.base_delay == 0.5
        assert TRANSLATION_RETRY_CONFIG.max_delay == 10.0  # Shorter for real-time


class TestRetryIntegration:
    """Test retry handler integration scenarios."""

    def test_retry_with_server_specified_delay(self):
        """Test retry respects server-specified retry_after."""
        config = RetryConfig(max_attempts=2, base_delay=1.0, jitter=False)
        handler = RetryHandler(config)

        def rate_limited_func():
            raise RateLimitError('Rate limited', retry_after=5)

        start_time = time.time()

        with pytest.raises(RateLimitError):
            handler.retry(rate_limited_func)

        end_time = time.time()

        # Should wait approximately 5 seconds (server-specified delay)
        assert end_time - start_time >= 4.5  # Allow some tolerance

    def test_retry_preserves_exception_details(self):
        """Test that retry preserves original exception details."""
        config = RetryConfig(max_attempts=2)
        handler = RetryHandler(config)

        original_correlation_id = 'original-123'

        def detailed_error_func():
            raise RateLimitError(
                message='Detailed rate limit error',
                retry_after=30,
                correlation_id=original_correlation_id,
                details={'quota_type': 'requests_per_minute'},
            )

        with pytest.raises(RateLimitError) as exc_info:
            handler.retry(detailed_error_func)

        exc = exc_info.value
        assert exc.message == 'Detailed rate limit error'
        assert exc.retry_after == 30
        assert exc.correlation_id == original_correlation_id
        assert exc.details['quota_type'] == 'requests_per_minute'


if __name__ == '__main__':
    pytest.main([__file__])
