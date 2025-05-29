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

from awslabs.aws_serverless_mcp_server.models import SamDeployRequest
from awslabs.aws_serverless_mcp_server.utils.process import run_command
from loguru import logger


async def handle_sam_deploy(request: SamDeployRequest):
    """Execute the AWS SAM deploy command with the provided parameters.

    Args:
        request: SamDeployRequest object containing all deploy parameters
    """
    cmd = ['sam', 'deploy']

    cmd.extend(['--stack-name', request.application_name])
    cmd.append('--no-confirm-changeset')

    if request.template_file:
        cmd.extend(['--template-file', request.template_file])
    if request.s3_bucket:
        cmd.extend(['--s3-bucket', request.s3_bucket])
    if request.s3_prefix:
        cmd.extend(['--s3-prefix', request.s3_prefix])
    if request.region:
        cmd.extend(['--region', request.region])
    if request.profile:
        cmd.extend(['--profile', request.profile])
    if request.parameter_overrides:
        cmd.extend(['--parameter-overrides', request.parameter_overrides])
    if request.capabilities:
        cmd.extend(['--capabilities'])
        for capability in request.capabilities:
            cmd.append(capability)
    if request.config_file:
        cmd.extend(['--config-file', request.config_file])
    if request.config_env:
        cmd.extend(['--config-env', request.config_env])
    if request.metadata:
        cmd.extend(['--metadata'])
        for key, value in request.metadata.items():
            cmd.append(f'{key}={value}')
    if request.tags:
        cmd.extend(['--tags'])
        for key, value in request.tags.items():
            cmd.append(f'{key}={value}')
    if request.resolve_s3:
        cmd.append('--resolve-s3')
    if request.debug:
        cmd.append('--debug')

    try:
        stdout, stderr = await run_command(cmd, cwd=request.project_directory)
        return {
            'success': True,
            'message': 'SAM project deployed successfully',
            'output': stdout.decode(),
        }
    except Exception as e:
        error_msg = getattr(e, 'stderr', str(e))
        logger.error(f'SAM deploy failed with error: {error_msg}')
        return {
            'success': False,
            'message': f'Failed to deploy SAM project: {error_msg}',
            'error': str(e),
        }
