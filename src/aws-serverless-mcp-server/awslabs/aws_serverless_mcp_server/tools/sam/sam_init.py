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
from typing import Any, Literal, Optional


class SamInitTool:
    """Tool to initialize AWS Serverless Application Model (SAM) projects using the SAM CLI."""

    def __init__(self, mcp: FastMCP):
        """Initialize the SAM init tool."""
        mcp.tool(name='sam_init')(self.handle_sam_init)

    async def handle_sam_init(
        self,
        ctx: Context,
        project_name: str = Field(description='Name of the SAM project to create'),
        runtime: Optional[str] = Field(
            description="""Runtime environment for the Lambda function.
                             This option applies only when the package type is Zip."""
        ),
        project_directory: str = Field(
            description='Absolute path to directory where the SAM application will be initialized'
        ),
        dependency_manager: str = Field(
            description='Dependency manager for the Lambda function (e.g. npm, pip)'
        ),
        architecture: Optional[Literal['x86_64', 'arm64']] = Field(
            default='x86_64', description='Architecture for the Lambda function.'
        ),
        package_type: Optional[Literal['Zip', 'Image']] = Field(
            default='Zip',
            description='Package type for the Lambda function. Zip creates a .zip file archive, and Image creates a container image.',
        ),
        application_template: str = Field(
            default='hello-world',
            description="""Template for the SAM application, e.g., hello-world, quick-start, etc.
             This parameter is required if location is not specified.""",
        ),
        application_insights: Optional[bool] = Field(
            default=False,
            description="""Activate Amazon CloudWatch Application Insights monitoring.
                Helps you monitor the AWS resources in your applications to help identify potential issues.
                It can analyze AWS resource data for signs of problems and build automated CloudWatch dashboards to visualize them.
                """,
        ),
        no_application_insights: Optional[bool] = Field(
            default=False,
            description='Deactivate Amazon CloudWatch Application Insights monitoring',
        ),
        base_image: Optional[str] = Field(
            default=None,
            description="""Base image for the application when package type is Image.
                The AWS base images are preloaded with a language runtime, a runtime interface client to manage the
                interaction between Lambda and your function code, and a runtime interface emulator for local testing.""",
        ),
        config_env: Optional[str] = Field(
            default=None,
            description='Environment name specifying default parameter values in the configuration file',
        ),
        config_file: Optional[str] = Field(
            default=None,
            description='Absolute path to configuration file containing default parameter values',
        ),
        debug: Optional[bool] = Field(default=False, description='Turn on debug logging'),
        extra_content: Optional[str] = Field(
            default=None,
            description="Override custom parameters in the template's cookiecutter.json",
        ),
        location: Optional[str] = Field(
            default=None,
            description="""Template or application location (Git, HTTP/HTTPS, zip file path).
                This GitHub repo https://github.com/aws/aws-sam-cli-app-templates contains a collection of templates.
                This parameter is required if app_template is not specified.""",
        ),
        save_params: Optional[bool] = Field(
            default=False, description='Save parameters to the SAM configuration file'
        ),
        tracing: Optional[bool] = Field(
            default=False,
            description="""Activate AWS X-Ray tracing for Lambda functions. X-ray collects data about requests
            that your application serves and provides tools that you can use to view, filter, and gain insights into that data to identify issues
            and opportunities for optimization.""",
        ),
        no_tracing: Optional[bool] = Field(
            default=False, description='Deactivate AWS X-Ray tracing for Lambda functions'
        ),
    ) -> dict[str, Any]:
        """Initializes a serverless application using AWS SAM (Serverless Application Model) CLI.

        Requirements:
        - AWS SAM CLI MUST be installed and configured in your environment

        This tool creates a new SAM project that consists of:
        - An AWS SAM template to define your infrastructure code
        - A folder structure that organizes your application
        - Configuration for your AWS Lambda functions

        Use this tool to intialize a new project when building a serverless application.
        This tool generates a project based on a pre-defined template. After calling this tool,
        modify the code and infrastructure templates to fit the requirements of your application.

        Usage tips:
        - Do not use this tool on existing projects as it creates brand new directory. Instead manually create SAM templates in the existing application's directory.
        - Either select from one of predefined templates, or from the SAM GitHub repo (https://github.com/aws/aws-sam-cli-app-templates)

        Returns:
            Dict[str, Any]: Result of the initialization
        """
        try:
            await ctx.info(f"Initializing SAM project '{project_name}' in {project_directory}")
            # Initialize command list
            cmd = ['sam', 'init']

            # Add required parameters
            cmd.extend(['--name', project_name])
            if runtime:
                cmd.extend(['--runtime', runtime])
            cmd.extend(['--dependency-manager', dependency_manager])
            # Set output directory
            cmd.extend(['--output-dir', project_directory])
            # Add --no-interactive to avoid prompts
            cmd.append('--no-interactive')

            # Add optional parameters if provided
            if application_insights:
                cmd.append('--application-insights')

            if no_application_insights:
                cmd.append('--no-application-insights')

            if application_template:
                cmd.extend(['--app-template', application_template])

            if architecture:
                cmd.extend(['--architecture', architecture])

            if base_image:
                cmd.extend(['--base-image', base_image])

            if config_env:
                cmd.extend(['--config-env', config_env])

            if config_file:
                cmd.extend(['--config-file', config_file])

            if debug:
                cmd.append('--debug')

            if extra_content:
                cmd.extend(['--extra-context', extra_content])

            if location:
                cmd.extend(['--location', location])

            if no_tracing:
                cmd.append('--no-tracing')

            if package_type:
                cmd.extend(['--package-type', package_type])

            if save_params:
                cmd.append('--save-params')

            if tracing:
                cmd.append('--tracing')

            if no_tracing:
                cmd.append('--no-tracing')

            stdout, stderr = await run_command(cmd, cwd=project_directory)
            return {
                'success': True,
                'message': f"Successfully initialized SAM project '{project_name}' in {project_directory}",
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
