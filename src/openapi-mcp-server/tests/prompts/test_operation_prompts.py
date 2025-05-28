"""Tests for the operation_prompts module."""

from awslabs.openapi_mcp_server.prompts.operation_prompts import (
    generate_operation_prompt,
)


def test_generate_operation_prompt_minimal():
    """Test generating an operation prompt with minimal information."""
    # Setup test data
    api_name = 'test_api'
    operation_id = 'getItem'
    mapping_type = 'function'
    method = 'get'
    path = '/items/{itemId}'
    summary = 'Get an item by ID'
    description = 'Returns a single item by its ID'
    parameters = []

    # Call the function
    result = generate_operation_prompt(
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
    assert '## Parameters' not in result  # No parameters provided


def test_generate_operation_prompt_with_parameters():
    """Test generating an operation prompt with parameters."""
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
        },
        {
            'name': 'fields',
            'in': 'query',
            'required': False,
            'description': 'Fields to include in the response',
            'schema': {'type': 'string'},
        },
    ]

    # Call the function
    result = generate_operation_prompt(
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
    assert '## Parameters' in result
    assert '### Path Parameters' in result
    assert 'itemId' in result
    assert 'The ID of the item' in result
    assert '### Query Parameters' in result
    assert 'fields' in result
    assert 'Fields to include in the response' in result


def test_generate_operation_prompt_with_request_body():
    """Test generating an operation prompt with a request body."""
    # Setup test data
    api_name = 'test_api'
    operation_id = 'createItem'
    mapping_type = 'function'
    method = 'post'
    path = '/items'
    summary = 'Create a new item'
    description = 'Creates a new item in the system'
    parameters = []
    request_body = {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['name'],
                    'properties': {
                        'name': {'type': 'string', 'description': 'The name of the item'},
                        'description': {
                            'type': 'string',
                            'description': 'The description of the item',
                        },
                    },
                }
            }
        },
    }

    # Call the function
    result = generate_operation_prompt(
        api_name=api_name,
        operation_id=operation_id,
        mapping_type=mapping_type,
        method=method,
        path=path,
        summary=summary,
        description=description,
        parameters=parameters,
        request_body=request_body,
    )

    # Verify the result
    assert '# createItem' in result
    assert '## Request Body' in result
    assert '**Required**: Yes' in result
    assert '**Content Type**: `application/json`' in result
    assert 'type' in result.lower()
    assert 'object' in result.lower()
    assert 'properties' in result.lower()
    assert 'name' in result
    assert 'description' in result


def test_generate_operation_prompt_with_responses():
    """Test generating an operation prompt with responses."""
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
    responses = {
        '200': {
            'description': 'Successful response',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string', 'description': 'The ID of the item'},
                            'name': {'type': 'string', 'description': 'The name of the item'},
                        },
                    }
                }
            },
        },
        '404': {'description': 'Item not found'},
    }

    # Call the function
    result = generate_operation_prompt(
        api_name=api_name,
        operation_id=operation_id,
        mapping_type=mapping_type,
        method=method,
        path=path,
        summary=summary,
        description=description,
        parameters=parameters,
        responses=responses,
    )

    # Verify the result
    assert '# getItem' in result
    assert '## Responses' in result
    assert '### 200 - Successful response' in result
    assert 'application/json' in result
    assert 'id' in result
    assert 'name' in result
    assert '### 404 - Item not found' in result


def test_generate_operation_prompt_with_security():
    """Test generating an operation prompt with security requirements."""
    # Setup test data
    api_name = 'test_api'
    operation_id = 'getItem'
    mapping_type = 'function'
    method = 'get'
    path = '/items/{itemId}'
    summary = 'Get an item by ID'
    description = 'Returns a single item by its ID'
    parameters = []
    security = [{'api_key': []}, {'oauth2': ['read']}]

    # Call the function
    result = generate_operation_prompt(
        api_name=api_name,
        operation_id=operation_id,
        mapping_type=mapping_type,
        method=method,
        path=path,
        summary=summary,
        description=description,
        parameters=parameters,
        security=security,
    )

    # Verify the result
    assert '# getItem' in result
    assert '## Security' in result
    assert 'api_key' in result
    assert 'oauth2' in result
    assert 'read' in result
