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

"""Pytest fixtures for AWS Support API MCP Server tests."""

import datetime
import pytest
from typing import Dict, List, Any


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
