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
from awslabs.aws_serverless_mcp_server.utils.process import run_command
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, List, Literal, Optional


class SamDeployTool:
    """Tool to deploy AWS Serverless Application Model (SAM) applications using the 'sam deploy' command."""

    def __init__(self, mcp: FastMCP, allow_write: bool):
        """Initialize the SAM deploy tool."""
        mcp.tool(name='sam_deploy_tool')(self.handle_sam_deploy)
        self.allow_write = allow_write

    async def handle_sam_deploy(
        self,
        ctx: Context,
        application_name: str = Field(description='Name of the application to be deployed'),
        project_directory: str = Field(
            description='Absolute path to directory containing the SAM project (defaults to current directory)'
        ),
        template_file: Optional[str] = Field(
            default=None,
            description='Absolute path to the template file (defaults to template.yaml)',
        ),
        s3_bucket: Optional[str] = Field(
            default=None, description='S3 bucket to deploy artifacts to'
        ),
        s3_prefix: Optional[str] = Field(default=None, description='S3 prefix for the artifacts'),
        region: Optional[str] = Field(default=None, description='AWS region to deploy to'),
        profile: Optional[str] = Field(default=None, description='AWS profile to use'),
        parameter_overrides: Optional[str] = Field(
            default=None,
            description='CloudFormation parameter overrides encoded as key-value pairs',
        ),
        capabilities: Optional[
            List[Literal['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND']]
        ] = Field(
            default=['CAPABILITY_IAM'], description='IAM capabilities required for the deployment'
        ),
        config_file: Optional[str] = Field(
            default=None, description='Absolute path to the SAM configuration file'
        ),
        config_env: Optional[str] = Field(
            default=None,
            description='Environment name specifying default parameter values in the configuration file',
        ),
        metadata: Optional[Dict[str, str]] = Field(
            default=None, description='Metadata to include with the stack'
        ),
        tags: Optional[Dict[str, str]] = Field(
            default=None, description='Tags to apply to the stack'
        ),
        resolve_s3: bool = Field(
            default=False, description='Automatically create an S3 bucket for deployment artifacts'
        ),
        debug: bool = Field(default=False, description='Turn on debug logging'),
    ) -> Dict[str, Any]:
        """Deploys a serverless application using AWS SAM (Serverless Application Model) CLI.

        Requirements:
        - AWS SAM CLI installed and configured in your environment
        - SAM project is initialized using sam_init tool and built with sam_build.

        This command deploys your SAM application's build artifacts located in the .aws-sam directory
        to AWS Cloud using AWS CloudFormation. When you make changes to your application's original files,
        run sam build to update the .aws-sam directory before deploying.

        Returns:
            Dict: SAM deploy command output
        """
        if not self.allow_write:
            return {
                'success': False,
                'error': 'Write operations are not allowed. Set --allow-write flag to true to enable write operations.',
            }

        cmd = ['sam', 'deploy']

        cmd.extend(['--stack-name', application_name])
        cmd.append('--no-confirm-changeset')

        if template_file:
            cmd.extend(['--template-file', template_file])
        if s3_bucket:
            cmd.extend(['--s3-bucket', s3_bucket])
        if s3_prefix:
            cmd.extend(['--s3-prefix', s3_prefix])
        if region:
            cmd.extend(['--region', region])
        if profile:
            cmd.extend(['--profile', profile])
        if parameter_overrides:
            cmd.extend(['--parameter-overrides', parameter_overrides])
        if capabilities:
            cmd.extend(['--capabilities'])
            for capability in capabilities:
                cmd.append(capability)
        if config_file:
            cmd.extend(['--config-file', config_file])
        if config_env:
            cmd.extend(['--config-env', config_env])
        if metadata:
            cmd.extend(['--metadata'])
            for key, value in metadata.items():
                cmd.append(f'{key}={value}')
        if tags:
            cmd.extend(['--tags'])
            for key, value in tags.items():
                cmd.append(f'{key}={value}')
        if resolve_s3:
            cmd.append('--resolve-s3')
        if debug:
            cmd.append('--debug')

        try:
            stdout, stderr = await run_command(cmd, cwd=project_directory)
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
