"""Tests for S3 storage functionality."""

import pandas as pd
import pytest
from awslabs.syntheticdata_mcp_server.storage.s3 import S3Target
from concurrent.futures import ThreadPoolExecutor
from pytest import mark
from typing import Any, Dict, List, cast
from unittest.mock import MagicMock


@pytest.fixture
def s3_target(mock_s3) -> S3Target:
    """Create an S3Target instance with mocked S3 client."""
    return S3Target()


def test_s3_target_init(monkeypatch) -> None:
    """Test S3Target initialization."""
    # Mock AWS profile
    test_profile = 'test_profile'
    monkeypatch.setenv('AWS_PROFILE', test_profile)

    # Mock boto3 session
    class MockSession:
        def __init__(self, profile_name=None):
            self.profile_name = profile_name

        def client(self, service_name):
            assert service_name == 's3'
            return {}

    monkeypatch.setattr('boto3.Session', MockSession)

    # Create target
    target = S3Target()

    # Verify initialization
    assert isinstance(target.executor, ThreadPoolExecutor)
    assert target.executor._max_workers == 4
    assert target.supported_formats == ['csv', 'json', 'parquet']


@mark.asyncio
async def test_validate_with_empty_data(s3_target: S3Target) -> None:
    """Test validation with empty data."""
    config = {
        'bucket': 'test-bucket',
        'prefix': 'data/',
        'format': 'csv',
    }

    # Test with empty dict
    is_valid = await s3_target.validate({}, config)
    assert is_valid is False

    # Test with None - use cast to satisfy type checker
    is_valid = await s3_target.validate(cast(Dict[str, List[Dict[str, Any]]], None), config)
    assert is_valid is False


@mark.asyncio
async def test_validate_with_invalid_data_structure(s3_target: S3Target) -> None:
    """Test validation with invalid data structures."""
    config = {
        'bucket': 'test-bucket',
        'prefix': 'data/',
        'format': 'csv',
    }

    # Test with non-list records
    invalid_data = {
        'table1': {'id': 1, 'name': 'test'},  # Should be a list
        'table2': [{'id': 2, 'name': 'test2'}],
    }
    is_valid = await s3_target.validate(invalid_data, config)
    assert is_valid is False


@mark.asyncio
async def test_validate_s3_access_error(s3_target: S3Target, sample_data: dict) -> None:
    """Test validation when S3 access fails."""

    def mock_head_bucket(**kwargs):
        raise Exception('Access denied')

    # Replace head_bucket with mock
    s3_target.s3_client = MagicMock()  # type: ignore
    s3_target.s3_client.head_bucket = mock_head_bucket  # type: ignore

    config = {
        'bucket': 'test-bucket',
        'prefix': 'data/',
        'format': 'csv',
    }

    is_valid = await s3_target.validate(sample_data, config)
    assert is_valid is False


@mark.asyncio
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
@mark.asyncio
async def test_validate_config_invalid(
    s3_target: S3Target, sample_data: dict, config: dict, expected: bool
) -> None:
    """Test validation with invalid configurations."""
    is_valid = await s3_target.validate(sample_data, config)
    assert is_valid is expected


@mark.asyncio
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


@mark.asyncio
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

    # Verify partition paths
    keys = [f['key'] for f in uploaded_files]
    assert any(k.endswith('orders.csv') for k in keys)  # Check file name
    assert any('data/orders/pending/' in k for k in keys)  # Check pending partition
    assert any('data/orders/completed/' in k for k in keys)  # Check completed partition


@pytest.mark.parametrize(
    'format,compression', [('csv', None), ('json', None), ('parquet', 'snappy')]
)
@mark.asyncio
async def test_convert_format(s3_target: S3Target, format: str, compression: str) -> None:
    """Test DataFrame conversion to different formats."""
    df = pd.DataFrame({'id': [1, 2], 'name': ['test1', 'test2']})

    content = s3_target._convert_format(df, format, compression)
    assert isinstance(content, bytes)
    assert len(content) > 0


@mark.asyncio
async def test_convert_format_empty_dataframe(s3_target: S3Target) -> None:
    """Test converting empty DataFrame."""
    # Create empty DataFrame with defined schema
    df = pd.DataFrame(data={}, columns=pd.Index(['id', 'value']))

    # Test CSV format
    content = s3_target._convert_format(df, 'csv')
    assert isinstance(content, bytes)
    assert len(content) > 0  # Should contain header row
    assert b'id,value' in content  # Verify headers are present

    # Test JSON format
    content = s3_target._convert_format(df, 'json')
    assert isinstance(content, bytes)
    assert content == b'[]'  # Empty JSON array

    # Test Parquet format
    content = s3_target._convert_format(df, 'parquet')
    assert isinstance(content, bytes)
    assert len(content) > 0  # Should contain Parquet metadata


