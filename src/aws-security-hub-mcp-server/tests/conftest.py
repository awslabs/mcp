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
"""Test configuration and fixtures for AWS Security Hub MCP Server."""

from datetime import datetime
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_security_hub_client():
    """Mock Security Hub client for testing."""
    client = Mock()
    client.get_findings.return_value = {"Findings": []}
    client.get_enabled_standards.return_value = {"StandardsSubscriptions": []}
    client.describe_standards.return_value = {"Standards": []}
    client.describe_standards_controls.return_value = {"Controls": []}
    client.get_insights.return_value = {"Insights": []}
    client.batch_update_findings.return_value = {"ProcessedFindings": [], "UnprocessedFindings": []}
    yield client


@pytest.fixture
def sample_finding():
    """Sample Security Hub finding for testing."""
    return {
        "Id": "arn:aws:securityhub:us-east-1:123456789012:finding/test-finding-1",
        "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
        "GeneratorId": "test-generator",
        "AwsAccountId": "123456789012",
        "Region": "us-east-1",
        "Title": "Test Security Finding",
        "Description": "This is a test security finding",
        "Severity": {"Label": "HIGH", "Normalized": 70},
        "Workflow": {"Status": "NEW"},
        "RecordState": "ACTIVE",
        "CreatedAt": datetime.utcnow(),
        "UpdatedAt": datetime.utcnow(),
        "Resources": [{"Type": "AwsEc2Instance", "Id": "i-1234567890abcdef0"}],
        "Compliance": {"Status": "FAILED"},
    }


@pytest.fixture
def sample_standard():
    """Sample Security Hub standard for testing."""
    return {
        "StandardsArn": "arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0",
        "Name": "AWS Foundational Security Standard",
        "Description": "AWS Foundational Security Standard",
        "EnabledByDefault": True,
    }


@pytest.fixture
def mock_context():
    """Mock MCP context for testing."""
    return Mock()


@pytest.fixture
def sample_enabled_standard():
    """Sample enabled Security Hub standard for testing."""
    return {
        "StandardsSubscriptionArn": "arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-standard/v/1.0.0",
        "StandardsArn": "arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0",
        "StandardsInput": {},
        "StandardsStatus": "READY",
    }


@pytest.fixture
def sample_control_definition():
    """Sample security control definition for testing."""
    return {
        "SecurityControlId": "S3.1",
        "SecurityControlArn": "arn:aws:securityhub:us-east-1:123456789012:security-control/S3.1",
        "Title": "S3 buckets should have public access blocked",
        "Description": "This control checks whether S3 buckets have public access blocked.",
        "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/S3.1/remediation",
        "SeverityRating": "HIGH",
        "CurrentRegionAvailability": "AVAILABLE",
    }


@pytest.fixture
def sample_finding_history():
    """Sample finding history record for testing."""
    return {
        "FindingIdentifier": {
            "Id": "arn:aws:securityhub:us-east-1:123456789012:finding/test-finding-1",
            "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
        },
        "UpdateTime": datetime.utcnow(),
        "FindingCreated": True,
        "UpdateSource": {"Type": "BATCH_UPDATE_FINDINGS", "Identity": "arn:aws:iam::123456789012:user/test-user"},
        "Updates": [{"UpdatedField": "Workflow/Status", "OldValue": "NEW", "NewValue": "RESOLVED"}],
    }
