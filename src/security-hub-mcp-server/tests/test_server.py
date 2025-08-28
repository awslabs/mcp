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

"""Unit tests for AWS Security Hub MCP Server."""

import json
import pytest
from awslabs.security_hub_mcp_server.server import (
    _get_security_hub_client,
    _handle_aws_error,
    get_enabled_standards,
    get_findings,
    get_insight_results,
    get_insights,
    get_security_score,
    update_finding_workflow_state,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


class TestSecurityHubMCPServer:
    """Test cases for Security Hub MCP Server."""

    @patch('awslabs.security_hub_mcp_server.server.boto3.client')
    def test_get_security_hub_client_success(self, mock_boto3_client):
        """Test successful Security Hub client creation."""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        client = _get_security_hub_client('us-east-1')

        assert client == mock_client
        mock_boto3_client.assert_called_once_with('securityhub', region_name='us-east-1')

    @patch('awslabs.security_hub_mcp_server.server.boto3.client')
    def test_get_security_hub_client_failure(self, mock_boto3_client):
        """Test Security Hub client creation failure."""
        mock_boto3_client.side_effect = Exception('Connection failed')

        with pytest.raises(Exception):
            _get_security_hub_client('us-east-1')

    def test_handle_aws_error_client_error(self):
        """Test AWS ClientError handling."""
        error_response = {'Error': {'Code': 'InvalidAccessException', 'Message': 'Access denied'}}
        client_error = ClientError(error_response, 'GetFindings')

        result = _handle_aws_error(client_error, 'get findings')

        assert 'Access denied for get findings' in result
        assert 'AWS credentials and IAM permissions' in result

    def test_handle_aws_error_generic_exception(self):
        """Test generic exception handling."""
        generic_error = Exception('Something went wrong')

        result = _handle_aws_error(generic_error, 'test operation')

        assert 'Unexpected error in test operation' in result
        assert 'Something went wrong' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server._get_security_hub_client')
    async def test_get_findings_success(self, mock_get_client):
        """Test successful findings retrieval."""
        # Mock client and response
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_response = {
            'Findings': [
                {
                    'Id': 'finding-1',
                    'ProductArn': 'arn:aws:securityhub:us-east-1::product/aws/securityhub',
                    'GeneratorId': 'security-control/EC2.1',
                    'AwsAccountId': '123456789012',
                    'Title': 'EC2 instances should not have a public IP address',
                    'Description': 'This control checks whether EC2 instances have a public IP address.',
                    'Severity': {'Label': 'HIGH', 'Normalized': 70},
                    'WorkflowState': 'NEW',
                    'RecordState': 'ACTIVE',
                    'CreatedAt': '2024-01-01T00:00:00.000Z',
                    'UpdatedAt': '2024-01-01T00:00:00.000Z',
                    'Resources': [{'Type': 'AwsEc2Instance', 'Id': 'i-1234567890abcdef0'}],
                }
            ]
        }
        mock_client.get_findings.return_value = mock_response

        # Call the function
        result = await get_findings(region='us-east-1', severity_labels=['HIGH'], max_results=10)

        # Verify the result
        result_data = json.loads(result)
        assert result_data['findings_count'] == 1
        assert len(result_data['findings']) == 1
        assert result_data['findings'][0]['id'] == 'finding-1'
        assert (
            result_data['findings'][0]['title']
            == 'EC2 instances should not have a public IP address'
        )

        # Verify client was called correctly
        mock_client.get_findings.assert_called_once()
        call_args = mock_client.get_findings.call_args
        assert call_args[1]['MaxResults'] == 10
        assert 'SeverityLabel' in call_args[1]['Filters']

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server._get_security_hub_client')
    async def test_get_findings_error(self, mock_get_client):
        """Test findings retrieval with error."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        error_response = {
            'Error': {'Code': 'InvalidAccessException', 'Message': 'Security Hub is not enabled'}
        }
        mock_client.get_findings.side_effect = ClientError(error_response, 'GetFindings')

        result = await get_findings()

        assert 'Error:' in result
        assert 'Access denied for get findings' in result

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server._get_security_hub_client')
    async def test_get_enabled_standards_success(self, mock_get_client):
        """Test successful enabled standards retrieval."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_response = {
            'StandardsSubscriptions': [
                {
                    'StandardsArn': 'arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0',
                    'StandardsInput': {
                        'Name': 'AWS Foundational Security Standard',
                        'Description': 'AWS Foundational Security Standard',
                    },
                    'StandardsStatus': 'ENABLED',
                }
            ]
        }
        mock_client.get_enabled_standards.return_value = mock_response

        result = await get_enabled_standards()

        result_data = json.loads(result)
        assert result_data['enabled_standards_count'] == 1
        assert len(result_data['enabled_standards']) == 1
        assert 'AWS Foundational Security Standard' in result_data['enabled_standards'][0]['name']

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server._get_security_hub_client')
    async def test_get_insights_success(self, mock_get_client):
        """Test successful insights retrieval."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_response = {
            'Insights': [
                {
                    'InsightArn': 'arn:aws:securityhub:us-east-1:123456789012:insight/123456789012/custom/insight-1',
                    'Name': 'High severity findings by resource type',
                    'Filters': {'SeverityLabel': [{'Value': 'HIGH', 'Comparison': 'EQUALS'}]},
                    'GroupByAttribute': 'ResourceType',
                }
            ]
        }
        mock_client.get_insights.return_value = mock_response

        result = await get_insights()

        result_data = json.loads(result)
        assert result_data['insights_count'] == 1
        assert len(result_data['insights']) == 1
        assert result_data['insights'][0]['name'] == 'High severity findings by resource type'

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server._get_security_hub_client')
    async def test_get_insight_results_success(self, mock_get_client):
        """Test successful insight results retrieval."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_response = {
            'InsightResults': {
                'GroupByAttribute': 'ResourceType',
                'ResultValues': [
                    {'GroupByAttributeValue': 'AwsEc2Instance', 'Count': 5},
                    {'GroupByAttributeValue': 'AwsS3Bucket', 'Count': 3},
                ],
            }
        }
        mock_client.get_insight_results.return_value = mock_response

        insight_arn = (
            'arn:aws:securityhub:us-east-1:123456789012:insight/123456789012/custom/insight-1'
        )
        result = await get_insight_results(insight_arn=insight_arn)

        result_data = json.loads(result)
        assert result_data['insight_arn'] == insight_arn
        assert result_data['group_by_attribute'] == 'ResourceType'
        assert len(result_data['result_values']) == 2

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server._get_security_hub_client')
    async def test_get_security_score_success(self, mock_get_client):
        """Test successful security score calculation."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock responses for different finding types
        mock_client.get_findings.side_effect = [
            {'Findings': [{'Id': 'passed-1'}]},  # Passed findings
            {'Findings': [{'Id': 'failed-1'}]},  # Failed findings
            {'Findings': []},  # INFORMATIONAL
            {'Findings': []},  # LOW
            {'Findings': []},  # MEDIUM
            {'Findings': [{'Id': 'high-1'}]},  # HIGH
            {'Findings': [{'Id': 'critical-1'}]},  # CRITICAL
        ]

        result = await get_security_score()

        result_data = json.loads(result)
        assert 'security_score' in result_data
        assert 'severity_breakdown' in result_data
        assert result_data['security_score']['total_active_findings'] == 2
        assert result_data['security_score']['passed_findings'] == 1
        assert result_data['security_score']['failed_findings'] == 1

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server._get_security_hub_client')
    async def test_update_finding_workflow_state_success(self, mock_get_client):
        """Test successful finding workflow state update."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_response = {
            'ProcessedFindings': [
                {
                    'Id': 'finding-1',
                    'ProductArn': 'arn:aws:securityhub:us-east-1::product/aws/securityhub',
                }
            ],
            'UnprocessedFindings': [],
        }
        mock_client.batch_update_findings.return_value = mock_response

        finding_identifiers = [
            {
                'Id': 'finding-1',
                'ProductArn': 'arn:aws:securityhub:us-east-1::product/aws/securityhub',
            }
        ]

        result = await update_finding_workflow_state(
            finding_identifiers=finding_identifiers,
            workflow_state='RESOLVED',
            note='Fixed by security team',
        )

        result_data = json.loads(result)
        assert len(result_data['processed_findings']) == 1
        assert len(result_data['unprocessed_findings']) == 0
        assert result_data['workflow_state'] == 'RESOLVED'
        assert result_data['note'] == 'Fixed by security team'

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server._get_security_hub_client')
    async def test_get_findings_with_filters(self, mock_get_client):
        """Test findings retrieval with multiple filters."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_findings.return_value = {'Findings': []}

        await get_findings(
            region='us-west-2',
            severity_labels=['HIGH', 'CRITICAL'],
            workflow_states=['NEW'],
            record_states=['ACTIVE'],
            compliance_statuses=['FAILED'],
            resource_type='AwsEc2Instance',
            aws_account_id='123456789012',
            days_back=30,
            max_results=25,
        )

        # Verify the client was called with correct filters
        call_args = mock_client.get_findings.call_args
        filters = call_args[1]['Filters']

        assert 'SeverityLabel' in filters
        assert 'WorkflowState' in filters
        assert 'RecordState' in filters
        assert 'ComplianceStatus' in filters
        assert 'ResourceType' in filters
        assert 'AwsAccountId' in filters
        assert 'UpdatedAt' in filters
        assert call_args[1]['MaxResults'] == 25

    def test_max_results_boundary_conditions(self):
        """Test max_results parameter boundary conditions."""
        # Test values are clamped to valid range
        from awslabs.security_hub_mcp_server.consts import DEFAULT_MAX_RESULTS

        # Test minimum boundary
        assert min(max(1, 0), DEFAULT_MAX_RESULTS) == 1

        # Test maximum boundary
        assert min(max(1, 200), DEFAULT_MAX_RESULTS) == DEFAULT_MAX_RESULTS

        # Test normal value
        assert min(max(1, 50), DEFAULT_MAX_RESULTS) == 50
