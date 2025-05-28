"""Tests for improving coverage of the API documentation generation modules."""

import unittest
from awslabs.openapi_mcp_server.prompts.api_documentation import (
    generate_api_documentation,
)
from unittest.mock import MagicMock, patch


class MockPromptManager:
    """Mock prompt manager for testing."""

    def __init__(self):
        """Initialize the mock prompt manager."""
        self._prompts = {}

    def add_prompt(self, prompt):
        """Add a prompt to the manager."""
        self._prompts[prompt.name] = prompt


class TestApiDocumentationCoverage(unittest.TestCase):
    """Test cases for API documentation generation coverage."""

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation.GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY',
        True,
    )
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.is_complex_operation')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.create_operation_prompt')
    async def test_generate_api_documentation_with_security(
        self, mock_create_prompt, mock_is_complex, mock_extract, mock_workflow
    ):
        """Test API documentation generation with security schemes."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_extract.return_value = {}
        mock_workflow.return_value = 'Test workflow'
        mock_is_complex.return_value = True
        mock_create_prompt.return_value = None

        # Test data
        api_name = 'test-api'
        openapi_spec = {
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/items': {
                    'get': {
                        'operationId': 'listItems',
                        'summary': 'List all items',
                        'parameters': [],
                        'responses': {'200': {'description': 'OK'}},
                        'security': [{'apiKey': []}],
                    }
                }
            },
            'components': {
                'securitySchemes': {
                    'apiKey': {
                        'type': 'apiKey',
                        'name': 'x-api-key',
                        'in': 'header',
                    }
                }
            },
            'servers': [{'url': 'https://api.example.com/v1'}],
        }

        # Call the function
        result = await generate_api_documentation(mock_server, api_name, openapi_spec)

        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn('workflow_prompts_generated', result)
        self.assertTrue(result['workflow_prompts_generated'])
        self.assertIn('operation_prompts_generated', result)
        self.assertTrue(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_extract.assert_called_once_with(openapi_spec)
        mock_workflow.assert_called_once()
        mock_create_prompt.assert_called_once_with(
            server=mock_server,
            api_name=api_name,
            operation_id='listItems',
            mapping_type='function',
            method='get',
            path='/items',
            summary='List all items',
            description='',
            parameters=[],
            request_body=None,
            responses={'200': {'description': 'OK'}},
            security=[{'apiKey': []}],
        )

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation.GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY',
        False,
    )
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.create_operation_prompt')
    async def test_generate_api_documentation_without_complex_only(
        self, mock_create_prompt, mock_extract, mock_workflow
    ):
        """Test API documentation generation without complex operations only."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_extract.return_value = {}
        mock_workflow.return_value = 'Test workflow'
        mock_create_prompt.return_value = None

        # Test data
        api_name = 'test-api'
        openapi_spec = {
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/items': {
                    'get': {
                        'operationId': 'listItems',
                        'summary': 'List all items',
                        'parameters': [],
                        'responses': {'200': {'description': 'OK'}},
                    }
                }
            },
            'components': {},
            'servers': [],
        }

        # Call the function
        result = await generate_api_documentation(mock_server, api_name, openapi_spec)

        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn('workflow_prompts_generated', result)
        self.assertTrue(result['workflow_prompts_generated'])
        self.assertIn('operation_prompts_generated', result)
        self.assertTrue(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_extract.assert_called_once_with(openapi_spec)
        mock_workflow.assert_called_once()
        mock_create_prompt.assert_called_once()

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.create_operation_prompt')
    async def test_generate_api_documentation_with_description(
        self, mock_create_prompt, mock_extract, mock_workflow
    ):
        """Test API documentation generation with operation description."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_extract.return_value = {}
        mock_workflow.return_value = 'Test workflow'
        mock_create_prompt.return_value = None

        # Test data
        api_name = 'test-api'
        openapi_spec = {
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/items': {
                    'get': {
                        'operationId': 'listItems',
                        'summary': 'List all items',
                        'description': 'Returns a list of all items in the system',
                        'parameters': [],
                        'responses': {'200': {'description': 'OK'}},
                    }
                }
            },
            'components': {},
            'servers': [],
        }

        # Call the function
        result = await generate_api_documentation(mock_server, api_name, openapi_spec)

        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn('workflow_prompts_generated', result)
        self.assertTrue(result['workflow_prompts_generated'])
        self.assertIn('operation_prompts_generated', result)
        self.assertTrue(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_extract.assert_called_once_with(openapi_spec)
        mock_workflow.assert_called_once()
        mock_create_prompt.assert_called_once_with(
            server=mock_server,
            api_name=api_name,
            operation_id='listItems',
            mapping_type='function',
            method='get',
            path='/items',
            summary='List all items',
            description='Returns a list of all items in the system',
            parameters=[],
            request_body=None,
            responses={'200': {'description': 'OK'}},
            security=[],
        )


if __name__ == '__main__':
    unittest.main()
