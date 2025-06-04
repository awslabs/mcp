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

"""Deploy Web App Tool for AWS Serverless MCP Server.

Handles deployment of web applications to AWS serverless infrastructure.
"""

import json
import os
import threading
from awslabs.aws_serverless_mcp_server.models import (
    BackendConfiguration,
    DeployWebAppRequest,
    FrontendConfiguration,
)
from awslabs.aws_serverless_mcp_server.tools.common.base_tool import BaseTool
from awslabs.aws_serverless_mcp_server.tools.webapps.utils.deploy_service import (
    DeploymentStatus,
    deploy_application,
)
from awslabs.aws_serverless_mcp_server.utils.const import DEPLOYMENT_STATUS_DIR
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, Literal, Optional


class DeployWebAppTool(BaseTool):
    """Tool for deploying web applications to AWS serverless infrastructure."""

    def __init__(self, mcp: FastMCP, allow_write):
        """Initialize the DeployWebAppTool with a FastMCP instance."""
        super().__init__(allow_write=allow_write)
        mcp.tool(name='deploy_webapp')(self.deploy_webapp)
        self.allow_write = allow_write

    async def deploy_webapp(
        self,
        ctx: Context,
        deployment_type: Literal['backend', 'frontend', 'fullstack'] = Field(
            description='Type of deployment'
        ),
        project_name: str = Field(description='Project name'),
        project_root: str = Field(description='Absolute path to the project root directory'),
        region: Optional[str] = Field(
            default=None, description='AWS Region to deploy to (e.g., us-east-1)'
        ),
        backend_configuration: Optional[BackendConfiguration] = Field(
            default=None, description='Backend configuration'
        ),
        frontend_configuration: Optional[FrontendConfiguration] = Field(
            default=None, description='Frontend configuration'
        ),
    ) -> Dict[str, Any]:
        """Deploy web applications to AWS Serverless, including Lambda as compute, DynamoDB as databases, API GW, ACM Certificates, and Route 53 DNS records.

        This tool uses the Lambda Web Adapter framework so that applications can be written in a standard web framework like Express or Next.js can be easily
        deployed to Lambda. You do not need to use integrate the code with any adapter framework before using this tool.

        Returns:
            Dict: Deployment result and link to pending deployment resource
        """
        self.checkToolAccess()
        try:
            params = DeployWebAppRequest(
                deployment_type=deployment_type,
                project_name=project_name,
                project_root=project_root,
                region=region,
                backend_configuration=backend_configuration,
                frontend_configuration=frontend_configuration,
            )
            os.makedirs(DEPLOYMENT_STATUS_DIR, exist_ok=True)

            # Check if this is a destructive deployment type change
            destructive_check = await self.check_destructive_deployment_change(
                project_name, deployment_type
            )

            if destructive_check.get('isDestructive'):
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': json.dumps(
                                {
                                    'success': False,
                                    'message': 'Destructive deployment type change detected',
                                    'warning': destructive_check.get('warning'),
                                    'error': 'Destructive change requires confirmation',
                                    'action': 'Please reconsider your deployment strategy based on the recommendation above.',
                                },
                                indent=2,
                            ),
                        }
                    ]
                }

            # Check for dependencies if this is a backend deployment
            if deployment_type in ['backend', 'fullstack'] and backend_configuration:
                backend_config = backend_configuration

                # Determine the full path to artifacts directory
                full_artifacts_path = backend_config.built_artifacts_path

                # If built_artifacts_path is not an absolute path, resolve it against project_root
                if not os.path.isabs(full_artifacts_path):
                    full_artifacts_path = os.path.join(project_root, full_artifacts_path)

                deps_installed = self.check_dependencies_installed(
                    full_artifacts_path, backend_config.runtime
                )

                if not deps_installed:
                    instructions = ''

                    if 'nodejs' in backend_config.runtime:
                        instructions = f"1. Copy package.json to {backend_config.built_artifacts_path}\n2. Run 'npm install --omit-dev' in {backend_config.built_artifacts_path}"
                    elif 'python' in backend_config.runtime:
                        instructions = f"1. Copy requirements.txt to {backend_config.built_artifacts_path}\n2. Run 'pip install -r requirements.txt -t .' in {backend_config.built_artifacts_path}"
                    elif 'ruby' in backend_config.runtime:
                        instructions = f"1. Copy Gemfile to {backend_config.built_artifacts_path}\n2. Run 'bundle install' in {backend_config.built_artifacts_path}"
                    else:
                        instructions = f'Install all required dependencies in {backend_config.built_artifacts_path}'

                    error_message = f"""
    IMPORTANT: Dependencies not found in built_artifacts_path ({backend_config.built_artifacts_path}).

    For {backend_config.runtime}, please:

    {instructions}

    Please install dependencies and try again.
                    """

                    return {
                        'content': [
                            {
                                'type': 'text',
                                'text': json.dumps(
                                    {
                                        'success': False,
                                        'message': 'Dependencies not found in built_artifacts_path',
                                        'error': 'Missing dependencies',
                                        'instructions': error_message,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    }

            # Start the deployment process in a background thread
            project_name = project_name

            def deploy_in_background():
                try:
                    import asyncio

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(deploy_application(params))
                    logger.info(
                        f'Background deployment completed for {project_name} with result: {json.dumps(result)}'
                    )
                except Exception as e:
                    logger.error(f'Background deployment failed for {project_name}: {str(e)}')

            thread = threading.Thread(target=deploy_in_background)
            thread.daemon = True
            thread.start()

            # Return an immediate response
            response_text = json.dumps(
                {
                    'success': True,
                    'message': f'Deployment of {project_name} initiated successfully.',
                    'status': DeploymentStatus.IN_PROGRESS,
                    'note': 'The deployment process is running in the background and may take several minutes to complete.',
                    'checkStatus': f'To check the status of your deployment, use the resource: deployment://{project_name}',
                },
                indent=2,
            )

            response = {'content': [{'type': 'text', 'text': response_text}]}

            logger.debug(f'Deploy tool response: {json.dumps(response)}')
            return response
        except Exception as e:
            logger.error(f'Deploy tool error: {str(e)}')

            return {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps(
                            {
                                'success': False,
                                'message': f'Deployment failed: {str(e)}',
                                'error': str(e),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

    @staticmethod
    def check_dependencies_installed(built_artifacts_path: str, runtime: str) -> bool:
        """Checks if dependencies appear to be installed in the built_artifacts_path.

        Args:
            built_artifacts_path: Path to the built artifacts
            runtime: Lambda runtime

        Returns:
            bool: True if dependencies appear to be installed, False otherwise
        """
        try:
            # For Node.js, check for node_modules directory
            if 'nodejs' in runtime:
                return os.path.exists(os.path.join(built_artifacts_path, 'node_modules'))

            # For Python, check for dependencies
            if 'python' in runtime:
                # Check for traditional Python package directories
                if (
                    os.path.exists(os.path.join(built_artifacts_path, 'site-packages'))
                    or os.path.exists(os.path.join(built_artifacts_path, '.venv'))
                    or os.path.exists(os.path.join(built_artifacts_path, 'dist-packages'))
                ):
                    return True

                # Check for pip installed dependencies directly in the directory (using -t .)
                # Look for .dist-info directories which indicate installed packages
                try:
                    files = os.listdir(built_artifacts_path)
                    # If we find any .dist-info directories, we have dependencies
                    return any(file.endswith('.dist-info') for file in files)
                except Exception as e:
                    logger.error(f'Error reading directory for Python dependencies: {str(e)}')
                    return False

            # For Ruby, check for vendor/bundle directory
            if 'ruby' in runtime:
                return os.path.exists(os.path.join(built_artifacts_path, 'vendor/bundle'))

            # For other runtimes, assume dependencies are installed
            return True
        except Exception as e:
            logger.error(f'Error checking for dependencies: {str(e)}')
            return False

    @staticmethod
    async def check_destructive_deployment_change(
        project_name: str, new_type: str
    ) -> Dict[str, Any]:
        """Check if a deployment type change is destructive.

        Args:
            project_name: Name of the project
            new_type: New deployment type

        Returns:
            Dict: Object with isDestructive flag and warning message
        """
        try:
            # Check if there's an existing deployment
            status_file_path = os.path.join(DEPLOYMENT_STATUS_DIR, f'{project_name}.json')

            if not os.path.exists(status_file_path):
                # No existing deployment, so not destructive
                return {'isDestructive': False}

            # Read the existing deployment status
            with open(status_file_path, 'r', encoding='utf-8') as f:
                status_data = json.load(f)

            current_type = status_data.get('deploymentType')

            if not current_type or current_type == new_type:
                # No type change or same type, not destructive
                return {'isDestructive': False}

            # Define destructive changes
            destructive_changes = [
                {'from': 'backend', 'to': 'frontend'},
                {'from': 'frontend', 'to': 'backend'},
                {'from': 'fullstack', 'to': 'backend'},
                {'from': 'fullstack', 'to': 'frontend'},
            ]

            # Check if this is a destructive change
            is_destructive = any(
                change['from'] == current_type and change['to'] == new_type
                for change in destructive_changes
            )

            if is_destructive:
                recommendation = ''

                # Provide specific recommendations based on the change
                if current_type == 'backend' and new_type == 'frontend':
                    recommendation = "Consider using 'fullstack' deployment type instead, which can maintain your backend while adding frontend capabilities."
                elif current_type == 'frontend' and new_type == 'backend':
                    recommendation = "Consider using 'fullstack' deployment type instead, which can maintain your frontend while adding backend capabilities."
                elif current_type == 'fullstack':
                    recommendation = "Consider keeping the 'fullstack' deployment type and simply updating the configuration you need."

                return {
                    'isDestructive': True,
                    'warning': f'WARNING: Changing deployment type from {current_type} to {new_type} is destructive and will delete existing resources, potentially causing data loss. {recommendation}',
                }

            return {'isDestructive': False}
        except Exception as e:
            logger.error(f'Error checking for destructive deployment change: {str(e)}')
            return {'isDestructive': False}  # Default to non-destructive on error
