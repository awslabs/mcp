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

from awslabs.aws_serverless_mcp_server.models import SamBuildRequest
from awslabs.aws_serverless_mcp_server.utils.process import run_command
from loguru import logger


async def handle_sam_build(request: SamBuildRequest):
    """Execute the AWS SAM build command with the provided parameters.

    Args:
        request: SamBuildRequest object containing all build parameters
    """
    cmd = ['sam', 'build']

    if request.base_dir:
        cmd.extend(['--base-dir', request.base_dir])
    if request.build_dir:
        cmd.extend(['--build-dir', request.build_dir])
    if request.build_image:
        cmd.extend(['--build-image', request.build_image])
    if request.container_env_var_file:
        cmd.extend(['--container-env-var-file', request.container_env_var_file])
    if request.container_env_vars:
        for key, value in request.container_env_vars.items():
            cmd.extend(['--container-env-var', f'{key}={value}'])
    if request.debug:
        cmd.append('--debug')
    if request.manifest:
        cmd.extend(['--manifest', request.manifest])
    if request.no_use_container:
        cmd.append('--no-use-container')
    if request.use_container:
        cmd.append('--use-container')
    if request.parameter_overrides:
        cmd.extend(['--parameter-overrides', request.parameter_overrides])
    if request.region:
        cmd.extend(['--region', request.region])
    if request.save_params:
        cmd.append('--save-params')
    if request.template_file:
        cmd.extend(['--template-file', request.template_file])
    if request.profile:
        cmd.extend(['--profile', request.profile])

    try:
        stdout, stderr = await run_command(cmd, cwd=request.project_directory)
        return {
            'success': True,
            'message': 'SAM project built successfully',
            'output': stdout.decode(),
        }
    except Exception as e:
        error_msg = getattr(e, 'stderr', str(e))
        logger.error(f'SAM build failed with error: {error_msg}')
        return {
            'success': False,
            'message': f'Failed to build SAM project: {error_msg}',
            'error': str(e),
        }
