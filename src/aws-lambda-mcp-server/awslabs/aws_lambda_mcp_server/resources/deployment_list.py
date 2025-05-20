"""
Deployment List Resource

Provides a list of all AWS deployments managed by the MCP server.
"""

import os
import tempfile
import json
from typing import Dict, Any
from awslabs.aws_lambda_mcp_server.utils.logger import logger


# Define the directory where deployment status files will be stored
DEPLOYMENT_STATUS_DIR = os.path.join(tempfile.gettempdir(), 'serverless-web-mcp-deployments')

# Ensure the directory exists
os.makedirs(DEPLOYMENT_STATUS_DIR, exist_ok=True)


async def list_deployments() -> Dict[str, Any]:
    """
    List all deployments.
    
    Returns:
        Dict: List of deployments
    """
    try:
        if not os.path.exists(DEPLOYMENT_STATUS_DIR):
            return {
                'success': True,
                'message': "No deployments found",
                'deployments': []
            }
        
        deployments = []
        for file_name in os.listdir(DEPLOYMENT_STATUS_DIR):
            if file_name.endswith('.json'):
                try:
                    with open(os.path.join(DEPLOYMENT_STATUS_DIR, file_name), 'r') as f:
                        status_data = json.load(f)
                    
                    project_name = file_name.replace('.json', '')
                    deployments.append({
                        'projectName': project_name,
                        'status': status_data.get('status', 'UNKNOWN'),
                        'deploymentType': status_data.get('deploymentType'),
                        'framework': status_data.get('framework'),
                        'updatedAt': status_data.get('updatedAt')
                    })
                except Exception as e:
                    logger.error(f"Error reading deployment status file {file_name}: {str(e)}")
        
        return {
            'success': True,
            'message': f"Found {len(deployments)} deployments",
            'deployments': deployments
        }
    except Exception as e:
        logger.error(f"Error listing deployments: {str(e)}")
        return {
            'success': False,
            'message': "Failed to list deployments",
            'error': str(e)
        }


async def handle_deployments_list() -> Dict[str, Any]:
    try:
        logger.info('Deployment list resource called')

        # Use the list_deployments function from deployment_help.py
        deployments_result = await list_deployments()
        deployments = deployments_result.get('deployments', [])
        logger.info(f"Found {len(deployments)} deployments")

        # Format deployments for MCP response
        formatted_deployments = [
            {
                "uri": f"deployment:://{deployment['projectName']}",
                "text": json.dumps({
                    "projectName": deployment['projectName'],
                    "type": deployment.get('deploymentType', 'unknown'),
                    "status": deployment.get('status', 'unknown'),
                    "lastUpdated": deployment.get('updatedAt', '')
                })
            } for deployment in deployments
        ]

        # Return in the format expected by MCP protocol
        return {
            "contents": formatted_deployments,
            "metadata": {
                "count": len(formatted_deployments)
            }
        }
    except Exception as error:
        logger.error(f'Error listing deployments: {error}')
        return {
            "contents": [],
            "metadata": {
                "count": 0,
                "error": f"Failed to list deployments: {str(error)}"
            }
        }