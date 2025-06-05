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

"""Deployment help tool for AWS Serverless MCP Server."""

from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, Literal, Optional


class WebappDeploymentHelpTool:
    """Tool to provide help information for web application deployments using the deploy_webapp_tool."""

    def __init__(self, mcp: FastMCP):
        """Initialize the webapp deployment help tool."""
        mcp.tool(name='webapp_deployment_help')(self.webapp_deployment_help_tool)

    async def webapp_deployment_help_tool(
        self,
        ctx: Context,
        deployment_type: Optional[Literal['backend', 'frontend', 'fullstack']] = Field(
            description='Type of deployment to get help information for'
        ),
    ) -> Dict[str, Any]:
        """Get help information about using the deploy_webapp_tool to perform web application deployments.

        If deployment_type is provided, returns help information for that deployment type.
        Otherwise, returns general help information.

        Returns:
            Dict: Deployment help information
        """
        await ctx.info(f'Getting deployment help for {deployment_type}')
        try:
            # General deployment help
            general_help = {
                'description': 'The deploy_webapp tool can be used to deploy web applications to AWS serverless infrastructure. Using Lambda Web Adapter,'
                '',
                'deploymentTypes': {
                    'backend': 'Deploy a backend application to AWS Lambda with API Gateway.',
                    'frontend': 'Deploy a frontend application to Amazon S3 and CloudFront.',
                    'fullstack': 'Deploy both backend and frontend components.',
                },
                'workflow': [
                    """1. Initialize your project with the appropriate framework. You can use popular frameworks like Express.js, Flask, React, etc.
                        without needing to follow AWS Lambda specific conventions. If you're building a fullstack application, ensure backend and frontend
                        are structured in separate directories.""",
                    '2. Build your application using the build command for your framework (e.g., `npm run build`, `python setup.py build`).',
                    '3. Deploy your application using the deploy_web_app_tool.',
                    '4. Check the deployment status using the deployment://{name} resource .',
                    '5. Configure a custom domain using the configure_domain_tool (optional).',
                    '6. Update your frontend using the update_frontend_tool (optional).',
                    '7. Monitor your application using the sam_logs tool and get_metrics_tool.',
                ],
            }
            specific_help = {}
            if deployment_type == 'backend':
                specific_help = {
                    'description': 'Backend deployments use AWS Lambda with API Gateway to host your web application.',
                    'supportedFrameworks': [
                        'Express.js',
                        'Flask',
                        'FastAPI',
                        'Spring Boot',
                        'Ruby on Rails',
                    ],
                    'requirements': [
                        'Your application must listen on a port specified by the PORT environment variable.',
                        'Dependencies must be installed in the built artifacts directory.',
                        'A startup script must be provided or generated.',
                    ],
                    'example': {
                        'deployment_type': 'backend',
                        'project_name': 'my-backend-app',
                        'project_root': '/path/to/project',
                        'backend_configuration': {
                            'built_artifacts_path': '/path/to/project/dist',
                            'runtime': 'nodejs22.x',
                            'port': 3000,
                            'startup_script': 'bootstrap',
                            'environment': {'NODE_ENV': 'production', 'DB_HOST': 'localhost'},
                        },
                    },
                }
            elif deployment_type == 'frontend':
                specific_help = {
                    'description': 'Frontend deployments use Amazon S3 for storage and CloudFront for content delivery.',
                    'supportedFrameworks': [
                        'React',
                        'Angular',
                        'Vue.js',
                        'Next.js (static export)',
                        'Svelte',
                    ],
                    'requirements': [
                        'Your application must be built as static assets.',
                        'An index.html file must be present in the built assets directory.',
                    ],
                    'example': {
                        'deployment_type': 'frontend',
                        'project_name': 'my-frontend-app',
                        'project_root': '/path/to/project',
                        'frontend_configuration': {
                            'built_assets_path': '/path/to/project/build',
                            'index_document': 'index.html',
                            'error_document': 'index.html',
                        },
                    },
                }
            elif deployment_type == 'fullstack':
                specific_help = {
                    'description': 'Fullstack deployments combine backend and frontend deployments.',
                    'requirements': [
                        'Both backend and frontend configurations must be provided.',
                        'See backend and frontend requirements for specific details.',
                    ],
                    'example': {
                        'deployment_type': 'fullstack',
                        'project_name': 'my-fullstack-app',
                        'project_root': '/path/to/project',
                        'backend_configuration': {
                            'built_artifacts_path': '/path/to/project/backend/dist',
                            'runtime': 'nodejs22.x',
                            'port': 3000,
                            'startup_script': 'bootstrap',
                        },
                        'frontend_configuration': {
                            'built_assets_path': '/path/to/project/frontend/build',
                            'index_document': 'index.html',
                            'error_document': 'index.html',
                        },
                    },
                }
            help_info = {**general_help}
            if specific_help:
                help_info['specificHelp'] = specific_help
            response = {'success': True, 'content': help_info}
            if deployment_type:
                response['topic'] = deployment_type
            return response
        except Exception as e:
            logger.error(f'Error in webapp_deployment_help: {str(e)}')
            return {
                'success': False,
                'message': 'Failed to get deployment help or status',
                'error': str(e),
            }
