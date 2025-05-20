"""Deployment help tool for AWS Lambda MCP Server."""

from typing import Dict, Any, Optional
from awslabs.aws_lambda_mcp_server.utils.logger import logger
from awslabs.aws_lambda_mcp_server.models import DeploymentHelpRequest

async def get_deployment_help(deployment_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Get help information about deployments.
    
    Args:
        deployment_type: Type of deployment (backend, frontend, fullstack)
    
    Returns:
        Dict: Deployment help information
    """
    try:
        # General deployment help
        general_help = {
            'description': 'The AWS Lambda MCP Server provides tools for deploying web applications to AWS serverless infrastructure.',
            'deploymentTypes': {
                'backend': 'Deploy a backend application to AWS Lambda with API Gateway.',
                'frontend': 'Deploy a frontend application to Amazon S3 and CloudFront.',
                'fullstack': 'Deploy both backend and frontend components.'
            },
            'workflow': [
                '1. Initialize your project with the appropriate framework.',
                '2. Build your application.',
                '3. Deploy your application using the deploy_web_app_tool.',
                '4. Check the deployment status using the deployment_help_tool.',
                '5. Configure a custom domain using the configure_domain_tool (optional).',
                '6. Update your frontend using the update_frontend_tool (optional).',
                '7. Monitor your application using the get_logs_tool and get_metrics_tool.'
            ]
        }
        
        # Specific deployment type help
        if deployment_type == 'backend':
            specific_help = {
                'description': 'Backend deployments use AWS Lambda with API Gateway to host your web application.',
                'supportedFrameworks': ['Express.js', 'Flask', 'FastAPI', 'Spring Boot', 'Ruby on Rails'],
                'requirements': [
                    'Your application must listen on a port specified by the PORT environment variable.',
                    'Dependencies must be installed in the built artifacts directory.',
                    'A startup script must be provided or generated.'
                ],
                'example': {
                    'deployment_type': 'backend',
                    'project_name': 'my-backend-app',
                    'project_root': '/path/to/project',
                    'backend_configuration': {
                        'built_artifacts_path': '/path/to/project/dist',
                        'runtime': 'nodejs18.x',
                        'port': 3000,
                        'startup_script': 'bootstrap',
                        'environment': {
                            'NODE_ENV': 'production',
                            'DB_HOST': 'localhost'
                        }
                    }
                }
            }
        elif deployment_type == 'frontend':
            specific_help = {
                'description': 'Frontend deployments use Amazon S3 for storage and CloudFront for content delivery.',
                'supportedFrameworks': ['React', 'Angular', 'Vue.js', 'Next.js (static export)', 'Svelte'],
                'requirements': [
                    'Your application must be built as static assets.',
                    'An index.html file must be present in the built assets directory.'
                ],
                'example': {
                    'deployment_type': 'frontend',
                    'project_name': 'my-frontend-app',
                    'project_root': '/path/to/project',
                    'frontend_configuration': {
                        'built_assets_path': '/path/to/project/build',
                        'index_document': 'index.html',
                        'error_document': 'index.html'
                    }
                }
            }
        elif deployment_type == 'fullstack':
            specific_help = {
                'description': 'Fullstack deployments combine backend and frontend deployments.',
                'requirements': [
                    'Both backend and frontend configurations must be provided.',
                    'See backend and frontend requirements for specific details.'
                ],
                'example': {
                    'deployment_type': 'fullstack',
                    'project_name': 'my-fullstack-app',
                    'project_root': '/path/to/project',
                    'backend_configuration': {
                        'built_artifacts_path': '/path/to/project/backend/dist',
                        'runtime': 'nodejs18.x',
                        'port': 3000,
                        'startup_script': 'bootstrap'
                    },
                    'frontend_configuration': {
                        'built_assets_path': '/path/to/project/frontend/build',
                        'index_document': 'index.html',
                        'error_document': 'index.html'
                    }
                }
            }
        else:
            specific_help = {}
        
        # Combine general and specific help
        help_info = {**general_help}
        if specific_help:
            help_info['specificHelp'] = specific_help
        
        return {
            'success': True,
            'message': f"Deployment help information for {deployment_type if deployment_type else 'all deployment types'}",
            'help': help_info
        }
    except Exception as e:
        logger.error(f"Error getting deployment help: {str(e)}")
        return {
            'success': False,
            'message': "Failed to get deployment help",
            'error': str(e)
        }

async def deployment_help(request: DeploymentHelpRequest) -> Dict[str, Any]:
    """
    Get help information about deployments or deployment status.
    
    Args:
        deployment_type: Type of deployment (backend, frontend, fullstack) (optional)
    
    Returns:
        Dict: Deployment help information or status
    """
    try:
        help_result = await get_deployment_help(request.deployment_type)
        
        return {
            'success': True,
            'topic': request.deployment_type,
            'content': help_result.get('help', {})
        }
    except Exception as e:
        logger.error(f"Error in deployment_help: {str(e)}")
        return {
            'success': False,
            'message': "Failed to get deployment help or status",
            'error': str(e)
        }
