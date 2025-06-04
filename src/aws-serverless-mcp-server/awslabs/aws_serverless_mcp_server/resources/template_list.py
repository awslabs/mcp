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

"""Template List Resource.

Provides a list of available deployment templates.
"""

import json
from typing import Any, Dict


def handle_template_list() -> Dict[str, Any]:
    """Generates a list of available project templates with their details.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'contents': A list of dictionaries, each with:
                - 'uri': A unique URI for the template.
                - 'text': A JSON string representation of the template details.
            - 'metadata': A dictionary with the total count of templates.

    The templates include backend, frontend, and fullstack options, each with supported frameworks.
    """
    templates = [
        {
            'name': 'backend',
            'description': 'Backend service using API Gateway and Lambda',
            'frameworks': ['express', 'flask', 'fastapi', 'nodejs'],
        },
        {
            'name': 'frontend',
            'description': 'Frontend application using S3 and CloudFront',
            'frameworks': ['react', 'vue', 'angular', 'static'],
        },
        {
            'name': 'fullstack',
            'description': 'Combined backend and frontend deployment',
            'frameworks': ['express+react', 'flask+vue', 'fastapi+react', 'nextjs'],
        },
    ]

    # Format the response according to MCP protocol requirements
    contents = [
        {'uri': f'template://{template["name"]}', 'text': json.dumps(template)}
        for template in templates
    ]

    return {'contents': contents, 'metadata': {'count': len(templates)}}
