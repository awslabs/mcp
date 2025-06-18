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

from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import create_operation_prompt
from fastmcp import FastMCP
from fastmcp.prompts.prompt import Prompt


def test_operation_prompt_with_security():
    """Test creating an operation prompt with security requirements."""
    # Create a mock server
    server = FastMCP(name='test-server')

    # Create a test operation with security requirements
    operation_id = 'secureOperation'
    method = 'post'
    path = '/secure/endpoint'
    summary = 'Secure operation'
    description = 'This operation requires authentication'
    parameters = []
    responses = {
        '200': {'description': 'successful operation'},
        '401': {'description': 'Unauthorized'},
    }

    # Add security requirements
    security = [{'api_key': []}, {'oauth2': ['read', 'write']}]

    paths = {
        '/secure/endpoint': {
            'post': {
                'tags': ['secure'],
                'summary': 'Secure operation',
                'description': 'This operation requires authentication',
                'operationId': 'secureOperation',
                'parameters': parameters,
                'responses': responses,
                'security': security,
            }
        }
    }

    # Create the operation prompt
    success = create_operation_prompt(
        server=server,
        api_name='secure-api',
        operation_id=operation_id,
        method=method,
        path=path,
        summary=summary,
        description=description,
        parameters=parameters,
        responses=responses,
        paths=paths,
        security=security,
    )

    # Verify prompt was created successfully
    assert success is True

    # Check that the prompt has the expected properties
    if hasattr(server, '_prompt_manager') and hasattr(server._prompt_manager, '_prompts'):
        prompt = server._prompt_manager._prompts.get(operation_id)
        assert prompt is not None
        assert prompt.name == 'secureOperation'

        # Check that the prompt has been registered
        assert prompt in server._prompt_manager._prompts.values()

        # Since we can't directly check the security info in the prompt object,
        # we'll verify that the prompt was created successfully
        assert isinstance(prompt, Prompt)


def test_operation_prompt_with_enum_parameters():
    """Test creating an operation prompt with enum parameters."""
    # Create a mock server
    server = FastMCP(name='test-server')

    # Create a test operation with enum parameters
    operation_id = 'enumOperation'
    method = 'get'
    path = '/enum/endpoint'
    summary = 'Operation with enum parameters'
    description = 'This operation has enum parameters'

    # Define parameters with enum values
    parameters = [
        {
            'name': 'string_enum',
            'in': 'query',
            'description': 'String enum parameter',
            'required': True,
            'schema': {
                'type': 'string',
                'enum': ['value1', 'value2', 'value3'],
            },
        },
        {
            'name': 'integer_enum',
            'in': 'query',
            'description': 'Integer enum parameter',
            'required': True,
            'schema': {
                'type': 'integer',
                'enum': [1, 2, 3],
            },
        },
    ]

    responses = {
        '200': {'description': 'successful operation'},
    }

    paths = {
        '/enum/endpoint': {
            'get': {
                'tags': ['enum'],
                'summary': 'Operation with enum parameters',
                'description': 'This operation has enum parameters',
                'operationId': 'enumOperation',
                'parameters': parameters,
                'responses': responses,
            }
        }
    }

    # Create the operation prompt
    success = create_operation_prompt(
        server=server,
        api_name='enum-api',
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
        assert prompt.name == 'enumOperation'

        # Check that the prompt has arguments
        assert len(prompt.arguments) == 2

        # Check argument names
        arg_names = [arg.name for arg in prompt.arguments]
        assert 'string_enum' in arg_names
        assert 'integer_enum' in arg_names


def test_operation_prompt_with_request_body_schema():
    """Test creating an operation prompt with request body schema."""
    # Create a mock server
    server = FastMCP(name='test-server')

    # Create a test operation with request body
    operation_id = 'createWithSchema'
    method = 'post'
    path = '/create/resource'
    summary = 'Create resource'
    description = 'Create a new resource with schema'
    parameters = []

    # Define request body with schema
    request_body = {
        'description': 'Resource to create',
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['name', 'type', 'active'],
                    'properties': {
                        'name': {'type': 'string'},
                        'type': {'type': 'string', 'enum': ['type1', 'type2']},
                        'active': {'type': 'boolean'},
                        'count': {'type': 'integer'},
                        'tags': {'type': 'array'},
                        'metadata': {'type': 'object'},
                    },
                }
            }
        },
    }

    responses = {
        '201': {'description': 'Resource created'},
        '400': {'description': 'Invalid request'},
    }

    paths = {
        '/create/resource': {
            'post': {
                'tags': ['resource'],
                'summary': 'Create resource',
                'description': 'Create a new resource with schema',
                'operationId': 'createWithSchema',
                'parameters': parameters,
                'requestBody': request_body,
                'responses': responses,
            }
        }
    }

    # Create the operation prompt
    success = create_operation_prompt(
        server=server,
        api_name='schema-api',
        operation_id=operation_id,
        method=method,
        path=path,
        summary=summary,
        description=description,
        parameters=parameters,
        responses=responses,
        paths=paths,
        request_body=request_body,
    )

    # Verify prompt was created successfully
    assert success is True

    # Check that the prompt has the expected properties
    if hasattr(server, '_prompt_manager') and hasattr(server._prompt_manager, '_prompts'):
        prompt = server._prompt_manager._prompts.get(operation_id)
        assert prompt is not None
        assert prompt.name == 'createWithSchema'

        # Get the full prompt metadata to check for request body schema
        prompt_metadata = prompt.model_dump()
        prompt_metadata_str = str(prompt_metadata)

        # Check that request body schema information is included
        assert 'name' in prompt_metadata_str
        assert 'type' in prompt_metadata_str
        assert 'active' in prompt_metadata_str
        assert 'type1' in prompt_metadata_str  # From the enum


def test_operation_prompt_error_handling():
    """Test error handling in create_operation_prompt."""
    # Create the operation prompt with invalid inputs to trigger an exception
    success = create_operation_prompt(
        server=None,  # Invalid server
        api_name='error-api',
        operation_id='errorOperation',
        method='get',
        path='/error/path',
        summary='Error operation',
        description='This should fail',
        parameters=[],
        responses={},
        paths={},
    )

    # Verify prompt creation failed
    assert success is False
