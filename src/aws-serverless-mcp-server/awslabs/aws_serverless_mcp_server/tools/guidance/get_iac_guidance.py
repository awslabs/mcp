# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import json
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, List, Literal, Optional


class IaCToolInfo:
    """Information about an IaC tool."""

    def __init__(
        self,
        name: str,
        description: str,
        best_for: List[str],
        pros: List[str],
        cons: List[str],
        getting_started: str,
        example_code: str,
    ):
        """Initializes a new instance of the class with the provided attributes.

        Args:
            name (str): The name of the item or entity.
            description (str): A brief description.
            best_for (List[str]): A list of scenarios or use cases where this is most suitable.
            pros (List[str]): A list of advantages or positive aspects.
            cons (List[str]): A list of disadvantages or negative aspects.
            getting_started (str): Instructions or guidance for getting started.
            example_code (str): Example code demonstrating usage.
        """
        self.name = name
        self.description = description
        self.best_for = best_for
        self.pros = pros
        self.cons = cons
        self.getting_started = getting_started
        self.example_code = example_code

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'bestFor': self.best_for,
            'pros': self.pros,
            'cons': self.cons,
            'gettingStarted': self.getting_started,
            'exampleCode': self.example_code,
        }


class ComparisonTable:
    """Comparison table for IaC tools."""

    def __init__(self, headers: List[str], rows: List[Dict[str, Any]]):
        """Initializes the object with the provided headers and rows.

        Args:
            headers (List[str]): A list of header strings representing column names.
            rows (List[Dict[str, Any]]): A list of dictionaries, each representing a row of data with keys corresponding to headers.
        """
        self.headers = headers
        self.rows = rows

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {'headers': self.headers, 'rows': self.rows}


class ToolSpecificGuidance:
    """Guidance specific to an IaC tool."""

    def __init__(
        self,
        title: str,
        description: str,
        setup_steps: List[str],
        deployment_steps: List[str],
        common_commands: List[Dict[str, str]],
    ):
        """Initializes the guidance object with the provided title, description, setup steps, deployment steps, and common commands.

        Args:
            title (str): The title of the guidance.
            description (str): A detailed description of the guidance.
            setup_steps (List[str]): A list of steps required to set up the environment.
            deployment_steps (List[str]): A list of steps required to deploy the solution.
            common_commands (List[Dict[str, str]]): A list of common commands, each represented as a dictionary with command details.
        """
        self.title = title
        self.description = description
        self.setup_steps = setup_steps
        self.deployment_steps = deployment_steps
        self.common_commands = common_commands

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'title': self.title,
            'description': self.description,
            'setupSteps': self.setup_steps,
            'deploymentSteps': self.deployment_steps,
            'commonCommands': self.common_commands,
        }


