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
    async def test_exception_decorator_behavior(self):
        """Test handle_exceptions decorator with various scenarios."""

        # Test 1: Successful execution
        @handle_exceptions
        async def successful_function():
            return 'success'

        result = await successful_function()
        assert result == 'success'

        # Test 2: Exception handling
        @handle_exceptions
        async def failing_function():
            raise ValueError('Test error message')

        result = await failing_function()
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error'] == 'Test error message'

        # Test 3: Function with arguments
        @handle_exceptions
        async def function_with_args(arg1, arg2):
            if arg1 == 'fail':
                raise RuntimeError(f'Failed with {arg2}')
            return f'{arg1} {arg2}'

        success_result = await function_with_args('hello', 'world')
        assert success_result == 'hello world'

        error_result = await function_with_args('fail', 'test')
        assert isinstance(error_result, dict)
        assert 'Failed with test' in error_result['error']

        # Test 4: Function with kwargs
        @handle_exceptions
        async def function_with_kwargs(name='default', value=0):
            if value < 0:
                raise ValueError(f'Invalid value for {name}')
            return f'{name}={value}'

        success_result = await function_with_kwargs(name='test', value=10)
        assert success_result == 'test=10'

        error_result = await function_with_kwargs(name='test', value=-5)
        assert isinstance(error_result, dict)
        assert 'Invalid value for test' in error_result['error']
