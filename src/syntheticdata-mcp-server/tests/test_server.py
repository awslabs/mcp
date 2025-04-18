"""Tests for syntheticdata MCP server functionality."""

import os
from awslabs.syntheticdata_mcp_server.server import (
    _extract_key_entities,
    _validate_table_data,
    execute_pandas_code,
    get_data_generation_instructions,
    load_to_storage,
    validate_and_save_data,
)


async def test_get_data_generation_instructions() -> None:
    """Test generation of data generation instructions."""
    business_description = """
    An e-commerce platform that sells electronics. We need customer data with their
    purchase history, product catalog with inventory levels, and order information
    including payment status.
    """

    result = await get_data_generation_instructions(business_description)

    assert result['success'] is True
    assert 'instructions' in result
    instructions = result['instructions']

    # Check instruction structure
    assert 'overview' in instructions
    assert 'data_structure_instructions' in instructions
    assert 'data_generation_instructions' in instructions
    assert 'format_instructions' in instructions

    # Check extracted entities
    entities = _extract_key_entities(business_description)
    assert 'customer' in entities
    assert 'product' in entities
    assert 'order' in entities

    # Check entity attribute suggestions
    entity_instructions = instructions['data_structure_instructions']['entity_instructions']
    assert 'customer' in entity_instructions
    assert 'email' in entity_instructions['customer']['suggestions']
    assert 'product' in entity_instructions
    assert 'price' in entity_instructions['product']['suggestions']


async def test_validate_and_save_data(temp_dir: str, sample_data: dict) -> None:
    """Test data validation and CSV file saving."""
    result = await validate_and_save_data(sample_data, temp_dir)

    assert result['success'] is True
    assert 'validation_results' in result
    assert 'csv_paths' in result
    assert 'row_counts' in result

    # Check validation results
    assert result['validation_results']['customers']['is_valid']
    assert result['validation_results']['orders']['is_valid']

    # Check saved files
    assert os.path.exists(os.path.join(temp_dir, 'customers.csv'))
    assert os.path.exists(os.path.join(temp_dir, 'orders.csv'))

    # Check row counts
    assert result['row_counts']['customers'] == 2
    assert result['row_counts']['orders'] == 3


async def test_validate_and_save_data_invalid(temp_dir: str) -> None:
    """Test validation with invalid data."""
    invalid_data = {
        'customers': [
            {'id': 1, 'name': 'John'},
            {'id': 1, 'email': 'john@example.com'},  # Different keys
        ]
    }

    result = await validate_and_save_data(invalid_data, temp_dir)
    assert result['success'] is True  # Overall operation succeeds
    assert not result['validation_results']['customers']['is_valid']
    assert 'must have the same keys' in result['validation_results']['customers']['errors'][0]


async def test_validate_and_save_data_duplicate_ids(temp_dir: str) -> None:
    """Test validation with duplicate IDs."""
    data_with_duplicates = {
        'customers': [
            {'id': 1, 'name': 'John', 'email': 'john@example.com'},
            {'id': 1, 'name': 'Jane', 'email': 'jane@example.com'},  # Duplicate ID
        ]
    }

    result = await validate_and_save_data(data_with_duplicates, temp_dir)
    assert result['success'] is True  # Overall operation succeeds
    assert not result['validation_results']['customers']['is_valid']
    assert 'Duplicate IDs' in result['validation_results']['customers']['errors'][0]


async def test_load_to_storage_s3(mock_s3, sample_data: dict) -> None:
    """Test loading data to S3."""
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

    result = await load_to_storage(sample_data, targets)

    assert result['success'] is True
    assert 's3' in result['results']
    assert result['results']['s3']['success'] is True

    # Verify files in S3
    s3_result = result['results']['s3']
    assert len(s3_result['uploaded_files']) == 2  # customers and orders
    assert any(f['key'] == 'data/customers/customers.csv' for f in s3_result['uploaded_files'])
    assert any(f['key'] == 'data/orders/orders.csv' for f in s3_result['uploaded_files'])


async def test_load_to_storage_invalid_config() -> None:
    """Test loading data with invalid storage configuration."""
    targets = [
        {
            'type': 's3',
            'config': {
                'bucket': 'test-bucket'
                # Missing required fields: prefix, format
            },
        }
    ]

    result = await load_to_storage({'test': []}, targets)
    assert result['success'] is False
    assert 's3' in result['results']
    assert not result['results']['s3']['success']


async def test_execute_pandas_code_success(temp_dir: str, sample_pandas_code: str) -> None:
    """Test pandas code execution through server endpoint."""
    result = await execute_pandas_code(sample_pandas_code, temp_dir)

    assert result['success'] is True
    assert 'saved_files' in result
    assert len(result['saved_files']) == 3
    assert 'workspace_dir' in result
    assert result['workspace_dir'] == temp_dir


async def test_execute_pandas_code_with_output_dir(temp_dir: str, sample_pandas_code: str) -> None:
    """Test pandas code execution with custom output directory."""
    output_dir = 'test_output'
    result = await execute_pandas_code(sample_pandas_code, temp_dir, output_dir)

    assert result['success'] is True
    assert 'output_subdir' in result
    assert result['output_subdir'] == output_dir
    assert os.path.exists(os.path.join(temp_dir, output_dir))


def test_validate_table_data() -> None:
    """Test table data validation function."""
    # Valid data
    valid_data = [{'id': 1, 'name': 'John'}, {'id': 2, 'name': 'Jane'}]
    result = _validate_table_data('test_table', valid_data)
    assert result['is_valid']
    assert not result['errors']

    # Invalid: mixed keys
    invalid_data = [{'id': 1, 'name': 'John'}, {'id': 2, 'email': 'jane@example.com'}]
    result = _validate_table_data('test_table', invalid_data)
    assert not result['is_valid']
    assert len(result['errors']) == 1

    # Invalid: duplicate IDs
    duplicate_ids = [{'id': 1, 'name': 'John'}, {'id': 1, 'name': 'Jane'}]
    result = _validate_table_data('test_table', duplicate_ids)
    assert not result['is_valid']
    assert 'Duplicate IDs' in result['errors'][0]

    # Invalid: empty data
    result = _validate_table_data('test_table', [])
    assert not result['is_valid']
    assert 'cannot be empty' in result['errors'][0]
