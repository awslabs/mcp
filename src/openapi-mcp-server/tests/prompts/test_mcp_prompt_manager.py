# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the MCPPromptManager class."""

import pytest
from awslabs.openapi_mcp_server.prompts import MCPPromptManager
from awslabs.openapi_mcp_server.prompts.generators.workflow_prompts import (
    identify_workflows,
)
from fastmcp.server.openapi import RouteType
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_server():
    """Create a mock server."""
    server = MagicMock()
    server.register_prompt = MagicMock()
    server.register_resource_handler = MagicMock()

    # Mock _openapi_router for operation type determination
    mock_route = MagicMock()
    mock_route.path = '/pet/{petId}'
    mock_route.method = 'GET'
    mock_route.route_type = RouteType.RESOURCE

    mock_route2 = MagicMock()
    mock_route2.path = '/pet/findByStatus'
    mock_route2.method = 'GET'
    mock_route2.route_type = RouteType.TOOL

    server._openapi_router = MagicMock()
    server._openapi_router._routes = [mock_route, mock_route2]

    return server


@pytest.fixture
def mock_client():
    """Create a mock HTTP client."""
    client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.text = '{"id": 1, "name": "doggie"}'
    mock_response.headers = {'Content-Type': 'application/json'}
    mock_response.raise_for_status = AsyncMock()
    client.get.return_value = mock_response
    return client


