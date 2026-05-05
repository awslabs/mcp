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

"""Security-approved IAM policy templates for ESM configurations.

These templates are pre-reviewed by security team and use parameter substitution
instead of LLM generation to ensure deterministic, secure policy creation.

CRITICAL: These templates must NOT be modified without security team approval.
Only parameter substitution is allowed - no structural changes to policies.
"""

import copy
import json
import re
from typing import Any, Dict, List


# MSK Kafka ESM Policy Template - Security Approved
# This template follows AWS documentation: https://docs.aws.amazon.com/lambda/latest/dg/with-msk-permissions.html
KAFKA_ESM_POLICY_TEMPLATE = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Sid': 'KafkaClusterAccess',
            'Effect': 'Allow',
            'Action': ['kafka-cluster:Connect', 'kafka-cluster:DescribeCluster'],
            'Resource': 'arn:${partition}:kafka:${region}:${account}:cluster/${cluster_name}/${cluster_uuid}',
        },
        {
            'Sid': 'KafkaTopicAccess',
            'Effect': 'Allow',
            'Action': ['kafka-cluster:DescribeTopic', 'kafka-cluster:ReadData'],
            'Resource': 'arn:${partition}:kafka:${region}:${account}:topic/${cluster_name}/${topic_pattern}',
            'Condition': {'StringLike': {'kafka-cluster:topicName': '${topic_pattern}'}},
        },
        {
            'Sid': 'KafkaConsumerGroupAccess',
            'Effect': 'Allow',
            'Action': ['kafka-cluster:AlterGroup', 'kafka-cluster:DescribeGroup'],
            'Resource': 'arn:${partition}:kafka:${region}:${account}:group/${cluster_name}/${consumer_group_pattern}',
        },
        {
            'Sid': 'MSKServiceAccess',
            'Effect': 'Allow',
            'Action': ['kafka:DescribeClusterV2', 'kafka:GetBootstrapBrokers'],
            'Resource': 'arn:${partition}:kafka:${region}:${account}:cluster/${cluster_name}/${cluster_uuid}',
        },
        {
            'Sid': 'VPCNetworkingAccess',
            'Effect': 'Allow',
            'Action': [
                'ec2:CreateNetworkInterface',
                'ec2:DescribeNetworkInterfaces',
                'ec2:DeleteNetworkInterface',
                'ec2:AttachNetworkInterface',
                'ec2:DetachNetworkInterface',
                'ec2:DescribeVpcs',
                'ec2:DescribeSubnets',
                'ec2:DescribeSecurityGroups',
            ],
            'Resource': '*',
        },
        {
            'Sid': 'CloudWatchLogsAccess',
            'Effect': 'Allow',
            'Action': [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
                'logs:DescribeLogGroups',
                'logs:DescribeLogStreams',
            ],
            'Resource': 'arn:${partition}:logs:${region}:${account}:log-group:/aws/lambda/${function_name}*',
        },
    ],
}

# Self-Managed Kafka ESM Policy Template - Security Approved
SELF_MANAGED_KAFKA_ESM_POLICY_TEMPLATE = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Sid': 'VPCNetworkingAccess',
            'Effect': 'Allow',
            'Action': [
                'ec2:CreateNetworkInterface',
                'ec2:DescribeNetworkInterfaces',
                'ec2:DeleteNetworkInterface',
                'ec2:AttachNetworkInterface',
                'ec2:DetachNetworkInterface',
                'ec2:DescribeVpcs',
                'ec2:DescribeSubnets',
                'ec2:DescribeSecurityGroups',
            ],
            'Resource': '*',
        },
        {
            'Sid': 'SecretsManagerAccess',
            'Effect': 'Allow',
            'Action': ['secretsmanager:GetSecretValue', 'secretsmanager:DescribeSecret'],
            'Resource': 'arn:${partition}:secretsmanager:${region}:${account}:secret:${secret_name_pattern}',
            'Condition': {'StringEquals': {'secretsmanager:ResourceTag/LambdaESM': 'true'}},
        },
        {
            'Sid': 'KMSDecryptAccess',
            'Effect': 'Allow',
            'Action': ['kms:Decrypt', 'kms:GenerateDataKey'],
            'Resource': 'arn:${partition}:kms:${region}:${account}:key/${kms_key_id}',
            'Condition': {
                'StringEquals': {'kms:ViaService': 'secretsmanager.${region}.amazonaws.com'}
            },
        },
        {
            'Sid': 'CloudWatchLogsAccess',
            'Effect': 'Allow',
            'Action': [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
                'logs:DescribeLogGroups',
                'logs:DescribeLogStreams',
            ],
            'Resource': 'arn:${partition}:logs:${region}:${account}:log-group:/aws/lambda/${function_name}*',
        },
    ],
}

