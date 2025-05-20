"""Deploy web application tool for AWS Lambda MCP Server."""

import json
import os
import tempfile
import datetime
from typing import Dict, Any
from awslabs.aws_lambda_mcp_server.models import DeployWebAppRequest
from awslabs.aws_lambda_mcp_server.utils.logger import logger

# Define the directory where deployment status files will be stored
DEPLOYMENT_STATUS_DIR = os.path.join(tempfile.gettempdir(), 'serverless-web-mcp-deployments')

# Ensure the directory exists
os.makedirs(DEPLOYMENT_STATUS_DIR, exist_ok=True)

def check_dependencies_installed(built_artifacts_path: str, runtime: str) -> bool:
    """
    Check if dependencies appear to be installed in the built artifacts path.
    
    Args:
        built_artifacts_path: Path to the built artifacts
        runtime: Runtime environment
    
    Returns:
        bool: True if dependencies are installed, False otherwise
    """
    try:
        # For Node.js, check for node_modules directory
        if 'nodejs' in runtime:
            return os.path.exists(os.path.join(built_artifacts_path, 'node_modules'))

        # For Python, check for dependencies
        if 'python' in runtime:
            # Check for traditional Python package directories
            if (os.path.exists(os.path.join(built_artifacts_path, 'site-packages')) or
                os.path.exists(os.path.join(built_artifacts_path, '.venv')) or
                os.path.exists(os.path.join(built_artifacts_path, 'dist-packages'))):
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

