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
import pytest
import time
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock, AsyncMock, ANY
from botocore.exceptions import ClientError
from pydantic import ValidationError

from awslabs.aws_support_mcp_server.client import SupportClient
from awslabs.aws_support_mcp_server.consts import (
    DEFAULT_REGION,
    ERROR_SUBSCRIPTION_REQUIRED,
    ERROR_CASE_NOT_FOUND,
    ERROR_RATE_LIMIT_EXCEEDED,
    MAX_RESULTS_PER_PAGE,
    ERROR_AUTHENTICATION_FAILED
)
from awslabs.aws_support_mcp_server.errors import (
    handle_client_error,
    handle_validation_error,
    handle_general_error,
    get_error_status_code,
    create_error_response
)
from awslabs.aws_support_mcp_server.formatters import (
    format_case,
    format_cases,
    format_communications,
    format_services,
    format_severity_levels,
    format_json_response,
    format_markdown_case_summary,
    format_markdown_services,
    format_markdown_severity_levels,
    format_markdown_supported_languages,
)


from awslabs.aws_support_mcp_server.server import (
    create_support_case,
    describe_support_cases,
    add_communication_to_case,
    resolve_support_case
)


# Fixtures

@pytest.fixture
def support_case_data() -> Dict[str, Any]:
    """Return a dictionary with sample support case data."""
    return {
        "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
        "displayId": "12345678910",
        "subject": "EC2 instance not starting",
        "status": "opened",
        "serviceCode": "amazon-elastic-compute-cloud-linux",
        "categoryCode": "using-aws",
        "severityCode": "urgent",
        "submittedBy": "user@example.com",
        "timeCreated": "2023-01-01T12:00:00Z",
        "recentCommunications": {
            "communications": [
                {
                    "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
                    "body": "My EC2 instance i-1234567890abcdef0 is not starting.",
                    "submittedBy": "user@example.com",
                    "timeCreated": "2023-01-01T12:00:00Z"
                }
            ],
            "nextToken": None
        },
        "ccEmailAddresses": ["team@example.com"],
        "language": "en",
        "nextToken": None
    }


@pytest.fixture
def minimal_support_case_data() -> Dict[str, Any]:
    """Return a dictionary with minimal support case data."""
    return {
        "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
        "subject": "EC2 instance not starting",
        "status": "opened",
        "serviceCode": "amazon-elastic-compute-cloud-linux",
        "categoryCode": "using-aws",
        "severityCode": "urgent",
        "submittedBy": "user@example.com",
        "timeCreated": "2023-01-01T12:00:00Z"
    }


@pytest.fixture
def edge_case_support_case_data() -> Dict[str, Any]:
    """Return a dictionary with edge case support case data."""
    return {
        "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
        "displayId": "12345678910",
        "subject": "EC2 instance not starting" * 50,  # Very long subject
        "status": "opened",
        "serviceCode": "amazon-elastic-compute-cloud-linux",
        "categoryCode": "using-aws",
        "severityCode": "urgent",
        "submittedBy": "user@example.com",
        "timeCreated": "2023-01-01T12:00:00Z",
        "recentCommunications": {
            "communications": [
                {
                    "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
                    "body": "My EC2 instance i-1234567890abcdef0 is not starting.",
                    "submittedBy": "user@example.com",
                    "timeCreated": "2023-01-01T12:00:00Z"
                }
            ],
            "nextToken": None
        },
        "ccEmailAddresses": ["team@example.com"],
        "language": "en",
        "nextToken": None
    }


@pytest.fixture
def multiple_support_cases_data() -> List[Dict[str, Any]]:
    """Return a list of dictionaries with sample support case data."""
    return [
        {
            "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
            "displayId": "12345678910",
            "subject": "EC2 instance not starting",
            "status": "opened",
            "serviceCode": "amazon-elastic-compute-cloud-linux",
            "categoryCode": "using-aws",
            "severityCode": "urgent",
            "submittedBy": "user@example.com",
            "timeCreated": "2023-01-01T12:00:00Z"
        },
        {
            "caseId": "case-98765432109-2013-a1b2c3d4e5f6",
            "displayId": "98765432109",
            "subject": "S3 bucket access issue",
            "status": "opened",
            "serviceCode": "amazon-s3",
            "categoryCode": "using-aws",
            "severityCode": "high",
            "submittedBy": "user@example.com",
            "timeCreated": "2023-01-02T12:00:00Z"
        }
    ]


@pytest.fixture
def communication_data() -> Dict[str, Any]:
    """Return a dictionary with sample communication data."""
    return {
        "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
        "body": "My EC2 instance i-1234567890abcdef0 is not starting.",
        "submittedBy": "user@example.com",
        "timeCreated": "2023-01-01T12:00:00Z",
        "attachmentSet": None
    }


@pytest.fixture
def minimal_communication_data() -> Dict[str, Any]:
    """Return a dictionary with minimal communication data."""
    return {
        "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
        "body": "My EC2 instance i-1234567890abcdef0 is not starting.",
        "submittedBy": "user@example.com",
        "timeCreated": "2023-01-01T12:00:00Z"
    }


