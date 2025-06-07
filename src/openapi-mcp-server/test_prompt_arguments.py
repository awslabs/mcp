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

from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import extract_prompt_arguments


# Test with a parameter that has a description, default value, and enum values
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
