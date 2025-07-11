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

from awslabs.aws_serverless_mcp_server.tools.common.base_tool import BaseTool
from awslabs.aws_serverless_mcp_server.utils.process import run_command
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, Optional


class SamDeleteTool(BaseTool):
    """Tool to delete AWS Serverless Application Model (SAM) applications using the 'sam delete' command."""

    def __init__(self, mcp: FastMCP, allow_write: bool):
        """Initialize the SAM delete tool."""
        super().__init__(allow_write=allow_write)
        mcp.tool(name='sam_delete')(self.handle_sam_delete)
        self.allow_write = allow_write

    async def handle_sam_delete(
        self,
        ctx: Context,
        stack_name: str = Field(description='Name of the CloudFormation stack to delete'),
        project_directory: Optional[str] = Field(
            default=None,
            description='Absolute path to directory containing the SAM project',
        ),
        region: Optional[str] = Field(default=None, description='AWS region where the stack exists'),
        profile: Optional[str] = Field(default=None, description='AWS profile to use'),
        config_file: Optional[str] = Field(
            default=None, description='Absolute path to the SAM configuration file'
        ),
        config_env: Optional[str] = Field(
            default=None,
            description='Environment name specifying default parameter values in the configuration file',
        ),
        s3_bucket: Optional[str] = Field(
            default=None,
            description='S3 bucket containing deployment artifacts to be deleted',
        ),
        s3_prefix: Optional[str] = Field(
            default=None, description='S3 prefix for the artifacts to be deleted'
        ),
        beta_features: Optional[bool] = Field(
            default=None, description='Enable/Disable beta features'
        ),
        debug: bool = Field(default=False, description='Turn on debug logging'),
        save_params: bool = Field(
            default=False, description='Save parameters to the SAM configuration file'
        ),
    ) -> Dict[str, Any]:
        """Deletes a deployed serverless application from AWS Cloud using AWS SAM (Serverless Application Model) CLI.

        Requirements:
        - AWS SAM CLI MUST be installed and configured in your environment
        - The stack must exist in the specified AWS region

        This command deletes a CloudFormation stack that was deployed using SAM. It can also optionally
        delete the S3 artifacts associated with the stack. The only required parameter is stack_name.

        Usage tips:
        - Use the no_prompts parameter to skip confirmation prompts (useful for automation)
        - Specify s3_bucket and s3_prefix to also delete deployment artifacts from S3

        Returns:
            Dict: SAM delete command output
        """
        self.checkToolAccess()

        cmd = ['sam', 'delete']

        cmd.extend(['--stack-name', stack_name])
        
        # Always include --no-prompts to ensure non-interactive behavior
        cmd.append('--no-prompts')

        if region:
            cmd.extend(['--region', region])
        if profile:
            cmd.extend(['--profile', profile])
        if config_file:
            cmd.extend(['--config-file', config_file])
        if config_env:
            cmd.extend(['--config-env', config_env])
        if s3_bucket:
            cmd.extend(['--s3-bucket', s3_bucket])
        if s3_prefix:
            cmd.extend(['--s3-prefix', s3_prefix])
        if beta_features is not None:
            if beta_features:
                cmd.append('--beta-features')
            else:
                cmd.append('--no-beta-features')
        if debug:
            cmd.append('--debug')
        if save_params:
            cmd.append('--save-params')

        try:
            stdout, stderr = await run_command(cmd, cwd=project_directory)
            return {
                'success': True,
                'message': 'SAM project deleted successfully',
                'output': stdout.decode(),
            }
        except Exception as e:
            error_msg = getattr(e, 'stderr', str(e))
            logger.error(f'SAM delete failed with error: {error_msg}')
            return {
                'success': False,
                'message': f'Failed to delete SAM project: {error_msg}',
                'error': str(e),
            }
