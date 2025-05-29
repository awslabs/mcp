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
