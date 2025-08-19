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

import os
import re
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, Literal, Optional


class EsmGuidanceTool:
    """Tool to provide guidance on EventSourceMapping(ESM) setup."""

    def __init__(self, mcp: FastMCP):
        """Initialize the ESM guidance tool."""
        mcp.tool(name='esm_guidance')(self.esm_guidance_tool)
        mcp.tool(name='esm_msk_policy')(self.esm_msk_policy_tool)
        mcp.tool(name='esm_msk_security_group')(self.esm_msk_security_group_tool)
        mcp.tool(name='esm_deployment_precheck')(self.esm_deployment_precheck_tool)

    async def esm_guidance_tool(
        self,
        ctx: Context,
        event_source: Optional[Literal['dynamodb', 'kinesis', 'kafka', 'unspecified']] = Field(
            default='unspecified', description='Type of event source for which to get guidance'
        ),
    ) -> Dict[str, Any]:
        """Provides step-by-step guidance for setting up AWS Lambda Event Source Mappings (ESM).

        This tool offers detailed instructions for configuring prerequisites like IAM permissions,
        stream settings, and network configurations based on the specified event source type.
        It helps users implement best practices when streaming data through Lambda pollers.

        Args:
            ctx: The execution context
            event_source: The event source type to configure ('dynamodb', 'kinesis', 'kafka', or 'unspecified')

        Returns:
            Dict containing deployment steps and next actions for the specified event source
        """
        await ctx.info(f'Getting deployment steps for {event_source} event source')

        common_requirements = [
            '# You MUST also do:',
            '## Before you start:',
            '   - Check the existance of the event source and the Lambda function. \
                If they exist, skip the creation of the event source and Lambda function. \
                Otherwise, create a SAM template for the missing Lambda function or prompt the \
                user to provide the correct event source name.',
            '## Whenever creating a new stack or component, prepend its name with \
                prefix the username of the credential.',
            '## Whenever creating Event Source Mapping:',
            '   - Use exact resource ARNs instead of asterisks in the template.',
            '   - Make the ESM depend on the permission created in the template.',
            '## Create a cleanup script file that can delete the SAM stack and undo all changes, \
                make sure all resources are deleted, including disabling the stream for DynamoDB \
                and detach the permissions from Lambda execution role',
            '## Before wrapping up:',
            '   - Create a test script file that can verify what has been deployed.',
            '   - Use SAM template as much as possible when deploying resources.',
            '   - Confirm the syntax is correct among all generated scripts.',
            '   - Validate the template to prevent circular dependency.',
            '   - Summerize what you have done in a README.md file.',
        ]

        if event_source == 'dynamodb':
            steps = [
                '1. Create a DynamoDB table, if not provided by the user.',
                '2. Check if the DynamoDB stream is enabled.',
                '3. Enable Streams on the DynamoDB table, if needed.',
                '4. Ask for the name or create a Lambda function to process the stream, if needed.',
                '5. Attach AWS policy AWSLambdaDynamoDBExecutionRole to the Lambda function if the function is newly created.',
                '6. Attach inline policy with requied permissions if the function alreday exists.',
                '7. Create Event Source Mapping with the following guidelines:',
                '   - Use exact resource ARNs instead of asterisks in the template.',
                '   - Make the ESM depend on the permission created in the template.',
            ]
        elif event_source == 'kinesis':
            steps = [
                '1. Create a Kinesis stream, if needed.',
                '2. Create a Lambda function to process the stream, if needed.',
                '3. Attach AWS policy `AWSLambdaKinesisExecutionRole` to the Lambda function if the function is newly created.',
                '4. Attach inline policy with requied permissions if the function alreday exists.',
                '5. Create Event Source Mapping with the following guidelines: ',
                '   - Use exact resource ARNs instead of asterisks in the template.',
                '   - Make the ESM depend on the permission created in the template.',
            ]
        elif event_source == 'kafka':
            steps = [
                'You MUST follow the steps to create the three main components:',
                '1. Configure VPC network settings, if needed:',
                '- Read the document: https://docs.aws.amazon.com/vpc/latest/userguide/create-a-vpc-with-private-subnets-and-nat-gateways-using-aws-cli.html',
                '- Create a new VPC, if not given.',
                '- Get the actual VPC ID by the given name or tag.',
                '- Use SAM commands for deployment.',
                '- Create corresponding network interfaces, NAT gateways, route tables, and security groups.',
                '- Use AWS CLI as fewer as possible, use SAM template instead',
                '- Check the availability of the CIDR for subnets you create.',
                '2. Setup the MSK clusters, if needed:',
                '- Read the document: https://docs.aws.amazon.com/lambda/latest/dg/with-msk.htm, \
                    https://docs.aws.amazon.com/lambda/latest/dg/with-msk-cluster-network.html \
                    and https://docs.aws.amazon.com/lambda/latest/dg/services-msk-tutorial.html.',
                '- Get the actual VPC ID by the given name or tag.',
                '- Create a provisioned cluster in the VPC.',
                '- Decide the number of zones according to the VPC.',
                '- Do NOT use default security group, create a new one dedicated for the cluster.',
                '- Allow inbound 443 and 9092-9098 in the new security group with source from itself.',
                '- Allow outbound all-traffic in the new security group with source from itself.',
                '- Separate the security group ingress rules into separate resources to break the circular dependency.',
                '- Enable IAM role-based authentication.',
                '- The new MSK cluster must resides the private subnet of VPC.',
                '- Create a script that can initialize Kafka and create a Kafka topic inside the cluster.',
                '- Create a producer script to write data into the Kafka topic.',
                '- Use the --resolve-s3 flag to create a managed S3 bucket in SAM deployment.',
                '- Do NOT make any change to security group of the lambda function since the ESM \
                    will use the security group of the cluster, this is automatically done by the \
                    ESM creation process.',
                '3. Create Event Source Mapping:',
                '- Read the documents: https://docs.aws.amazon.com/lambda/latest/dg/with-msk-configure.html, \
                    https://docs.aws.amazon.com/lambda/latest/dg/with-msk-permissions.html, \
                    and https://docs.aws.amazon.com/lambda/latest/dg/services-msk-tutorial.html.',
                '- Create a new SAM template for the ESM and the lambda consumer function.',
                '- Add ingress/egress rules in the template using the `esm_msk_security_group` tool.',
                '- Create a new policy using `esm_msk_policy` tool and attach it to the lambda execution role.',
                '- Wait for the policy be available, then create and enable the ESM with provision mode configured.',
                '- Make sure the VPC ID parameter is correct, not malformed.',
                '- The target number of broker nodes must be a multiple of the number of Availability Zones.',
                'Important:',
                "   - Don't change the default security group of the lambda function. The Lambda function \
                    must not depened on the cluster's security group and must not resides in the VPC.",
                "   - Don't use !GetAtt MSKCluster.BootstrapBrokerStringSaslIam in the template because it \
                    doesn't exist.",
                '   - Validate the template to prevent circular dependency.',
                '   - Validate ESM configurations using `esm_validate_configs` tool.',
            ]
        else:
            steps = [
                'Use solicit prompt to user to specify an event source type.',
            ]

        next_actions = [
            'Confirm with the user before deployment using `esm_deployment_precheck`.',
            'Follow the guidance to build a SAM template and deploy it.',
        ]

        response = {'steps': steps + common_requirements, 'next_actions': next_actions}

        return response

    def _validate_aws_parameters(
        self, region: str, account: str, cluster_name: str, cluster_uuid: str, partition: str
    ) -> Dict[str, str]:
        """Validate AWS parameters and return error messages if invalid."""
        errors = {}

        # AWS Region: format like us-east-1, eu-west-1, ap-southeast-2
        if not re.match(r'^[a-z]{2}-[a-z]+-\d+$', region):
            errors['region'] = f'Invalid AWS region format: {region}. Expected format: us-east-1'

        # AWS Account ID: exactly 12 digits
        if not re.match(r'^\d{12}$', account):
            errors['account'] = f'Invalid AWS account ID: {account}. Must be exactly 12 digits'

        # Cluster name: alphanumeric, hyphens, underscores (1-64 chars)
        if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', cluster_name):
            errors['cluster_name'] = (
                f'Invalid cluster name: {cluster_name}. Use alphanumeric, hyphens, underscores (1-64 chars)'
            )

        # Cluster UUID: alphanumeric or "*" wildcard
        if cluster_uuid != '*' and not re.match(r'^[a-zA-Z0-9-]{1,64}$', cluster_uuid):
            errors['cluster_uuid'] = (
                f"Invalid cluster UUID: {cluster_uuid}. Use alphanumeric/hyphens or '*'"
            )

        # AWS Partition: aws, aws-cn, aws-us-gov
        if partition not in ['aws', 'aws-cn', 'aws-us-gov']:
            errors['partition'] = (
                f'Invalid partition: {partition}. Must be: aws, aws-cn, or aws-us-gov'
            )

        return errors

    async def esm_msk_policy_tool(
        self,
        ctx: Context,
        region: str = Field(description='AWS region (e.g., us-east-1)'),
        account: str = Field(description='AWS account ID'),
        cluster_name: str = Field(description='MSK cluster name'),
        cluster_uuid: str = Field(description='MSK cluster UUID', default='*'),
        partition: str = Field(
            description='AWS partition (aws, aws-cn, aws-us-gov)', default='aws'
        ),
    ) -> Dict[str, Any]:
        """Generate IAM policy for MSK cluster access.

        Returns:
            Dict containing IAM policy document for MSK access
        """
        errors = self._validate_aws_parameters(
            region, account, cluster_name, cluster_uuid, partition
        )
        if errors:
            return {'error': 'Invalid parameters', 'details': errors}

        await ctx.info(f'Generating Kafka policy for cluster {cluster_name}')

        return {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': ['kafka-cluster:Connect', 'kafka-cluster:DescribeCluster'],
                    'Resource': f'arn:{partition}:kafka:{region}:{account}:cluster/{cluster_name}/{cluster_uuid}',
                },
                {
                    'Effect': 'Allow',
                    'Action': ['kafka-cluster:DescribeTopic', 'kafka-cluster:ReadData'],
                    'Resource': f'arn:{partition}:kafka:{region}:{account}:topic/{cluster_name}/*',
                },
                {
                    'Effect': 'Allow',
                    'Action': ['kafka-cluster:AlterGroup', 'kafka-cluster:DescribeGroup'],
                    'Resource': f'arn:{partition}:kafka:{region}:{account}:group/{cluster_name}/*',
                },
                {
                    'Effect': 'Allow',
                    'Action': ['kafka:DescribeClusterV2', 'kafka:GetBootstrapBrokers'],
                    'Resource': [
                        f'arn:{partition}:kafka:{region}:{account}:cluster/{cluster_name}/{cluster_uuid}',
                        f'arn:{partition}:kafka:{region}:{account}:topic/{cluster_name}/*',
                        f'arn:{partition}:kafka:{region}:{account}:group/{cluster_name}/*',
                    ],
                },
                {
                    'Effect': 'Allow',
                    'Action': [
                        'ec2:CreateNetworkInterface',
                        'ec2:DescribeNetworkInterfaces',
                        'ec2:DescribeVpcs',
                        'ec2:DeleteNetworkInterface',
                        'ec2:DescribeSubnets',
                        'ec2:DescribeSecurityGroups',
                    ],
                    'Resource': '*',
                },
            ],
        }

    async def esm_msk_security_group_tool(
        self,
        ctx: Context,
        security_group_id: str = Field(description='Security group ID for MSK cluster'),
    ) -> Dict[str, Any]:
        """Generate the ingress and egress rules in SAM template for MSK ESM security group.

        Returns:
            Dict containing SAM template with necessary security group rules
        """
        # Checking for valid secruity ID format
        if not re.match(r'^sg-[0-9a-f]{8}([0-9a-f]{9})?$', security_group_id):
            return {
                'error': f'Invalid security group ID format: {security_group_id}',
                'expected_format': "sg-xxxxxxxx or sg-xxxxxxxxxxxxxxxxx (8 or 17 hex characters after 'sg-')",
            }

        await ctx.info(f'Generating SAM template for security group {security_group_id}')

        # Returns the required rule by filling in the security group ID and pre-defined rules
        # Rules: ingress 9092:9098 and 443; egress all-trafiic;
        return {
            'AWSTemplateFormatVersion': '2010-09-09',
            'Transform': 'AWS::Serverless-2016-10-31',
            'Parameters': {
                'SecurityGroupId': {
                    'Type': 'String',
                    'Default': security_group_id,
                    'Description': 'Security group ID for MSK cluster',
                }
            },
            'Resources': {
                'MSKIngressHTTPS': {
                    'Type': 'AWS::EC2::SecurityGroupIngress',
                    'Properties': {
                        'GroupId': {'Ref': 'SecurityGroupId'},
                        'IpProtocol': 'tcp',
                        'FromPort': 443,
                        'ToPort': 443,
                        'SourceSecurityGroupId': {'Ref': 'SecurityGroupId'},
                        'Description': 'HTTPS access for MSK cluster',
                    },
                },
                'MSKIngressKafka': {
                    'Type': 'AWS::EC2::SecurityGroupIngress',
                    'Properties': {
                        'GroupId': {'Ref': 'SecurityGroupId'},
                        'IpProtocol': 'tcp',
                        'FromPort': 9092,
                        'ToPort': 9098,
                        'SourceSecurityGroupId': {'Ref': 'SecurityGroupId'},
                        'Description': 'Kafka broker access for MSK cluster',
                    },
                },
                'MSKEgressAll': {
                    'Type': 'AWS::EC2::SecurityGroupEgress',
                    'Properties': {
                        'GroupId': {'Ref': 'SecurityGroupId'},
                        'IpProtocol': '-1',
                        'DestinationSecurityGroupId': {'Ref': 'SecurityGroupId'},
                        'Description': 'All outbound traffic within security group',
                    },
                },
            },
            'Outputs': {
                'SecurityGroupId': {
                    'Description': 'Security group ID with MSK rules',
                    'Value': {'Ref': 'SecurityGroupId'},
                }
            },
        }

    async def esm_deployment_precheck_tool(
        self,
        ctx: Context,
        prompt: str = Field(description='User prompt to check for deploy intent'),
        project_directory: str = Field(description='Path to SAM project directory'),
    ) -> Dict[str, Any]:
        """Confirm ESM deployment when deploy intent is detected in prompt.

        This tool checks if the prompt contains deploy intent and ensures
        ESM configuration is deployed through sam_deploy tool.
        """
        # Check for deploy intent
        deploy_keywords = ['deploy', 'deployment', 'deploying']
        has_deploy_intent = any(keyword in prompt.lower() for keyword in deploy_keywords)

        if not has_deploy_intent:
            return {
                'deploy_intent_detected': False,
                'message': 'No deploy intent detected in prompt',
            }

        await ctx.info('Deploy intent detected, checking for template files')

        # Check for template files in project directory
        template_files = ['template.yaml', 'template.yml', 'template.json']
        template_found = False

        for template_file in template_files:
            template_path = os.path.join(project_directory, template_file)
            if os.path.exists(template_path):
                template_found = True
                break

        if not template_found:
            return {
                'deploy_intent_detected': True,
                'error': 'No SAM template found in project directory. You must use a SAM template (template.yaml/yml/json) to deploy instead of using AWS CLI directly.',
            }

        return {
            'deploy_intent_detected': True,
            'template_found': True,
            'message': 'Deploy intent confirmed and SAM template found. ESM configuration can be deployed using sam_deploy tool.',
            'recommended_action': f'Execute sam_deploy with project_directory: {project_directory}',
        }