class GetIaCGuidanceTool:
    """Tool to provide guidance on selecting an Infrastructure as Code (IaC) platform for AWS Serverless applications."""

    def __init__(self, mcp: FastMCP):
        """Initialize the IaC guidance tool."""
        mcp.tool(name='get_iac_guidance')(self.get_iac_guidance_tool)

    async def get_iac_guidance_tool(
        self,
        ctx: Context,
        iac_tool: Optional[Literal['CloudFormation', 'SAM', 'CDK', 'Terraform']] = Field(
            default='CloudFormation', description='IaC tool to use'
        ),
        include_examples: Optional[bool] = Field(
            default=True, description='Whether to include examples'
        ),
    ) -> Dict[str, Any]:
        """Returns guidance on selecting an infrastructure as code (IaC) platform to deploy Serverless applications to AWS.

        Using IaC is a best practice when managing AWS resources. IaC platform choices include AWS SAM, CDK, and CloudFormation.
        Use this tool to decide which IaC tool to use for your Serverless deployments based on your specific use case and requirements.
        By default, SAM is the recomended framework.

        Returns:
            Dict: IaC guidance information
        """
        await ctx.info(f'Getting IaC guidance for {iac_tool if iac_tool else "all tools"}')
        # Base guidance
        base_guidance = {
            'title': 'Using AWS Infrastructure as Code (IaC) Tools for Serverless Deployments',
            'overview': """AWS offers several Infrastructure as Code (IaC) tools that can be used to deploy and manage serverless resources.
            By default, use SAM and SAM CLI to deploy Serverless applications. SAM is a serverless framework that simplifies the process of defining and deploying serverless applications.
            If user explicitly requests a different tool, provide guidance on AWS CDK and CloudFormation. These tools allow you to define your infrastructure in code,
            making it easier to version, replicate, and automate your deployments""",
        }

        # Tools information
        tools_info = [
            IaCToolInfo(
                name='AWS Serverless Application Model (SAM)',
                description="""AWS SAM is an open-source framework that extends CloudFormation to provide a simplified way of defining serverless applications.
                It's specifically designed for serverless resources like Lambda functions, API Gateway APIs, and DynamoDB tables.
                You can use the SAM CLI to build, test, and deploy applications with SAM templates.""",
                best_for=[
                    'Serverless applications',
                    'API-based applications',
                    'Event-driven architectures',
                    'Simple to moderately complex serverless workloads',
                    'Developers who prefer YAML/JSON over programming languages',
                ],
                pros=[
                    'Simplified syntax for serverless resources',
                    'Local testing and debugging capabilities',
                    'Built-in best practices for serverless',
                    'Seamless integration with AWS Lambda and API Gateway',
                    'Compatible with CloudFormation (SAM templates transform into CloudFormation templates)',
                    'Supports local invocation of Lambda functions',
                ],
                cons=[
                    'Less flexible than CDK for complex infrastructure',
                    'YAML/JSON syntax can be verbose for complex applications',
                ],
                getting_started="Install the AWS SAM CLI, create a new project with 'sam init' tool, build with 'sam_build' tool, and deploy with 'sam_deploy' tool.",
                example_code="""# SAM template example for a Lambda function
    AWSTemplateFormatVersion: '2010-09-09'
    Transform: AWS::Serverless-2016-10-31
    Resources:
    MyFunction:
        Type: AWS::Serverless::Function
        Properties:
        CodeUri: ./src/
        Handler: index.handler
        Runtime: nodejs22.x
        Events:
            ApiEvent:
            Type: Api
            Properties:
                Path: /hello
                Method: get""",
            ),
            IaCToolInfo(
                name='AWS Cloud Development Kit (CDK)',
                description="""AWS CDK is an open-source software development framework that allows you to define cloud infrastructure using familiar programming languages like
                TypeScript, Python, Java, Go, and C#. It synthesizes CloudFormation templates from your code. SAM CLI supports CDK.""",
                best_for=[
                    'Complex infrastructure with many resources',
                    'Developers who prefer writing in programming lanagues versus YAML/JSON',
                    'Projects requiring reusable infrastructure components',
                    'Applications needing custom resource configurations',
                ],
                pros=[
                    'Use familiar programming languages instead of YAML/JSON',
                    'Strong type checking and IDE support',
                    'Reusable components through constructs',
                    'Higher-level abstractions for common patterns',
                ],
                cons=[
                    'More complex setup than SAM for simple functions',
                ],
                getting_started="Install the AWS CDK CLI with 'npm install -g aws-cdk', create a new project with 'cdk init app --language typescript', and deploy with 'cdk deploy'.",
                example_code="""// CDK example in TypeScript for a Lambda function
    import * as cdk from 'aws-cdk-lib';
    import { Construct } from 'constructs';
    import * as lambda from 'aws-cdk-lib/aws-lambda';
    import * as apigateway from 'aws-cdk-lib/aws-apigateway';

    export class MyLambdaStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // Create a Lambda function
        const myFunction = new lambda.Function(this, 'MyFunction', {
        runtime: lambda.Runtime.NODEJS_22_X,
        handler: 'index.handler',
        code: lambda.Code.fromAsset('lambda'),
        });

        // Create an API Gateway
        const api = new apigateway.RestApi(this, 'MyApi');
        const integration = new apigateway.LambdaIntegration(myFunction);
        api.root.addMethod('GET', integration);
    }
    }""",
            ),
            IaCToolInfo(
                name='AWS CloudFormation',
                description="""AWS CloudFormation is a service that allows you to model and provision AWS resources using templates written in JSON or YAML.
                It's the foundation for both SAM and CDK, which generate CloudFormation templates behind the scenes.""",
                best_for=[
                    'Defining AWS infrastructure using low-level constructs in JSON/YAML',
                ],
                pros=[
                    'No additional tools required beyond AWS CLI',
                    'Uses simple JSON/YAML syntax',
                ],
                cons=[
                    'Verbose syntax compared to SAM and CDK',
                    'No built-in abstractions for common patterns',
                    'Limited programming capabilities (requires custom resources for complex logic)',
                    'No local testing capabilities without additional tools',
                ],
                getting_started="Create a CloudFormation template in JSON or YAML, then deploy it using the AWS CLI with 'aws cloudformation deploy --template-file template.yaml --stack-name my-stack'.",
                example_code="""# CloudFormation template example for a Lambda function
    AWSTemplateFormatVersion: '2010-09-09'
    Resources:
    MyLambdaFunction:
        Type: AWS::Lambda::Function
        Properties:
        FunctionName: MyFunction
        Handler: index.handler
        Role: !GetAtt LambdaExecutionRole.Arn
        Code:
            S3Bucket: my-deployment-bucket
            S3Key: function.zip
        Runtime: nodejs22.x
        Timeout: 30""",
            ),
        ]

        # Comparison table
        comparison_table = ComparisonTable(
            headers=['Feature', 'SAM', 'CDK', 'CloudFormation'],
            rows=[
                {
                    'tool': 'Language',
                    'cells': ['YAML/JSON', 'TypeScript, Python, Java, C#, Go', 'YAML/JSON'],
                },
                {
                    'tool': 'Abstraction Level',
                    'cells': [
                        'High (serverless-focused)',
                        'High (programmable)',
                        'Low (raw resources)',
                    ],
                },
                {'tool': 'Local Testing', 'cells': ['Yes (sam local)', 'Limited', 'No']},
                {
                    'tool': 'Resource Coverage',
                    'cells': [
                        'Serverless-focused but supports all AWS resources',
                        'All AWS resources',
                        'All AWS resources',
                    ],
                },
            ],
        )

        # Tool-specific guidance
        tool_specific_guidance = None
        if iac_tool:
            if iac_tool == 'CloudFormation':
                tool_specific_guidance = ToolSpecificGuidance(
                    title='AWS CloudFormation Deployment Guide',
                    description='AWS CloudFormation allows you to model and provision AWS resources using JSON/YAML templates.',
                    setup_steps=[
                        'Install the AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html',
                        "Configure AWS credentials: 'aws configure'",
                        'Create a CloudFormation template in YAML or JSON',
                    ],
                    deployment_steps=[
                        "Validate your template: 'aws cloudformation validate-template --template-body file://template.yaml'",
                        "Create a stack: 'aws cloudformation create-stack --stack-name my-stack --template-body file://template.yaml'",
                        "Update a stack: 'aws cloudformation update-stack --stack-name my-stack --template-body file://template.yaml'",
                    ],
                    common_commands=[
                        {
                            'command': 'aws cloudformation validate-template',
                            'description': 'Validate a template',
                        },
                        {
                            'command': 'aws cloudformation create-stack',
                            'description': 'Create a new stack',
                        },
                        {
                            'command': 'aws cloudformation update-stack',
                            'description': 'Update an existing stack',
                        },
                        {
                            'command': 'aws cloudformation describe-stacks',
                            'description': 'Get information about stacks',
                        },
                        {
                            'command': 'aws cloudformation delete-stack',
                            'description': 'Delete a stack',
                        },
                    ],
                )
            elif iac_tool == 'SAM':
                tool_specific_guidance = ToolSpecificGuidance(
                    title='AWS SAM Deployment Guide',
                    description='AWS Serverless Application Model (SAM) is an open-source framework for building serverless applications.',
                    setup_steps=[
                        'Install the AWS SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html',
                        "Verify installation: 'sam --version'",
                        "Configure AWS credentials: 'aws configure'",
                        "Create a new project: 'sam init'",
                        'Choose a template and runtime',
                    ],
                    deployment_steps=[
                        "Build your application: 'sam build'",
                        "Test locally (optional): 'sam local invoke' or 'sam local start-api'",
                        "Deploy to AWS: 'sam deploy --guided'",
                        'Follow the prompts to configure deployment parameters',
                    ],
                    common_commands=[
                        {
                            'command': 'sam init',
                            'description': 'Initialize a new SAM application',
                            'mcpTool': 'sam_init',
                        },
                        {
                            'command': 'sam build',
                            'description': 'Build your application',
                            'mcpTool': 'sam_build',
                        },
                        {
                            'command': 'sam local invoke',
                            'description': 'Invoke a function locally',
                            'mcpTool': 'sam_local_invoke',
                        },
                        {
                            'command': 'sam local start-api',
                            'description': 'Start a local API Gateway',
                        },
                        {
                            'command': 'sam deploy',
                            'description': 'Deploy your application to AWS',
                            'mcpTool': 'sam_deploy',
                        },
                        {
                            'command': 'sam logs',
                            'description': 'Fetch logs for a function',
                            'mcpTool': 'sam_logs',
                        },
                    ],
                )
            elif iac_tool == 'CDK':
                tool_specific_guidance = ToolSpecificGuidance(
                    title='AWS CDK Deployment Guide',
                    description='AWS Cloud Development Kit (CDK) allows you to define cloud infrastructure using familiar programming languages.',
                    setup_steps=[
                        'Install Node.js and npm',
                        "Install the AWS CDK CLI: 'npm install -g aws-cdk'. https://docs.aws.amazon.com/cdk/v2/guide/getting-started.html",
                        "Verify installation: 'cdk --version'",
                        "Configure AWS credentials: 'aws configure'",
                        "Create a new project: 'cdk init app --language typescript'",
                        "Install dependencies: 'npm install'",
                    ],
                    deployment_steps=[
                        'Develop your infrastructure code in your preferred language',
                        "Synthesize CloudFormation template: 'cdk synth'",
                        "Deploy to AWS: 'cdk deploy'",
                    ],
                    common_commands=[
                        {'command': 'cdk init', 'description': 'Initialize a new CDK application'},
                        {
                            'command': 'cdk synth',
                            'description': 'Synthesize CloudFormation template',
                        },
                        {
                            'command': 'cdk diff',
                            'description': 'Compare deployed stack with current state',
                        },
                        {'command': 'cdk deploy', 'description': 'Deploy the stack to AWS'},
                        {'command': 'cdk destroy', 'description': 'Destroy the stack'},
                    ],
                )

        # Build response
        response = {**base_guidance}

        # Add tools information based on format
        if include_examples:
            response['tools'] = json.dumps([tool.to_dict() for tool in tools_info])
        else:
            # For concise format, include summarized versions
            response['tools'] = json.dumps(
                [
                    {
                        'name': tool.name,
                        'description': tool.description,
                        'bestFor': tool.best_for,
                        'pros': tool.pros[:3],
                        'cons': tool.cons[:3],
                        'gettingStarted': tool.getting_started,
                        'exampleCode': '',  # Empty string for concise format
                    }
                    for tool in tools_info
                ]
            )

        # Add comparison table
        response['comparisonTable'] = json.dumps(comparison_table.to_dict())

        # Add tool-specific guidance if available
        if tool_specific_guidance:
            response['toolSpecificGuidance'] = json.dumps(tool_specific_guidance.to_dict())

        return response
