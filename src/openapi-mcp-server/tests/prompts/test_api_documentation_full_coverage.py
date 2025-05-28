"""Tests for full coverage of the API documentation generation modules."""

import unittest
from awslabs.openapi_mcp_server.prompts.api_documentation import (
    generate_api_documentation,
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


class TestApiDocumentationFullCoverage(unittest.TestCase):
    """Test cases for full coverage of API documentation generation."""

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation.GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY',
        False,
    )
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.create_operation_prompt')
    async def test_generate_api_documentation_with_all_methods(
        self, mock_create_prompt, mock_workflow, mock_extract
    ):
        """Test API documentation generation with all HTTP methods."""
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
                                        },
                                    }
                                }
                            }
                        },
                        'responses': {'201': {'description': 'Created'}},
                    },
                    'put': {
                        'operationId': 'updateItem',
                        'summary': 'Update an item',
                        'requestBody': {
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'name': {'type': 'string'},
                                        },
                                    }
                                }
                            }
                        },
                        'responses': {'200': {'description': 'OK'}},
                    },
                    'patch': {
                        'operationId': 'patchItem',
                        'summary': 'Patch an item',
                        'requestBody': {
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'name': {'type': 'string'},
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
                        'responses': {'204': {'description': 'No Content'}},
                    },
                    'options': {  # This method should be skipped
                        'operationId': 'optionsItem',
                        'summary': 'Options for items',
                        'responses': {'200': {'description': 'OK'}},
                    },
                },
                '/items/{itemId}': {
                    'get': {
                        # Missing operationId, should be skipped
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
                },
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
        self.assertEqual(mock_create_prompt.call_count, 5)  # 5 valid operations

        # Verify the create_operation_prompt calls for each method
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
                operation_id='updateItem',
                mapping_type='function',
                method='put',
                path='/items',
                summary='Update an item',
                description='',
                parameters=[],
                request_body={
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'name': {'type': 'string'},
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
                operation_id='patchItem',
                mapping_type='function',
                method='patch',
                path='/items',
                summary='Patch an item',
                description='',
                parameters=[],
                request_body={
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'name': {'type': 'string'},
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
                path='/items',
                summary='Delete an item',
                description='',
                parameters=[],
                request_body=None,
                responses={'204': {'description': 'No Content'}},
                security=[],
            ),
        ]
        mock_create_prompt.assert_has_calls(expected_calls, any_order=True)

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation.GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY',
        True,
    )
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.is_complex_operation')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.create_operation_prompt')
    async def test_generate_api_documentation_with_operation_error(
        self, mock_create_prompt, mock_is_complex, mock_workflow, mock_extract
    ):
        """Test API documentation generation with operation error."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_extract.return_value = {}
        mock_workflow.return_value = 'Test workflow'
        mock_is_complex.return_value = True
        # First call succeeds, second call raises exception
        mock_create_prompt.side_effect = [None, Exception('Operation error')]

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
        self.assertEqual(mock_create_prompt.call_count, 2)
        mock_is_complex.assert_called()


if __name__ == '__main__':
    unittest.main()
