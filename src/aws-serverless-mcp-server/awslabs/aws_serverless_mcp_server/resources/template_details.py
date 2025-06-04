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

"""Template Details Resource.

Provides details about a specific deployment template.
"""

import json
from typing import Any, Dict


def handle_template_details(template_name: str) -> Dict[str, Any]:
    """Retrieve detailed information about a specified deployment template.

    Args:
        template_name (str): The name of the template to retrieve details for.
            Supported values are 'backend', 'frontend', and 'fullstack'.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'contents': A list with a dictionary containing:
                - 'uri': The template URI (e.g., 'template:backend').
                - 'text': A JSON string with the template details or an error message.
            - 'metadata': Metadata about the template, including its name or error information.

    If the template_name is not recognized, returns an error message in the expected format.
    """
    template_details = None

    if template_name == 'backend':
        template_details = {
            'name': 'backend',
            'description': 'Backend service using API Gateway and Lambda',
            'frameworks': ['express', 'flask', 'fastapi', 'nodejs'],
            'parameters': {
                'runtime': {
                    'type': 'string',
                    'description': 'Lambda runtime',
                    'default': 'nodejs22.x',
                    'options': ['nodejs22.x', 'nodejs20.x', 'python3.13', 'python3.12'],
                },
                'memorySize': {
                    'type': 'number',
                    'description': 'Lambda memory size in MB',
                    'default': 512,
                    'min': 128,
                    'max': 10240,
                },
                'timeout': {
                    'type': 'number',
                    'description': 'Lambda timeout in seconds',
                    'default': 30,
                    'min': 1,
                    'max': 900,
                },
            },
            'example': {
                'deploymentType': 'backend',
                'source': {'path': './my-api'},
                'framework': 'express',
                'configuration': {
                    'projectName': 'my-api',
                    'region': 'us-east-1',
                    'backendConfiguration': {
                        'runtime': 'nodejs22.x',
                        'entryPoint': 'app.js',
                        'memorySize': 512,
                        'timeout': 30,
                    },
                },
            },
        }
    elif template_name == 'frontend':
        template_details = {
            'name': 'frontend',
            'description': 'Frontend application using S3 and CloudFront',
            'frameworks': ['react', 'vue', 'angular', 'static'],
            'parameters': {
                'type': {
                    'type': 'string',
                    'description': 'Frontend type',
                    'default': 'static',
                    'options': ['static', 'react', 'vue', 'angular'],
                },
                'indexDocument': {
                    'type': 'string',
                    'description': 'Index document',
                    'default': 'index.html',
                },
                'errorDocument': {
                    'type': 'string',
                    'description': 'Error document',
                    'default': 'error.html',
                },
            },
            'example': {
                'deploymentType': 'frontend',
                'source': {'path': './my-website'},
                'configuration': {
                    'projectName': 'my-website',
                    'region': 'us-east-1',
                    'frontendConfiguration': {
                        'type': 'react',
                        'indexDocument': 'index.html',
                        'errorDocument': 'index.html',
                    },
                },
            },
        }
    elif template_name == 'fullstack':
        template_details = {
            'name': 'fullstack',
            'description': 'Combined backend and frontend deployment',
            'frameworks': ['express+react', 'flask+vue', 'fastapi+react', 'nextjs'],
            'parameters': {
                # Combined parameters from backend and frontend
                'backend': {
                    'runtime': {
                        'type': 'string',
                        'description': 'Lambda runtime',
                        'default': 'nodejs22.x',
                        'options': ['nodejs22.x', 'nodejs20.x', 'python3.13', 'python3.12'],
                    },
                    'memorySize': {
                        'type': 'number',
                        'description': 'Lambda memory size in MB',
                        'default': 512,
                        'min': 128,
                        'max': 10240,
                    },
                },
                'frontend': {
                    'type': {
                        'type': 'string',
                        'description': 'Frontend type',
                        'default': 'react',
                        'options': ['react', 'vue', 'angular'],
                    }
                },
            },
            'example': {
                'deploymentType': 'fullstack',
                'source': {'path': './my-fullstack-app'},
                'framework': 'express+react',
                'configuration': {
                    'projectName': 'my-fullstack-app',
                    'region': 'us-east-1',
                    'backendConfiguration': {
                        'runtime': 'nodejs22.x',
                        'entryPoint': 'api/app.js',
                        'memorySize': 512,
                        'timeout': 30,
                    },
                    'frontendConfiguration': {
                        'type': 'react',
                        'indexDocument': 'index.html',
                        'errorDocument': 'index.html',
                    },
                },
            },
        }
    else:
        return {
            'contents': [
                {
                    'uri': f'template:{template_name}',
                    'text': json.dumps({'error': f"Template '{template_name}' not found"}),
                }
            ],
            'metadata': {'error': f"Template '{template_name}' not found"},
        }

    # Return in the format expected by MCP protocol
    return {
        'contents': [{'uri': f'template:{template_name}', 'text': json.dumps(template_details)}],
        'metadata': {'name': template_name},
    }
