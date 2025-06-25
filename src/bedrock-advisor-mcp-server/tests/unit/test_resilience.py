"""
Unit tests for the resilience utilities.
"""

import unittest
from unittest.mock import MagicMock

import pytest

from bedrock_advisor.utils.resilience import async_retry, retry


class TestRetry(unittest.TestCase):
    """Test cases for the retry decorator."""

    def test_successful_execution(self):
        """Test successful execution with retry."""
        # Define a test function
        def test_func():
            return "success"

        mock_func = MagicMock(wraps=test_func)

        # Wrap the function with retry
        wrapped_func = retry(max_retries=3)(mock_func)

        # Execute the function
        result = wrapped_func()

        # Verify the result and call count
        self.assertEqual(result, "success")
        mock_func.assert_called_once()

    def test_retry_on_exception(self):
        """Test retry on exception."""
        # Define a test function that raises an exception on first call
        call_count = 0

        def test_func():
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                raise ValueError("test error")
            return "success"

        mock_func = MagicMock(wraps=test_func)

        # Wrap the function with retry
        wrapped_func = retry(max_retries=3, retry_delay=0.01)(mock_func)

        # Execute the function
        result = wrapped_func()

        # Verify the result and call count
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 2)

    def test_max_retries_exceeded(self):
        """Test max retries exceeded."""
        # Define a test function that always raises an exception
        def test_func():
            raise ValueError("test error")

        mock_func = MagicMock(wraps=test_func)

        # Wrap the function with retry
        wrapped_func = retry(max_retries=2, retry_delay=0.01)(mock_func)

        # Execute the function and expect an exception
        with self.assertRaises(ValueError):
            wrapped_func()

        # Verify the call count
        self.assertEqual(mock_func.call_count, 3)  # Initial call + 2 retries


class TestAsyncRetry:
    """Test cases for the async_retry decorator."""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test successful execution with retry."""
        # Define a test function
        mock_func = MagicMock()
        mock_func.return_value = "success"

        # Wrap the function with retry
        @async_retry(max_retries=3)
        async def test_func():
            return mock_func()

        # Execute the function
        result = await test_func()

        # Verify the result and call count
        assert result == "success"
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_exception(self):
        """Test retry on exception."""
        # Define a test function that raises an exception on first call
        mock_func = MagicMock(side_effect=[ValueError("test error"), "success"])

        # Wrap the function with retry
        @async_retry(max_retries=3, retry_delay=0.01)
        async def test_func():
            return mock_func()

        # Execute the function
        result = await test_func()

        # Verify the result and call count
        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test max retries exceeded."""
        # Define a test function that always raises an exception
        mock_func = MagicMock(side_effect=ValueError("test error"))

        # Wrap the function with retry
        @async_retry(max_retries=2, retry_delay=0.01)
        async def test_func():
            return mock_func()

        # Execute the function and expect an exception
        with pytest.raises(ValueError):
            await test_func()

        # Verify the call count
        assert mock_func.call_count == 3  # Initial call + 2 retries
