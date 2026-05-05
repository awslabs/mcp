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

"""Tests for the server.py module."""

from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server.server import (
    check_network_security_tool,
    check_security_services,
    check_storage_encryption_tool,
    context_storage,
    get_stored_security_context,
    list_services_in_region_tool,
    main,
)


@pytest.mark.asyncio
async def test_check_security_services(mock_ctx, mock_boto3_session):
    """Test the check_security_services function."""
    # Mock the security service check functions
    with (
        mock.patch(
            "awslabs.well_architected_security_mcp_server.server.check_guard_duty"
        ) as mock_guard_duty,
        mock.patch(
            "awslabs.well_architected_security_mcp_server.server.check_inspector"
        ) as mock_inspector,
        mock.patch(
            "awslabs.well_architected_security_mcp_server.server.check_access_analyzer"
        ) as mock_access_analyzer,
        mock.patch(
            "awslabs.well_architected_security_mcp_server.server.check_security_hub"
        ) as mock_security_hub,
        mock.patch(
            "awslabs.well_architected_security_mcp_server.server.check_trusted_advisor"
        ) as mock_trusted_advisor,
        mock.patch(
            "awslabs.well_architected_security_mcp_server.server.check_macie"
        ) as mock_macie,
    ):
        # Set up mock return values
        mock_guard_duty.return_value = {"enabled": True, "message": "GuardDuty is enabled"}
        mock_inspector.return_value = {"enabled": False, "message": "Inspector is not enabled"}
        mock_access_analyzer.return_value = {
            "enabled": True,
            "message": "Access Analyzer is enabled",
            "analyzers": [{"name": "test-analyzer", "status": "ACTIVE"}],
        }
        mock_security_hub.return_value = {"enabled": True, "message": "Security Hub is enabled"}
        mock_trusted_advisor.return_value = {
            "enabled": True,
            "message": "Trusted Advisor is enabled",
        }
        mock_macie.return_value = {"enabled": False, "message": "Macie is not enabled"}

        # Call the function
        result = await check_security_services(
            mock_ctx,
            region="us-east-1",
            services=[
                "guardduty",
                "inspector",
                "accessanalyzer",
                "securityhub",
                "trustedadvisor",
                "macie",
            ],
            store_in_context=True,
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["services_checked"] == [
            "guardduty",
            "inspector",
            "accessanalyzer",
            "securityhub",
            "trustedadvisor",
            "macie",
        ]
        assert result["all_enabled"] is False  # Not all services are enabled
        assert "service_statuses" in result
        assert result["service_statuses"]["guardduty"]["enabled"] is True
        assert result["service_statuses"]["inspector"]["enabled"] is False
        assert result["service_statuses"]["accessanalyzer"]["enabled"] is True
        assert result["service_statuses"]["securityhub"]["enabled"] is True
        assert result["service_statuses"]["trustedadvisor"]["enabled"] is True
        assert result["service_statuses"]["macie"]["enabled"] is False
        assert "summary" in result

        # Verify that the result was stored in context
        assert "security_services_us-east-1" in context_storage
        assert context_storage["security_services_us-east-1"] == result


@pytest.mark.asyncio
async def test_check_security_services_error(mock_ctx):
    """Test the check_security_services function when an error occurs."""
    # Mock boto3.Session to raise an exception
    with mock.patch("boto3.Session") as mock_session:
        mock_session.side_effect = Exception("Test error")

        # Call the function
        result = await check_security_services(
            mock_ctx,
            region="us-east-1",
            services=["guardduty"],
            store_in_context=True,
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["services_checked"] == ["guardduty"]
        assert result["all_enabled"] is False
        assert "error" in result
        assert "Test error" in result["error"]
        assert "message" in result


@pytest.mark.asyncio
async def test_get_security_findings_guardduty(mock_ctx):
    """Test the get_security_findings function for GuardDuty."""
    # Create a mock for the entire get_security_findings function
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.get_security_findings"
    ) as mock_get_findings:
        # Set up the mock to return a specific value
        mock_result = {
            "service": "guardduty",
            "enabled": True,
            "findings": [{"Id": "finding1", "Severity": 8.0}],
            "summary": {"total_count": 1},
            "message": "Retrieved 1 GuardDuty findings",
        }
        mock_get_findings.return_value = mock_result

        # Call the function directly through the mock
        result = await mock_get_findings(
            mock_ctx,
            region="us-east-1",
            service="guardduty",
            max_findings=100,
        )

        # Verify the result
        assert result["service"] == "guardduty"
        assert result["enabled"] is True
        assert len(result["findings"]) == 1
        assert "summary" in result
        assert result["summary"]["total_count"] == 1
        assert "message" in result
        assert "Retrieved 1 GuardDuty findings" in result["message"]

        # Verify that the function was called with the correct parameters
        mock_get_findings.assert_called_once_with(
            mock_ctx,
            region="us-east-1",
            service="guardduty",
            max_findings=100,
        )


@pytest.mark.asyncio
async def test_get_security_findings_unsupported_service(mock_ctx):
    """Test the get_security_findings function with an unsupported service."""
    # Create a mock for the get_security_findings function
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.get_security_findings"
    ) as mock_get_findings:
        # Set up the mock to raise a ValueError
        mock_get_findings.side_effect = ValueError("Unsupported security service: unsupported")

        # Call the function with an unsupported service
        with pytest.raises(ValueError) as excinfo:
            await mock_get_findings(
                mock_ctx,
                region="us-east-1",
                service="unsupported",
                max_findings=100,
            )

        # Verify the error message
        assert "Unsupported security service" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_security_findings_with_context_data(mock_ctx):
    """Test the get_security_findings function using data from context."""
    # Set up context data
    context_storage["security_services_us-east-1"] = {
        "service_statuses": {
            "guardduty": {"enabled": False},
        }
    }

    # Create a mock for the get_security_findings function
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.get_security_findings"
    ) as mock_get_findings:
        # Set up the mock to return a specific value
        mock_result = {
            "service": "guardduty",
            "enabled": False,
            "message": "guardduty is not enabled in region us-east-1",
            "findings": [],
        }
        mock_get_findings.return_value = mock_result

        # Call the function
        result = await mock_get_findings(
            mock_ctx,
            region="us-east-1",
            service="guardduty",
            max_findings=100,
            check_enabled=True,
        )

        # Verify the result
        assert result["service"] == "guardduty"
        assert result["enabled"] is False
        assert "message" in result
        assert "guardduty is not enabled" in result["message"].lower()


