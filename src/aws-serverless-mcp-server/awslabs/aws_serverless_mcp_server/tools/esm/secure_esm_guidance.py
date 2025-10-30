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

"""Secure ESM guidance tool using pre-approved IAM policy templates.

This module addresses security concerns by:
1. Using deterministic, security-approved IAM policy templates
2. Scoping permissions to specific resources instead of wildcards
3. Validating all input parameters before policy generation
4. Separating policy structure from parameter substitution
"""

from awslabs.aws_serverless_mcp_server.templates.iam_policies import SecurePolicyGenerator
from awslabs.aws_serverless_mcp_server.tools.common.base_tool import BaseTool
from awslabs.aws_serverless_mcp_server.utils.data_scrubber import DataScrubber
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict


class SecureEsmGuidanceTool(BaseTool):
    """Secure ESM guidance tool using pre-approved IAM policy templates.

    This tool addresses security team concerns by:
    - Using deterministic policy generation (no LLM-generated policies)
    - Scoping permissions to specific resources (no Resource: *)
    - Validating all parameters before policy generation
    - Using security-approved templates only
    """

    def __init__(self, mcp: FastMCP, allow_write: bool = False):
        """Initialize the secure ESM guidance tool."""
        super().__init__(allow_write=allow_write)
        self.allow_write = allow_write

        # Register secure policy generation tools
        mcp.tool(
            name='secure_esm_msk_policy',
            description='Generate security-approved IAM policy for MSK Kafka ESM with scoped permissions. Uses pre-approved templates, not LLM generation.',
        )(self.secure_esm_msk_policy_tool)

        mcp.tool(
            name='secure_esm_sqs_policy',
            description='Generate security-approved IAM policy for SQS ESM with scoped permissions. Uses pre-approved templates, not LLM generation.',
        )(self.secure_esm_sqs_policy_tool)

        mcp.tool(
            name='secure_esm_kinesis_policy',
            description='Generate security-approved IAM policy for Kinesis ESM with scoped permissions. Uses pre-approved templates, not LLM generation.',
        )(self.secure_esm_kinesis_policy_tool)

        mcp.tool(
            name='secure_esm_dynamodb_policy',
            description='Generate security-approved IAM policy for DynamoDB Streams ESM with scoped permissions. Uses pre-approved templates, not LLM generation.',
        )(self.secure_esm_dynamodb_policy_tool)

    async def secure_esm_msk_policy_tool(
        self,
        ctx: Context,
        region: str = Field(description='AWS region (e.g., us-east-1)'),
        account: str = Field(description='AWS account ID (12 digits)'),
        cluster_name: str = Field(description='MSK cluster name'),
        cluster_uuid: str = Field(description='MSK cluster UUID'),
        function_name: str = Field(
            description='Lambda function name that will process Kafka events'
        ),
        topic_pattern: str = Field(default='*', description='Kafka topic pattern (default: *)'),
        consumer_group_pattern: str = Field(
            default='*', description='Consumer group pattern (default: *)'
        ),
        partition: str = Field(
            default='aws', description='AWS partition (aws, aws-cn, aws-us-gov)'
        ),
    ) -> Dict[str, Any]:
        """Generate security-approved IAM policy for MSK Kafka ESM.

        This tool uses pre-approved policy templates and only performs parameter substitution.
        It does NOT generate policy structure or permissions via LLM.

        Key Security Features:
        - Deterministic policy generation (same inputs = same output)
        - Security-approved template structure
        - Comprehensive parameter validation

        Args:
            ctx: MCP context for logging
            region: AWS region where MSK cluster is located
            account: 12-digit AWS account ID
            cluster_name: Name of the MSK cluster
            cluster_uuid: UUID of the MSK cluster
            function_name: Lambda function name for processing events
            topic_pattern: Kafka topic access pattern
            consumer_group_pattern: Consumer group access pattern
            partition: AWS partition

        Returns:
            Dict containing the complete, security-approved IAM policy document
        """
        self.checkToolAccess()

        # Scrub sensitive data before logging
        scrubbed_cluster_name = DataScrubber.scrub_text(cluster_name)
        scrubbed_function_name = DataScrubber.scrub_text(function_name)

        await ctx.info(
            f'Generating secure MSK policy for cluster {scrubbed_cluster_name}, function {scrubbed_function_name}'
        )

        try:
            # Extract actual values from Pydantic Field objects if needed
            actual_topic_pattern = topic_pattern if isinstance(topic_pattern, str) else '*'
            actual_consumer_group_pattern = (
                consumer_group_pattern if isinstance(consumer_group_pattern, str) else '*'
            )
            actual_partition = partition if isinstance(partition, str) else 'aws'

            # Use security-approved template with parameter validation
            policy = SecurePolicyGenerator.generate_kafka_esm_policy(
                region=region,
                account=account,
                cluster_name=cluster_name,
                cluster_uuid=cluster_uuid,
                function_name=function_name,
                topic_pattern=actual_topic_pattern,
                consumer_group_pattern=actual_consumer_group_pattern,
                partition=actual_partition,
            )

            return {
                'policy_document': policy,
                'security_features': {
                    'deterministic_generation': True,
                    'security_approved_template': True,
                    'comprehensive_parameter_validation': True,
                },
                'policy_summary': {
                    'kafka_cluster_access': f'Scoped to cluster {cluster_name}',
                    'vpc_networking': 'Standard VPC permissions for ESM',
                    'topic_access': f'Pattern: {topic_pattern}',
                    'consumer_group_access': f'Pattern: {consumer_group_pattern}',
                    'cloudwatch_logs': f'Scoped to function {function_name}',
                },
                'usage_instructions': {
                    'attach_to': 'Lambda execution role',
                    'deployment': 'Use in SAM template or CloudFormation',
                    'validation': 'Policy structure is pre-approved by security team',
                },
            }

        except ValueError as e:
            return {
                'error': 'Parameter validation failed',
                'details': str(e),
                'security_note': 'All parameters must pass validation before policy generation',
            }

    async def secure_esm_sqs_policy_tool(
        self,
        ctx: Context,
        region: str = Field(description='AWS region (e.g., us-east-1)'),
        account: str = Field(description='AWS account ID (12 digits)'),
        queue_name: str = Field(description='SQS queue name'),
        function_name: str = Field(
            description='Lambda function name that will process SQS messages'
        ),
        partition: str = Field(
            default='aws', description='AWS partition (aws, aws-cn, aws-us-gov)'
        ),
    ) -> Dict[str, Any]:
        """Generate security-approved IAM policy for SQS ESM.

        This tool uses pre-approved policy templates and only performs parameter substitution.
        All permissions are scoped to specific queue ARNs.

        Args:
            ctx: MCP context for logging
            region: AWS region where SQS queue is located
            account: 12-digit AWS account ID
            queue_name: Name of the SQS queue
            function_name: Lambda function name for processing messages
            partition: AWS partition

        Returns:
            Dict containing the complete, security-approved IAM policy document
        """
        self.checkToolAccess()

        # Scrub sensitive data before logging
        scrubbed_queue_name = DataScrubber.scrub_text(queue_name)
        scrubbed_function_name = DataScrubber.scrub_text(function_name)

        await ctx.info(
            f'Generating secure SQS policy for queue {scrubbed_queue_name}, function {scrubbed_function_name}'
        )

        try:
            # Extract actual value from Pydantic Field object if needed
            actual_partition = partition if isinstance(partition, str) else 'aws'

            # Use security-approved template with parameter validation
            policy = SecurePolicyGenerator.generate_sqs_esm_policy(
                region=region,
                account=account,
                queue_name=queue_name,
                function_name=function_name,
                partition=actual_partition,
            )

            return {
                'policy_document': policy,
                'security_features': {
                    'deterministic_generation': True,
                    'scoped_queue_permissions': True,
                    'dlq_support_included': True,
                    'security_approved_template': True,
                },
                'policy_summary': {
                    'queue_access': f'Scoped to queue {queue_name}',
                    'dlq_access': f'Scoped to {queue_name}-dlq',
                    'cloudwatch_logs': f'Scoped to function {function_name}',
                },
                'usage_instructions': {
                    'attach_to': 'Lambda execution role',
                    'deployment': 'Use in SAM template or CloudFormation',
                    'validation': 'Policy structure is pre-approved by security team',
                },
            }

        except ValueError as e:
            return {
                'error': 'Parameter validation failed',
                'details': str(e),
                'security_note': 'All parameters must pass validation before policy generation',
            }

    async def secure_esm_kinesis_policy_tool(
        self,
        ctx: Context,
        region: str = Field(description='AWS region (e.g., us-east-1)'),
        account: str = Field(description='AWS account ID (12 digits)'),
        stream_name: str = Field(description='Kinesis stream name'),
        function_name: str = Field(
            description='Lambda function name that will process Kinesis records'
        ),
        partition: str = Field(
            default='aws', description='AWS partition (aws, aws-cn, aws-us-gov)'
        ),
    ) -> Dict[str, Any]:
        """Generate security-approved IAM policy for Kinesis ESM.

        This tool uses pre-approved policy templates and only performs parameter substitution.
        All permissions are scoped to specific stream ARNs.

        Args:
            ctx: MCP context for logging
            region: AWS region where Kinesis stream is located
            account: 12-digit AWS account ID
            stream_name: Name of the Kinesis stream
            function_name: Lambda function name for processing records
            partition: AWS partition

        Returns:
            Dict containing the complete, security-approved IAM policy document
        """
        self.checkToolAccess()

        # Scrub sensitive data before logging
        scrubbed_stream_name = DataScrubber.scrub_text(stream_name)
        scrubbed_function_name = DataScrubber.scrub_text(function_name)

        await ctx.info(
            f'Generating secure Kinesis policy for stream {scrubbed_stream_name}, function {scrubbed_function_name}'
        )

        try:
            # Extract actual value from Pydantic Field object if needed
            actual_partition = partition if isinstance(partition, str) else 'aws'

            # Use security-approved template with parameter validation
            policy = SecurePolicyGenerator.generate_kinesis_esm_policy(
                region=region,
                account=account,
                stream_name=stream_name,
                function_name=function_name,
                partition=actual_partition,
            )

            return {
                'policy_document': policy,
                'security_features': {
                    'deterministic_generation': True,
                    'scoped_stream_permissions': True,
                    'security_approved_template': True,
                },
                'policy_summary': {
                    'stream_access': f'Scoped to stream {stream_name}',
                    'cloudwatch_logs': f'Scoped to function {function_name}',
                },
                'usage_instructions': {
                    'attach_to': 'Lambda execution role',
                    'deployment': 'Use in SAM template or CloudFormation',
                    'validation': 'Policy structure is pre-approved by security team',
                },
            }

        except ValueError as e:
            return {
                'error': 'Parameter validation failed',
                'details': str(e),
                'security_note': 'All parameters must pass validation before policy generation',
            }

    async def secure_esm_dynamodb_policy_tool(
        self,
        ctx: Context,
        region: str = Field(description='AWS region (e.g., us-east-1)'),
        account: str = Field(description='AWS account ID (12 digits)'),
        table_name: str = Field(description='DynamoDB table name'),
        function_name: str = Field(
            description='Lambda function name that will process DynamoDB stream records'
        ),
        partition: str = Field(
            default='aws', description='AWS partition (aws, aws-cn, aws-us-gov)'
        ),
    ) -> Dict[str, Any]:
        """Generate security-approved IAM policy for DynamoDB Streams ESM.

        This tool uses pre-approved policy templates and only performs parameter substitution.
        All permissions are scoped to specific table stream ARNs.

        Args:
            ctx: MCP context for logging
            region: AWS region where DynamoDB table is located
            account: 12-digit AWS account ID
            table_name: Name of the DynamoDB table
            function_name: Lambda function name for processing stream records
            partition: AWS partition

        Returns:
            Dict containing the complete, security-approved IAM policy document
        """
        self.checkToolAccess()

        # Scrub sensitive data before logging
        scrubbed_table_name = DataScrubber.scrub_text(table_name)
        scrubbed_function_name = DataScrubber.scrub_text(function_name)

        await ctx.info(
            f'Generating secure DynamoDB policy for table {scrubbed_table_name}, function {scrubbed_function_name}'
        )

        try:
            # Extract actual value from Pydantic Field object if needed
            actual_partition = partition if isinstance(partition, str) else 'aws'

            # Use security-approved template with parameter validation
            policy = SecurePolicyGenerator.generate_dynamodb_esm_policy(
                region=region,
                account=account,
                table_name=table_name,
                function_name=function_name,
                partition=actual_partition,
            )

            return {
                'policy_document': policy,
                'security_features': {
                    'deterministic_generation': True,
                    'scoped_table_permissions': True,
                    'security_approved_template': True,
                },
                'policy_summary': {
                    'table_stream_access': f'Scoped to table {table_name} streams',
                    'cloudwatch_logs': f'Scoped to function {function_name}',
                },
                'usage_instructions': {
                    'attach_to': 'Lambda execution role',
                    'deployment': 'Use in SAM template or CloudFormation',
                    'validation': 'Policy structure is pre-approved by security team',
                },
            }

        except ValueError as e:
            return {
                'error': 'Parameter validation failed',
                'details': str(e),
                'security_note': 'All parameters must pass validation before policy generation',
            }
