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
from awslabs.aws_serverless_mcp_server.tools.common.base_tool import BaseTool
from awslabs.aws_serverless_mcp_server.utils.data_scrubber import DataScrubber
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, Literal, Optional, cast


class EsmGuidanceTool(BaseTool):
    """Tool to provide comprehensive guidance on AWS Lambda Event Source Mapping (ESM) setup.

    This class provides step-by-step instructions for configuring ESM with different event sources
    including DynamoDB streams, Kinesis streams, and MSK Kafka clusters. It handles IAM policies,
    security groups, and deployment validation for proper ESM configuration.
    """

    def __init__(self, mcp: FastMCP, allow_write: bool = False):
        """Initialize the ESM guidance tool and register all available tools.

        Args:
            mcp: FastMCP instance for tool registration
            allow_write: Whether write operations are allowed
        """
        super().__init__(allow_write=allow_write)
        self.allow_write = allow_write
        # Register main ESM guidance tool - PRIMARY USER-FACING TOOL
        mcp.tool(
            name='esm_guidance',
            description='Create and configure AWS infrastructure for streaming data processing. Handles Kafka clusters (MSK), Kinesis streams, DynamoDB streams, SQS queues with Lambda functions. Sets up VPCs, security groups, IAM roles, and Event Source Mappings. Generates complete SAM templates for deployment.',
        )(self.esm_guidance_tool)

    async def esm_guidance_tool(
        self,
        ctx: Context,
        event_source: Optional[
            Literal['dynamodb', 'kinesis', 'kafka', 'sqs', 'unspecified']
        ] = Field(
            default='unspecified', description='Type of event source for which to get guidance'
        ),
        guidance_type: Optional[Literal['setup', 'networking', 'troubleshooting']] = Field(
            default='setup',
            description='Type of guidance: "setup" for initial configuration, "networking" for VPC/connectivity, "troubleshooting" for issues',
        ),
        networking_question: Optional[str] = Field(
            default='general',
            description='Specific networking question (used with guidance_type="networking")',
        ),
    ) -> Dict[str, Any]:
        """Comprehensive guidance for AWS Lambda Event Source Mappings (ESM).

        This unified tool provides setup guidance, networking configuration, and troubleshooting
        for all ESM event sources. It generates SAM templates and integrates with sam_deploy.

        Args:
            ctx: The execution context
            event_source: The event source type ('dynamodb', 'kinesis', 'kafka', 'sqs', 'unspecified')
            guidance_type: Type of guidance needed ('setup', 'networking', 'troubleshooting')
            networking_question: Specific networking question for networking guidance

        Returns:
            Dict containing guidance, templates, and deployment instructions
        """
        # Check tool access permissions for write operations (template generation)
        self.checkToolAccess()

        await ctx.info(f'Getting {guidance_type} guidance for {event_source} event source')

        # Route to appropriate guidance based on type
        if guidance_type == 'networking':
            return await self._get_networking_guidance(ctx, event_source, networking_question)
        elif guidance_type == 'troubleshooting':
            return await self._get_troubleshooting_guidance(ctx, event_source)
        else:  # setup guidance (default)
            return await self._get_setup_guidance(ctx, event_source)

    async def _get_setup_guidance(
        self, ctx: Context, event_source: Optional[str]
    ) -> Dict[str, Any]:
        """Get setup guidance for ESM configuration."""
        # Common requirements that apply to all ESM configurations regardless of event source type
        # These ensure proper resource management, security, and maintainability
        common_requirements = [
            '# You MUST also do:',
            '## Before you start:',
            '   - Check the existence of the event source and the Lambda function. \
                If they exist, skip the creation of the event source and Lambda function. \
                Otherwise, create a SAM template for the missing Lambda function or prompt the \
                user to provide the correct event source name.',
            '   - ALWAYS use the latest supported Lambda runtime versions (e.g., python3.13, nodejs22.x) \
                to avoid deprecated runtime issues. Never use python3.9 or older versions.',
            '## Whenever creating a new stack or component, prepend its name with \
                the username of the credential as a prefix.',
            '## Whenever creating Event Source Mapping:',
            '   - Use exact resource ARNs instead of asterisks in the template.',
            '   - Make the ESM depend on the permission created in the template.',
            '## Create a cleanup script file that can delete the SAM stack and undo all changes. \
                Make sure all resources are deleted, including disabling the stream for DynamoDB \
                and detaching the permissions from Lambda execution role.',
            '## Before wrapping up:',
            '   - Create a test script file that can verify what has been deployed.',
            '   - Use SAM template as much as possible when deploying resources.',
            '   - Confirm the syntax is correct among all generated scripts.',
            '   - Validate the template to prevent circular dependency.',
            '   - Summarize what you have done in a README.md file.',
        ]

        # DynamoDB Streams configuration - handles real-time data changes from DynamoDB tables
        if event_source == 'dynamodb':
            steps = [
                '1. Create a DynamoDB table, if not provided by the user.',
                '2. Check if the DynamoDB stream is enabled.',
                '3. Enable Streams on the DynamoDB table, if needed.',
                '4. Ask for the name or create a Lambda function to process the stream, if needed.',
                '5. Attach AWS policy AWSLambdaDynamoDBExecutionRole to the Lambda function if the function is newly created.',
                '6. Attach inline policy with required permissions if the function already exists.',
                '7. Create Event Source Mapping with the following guidelines:',
                '   - Use exact resource ARNs instead of asterisks in the template.',
                '   - Make the ESM depend on the permission created in the template.',
            ]
        # Kinesis Streams configuration - handles real-time streaming data processing
        elif event_source == 'kinesis':
            steps = [
                '1. Create a Kinesis stream, if needed.',
                '2. Create a Lambda function to process the stream, if needed.',
                '3. Attach AWS policy `AWSLambdaKinesisExecutionRole` to the Lambda function if the function is newly created.',
                '4. Attach inline policy with required permissions if the function already exists.',
                '5. Create Event Source Mapping with the following guidelines: ',
                '   - Use exact resource ARNs instead of asterisks in the template.',
                '   - Make the ESM depend on the permission created in the template.',
            ]
        # SQS configuration - focuses on concurrency, batching, and error handling
        elif event_source == 'sqs':
            steps = [
                '1. Create an SQS queue, if needed.',
                '2. Configure queue settings for optimal Lambda integration:',
                '   - Set VisibilityTimeout to at least 6x your Lambda function timeout',
                '   - Configure MessageRetentionPeriod based on your retry requirements',
                '   - Set up Dead Letter Queue (DLQ) for failed message handling',
                '   - Consider using FIFO queues for ordered processing if needed',
                '3. Create a Lambda function to process SQS messages, if needed.',
                '4. Attach AWS policy `AWSLambdaSQSQueueExecutionRole` to the Lambda function if newly created.',
                '5. Attach inline policy with required SQS permissions if the function already exists.',
                '6. Create Event Source Mapping with SQS-specific considerations:',
                '   - Configure BatchSize (1-10 for standard queues, 1-10 for FIFO queues)',
                '   - Set MaximumBatchingWindowInSeconds for batching optimization',
                '   - Configure ScalingConfig with MaximumConcurrency for concurrency control',
                '   - Set up FunctionResponseTypes for partial batch failure handling',
                '   - Use exact queue ARN instead of asterisks in the template',
                '   - Make the ESM depend on the permission created in the template',
                '7. Configure concurrency and scaling:',
                '   - Use MaximumConcurrency in ScalingConfig to control concurrent executions',
                '   - Consider Reserved Concurrency on the Lambda function for predictable scaling',
                '   - Monitor ApproximateNumberOfMessages and ApproximateAgeOfOldestMessage metrics',
            ]
        # MSK Kafka configuration - most complex setup requiring VPC, security groups, and IAM
        # Kafka ESM requires careful network configuration since it operates within a VPC
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
                '- The new MSK cluster must reside in the private subnet of the VPC.',
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
                "   - Don't change the default security group of the Lambda function. The Lambda function \
                    must not depend on the cluster's security group and must not reside in the VPC.",
                "   - Don't use !GetAtt MSKCluster.BootstrapBrokerStringSaslIam in the template because it \
                    doesn't exist.",
                '   - Validate the template to prevent circular dependency.',
                '   - Validate ESM configurations using `esm_validate_configs` tool.',
            ]
        # Fallback case when event source is not specified or unrecognized
        else:
            steps = [
                'Prompt the user to specify an event source type.',
            ]

        next_actions = [
            'Generate complete SAM template with all required resources',
            'IMPORTANT: Ask user for explicit confirmation before any deployment',
            'Use sam_deploy tool to deploy the generated SAM template (only after user confirmation)',
            'Validate configuration using esm_optimize tool with action="validate"',
            'For optimization: Use esm_optimize tool with action="analyze"',
            'For troubleshooting: Use esm_kafka_troubleshoot tool (Kafka) or esm_guidance with guidance_type="troubleshooting"',
        ]

        response = {
            'steps': steps + common_requirements,
            'next_actions': next_actions,
            'deployment_warning': {
                'CRITICAL': 'ALWAYS ask for user confirmation before any deployment or mutating operation',
                'required_confirmation': 'User must explicitly approve deployment before proceeding',
                'safety_note': 'ESM tools generate templates but do NOT automatically deploy them',
            },
            'sam_deploy_integration': {
                'note': 'Generated SAM templates should be deployed using the existing sam_deploy tool',
                'confirmation_required': 'Ask user: "Do you want to deploy this ESM configuration to AWS?" before calling sam_deploy',
                'typical_params': {
                    'application_name': 'esm-setup',
                    'project_directory': './esm-project',
                    'capabilities': ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
                },
            },
        }

        # Scrub sensitive data from response before returning
        return self.scrub_response_data(response)

    async def _get_networking_guidance(
        self, ctx: Context, event_source: Optional[str], networking_question: Optional[str]
    ) -> Dict[str, Any]:
        """Get networking guidance for ESM configuration."""
        # This is the consolidated networking guidance from the old esm_networking_guidance_tool
        actual_event_source = event_source or 'general'
        if actual_event_source not in ['kafka', 'kinesis', 'dynamodb', 'sqs', 'general']:
            actual_event_source = 'general'
        return await self.esm_networking_guidance_tool(
            ctx,
            cast(Literal['kafka', 'kinesis', 'dynamodb', 'sqs', 'general'], actual_event_source),
            networking_question or 'general',
        )

    async def _get_troubleshooting_guidance(
        self, ctx: Context, event_source: Optional[str]
    ) -> Dict[str, Any]:
        """Get troubleshooting guidance for ESM configuration."""
        if event_source == 'kafka':
            return {
                'guidance': 'For Kafka troubleshooting, use the esm_kafka_troubleshoot tool',
                'next_action': 'Use esm_kafka_troubleshoot with appropriate kafka_type and issue_type parameters',
            }
        else:
            return {
                'guidance': f'General troubleshooting guidance for {event_source}',
                'common_issues': [
                    'Check IAM permissions for the Lambda execution role',
                    'Verify event source configuration and accessibility',
                    'Check CloudWatch logs for error messages',
                    'Validate network connectivity if using VPC',
                    'Ensure proper resource ARNs in ESM configuration',
                ],
                'next_actions': [
                    'Check CloudWatch logs for specific error messages',
                    'Use esm_optimize tool with action="validate" to check configuration',
                    'For Kafka issues: Use esm_kafka_troubleshoot tool',
                ],
            }

    async def esm_sqs_policy_tool(
        self,
        ctx: Context,
        region: str = Field(description='AWS region (e.g., us-east-1)'),
        account: str = Field(description='AWS account ID'),
        queue_name: str = Field(description='SQS queue name'),
        partition: str = Field(
            description='AWS partition (aws, aws-cn, aws-us-gov)', default='aws'
        ),
    ) -> Dict[str, Any]:
        """Generate comprehensive IAM policy for SQS queue access with ESM.

        Creates an IAM policy document that grants the necessary permissions for
        Lambda Event Source Mapping to connect to and consume from SQS queues.
        Includes permissions for message operations, queue attributes, and DLQ handling.

        Args:
            ctx: MCP context for logging
            region: AWS region where the SQS queue is located
            account: AWS account ID that owns the SQS queue
            queue_name: Name of the SQS queue
            partition: AWS partition (standard, China, or GovCloud)

        Returns:
            Dict containing complete IAM policy document with all required permissions
        """
        # Validate AWS parameters for SQS policy generation
        errors = {}

        # Validate AWS Region format
        if not re.match(r'^[a-z]{2}-[a-z]+-\d+$', region):
            errors['region'] = f'Invalid AWS region format: {region}. Expected format: us-east-1'

        # Validate AWS Account ID: must be exactly 12 digits
        if not re.match(r'^\d{12}$', account):
            errors['account'] = f'Invalid AWS account ID: {account}. Must be exactly 12 digits'

        # Validate SQS queue name: 1-80 characters, alphanumeric plus hyphens and underscores
        if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', queue_name):
            errors['queue_name'] = (
                f'Invalid queue name: {queue_name}. Use alphanumeric, hyphens, underscores (1-80 chars)'
            )

        # Validate AWS partition - handle the Field annotation issue
        partition_value = partition if isinstance(partition, str) else 'aws'
        if partition_value not in ['aws', 'aws-cn', 'aws-us-gov']:
            errors['partition'] = (
                f'Invalid partition: {partition_value}. Must be: aws, aws-cn, or aws-us-gov'
            )

        if errors:
            return {'error': 'Invalid parameters', 'details': errors}

        # Scrub sensitive data from queue name before logging
        scrubbed_queue_name = DataScrubber.scrub_text(queue_name)
        await ctx.info(f'Generating SQS policy for queue {scrubbed_queue_name}')

        # Return comprehensive IAM policy with all necessary permissions for SQS ESM
        return {
            'Version': '2012-10-17',
            'Statement': [
                {
                    # Basic SQS message operations - required for ESM to consume messages
                    'Effect': 'Allow',
                    'Action': [
                        'sqs:ReceiveMessage',
                        'sqs:DeleteMessage',
                        'sqs:GetQueueAttributes',
                        'sqs:GetQueueUrl',
                    ],
                    'Resource': f'arn:{partition}:sqs:{region}:{account}:{queue_name}',
                },
                {
                    # Dead Letter Queue operations - required if DLQ is configured
                    'Effect': 'Allow',
                    'Action': ['sqs:SendMessage', 'sqs:GetQueueAttributes', 'sqs:GetQueueUrl'],
                    'Resource': f'arn:{partition}:sqs:{region}:{account}:{queue_name}-dlq',
                    'Condition': {'StringEquals': {'aws:SourceAccount': account}},
                },
                {
                    # CloudWatch Logs permissions for ESM monitoring and debugging
                    'Effect': 'Allow',
                    'Action': ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
                    'Resource': f'arn:{partition}:logs:{region}:{account}:log-group:/aws/lambda/*',
                },
            ],
        }

    async def esm_sqs_concurrency_guidance_tool(
        self,
        ctx: Context,
        target_throughput: Optional[str] = Field(
            default='medium', description='Target throughput level: low, medium, high, or custom'
        ),
        message_processing_time: Optional[int] = Field(
            default=5, description='Average message processing time in seconds'
        ),
        queue_type: Optional[Literal['standard', 'fifo']] = Field(
            default='standard', description='SQS queue type'
        ),
    ) -> Dict[str, Any]:
        """Provides SQS-specific concurrency and scaling guidance for Lambda ESM.

        Analyzes SQS queue characteristics and provides recommendations for:
        - MaximumConcurrency settings in ScalingConfig
        - BatchSize optimization
        - Reserved Concurrency considerations
        - Monitoring and alerting setup

        Args:
            ctx: MCP context for logging
            target_throughput: Desired throughput level or specific requirements
            message_processing_time: Average time to process one message
            queue_type: Type of SQS queue (standard or FIFO)

        Returns:
            Dict containing concurrency recommendations and configuration guidance
        """
        await ctx.info(f'Providing SQS concurrency guidance for {queue_type} queue')

        # Base recommendations based on queue type and throughput requirements
        if queue_type == 'fifo':
            base_recommendations = {
                'MaximumConcurrency': {
                    'recommended_range': '2-10',
                    'reasoning': 'FIFO queues process messages in order, limiting parallelism',
                    'considerations': [
                        'Higher concurrency may not improve throughput due to ordering constraints',
                        'Consider message group ID distribution for better parallelism',
                        'Monitor MessageGroupId distribution in CloudWatch',
                    ],
                },
                'BatchSize': {
                    'recommended_range': '1-10',
                    'reasoning': 'FIFO queues support smaller batch sizes',
                    'optimal_value': min(10, max(1, 30 // (message_processing_time or 1))),
                },
            }
        else:  # standard queue
            # Calculate optimal concurrency based on throughput targets
            throughput_configs = {
                'low': {'max_concurrency': 10, 'batch_size': 5},
                'medium': {'max_concurrency': 50, 'batch_size': 10},
                'high': {'max_concurrency': 1000, 'batch_size': 10},
            }

            actual_target_throughput = target_throughput or 'medium'
            config = throughput_configs.get(actual_target_throughput, throughput_configs['medium'])

            base_recommendations = {
                'MaximumConcurrency': {
                    'recommended_value': config['max_concurrency'],
                    'reasoning': f'Optimized for {target_throughput} throughput scenarios',
                    'considerations': [
                        'Standard queues support high parallelism',
                        'Monitor Lambda concurrency metrics to avoid throttling',
                        'Consider account-level concurrency limits',
                    ],
                },
                'BatchSize': {
                    'recommended_value': config['batch_size'],
                    'reasoning': 'Balances throughput and cost efficiency',
                    'optimal_calculation': f'Based on {message_processing_time}s processing time',
                },
            }

        # Additional configuration recommendations
        additional_config = {
            'MaximumBatchingWindowInSeconds': {
                'recommended_range': '0-20',
                'reasoning': 'Allows batching for cost optimization without excessive latency',
                'fifo_note': 'Less critical for FIFO queues due to ordering requirements'
                if queue_type == 'fifo'
                else None,
            },
            'FunctionResponseTypes': {
                'recommended': ['ReportBatchItemFailures'],
                'reasoning': 'Enables partial batch failure handling for better reliability',
            },
            'ReservedConcurrency': {
                'consideration': 'Set on Lambda function to guarantee capacity and prevent throttling',
                'calculation': f'Consider setting to {base_recommendations["MaximumConcurrency"]["recommended_value"] if "recommended_value" in base_recommendations["MaximumConcurrency"] else "10-50"} or higher',
            },
        }

        # Monitoring and alerting recommendations
        monitoring_setup = {
            'key_metrics': [
                'ApproximateNumberOfMessages',
                'ApproximateAgeOfOldestMessage',
                'NumberOfMessagesSent',
                'NumberOfMessagesReceived',
                'NumberOfMessagesDeleted',
            ],
            'lambda_metrics': ['Duration', 'Errors', 'Throttles', 'ConcurrentExecutions'],
            'recommended_alarms': [
                {
                    'metric': 'ApproximateAgeOfOldestMessage',
                    'threshold': '300 seconds',
                    'reasoning': 'Detect message processing delays',
                },
                {
                    'metric': 'ApproximateNumberOfMessages',
                    'threshold': '1000 messages',
                    'reasoning': 'Detect queue backlog buildup',
                },
                {
                    'metric': 'Lambda Throttles',
                    'threshold': '> 0',
                    'reasoning': 'Detect concurrency limit issues',
                },
            ],
        }

        # Performance tuning guidance
        performance_tuning = {
            'scaling_behavior': {
                'standard_queue': 'ESM scales up to MaximumConcurrency based on queue depth',
                'fifo_queue': 'Scaling limited by message group distribution and ordering',
            },
            'cost_optimization': [
                'Use larger batch sizes to reduce Lambda invocation costs',
                'Set appropriate MaximumBatchingWindowInSeconds to improve batching',
                'Monitor and adjust MaximumConcurrency to avoid over-provisioning',
            ],
            'latency_optimization': [
                'Use smaller batch sizes for lower latency',
                'Set MaximumBatchingWindowInSeconds to 0 for immediate processing',
                'Increase MaximumConcurrency to handle traffic spikes',
            ],
        }

        return {
            'queue_type': queue_type,
            'target_throughput': target_throughput,
            'base_recommendations': base_recommendations,
            'additional_config': additional_config,
            'monitoring_setup': monitoring_setup,
            'performance_tuning': performance_tuning,
            'next_actions': [
                'Generate SAM template with optimized SQS ESM configuration',
                'Create CloudWatch alarms for key metrics',
                'Set up Lambda function with appropriate reserved concurrency',
                'Test with realistic message volumes',
                'Monitor and adjust based on actual performance',
            ],
        }

    async def esm_self_managed_kafka_policy_tool(
        self,
        ctx: Context,
        region: str = Field(description='AWS region (e.g., us-east-1)'),
        account: str = Field(description='AWS account ID'),
        partition: str = Field(
            description='AWS partition (aws, aws-cn, aws-us-gov)', default='aws'
        ),
    ) -> Dict[str, Any]:
        """Generate comprehensive IAM policy for self-managed Apache Kafka cluster access with ESM.

        Creates an IAM policy document that grants the necessary permissions for
        Lambda Event Source Mapping to connect to and consume from self-managed Kafka clusters.
        Includes permissions for VPC operations, Secrets Manager access, and Lambda invocation.

        Args:
            ctx: MCP context for logging
            region: AWS region where the Kafka cluster is located
            account: AWS account ID
            partition: AWS partition (standard, China, or GovCloud)

        Returns:
            Dict containing complete IAM policy document with all required permissions
        """
        # Validate AWS parameters for self-managed Kafka policy generation
        errors = {}

        # Validate AWS Region format
        if not re.match(r'^[a-z]{2}-[a-z]+-\d+$', region):
            errors['region'] = f'Invalid AWS region format: {region}. Expected format: us-east-1'

        # Validate AWS Account ID: must be exactly 12 digits
        if not re.match(r'^\d{12}$', account):
            errors['account'] = f'Invalid AWS account ID: {account}. Must be exactly 12 digits'

        # Validate AWS partition - handle the Field annotation issue
        partition_value = partition if isinstance(partition, str) else 'aws'
        if partition_value not in ['aws', 'aws-cn', 'aws-us-gov']:
            errors['partition'] = (
                f'Invalid partition: {partition_value}. Must be: aws, aws-cn, or aws-us-gov'
            )

        if errors:
            return {'error': 'Invalid parameters', 'details': errors}

        await ctx.info('Generating self-managed Kafka policy')

        # Return comprehensive IAM policy with all necessary permissions for self-managed Kafka ESM
        return {
            'Version': '2012-10-17',
            'Statement': [
                {
                    # VPC networking permissions - required for ESM to operate within VPC
                    # Self-managed Kafka ESM needs to create/manage network interfaces
                    'Effect': 'Allow',
                    'Action': [
                        'ec2:CreateNetworkInterface',
                        'ec2:DescribeNetworkInterfaces',
                        'ec2:DescribeVpcs',
                        'ec2:DeleteNetworkInterface',
                        'ec2:DescribeSubnets',
                        'ec2:DescribeSecurityGroups',
                        'ec2:AttachNetworkInterface',
                        'ec2:DetachNetworkInterface',
                    ],
                    'Resource': '*',  # VPC operations require wildcard resource
                },
                {
                    # Secrets Manager permissions - required for SASL authentication
                    # Self-managed Kafka often uses SASL/SCRAM or SASL/PLAIN authentication
                    'Effect': 'Allow',
                    'Action': ['secretsmanager:GetSecretValue', 'secretsmanager:DescribeSecret'],
                    'Resource': [
                        f'arn:{partition_value}:secretsmanager:{region}:{account}:secret:*'
                    ],
                    'Condition': {
                        'StringEquals': {'secretsmanager:ResourceTag/LambdaESM': 'true'}
                    },
                },
                {
                    # KMS permissions - required if Secrets Manager secrets are encrypted with customer KMS keys
                    'Effect': 'Allow',
                    'Action': ['kms:Decrypt', 'kms:GenerateDataKey'],
                    'Resource': [f'arn:{partition_value}:kms:{region}:{account}:key/*'],
                    'Condition': {
                        'StringEquals': {
                            'kms:ViaService': f'secretsmanager.{region}.amazonaws.com'  # pragma: allowlist secret
                        }
                    },
                },
                {
                    # CloudWatch Logs permissions - required for ESM monitoring and debugging
                    'Effect': 'Allow',
                    'Action': [
                        'logs:CreateLogGroup',
                        'logs:CreateLogStream',
                        'logs:PutLogEvents',
                        'logs:DescribeLogGroups',
                        'logs:DescribeLogStreams',
                    ],
                    'Resource': f'arn:{partition_value}:logs:{region}:{account}:log-group:/aws/lambda/*',
                },
                {
                    # Lambda invocation permissions - required for ESM to invoke the target function
                    'Effect': 'Allow',
                    'Action': ['lambda:InvokeFunction'],
                    'Resource': f'arn:{partition_value}:lambda:{region}:{account}:function:*',
                },
            ],
            'policy_notes': {
                'vpc_permissions': 'Required for ESM to create network interfaces in your VPC',
                'secrets_manager': 'Required for SASL authentication - tag secrets with LambdaESM=true',  # pragma: allowlist secret
                'kms_permissions': 'Required if secrets are encrypted with customer-managed KMS keys',
                'cloudwatch_logs': 'Required for ESM monitoring and troubleshooting',
                'lambda_invoke': 'Required for ESM to invoke your Lambda function',
                'security_note': 'This policy follows least-privilege principles with appropriate conditions',
            },
        }

    def _validate_aws_parameters(
        self, region: str, account: str, cluster_name: str, cluster_uuid: str, partition: str
    ) -> Dict[str, str]:
        """Validate AWS parameters for MSK policy generation.

        Ensures all AWS identifiers follow proper formatting rules to prevent
        policy generation errors and security issues.

        Args:
            region: AWS region identifier (e.g., 'us-east-1')
            account: 12-digit AWS account ID
            cluster_name: MSK cluster name (1-64 alphanumeric chars, hyphens, underscores)
            cluster_uuid: MSK cluster UUID or '*' wildcard
            partition: AWS partition (aws, aws-cn, aws-us-gov)

        Returns:
            Dict mapping parameter names to error messages for invalid parameters
        """
        errors = {}

        # Validate AWS Region format: two lowercase letters, dash, region name, dash, number
        # Examples: us-east-1, eu-west-1, ap-southeast-2
        if not re.match(r'^[a-z]{2}-[a-z]+-\d+$', region):
            errors['region'] = f'Invalid AWS region format: {region}. Expected format: us-east-1'

        # Validate AWS Account ID: must be exactly 12 digits (no letters or special chars)
        if not re.match(r'^\d{12}$', account):
            errors['account'] = f'Invalid AWS account ID: {account}. Must be exactly 12 digits'

        # Validate MSK cluster name: 1-64 characters, alphanumeric plus hyphens and underscores
        if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', cluster_name):
            errors['cluster_name'] = (
                f'Invalid cluster name: {cluster_name}. Use alphanumeric, hyphens, underscores (1-64 chars)'
            )

        # Validate cluster UUID: either '*' wildcard for all clusters or specific UUID format
        if cluster_uuid != '*' and not re.match(r'^[a-zA-Z0-9-]{1,64}$', cluster_uuid):
            errors['cluster_uuid'] = (
                f"Invalid cluster UUID: {cluster_uuid}. Use alphanumeric/hyphens or '*'"
            )

        # Validate AWS partition: must be one of the three supported partitions
        # Handle FieldInfo objects by extracting the actual value
        actual_partition = partition if isinstance(partition, str) else 'aws'
        if actual_partition not in ['aws', 'aws-cn', 'aws-us-gov']:
            errors['partition'] = (
                f'Invalid partition: {actual_partition}. Must be: aws, aws-cn, or aws-us-gov'
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
        """Generate comprehensive IAM policy for MSK cluster access with ESM.

        Creates an IAM policy document that grants the necessary permissions for
        Lambda Event Source Mapping to connect to and consume from MSK Kafka clusters.
        Includes permissions for cluster operations, topic access, consumer groups,
        and VPC networking.

        Args:
            ctx: MCP context for logging
            region: AWS region where the MSK cluster is located
            account: AWS account ID that owns the MSK cluster
            cluster_name: Name of the MSK cluster
            cluster_uuid: UUID of the MSK cluster (use '*' for wildcard)
            partition: AWS partition (standard, China, or GovCloud)

        Returns:
            Dict containing complete IAM policy document with all required permissions
        """
        # Extract actual values from Pydantic Field objects if needed
        actual_cluster_uuid = cluster_uuid if isinstance(cluster_uuid, str) else '*'
        actual_partition = partition if isinstance(partition, str) else 'aws'

        # Validate all AWS parameters before generating policy to prevent malformed ARNs
        errors = self._validate_aws_parameters(
            region, account, cluster_name, actual_cluster_uuid, actual_partition
        )
        if errors:
            return {'error': 'Invalid parameters', 'details': errors}

        # Scrub sensitive data from cluster name before logging
        scrubbed_cluster_name = DataScrubber.scrub_text(cluster_name)
        await ctx.info(f'Generating Kafka policy for cluster {scrubbed_cluster_name}')

        # Return comprehensive IAM policy with all necessary permissions for MSK ESM
        return {
            'Version': '2012-10-17',
            'Statement': [
                {
                    # Basic cluster connectivity permissions - required to establish connection
                    'Effect': 'Allow',
                    'Action': ['kafka-cluster:Connect', 'kafka-cluster:DescribeCluster'],
                    'Resource': f'arn:{actual_partition}:kafka:{region}:{account}:cluster/{cluster_name}/{actual_cluster_uuid}',
                },
                {
                    # Topic-level permissions - required to read messages from Kafka topics
                    'Effect': 'Allow',
                    'Action': ['kafka-cluster:DescribeTopic', 'kafka-cluster:ReadData'],
                    'Resource': f'arn:{actual_partition}:kafka:{region}:{account}:topic/{cluster_name}/*',
                },
                {
                    # Consumer group permissions - required for ESM to manage consumer offsets
                    'Effect': 'Allow',
                    'Action': ['kafka-cluster:AlterGroup', 'kafka-cluster:DescribeGroup'],
                    'Resource': f'arn:{actual_partition}:kafka:{region}:{account}:group/{cluster_name}/*',
                },
                {
                    # MSK service-level permissions - required for cluster metadata and bootstrap brokers
                    'Effect': 'Allow',
                    'Action': ['kafka:DescribeClusterV2', 'kafka:GetBootstrapBrokers'],
                    'Resource': [
                        f'arn:{actual_partition}:kafka:{region}:{account}:cluster/{cluster_name}/{actual_cluster_uuid}',
                        f'arn:{actual_partition}:kafka:{region}:{account}:topic/{cluster_name}/*',
                        f'arn:{actual_partition}:kafka:{region}:{account}:group/{cluster_name}/*',
                    ],
                },
                {
                    # VPC networking permissions - required for ESM to operate within VPC
                    # ESM needs to create/manage network interfaces to connect to MSK in VPC
                    'Effect': 'Allow',
                    'Action': [
                        'ec2:CreateNetworkInterface',
                        'ec2:DescribeNetworkInterfaces',
                        'ec2:DescribeVpcs',
                        'ec2:DeleteNetworkInterface',
                        'ec2:DescribeSubnets',
                        'ec2:DescribeSecurityGroups',
                    ],
                    'Resource': '*',  # VPC operations require wildcard resource
                },
            ],
        }

    async def esm_msk_security_group_tool(
        self,
        ctx: Context,
        security_group_id: str = Field(description='Security group ID for MSK cluster'),
    ) -> Dict[str, Any]:
        """Generate SAM template with security group rules for MSK ESM connectivity.

        Creates CloudFormation resources for security group ingress and egress rules
        that allow proper communication between Lambda ESM and MSK cluster.
        The rules enable HTTPS (443) and Kafka broker (9092-9098) traffic.

        Args:
            ctx: MCP context for logging
            security_group_id: ID of the security group attached to MSK cluster

        Returns:
            Dict containing complete SAM template with security group rules
        """
        # Validate security group ID format to prevent template generation errors
        # AWS security group IDs follow specific patterns: sg-xxxxxxxx or sg-xxxxxxxxxxxxxxxxx
        if not re.match(r'^sg-[0-9a-f]{8}([0-9a-f]{9})?$', security_group_id):
            return {
                'error': f'Invalid security group ID format: {security_group_id}',
                'expected_format': "sg-xxxxxxxx or sg-xxxxxxxxxxxxxxxxx (8 or 17 hex characters after 'sg-')",
            }

        # Scrub sensitive data from security group ID before logging
        scrubbed_sg_id = DataScrubber.scrub_text(security_group_id)
        await ctx.info(f'Generating SAM template for security group {scrubbed_sg_id}')

        # Generate SAM template with security group rules for MSK ESM connectivity
        # Required rules:
        # - Ingress: HTTPS (443) for cluster management, Kafka brokers (9092-9098) for data
        # - Egress: All traffic within security group for internal communication
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
                # HTTPS ingress rule - allows secure communication for cluster management
                'MSKIngressHTTPS': {
                    'Type': 'AWS::EC2::SecurityGroupIngress',
                    'Properties': {
                        'GroupId': {'Ref': 'SecurityGroupId'},
                        'IpProtocol': 'tcp',
                        'FromPort': 443,
                        'ToPort': 443,
                        'SourceSecurityGroupId': {
                            'Ref': 'SecurityGroupId'
                        },  # Self-referencing for internal traffic
                        'Description': 'HTTPS access for MSK cluster management',
                    },
                },
                # Kafka broker ingress rule - allows data plane communication
                # Port range 9092-9098 covers all Kafka broker protocols (plaintext, TLS, SASL)
                'MSKIngressKafka': {
                    'Type': 'AWS::EC2::SecurityGroupIngress',
                    'Properties': {
                        'GroupId': {'Ref': 'SecurityGroupId'},
                        'IpProtocol': 'tcp',
                        'FromPort': 9092,
                        'ToPort': 9098,
                        'SourceSecurityGroupId': {
                            'Ref': 'SecurityGroupId'
                        },  # Self-referencing for internal traffic
                        'Description': 'Kafka broker access for MSK cluster data plane',
                    },
                },
                # Egress rule - allows all outbound traffic within the security group
                # Required for ESM to communicate back to MSK cluster and other services
                'MSKEgressAll': {
                    'Type': 'AWS::EC2::SecurityGroupEgress',
                    'Properties': {
                        'GroupId': {'Ref': 'SecurityGroupId'},
                        'IpProtocol': '-1',  # All protocols
                        'DestinationSecurityGroupId': {
                            'Ref': 'SecurityGroupId'
                        },  # Self-referencing
                        'Description': 'All outbound traffic within security group',
                    },
                },
            },
            'Outputs': {
                'SecurityGroupId': {
                    'Description': 'Security group ID with MSK ESM connectivity rules applied',
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
        """Validate deployment readiness and confirm user intent before ESM deployment.

        This tool performs pre-deployment validation by:
        1. Analyzing user prompt for deployment keywords
        2. Verifying SAM template exists in project directory
        3. Ensuring proper deployment workflow is followed

        Args:
            ctx: MCP context for logging
            prompt: User's input text to analyze for deployment intent
            project_directory: Path to SAM project containing template files

        Returns:
            Dict with deployment validation results and recommended actions
        """
        # Analyze user prompt for deployment-related keywords
        # This prevents accidental deployments and ensures user explicitly wants to deploy
        deploy_keywords = ['deploy', 'deployment', 'deploying']
        has_deploy_intent = any(keyword in prompt.lower() for keyword in deploy_keywords)

        if not has_deploy_intent:
            return {
                'deploy_intent_detected': False,
                'message': 'No deploy intent detected in prompt',
            }

        await ctx.info('Deploy intent detected, checking for template files')

        # Verify SAM template exists in project directory
        # SAM supports multiple template file formats - check for all supported types
        template_files = ['template.yaml', 'template.yml', 'template.json']
        template_found = False

        for template_file in template_files:
            template_path = os.path.join(project_directory, template_file)
            if os.path.exists(template_path):
                template_found = True
                break

        # Enforce SAM template usage for proper infrastructure as code practices
        if not template_found:
            return {
                'deploy_intent_detected': True,
                'error': 'No SAM template found in project directory. You must use a SAM template (template.yaml/yml/json) to deploy instead of using AWS CLI directly.',
            }

        # All validation checks passed - ready for deployment
        return {
            'deploy_intent_detected': True,
            'template_found': True,
            'message': 'Deploy intent confirmed and SAM template found. ESM configuration can be deployed using sam_deploy tool.',
            'recommended_action': f'Execute sam_deploy with project_directory: {project_directory}',
        }

    async def esm_networking_guidance_tool(
        self,
        ctx: Context,
        event_source: Optional[Literal['kafka', 'kinesis', 'dynamodb', 'sqs', 'general']] = Field(
            default='general', description='Event source type for networking guidance'
        ),
        networking_question: Optional[str] = Field(
            default='general', description='Specific networking question or concern'
        ),
    ) -> Dict[str, Any]:
        """Provides comprehensive networking guidance for VPC-based Event Source Mappings.

        This tool answers networking questions about ESM connectivity, VPC configuration,
        security groups, and troubleshooting network issues between Lambda and event sources.

        Args:
            ctx: The execution context
            event_source: Type of event source (kafka, kinesis, dynamodb, general)
            networking_question: Specific networking question or area of concern

        Returns:
            Dict containing networking guidance, requirements, and troubleshooting steps
        """
        await ctx.info(f'Providing networking guidance for {event_source} event source')

        # Common networking principles that apply to all ESM types
        common_networking_principles = [
            '# ESM Networking Fundamentals:',
            '',
            '## Critical Architectural Facts:',
            '- Lambda Event Source Mappings do NOT inherit the VPC configuration of the Lambda function',
            '- ESM uses the network configuration of the EVENT SOURCE (MSK cluster, Kinesis, etc.)',
            '- The Lambda function itself can be outside the VPC while ESM operates inside the VPC',
            '- ESM creates its own network interfaces in the event source VPC/subnets',
            '',
            '## General Requirements:',
            '- Event source must be accessible from its configured subnets',
            '- Security groups must allow ESM traffic to/from the event source',
            '- NAT Gateways required for private subnets to reach AWS services (Lambda, STS)',
            '- Route tables must be properly configured for internet access',
        ]

        # Kafka-specific networking guidance
        if event_source == 'kafka':
            specific_guidance = [
                '# Kafka (MSK) Networking Requirements:',
                '',
                '## VPC Configuration:',
                '- MSK cluster must be in private subnets (security best practice)',
                '- Minimum 2 subnets across different AZs for high availability',
                '- Each subnet needs route to NAT Gateway for outbound internet access',
                '',
                '## Security Group Rules:',
                '- **Inbound Rules:**',
                '  - Port 443 (HTTPS): For cluster management and metadata',
                '  - Ports 9092-9098 (Kafka): For broker communication',
                '  - Source: Self-referencing security group',
                '- **Outbound Rules:**',
                '  - All traffic to self-referencing security group',
                '  - Port 443 to 0.0.0.0/0 (for AWS service calls)',
                '',
                '## Lambda Function Placement:',
                '- Lambda function does NOT need to be in the VPC',
                '- ESM automatically handles VPC connectivity',
                '- Lambda function can remain in AWS managed VPC for better performance',
                '',
                '## Required AWS Service Access:',
                '- **Lambda API**: ESM needs to invoke your Lambda function',
                '- **STS API**: For IAM role assumption',
                '- **Secrets Manager**: If using secret-based authentication',
                '- **CloudWatch**: For logging and metrics',
                '',
                '## Network Troubleshooting:',
                '- Use `esm_kafka_troubleshoot` tool for connectivity issues',
                '- Check NAT Gateway routes for private subnet internet access',
                '- Verify security group rules allow required ports',
                '- Ensure IAM policies include VPC networking permissions',
            ]

        # Kinesis-specific networking guidance
        elif event_source == 'kinesis':
            specific_guidance = [
                '# Kinesis Networking Requirements:',
                '',
                '## VPC Configuration:',
                '- Kinesis streams are AWS managed services (no VPC placement)',
                '- ESM operates from AWS managed infrastructure',
                '- No custom VPC configuration required for Kinesis',
                '',
                '## Security Considerations:',
                '- Use IAM policies for access control',
                '- Enable encryption in transit and at rest',
                '- Consider VPC endpoints for enhanced security (optional)',
                '',
                '## Lambda Function Placement:',
                '- Lambda function can be in VPC or AWS managed VPC',
                '- No special networking configuration required',
                '- ESM handles all connectivity automatically',
            ]

        # DynamoDB-specific networking guidance
        elif event_source == 'dynamodb':
            specific_guidance = [
                '# DynamoDB Streams Networking Requirements:',
                '',
                '## VPC Configuration:',
                '- DynamoDB is an AWS managed service (no VPC placement)',
                '- DynamoDB Streams operate from AWS managed infrastructure',
                '- No custom VPC configuration required',
                '',
                '## Security Considerations:',
                '- Use IAM policies for table and stream access',
                '- Enable encryption at rest for DynamoDB table',
                '- Consider VPC endpoints for enhanced security (optional)',
                '',
                '## Lambda Function Placement:',
                '- Lambda function can be in VPC or AWS managed VPC',
                '- No special networking configuration required',
                '- ESM handles all connectivity automatically',
            ]

        # General networking guidance
        else:
            specific_guidance = [
                '# General ESM Networking Guidance:',
                '',
                '## Event Source Types:',
                '- **VPC-based**: MSK Kafka, Self-managed Kafka',
                '  - Requires VPC configuration, security groups, NAT gateways',
                '  - ESM operates within the event source VPC',
                '- **AWS Managed**: Kinesis, DynamoDB Streams, SQS',
                '  - No VPC configuration required',
                '  - ESM operates from AWS managed infrastructure',
                '',
                '## Common Networking Patterns:',
                '- Use private subnets for event sources (security)',
                '- NAT Gateways for outbound internet access',
                '- Security groups with least-privilege rules',
                '- Route tables configured for proper traffic flow',
            ]

        # Troubleshooting and next steps
        troubleshooting_steps = [
            '# Troubleshooting Network Issues:',
            '',
            '## Diagnostic Tools:',
            '- Use `esm_kafka_troubleshoot` for Kafka connectivity issues',
            '- Check CloudWatch logs for ESM error messages',
            '- Verify security group rules and route table configuration',
            '',
            '## Common Solutions:',
            '- Update security group rules using `esm_msk_security_group` tool',
            '- Validate IAM policies using `esm_msk_policy` tool',
            '- Check NAT Gateway and internet gateway configuration',
            '',
            '## Best Practices:',
            '- Always use latest Lambda runtime versions (python3.13, nodejs22.x)',
            '- Avoid deprecated runtimes like python3.9 which will be unsupported',
            '- Ensure proper subnet routing to AWS services',
        ]

        # Generate configuration templates if requested
        configuration_templates = []
        if event_source == 'kafka':
            configuration_templates = [
                '# Sample Security Group Configuration:',
                'Use `esm_msk_security_group` tool to generate proper rules',
                '',
                '# Sample IAM Policy:',
                'Use `esm_msk_policy` tool to generate least-privilege permissions',
            ]
        # SQS-specific networking guidance
        elif event_source == 'sqs':
            specific_guidance = [
                '# SQS Networking Requirements:',
                '',
                '## Network Architecture:',
                '- SQS is a fully managed service - no VPC configuration required',
                '- Lambda ESM connects to SQS over AWS backbone network',
                '- No security groups or subnets needed for SQS connectivity',
                '- Lambda function can be in VPC or outside VPC without affecting SQS access',
                '',
                '## Lambda Function Placement:',
                '- **Outside VPC (Recommended)**: Fastest cold start, no networking overhead',
                '- **Inside VPC**: Requires NAT Gateway for SQS access, slower cold starts',
                '- ESM polling happens outside your VPC regardless of Lambda placement',
                '',
                '## Security Considerations:',
                '- **IAM Policies**: Primary security mechanism for SQS access',
                '- **Queue Policies**: Resource-based policies for cross-account access',
                '- **Encryption**: Use SQS-managed (SSE-SQS) or KMS encryption',
                '- **VPC Endpoints**: Optional for Lambda functions in VPC (cost optimization)',
                '',
                '## Performance Optimization:',
                '- **No network latency concerns**: SQS is AWS-managed service',
                '- **Concurrency**: Use ScalingConfig MaximumConcurrency for control',
                '- **Batching**: Configure BatchSize and MaximumBatchingWindowInSeconds',
                '- **Monitoring**: Focus on queue depth and message age metrics',
                '',
                '## Common Configurations:',
                '- **Standard Queue**: No special networking requirements',
                '- **FIFO Queue**: Same networking as standard, ordering handled by SQS',
                '- **Dead Letter Queue**: Separate queue, same networking principles',
                '- **Cross-Region**: SQS and Lambda should be in same region for best performance',
            ]

            troubleshooting_steps = [
                '# SQS ESM Troubleshooting:',
                '',
                '## Common Issues:',
                '1. **Permission Errors**:',
                '   - Check IAM policy has sqs:ReceiveMessage, sqs:DeleteMessage permissions',
                '   - Verify queue policy allows Lambda service access',
                '   - Ensure queue ARN is correct in ESM configuration',
                '',
                '2. **Messages Not Processing**:',
                '   - Check ESM is enabled and in "Enabled" state',
                '   - Verify Lambda function is not throttled (check ConcurrentExecutions)',
                '   - Check queue visibility timeout (should be 6x Lambda timeout)',
                '   - Monitor ApproximateNumberOfMessages metric',
                '',
                '3. **Performance Issues**:',
                '   - Increase MaximumConcurrency in ScalingConfig',
                '   - Optimize BatchSize for your use case',
                '   - Check Lambda function duration and memory allocation',
                '   - Monitor ApproximateAgeOfOldestMessage',
                '',
                '4. **Cost Optimization**:',
                '   - Use larger batch sizes to reduce invocation count',
                '   - Set appropriate MaximumBatchingWindowInSeconds',
                '   - Consider Reserved Concurrency to control costs',
                '   - Enable ReportBatchItemFailures for partial batch processing',
            ]

            configuration_templates = [
                '# SQS ESM Configuration Template:',
                '',
                '## Basic ESM Configuration:',
                '```yaml',
                'EventSourceMapping:',
                '  Type: AWS::Lambda::EventSourceMapping',
                '  Properties:',
                '    EventSourceArn: !GetAtt MyQueue.Arn',
                '    FunctionName: !Ref MyLambdaFunction',
                '    BatchSize: 10',
                '    MaximumBatchingWindowInSeconds: 5',
                '    FunctionResponseTypes:',
                '      - ReportBatchItemFailures',
                '    ScalingConfig:',
                '      MaximumConcurrency: 100',
                '```',
                '',
                '## IAM Policy Template:',
                'Use `esm_sqs_policy` tool to generate least-privilege permissions',
                '',
                '## Monitoring Template:',
                '```yaml',
                'QueueDepthAlarm:',
                '  Type: AWS::CloudWatch::Alarm',
                '  Properties:',
                '    MetricName: ApproximateNumberOfMessages',
                '    Namespace: AWS/SQS',
                '    Statistic: Average',
                '    Threshold: 1000',
                '    ComparisonOperator: GreaterThanThreshold',
                '```',
            ]
        # Default/general networking guidance
        else:
            specific_guidance = [
                '# General ESM Networking Guidance:',
                '',
                '## Event Source Types:',
                '- **SQS**: No VPC configuration needed, fully managed',
                '- **Kinesis/DynamoDB**: Regional services, no VPC required',
                '- **Kafka/MSK**: Requires VPC configuration and security groups',
                '',
                '## Best Practices:',
                '- Place Lambda functions outside VPC when possible for better performance',
                '- Use VPC only when Lambda needs to access VPC resources',
                '- Configure appropriate security groups for VPC-based event sources',
                '- Monitor networking costs and performance metrics',
            ]

            troubleshooting_steps = [
                '# General Troubleshooting Steps:',
                '1. Identify your event source type',
                '2. Use specific networking guidance tools for your event source',
                '3. Check IAM permissions and resource policies',
                '4. Monitor CloudWatch metrics for performance issues',
            ]

            configuration_templates = [
                '# Use specific tools for detailed configuration:',
                '- SQS: Use `esm_sqs_concurrency_guidance` tool',
                '- Kafka: Use `esm_msk_policy` and `esm_msk_security_group` tools',
                '- General: Use `esm_guidance` tool with specific event source',
            ]

        return {
            'networking_guidance': {
                'event_source': event_source,
                'common_principles': common_networking_principles,
                'specific_guidance': specific_guidance,
                'troubleshooting': troubleshooting_steps,
                'configuration_templates': configuration_templates,
                'next_actions': [
                    f'For {event_source} setup: Use esm_guidance tool',
                    'For Kafka policy generation: Use esm_msk_policy tool',
                    'For Kafka security groups: Use esm_msk_security_group tool',
                    'For SQS policy generation: Use esm_sqs_policy tool',
                    'For SQS concurrency guidance: Use esm_sqs_concurrency_guidance tool',
                    'For troubleshooting: Use esm_kafka_troubleshoot tool (Kafka) or check SQS metrics',
                ],
            }
        }