@mark.asyncio
async def test_convert_format_with_special_characters(s3_target: S3Target) -> None:
    """Test handling of special characters in data."""
    df = pd.DataFrame(
        {
            'id': [1, 2],
            'text': ['Test, with comma', 'Test\nwith\nnewlines'],
            'unicode': ['测试', '🌟'],
        }
    )

    # Test CSV format
    csv_content = s3_target._convert_format(df, 'csv')
    assert isinstance(csv_content, bytes)
    assert b'Test, with comma' in csv_content
    assert b'Test\nwith\nnewlines' in csv_content

    # Test JSON format
    json_content = s3_target._convert_format(df, 'json')
    assert isinstance(json_content, bytes)
    assert b'Test, with comma' in json_content
    assert b'Test\\nwith\\nnewlines' in json_content


@pytest.mark.parametrize(
    'format,compression,expected_size_ratio',
    [
        ('csv', 'gzip', 1.5),  # Allow for some overhead
        ('json', 'gzip', 1.5),
        ('parquet', 'snappy', 1.0),
        ('parquet', 'gzip', 1.0),
        ('parquet', None, 1.0),  # No compression
    ],
)
@mark.asyncio
async def test_convert_format_compression_options(
    s3_target: S3Target, format: str, compression: str, expected_size_ratio: float
) -> None:
    """Test different compression options for each format."""
    # Create a DataFrame with repetitive data for better compression
    df = pd.DataFrame(
        {'id': range(100), 'text': ['test text ' * 10] * 100, 'numbers': [1.23456789] * 100}
    )

    # Get uncompressed size
    uncompressed = s3_target._convert_format(df, format, None)

    # Get compressed size
    compressed = s3_target._convert_format(df, format, compression)

    # Verify compression ratio
    if compression:
        ratio = len(compressed) / len(uncompressed)
        assert ratio <= expected_size_ratio


@mark.asyncio
async def test_convert_format_invalid(s3_target: S3Target) -> None:
    """Test conversion with invalid format."""
    df = pd.DataFrame({'id': [1]})

    with pytest.raises(ValueError, match='Unsupported format'):
        s3_target._convert_format(df, 'invalid', None)


@mark.asyncio
async def test_apply_partitioning_multiple_columns(s3_target: S3Target) -> None:
    """Test partitioning by multiple columns."""
    dataframes = {
        'sales': pd.DataFrame(
            {
                'order_id': range(1, 5),
                'region': ['US', 'US', 'EU', 'EU'],
                'status': ['completed', 'pending', 'completed', 'pending'],
                'amount': [100, 200, 300, 400],
            }
        )
    }

    partition_config = {'columns': ['region', 'status'], 'drop_columns': True}

    result = s3_target._apply_partitioning(dataframes, partition_config)

    # Check partitions
    assert 'sales' in result
    partitions = result['sales']
    assert len(partitions) == 4  # US/completed, US/pending, EU/completed, EU/pending

    # Check partition keys
    keys = list(partitions.keys())
    assert 'US/completed' in str(keys)
    assert 'US/pending' in str(keys)
    assert 'EU/completed' in str(keys)
    assert 'EU/pending' in str(keys)

    # Check columns are dropped
    for partition_df in partitions.values():
        assert 'region' not in partition_df.columns
        assert 'status' not in partition_df.columns


@mark.asyncio
async def test_apply_partitioning_missing_columns(s3_target: S3Target) -> None:
    """Test partitioning when columns don't exist."""
    dataframes = {'data': pd.DataFrame({'id': [1, 2], 'value': ['a', 'b']})}

    partition_config = {'columns': ['missing_column'], 'drop_columns': True}

    result = s3_target._apply_partitioning(dataframes, partition_config)

    # Should return original DataFrame in default partition
    assert 'data' in result
    assert '' in result['data']  # Default partition key
    assert result['data'][''].equals(dataframes['data'])


@mark.asyncio
async def test_apply_partitioning_with_null_values(s3_target: S3Target) -> None:
    """Test partitioning with null values."""
    dataframes = {
        'data': pd.DataFrame(
            {'id': [1, 2, 3, 4], 'category': ['A', None, 'B', pd.NA], 'value': [10, 20, 30, 40]}
        )
    }

    partition_config = {'columns': ['category'], 'drop_columns': True}

    result = s3_target._apply_partitioning(dataframes, partition_config)

    # Check partitions
    partitions = result['data']
    assert len(partitions) == 2  # A, B (null values are skipped)

    # Verify values are handled
    keys = list(partitions.keys())
    assert 'A' in str(keys)
    assert 'B' in str(keys)


@mark.asyncio
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


@mark.asyncio
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


@mark.asyncio
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


