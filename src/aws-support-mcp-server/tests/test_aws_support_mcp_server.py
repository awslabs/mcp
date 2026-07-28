# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use
# this file except in compliance with the License. A copy of the License is
# located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an
# 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the AWS Support API MCP Server."""

import asyncio
import json
import os
import pytest
import tempfile
import time
from awslabs.aws_support_mcp_server.client import SupportClient
from awslabs.aws_support_mcp_server.consts import (
    DEFAULT_REGION,
    ERROR_AUTHENTICATION_FAILED,
    ERROR_CASE_NOT_FOUND,
    ERROR_RATE_LIMIT_EXCEEDED,
    ERROR_SUBSCRIPTION_REQUIRED,
    PERMITTED_LANGUAGE_CODES,
)
from awslabs.aws_support_mcp_server.errors import (
    create_error_response,
    handle_client_error,
    handle_general_error,
    handle_validation_error,
)
from awslabs.aws_support_mcp_server.formatters import (
    format_case,
    format_cases,
    format_communications,
    format_json_response,
    format_markdown_case_summary,
    format_markdown_services,
    format_markdown_severity_levels,
    format_services,
    format_severity_levels,
)
from awslabs.aws_support_mcp_server.server import (
    _add_attachments_to_set_logic,
    _add_communication_to_case_logic,
    _create_support_case_logic,
    _describe_attachment_logic,
    _describe_communications_logic,
    _describe_create_case_options_logic,
    _describe_support_cases_logic,
    _describe_supported_languages_logic,
    _resolve_support_case_logic,
)
from botocore.exceptions import ClientError
from pydantic import ValidationError
from typing import Any, Dict, List
from unittest.mock import ANY, AsyncMock, MagicMock, patch


# Fixtures


@pytest.fixture
def support_case_data() -> Dict[str, Any]:
    """Return a dictionary with sample support case data."""
    return {
        'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
        'displayId': '12345678910',
        'subject': 'EC2 instance not starting',
        'status': 'opened',
        'serviceCode': 'amazon-elastic-compute-cloud-linux',
        'categoryCode': 'using-aws',
        'severityCode': 'urgent',
        'submittedBy': 'user@example.com',
        'timeCreated': '2023-01-01T12:00:00Z',
        'recentCommunications': {
            'communications': [
                {
                    'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
                    'body': 'My EC2 instance i-1234567890abcdef0 is not starting.',
                    'submittedBy': 'user@example.com',
                    'timeCreated': '2023-01-01T12:00:00Z',
                }
            ],
            'nextToken': None,
        },
        'ccEmailAddresses': ['team@example.com'],
        'language': 'en',
        'nextToken': None,
    }


@pytest.fixture
def minimal_support_case_data() -> Dict[str, Any]:
    """Return a dictionary with minimal support case data."""
    return {
        'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
        'subject': 'EC2 instance not starting',
        'status': 'opened',
        'serviceCode': 'amazon-elastic-compute-cloud-linux',
        'categoryCode': 'using-aws',
        'severityCode': 'urgent',
        'submittedBy': 'user@example.com',
        'timeCreated': '2023-01-01T12:00:00Z',
    }


@pytest.fixture
def edge_case_support_case_data() -> Dict[str, Any]:
    """Return a dictionary with edge case support case data."""
    return {
        'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
        'displayId': '12345678910',
        'subject': 'EC2 instance not starting' * 50,  # Very long subject
        'status': 'opened',
        'serviceCode': 'amazon-elastic-compute-cloud-linux',
        'categoryCode': 'using-aws',
        'severityCode': 'urgent',
        'submittedBy': 'user@example.com',
        'timeCreated': '2023-01-01T12:00:00Z',
        'recentCommunications': {
            'communications': [
                {
                    'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
                    'body': 'My EC2 instance i-1234567890abcdef0 is not starting.',
                    'submittedBy': 'user@example.com',
                    'timeCreated': '2023-01-01T12:00:00Z',
                }
            ],
            'nextToken': None,
        },
        'ccEmailAddresses': ['team@example.com'],
        'language': 'en',
        'nextToken': None,
    }


@pytest.fixture
def multiple_support_cases_data() -> List[Dict[str, Any]]:
    """Return a list of dictionaries with sample support case data."""
    return [
        {
            'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
            'displayId': '12345678910',
            'subject': 'EC2 instance not starting',
            'status': 'opened',
            'serviceCode': 'amazon-elastic-compute-cloud-linux',
            'categoryCode': 'using-aws',
            'severityCode': 'urgent',
            'submittedBy': 'user@example.com',
            'timeCreated': '2023-01-01T12:00:00Z',
        },
        {
            'caseId': 'case-98765432109-2013-a1b2c3d4e5f6',
            'displayId': '98765432109',
            'subject': 'S3 bucket access issue',
            'status': 'opened',
            'serviceCode': 'amazon-s3',
            'categoryCode': 'using-aws',
            'severityCode': 'high',
            'submittedBy': 'user@example.com',
            'timeCreated': '2023-01-02T12:00:00Z',
        },
    ]


@pytest.fixture
def communication_data() -> Dict[str, Any]:
    """Return a dictionary with sample communication data."""
    return {
        'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
        'body': 'My EC2 instance i-1234567890abcdef0 is not starting.',
        'submittedBy': 'user@example.com',
        'timeCreated': '2023-01-01T12:00:00Z',
        'attachmentSet': None,
    }


@pytest.fixture
def minimal_communication_data() -> Dict[str, Any]:
    """Return a dictionary with minimal communication data."""
    return {
        'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
        'body': 'My EC2 instance i-1234567890abcdef0 is not starting.',
        'submittedBy': 'user@example.com',
        'timeCreated': '2023-01-01T12:00:00Z',
    }


@pytest.fixture
def communications_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample communications response data."""
    return {
        'communications': [
            {
                'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
                'body': 'My EC2 instance i-1234567890abcdef0 is not starting.',
                'submittedBy': 'user@example.com',
                'timeCreated': '2023-01-01T12:00:00Z',
            },
            {
                'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
                'body': "I've tried rebooting the instance but it's still not starting.",
                'submittedBy': 'user@example.com',
                'timeCreated': '2023-01-01T12:30:00Z',
            },
        ],
        'nextToken': None,
    }


@pytest.fixture
def empty_communications_response_data() -> Dict[str, Any]:
    """Return a dictionary with empty communications response data."""
    return {
        'communications': [],
        'nextToken': None,
    }


@pytest.fixture
def service_data() -> Dict[str, Any]:
    """Return a dictionary with sample service data."""
    return {
        'code': 'amazon-elastic-compute-cloud-linux',
        'name': 'Amazon Elastic Compute Cloud (Linux)',
        'categories': [
            {'code': 'using-aws', 'name': 'Using AWS'},
            {'code': 'performance', 'name': 'Performance'},
        ],
    }


@pytest.fixture
def minimal_service_data() -> Dict[str, Any]:
    """Return a dictionary with minimal service data."""
    return {
        'code': 'amazon-elastic-compute-cloud-linux',
        'name': 'Amazon Elastic Compute Cloud (Linux)',
        'categories': [],
    }


@pytest.fixture
def services_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample services response data."""
    return {
        'services': [
            {
                'code': 'amazon-elastic-compute-cloud-linux',
                'name': 'Amazon Elastic Compute Cloud (Linux)',
                'categories': [
                    {'code': 'using-aws', 'name': 'Using AWS'},
                    {'code': 'performance', 'name': 'Performance'},
                ],
            },
            {
                'code': 'amazon-s3',
                'name': 'Amazon Simple Storage Service',
                'categories': [{'code': 'using-aws', 'name': 'Using AWS'}],
            },
        ]
    }


@pytest.fixture
def empty_services_response_data() -> Dict[str, Any]:
    """Return a dictionary with empty services response data."""
    return {'services': []}


@pytest.fixture
def category_data() -> Dict[str, Any]:
    """Return a dictionary with sample category data."""
    return {'code': 'using-aws', 'name': 'Using AWS'}


@pytest.fixture
def severity_level_data() -> Dict[str, Any]:
    """Return a dictionary with sample severity level data."""
    return {'code': 'urgent', 'name': 'Production system down'}


@pytest.fixture
def minimal_severity_level_data() -> Dict[str, Any]:
    """Return a dictionary with minimal severity level data."""
    return {'code': 'urgent', 'name': 'Production system down'}


@pytest.fixture
def severity_levels_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample severity levels response data."""
    return {
        'severityLevels': [
            {'code': 'low', 'name': 'General guidance'},
            {'code': 'normal', 'name': 'System impaired'},
            {'code': 'high', 'name': 'Production system impaired'},
            {'code': 'urgent', 'name': 'Production system down'},
            {'code': 'critical', 'name': 'Business-critical system down'},
        ]
    }


@pytest.fixture
def empty_severity_levels_response_data() -> Dict[str, Any]:
    """Return a dictionary with empty severity levels response data."""
    return {'severityLevels': []}


@pytest.fixture
def supported_languages_data() -> List[Dict[str, Any]]:
    """Return a list of supported languages."""
    return [
        {'code': 'en', 'name': 'English', 'nativeName': 'English'},
        {'code': 'ja', 'name': 'Japanese', 'nativeName': '日本語'},
        {'code': 'zh', 'name': 'Chinese', 'nativeName': '中文'},
        {'code': 'ko', 'name': 'Korean', 'nativeName': '한국어'},
    ]


@pytest.fixture
def create_case_request_data() -> Dict[str, Any]:
    """Return a dictionary with sample create case request data."""
    return {
        'subject': 'EC2 instance not starting',
        'service_code': 'amazon-elastic-compute-cloud-linux',
        'category_code': 'using-aws',
        'severity_code': 'urgent',
        'communication_body': 'My EC2 instance i-1234567890abcdef0 is not starting.',
        'cc_email_addresses': ['team@example.com'],
        'language': 'en',
        'issue_type': 'technical',
        'attachment_set_id': None,
    }


@pytest.fixture
def minimal_create_case_request_data() -> Dict[str, Any]:
    """Return a dictionary with minimal create case request data."""
    return {
        'subject': 'EC2 instance not starting',
        'service_code': 'amazon-elastic-compute-cloud-linux',
        'category_code': 'using-aws',
        'severity_code': 'urgent',
        'communication_body': 'My EC2 instance i-1234567890abcdef0 is not starting.',
    }


@pytest.fixture
def create_case_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample create case response data."""
    return {
        'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
        'status': 'success',
        'message': 'Support case created successfully with ID: case-12345678910-2013-c4c1d2bf33c5cf47',
    }


@pytest.fixture
def describe_cases_request_data() -> Dict[str, Any]:
    """Return a dictionary with sample describe cases request data."""
    return {
        'case_id_list': ['case-12345678910-2013-c4c1d2bf33c5cf47'],
        'display_id': None,
        'after_time': '2023-01-01T00:00:00Z',
        'before_time': '2023-01-31T23:59:59Z',
        'include_resolved_cases': False,
        'include_communications': True,
        'language': 'en',
        'max_results': 100,
        'next_token': None,
    }


@pytest.fixture
def minimal_describe_cases_request_data() -> Dict[str, Any]:
    """Return a dictionary with minimal describe cases request data."""
    return {'include_resolved_cases': False, 'include_communications': True}


@pytest.fixture
def describe_cases_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample describe cases response data."""
    return {
        'cases': [
            {
                'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
                'displayId': '12345678910',
                'subject': 'EC2 instance not starting',
                'status': 'opened',
                'serviceCode': 'amazon-elastic-compute-cloud-linux',
                'categoryCode': 'using-aws',
                'severityCode': 'urgent',
                'submittedBy': 'user@example.com',
                'timeCreated': '2023-01-01T12:00:00Z',
                'recentCommunications': {
                    'communications': [
                        {
                            'caseId': 'case-12345678910-2013-c4c1d2bf33c5cf47',
                            'body': 'My EC2 instance i-1234567890abcdef0 is not starting.',
                            'submittedBy': 'user@example.com',
                            'timeCreated': '2023-01-01T12:00:00Z',
                        }
                    ],
                    'nextToken': None,
                },
            }
        ],
        'nextToken': None,
    }


@pytest.fixture
def empty_describe_cases_response_data() -> Dict[str, Any]:
    """Return a dictionary with empty describe cases response data."""
    return {'cases': [], 'nextToken': None}


@pytest.fixture
def add_communication_request_data() -> Dict[str, Any]:
    """Return a dictionary with sample add communication request data."""
    return {
        'case_id': 'case-12345678910-2013-c4c1d2bf33c5cf47',
        'communication_body': "I've tried rebooting the instance but it's still not starting.",
        'cc_email_addresses': ['team@example.com'],
        'attachment_set_id': None,
    }


@pytest.fixture
def minimal_add_communication_request_data() -> Dict[str, Any]:
    """Return a dictionary with minimal add communication request data."""
    return {
        'case_id': 'case-12345678910-2013-c4c1d2bf33c5cf47',
        'communication_body': "I've tried rebooting the instance but it's still not starting.",
    }


@pytest.fixture
def add_communication_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample add communication response data."""
    return {
        'result': True,
        'status': 'success',
        'message': 'Communication added successfully to case: case-12345678910-2013-c4c1d2bf33c5cf47',
    }


