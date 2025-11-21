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

import json
from awslabs.aws_iac_mcp_server.deployment_troubleshooter import DeploymentTroubleshooter
from datetime import datetime, timezone
from unittest.mock import ANY, Mock, patch


class TestDeploymentTroubleshooterInit:
    """Test DeploymentTroubleshooter initialization."""

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_init_creates_clients(self, mock_boto_client):
        """Test that boto3 clients are created with correct region."""
        mock_cfn = Mock()
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

        troubleshooter = DeploymentTroubleshooter(region='us-west-2')

        assert troubleshooter.region == 'us-west-2'
        assert mock_boto_client.call_count == 2
        mock_boto_client.assert_any_call('cloudformation', region_name='us-west-2', config=ANY)
        mock_boto_client.assert_any_call('cloudtrail', region_name='us-west-2', config=ANY)

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_init_default_region(self, mock_boto_client):
        """Test default region is us-east-1."""
        mock_boto_client.return_value = Mock()

        troubleshooter = DeploymentTroubleshooter()

        assert troubleshooter.region == 'us-east-1'


class TestFilterCloudTrailEvents:
    """Test CloudTrail event filtering."""

    def test_filter_cloudtrail_events_with_cfn_errors(self):
        """Test filtering CloudFormation events with errors."""
        troubleshooter = DeploymentTroubleshooter()

        cloudtrail_events = [
            {
                'EventName': 'CreateBucket',
                'EventTime': datetime.now(timezone.utc),
                'Username': 'CloudFormation',
                'CloudTrailEvent': json.dumps(
                    {
                        'sourceIPAddress': 'cloudformation.amazonaws.com',
                        'errorCode': 'BucketAlreadyExists',
                        'errorMessage': 'The requested bucket name is not available',
                    }
                ),
            }
        ]
        cloudformation_events = [{'Timestamp': datetime.now(timezone.utc)}]

        result = troubleshooter.filter_cloudtrail_events(cloudtrail_events, cloudformation_events)

        assert result['has_relevant_events'] is True
        assert len(result['cloudtrail_events']) == 1
        assert result['cloudtrail_events'][0]['error_code'] == 'BucketAlreadyExists'
        assert 'cloudtrail_url' in result

    def test_filter_cloudtrail_events_no_errors(self):
        """Test when no error events exist."""
        troubleshooter = DeploymentTroubleshooter()

        cloudtrail_events = [
            {
                'EventName': 'CreateBucket',
                'EventTime': datetime.now(timezone.utc),
                'CloudTrailEvent': json.dumps(
                    {
                        'sourceIPAddress': 'cloudformation.amazonaws.com',
                    }
                ),
            }
        ]
        cloudformation_events = [{'Timestamp': datetime.now(timezone.utc)}]

        result = troubleshooter.filter_cloudtrail_events(cloudtrail_events, cloudformation_events)

        assert result['has_relevant_events'] is False
        assert len(result['cloudtrail_events']) == 0

    def test_filter_cloudtrail_events_empty_list(self):
        """Test with empty event list."""
        troubleshooter = DeploymentTroubleshooter()

        result = troubleshooter.filter_cloudtrail_events(
            [], [{'EventTime': datetime.now(timezone.utc)}]
        )

        assert result['has_relevant_events'] is False
        assert len(result['cloudtrail_events']) == 0

    def test_filter_cloudtrail_events_no_root_cause(self):
        """Test when root_cause_event is None."""
        troubleshooter = DeploymentTroubleshooter()

        result = troubleshooter.filter_cloudtrail_events([], [])

        assert result['has_relevant_events'] is False
        assert result['cloudtrail_events'] == []
        assert result['cloudtrail_url'] == ''

    def test_filter_cloudtrail_events_non_cfn_source(self):
        """Test filtering out non-CloudFormation events."""
        troubleshooter = DeploymentTroubleshooter()

        cloudtrail_events = [
            {
                'EventName': 'CreateBucket',
                'EventTime': datetime.now(timezone.utc),
                'CloudTrailEvent': json.dumps(
                    {
                        'sourceIPAddress': '192.168.1.1',
                        'errorCode': 'AccessDenied',
                    }
                ),
            }
        ]
        cloudformation_events = [{'Timestamp': datetime.now(timezone.utc)}]

        result = troubleshooter.filter_cloudtrail_events(cloudtrail_events, cloudformation_events)

        assert result['has_relevant_events'] is False
        assert len(result['cloudtrail_events']) == 0


