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
from awslabs.aws_serverless_mcp_server.utils.process import run_command
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, Optional


class SamLocalInvokeTool:
    """Tool to locally invoke AWS Lambda functions using the SAM CLI."""

    def __init__(self, mcp: FastMCP):
        """Initialize the SAM local invoke tool."""
        mcp.tool(name='sam_local_invoke_tool')(self.handle_sam_local_invoke)

    async def handle_sam_local_invoke(
        self,
        ctx: Context,
        project_directory: str = Field(
            description='Absolute path to directory containing the SAM project'
        ),
        resource_name: str = Field(description='Name of the Lambda function to invoke locally'),
        template_file: Optional[str] = Field(
            default=None,
            description='Absolute path to the SAM template file (defaults to template.yaml)',
        ),
        event_file: Optional[str] = Field(
            default=None, description='Absolute path to a JSON file containing event data'
        ),
        event_data: Optional[str] = Field(
            default=None,
            description='JSON string containing event data (alternative to event_file)',
        ),
        environment_variables_file: Optional[str] = Field(
            default=None,
            description='Absolute path to a JSON file containing environment variables to pass to the function',
        ),
        docker_network: Optional[str] = Field(
            default=None, description='Docker network to run the Lambda function in'
        ),
        container_env_vars: Optional[Dict[str, str]] = Field(
            default=None, description='Environment variables to pass to the container'
        ),
        parameter: Optional[Dict[str, str]] = Field(
            default=None, description='Override parameters from the template file'
        ),
        log_file: Optional[str] = Field(
            default=None,
            description='Absolute path to a file where the function logs will be written',
        ),
        layer_cache_basedir: Optional[str] = Field(
            default=None, description='Directory where the layers will be cached'
        ),
        region: Optional[str] = Field(
            default=None, description='AWS region to use (e.g., us-east-1)'
        ),
        profile: Optional[str] = Field(default=None, description='AWS profile to use'),
    ) -> Dict[str, Any]:
        """Locally invokes a Lambda function using AWS SAM CLI.

        Requirements:
        - AWS SAM CLI installed and configured in your environment
        - Docker must be installed and running in your environment.

        This command runs your Lambda function locally in a Docker container that simulates the AWS Lambda environment.
        Use this tool to test your Lambda functions before deploying them to AWS. It allows you to test the logic of your function faster.
        Testing locally first reduces the likelihood of identifying issues when testing in the cloud or during deployment,
        which can help you avoid unnecessary costs. Additionally, local testing makes debugging easier to do.

        Returns:
            Dict: Local invoke result and the execution logs
        """
        try:
            await ctx.info(f"Locally invoking resource '{resource_name}' in {project_directory}")
            project_directory = project_directory
            resource_name = resource_name
            template_file = template_file
            event_file = event_file
            event_data = event_data
            environment_variables_file = environment_variables_file
            docker_network = docker_network
            container_env_vars = container_env_vars
            parameter = parameter
            log_file = log_file
            layer_cache_basedir = layer_cache_basedir
            region = region
            profile = profile

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
                stdout, stderr = await run_command(cmd, cwd=project_directory)

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
