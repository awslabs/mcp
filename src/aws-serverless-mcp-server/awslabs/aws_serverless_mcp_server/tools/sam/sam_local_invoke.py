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

"""SAM local invoke tool for AWS Serverless MCP Server."""

import json
import os
import tempfile
from awslabs.aws_serverless_mcp_server.models import SamLocalInvokeRequest
from awslabs.aws_serverless_mcp_server.utils.process import run_command
from loguru import logger
from typing import Any, Dict


async def handle_sam_local_invoke(request: SamLocalInvokeRequest) -> Dict[str, Any]:
    """Locally invokes a Lambda function using AWS SAM CLI.

    Args:
        request: SamLocalInvokeRequest object containing local invoke parameters

    Returns:
        Dict: Local invoke result
    """
    try:
        project_directory = request.project_directory
        resource_name = request.resource_name
        template_file = request.template_file
        event_file = request.event_file
        event_data = request.event_data
        environment_variables_file = request.environment_variables_file
        docker_network = request.docker_network
        container_env_vars = request.container_env_vars
        parameter = request.parameter
        log_file = request.log_file
        layer_cache_basedir = request.layer_cache_basedir
        region = request.region
        profile = request.profile

        # Create a temporary event file if eventData is provided
        temp_event_file = None
        if event_data and not event_file:
            fd, temp_event_file = tempfile.mkstemp(
                suffix='.json', prefix='.temp-event-', dir=project_directory
            )
            with os.fdopen(fd, 'w') as f:
                f.write(event_data)
            event_file = temp_event_file

        try:
            # Build the command arguments
            cmd = ['sam', 'local', 'invoke', resource_name]

            if template_file:
                cmd.extend(['--template', template_file])

            if event_file:
                cmd.extend(['--event', event_file])

            if environment_variables_file:
                cmd.extend(['--env-vars', environment_variables_file])

            if docker_network:
                cmd.extend(['--docker-network', docker_network])

            if container_env_vars:
                cmd.extend(['--container-env-vars'])
                for key, value in container_env_vars.items():
                    cmd.append(f'{key}={value}')

            if parameter:
                cmd.extend(['--parameter-overrides'])
                for key, value in parameter.items():
                    cmd.append(f'ParameterKey={key},ParameterValue={value}')

            if log_file:
                cmd.extend(['--log-file', log_file])

            if layer_cache_basedir:
                cmd.extend(['--layer-cache-basedir', layer_cache_basedir])

            if region:
                cmd.extend(['--region', region])

            if profile:
                cmd.extend(['--profile', profile])

            # Execute the command
            logger.info(f'Executing command: {" ".join(cmd)}')
            stdout, stderr = await run_command(cmd, cwd=request.project_directory)

            # Parse the result to extract function output and logs
            function_output = stdout.decode()
            try:
                function_output = json.loads(function_output)
            except json.JSONDecodeError:
                # If not valid JSON, keep as string
                pass

            return {
                'success': True,
                'message': f"Successfully invoked resource '{resource_name}' locally.",
                'logs': stderr.decode(),
                'function_output': function_output,
            }
        finally:
            # Clean up temporary event file if created
            if temp_event_file and os.path.exists(temp_event_file):
                os.unlink(temp_event_file)
    except Exception as e:
        logger.error(f'Error in sam_local_invoke: {str(e)}')
        return {
            'success': False,
            'message': f'Failed to invoke resource locally: {str(e)}',
            'error': str(e),
        }
