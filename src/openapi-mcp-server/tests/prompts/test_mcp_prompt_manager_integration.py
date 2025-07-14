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
"""Integration test for the MCPPromptManager."""

import pytest
from awslabs.openapi_mcp_server.prompts import MCPPromptManager
from fastmcp.server.openapi import RouteType
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_server():
    """Create a mock server with the necessary attributes."""
    server = MagicMock()

    # Mock _prompt_manager
    server._prompt_manager = MagicMock()
    server._prompt_manager.add_prompt = MagicMock()

    # Mock register_resource_handler
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
            '/pet': {
                'post': {
                    'operationId': 'addPet',
                    'summary': 'Add a new pet to the store',
                    'requestBody': {
                        'description': 'Pet object that needs to be added to the store',
                        'required': True,
                        'content': {
                            'application/json': {'schema': {'$ref': '#/components/schemas/Pet'}}
                        },
                    },
                    'responses': {
                        '200': {
                            'description': 'successful operation',
                            'content': {
                                'application/json': {'schema': {'$ref': '#/components/schemas/Pet'}}
                            },
                        }
                    },
                },
                'get': {
                    'operationId': 'listPets',
                    'summary': 'List all pets',
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
                },
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
async def test_generate_prompts_integration(mock_server, petstore_openapi_spec):
    """Test the full prompt generation process."""
    # Create the prompt manager
    prompt_manager = MCPPromptManager()

    # Generate prompts
    result = await prompt_manager.generate_prompts(mock_server, 'petstore', petstore_openapi_spec)

    # Check that prompts were registered
    assert mock_server._prompt_manager.add_prompt.call_count >= 3  # At least 3 operations

    # Check the result
    assert result['operation_prompts_generated'] is True

    # Check that workflow prompts were generated
    # We should have at least one workflow (list-get-update)
    assert result['workflow_prompts_generated'] is True


@pytest.mark.asyncio
async def test_register_api_resource_handler_integration(mock_server, mock_client):
    """Test the resource handler registration process."""
    # Create the prompt manager
    prompt_manager = MCPPromptManager()

    # Register the resource handler
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
async def test_full_integration(mock_server, mock_client, petstore_openapi_spec):
    """Test the full integration of the prompt manager."""
    # Create the prompt manager
    prompt_manager = MCPPromptManager()

    # Generate prompts
    result = await prompt_manager.generate_prompts(mock_server, 'petstore', petstore_openapi_spec)

    # Register the resource handler
    prompt_manager.register_api_resource_handler(mock_server, 'petstore', mock_client)

    # Check that prompts were registered
    assert mock_server._prompt_manager.add_prompt.call_count >= 3

    # Check that the resource handler was registered
    mock_server.register_resource_handler.assert_called_once()

    # Check the result
    assert result['operation_prompts_generated'] is True
    assert result['workflow_prompts_generated'] is True
