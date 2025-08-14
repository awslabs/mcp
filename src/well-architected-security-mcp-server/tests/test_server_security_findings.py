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

"""Tests for the get_security_findings function in server.py."""

from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server.server import (
    context_storage,
    get_security_findings,
)


@pytest.mark.asyncio
async def test_get_security_findings_with_service_enabled_in_context(mock_ctx, mock_boto3_session):
    """Test get_security_findings with service enabled in context."""
    # Set up context storage with service enabled
    context_storage["security_services_us-east-1"] = {
        "service_statuses": {
            "guardduty": {"enabled": True},
        }
    }

    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_guardduty_findings
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_guardduty_findings"
        ) as mock_get_findings:
            # Set up mock return value
            mock_get_findings.return_value = {
                "service": "guardduty",
                "enabled": True,
                "findings": [{"Id": "finding1", "Severity": 8.0}],
                "summary": {"total_count": 1},
                "message": "Retrieved 1 GuardDuty findings",
            }

            # Call the function
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="guardduty",
                max_findings=100,
                check_enabled=True,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "guardduty"
            assert result["enabled"] is True
            assert len(result["findings"]) == 1
            assert "summary" in result
            assert result["summary"]["total_count"] == 1
            assert "message" in result

            # Verify get_guardduty_findings was called
            mock_get_findings.assert_called_once()


@pytest.mark.asyncio
async def test_get_security_findings_with_service_disabled_in_context(
    mock_ctx, mock_boto3_session
):
    """Test get_security_findings with service disabled in context."""
    # Set up context storage with service disabled
    context_storage["security_services_us-east-1"] = {
        "service_statuses": {
            "guardduty": {
                "enabled": False,
                "setup_instructions": "Enable GuardDuty in the console",
            },
        }
    }

    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_guardduty_findings (should not be called)
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_guardduty_findings"
        ) as mock_get_findings:
            # Call the function
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="guardduty",
                max_findings=100,
                check_enabled=True,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "guardduty"
            assert result["enabled"] is False
            assert "message" in result
            assert "not enabled" in result["message"]
            assert "setup_instructions" in result

            # Verify get_guardduty_findings was not called
            mock_get_findings.assert_not_called()


@pytest.mark.asyncio
async def test_get_security_findings_with_service_not_in_context(mock_ctx, mock_boto3_session):
    """Test get_security_findings with service not in context."""
    # Set up context storage without the service
    context_storage["security_services_us-east-1"] = {
        "service_statuses": {
            "securityhub": {"enabled": True},
        }
    }

    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_guardduty_findings
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_guardduty_findings"
        ) as mock_get_findings:
            # Set up mock return value
            mock_get_findings.return_value = {
                "service": "guardduty",
                "enabled": True,
                "findings": [{"Id": "finding1", "Severity": 8.0}],
                "summary": {"total_count": 1},
                "message": "Retrieved 1 GuardDuty findings",
            }

            # Call the function
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="guardduty",
                max_findings=100,
                check_enabled=True,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "guardduty"
            assert result["enabled"] is True
            assert len(result["findings"]) == 1

            # Verify get_guardduty_findings was called
            mock_get_findings.assert_called_once()


@pytest.mark.asyncio
async def test_get_security_findings_with_no_context_storage(mock_ctx, mock_boto3_session):
    """Test get_security_findings with no context storage."""
    # Clear context storage
    context_storage.clear()

    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_guardduty_findings
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_guardduty_findings"
        ) as mock_get_findings:
            # Set up mock return value
            mock_get_findings.return_value = {
                "service": "guardduty",
                "enabled": True,
                "findings": [{"Id": "finding1", "Severity": 8.0}],
                "summary": {"total_count": 1},
                "message": "Retrieved 1 GuardDuty findings",
            }

            # Call the function
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="guardduty",
                max_findings=100,
                check_enabled=True,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "guardduty"
            assert result["enabled"] is True
            assert len(result["findings"]) == 1

            # Verify get_guardduty_findings was called
            mock_get_findings.assert_called_once()


@pytest.mark.asyncio
async def test_get_security_findings_with_check_enabled_false(mock_ctx, mock_boto3_session):
    """Test get_security_findings with check_enabled=False."""
    # Set up context storage with service disabled
    context_storage["security_services_us-east-1"] = {
        "service_statuses": {
            "guardduty": {"enabled": False},
        }
    }

    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_guardduty_findings
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_guardduty_findings"
        ) as mock_get_findings:
            # Set up mock return value
            mock_get_findings.return_value = {
                "service": "guardduty",
                "enabled": True,
                "findings": [{"Id": "finding1", "Severity": 8.0}],
                "summary": {"total_count": 1},
                "message": "Retrieved 1 GuardDuty findings",
            }

            # Call the function with check_enabled=False
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="guardduty",
                max_findings=100,
                check_enabled=False,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "guardduty"
            assert result["enabled"] is True
            assert len(result["findings"]) == 1

            # Verify get_guardduty_findings was called
            mock_get_findings.assert_called_once()