@mark.asyncio
async def test_load_with_multiple_tables(s3_target: S3Target) -> None:
    """Test loading multiple tables simultaneously."""
    data = {
        'customers': [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}],
        'orders': [
            {'id': 1, 'customer_id': 1, 'amount': 100},
            {'id': 2, 'customer_id': 1, 'amount': 200},
            {'id': 3, 'customer_id': 2, 'amount': 300},
        ],
        'products': [
            {'id': 1, 'name': 'Product A', 'price': 50},
            {'id': 2, 'name': 'Product B', 'price': 75},
        ],
    }

    config = {
        'bucket': 'test-bucket',
        'prefix': 'data/',
        'format': 'csv',
        'storage': {'class': 'STANDARD', 'encryption': 'AES256'},
    }

    result = await s3_target.load(data, config)

    assert result['success'] is True
    assert len(result['uploaded_files']) == 3  # One file per table
    assert result['total_records'] == 7  # Total records across all tables

    # Verify file paths
    uploaded_keys = [f['key'] for f in result['uploaded_files']]
    assert 'data/customers/customers.csv' in uploaded_keys
    assert 'data/orders/orders.csv' in uploaded_keys
    assert 'data/products/products.csv' in uploaded_keys


@mark.asyncio
async def test_load_with_large_data(s3_target: S3Target) -> None:
    """Test loading large datasets."""
    # Create a moderately sized dataset for testing
    num_records = 1000
    data = {
        'large_table': [
            {
                'id': i,
                'name': f'Name {i}',
                'description': 'A' * 100,  # 100 bytes of text per record
                'value': i * 1.23456789,
                'category': 'test' if i % 2 == 0 else 'prod',  # Add some variety for compression
            }
            for i in range(num_records)
        ]
    }

    config = {
        'bucket': 'test-bucket',
        'prefix': 'data/',
        'format': 'parquet',  # Use Parquet for better performance
        'compression': 'snappy',
        'storage': {'class': 'STANDARD'},
    }

    result = await s3_target.load(data, config)

    assert result['success'] is True
    assert result['total_records'] == num_records
    assert len(result['uploaded_files']) == 1

    # Verify the file was uploaded
    uploaded_file = result['uploaded_files'][0]
    assert uploaded_file['key'] == 'data/large_table/large_table.parquet'
    assert uploaded_file['size'] > 0


@pytest.mark.parametrize(
    'storage_class,encryption',
    [
        ('STANDARD', None),
        ('STANDARD_IA', 'AES256'),
        ('ONEZONE_IA', 'aws:kms'),
        ('INTELLIGENT_TIERING', 'AES256'),
        ('GLACIER', None),
    ],
)
@mark.asyncio
async def test_upload_with_storage_options(
    s3_target: S3Target, storage_class: str, encryption: str
) -> None:
    """Test different S3 storage classes and encryption options."""
    data = {'test': [{'id': 1, 'value': 'test'}]}

    config = {
        'bucket': 'test-bucket',
        'prefix': 'data/',
        'format': 'json',
        'storage': {'class': storage_class, **({'encryption': encryption} if encryption else {})},
    }

    result = await s3_target.load(data, config)

    assert result['success'] is True
    assert len(result['uploaded_files']) == 1

    # Verify storage options were applied
    uploaded_file = result['uploaded_files'][0]
    response = s3_target.s3_client.head_object(
        Bucket=uploaded_file['bucket'], Key=uploaded_file['key']
    )

    # For STANDARD storage class, the key is not included in response
    if storage_class != 'STANDARD':
        assert response['StorageClass'] == storage_class
    if encryption:
        assert response.get('ServerSideEncryption') == encryption


@mark.asyncio
async def test_parquet_with_complex_data(s3_target: S3Target) -> None:
    """Test parquet format with complex data types and snappy compression."""
    # Create a DataFrame with various data types
    df = pd.DataFrame(
        {
            'int_col': [1, 2, 3],
            'float_col': [1.1, 2.2, 3.3],
            'str_col': ['a', 'b', 'c'],
            'bool_col': [True, False, True],
            'datetime_col': pd.date_range('2024-01-01', periods=3),
            'category_col': pd.Series(['A', 'B', 'A']).astype('category'),
            'nullable_int': pd.array([1, None, 3], dtype='Int64'),
            'unicode_col': ['测试', '🌟', 'ascii'],
        }
    )

    # Test parquet with snappy compression
    content = s3_target._convert_format(df, 'parquet', 'snappy')
    assert isinstance(content, bytes)
    assert len(content) > 0

    # Verify the content can be read back
    import io

    result_df = pd.read_parquet(io.BytesIO(content))
    assert all(df.columns == result_df.columns)
    assert len(df) == len(result_df)
    assert all(df['unicode_col'] == result_df['unicode_col'])


@mark.asyncio
async def test_load_error_handling(s3_target: S3Target) -> None:
    """Test error handling during load operation."""
    data = {'test': [{'id': 1}]}

    # Test with invalid format
    config_invalid_format = {'bucket': 'test-bucket', 'prefix': 'data/', 'format': 'invalid'}
    # First validate the config (should fail)
    is_valid = await s3_target.validate(data, config_invalid_format)
    assert not is_valid

    # Then try to load (should fail)
    result = await s3_target.load(data, config_invalid_format)
    assert not result['success']
    assert 'error' in result
