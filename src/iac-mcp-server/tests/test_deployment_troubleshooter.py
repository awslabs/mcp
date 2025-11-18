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
from awslabs.iac_mcp_server.deployment_troubleshooter import DeploymentTroubleshooter
from datetime import datetime, timezone
from unittest.mock import ANY, Mock, patch


class TestDeploymentTroubleshooterInit:
    """Test DeploymentTroubleshooter initialization."""

    @patch('awslabs.iac_mcp_server.deployment_troubleshooter.boto3.client')
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

    @patch('awslabs.iac_mcp_server.deployment_troubleshooter.boto3.client')
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
        root_cause = {'Timestamp': datetime.now(timezone.utc)}

        result = troubleshooter.filter_cloudtrail_events(cloudtrail_events, root_cause)

        assert result['has_relevant_events'] is True
        assert len(result['filtered_events']) == 1
        assert result['filtered_events'][0]['error_code'] == 'BucketAlreadyExists'
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
        root_cause = {'Timestamp': datetime.now(timezone.utc)}

        result = troubleshooter.filter_cloudtrail_events(cloudtrail_events, root_cause)

        assert result['has_relevant_events'] is False
        assert len(result['filtered_events']) == 0

    def test_filter_cloudtrail_events_empty_list(self):
        """Test with empty event list."""
        troubleshooter = DeploymentTroubleshooter()

        result = troubleshooter.filter_cloudtrail_events(
            [], {'Timestamp': datetime.now(timezone.utc)}
        )

        assert result['has_relevant_events'] is False
        assert len(result['filtered_events']) == 0

    def test_filter_cloudtrail_events_no_root_cause(self):
        """Test when root_cause_event is None."""
        troubleshooter = DeploymentTroubleshooter()

        result = troubleshooter.filter_cloudtrail_events([], {})

        assert result['has_relevant_events'] is False
        assert result['filtered_events'] == []
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
        root_cause = {'Timestamp': datetime.now(timezone.utc)}

        result = troubleshooter.filter_cloudtrail_events(cloudtrail_events, root_cause)

        assert result['has_relevant_events'] is False
        assert len(result['filtered_events']) == 0


class TestFilterCloudFormationStackEvents:
    """Test CloudFormation stack event filtering."""

    def test_filter_stack_events_with_failures(self):
        """Test identifying root cause vs cascading failures."""
        troubleshooter = DeploymentTroubleshooter()

        events = [
            {
                'ResourceStatus': 'CREATE_FAILED',
                'ResourceStatusReason': 'Bucket already exists',
                'LogicalResourceId': 'MyBucket',
            },
            {
                'ResourceStatus': 'CREATE_FAILED',
                'ResourceStatusReason': 'Resource creation cancelled',
                'LogicalResourceId': 'MyTable',
            },
        ]

        result = troubleshooter.filter_cloudformation_stack_events(events)

        assert result['root_cause_event'] is not None
        assert result['root_cause_event']['LogicalResourceId'] == 'MyBucket'
        assert len(result['actual_failures']) == 1
        assert len(result['cascading_cancellations']) == 1

    def test_filter_stack_events_only_cancelled(self):
        """Test when only cancelled events exist."""
        troubleshooter = DeploymentTroubleshooter()

        events = [
            {
                'ResourceStatus': 'CREATE_FAILED',
                'ResourceStatusReason': 'Resource creation cancelled',
                'LogicalResourceId': 'MyTable',
            }
        ]

        result = troubleshooter.filter_cloudformation_stack_events(events)

        assert result['root_cause_event'] is None
        assert len(result['actual_failures']) == 0
        assert len(result['cascading_cancellations']) == 1

    def test_filter_stack_events_empty_list(self):
        """Test with empty event list."""
        troubleshooter = DeploymentTroubleshooter()

        result = troubleshooter.filter_cloudformation_stack_events([])

        assert result['root_cause_event'] is None
        assert len(result['actual_failures']) == 0
        assert len(result['cascading_cancellations']) == 0


class TestCloudTrailUrlGeneration:
    """Test CloudTrail console URL generation."""

    def test_cloudtrail_url_format(self):
        """Test CloudTrail URL has correct format."""
        troubleshooter = DeploymentTroubleshooter(region='us-west-2')

        cloudtrail_events = []
        root_cause = {'Timestamp': datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)}

        result = troubleshooter.filter_cloudtrail_events(cloudtrail_events, root_cause)

        assert 'us-west-2' in result['cloudtrail_url']
        assert 'cloudtrailv2' in result['cloudtrail_url']
        assert 'StartTime=' in result['cloudtrail_url']
        assert 'EndTime=' in result['cloudtrail_url']