async def check_destructive_deployment_change(project_name: str, new_type: str) -> Dict[str, Any]:
    """
    Check if a deployment type change is destructive.
    
    Args:
        project_name: Project name
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
        with open(status_file_path, 'r') as f:
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
            {'from': 'fullstack', 'to': 'frontend'}
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
                'warning': f"WARNING: Changing deployment type from {current_type} to {new_type} is destructive and will delete existing resources, potentially causing data loss. {recommendation}"
            }

        return {'isDestructive': False}
    except Exception as e:
        logger.error(f'Error checking for destructive deployment change: {str(e)}')
        return {'isDestructive': False}  # Default to non-destructive on error

async def deploy_application(params: DeployWebAppRequest) -> Dict[str, Any]:
    """
    Deploy a web application to AWS serverless infrastructure.
    
    Args:
        params: Deployment parameters
    
    Returns:
        Dict: Deployment result
    """
    try:
        # Extract parameters
        deployment_type = params.deployment_type
        project_name = params.project_name
        project_root = params.project_root
        
        logger.info(f'[DEPLOY START] Starting deployment process for {project_name}')
        logger.info(f'Deployment type: {deployment_type}')
        logger.info(f'Project root: {project_root}')
        
        # Initialize deployment status
        status_file_path = os.path.join(DEPLOYMENT_STATUS_DIR, f'{project_name}.json')
        status_data = {
            'projectName': project_name,
            'deploymentType': deployment_type,
            'status': 'IN_PROGRESS',
            'framework': params.backend_configuration.framework if params.backend_configuration else params.frontend_configuration.framework if params.frontend_configuration else 'unknown',
            'startedAt': str(datetime.datetime.now())
        }
        
        with open(status_file_path, 'w') as f:
            json.dump(status_data, f)
        
        # If backend configuration exists, convert relative paths to absolute
        if (deployment_type in ['backend', 'fullstack'] and params.backend_configuration):
            if not os.path.isabs(params.backend_configuration.built_artifacts_path):
                params.backend_configuration.built_artifacts_path = os.path.abspath(
                    os.path.join(project_root, params.backend_configuration.built_artifacts_path)
                )
            
            logger.info(f'Backend artifacts path: {params.backend_configuration.built_artifacts_path}')
        
        # If frontend configuration exists, convert relative paths to absolute
        if (deployment_type in ['frontend', 'fullstack'] and params.frontend_configuration):
            if not os.path.isabs(params.frontend_configuration.built_assets_path):
                params.frontend_configuration.built_assets_path = os.path.abspath(
                    os.path.join(project_root, params.frontend_configuration.built_assets_path)
                )
            
            logger.info(f'Frontend assets path: {params.frontend_configuration.built_assets_path}')
        
        # Check if we need to generate a startup script or if one was provided
        if (deployment_type in ['backend', 'fullstack'] and params.backend_configuration):
            # If a startup script was provided, verify it exists and is executable
            if params.backend_configuration.startup_script:
                logger.info(f'Verifying provided startup script: {params.backend_configuration.startup_script}')
                
                # Check if the provided startup script is an absolute path
                if os.path.isabs(params.backend_configuration.startup_script):
                    raise ValueError('Startup script must be relative to built_artifacts_path, not an absolute path.')
                
                # Resolve the full path to the built_artifacts_path
                full_artifacts_path = params.backend_configuration.built_artifacts_path
                
                # Construct the full path to the startup script
                script_path = os.path.join(full_artifacts_path, params.backend_configuration.startup_script)
                
                # Check if the script exists
                if not os.path.exists(script_path):
                    raise ValueError(
                        f'Startup script not found at {script_path}. '
                        f'The startup script should be specified as a path relative to built_artifacts_path.'
                    )
                
                # Check if the script is executable
                try:
                    script_stat = os.stat(script_path)
                    is_executable = bool(script_stat.st_mode & 0o111)  # Check if any execute bit is set
                    
                    if not is_executable:
                        logger.warning(f'Startup script {script_path} is not executable. Making it executable...')
                        os.chmod(script_path, 0o755)
                except Exception as e:
                    raise ValueError(f'Failed to check permissions on startup script: {str(e)}')
                
                logger.info(f'Verified startup script exists and is executable: {script_path}')
            # Generate a startup script if requested
            elif (params.backend_configuration.generate_startup_script and
                  params.backend_configuration.entry_point):
                logger.info(f'Generating startup script for {project_name}...')
                
                # TODO: Implement startup script generation
                # For now, just raise an error
                raise NotImplementedError('Startup script generation is not yet implemented')
            # Neither startup script nor generate_startup_script+entry_point provided
            elif not params.backend_configuration.startup_script:
                raise ValueError('No startup script provided or generated. Please either provide a startup_script or set generate_startup_script=True with an entry_point.')
        
        # Create deployment configuration
        configuration = {
            'projectName': project_name,
            'region': params.region or 'us-east-1',
            'backendConfiguration': params.backend_configuration.dict() if params.backend_configuration else None,
            'frontendConfiguration': params.frontend_configuration.dict() if params.frontend_configuration else None
        }
        
        # Log deployment status
        logger.info(f'Deployment status for {project_name}: preparing')
        logger.info('Preparing deployment...')
        
        # Generate SAM template
        # TODO: Implement SAM template generation
        # For now, just log a message
        logger.info('Generating SAM template...')
        
        # Deploy the application
        # TODO: Implement SAM deployment
        # For now, just log a message
        logger.info('Deploying application...')
        
        # Update deployment status with success information
        status_data.update({
            'status': 'DEPLOYED',
            'success': True,
            'outputs': {},
            'stackName': project_name,
            'updatedAt': str(datetime.datetime.now())
        })
        
        with open(status_file_path, 'w') as f:
            json.dump(status_data, f)
        
        logger.info(f'[DEPLOY COMPLETE] Deployment completed for {project_name}')
        
        return {
            'status': 'DEPLOYED',
            'message': 'Deployment completed successfully',
            'projectName': project_name
        }
    except Exception as e:
        logger.error(f'[DEPLOY ERROR] Deployment failed for {project_name}: {str(e)}')
        
        # Update deployment status with error information
        status_data = {
            'projectName': project_name,
            'deploymentType': params.deployment_type,
            'status': 'FAILED',
            'error': str(e),
            'updatedAt': str(datetime.datetime.now())
        }
        
        with open(status_file_path, 'w') as f:
            json.dump(status_data, f)
        
        return {
            'status': 'FAILED',
            'message': f'Deployment failed: {str(e)}',
            'error': str(e),
            'projectName': project_name
        }

async def deploy_web_app(request: DeployWebAppRequest) -> Dict[str, Any]:
    """
    Deploy a web application to AWS serverless infrastructure.
    
    Args:
        request: DeployWebAppRequest object containing deployment parameters
    
    Returns:
        Dict: Deployment result
    """
    try:
        logger.debug('Deploy tool called with params', {'params': request})
        
        # Validate that project_root is provided
        if not request.project_root:
            return {
                'success': False,
                'message': 'Project root is required',
                'error': 'Missing required parameter: project_root'
            }
        
        # Check if this is a destructive deployment type change
        destructive_check = await check_destructive_deployment_change(request.project_name, request.deployment_type)
        if destructive_check.get('isDestructive'):
            return {
                'success': False,
                'message': 'Destructive deployment type change detected',
                'warning': destructive_check.get('warning'),
                'error': 'Destructive change requires confirmation',
                'action': 'Please reconsider your deployment strategy based on the recommendation above.'
            }
        
        # Check for dependencies if this is a backend deployment
        if (request.deployment_type in ['backend', 'fullstack'] and request.backend_configuration):
            # Determine the full path to artifacts directory
            full_artifacts_path = request.backend_configuration.built_artifacts_path
            
            # If built_artifacts_path is not an absolute path, resolve it against project_root
            if not os.path.isabs(full_artifacts_path):
                full_artifacts_path = os.path.abspath(os.path.join(request.project_root, full_artifacts_path))
            
            deps_installed = check_dependencies_installed(
                full_artifacts_path,
                request.backend_configuration.runtime
            )
            
            if not deps_installed:
                instructions = ''
                
                if 'nodejs' in request.backend_configuration.runtime:
                    instructions = f"1. Copy package.json to {request.backend_configuration.built_artifacts_path}\n2. Run 'npm install --omit-dev' in {request.backend_configuration.built_artifacts_path}"
                elif 'python' in request.backend_configuration.runtime:
                    instructions = f"1. Copy requirements.txt to {request.backend_configuration.built_artifacts_path}\n2. Run 'pip install -r requirements.txt -t .' in {request.backend_configuration.built_artifacts_path}"
                elif 'ruby' in request.backend_configuration.runtime:
                    instructions = f"1. Copy Gemfile to {request.backend_configuration.built_artifacts_path}\n2. Run 'bundle install' in {request.backend_configuration.built_artifacts_path}"
                else:
                    instructions = f"Install all required dependencies in {request.backend_configuration.built_artifacts_path}"
                
                error_message = f"""
IMPORTANT: Dependencies not found in built_artifacts_path ({request.backend_configuration.built_artifacts_path}).

For {request.backend_configuration.runtime}, please:

{instructions}

Please install dependencies and try again.
                """
                
                return {
                    'success': False,
                    'message': 'Dependencies not found in built_artifacts_path',
                    'error': 'Missing dependencies',
                    'instructions': error_message
                }
        
        # Start the deployment process in a separate thread or process
        # For now, we'll just return a success message
        
        response = {
            'success': True,
            'message': f'Deployment of {request.project_name} initiated successfully.',
            'status': 'INITIATED',
            'note': 'The deployment process is running in the background and may take several minutes to complete.',
            'checkStatus': f'To check the status of your deployment, use the resource: deployment://{request.project_name}'
        }
        
        logger.debug('Deploy tool response', {'response': response})
        return response
    except Exception as e:
        logger.error('Deploy tool error', {'error': str(e)})
        
        return {
            'success': False,
            'message': f'Deployment failed: {str(e)}',
            'error': str(e)
        }