@pytest.fixture
def resolve_case_request_data() -> Dict[str, Any]:
    """Return a dictionary with sample resolve case request data."""
    return {'case_id': 'case-12345678910-2013-c4c1d2bf33c5cf47'}


@pytest.fixture
def resolve_case_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample resolve case response data."""
    return {
        'initial_case_status': 'opened',
        'final_case_status': 'resolved',
        'status': 'success',
        'message': 'Support case resolved successfully: case-12345678910-2013-c4c1d2bf33c5cf47',
    }


# Client Tests


class TestSupportClient:
    """Tests for the SupportClient class."""

    @patch('boto3.Session')
    def test_initialization_default_parameters(self, mock_session):
        """Test that SupportClient initializes correctly with default parameters."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.return_value = MagicMock(access_key='TEST1234')

        # Create client
        client = SupportClient()

        # Verify
        mock_session.assert_called_once_with(**{'region_name': DEFAULT_REGION})
        mock_session.return_value.client.assert_called_once_with(
            'support',
            config=ANY,  # Using ANY since we just want to verify the service name
        )
        assert client.region_name == DEFAULT_REGION

    @patch('boto3.Session')
    def test_initialization_custom_parameters(self, mock_session):
        """Test that SupportClient initializes correctly with custom parameters."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.return_value = MagicMock(access_key='TEST1234')

        # Test parameters
        custom_region = 'us-west-2'
        custom_profile = 'test-profile'

        # Create client
        client = SupportClient(region_name=custom_region, profile_name=custom_profile)

        # Verify
        mock_session.assert_called_once_with(
            **{'region_name': custom_region, 'profile_name': custom_profile}
        )
        mock_session.return_value.client.assert_called_once_with(
            'support',
            config=ANY,  # Using ANY since we just want to verify the service name
        )
        assert client.region_name == custom_region

    @patch('boto3.Session')
    def test_initialization_subscription_required_error(self, mock_session):
        """Test that a SupportClient raises an error when subscription is required."""
        # Setup mock
        error_response = {
            'Error': {'Code': 'SubscriptionRequiredException', 'Message': 'Subscription required'}
        }
        mock_session.return_value.client.side_effect = ClientError(error_response, 'create_case')

        # Create client and verify error
        with pytest.raises(ClientError) as excinfo:
            SupportClient()

        # Verify error
        assert excinfo.value.response['Error']['Code'] == 'SubscriptionRequiredException'

    @patch('boto3.Session')
    def test_initialization_other_client_error(self, mock_session):
        """Test that a SupportClient raises an error when there's another client error."""
        # Setup mock
        error_response = {'Error': {'Code': 'OtherError', 'Message': 'Some other error'}}
        mock_session.return_value.client.side_effect = ClientError(error_response, 'create_case')

        # Create client and verify error
        with pytest.raises(ClientError) as excinfo:
            SupportClient()

        # Verify error
        assert excinfo.value.response['Error']['Code'] == 'OtherError'

    @patch('boto3.Session')
    @patch('asyncio.get_event_loop')
    async def test_run_in_executor(self, mock_get_event_loop, mock_session):
        """Test that _run_in_executor runs a function in an executor."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_loop = MagicMock()
        mock_get_event_loop.return_value = mock_loop
        mock_loop.run_in_executor.return_value = asyncio.Future()
        mock_loop.run_in_executor.return_value.set_result('test-result')

        # Create client
        client = SupportClient()

        # Call _run_in_executor
        mock_func = MagicMock()
        result = await client._run_in_executor(mock_func, 'arg1', arg2='arg2')

        # Verify
        mock_get_event_loop.assert_called_once()
        mock_loop.run_in_executor.assert_called_once()
        assert result == 'test-result'

    @patch('boto3.Session')
    def test_initialization_with_no_credentials_warning(self, mock_session):
        """Test initialization when no credentials are found and warning is logged."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.return_value = None

        with patch('awslabs.aws_support_mcp_server.client.logger') as mock_logger:
            SupportClient()
            mock_logger.warning.assert_called_with('No AWS credentials found in session')

    @patch('boto3.Session')
    def test_initialization_with_credential_error_warning(self, mock_session):
        """Test initialization when credential check raises an error and warning is logged."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.side_effect = Exception('Credential error')

        with patch('awslabs.aws_support_mcp_server.client.logger') as mock_logger:
            SupportClient()
            mock_logger.warning.assert_called_with('Error checking credentials: Credential error')

    @patch('boto3.Session')
    def test_initialization_with_unexpected_error_logging(self, mock_session):
        """Test initialization when an unexpected error occurs and error is logged."""
        # Setup mock
        mock_session.side_effect = Exception('Unexpected initialization error')

        with patch('awslabs.aws_support_mcp_server.client.logger') as mock_logger:
            with pytest.raises(Exception) as exc_info:
                SupportClient()
            assert str(exc_info.value) == 'Unexpected initialization error'
            mock_logger.error.assert_called_with(
                'Unexpected error initializing AWS Support client: Unexpected initialization error',
                exc_info=True,
            )

    @patch('boto3.Session')
    def test_initialization_business_subscription_required_error(self, mock_session):
        """Test initialization when AWS Business Support subscription is required."""
        # Setup mock
        MagicMock()
        error_response = {
            'Error': {
                'Code': 'SubscriptionRequiredException',
                'Message': 'AWS Business Support or higher is required',
            }
        }
        mock_session.return_value.client.side_effect = ClientError(error_response, 'support')

        # Verify subscription required error is raised
        with pytest.raises(ClientError) as exc_info:
            SupportClient()

        assert exc_info.value.response['Error']['Code'] == 'SubscriptionRequiredException'

    @patch('boto3.Session')
    def test_initialization_unexpected_error(self, mock_session):
        """Test initialization when unexpected error occurs."""
        # Setup mock
        mock_session.side_effect = Exception('Unexpected error')

        # Verify error is raised
        with pytest.raises(Exception) as exc_info:
            SupportClient()

        assert str(exc_info.value) == 'Unexpected error'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_communications_case_not_found(
        self, mock_run_in_executor, mock_session
    ):
        """Test describe_communications when case is not found."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {'Error': {'Code': 'CaseIdNotFound', 'Message': 'Case not found'}}
        mock_run_in_executor.side_effect = ClientError(error_response, 'describe_communications')

        # Create client
        client = SupportClient()

        # Verify error is raised
        with pytest.raises(ClientError) as exc_info:
            await client.describe_communications('non-existent-case')

        assert exc_info.value.response['Error']['Code'] == 'CaseIdNotFound'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_communications_unexpected_error(
        self, mock_run_in_executor, mock_session
    ):
        """Test describe_communications when unexpected error occurs."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.side_effect = Exception('Unexpected error')

        # Create client
        client = SupportClient()

        # Verify error is raised
        with pytest.raises(Exception) as exc_info:
            await client.describe_communications('test-case')

        assert str(exc_info.value) == 'Unexpected error'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_supported_languages_client_error(
        self, mock_run_in_executor, mock_session
    ):
        """Test describe_supported_languages when client error occurs."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {'Error': {'Code': 'SomeError', 'Message': 'Some error occurred'}}
        mock_run_in_executor.side_effect = ClientError(
            error_response, 'describe_supported_languages'
        )

        # Create client
        client = SupportClient()

        # Verify error is raised
        with pytest.raises(ClientError) as exc_info:
            await client.describe_supported_languages(
                service_code='test-service',
                category_code='test-category',
            )

        assert exc_info.value.response['Error']['Code'] == 'SomeError'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_create_case_options_client_error(
        self, mock_run_in_executor, mock_session
    ):
        """Test describe_create_case_options when client error occurs."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {'Error': {'Code': 'SomeError', 'Message': 'Some error occurred'}}
        mock_run_in_executor.side_effect = ClientError(
            error_response, 'describe_create_case_options'
        )

        # Create client
        client = SupportClient()

        # Verify error is raised
        with pytest.raises(ClientError) as exc_info:
            await client.describe_create_case_options('test-service')

        assert exc_info.value.response['Error']['Code'] == 'SomeError'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_add_attachments_to_set_client_error(self, mock_run_in_executor, mock_session):
        """Test add_attachments_to_set when client error occurs."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {'Error': {'Code': 'SomeError', 'Message': 'Some error occurred'}}
        mock_run_in_executor.side_effect = ClientError(error_response, 'add_attachments_to_set')

        # Create client
        client = SupportClient()

        # Test data
        attachments = [{'fileName': 'test.txt', 'data': 'base64_encoded_content'}]

        # Verify error is raised
        with pytest.raises(ClientError) as exc_info:
            await client.add_attachments_to_set(attachments)

        assert exc_info.value.response['Error']['Code'] == 'SomeError'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_retry_with_backoff_max_retries_exceeded(
        self, mock_run_in_executor, mock_session
    ):
        """Test _retry_with_backoff when max retries are exceeded."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Create mock function that always fails with throttling
        mock_func = AsyncMock()
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_func.side_effect = ClientError(error_response, 'operation')

        # Verify error is raised after max retries
        with pytest.raises(ClientError) as exc_info:
            await client._retry_with_backoff(mock_func, max_retries=2)

        assert exc_info.value.response['Error']['Code'] == 'ThrottlingException'
        assert mock_func.call_count == 3  # Initial try + 2 retries

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_retry_with_backoff_non_retryable_error(
        self, mock_run_in_executor, mock_session
    ):
        """Test _retry_with_backoff with non-retryable error."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Create mock function that fails with non-retryable error
        mock_func = AsyncMock()
        error_response = {'Error': {'Code': 'ValidationError', 'Message': 'Invalid input'}}
        mock_func.side_effect = ClientError(error_response, 'operation')

        # Verify error is raised immediately
        with pytest.raises(ClientError) as exc_info:
            await client._retry_with_backoff(mock_func)

        assert exc_info.value.response['Error']['Code'] == 'ValidationError'
        assert mock_func.call_count == 1  # Only tried once

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_retry_with_backoff_unexpected_error(self, mock_run_in_executor, mock_session):
        """Test _retry_with_backoff with unexpected error."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Create mock function that fails with unexpected error
        mock_func = AsyncMock()
        mock_func.side_effect = Exception('Unexpected error')

        # Verify error is raised immediately
        with pytest.raises(Exception) as exc_info:
            await client._retry_with_backoff(mock_func)

        assert str(exc_info.value) == 'Unexpected error'
        assert mock_func.call_count == 1  # Only tried once

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_retry_with_backoff_too_many_requests(self, mock_run_in_executor, mock_session):
        """Test _retry_with_backoff with TooManyRequestsException."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Create mock function that fails with TooManyRequestsException
        mock_func = AsyncMock()
        error_response = {
            'Error': {'Code': 'TooManyRequestsException', 'Message': 'Too many requests'}
        }
        mock_func.side_effect = [ClientError(error_response, 'operation'), {'success': True}]

        # Call _retry_with_backoff
        result = await client._retry_with_backoff(mock_func)

        # Verify
        assert mock_func.call_count == 2
        assert result == {'success': True}

    @patch('boto3.Session')
    def test_initialization_credential_handling(self, mock_session):
        """Test that credential handling during initialization works correctly."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_credentials = MagicMock()
        mock_credentials.access_key = 'TEST1234567890'
        mock_session.return_value.get_credentials.return_value = mock_credentials

        # Create client
        client = SupportClient()

        # Verify
        mock_session.return_value.get_credentials.assert_called_once()
        assert client.region_name == DEFAULT_REGION

    @patch('boto3.Session')
    def test_initialization_no_credentials(self, mock_session):
        """Test initialization when no credentials are found."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.return_value = None

        # Create client
        client = SupportClient()

        # Verify
        mock_session.return_value.get_credentials.assert_called_once()
        assert client.region_name == DEFAULT_REGION

    @patch('boto3.Session')
    def test_initialization_credential_error(self, mock_session):
        """Test initialization when credential check raises an error."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.side_effect = Exception('Credential error')

        # Create client
        client = SupportClient()

        # Verify
        mock_session.return_value.get_credentials.assert_called_once()
        assert client.region_name == DEFAULT_REGION

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_communications(self, mock_run_in_executor, mock_session):
        """Test that describe_communications calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            'communications': [
                {
                    'caseId': 'test-case-id',
                    'body': 'Test communication',
                    'submittedBy': 'test-user',
                    'timeCreated': '2023-01-01T00:00:00Z',
                }
            ],
            'nextToken': None,
        }

        # Create client
        client = SupportClient()

        # Call describe_communications with all parameters
        result = await client.describe_communications(
            case_id='test-case-id',
            after_time='2023-01-01T00:00:00Z',
            before_time='2023-01-31T23:59:59Z',
            max_results=10,
            next_token='test-token',
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert 'communications' in result
        assert len(result['communications']) == 1
        assert result['communications'][0]['caseId'] == 'test-case-id'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_supported_languages(self, mock_run_in_executor, mock_session):
        """Test that describe_supported_languages calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            'supportedLanguages': [{'code': 'en', 'language': 'English', 'display': 'English'}]
        }

        # Create client
        client = SupportClient()

        # Call describe_supported_languages
        result = await client.describe_supported_languages(
            service_code='test-service',
            category_code='test-category',
            issue_type='technical',
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert 'supportedLanguages' in result
        assert len(result['supportedLanguages']) == 1
        assert result['supportedLanguages'][0]['code'] == 'en'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_create_case_options(self, mock_run_in_executor, mock_session):
        """Test that describe_create_case_options calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            'categoryList': [{'code': 'test-category', 'name': 'Test Category'}],
            'severityLevels': [{'code': 'low', 'name': 'General guidance'}],
        }

        # Create client
        client = SupportClient()

        # Call describe_create_case_options
        result = await client.describe_create_case_options(
            service_code='test-service', language='en'
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert 'categoryList' in result
        assert 'severityLevels' in result

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_retry_with_backoff_success(self, mock_run_in_executor, mock_session):
        """Test that _retry_with_backoff succeeds after retries."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Create mock function that fails twice then succeeds
        mock_func = AsyncMock()
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_func.side_effect = [
            ClientError(error_response, 'operation'),  # First call fails
            ClientError(error_response, 'operation'),  # Second call fails
            {'success': True},  # Third call succeeds
        ]

        # Call _retry_with_backoff
        result = await client._retry_with_backoff(mock_func)

        # Verify
        assert mock_func.call_count == 3
        assert result == {'success': True}

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_services(self, mock_run_in_executor, mock_session):
        """Test that describe_services calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            'services': [
                {
                    'code': 'test-service',
                    'name': 'Test Service',
                    'categories': [{'code': 'test-category', 'name': 'Test Category'}],
                }
            ]
        }

        # Create client
        client = SupportClient()

        # Call describe_services
        result = await client.describe_services(service_code_list=['test-service'], language='en')

        # Verify
        mock_run_in_executor.assert_called_once()
        assert 'services' in result
        assert len(result['services']) == 1
        assert result['services'][0]['code'] == 'test-service'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_severity_levels(self, mock_run_in_executor, mock_session):
        """Test that describe_severity_levels calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            'severityLevels': [{'code': 'low', 'name': 'General guidance'}]
        }

        # Create client
        client = SupportClient()

        # Call describe_severity_levels
        result = await client.describe_severity_levels(language='en')

        # Verify
        mock_run_in_executor.assert_called_once()
        assert 'severityLevels' in result
        assert len(result['severityLevels']) == 1
        assert result['severityLevels'][0]['code'] == 'low'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_add_attachments_to_set(self, mock_run_in_executor, mock_session):
        """Test that add_attachments_to_set calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            'attachmentSetId': 'test-attachment-set-id',
            'expiryTime': '2023-01-01T01:00:00Z',
        }

        # Create client
        client = SupportClient()

        # Test data
        attachments = [{'fileName': 'test.txt', 'data': 'base64_encoded_content'}]

        # Call add_attachments_to_set
        result = await client.add_attachments_to_set(
            attachments=attachments, attachment_set_id='existing-set-id'
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert 'attachmentSetId' in result
        assert 'expiryTime' in result

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_retry_with_backoff(self, mock_run_in_executor, mock_session):
        """Test that _retry_with_backoff handles retries correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Setup mock function that fails twice then succeeds
        mock_func = AsyncMock()
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_func.side_effect = [
            ClientError(error_response, 'operation'),  # First call fails
            ClientError(error_response, 'operation'),  # Second call fails
            {'success': True},  # Third call succeeds
        ]

        # Call _retry_with_backoff
        result = await client._retry_with_backoff(mock_func)

        # Verify
        assert mock_func.call_count == 3
        assert result == {'success': True}

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_create_case(self, mock_run_in_executor, mock_session):
        """Test that create_case calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {'caseId': 'test-case-id'}

        # Create client
        client = SupportClient()

        # Call create_case
        result = await client.create_case(
            subject='Test subject',
            service_code='test-service',
            category_code='test-category',
            severity_code='low',
            communication_body='Test body',
            cc_email_addresses=['test@example.com'],
            language='en',
            issue_type='technical',
            attachment_set_id='test-attachment-set-id',
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {'caseId': 'test-case-id'}

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_create_case_minimal(self, mock_run_in_executor, mock_session):
        """Test that create_case calls the AWS Support API with minimal parameters."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {'caseId': 'test-case-id'}

        # Create client
        client = SupportClient()

        # Call create_case
        result = await client.create_case(
            subject='Test subject',
            service_code='test-service',
            category_code='test-category',
            severity_code='low',
            communication_body='Test body',
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {'caseId': 'test-case-id'}

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_create_case_client_error(self, mock_run_in_executor, mock_session):
        """Test that create_case handles client errors correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {'Error': {'Code': 'OtherError', 'Message': 'Some other error'}}
        mock_run_in_executor.side_effect = ClientError(error_response, 'create_case')

        # Create client
        client = SupportClient()

        # Call create_case and verify error
        with pytest.raises(ClientError) as excinfo:
            await client.create_case(
                subject='Test subject',
                service_code='test-service',
                category_code='test-category',
                severity_code='low',
                communication_body='Test body',
            )

        # Verify error
        assert excinfo.value.response['Error']['Code'] == 'OtherError'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_cases(self, mock_run_in_executor, mock_session):
        """Test that describe_cases calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {'cases': [{'caseId': 'test-case-id'}]}

        # Create client
        client = SupportClient()

        # Call describe_cases
        result = await client.describe_cases(
            case_id_list=['test-case-id'],
            display_id='test-display-id',
            after_time='2023-01-01T00:00:00Z',
            before_time='2023-01-31T23:59:59Z',
            include_resolved_cases=True,
            include_communications=True,
            language='en',
            max_results=10,
            next_token='test-next-token',
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {'cases': [{'caseId': 'test-case-id'}]}

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_cases_minimal(self, mock_run_in_executor, mock_session):
        """Test that describe_cases calls the AWS Support API with minimal parameters."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {'cases': [{'caseId': 'test-case-id'}]}

        # Create client
        client = SupportClient()

        # Call describe_cases
        result = await client.describe_cases()

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {'cases': [{'caseId': 'test-case-id'}]}

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_cases_case_not_found(self, mock_run_in_executor, mock_session):
        """Test that describe_cases handles case not found errors correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {'Error': {'Code': 'CaseIdNotFound', 'Message': 'Case not found'}}
        mock_run_in_executor.side_effect = ClientError(error_response, 'describe_cases')

        # Create client
        client = SupportClient()

        # Call describe_cases and verify error
        with pytest.raises(ClientError) as excinfo:
            await client.describe_cases(case_id_list=['test-case-id'])

        # Verify error
        assert excinfo.value.response['Error']['Code'] == 'CaseIdNotFound'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_resolve_case(self, mock_run_in_executor, mock_session):
        """Test that resolve_case calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            'initialCaseStatus': 'opened',
            'finalCaseStatus': 'resolved',
        }

        # Create client
        client = SupportClient()

        # Call resolve_case
        result = await client.resolve_case(case_id='test-case-id')

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {'initialCaseStatus': 'opened', 'finalCaseStatus': 'resolved'}

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_resolve_case_case_not_found(self, mock_run_in_executor, mock_session):
        """Test that resolve_case handles case not found errors correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {'Error': {'Code': 'CaseIdNotFound', 'Message': 'Case not found'}}
        mock_run_in_executor.side_effect = ClientError(error_response, 'resolve_case')

        # Create client
        client = SupportClient()

        # Call resolve_case and verify error
        with pytest.raises(ClientError) as excinfo:
            await client.resolve_case(case_id='test-case-id')

        # Verify error
        assert excinfo.value.response['Error']['Code'] == 'CaseIdNotFound'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_add_communication_to_case(self, mock_run_in_executor, mock_session):
        """Test that add_communication_to_case calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {'result': True}

        # Create client
        client = SupportClient()

        # Call add_communication_to_case
        result = await client.add_communication_to_case(
            case_id='test-case-id',
            communication_body='Test body',
            cc_email_addresses=['test@example.com'],
            attachment_set_id='test-attachment-set-id',
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {'result': True}

    @patch('boto3.Session')
    def test_validate_email_addresses_valid(self, mock_session):
        """Test that _validate_email_addresses accepts valid email addresses."""
        # Setup
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        client = SupportClient()

        # Test valid email addresses
        valid_emails = [
            ['user@example.com'],
            ['first.last@example.com'],
            ['user+tag@example.com'],
            ['user@subdomain.example.com'],
            ['user@example-domain.com'],
            ['user123@example.com'],
            ['user@example.co.uk'],
            ['first.middle.last@example.com'],
            ['user@example.technology'],
            ['user-name@example.com'],
            ['user@example.com', 'another@example.com'],  # Multiple valid emails
        ]

        # Verify no exceptions are raised for valid emails
        for emails in valid_emails:
            try:
                client._validate_email_addresses(emails)
            except ValueError as e:
                pytest.fail(f'Validation failed for valid email(s) {emails}: {str(e)}')

    @patch('boto3.Session')
    def test_validate_email_addresses_invalid(self, mock_session):
        """Test that _validate_email_addresses rejects invalid email addresses."""
        # Setup
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        client = SupportClient()

        # Test cases with invalid email addresses
        invalid_cases = [
            ['plainaddress'],  # Missing @ and domain
            ['@missinguser.com'],  # Missing username
            ['user@'],  # Missing domain
            ['user@.com'],  # Missing domain name
            ['user@.com.'],  # Trailing dot
            ['user@com'],  # Missing dot in domain
            ['user@example..com'],  # Double dots
            ['user name@example.com'],  # Space in username
            ['user@exam ple.com'],  # Space in domain
            ['user@example.c'],  # TLD too short
            ['user@@example.com'],  # Double @
            ['user@example.com', 'invalid@'],  # One valid, one invalid
        ]

        # Verify ValueError is raised for each invalid case
        for emails in invalid_cases:
            with pytest.raises(ValueError) as exc_info:
                client._validate_email_addresses(emails)
            assert 'Invalid email address(es):' in str(exc_info.value)

    @patch('boto3.Session')
    def test_validate_email_addresses_empty_input(self, mock_session):
        """Test that _validate_email_addresses handles empty input correctly."""
        # Setup
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        client = SupportClient()

        # Test empty list
        client._validate_email_addresses([])

        # Test None - should not raise error since method handles None
        client._validate_email_addresses([])  # Use empty list instead of None

    @patch('boto3.Session')
    def test_validate_email_addresses_mixed_case(self, mock_session):
        """Test that _validate_email_addresses handles mixed case email addresses."""
        # Setup
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        client = SupportClient()

        # Test mixed case emails
        mixed_case_emails = ['User@Example.COM', 'UPPER@EXAMPLE.COM', 'lower@example.com']
        client._validate_email_addresses(mixed_case_emails)

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_add_communication_to_case_minimal(self, mock_run_in_executor, mock_session):
        """Test that add_communication_to_case calls the AWS Support API with minimal parameters."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {'result': True}

        # Create client
        client = SupportClient()

        # Call add_communication_to_case
        result = await client.add_communication_to_case(
            case_id='test-case-id', communication_body='Test body'
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {'result': True}

    @patch('boto3.Session')
    def test_validate_issue_type_valid(self, mock_session):
        """Test that _validate_issue_type accepts valid issue types."""
        # Setup
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        client = SupportClient()

        # Test all valid issue types from IssueType enum
        valid_types = ['technical', 'account-and-billing', 'service-limit']

        # Verify no exceptions are raised for valid types
        for issue_type in valid_types:
            try:
                client._validate_issue_type(issue_type)
            except ValueError as e:
                pytest.fail(f'Validation failed for valid issue type {issue_type}: {str(e)}')

    @patch('boto3.Session')
    def test_validate_issue_type_invalid(self, mock_session):
        """Test that _validate_issue_type rejects invalid issue types."""
        # Setup
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        client = SupportClient()

        # Test invalid issue types
        invalid_types = [
            '',  # Empty string
            'invalid',  # Non-existent type
            'TECHNICAL',  # Wrong case
            'tech',  # Partial match
            'billing',  # Partial match
            ' technical ',  # Extra whitespace
        ]

        # Verify ValueError is raised for each invalid type
        for issue_type in invalid_types:
            with pytest.raises(ValueError) as exc_info:
                client._validate_issue_type(issue_type)
            assert 'Invalid issue type:' in str(exc_info.value)
            assert 'Must be one of:' in str(exc_info.value)

    @patch('boto3.Session')
    def test_validate_language_valid(self, mock_session):
        """Test that _validate_language accepts valid language codes."""
        # Setup
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        client = SupportClient()

        # Test all permitted language codes
        for lang in PERMITTED_LANGUAGE_CODES:
            try:
                client._validate_language(lang)
            except ValueError as e:
                pytest.fail(f'Validation failed for valid language code {lang}: {str(e)}')

    @patch('boto3.Session')
    def test_validate_language_invalid(self, mock_session):
        """Test that _validate_language rejects invalid language codes."""
        # Setup
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        client = SupportClient()

        # Test invalid language codes
        invalid_codes = [
            '',  # Empty string
            'eng',  # Wrong format
            'EN',  # Wrong case
            'zz',  # Non-existent code
            ' en ',  # Extra whitespace
            'en-US',  # Wrong format
            'english',  # Full name instead of code
        ]

        # Verify ValueError is raised for each invalid code
        for lang in invalid_codes:
            with pytest.raises(ValueError) as exc_info:
                client._validate_language(lang)
            assert 'Invalid language code:' in str(exc_info.value)
            assert 'Must be one of:' in str(exc_info.value)

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_add_communication_to_case_case_not_found(
        self, mock_run_in_executor, mock_session
    ):
        """Test that add_communication_to_case handles case not found errors correctly."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {'Error': {'Code': 'CaseIdNotFound', 'Message': 'Case not found'}}
        mock_run_in_executor.side_effect = ClientError(error_response, 'add_communication_to_case')

        # Create client
        client = SupportClient()

        # Call add_communication_to_case and verify error
        with pytest.raises(ClientError) as excinfo:
            await client.add_communication_to_case(
                case_id='test-case-id', communication_body='Test body'
            )

        # Verify error
        assert excinfo.value.response['Error']['Code'] == 'CaseIdNotFound'


# Error Handling Tests


class TestErrorHandling:
    """Test suite for error handling functions in the AWS Support MCP Server."""

    from awslabs.aws_support_mcp_server.consts import (
        ERROR_AUTHENTICATION_FAILED,
        ERROR_CASE_NOT_FOUND,
        ERROR_RATE_LIMIT_EXCEEDED,
        ERROR_SUBSCRIPTION_REQUIRED,
    )

    """Tests for the error handling functions."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context with error method."""
        context = MagicMock()
        context.error = AsyncMock(return_value={'status': 'error', 'message': 'Error message'})
        return context

    async def test_handle_client_error_access_denied(self, mock_context):
        """Test handling of AccessDeniedException."""
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        error = ClientError(error_response, 'test_operation')

        result = await handle_client_error(mock_context, error, 'test_operation')

        assert result['status'] == 'error'
        assert result['message'] == ERROR_AUTHENTICATION_FAILED
        assert result['status_code'] == 403
        mock_context.error.assert_called_once()

    async def test_handle_client_error_case_not_found(self, mock_context):
        """Test handling of CaseIdNotFound."""
        error_response = {'Error': {'Code': 'CaseIdNotFound', 'Message': 'Case not found'}}
        error = ClientError(error_response, 'test_operation')

        result = await handle_client_error(mock_context, error, 'test_operation')

        assert result['status'] == 'error'
        assert result['message'] == ERROR_CASE_NOT_FOUND
        assert result['status_code'] == 404
        mock_context.error.assert_called_once()

    async def test_handle_client_error_throttling(self, mock_context):
        """Test handling of ThrottlingException."""
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        error = ClientError(error_response, 'test_operation')

        result = await handle_client_error(mock_context, error, 'test_operation')

        assert result['status'] == 'error'
        assert result['message'] == ERROR_RATE_LIMIT_EXCEEDED
        assert result['status_code'] == 429
        mock_context.error.assert_called_once()

    async def test_handle_general_error_with_custom_exception(self, mock_context):
        """Test handling of custom exception types."""

        class CustomError(Exception):
            pass

        error = CustomError('Custom error message')
        result = await handle_general_error(mock_context, error, 'test_operation')

        assert result['status'] == 'error'
        assert 'Error in test_operation' in result['message']
        assert 'CustomError' in result['message']
        assert result['details']['error_type'] == 'CustomError'
        assert result['status_code'] == 500
        mock_context.error.assert_called_once()

    def test_create_error_response_with_details(self):
        """Test creating error response with additional details."""
        details = {
            'error_code': 'TEST001',
            'error_source': 'test_module',
            'additional_info': 'Test information',
        }
        result = create_error_response('Test error', details=details, status_code=418)

        assert result['status'] == 'error'
        assert result['message'] == 'Test error'
        assert result['status_code'] == 418
        assert 'timestamp' in result
        assert result['details'] == details

    async def test_handle_client_error_subscription_required(self, mock_context):
        """Test handling of SubscriptionRequiredException."""
        error_response = {
            'Error': {'Code': 'SubscriptionRequiredException', 'Message': 'Subscription required'}
        }
        error = ClientError(error_response, 'test_operation')

        result = await handle_client_error(mock_context, error, 'test_operation')

        assert result['status'] == 'error'
        assert result['message'] == ERROR_SUBSCRIPTION_REQUIRED
        assert result['status_code'] == 400  # Default client error status code
        mock_context.error.assert_called_once()

    """Tests for the error handling functions."""

    async def test_handle_client_error_unauthorized(self):
        """Test handling of UnauthorizedException."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(
            return_value={'status': 'error', 'message': 'AWS Support API error: Unauthorized'}
        )
        error_response = {'Error': {'Code': 'UnauthorizedException', 'Message': 'Unauthorized'}}
        error = ClientError(error_response, 'operation_name')

        # Call function
        result = await handle_client_error(context, error, 'test_function')

        # Verify
        assert result['status'] == 'error'
        assert 'Unauthorized' in result['message']

    async def test_handle_client_error_other(self):
        """Test handling of other client errors."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(
            return_value={'status': 'error', 'message': 'AWS Support API error: Some other error'}
        )
        error_response = {'Error': {'Code': 'OtherError', 'Message': 'Some other error'}}
        error = ClientError(error_response, 'operation_name')

        # Call function
        result = await handle_client_error(context, error, 'test_function')

        # Verify
        assert result['status'] == 'error'
        assert 'AWS Support API error' in result['message']
        assert 'Some other error' in result['message']

    async def test_handle_validation_error(self):
        """Test handling of validation errors."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(return_value={'status': 'error', 'message': 'Validation error'})

        # Create a ValidationError with proper arguments
        from pydantic import BaseModel

        class TestModel(BaseModel):
            field1: str
            field2: int

        try:
            TestModel(field1='test', field2=123)  # This should pass first
            # Now test with missing field2 - this will raise ValidationError
            TestModel(field1='test', field2=456)  # This should also pass
        except ValidationError:
            # This shouldn't happen with valid data, so create the error manually
            pass

        # Actually test the validation error case
        try:
            TestModel(field1='test', field2=789)  # Valid case
        except Exception:
            pass

        # Create a proper validation error for testing
        try:
            # Use an invalid model creation that will definitely fail
            from pydantic import ValidationError as PydanticValidationError

            raise PydanticValidationError.from_exception_data('TestModel', [])
        except ValidationError as validation_error:
            # Call function
            result = await handle_validation_error(context, validation_error, 'test_function')

            # Verify
            assert result is not None
            assert result['status'] == 'error'
            assert 'Validation error' in result['message']

    async def test_handle_general_error(self):
        """Test handling of general errors."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(
            return_value={
                'status': 'error',
                'message': 'Error in test_function: Test error message',
            }
        )
        error = ValueError('Test error message')

        # Call function
        result = await handle_general_error(context, error, 'test_function')

        # Verify
        assert result['status'] == 'error'
        assert 'Error in test_function' in result['message']
        assert 'Test error message' in result['message']

    async def test_handle_general_error_with_internal_server_error(self):
        """Test handling of general errors with internal server error."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(
            return_value={
                'status': 'error',
                'message': 'Error in test_function: Internal server error',
            }
        )
        error = Exception('Internal server error')

        # Call function
        result = await handle_general_error(context, error, 'test_function')

        # Verify
        assert result['status'] == 'error'
        assert 'Error in test_function' in result['message']
        assert 'Internal server error' in result['message']


# Formatter Tests
class TestFormatCases:
    """Tests for the format_cases function."""

    def test_format_multiple_cases(self, multiple_support_cases_data):
        """Test formatting multiple cases."""
        formatted = format_cases(multiple_support_cases_data)

        assert len(formatted) == len(multiple_support_cases_data)
        for formatted_case, original_case in zip(
            formatted, multiple_support_cases_data, strict=False
        ):
            assert formatted_case['caseId'] == original_case['caseId']
            assert formatted_case['subject'] == original_case['subject']

    def test_format_empty_cases_list(self):
        """Test formatting an empty list of cases."""
        formatted = format_cases([])
        assert formatted == []


class TestFormatCommunications:
    """Tests for the format_communications function."""

    def test_format_communications_with_attachments(self, communications_response_data):
        """Test formatting communications with attachments."""
        formatted = format_communications(communications_response_data)

        assert 'communications' in formatted
        assert len(formatted['communications']) == len(
            communications_response_data['communications']
        )

        first_comm = formatted['communications'][0]
        orig_comm = communications_response_data['communications'][0]
        assert first_comm['body'] == orig_comm['body']
        assert first_comm['submittedBy'] == orig_comm['submittedBy']

    def test_format_empty_communications(self, empty_communications_response_data):
        """Test formatting empty communications."""
        formatted = format_communications(empty_communications_response_data)

        assert 'communications' in formatted
        assert len(formatted['communications']) == 0
        assert formatted['nextToken'] is None


class TestFormatServices:
    """Tests for the format_services function."""

    def test_format_services_with_categories(self, services_response_data):
        """Test formatting services with categories."""
        formatted = format_services(services_response_data['services'])

        # Verify first service
        first_service = services_response_data['services'][0]
        service_code = first_service['code']

        assert service_code in formatted
        assert formatted[service_code]['name'] == first_service['name']
        assert len(formatted[service_code]['categories']) == len(first_service['categories'])

    def test_format_empty_services(self, empty_services_response_data):
        """Test formatting empty services."""
        formatted = format_services(empty_services_response_data['services'])
        assert formatted == {}


class TestFormatSeverityLevels:
    """Tests for the format_severity_levels function."""

    def test_format_severity_levels(self, severity_levels_response_data):
        """Test formatting severity levels."""
        formatted = format_severity_levels(severity_levels_response_data['severityLevels'])

        for level in severity_levels_response_data['severityLevels']:
            assert level['code'] in formatted
            assert formatted[level['code']]['name'] == level['name']

    def test_format_empty_severity_levels(self, empty_severity_levels_response_data):
        """Test formatting empty severity levels."""
        formatted = format_severity_levels(empty_severity_levels_response_data['severityLevels'])
        assert formatted == {}


class TestFormatMarkdown:
    """Tests for the Markdown formatting functions."""

    def test_format_markdown_case_summary(self, support_case_data):
        """Test formatting a case summary in Markdown."""
        formatted_case = format_case(support_case_data)
        markdown = format_markdown_case_summary(formatted_case)

        # Verify key elements are present in the Markdown
        assert f'**Case ID**: {support_case_data["caseId"]}' in markdown
        assert f'**Subject**: {support_case_data["subject"]}' in markdown
        assert '## Recent Communications' in markdown

        # Verify communication details
        first_comm = support_case_data['recentCommunications']['communications'][0]
        assert first_comm['body'] in markdown
        assert first_comm['submittedBy'] in markdown

    def test_format_markdown_services(self, services_response_data):
        """Test formatting services in Markdown."""
        formatted_services = format_services(services_response_data['services'])
        markdown = format_markdown_services(formatted_services)

        # Verify key elements are present in the Markdown
        assert '# AWS Services' in markdown

        # Verify first service
        first_service = services_response_data['services'][0]
        assert f'## {first_service["name"]}' in markdown
        assert f'`{first_service["code"]}`' in markdown

        # Verify categories
        if first_service['categories']:
            assert '### Categories' in markdown
            first_category = first_service['categories'][0]
            assert f'`{first_category["code"]}`' in markdown

    def test_format_markdown_severity_levels(self, severity_levels_response_data):
        """Test formatting severity levels in Markdown."""
        formatted_levels = format_severity_levels(severity_levels_response_data['severityLevels'])
        markdown = format_markdown_severity_levels(formatted_levels)

        # Verify key elements are present in the Markdown
        assert '# AWS Support Severity Levels' in markdown

        # Verify severity levels
        for level in severity_levels_response_data['severityLevels']:
            assert f'**{level["name"]}**' in markdown
            assert f'`{level["code"]}`' in markdown

    def test_format_json_response(self):
        """Test JSON response formatting."""
        test_data = {'key1': 'value1', 'key2': {'nested': 'value2'}, 'key3': [1, 2, 3]}

        formatted = format_json_response(test_data)
        assert isinstance(formatted, str)
        parsed = json.loads(formatted)
        assert parsed == test_data


class TestFormatCase:
    """Tests for the format_case function."""

    def test_valid_case_formatting(self, support_case_data):
        """Test that a valid case is formatted correctly."""
        formatted_case = format_case(support_case_data)
        assert formatted_case['caseId'] == support_case_data['caseId']
        assert formatted_case['displayId'] == support_case_data['displayId']
        assert formatted_case['subject'] == support_case_data['subject']
        assert formatted_case['status'] == support_case_data['status']
        assert formatted_case['serviceCode'] == support_case_data['serviceCode']
        assert formatted_case['categoryCode'] == support_case_data['categoryCode']
        assert formatted_case['severityCode'] == support_case_data['severityCode']
        assert formatted_case['submittedBy'] == support_case_data['submittedBy']
        assert formatted_case['timeCreated'] == support_case_data['timeCreated']
        assert formatted_case['ccEmailAddresses'] == support_case_data['ccEmailAddresses']
        assert formatted_case['language'] == support_case_data['language']
        assert 'recentCommunications' in formatted_case
        assert len(formatted_case['recentCommunications']['communications']) == len(
            support_case_data['recentCommunications']['communications']
        )

    def test_minimal_case_formatting(self, minimal_support_case_data):
        """Test that a minimal case is formatted correctly."""
        formatted_case = format_case(minimal_support_case_data)
        assert formatted_case['caseId'] == minimal_support_case_data['caseId']
        assert formatted_case['subject'] == minimal_support_case_data['subject']
        assert formatted_case['status'] == minimal_support_case_data['status']
        assert formatted_case['serviceCode'] == minimal_support_case_data['serviceCode']
        assert formatted_case['categoryCode'] == minimal_support_case_data['categoryCode']
        assert formatted_case['severityCode'] == minimal_support_case_data['severityCode']
        assert formatted_case['submittedBy'] == minimal_support_case_data['submittedBy']
        assert formatted_case['timeCreated'] == minimal_support_case_data['timeCreated']

    def test_edge_case_formatting(self, edge_case_support_case_data):
        """Test that an edge case is formatted correctly."""
        formatted_case = format_case(edge_case_support_case_data)
        assert formatted_case['caseId'] == edge_case_support_case_data['caseId']
        assert formatted_case['subject'] == edge_case_support_case_data['subject']
        assert len(formatted_case['subject']) == len(edge_case_support_case_data['subject'])


# Server Tests


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_create_case(mock_support_client):
    """Test that create_case calls the AWS Support API correctly."""
    # Setup mocks
    mock_support_client.create_case = AsyncMock(return_value={'caseId': 'test-case-id'})

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Error message'})

    # Call the logic function directly
    result = await _create_support_case_logic(
        context,
        subject='Test subject',
        service_code='test-service',
        category_code='test-category',
        severity_code='low',
        communication_body='Test body',
        cc_email_addresses=['test@example.com'],
        language='en',
        issue_type='technical',
        attachment_set_id='test-attachment-set-id',
    )

    # Verify
    mock_support_client.create_case.assert_called_once()
    assert 'caseId' in result
    assert result['caseId'] == 'test-case-id'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_cases(mock_support_client):
    """Test that describe_cases calls the AWS Support API correctly."""
    # Setup mocks
    mock_support_client.describe_cases = AsyncMock(
        return_value={
            'cases': [
                {
                    'caseId': 'test-case-id',
                    'displayId': 'test-display-id',
                    'subject': 'Test subject',
                    'status': 'opened',
                    'serviceCode': 'test-service',
                    'categoryCode': 'test-category',
                    'severityCode': 'low',
                    'submittedBy': 'test-user',
                    'timeCreated': '2023-01-01T00:00:00Z',
                    'recentCommunications': {
                        'communications': [
                            {
                                'caseId': 'test-case-id',
                                'body': 'Test body',
                                'submittedBy': 'test-user',
                                'timeCreated': '2023-01-01T00:00:00Z',
                            }
                        ]
                    },
                }
            ]
        }
    )

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Error message'})

    # Call the logic function directly
    result = await _describe_support_cases_logic(
        context,
        case_id_list=['test-case-id'],
        display_id='test-display-id',
        after_time='2023-01-01T00:00:00Z',
        before_time='2023-01-31T23:59:59Z',
        include_resolved_cases=True,
        include_communications=True,
        language='en',
        max_results=10,
        next_token='test-next-token',
        format='json',
    )

    # Verify
    mock_support_client.describe_cases.assert_called_once()
    assert 'cases' in result
    assert len(result['cases']) == 1
    assert result['cases'][0]['caseId'] == 'test-case-id'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_add_communication_to_case(mock_support_client):
    """Test that add_communication_to_case calls the AWS Support API correctly."""
    # Setup mocks
    mock_support_client.add_communication_to_case = AsyncMock(return_value={'result': True})

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Error message'})

    # Call the logic function directly
    result = await _add_communication_to_case_logic(
        context,
        case_id='test-case-id',
        communication_body='Test body',
        cc_email_addresses=['test@example.com'],
        attachment_set_id='test-attachment-set-id',
    )

    # Verify
    mock_support_client.add_communication_to_case.assert_called_once()
    assert 'result' in result
    assert result['result'] is True


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_resolve_case(mock_support_client):
    """Test that resolve_case calls the AWS Support API correctly."""
    # Setup mocks
    mock_support_client.resolve_case = AsyncMock(
        return_value={'initialCaseStatus': 'opened', 'finalCaseStatus': 'resolved'}
    )

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Error message'})

    # Call the logic function directly
    result = await _resolve_support_case_logic(context, case_id='test-case-id')

    # Verify
    mock_support_client.resolve_case.assert_called_once()
    assert 'initialCaseStatus' in result
    assert result['initialCaseStatus'] == 'opened'
    assert 'finalCaseStatus' in result
    assert result['finalCaseStatus'] == 'resolved'


async def test_error_handling():
    """Test that the server handles errors correctly."""


# Server Logic Error Handling Tests


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_create_case_validation_error(mock_support_client):
    """Test create_case_logic handles ValidationError correctly."""
    # Setup mocks
    mock_support_client.create_case = AsyncMock(return_value={'caseId': 'test-case-id'})

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Validation error'})

    # Mock CreateCaseResponse to raise ValidationError
    with patch('awslabs.aws_support_mcp_server.server.CreateCaseResponse') as mock_response:
        from pydantic import ValidationError as PydanticValidationError

        mock_response.side_effect = PydanticValidationError.from_exception_data(
            'CreateCaseResponse', []
        )

        result = await _create_support_case_logic(
            context,
            subject='Test',
            service_code='test-service',
            category_code='test-category',
            severity_code='low',
            communication_body='Test body',
        )

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_create_case_client_error(mock_support_client):
    """Test create_case_logic handles ClientError correctly."""
    # Setup mocks
    error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
    mock_support_client.create_case = AsyncMock(
        side_effect=ClientError(error_response, 'create_case')
    )

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Client error'})

    result = await _create_support_case_logic(
        context,
        subject='Test',
        service_code='test-service',
        category_code='test-category',
        severity_code='low',
        communication_body='Test body',
    )

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_create_case_general_error(mock_support_client):
    """Test create_case_logic handles general Exception correctly."""
    # Setup mocks
    mock_support_client.create_case = AsyncMock(side_effect=Exception('Unexpected error'))

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'General error'})

    result = await _create_support_case_logic(
        context,
        subject='Test',
        service_code='test-service',
        category_code='test-category',
        severity_code='low',
        communication_body='Test body',
    )

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_cases_validation_error(mock_support_client):
    """Test describe_cases_logic handles ValidationError correctly."""
    # Setup mocks
    mock_support_client.describe_cases = AsyncMock(
        return_value={'cases': [{'caseId': 'test-case-id', 'invalid_field': 'value'}]}
    )

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Validation error'})

    # This should raise ValidationError when creating SupportCase
    result = await _describe_support_cases_logic(context)

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_cases_client_error(mock_support_client):
    """Test describe_cases_logic handles ClientError correctly."""
    # Setup mocks
    error_response = {'Error': {'Code': 'CaseIdNotFound', 'Message': 'Case not found'}}
    mock_support_client.describe_cases = AsyncMock(
        side_effect=ClientError(error_response, 'describe_cases')
    )

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Client error'})

    result = await _describe_support_cases_logic(context)

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_cases_general_error(mock_support_client):
    """Test describe_cases_logic handles general Exception correctly."""
    # Setup mocks
    mock_support_client.describe_cases = AsyncMock(side_effect=Exception('Unexpected error'))

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'General error'})

    result = await _describe_support_cases_logic(context)

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_cases_markdown_format(mock_support_client):
    """Test describe_cases_logic with markdown format."""
    # Setup mocks
    mock_support_client.describe_cases = AsyncMock(
        return_value={
            'cases': [
                {
                    'caseId': 'test-case-id',
                    'subject': 'Test subject',
                    'status': 'opened',
                    'serviceCode': 'test-service',
                    'categoryCode': 'test-category',
                    'severityCode': 'low',
                    'submittedBy': 'test-user',
                    'timeCreated': '2023-01-01T00:00:00Z',
                }
            ]
        }
    )

    # Create mock context
    context = MagicMock()

    result = await _describe_support_cases_logic(context, format='markdown')

    assert 'markdown' in result


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_add_communication_validation_error(mock_support_client):
    """Test add_communication_logic handles ValidationError correctly."""
    # Setup mocks
    mock_support_client.add_communication_to_case = AsyncMock(return_value={'result': True})

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Validation error'})

    # Mock AddCommunicationResponse to raise ValidationError
    with patch('awslabs.aws_support_mcp_server.server.AddCommunicationResponse') as mock_response:
        from pydantic import ValidationError as PydanticValidationError

        mock_response.side_effect = PydanticValidationError.from_exception_data(
            'AddCommunicationResponse', []
        )

        result = await _add_communication_to_case_logic(
            context, case_id='test-case-id', communication_body='Test body'
        )

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_add_communication_client_error(mock_support_client):
    """Test add_communication_logic handles ClientError correctly."""
    # Setup mocks
    error_response = {'Error': {'Code': 'CaseIdNotFound', 'Message': 'Case not found'}}
    mock_support_client.add_communication_to_case = AsyncMock(
        side_effect=ClientError(error_response, 'add_communication_to_case')
    )

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Client error'})

    result = await _add_communication_to_case_logic(
        context, case_id='test-case-id', communication_body='Test body'
    )

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_add_communication_general_error(mock_support_client):
    """Test add_communication_logic handles general Exception correctly."""
    # Setup mocks
    mock_support_client.add_communication_to_case = AsyncMock(
        side_effect=Exception('Unexpected error')
    )

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'General error'})

    result = await _add_communication_to_case_logic(
        context, case_id='test-case-id', communication_body='Test body'
    )

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_resolve_case_validation_error(mock_support_client):
    """Test resolve_case_logic handles ValidationError correctly."""
    # Setup mocks
    mock_support_client.resolve_case = AsyncMock(
        return_value={'initialCaseStatus': 'opened', 'finalCaseStatus': 'resolved'}
    )

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Validation error'})

    # Mock ResolveCaseResponse to raise ValidationError
    with patch('awslabs.aws_support_mcp_server.server.ResolveCaseResponse') as mock_response:
        from pydantic import ValidationError as PydanticValidationError

        mock_response.side_effect = PydanticValidationError.from_exception_data(
            'ResolveCaseResponse', []
        )

        result = await _resolve_support_case_logic(context, case_id='test-case-id')

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_resolve_case_client_error(mock_support_client):
    """Test resolve_case_logic handles ClientError correctly."""
    # Setup mocks
    error_response = {'Error': {'Code': 'CaseIdNotFound', 'Message': 'Case not found'}}
    mock_support_client.resolve_case = AsyncMock(
        side_effect=ClientError(error_response, 'resolve_case')
    )

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'Client error'})

    result = await _resolve_support_case_logic(context, case_id='test-case-id')

    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_resolve_case_general_error(mock_support_client):
    """Test resolve_case_logic handles general Exception correctly."""
    # Setup mocks
    mock_support_client.resolve_case = AsyncMock(side_effect=Exception('Unexpected error'))

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={'status': 'error', 'message': 'General error'})

    result = await _resolve_support_case_logic(context, case_id='test-case-id')

    assert result['status'] == 'error'


# --- Tests for new tools ---


# describe_communications tests


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_communications(mock_support_client):
    """Test describe_communications calls the API correctly."""
    mock_support_client.describe_communications = AsyncMock(
        return_value={
            'communications': [
                {
                    'caseId': 'test-case-id',
                    'body': 'Test body',
                    'submittedBy': 'user@example.com',
                    'timeCreated': '2023-01-01T00:00:00Z',
                }
            ],
            'nextToken': 'token123',
        }
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_communications_logic(
        context,
        case_id='test-case-id',
        after_time='2023-01-01T00:00:00Z',
        before_time='2023-01-31T00:00:00Z',
        max_results=10,
        next_token=None,
    )

    mock_support_client.describe_communications.assert_called_once()
    assert 'communications' in result
    assert len(result['communications']) == 1
    assert result['communications'][0]['body'] == 'Test body'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_communications_client_error(mock_support_client):
    """Test describe_communications handles ClientError."""
    error_response = {'Error': {'Code': 'CaseIdNotFound', 'Message': 'Case not found'}}
    mock_support_client.describe_communications = AsyncMock(
        side_effect=ClientError(error_response, 'describe_communications')
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_communications_logic(context, case_id='bad-id')
    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_communications_general_error(mock_support_client):
    """Test describe_communications handles general Exception."""
    mock_support_client.describe_communications = AsyncMock(side_effect=Exception('Unexpected'))
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_communications_logic(context, case_id='test-case-id')
    assert result['status'] == 'error'


# describe_supported_languages tests


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_supported_languages(mock_support_client):
    """Test describe_supported_languages calls the API correctly."""
    mock_support_client.describe_supported_languages = AsyncMock(
        return_value={
            'supportedLanguages': [
                {'code': 'en', 'language': 'English', 'display': 'English'},
            ]
        }
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_supported_languages_logic(
        context,
        service_code='amazon-elastic-compute-cloud-linux',
        category_code='general-guidance',
        issue_type='technical',
    )

    mock_support_client.describe_supported_languages.assert_called_once()
    assert 'supportedLanguages' in result
    assert len(result['supportedLanguages']) == 1
    assert result['supportedLanguages'][0]['code'] == 'en'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_supported_languages_client_error(mock_support_client):
    """Test describe_supported_languages handles ClientError."""
    error_response = {
        'Error': {'Code': 'SubscriptionRequiredException', 'Message': 'Sub required'}
    }
    mock_support_client.describe_supported_languages = AsyncMock(
        side_effect=ClientError(error_response, 'describe_supported_languages')
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_supported_languages_logic(
        context,
        service_code='test',
        category_code='test',
    )
    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_supported_languages_general_error(mock_support_client):
    """Test describe_supported_languages handles general Exception."""
    mock_support_client.describe_supported_languages = AsyncMock(
        side_effect=Exception('Unexpected')
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_supported_languages_logic(
        context,
        service_code='test',
        category_code='test',
    )
    assert result['status'] == 'error'


# describe_create_case_options tests


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_create_case_options(mock_support_client):
    """Test describe_create_case_options calls the API correctly."""
    mock_support_client.describe_create_case_options = AsyncMock(
        return_value={
            'communicationTypes': [
                {
                    'type': 'chat',
                    'supportedHours': [{'startTime': '06:00', 'endTime': '22:00'}],
                    'datesWithoutSupport': [],
                }
            ],
            'languageAvailability': 'available',
        }
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_create_case_options_logic(
        context, service_code='amazon-ec2', language='en'
    )

    mock_support_client.describe_create_case_options.assert_called_once()
    assert 'communicationTypes' in result
    assert 'languageAvailability' in result
    assert len(result['communicationTypes']) == 1


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_create_case_options_client_error(mock_support_client):
    """Test describe_create_case_options handles ClientError."""
    error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Denied'}}
    mock_support_client.describe_create_case_options = AsyncMock(
        side_effect=ClientError(error_response, 'describe_create_case_options')
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_create_case_options_logic(context, service_code='bad-service')
    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_create_case_options_general_error(mock_support_client):
    """Test describe_create_case_options handles general Exception."""
    mock_support_client.describe_create_case_options = AsyncMock(
        side_effect=Exception('Unexpected')
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_create_case_options_logic(context, service_code='test')
    assert result['status'] == 'error'


# add_attachments_to_set tests


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_add_attachments_to_set_tool(mock_support_client):
    """Test add_attachments_to_set tool calls the API correctly."""
    mock_support_client.add_attachments_to_set = AsyncMock(
        return_value={
            'attachmentSetId': 'set-123',
            'expiryTime': '2023-01-01T13:00:00Z',
        }
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _add_attachments_to_set_logic(
        context,
        attachments=[{'fileName': 'test.txt', 'data': 'dGVzdA=='}],
        attachment_set_id=None,
    )

    mock_support_client.add_attachments_to_set.assert_called_once()
    assert result['attachmentSetId'] == 'set-123'
    assert result['status'] == 'success'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_add_attachments_to_set_tool_double_encoded(mock_support_client):
    """Test add_attachments_to_set rejects double-encoded data."""
    import base64

    # Simulate double-encoding: encode "hello world" to base64, then encode THAT to base64
    raw = b'hello world test data that is long enough'
    single_encoded = base64.b64encode(raw).decode('utf-8')
    double_encoded = base64.b64encode(single_encoded.encode('ascii')).decode('utf-8')

    # The client should raise ValueError for double-encoded data
    mock_support_client.add_attachments_to_set = AsyncMock(
        side_effect=ValueError('Attachment "test.txt": data appears to be double-base64-encoded.')
    )

    context = MagicMock()
    context.error = AsyncMock()

    result = await _add_attachments_to_set_logic(
        context,
        attachments=[{'fileName': 'test.txt', 'data': double_encoded}],
    )

    assert result['status'] == 'error'
    assert result['status_code'] == 400


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_add_attachments_to_set_tool_client_error(mock_support_client):
    """Test add_attachments_to_set tool handles ClientError."""
    error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Denied'}}
    mock_support_client.add_attachments_to_set = AsyncMock(
        side_effect=ClientError(error_response, 'add_attachments_to_set')
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _add_attachments_to_set_logic(
        context, attachments=[{'fileName': 'f.txt', 'data': 'x'}]
    )
    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_add_attachments_to_set_tool_general_error(mock_support_client):
    """Test add_attachments_to_set tool handles general Exception."""
    mock_support_client.add_attachments_to_set = AsyncMock(side_effect=Exception('Unexpected'))
    context = MagicMock()
    context.error = AsyncMock()

    result = await _add_attachments_to_set_logic(
        context, attachments=[{'fileName': 'f.txt', 'data': 'x'}]
    )
    assert result['status'] == 'error'


# describe_attachment tests


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_attachment(mock_support_client):
    """Test describe_attachment calls the API correctly."""
    mock_support_client.describe_attachment = AsyncMock(
        return_value={
            'attachment': {'fileName': 'error.log', 'data': 'dGVzdCBkYXRh'},
        }
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_attachment_logic(context, attachment_id='att-123')

    mock_support_client.describe_attachment.assert_called_once()
    assert 'attachment' in result
    assert result['attachment']['fileName'] == 'error.log'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_attachment_not_found(mock_support_client):
    """Test describe_attachment handles AttachmentIdNotFound."""
    error_response = {'Error': {'Code': 'AttachmentIdNotFound', 'Message': 'Not found'}}
    mock_support_client.describe_attachment = AsyncMock(
        side_effect=ClientError(error_response, 'describe_attachment')
    )
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_attachment_logic(context, attachment_id='bad-id')
    assert result['status'] == 'error'


@patch('awslabs.aws_support_mcp_server.server.support_client')
async def test_describe_attachment_general_error(mock_support_client):
    """Test describe_attachment handles general Exception."""
    mock_support_client.describe_attachment = AsyncMock(side_effect=Exception('Unexpected'))
    context = MagicMock()
    context.error = AsyncMock()

    result = await _describe_attachment_logic(context, attachment_id='att-123')
    assert result['status'] == 'error'


# Client tests for describe_attachment


class TestSupportClientDescribeAttachment:
    """Tests for the SupportClient.describe_attachment method."""

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_attachment(self, mock_run_in_executor, mock_session):
        """Test describe_attachment calls the API correctly."""
        mock_client = AsyncMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            'attachment': {'fileName': 'test.log', 'data': 'dGVzdA=='}
        }

        client = SupportClient()
        result = await client.describe_attachment(attachment_id='att-123')

        mock_run_in_executor.assert_called_once()
        assert result['attachment']['fileName'] == 'test.log'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_attachment_not_found(self, mock_run_in_executor, mock_session):
        """Test describe_attachment handles AttachmentIdNotFound."""
        mock_client = AsyncMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {'Error': {'Code': 'AttachmentIdNotFound', 'Message': 'Not found'}}
        mock_run_in_executor.side_effect = ClientError(error_response, 'describe_attachment')

        client = SupportClient()
        with pytest.raises(ClientError) as excinfo:
            await client.describe_attachment(attachment_id='bad-id')
        assert excinfo.value.response['Error']['Code'] == 'AttachmentIdNotFound'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_attachment_unexpected_error(self, mock_run_in_executor, mock_session):
        """Test describe_attachment handles unexpected errors."""
        mock_client = AsyncMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.side_effect = Exception('Unexpected')

        client = SupportClient()
        with pytest.raises(Exception, match='Unexpected'):
            await client.describe_attachment(attachment_id='att-123')


class TestSupportClientExceptionBranches:
    """Tests for uncovered exception branches in SupportClient methods."""

    def test_resolve_service_code_alias(self):
        """Test that common aliases are resolved to correct service codes."""
        assert SupportClient.resolve_service_code('ecs') == 'ec2-container-service'
        assert (
            SupportClient.resolve_service_code('amazon-elastic-container-service')
            == 'ec2-container-service'
        )
        assert SupportClient.resolve_service_code('s3') == 'amazon-simple-storage-service'
        assert SupportClient.resolve_service_code('amazon-s3') == 'amazon-simple-storage-service'
        assert SupportClient.resolve_service_code('lambda') == 'aws-lambda'
        assert SupportClient.resolve_service_code('iam') == 'aws-identity-and-access-management'
        assert SupportClient.resolve_service_code('fargate') == 'ec2-container-service'
        assert SupportClient.resolve_service_code('ec2') == 'amazon-elastic-compute-cloud-linux'

    def test_resolve_service_code_passthrough(self):
        """Test that already-correct codes pass through unchanged."""
        assert (
            SupportClient.resolve_service_code('ec2-container-service') == 'ec2-container-service'
        )
        assert (
            SupportClient.resolve_service_code('amazon-simple-storage-service')
            == 'amazon-simple-storage-service'
        )
        assert SupportClient.resolve_service_code('unknown-service') == 'unknown-service'

    def test_resolve_service_code_case_insensitive(self):
        """Test that resolution is case-insensitive."""
        assert SupportClient.resolve_service_code('ECS') == 'ec2-container-service'
        assert SupportClient.resolve_service_code('S3') == 'amazon-simple-storage-service'
        assert SupportClient.resolve_service_code('Lambda') == 'aws-lambda'

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_create_case_resolves_alias(self, mock_run_in_executor, mock_session):
        """Test that create_case resolves service code aliases."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.return_value = {'caseId': 'test-id'}

        client = SupportClient()
        await client.create_case(
            subject='test',
            service_code='ecs',
            category_code='other',
            severity_code='low',
            communication_body='test',
        )

        call_kwargs = mock_run_in_executor.call_args
        assert (
            call_kwargs.kwargs.get('serviceCode', call_kwargs[1].get('serviceCode'))
            == 'ec2-container-service'
        )

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_services_resolves_aliases(self, mock_run_in_executor, mock_session):
        """Test that describe_services resolves service code aliases in the list."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.return_value = {'services': []}

        client = SupportClient()
        await client.describe_services(service_code_list=['ecs', 's3'])

        call_kwargs = mock_run_in_executor.call_args
        code_list = call_kwargs.kwargs.get(
            'serviceCodeList', call_kwargs[1].get('serviceCodeList')
        )
        assert code_list == ['ec2-container-service', 'amazon-simple-storage-service']

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_create_case_unexpected_error(self, mock_run_in_executor, mock_session):
        """Test create_case propagates unexpected exceptions."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.side_effect = Exception('Unexpected')
        client = SupportClient()
        with pytest.raises(Exception, match='Unexpected'):
            await client.create_case(
                subject='t',
                service_code='s',
                category_code='c',
                severity_code='low',
                communication_body='b',
            )

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_cases_unexpected_error(self, mock_run_in_executor, mock_session):
        """Test describe_cases propagates unexpected exceptions."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.side_effect = Exception('Unexpected')
        client = SupportClient()
        with pytest.raises(Exception, match='Unexpected'):
            await client.describe_cases()

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_resolve_case_unexpected_error(self, mock_run_in_executor, mock_session):
        """Test resolve_case propagates unexpected exceptions."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.side_effect = Exception('Unexpected')
        client = SupportClient()
        with pytest.raises(Exception, match='Unexpected'):
            await client.resolve_case(case_id='test')

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_resolve_case_other_client_error(self, mock_run_in_executor, mock_session):
        """Test resolve_case re-raises unexpected AWS client errors."""
        mock_session.return_value.client.return_value = MagicMock()
        error_response = {'Error': {'Code': 'InternalServerError', 'Message': 'ISE'}}
        mock_run_in_executor.side_effect = ClientError(error_response, 'resolve_case')
        client = SupportClient()
        with pytest.raises(ClientError):
            await client.resolve_case(case_id='test')

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_add_communication_unexpected_error(self, mock_run_in_executor, mock_session):
        """Test add_communication_to_case propagates unexpected exceptions."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.side_effect = Exception('Unexpected')
        client = SupportClient()
        with pytest.raises(Exception, match='Unexpected'):
            await client.add_communication_to_case(case_id='t', communication_body='b')

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_add_communication_other_client_error(self, mock_run_in_executor, mock_session):
        """Test add_communication_to_case re-raises unexpected AWS client errors."""
        mock_session.return_value.client.return_value = MagicMock()
        error_response = {'Error': {'Code': 'InternalServerError', 'Message': 'ISE'}}
        mock_run_in_executor.side_effect = ClientError(error_response, 'add_communication')
        client = SupportClient()
        with pytest.raises(ClientError):
            await client.add_communication_to_case(case_id='t', communication_body='b')

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_services_unexpected_error(self, mock_run_in_executor, mock_session):
        """Test describe_services propagates unexpected exceptions."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.side_effect = Exception('Unexpected')
        client = SupportClient()
        with pytest.raises(Exception, match='Unexpected'):
            await client.describe_services()

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_severity_levels_unexpected_error(
        self, mock_run_in_executor, mock_session
    ):
        """Test describe_severity_levels propagates unexpected exceptions."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.side_effect = Exception('Unexpected')
        client = SupportClient()
        with pytest.raises(Exception, match='Unexpected'):
            await client.describe_severity_levels()

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_supported_languages_unexpected_error(
        self, mock_run_in_executor, mock_session
    ):
        """Test describe_supported_languages propagates unexpected exceptions."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.side_effect = Exception('Unexpected')
        client = SupportClient()
        with pytest.raises(Exception, match='Unexpected'):
            await client.describe_supported_languages(
                service_code='s',
                category_code='c',
            )

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_describe_create_case_options_unexpected_error(
        self, mock_run_in_executor, mock_session
    ):
        """Test describe_create_case_options propagates unexpected exceptions."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.side_effect = Exception('Unexpected')
        client = SupportClient()
        with pytest.raises(Exception, match='Unexpected'):
            await client.describe_create_case_options(service_code='s')

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_add_attachments_unexpected_error(self, mock_run_in_executor, mock_session):
        """Test unexpected error after base64 decode succeeds."""
        mock_session.return_value.client.return_value = MagicMock()
        mock_run_in_executor.side_effect = Exception('Unexpected')
        client = SupportClient()
        with pytest.raises(Exception, match='Unexpected'):
            await client.add_attachments_to_set(
                attachments=[{'fileName': 'f.txt', 'data': 'dGVzdA=='}]
            )


# Server inline tool tests — skipped because @mcp.tool wraps into FunctionTool objects.
# The client exception branches below cover the same code paths.


class TestSupportClientAttachmentEncoding:
    """Tests for attachment base64 decoding and double-encoding detection."""

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_decodes_base64_to_bytes(self, mock_run_in_executor, mock_session):
        """Test that base64 data is decoded to raw bytes before passing to boto3."""
        import base64

        mock_client = AsyncMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            'attachmentSetId': 'set-1',
            'expiryTime': '2023-01-01T13:00:00Z',
        }

        client = SupportClient()
        raw_content = b'hello world'
        encoded = base64.b64encode(raw_content).decode('utf-8')

        await client.add_attachments_to_set(
            attachments=[{'fileName': 'test.txt', 'data': encoded}]
        )

        # Verify the data passed to boto3 is raw bytes, not the base64 string
        call_kwargs = mock_run_in_executor.call_args
        attachment_data = call_kwargs.kwargs.get(
            'attachments', call_kwargs[1].get('attachments', [])
        )[0]['data']
        assert isinstance(attachment_data, bytes)
        assert attachment_data == raw_content

    @patch('boto3.Session')
    async def test_rejects_double_encoded_data(self, mock_session):
        """Test that double-base64-encoded data is rejected."""
        import base64

        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        client = SupportClient()

        # Double-encode: raw → base64 → base64
        raw = b'this is a test file with enough content to detect'
        single = base64.b64encode(raw).decode('utf-8')
        double = base64.b64encode(single.encode('ascii')).decode('utf-8')

        with pytest.raises(ValueError, match='double-base64-encoded'):
            await client.add_attachments_to_set(
                attachments=[{'fileName': 'test.txt', 'data': double}]
            )

    @patch('boto3.Session')
    async def test_rejects_invalid_base64(self, mock_session):
        """Test that non-base64 data is rejected."""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        client = SupportClient()

        with pytest.raises(ValueError, match='not valid base64'):
            await client.add_attachments_to_set(
                attachments=[{'fileName': 'test.txt', 'data': '!!!not-base64!!!'}]
            )

    @patch('boto3.Session')
    @patch('awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor')
    async def test_accepts_binary_content_as_base64(self, mock_run_in_executor, mock_session):
        """Test that genuine binary content (e.g., PNG header) passes validation."""
        import base64

        mock_client = AsyncMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            'attachmentSetId': 'set-1',
            'expiryTime': '2023-01-01T13:00:00Z',
        }

        client = SupportClient()
        # PNG file header bytes — definitely not base64 text when decoded
        binary_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + b'\x00' * 20
        encoded = base64.b64encode(binary_content).decode('utf-8')

        result = await client.add_attachments_to_set(
            attachments=[{'fileName': 'screenshot.png', 'data': encoded}]
        )

        assert result['attachmentSetId'] == 'set-1'


# Error handling tests for new error codes


class TestNewErrorCodes:
    """Tests for new error codes in error handling."""

    @pytest.fixture
    def mock_context(self):
        """Return a mock MCP context with async error logger."""
        ctx = MagicMock()
        ctx.error = AsyncMock()
        return ctx

    async def test_handle_client_error_attachment_not_found(self, mock_context):
        """Test AttachmentIdNotFound maps to a 404 error response."""
        error_response = {'Error': {'Code': 'AttachmentIdNotFound', 'Message': 'Not found'}}
        error = ClientError(error_response, 'describe_attachment')
        result = await handle_client_error(mock_context, error, 'describe_attachment')
        assert result['status'] == 'error'
        assert result['status_code'] == 404
        mock_context.error.assert_called_once()

    async def test_handle_client_error_describe_attachment_limit(self, mock_context):
        """Test DescribeAttachmentLimitExceeded maps to a 429 error response."""
        error_response = {
            'Error': {'Code': 'DescribeAttachmentLimitExceeded', 'Message': 'Limit exceeded'}
        }
        error = ClientError(error_response, 'describe_attachment')
        result = await handle_client_error(mock_context, error, 'describe_attachment')
        assert result['status'] == 'error'
        assert result['status_code'] == 429
        mock_context.error.assert_called_once()


# Model tests for DescribeAttachmentResponse


class TestDescribeAttachmentModel:
    """Tests for the DescribeAttachmentResponse model."""

    def test_describe_attachment_response(self):
        """Test DescribeAttachmentResponse accepts expected attachment payload."""
        from awslabs.aws_support_mcp_server.models import DescribeAttachmentResponse

        response = DescribeAttachmentResponse(
            attachment={'fileName': 'test.log', 'data': 'dGVzdA=='},
            status='success',
            message='Retrieved attachment',
        )
        assert response.attachment['fileName'] == 'test.log'
        assert response.status == 'success'


# Debug Helper Tests
class TestDiagnosticsTracker:
    """Tests for the DiagnosticsTracker class."""

    def setup_method(self):
        """Set up test fixtures."""
        from awslabs.aws_support_mcp_server.debug_helper import DiagnosticsTracker

        self.tracker = DiagnosticsTracker()

    def test_initial_state(self):
        """Test initial state of DiagnosticsTracker."""
        assert not self.tracker.enabled
        assert isinstance(self.tracker.uptime, float)
        report = self.tracker.get_diagnostics_report()
        assert report == {'diagnostics_enabled': False}

    def test_enable_disable(self):
        """Test enabling and disabling diagnostics."""
        self.tracker.enable()
        assert self.tracker.enabled
        report = self.tracker.get_diagnostics_report()
        assert report['diagnostics_enabled'] is True

        self.tracker.disable()
        assert not self.tracker.enabled
        report = self.tracker.get_diagnostics_report()
        assert report == {'diagnostics_enabled': False}

    def test_reset(self):
        """Test resetting diagnostics data."""
        self.tracker.enable()
        self.tracker.track_performance('test_func', 1.0)
        self.tracker.track_error('TestError')
        self.tracker.track_request('test_request')

        self.tracker.reset()
        report = self.tracker.get_diagnostics_report()
        assert report['performance'] == {}
        assert report['errors'] == {}
        assert report['requests'] == {}

    def test_track_performance(self):
        """Test performance tracking."""
        self.tracker.enable()
        self.tracker.track_performance('test_func', 1.0)
        self.tracker.track_performance('test_func', 2.0)

        report = self.tracker.get_diagnostics_report()
        perf_data = report['performance']['test_func']
        assert perf_data['count'] == 2
        assert perf_data['total_time'] == 3.0
        assert perf_data['min_time'] == 1.0
        assert perf_data['max_time'] == 2.0
        assert isinstance(perf_data['last_call'], float)

    def test_track_performance_disabled(self):
        """Test performance tracking when disabled."""
        self.tracker.track_performance('test_func', 1.0)
        report = self.tracker.get_diagnostics_report()
        assert report == {'diagnostics_enabled': False}

    def test_track_error(self):
        """Test error tracking."""
        self.tracker.enable()
        self.tracker.track_error('TestError')
        self.tracker.track_error('TestError')
        self.tracker.track_error('OtherError')

        report = self.tracker.get_diagnostics_report()
        assert report['errors']['TestError'] == 2
        assert report['errors']['OtherError'] == 1

    def test_track_error_disabled(self):
        """Test error tracking when disabled."""
        self.tracker.track_error('TestError')
        report = self.tracker.get_diagnostics_report()
        assert report == {'diagnostics_enabled': False}

    def test_track_request(self):
        """Test request tracking."""
        self.tracker.enable()
        self.tracker.track_request('GET')
        self.tracker.track_request('GET')
        self.tracker.track_request('POST')

        report = self.tracker.get_diagnostics_report()
        assert report['requests']['GET'] == 2
        assert report['requests']['POST'] == 1

    def test_track_request_disabled(self):
        """Test request tracking when disabled."""
        self.tracker.track_request('GET')
        report = self.tracker.get_diagnostics_report()
        assert report == {'diagnostics_enabled': False}

    def test_uptime(self):
        """Test uptime calculation."""
        self.tracker.enable()
        time.sleep(0.1)  # Small delay to ensure uptime > 0
        assert self.tracker.uptime > 0

    @patch('time.time')
    def test_performance_tracking_edge_cases(self, mock_time):
        """Test performance tracking edge cases."""
        self.tracker.enable()

        # Test with very small duration
        mock_time.return_value = 1000.0
        self.tracker.track_performance('test_func', 0.000001)

        # Test with very large duration
        self.tracker.track_performance('test_func', 999999.999)

        report = self.tracker.get_diagnostics_report()
        perf_data = report['performance']['test_func']
        assert perf_data['min_time'] == 0.000001
        assert perf_data['max_time'] == 999999.999


# Server Tests
class TestServer:
    """Tests for the MCP server implementation."""

    @patch('awslabs.aws_support_mcp_server.server.logger')
    def test_logging_configuration(self, mock_logger):
        """Test logging configuration."""
        import sys
        from awslabs.aws_support_mcp_server.server import main

        # Create mock arguments
        sys.argv = ['server.py', '--debug']

        # Call main (but mock the actual server run)
        with patch('awslabs.aws_support_mcp_server.server.mcp.run'):
            main()

        # Verify logging configuration
        mock_logger.remove.assert_called()
        mock_logger.add.assert_called()
        # Verify debug level was set
        assert any('DEBUG' in str(call) for call in mock_logger.add.call_args_list)

    @patch('awslabs.aws_support_mcp_server.server.logger')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_main_with_log_file_and_directory_creation(
        self, mock_makedirs, mock_exists, mock_logger
    ):
        """Test main function with log file argument and directory creation."""
        import sys
        from awslabs.aws_support_mcp_server.server import main

        # Setup
        tmpdir = tempfile.mkdtemp()
        sys.argv = ['server.py', '--debug', '--log-file', f'{tmpdir}/test/server.log']
        mock_exists.return_value = False  # Directory doesn't exist

        # Call main (but mock the actual server run)
        with patch('awslabs.aws_support_mcp_server.server.mcp.run'):
            main()

        # Verify directory was created (OS-native path separators)
        mock_makedirs.assert_called_once_with(os.path.join(tmpdir, 'test'))
        # Verify logging was configured
        assert mock_logger.add.call_count >= 2  # Console and file logging

    @patch('awslabs.aws_support_mcp_server.server.logger')
    def test_main_without_debug_flag(self, mock_logger):
        """Test main function without debug flag."""
        import sys
        from awslabs.aws_support_mcp_server.server import main

        # Setup
        sys.argv = ['server.py']

        # Call main (but mock the actual server run)
        with patch('awslabs.aws_support_mcp_server.server.mcp.run'):
            main()

        # Verify INFO level logging was set (not DEBUG)
        assert any('INFO' in str(call) for call in mock_logger.add.call_args_list)

    @patch('awslabs.aws_support_mcp_server.server.logger')
    @patch('awslabs.aws_support_mcp_server.server.diagnostics')
    def test_main_debug_enables_diagnostics(self, mock_diagnostics, mock_logger):
        """Test main function with debug flag enables diagnostics."""
        import sys
        from awslabs.aws_support_mcp_server.server import main

        # Setup
        sys.argv = ['server.py', '--debug']

        # Call main (but mock the actual server run)
        with patch('awslabs.aws_support_mcp_server.server.mcp.run'):
            main()

        # Verify diagnostics were enabled
        mock_diagnostics.enable.assert_called_once()


class TestServerBranchCoverage:
    """Targeted tests for uncovered server branches."""

    async def test_diagnostics_resource_when_disabled(self):
        """Test diagnostics resource returns disabled message when diagnostics are off."""
        from awslabs.aws_support_mcp_server.server import diagnostics_resource

        with patch(
            'awslabs.aws_support_mcp_server.server.get_diagnostics_report',
            return_value={'diagnostics_enabled': False},
        ):
            result = await diagnostics_resource()
        assert 'Diagnostics not enabled' in result

    async def test_diagnostics_resource_when_enabled(self):
        """Test diagnostics resource returns report JSON when diagnostics are enabled."""
        from awslabs.aws_support_mcp_server.server import diagnostics_resource

        with patch(
            'awslabs.aws_support_mcp_server.server.get_diagnostics_report',
            return_value={'diagnostics_enabled': True, 'ok': 1},
        ):
            result = await diagnostics_resource()
        assert '"ok": 1' in result

    async def test_create_support_case_wrapper_calls_logic(self):
        """Test create_support_case wrapper forwards args to logic function."""
        from awslabs.aws_support_mcp_server.server import create_support_case

        with patch(
            'awslabs.aws_support_mcp_server.server._create_support_case_logic',
            new=AsyncMock(return_value={'status': 'success'}),
        ) as mock_logic:
            ctx = MagicMock()
            result = await create_support_case(
                ctx=ctx,
                subject='s',
                service_code='svc',
                category_code='cat',
                severity_code='low',
                communication_body='body',
            )
        assert result['status'] == 'success'
        mock_logic.assert_awaited_once()

    async def test_describe_support_cases_wrapper_calls_logic(self):
        """Test describe_support_cases wrapper forwards args to logic function."""
        from awslabs.aws_support_mcp_server.server import describe_support_cases

        with patch(
            'awslabs.aws_support_mcp_server.server._describe_support_cases_logic',
            new=AsyncMock(return_value={'cases': []}),
        ) as mock_logic:
            result = await describe_support_cases(ctx=MagicMock())
        assert result == {'cases': []}
        mock_logic.assert_awaited_once()

    async def test_add_communication_wrapper_calls_logic(self):
        """Test add_communication_to_case wrapper forwards args to logic function."""
        from awslabs.aws_support_mcp_server.server import add_communication_to_case

        with patch(
            'awslabs.aws_support_mcp_server.server._add_communication_to_case_logic',
            new=AsyncMock(return_value={'status': 'success'}),
        ) as mock_logic:
            result = await add_communication_to_case(
                ctx=MagicMock(),
                case_id='case-1',
                communication_body='hello',
            )
        assert result['status'] == 'success'
        mock_logic.assert_awaited_once()

    async def test_resolve_support_case_wrapper_calls_logic(self):
        """Test resolve_support_case wrapper forwards args to logic function."""
        from awslabs.aws_support_mcp_server.server import resolve_support_case

        with patch(
            'awslabs.aws_support_mcp_server.server._resolve_support_case_logic',
            new=AsyncMock(return_value={'status': 'success'}),
        ) as mock_logic:
            result = await resolve_support_case(ctx=MagicMock(), case_id='case-1')
        assert result['status'] == 'success'
        mock_logic.assert_awaited_once()

    async def test_describe_services_markdown_branch(self):
        """Test describe_services returns markdown when requested."""
        from awslabs.aws_support_mcp_server.server import describe_services

        with patch(
            'awslabs.aws_support_mcp_server.server.support_client.describe_services',
            new=AsyncMock(return_value={'services': []}),
        ):
            result = await describe_services(ctx=MagicMock(), format='markdown')
        assert 'markdown' in result

    async def test_describe_services_general_error_branch(self):
        """Test describe_services general exception branch."""
        from awslabs.aws_support_mcp_server.server import describe_services

        ctx = MagicMock()
        ctx.error = AsyncMock()
        with patch(
            'awslabs.aws_support_mcp_server.server.support_client.describe_services',
            new=AsyncMock(side_effect=Exception('boom')),
        ):
            result = await describe_services(ctx=ctx, format='json')
        assert result.get('status') == 'error'

    async def test_describe_severity_levels_markdown_branch(self):
        """Test describe_severity_levels returns markdown when requested."""
        from awslabs.aws_support_mcp_server.server import describe_severity_levels

        with patch(
            'awslabs.aws_support_mcp_server.server.support_client.describe_severity_levels',
            new=AsyncMock(return_value={'severityLevels': []}),
        ):
            result = await describe_severity_levels(ctx=MagicMock(), format='markdown')
        assert 'markdown' in result

    async def test_describe_severity_levels_general_error_branch(self):
        """Test describe_severity_levels general exception branch."""
        from awslabs.aws_support_mcp_server.server import describe_severity_levels

        ctx = MagicMock()
        ctx.error = AsyncMock()
        with patch(
            'awslabs.aws_support_mcp_server.server.support_client.describe_severity_levels',
            new=AsyncMock(side_effect=Exception('boom')),
        ):
            result = await describe_severity_levels(ctx=ctx, format='json')
        assert result.get('status') == 'error'

    async def test_describe_communications_wrapper_calls_logic(self):
        """Test describe_communications wrapper forwards args to logic function."""
        from awslabs.aws_support_mcp_server.server import describe_communications

        with patch(
            'awslabs.aws_support_mcp_server.server._describe_communications_logic',
            new=AsyncMock(return_value={'communications': []}),
        ) as mock_logic:
            result = await describe_communications(ctx=MagicMock(), case_id='case-1')
        assert result == {'communications': []}
        mock_logic.assert_awaited_once()

    async def test_describe_supported_languages_wrapper_calls_logic(self):
        """Test describe_supported_languages wrapper forwards args to logic function."""
        from awslabs.aws_support_mcp_server.server import describe_supported_languages

        with patch(
            'awslabs.aws_support_mcp_server.server._describe_supported_languages_logic',
            new=AsyncMock(return_value={'supportedLanguages': []}),
        ) as mock_logic:
            result = await describe_supported_languages(
                ctx=MagicMock(), service_code='svc', category_code='cat'
            )
        assert result == {'supportedLanguages': []}
        mock_logic.assert_awaited_once()

    async def test_describe_create_case_options_wrapper_calls_logic(self):
        """Test describe_create_case_options wrapper forwards args to logic function."""
        from awslabs.aws_support_mcp_server.server import describe_create_case_options

        with patch(
            'awslabs.aws_support_mcp_server.server._describe_create_case_options_logic',
            new=AsyncMock(
                return_value={'communicationTypes': [], 'languageAvailability': 'available'}
            ),
        ) as mock_logic:
            result = await describe_create_case_options(ctx=MagicMock(), service_code='svc')
        assert result['languageAvailability'] == 'available'
        mock_logic.assert_awaited_once()

    async def test_add_attachments_wrapper_calls_logic(self):
        """Test add_attachments_to_set wrapper forwards args to logic function."""
        from awslabs.aws_support_mcp_server.server import add_attachments_to_set

        with patch(
            'awslabs.aws_support_mcp_server.server._add_attachments_to_set_logic',
            new=AsyncMock(return_value={'status': 'success'}),
        ) as mock_logic:
            result = await add_attachments_to_set(
                ctx=MagicMock(),
                attachments=[{'fileName': 'a.txt', 'data': 'dGVzdA=='}],
            )
        assert result['status'] == 'success'
        mock_logic.assert_awaited_once()

    async def test_describe_attachment_wrapper_calls_logic(self):
        """Test describe_attachment wrapper forwards args to logic function."""
        from awslabs.aws_support_mcp_server.server import describe_attachment

        with patch(
            'awslabs.aws_support_mcp_server.server._describe_attachment_logic',
            new=AsyncMock(return_value={'attachment': {}}),
        ) as mock_logic:
            result = await describe_attachment(ctx=MagicMock(), attachment_id='att-1')
        assert result == {'attachment': {}}
        mock_logic.assert_awaited_once()

    @patch('awslabs.aws_support_mcp_server.server.logger')
    @patch('awslabs.aws_support_mcp_server.server.diagnostics')
    def test_main_debug_settings_path_with_settings_attr(self, mock_diagnostics, mock_logger):
        """Test main sets debug on mcp.settings when available."""
        import sys
        from awslabs.aws_support_mcp_server.server import main
        from types import SimpleNamespace

        sys.argv = ['server.py', '--debug']
        with patch('awslabs.aws_support_mcp_server.server.mcp') as mock_mcp:
            mock_mcp.settings = SimpleNamespace(debug=False)
            main()
            assert mock_mcp.settings.debug is True

    @patch('awslabs.aws_support_mcp_server.server.logger')
    @patch('awslabs.aws_support_mcp_server.server.diagnostics')
    def test_main_debug_settings_path_with_debug_attr(self, mock_diagnostics, mock_logger):
        """Test main sets debug directly on mcp when settings are unavailable."""
        import sys
        from awslabs.aws_support_mcp_server.server import main

        class DummyMCP:
            """Minimal MCP object with debug attribute and run method."""

            def __init__(self):
                self.debug = False

            def run(self, transport='stdio'):
                """Mock run method."""
                return transport

        sys.argv = ['server.py', '--debug']
        with patch('awslabs.aws_support_mcp_server.server.mcp', new=DummyMCP()) as dummy:
            main()
            assert dummy.debug is True
