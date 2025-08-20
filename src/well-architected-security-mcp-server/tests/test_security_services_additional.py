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

"""Additional tests for the security_services module to improve coverage."""

from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server.util.security_services import (
    get_access_analyzer_findings,
    get_inspector_findings,
    get_macie_findings,
    get_securityhub_findings,
    get_trusted_advisor_findings,
)


@pytest.mark.asyncio
async def test_get_securityhub_findings_with_no_filter_criteria(
    mock_ctx, mock_boto3_session, mock_securityhub_client
):
    """Test the get_securityhub_findings function with no filter criteria."""
    # Set up mock_boto3_session to return mock_securityhub_client
    mock_boto3_session.client.return_value = mock_securityhub_client

    # Mock check_security_hub to return enabled
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.security_services.check_security_hub"
    ) as mock_check:
        mock_check.return_value = {"enabled": True}

        # Mock get_findings to return findings
        mock_securityhub_client.get_findings = mock.MagicMock(
            return_value={
                "Findings": [
                    {
                        "Id": "finding1",
                        "Severity": {"Label": "HIGH"},
                        "ProductName": "Security Hub",
                        "Resources": [{"Type": "AwsAccount"}],
                    }
                ]
            }
        )

        # Call the function with no filter_criteria (explicitly set to None)
        result = await get_securityhub_findings(
            "us-east-1", mock_boto3_session, mock_ctx, max_findings=100, filter_criteria=None
        )

        # Verify the result
        assert result["enabled"] is True
        assert len(result["findings"]) == 1
        assert "summary" in result
        assert result["summary"]["total_count"] == 1
        assert "message" in result
        assert "Retrieved 1 Security Hub findings" in result["message"]

        # Verify that get_findings was called with the default filter criteria
        # The default filter criteria should include:
        # - RecordState: ACTIVE
        # - WorkflowStatus: NEW
        # - UpdatedAt: last 30 days
        # - SeverityLabel: HIGH or CRITICAL
        call_args = mock_securityhub_client.get_findings.call_args[1]
        assert "Filters" in call_args
        filters = call_args["Filters"]

        # Check that the default filters were applied
        assert "RecordState" in filters
        assert filters["RecordState"][0]["Comparison"] == "EQUALS"
        assert filters["RecordState"][0]["Value"] == "ACTIVE"

        assert "WorkflowStatus" in filters
        assert filters["WorkflowStatus"][0]["Comparison"] == "EQUALS"
        assert filters["WorkflowStatus"][0]["Value"] == "NEW"

        assert "UpdatedAt" in filters
        assert len(filters["UpdatedAt"]) == 1
        assert "Start" in filters["UpdatedAt"][0]
        assert "End" in filters["UpdatedAt"][0]

        assert "SeverityLabel" in filters
        assert len(filters["SeverityLabel"]) == 2
        assert filters["SeverityLabel"][0]["Comparison"] == "EQUALS"
        assert filters["SeverityLabel"][0]["Value"] == "HIGH"
        assert filters["SeverityLabel"][1]["Comparison"] == "EQUALS"
        assert filters["SeverityLabel"][1]["Value"] == "CRITICAL"

        # Check that MaxResults was set correctly
        assert call_args["MaxResults"] == 100


