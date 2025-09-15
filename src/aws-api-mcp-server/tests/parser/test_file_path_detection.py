from awslabs.aws_api_mcp_server.core.common.command_metadata import CommandMetadata
from awslabs.aws_api_mcp_server.core.common.file_operations import (
    _could_be_file_path,
    _is_remote_path,
    extract_file_paths_from_parameters,
)


def test_is_remote_path():
    """Test detection of remote paths that should not be validated."""
    remote_paths = [
        's3://bucket/key',
        'http://example.com',
        'https://example.com/file',
        'ftp://ftp.example.com',
        'arn:aws:s3:::bucket/key',
    ]

    for path in remote_paths:
        assert _is_remote_path(path), f"'{path}' should be treated as remote"

    local_paths = [
        '/tmp/file.txt',
        './config.yaml',
        'response.json',
        '~/document.pdf',
    ]

    for path in local_paths:
        assert not _is_remote_path(path), f"'{path}' should not be treated as remote"


def test_could_be_file_path():
    """Test conservative file path detection."""
    # Should be detected as file paths
    file_paths = [
        'response.json',
        '/tmp/file.txt',
        './config.yaml',
        'folder/file.csv',
        'document.pdf',
    ]

    for path in file_paths:
        assert _could_be_file_path(path), f"'{path}' should be detected as file path"

    # Should NOT be detected as file paths
    non_file_paths = [
        'i-1234567890abcdef0',  # EC2 instance ID
        'sg-1234567890abcdef0',  # Security group ID
        'my-function',  # Lambda function name
        '-',  # stdout/stdin
        'a',  # Too short
    ]

    for path in non_file_paths:
        assert not _could_be_file_path(path), f"'{path}' should not be detected as file path"


def test_comprehensive_file_extraction():
    """Test comprehensive file path extraction."""
    # Test S3 operations
    metadata = CommandMetadata('s3', 's3', 'cp')
    parameters = {'--paths': ['s3://bucket/key', '/tmp/local.txt', 'local.json']}

    file_paths = extract_file_paths_from_parameters(metadata, parameters)
    assert '/tmp/local.txt' in file_paths
    assert 'local.json' in file_paths
    assert 's3://bucket/key' not in file_paths

    # Test binary output operations
    metadata = CommandMetadata('lambda', 'lambda', 'invoke')
    parameters = {'--function-name': 'my-function', 'output.json': 'value'}

    file_paths = extract_file_paths_from_parameters(metadata, parameters)
    assert 'output.json' in file_paths
    assert 'my-function' not in file_paths  # Function name excluded by heuristics
