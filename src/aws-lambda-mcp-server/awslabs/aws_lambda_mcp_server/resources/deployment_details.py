"""
Deployment Details Resource

Provides information about a specific deployment.
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

async def get_deployment_status(project_name: str) -> Dict[str, Any]:
    """
    Get the status of a deployment.
    
    Args:
        project_name: Name of the project
    
    Returns:
        Dict: Deployment status
    """
    try:
        status_file_path = os.path.join(DEPLOYMENT_STATUS_DIR, f'{project_name}.json')
        
        if not os.path.exists(status_file_path):
            return {
                'success': False,
                'message': f"No deployment found for project '{project_name}'",
                'status': 'NOT_FOUND'
            }
        
        with open(status_file_path, 'r') as f:
            status_data = json.load(f)
        
        return {
            'success': True,
            'message': f"Deployment status retrieved for project '{project_name}'",
            'status': status_data.get('status', 'UNKNOWN'),
            'deploymentType': status_data.get('deploymentType'),
            'framework': status_data.get('framework'),
            'startedAt': status_data.get('startedAt'),
            'updatedAt': status_data.get('updatedAt'),
            'outputs': status_data.get('outputs', {}),
            'error': status_data.get('error')
        }
    except Exception as e:
        logger.error(f"Error getting deployment status: {str(e)}")
        return {
            'success': False,
            'message': f"Failed to get deployment status for project '{project_name}'",
            'error': str(e)
        }


async def handle_deployment_details(project_name: str) -> Dict[str, Any]:
    logger.debug(f'Deployment details resource called for project: {project_name}')

    try:
        # Get deployment status
        deployment = await get_deployment_status(project_name)

        if not deployment or deployment.get('status') == 'NOT_FOUND':
            return {
                "contents": [{
                    "uri": f"deployment:{project_name}",
                    "text": json.dumps({
                        "error": f"Deployment not found for project: {project_name}",
                        "message": f"No deployment information available for {project_name}. Make sure you have initiated a deployment for this project."
                    }, indent=2)
                }],
                "metadata": {
                    "projectName": project_name
                }
            }

        # Format the response based on deployment status
        response_data = {
            "projectName": project_name,
            "status": deployment.get('status', 'UNKNOWN')
        }

        if deployment.get('status') == 'COMPLETE':
            response_data.update({
                "success": True,
                "outputs": deployment.get('outputs', {}),
                "deploymentType": deployment.get('deploymentType'),
                "framework": deployment.get('framework')
            })
        elif deployment.get('status') == 'FAILED':
            response_data.update({
                "success": False,
                "error": deployment.get('error', 'Unknown error'),
                "deploymentType": deployment.get('deploymentType'),
                "framework": deployment.get('framework')
            })
        else:
            # Deployment is still in progress
            response_data.update({
                "message": f"Deployment is currently in progress ({deployment.get('status', 'UNKNOWN')}).",
                "deploymentType": deployment.get('deploymentType'),
                "framework": deployment.get('framework'),
                "note": "Check this resource again in a few moments for updated status."
            })

        # Return in the format expected by MCP protocol
        return {
            "contents": [{
                "uri": f"deployment:{project_name}",
                "text": json.dumps(response_data, indent=2)
            }],
            "metadata": {
                "projectName": project_name
            }
        }
    except Exception as error:
        logger.error(f'Deployment details resource error: {error}')

        return {
            "contents": [{
                "uri": f"deployment:{project_name}",
                "text": json.dumps({
                    "error": f"Failed to get deployment details: {str(error)}"
                }, indent=2)
            }],
            "metadata": {
                "error": str(error)
            }
        }
