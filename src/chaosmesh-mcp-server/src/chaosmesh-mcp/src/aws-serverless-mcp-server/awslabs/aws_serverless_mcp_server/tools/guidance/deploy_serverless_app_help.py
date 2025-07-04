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

"""Deploy serverless app help tool for AWS Serverless MCP Server."""

from enum import Enum
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, Literal


class ApplicationType(str, Enum):
    """Application types for serverless deployments."""

    EVENT_DRIVEN = 'event_driven'
    BACKEND = 'backend'
    FULLSTACK = 'fullstack'


class DeployServerlessAppHelpTool:
    """Tool to provide help information for deploying serverless applications to AWS Lambda."""

    def __init__(self, mcp: FastMCP):
        """Initialize the DeployServerlessAppHelpTool."""
        mcp.tool(name='deploy_serverless_app_help')(self.deploy_serverless_app_help_tool)

    async def deploy_serverless_app_help_tool(
        self,
        ctx: Context,
        application_type: Literal['event_driven', 'backend', 'fullstack'] = Field(
            description='Type of application to deploy'
        ),
    ) -> Dict[str, Any]:
        """Provides instructions on how to deploy a serverless application to AWS Lambda.

        Deploying a Lambda application requires generating IaC templates, building the code, packaging
        the code, selecting a deployment tool, and executing the deployment commands. This tool walks through
        each step and links to tools in this MCP server. For deploying web applications specifically, use the deploy_webapp_tool.

        Returns:
            Dict[str, Any]: A dictionary containing the deployment help information.
        """
        await ctx.info(f'Getting deployment help for {application_type} application')
        iac_guidance = (
            "Design the application's serverless architecture and generate the infrastructure as code (IaC) template. "
            'Use the get_iac_guidance tool to decide which IaC tool to use based on the application type. '
            'If using SAM, you can use get_serverless_templates tool to find example SAM template for the Lambda function from ServerlessLand. '
            'Configure Lambda function properties such as memory size, timeout, environment variables, etc. using best practices from AWS documentation. '
            'Consider the application use case and expected scale if that info is available'
        )

        if application_type == ApplicationType.EVENT_DRIVEN:
            iac_guidance += ' For event driven applications, use an event source mapping (ESM) to trigger the Lambda function.'
        elif application_type == ApplicationType.BACKEND:
            iac_guidance += ' For backend APIs, you can use API Gateway or Lambda function URLs to expose the Lambda function as an API endpoint.'
        elif application_type == ApplicationType.FULLSTACK:
            iac_guidance += (
                ' Full stack applications typically involve both frontend and backend components. '
                'For the backend, you can use Lambda functions with API Gateway or Lambda function URLs. '
                'For the frontend, you can use S3 for static hosting. Use CloudFront for CDN and caching.'
            )

        result = [
            {
                'step': 1,
                'prompt': (
                    """For new applications, use the sam_init tool to generate the project directory structure that is compatible with AWS SAM CLI.
                    Then generate Lambda function handler code or update existing code to ensure that the structure is compatible with AWS Lambda.
                    Lambda requires a handler method that is the entry point into the function when it is invoked.
                    The handler method should accept an event object and a context object, and return a response object.
                    For event-driven applications, use the get_lambda_event_schemas tool to get the event specific schema for the event source (e.g. SQS, SNS)
                    and ensure the event parameter is using the correct type. For web servers using frameworks, such as next.js, express.js, SpringBoot,
                    use Lambda Web Adapter (https://github.com/awslabs/aws-lambda-web-adapter) to avoid needing to modify the code to conform to the Lambda handler format."""
                ),
            },
            {'step': 2, 'prompt': iac_guidance},
            {
                'step': 3,
                'prompt': (
                    "Install dependencies using the package's configured dependency manager. For example, python applications use pip to install dependencies, "
                    'node.js applications use npm or yarn to install dependencies, and java applications use maven or gradle to build the package.\n\n'
                    'If package is using SAM, the sam_build tool automatically installs dependencies and this step can be skipped.'
                ),
            },
            {
                'step': 4,
                'prompt': (
                    'Build the package. Analyze the project structure to determine the build command. '
                    'For example, for node.js applications, run `npm run build` or `yarn build`. For python applications, run `python setup.py build` or `pip install -e`.\n\n'
                    'If package is using SAM, run the sam_build tool to build the package.'
                ),
            },
            {
                'step': 5,
                'prompt': (
                    'Package the code into the deployment artifact. AWS Lambda accepts deployment packages in direct ZIP upload, S3 bucket, or conatiner image in an ECR repository. '
                    'If there is already a Dockerfile in the project directory, then use OCI format. For code packages larger than 250 MB (unzipped), use the AWS Lambda container image support. '
                    'For packages smaller than 250MB, use the ZIP format or S3 upload option.\n\n'
                    'If package is using SAM, the sam_deploy tool will automatically upload deployment artifacts to S3, and this step can be skipped.'
                ),
            },
            {
                'step': 6,
                'prompt': (
                    'Run the IaC tool commands to perform the deployment. If package is using SAM, use sam_deploy tool to deploy the application. '
                    'For Cloudformation and CDK, use the CFN or CDK cli commands.'
                ),
            },
        ]

        return {'content': result}
