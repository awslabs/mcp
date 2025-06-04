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

"""Deployment Service for AWS Serverless MCP Server.

Handles the deployment of web applications to AWS serverless infrastructure.
"""

import asyncio
import os
from awslabs.aws_serverless_mcp_server.models import DeployWebAppRequest
from awslabs.aws_serverless_mcp_server.template.renderer import render_template
from awslabs.aws_serverless_mcp_server.tools.webapps.utils.frontend_uploader import (
    upload_frontend_assets,
)
from awslabs.aws_serverless_mcp_server.tools.webapps.utils.startup_script_generator import (
    EntryPointNotFoundError,
    generate_startup_script,
)
from awslabs.aws_serverless_mcp_server.utils.aws_client_helper import get_aws_client
from awslabs.aws_serverless_mcp_server.utils.deployment_manager import (
    DeploymentStatus,
    get_deployment_status,
    initialize_deployment_status,
    store_deployment_error,
    store_deployment_metadata,
)
from awslabs.aws_serverless_mcp_server.utils.process import run_command
from botocore.exceptions import ClientError
from datetime import datetime
from loguru import logger
from typing import Any, Dict, Optional


async def deploy_application(request: DeployWebAppRequest) -> Dict[str, Any]:
    """Deploy a web application to AWS serverless infrastructure.

    Args:
        request: Deployment options

    Returns:
        Dict: Deployment result
    """
    deployment_type = request.deployment_type
    project_name = request.project_name
    project_root = request.project_root

    logger.info(f'[DEPLOY START] Starting deployment process for {project_name}')

    # Update deployment status
    framework = 'unknown'
    if request.backend_configuration and request.backend_configuration.framework:
        framework = request.backend_configuration.framework
    elif request.frontend_configuration and request.frontend_configuration.framework:
        framework = request.frontend_configuration.framework

    await initialize_deployment_status(project_name, deployment_type, framework, request.region)

    logger.info(f'Deployment type: {deployment_type}')
    logger.info(f'Project root: {project_root}')

    try:
        # If backend configuration exists, convert relative paths to absolute
        if deployment_type in ['backend', 'fullstack'] and request.backend_configuration:
            backend_config = request.backend_configuration
            if not os.path.isabs(backend_config.built_artifacts_path):
                backend_config.built_artifacts_path = os.path.join(
                    project_root, backend_config.built_artifacts_path
                )

            logger.info(f'Backend artifacts path: {backend_config.built_artifacts_path}')

        # If frontend configuration exists, convert relative paths to absolute
        if deployment_type in ['frontend', 'fullstack'] and request.frontend_configuration:
            frontend_config = request.frontend_configuration
            if not os.path.isabs(frontend_config.built_assets_path):
                frontend_config.built_assets_path = os.path.join(
                    project_root, frontend_config.built_assets_path
                )

            logger.info(f'Frontend assets path: {frontend_config.built_assets_path}')

        # Check if we need to generate a startup script or if one was provided
        if deployment_type in ['backend', 'fullstack'] and request.backend_configuration:
            backend_config = request.backend_configuration

            # If a startup script was provided, verify it exists and is executable
            if backend_config.startup_script:
                logger.info(f'Verifying provided startup script: {backend_config.startup_script}')

                # Check if the provided startup script is an absolute path
                if os.path.isabs(backend_config.startup_script):
                    raise Exception(
                        'Startup script must be relative to built_artifacts_path, not an absolute path. Please provide a path relative to the built_artifacts_path directory.'
                    )

                # Resolve the full path to the built_artifacts_path
                full_artifacts_path = (
                    os.path.join(project_root, backend_config.built_artifacts_path)
                    if not os.path.isabs(backend_config.built_artifacts_path)
                    else backend_config.built_artifacts_path
                )

                # Construct the full path to the startup script
                script_path = os.path.join(full_artifacts_path, backend_config.startup_script)

                # Check if the script exists
                if not os.path.exists(script_path):
                    raise Exception(
                        f'Startup script not found at {script_path}. '
                        + 'The startup script should be specified as a path relative to built_artifacts_path. '
                        + f"For example, if your script is at '{full_artifacts_path}/bootstrap', "
                        + "you should set startup_script to 'bootstrap'."
                    )

                # Check if the script is executable
                try:
                    stats = os.stat(script_path)
                    is_executable = bool(stats.st_mode & 0o111)  # Check if any execute bit is set

                    if not is_executable:
                        logger.warning(
                            f'Startup script {script_path} is not executable. Making it executable...'
                        )
                        #  Ignore Bandit error as startup scripts should be executable and does not container sensitive data
                        os.chmod(script_path, 0o755)  # nosec
                except Exception as e:
                    raise Exception(f'Failed to check permissions on startup script: {str(e)}')

                logger.info(f'Verified startup script exists and is executable: {script_path}')
            # Generate a startup script if requested
            elif backend_config.generate_startup_script and backend_config.entry_point:
                logger.info(f'Generating startup script for {project_name}...')

                try:
                    startup_script_name = await generate_startup_script(
                        runtime=backend_config.runtime,
                        entry_point=backend_config.entry_point,
                        built_artifacts_path=backend_config.built_artifacts_path,
                        startup_script_name=backend_config.startup_script,
                        additional_env=backend_config.environment,
                    )

                    # Update the configuration with the generated script name
                    backend_config.startup_script = startup_script_name

                    logger.info(f'Startup script generated: {startup_script_name}')
                except EntryPointNotFoundError as e:
                    # Provide a more helpful error message for entry point not found
                    raise Exception(
                        f'Failed to generate startup script: {str(e)}. Please check that your entry point file exists in the built artifacts directory and the path is correct.'
                    )
                except Exception as e:
                    raise e
            # Neither startup script nor generate_startup_script+entry_point provided
            elif not backend_config.startup_script:
                raise Exception(
                    'No startup script provided or generated. Please either provide a startup_script or set generate_startup_script=true with an entry_point.'
                )

        # Log deployment status
        logger.info(f'Deployment status for {project_name}: preparing')
        logger.info('Preparing deployment...')

        # Generate SAM template
        await generate_sam_template(project_root, request)

        # Deploy the application
        deploy_result = await build_and_deploy_application(project_root, request)

        # Upload frontend assets for frontend or fullstack deployments
        if (
            deployment_type in ['frontend', 'fullstack']
            and request.frontend_configuration
            and request.frontend_configuration.built_assets_path
        ):
            logger.info('Uploading frontend assets...')
            await upload_frontend_assets(request, deploy_result)

        # Update deployment status with success information
        await store_deployment_metadata(
            project_name,
            {
                'status': DeploymentStatus.DEPLOYED,
                'success': True,
                'outputs': deploy_result.get('outputs', {}),
                'stackName': deploy_result.get('stackName'),
                'updatedAt': datetime.now().isoformat(),
            },
        )

        # Get deployment result
        result = await get_deployment_status(project_name)

        logger.info(f'[DEPLOY COMPLETE] Deployment completed for {project_name}')
        return result
    except Exception as e:
        logger.error(f'[DEPLOY ERROR] Deployment failed for {project_name}: {str(e)}')

        # Log deployment error
        logger.error(f'Deployment process failed: {str(e)}')

        # Update deployment status with error information
        await store_deployment_error(project_name, str(e))

        return {
            'status': DeploymentStatus.FAILED,
            'message': f'Deployment failed: {str(e)}',
            'error': str(e),
            'project_name': project_name,
        }