@pytest.mark.asyncio
async def test_get_security_findings_with_securityhub(mock_ctx, mock_boto3_session):
    """Test get_security_findings with securityhub service."""
    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_securityhub_findings
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_securityhub_findings"
        ) as mock_get_findings:
            # Set up mock return value
            mock_get_findings.return_value = {
                "service": "securityhub",
                "enabled": True,
                "findings": [{"Id": "finding1", "Severity": {"Label": "HIGH"}}],
                "summary": {"total_count": 1},
                "message": "Retrieved 1 Security Hub findings",
            }

            # Call the function
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="securityhub",
                max_findings=100,
                check_enabled=False,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "securityhub"
            assert result["enabled"] is True
            assert len(result["findings"]) == 1

            # Verify get_securityhub_findings was called
            mock_get_findings.assert_called_once()


@pytest.mark.asyncio
async def test_get_security_findings_with_inspector(mock_ctx, mock_boto3_session):
    """Test get_security_findings with inspector service."""
    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_inspector_findings
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_inspector_findings"
        ) as mock_get_findings:
            # Set up mock return value
            mock_get_findings.return_value = {
                "service": "inspector",
                "enabled": True,
                "findings": [{"id": "finding1", "severity": "HIGH"}],
                "summary": {"total_count": 1},
                "message": "Retrieved 1 Inspector findings",
            }

            # Call the function
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="inspector",
                max_findings=100,
                check_enabled=False,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "inspector"
            assert result["enabled"] is True
            assert len(result["findings"]) == 1

            # Verify get_inspector_findings was called
            mock_get_findings.assert_called_once()


@pytest.mark.asyncio
async def test_get_security_findings_with_accessanalyzer(mock_ctx, mock_boto3_session):
    """Test get_security_findings with accessanalyzer service."""
    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_access_analyzer_findings
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_access_analyzer_findings"
        ) as mock_get_findings:
            # Set up mock return value
            mock_get_findings.return_value = {
                "service": "accessanalyzer",
                "enabled": True,
                "findings": [{"id": "finding1", "status": "ACTIVE"}],
                "summary": {"total_count": 1},
                "message": "Retrieved 1 Access Analyzer findings",
            }

            # Call the function
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="accessanalyzer",
                max_findings=100,
                check_enabled=False,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "accessanalyzer"
            assert result["enabled"] is True
            assert len(result["findings"]) == 1

            # Verify get_access_analyzer_findings was called
            mock_get_findings.assert_called_once()


@pytest.mark.asyncio
async def test_get_security_findings_with_trustedadvisor(mock_ctx, mock_boto3_session):
    """Test get_security_findings with trustedadvisor service."""
    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_trusted_advisor_findings
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_trusted_advisor_findings"
        ) as mock_get_findings:
            # Set up mock return value
            mock_get_findings.return_value = {
                "service": "trustedadvisor",
                "enabled": True,
                "findings": [{"id": "finding1", "status": "error"}],
                "summary": {"total_count": 1},
                "message": "Retrieved 1 Trusted Advisor findings",
            }

            # Call the function
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="trustedadvisor",
                max_findings=100,
                check_enabled=False,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "trustedadvisor"
            assert result["enabled"] is True
            assert len(result["findings"]) == 1

            # Verify get_trusted_advisor_findings was called with correct parameters
            mock_get_findings.assert_called_once_with(
                "us-east-1",
                mock_boto3_session,
                mock_ctx,
                max_findings=100,
                status_filter=["error", "warning"],
                category_filter="security",
            )


@pytest.mark.asyncio
async def test_get_security_findings_with_trustedadvisor_and_severity_filter(
    mock_ctx, mock_boto3_session
):
    """Test get_security_findings with trustedadvisor service and severity filter."""
    # Mock get_trusted_advisor_findings
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.get_trusted_advisor_findings"
    ) as mock_get_findings:
        # Set up mock return value
        mock_get_findings.return_value = {
            "service": "trustedadvisor",
            "enabled": True,
            "findings": [{"id": "finding1", "status": "error"}],
            "summary": {"total_count": 1},
            "message": "Retrieved 1 Trusted Advisor findings",
        }

        # Call the function with severity_filter
        result = await get_security_findings(
            mock_ctx,
            region="us-east-1",
            service="trustedadvisor",
            max_findings=100,
            severity_filter="ERROR",
            check_enabled=False,
        )

        # Verify the result
        assert result["service"] == "trustedadvisor"
        assert result["enabled"] is True
        assert len(result["findings"]) == 1

        # Verify get_trusted_advisor_findings was called with correct parameters
        mock_get_findings.assert_called_once_with(
            "us-east-1",
            mock_boto3_session,
            mock_ctx,
            max_findings=100,
            status_filter=["error"],
            category_filter="security",
        )


