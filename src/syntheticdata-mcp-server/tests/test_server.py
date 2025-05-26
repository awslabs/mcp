"""Tests for syntheticdata MCP server functionality."""

import os
import pytest
from awslabs.syntheticdata_mcp_server.server import (
    ExecutePandasCodeInput,
    LoadToStorageInput,
    ValidateAndSaveDataInput,
    _extract_key_entities,
    _generate_data_generation_instructions,
    _generate_data_structure_instructions,
    _get_entity_example_data,
    _get_recommended_record_counts,
    _validate_table_data,
    execute_pandas_code,
    get_data_gen_instructions,
    load_to_storage,
    main,
    validate_and_save_data,
)
from pytest import mark


@mark.asyncio
async def test_get_data_gen_instructions() -> None:
    """Test generation of data generation instructions."""
    business_description = """
    An e-commerce platform that sells electronics. We need customer data with their
    purchase history, product catalog with inventory levels, and order information
    including payment status.
    """

    result = await get_data_gen_instructions(business_description)

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


@mark.asyncio
async def test_get_data_gen_instructions_empty() -> None:
    """Test generation of data generation instructions with empty input."""
    result = await get_data_gen_instructions('')

    assert result['success'] is False
    assert 'error' in result
    assert 'empty' in result['error'].lower()


@mark.asyncio
async def test_get_data_gen_instructions_invalid() -> None:
    """Test generation of data generation instructions with invalid input."""
    result = await get_data_gen_instructions('   ')

    assert result['success'] is False
    assert 'error' in result
    assert 'empty' in result['error'].lower()


@mark.asyncio
async def test_validate_and_save_data(temp_dir: str, sample_data: dict) -> None:
    """Test data validation and CSV file saving."""
    input_data = ValidateAndSaveDataInput(
        data=sample_data, workspace_dir=temp_dir, output_dir=None
    )
    result = await validate_and_save_data(input_data)

    assert result['success'] is True
    assert 'validation_results' in result
    assert 'csv_paths' in result
    assert 'row_counts' in result
    assert os.path.exists(os.path.join(temp_dir, 'customers.csv'))
    assert os.path.exists(os.path.join(temp_dir, 'orders.csv'))

    # Verify row counts
    assert result['row_counts']['customers'] == 2
    assert result['row_counts']['orders'] == 3


@mark.asyncio
async def test_validate_and_save_data_invalid(temp_dir: str) -> None:
    """Test validation with invalid data."""
    invalid_data = {
        'customers': [
            {'id': 1, 'name': 'John'},
            {'id': 1, 'email': 'john@example.com'},  # Different keys
        ]
    }

    input_data = ValidateAndSaveDataInput(
        data=invalid_data, workspace_dir=temp_dir, output_dir=None
    )
    result = await validate_and_save_data(input_data)
    assert result['success'] is False
    assert 'error' in result
    assert "All records for table 'customers' must have the same keys" in result['error']
    assert not os.path.exists(os.path.join(temp_dir, 'customers.csv'))


@mark.asyncio
async def test_validate_and_save_data_duplicate_ids(temp_dir: str) -> None:
    """Test validation with duplicate IDs."""
    data_with_duplicates = {
        'customers': [
            {'id': 1, 'name': 'John', 'email': 'john@example.com'},
            {'id': 1, 'name': 'Jane', 'email': 'jane@example.com'},  # Duplicate ID
        ]
    }

    input_data = ValidateAndSaveDataInput(
        data=data_with_duplicates, workspace_dir=temp_dir, output_dir=None
    )
    result = await validate_and_save_data(input_data)
    assert result['success'] is False
    assert 'error' in result
    assert "Duplicate IDs found in table 'customers'" in result['error']
    assert not os.path.exists(os.path.join(temp_dir, 'customers.csv'))


@mark.asyncio
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

    input_data = LoadToStorageInput(data=sample_data, targets=targets)
    result = await load_to_storage(input_data)

    assert result['success'] is True
    assert 's3' in result['results']
    assert result['results']['s3']['success'] is True

    # Verify files in S3
    s3_result = result['results']['s3']
    assert len(s3_result['uploaded_files']) == 2  # customers and orders
    assert any(f['key'] == 'data/customers/customers.csv' for f in s3_result['uploaded_files'])
    assert any(f['key'] == 'data/orders/orders.csv' for f in s3_result['uploaded_files'])


@mark.asyncio
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

    input_data = LoadToStorageInput(data={'test': []}, targets=targets)
    result = await load_to_storage(input_data)
    assert result['success'] is False
    assert 's3' in result['results']
    assert not result['results']['s3']['success']


@mark.asyncio
async def test_execute_pandas_code_success(temp_dir: str, sample_pandas_code: str) -> None:
    """Test pandas code execution through server endpoint."""
    input_data = ExecutePandasCodeInput(
        code=sample_pandas_code, workspace_dir=temp_dir, output_dir=None
    )
    result = await execute_pandas_code(input_data)

    assert result['success'] is True
    assert 'saved_files' in result
    assert len(result['saved_files']) == 3
    assert 'workspace_dir' in result
    assert result['workspace_dir'] == temp_dir


