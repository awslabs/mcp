import json
from awslabs.aws_serverless_mcp_server.utils.deployment_manager import list_deployments
from loguru import logger
from typing import Any, Dict


async def handle_deployments_list() -> Dict[str, Any]:
    """List all deployments with CloudFormation stacks managed by this MCP server."""
    try:
        logger.info('Deployment list resource called')
        detailed_deployments = await list_deployments()

        if not detailed_deployments:
            return {'contents': [], 'metadata': {'count': 0, 'message': 'No deployments found'}}

        formatted_deployments = [
            {
                'uri': f'deployment://{deployment.get("projectName")}',
                'text': json.dumps(
                    {
                        'projectName': deployment.get('projectName'),
                        'type': deployment.get('deploymentType', 'unknown'),
                        'status': deployment.get('status', 'unknown'),
                        'timestamp': deployment.get('timestamp', ''),
                        'lastUpdated': deployment.get('lastUpdated', ''),
                    }
                ),
            }
            for deployment in detailed_deployments
        ]

        return {
            'contents': formatted_deployments,
            'metadata': {'count': len(formatted_deployments)},
        }
    except Exception as error:
        logger.error(f'Error listing deployments: {error}')
        return {
            'contents': [],
            'metadata': {'count': 0, 'error': f'Failed to list deployments: {str(error)}'},
        }
