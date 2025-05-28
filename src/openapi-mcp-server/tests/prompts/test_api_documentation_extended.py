"""Extended tests for the API documentation generation modules."""

import unittest
from awslabs.openapi_mcp_server.prompts.api_documentation import (
    generate_api_documentation,
    generate_api_instructions,
    generate_unified_prompts,
)
from unittest.mock import MagicMock, call, patch


class MockPromptManager:
    """Mock prompt manager for testing."""

    def __init__(self):
        """Initialize the mock prompt manager."""
        self._prompts = {}

    def add_prompt(self, prompt):
        """Add a prompt to the manager."""
        self._prompts[prompt.name] = prompt


class TestApiDocumentationExtended(unittest.TestCase):
    """Extended test cases for API documentation generation."""

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.create_operation_prompt')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.is_complex_operation')
    async def test_generate_api_documentation_with_multiple_operations(
        self, mock_is_complex, mock_create_prompt, mock_extract, mock_workflow
    ):
        """Test API documentation generation with multiple operations."""
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
                    },
                    'post': {
                        'operationId': 'createItem',
                        'summary': 'Create a new item',
                        'requestBody': {
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'name': {'type': 'string'},
                                            'description': {'type': 'string'},
                                        },
                                    }
                                }
                            }
                        },
                        'responses': {'201': {'description': 'Created'}},
                    },
                },
                '/items/{itemId}': {
                    'get': {
                        'operationId': 'getItem',
                        'summary': 'Get an item by ID',
                        'parameters': [
                            {
                                'name': 'itemId',
                                'in': 'path',
                                'required': True,
                                'schema': {'type': 'string'},
                            }
                        ],
                        'responses': {'200': {'description': 'OK'}},
                    },
                    'put': {
                        'operationId': 'updateItem',
                        'summary': 'Update an item',
                        'parameters': [
                            {
                                'name': 'itemId',
                                'in': 'path',
                                'required': True,
                                'schema': {'type': 'string'},
                            }
                        ],
                        'requestBody': {
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'name': {'type': 'string'},
                                            'description': {'type': 'string'},
                                        },
                                    }
                                }
                            }
                        },
                        'responses': {'200': {'description': 'OK'}},
                    },
                    'delete': {
                        'operationId': 'deleteItem',
                        'summary': 'Delete an item',
                        'parameters': [
                            {
                                'name': 'itemId',
                                'in': 'path',
                                'required': True,
                                'schema': {'type': 'string'},
                            }
                        ],
                        'responses': {'204': {'description': 'No Content'}},
                    },
                },
            },
            'components': {
                'schemas': {
                    'Item': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'name': {'type': 'string'},
                            'description': {'type': 'string'},
                        },
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
        self.assertEqual(mock_create_prompt.call_count, 5)  # 5 operations

        # Verify the create_operation_prompt calls
        expected_calls = [
            call(
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
                security=[],
            ),
            call(
                server=mock_server,
                api_name=api_name,
                operation_id='createItem',
                mapping_type='function',
                method='post',
                path='/items',
                summary='Create a new item',
                description='',
                parameters=[],
                request_body={
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'name': {'type': 'string'},
                                    'description': {'type': 'string'},
                                },
                            }
                        }
                    }
                },
                responses={'201': {'description': 'Created'}},
                security=[],
            ),
            call(
                server=mock_server,
                api_name=api_name,
                operation_id='getItem',
                mapping_type='function',
                method='get',
                path='/items/{itemId}',
                summary='Get an item by ID',
                description='',
                parameters=[
                    {
                        'name': 'itemId',
                        'in': 'path',
                        'required': True,
                        'schema': {'type': 'string'},
                    }
                ],
                request_body=None,
                responses={'200': {'description': 'OK'}},
                security=[],
            ),
            call(
                server=mock_server,
                api_name=api_name,
                operation_id='updateItem',
                mapping_type='function',
                method='put',
                path='/items/{itemId}',
                summary='Update an item',
                description='',
                parameters=[
                    {
                        'name': 'itemId',
                        'in': 'path',
                        'required': True,
                        'schema': {'type': 'string'},
                    }
                ],
                request_body={
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'name': {'type': 'string'},
                                    'description': {'type': 'string'},
                                },
                            }
                        }
                    }
                },
                responses={'200': {'description': 'OK'}},
                security=[],
            ),
            call(
                server=mock_server,
                api_name=api_name,
                operation_id='deleteItem',
                mapping_type='function',
                method='delete',
                path='/items/{itemId}',
                summary='Delete an item',
                description='',
                parameters=[
                    {
                        'name': 'itemId',
                        'in': 'path',
                        'required': True,
                        'schema': {'type': 'string'},
                    }
                ],
                request_body=None,
                responses={'204': {'description': 'No Content'}},
                security=[],
            ),
        ]
        mock_create_prompt.assert_has_calls(expected_calls, any_order=True)

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_api_documentation')
    async def test_generate_api_instructions_alias(self, mock_generate_api_documentation):
        """Test that generate_api_instructions is an alias for generate_api_documentation."""
        # Setup mocks
        mock_server = MagicMock()
        api_name = 'test-api'
        openapi_spec = {'info': {'title': 'Test API'}}
        mock_generate_api_documentation.return_value = {'result': 'success'}

        # Call the function
        result = await generate_api_instructions(mock_server, api_name, openapi_spec)

        # Verify the result
        self.assertEqual(result, {'result': 'success'})
        mock_generate_api_documentation.assert_called_once_with(mock_server, api_name, openapi_spec)

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_api_documentation')
    async def test_generate_unified_prompts_alias(self, mock_generate_api_documentation):
        """Test that generate_unified_prompts is an alias for generate_api_documentation."""
        # Setup mocks
        mock_server = MagicMock()
        api_name = 'test-api'
        openapi_spec = {'info': {'title': 'Test API'}}
        mock_generate_api_documentation.return_value = {'result': 'success'}

        # Call the function
        result = await generate_unified_prompts(mock_server, api_name, openapi_spec)

        # Verify the result
        self.assertEqual(result, {'result': 'success'})
        mock_generate_api_documentation.assert_called_once_with(mock_server, api_name, openapi_spec)

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', False)
    async def test_generate_api_documentation_operations_disabled(
        self, mock_extract, mock_workflow
    ):
        """Test API documentation generation with operations disabled."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_extract.return_value = {}
        mock_workflow.return_value = 'Test workflow'

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
        with patch(
            'awslabs.openapi_mcp_server.prompts.api_documentation.create_operation_prompt'
        ) as mock_create_prompt:
            result = await generate_api_documentation(mock_server, api_name, openapi_spec)

        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn('workflow_prompts_generated', result)
        self.assertTrue(result['workflow_prompts_generated'])
        self.assertIn('operation_prompts_generated', result)
        self.assertFalse(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_extract.assert_called_once_with(openapi_spec)
        mock_workflow.assert_called_once()
        mock_create_prompt.assert_not_called()

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation.GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY',
        True,
    )
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.is_complex_operation')
    async def test_generate_api_documentation_complex_operations_only(
        self, mock_is_complex, mock_extract, mock_workflow
    ):
        """Test API documentation generation with complex operations only."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_extract.return_value = {}
        mock_workflow.return_value = 'Test workflow'
        # First operation is simple, second is complex
        mock_is_complex.side_effect = [False, True]

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
                },
                '/items/{itemId}': {
                    'get': {
                        'operationId': 'getItem',
                        'summary': 'Get an item by ID',
                        'parameters': [
                            {
                                'name': 'itemId',
                                'in': 'path',
                                'required': True,
                                'schema': {'type': 'string'},
                            }
                        ],
                        'responses': {'200': {'description': 'OK'}},
                    }
                },
            },
            'components': {},
            'servers': [],
        }

        # Call the function
        with patch(
            'awslabs.openapi_mcp_server.prompts.api_documentation.create_operation_prompt'
        ) as mock_create_prompt:
            mock_create_prompt.return_value = None
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
        self.assertEqual(mock_is_complex.call_count, 2)
        # Only the complex operation should have a prompt created
        self.assertEqual(mock_create_prompt.call_count, 1)
        mock_create_prompt.assert_called_once_with(
            server=mock_server,
            api_name=api_name,
            operation_id='getItem',
            mapping_type='function',
            method='get',
            path='/items/{itemId}',
            summary='Get an item by ID',
            description='',
            parameters=[
                {
                    'name': 'itemId',
                    'in': 'path',
                    'required': True,
                    'schema': {'type': 'string'},
                }
            ],
            request_body=None,
            responses={'200': {'description': 'OK'}},
            security=[],
        )


if __name__ == '__main__':
    unittest.main()
