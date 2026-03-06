"""Tests for common utility functions.

These tests cover validation functions and decorators used across the application.
"""

import os
import pytest
import tempfile
from awslabs.dynamodb_mcp_server.common import (
    handle_exceptions,
    validate_database_name,
    validate_path_within_directory,
)


class TestValidateDatabaseName:
    """Test database name validation."""

    def test_database_name_validation(self):
        """Test database name validation with valid and invalid inputs."""
        # Arrange - Valid names
        valid_names = [
            'test_db',
            'TestDB123',
            'my-database',
            'db$name',
            'database.name',
            'a1_b2-c3$d4.e5',
            'a' * 128,  # Max length (128) should be valid
        ]

        # Act & Assert - Valid names should not raise
        for name in valid_names:
            validate_database_name(name)

        # Arrange - Invalid names
        invalid_names = [
            '',  # Empty
            'test db',  # Space
            'test;db',  # Semicolon
            'test/db',  # Slash
            'test\\db',  # Backslash
            'test|db',  # Pipe
            'test&db',  # Ampersand
            'test(db)',  # Parentheses
            'test[db]',  # Brackets
            'test{db}',  # Braces
            'test<db>',  # Angle brackets
            'test"db"',  # Quotes
            "test'db'",  # Single quotes
            'test`db`',  # Backticks
            'a' * 129,  # Exceeds max length (128)
        ]

        # Act & Assert - Invalid names should raise ValueError
        for name in invalid_names:
            with pytest.raises(ValueError, match='Invalid database name'):
                validate_database_name(name)


class TestValidatePathWithinDirectory:
    """Test path validation within directory."""

    def test_path_validation_scenarios(self):
        """Test various path validation scenarios including valid and invalid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test 1: Valid relative path
            subdir = os.path.join(tmpdir, 'subdir')
            os.makedirs(subdir, exist_ok=True)
            file_path = os.path.join(subdir, 'file.txt')
            result = validate_path_within_directory(file_path, tmpdir, 'test file')
            assert result.startswith(os.path.realpath(tmpdir))
            assert 'subdir' in result

            # Test 2: Valid absolute path
            file_path = os.path.join(tmpdir, 'file.txt')
            result = validate_path_within_directory(file_path, tmpdir, 'test file')
            assert result == os.path.normpath(os.path.realpath(file_path))

            # Test 3: Path equals base directory
            result = validate_path_within_directory(tmpdir, tmpdir, 'test file')
            assert result == os.path.normpath(os.path.realpath(tmpdir))

            # Test 4: Path traversal with relative path
            with pytest.raises(ValueError, match='Path traversal detected'):
                validate_path_within_directory('../../../etc/passwd', tmpdir, 'test file')

            # Test 5: Path traversal with absolute path
            with pytest.raises(ValueError, match='Path traversal detected'):
                validate_path_within_directory('/etc/passwd', tmpdir, 'test file')

            # Test 6: Custom error message
            with pytest.raises(ValueError, match='custom output file'):
                validate_path_within_directory('/etc/passwd', tmpdir, 'custom output file')

            # Test 7: Symlink path traversal (if supported)
            try:
                link_path = os.path.join(tmpdir, 'link')
                os.symlink('/tmp', link_path)
                with pytest.raises(ValueError, match='Path traversal detected'):
                    validate_path_within_directory(link_path, tmpdir, 'test file')
            except OSError:
                pass  # Symlink not supported on this system


class TestHandleExceptionsDecorator:
    """Test handle_exceptions decorator."""

    @pytest.mark.asyncio
    async def test_successful_execution_returns_result(self):
        """Decorated function should return result on success."""

        @handle_exceptions
        async def successful_function():
            return 'success'

        result = await successful_function()

        assert result == 'success'

    @pytest.mark.asyncio
    async def test_exception_returns_error_dict(self):
        """Decorated function should return error dict on exception."""

        @handle_exceptions
        async def failing_function():
            raise ValueError('Test error message')

        result = await failing_function()

        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error'] == 'Test error message'

    @pytest.mark.asyncio
    async def test_preserves_positional_arguments(self):
        """Decorated function should preserve positional arguments."""

        @handle_exceptions
        async def function_with_args(arg1, arg2):
            return f'{arg1} {arg2}'

        result = await function_with_args('hello', 'world')

        assert result == 'hello world'

    @pytest.mark.asyncio
    async def test_preserves_keyword_arguments(self):
        """Decorated function should preserve keyword arguments."""

        @handle_exceptions
        async def function_with_kwargs(name='default', value=0):
            return f'{name}={value}'

        result = await function_with_kwargs(name='test', value=10)

        assert result == 'test=10'

    @pytest.mark.asyncio
    async def test_exception_with_arguments_returns_error(self):
        """Decorated function with args should return error dict on exception."""

        @handle_exceptions
        async def function_with_args(arg1, arg2):
            raise RuntimeError(f'Failed with {arg2}')

        result = await function_with_args('fail', 'test')

        assert isinstance(result, dict)
        assert 'Failed with test' in result['error']

    @pytest.mark.asyncio
    async def test_exception_with_kwargs_returns_error(self):
        """Decorated function with kwargs should return error dict on exception."""

        @handle_exceptions
        async def function_with_kwargs(name='default', value=0):
            raise ValueError(f'Invalid value for {name}')

        result = await function_with_kwargs(name='test', value=-5)

        assert isinstance(result, dict)
        assert 'Invalid value for test' in result['error']

    @pytest.mark.asyncio
    async def test_logs_exception_with_function_name(self, caplog):
        """Decorator should log exception with function name."""

        @handle_exceptions
        async def my_failing_function():
            raise ValueError('Something went wrong')

        with caplog.at_level('ERROR'):
            await my_failing_function()

        assert 'my_failing_function' in caplog.text
        assert 'Something went wrong' in caplog.text

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        """Decorator should preserve original function metadata."""

        @handle_exceptions
        async def documented_function():
            """This is the docstring."""
            return 'result'

        assert documented_function.__name__ == 'documented_function'
        assert documented_function.__doc__ == 'This is the docstring.'
