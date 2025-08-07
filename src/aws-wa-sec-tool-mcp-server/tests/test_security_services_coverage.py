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

"""Additional tests for security_services module to improve coverage."""

from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.aws_wa_sec_tool_mcp_server.util.security_services import (
    check_access_analyzer,
    check_guard_duty,
    check_inspector,
    check_macie,
    check_security_hub,
    check_trusted_advisor,
)


@pytest.mark.asyncio
async def test_check_access_analyzer_with_findings_count_error(mock_ctx, mock_boto3_session):
    """Test Access Analyzer when getting findings count fails."""
    # Create mock Access Analyzer client
    mock_access_analyzer_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_access_analyzer_client

    # Mock list_analyzers to return analyzer with ARN
    mock_access_analyzer_client.list_analyzers.return_value = {
        "analyzers": [
            {
                "name": "test-analyzer",
                "type": "ACCOUNT",
                "status": "ACTIVE",
                "arn": "arn:aws:access-analyzer:us-east-1:123456789012:analyzer/test-analyzer",
            }
        ]
    }

    # Mock list_findings to raise an exception
    mock_access_analyzer_client.list_findings.side_effect = Exception("API Error")

    # Call the function
    result = await check_access_analyzer("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is True
    assert len(result["analyzers"]) == 1
    assert result["analyzers"][0]["findings_count"] == "Unknown"


@pytest.mark.asyncio
async def test_check_access_analyzer_missing_arn(mock_ctx, mock_boto3_session):
    """Test Access Analyzer when analyzer is missing ARN."""
    # Create mock Access Analyzer client
    mock_access_analyzer_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_access_analyzer_client

    # Mock list_analyzers to return analyzer without ARN
    mock_access_analyzer_client.list_analyzers.return_value = {
        "analyzers": [
            {
                "name": "test-analyzer",
                "type": "ACCOUNT",
                "status": "ACTIVE",
                # Missing "arn" field
            }
        ]
    }

    # Call the function
    result = await check_access_analyzer("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is True
    assert len(result["analyzers"]) == 1
    assert result["analyzers"][0]["findings_count"] == "Unknown (No ARN)"


@pytest.mark.asyncio
async def test_check_guard_duty_with_disabled_detector(mock_ctx, mock_boto3_session):
    """Test GuardDuty when detector exists but is disabled."""
    # Create mock GuardDuty client
    mock_guardduty_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_guardduty_client

    # Mock list_detectors to return detector ID
    mock_guardduty_client.list_detectors.return_value = {"DetectorIds": ["test-detector-id"]}

    # Mock get_detector to return disabled detector
    mock_guardduty_client.get_detector.return_value = {
        "Status": "DISABLED",
        "ServiceRole": "arn:aws:iam::123456789012:role/aws-guardduty-role",
        "Tags": {},
    }

    # Call the function
    result = await check_guard_duty("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result - GuardDuty considers a detector as enabled even if disabled
    assert result["enabled"] is True  # The function checks for detector existence, not status


@pytest.mark.asyncio
async def test_check_guard_duty_no_detectors(mock_ctx, mock_boto3_session):
    """Test GuardDuty when no detectors are found."""
    # Create mock GuardDuty client
    mock_guardduty_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_guardduty_client

    # Mock list_detectors to return empty list
    mock_guardduty_client.list_detectors.return_value = {"DetectorIds": []}

    # Call the function
    result = await check_guard_duty("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is False
    assert "not enabled" in result["message"].lower()


@pytest.mark.asyncio
async def test_check_security_hub_invalid_access(mock_ctx, mock_boto3_session):
    """Test Security Hub when access is invalid."""
    # Create mock Security Hub client
    mock_securityhub_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_securityhub_client

    # Mock describe_hub to raise InvalidAccessException
    mock_securityhub_client.describe_hub.side_effect = ClientError(
        {"Error": {"Code": "InvalidAccessException"}}, "DescribeHub"
    )

    # Call the function
    result = await check_security_hub("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is False
    assert "error" in result["message"].lower()


@pytest.mark.asyncio
async def test_check_inspector_no_assessment_targets(mock_ctx, mock_boto3_session):
    """Test Inspector when no assessment targets exist."""
    # Create mock Inspector client
    mock_inspector_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_inspector_client

    # Mock get_status to return empty status
    mock_inspector_client.get_status.return_value = {}

    # Mock list_assessment_targets to return empty list
    mock_inspector_client.list_assessment_targets.return_value = {"assessmentTargetArns": []}

    # Call the function
    result = await check_inspector("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result - Inspector checks get_status first
    assert result["enabled"] is True  # The function checks get_status, not assessment targets


@pytest.mark.asyncio
async def test_check_macie_resource_not_found(mock_ctx, mock_boto3_session):
    """Test Macie when session is not found."""
    # Create mock Macie client
    mock_macie_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_macie_client

    # Mock get_macie_session to raise ResourceNotFoundException
    mock_macie_client.get_macie_session.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException"}}, "GetMacieSession"
    )

    # Call the function
    result = await check_macie("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is False
    assert "error" in result["message"].lower()


@pytest.mark.asyncio
async def test_check_trusted_advisor_subscription_required(mock_ctx, mock_boto3_session):
    """Test Trusted Advisor when subscription is required."""
    # Create mock Support client
    mock_support_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_support_client

    # Mock describe_trusted_advisor_checks to raise SubscriptionRequiredException
    mock_support_client.describe_trusted_advisor_checks.side_effect = ClientError(
        {"Error": {"Code": "SubscriptionRequiredException"}}, "DescribeTrustedAdvisorChecks"
    )

    # Call the function
    result = await check_trusted_advisor("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is False
    assert "error" in result["message"].lower()


@pytest.mark.asyncio
async def test_check_guard_duty_api_error(mock_ctx, mock_boto3_session):
    """Test GuardDuty when API call fails."""
    # Create mock GuardDuty client
    mock_guardduty_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_guardduty_client

    # Mock list_detectors to raise an exception
    mock_guardduty_client.list_detectors.side_effect = Exception("API Error")

    # Call the function
    result = await check_guard_duty("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is False
    assert "error" in result["message"].lower()


@pytest.mark.asyncio
async def test_check_inspector_api_error(mock_ctx, mock_boto3_session):
    """Test Inspector when API call fails."""
    # Create mock Inspector client
    mock_inspector_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_inspector_client

    # Mock all API calls to raise exceptions to ensure Inspector is detected as disabled
    mock_inspector_client.get_status.side_effect = Exception("API Error")
    mock_inspector_client.batch_get_account_status.side_effect = Exception("API Error")
    mock_inspector_client.list_findings.side_effect = Exception("API Error")

    # Call the function
    result = await check_inspector("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is False
    assert "could not be determined" in result["message"]


@pytest.mark.asyncio
async def test_check_macie_api_error(mock_ctx, mock_boto3_session):
    """Test Macie when API call fails."""
    # Create mock Macie client
    mock_macie_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_macie_client

    # Mock get_macie_session to raise a generic exception
    mock_macie_client.get_macie_session.side_effect = Exception("API Error")

    # Call the function
    result = await check_macie("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is False
    assert "error" in result["message"].lower()


@pytest.mark.asyncio
async def test_check_security_hub_api_error(mock_ctx, mock_boto3_session):
    """Test Security Hub when API call fails."""
    # Create mock Security Hub client
    mock_securityhub_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_securityhub_client

    # Mock describe_hub to raise a generic exception
    mock_securityhub_client.describe_hub.side_effect = Exception("API Error")

    # Call the function
    result = await check_security_hub("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is False
    assert "error" in result["message"].lower()


@pytest.mark.asyncio
async def test_check_trusted_advisor_api_error(mock_ctx, mock_boto3_session):
    """Test Trusted Advisor when API call fails."""
    # Create mock Support client
    mock_support_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_support_client

    # Mock describe_trusted_advisor_checks to raise a generic exception
    mock_support_client.describe_trusted_advisor_checks.side_effect = Exception("API Error")

    # Call the function
    result = await check_trusted_advisor("us-east-1", mock_boto3_session, mock_ctx)

    # Verify the result
    assert result["enabled"] is False
    assert "error" in result["message"].lower()