@pytest.mark.asyncio
async def test_get_securityhub_findings_with_custom_filter_criteria(
    mock_ctx, mock_boto3_session, mock_securityhub_client
):
    """Test the get_securityhub_findings function with custom filter criteria."""
    # Set up mock_boto3_session to return mock_securityhub_client
    mock_boto3_session.client.return_value = mock_securityhub_client

    # Mock check_security_hub to return enabled
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.security_services.check_security_hub"
    ) as mock_check:
        mock_check.return_value = {"enabled": True}

        # Mock get_findings to return findings
        mock_securityhub_client.get_findings = mock.MagicMock(
            return_value={
                "Findings": [
                    {
                        "Id": "finding1",
                        "Severity": {"Label": "MEDIUM"},
                        "ProductName": "Security Hub",
                        "Resources": [{"Type": "AwsAccount"}],
                    }
                ]
            }
        )

        # Create custom filter criteria
        custom_filter = {
            "SeverityLabel": [{"Comparison": "EQUALS", "Value": "MEDIUM"}],
            "ComplianceStatus": [{"Comparison": "EQUALS", "Value": "FAILED"}],
        }

        # Call the function with custom filter_criteria
        result = await get_securityhub_findings(
            "us-east-1",
            mock_boto3_session,
            mock_ctx,
            max_findings=50,
            filter_criteria=custom_filter,
        )

        # Verify the result
        assert result["enabled"] is True
        assert len(result["findings"]) == 1
        assert "summary" in result
        assert result["summary"]["total_count"] == 1
        assert "message" in result
        assert "Retrieved 1 Security Hub findings" in result["message"]

        # Verify that get_findings was called with the custom filter criteria
        call_args = mock_securityhub_client.get_findings.call_args[1]
        assert "Filters" in call_args
        filters = call_args["Filters"]

        # Check that the custom filters were applied
        assert "SeverityLabel" in filters
        assert filters["SeverityLabel"][0]["Comparison"] == "EQUALS"
        assert filters["SeverityLabel"][0]["Value"] == "MEDIUM"

        assert "ComplianceStatus" in filters
        assert filters["ComplianceStatus"][0]["Comparison"] == "EQUALS"
        assert filters["ComplianceStatus"][0]["Value"] == "FAILED"

        # Check that MaxResults was set correctly
        assert call_args["MaxResults"] == 50


@pytest.mark.asyncio
async def test_get_securityhub_findings_with_no_findings(
    mock_ctx, mock_boto3_session, mock_securityhub_client
):
    """Test the get_securityhub_findings function when no findings match the criteria."""
    # Set up mock_boto3_session to return mock_securityhub_client
    mock_boto3_session.client.return_value = mock_securityhub_client

    # Mock check_security_hub to return enabled
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.security_services.check_security_hub"
    ) as mock_check:
        mock_check.return_value = {"enabled": True}

        # Mock get_findings to return no findings
        mock_securityhub_client.get_findings = mock.MagicMock(return_value={"Findings": []})

        # Call the function
        result = await get_securityhub_findings(
            "us-east-1", mock_boto3_session, mock_ctx, max_findings=100, filter_criteria=None
        )

        # Verify the result
        assert result["enabled"] is True
        assert len(result["findings"]) == 0
        assert "message" in result
        assert "No Security Hub findings match the filter criteria" in result["message"]


