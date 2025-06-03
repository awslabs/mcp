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
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Deployment Metadata for AWS Serverless MCP Server.

Handles storage and retrieval of deployment metadata for serverless web applications.
Provides detailed information about deployments by fetching CloudFormation stack status.
"""

import json
import os
from awslabs.aws_serverless_mcp_server.utils.cloudformation import (
    get_stack_info,
    map_cloudformation_status,
)
from awslabs.aws_serverless_mcp_server.utils.const import DEPLOYMENT_STATUS_DIR
from datetime import datetime
from loguru import logger
from typing import Any, Dict, List, Optional


class DeploymentStatus:
    """Deployment status enum."""

    IN_PROGRESS = 'IN_PROGRESS'
    DEPLOYED = 'DEPLOYED'
    FAILED = 'FAILED'
    NOT_FOUND = 'NOT_FOUND'


async def initialize_deployment_status(
    project_name: str, deployment_type: str, framework: str, region: Optional[str]
) -> None:
    """Initialize deployment metadata for a new deployment.

    Args:
        project_name: Name of the project
        deployment_type: Type of deployment (backend, frontend, fullstack)
        framework: Framework used for the deployment
        region: AWS region for the deployment (optional)
    """
    metadata_file = os.path.join(DEPLOYMENT_STATUS_DIR, f'{project_name}.json')

    try:
        # Create the metadata file with minimal information
        metadata = {
            'projectName': project_name,
            'timestamp': datetime.now().isoformat(),
            'deploymentType': deployment_type,
            'framework': framework,
            'status': DeploymentStatus.IN_PROGRESS,
        }
        if region:
            metadata['region'] = region

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f'Deployment metadata initialized for {project_name}')
    except Exception as e:
        logger.error(f'Failed to initialize deployment metadata for {project_name}: {str(e)}')


async def store_deployment_metadata(project_name: str, metadata: Dict[str, Any]) -> None:
    """Update deployment metadata with additional information.

    Args:
        project_name: Name of the project
        metadata: Additional metadata to store
    """
    metadata_file = os.path.join(DEPLOYMENT_STATUS_DIR, f'{project_name}.json')

    try:
        # Read existing metadata
        existing_metadata = {}
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                existing_metadata = json.load(f)
        except Exception:
            # File might not exist yet, that's ok
            pass

        # Merge with new metadata
        updated_metadata = {
            **existing_metadata,
            **metadata,
            'lastUpdated': datetime.now().isoformat(),
        }

        # Write back to file
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(updated_metadata, f, indent=2)

        logger.info(f'Deployment metadata updated for {project_name}')
    except Exception as e:
        logger.error(f'Failed to store deployment metadata for {project_name}: {str(e)}')


async def store_deployment_error(project_name: str, error: Any) -> None:
    """Store deployment errors when a deployment fails.

    Args:
        project_name: Name of the project
        error: Error information
    """
    error_message = str(error) if not isinstance(error, str) else error
    await store_deployment_metadata(
        project_name,
        {
            'status': DeploymentStatus.FAILED,
            'error': error_message,
            'errorTimestamp': datetime.now().isoformat(),
        },
    )


async def get_deployment_status(project_name: str) -> Dict[str, Any]:
    """Get deployment status by combining metadata and CloudFormation status.

    Args:
        project_name: Name of the project

    Returns:
        Dict: Deployment status information
    """
    metadata_file = os.path.join(DEPLOYMENT_STATUS_DIR, f'{project_name}.json')

    try:
        # Check if metadata file exists
        if not os.path.exists(metadata_file):
            logger.info(f'No deployment metadata found for project: {project_name}')
            return {
                'status': DeploymentStatus.NOT_FOUND,
                'message': f'No deployment found for project: {project_name}',
                'projectName': project_name,
            }

        # Read metadata file
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # Get stack info from CloudFormation
        region = metadata.get('region')

        try:
            stack_info = await get_stack_info(project_name, region)

            # Map CloudFormation status to our status format
            cf_status = stack_info.get('status')
            status = map_cloudformation_status(cf_status) if cf_status is not None else 'UNKNOWN'

            # If stack not found but we have metadata, deployment failed before CFN or CFN deployment is in progress.
            if stack_info.get('status') == 'NOT_FOUND':
                return metadata

            # Return combined information
            deployment = {
                'status': status,
                'stackStatus': stack_info.get('status'),
                'stackStatusReason': stack_info.get('statusReason'),
                'timestamp': metadata.get('timestamp'),
                'lastUpdated': stack_info.get('lastUpdatedTime') or metadata.get('lastUpdated'),
                'deploymentType': metadata.get('deploymentType'),
                'framework': metadata.get('framework'),
                'outputs': stack_info.get('outputs'),
                'projectName': project_name,
            }
            if region:
                deployment['region'] = region

            if 'outputs' in deployment and deployment['outputs']:
                formatted_outputs = {}
                for key, value in deployment['outputs'].items():
                    formatted_outputs[key] = {'value': value, 'description': f'Output for {key}'}
                deployment['formattedOutputs'] = formatted_outputs
            return deployment
        except Exception as e:
            # If CloudFormation query fails, return metadata with error
            logger.error(f'Failed to get CloudFormation stack info for {project_name}: {str(e)}')
            return {
                'status': 'unknown',
                'timestamp': metadata.get('timestamp'),
                'deploymentType': metadata.get('deploymentType'),
                'framework': metadata.get('framework'),
                'message': f'Error querying CloudFormation: {str(e)}',
                'projectName': metadata.get('projectName'),
            }
    except Exception as e:
        logger.error(f'Failed to get deployment status for {project_name}: {str(e)}')
        raise Exception(f'Failed to get deployment status: {str(e)}')


async def list_deployments(
    limit: Optional[int] = None,
    sort_by: str = 'timestamp',
    sort_order: str = 'desc',
    filter_status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all deployments by combining metadata and CloudFormation status.

    Args:
        limit: Maximum number of deployments to return
        sort_by: Field to sort by (defaults to 'timestamp')
        sort_order: Sort order ('asc' or 'desc', defaults to 'desc')
        filter_status: Optional status to filter deployments by

    Returns:
        List[Dict]: List of deployment status information
    """
    try:
        logger.info(f'Listing deployments from directory: {DEPLOYMENT_STATUS_DIR}')
        try:
            files = os.listdir(DEPLOYMENT_STATUS_DIR)
        except Exception as e:
            logger.error(f'Error reading deployment directory: {str(e)}')
            return []
        metadata_files = [f for f in files if f.endswith('.json')]
        deployments = []
        for file in metadata_files:
            try:
                project_name = os.path.splitext(file)[0]
                status = await get_deployment_status(project_name)
                if status:
                    deployments.append(status)
            except Exception as e:
                logger.error(f'Error processing deployment {file}: {str(e)}')
        if filter_status:
            deployments = [d for d in deployments if d.get('status') == filter_status]
        reverse = sort_order.lower() == 'desc'
        deployments.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        if limit:
            deployments = deployments[:limit]
        return deployments
    except Exception as e:
        logger.error(f'Failed to list deployments: {str(e)}')
        raise
