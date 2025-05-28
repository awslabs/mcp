"""Extended tests for the operation_prompts module - Part 2."""

from awslabs.openapi_mcp_server.prompts.operation_prompts import (
    create_operation_prompt,
    operation_prompt_fn,
)
from unittest.mock import MagicMock, patch


def test_operation_prompt_fn():
    """Test the operation_prompt_fn function."""
    # Setup test data
    api_name = 'test_api'
    operation_id = 'getItem'
    mapping_type = 'function'
    method = 'get'
    path = '/items/{itemId}'
    summary = 'Get an item by ID'
    description = 'Returns a single item by its ID'
    parameters = [
        {
            'name': 'itemId',
            'in': 'path',
            'required': True,
            'description': 'The ID of the item',
            'schema': {'type': 'string'},
        }
    ]

    # Call the function
    result = operation_prompt_fn(
        api_name=api_name,
        operation_id=operation_id,
        mapping_type=mapping_type,
        method=method,
        path=path,
        summary=summary,
        description=description,
        parameters=parameters,
    )

    # Verify the result
    assert '# getItem' in result
    assert 'Get an item by ID' in result
    assert 'Returns a single item by its ID' in result
    assert '## API Details' in result
    assert '- **HTTP Method**: GET' in result
    assert '- **Path**: `/items/{itemId}`' in result
    assert '- **Mapping Type**: function' in result
    assert '## Parameters' in result
    assert '### Path Parameters' in result
    assert 'itemId' in result
    assert 'The ID of the item' in result


@patch('fastmcp.prompts.prompt.Prompt')
def test_create_operation_prompt(mock_prompt_class):
    """Test creating an operation prompt."""
    # Setup test data
    mock_server = MagicMock()
    mock_prompt_manager = MagicMock()
    mock_server._prompt_manager = mock_prompt_manager

    mock_prompt = MagicMock()
    mock_prompt_class.from_function.return_value = mock_prompt

    api_name = 'test_api'
    operation_id = 'getItem'
    mapping_type = 'function'
    method = 'get'
    path = '/items/{itemId}'
    summary = 'Get an item by ID'
    description = 'Returns a single item by its ID'
    parameters = []

    # Call the function
    create_operation_prompt(
        server=mock_server,
        api_name=api_name,
        operation_id=operation_id,
        mapping_type=mapping_type,
        method=method,
        path=path,
        summary=summary,
        description=description,
        parameters=parameters,
    )

    # Verify the result - we now use a formatted display name
    mock_prompt_class.from_function.assert_called_once_with(
        fn=operation_prompt_fn,
        name=f'{api_name} Get Item',
        description=f'Documentation for {operation_id} operation',
    )
    mock_prompt_manager.add_prompt.assert_called_once_with(mock_prompt)


@patch('fastmcp.prompts.prompt.Prompt')
def test_create_operation_prompt_error(mock_prompt_class):
    """Test error handling when creating an operation prompt."""
    # Setup test data
    mock_server = MagicMock()
    mock_prompt_manager = MagicMock()
    mock_server._prompt_manager = mock_prompt_manager

    mock_prompt_class.from_function.side_effect = Exception('Test error')

    api_name = 'test_api'
    operation_id = 'getItem'
    mapping_type = 'function'
    method = 'get'
    path = '/items/{itemId}'
    summary = 'Get an item by ID'
    description = 'Returns a single item by its ID'
    parameters = []

    # Call the function - should not raise an exception
    create_operation_prompt(
        server=mock_server,
        api_name=api_name,
        operation_id=operation_id,
        mapping_type=mapping_type,
        method=method,
        path=path,
        summary=summary,
        description=description,
        parameters=parameters,
    )

    # Verify the result
    mock_prompt_class.from_function.assert_called_once()
    mock_prompt_manager.add_prompt.assert_not_called()
