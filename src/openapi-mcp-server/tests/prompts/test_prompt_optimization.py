"""Tests for the optimized prompt generation modules."""

import unittest

# Import the modules for testing
from awslabs.openapi_mcp_server.prompts.api_documentation_operation import (
    generate_operation_prompt,
)
from awslabs.openapi_mcp_server.prompts.api_documentation_workflow import (
    _generate_list_get_update_workflow,
)


class MockPromptManager:
    """Mock prompt manager for testing."""

    def __init__(self):
        """Initialize the mock prompt manager."""
        self._prompts = {}

    def add_prompt(self, prompt):
        """Add a prompt to the manager."""
        self._prompts[prompt.name] = prompt


class TestPromptOptimization(unittest.TestCase):
    """Test cases for prompt optimization."""

    def test_operation_prompt_efficiency(self):
        """Test that operation prompts are efficient."""
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
        responses = {
            '200': {
                'description': 'Successful operation',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'string'},
                                'name': {'type': 'string'},
                                'description': {'type': 'string'},
                                'created': {'type': 'string', 'format': 'date-time'},
                                'status': {
                                    'type': 'string',
                                    'enum': ['active', 'inactive', 'pending'],
                                },
                            },
                        }
                    }
                },
            },
            '404': {'description': 'Item not found'},
        }
        security = [{'apiKey': []}]

        # Generate prompt
        prompt = generate_operation_prompt(
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

        # Verify the prompt contains essential information
        self.assertIn(operation_id, prompt)
        self.assertIn(method.upper(), prompt)
        self.assertIn(path, prompt)
        self.assertIn('itemId', prompt)
        self.assertIn('200', prompt)
        self.assertIn('404', prompt)
        self.assertIn('apiKey', prompt)

        # Verify the prompt includes example usage
        self.assertIn('Example usage', prompt)
        self.assertIn('```python', prompt)

        # Verify token efficiency (rough estimate)
        tokens = len(prompt) / 4
        print(f'Operation prompt tokens: {tokens}')
        self.assertLess(tokens, 400, 'Operation prompt should be under 400 tokens')

    def test_workflow_prompt_efficiency(self):
        """Test that workflow prompts are efficient."""
        # Test data
        resource_type = 'User'
        list_op = {'operationId': 'listUsers'}
        get_op = {'operationId': 'getUser'}
        update_op = {'operationId': 'updateUser'}

        # Generate workflow prompt
        workflow = _generate_list_get_update_workflow(resource_type, list_op, get_op, update_op)

        # Verify essential information is present
        self.assertIn(resource_type, workflow)
        self.assertIn('listUsers', workflow)
        self.assertIn('getUser', workflow)
        self.assertIn('updateUser', workflow)
        self.assertIn('```python', workflow)

        # Verify token efficiency (rough estimate)
        tokens = len(workflow) / 4
        print(f'Workflow prompt tokens: {tokens}')
        self.assertLess(tokens, 200, 'Workflow prompt should be under 200 tokens')

    # Example prompt test removed as it's no longer needed


if __name__ == '__main__':
    unittest.main()
