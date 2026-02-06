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
"""Tests for test configuration and fixtures."""

from datetime import datetime


def test_mock_security_hub_client(mock_security_hub_client):
    """Test the mock Security Hub client fixture."""
    # Test that all expected methods are available
    assert hasattr(mock_security_hub_client, "get_findings")
    assert hasattr(mock_security_hub_client, "get_enabled_standards")
    assert hasattr(mock_security_hub_client, "describe_standards")
    assert hasattr(mock_security_hub_client, "describe_standards_controls")
    assert hasattr(mock_security_hub_client, "get_insights")
    assert hasattr(mock_security_hub_client, "batch_update_findings")

    # Test that methods return expected default values
    assert mock_security_hub_client.get_findings.return_value == {"Findings": []}
    assert mock_security_hub_client.get_enabled_standards.return_value == {"StandardsSubscriptions": []}
    assert mock_security_hub_client.describe_standards.return_value == {"Standards": []}
    assert mock_security_hub_client.describe_standards_controls.return_value == {"Controls": []}
    assert mock_security_hub_client.get_insights.return_value == {"Insights": []}
    assert mock_security_hub_client.batch_update_findings.return_value == {
        "ProcessedFindings": [],
        "UnprocessedFindings": [],
    }


def test_sample_finding(sample_finding):
    """Test the sample finding fixture."""
    # Test that all required fields are present
    required_fields = [
        "Id",
        "ProductArn",
        "GeneratorId",
        "AwsAccountId",
        "Region",
        "Title",
        "Description",
        "Severity",
        "Workflow",
        "RecordState",
        "CreatedAt",
        "UpdatedAt",
        "Resources",
        "Compliance",
    ]

    for field in required_fields:
        assert field in sample_finding

    # Test field values
    assert sample_finding["Severity"]["Label"] == "HIGH"
    assert sample_finding["Workflow"]["Status"] == "NEW"
    assert sample_finding["RecordState"] == "ACTIVE"
    assert sample_finding["Compliance"]["Status"] == "FAILED"
    assert len(sample_finding["Resources"]) == 1
    assert sample_finding["Resources"][0]["Type"] == "AwsEc2Instance"
    assert isinstance(sample_finding["CreatedAt"], datetime)
    assert isinstance(sample_finding["UpdatedAt"], datetime)


def test_sample_standard(sample_standard):
    """Test the sample standard fixture."""
    required_fields = ["StandardsArn", "Name", "Description", "EnabledByDefault"]

    for field in required_fields:
        assert field in sample_standard

    assert "aws-foundational-security-standard" in sample_standard["StandardsArn"]
    assert sample_standard["Name"] == "AWS Foundational Security Standard"
    assert sample_standard["EnabledByDefault"] is True


def test_mock_context(mock_context):
    """Test the mock context fixture."""
    # Should be a Mock object
    assert mock_context is not None
    # Mock objects are callable
    assert callable(mock_context)


def test_sample_enabled_standard(sample_enabled_standard):
    """Test the sample enabled standard fixture."""
    required_fields = ["StandardsSubscriptionArn", "StandardsArn", "StandardsInput", "StandardsStatus"]

    for field in required_fields:
        assert field in sample_enabled_standard

    assert "subscription" in sample_enabled_standard["StandardsSubscriptionArn"]
    assert "aws-foundational-security-standard" in sample_enabled_standard["StandardsArn"]
    assert sample_enabled_standard["StandardsStatus"] == "READY"
    assert isinstance(sample_enabled_standard["StandardsInput"], dict)


def test_sample_control_definition(sample_control_definition):
    """Test the sample control definition fixture."""
    required_fields = [
        "SecurityControlId",
        "SecurityControlArn",
        "Title",
        "Description",
        "RemediationUrl",
        "SeverityRating",
        "CurrentRegionAvailability",
    ]

    for field in required_fields:
        assert field in sample_control_definition

    assert sample_control_definition["SecurityControlId"] == "S3.1"
    assert "S3 buckets should have public access blocked" in sample_control_definition["Title"]
    assert sample_control_definition["SeverityRating"] == "HIGH"
    assert sample_control_definition["CurrentRegionAvailability"] == "AVAILABLE"


def test_sample_finding_history(sample_finding_history):
    """Test the sample finding history fixture."""
    required_fields = ["FindingIdentifier", "UpdateTime", "FindingCreated", "UpdateSource", "Updates"]

    for field in required_fields:
        assert field in sample_finding_history

    # Test FindingIdentifier structure
    assert "Id" in sample_finding_history["FindingIdentifier"]
    assert "ProductArn" in sample_finding_history["FindingIdentifier"]

    # Test UpdateSource structure
    assert "Type" in sample_finding_history["UpdateSource"]
    assert "Identity" in sample_finding_history["UpdateSource"]
    assert sample_finding_history["UpdateSource"]["Type"] == "BATCH_UPDATE_FINDINGS"

    # Test Updates structure
    assert isinstance(sample_finding_history["Updates"], list)
    assert len(sample_finding_history["Updates"]) == 1
    update = sample_finding_history["Updates"][0]
    assert "UpdatedField" in update
    assert "OldValue" in update
    assert "NewValue" in update
    assert update["UpdatedField"] == "Workflow/Status"
    assert update["OldValue"] == "NEW"
    assert update["NewValue"] == "RESOLVED"

    assert sample_finding_history["FindingCreated"] is True
    assert isinstance(sample_finding_history["UpdateTime"], datetime)