async def generate_sam_template(
    project_root: str,
    configuration: DeployWebAppRequest,
) -> None:
    """Generate a SAM template for the deployment using the template renderer.

    Args:
        project_root: Project root directory
        configuration: Deployment configuration
    """
    logger.info('Generating SAM template...')

    try:
        # Use the renderer to generate the SAM template
        rendered_template = await render_template(configuration)

        # Write the template to the project root
        template_path = os.path.join(project_root, 'template.yaml')
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(rendered_template)

        logger.info(f'SAM template generated at {template_path}')
    except Exception as e:
        logger.error(f'Failed to generate SAM template: {str(e)}')
        raise Exception(f'Failed to generate SAM template: {str(e)}')


async def build_and_deploy_application(
    project_root: str,
    configuration: DeployWebAppRequest,
) -> Dict[str, Any]:
    """Build and deploy the application using SAM CLI.

    Args:
        project_root: Project root directory
        configuration: Deployment configuration
        deployment_type: Deployment type

    Returns:
        Dict: Deployment result with outputs
    """
    logger.info('Deploying application...')

    stack_name = configuration.project_name

    try:
        # Create samconfig.toml file
        sam_config_path = os.path.join(project_root, 'samconfig.toml')
        sam_config_content = f"""version = 0.1
    [default]
    [default.deploy]
    [default.deploy.parameters]
    stack_name = "{stack_name}"
    resolve_s3 = true
    confirm_changeset = false
    capabilities = "CAPABILITY_IAM"
    """
        if configuration.region:
            sam_config_content += f'region = "{configuration.region}"\n'
        with open(sam_config_path, 'w', encoding='utf-8') as f:
            f.write(sam_config_content)
        logger.debug(f'Created samconfig.toml at {sam_config_path}')

        # Actually deploy the SAM application using run_command
        logger.info(f'Deploying SAM application with stack name: {stack_name}...')

        sam_deploy_cmd = [
            'sam',
            'deploy',
            '--stack-name',
            stack_name,
            '--capabilities',
            'CAPABILITY_IAM',
            '--no-confirm-changeset',
            '--no-fail-on-empty-changeset',
        ]
        if configuration.region:
            sam_deploy_cmd.extend(['--region', configuration.region])
        stdout, stderr = await run_command(sam_deploy_cmd, cwd=project_root)

        logger.info('SAM deployment completed successfully')
        logger.debug(f'SAM deploy output: {stdout.decode()}')

        # Get stack outputs (replace with real implementation if needed)
        outputs = await get_stack_outputs(stack_name, configuration.region)

        logger.info('SAM deployment completed successfully')

        return {'stackName': stack_name, 'outputs': outputs}
    except Exception as e:
        logger.error(f'SAM deployment failed: {str(e)}')
        raise Exception(f'Failed to deploy application: {str(e)}')


async def get_stack_outputs(stack_name: str, region: Optional[str] = None) -> Dict[str, str]:
    """Get CloudFormation stack outputs.

    Args:
        stack_name: Stack name
        region: AWS region (optional)

    Returns:
        Dict: Stack outputs
    """
    try:

        def fetch_outputs():
            cfn = get_aws_client('cloudformation', region)
            try:
                response = cfn.describe_stacks(StackName=stack_name)
                stacks = response.get('Stacks', [])
                if not stacks:
                    logger.error(f'No stack found with name {stack_name}')
                    return {}
                outputs = stacks[0].get('Outputs', [])
                return {o['OutputKey']: o['OutputValue'] for o in outputs}
            except ClientError as e:
                logger.error(f'Failed to get stack outputs: {str(e)}')
                return {}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fetch_outputs)
    except Exception as e:
        logger.error(f'Failed to get stack outputs: {str(e)}')
        return {}