class TestCloudTrailUrlGeneration:
    """Test CloudTrail console URL generation."""

    def test_cloudtrail_url_format(self):
        """Test CloudTrail URL has correct format."""
        troubleshooter = DeploymentTroubleshooter(region='us-west-2')

        cloudtrail_events = []
        cloudformation_events = [
            {'Timestamp': datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)}
        ]

        result = troubleshooter.filter_cloudtrail_events(cloudtrail_events, cloudformation_events)

        assert 'us-west-2' in result['cloudtrail_url']
        assert 'cloudtrailv2' in result['cloudtrail_url']
        assert 'StartTime=' in result['cloudtrail_url']
        assert 'EndTime=' in result['cloudtrail_url']


class TestCloudTrailIntegration:
    """Test CloudTrail integration in troubleshoot_stack_deployment."""

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_cloudtrail_integration_enabled(self, mock_boto_client):
        """Test CloudTrail integration when enabled."""
        mock_cfn = Mock()
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

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

        mock_cloudtrail.lookup_events.return_value = {
            'Events': [
                {
                    'EventName': 'CreateBucket',
                    'EventTime': datetime.now(timezone.utc),
                    'Username': 'test-user',
                    'CloudTrailEvent': json.dumps(
                        {
                            'sourceIPAddress': 'cloudformation.amazonaws.com',
                            'errorCode': 'BucketAlreadyExists',
                            'errorMessage': 'Bucket already exists',
                        }
                    ),
                }
            ]
        }

        troubleshooter = DeploymentTroubleshooter(region='us-east-1')
        result = troubleshooter.troubleshoot_stack_deployment(
            'test-stack', include_cloudtrail=True
        )

        assert result['status'] == 'success'
        assert 'filtered_cloudtrail' in result['raw_data']
        assert result['raw_data']['filtered_cloudtrail']['has_relevant_events'] is True
        mock_cloudtrail.lookup_events.assert_called_once()

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_cloudtrail_integration_disabled(self, mock_boto_client):
        """Test CloudTrail integration when disabled."""
        mock_cfn = Mock()
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

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

        troubleshooter = DeploymentTroubleshooter(region='us-east-1')
        result = troubleshooter.troubleshoot_stack_deployment(
            'test-stack', include_cloudtrail=False
        )

        assert result['status'] == 'success'
        assert 'filtered_cloudtrail' not in result['raw_data']
        mock_cloudtrail.lookup_events.assert_not_called()

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_stack_not_found_error(self, mock_boto_client):
        """Test error handling when stack doesn't exist."""
        from botocore.exceptions import ClientError

        mock_cfn = Mock()
        mock_cloudtrail = Mock()

        # Mock the exceptions attribute
        mock_cfn.exceptions = Mock()
        mock_cfn.exceptions.ClientError = ClientError

        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

        mock_cfn.describe_stacks.side_effect = ClientError(
            {'Error': {'Code': 'ValidationError', 'Message': 'Stack does not exist'}},
            'DescribeStacks',
        )

        troubleshooter = DeploymentTroubleshooter(region='us-east-1')
        result = troubleshooter.troubleshoot_stack_deployment('nonexistent-stack')

        assert result['status'] == 'error'
        assert 'nonexistent-stack' in result['error']
        assert result['stack_name'] == 'nonexistent-stack'

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_no_failed_events(self, mock_boto_client):
        """Test when stack has no failed events."""
        mock_cfn = Mock()
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

        mock_cfn.describe_stacks.return_value = {'Stacks': [{'StackStatus': 'CREATE_COMPLETE'}]}

        mock_cfn.describe_events.return_value = {'OperationEvents': []}

        troubleshooter = DeploymentTroubleshooter(region='us-east-1')
        result = troubleshooter.troubleshoot_stack_deployment(
            'test-stack', include_cloudtrail=True
        )

        assert result['status'] == 'success'
        assert result['raw_data']['failed_event_count'] == 0
        assert 'filtered_cloudtrail' not in result['raw_data']

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_timestamp_as_string(self, mock_boto_client):
        """Test CloudTrail integration with timestamp as string."""
        mock_cfn = Mock()
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

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

        mock_cloudtrail.lookup_events.return_value = {'Events': []}

        troubleshooter = DeploymentTroubleshooter(region='us-east-1')
        result = troubleshooter.troubleshoot_stack_deployment(
            'test-stack', include_cloudtrail=True
        )

        assert result['status'] == 'success'
        mock_cloudtrail.lookup_events.assert_called_once()

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_invalid_timestamp_type(self, mock_boto_client):
        """Test handling of invalid timestamp type."""
        mock_cfn = Mock()
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

        troubleshooter = DeploymentTroubleshooter(region='us-east-1')

        # Test with invalid timestamp (not datetime or string)
        cloudtrail_events = []
        cloudformation_events = [{'Timestamp': 12345}]  # Invalid: integer

        result = troubleshooter.filter_cloudtrail_events(cloudtrail_events, cloudformation_events)

        assert result['cloudtrail_events'] == []
        assert result['has_relevant_events'] is False


