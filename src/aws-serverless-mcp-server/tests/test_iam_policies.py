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

"""Tests for IAM policy templates."""

import pytest
from awslabs.aws_serverless_mcp_server.templates.iam_policies import SecurePolicyGenerator


class TestSecurePolicyGenerator:
    """Test cases for secure policy generator."""

    def test_validate_aws_parameters_valid_inputs(self):
        """Test validation with valid AWS parameters."""
        errors = SecurePolicyGenerator.validate_aws_parameters(
            region='us-east-1', account='123456789012'
        )
        assert errors == []

    def test_validate_aws_parameters_invalid_region(self):
        """Test validation with invalid region format."""
        errors = SecurePolicyGenerator.validate_aws_parameters(
            region='invalid-region', account='123456789012'
        )
        assert len(errors) == 1
        assert 'Invalid region format' in errors[0]

    def test_validate_aws_parameters_invalid_account(self):
        """Test validation with invalid account ID."""
        errors = SecurePolicyGenerator.validate_aws_parameters(
            region='us-east-1', account='invalid-account'
        )
        assert len(errors) == 1
        assert 'Invalid account ID' in errors[0]

    def test_validate_aws_parameters_both_invalid(self):
        """Test validation with both invalid region and account."""
        errors = SecurePolicyGenerator.validate_aws_parameters(
            region='invalid-region', account='invalid-account'
        )
        assert len(errors) == 2
        assert any('Invalid region format' in error for error in errors)
        assert any('Invalid account ID' in error for error in errors)

    def test_validate_aws_parameters_edge_cases(self):
        """Test validation with edge case inputs."""
        # Test with empty strings
        errors = SecurePolicyGenerator.validate_aws_parameters(region='', account='')
        assert len(errors) == 2

        # Test with None values - this will cause TypeError in regex
        with pytest.raises(TypeError):
            SecurePolicyGenerator.validate_aws_parameters(region=None, account=None)  # type: ignore

    def test_generate_kafka_esm_policy_basic(self):
        """Test basic Kafka ESM policy generation."""
        policy = SecurePolicyGenerator.generate_kafka_esm_policy(
            region='us-east-1',
            account='123456789012',
            cluster_name='test-cluster',
            cluster_uuid='12345678-1234-1234-1234-123456789012',
            function_name='test-function',
        )

        assert 'Version' in policy
        assert 'Statement' in policy
        assert policy['Version'] == '2012-10-17'
        assert len(policy['Statement']) > 0

    def test_generate_kafka_esm_policy_with_patterns(self):
        """Test Kafka ESM policy generation with custom patterns."""
        policy = SecurePolicyGenerator.generate_kafka_esm_policy(
            region='us-east-1',
            account='123456789012',
            cluster_name='test-cluster',
            cluster_uuid='12345678-1234-1234-1234-123456789012',
            function_name='test-function',
            topic_pattern='test-topic-*',
            consumer_group_pattern='test-group-*',
        )

        assert 'Version' in policy
        assert 'Statement' in policy
        # Check that custom patterns are used in the policy
        policy_str = str(policy)
        assert 'test-topic-*' in policy_str or 'test-group-*' in policy_str

    def test_generate_kafka_esm_policy_different_partitions(self):
        """Test Kafka ESM policy generation with different AWS partitions."""
        # Test with aws-cn partition
        policy = SecurePolicyGenerator.generate_kafka_esm_policy(
            region='cn-north-1',
            account='123456789012',
            cluster_name='test-cluster',
            cluster_uuid='12345678-1234-1234-1234-123456789012',
            function_name='test-function',
            partition='aws-cn',
        )

        assert 'Version' in policy
        assert 'Statement' in policy

        # Test with standard AWS partition but different region
        policy = SecurePolicyGenerator.generate_kafka_esm_policy(
            region='eu-west-1',
            account='123456789012',
            cluster_name='test-cluster',
            cluster_uuid='12345678-1234-1234-1234-123456789012',
            function_name='test-function',
            partition='aws',
        )

        assert 'Version' in policy
        assert 'Statement' in policy

    def test_generate_sqs_esm_policy_basic(self):
        """Test basic SQS ESM policy generation."""
        policy = SecurePolicyGenerator.generate_sqs_esm_policy(
            region='us-east-1',
            account='123456789012',
            queue_name='test-queue',
            function_name='test-function',
        )

        assert 'Version' in policy
        assert 'Statement' in policy
        assert policy['Version'] == '2012-10-17'
        assert len(policy['Statement']) > 0

    def test_generate_sqs_esm_policy_different_partitions(self):
        """Test SQS ESM policy generation with different AWS partitions."""
        policy = SecurePolicyGenerator.generate_sqs_esm_policy(
            region='cn-north-1',
            account='123456789012',
            queue_name='test-queue',
            function_name='test-function',
            partition='aws-cn',
        )

        assert 'Version' in policy
        assert 'Statement' in policy

    def test_generate_kinesis_esm_policy_basic(self):
        """Test basic Kinesis ESM policy generation."""
        policy = SecurePolicyGenerator.generate_kinesis_esm_policy(
            region='us-east-1',
            account='123456789012',
            stream_name='test-stream',
            function_name='test-function',
        )

        assert 'Version' in policy
        assert 'Statement' in policy
        assert policy['Version'] == '2012-10-17'
        assert len(policy['Statement']) > 0

    def test_generate_kinesis_esm_policy_different_partitions(self):
        """Test Kinesis ESM policy generation with different AWS partitions."""
        policy = SecurePolicyGenerator.generate_kinesis_esm_policy(
            region='ap-south-1',
            account='123456789012',
            stream_name='test-stream',
            function_name='test-function',
            partition='aws',
        )

        assert 'Version' in policy
        assert 'Statement' in policy

    def test_generate_dynamodb_esm_policy_basic(self):
        """Test basic DynamoDB ESM policy generation."""
        policy = SecurePolicyGenerator.generate_dynamodb_esm_policy(
            region='us-east-1',
            account='123456789012',
            table_name='test-table',
            function_name='test-function',
        )

        assert 'Version' in policy
        assert 'Statement' in policy
        assert policy['Version'] == '2012-10-17'
        assert len(policy['Statement']) > 0

    def test_generate_dynamodb_esm_policy_different_partitions(self):
        """Test DynamoDB ESM policy generation with different AWS partitions."""
        policy = SecurePolicyGenerator.generate_dynamodb_esm_policy(
            region='eu-west-1',
            account='123456789012',
            table_name='test-table',
            function_name='test-function',
            partition='aws',
        )

        assert 'Version' in policy
        assert 'Statement' in policy

    def test_policy_generation_with_special_characters(self):
        """Test policy generation with special characters in names."""
        # Test with hyphens and underscores
        policy = SecurePolicyGenerator.generate_kafka_esm_policy(
            region='us-east-1',
            account='123456789012',
            cluster_name='test-cluster-with-hyphens',
            cluster_uuid='12345678-1234-1234-1234-123456789012',
            function_name='test_function_with_underscores',
        )

        assert 'Version' in policy
        assert 'Statement' in policy

    def test_policy_generation_resource_arns(self):
        """Test that generated policies contain proper ARN formats."""
        policy = SecurePolicyGenerator.generate_sqs_esm_policy(
            region='us-west-2',
            account='987654321098',
            queue_name='my-test-queue',
            function_name='my-test-function',
        )

        # Convert policy to string to check for ARN patterns
        policy_str = str(policy)

        # Should contain proper ARN format
        assert 'arn:aws:' in policy_str
        assert 'us-west-2' in policy_str
        assert '987654321098' in policy_str

    def test_policy_statements_structure(self):
        """Test that policy statements have proper structure."""
        policy = SecurePolicyGenerator.generate_kinesis_esm_policy(
            region='eu-central-1',
            account='111122223333',
            stream_name='test-stream',
            function_name='test-function',
        )

        # Check that each statement has required fields
        for statement in policy['Statement']:
            assert 'Effect' in statement
            assert 'Action' in statement
            assert statement['Effect'] in ['Allow', 'Deny']
            assert isinstance(statement['Action'], (str, list))

    def test_policy_generation_minimal_permissions(self):
        """Test that policies follow principle of least privilege."""
        policy = SecurePolicyGenerator.generate_dynamodb_esm_policy(
            region='ap-southeast-1',
            account='444455556666',
            table_name='test-table',
            function_name='test-function',
        )

        # Should not contain overly broad permissions
        policy_str = str(policy).lower()
        assert '*:*' not in policy_str  # No wildcard permissions
        assert "'effect': 'allow'" in policy_str  # Should have allow statements

    # Simple error scenario tests

    def test_secure_policy_generator_basic_functionality(self):
        """Test basic functionality of secure policy generator."""
        generator = SecurePolicyGenerator()
        assert generator is not None

    def test_generate_kafka_esm_policy_with_validation_errors(self):
        """Test Kafka ESM policy generation with validation errors that raise ValueError."""
        with pytest.raises(ValueError, match='Invalid parameters'):
            SecurePolicyGenerator.generate_kafka_esm_policy(
                region='invalid-region',  # Invalid region
                account='invalid-account',  # Invalid account
                cluster_name='',  # Empty cluster name
                cluster_uuid='invalid-uuid',  # Invalid UUID
                function_name='test-function',
            )

    def test_generate_sqs_esm_policy_with_validation_errors(self):
        """Test SQS ESM policy generation with validation errors that raise ValueError."""
        with pytest.raises(ValueError, match='Invalid parameters'):
            SecurePolicyGenerator.generate_sqs_esm_policy(
                region='invalid-region',  # Invalid region
                account='invalid-account',  # Invalid account
                queue_name='',  # Empty queue name
                function_name='test-function',
            )

    def test_generate_kinesis_esm_policy_with_validation_errors(self):
        """Test Kinesis ESM policy generation with validation errors that raise ValueError."""
        with pytest.raises(ValueError, match='Invalid parameters'):
            SecurePolicyGenerator.generate_kinesis_esm_policy(
                region='invalid-region',  # Invalid region
                account='invalid-account',  # Invalid account
                stream_name='',  # Empty stream name
                function_name='test-function',
            )

    def test_generate_dynamodb_esm_policy_with_validation_errors(self):
        """Test DynamoDB ESM policy generation with validation errors that raise ValueError."""
        with pytest.raises(ValueError, match='Invalid parameters'):
            SecurePolicyGenerator.generate_dynamodb_esm_policy(
                region='invalid-region',  # Invalid region
                account='invalid-account',  # Invalid account
                table_name='',  # Empty table name
                function_name='test-function',
            )