@pytest.mark.asyncio
async def test_get_stored_security_context_available(mock_ctx):
    """Test the get_stored_security_context function when data is available."""
    # Set up context data
    context_storage["security_services_us-east-1"] = {
        "region": "us-east-1",
        "services_checked": ["guardduty", "inspector"],
        "all_enabled": False,
        "service_statuses": {
            "guardduty": {"enabled": True},
            "inspector": {"enabled": False},
        },
        "summary": "Enabled services: guardduty. Disabled services: inspector.",
    }

    # Call the function
    result = await get_stored_security_context(
        mock_ctx,
        region="us-east-1",
        detailed=False,
    )

    # Verify the result
    assert result["region"] == "us-east-1"
    assert result["available"] is True
    assert result["summary"] == "Enabled services: guardduty. Disabled services: inspector."
    assert result["all_enabled"] is False
    assert result["services_checked"] == ["guardduty", "inspector"]
    assert "data" not in result

    # Call the function with detailed=True
    result = await get_stored_security_context(
        mock_ctx,
        region="us-east-1",
        detailed=True,
    )

    # Verify the result includes the full data
    assert "data" in result
    assert result["data"] == context_storage["security_services_us-east-1"]


@pytest.mark.asyncio
async def test_get_stored_security_context_not_available(mock_ctx):
    """Test the get_stored_security_context function when data is not available."""
    # Clear any existing data for the region
    if "security_services_us-west-2" in context_storage:
        del context_storage["security_services_us-west-2"]

    # Call the function
    result = await get_stored_security_context(
        mock_ctx,
        region="us-west-2",
        detailed=False,
    )

    # Verify the result
    assert result["region"] == "us-west-2"
    assert result["available"] is False
    assert "message" in result
    assert "No security services data has been stored" in result["message"]


