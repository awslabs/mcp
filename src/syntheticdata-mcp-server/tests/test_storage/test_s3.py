"""Tests for S3 storage functionality."""

import pandas as pd
import pytest
from awslabs.syntheticdata_mcp_server.storage.s3 import S3Target


@pytest.fixture
def s3_target(mock_s3) -> S3Target:
    """Create an S3Target instance with mocked S3 client."""
    return S3Target()


async def test_validate_config_success(s3_target: S3Target, sample_data: dict) -> None:
    """Test successful config validation."""
    config = {
        'bucket': 'test-bucket',
        'prefix': 'data/',
        'format': 'csv',
        'storage': {'class': 'STANDARD', 'encryption': 'AES256'},
    }

    is_valid = await s3_target.validate(sample_data, config)
    assert is_valid is True


@pytest.mark.parametrize(
    'config,expected',
    [
        (
            {'bucket': 'test-bucket', 'prefix': 'data/'},  # Missing format
            False,
        ),
        (
            {'bucket': 'test-bucket', 'prefix': 'data/', 'format': 'invalid'},  # Invalid format
            False,
        ),
        (
            {'prefix': 'data/', 'format': 'csv'},  # Missing bucket
            False,
        ),
    ],
)
async def test_validate_config_invalid(
    s3_target: S3Target, sample_data: dict, config: dict, expected: bool
) -> None:
    """Test validation with invalid configurations."""
    is_valid = await s3_target.validate(sample_data, config)
    assert is_valid is expected


async def test_load_success(s3_target: S3Target, sample_data: dict) -> None:
    """Test successful data loading to S3."""
    config = {
        'bucket': 'test-bucket',
        'prefix': 'data/',
        'format': 'csv',
        'storage': {'class': 'STANDARD', 'encryption': 'AES256'},
    }

    result = await s3_target.load(sample_data, config)
    assert result['success'] is True
    assert 'uploaded_files' in result
    assert len(result['uploaded_files']) == len(sample_data)


async def test_load_with_partitioning(s3_target: S3Target) -> None:
    """Test data loading with partitioning enabled."""
    # Create test data with partition column
    data = {
        'orders': [
            {'order_id': 1, 'status': 'pending', 'amount': 100},
            {'order_id': 2, 'status': 'completed', 'amount': 200},
            {'order_id': 3, 'status': 'pending', 'amount': 300},
        ]
    }

    config = {
        'bucket': 'test-bucket',
        'prefix': 'data/',
        'format': 'csv',
        'partitioning': {'enabled': True, 'columns': ['status']},
        'storage': {'class': 'STANDARD', 'encryption': 'AES256'},
    }

    result = await s3_target.load(data, config)
    assert result['success'] is True

    # Should create partitioned files
    uploaded_files = result['uploaded_files']
    assert len(uploaded_files) == 2  # One for each status value
    assert any('status=pending' in f['key'] for f in uploaded_files)
    assert any('status=completed' in f['key'] for f in uploaded_files)


@pytest.mark.parametrize(
    'format,compression', [('csv', None), ('json', None), ('parquet', 'snappy')]
)
async def test_convert_format(s3_target: S3Target, format: str, compression: str) -> None:
    """Test DataFrame conversion to different formats."""
    df = pd.DataFrame({'id': [1, 2], 'name': ['test1', 'test2']})

    content = s3_target._convert_format(df, format, compression)
    assert isinstance(content, bytes)
    assert len(content) > 0


async def test_convert_format_invalid(s3_target: S3Target) -> None:
    """Test conversion with invalid format."""
    df = pd.DataFrame({'id': [1]})

    with pytest.raises(ValueError, match='Unsupported format'):
        s3_target._convert_format(df, 'invalid', None)


async def test_apply_partitioning(s3_target: S3Target) -> None:
    """Test DataFrame partitioning."""
    dataframes = {
        'orders': pd.DataFrame(
            {
                'order_id': [1, 2, 3, 4],
                'status': ['pending', 'completed', 'pending', 'shipped'],
                'amount': [100, 200, 300, 400],
            }
        )
    }

    partition_config = {'columns': ['status'], 'drop_columns': True}

    result = s3_target._apply_partitioning(dataframes, partition_config)

    assert 'orders' in result
    partitions = result['orders']
    assert len(partitions) == 3  # Three unique status values
    assert 'pending' in str(list(partitions.keys()))
    assert 'completed' in str(list(partitions.keys()))
    assert 'shipped' in str(list(partitions.keys()))

    # Check that partition columns are dropped
    for partition_df in partitions.values():
        assert 'status' not in partition_df.columns


async def test_upload_to_s3(s3_target: S3Target) -> None:
    """Test S3 upload functionality."""
    content = b'test content'
    bucket = 'test-bucket'
    key = 'test/file.txt'
    storage_config = {'class': 'STANDARD', 'encryption': 'AES256'}
    metadata = {'test': 'value'}

    result = await s3_target._upload_to_s3(content, bucket, key, storage_config, metadata)

    assert result['bucket'] == bucket
    assert result['key'] == key
    assert result['size'] == len(content)
    assert result['metadata'] == metadata


async def test_upload_to_s3_error(s3_target: S3Target) -> None:
    """Test S3 upload error handling."""
    with pytest.raises(Exception, match='Failed to upload to S3'):
        await s3_target._upload_to_s3(
            b'content',
            'nonexistent-bucket',  # This should cause an error
            'key',
            {},
            {},
        )