@mark.asyncio
async def test_execute_pandas_code_with_output_dir(temp_dir: str, sample_pandas_code: str) -> None:
    """Test pandas code execution with custom output directory."""
    output_dir = 'test_output'
    input_data = ExecutePandasCodeInput(
        code=sample_pandas_code, workspace_dir=temp_dir, output_dir=output_dir
    )
    result = await execute_pandas_code(input_data)

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


def test_generate_data_structure_instructions() -> None:
    """Test generation of data structure instructions."""
    description = 'An e-commerce platform with users, products, and orders.'
    entities = ['user', 'product', 'order']

    result = _generate_data_structure_instructions(description, entities)

    # Check structure
    assert 'general_instructions' in result
    assert 'entity_instructions' in result
    assert 'relationship_instructions' in result

    # Check entity instructions
    assert all(entity in result['entity_instructions'] for entity in entities)

    # Check user entity suggestions
    user_suggestions = result['entity_instructions']['user']['suggestions']
    assert 'email' in user_suggestions
    assert 'password_hash' in user_suggestions

    # Check product entity suggestions
    product_suggestions = result['entity_instructions']['product']['suggestions']
    assert 'price' in product_suggestions
    assert 'category_id' in product_suggestions

    # Check relationship instructions
    rel_instructions = result['relationship_instructions']
    assert any('foreign keys' in instr.lower() for instr in rel_instructions)
    assert any('relationships' in instr.lower() for instr in rel_instructions)


def test_generate_data_generation_instructions() -> None:
    """Test generation of data generation instructions."""
    entities = ['user', 'product', 'order']

    result = _generate_data_generation_instructions(entities)

    # Check structure
    assert 'general_instructions' in result
    assert 'data_quality_instructions' in result
    assert 'recommended_record_counts' in result

    # Check instructions content
    gen_instructions = result['general_instructions']
    assert any('realistic' in instr.lower() for instr in gen_instructions)
    assert any('consistency' in instr.lower() for instr in gen_instructions)

    # Check quality instructions
    quality_instructions = result['data_quality_instructions']
    assert any('data types' in instr.lower() for instr in quality_instructions)
    assert any('null values' in instr.lower() for instr in quality_instructions)

    # Check record counts
    record_counts = result['recommended_record_counts']
    assert all(entity in record_counts for entity in entities)
    assert record_counts['user'] > 0
    assert record_counts['product'] > 0
    assert record_counts['order'] > 0


def test_get_recommended_record_counts() -> None:
    """Test record count recommendations."""
    # Test common entities
    common_entities = ['user', 'product', 'order']
    result = _get_recommended_record_counts(common_entities)
    assert result['user'] == 50  # Default for user-type entities
    assert result['product'] == 20  # Default for product-type entities
    assert result['order'] == 100  # Default for transaction-type entities

    # Test custom entities
    custom_entities = ['custom_entity']
    result = _get_recommended_record_counts(custom_entities)
    assert result['custom_entity'] == 30  # Default for unknown entities

    # Test empty input
    result = _get_recommended_record_counts([])
    assert isinstance(result, dict)
    assert len(result) == 0


def test_get_entity_example_data() -> None:
    """Test example data generation for entities."""
    # Test predefined entities
    user_data = _get_entity_example_data('user')
    assert len(user_data) == 2
    assert all(isinstance(record, dict) for record in user_data)
    assert all('email' in record for record in user_data)
    assert all('created_at' in record for record in user_data)

    product_data = _get_entity_example_data('product')
    assert len(product_data) == 2
    assert all('price' in record for record in product_data)
    assert all('stock_quantity' in record for record in product_data)

    order_data = _get_entity_example_data('order')
    assert len(order_data) == 2
    assert all('customer_id' in record for record in order_data)
    assert all('total_amount' in record for record in order_data)

    # Test custom entity
    custom_data = _get_entity_example_data('custom_entity')
    assert len(custom_data) == 2
    assert all('id' in record for record in custom_data)
    assert all('name' in record for record in custom_data)
    assert all('description' in record for record in custom_data)


@pytest.mark.parametrize(
    'args',
    [
        ([]),  # Default values
        (['--port   ', '9999']),  # Custom port
        (['--sse', '']),  # SSE enabled
        (['--sse', '--port', '7777', '']),  # Both custom
    ],
)
def test_main_cli_arguments(mock_cli_args, monkeypatch, args) -> None:
    """Test CLI argument handling."""
    # Update mock CLI args
    mock_cli_args.extend(args)

    # Mock FastMCP.run to capture arguments
    run_args = {}

    def mock_run(self, **kwargs):
        run_args.update(kwargs)

    monkeypatch.setattr('mcp.server.fastmcp.FastMCP.run', mock_run)

    # Run main
    main()