@pytest.fixture
def petstore_openapi_spec():
    """Create a simple PetStore OpenAPI spec for testing."""
    return {
        'openapi': '3.0.0',
        'info': {'title': 'Swagger Petstore', 'version': '1.0.0'},
        'paths': {
            '/pet/{petId}': {
                'get': {
                    'operationId': 'getPetById',
                    'summary': 'Find pet by ID',
                    'parameters': [
                        {
                            'name': 'petId',
                            'in': 'path',
                            'description': 'ID of pet to return',
                            'required': True,
                            'schema': {'type': 'integer', 'format': 'int64'},
                        }
                    ],
                    'responses': {
                        '200': {
                            'description': 'successful operation',
                            'content': {
                                'application/json': {'schema': {'$ref': '#/components/schemas/Pet'}}
                            },
                        }
                    },
                }
            },
            '/pet/findByStatus': {
                'get': {
                    'operationId': 'findPetsByStatus',
                    'summary': 'Finds Pets by status',
                    'parameters': [
                        {
                            'name': 'status',
                            'in': 'query',
                            'description': 'Status values that need to be considered for filter',
                            'required': True,
                            'schema': {
                                'type': 'array',
                                'items': {
                                    'type': 'string',
                                    'enum': ['available', 'pending', 'sold'],
                                },
                            },
                        }
                    ],
                    'responses': {
                        '200': {
                            'description': 'successful operation',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'array',
                                        'items': {'$ref': '#/components/schemas/Pet'},
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
        'components': {
            'schemas': {
                'Pet': {
                    'type': 'object',
                    'required': ['id', 'name'],
                    'properties': {
                        'id': {'type': 'integer', 'format': 'int64'},
                        'name': {'type': 'string'},
                        'status': {'type': 'string', 'enum': ['available', 'pending', 'sold']},
                    },
                }
            }
        },
    }


@pytest.mark.asyncio
async def test_generate_prompts(mock_server, petstore_openapi_spec):
    """Test generating prompts from an OpenAPI spec."""
    # Create the prompt manager
    prompt_manager = MCPPromptManager()

    # Mock the create_operation_prompt function
    with patch(
        'awslabs.openapi_mcp_server.prompts.prompt_manager.create_operation_prompt'
    ) as mock_create_op:
        # Mock the identify_workflows function to return a simple workflow
        with patch(
            'awslabs.openapi_mcp_server.prompts.prompt_manager.identify_workflows'
        ) as mock_identify:
            mock_workflow = {
                'name': 'pet_workflow',
                'type': 'list_get_update',
                'resource_type': 'pet',
                'operations': {},
            }
            mock_identify.return_value = [mock_workflow]

            # Mock the create_workflow_prompt function
            with patch(
                'awslabs.openapi_mcp_server.prompts.prompt_manager.create_workflow_prompt'
            ) as mock_create_wf:
                # Call the function under test
                result = await prompt_manager.generate_prompts(
                    mock_server, 'petstore', petstore_openapi_spec
                )

                # Check that the functions were called with the correct arguments
                assert mock_create_op.call_count == 2  # Two operations in the spec
                assert mock_identify.call_count == 1
                assert mock_create_wf.call_count == 1
                mock_create_wf.assert_called_with(mock_server, mock_workflow)

                # Check the result
                assert result['operation_prompts_generated'] is True
                assert result['workflow_prompts_generated'] is True


@pytest.mark.asyncio
async def test_register_api_resource_handler(mock_server, mock_client):
    """Test registering an API resource handler."""
    # Create the prompt manager
    prompt_manager = MCPPromptManager()

    # Call the function under test
    prompt_manager.register_api_resource_handler(mock_server, 'petstore', mock_client)

    # Check that the resource handler was registered
    mock_server.register_resource_handler.assert_called_once()

    # Get the handler function
    handler_uri = mock_server.register_resource_handler.call_args[0][0]
    handler_func = mock_server.register_resource_handler.call_args[0][1]

    # Check the handler URI
    assert handler_uri == 'api://petstore/'

    # Test the handler function
    result = await handler_func('api://petstore/pet/123', {'petId': '123'})

    # Check that the client was called with the correct arguments
    mock_client.get.assert_called_once_with('/pet/123')

    # Check the result
    assert result['text'] == '{"id": 1, "name": "doggie"}'
    assert result['mimeType'] == 'application/json'


@pytest.mark.asyncio
async def test_api_resource_handler_error(mock_server, mock_client):
    """Test error handling in the API resource handler."""
    # Create the prompt manager
    prompt_manager = MCPPromptManager()

    # Configure the mock client to raise an exception
    mock_client.get.side_effect = Exception('Connection error')

    # Call the function under test
    prompt_manager.register_api_resource_handler(mock_server, 'petstore', mock_client)

    # Get the handler function
    handler_func = mock_server.register_resource_handler.call_args[0][1]

    # Test the handler function
    result = await handler_func('api://petstore/pet/123', {'petId': '123'})

    # Check the result
    assert 'Error:' in result['text']
    assert result['mimeType'] == 'text/plain'


def test_format_enum_values():
    """Test the format_enum_values function."""
    from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import format_enum_values

    # Test with string values
    enum_values = ['available', 'pending', 'sold']
    result = format_enum_values(enum_values)
    assert result == '("available", "pending", "sold")'

    # Test with numeric values
    enum_values = [1, 2, 3]
    result = format_enum_values(enum_values)
    assert result == '(1, 2, 3)'

    # Test with mixed values
    enum_values = ['available', 1, True]
    result = format_enum_values(enum_values)
    assert result == '("available", 1, True)'

    # Test with empty list
    enum_values = []
    result = format_enum_values(enum_values)
    assert result == ''

    # Test with long list
    enum_values = ['a', 'b', 'c', 'd', 'e']
    result = format_enum_values(enum_values)
    assert result == '(5 possible values)'


def test_extract_prompt_arguments():
    """Test the extract_prompt_arguments function."""
    from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import (
        extract_prompt_arguments,
    )

    # Test with path parameter
    parameters = [
        {
            'name': 'petId',
            'in': 'path',
            'description': 'ID of pet to return',
            'required': True,
            'schema': {'type': 'integer', 'format': 'int64'},
        }
    ]

    result = extract_prompt_arguments(parameters)
    assert len(result) == 1
    assert result[0].name == 'petId'
    assert result[0].description == 'ID of pet to return'
    assert result[0].required is True

    # Test with query parameter with enum
    parameters = [
        {
            'name': 'status',
            'in': 'query',
            'description': 'Status values',
            'required': True,
            'schema': {'type': 'string', 'enum': ['available', 'pending', 'sold']},
        }
    ]

    result = extract_prompt_arguments(parameters)
    assert len(result) == 1
    assert result[0].name == 'status'
    assert result[0].description is not None
    assert 'Status values' in result[0].description
    assert 'Allowed values' in result[0].description
    assert result[0].required is True

    # Test with request body
    request_body = {
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['name'],
                    'properties': {
                        'name': {'type': 'string', 'description': 'Pet name'},
                        'status': {'type': 'string', 'enum': ['available', 'pending', 'sold']},
                    },
                }
            }
        }
    }

    result = extract_prompt_arguments([], request_body)
    assert len(result) == 2

    # Find the name parameter
    name_param = next((p for p in result if p.name == 'name'), None)
    assert name_param is not None
    assert name_param.description == 'Pet name'
    assert name_param.required is True

    # Find the status parameter
    status_param = next((p for p in result if p.name == 'status'), None)
    assert status_param is not None
    assert status_param.description is not None
    assert 'Allowed values' in status_param.description
    assert status_param.required is False


def test_determine_operation_type(mock_server):
    """Test the determine_operation_type function."""
    from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import (
        determine_operation_type,
    )

    # Test with resource operation
    result = determine_operation_type(mock_server, '/pet/{petId}', 'GET')
    assert result == 'resource'

    # Test with tool operation
    result = determine_operation_type(mock_server, '/pet/findByStatus', 'GET')
    assert result == 'tool'

    # Test with unknown operation
    result = determine_operation_type(mock_server, '/unknown', 'GET')
    assert result == 'tool'  # Default to tool


def test_determine_mime_type():
    """Test the determine_mime_type function."""
    from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import determine_mime_type

    # Test with JSON response
    responses = {
        '200': {
            'description': 'successful operation',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Pet'}}},
        }
    }

    result = determine_mime_type(responses)
    assert result == 'application/json'

    # Test with XML response
    responses = {
        '200': {
            'description': 'successful operation',
            'content': {'application/xml': {'schema': {'$ref': '#/components/schemas/Pet'}}},
        }
    }

    result = determine_mime_type(responses)
    assert result == 'application/xml'

    # Test with no content
    responses = {'204': {'description': 'successful operation'}}

    result = determine_mime_type(responses)
    assert result == 'application/json'  # Default

    # Test with None
    result = determine_mime_type(None)
    assert result == 'application/json'  # Default


def test_generate_operation_documentation():
    """Test the generate_operation_documentation function."""
    from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import (
        generate_operation_documentation,
    )

    # Test with a simple operation
    result = generate_operation_documentation(
        operation_id='getPetById',
        method='get',
        path='/pet/{petId}',
        summary='Find pet by ID',
        description='Returns a single pet',
        parameters=[
            {
                'name': 'petId',
                'in': 'path',
                'description': 'ID of pet to return',
                'required': True,
                'schema': {'type': 'integer', 'format': 'int64'},
            }
        ],
        responses={
            '200': {
                'description': 'successful operation',
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Pet'}}},
            }
        },
    )

    # Check that the result contains the expected sections
    assert '# getPetById' in result
    assert 'Find pet by ID' in result
    assert '**GET** `/pet/{petId}`' in result
    assert '**Path parameters:**' in result
    assert '- petId*' in result
    assert '**Responses:**' in result
    assert '- 200: successful operation' in result
    assert '**Example usage:**' in result
    assert 'response = await getPetById(petId="value")' in result


def test_identify_workflows():
    """Test the identify_workflows function."""
    # Create a simple paths object
    paths = {
        '/pet': {
            'get': {'operationId': 'listPets', 'summary': 'List all pets'},
            'post': {'operationId': 'createPet', 'summary': 'Create a pet'},
        },
        '/pet/{petId}': {
            'get': {'operationId': 'getPetById', 'summary': 'Find pet by ID'},
            'put': {'operationId': 'updatePet', 'summary': 'Update a pet'},
        },
        '/pet/findByStatus': {
            'get': {'operationId': 'findPetsByStatus', 'summary': 'Finds Pets by status'}
        },
    }

    # Call the function under test
    result = identify_workflows(paths)

    # Check that the list-get-update workflow was identified
    list_get_update = next(
        (w for w in result if w['type'] == 'list_get_update' and w['resource_type'] == 'pet'), None
    )
    assert list_get_update is not None
    assert list_get_update['name'] == 'pet_list_get_update'
    assert 'list' in list_get_update['operations']
    assert 'get' in list_get_update['operations']
    assert 'update' in list_get_update['operations']

    # Check that the search-create workflow was identified
    search_create = next(
        (w for w in result if w['type'] == 'search_create' and w['resource_type'] == 'pet'), None
    )
    assert search_create is not None
    assert search_create['name'] == 'pet_search_create'
    assert 'search' in search_create['operations']
    assert 'create' in search_create['operations']


def test_generate_workflow_documentation():
    """Test the generate_workflow_documentation function."""
    from awslabs.openapi_mcp_server.prompts.generators.workflow_prompts import (
        generate_workflow_documentation,
    )

    # Create a simple workflow
    workflow = {
        'name': 'pet_list_get_update',
        'type': 'list_get_update',
        'resource_type': 'pet',
        'operations': {
            'list': {'operationId': 'listPets'},
            'get': {'operationId': 'getPetById'},
            'update': {'operationId': 'updatePet'},
        },
    }

    # Call the function under test
    result = generate_workflow_documentation(workflow)

    # Check that the result contains the expected sections
    assert '# Pet List Get Update Workflow' in result
    assert '## Steps' in result
    assert '1. List pets using `listPets`' in result
    assert '2. Get a specific pet using `getPetById`' in result
    assert '3. Update the pet using `updatePet`' in result
    assert '## Example Code' in result
    assert 'pet_list = await listPets()' in result
    assert "pet_id = pet_list[0]['id']" in result
    assert 'pet_details = await getPetById(pet_id)' in result
    assert 'updated = await updatePet(pet_id, update_data)' in result
