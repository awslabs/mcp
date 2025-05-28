"""Tests for the prompt_orchestrator module."""

import pytest
from awslabs.openapi_mcp_server.prompts.prompt_orchestrator import (
    generate_api_instructions,
    generate_unified_prompts,
)
from unittest.mock import AsyncMock, MagicMock, patch


class MockPromptManager:
    """Mock prompt manager for testing."""

    def __init__(self):
        """Initialize the mock prompt manager."""
        self._prompts = {}

    def add_prompt(self, prompt):
        """Add a prompt to the manager."""
        self._prompts[prompt.name] = prompt


@pytest.mark.asyncio
async def test_generate_api_instructions():
    """Test generating API instructions."""
    # Setup test data
    server = MagicMock()
    server.get_tools = AsyncMock(return_value={})
    server.get_resources = AsyncMock(return_value={})
    server._prompt_manager = MockPromptManager()

    api_name = 'test-api'
    openapi_spec = {
        'info': {'title': 'Test API Title', 'description': 'This is a test API description'},
        'paths': {},
    }

    # Mock the required functions
    with patch(
        'awslabs.openapi_mcp_server.prompts.prompt_orchestrator._generate_api_documentation'
    ) as mock_documentation:
        # Set up the mock to return a value
        mock_documentation.return_value = {
            'operation_prompts_generated': True,
            'workflow_prompts_generated': True,
        }

        # Call the function
        result = await generate_api_instructions(server, api_name, openapi_spec)

        # Verify the result
        mock_documentation.assert_called_once_with(server, api_name, openapi_spec)
        assert result == {
            'operation_prompts_generated': True,
            'workflow_prompts_generated': True,
        }


@pytest.mark.asyncio
async def test_generate_unified_prompts_minimal():
    """Test generating unified prompts with minimal data."""
    # Setup test data
    server = MagicMock()
    server.get_tools = AsyncMock(return_value={})
    server.get_resources = AsyncMock(return_value={})
    server._prompt_manager = MockPromptManager()

    api_name = 'test-api'
    openapi_spec = {
        'info': {'title': 'Test API Title', 'description': 'This is a test API description'},
        'paths': {},
    }

    # Mock the required functions
    with patch(
        'awslabs.openapi_mcp_server.prompts.prompt_orchestrator._generate_api_documentation',
        return_value={
            'api_overview_generated': True,
            'operation_prompts_generated': False,
            'workflow_prompts_generated': True,
            'mapping_reference_generated': False,
        },
    ) as mock_documentation:
        # Call the function
        result = await generate_unified_prompts(server, api_name, openapi_spec)

        # Verify the result
        mock_documentation.assert_called_once_with(server, api_name, openapi_spec)
        assert result == {
            'api_overview_generated': True,
            'operation_prompts_generated': False,
            'workflow_prompts_generated': True,
            'mapping_reference_generated': False,
        }


@pytest.mark.asyncio
async def test_generate_unified_prompts_with_paths():
    """Test generating unified prompts with API paths."""
    # Setup test data
    server = MagicMock()
    server.get_tools = AsyncMock(return_value={})
    server.get_resources = AsyncMock(return_value={})
    server._prompt_manager = MockPromptManager()

    api_name = 'test-api'
    openapi_spec = {
        'info': {'title': 'Test API Title', 'description': 'This is a test API description'},
        'paths': {
            '/items': {
                'get': {'operationId': 'listItems', 'summary': 'List all items', 'tags': ['items']}
            },
            '/items/{itemId}': {
                'get': {
                    'operationId': 'getItem',
                    'summary': 'Get an item by ID',
                    'tags': ['items'],
                }
            },
        },
    }

    # Mock the required functions
    with patch(
        'awslabs.openapi_mcp_server.prompts.prompt_orchestrator._generate_api_documentation',
        return_value={
            'api_overview_generated': True,
            'operation_prompts_generated': True,
            'workflow_prompts_generated': True,
            'mapping_reference_generated': True,
        },
    ) as mock_documentation:
        # Call the function
        result = await generate_unified_prompts(server, api_name, openapi_spec)

        # Verify the result
        mock_documentation.assert_called_once_with(server, api_name, openapi_spec)
        assert result == {
            'api_overview_generated': True,
            'operation_prompts_generated': True,
            'workflow_prompts_generated': True,
            'mapping_reference_generated': True,
        }