@pytest.fixture
def communications_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample communications response data."""
    return {
        "communications": [
            {
                "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
                "body": "My EC2 instance i-1234567890abcdef0 is not starting.",
                "submittedBy": "user@example.com",
                "timeCreated": "2023-01-01T12:00:00Z"
            },
            {
                "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
                "body": "I've tried rebooting the instance but it's still not starting.",
                "submittedBy": "user@example.com",
                "timeCreated": "2023-01-01T12:30:00Z"
            }
        ],
        "nextToken": None
    }


@pytest.fixture
def empty_communications_response_data() -> Dict[str, Any]:
    """Return a dictionary with empty communications response data."""
    return {
        "communications": [],
        "nextToken": None
    }


@pytest.fixture
def service_data() -> Dict[str, Any]:
    """Return a dictionary with sample service data."""
    return {
        "code": "amazon-elastic-compute-cloud-linux",
        "name": "Amazon Elastic Compute Cloud (Linux)",
        "categories": [
            {
                "code": "using-aws",
                "name": "Using AWS"
            },
            {
                "code": "performance",
                "name": "Performance"
            }
        ]
    }


@pytest.fixture
def minimal_service_data() -> Dict[str, Any]:
    """Return a dictionary with minimal service data."""
    return {
        "code": "amazon-elastic-compute-cloud-linux",
        "name": "Amazon Elastic Compute Cloud (Linux)",
        "categories": []
    }


@pytest.fixture
def services_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample services response data."""
    return {
        "services": [
            {
                "code": "amazon-elastic-compute-cloud-linux",
                "name": "Amazon Elastic Compute Cloud (Linux)",
                "categories": [
                    {
                        "code": "using-aws",
                        "name": "Using AWS"
                    },
                    {
                        "code": "performance",
                        "name": "Performance"
                    }
                ]
            },
            {
                "code": "amazon-s3",
                "name": "Amazon Simple Storage Service",
                "categories": [
                    {
                        "code": "using-aws",
                        "name": "Using AWS"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def empty_services_response_data() -> Dict[str, Any]:
    """Return a dictionary with empty services response data."""
    return {
        "services": []
    }


@pytest.fixture
def category_data() -> Dict[str, Any]:
    """Return a dictionary with sample category data."""
    return {
        "code": "using-aws",
        "name": "Using AWS"
    }


@pytest.fixture
def severity_level_data() -> Dict[str, Any]:
    """Return a dictionary with sample severity level data."""
    return {
        "code": "urgent",
        "name": "Production system down"
    }


@pytest.fixture
def minimal_severity_level_data() -> Dict[str, Any]:
    """Return a dictionary with minimal severity level data."""
    return {
        "code": "urgent",
        "name": "Production system down"
    }


@pytest.fixture
def severity_levels_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample severity levels response data."""
    return {
        "severityLevels": [
            {
                "code": "low",
                "name": "General guidance"
            },
            {
                "code": "normal",
                "name": "System impaired"
            },
            {
                "code": "high",
                "name": "Production system impaired"
            },
            {
                "code": "urgent",
                "name": "Production system down"
            },
            {
                "code": "critical",
                "name": "Business-critical system down"
            }
        ]
    }


@pytest.fixture
def empty_severity_levels_response_data() -> Dict[str, Any]:
    """Return a dictionary with empty severity levels response data."""
    return {
        "severityLevels": []
    }

@pytest.fixture
def supported_languages_data() -> List[Dict[str, Any]]:
    """Return a list of supported languages."""
    return [
        {"code": "en", "name": "English", "nativeName": "English"},
        {"code": "ja", "name": "Japanese", "nativeName": "日本語"},
        {"code": "zh", "name": "Chinese", "nativeName": "中文"},
        {"code": "ko", "name": "Korean", "nativeName": "한국어"}
    ]


@pytest.fixture
def create_case_request_data() -> Dict[str, Any]:
    """Return a dictionary with sample create case request data."""
    return {
        "subject": "EC2 instance not starting",
        "service_code": "amazon-elastic-compute-cloud-linux",
        "category_code": "using-aws",
        "severity_code": "urgent",
        "communication_body": "My EC2 instance i-1234567890abcdef0 is not starting.",
        "cc_email_addresses": ["team@example.com"],
        "language": "en",
        "issue_type": "technical",
        "attachment_set_id": None
    }


@pytest.fixture
def minimal_create_case_request_data() -> Dict[str, Any]:
    """Return a dictionary with minimal create case request data."""
    return {
        "subject": "EC2 instance not starting",
        "service_code": "amazon-elastic-compute-cloud-linux",
        "category_code": "using-aws",
        "severity_code": "urgent",
        "communication_body": "My EC2 instance i-1234567890abcdef0 is not starting."
    }


@pytest.fixture
def create_case_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample create case response data."""
    return {
        "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
        "status": "success",
        "message": "Support case created successfully with ID: case-12345678910-2013-c4c1d2bf33c5cf47"
    }


@pytest.fixture
def describe_cases_request_data() -> Dict[str, Any]:
    """Return a dictionary with sample describe cases request data."""
    return {
        "case_id_list": ["case-12345678910-2013-c4c1d2bf33c5cf47"],
        "display_id": None,
        "after_time": "2023-01-01T00:00:00Z",
        "before_time": "2023-01-31T23:59:59Z",
        "include_resolved_cases": False,
        "include_communications": True,
        "language": "en",
        "max_results": 100,
        "next_token": None
    }


@pytest.fixture
def minimal_describe_cases_request_data() -> Dict[str, Any]:
    """Return a dictionary with minimal describe cases request data."""
    return {
        "include_resolved_cases": False,
        "include_communications": True
    }


@pytest.fixture
def describe_cases_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample describe cases response data."""
    return {
        "cases": [
            {
                "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
                "displayId": "12345678910",
                "subject": "EC2 instance not starting",
                "status": "opened",
                "serviceCode": "amazon-elastic-compute-cloud-linux",
                "categoryCode": "using-aws",
                "severityCode": "urgent",
                "submittedBy": "user@example.com",
                "timeCreated": "2023-01-01T12:00:00Z",
                "recentCommunications": {
                    "communications": [
                        {
                            "caseId": "case-12345678910-2013-c4c1d2bf33c5cf47",
                            "body": "My EC2 instance i-1234567890abcdef0 is not starting.",
                            "submittedBy": "user@example.com",
                            "timeCreated": "2023-01-01T12:00:00Z"
                        }
                    ],
                    "nextToken": None
                }
            }
        ],
        "nextToken": None
    }


@pytest.fixture
def empty_describe_cases_response_data() -> Dict[str, Any]:
    """Return a dictionary with empty describe cases response data."""
    return {
        "cases": [],
        "nextToken": None
    }


@pytest.fixture
def add_communication_request_data() -> Dict[str, Any]:
    """Return a dictionary with sample add communication request data."""
    return {
        "case_id": "case-12345678910-2013-c4c1d2bf33c5cf47",
        "communication_body": "I've tried rebooting the instance but it's still not starting.",
        "cc_email_addresses": ["team@example.com"],
        "attachment_set_id": None
    }


@pytest.fixture
def minimal_add_communication_request_data() -> Dict[str, Any]:
    """Return a dictionary with minimal add communication request data."""
    return {
        "case_id": "case-12345678910-2013-c4c1d2bf33c5cf47",
        "communication_body": "I've tried rebooting the instance but it's still not starting."
    }


@pytest.fixture
def add_communication_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample add communication response data."""
    return {
        "result": True,
        "status": "success",
        "message": "Communication added successfully to case: case-12345678910-2013-c4c1d2bf33c5cf47"
    }


@pytest.fixture
def resolve_case_request_data() -> Dict[str, Any]:
    """Return a dictionary with sample resolve case request data."""
    return {
        "case_id": "case-12345678910-2013-c4c1d2bf33c5cf47"
    }


@pytest.fixture
def resolve_case_response_data() -> Dict[str, Any]:
    """Return a dictionary with sample resolve case response data."""
    return {
        "initial_case_status": "opened",
        "final_case_status": "resolved",
        "status": "success",
        "message": "Support case resolved successfully: case-12345678910-2013-c4c1d2bf33c5cf47"
    }


# Client Tests

class TestSupportClient:
    """Tests for the SupportClient class."""

    @patch("boto3.Session")
    def test_initialization_default_parameters(self, mock_session):
        """Test that SupportClient initializes correctly with default parameters."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.return_value = MagicMock(access_key="TEST1234")

        # Create client
        client = SupportClient()

        # Verify
        mock_session.assert_called_once_with(**{"region_name": DEFAULT_REGION})
        mock_session.return_value.client.assert_called_once_with(
            "support",
            config=ANY  # Using ANY since we just want to verify the service name
        )
        assert client.region_name == DEFAULT_REGION

    @patch("boto3.Session")
    def test_initialization_custom_parameters(self, mock_session):
        """Test that SupportClient initializes correctly with custom parameters."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.return_value = MagicMock(access_key="TEST1234")

        # Test parameters
        custom_region = "us-west-2"
        custom_profile = "test-profile"

        # Create client
        client = SupportClient(region_name=custom_region, profile_name=custom_profile)

        # Verify
        mock_session.assert_called_once_with(
            **{
                "region_name": custom_region,
                "profile_name": custom_profile
            }
        )
        mock_session.return_value.client.assert_called_once_with(
            "support",
            config=ANY  # Using ANY since we just want to verify the service name
        )
        assert client.region_name == custom_region

    @patch("boto3.Session")
    def test_initialization_subscription_required_error(self, mock_session):
        """Test that a SupportClient raises an error when subscription is required."""
        # Setup mock
        error_response = {
            "Error": {
                "Code": "SubscriptionRequiredException",
                "Message": "Subscription required"
            }
        }
        mock_session.return_value.client.side_effect = ClientError(
            error_response, "create_case"
        )

        # Create client and verify error
        with pytest.raises(ClientError) as excinfo:
            SupportClient()

        # Verify error
        assert excinfo.value.response["Error"]["Code"] == "SubscriptionRequiredException"

    @patch("boto3.Session")
    def test_initialization_other_client_error(self, mock_session):
        """Test that a SupportClient raises an error when there's another client error."""
        # Setup mock
        error_response = {
            "Error": {
                "Code": "OtherError",
                "Message": "Some other error"
            }
        }
        mock_session.return_value.client.side_effect = ClientError(
            error_response, "create_case"
        )

        # Create client and verify error
        with pytest.raises(ClientError) as excinfo:
            SupportClient()

        # Verify error
        assert excinfo.value.response["Error"]["Code"] == "OtherError"

    @patch("boto3.Session")
    @patch("asyncio.get_event_loop")
    async def test_run_in_executor(self, mock_get_event_loop, mock_session):
        """Test that _run_in_executor runs a function in an executor."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_loop = MagicMock()
        mock_get_event_loop.return_value = mock_loop
        mock_loop.run_in_executor.return_value = asyncio.Future()
        mock_loop.run_in_executor.return_value.set_result("test-result")

        # Create client
        client = SupportClient()

        # Call _run_in_executor
        mock_func = MagicMock()
        result = await client._run_in_executor(mock_func, "arg1", arg2="arg2")

        # Verify
        mock_get_event_loop.assert_called_once()
        mock_loop.run_in_executor.assert_called_once()
        assert result == "test-result"

    @patch("boto3.Session")
    def test_initialization_with_no_credentials_warning(self, mock_session):
        """Test initialization when no credentials are found and warning is logged."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.return_value = None

        with patch("awslabs.aws_support_mcp_server.client.logger") as mock_logger:
            client = SupportClient()
            mock_logger.warning.assert_called_with("No AWS credentials found in session")

    @patch("boto3.Session")
    def test_initialization_with_credential_error_warning(self, mock_session):
        """Test initialization when credential check raises an error and warning is logged."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.side_effect = Exception("Credential error")

        with patch("awslabs.aws_support_mcp_server.client.logger") as mock_logger:
            client = SupportClient()
            mock_logger.warning.assert_called_with("Error checking credentials: Credential error")

    @patch("boto3.Session")
    def test_initialization_with_unexpected_error_logging(self, mock_session):
        """Test initialization when an unexpected error occurs and error is logged."""
        # Setup mock
        mock_session.side_effect = Exception("Unexpected initialization error")

        with patch("awslabs.aws_support_mcp_server.client.logger") as mock_logger:
            with pytest.raises(Exception) as exc_info:
                SupportClient()
            mock_logger.error.assert_called_with(
                "Unexpected error initializing AWS Support client: Unexpected initialization error",
                exc_info=True
            )


    @patch("boto3.Session")
    def test_initialization_business_subscription_required_error(self, mock_session):
        """Test initialization when AWS Business Support subscription is required."""
        # Setup mock
        mock_client = MagicMock()
        error_response = {
            "Error": {
                "Code": "SubscriptionRequiredException",
                "Message": "AWS Business Support or higher is required"
            }
        }
        mock_session.return_value.client.side_effect = ClientError(error_response, "support")

        # Verify subscription required error is raised
        with pytest.raises(ClientError) as exc_info:
            SupportClient()

        assert exc_info.value.response["Error"]["Code"] == "SubscriptionRequiredException"

    @patch("boto3.Session")
    def test_initialization_unexpected_error(self, mock_session):
        """Test initialization when unexpected error occurs."""
        # Setup mock
        mock_session.side_effect = Exception("Unexpected error")

        # Verify error is raised
        with pytest.raises(Exception) as exc_info:
            SupportClient()

        assert str(exc_info.value) == "Unexpected error"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_communications_case_not_found(self, mock_run_in_executor, mock_session):
        """Test describe_communications when case is not found."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {
            "Error": {
                "Code": "CaseIdNotFound",
                "Message": "Case not found"
            }
        }
        mock_run_in_executor.side_effect = ClientError(error_response, "describe_communications")

        # Create client
        client = SupportClient()

        # Verify error is raised
        with pytest.raises(ClientError) as exc_info:
            await client.describe_communications("non-existent-case")

        assert exc_info.value.response["Error"]["Code"] == "CaseIdNotFound"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_communications_unexpected_error(self, mock_run_in_executor, mock_session):
        """Test describe_communications when unexpected error occurs."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.side_effect = Exception("Unexpected error")

        # Create client
        client = SupportClient()

        # Verify error is raised
        with pytest.raises(Exception) as exc_info:
            await client.describe_communications("test-case")

        assert str(exc_info.value) == "Unexpected error"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_supported_languages_client_error(self, mock_run_in_executor, mock_session):
        """Test describe_supported_languages when client error occurs."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {
            "Error": {
                "Code": "SomeError",
                "Message": "Some error occurred"
            }
        }
        mock_run_in_executor.side_effect = ClientError(error_response, "describe_supported_languages")

        # Create client
        client = SupportClient()

        # Verify error is raised
        with pytest.raises(ClientError) as exc_info:
            await client.describe_supported_languages()

        assert exc_info.value.response["Error"]["Code"] == "SomeError"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_create_case_options_client_error(self, mock_run_in_executor, mock_session):
        """Test describe_create_case_options when client error occurs."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {
            "Error": {
                "Code": "SomeError",
                "Message": "Some error occurred"
            }
        }
        mock_run_in_executor.side_effect = ClientError(error_response, "describe_create_case_options")

        # Create client
        client = SupportClient()

        # Verify error is raised
        with pytest.raises(ClientError) as exc_info:
            await client.describe_create_case_options("test-service")

        assert exc_info.value.response["Error"]["Code"] == "SomeError"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_add_attachments_to_set_client_error(self, mock_run_in_executor, mock_session):
        """Test add_attachments_to_set when client error occurs."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {
            "Error": {
                "Code": "SomeError",
                "Message": "Some error occurred"
            }
        }
        mock_run_in_executor.side_effect = ClientError(error_response, "add_attachments_to_set")

        # Create client
        client = SupportClient()

        # Test data
        attachments = [
            {
                "fileName": "test.txt",
                "data": "base64_encoded_content"
            }
        ]

        # Verify error is raised
        with pytest.raises(ClientError) as exc_info:
            await client.add_attachments_to_set(attachments)

        assert exc_info.value.response["Error"]["Code"] == "SomeError"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_retry_with_backoff_max_retries_exceeded(self, mock_run_in_executor, mock_session):
        """Test _retry_with_backoff when max retries are exceeded."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Create mock function that always fails with throttling
        mock_func = AsyncMock()
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded"
            }
        }
        mock_func.side_effect = ClientError(error_response, "operation")

        # Verify error is raised after max retries
        with pytest.raises(ClientError) as exc_info:
            await client._retry_with_backoff(mock_func, max_retries=2)

        assert exc_info.value.response["Error"]["Code"] == "ThrottlingException"
        assert mock_func.call_count == 3  # Initial try + 2 retries

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_retry_with_backoff_non_retryable_error(self, mock_run_in_executor, mock_session):
        """Test _retry_with_backoff with non-retryable error."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Create mock function that fails with non-retryable error
        mock_func = AsyncMock()
        error_response = {
            "Error": {
                "Code": "ValidationError",
                "Message": "Invalid input"
            }
        }
        mock_func.side_effect = ClientError(error_response, "operation")

        # Verify error is raised immediately
        with pytest.raises(ClientError) as exc_info:
            await client._retry_with_backoff(mock_func)

        assert exc_info.value.response["Error"]["Code"] == "ValidationError"
        assert mock_func.call_count == 1  # Only tried once

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_retry_with_backoff_unexpected_error(self, mock_run_in_executor, mock_session):
        """Test _retry_with_backoff with unexpected error."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Create mock function that fails with unexpected error
        mock_func = AsyncMock()
        mock_func.side_effect = Exception("Unexpected error")

        # Verify error is raised immediately
        with pytest.raises(Exception) as exc_info:
            await client._retry_with_backoff(mock_func)

        assert str(exc_info.value) == "Unexpected error"
        assert mock_func.call_count == 1  # Only tried once

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
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
            "Error": {
                "Code": "TooManyRequestsException",
                "Message": "Too many requests"
            }
        }
        mock_func.side_effect = [
            ClientError(error_response, "operation"),
            {"success": True}
        ]

        # Call _retry_with_backoff
        result = await client._retry_with_backoff(mock_func)

        # Verify
        assert mock_func.call_count == 2
        assert result == {"success": True}

    @patch("boto3.Session")
    def test_initialization_credential_handling(self, mock_session):
        """Test that credential handling during initialization works correctly."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_credentials = MagicMock()
        mock_credentials.access_key = "TEST1234567890"
        mock_session.return_value.get_credentials.return_value = mock_credentials

        # Create client
        client = SupportClient()

        # Verify
        mock_session.return_value.get_credentials.assert_called_once()
        assert client.region_name == DEFAULT_REGION

    @patch("boto3.Session")
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

    @patch("boto3.Session")
    def test_initialization_credential_error(self, mock_session):
        """Test initialization when credential check raises an error."""
        # Setup mock
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.get_credentials.side_effect = Exception("Credential error")

        # Create client
        client = SupportClient()

        # Verify
        mock_session.return_value.get_credentials.assert_called_once()
        assert client.region_name == DEFAULT_REGION

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_communications(self, mock_run_in_executor, mock_session):
        """Test that describe_communications calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            "communications": [
                {
                    "caseId": "test-case-id",
                    "body": "Test communication",
                    "submittedBy": "test-user",
                    "timeCreated": "2023-01-01T00:00:00Z"
                }
            ],
            "nextToken": None
        }

        # Create client
        client = SupportClient()

        # Call describe_communications with all parameters
        result = await client.describe_communications(
            case_id="test-case-id",
            after_time="2023-01-01T00:00:00Z",
            before_time="2023-01-31T23:59:59Z",
            max_results=10,
            next_token="test-token"
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert "communications" in result
        assert len(result["communications"]) == 1
        assert result["communications"][0]["caseId"] == "test-case-id"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_supported_languages(self, mock_run_in_executor, mock_session):
        """Test that describe_supported_languages calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            "languages": [
                {
                    "code": "en",
                    "name": "English"
                }
            ]
        }

        # Create client
        client = SupportClient()

        # Call describe_supported_languages
        result = await client.describe_supported_languages()

        # Verify
        mock_run_in_executor.assert_called_once()
        assert "languages" in result
        assert len(result["languages"]) == 1
        assert result["languages"][0]["code"] == "en"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_create_case_options(self, mock_run_in_executor, mock_session):
        """Test that describe_create_case_options calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            "categoryList": [
                {
                    "code": "test-category",
                    "name": "Test Category"
                }
            ],
            "severityLevels": [
                {
                    "code": "low",
                    "name": "General guidance"
                }
            ]
        }

        # Create client
        client = SupportClient()

        # Call describe_create_case_options
        result = await client.describe_create_case_options(
            service_code="test-service",
            language="en"
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert "categoryList" in result
        assert "severityLevels" in result

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_retry_with_backoff_success(self, mock_run_in_executor, mock_session):
        """Test that _retry_with_backoff succeeds after retries."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Create mock function that fails twice then succeeds
        mock_func = AsyncMock()
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded"
            }
        }
        mock_func.side_effect = [
            ClientError(error_response, "operation"),  # First call fails
            ClientError(error_response, "operation"),  # Second call fails
            {"success": True}  # Third call succeeds
        ]

        # Call _retry_with_backoff
        result = await client._retry_with_backoff(mock_func)

        # Verify
        assert mock_func.call_count == 3
        assert result == {"success": True}

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_services(self, mock_run_in_executor, mock_session):
        """Test that describe_services calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            "services": [
                {
                    "code": "test-service",
                    "name": "Test Service",
                    "categories": [
                        {
                            "code": "test-category",
                            "name": "Test Category"
                        }
                    ]
                }
            ]
        }

        # Create client
        client = SupportClient()

        # Call describe_services
        result = await client.describe_services(
            service_code_list=["test-service"],
            language="en"
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert "services" in result
        assert len(result["services"]) == 1
        assert result["services"][0]["code"] == "test-service"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_severity_levels(self, mock_run_in_executor, mock_session):
        """Test that describe_severity_levels calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            "severityLevels": [
                {
                    "code": "low",
                    "name": "General guidance"
                }
            ]
        }

        # Create client
        client = SupportClient()

        # Call describe_severity_levels
        result = await client.describe_severity_levels(language="en")

        # Verify
        mock_run_in_executor.assert_called_once()
        assert "severityLevels" in result
        assert len(result["severityLevels"]) == 1
        assert result["severityLevels"][0]["code"] == "low"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_communications(self, mock_run_in_executor, mock_session):
        """Test that describe_communications calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            "communications": [
                {
                    "caseId": "test-case-id",
                    "body": "Test communication",
                    "submittedBy": "test-user",
                    "timeCreated": "2023-01-01T00:00:00Z"
                }
            ],
            "nextToken": None
        }

        # Create client
        client = SupportClient()

        # Call describe_communications
        result = await client.describe_communications(
            case_id="test-case-id",
            after_time="2023-01-01T00:00:00Z",
            before_time="2023-01-31T23:59:59Z",
            max_results=10,
            next_token=None
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert "communications" in result
        assert len(result["communications"]) == 1
        assert result["communications"][0]["caseId"] == "test-case-id"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_create_case_options(self, mock_run_in_executor, mock_session):
        """Test that describe_create_case_options calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            "categoryList": [
                {
                    "code": "test-category",
                    "name": "Test Category"
                }
            ],
            "severityLevels": [
                {
                    "code": "low",
                    "name": "General guidance"
                }
            ]
        }

        # Create client
        client = SupportClient()

        # Call describe_create_case_options
        result = await client.describe_create_case_options(
            service_code="test-service",
            language="en"
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert "categoryList" in result
        assert "severityLevels" in result

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_add_attachments_to_set(self, mock_run_in_executor, mock_session):
        """Test that add_attachments_to_set calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            "attachmentSetId": "test-attachment-set-id",
            "expiryTime": "2023-01-01T01:00:00Z"
        }

        # Create client
        client = SupportClient()

        # Test data
        attachments = [
            {
                "fileName": "test.txt",
                "data": "base64_encoded_content"
            }
        ]

        # Call add_attachments_to_set
        result = await client.add_attachments_to_set(
            attachments=attachments,
            attachment_set_id="existing-set-id"
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert "attachmentSetId" in result
        assert "expiryTime" in result

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_retry_with_backoff(self, mock_run_in_executor, mock_session):
        """Test that _retry_with_backoff handles retries correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Create client
        client = SupportClient()

        # Setup mock function that fails twice then succeeds
        mock_func = AsyncMock()
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded"
            }
        }
        mock_func.side_effect = [
            ClientError(error_response, "operation"),  # First call fails
            ClientError(error_response, "operation"),  # Second call fails
            {"success": True}  # Third call succeeds
        ]

        # Call _retry_with_backoff
        result = await client._retry_with_backoff(mock_func)

        # Verify
        assert mock_func.call_count == 3
        assert result == {"success": True}

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_create_case(self, mock_run_in_executor, mock_session):
        """Test that create_case calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {"caseId": "test-case-id"}

        # Create client
        client = SupportClient()

        # Call create_case
        result = await client.create_case(
            subject="Test subject",
            service_code="test-service",
            category_code="test-category",
            severity_code="low",
            communication_body="Test body",
            cc_email_addresses=["test@example.com"],
            language="en",
            issue_type="technical",
            attachment_set_id="test-attachment-set-id"
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {"caseId": "test-case-id"}

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_create_case_minimal(self, mock_run_in_executor, mock_session):
        """Test that create_case calls the AWS Support API with minimal parameters."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {"caseId": "test-case-id"}

        # Create client
        client = SupportClient()

        # Call create_case
        result = await client.create_case(
            subject="Test subject",
            service_code="test-service",
            category_code="test-category",
            severity_code="low",
            communication_body="Test body"
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {"caseId": "test-case-id"}

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_create_case_client_error(self, mock_run_in_executor, mock_session):
        """Test that create_case handles client errors correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {
            "Error": {
                "Code": "OtherError",
                "Message": "Some other error"
            }
        }
        mock_run_in_executor.side_effect = ClientError(error_response, "create_case")

        # Create client
        client = SupportClient()

        # Call create_case and verify error
        with pytest.raises(ClientError) as excinfo:
            await client.create_case(
                subject="Test subject",
                service_code="test-service",
                category_code="test-category",
                severity_code="low",
                communication_body="Test body"
            )

        # Verify error
        assert excinfo.value.response["Error"]["Code"] == "OtherError"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_cases(self, mock_run_in_executor, mock_session):
        """Test that describe_cases calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {"cases": [{"caseId": "test-case-id"}]}

        # Create client
        client = SupportClient()

        # Call describe_cases
        result = await client.describe_cases(
            case_id_list=["test-case-id"],
            display_id="test-display-id",
            after_time="2023-01-01T00:00:00Z",
            before_time="2023-01-31T23:59:59Z",
            include_resolved_cases=True,
            include_communications=True,
            language="en",
            max_results=10,
            next_token="test-next-token"
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {"cases": [{"caseId": "test-case-id"}]}

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_cases_minimal(self, mock_run_in_executor, mock_session):
        """Test that describe_cases calls the AWS Support API with minimal parameters."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {"cases": [{"caseId": "test-case-id"}]}

        # Create client
        client = SupportClient()

        # Call describe_cases
        result = await client.describe_cases()

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {"cases": [{"caseId": "test-case-id"}]}

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_describe_cases_case_not_found(self, mock_run_in_executor, mock_session):
        """Test that describe_cases handles case not found errors correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {
            "Error": {
                "Code": "CaseIdNotFound",
                "Message": "Case not found"
            }
        }
        mock_run_in_executor.side_effect = ClientError(error_response, "describe_cases")

        # Create client
        client = SupportClient()

        # Call describe_cases and verify error
        with pytest.raises(ClientError) as excinfo:
            await client.describe_cases(case_id_list=["test-case-id"])

        # Verify error
        assert excinfo.value.response["Error"]["Code"] == "CaseIdNotFound"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_resolve_case(self, mock_run_in_executor, mock_session):
        """Test that resolve_case calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {
            "initialCaseStatus": "opened",
            "finalCaseStatus": "resolved"
        }

        # Create client
        client = SupportClient()

        # Call resolve_case
        result = await client.resolve_case(case_id="test-case-id")

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {
            "initialCaseStatus": "opened",
            "finalCaseStatus": "resolved"
        }

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_resolve_case_case_not_found(self, mock_run_in_executor, mock_session):
        """Test that resolve_case handles case not found errors correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {
            "Error": {
                "Code": "CaseIdNotFound",
                "Message": "Case not found"
            }
        }
        mock_run_in_executor.side_effect = ClientError(error_response, "resolve_case")

        # Create client
        client = SupportClient()

        # Call resolve_case and verify error
        with pytest.raises(ClientError) as excinfo:
            await client.resolve_case(case_id="test-case-id")

        # Verify error
        assert excinfo.value.response["Error"]["Code"] == "CaseIdNotFound"

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_add_communication_to_case(self, mock_run_in_executor, mock_session):
        """Test that add_communication_to_case calls the AWS Support API correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {"result": True}

        # Create client
        client = SupportClient()

        # Call add_communication_to_case
        result = await client.add_communication_to_case(
            case_id="test-case-id",
            communication_body="Test body",
            cc_email_addresses=["test@example.com"],
            attachment_set_id="test-attachment-set-id"
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {"result": True}

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_add_communication_to_case_minimal(self, mock_run_in_executor, mock_session):
        """Test that add_communication_to_case calls the AWS Support API with minimal parameters."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_run_in_executor.return_value = {"result": True}

        # Create client
        client = SupportClient()

        # Call add_communication_to_case
        result = await client.add_communication_to_case(
            case_id="test-case-id",
            communication_body="Test body"
        )

        # Verify
        mock_run_in_executor.assert_called_once()
        assert result == {"result": True}

    @patch("boto3.Session")
    @patch("awslabs.aws_support_mcp_server.client.SupportClient._run_in_executor")
    async def test_add_communication_to_case_case_not_found(self, mock_run_in_executor, mock_session):
        """Test that add_communication_to_case handles case not found errors correctly."""
        # Setup mocks
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        error_response = {
            "Error": {
                "Code": "CaseIdNotFound",
                "Message": "Case not found"
            }
        }
        mock_run_in_executor.side_effect = ClientError(error_response, "add_communication_to_case")

        # Create client
        client = SupportClient()

        # Call add_communication_to_case and verify error
        with pytest.raises(ClientError) as excinfo:
            await client.add_communication_to_case(
                case_id="test-case-id",
                communication_body="Test body"
            )

        # Verify error
        assert excinfo.value.response["Error"]["Code"] == "CaseIdNotFound"


# Error Handling Tests

class TestErrorHandling:
    from awslabs.aws_support_mcp_server.consts import ERROR_AUTHENTICATION_FAILED, ERROR_CASE_NOT_FOUND, ERROR_RATE_LIMIT_EXCEEDED, ERROR_SUBSCRIPTION_REQUIRED
    """Tests for the error handling functions."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context with error method."""
        context = MagicMock()
        context.error = AsyncMock(return_value={"status": "error", "message": "Error message"})
        return context

    async def test_handle_client_error_access_denied(self, mock_context):
        """Test handling of AccessDeniedException."""
        error_response = {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "Access denied"
            }
        }
        error = ClientError(error_response, "test_operation")

        result = await handle_client_error(mock_context, error, "test_operation")

        assert result["status"] == "error"
        assert result["message"] == ERROR_AUTHENTICATION_FAILED
        assert result["status_code"] == 403
        mock_context.error.assert_called_once()

    async def test_handle_client_error_case_not_found(self, mock_context):
        """Test handling of CaseIdNotFound."""
        error_response = {
            "Error": {
                "Code": "CaseIdNotFound",
                "Message": "Case not found"
            }
        }
        error = ClientError(error_response, "test_operation")

        result = await handle_client_error(mock_context, error, "test_operation")

        assert result["status"] == "error"
        assert result["message"] == ERROR_CASE_NOT_FOUND
        assert result["status_code"] == 404
        mock_context.error.assert_called_once()

    async def test_handle_client_error_throttling(self, mock_context):
        """Test handling of ThrottlingException."""
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded"
            }
        }
        error = ClientError(error_response, "test_operation")

        result = await handle_client_error(mock_context, error, "test_operation")

        assert result["status"] == "error"
        assert result["message"] == ERROR_RATE_LIMIT_EXCEEDED
        assert result["status_code"] == 429
        mock_context.error.assert_called_once()



    async def test_handle_general_error_with_custom_exception(self, mock_context):
        """Test handling of custom exception types."""
        class CustomError(Exception):
            pass

        error = CustomError("Custom error message")
        result = await handle_general_error(mock_context, error, "test_operation")

        assert result["status"] == "error"
        assert "Error in test_operation" in result["message"]
        assert "CustomError" in result["message"]
        assert result["details"]["error_type"] == "CustomError"
        assert result["status_code"] == 500
        mock_context.error.assert_called_once()

    def test_create_error_response_with_details(self):
        """Test creating error response with additional details."""
        details = {
            "error_code": "TEST001",
            "error_source": "test_module",
            "additional_info": "Test information"
        }
        result = create_error_response("Test error", details=details, status_code=418)

        assert result["status"] == "error"
        assert result["message"] == "Test error"
        assert result["status_code"] == 418
        assert "timestamp" in result
        assert result["details"] == details


    async def test_handle_client_error_subscription_required(self, mock_context):
        """Test handling of SubscriptionRequiredException."""
        error_response = {
            "Error": {
                "Code": "SubscriptionRequiredException",
                "Message": "Subscription required"
            }
        }
        error = ClientError(error_response, "test_operation")

        result = await handle_client_error(mock_context, error, "test_operation")

        assert result["status"] == "error"
        assert result["message"] == ERROR_SUBSCRIPTION_REQUIRED
        assert result["status_code"] == 400  # Default client error status code
        mock_context.error.assert_called_once()

    """Tests for the error handling functions."""

    """Tests for the error handling functions."""

    async def test_handle_client_error_subscription_required(self):
        """Test handling of SubscriptionRequiredException."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(return_value={"status": "error", "message": ERROR_SUBSCRIPTION_REQUIRED})
        error_response = {
            "Error": {
                "Code": "SubscriptionRequiredException",
                "Message": "Subscription required"
            }
        }
        error = ClientError(error_response, "operation_name")

        # Call function
        result = await handle_client_error(context, error, "test_function")

        # Verify
        assert result["status"] == "error"
        assert ERROR_SUBSCRIPTION_REQUIRED in result["message"]

    async def test_handle_client_error_unauthorized(self):
        """Test handling of UnauthorizedException."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(return_value={"status": "error", "message": "AWS Support API error: Unauthorized"})
        error_response = {
            "Error": {
                "Code": "UnauthorizedException",
                "Message": "Unauthorized"
            }
        }
        error = ClientError(error_response, "operation_name")

        # Call function
        result = await handle_client_error(context, error, "test_function")

        # Verify
        assert result["status"] == "error"
        assert "Unauthorized" in result["message"]

    async def test_handle_client_error_case_not_found(self):
        """Test handling of CaseIdNotFound."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(return_value={"status": "error", "message": ERROR_CASE_NOT_FOUND})
        error_response = {
            "Error": {
                "Code": "CaseIdNotFound",
                "Message": "Case not found"
            }
        }
        error = ClientError(error_response, "operation_name")

        # Call function
        result = await handle_client_error(context, error, "test_function")

        # Verify
        assert result["status"] == "error"
        assert ERROR_CASE_NOT_FOUND in result["message"]

    async def test_handle_client_error_throttling(self):
        """Test handling of ThrottlingException."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(return_value={"status": "error", "message": ERROR_RATE_LIMIT_EXCEEDED})
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded"
            }
        }
        error = ClientError(error_response, "operation_name")

        # Call function
        result = await handle_client_error(context, error, "test_function")

        # Verify
        assert result["status"] == "error"
        assert ERROR_RATE_LIMIT_EXCEEDED in result["message"]

    async def test_handle_client_error_other(self):
        """Test handling of other client errors."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(return_value={"status": "error", "message": "AWS Support API error: Some other error"})
        error_response = {
            "Error": {
                "Code": "OtherError",
                "Message": "Some other error"
            }
        }
        error = ClientError(error_response, "operation_name")

        # Call function
        result = await handle_client_error(context, error, "test_function")

        # Verify
        assert result["status"] == "error"
        assert "AWS Support API error" in result["message"]
        assert "Some other error" in result["message"]

    async def test_handle_validation_error(self):
        """Test handling of validation errors."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(return_value={"status": "error", "message": "Validation error"})

        # Create a ValidationError with proper arguments
        try:
            # Intentionally cause a validation error
            from pydantic import BaseModel

            class TestModel(BaseModel):
                field1: str
                field2: int

            TestModel(field2="not an int")
        except ValidationError as e:
            error = e

        # Call function
        result = await handle_validation_error(context, error, "test_function")

        # Verify
        assert result["status"] == "error"
        assert "Validation error" in result["message"]

    async def test_handle_general_error(self):
        """Test handling of general errors."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(return_value={"status": "error", "message": "Error in test_function: Test error message"})
        error = ValueError("Test error message")

        # Call function
        result = await handle_general_error(context, error, "test_function")

        # Verify
        assert result["status"] == "error"
        assert "Error in test_function" in result["message"]
        assert "Test error message" in result["message"]

    async def test_handle_general_error_with_internal_server_error(self):
        """Test handling of general errors with internal server error."""
        # Setup
        context = MagicMock()
        context.error = AsyncMock(return_value={"status": "error", "message": "Error in test_function: Internal server error"})
        error = Exception("Internal server error")

        # Call function
        result = await handle_general_error(context, error, "test_function")

        # Verify
        assert result["status"] == "error"
        assert "Error in test_function" in result["message"]
        assert "Internal server error" in result["message"]


# Formatter Tests

class TestFormatCase:
    """Tests for the format_case function."""

    def test_format_case_with_communications(self, support_case_data):
        """Test formatting a case with communications."""
        formatted = format_case(support_case_data, include_communications=True)

        # Verify basic case fields
        assert formatted["caseId"] == support_case_data["caseId"]
        assert formatted["displayId"] == support_case_data["displayId"]
        assert formatted["subject"] == support_case_data["subject"]
        assert formatted["status"] == support_case_data["status"]
        assert formatted["serviceCode"] == support_case_data["serviceCode"]
        assert formatted["categoryCode"] == support_case_data["categoryCode"]
        assert formatted["severityCode"] == support_case_data["severityCode"]

        # Verify communications
        assert "recentCommunications" in formatted
        comms = formatted["recentCommunications"]["communications"]
        assert len(comms) == len(support_case_data["recentCommunications"]["communications"])

        # Verify first communication
        first_comm = comms[0]
        orig_comm = support_case_data["recentCommunications"]["communications"][0]
        assert first_comm["body"] == orig_comm["body"]
        assert first_comm["submittedBy"] == orig_comm["submittedBy"]
        assert first_comm["timeCreated"] == orig_comm["timeCreated"]

    def test_format_case_without_communications(self, support_case_data):
        """Test formatting a case without communications."""
        formatted = format_case(support_case_data, include_communications=False)

        # Verify basic case fields are present
        assert formatted["caseId"] == support_case_data["caseId"]
        assert formatted["subject"] == support_case_data["subject"]

        # Verify communications are not included
        assert "recentCommunications" not in formatted

    def test_format_case_minimal(self, minimal_support_case_data):
        """Test formatting a case with minimal data."""
        formatted = format_case(minimal_support_case_data)

        # Verify required fields
        assert formatted["caseId"] == minimal_support_case_data["caseId"]
        assert formatted["subject"] == minimal_support_case_data["subject"]
        assert formatted["status"] == minimal_support_case_data["status"]

        # Verify optional fields are handled
        assert formatted.get("displayId") is None
        assert "recentCommunications" not in formatted


class TestFormatCases:
    """Tests for the format_cases function."""

    def test_format_multiple_cases(self, multiple_support_cases_data):
        """Test formatting multiple cases."""
        formatted = format_cases(multiple_support_cases_data)

        assert len(formatted) == len(multiple_support_cases_data)
        for formatted_case, original_case in zip(formatted, multiple_support_cases_data):
            assert formatted_case["caseId"] == original_case["caseId"]
            assert formatted_case["subject"] == original_case["subject"]

    def test_format_empty_cases_list(self):
        """Test formatting an empty list of cases."""
        formatted = format_cases([])
        assert formatted == []


class TestFormatCommunications:
    """Tests for the format_communications function."""

    def test_format_communications_with_attachments(self, communications_response_data):
        """Test formatting communications with attachments."""
        formatted = format_communications(communications_response_data)

        assert "communications" in formatted
        assert len(formatted["communications"]) == len(communications_response_data["communications"])

        first_comm = formatted["communications"][0]
        orig_comm = communications_response_data["communications"][0]
        assert first_comm["body"] == orig_comm["body"]
        assert first_comm["submittedBy"] == orig_comm["submittedBy"]

    def test_format_empty_communications(self, empty_communications_response_data):
        """Test formatting empty communications."""
        formatted = format_communications(empty_communications_response_data)

        assert "communications" in formatted
        assert len(formatted["communications"]) == 0
        assert formatted["next_token"] is None


class TestFormatServices:
    """Tests for the format_services function."""

    def test_format_services_with_categories(self, services_response_data):
        """Test formatting services with categories."""
        formatted = format_services(services_response_data["services"])

        # Verify first service
        first_service = services_response_data["services"][0]
        service_code = first_service["code"]

        assert service_code in formatted
        assert formatted[service_code]["name"] == first_service["name"]
        assert len(formatted[service_code]["categories"]) == len(first_service["categories"])

    def test_format_empty_services(self, empty_services_response_data):
        """Test formatting empty services."""
        formatted = format_services(empty_services_response_data["services"])
        assert formatted == {}


class TestFormatSeverityLevels:
    """Tests for the format_severity_levels function."""

    def test_format_severity_levels(self, severity_levels_response_data):
        """Test formatting severity levels."""
        formatted = format_severity_levels(severity_levels_response_data["severityLevels"])

        for level in severity_levels_response_data["severityLevels"]:
            assert level["code"] in formatted
            assert formatted[level["code"]]["name"] == level["name"]

    def test_format_empty_severity_levels(self, empty_severity_levels_response_data):
        """Test formatting empty severity levels."""
        formatted = format_severity_levels(empty_severity_levels_response_data["severityLevels"])
        assert formatted == {}


class TestFormatMarkdown:
    """Tests for the Markdown formatting functions."""

    def test_format_markdown_case_summary(self, support_case_data):
        """Test formatting a case summary in Markdown."""
        formatted_case = format_case(support_case_data)
        markdown = format_markdown_case_summary(formatted_case)

        # Verify key elements are present in the Markdown
        assert f"**Case ID**: {support_case_data['caseId']}" in markdown
        assert f"**Subject**: {support_case_data['subject']}" in markdown
        assert "## Recent Communications" in markdown

        # Verify communication details
        first_comm = support_case_data["recentCommunications"]["communications"][0]
        assert first_comm["body"] in markdown
        assert first_comm["submittedBy"] in markdown

    def test_format_markdown_services(self, services_response_data):
        """Test formatting services in Markdown."""
        formatted_services = format_services(services_response_data["services"])
        markdown = format_markdown_services(formatted_services)

        # Verify key elements are present in the Markdown
        assert "# AWS Services" in markdown

        # Verify first service
        first_service = services_response_data["services"][0]
        assert f"## {first_service['name']}" in markdown
        assert f"`{first_service['code']}`" in markdown

        # Verify categories
        if first_service["categories"]:
            assert "### Categories" in markdown
            first_category = first_service["categories"][0]
            assert f"`{first_category['code']}`" in markdown

    def test_format_markdown_severity_levels(self, severity_levels_response_data):
        """Test formatting severity levels in Markdown."""
        formatted_levels = format_severity_levels(severity_levels_response_data["severityLevels"])
        markdown = format_markdown_severity_levels(formatted_levels)

        # Verify key elements are present in the Markdown
        assert "# AWS Support Severity Levels" in markdown

        # Verify severity levels
        for level in severity_levels_response_data["severityLevels"]:
            assert f"**{level['name']}**" in markdown
            assert f"`{level['code']}`" in markdown

    def test_format_json_response(self):
        """Test JSON response formatting."""
        test_data = {
            "key1": "value1",
            "key2": {
                "nested": "value2"
            },
            "key3": [1, 2, 3]
        }

        formatted = format_json_response(test_data)
        assert isinstance(formatted, str)
        parsed = json.loads(formatted)
        assert parsed == test_data


class TestFormatCase:
    """Tests for the format_case function."""

    def test_valid_case_formatting(self, support_case_data):
        """Test that a valid case is formatted correctly."""
        formatted_case = format_case(support_case_data)
        assert formatted_case["caseId"] == support_case_data["caseId"]
        assert formatted_case["displayId"] == support_case_data["displayId"]
        assert formatted_case["subject"] == support_case_data["subject"]
        assert formatted_case["status"] == support_case_data["status"]
        assert formatted_case["serviceCode"] == support_case_data["serviceCode"]
        assert formatted_case["categoryCode"] == support_case_data["categoryCode"]
        assert formatted_case["severityCode"] == support_case_data["severityCode"]
        assert formatted_case["submittedBy"] == support_case_data["submittedBy"]
        assert formatted_case["timeCreated"] == support_case_data["timeCreated"]
        assert formatted_case["ccEmailAddresses"] == support_case_data["ccEmailAddresses"]
        assert formatted_case["language"] == support_case_data["language"]
        assert "recentCommunications" in formatted_case
        assert len(formatted_case["recentCommunications"]["communications"]) == len(
            support_case_data["recentCommunications"]["communications"]
        )

    def test_minimal_case_formatting(self, minimal_support_case_data):
        """Test that a minimal case is formatted correctly."""
        formatted_case = format_case(minimal_support_case_data)
        assert formatted_case["caseId"] == minimal_support_case_data["caseId"]
        assert formatted_case["subject"] == minimal_support_case_data["subject"]
        assert formatted_case["status"] == minimal_support_case_data["status"]
        assert formatted_case["serviceCode"] == minimal_support_case_data["serviceCode"]
        assert formatted_case["categoryCode"] == minimal_support_case_data["categoryCode"]
        assert formatted_case["severityCode"] == minimal_support_case_data["severityCode"]
        assert formatted_case["submittedBy"] == minimal_support_case_data["submittedBy"]
        assert formatted_case["timeCreated"] == minimal_support_case_data["timeCreated"]

    def test_edge_case_formatting(self, edge_case_support_case_data):
        """Test that an edge case is formatted correctly."""
        formatted_case = format_case(edge_case_support_case_data)
        assert formatted_case["caseId"] == edge_case_support_case_data["caseId"]
        assert formatted_case["subject"] == edge_case_support_case_data["subject"]
        assert len(formatted_case["subject"]) == len(edge_case_support_case_data["subject"])


# Server Tests

@patch("awslabs.aws_support_mcp_server.server.support_client")
async def test_create_case(mock_support_client):
    """Test that create_case calls the AWS Support API correctly."""
    # Setup mocks
    mock_support_client.create_case = AsyncMock(return_value={"caseId": "test-case-id"})

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={"status": "error", "message": "Error message"})

    # Call create_case
    request_data = {
        "subject": "Test subject",
        "service_code": "test-service",
        "category_code": "test-category",
        "severity_code": "low",
        "communication_body": "Test body",
        "cc_email_addresses": ["test@example.com"],
        "language": "en",
        "issue_type": "technical",
        "attachment_set_id": "test-attachment-set-id"
    }

    # Patch the to_api_params method to return the correct parameter names
    with patch("awslabs.aws_support_mcp_server.models.CreateCaseRequest.to_api_params") as mock_to_api_params:
        mock_to_api_params.return_value = {
            "subject": "Test subject",
            "service_code": "test-service",
            "category_code": "test-category",
            "severity_code": "low",
            "communication_body": "Test body",
            "cc_email_addresses": ["test@example.com"],
            "language": "en",
            "issue_type": "technical",
            "attachment_set_id": "test-attachment-set-id"
        }

        result = await create_support_case(context, **request_data)

    # Verify
    mock_support_client.create_case.assert_called_once()
    assert "case_id" in result
    assert result["case_id"] == "test-case-id"


@patch("awslabs.aws_support_mcp_server.server.support_client")
async def test_describe_cases(mock_support_client):
    """Test that describe_cases calls the AWS Support API correctly."""
    # Setup mocks
    mock_support_client.describe_cases = AsyncMock(return_value={
        "cases": [
            {
                "caseId": "test-case-id",
                "displayId": "test-display-id",
                "subject": "Test subject",
                "status": "opened",
                "serviceCode": "test-service",
                "categoryCode": "test-category",
                "severityCode": "low",
                "submittedBy": "test-user",
                "timeCreated": "2023-01-01T00:00:00Z",
                "recentCommunications": {
                    "communications": [
                        {
                            "caseId": "test-case-id",
                            "body": "Test body",
                            "submittedBy": "test-user",
                            "timeCreated": "2023-01-01T00:00:00Z"
                        }
                    ]
                }
            }
        ]
    })

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={"status": "error", "message": "Error message"})

    # Call describe_cases
    request_data = {
        "case_id_list": ["test-case-id"],
        "display_id": "test-display-id",
        "after_time": "2023-01-01T00:00:00Z",
        "before_time": "2023-01-31T23:59:59Z",
        "include_resolved_cases": True,
        "include_communications": True,
        "language": "en",
        "max_results": 10,
        "next_token": "test-next-token",
        "format": "json"
    }

    # Patch the to_api_params method to return the correct parameter names
    with patch("awslabs.aws_support_mcp_server.models.DescribeCasesRequest.to_api_params") as mock_to_api_params:
        mock_to_api_params.return_value = {
            "case_id_list": ["test-case-id"],
            "display_id": "test-display-id",
            "after_time": "2023-01-01T00:00:00Z",
            "before_time": "2023-01-31T23:59:59Z",
            "include_resolved_cases": True,
            "include_communications": True,
            "language": "en",
            "max_results": 10,
            "next_token": "test-next-token"
        }

        result = await describe_support_cases(context, **request_data)

    # Verify
    mock_support_client.describe_cases.assert_called_once()
    assert "cases" in result
    assert len(result["cases"]) == 1
    assert result["cases"][0]["case_id"] == "test-case-id"


@patch("awslabs.aws_support_mcp_server.server.support_client")
async def test_add_communication_to_case(mock_support_client):
    """Test that add_communication_to_case calls the AWS Support API correctly."""
    # Setup mocks
    mock_support_client.add_communication_to_case = AsyncMock(return_value={"result": True})

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={"status": "error", "message": "Error message"})

    # Call add_communication_to_case
    request_data = {
        "case_id": "test-case-id",
        "communication_body": "Test body",
        "cc_email_addresses": ["test@example.com"],
        "attachment_set_id": "test-attachment-set-id"
    }

    # Patch the to_api_params method to return the correct parameter names
    with patch("awslabs.aws_support_mcp_server.models.AddCommunicationRequest.to_api_params") as mock_to_api_params:
        mock_to_api_params.return_value = {
            "case_id": "test-case-id",
            "communication_body": "Test body",
            "cc_email_addresses": ["test@example.com"],
            "attachment_set_id": "test-attachment-set-id"
        }

        result = await add_communication_to_case(context, **request_data)

    # Verify
    mock_support_client.add_communication_to_case.assert_called_once()
    assert "result" in result
    assert result["result"] is True


@patch("awslabs.aws_support_mcp_server.server.support_client")
async def test_resolve_case(mock_support_client):
    """Test that resolve_case calls the AWS Support API correctly."""
    # Setup mocks
    mock_support_client.resolve_case = AsyncMock(return_value={
        "initialCaseStatus": "opened",
        "finalCaseStatus": "resolved"
    })

    # Create mock context
    context = MagicMock()
    context.error = AsyncMock(return_value={"status": "error", "message": "Error message"})

    # Call resolve_case
    # Patch the to_api_params method to return the correct parameter names
    with patch("awslabs.aws_support_mcp_server.models.ResolveCaseRequest.to_api_params") as mock_to_api_params:
        mock_to_api_params.return_value = {
            "case_id": "test-case-id"
        }

        result = await resolve_support_case(context, case_id="test-case-id")

    # Verify
    mock_support_client.resolve_case.assert_called_once()
    assert "initial_case_status" in result
    assert result["initial_case_status"] == "opened"
    assert "final_case_status" in result
    assert result["final_case_status"] == "resolved"



async def test_error_handling():
    """Test that the server handles errors correctly."""


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
        assert report == {"diagnostics_enabled": False}

    def test_enable_disable(self):
        """Test enabling and disabling diagnostics."""
        self.tracker.enable()
        assert self.tracker.enabled
        report = self.tracker.get_diagnostics_report()
        assert report["diagnostics_enabled"] is True

        self.tracker.disable()
        assert not self.tracker.enabled
        report = self.tracker.get_diagnostics_report()
        assert report == {"diagnostics_enabled": False}

    def test_reset(self):
        """Test resetting diagnostics data."""
        self.tracker.enable()
        self.tracker.track_performance("test_func", 1.0)
        self.tracker.track_error("TestError")
        self.tracker.track_request("test_request")

        self.tracker.reset()
        report = self.tracker.get_diagnostics_report()
        assert report["performance"] == {}
        assert report["errors"] == {}
        assert report["requests"] == {}

    def test_track_performance(self):
        """Test performance tracking."""
        self.tracker.enable()
        self.tracker.track_performance("test_func", 1.0)
        self.tracker.track_performance("test_func", 2.0)

        report = self.tracker.get_diagnostics_report()
        perf_data = report["performance"]["test_func"]
        assert perf_data["count"] == 2
        assert perf_data["total_time"] == 3.0
        assert perf_data["min_time"] == 1.0
        assert perf_data["max_time"] == 2.0
        assert isinstance(perf_data["last_call"], float)

    def test_track_performance_disabled(self):
        """Test performance tracking when disabled."""
        self.tracker.track_performance("test_func", 1.0)
        report = self.tracker.get_diagnostics_report()
        assert report == {"diagnostics_enabled": False}

    def test_track_error(self):
        """Test error tracking."""
        self.tracker.enable()
        self.tracker.track_error("TestError")
        self.tracker.track_error("TestError")
        self.tracker.track_error("OtherError")

        report = self.tracker.get_diagnostics_report()
        assert report["errors"]["TestError"] == 2
        assert report["errors"]["OtherError"] == 1

    def test_track_error_disabled(self):
        """Test error tracking when disabled."""
        self.tracker.track_error("TestError")
        report = self.tracker.get_diagnostics_report()
        assert report == {"diagnostics_enabled": False}

    def test_track_request(self):
        """Test request tracking."""
        self.tracker.enable()
        self.tracker.track_request("GET")
        self.tracker.track_request("GET")
        self.tracker.track_request("POST")

        report = self.tracker.get_diagnostics_report()
        assert report["requests"]["GET"] == 2
        assert report["requests"]["POST"] == 1

    def test_track_request_disabled(self):
        """Test request tracking when disabled."""
        self.tracker.track_request("GET")
        report = self.tracker.get_diagnostics_report()
        assert report == {"diagnostics_enabled": False}

    def test_uptime(self):
        """Test uptime calculation."""
        self.tracker.enable()
        time.sleep(0.1)  # Small delay to ensure uptime > 0
        assert self.tracker.uptime > 0

    @patch("time.time")
    def test_performance_tracking_edge_cases(self, mock_time):
        """Test performance tracking edge cases."""
        self.tracker.enable()

        # Test with very small duration
        mock_time.return_value = 1000.0
        self.tracker.track_performance("test_func", 0.000001)

        # Test with very large duration
        self.tracker.track_performance("test_func", 999999.999)

        report = self.tracker.get_diagnostics_report()
        perf_data = report["performance"]["test_func"]
        assert perf_data["min_time"] == 0.000001
        assert perf_data["max_time"] == 999999.999



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
        assert report == {"diagnostics_enabled": False}

    def test_enable_disable(self):
        """Test enabling and disabling diagnostics."""
        self.tracker.enable()
        assert self.tracker.enabled
        report = self.tracker.get_diagnostics_report()
        assert report["diagnostics_enabled"] is True

        self.tracker.disable()
        assert not self.tracker.enabled
        report = self.tracker.get_diagnostics_report()
        assert report == {"diagnostics_enabled": False}

    def test_reset(self):
        """Test resetting diagnostics data."""
        self.tracker.enable()
        self.tracker.track_performance("test_func", 1.0)
        self.tracker.track_error("TestError")
        self.tracker.track_request("test_request")

        self.tracker.reset()
        report = self.tracker.get_diagnostics_report()
        assert report["performance"] == {}
        assert report["errors"] == {}
        assert report["requests"] == {}

    def test_track_performance(self):
        """Test performance tracking."""
        self.tracker.enable()
        self.tracker.track_performance("test_func", 1.0)
        self.tracker.track_performance("test_func", 2.0)

        report = self.tracker.get_diagnostics_report()
        perf_data = report["performance"]["test_func"]
        assert perf_data["count"] == 2
        assert perf_data["total_time"] == 3.0
        assert perf_data["min_time"] == 1.0
        assert perf_data["max_time"] == 2.0
        assert isinstance(perf_data["last_call"], float)

    def test_track_performance_disabled(self):
        """Test performance tracking when disabled."""
        self.tracker.track_performance("test_func", 1.0)
        report = self.tracker.get_diagnostics_report()
        assert report == {"diagnostics_enabled": False}

    def test_track_error(self):
        """Test error tracking."""
        self.tracker.enable()
        self.tracker.track_error("TestError")
        self.tracker.track_error("TestError")
        self.tracker.track_error("OtherError")

        report = self.tracker.get_diagnostics_report()
        assert report["errors"]["TestError"] == 2
        assert report["errors"]["OtherError"] == 1

    def test_track_error_disabled(self):
        """Test error tracking when disabled."""
        self.tracker.track_error("TestError")
        report = self.tracker.get_diagnostics_report()
        assert report == {"diagnostics_enabled": False}

    def test_track_request(self):
        """Test request tracking."""
        self.tracker.enable()
        self.tracker.track_request("GET")
        self.tracker.track_request("GET")
        self.tracker.track_request("POST")

        report = self.tracker.get_diagnostics_report()
        assert report["requests"]["GET"] == 2
        assert report["requests"]["POST"] == 1

    def test_track_request_disabled(self):
        """Test request tracking when disabled."""
        self.tracker.track_request("GET")
        report = self.tracker.get_diagnostics_report()
        assert report == {"diagnostics_enabled": False}

    def test_uptime(self):
        """Test uptime calculation."""
        self.tracker.enable()
        time.sleep(0.1)  # Small delay to ensure uptime > 0
        assert self.tracker.uptime > 0

    @patch("time.time")
    def test_performance_tracking_edge_cases(self, mock_time):
        """Test performance tracking edge cases."""
        self.tracker.enable()
        mock_time.return_value = 1000.0

        # Test with very small duration
        self.tracker.track_performance("test_func", 0.000001)

        # Test with very large duration
        self.tracker.track_performance("test_func", 999999.999)

        report = self.tracker.get_diagnostics_report()
        perf_data = report["performance"]["test_func"]
        assert perf_data["min_time"] == 0.000001
        assert perf_data["max_time"] == 999999.999


# Server Tests
class TestServer:
    """Tests for the MCP server implementation."""

    @patch("awslabs.aws_support_mcp_server.server.logger")
    def test_logging_configuration(self, mock_logger):
        """Test logging configuration."""
        import sys
        from awslabs.aws_support_mcp_server.server import main

        # Create mock arguments
        sys.argv = ["server.py", "--debug"]

        # Call main (but mock the actual server run)
        with patch("awslabs.aws_support_mcp_server.server.mcp.run"):
            main()

        # Verify logging configuration
        mock_logger.remove.assert_called()
        mock_logger.add.assert_called()
        # Verify debug level was set
        assert any("DEBUG" in str(call) for call in mock_logger.add.call_args_list)
