"""Tests for AWS Security MCP Server."""

from unittest.mock import MagicMock, patch

from mcp.types import TextContent

from awslabs.aws_security_mcp_server.models import ResponseStatus, ServiceName
from awslabs.aws_security_mcp_server.server import (
    health_check,
    list_guardduty_findings,
    list_securityhub_findings,
)


class TestHealthCheck:
    """Test health check functionality."""

    @patch("awslabs.aws_security_mcp_server.server.get_boto3_session")
    async def test_health_check_success(self, mock_session):
        """Test successful health check."""
        # Mock AWS STS response
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:user/test-user",
        }
        mock_session.return_value.client.return_value = mock_sts

        result = await health_check()

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

        # Parse JSON response
        import json

        response_data = json.loads(result[0].text)

        assert response_data["status"] == ResponseStatus.SUCCESS
        assert response_data["service"] == ServiceName.AWS_STS
        assert response_data["data"]["aws_account"] == "123456789012"

    @patch("awslabs.aws_security_mcp_server.server.get_boto3_session")
    async def test_health_check_failure(self, mock_session):
        """Test health check failure."""
        # Mock AWS STS exception
        mock_session.return_value.client.side_effect = Exception("AWS connection failed")

        result = await health_check()

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

        # Parse JSON response
        import json

        response_data = json.loads(result[0].text)

        assert response_data["status"] == ResponseStatus.ERROR
        assert response_data["service"] == ServiceName.AWS_STS
        assert "AWS connection failed" in response_data["data"]["message"]


class TestGuardDutyFindings:
    """Test GuardDuty findings functionality."""

    @patch("awslabs.aws_security_mcp_server.server.get_boto3_session")
    async def test_list_guardduty_findings_no_detectors(self, mock_session):
        """Test GuardDuty with no detectors."""
        # Mock GuardDuty response with no detectors
        mock_guardduty = MagicMock()
        mock_guardduty.list_detectors.return_value = {"DetectorIds": []}
        mock_session.return_value.client.return_value = mock_guardduty

        result = await list_guardduty_findings()

        assert len(result) == 1

        # Parse JSON response
        import json

        response_data = json.loads(result[0].text)

        assert response_data["status"] == ResponseStatus.SUCCESS
        assert response_data["service"] == ServiceName.GUARDDUTY
        assert response_data["data"]["total_count"] == 0
        assert "No GuardDuty detectors found" in response_data["data"]["message"]

    @patch("awslabs.aws_security_mcp_server.server.get_boto3_session")
    async def test_list_guardduty_findings_with_findings(self, mock_session):
        """Test GuardDuty with findings."""
        # Mock GuardDuty responses
        mock_guardduty = MagicMock()
        mock_guardduty.list_detectors.return_value = {"DetectorIds": ["detector-123"]}
        mock_guardduty.list_findings.return_value = {"FindingIds": ["finding-123"]}
        mock_guardduty.get_findings.return_value = {
            "Findings": [
                {"Id": "finding-123", "Type": "Backdoor:EC2/C&CActivity.B!DNS", "Severity": 8.5}
            ]
        }
        mock_session.return_value.client.return_value = mock_guardduty

        result = await list_guardduty_findings()

        assert len(result) == 1

        # Parse JSON response
        import json

        response_data = json.loads(result[0].text)

        assert response_data["status"] == ResponseStatus.SUCCESS
        assert response_data["service"] == ServiceName.GUARDDUTY
        assert response_data["data"]["total_count"] == 1
        assert response_data["data"]["findings"][0]["id"] == "finding-123"


class TestSecurityHubFindings:
    """Test Security Hub findings functionality."""

    @patch("awslabs.aws_security_mcp_server.server.get_boto3_session")
    async def test_list_securityhub_findings_success(self, mock_session):
        """Test Security Hub findings success."""
        # Mock Security Hub response
        mock_securityhub = MagicMock()
        mock_securityhub.get_findings.return_value = {
            "Findings": [
                {
                    "Title": "EC2 instance has unrestricted access",
                    "Severity": {"Label": "HIGH"},
                    "Resources": [{"Id": "arn:aws:ec2:us-east-1:123456789012:instance/i-123"}],
                    "Workflow": {"Status": "NEW"},
                }
            ]
        }
        mock_session.return_value.client.return_value = mock_securityhub

        result = await list_securityhub_findings()

        assert len(result) == 1

        # Parse JSON response
        import json

        response_data = json.loads(result[0].text)

        assert response_data["status"] == ResponseStatus.SUCCESS
        assert response_data["service"] == ServiceName.SECURITY_HUB
        assert response_data["data"]["total_count"] == 1
        assert (
            response_data["data"]["findings"][0]["title"] == "EC2 instance has unrestricted access"
        )

    @patch("awslabs.aws_security_mcp_server.server.get_boto3_session")
    async def test_list_securityhub_findings_failure(self, mock_session):
        """Test Security Hub findings failure."""
        # Mock Security Hub exception
        mock_session.return_value.client.side_effect = Exception("Security Hub not enabled")

        result = await list_securityhub_findings()

        assert len(result) == 1

        # Parse JSON response
        import json

        response_data = json.loads(result[0].text)

        assert response_data["status"] == ResponseStatus.ERROR
        assert response_data["service"] == ServiceName.SECURITY_HUB
        assert "Security Hub not enabled" in response_data["data"]["message"]
