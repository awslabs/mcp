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

from awslabs.aws_serverless_mcp_server.models import SamInitRequest
from awslabs.aws_serverless_mcp_server.utils.process import run_command
from loguru import logger
from typing import Any, Dict


async def handle_sam_init(request: SamInitRequest) -> Dict[str, Any]:
    """Initialize a serverless application with an AWS SAM template.

    This tool creates a new SAM project that consists of:
    - An AWS SAM template to define your infrastructure code
    - A folder structure that organizes your application
    - Configuration for your AWS Lambda functions

    Args:
        request (SamInitRequest): Object containing init parameters

    Returns:
    -------
    Dict[str, Any]
        Result of the initialization
    """
    try:
        # Initialize command list
        cmd = ['sam', 'init']

        # Add required parameters
        cmd.extend(['--name', request.project_name])
        cmd.extend(['--runtime', request.runtime])
        cmd.extend(['--dependency-manager', request.dependency_manager])
        # Set output directory
        cmd.extend(['--output-dir', request.project_directory])
        # Add --no-interactive to avoid prompts
        cmd.append('--no-interactive')

        # Add optional parameters if provided
        if request.application_insights:
            cmd.append('--application-insights')

        if request.no_application_insights:
            cmd.append('--no-application-insights')

        if request.application_template:
            cmd.extend(['--app-template', request.application_template])

        if request.architecture:
            cmd.extend(['--architecture', request.architecture])

        if request.base_image:
            cmd.extend(['--base-image', request.base_image])

        if request.config_env:
            cmd.extend(['--config-env', request.config_env])

        if request.config_file:
            cmd.extend(['--config-file', request.config_file])

        if request.debug:
            cmd.append('--debug')

        if request.extra_content:
            cmd.extend(['--extra-context', request.extra_content])

        if request.location:
            cmd.extend(['--location', request.location])

        if request.no_tracing:
            cmd.append('--no-tracing')

        if request.package_type:
            cmd.extend(['--package-type', request.package_type])

        if request.save_params:
            cmd.append('--save-params')

        if request.tracing:
            cmd.append('--tracing')

        if request.no_tracing:
            cmd.append('--no-tracing')

        stdout, stderr = await run_command(cmd, cwd=request.project_directory)
        return {
            'success': True,
            'message': f"Successfully initialized SAM project '{request.project_name}' in {request.project_directory}",
            'output': stdout.decode(),
        }
    except Exception as e:
        error_msg = getattr(e, 'stderr', str(e))
        logger.error(f'SAM init failed with error: {error_msg}')
        return {
            'success': False,
            'message': f'Failed to initialize SAM project: {error_msg}',
            'error': str(e),
        }