@pytest.mark.asyncio
async def test_get_securityhub_findings_error(
    mock_ctx, mock_boto3_session, mock_securityhub_client
):
    """Test the get_securityhub_findings function when an error occurs."""
    # Set up mock_boto3_session to return mock_securityhub_client
    mock_boto3_session.client.return_value = mock_securityhub_client

    # Mock check_security_hub to return enabled
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.security_services.check_security_hub"
    ) as mock_check:
        mock_check.return_value = {"enabled": True}

        # Mock get_findings to raise an exception
        mock_securityhub_client.get_findings = mock.MagicMock(side_effect=Exception("API Error"))

        # Call the function
        result = await get_securityhub_findings(
            "us-east-1", mock_boto3_session, mock_ctx, max_findings=100, filter_criteria=None
        )

        # Verify the result
        assert result["enabled"] is True
        assert "error" in result
        assert "API Error" in result["error"]
        assert len(result["findings"]) == 0
        assert "message" in result
        assert "Error getting Security Hub findings" in result["message"]
        mock_ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_get_inspector_findings_error(mock_ctx, mock_boto3_session, mock_inspector_client):
    """Test the get_inspector_findings function when an error occurs."""
    # Set up mock_boto3_session to return mock_inspector_client
    mock_boto3_session.client.return_value = mock_inspector_client

    # Mock check_inspector to return enabled
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.security_services.check_inspector"
    ) as mock_check:
        mock_check.return_value = {"enabled": True}

        # Mock list_findings to raise an exception
        mock_inspector_client.list_findings = mock.MagicMock(side_effect=Exception("API Error"))

        # Call the function
        result = await get_inspector_findings(
            "us-east-1", mock_boto3_session, mock_ctx, max_findings=100, filter_criteria=None
        )

        # Verify the result
        assert result["enabled"] is True
        assert "error" in result
        assert "API Error" in result["error"]
        assert len(result["findings"]) == 0
        assert "message" in result
        assert "Error getting Inspector findings" in result["message"]
        mock_ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_get_access_analyzer_findings_error(
    mock_ctx, mock_boto3_session, mock_accessanalyzer_client
):
    """Test the get_access_analyzer_findings function when an error occurs."""
    # Set up mock_boto3_session to return mock_accessanalyzer_client
    mock_boto3_session.client.return_value = mock_accessanalyzer_client

    # Mock check_access_analyzer to return enabled
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.security_services.check_access_analyzer"
    ) as mock_check:
        mock_check.return_value = {
            "enabled": True,
            "analyzers": [
                {
                    "arn": "arn:aws:access-analyzer:us-east-1:123456789012:analyzer/account-analyzer",
                    "name": "account-analyzer",
                    "status": "ACTIVE",
                }
            ],
        }

        # Mock list_findings to raise an exception
        mock_accessanalyzer_client.list_findings = mock.MagicMock(
            side_effect=Exception("API Error")
        )

        # Call the function
        result = await get_access_analyzer_findings("us-east-1", mock_boto3_session, mock_ctx)

        # Verify the result
        assert result["enabled"] is True
        assert "error" in result
        assert "API Error" in result["error"]
        assert len(result["findings"]) == 0
        assert "message" in result
        assert "Error getting IAM Access Analyzer findings" in result["message"]
        mock_ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_get_macie_findings_error(mock_ctx, mock_boto3_session, mock_macie_client):
    """Test the get_macie_findings function when an error occurs."""
    # Set up mock_boto3_session to return mock_macie_client
    mock_boto3_session.client.return_value = mock_macie_client

    # Mock check_macie to return enabled
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.security_services.check_macie"
    ) as mock_check:
        mock_check.return_value = {"enabled": True}

        # Mock list_findings to raise an exception
        mock_macie_client.list_findings = mock.MagicMock(side_effect=Exception("API Error"))

        # Call the function
        result = await get_macie_findings(
            "us-east-1", mock_boto3_session, mock_ctx, max_findings=100, filter_criteria=None
        )

        # Verify the result
        assert result["enabled"] is True
        assert "error" in result
        assert "API Error" in result["error"]
        assert len(result["findings"]) == 0
        assert "message" in result
        assert "Error getting Macie findings" in result["message"]
        mock_ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_get_trusted_advisor_findings_error(
    mock_ctx, mock_boto3_session, mock_support_client
):
    """Test the get_trusted_advisor_findings function when an error occurs."""
    # Set up mock_boto3_session to return mock_support_client
    mock_boto3_session.client.return_value = mock_support_client

    # Mock check_trusted_advisor to return enabled
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.security_services.check_trusted_advisor"
    ) as mock_check:
        mock_check.return_value = {"enabled": True, "support_tier": "Business/Enterprise"}

        # Mock describe_trusted_advisor_checks to raise an exception
        mock_support_client.describe_trusted_advisor_checks = mock.MagicMock(
            side_effect=Exception("API Error")
        )

        # Call the function
        result = await get_trusted_advisor_findings(
            "us-east-1", mock_boto3_session, mock_ctx, max_findings=100
        )

        # Verify the result
        assert result["enabled"] is True
        assert "error" in result
        assert "API Error" in result["error"]
        assert len(result["findings"]) == 0
        assert "message" in result
        assert "Error getting Trusted Advisor findings" in result["message"]
        mock_ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_get_inspector_findings_with_custom_filter_criteria(
    mock_ctx, mock_boto3_session, mock_inspector_client
):
    """Test the get_inspector_findings function with custom filter criteria."""
    # Set up mock_boto3_session to return mock_inspector_client
    mock_boto3_session.client.return_value = mock_inspector_client

    # Mock check_inspector to return enabled
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.security_services.check_inspector"
    ) as mock_check:
        mock_check.return_value = {"enabled": True}

        # Mock list_findings to return findings
        mock_inspector_client.list_findings = mock.MagicMock(
            return_value={
                "findings": [
                    {
                        "findingArn": "finding1",
                        "severity": "CRITICAL",
                        "type": "PACKAGE_VULNERABILITY",
                        "resourceType": "AWS_EC2_INSTANCE",
                    }
                ]
            }
        )

        # Create custom filter criteria
        custom_filter = {
            "severities": [{"comparison": "EQUALS", "value": "CRITICAL"}],
            "resourceTypes": [{"comparison": "EQUALS", "value": "AWS_EC2_INSTANCE"}],
        }

        # Call the function with custom filter_criteria
        result = await get_inspector_findings(
            "us-east-1",
            mock_boto3_session,
            mock_ctx,
            max_findings=50,
            filter_criteria=custom_filter,
        )

        # Verify the result
        assert result["enabled"] is True
        assert len(result["findings"]) == 1
        assert "summary" in result
        assert result["summary"]["total_count"] == 1
        assert "message" in result
        assert "Retrieved 1 Inspector findings" in result["message"]

        # Verify that list_findings was called with the custom filter criteria
        call_args = mock_inspector_client.list_findings.call_args[1]
        assert "filterCriteria" in call_args
        filters = call_args["filterCriteria"]

        # Check that the custom filters were applied
        assert "severities" in filters
        assert filters["severities"][0]["comparison"] == "EQUALS"
        assert filters["severities"][0]["value"] == "CRITICAL"

        assert "resourceTypes" in filters
        assert filters["resourceTypes"][0]["comparison"] == "EQUALS"
        assert filters["resourceTypes"][0]["value"] == "AWS_EC2_INSTANCE"

        # Check that maxResults was set correctly
        assert call_args["maxResults"] == 50


