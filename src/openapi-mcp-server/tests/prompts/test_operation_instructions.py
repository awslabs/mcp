"""Tests for operation instructions generation."""

import pytest
from awslabs.openapi_mcp_server.prompts.operation_instructions import (
    generate_operation_prompts,
    generate_simple_prompt,
    get_required_body_fields,
    get_required_parameters,
)
from unittest.mock import MagicMock, patch


# Mock the config module
@pytest.fixture(autouse=True)
def mock_config():
    """Mock the configuration module for testing."""
    with patch(
        'awslabs.openapi_mcp_server.prompts.operation_instructions.ENABLE_OPERATION_PROMPTS', True
    ):
        yield


def test_get_required_parameters():
    """Test getting required parameters from an operation."""
    operation = {
        'parameters': [
            {'name': 'id', 'required': True},
            {'name': 'name', 'required': False},
        ]
    }

    required = get_required_parameters(operation)
    assert len(required) == 1
    assert required[0]['name'] == 'id'


def test_get_required_body_fields():
    """Test getting required fields from request body."""
    operation = {
        'requestBody': {
            'required': True,
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Pet'}}},
        }
    }

    components = {'schemas': {'Pet': {'required': ['name', 'photoUrls']}}}

    required = get_required_body_fields(operation, components)
    assert len(required) == 2
    assert 'name' in required
    assert 'photoUrls' in required


def test_generate_simple_prompt():
    """Test generating a simple prompt for an operation."""
    operation_id = 'getPetById'
    method = 'get'
    path = '/pet/{petId}'
    operation = {'summary': 'Find pet by ID', 'parameters': [{'name': 'petId', 'required': True}]}
    components = {}

    prompt = generate_simple_prompt(operation_id, method, path, operation, components)
    assert 'Find pet by ID.' in prompt
    assert 'The petId is {petId}.' in prompt


def test_generate_simple_prompt_with_body():
    """Test generating a simple prompt for an operation with request body."""
    operation_id = 'addPet'
    method = 'post'
    path = '/pet'
    operation = {
        'summary': 'Add a new pet to the store',
        'requestBody': {
            'required': True,
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Pet'}}},
        },
    }
    components = {'schemas': {'Pet': {'required': ['name', 'photoUrls']}}}

    prompt = generate_simple_prompt(operation_id, method, path, operation, components)
    assert 'Add a new pet to the store.' in prompt
    assert 'The name is {name}.' in prompt
    assert 'The photoUrls is {photoUrls}.' in prompt


def test_generate_simple_prompt_no_summary():
    """Test generating a simple prompt when summary is missing."""
    operation_id = 'getPetById'
    method = 'get'
    path = '/pet/{petId}'
    operation = {'parameters': [{'name': 'petId', 'required': True}]}
    components = {}

    prompt = generate_simple_prompt(operation_id, method, path, operation, components)
    assert 'Get pet by id.' in prompt
    assert 'The petId is {petId}.' in prompt


@pytest.mark.asyncio
async def test_generate_operation_prompts():
    """Test generating operation prompts."""
    # Create a server mock that properly simulates FastMCP behavior
    server = MagicMock()

    # Set up the add_prompt_from_fn method which is what our code will try to use first
    server.add_prompt_from_fn = MagicMock()

    openapi_spec = {
        'paths': {
            '/pet/{petId}': {
                'get': {
                    'operationId': 'getPetById',
                    'summary': 'Find pet by ID',
                    'parameters': [{'name': 'petId', 'required': True}],
                }
            },
            '/pet': {
                'post': {
                    'operationId': 'addPet',
                    'summary': 'Add a new pet to the store',
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {'schema': {'$ref': '#/components/schemas/Pet'}}
                        },
                    },
                }
            },
        },
        'components': {'schemas': {'Pet': {'required': ['name', 'photoUrls']}}},
    }

    await generate_operation_prompts(server, 'petstore', openapi_spec)

    # Check that prompts were added using add_prompt_from_fn
    assert server.add_prompt_from_fn.call_count == 2

    # Check the first call arguments
    args, kwargs = server.add_prompt_from_fn.call_args_list[0]
    assert kwargs['name'] == 'petstore_getPetById_prompt'
    assert kwargs['description'] == 'Simple prompt for getPetById operation'
    assert callable(kwargs['fn'])

    # Check the second call arguments
    args, kwargs = server.add_prompt_from_fn.call_args_list[1]
    assert kwargs['name'] == 'petstore_addPet_prompt'
    assert kwargs['description'] == 'Simple prompt for addPet operation'
    assert callable(kwargs['fn'])


@pytest.mark.asyncio
async def test_generate_operation_prompts_disabled():
    """Test that prompt generation is disabled when env var is set."""
    server = MagicMock()
    server.add_prompt = MagicMock()

    with patch(
        'awslabs.openapi_mcp_server.prompts.operation_instructions.ENABLE_OPERATION_PROMPTS', False
    ):
        await generate_operation_prompts(server, 'petstore', {})

    # Check that no prompts were added
    server.add_prompt.assert_not_called()


@pytest.mark.asyncio
async def test_generate_operation_prompts_missing_operation_id():
    """Test handling of operations without operationId."""
    server = MagicMock()
    server.add_prompt = MagicMock()

    openapi_spec = {
        'paths': {
            '/pet/{petId}': {
                'get': {
                    # No operationId
                    'summary': 'Find pet by ID',
                    'parameters': [{'name': 'petId', 'required': True}],
                }
            }
        }
    }

    await generate_operation_prompts(server, 'petstore', openapi_spec)

    # Check that no prompts were added
    server.add_prompt.assert_not_called()
