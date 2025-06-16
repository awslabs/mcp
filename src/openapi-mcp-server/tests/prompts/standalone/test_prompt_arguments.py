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

import pytest
from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import extract_prompt_arguments


def test_parameter_with_description_and_enum():
    """Test extracting arguments from a parameter with description, default, and enum."""
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

    arguments = extract_prompt_arguments(parameters)
    
    assert len(arguments) == 1
    assert arguments[0].name == 'status'
    assert 'Status values that need to be considered for filter' in arguments[0].description
    assert 'Default: "available"' in arguments[0].description
    assert 'Allowed values: ("available", "pending", "sold")' in arguments[0].description
    assert arguments[0].required is False


def test_parameter_without_description():
    """Test extracting arguments from a parameter without description."""
    parameters = [
        {
            'name': 'petId',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer', 'format': 'int64'},
        }
    ]

    arguments = extract_prompt_arguments(parameters)
    
    assert len(arguments) == 1
    assert arguments[0].name == 'petId'
    assert arguments[0].required is True


def test_request_body_with_required_properties():
    """Test extracting arguments from a request body with required properties."""
    request_body = {
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string', 'description': 'The name of the pet'},
                        'photoUrls': {'type': 'array', 'items': {'type': 'string'}},
                        'status': {
                            'type': 'string',
                            'description': 'Pet status in the store',
                            'default': 'available',
                            'enum': ['available', 'pending', 'sold'],
                        },
                        'tags': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer', 'format': 'int64'},
                                    'name': {'type': 'string'},
                                },
                            },
                        },
                    },
                    'required': ['name', 'photoUrls'],
                }
            }
        }
    }

    arguments = extract_prompt_arguments([], request_body)
    
    assert len(arguments) == 4
    
    # Find the name parameter
    name_param = next((p for p in arguments if p.name == 'name'), None)
    assert name_param is not None
    assert name_param.description == 'The name of the pet'
    assert name_param.required is True
    
    # Find the photoUrls parameter
    photo_param = next((p for p in arguments if p.name == 'photoUrls'), None)
    assert photo_param is not None
    assert photo_param.required is True
    
    # Find the status parameter
    status_param = next((p for p in arguments if p.name == 'status'), None)
    assert status_param is not None
    assert 'Pet status in the store' in status_param.description
    assert 'Default: "available"' in status_param.description
    assert 'Allowed values: ("available", "pending", "sold")' in status_param.description
    assert status_param.required is False
    
    # Find the tags parameter
    tags_param = next((p for p in arguments if p.name == 'tags'), None)
    assert tags_param is not None
    assert tags_param.required is False


if __name__ == '__main__':
    # For backwards compatibility when running as a script
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

    # Extract arguments
    arguments = extract_prompt_arguments(parameters)

    # Print the arguments
    for arg in arguments:
        print(f'Name: {arg.name}')
        print(f'Description: {arg.description}')
        print(f'Required: {arg.required}')
        print()

    # Test with a parameter that has no description
    parameters = [
        {
            'name': 'petId',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer', 'format': 'int64'},
        }
    ]

    # Extract arguments
    arguments = extract_prompt_arguments(parameters)

    # Print the arguments
    for arg in arguments:
        print(f'Name: {arg.name}')
        print(f'Description: {arg.description}')
        print(f'Required: {arg.required}')
        print()

    # Test with a request body that has both required and non-required properties
    request_body = {
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string', 'description': 'The name of the pet'},
                        'photoUrls': {'type': 'array', 'items': {'type': 'string'}},
                        'status': {
                            'type': 'string',
                            'description': 'Pet status in the store',
                            'default': 'available',
                            'enum': ['available', 'pending', 'sold'],
                        },
                        'tags': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer', 'format': 'int64'},
                                    'name': {'type': 'string'},
                                },
                            },
                        },
                    },
                    'required': ['name', 'photoUrls'],
                }
            }
        }
    }

    # Extract arguments
    arguments = extract_prompt_arguments([], request_body)

    # Print the arguments
    for arg in arguments:
        print(f'Name: {arg.name}')
        print(f'Description: {arg.description}')
        print(f'Required: {arg.required}')
        print()