@pytest.mark.asyncio
async def test_get_security_findings_with_macie(mock_ctx, mock_boto3_session):
    """Test get_security_findings with macie service."""
    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_macie_findings
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_macie_findings"
        ) as mock_get_findings:
            # Set up mock return value
            mock_get_findings.return_value = {
                "service": "macie",
                "enabled": True,
                "findings": [{"id": "finding1", "severity": "HIGH"}],
                "summary": {"total_count": 1},
                "message": "Retrieved 1 Macie findings",
            }

            # Call the function
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="macie",
                max_findings=100,
                check_enabled=False,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "macie"
            assert result["enabled"] is True
            assert len(result["findings"]) == 1

            # Verify get_macie_findings was called
            mock_get_findings.assert_called_once()


@pytest.mark.asyncio
async def test_get_security_findings_with_severity_filter_guardduty(mock_ctx, mock_boto3_session):
    """Test get_security_findings with guardduty service and severity filter."""
    # Mock get_guardduty_findings
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.get_guardduty_findings"
    ) as mock_get_findings:
        # Set up mock return value
        mock_get_findings.return_value = {
            "service": "guardduty",
            "enabled": True,
            "findings": [{"Id": "finding1", "Severity": 8.0}],
            "summary": {"total_count": 1},
            "message": "Retrieved 1 GuardDuty findings with severity HIGH",
        }

        # Call the function with severity_filter
        result = await get_security_findings(
            mock_ctx,
            region="us-east-1",
            service="guardduty",
            max_findings=100,
            severity_filter="HIGH",
            check_enabled=False,
        )

        # Verify the result
        assert result["service"] == "guardduty"
        assert result["enabled"] is True
        assert len(result["findings"]) == 1
        assert "HIGH" in result["message"]

        # Verify get_guardduty_findings was called with correct filter criteria
        mock_get_findings.assert_called_once()
        # We can't directly check the filter criteria since we're not mocking the severity mapping
        # but we can verify that mock_get_findings was called


@pytest.mark.asyncio
async def test_get_security_findings_with_unsupported_service(mock_ctx, mock_boto3_session):
    """Test get_security_findings with unsupported service."""
    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Call the function with unsupported service
        with pytest.raises(ValueError) as excinfo:
            await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="unsupported",
                max_findings=100,
                check_enabled=False,
                severity_filter=None,
            )

        # Verify the error message
        assert "Unsupported security service" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_security_findings_with_exception(mock_ctx, mock_boto3_session):
    """Test get_security_findings with exception."""
    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_guardduty_findings to raise an exception
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_guardduty_findings",
            side_effect=Exception("Test error"),
        ):
            # Call the function
            with pytest.raises(Exception) as excinfo:
                await get_security_findings(
                    mock_ctx,
                    region="us-east-1",
                    service="guardduty",
                    max_findings=100,
                    check_enabled=False,
                    severity_filter=None,
                )

            # Verify the error message
            assert "Test error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_security_findings_updates_context_when_service_disabled(
    mock_ctx, mock_boto3_session
):
    """Test get_security_findings updates context when service is disabled."""
    # Set up context storage
    context_storage["security_services_us-east-1"] = {"service_statuses": {}}

    # Mock the severity_filter Field
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.FIELD_SEVERITY_FILTER"
    ) as mock_severity_filter:
        # Set the mock severity_filter to None
        mock_severity_filter.default = None

        # Mock get_guardduty_findings
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.server.get_guardduty_findings"
        ) as mock_get_findings:
            # Set up mock return value indicating service is disabled
            mock_get_findings.return_value = {
                "service": "guardduty",
                "enabled": False,
                "message": "GuardDuty is not enabled in this region",
            }

            # Call the function
            result = await get_security_findings(
                mock_ctx,
                region="us-east-1",
                service="guardduty",
                max_findings=100,
                check_enabled=False,
                severity_filter=None,
            )

            # Verify the result
            assert result["service"] == "guardduty"
            assert result["enabled"] is False

            # Verify context was updated
            assert (
                "guardduty" in context_storage["security_services_us-east-1"]["service_statuses"]
            )
            assert (
                context_storage["security_services_us-east-1"]["service_statuses"]["guardduty"][
                    "enabled"
                ]
                is False
            )
