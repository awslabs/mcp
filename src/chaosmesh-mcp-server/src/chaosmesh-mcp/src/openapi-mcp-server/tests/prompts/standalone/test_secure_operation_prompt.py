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
#!/usr/bin/env python3

import unittest
from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import create_operation_prompt
from fastmcp import FastMCP
from unittest.mock import MagicMock


class TestSecureOperationPrompt(unittest.TestCase):
    """Test the secure implementation of operation_prompts."""

    def setUp(self):
        """Set up test environment."""
        # Create a mock server
        self.server = FastMCP(name='test-server')
        self.server._prompt_manager = MagicMock()

    def test_basic_operation(self):
        """Test creating a basic operation prompt."""
        # Create a test operation
        operation_id = 'findPetsByStatus'
        method = 'get'
        path = '/pet/findByStatus'
        summary = 'Finds Pets by status'
        description = 'Multiple status values can be provided with comma separated strings'
        parameters = [
            {
                'name': 'status',
                'in': 'query',
                'description': 'Status values that need to be considered for filter',
                'required': False,
                'schema': {
                    'type': 'string',
                    'default': 'available',
                    'enum': ['available', 'pending', 'sold'],
                },
            }
        ]
        responses = {
            '200': {
                'description': 'successful operation',
                'content': {
                    'application/json': {
                        'schema': {'type': 'array', 'items': {'$ref': '#/components/schemas/Pet'}}
                    }
                },
            },
            '400': {'description': 'Invalid status value'},
        }
        paths = {
            '/pet/findByStatus': {
                'get': {
                    'tags': ['pet'],
                    'summary': 'Finds Pets by status',
                    'description': 'Multiple status values can be provided with comma separated strings',
                    'operationId': 'findPetsByStatus',
                    'parameters': parameters,
                    'responses': responses,
                }
            }
        }

        # Create the operation prompt
        success = create_operation_prompt(
            server=self.server,
            api_name='petstore',
            operation_id=operation_id,
            method=method,
            path=path,
            summary=summary,
            description=description,
            parameters=parameters,
            responses=responses,
            paths=paths,
        )

        # Verify prompt was created successfully
        self.assertTrue(success)
        self.server._prompt_manager.add_prompt.assert_called_once()

        # Get the prompt that was added
        prompt = self.server._prompt_manager.add_prompt.call_args[0][0]

        # Verify prompt properties
        self.assertEqual(prompt.name, 'findPetsByStatus')
        self.assertEqual(prompt.description, 'Finds Pets by status')

        # Verify prompt arguments
        self.assertEqual(len(prompt.arguments), 1)
        self.assertEqual(prompt.arguments[0].name, 'status')
        self.assertEqual(prompt.arguments[0].required, False)

        # Test the function with a parameter
        messages = prompt.fn('available')
        self.assertIsInstance(messages, list)
        self.assertGreaterEqual(len(messages), 1)
        self.assertEqual(messages[0]['role'], 'user')
        self.assertEqual(messages[0]['content']['type'], 'text')
        self.assertIn('findPetsByStatus', messages[0]['content']['text'])

    def test_required_parameters(self):
        """Test operation with required parameters."""
        # Create a test operation with required parameters
        operation_id = 'getPetById'
        method = 'get'
        path = '/pet/{petId}'
        summary = 'Find pet by ID'
        description = 'Returns a single pet'
        parameters = [
            {
                'name': 'petId',
                'in': 'path',
                'description': 'ID of pet to return',
                'required': True,
                'schema': {
                    'type': 'integer',
                    'format': 'int64',
                },
            }
        ]
        responses = {
            '200': {
                'description': 'successful operation',
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Pet'}}},
            },
            '400': {'description': 'Invalid ID supplied'},
            '404': {'description': 'Pet not found'},
        }
        paths = {
            '/pet/{petId}': {
                'get': {
                    'tags': ['pet'],
                    'summary': 'Find pet by ID',
                    'description': 'Returns a single pet',
                    'operationId': 'getPetById',
                    'parameters': parameters,
                    'responses': responses,
                }
            }
        }

        # Create the operation prompt
        success = create_operation_prompt(
            server=self.server,
            api_name='petstore',
            operation_id=operation_id,
            method=method,
            path=path,
            summary=summary,
            description=description,
            parameters=parameters,
            responses=responses,
            paths=paths,
        )

        # Verify prompt was created successfully
        self.assertTrue(success)

        # Get the prompt that was added
        prompt = self.server._prompt_manager.add_prompt.call_args[0][0]

        # Verify prompt arguments
        self.assertEqual(len(prompt.arguments), 1)
        self.assertEqual(prompt.arguments[0].name, 'petId')
        self.assertEqual(prompt.arguments[0].required, True)

        # Test the function with a parameter
        messages = prompt.fn('123')
        self.assertIsInstance(messages, list)
        self.assertGreaterEqual(len(messages), 1)

        # Test missing required parameter - this will now raise a TypeError or ValidationError
        with self.assertRaises(Exception):
            prompt.fn()

    def test_resource_operation(self):
        """Test resource operation type."""
        # Mock the determine_operation_type function
        import awslabs.openapi_mcp_server.prompts.generators.operation_prompts as op_prompts

        original_determine = op_prompts.determine_operation_type
        op_prompts.determine_operation_type = MagicMock(return_value='resource')

        try:
            # Create a test resource operation
            operation_id = 'getPetById'
            method = 'get'
            path = '/pet/{petId}'
            summary = 'Find pet by ID'
            description = 'Returns a single pet'
            parameters = [
                {
                    'name': 'petId',
                    'in': 'path',
                    'description': 'ID of pet to return',
                    'required': True,
                    'schema': {
                        'type': 'integer',
                        'format': 'int64',
                    },
                }
            ]
            responses = {
                '200': {
                    'description': 'successful operation',
                    'content': {
                        'application/json': {'schema': {'$ref': '#/components/schemas/Pet'}}
                    },
                },
            }

            # Create the operation prompt
            success = create_operation_prompt(
                server=self.server,
                api_name='petstore',
                operation_id=operation_id,
                method=method,
                path=path,
                summary=summary,
                description=description,
                parameters=parameters,
                responses=responses,
            )

            # Verify prompt was created successfully
            self.assertTrue(success)

            # Get the prompt that was added
            prompt = self.server._prompt_manager.add_prompt.call_args[0][0]

            # Test the function
            messages = prompt.fn('123')
            self.assertIsInstance(messages, list)
            self.assertEqual(len(messages), 2)  # Should have text and resource messages

            # Verify resource message
            resource_message = messages[1]
            self.assertEqual(resource_message['role'], 'user')
            self.assertEqual(resource_message['content']['type'], 'resource')
            self.assertEqual(
                resource_message['content']['resource']['uri'], 'api://petstore/pet/{petId}'
            )
            self.assertEqual(
                resource_message['content']['resource']['mimeType'], 'application/json'
            )

        finally:
            # Restore original function
            op_prompts.determine_operation_type = original_determine

    def test_multiple_parameters(self):
        """Test operation with multiple parameters."""
        # Create a test operation with multiple parameters
        operation_id = 'updatePet'
        method = 'put'
        path = '/pet'
        summary = 'Update an existing pet'
        description = 'Update an existing pet by Id'
        parameters = []
        request_body = {
            'description': 'Pet object that needs to be added to the store',
            'required': True,
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'required': ['id', 'name', 'status'],
                        'properties': {
                            'id': {
                                'type': 'integer',
                                'format': 'int64',
                            },
                            'name': {
                                'type': 'string',
                                'example': 'doggie',
                            },
                            'status': {
                                'type': 'string',
                                'description': 'pet status in the store',
                                'enum': ['available', 'pending', 'sold'],
                            },
                        },
                    }
                }
            },
        }
        responses = {
            '200': {'description': 'successful operation'},
            '400': {'description': 'Invalid ID supplied'},
            '404': {'description': 'Pet not found'},
            '405': {'description': 'Validation exception'},
        }

        # Create the operation prompt
        success = create_operation_prompt(
            server=self.server,
            api_name='petstore',
            operation_id=operation_id,
            method=method,
            path=path,
            summary=summary,
            description=description,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
        )

        # Verify prompt was created successfully
        self.assertTrue(success)

        # Get the prompt that was added
        prompt = self.server._prompt_manager.add_prompt.call_args[0][0]

        # Verify prompt arguments
        self.assertEqual(len(prompt.arguments), 3)
        self.assertEqual(prompt.arguments[0].name, 'id')
        self.assertEqual(prompt.arguments[1].name, 'name')
        self.assertEqual(prompt.arguments[2].name, 'status')

        # Test the function with parameters
        messages = prompt.fn(1, 'doggie', 'available')
        self.assertIsInstance(messages, list)
        self.assertGreaterEqual(len(messages), 1)


if __name__ == '__main__':
    unittest.main()
