"""
Template Details Resource

Provides details about a specific deployment template.
"""

import json
from typing import Dict, Any


def handle_template_details(template_name: str) -> Dict[str, Any]:
    template_details = None

    # Implement template-specific logic here
    if template_name == "backend":
        template_details = {
            "name": "backend",
            "description": "Backend service using API Gateway and Lambda",
            "frameworks": ["express", "flask", "fastapi", "nodejs"],
            "parameters": {
                "runtime": {
                    "type": "string",
                    "description": "Lambda runtime",
                    "default": "nodejs18.x",
                    "options": ["nodejs18.x", "nodejs16.x", "python3.9", "python3.8"]
                },
                "memorySize": {
                    "type": "number",
                    "description": "Lambda memory size in MB",
                    "default": 512,
                    "min": 128,
                    "max": 10240
                },
                "timeout": {
                    "type": "number",
                    "description": "Lambda timeout in seconds",
                    "default": 30,
                    "min": 1,
                    "max": 900
                }
            },
            "example": {
                "deploymentType": "backend",
                "source": {
                    "path": "./my-api"
                },
                "framework": "express",
                "configuration": {
                    "projectName": "my-api",
                    "region": "us-east-1",
                    "backendConfiguration": {
                        "runtime": "nodejs18.x",
                        "entryPoint": "app.js",
                        "memorySize": 512,
                        "timeout": 30
                    }
                }
            }
        }
    elif template_name == "frontend":
        template_details = {
            "name": "frontend",
            "description": "Frontend application using S3 and CloudFront",
            "frameworks": ["react", "vue", "angular", "static"],
            "parameters": {
                "type": {
                    "type": "string",
                    "description": "Frontend type",
                    "default": "static",
                    "options": ["static", "react", "vue", "angular"]
                },
                "indexDocument": {
                    "type": "string",
                    "description": "Index document",
                    "default": "index.html"
                },
                "errorDocument": {
                    "type": "string",
                    "description": "Error document",
                    "default": "error.html"
                }
            },
            "example": {
                "deploymentType": "frontend",
                "source": {
                    "path": "./my-website"
                },
                "configuration": {
                    "projectName": "my-website",
                    "region": "us-east-1",
                    "frontendConfiguration": {
                        "type": "react",
                        "indexDocument": "index.html",
                        "errorDocument": "index.html"
                    }
                }
            }
        }
    elif template_name == "fullstack":
        template_details = {
            "name": "fullstack",
            "description": "Combined backend and frontend deployment",
            "frameworks": ["express+react", "flask+vue", "fastapi+react", "nextjs"],
            "parameters": {
                # Combined parameters from backend and frontend
                "backend": {
                    "runtime": {
                        "type": "string",
                        "description": "Lambda runtime",
                        "default": "nodejs18.x",
                        "options": ["nodejs18.x", "nodejs16.x", "python3.9", "python3.8"]
                    },
                    "memorySize": {
                        "type": "number",
                        "description": "Lambda memory size in MB",
                        "default": 512,
                        "min": 128,
                        "max": 10240
                    }
                },
                "frontend": {
                    "type": {
                        "type": "string",
                        "description": "Frontend type",
                        "default": "react",
                        "options": ["react", "vue", "angular"]
                    }
                }
            },
            "example": {
                "deploymentType": "fullstack",
                "source": {
                    "path": "./my-fullstack-app"
                },
                "framework": "express+react",
                "configuration": {
                    "projectName": "my-fullstack-app",
                    "region": "us-east-1",
                    "backendConfiguration": {
                        "runtime": "nodejs18.x",
                        "entryPoint": "api/app.js",
                        "memorySize": 512,
                        "timeout": 30
                    },
                    "frontendConfiguration": {
                        "type": "react",
                        "indexDocument": "index.html",
                        "errorDocument": "index.html"
                    }
                }
            }
        }
    elif template_name == "database":
        template_details = {
            "name": "database",
            "description": "DynamoDB database",
            "type": "dynamodb",
            "parameters": {
                "tableName": {
                    "type": "string",
                    "description": "DynamoDB table name",
                    "required": True
                },
                "billingMode": {
                    "type": "string",
                    "description": "DynamoDB billing mode",
                    "default": "PAY_PER_REQUEST",
                    "options": ["PROVISIONED", "PAY_PER_REQUEST"]
                }
            },
            "example": {
                "tableName": "my-table",
                "billingMode": "PAY_PER_REQUEST",
                "attributeDefinitions": [
                    {"name": "id", "type": "S"}
                ],
                "keySchema": [
                    {"name": "id", "type": "HASH"}
                ]
            }
        }
    else:
        return {
            "contents": [{
                "uri": f"template:{template_name}",
                "text": json.dumps({"error": f"Template '{template_name}' not found"})
            }],
            "metadata": {
                "error": f"Template '{template_name}' not found"
            }
        }

    # Return in the format expected by MCP protocol
    return {
        "contents": [{
            "uri": f"template:{template_name}",
            "text": json.dumps(template_details)
        }],
        "metadata": {
            "name": template_name
        }
    }