class TestPatternMatching:
    """Test failure case pattern matching."""

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_pattern_matching_s3_bucket_not_empty(self, mock_boto_client):
        """Test pattern matching for S3 bucket not empty error."""
        mock_cfn = Mock()
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

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

        troubleshooter = DeploymentTroubleshooter(region='us-east-1')
        result = troubleshooter.troubleshoot_stack_deployment(
            'test-stack', include_cloudtrail=False
        )

        assert result['status'] == 'success'
        assert result['raw_data']['matched_failure_count'] == 1
        assert (
            result['raw_data']['matched_failures'][0]['matched_case']['case_id']
            == 'S3_BUCKET_NOT_EMPTY'
        )

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_pattern_matching_security_group_dependency(self, mock_boto_client):
        """Test pattern matching for security group dependency error."""
        mock_cfn = Mock()
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

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

        troubleshooter = DeploymentTroubleshooter(region='us-east-1')
        result = troubleshooter.troubleshoot_stack_deployment(
            'test-stack', include_cloudtrail=False
        )

        assert result['status'] == 'success'
        assert result['raw_data']['matched_failure_count'] == 1
        assert (
            result['raw_data']['matched_failures'][0]['matched_case']['case_id']
            == 'SECURITY_GROUP_DEPENDENCY'
        )

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_pattern_matching_no_match(self, mock_boto_client):
        """Test when error doesn't match any known pattern."""
        mock_cfn = Mock()
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

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

        troubleshooter = DeploymentTroubleshooter(region='us-east-1')
        result = troubleshooter.troubleshoot_stack_deployment(
            'test-stack', include_cloudtrail=False
        )

        assert result['status'] == 'success'
        assert result['raw_data']['matched_failure_count'] == 0
        assert result['raw_data']['failed_event_count'] == 1

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_pattern_matching_multiple_failures(self, mock_boto_client):
        """Test pattern matching with multiple failures."""
        mock_cfn = Mock()
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

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

        troubleshooter = DeploymentTroubleshooter(region='us-east-1')
        result = troubleshooter.troubleshoot_stack_deployment(
            'test-stack', include_cloudtrail=False
        )

        assert result['status'] == 'success'
        assert result['raw_data']['matched_failure_count'] == 2
        assert result['raw_data']['failed_event_count'] == 2
        case_ids = [m['matched_case']['case_id'] for m in result['raw_data']['matched_failures']]
        assert 'S3_BUCKET_NOT_EMPTY' in case_ids
        assert 'SECURITY_GROUP_DEPENDENCY' in case_ids


class TestAnalyzeDeploymentEdgeCases:
    """Test edge cases in troubleshoot_stack_deployment."""

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
    def test_empty_stacks_response(self, mock_boto_client):
        """Test when describe_stacks returns empty list."""
        from botocore.exceptions import ClientError

        mock_cfn = Mock()
        mock_cfn.describe_stacks.return_value = {'Stacks': []}
        mock_cfn.exceptions.ClientError = ClientError
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

        troubleshooter = DeploymentTroubleshooter()
        result = troubleshooter.troubleshoot_stack_deployment(
            'test-stack', include_cloudtrail=False
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    @patch('awslabs.aws_iac_mcp_server.deployment_troubleshooter.boto3.client')
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
                }
            ]
        }
        mock_cloudtrail = Mock()
        mock_boto_client.side_effect = [mock_cfn, mock_cloudtrail]

        troubleshooter = DeploymentTroubleshooter()
        result = troubleshooter.troubleshoot_stack_deployment(
            'test-stack', include_cloudtrail=False
        )

        assert result['status'] == 'success'
