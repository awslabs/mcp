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

import json
from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import create_operation_prompt
from fastmcp import FastMCP


def test_create_operation_prompt():
    """Test creating an operation prompt."""
    # Create a mock server
    server = FastMCP(name='test-server')

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
        server=server,
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
    assert success is True

    # Check that the prompt has the expected properties
    if hasattr(server, '_prompt_manager') and hasattr(server._prompt_manager, '_prompts'):
        prompt = server._prompt_manager._prompts.get(operation_id)
        assert prompt is not None
        assert prompt.name == 'findPetsByStatus'
        assert prompt.description == 'Finds Pets by status'
        assert len(prompt.arguments) == 1
        assert prompt.arguments[0].name == 'status'
        assert prompt.arguments[0].required is False


if __name__ == '__main__':
    # For backwards compatibility when running as a script
    server = FastMCP(name='test-server')

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
        server=server,
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

    # Print the result
    print(f'Prompt creation success: {success}')

    # Print the prompt
    if (
        success
        and hasattr(server, '_prompt_manager')
        and hasattr(server._prompt_manager, '_prompts')
    ):
        prompt = server._prompt_manager._prompts.get(operation_id)
        if prompt:
            # Convert to dict and remove function reference for serialization
            prompt_dict = prompt.model_dump()
            prompt_dict.pop('fn', None)

            # Convert sets to lists for JSON serialization
            if 'tags' in prompt_dict and isinstance(prompt_dict['tags'], set):
                prompt_dict['tags'] = list(prompt_dict['tags'])

            # Print the prompt structure
            print(f'Prompt structure for {operation_id}:')
            print(json.dumps(prompt_dict, indent=2))
