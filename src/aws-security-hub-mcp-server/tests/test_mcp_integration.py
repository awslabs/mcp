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
"""Integration tests for AWS Security Hub MCP Server."""

from unittest.mock import patch

import pytest

from awslabs.aws_security_hub_mcp_server.server import mcp


def extract_mcp_result(response):
    """Extract the actual result from MCP response tuple."""
    if isinstance(response, tuple) and len(response) == 2:
        content, result = response
        # For report tools, the result is in the first element (content) as JSON text
        if isinstance(content, list) and len(content) > 0:
            try:
                import json

                text_content = content[0].text if hasattr(content[0], "text") else str(content[0])
                return json.loads(text_content)
            except (json.JSONDecodeError, AttributeError, IndexError):
                pass
        # For other tools, the result is in the second element
        return result
    # If it's a list with TextContent, extract JSON from it
    elif isinstance(response, list) and len(response) > 0:
        try:
            import json

            text_content = response[0].text if hasattr(response[0], "text") else str(response[0])
            return json.loads(text_content)
        except (json.JSONDecodeError, AttributeError, IndexError):
            pass
    # If it's not a tuple, return as-is
    return response


@pytest.mark.integration
class TestSecurityHubMCPIntegration:
    """Integration tests for Security Hub MCP Server."""

    @pytest.mark.asyncio
    async def test_mcp_server_tools_available(self):
        """Test that MCP server has all expected tools available."""
        # Test list_tools
        response = await mcp.list_tools()

        tool_names = [tool.name for tool in response]
        expected_tools = [
            "get-security-findings",
            "get-finding-statistics",
            "get-security-score",
            "get-enabled-standards",
            "list-security-control-definitions",
            "get-finding-history",
            "describe-standards-controls",
            "generate-security-report",
            "generate-compliance-report",
            "generate-security-trends-report",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool {expected_tool} not found in available tools"

    @pytest.mark.asyncio
    async def test_get_security_findings_tool_integration(self):
        """Test the get-security-findings tool through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock the Security Hub client response
            mock_finding = {
                "Id": "test-finding-1",
                "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                "GeneratorId": "test-generator",
                "AwsAccountId": "123456789012",
                "Region": "us-east-1",
                "Title": "Test Security Finding",
                "Description": "This is a test security finding",
                "Severity": {"Label": "HIGH"},
                "Workflow": {"Status": "NEW"},
                "RecordState": "ACTIVE",
                "CreatedAt": "2024-01-01T00:00:00Z",
                "UpdatedAt": "2024-01-01T00:00:00Z",
                "Resources": [{"Type": "AwsEc2Instance", "Id": "i-1234567890abcdef0"}],
                "Compliance": {"Status": "FAILED"},
            }
            mock_client.return_value.get_findings.return_value = {"Findings": [mock_finding]}

            # Test the tool directly
            response = await mcp.call_tool("get-security-findings", {"max_results": 5, "days_back": 7})

            assert response is not None
            # Just verify we got a response - don't check specific format
            actual_result = extract_mcp_result(response)
            assert actual_result is not None

    @pytest.mark.asyncio
    async def test_get_finding_statistics_tool_integration(self):
        """Test the get-finding-statistics tool through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_finding = {
                "Id": "test-finding-1",
                "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                "GeneratorId": "test-generator",
                "AwsAccountId": "123456789012",
                "Region": "us-east-1",
                "Title": "Test Security Finding",
                "Description": "This is a test security finding",
                "Severity": {"Label": "HIGH"},
                "Workflow": {"Status": "NEW"},
                "RecordState": "ACTIVE",
                "CreatedAt": "2024-01-01T00:00:00Z",
                "UpdatedAt": "2024-01-01T00:00:00Z",
                "Resources": [{"Type": "AwsEc2Instance"}],
            }
            mock_client.return_value.get_findings.return_value = {"Findings": [mock_finding]}

            response = await mcp.call_tool("get-finding-statistics", {"group_by": "SeverityLabel", "days_back": 30})

            assert response is not None
            actual_result = extract_mcp_result(response)
            assert actual_result is not None

    @pytest.mark.asyncio
    async def test_get_security_score_tool_integration(self):
        """Test the get-security-score tool through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": []}

            response = await mcp.call_tool("get-security-score", {})

            assert response is not None
            actual_result = extract_mcp_result(response)
            # Response should be a SecurityScore object
            assert actual_result["current_score"] == 100.0  # No findings = perfect score
            assert actual_result["max_score"] == 100.0
            assert actual_result["control_findings_count"] == 0

    @pytest.mark.asyncio
    async def test_get_enabled_standards_tool_integration(self):
        """Test the get-enabled-standards tool through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_standards = [
                {
                    "StandardsSubscriptionArn": "arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-standard/v/1.0.0",
                    "StandardsArn": "arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0",
                    "StandardsInput": {},
                    "StandardsStatus": "READY",
                }
            ]
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": mock_standards}
            mock_client.return_value.describe_standards.return_value = {
                "Standards": [
                    {
                        "StandardsArn": "arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0",
                        "Name": "AWS Foundational Security Standard",
                        "Description": "AWS Foundational Security Standard",
                    }
                ]
            }

            response = await mcp.call_tool("get-enabled-standards", {})

            assert response is not None
            actual_result = extract_mcp_result(response)
            assert actual_result is not None

    @pytest.mark.asyncio
    async def test_list_security_control_definitions_tool_integration(self):
        """Test the list-security-control-definitions tool through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_controls = [
                {
                    "SecurityControlId": "S3.1",
                    "SecurityControlArn": "arn:aws:securityhub:us-east-1:123456789012:security-control/S3.1",
                    "Title": "S3 buckets should have public access blocked",
                    "Description": "This control checks whether S3 buckets have public access blocked.",
                    "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/S3.1/remediation",
                    "SeverityRating": "HIGH",
                    "CurrentRegionAvailability": "AVAILABLE",
                }
            ]
            mock_client.return_value.list_security_control_definitions.return_value = {
                "SecurityControlDefinitions": mock_controls
            }

            response = await mcp.call_tool("list-security-control-definitions", {})

            assert response is not None
            actual_result = extract_mcp_result(response)
            assert actual_result is not None

    @pytest.mark.asyncio
    async def test_get_finding_history_tool_integration(self):
        """Test the get-finding-history tool through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            from datetime import datetime

            mock_history = [
                {
                    "FindingIdentifier": {
                        "Id": "arn:aws:securityhub:us-east-1:123456789012:finding/test-finding-1",
                        "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                    },
                    "UpdateTime": datetime(2024, 1, 1, 0, 0, 0),
                    "FindingCreated": True,
                    "UpdateSource": {
                        "Type": "BATCH_UPDATE_FINDINGS",
                        "Identity": "arn:aws:iam::123456789012:user/test-user",
                    },
                    "Updates": [
                        {
                            "UpdatedField": "Workflow/Status",
                            "OldValue": "NEW",
                            "NewValue": "RESOLVED",
                        }
                    ],
                }
            ]
            mock_client.return_value.get_finding_history.return_value = {"Records": mock_history}

            response = await mcp.call_tool("get-finding-history", {"finding_identifier": "test-finding-id"})

            assert response is not None
            actual_result = extract_mcp_result(response)
            assert actual_result is not None

    @pytest.mark.asyncio
    async def test_describe_standards_controls_tool_integration(self):
        """Test the describe-standards-controls tool through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            from datetime import datetime

            mock_controls = [
                {
                    "StandardsControlArn": "arn:aws:securityhub:us-east-1:123456789012:control/aws-foundational-security-standard/v/1.0.0/S3.1",
                    "ControlStatus": "ENABLED",
                    "DisabledReason": None,
                    "ControlStatusUpdatedAt": datetime(2024, 1, 1, 0, 0, 0),
                    "ControlId": "S3.1",
                    "Title": "S3 buckets should have public access blocked",
                    "Description": "This control checks whether S3 buckets have public access blocked.",
                    "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/S3.1/remediation",
                    "SeverityRating": "HIGH",
                    "RelatedRequirements": ["NIST.800-53.r5 AC-3", "NIST.800-53.r5 AC-6"],
                }
            ]
            mock_client.return_value.describe_standards_controls.return_value = {"Controls": mock_controls}

            response = await mcp.call_tool(
                "describe-standards-controls",
                {
                    "standards_subscription_arn": "arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-standard/v/1.0.0"
                },
            )

            assert response is not None
            actual_result = extract_mcp_result(response)
            assert actual_result is not None

    @pytest.mark.asyncio
    async def test_generate_security_report_tool_integration(self):
        """Test the generate-security-report tool through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_finding = {
                "Id": "test-finding-1",
                "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                "GeneratorId": "test-generator",
                "AwsAccountId": "123456789012",
                "Region": "us-east-1",
                "Title": "Test Security Finding",
                "Description": "This is a test security finding",
                "Severity": {"Label": "HIGH"},
                "Workflow": {"Status": "NEW"},
                "RecordState": "ACTIVE",
                "CreatedAt": "2024-01-01T00:00:00Z",
                "UpdatedAt": "2024-01-01T00:00:00Z",
                "Resources": [{"Type": "AwsEc2Instance"}],
                "Compliance": {"Status": "FAILED"},
            }
            mock_client.return_value.get_findings.return_value = {"Findings": [mock_finding]}
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": []}
            mock_client.return_value.describe_standards.return_value = {"Standards": []}

            response = await mcp.call_tool("generate-security-report", {})

            assert response is not None
            actual_result = extract_mcp_result(response)
            # Just verify we got a result - the format varies
            assert actual_result is not None

    @pytest.mark.asyncio
    async def test_generate_compliance_report_tool_integration(self):
        """Test the generate-compliance-report tool through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_finding = {
                "Id": "test-finding-1",
                "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                "GeneratorId": "test-generator",
                "AwsAccountId": "123456789012",
                "Region": "us-east-1",
                "Title": "Test Security Finding",
                "Description": "This is a test security finding",
                "Severity": {"Label": "HIGH"},
                "Workflow": {"Status": "NEW"},
                "RecordState": "ACTIVE",
                "CreatedAt": "2024-01-01T00:00:00Z",
                "UpdatedAt": "2024-01-01T00:00:00Z",
                "Resources": [{"Type": "AwsEc2Instance"}],
                "Compliance": {"Status": "FAILED"},
            }
            mock_client.return_value.get_findings.return_value = {"Findings": [mock_finding]}
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": []}
            mock_client.return_value.describe_standards.return_value = {"Standards": []}

            response = await mcp.call_tool("generate-compliance-report", {})

            assert response is not None
            actual_result = extract_mcp_result(response)
            # Response should be a dictionary with compliance report structure
            assert "report_metadata" in actual_result
            assert "executive_summary" in actual_result
            assert "standards_compliance" in actual_result
            assert actual_result["executive_summary"]["total_compliance_findings"] == 1

    @pytest.mark.asyncio
    async def test_generate_security_trends_report_tool_integration(self):
        """Test the generate-security-trends-report tool through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_finding = {
                "Id": "test-finding-1",
                "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                "GeneratorId": "test-generator",
                "AwsAccountId": "123456789012",
                "Region": "us-east-1",
                "Title": "Test Security Finding",
                "Description": "This is a test security finding",
                "Severity": {"Label": "HIGH"},
                "Workflow": {"Status": "NEW"},
                "RecordState": "ACTIVE",
                "CreatedAt": "2024-01-01T00:00:00Z",
                "UpdatedAt": "2024-01-01T00:00:00Z",
                "Resources": [{"Type": "AwsEc2Instance"}],
            }
            mock_client.return_value.get_findings.return_value = {"Findings": [mock_finding]}
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": []}
            mock_client.return_value.describe_standards.return_value = {"Standards": []}

            response = await mcp.call_tool("generate-security-trends-report", {})

            assert response is not None
            actual_result = extract_mcp_result(response)
            # Response should be a dictionary with trends report structure
            assert "report_metadata" in actual_result
            assert "executive_summary" in actual_result
            assert "historical_data_points" in actual_result
            assert "trend_analysis" in actual_result

    @pytest.mark.asyncio
    async def test_tool_error_handling_integration(self):
        """Test error handling through MCP interface."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            from botocore.exceptions import ClientError

            mock_client.return_value.get_findings.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetFindings"
            )

            # Should handle the error gracefully and raise an exception
            with pytest.raises(Exception, match="Security Hub API error"):
                await mcp.call_tool("get-security-findings", {})

    @pytest.mark.asyncio
    async def test_invalid_tool_name_integration(self):
        """Test calling an invalid tool name through MCP interface."""
        # Should raise an error for invalid tool name
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError):
            await mcp.call_tool("invalid-tool-name", {})

    @pytest.mark.asyncio
    async def test_tool_input_validation_integration(self):
        """Test input validation through MCP interface."""
        # Test with invalid arguments that should be caught by input validation
        # Should handle validation errors gracefully
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError):
            await mcp.call_tool("get-security-findings", {"max_results": "invalid"})

    @pytest.mark.asyncio
    async def test_all_tools_with_empty_responses(self):
        """Test all tools with empty AWS responses to increase coverage."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock empty responses for all AWS calls
            mock_client.return_value.get_findings.return_value = {"Findings": []}
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": []}
            mock_client.return_value.describe_standards.return_value = {"Standards": []}
            mock_client.return_value.list_security_control_definitions.return_value = {"SecurityControlDefinitions": []}
            mock_client.return_value.get_finding_history.return_value = {"Records": []}
            mock_client.return_value.describe_standards_controls.return_value = {"Controls": []}

            # Test all tools with empty responses
            tools_to_test = [
                ("get-security-findings", {}),
                ("get-finding-statistics", {"group_by": "SeverityLabel"}),
                ("get-security-score", {}),
                ("get-enabled-standards", {}),
                ("list-security-control-definitions", {}),
                ("get-finding-history", {"finding_identifier": "test-id"}),
                ("describe-standards-controls", {"standards_subscription_arn": "test-arn"}),
                ("generate-security-report", {}),
                ("generate-compliance-report", {}),
                ("generate-security-trends-report", {}),
            ]

            for tool_name, arguments in tools_to_test:
                response = await mcp.call_tool(tool_name, arguments)
                assert response is not None, f"Tool {tool_name} returned None"
                actual_result = extract_mcp_result(response)
                assert actual_result is not None, f"Tool {tool_name} returned no actual result"

    @pytest.mark.asyncio
    async def test_tools_with_various_parameters(self):
        """Test tools with various parameter combinations to increase coverage."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock responses
            mock_finding = {
                "Id": "test-finding-1",
                "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                "GeneratorId": "test-generator",
                "AwsAccountId": "123456789012",
                "Region": "us-east-1",
                "Title": "Test Security Finding",
                "Description": "This is a test security finding",
                "Severity": {"Label": "CRITICAL"},
                "Workflow": {"Status": "RESOLVED"},
                "RecordState": "ARCHIVED",
                "CreatedAt": "2024-01-01T00:00:00Z",
                "UpdatedAt": "2024-01-01T00:00:00Z",
                "Resources": [{"Type": "AwsS3Bucket", "Id": "test-bucket"}],
                "Compliance": {"Status": "PASSED"},
            }
            mock_client.return_value.get_findings.return_value = {"Findings": [mock_finding]}

            # Test get-security-findings with various filters
            test_cases = [
                {"severity_labels": ["CRITICAL", "HIGH"]},
                {"workflow_status": ["RESOLVED", "SUPPRESSED"]},
                {"compliance_status": ["PASSED", "FAILED"]},
                {"record_state": ["ARCHIVED"]},
                {"product_name": "Security Hub"},
                {"resource_type": "AwsS3Bucket"},
                {"days_back": 30, "max_results": 100},
            ]

            for arguments in test_cases:
                response = await mcp.call_tool("get-security-findings", arguments)
                assert response is not None
                actual_result = extract_mcp_result(response)
                assert actual_result is not None
                # Should return a list of findings
                if isinstance(actual_result, list):
                    assert len(actual_result) == 1
                    assert actual_result[0]["severity_label"] == "CRITICAL"
                else:
                    # If it's a single finding object, check it directly
                    assert actual_result["severity_label"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_error_conditions_coverage(self):
        """Test various error conditions to increase coverage."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            from botocore.exceptions import BotoCoreError, ClientError

            # Test different types of AWS errors
            error_conditions = [
                ClientError(
                    {"Error": {"Code": "InvalidParameterValue", "Message": "Invalid parameter"}}, "GetFindings"
                ),
                ClientError({"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}}, "GetFindings"),
                ClientError({"Error": {"Code": "InternalException", "Message": "Internal error"}}, "GetFindings"),
                BotoCoreError(),
                Exception("Generic error"),
            ]

            for error in error_conditions:
                mock_client.return_value.get_findings.side_effect = error

                from mcp.server.fastmcp.exceptions import ToolError

                with pytest.raises(ToolError):
                    await mcp.call_tool("get-security-findings", {})

    @pytest.mark.asyncio
    async def test_report_generation_with_data(self):
        """Test report generation tools with comprehensive data to increase coverage."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create comprehensive mock data
            mock_findings = []
            severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]
            statuses = ["NEW", "NOTIFIED", "RESOLVED", "SUPPRESSED"]
            compliance_statuses = ["PASSED", "FAILED", "WARNING", "NOT_AVAILABLE"]

            for i, severity in enumerate(severities):
                for j, status in enumerate(statuses):
                    for k, compliance in enumerate(compliance_statuses):
                        mock_findings.append(
                            {
                                "Id": f"test-finding-{i}-{j}-{k}",
                                "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                                "GeneratorId": f"test-generator-{i}",
                                "AwsAccountId": "123456789012",
                                "Region": "us-east-1",
                                "Title": f"Test Security Finding {severity}",
                                "Description": f"This is a test {severity} security finding",
                                "Severity": {"Label": severity},
                                "Workflow": {"Status": status},
                                "RecordState": "ACTIVE",
                                "CreatedAt": "2024-01-01T00:00:00Z",
                                "UpdatedAt": "2024-01-01T00:00:00Z",
                                "Resources": [{"Type": "AwsEc2Instance", "Id": f"i-{i}{j}{k}"}],
                                "Compliance": {"Status": compliance},
                            }
                        )

            mock_standards = [
                {
                    "StandardsSubscriptionArn": "arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-standard/v/1.0.0",
                    "StandardsArn": "arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0",
                    "StandardsInput": {},
                    "StandardsStatus": "READY",
                },
                {
                    "StandardsSubscriptionArn": "arn:aws:securityhub:us-east-1:123456789012:subscription/cis-aws-foundations-benchmark/v/1.2.0",
                    "StandardsArn": "arn:aws:securityhub:::standard/cis-aws-foundations-benchmark/v/1.2.0",
                    "StandardsInput": {},
                    "StandardsStatus": "INCOMPLETE",
                },
            ]

            mock_client.return_value.get_findings.return_value = {"Findings": mock_findings}
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": mock_standards}
            mock_client.return_value.describe_standards.return_value = {
                "Standards": [
                    {
                        "StandardsArn": "arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0",
                        "Name": "AWS Foundational Security Standard",
                        "Description": "AWS Foundational Security Standard",
                    },
                    {
                        "StandardsArn": "arn:aws:securityhub:::standard/cis-aws-foundations-benchmark/v/1.2.0",
                        "Name": "CIS AWS Foundations Benchmark",
                        "Description": "CIS AWS Foundations Benchmark",
                    },
                ]
            }

            # Test all report generation tools with comprehensive data
            report_tools = [
                ("generate-security-report", {"include_findings_details": True, "max_findings_per_severity": 5}),
                ("generate-compliance-report", {"include_control_details": True}),
                (
                    "generate-security-trends-report",
                    {"analysis_periods": [7, 14, 30], "include_detailed_analysis": True},
                ),
            ]

            for tool_name, arguments in report_tools:
                response = await mcp.call_tool(tool_name, arguments)
                assert response is not None, f"Report tool {tool_name} returned None"
                actual_result = extract_mcp_result(response)
                # Verify the response contains substantial data
                assert isinstance(actual_result, dict), f"Report tool {tool_name} should return a dictionary"
                assert "report_metadata" in actual_result, f"Report tool {tool_name} missing report_metadata"

    @pytest.mark.asyncio
    async def test_edge_cases_and_boundary_conditions(self):
        """Test edge cases and boundary conditions to increase coverage."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Test with very large days_back value (should be limited)
            mock_client.return_value.get_findings.return_value = {"Findings": []}

            response = await mcp.call_tool("get-security-findings", {"days_back": 500})  # Over 365 limit
            assert response is not None

            # Test with zero max_results
            response = await mcp.call_tool("get-security-findings", {"max_results": 0})
            assert response is not None

            # Test with very high max_results
            response = await mcp.call_tool("get-security-findings", {"max_results": 10000})
            assert response is not None

    @pytest.mark.asyncio
    async def test_pagination_coverage(self):
        """Test pagination logic to increase coverage."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock paginated responses
            def mock_get_findings(**kwargs):
                if kwargs.get("NextToken") == "token1":
                    return {"Findings": [], "NextToken": "token2"}
                elif kwargs.get("NextToken") == "token2":
                    return {"Findings": []}  # No more pages
                else:
                    return {"Findings": [], "NextToken": "token1"}

            mock_client.return_value.get_findings.side_effect = mock_get_findings

            response = await mcp.call_tool("get-security-findings", {"max_results": 200})
            assert response is not None

    @pytest.mark.asyncio
    async def test_invalid_enum_handling(self):
        """Test handling of invalid enum values to increase coverage."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock finding with invalid enum values
            mock_finding = {
                "Id": "test-finding-1",
                "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                "GeneratorId": "test-generator",
                "AwsAccountId": "123456789012",
                "Region": "us-east-1",
                "Title": "Test Security Finding",
                "Description": "This is a test security finding",
                "Severity": {"Label": "INVALID_SEVERITY"},  # Invalid severity
                "Workflow": {"Status": "INVALID_STATUS"},  # Invalid workflow status
                "RecordState": "INVALID_STATE",  # Invalid record state
                "CreatedAt": "2024-01-01T00:00:00Z",
                "UpdatedAt": "2024-01-01T00:00:00Z",
                "Resources": [{"Type": "AwsEc2Instance"}],
                "Compliance": {"Status": "INVALID_COMPLIANCE"},  # Invalid compliance
            }
            mock_client.return_value.get_findings.return_value = {"Findings": [mock_finding]}

            response = await mcp.call_tool("get-security-findings", {})
            assert response is not None
            actual_result = extract_mcp_result(response)
            # Should handle invalid enum values gracefully
            if isinstance(actual_result, list):
                assert len(actual_result) == 1
                result = actual_result[0]
            else:
                result = actual_result

            assert result["severity_label"] == "INFORMATIONAL"  # Default
            assert result["workflow_status"] == "NEW"  # Default
            assert result["record_state"] == "ACTIVE"  # Default

    @pytest.mark.asyncio
    async def test_missing_optional_fields(self):
        """Test handling of missing optional fields to increase coverage."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock finding with minimal required fields only
            mock_finding = {
                "Id": "test-finding-1",
                "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                "GeneratorId": "test-generator",
                "AwsAccountId": "123456789012",
                "Region": "us-east-1",
                "Title": "Test Security Finding",
                "Description": "This is a test security finding",
                "CreatedAt": "2024-01-01T00:00:00Z",
                "UpdatedAt": "2024-01-01T00:00:00Z",
                # Missing: Severity, Workflow, RecordState, Resources, Compliance
            }
            mock_client.return_value.get_findings.return_value = {"Findings": [mock_finding]}

            response = await mcp.call_tool("get-security-findings", {})
            assert response is not None
            actual_result = extract_mcp_result(response)
            # Should handle missing optional fields gracefully
            if isinstance(actual_result, list):
                assert len(actual_result) == 1
                result = actual_result[0]
            else:
                result = actual_result

            assert result["severity_label"] == "INFORMATIONAL"  # Default
            assert result["workflow_status"] == "NEW"  # Default
            assert result["compliance_status"] is None  # Should be None

    @pytest.mark.asyncio
    async def test_statistics_with_different_group_by_values(self):
        """Test finding statistics with different group_by values to increase coverage."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_finding = {
                "Id": "test-finding-1",
                "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                "GeneratorId": "test-generator",
                "AwsAccountId": "123456789012",
                "Region": "us-east-1",
                "Title": "Test Security Finding",
                "Description": "This is a test security finding",
                "Severity": {"Label": "HIGH"},
                "Workflow": {"Status": "NEW"},
                "RecordState": "ACTIVE",
                "CreatedAt": "2024-01-01T00:00:00Z",
                "UpdatedAt": "2024-01-01T00:00:00Z",
                "Resources": [{"Type": "AwsEc2Instance"}],
                "Compliance": {"Status": "FAILED"},
                "ProductFields": {"aws/securityhub/ProductName": "Security Hub"},
            }
            mock_client.return_value.get_findings.return_value = {"Findings": [mock_finding]}

            # Test different group_by values
            group_by_values = [
                "SeverityLabel",
                "WorkflowStatus",
                "ProductName",
                "ResourceType",
                "ComplianceStatus",
                "RecordState",
                "UnknownField",
            ]

            for group_by in group_by_values:
                response = await mcp.call_tool("get-finding-statistics", {"group_by": group_by})
                assert response is not None
                actual_result = extract_mcp_result(response)
                assert len(actual_result) > 0
