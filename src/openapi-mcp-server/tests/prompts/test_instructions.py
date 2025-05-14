"""Tests for the prompts instructions module."""

import pytest
from awslabs.openapi_mcp_server.prompts.instructions import generate_api_instructions
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_generate_api_instructions():
    """Test generating API instructions."""
    # Create mock server
    server = MagicMock()
    server._prompt_manager = MagicMock()

    # Mock get_tools and get_resources
    server.get_tools = AsyncMock(return_value={})
    server.get_resources = AsyncMock(return_value={})

    api_name = 'test-api'
    openapi_spec = {
        'info': {
            'title': 'Test API Title',
            'description': 'This is a test API description',
            'version': '1.0.0',
        },
        'paths': {},
    }

    # Call the function
    await generate_api_instructions(server, api_name, openapi_spec)

    # Verify that the prompt manager was called
    server._prompt_manager.add_prompt.assert_called_once()

    # Verify the arguments
    call_args = server._prompt_manager.add_prompt.call_args[0]
    assert call_args[0].name == f'{api_name}_instructions'


@pytest.mark.asyncio
async def test_generate_api_instructions_with_paths():
    """Test generating API instructions with paths."""
    # Create mock server
    server = MagicMock()
    server._prompt_manager = MagicMock()

    # Mock get_tools and get_resources
    server.get_tools = AsyncMock(return_value={})
    server.get_resources = AsyncMock(return_value={})

    api_name = 'test-api'
    openapi_spec = {
        'info': {
            'title': 'Test API Title',
            'description': 'This is a test API description',
            'version': '1.0.0',
        },
        'paths': {
            '/users': {
                'get': {
                    'operationId': 'getUsers',
                    'summary': 'Get all users',
                    'description': 'Get a list of all users',
                    'parameters': [
                        {
                            'name': 'limit',
                            'in': 'query',
                            'description': 'Maximum number of users to return',
                            'required': False,
                            'schema': {'type': 'integer', 'default': 10},
                        }
                    ],
                    'responses': {
                        '200': {
                            'description': 'Successful response',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'array',
                                        'items': {
                                            'type': 'object',
                                            'properties': {
                                                'id': {'type': 'integer'},
                                                'name': {'type': 'string'},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }

    # Call the function
    await generate_api_instructions(server, api_name, openapi_spec)

    # Verify that the prompt manager was called
    server._prompt_manager.add_prompt.assert_called_once()


@pytest.mark.asyncio
async def test_generate_api_instructions_with_tools():
    """Test generating API instructions with tools."""
    # Create mock server
    server = MagicMock()
    server._prompt_manager = MagicMock()

    # Mock get_tools
    tools = {
        'test-api_getUsers': MagicMock(
            name='test-api_getUsers',
            description='Get all users',
            parameters=[
                MagicMock(
                    name='limit', description='Maximum number of users to return', required=False
                )
            ],
        )
    }
    server.get_tools = AsyncMock(return_value=tools)
    server.get_resources = AsyncMock(return_value={})

    api_name = 'test-api'
    openapi_spec = {
        'info': {
            'title': 'Test API Title',
            'description': 'This is a test API description',
            'version': '1.0.0',
        },
        'paths': {},
    }

    # Call the function
    await generate_api_instructions(server, api_name, openapi_spec)

    # Verify that the prompt manager was called
    server._prompt_manager.add_prompt.assert_called_once()


@pytest.mark.asyncio
async def test_generate_api_instructions_with_resources():
    """Test generating API instructions with resources."""
    # Create mock server
    server = MagicMock()
    server._prompt_manager = MagicMock()

    # Mock get_resources
    resources = {
        'User': MagicMock(
            name='User',
            description='A user in the system',
            uri='test-api+User',
            properties={
                'id': MagicMock(description='The user ID'),
                'name': MagicMock(description='The user name'),
            },
        )
    }
    server.get_tools = AsyncMock(return_value={})
    server.get_resources = AsyncMock(return_value=resources)

    api_name = 'test-api'
    openapi_spec = {
        'info': {
            'title': 'Test API Title',
            'description': 'This is a test API description',
            'version': '1.0.0',
        },
        'paths': {},
    }

    # Call the function
    await generate_api_instructions(server, api_name, openapi_spec)

    # Verify that the prompt manager was called
    server._prompt_manager.add_prompt.assert_called_once()


@pytest.mark.asyncio
async def test_generate_api_instructions_with_components():
    """Test generating API instructions with components."""
    # Create mock server
    server = MagicMock()
    server._prompt_manager = MagicMock()

    # Mock get_tools and get_resources
    server.get_tools = AsyncMock(return_value={})
    server.get_resources = AsyncMock(return_value={})

    api_name = 'test-api'
    openapi_spec = {
        'info': {
            'title': 'Test API Title',
            'description': 'This is a test API description',
            'version': '1.0.0',
        },
        'paths': {},
        'components': {
            'schemas': {
                'User': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'name': {'type': 'string'},
                        'status': {'type': 'string', 'enum': ['active', 'inactive']},
                    },
                    'required': ['name'],
                }
            }
        },
    }

    # Call the function
    await generate_api_instructions(server, api_name, openapi_spec)

    # Verify that the prompt manager was called
    server._prompt_manager.add_prompt.assert_called_once()
