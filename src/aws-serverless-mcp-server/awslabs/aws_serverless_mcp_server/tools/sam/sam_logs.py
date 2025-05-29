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

"""SAM logs tool for AWS Serverless MCP Server."""

from awslabs.aws_serverless_mcp_server.models import SamLogsRequest
from awslabs.aws_serverless_mcp_server.utils.process import run_command
from loguru import logger
from typing import Any, Dict


async def handle_sam_logs(request: SamLogsRequest) -> Dict[str, Any]:
    """Fetch logs for AWS Lambda functions deployed through AWS SAM.

    Args:
        request: SamLogsRequest object containing log retrieval parameters

    Returns:
        Dict: Log retrieval result
    """
    try:
        # Build the command arguments
        cmd = ['sam', 'logs']

        if request.resource_name:
            cmd.extend(['--name', request.resource_name])

        if request.config_env:
            cmd.extend(['--config-env', request.config_env])

        if request.config_file:
            cmd.extend(['--config-file', request.config_file])

        if request.cw_log_group:
            cmd.extend(['--cw-log-group'])
            for group in request.cw_log_group:
                cmd.append(group)

        if request.start_time:
            cmd.extend(['--start-time', request.start_time])

        if request.end_time:
            cmd.extend(['--end-time', request.end_time])

        if request.save_params:
            cmd.extend(['--save-params'])

        if request.stack_name:
            cmd.extend(['--stack-name', request.stack_name])

        if request.profile:
            cmd.extend(['--profile', request.profile])

        if request.region:
            cmd.extend(['--region', request.region])

        # Execute the command
        logger.info(f'Executing command: {" ".join(cmd)}')
        stdout, stderr = await run_command(cmd)
        return {
            'success': True,
            'message': f"Successfully fetched logs for resource '{request.resource_name}'",
            'output': stdout.decode(),
        }
    except Exception as e:
        error_message = getattr(e, 'stderr', str(e))
        logger.error(f'Error fetching logs for resource: {error_message}')
        return {
            'success': False,
            'message': f'Failed to fetch logs for resource: {error_message}',
            'error': str(e),
        }
