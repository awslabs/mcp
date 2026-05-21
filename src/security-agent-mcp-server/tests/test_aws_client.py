# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for aws_client.py using boto3 SDK."""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.security_agent_mcp_server.aws_client import SecurityAgentClient


class TestSecurityAgentClient:
    """Tests for SecurityAgentClient."""

    def test_init_default_region(self):
        client = SecurityAgentClient()
        assert client.region == 'us-east-1'

    def test_init_custom_region(self):
        client = SecurityAgentClient(region='us-west-2')
        assert client.region == 'us-west-2'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_list_agent_spaces(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.list_agent_spaces.return_value = {
            'agentSpaceSummaries': [{'agentSpaceId': 'as-1', 'name': 'test'}]
        }
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.list_agent_spaces()
        assert len(result) == 1
        assert result[0]['agentSpaceId'] == 'as-1'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_get_agent_space(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.batch_get_agent_spaces.return_value = {
            'agentSpaces': [{'agentSpaceId': 'as-1', 'name': 'test'}]
        }
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.get_agent_space('as-1')
        assert result['name'] == 'test'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_get_agent_space_empty(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.batch_get_agent_spaces.return_value = {'agentSpaces': []}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.get_agent_space('as-nonexistent')
        assert result == {}

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_create_code_review(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.create_code_review.return_value = {'codeReviewId': 'cr-123'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.create_code_review(
            agent_space_id='as-1',
            title='test',
            service_role='arn:role',
            s3_url='s3://bucket/key.zip',
        )
        assert result['codeReviewId'] == 'cr-123'
        mock_client.create_code_review.assert_called_once()

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_start_code_review_job(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.start_code_review_job.return_value = {'codeReviewJobId': 'cj-456'}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.start_code_review_job('as-1', 'cr-123')
        assert result['codeReviewJobId'] == 'cj-456'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_list_findings_pagination(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.list_findings.side_effect = [
            {'findingsSummaries': [{'findingId': 'f-1'}], 'nextToken': 'tok'},
            {'findingsSummaries': [{'findingId': 'f-2'}]},
        ]
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.list_findings('as-1', 'cj-456')
        assert len(result['findingsSummaries']) == 2

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_batch_get_findings(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.batch_get_findings.return_value = {
            'findings': [{'findingId': 'f-1', 'name': 'SQL Injection'}]
        }
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.batch_get_findings('as-1', ['f-1'])
        assert result['findings'][0]['name'] == 'SQL Injection'

    @patch('awslabs.security_agent_mcp_server.aws_client.boto3')
    def test_call_generic(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.list_pentests.return_value = {'pentests': []}
        mock_boto3.Session.return_value.client.return_value = mock_client

        client = SecurityAgentClient()
        result = client.call('ListPentests', {'agentSpaceId': 'as-1'})
        assert result == {'pentests': []}

    def test_call_invalid_operation(self):
        client = SecurityAgentClient()
        with pytest.raises(ValueError, match='Invalid operation'):
            client.call('../evil', {})

