# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Deployment Details Resource.

Provides information about a specific deployment.
"""

from awslabs.aws_serverless_mcp_server.utils.deployment_manager import (
    DeploymentStatus,
    get_deployment_status,
)
from loguru import logger
from typing import Any, Dict


async def handle_deployment_details(project_name: str) -> Dict[str, Any]:
    """Get the status of a CloudFormation deployment that is managed by this MCP server.

    Args:
        project_name: Name of the project

    Returns:
        Dict: Deployment status with CloudFormation stack details and stack outputs
    """
    try:
        # Use deployment_metadata.py to get detailed stack information
        deployment_details = await get_deployment_status(project_name)

        if deployment_details.get('status') == DeploymentStatus.NOT_FOUND:
            return {
                'success': False,
                'message': f"No deployment found for project '{project_name}'",
                'status': 'NOT_FOUND',
            }

        return {
            'success': True,
            'message': f"Deployment status retrieved for project '{project_name}'",
            'status': deployment_details.get('status'),
            'deploymentType': deployment_details.get('deploymentType'),
            'framework': deployment_details.get('framework'),
            'startedAt': deployment_details.get('timestamp'),
            'updatedAt': deployment_details.get('lastUpdated'),
            'outputs': deployment_details.get('outputs', {}),
            'error': deployment_details.get('error'),
            'stackStatus': deployment_details.get('stackStatus'),
            'stackStatusReason': deployment_details.get('stackStatusReason'),
        }
    except Exception as e:
        logger.error(f'Error getting deployment status: {str(e)}')
        return {
            'success': False,
            'message': f"Failed to get deployment status for project '{project_name}'",
            'error': str(e),
        }