# SQS ESM Policy Template - Security Approved
SQS_ESM_POLICY_TEMPLATE = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Sid': 'SQSQueueAccess',
            'Effect': 'Allow',
            'Action': [
                'sqs:ReceiveMessage',
                'sqs:DeleteMessage',
                'sqs:GetQueueAttributes',
                'sqs:GetQueueUrl',
            ],
            'Resource': 'arn:${partition}:sqs:${region}:${account}:${queue_name}',
        },
        {
            'Sid': 'SQSDeadLetterQueueAccess',
            'Effect': 'Allow',
            'Action': ['sqs:SendMessage', 'sqs:GetQueueAttributes', 'sqs:GetQueueUrl'],
            'Resource': 'arn:${partition}:sqs:${region}:${account}:${queue_name}-dlq',
            'Condition': {'StringEquals': {'aws:SourceAccount': '${account}'}},
        },
        {
            'Sid': 'CloudWatchLogsAccess',
            'Effect': 'Allow',
            'Action': ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
            'Resource': 'arn:${partition}:logs:${region}:${account}:log-group:/aws/lambda/${function_name}*',
        },
    ],
}

# Kinesis ESM Policy Template - Security Approved
KINESIS_ESM_POLICY_TEMPLATE = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Sid': 'KinesisStreamAccess',
            'Effect': 'Allow',
            'Action': [
                'kinesis:DescribeStream',
                'kinesis:DescribeStreamSummary',
                'kinesis:GetRecords',
                'kinesis:GetShardIterator',
                'kinesis:ListShards',
                'kinesis:ListStreams',
            ],
            'Resource': 'arn:${partition}:kinesis:${region}:${account}:stream/${stream_name}',
        },
        {
            'Sid': 'CloudWatchLogsAccess',
            'Effect': 'Allow',
            'Action': ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
            'Resource': 'arn:${partition}:logs:${region}:${account}:log-group:/aws/lambda/${function_name}*',
        },
    ],
}

# DynamoDB Streams ESM Policy Template - Security Approved
DYNAMODB_ESM_POLICY_TEMPLATE = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Sid': 'DynamoDBStreamAccess',
            'Effect': 'Allow',
            'Action': [
                'dynamodb:DescribeStream',
                'dynamodb:GetRecords',
                'dynamodb:GetShardIterator',
                'dynamodb:ListStreams',
            ],
            'Resource': 'arn:${partition}:dynamodb:${region}:${account}:table/${table_name}/stream/*',
        },
        {
            'Sid': 'CloudWatchLogsAccess',
            'Effect': 'Allow',
            'Action': ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
            'Resource': 'arn:${partition}:logs:${region}:${account}:log-group:/aws/lambda/${function_name}*',
        },
    ],
}


