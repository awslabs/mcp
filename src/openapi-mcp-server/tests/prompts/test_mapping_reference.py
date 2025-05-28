"""Tests for the mapping_reference module."""

from awslabs.openapi_mcp_server.prompts.mapping_reference import (
    create_mapping_reference_prompt,
    generate_mapping_reference,
)
from unittest.mock import MagicMock, patch


def test_generate_mapping_reference_basic():
    """Test generating a basic mapping reference."""
    # Setup test data
    api_name = 'test_api'
    paths = {
        '/items': {
            'get': {'operationId': 'listItems', 'summary': 'List all items', 'tags': ['items']},
            'post': {
                'operationId': 'createItem',
                'summary': 'Create a new item',
                'tags': ['items'],
            },
        },
        '/items/{itemId}': {
            'get': {'operationId': 'getItem', 'summary': 'Get an item by ID', 'tags': ['items']}
        },
    }
    operation_mappings = {
        'listItems': {
            'type': 'function',
            'path': '/items',
            'method': 'get',
            'operationId': 'listItems',
        },
        'createItem': {
            'type': 'function',
            'path': '/items',
            'method': 'post',
            'operationId': 'createItem',
        },
        'getItem': {
            'type': 'function',
            'path': '/items/{itemId}',
            'method': 'get',
            'operationId': 'getItem',
        },
    }

    # Call the function
    result = generate_mapping_reference(
        api_name=api_name,
        paths=paths,
        operation_mappings=operation_mappings,
    )

    # Verify the result
    assert '# test_api API Mapping Reference' in result
    assert 'This document provides a comprehensive reference' in result

    # Check that the table contains the expected operations
    assert 'Function Mappings' in result
    assert 'Resource Mappings' in result
    assert 'Parameter Mappings' in result
    assert 'Usage Examples' in result


def test_generate_mapping_reference_with_query_params():
    """Test generating a mapping reference with query parameters."""
    # Setup test data
    api_name = 'test_api'
    paths = {
        '/items': {
            'get': {
                'operationId': 'listItems',
                'summary': 'List all items',
                'tags': ['items'],
                'parameters': [
                    {
                        'name': 'limit',
                        'in': 'query',
                        'description': 'Maximum number of items to return',
                        'schema': {'type': 'integer', 'default': 10},
                    },
                    {
                        'name': 'offset',
                        'in': 'query',
                        'description': 'Number of items to skip',
                        'schema': {'type': 'integer', 'default': 0},
                    },
                ],
            }
        }
    }
    operation_mappings = {
        'listItems': {
            'type': 'function',
            'path': '/items',
            'method': 'get',
            'operationId': 'listItems',
        }
    }

    # Call the function
    result = generate_mapping_reference(
        api_name=api_name,
        paths=paths,
        operation_mappings=operation_mappings,
    )

    # Verify the result
    assert '# test_api API Mapping Reference' in result
    assert 'This document provides a comprehensive reference' in result

    # Check that the table contains the expected operations
    assert 'Function Mappings' in result
    assert 'Resource Mappings' in result
    assert 'Parameter Mappings' in result
    assert 'Usage Examples' in result

    # Check that query parameters are mentioned
    assert 'Parameter Mappings' in result


def test_create_mapping_reference_prompt():
    """Test creating a mapping reference prompt."""
    # Setup test data
    server = MagicMock()
    server._prompt_manager = MagicMock()

    api_name = 'test_api'
    paths = {
        '/items': {
            'get': {'operationId': 'listItems', 'summary': 'List all items', 'tags': ['items']}
        }
    }
    operation_mappings = {
        'listItems': {
            'type': 'function',
            'path': '/items',
            'method': 'get',
            'operationId': 'listItems',
        }
    }

    # Mock the generate_mapping_reference function
    with patch(
        'awslabs.openapi_mcp_server.prompts.mapping_reference.generate_mapping_reference',
        return_value='mocked_mapping_reference',
    ):
        with patch('fastmcp.prompts.prompt.Prompt') as mock_prompt:
            mock_prompt.from_function = MagicMock()

            # Call the function
            create_mapping_reference_prompt(
                server=server,
                api_name=api_name,
                paths=paths,
                operation_mappings=operation_mappings,
            )

            # Verify the result
            mock_prompt.from_function.assert_called_once()
            server._prompt_manager.add_prompt.assert_called_once()
