import pytest
from awslabs.aws_api_mcp_server.core.common.errors import SanitizedException


@pytest.mark.parametrize(
    'exception,expected_message',
    [
        (ValueError('some value'), 'An invalid value was provided.'),
        (
            FileNotFoundError(2, 'No such file or directory', '/secret/path/to/file'),
            'The requested file was not found.',
        ),
        (FileExistsError(17, 'File exists', '/secret/path/to/file'), 'The file already exists.'),
        (
            IsADirectoryError(21, 'Is a directory', '/secret/path/to/dir'),
            'The path is a directory, not a file.',
        ),
        (
            NotADirectoryError(20, 'Not a directory', '/secret/path/to/file'),
            'The path is not a directory.',
        ),
        (PermissionError(13, 'Permission denied', '/secret/path/to/file'), 'Permission denied.'),
        (
            OSError(28, 'No space left on device', '/secret/path/to/file'),
            'An OS error occurred.',
        ),
    ],
    ids=[
        'ValueError',
        'FileNotFoundError',
        'FileExistsError',
        'IsADirectoryError',
        'NotADirectoryError',
        'PermissionError',
        'OSError',
    ],
)
def test_sanitized_exception_uses_safe_message(exception, expected_message):
    """Test that SanitizedException maps known exception types to safe messages."""
    sanitized = SanitizedException(exception)
    assert str(sanitized) == expected_message


@pytest.mark.parametrize(
    'exception',
    [
        FileNotFoundError(2, 'No such file or directory', '/secret/path/to/file'),
        FileExistsError(17, 'File exists', '/secret/path/to/file'),
        IsADirectoryError(21, 'Is a directory', '/secret/path/to/dir'),
        NotADirectoryError(20, 'Not a directory', '/secret/path/to/file'),
        PermissionError(13, 'Permission denied', '/secret/path/to/file'),
        OSError(28, 'No space left on device', '/secret/path/to/file'),
    ],
    ids=[
        'FileNotFoundError',
        'FileExistsError',
        'IsADirectoryError',
        'NotADirectoryError',
        'PermissionError',
        'OSError',
    ],
)
def test_sanitized_exception_does_not_leak_file_path(exception):
    """Test that SanitizedException does not leak file paths from the original exception."""
    sanitized = SanitizedException(exception)
    assert '/secret/path' not in str(sanitized)


def test_sanitized_exception_stores_original():
    """Test that SanitizedException stores the original exception."""
    original = ValueError('original error')
    sanitized = SanitizedException(original)
    assert sanitized.original is original


def test_sanitized_exception_uses_default_message_for_unknown_type():
    """Test that SanitizedException uses a default message for unmapped exception types."""
    sanitized = SanitizedException(RuntimeError('something went wrong'))
    assert str(sanitized) == 'A RuntimeError occurred.'


def test_sanitized_exception_resolves_most_specific_message():
    """Test that SanitizedException resolves the most specific safe message via MRO.

    FileNotFoundError inherits from OSError, but should match its own entry first.
    """
    sanitized = SanitizedException(FileNotFoundError(2, 'No such file or directory', '/tmp/x'))
    assert str(sanitized) == 'The requested file was not found.'


def test_sanitized_exception_is_exception():
    """Test that SanitizedException is an Exception subclass."""
    sanitized = SanitizedException(ValueError('test'))
    assert isinstance(sanitized, Exception)


def test_sanitized_exception_all_file_exceptions_with_path_are_covered():
    """Test that all built-in file-related exceptions that include path in their message are covered.

    These are the OSError subclasses that set the filename attribute and include it in str().
    """
    file_path_exceptions = [
        FileNotFoundError,
        FileExistsError,
        IsADirectoryError,
        NotADirectoryError,
        PermissionError,
    ]
    for exc_type in file_path_exceptions:
        assert exc_type in SanitizedException._SAFE_MESSAGES, (
            f'{exc_type.__name__} is not covered in _SAFE_MESSAGES'
        )
