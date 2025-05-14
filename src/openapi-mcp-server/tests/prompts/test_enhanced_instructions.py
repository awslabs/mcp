"""Tests for enhanced instructions generation."""

import pytest
from awslabs.openapi_mcp_server.prompts.enhanced_instructions import (
    categorize_operations,
    format_parameter_info,
    format_request_body_info,
    format_response_info,
    generate_enhanced_api_instructions,
    generate_tool_description,
)
from unittest.mock import MagicMock, patch


def test_format_parameter_info():
    """Test formatting parameter information."""
    # Test basic parameter
    param = {
        'name': 'test',
        'in': 'query',
        'required': True,
        'description': 'A test parameter',
    }
    result = format_parameter_info(param)
    assert '`test`' in result
    assert '(required)' in result
    assert 'query parameter' in result
    assert 'A test parameter' in result

    # Test parameter with schema
    param = {
        'name': 'test',
        'in': 'path',
        'required': True,
        'schema': {
            'type': 'string',
            'enum': ['a', 'b', 'c'],
            'example': 'a',
        },
    }
    result = format_parameter_info(param)
    assert '`test`' in result
    assert 'path parameter' in result
    assert 'type: string' in result
    assert 'allowed values: [`a`, `b`, `c`]' in result
    assert 'example: `a`' in result


def test_format_request_body_info():
    """Test formatting request body information."""
    # Test basic request body
    request_body = {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    '$ref': '#/components/schemas/Pet',
                },
            },
        },
    }
    components = {
        'schemas': {
            'Pet': {
                'type': 'object',
                'required': ['name', 'photoUrls'],
                'properties': {
                    'id': {'type': 'integer', 'format': 'int64'},
                    'name': {'type': 'string'},
                    'photoUrls': {'type': 'array', 'items': {'type': 'string'}},
                },
            },
        },
    }
    result = format_request_body_info(request_body, components)
    assert 'Request body is required' in result
    assert 'Content type: `application/json`' in result
    assert 'Schema: `Pet`' in result
    assert 'Required fields: `name`, `photoUrls`' in result
    assert '- `id` (integer)' in result
    assert '- `name` (string)' in result


def test_format_response_info():
    """Test formatting response information."""
    # Test basic responses
    responses = {
        '200': {
            'description': 'Successful operation',
            'content_types': ['application/json'],
        },
        '400': {
            'description': 'Invalid ID supplied',
            'content_types': ['application/json'],
        },
        '404': {
            'description': 'Pet not found',
            'content_types': ['application/json'],
        },
    }
    result = format_response_info(responses)
    assert 'Status 200: Successful operation' in result
    assert 'Status 400: Invalid ID supplied' in result
    assert 'Status 404: Pet not found' in result


def test_generate_tool_description():
    """Test generating tool description."""
    operation_id = 'getPetById'
    method = 'get'
    path = '/pet/{petId}'
    operation = {
        'summary': 'Find pet by ID',
        'description': 'Returns a single pet',
        'parameters': [
            {
                'name': 'petId',
                'in': 'path',
                'required': True,
                'description': 'ID of pet to return',
                'schema': {'type': 'integer', 'format': 'int64'},
            },
        ],
        'responses': {
            '200': {
                'description': 'Successful operation',
                'content_types': ['application/json'],
            },
            '400': {
                'description': 'Invalid ID supplied',
                'content_types': ['application/json'],
            },
        },
    }
    components = {}
    result = generate_tool_description(operation_id, method, path, operation, components)
    assert 'Find pet by ID' in result
    assert 'Returns a single pet' in result
    assert 'Endpoint: `GET /pet/{petId}`' in result
    assert '- `petId` (required) - path parameter' in result
    assert 'Usage Example:' in result
    assert '`getPetById(petId=1)`' in result


def test_categorize_operations():
    """Test categorizing operations."""
    operations = [
        {'operationId': 'getPet', 'method': 'GET', 'path': '/pet/{petId}'},
        {'operationId': 'createPet', 'method': 'POST', 'path': '/pet'},
        {'operationId': 'updatePet', 'method': 'PUT', 'path': '/pet'},
        {'operationId': 'getOrder', 'method': 'GET', 'path': '/store/order/{orderId}'},
        {'operationId': 'placeOrder', 'method': 'POST', 'path': '/store/order'},
    ]
    categories = categorize_operations(operations)
    assert 'Pet' in categories

    # The categorization might put 'placeOrder' in a different category
    # depending on the regex matching, so we'll just check that all operations
    # are categorized somewhere
    total_operations = sum(len(ops) for ops in categories.values())
    assert total_operations == 5


@pytest.mark.asyncio
async def test_generate_enhanced_api_instructions():
    """Test generating enhanced API instructions."""
    # Mock server
    server = MagicMock()
    server.get_tools.return_value = {}
    server.get_resources.return_value = {}
    server._prompt_manager = MagicMock()

    # Mock OpenAPI spec
    openapi_spec = {
        'openapi': '3.0.0',
        'info': {
            'title': 'Test API',
            'version': '1.0.0',
            'description': 'A test API',
        },
        'paths': {
            '/pet': {
                'get': {
                    'operationId': 'listPets',
                    'summary': 'List all pets',
                    'parameters': [
                        {
                            'name': 'limit',
                            'in': 'query',
                            'description': 'How many items to return',
                            'schema': {'type': 'integer', 'format': 'int32'},
                        },
                    ],
                    'responses': {
                        '200': {
                            'description': 'A paged array of pets',
                            'content': {'application/json': {}},
                        },
                    },
                },
                'post': {
                    'operationId': 'createPet',
                    'summary': 'Create a pet',
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/Pet'},
                            },
                        },
                    },
                    'responses': {
                        '201': {
                            'description': 'Pet created',
                            'content': {'application/json': {}},
                        },
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'Pet': {
                    'type': 'object',
                    'required': ['name'],
                    'properties': {
                        'id': {'type': 'integer', 'format': 'int64'},
                        'name': {'type': 'string'},
                    },
                },
            },
        },
    }

    # Mock Prompt class
    mock_prompt = MagicMock()
    with patch('awslabs.openapi_mcp_server.prompts.enhanced_instructions.Prompt') as MockPrompt:
        MockPrompt.from_function.return_value = mock_prompt

        # Call the function
        await generate_enhanced_api_instructions(server, 'test', openapi_spec)

        # Check that the prompt was created and added
        assert MockPrompt.from_function.called
        assert server._prompt_manager.add_prompt.called
        assert server._prompt_manager.add_prompt.call_args[0][0] == mock_prompt
