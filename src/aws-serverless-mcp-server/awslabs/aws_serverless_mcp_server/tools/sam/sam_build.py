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
from typing import Any, Dict, Optional


class SamBuildTool:
    """Tool to build AWS Serverless Application Model (SAM) projects using the SAM CLI."""

    def __init__(self, mcp: FastMCP):
        """Initialize the SAM build tool."""
        mcp.tool(name='sam_build')(self.handle_sam_build)

    async def handle_sam_build(
        self,
        ctx: Context,
        project_directory: str = Field(
            description='Absolute path to directory containing the SAM project'
        ),
        template_file: Optional[str] = Field(
            default=None,
            description='Absolute path to the template file (defaults to template.yaml)',
        ),
        base_dir: Optional[str] = Field(
            default=None,
            description="""Resolve relative paths to function's source code with respect to this folder.
             Use this option if you want to change how relative paths to source code folders are resolved.
             By default, relative paths are resolved with respect to the AWS SAM template's location.""",
        ),
        build_dir: Optional[str] = Field(
            default=None,
            description="""The absolute path to a directory where the built artifacts are stored
                This directory and all of its content are removed with this option""",
        ),
        use_container: bool = Field(
            default=False,
            description="""Use a Lambda-like container to build the function. Use this option if your function requires a specific
                runtime environment or dependencies that are not available on the local machine. Docker must be installed""",
        ),
        no_use_container: bool = Field(
            default=False,
            description="""Run build in local machine instead of Docker container.""",
        ),
        container_env_vars: Optional[Dict[str, str]] = Field(
            default=None,
            description="""Environment variables to pass to the build container.
                Each instance takes a key-value pair, where the key is the resource and environment variable, and the
                value is the environment variable's value.
                For example: --container-env-var Function1.GITHUB_TOKEN=TOKEN1 --container-env-var Function2.GITHUB_TOKEN=TOKEN2.""",
        ),
        container_env_var_file: Optional[str] = Field(
            default=None,
            description="""Absolute path to a JSON file containing container environment variables. You can provide a single environment variable that applies to all serverless resources,
                or different environment variables for each resource.
                For example, for all resources:
                {
                    "Parameters": {
                        "GITHUB_TOKEN": "TOKEN_GLOBAL"
                    }
                }
                For individual resources:
                {
                    "MyFunction1": {
                        "GITHUB_TOKEN": "TOKEN1"
                    },
                    "MyFunction2": {
                        "GITHUB_TOKEN": "TOKEN2"
                    }
                }
                """,
        ),
        build_image: Optional[str] = Field(
            default=None,
            description="""The URI of the container image that you want to pull for the build. By default, AWS SAM pulls the
             container image from Amazon ECR Public. Use this option to pull the image from another location""",
        ),
        debug: bool = Field(default=False, description='Turn on debug logging'),
        manifest: Optional[str] = Field(
            default=None,
            description="""Absolute path to a custom dependency manifest file (e.g., package.json) instead of the default.
             For example: 'ParameterKey=KeyPairName, ParameterValue=MyKey ParameterKey=InstanceType, ParameterValue=t1.micro.""",
        ),
        parameter_overrides: Optional[str] = Field(
            default=None,
            description="""CloudFormation parameter overrides encoded as key-value pairs.
                For example: 'ParameterKey=KeyPairName, ParameterValue=MyKey ParameterKey=InstanceType, ParameterValue=t1.micro""",
        ),
        region: Optional[str] = Field(
            default=None, description='AWS Region to deploy to (e.g., us-east-1)'
        ),
        save_params: bool = Field(
            default=False, description='Save parameters to the SAM configuration file'
        ),
        profile: Optional[str] = Field(default=None, description='AWS profile to use'),
    ) -> dict[str, Any]:
        """Builds a serverless application using AWS SAM (Serverless Application Model) CLI.

        Requirements:
        - AWS SAM CLI MUST be installed and configured in your environment
        - An application MUST already be initialized with 'sam_init' tool to create sam project structure.

        This command compiles your Lambda function and layer code, creates deployment artifacts, and prepares your application for deployment and local testing.
        It creates a .aws-sam directory that structures your application in a format and location that sam local and sam deploy require. For Zip
        functions, a .zip file archive is created, which contains your application code and its dependencies. For Image functions, a container image is created,
        which includes the base operating system, runtime, and extensions, in addition to your application code and its dependencies.

        Usage tips:
        - Don’t edit any code under the .aws-sam/build directory. Instead, update your original source code in
        your project folder and run sam build to update the .aws-sam/build directory.
        - When you modify your original files, run sam build to update the .aws-sam/build directory.
        - You may want the AWS SAM CLI to reference your project’s original root directory
        instead of the .aws-sam directory, such as when developing and testing with sam local. Delete the .aws-sam directory
        or the AWS SAM template in the .aws-sam directory to have the AWS SAM CLI recognize your original project directory as
        the root project directory. When ready, run sam build again to create the .aws-sam directory.
        - When you run sam build, the .aws-sam/build directory gets overwritten each time.
        The .aws-sam directory does not. If you want to store files, such as logs, store them in .aws-sam to
        prevent them from being overwritten.

        Returns:
            Dict: SAM init command output
        """
        await ctx.info(f'Building SAM project in {project_directory}')
        cmd = ['sam', 'build']

        if base_dir:
            cmd.extend(['--base-dir', base_dir])
        if build_dir:
            cmd.extend(['--build-dir', build_dir])
        if build_image:
            cmd.extend(['--build-image', build_image])
        if container_env_var_file:
            cmd.extend(['--container-env-var-file', container_env_var_file])
        if container_env_vars:
            for key, value in container_env_vars.items():
                cmd.extend(['--container-env-var', f'{key}={value}'])
        if debug:
            cmd.append('--debug')
        if manifest:
            cmd.extend(['--manifest', manifest])
        if no_use_container:
            cmd.append('--no-use-container')
        if use_container:
            cmd.append('--use-container')
        if parameter_overrides:
            cmd.extend(['--parameter-overrides', parameter_overrides])
        if region:
            cmd.extend(['--region', region])
        if save_params:
            cmd.append('--save-params')
        if template_file:
            cmd.extend(['--template-file', template_file])
        if profile:
            cmd.extend(['--profile', profile])

        try:
            stdout, stderr = await run_command(cmd, cwd=project_directory)
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
