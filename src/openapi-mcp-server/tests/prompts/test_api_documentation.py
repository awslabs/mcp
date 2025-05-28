"""Tests for the API documentation generation modules."""

import unittest
from awslabs.openapi_mcp_server.prompts.api_documentation import (
    generate_api_documentation,
)
from awslabs.openapi_mcp_server.prompts.api_documentation_operation import (
    _format_schema,
    _is_complex_schema,
    create_operation_prompt,
    generate_simple_description,
    generate_simple_prompt,
    get_required_body_fields,
    get_required_parameters,
    is_complex_operation,
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


class TestApiDocumentation(unittest.TestCase):
    """Test cases for API documentation generation."""

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    async def test_generate_api_documentation_basic(self, mock_extract, mock_workflow):
        """Test basic API documentation generation."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_extract.return_value = {}
        mock_workflow.return_value = 'Test workflow'

        # Test data
        api_name = 'test-api'
        openapi_spec = {
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {},
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
        self.assertFalse(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_extract.assert_called_once_with(openapi_spec)
        mock_workflow.assert_called_once()

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.create_operation_prompt')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    async def test_generate_api_documentation_with_operations(
        self, mock_create_prompt, mock_extract, mock_workflow
    ):
        """Test API documentation generation with operations."""
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

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.ENABLE_OPERATION_PROMPTS', True)
    @patch(
        'awslabs.openapi_mcp_server.prompts.api_documentation.GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY',
        True,
    )
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.is_complex_operation')
    async def test_generate_api_documentation_complex_only(
        self, mock_is_complex, mock_extract, mock_workflow
    ):
        """Test API documentation generation with complex operations only."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_extract.return_value = {}
        mock_workflow.return_value = 'Test workflow'
        mock_is_complex.side_effect = [False, True]  # First operation simple, second complex

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

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts')
    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    async def test_generate_api_documentation_workflow_error(self, mock_extract, mock_workflow):
        """Test API documentation generation with workflow error."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_extract.return_value = {}
        mock_workflow.side_effect = Exception('Workflow error')

        # Test data
        api_name = 'test-api'
        openapi_spec = {
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {},
            'components': {},
            'servers': [],
        }

        # Call the function
        result = await generate_api_documentation(mock_server, api_name, openapi_spec)

        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn('workflow_prompts_generated', result)
        self.assertFalse(result['workflow_prompts_generated'])
        self.assertIn('operation_prompts_generated', result)
        self.assertFalse(result['operation_prompts_generated'])

        # Verify the mocks were called
        mock_extract.assert_called_once_with(openapi_spec)
        mock_workflow.assert_called_once()

    @patch('awslabs.openapi_mcp_server.prompts.api_documentation.extract_api_structure')
    async def test_generate_api_documentation_extract_error(self, mock_extract):
        """Test API documentation generation with extraction error."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_extract.side_effect = Exception('Extract error')

        # Test data
        api_name = 'test-api'
        openapi_spec = {
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {},
            'components': {},
            'servers': [],
        }

        # Call the function
        with patch(
            'awslabs.openapi_mcp_server.prompts.api_documentation.generate_generic_workflow_prompts'
        ) as mock_workflow:
            mock_workflow.return_value = 'Test workflow'
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


class TestApiDocumentationOperation(unittest.TestCase):
    """Test cases for API documentation operation functions."""

    def test_format_schema_object(self):
        """Test formatting an object schema."""
        schema = {
            'type': 'object',
            'properties': {
                'id': {'type': 'string'},
                'name': {'type': 'string', 'description': 'The name'},
                'status': {'type': 'string', 'enum': ['active', 'inactive']},
            },
            'required': ['id', 'name'],
        }

        result = _format_schema(schema)

        # Verify the result
        self.assertIn('**Type**: Object', result)
        self.assertIn('**Properties**:', result)
        self.assertIn('**id** (required)', result)
        self.assertIn('**name** (required): string: The name', result)
        self.assertIn('**status**', result)
        self.assertIn('**Values**: `active`, `inactive`', result)

    def test_format_schema_array(self):
        """Test formatting an array schema."""
        schema = {
            'type': 'array',
            'items': {'type': 'string'},
        }

        result = _format_schema(schema)

        # Verify the result
        self.assertIn('**Type**: Array of string', result)

    def test_format_schema_primitive(self):
        """Test formatting a primitive schema."""
        schema = {
            'type': 'string',
            'format': 'date-time',
            'enum': ['value1', 'value2'],
        }

        result = _format_schema(schema)

        # Verify the result
        self.assertIn('**Type**: string', result)
        self.assertIn('**Format**: date-time', result)
        self.assertIn('**Values**: `value1`, `value2`', result)

    def test_generate_simple_description(self):
        """Test generating a simple description."""
        # Test GET operation
        result = generate_simple_description('getItem', 'get', '/items/{itemId}')
        self.assertEqual(result, 'Retrieve items information.')

        # Test POST operation
        result = generate_simple_description('createItem', 'post', '/items')
        self.assertEqual(result, 'Create a new items.')

        # Test PUT operation
        result = generate_simple_description('updateItem', 'put', '/items/{itemId}')
        self.assertEqual(result, 'Update an existing items.')

        # Test DELETE operation
        result = generate_simple_description('deleteItem', 'delete', '/items/{itemId}')
        self.assertEqual(result, 'Delete an existing items.')

        # Test special case
        result = generate_simple_description('findPetsByStatus', 'get', '/pets/findByStatus')
        self.assertEqual(result, 'Retrieve pets filtered by their status.')

    def test_is_complex_operation(self):
        """Test determining if an operation is complex."""
        # Test simple operation
        parameters = [{'name': 'id', 'in': 'path', 'required': True}]
        request_body = None
        responses = {'200': {'description': 'OK'}}
        self.assertFalse(is_complex_operation(parameters, request_body, responses))

        # Test complex parameters
        parameters = [
            {'name': 'id', 'in': 'path', 'required': True},
            {'name': 'name', 'in': 'query'},
            {'name': 'status', 'in': 'query'},
        ]
        self.assertTrue(is_complex_operation(parameters, request_body, responses))

        # Test complex request body
        parameters = [{'name': 'id', 'in': 'path', 'required': True}]
        request_body = {
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'description': {'type': 'string'},
                            'status': {'type': 'string'},
                            'tags': {'type': 'array', 'items': {'type': 'string'}},
                        },
                    }
                }
            }
        }
        self.assertTrue(is_complex_operation(parameters, request_body, responses))

        # Test complex response
        parameters = [{'name': 'id', 'in': 'path', 'required': True}]
        request_body = None
        responses = {
            '200': {
                'description': 'OK',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'string'},
                                'name': {'type': 'string'},
                                'description': {'type': 'string'},
                                'status': {'type': 'string'},
                                'created': {'type': 'string', 'format': 'date-time'},
                            },
                        }
                    }
                },
            }
        }
        self.assertTrue(is_complex_operation(parameters, request_body, responses))

    def test_is_complex_schema(self):
        """Test determining if a schema is complex."""
        # Test simple schema
        schema = {'type': 'string'}
        self.assertFalse(_is_complex_schema(schema))

        # Test simple object
        schema = {
            'type': 'object',
            'properties': {
                'id': {'type': 'string'},
                'name': {'type': 'string'},
            },
        }
        self.assertFalse(_is_complex_schema(schema))

        # Test complex object (many properties)
        schema = {
            'type': 'object',
            'properties': {
                'id': {'type': 'string'},
                'name': {'type': 'string'},
                'description': {'type': 'string'},
                'status': {'type': 'string'},
            },
        }
        self.assertTrue(_is_complex_schema(schema))

        # Test complex object (nested object)
        schema = {
            'type': 'object',
            'properties': {
                'id': {'type': 'string'},
                'metadata': {'type': 'object', 'properties': {'key': {'type': 'string'}}},
            },
        }
        self.assertTrue(_is_complex_schema(schema))

        # Test complex object (array)
        schema = {
            'type': 'object',
            'properties': {
                'id': {'type': 'string'},
                'tags': {'type': 'array', 'items': {'type': 'string'}},
            },
        }
        self.assertTrue(_is_complex_schema(schema))

        # Test array of objects
        schema = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'name': {'type': 'string'},
                },
            },
        }
        self.assertTrue(_is_complex_schema(schema))

    def test_get_required_parameters(self):
        """Test getting required parameters."""
        # Test with required parameters
        operation = {
            'parameters': [
                {'name': 'id', 'in': 'path', 'required': True},
                {'name': 'name', 'in': 'query', 'required': False},
            ]
        }
        result = get_required_parameters(operation)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'id')

        # Test with no parameters
        operation = {}
        result = get_required_parameters(operation)
        self.assertEqual(len(result), 0)

    def test_get_required_body_fields(self):
        """Test getting required body fields."""
        # Test with required fields
        operation = {
            'requestBody': {
                'required': True,
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Item'}}},
            }
        }
        components = {
            'schemas': {
                'Item': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string'},
                        'name': {'type': 'string'},
                    },
                    'required': ['name'],
                }
            }
        }
        result = get_required_body_fields(operation, components)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], 'name')

        # Test with no request body
        operation = {}
        result = get_required_body_fields(operation, components)
        self.assertEqual(len(result), 0)

    def test_generate_simple_prompt(self):
        """Test generating a simple prompt."""
        # Test data
        operation_id = 'getItem'
        method = 'get'
        path = '/items/{itemId}'
        operation = {
            'summary': 'Get an item by ID',
            'parameters': [
                {
                    'name': 'itemId',
                    'in': 'path',
                    'required': True,
                    'schema': {'type': 'string'},
                }
            ],
        }
        components = {}

        # Generate prompt
        result = generate_simple_prompt(operation_id, method, path, operation, components)

        # Verify the result
        self.assertIn('Get an item by ID.', result)
        self.assertIn('The itemId is {itemId}.', result)

    @patch('fastmcp.prompts.prompt.Prompt')
    def test_create_operation_prompt(self, mock_prompt):
        """Test creating an operation prompt."""
        # Setup mocks
        mock_server = MagicMock()
        mock_server._prompt_manager = MockPromptManager()
        mock_prompt.return_value = MagicMock()

        # Test data
        api_name = 'test-api'
        operation_id = 'getItem'
        mapping_type = 'function'
        method = 'get'
        path = '/items/{itemId}'
        summary = 'Get an item by ID'
        description = 'Returns a single item by its unique identifier'
        parameters = [
            {
                'name': 'itemId',
                'in': 'path',
                'required': True,
                'schema': {'type': 'string'},
                'description': 'Unique identifier of the item',
            }
        ]
        request_body = None
        responses = {'200': {'description': 'OK'}}
        security = [{'apiKey': []}]

        # Call the function
        create_operation_prompt(
            server=mock_server,
            api_name=api_name,
            operation_id=operation_id,
            mapping_type=mapping_type,
            method=method,
            path=path,
            summary=summary,
            description=description,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security=security,
        )

        # Verify the prompt was created and added
        mock_prompt.assert_called_once()
        self.assertEqual(len(mock_server._prompt_manager._prompts), 1)


if __name__ == '__main__':
    unittest.main()
