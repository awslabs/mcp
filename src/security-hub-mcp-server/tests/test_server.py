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

"""Unit tests for the Security Hub MCP Server."""

import os
import pytest
from awslabs.security_hub_mcp_server.server import (
    Severity,
    WorkflowStatus,
    get_findings,
    main,
)
from unittest.mock import Mock, patch


class TestGetFindings:
    """Tests for the get_findings function."""

    @pytest.fixture
    def mock_security_hub_client(self):
        """Mock Security Hub client."""
        client = Mock()
        paginator = Mock()
        client.get_paginator.return_value = paginator
        return client, paginator

    @pytest.fixture
    def sample_findings(self):
        """Sample Security Hub findings for testing."""
        return [
            {
                'Id': 'finding-1',
                'ProductArn': 'arn:aws:securityhub:us-east-1::product/aws/inspector',
                'GeneratorId': 'inspector-generator',
                'AwsAccountId': '123456789012',
                'Types': ['Software and Configuration Checks'],
                'Title': 'Test Finding 1',
                'Description': 'Test description 1',
                'Severity': {'Label': 'HIGH'},
                'Workflow': {'Status': 'NEW'},
            },
            {
                'Id': 'finding-2',
                'ProductArn': 'arn:aws:securityhub:us-east-1::product/aws/guardduty',
                'GeneratorId': 'guardduty-generator',
                'AwsAccountId': '123456789012',
                'Types': ['Threat Detection'],
                'Title': 'Test Finding 2',
                'Description': 'Test description 2',
                'Severity': {'Label': 'MEDIUM'},
                'Workflow': {'Status': 'RESOLVED'},
            },
        ]

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_basic(
        self, mock_session, mock_security_hub_client, sample_findings
    ):
        """Test basic get_findings functionality."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client

        # Mock paginator response
        paginator.paginate.return_value = [{'Findings': sample_findings}]

        result = await get_findings(region='us-east-1')

        assert result == sample_findings
        mock_session.assert_called_once_with(profile_name='default')
        mock_session.return_value.client.assert_called_once_with(
            'securityhub', region_name='us-east-1'
        )
        client.get_paginator.assert_called_once_with('get_findings')
        paginator.paginate.assert_called_once_with(Filters={})

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_with_aws_account_id(
        self, mock_session, mock_security_hub_client, sample_findings
    ):
        """Test get_findings with AWS account ID filter."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{'Findings': sample_findings}]

        result = await get_findings(region='us-east-1', aws_account_id='123456789012')

        expected_filters = {'AwsAccountId': [{'Value': '123456789012', 'Comparison': 'EQUALS'}]}
        paginator.paginate.assert_called_once_with(Filters=expected_filters)
        assert result == sample_findings

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_with_severity(
        self, mock_session, mock_security_hub_client, sample_findings
    ):
        """Test get_findings with severity filter."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{'Findings': sample_findings}]

        result = await get_findings(region='us-east-1', severity='HIGH')

        expected_filters = {'SeverityLabel': [{'Value': 'HIGH', 'Comparison': 'EQUALS'}]}
        paginator.paginate.assert_called_once_with(Filters=expected_filters)
        assert result == sample_findings

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_with_workflow_status(
        self, mock_session, mock_security_hub_client, sample_findings
    ):
        """Test get_findings with workflow status filter."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{'Findings': sample_findings}]

        result = await get_findings(region='us-east-1', workflow_status='NEW')

        expected_filters = {'WorkflowStatus': [{'Value': 'NEW', 'Comparison': 'EQUALS'}]}
        paginator.paginate.assert_called_once_with(Filters=expected_filters)
        assert result == sample_findings

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_with_custom_filters(
        self, mock_session, mock_security_hub_client, sample_findings
    ):
        """Test get_findings with custom filters."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{'Findings': sample_findings}]

        custom_filters = {'ResourceType': [{'Comparison': 'EQUALS', 'Value': 'AwsAccount'}]}

        result = await get_findings(region='us-east-1', custom_filters=custom_filters)

        expected_filters = {'ResourceType': [{'Comparison': 'EQUALS', 'Value': 'AwsAccount'}]}
        paginator.paginate.assert_called_once_with(Filters=expected_filters)
        assert result == sample_findings

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_with_all_filters(
        self, mock_session, mock_security_hub_client, sample_findings
    ):
        """Test get_findings with all filter types combined."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{'Findings': sample_findings}]

        custom_filters = {'ResourceType': [{'Comparison': 'EQUALS', 'Value': 'AwsAccount'}]}

        result = await get_findings(
            region='us-east-1',
            aws_account_id='123456789012',
            severity='HIGH',
            workflow_status='NEW',
            custom_filters=custom_filters,
        )

        expected_filters = {
            'AwsAccountId': [{'Value': '123456789012', 'Comparison': 'EQUALS'}],
            'SeverityLabel': [{'Value': 'HIGH', 'Comparison': 'EQUALS'}],
            'WorkflowStatus': [{'Value': 'NEW', 'Comparison': 'EQUALS'}],
            'ResourceType': [{'Comparison': 'EQUALS', 'Value': 'AwsAccount'}],
        }
        paginator.paginate.assert_called_once_with(Filters=expected_filters)
        assert result == sample_findings

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_with_max_results(
        self, mock_session, mock_security_hub_client, sample_findings
    ):
        """Test get_findings with max_results parameter."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{'Findings': sample_findings}]

        result = await get_findings(region='us-east-1', max_results=10)

        expected_params = {'Filters': {}, 'MaxResults': 10}
        paginator.paginate.assert_called_once_with(**expected_params)
        assert result == sample_findings

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_max_results_truncation(
        self, mock_session, mock_security_hub_client
    ):
        """Test get_findings truncates results when exceeding max_results."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client

        # Create more findings than max_results
        many_findings = [{'Id': f'finding-{i}'} for i in range(15)]
        paginator.paginate.return_value = [{'Findings': many_findings}]

        result = await get_findings(region='us-east-1', max_results=10)

        assert len(result) == 10
        assert result == many_findings[:10]

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_pagination(self, mock_session, mock_security_hub_client):
        """Test get_findings handles pagination correctly."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client

        # Mock multiple pages
        page1_findings = [{'Id': 'finding-1'}, {'Id': 'finding-2'}]
        page2_findings = [{'Id': 'finding-3'}, {'Id': 'finding-4'}]
        paginator.paginate.return_value = [
            {'Findings': page1_findings},
            {'Findings': page2_findings},
        ]

        result = await get_findings(region='us-east-1')

        expected_findings = page1_findings + page2_findings
        assert result == expected_findings

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_empty_response(self, mock_session, mock_security_hub_client):
        """Test get_findings handles empty response."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{'Findings': []}]

        result = await get_findings(region='us-east-1')

        assert result == []

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_no_findings_key(self, mock_session, mock_security_hub_client):
        """Test get_findings handles response without Findings key."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{}]  # No 'Findings' key

        result = await get_findings(region='us-east-1')

        assert result == []

    @pytest.mark.asyncio
    async def test_get_findings_invalid_severity(self):
        """Test get_findings with invalid severity."""
        result = await get_findings(region='us-east-1', severity='INVALID')

        assert len(result) == 1
        assert 'error' in result[0]
        assert 'Invalid severity (INVALID)' in result[0]['error']
        assert 'INFORMATIONAL, LOW, MEDIUM, HIGH, CRITICAL' in result[0]['error']

    @pytest.mark.asyncio
    async def test_get_findings_invalid_workflow_status(self):
        """Test get_findings with invalid workflow status."""
        result = await get_findings(region='us-east-1', workflow_status='INVALID')

        assert len(result) == 1
        assert 'error' in result[0]
        assert 'Invalid workflow status (INVALID)' in result[0]['error']
        assert 'NEW, NOTIFIED, RESOLVED, SUPPRESSED' in result[0]['error']

    @pytest.mark.asyncio
    async def test_get_findings_case_insensitive_severity(self):
        """Test get_findings handles case-insensitive severity."""
        with patch('awslabs.security_hub_mcp_server.server.boto3.Session') as mock_session:
            client = Mock()
            paginator = Mock()
            client.get_paginator.return_value = paginator
            mock_session.return_value.client.return_value = client
            paginator.paginate.return_value = [{'Findings': []}]

            # Test lowercase
            await get_findings(region='us-east-1', severity='high')

            expected_filters = {'SeverityLabel': [{'Value': 'HIGH', 'Comparison': 'EQUALS'}]}
            paginator.paginate.assert_called_with(Filters=expected_filters)

    @pytest.mark.asyncio
    async def test_get_findings_case_insensitive_workflow_status(self):
        """Test get_findings handles case-insensitive workflow status."""
        with patch('awslabs.security_hub_mcp_server.server.boto3.Session') as mock_session:
            client = Mock()
            paginator = Mock()
            client.get_paginator.return_value = paginator
            mock_session.return_value.client.return_value = client
            paginator.paginate.return_value = [{'Findings': []}]

            # Test lowercase
            await get_findings(region='us-east-1', workflow_status='new')

            expected_filters = {'WorkflowStatus': [{'Value': 'NEW', 'Comparison': 'EQUALS'}]}
            paginator.paginate.assert_called_with(Filters=expected_filters)

    @pytest.mark.asyncio
    async def test_get_findings_invalid_custom_filters_type(self):
        """Test get_findings with invalid custom_filters type."""
        result = await get_findings(region='us-east-1', custom_filters='not a dict')

        assert len(result) == 1
        assert 'error' in result[0]
        assert 'custom_filters must be a JSON object' in result[0]['error']

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_max_results_zero(
        self, mock_session, mock_security_hub_client, sample_findings
    ):
        """Test get_findings with max_results=0 (should not include MaxResults in query)."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{'Findings': sample_findings}]

        result = await get_findings(region='us-east-1', max_results=0)

        # Should not include MaxResults in the query when max_results is 0
        paginator.paginate.assert_called_once_with(Filters={})
        assert result == sample_findings

    @pytest.mark.asyncio
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_max_results_none(
        self, mock_session, mock_security_hub_client, sample_findings
    ):
        """Test get_findings with max_results=None (should not include MaxResults in query)."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{'Findings': sample_findings}]

        result = await get_findings(region='us-east-1', max_results=None)

        # Should not include MaxResults in the query when max_results is None
        paginator.paginate.assert_called_once_with(Filters={})
        assert result == sample_findings

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'AWS_PROFILE': 'test-profile'})
    @patch('awslabs.security_hub_mcp_server.server.boto3.Session')
    async def test_get_findings_custom_aws_profile(
        self, mock_session, mock_security_hub_client, sample_findings
    ):
        """Test get_findings uses custom AWS profile from environment."""
        client, paginator = mock_security_hub_client
        mock_session.return_value.client.return_value = client
        paginator.paginate.return_value = [{'Findings': sample_findings}]

        # Need to reload the module to pick up the new environment variable
        import awslabs.security_hub_mcp_server.server
        import importlib

        importlib.reload(awslabs.security_hub_mcp_server.server)

        result = await awslabs.security_hub_mcp_server.server.get_findings(region='us-east-1')

        mock_session.assert_called_with(profile_name='test-profile')
        assert result == sample_findings


class TestEnums:
    """Tests for the enum classes."""

    def test_severity_enum_values(self):
        """Test Severity enum has correct values."""
        assert Severity.INFORMATIONAL.value == 'INFORMATIONAL'
        assert Severity.LOW.value == 'LOW'
        assert Severity.MEDIUM.value == 'MEDIUM'
        assert Severity.HIGH.value == 'HIGH'
        assert Severity.CRITICAL.value == 'CRITICAL'

    def test_workflow_status_enum_values(self):
        """Test WorkflowStatus enum has correct values."""
        assert WorkflowStatus.NEW.value == 'NEW'
        assert WorkflowStatus.NOTIFIED.value == 'NOTIFIED'
        assert WorkflowStatus.RESOLVED.value == 'RESOLVED'
        assert WorkflowStatus.SUPPRESSED.value == 'SUPPRESSED'

    def test_severity_enum_membership(self):
        """Test Severity enum membership."""
        valid_severities = ['INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        for severity in valid_severities:
            assert Severity(severity) in Severity

    def test_workflow_status_enum_membership(self):
        """Test WorkflowStatus enum membership."""
        valid_statuses = ['NEW', 'NOTIFIED', 'RESOLVED', 'SUPPRESSED']
        for status in valid_statuses:
            assert WorkflowStatus(status) in WorkflowStatus


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.security_hub_mcp_server.server.mcp')
    @patch('sys.argv', ['server.py'])  # Mock sys.argv to avoid pytest arguments
    def test_main_default(self, mock_mcp):
        """Test the main function with default arguments."""
        # Set up the mock
        with patch.dict(os.environ, {'FASTMCP_LOG_LEVEL': 'DEBUG'}):
            # Call the function
            main()

            # Check that mcp.run was called with the correct arguments
            mock_mcp.run.assert_called_once_with()

    @patch('awslabs.security_hub_mcp_server.server.mcp')
    @patch('sys.argv', ['server.py', '--sse'])  # Mock sys.argv to avoid pytest arguments
    def test_sse_default(self, mock_mcp):
        """Test the main function with default arguments."""
        # Set up the mock
        with patch.dict(os.environ, {'FASTMCP_LOG_LEVEL': 'DEBUG'}):
            # Call the function
            main()

            # Check that mcp.run was called with the correct arguments
            assert 8888 == mock_mcp.settings.port
            mock_mcp.run.assert_called_once_with(transport='sse')

    @patch('awslabs.security_hub_mcp_server.server.mcp')
    @patch(
        'sys.argv', ['server.py', '--sse', '--port', '4242']
    )  # Mock sys.argv to avoid pytest arguments
    def test_sse_custom_port(self, mock_mcp):
        """Test the main function with default arguments."""
        # Set up the mock
        with patch.dict(os.environ, {'FASTMCP_LOG_LEVEL': 'DEBUG'}):
            # Call the function
            main()

            # Check that mcp.run was called with the correct arguments
            assert 4242 == mock_mcp.settings.port
            mock_mcp.run.assert_called_once_with(transport='sse')
