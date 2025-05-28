"""Improved tests for the API documentation generation modules."""

import unittest
from awslabs.openapi_mcp_server.prompts.api_documentation import (
    generate_api_documentation,
    generate_api_instructions,
    generate_unified_prompts,
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


class TestApiDocumentationImproved(unittest.TestCase):
    """Improved test cases for API documentation generation."""

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation_operation.create_operation_prompt')
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation_workflow.generate_generic_workflow_prompts'
    )
    async def test_generate_api_documentation_operation_error(
        self, mock_workflow, mock_create_prompt
    ):
        """Test API documentation generation with operation error."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_workflow.return_value = 'Test workflow'
        mock_create_prompt.side_effect = Exception('Operation error')

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
        # Operation prompts should still be generated even if one fails
        self.assertTrue(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_workflow.assert_called_once()
        mock_create_prompt.assert_called_once()

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation_operation.create_operation_prompt')
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation_workflow.generate_generic_workflow_prompts'
    )
    async def test_generate_api_documentation_missing_operation_id(
        self, mock_workflow, mock_create_prompt
    ):
        """Test API documentation generation with missing operation ID."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_workflow.return_value = 'Test workflow'
        mock_create_prompt.return_value = None

        # Test data
        api_name = 'test-api'
        openapi_spec = {
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/items': {
                    'get': {
                        # No operationId
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
        # No operation prompts should be generated
        self.assertFalse(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_workflow.assert_called_once()
        mock_create_prompt.assert_not_called()

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation_operation.create_operation_prompt')
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation_workflow.generate_generic_workflow_prompts'
    )
    async def test_generate_api_documentation_unsupported_method(
        self, mock_workflow, mock_create_prompt
    ):
        """Test API documentation generation with unsupported HTTP method."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_workflow.return_value = 'Test workflow'
        mock_create_prompt.return_value = None

        # Test data
        api_name = 'test-api'
        openapi_spec = {
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/items': {
                    'options': {  # Unsupported method
                        'operationId': 'optionsItems',
                        'summary': 'Options for items',
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
        # No operation prompts should be generated
        self.assertFalse(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_workflow.assert_called_once()
        mock_create_prompt.assert_not_called()

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation.GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY',
        True,
    )
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation_operation.create_operation_prompt')
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation_workflow.generate_generic_workflow_prompts'
    )
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation_operation.is_complex_operation')
    async def test_generate_api_documentation_skip_simple_operations(
        self, mock_is_complex, mock_workflow, mock_create_prompt
    ):
        """Test API documentation generation skipping simple operations."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_workflow.return_value = 'Test workflow'
        mock_create_prompt.return_value = None
        mock_is_complex.return_value = False  # All operations are simple

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
        # No operation prompts should be generated for simple operations
        self.assertFalse(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_workflow.assert_called_once()
        mock_is_complex.assert_called_once()
        mock_create_prompt.assert_not_called()

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', False)
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation_operation.create_operation_prompt')
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation_workflow.generate_generic_workflow_prompts'
    )
    async def test_generate_api_documentation_operations_disabled(
        self, mock_workflow, mock_create_prompt
    ):
        """Test API documentation generation with operations disabled."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
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
        # No operation prompts should be generated when disabled
        self.assertFalse(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_workflow.assert_called_once()
        mock_create_prompt.assert_not_called()

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_api_documentation')
    async def test_generate_api_instructions_alias(self, mock_generate):
        """Test the generate_api_instructions alias."""
        # Setup mocks
        mock_server = MagicMock()
        mock_generate.return_value = {'result': 'success'}

        # Test data
        api_name = 'test-api'
        openapi_spec = {'info': {'title': 'Test API'}}

        # Call the function
        result = await generate_api_instructions(mock_server, api_name, openapi_spec)

        # Verify the result
        self.assertEqual(result, {'result': 'success'})
        mock_generate.assert_called_once_with(mock_server, api_name, openapi_spec)

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_api_documentation')
    async def test_generate_unified_prompts_alias(self, mock_generate):
        """Test the generate_unified_prompts alias."""
        # Setup mocks
        mock_server = MagicMock()
        mock_generate.return_value = {'result': 'success'}

        # Test data
        api_name = 'test-api'
        openapi_spec = {'info': {'title': 'Test API'}}

        # Call the function
        result = await generate_unified_prompts(mock_server, api_name, openapi_spec)

        # Verify the result
        self.assertEqual(result, {'result': 'success'})
        mock_generate.assert_called_once_with(mock_server, api_name, openapi_spec)

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation_operation.create_operation_prompt')
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation_workflow.generate_generic_workflow_prompts'
    )
    async def test_generate_api_documentation_invalid_components(
        self, mock_workflow, mock_create_prompt
    ):
        """Test API documentation generation with invalid components."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
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
            'components': 'invalid',  # Not a dict
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
        mock_workflow.assert_called_once()
        mock_create_prompt.assert_called_once()


if __name__ == '__main__':
    unittest.main()