@pytest.mark.asyncio
async def test_get_macie_findings_with_custom_filter_criteria(
    mock_ctx, mock_boto3_session, mock_macie_client
):
    """Test the get_macie_findings function with custom filter criteria."""
    # Set up mock_boto3_session to return mock_macie_client
    mock_boto3_session.client.return_value = mock_macie_client

    # Mock check_macie to return enabled
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.security_services.check_macie"
    ) as mock_check:
        mock_check.return_value = {"enabled": True}

        # Mock list_findings to return findings
        mock_macie_client.list_findings = mock.MagicMock(return_value={"findingIds": ["finding1"]})

        # Mock get_findings to return finding details
        mock_macie_client.get_findings = mock.MagicMock(
            return_value={
                "findings": [
                    {
                        "id": "finding1",
                        "severity": {"score": 8},
                        "type": "SensitiveData:S3Object/Personal",
                        "resourcesAffected": {"s3Bucket": {"name": "bucket1"}},
                    }
                ]
            }
        )

        # Create custom filter criteria
        custom_filter = {
            "criterion": {
                "severity.score": {"gt": 7},
                "type": {"eq": ["SensitiveData:S3Object/Personal"]},
            }
        }

        # Call the function with custom filter_criteria
        result = await get_macie_findings(
            "us-east-1",
            mock_boto3_session,
            mock_ctx,
            max_findings=50,
            filter_criteria=custom_filter,
        )

        # Verify the result
        assert result["enabled"] is True
        assert len(result["findings"]) == 1
        assert "summary" in result
        assert result["summary"]["total_count"] == 1
        assert "message" in result
        assert "Retrieved 1 Macie findings" in result["message"]

        # Verify that list_findings was called with the custom filter criteria
        call_args = mock_macie_client.list_findings.call_args[1]
        assert "findingCriteria" in call_args
        filters = call_args["findingCriteria"]

        # Check that the custom filters were applied
        assert "criterion" in filters
        assert "severity.score" in filters["criterion"]
        assert "gt" in filters["criterion"]["severity.score"]
        assert filters["criterion"]["severity.score"]["gt"] == 7

        assert "type" in filters["criterion"]
        assert "eq" in filters["criterion"]["type"]
        assert "SensitiveData:S3Object/Personal" in filters["criterion"]["type"]["eq"]

        # Check that maxResults was set correctly
        assert call_args["maxResults"] == 50
