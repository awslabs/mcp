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

"""Tests for deployment_troubleshooter module."""

from awslabs.aws_iac_mcp_server.tools.deployment_tools import troubleshoot_deployment
from awslabs.aws_iac_mcp_server.models.deployment_models import DeploymentResponse
from datetime import datetime, timezone
from unittest.mock import ANY, Mock, patch


class TestTroubleshootDeployment:
    """Test troubleshoot_deployment function."""

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_creates_clients(self, mock_boto_client):
        """Test that boto3 clients are created with correct region."""
        mock_cfn = Mock()
        mock_boto_client.return_value = mock_cfn

        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'CREATE_FAILED'}]}
        mock_cfn.describe_events.return_value = {'OperationEvents': []}

        result = troubleshoot_deployment(stack_name='test-stack', region='us-west-2')

        # Should call boto3.client with correct parameters
        mock_boto_client.assert_called_with('cloudformation', region_name='us-west-2', config=ANY)
        assert isinstance(result, DeploymentResponse)


class TestCloudTrailIntegration:
    """Test CloudTrail integration in troubleshoot_deployment."""

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_cloudtrail_integration_enabled(self, mock_boto_client):
        """Test CloudTrail integration when enabled."""
        mock_cfn = Mock()
        mock_boto_client.return_value = mock_cfn

        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'CREATE_FAILED'}]}

        mock_cfn.describe_events.return_value = {
            'OperationEvents': [
                {
                    'EventId': 'event-1',
                    'ResourceType': 'AWS::S3::Bucket',
                    'ResourceStatus': 'CREATE_FAILED',
                    'ResourceStatusReason': 'Bucket already exists',
                    'LogicalResourceId': 'MyBucket',
                    'Timestamp': datetime.now(timezone.utc),
                    'EventType': 'PROVISIONING_ERROR',
                }
            ]
        }

        result = troubleshoot_deployment(
            stack_name='test-stack', region='us-east-1', include_cloudtrail=True
        )

        assert result.stack_name == 'test-stack'
        assert isinstance(result.failed_resources, list)
        assert isinstance(result, DeploymentResponse)

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_cloudtrail_integration_disabled(self, mock_boto_client):
        """Test CloudTrail integration when disabled."""
        mock_cfn = Mock()
        mock_boto_client.return_value = mock_cfn

        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'CREATE_FAILED'}]}

        mock_cfn.describe_events.return_value = {
            'OperationEvents': [
                {
                    'EventId': 'event-1',
                    'ResourceType': 'AWS::S3::Bucket',
                    'ResourceStatus': 'CREATE_FAILED',
                    'ResourceStatusReason': 'Bucket already exists',
                    'LogicalResourceId': 'MyBucket',
                    'Timestamp': datetime.now(timezone.utc),
                }
            ]
        }

        result = troubleshoot_deployment(
            stack_name='test-stack', region='us-east-1', include_cloudtrail=False
        )

        assert result.stack_name == 'test-stack'
        assert isinstance(result, DeploymentResponse)

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_stack_not_found_error(self, mock_boto_client):
        """Test error handling when stack doesn't exist."""
        from botocore.exceptions import ClientError

        mock_cfn = Mock()
        mock_cfn.exceptions = Mock()
        mock_cfn.exceptions.ClientError = ClientError

        mock_boto_client.return_value = mock_cfn

        mock_cfn.describe_stacks.side_effect = ClientError(
            {'Error': {'Code': 'ValidationError', 'Message': 'Stack does not exist'}},
            'DescribeStacks',
        )

        result = troubleshoot_deployment(stack_name='nonexistent-stack', region='us-east-1')

        assert 'nonexistent-stack' in result.root_cause_analysis
        assert result.stack_name == 'nonexistent-stack'

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_no_failed_events(self, mock_boto_client):
        """Test when stack has no failed events."""
        mock_cfn = Mock()
        mock_boto_client.return_value = mock_cfn

        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'CREATE_COMPLETE'}]}
        mock_cfn.describe_events.return_value = {'OperationEvents': []}

        result = troubleshoot_deployment(
            stack_name='test-stack', region='us-east-1', include_cloudtrail=True
        )

        assert len(result.failed_resources) == 0

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_timestamp_as_string(self, mock_boto_client):
        """Test CloudTrail integration with timestamp as string."""
        mock_cfn = Mock()
        mock_boto_client.return_value = mock_cfn

        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'CREATE_FAILED'}]}

        # Timestamp as string (ISO format)
        mock_cfn.describe_events.return_value = {
            'OperationEvents': [
                {
                    'EventId': 'event-1',
                    'ResourceType': 'AWS::S3::Bucket',
                    'ResourceStatus': 'CREATE_FAILED',
                    'ResourceStatusReason': 'Error',
                    'LogicalResourceId': 'MyBucket',
                    'Timestamp': '2025-01-15T12:00:00Z',
                    'EventType': 'PROVISIONING_ERROR',
                }
            ]
        }

        result = troubleshoot_deployment(
            stack_name='test-stack', region='us-east-1', include_cloudtrail=True
        )

        assert isinstance(result, DeploymentResponse)