class SecurePolicyGenerator:
    """Secure IAM policy generator using pre-approved templates.

    This class ONLY performs parameter substitution on security-approved templates.
    It does NOT generate policy structure or modify permissions.
    """

    @staticmethod
    def validate_aws_parameters(region: str, account: str, **kwargs) -> List[str]:
        """Validate AWS parameters for policy generation."""
        errors = []

        # Region validation
        if not re.match(r'^[a-z]{2}-[a-z]+-\d+$', region):
            errors.append(f'Invalid region format: {region}')

        # Account validation
        if not re.match(r'^\d{12}$', account):
            errors.append(f'Invalid account ID: {account}')

        return errors

    @staticmethod
    def generate_kafka_esm_policy(
        region: str,
        account: str,
        cluster_name: str,
        cluster_uuid: str,
        function_name: str,
        topic_pattern: str = '*',
        consumer_group_pattern: str = '*',
        partition: str = 'aws',
    ) -> Dict[str, Any]:
        """Generate MSK Kafka ESM policy using security-approved template.

        This function ONLY substitutes parameters into the pre-approved template.
        It does NOT generate policy structure or modify permissions.

        Args:
            region: AWS region (e.g., 'us-east-1')
            account: 12-digit AWS account ID
            cluster_name: MSK cluster name
            cluster_uuid: MSK cluster UUID
            function_name: Lambda function name
            topic_pattern: Kafka topic pattern (default: '*')
            consumer_group_pattern: Consumer group pattern (default: '*')
            partition: AWS partition (default: 'aws')

        Returns:
            Dict containing the complete IAM policy document

        Raises:
            ValueError: If any parameters are invalid
        """
        # Validate all parameters
        errors = SecurePolicyGenerator.validate_aws_parameters(region, account)

        # Additional validations
        if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', cluster_name):
            errors.append(f'Invalid cluster name: {cluster_name}')

        if errors:
            raise ValueError(f'Invalid parameters: {errors}')

        # Use template substitution - NO policy generation
        policy = copy.deepcopy(KAFKA_ESM_POLICY_TEMPLATE)
        policy_str = json.dumps(policy)

        # Substitute parameters in template
        substitutions = {
            '${partition}': partition,
            '${region}': region,
            '${account}': account,
            '${cluster_name}': cluster_name,
            '${cluster_uuid}': cluster_uuid,
            '${function_name}': function_name,
            '${topic_pattern}': topic_pattern,
            '${consumer_group_pattern}': consumer_group_pattern,
        }

        for placeholder, value in substitutions.items():
            policy_str = policy_str.replace(placeholder, value)

        return json.loads(policy_str)

    @staticmethod
    def generate_sqs_esm_policy(
        region: str, account: str, queue_name: str, function_name: str, partition: str = 'aws'
    ) -> Dict[str, Any]:
        """Generate SQS ESM policy using security-approved template."""
        # Validate parameters
        errors = SecurePolicyGenerator.validate_aws_parameters(region, account)

        if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', queue_name):
            errors.append(f'Invalid queue name: {queue_name}')

        if errors:
            raise ValueError(f'Invalid parameters: {errors}')

        # Template substitution only
        policy = copy.deepcopy(SQS_ESM_POLICY_TEMPLATE)
        policy_str = json.dumps(policy)

        substitutions = {
            '${partition}': partition,
            '${region}': region,
            '${account}': account,
            '${queue_name}': queue_name,
            '${function_name}': function_name,
        }

        for placeholder, value in substitutions.items():
            policy_str = policy_str.replace(placeholder, value)

        return json.loads(policy_str)

    @staticmethod
    def generate_kinesis_esm_policy(
        region: str, account: str, stream_name: str, function_name: str, partition: str = 'aws'
    ) -> Dict[str, Any]:
        """Generate Kinesis ESM policy using security-approved template."""
        # Validate parameters
        errors = SecurePolicyGenerator.validate_aws_parameters(region, account)

        if not re.match(r'^[a-zA-Z0-9_.-]{1,128}$', stream_name):
            errors.append(f'Invalid stream name: {stream_name}')

        if errors:
            raise ValueError(f'Invalid parameters: {errors}')

        # Template substitution only
        policy = copy.deepcopy(KINESIS_ESM_POLICY_TEMPLATE)
        policy_str = json.dumps(policy)

        substitutions = {
            '${partition}': partition,
            '${region}': region,
            '${account}': account,
            '${stream_name}': stream_name,
            '${function_name}': function_name,
        }

        for placeholder, value in substitutions.items():
            policy_str = policy_str.replace(placeholder, value)

        return json.loads(policy_str)

    @staticmethod
    def generate_dynamodb_esm_policy(
        region: str, account: str, table_name: str, function_name: str, partition: str = 'aws'
    ) -> Dict[str, Any]:
        """Generate DynamoDB Streams ESM policy using security-approved template."""
        # Validate parameters
        errors = SecurePolicyGenerator.validate_aws_parameters(region, account)

        if not re.match(r'^[a-zA-Z0-9_.-]{3,255}$', table_name):
            errors.append(f'Invalid table name: {table_name}')

        if errors:
            raise ValueError(f'Invalid parameters: {errors}')

        # Template substitution only
        policy = copy.deepcopy(DYNAMODB_ESM_POLICY_TEMPLATE)
        policy_str = json.dumps(policy)

        substitutions = {
            '${partition}': partition,
            '${region}': region,
            '${account}': account,
            '${table_name}': table_name,
            '${function_name}': function_name,
        }

        for placeholder, value in substitutions.items():
            policy_str = policy_str.replace(placeholder, value)

        return json.loads(policy_str)
