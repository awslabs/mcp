"""
Template List Resource

Provides a list of available deployment templates.
"""

import json
from typing import Dict, Any


def handle_template_list() -> Dict[str, Any]:
    templates = [
        {
            "name": "backend",
            "description": "Backend service using API Gateway and Lambda",
            "frameworks": ["express", "flask", "fastapi", "nodejs"]
        },
        {
            "name": "frontend",
            "description": "Frontend application using S3 and CloudFront",
            "frameworks": ["react", "vue", "angular", "static"]
        },
        {
            "name": "fullstack",
            "description": "Combined backend and frontend deployment",
            "frameworks": ["express+react", "flask+vue", "fastapi+react", "nextjs"]
        },
        {
            "name": "database",
            "description": "DynamoDB database",
            "type": "dynamodb"
        }
    ]

    # Format the response according to MCP protocol requirements
    contents = [
        {
            "uri": f"template:://{template['name']}",
            "text": json.dumps(template)
        } for template in templates
    ]

    return {
        "contents": contents,
        "metadata": {
            "count": len(templates)
        }
    }