class TestPatternMatching:
    """Test failure case pattern matching."""

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_pattern_matching_s3_bucket_not_empty(self, mock_boto_client):
        """Test pattern matching for S3 bucket not empty error."""
        mock_cfn = Mock()
        mock_boto_client.return_value = mock_cfn

        # Mock stack response
        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'DELETE_FAILED'}]}

        # Mock failed event with S3 bucket not empty error
        mock_cfn.describe_events.return_value = {
            'OperationEvents': [
                {
                    'EventId': 'test-event-1',
                    'ResourceType': 'AWS::S3::Bucket',
                    'ResourceStatus': 'DELETE_FAILED',
                    'ResourceStatusReason': 'The bucket you tried to delete is not empty',
                    'LogicalResourceId': 'MyBucket',
                    'Timestamp': datetime.now(timezone.utc),
                }
            ]
        }

        result = troubleshoot_deployment(
            stack_name='test-stack', region='us-east-1', include_cloudtrail=False
        )

        assert len(result.failed_resources) == 1
        assert len(result.remediation_steps) > 0

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_pattern_matching_security_group_dependency(self, mock_boto_client):
        """Test pattern matching for security group dependency error."""
        mock_cfn = Mock()
        mock_boto_client.return_value = mock_cfn

        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'DELETE_FAILED'}]}

        mock_cfn.describe_events.return_value = {
            'OperationEvents': [
                {
                    'EventId': 'test-event-2',
                    'ResourceType': 'AWS::EC2::SecurityGroup',
                    'ResourceStatus': 'DELETE_FAILED',
                    'ResourceStatusReason': 'resource sg-12345 has a dependent object',
                    'LogicalResourceId': 'MySecurityGroup',
                    'Timestamp': datetime.now(timezone.utc),
                }
            ]
        }

        result = troubleshoot_deployment(
            stack_name='test-stack', region='us-east-1', include_cloudtrail=False
        )

        assert len(result.failed_resources) == 1
        assert len(result.remediation_steps) > 0

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_pattern_matching_no_match(self, mock_boto_client):
        """Test when error doesn't match any known pattern."""
        mock_cfn = Mock()
        mock_boto_client.return_value = mock_cfn

        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'CREATE_FAILED'}]}

        mock_cfn.describe_events.return_value = {
            'OperationEvents': [
                {
                    'EventId': 'test-event-3',
                    'ResourceType': 'AWS::EC2::Instance',
                    'ResourceStatus': 'CREATE_FAILED',
                    'ResourceStatusReason': 'Some unknown error that does not match any pattern',
                    'LogicalResourceId': 'MyInstance',
                    'Timestamp': datetime.now(timezone.utc),
                }
            ]
        }

        result = troubleshoot_deployment(
            stack_name='test-stack', region='us-east-1', include_cloudtrail=False
        )

        assert len(result.failed_resources) == 1

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_pattern_matching_multiple_failures(self, mock_boto_client):
        """Test pattern matching with multiple failures."""
        mock_cfn = Mock()
        mock_boto_client.return_value = mock_cfn

        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'DELETE_FAILED'}]}

        mock_cfn.describe_events.return_value = {
            'OperationEvents': [
                {
                    'EventId': 'test-event-4',
                    'ResourceType': 'AWS::S3::Bucket',
                    'ResourceStatus': 'DELETE_FAILED',
                    'ResourceStatusReason': 'The bucket you tried to delete is not empty',
                    'LogicalResourceId': 'MyBucket',
                    'Timestamp': datetime.now(timezone.utc),
                },
                {
                    'EventId': 'test-event-5',
                    'ResourceType': 'AWS::EC2::SecurityGroup',
                    'ResourceStatus': 'DELETE_FAILED',
                    'ResourceStatusReason': 'resource sg-12345 has a dependent object',
                    'LogicalResourceId': 'MySecurityGroup',
                    'Timestamp': datetime.now(timezone.utc),
                },
            ]
        }

        result = troubleshoot_deployment(
            stack_name='test-stack', region='us-east-1', include_cloudtrail=False
        )

        assert len(result.failed_resources) == 2


class TestAnalyzeDeploymentEdgeCases:
    """Test edge cases in troubleshoot_deployment."""

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_empty_stacks_response(self, mock_boto_client):
        """Test when describe_stacks returns empty list."""
        from botocore.exceptions import ClientError

        mock_cfn = Mock()
        mock_cfn.describe_stacks.return_value = {'Stacks': []}
        mock_cfn.exceptions.ClientError = ClientError
        mock_boto_client.return_value = mock_cfn

        result = troubleshoot_deployment(
            stack_name='test-stack', region='us-east-1', include_cloudtrail=False
        )

        assert 'not found' in result.root_cause_analysis

    @patch('awslabs.aws_iac_mcp_server.tools.deployment_tools.boto3.client')
    def test_create_operation_detection(self, mock_boto_client):
        """Test CREATE operation is detected from ResourceStatus."""
        mock_cfn = Mock()
        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'CREATE_FAILED'}]}
        mock_cfn.describe_events.return_value = {
            'OperationEvents': [
                {
                    'ResourceStatus': 'CREATE_FAILED',
                    'ResourceStatusReason': 'Test error',
                    'ResourceType': 'AWS::S3::Bucket',
                    'LogicalResourceId': 'MyBucket',
                    'Timestamp': datetime.now(timezone.utc),
                }
            ]
        }
        mock_boto_client.return_value = mock_cfn

        result = troubleshoot_deployment(
            stack_name='test-stack', region='us-east-1', include_cloudtrail=False
        )

        assert isinstance(result, DeploymentResponse)