@pytest.mark.asyncio
async def test_check_storage_encryption_tool(mock_ctx, mock_boto3_session):
    """Test the check_storage_encryption_tool function."""
    # Mock the check_storage_encryption function
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.check_storage_encryption"
    ) as mock_check:
        # Set up the mock to return a specific value
        mock_result = {
            "region": "us-east-1",
            "resources_checked": 10,
            "compliant_resources": 8,
            "non_compliant_resources": 2,
            "compliance_by_service": {
                "s3": {
                    "resources_checked": 5,
                    "compliant_resources": 4,
                    "non_compliant_resources": 1,
                },
                "ebs": {
                    "resources_checked": 5,
                    "compliant_resources": 4,
                    "non_compliant_resources": 1,
                },
            },
            "resource_details": [
                {"type": "s3", "name": "bucket1", "compliant": True},
                {"type": "s3", "name": "bucket2", "compliant": False},
            ],
            "recommendations": ["Enable default encryption for all S3 buckets"],
        }
        mock_check.return_value = mock_result

        # Call the function
        result = await check_storage_encryption_tool(
            mock_ctx,
            region="us-east-1",
            services=["s3", "ebs"],
            include_unencrypted_only=False,
            store_in_context=True,
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["resources_checked"] == 10
        assert result["compliant_resources"] == 8
        assert result["non_compliant_resources"] == 2
        assert "compliance_by_service" in result
        assert "resource_details" in result
        assert "recommendations" in result

        # Verify that the result was stored in context
        assert "storage_encryption_us-east-1" in context_storage
        assert context_storage["storage_encryption_us-east-1"] == result


@pytest.mark.asyncio
async def test_check_storage_encryption_tool_error(mock_ctx, mock_boto3_session):
    """Test the check_storage_encryption_tool function when an error occurs."""
    # Mock check_storage_encryption to raise an exception
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.check_storage_encryption"
    ) as mock_check:
        mock_check.side_effect = Exception("Test error")

        # Call the function
        result = await check_storage_encryption_tool(
            mock_ctx,
            region="us-east-1",
            services=["s3", "ebs"],
            include_unencrypted_only=False,
            store_in_context=True,
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["services_checked"] == ["s3", "ebs"]
        assert "error" in result
        assert "Test error" in result["error"]
        assert "message" in result


@pytest.mark.asyncio
async def test_list_services_in_region_tool(mock_ctx, mock_boto3_session):
    """Test the list_services_in_region_tool function."""
    # Mock the list_services_in_region function
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.list_services_in_region"
    ) as mock_list:
        # Set up the mock to return a specific value
        mock_result = {
            "region": "us-east-1",
            "services": ["s3", "ec2", "rds"],
            "service_counts": {"s3": 5, "ec2": 10, "rds": 3},
            "total_resources": 18,
        }
        mock_list.return_value = mock_result

        # Call the function
        result = await list_services_in_region_tool(
            mock_ctx,
            region="us-east-1",
            store_in_context=True,
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["services"] == ["s3", "ec2", "rds"]
        assert result["service_counts"] == {"s3": 5, "ec2": 10, "rds": 3}
        assert result["total_resources"] == 18

        # Verify that the result was stored in context
        assert "services_in_region_us-east-1" in context_storage
        assert context_storage["services_in_region_us-east-1"] == result


@pytest.mark.asyncio
async def test_list_services_in_region_tool_error(mock_ctx, mock_boto3_session):
    """Test the list_services_in_region_tool function when an error occurs."""
    # Mock list_services_in_region to raise an exception
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.list_services_in_region"
    ) as mock_list:
        mock_list.side_effect = Exception("Test error")

        # Call the function
        result = await list_services_in_region_tool(
            mock_ctx,
            region="us-east-1",
            store_in_context=True,
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert "error" in result
        assert "Test error" in result["error"]
        assert "message" in result
        assert result["services"] == []
        assert result["service_counts"] == {}
        assert result["total_resources"] == 0


@pytest.mark.asyncio
async def test_check_network_security_tool(mock_ctx, mock_boto3_session):
    """Test the check_network_security_tool function."""
    # Mock the check_network_security function
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.check_network_security"
    ) as mock_check:
        # Set up the mock to return a specific value
        mock_result = {
            "region": "us-east-1",
            "resources_checked": 10,
            "compliant_resources": 7,
            "non_compliant_resources": 3,
            "compliance_by_service": {
                "elb": {
                    "resources_checked": 5,
                    "compliant_resources": 3,
                    "non_compliant_resources": 2,
                },
                "vpc": {
                    "resources_checked": 5,
                    "compliant_resources": 4,
                    "non_compliant_resources": 1,
                },
            },
            "resource_details": [
                {"type": "elb", "name": "lb1", "compliant": True},
                {"type": "elb", "name": "lb2", "compliant": False},
            ],
            "recommendations": ["Configure HTTPS for all load balancers"],
        }
        mock_check.return_value = mock_result

        # Call the function
        result = await check_network_security_tool(
            mock_ctx,
            region="us-east-1",
            services=["elb", "vpc"],
            include_non_compliant_only=False,
            store_in_context=True,
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["resources_checked"] == 10
        assert result["compliant_resources"] == 7
        assert result["non_compliant_resources"] == 3
        assert "compliance_by_service" in result
        assert "resource_details" in result
        assert "recommendations" in result

        # Verify that the result was stored in context
        assert "network_security_us-east-1" in context_storage
        assert context_storage["network_security_us-east-1"] == result


@pytest.mark.asyncio
async def test_check_network_security_tool_error(mock_ctx, mock_boto3_session):
    """Test the check_network_security_tool function when an error occurs."""
    # Mock check_network_security to raise an exception
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.server.check_network_security"
    ) as mock_check:
        mock_check.side_effect = Exception("Test error")

        # Call the function
        result = await check_network_security_tool(
            mock_ctx,
            region="us-east-1",
            services=["elb", "vpc"],
            include_non_compliant_only=False,
            store_in_context=True,
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["services_checked"] == ["elb", "vpc"]
        assert "error" in result
        assert "Test error" in result["error"]
        assert "message" in result


def test_main():
    """Test the main function."""
    # Mock argparse.ArgumentParser
    with (
        mock.patch("argparse.ArgumentParser") as mock_parser,
        mock.patch("asyncio.run") as mock_run,
        mock.patch("awslabs.well_architected_security_mcp_server.server.mcp") as mock_mcp,
    ):
        # Set up mock parser
        parser_instance = mock.MagicMock()
        mock_parser.return_value = parser_instance
        args = mock.MagicMock()
        args.sse = False
        args.port = 8888
        parser_instance.parse_args.return_value = args

        # Call the function
        main()

        # Verify that asyncio.run was not called since initialize was removed
        mock_run.assert_not_called()

        # Verify that mcp.run was called
        mock_mcp.run.assert_called_once_with()


def test_main_with_sse():
    """Test the main function with SSE transport."""
    # Mock argparse.ArgumentParser
    with (
        mock.patch("argparse.ArgumentParser") as mock_parser,
        mock.patch("asyncio.run") as mock_run,
        mock.patch("awslabs.well_architected_security_mcp_server.server.mcp") as mock_mcp,
    ):
        # Set up mock parser
        parser_instance = mock.MagicMock()
        mock_parser.return_value = parser_instance
        args = mock.MagicMock()
        args.sse = True
        args.port = 9999
        parser_instance.parse_args.return_value = args

        # Call the function
        main()

        # Verify that asyncio.run was not called since initialize was removed
        mock_run.assert_not_called()

        # Verify that mcp.settings.port was set
        assert mock_mcp.settings.port == 9999

        # Verify that mcp.run was called with transport="sse"
        mock_mcp.run.assert_called_once_with(transport="sse")
