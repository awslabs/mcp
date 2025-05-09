"""Tests for UnifiedDataLoader functionality."""

import pytest
from awslabs.syntheticdata_mcp_server.storage.loader import UnifiedDataLoader
from pytest import mark


@pytest.fixture
def data_loader() -> UnifiedDataLoader:
    """Create a UnifiedDataLoader instance."""
    return UnifiedDataLoader()


@mark.asyncio
async def test_load_data_s3_success(
    data_loader: UnifiedDataLoader, mock_s3, sample_data: dict
) -> None:
    """Test successful data loading to S3."""
    targets = [
        {
            'type': 's3',
            'config': {
                'bucket': 'test-bucket',
                'prefix': 'data/',
                'format': 'csv',
                'storage': {'class': 'STANDARD', 'encryption': 'AES256'},
            },
        }
    ]

    result = await data_loader.load_data(sample_data, targets)

    assert result['success'] is True
    assert 's3' in result['results']
    assert result['results']['s3']['success'] is True


@mark.asyncio
async def test_load_data_multiple_targets(
    data_loader: UnifiedDataLoader, mock_s3, sample_data: dict
) -> None:
    """Test loading data to multiple targets."""
    targets = [
        {
            'type': 's3',
            'config': {'bucket': 'test-bucket', 'prefix': 'csv-data/', 'format': 'csv'},
        }
    ]

    result = await data_loader.load_data(sample_data, targets)

    assert result['success'] is True
    assert len(result['results']) == 1
    assert result['results']['s3']['success'] is True


@mark.asyncio
async def test_load_data_unsupported_target(
    data_loader: UnifiedDataLoader, sample_data: dict
) -> None:
    """Test handling of unsupported target types."""
    targets = [{'type': 'unsupported', 'config': {}}]

    result = await data_loader.load_data(sample_data, targets)

    assert not result['success']
    assert 'unsupported' in result['results']
    assert not result['results']['unsupported']['success']
    assert 'Unsupported target type' in result['results']['unsupported']['error']


@mark.asyncio
async def test_load_data_invalid_config(
    data_loader: UnifiedDataLoader, mock_s3, sample_data: dict
) -> None:
    """Test handling of invalid target configuration."""
    targets = [
        {
            'type': 's3',
            'config': {
                'bucket': 'test-bucket'
                # Missing required fields
            },
        }
    ]

    result = await data_loader.load_data(sample_data, targets)

    assert not result['success']
    assert 's3' in result['results']
    assert not result['results']['s3']['success']


@mark.asyncio
async def test_load_data_mixed_success(
    data_loader: UnifiedDataLoader, mock_s3, sample_data: dict
) -> None:
    """Test handling of mixed success/failure across targets."""
    targets = [
        {'type': 's3', 'config': {'bucket': 'test-bucket', 'prefix': 'data/', 'format': 'csv'}},
        {'type': 'unsupported', 'config': {}},
    ]

    result = await data_loader.load_data(sample_data, targets)

    assert not result['success']  # Overall success is False if any target fails
    assert result['results']['s3']['success']
    assert not result['results']['unsupported']['success']


@mark.asyncio
async def test_load_data_empty_targets(data_loader: UnifiedDataLoader, sample_data: dict) -> None:
    """Test handling of empty targets list."""
    result = await data_loader.load_data(sample_data, [])

    assert result['success'] is True
    assert not result['results']


@mark.asyncio
async def test_load_data_empty_data(data_loader: UnifiedDataLoader, mock_s3) -> None:
    """Test handling of empty data."""
    targets = [
        {'type': 's3', 'config': {'bucket': 'test-bucket', 'prefix': 'data/', 'format': 'csv'}}
    ]

    result = await data_loader.load_data({}, targets)

    assert not result['success']
    assert 's3' in result['results']
    assert not result['results']['s3']['success']


@pytest.mark.parametrize(
    'target_config',
    [
        {'type': 's3', 'config': None},  # Invalid config
        {'config': {'bucket': 'test'}},  # Missing type
        {},  # Empty config
    ],
)
@mark.asyncio
async def test_load_data_invalid_target_config(
    data_loader: UnifiedDataLoader, sample_data: dict, target_config: dict
) -> None:
    """Test handling of invalid target configurations."""
    targets = [target_config]

    result = await data_loader.load_data(sample_data, targets)

    assert not result['success']
    if 'type' in target_config:
        target_type = target_config['type']
        assert target_type in result['results']
        assert not result['results'][target_type]['success']
