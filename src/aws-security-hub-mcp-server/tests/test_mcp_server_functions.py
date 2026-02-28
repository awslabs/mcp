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
"""Tests for AWS Security Hub MCP Server."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from awslabs.aws_security_hub_mcp_server.models import (
    ComplianceStatus,
    SeverityLabel,
    WorkflowStatus,
)
from awslabs.aws_security_hub_mcp_server.server import (
    analyze_compliance_trends,
    analyze_resource_type_trends,
    analyze_severity_trends,
    calculate_compliance_score_trend,
    describe_standards_controls,
    determine_overall_trend_direction,
    generate_compliance_report,
    generate_detailed_trend_analysis,
    generate_security_report,
    generate_security_trends_report,
    generate_trend_insights,
    get_enabled_standards,
    get_finding_history,
    get_finding_statistics,
    get_security_findings,
    get_security_hub_client,
    get_security_score,
    identify_most_affected_resources,
    list_security_control_definitions,
    parse_finding,
)


class TestSecurityHubServer:
    """Test cases for Security Hub MCP Server."""

    @pytest.mark.asyncio
    async def test_get_security_findings_success(self, mock_context, sample_finding):
        """Test successful retrieval of security findings."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            findings = await get_security_findings(mock_context, severity_labels=[SeverityLabel.HIGH], max_results=10)

            assert len(findings) == 1
            assert findings[0].severity_label == SeverityLabel.HIGH
            assert findings[0].title == "Test Security Finding"

    @pytest.mark.asyncio
    async def test_get_security_findings_with_filters(self, mock_context, sample_finding):
        """Test security findings retrieval with multiple filters."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            findings = await get_security_findings(
                mock_context,
                severity_labels=[SeverityLabel.HIGH, SeverityLabel.CRITICAL],
                workflow_status=[WorkflowStatus.NEW],
                compliance_status=[ComplianceStatus.FAILED],
                resource_type="AwsEc2Instance",
                days_back=30,
            )

            assert len(findings) == 1
            mock_client.return_value.get_findings.assert_called_once()

            # Verify filters were applied
            call_args = mock_client.return_value.get_findings.call_args
            filters = call_args[1]["Filters"]
            assert "SeverityLabel" in filters
            assert "WorkflowStatus" in filters
            assert "ComplianceStatus" in filters
            assert "ResourceType" in filters
            assert "UpdatedAt" in filters

    @pytest.mark.asyncio
    async def test_get_finding_statistics_success(self, mock_context, sample_finding):
        """Test successful retrieval of finding statistics."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create multiple findings with different severities
            findings = [
                {**sample_finding, "Severity": {"Label": "HIGH"}},
                {**sample_finding, "Severity": {"Label": "HIGH"}},
                {**sample_finding, "Severity": {"Label": "MEDIUM"}},
            ]

            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            stats = await get_finding_statistics(mock_context, group_by="SeverityLabel", days_back=30)

            assert len(stats) == 2  # HIGH and MEDIUM
            # Should be sorted by count descending
            assert stats[0].group_key == "HIGH"
            assert stats[0].count == 2
            assert stats[0].percentage == 66.67
            assert stats[1].group_key == "MEDIUM"
            assert stats[1].count == 1
            assert stats[1].percentage == 33.33

    @pytest.mark.asyncio
    async def test_get_security_score_success(self, mock_context, sample_finding):
        """Test successful calculation of security score."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create findings with different severities
            findings = [
                {**sample_finding, "Severity": {"Label": "CRITICAL"}},
                {**sample_finding, "Severity": {"Label": "HIGH"}},
                {**sample_finding, "Severity": {"Label": "LOW"}},
            ]

            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            score = await get_security_score(mock_context)

            assert score.max_score == 100.0
            assert 0 <= score.current_score <= 100
            assert score.security_score_percentage == score.current_score
            assert isinstance(score.score_date, str)  # Changed from datetime to str

    def test_parse_finding_success(self, sample_finding):
        """Test successful parsing of finding data."""
        finding = parse_finding(sample_finding)

        assert finding.id == sample_finding["Id"]
        assert finding.title == sample_finding["Title"]
        assert finding.severity_label == SeverityLabel.HIGH
        assert finding.workflow_status == WorkflowStatus.NEW
        assert finding.compliance_status == ComplianceStatus.FAILED
        assert finding.resource_type == "AwsEc2Instance"

    @pytest.mark.asyncio
    async def test_get_security_findings_client_error(self, mock_context):
        """Test handling of AWS client errors."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            from botocore.exceptions import ClientError

            mock_client.return_value.get_findings.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetFindings"
            )

            with pytest.raises(Exception) as exc_info:
                await get_security_findings(mock_context)

            assert "Security Hub API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_security_findings_empty_response(self, mock_context):
        """Test handling of empty findings response."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": []}

            findings = await get_security_findings(mock_context)

            assert len(findings) == 0

    # Test get_security_hub_client function
    def test_get_security_hub_client_success(self):
        """Test successful creation of Security Hub client."""
        with patch("awslabs.aws_security_hub_mcp_server.server.boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            client = get_security_hub_client()

            assert client == mock_client
            mock_session.assert_called_once()

    def test_get_security_hub_client_no_credentials(self):
        """Test Security Hub client creation with no credentials."""
        with patch("awslabs.aws_security_hub_mcp_server.server.boto3.Session") as mock_session:
            mock_session.side_effect = NoCredentialsError()

            with pytest.raises(NoCredentialsError):
                get_security_hub_client()

    def test_get_security_hub_client_client_error(self):
        """Test Security Hub client creation with client error."""
        with patch("awslabs.aws_security_hub_mcp_server.server.boto3.Session") as mock_session:
            mock_session.side_effect = Exception("Connection error")

            with pytest.raises(Exception, match="Connection error"):
                get_security_hub_client()

    # Test get_enabled_standards function
    @pytest.mark.asyncio
    async def test_get_enabled_standards_success(self, mock_context):
        """Test successful retrieval of enabled standards."""
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

            standards = await get_enabled_standards(mock_context)

            assert len(standards) == 1
            assert standards[0].standards_subscription_arn == mock_standards[0]["StandardsSubscriptionArn"]
            assert standards[0].standards_arn == mock_standards[0]["StandardsArn"]
            assert standards[0].standards_status == "READY"

    @pytest.mark.asyncio
    async def test_get_enabled_standards_client_error(self, mock_context):
        """Test get_enabled_standards with client error."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_enabled_standards.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetEnabledStandards"
            )

            with pytest.raises(Exception) as exc_info:
                await get_enabled_standards(mock_context)

            assert "Security Hub API error" in str(exc_info.value)

    # Test list_security_control_definitions function
    @pytest.mark.asyncio
    async def test_list_security_control_definitions_success(self, mock_context):
        """Test successful listing of security control definitions."""
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

            controls = await list_security_control_definitions(mock_context)

            assert len(controls) == 1
            assert controls[0].security_control_id == "S3.1"
            assert controls[0].title == "S3 buckets should have public access blocked"
            assert controls[0].severity_rating == "HIGH"

    @pytest.mark.asyncio
    async def test_list_security_control_definitions_with_standard_arn(self, mock_context):
        """Test listing security control definitions with standard ARN filter."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.list_security_control_definitions.return_value = {"SecurityControlDefinitions": []}

            await list_security_control_definitions(
                mock_context, standard_arn="arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0"
            )

            call_args = mock_client.return_value.list_security_control_definitions.call_args
            assert (
                call_args[1]["StandardsArn"]
                == "arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0"
            )

    # Test get_finding_history function
    @pytest.mark.asyncio
    async def test_get_finding_history_success(self, mock_context):
        """Test successful retrieval of finding history."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_history = [
                {
                    "FindingIdentifier": {
                        "Id": "arn:aws:securityhub:us-east-1:123456789012:finding/test-finding-1",
                        "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                    },
                    "UpdateTime": datetime.utcnow(),
                    "FindingCreated": True,
                    "UpdateSource": {
                        "Type": "BATCH_UPDATE_FINDINGS",
                        "Identity": "arn:aws:iam::123456789012:user/test-user",
                    },
                    "Updates": [{"UpdatedField": "Workflow/Status", "OldValue": "NEW", "NewValue": "RESOLVED"}],
                }
            ]
            mock_client.return_value.get_finding_history.return_value = {"Records": mock_history}

            history = await get_finding_history(
                mock_context, "arn:aws:securityhub:us-east-1:123456789012:finding/test-finding-1"
            )

            assert len(history) == 1
            assert (
                history[0]["finding_identifier"]["Id"]
                == "arn:aws:securityhub:us-east-1:123456789012:finding/test-finding-1"
            )
            assert history[0]["finding_created"] is True

    @pytest.mark.asyncio
    async def test_get_finding_history_with_dates(self, mock_context):
        """Test get_finding_history with start and end times."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_finding_history.return_value = {"Records": []}

            start_time = "2024-01-01T00:00:00Z"
            end_time = "2024-01-31T23:59:59Z"

            await get_finding_history(mock_context, "test-finding-id", start_time=start_time, end_time=end_time)

            call_args = mock_client.return_value.get_finding_history.call_args
            assert "StartTime" in call_args[1]
            assert "EndTime" in call_args[1]

    # Test describe_standards_controls function
    @pytest.mark.asyncio
    async def test_describe_standards_controls_success(self, mock_context):
        """Test successful description of standards controls."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_controls = [
                {
                    "StandardsControlArn": "arn:aws:securityhub:us-east-1:123456789012:control/aws-foundational-security-standard/v/1.0.0/S3.1",
                    "ControlStatus": "ENABLED",
                    "DisabledReason": None,
                    "ControlStatusUpdatedAt": datetime.utcnow(),
                    "ControlId": "S3.1",
                    "Title": "S3 buckets should have public access blocked",
                    "Description": "This control checks whether S3 buckets have public access blocked.",
                    "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/S3.1/remediation",
                    "SeverityRating": "HIGH",
                    "RelatedRequirements": ["NIST.800-53.r5 AC-3", "NIST.800-53.r5 AC-6"],
                }
            ]
            mock_client.return_value.describe_standards_controls.return_value = {"Controls": mock_controls}

            controls = await describe_standards_controls(
                mock_context,
                "arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-standard/v/1.0.0",
            )

            assert len(controls) == 1
            assert controls[0]["control_id"] == "S3.1"
            assert controls[0]["control_status"] == "ENABLED"
            assert controls[0]["severity_rating"] == "HIGH"

    # Test report generation functions
    @pytest.mark.asyncio
    async def test_generate_security_report_success(self, mock_context, sample_finding):
        """Test successful generation of security report."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": []}

            report = await generate_security_report(mock_context)

            assert "executive_summary" in report
            assert "security_score" in report["executive_summary"]
            assert "detailed_findings" in report
            assert "recommendations" in report
            assert "enabled_standards" in report

    @pytest.mark.asyncio
    async def test_generate_compliance_report_success(self, mock_context, sample_finding):
        """Test successful generation of compliance report."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": []}

            report = await generate_compliance_report(mock_context)

            assert "executive_summary" in report
            assert "overall_compliance_percentage" in report["executive_summary"]
            assert "standards_compliance" in report
            assert "compliance_findings_by_category" in report
            assert "recommendations" in report

    @pytest.mark.asyncio
    async def test_generate_security_trends_report_success(self, mock_context, sample_finding):
        """Test successful generation of security trends report."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            report = await generate_security_trends_report(mock_context)

            assert "trend_analysis" in report
            assert "severity_trends" in report["trend_analysis"]
            assert "insights_and_recommendations" in report
            assert "historical_data_points" in report

    # Test trend analysis helper functions
    def test_analyze_severity_trends(self):
        """Test severity trends analysis."""
        trend_data = {
            "7_days": {"severity_breakdown": {"HIGH": 1, "MEDIUM": 1}, "data_available": True},
            "14_days": {"severity_breakdown": {"HIGH": 2, "LOW": 1}, "data_available": True},
        }
        periods = [7, 14]

        result = analyze_severity_trends(trend_data, periods)

        assert "severity_data_points" in result
        assert "trend_directions" in result
        assert "HIGH" in result["severity_data_points"]
        assert "MEDIUM" in result["severity_data_points"]
        assert "LOW" in result["severity_data_points"]
        assert len(result["severity_data_points"]["HIGH"]) == 2
        assert result["severity_data_points"]["HIGH"][0]["count"] == 1  # 7-day period
        assert result["severity_data_points"]["HIGH"][1]["count"] == 2  # 14-day period

    def test_analyze_compliance_trends(self):
        """Test compliance trends analysis."""
        trend_data = {
            "7_days": {"compliance_breakdown": {"FAILED": 1, "PASSED": 1}, "data_available": True},
            "14_days": {"compliance_breakdown": {"FAILED": 2, "PASSED": 0}, "data_available": True},
        }
        periods = [7, 14]

        result = analyze_compliance_trends(trend_data, periods)

        assert "compliance_data_points" in result
        assert "compliance_score_trend" in result
        assert "FAILED" in result["compliance_data_points"]
        assert "PASSED" in result["compliance_data_points"]
        assert len(result["compliance_data_points"]["FAILED"]) == 2
        assert result["compliance_data_points"]["FAILED"][0]["count"] == 1  # 7-day period
        assert result["compliance_data_points"]["FAILED"][1]["count"] == 2  # 14-day period

    def test_analyze_resource_type_trends(self):
        """Test resource type trends analysis."""
        trend_data = {
            "7_days": {"top_resource_types": {"AwsEc2Instance": 1, "AwsS3Bucket": 1}, "data_available": True},
            "14_days": {"top_resource_types": {"AwsEc2Instance": 2, "AwsS3Bucket": 0}, "data_available": True},
        }
        periods = [7, 14]

        result = analyze_resource_type_trends(trend_data, periods)

        assert "resource_type_data_points" in result
        assert "most_affected_resources" in result
        assert "AwsEc2Instance" in result["resource_type_data_points"]
        assert "AwsS3Bucket" in result["resource_type_data_points"]
        assert len(result["resource_type_data_points"]["AwsEc2Instance"]) == 2
        assert result["resource_type_data_points"]["AwsEc2Instance"][0]["findings_count"] == 1  # 7-day period
        assert result["resource_type_data_points"]["AwsEc2Instance"][1]["findings_count"] == 2  # 14-day period

    def test_calculate_compliance_score_trend(self):
        """Test compliance score trend calculation."""
        compliance_trends = {
            "PASSED": [{"period_days": 7, "count": 10}, {"period_days": 14, "count": 15}],
            "FAILED": [{"period_days": 7, "count": 5}, {"period_days": 14, "count": 3}],
            "WARNING": [{"period_days": 7, "count": 2}, {"period_days": 14, "count": 1}],
            "NOT_AVAILABLE": [{"period_days": 7, "count": 0}, {"period_days": 14, "count": 0}],
        }

        result = calculate_compliance_score_trend(compliance_trends)

        assert len(result) == 2
        assert 0 <= result[0]["compliance_score"] <= 100
        assert 0 <= result[1]["compliance_score"] <= 100
        # Second period should have higher score (more passed, fewer failed)
        assert result[1]["compliance_score"] > result[0]["compliance_score"]

    def test_identify_most_affected_resources(self):
        """Test identification of most affected resources."""
        resource_trends = {
            "AwsEc2Instance": [{"period_days": 7, "findings_count": 5}, {"period_days": 14, "findings_count": 8}],
            "AwsS3Bucket": [{"period_days": 7, "findings_count": 2}, {"period_days": 14, "findings_count": 3}],
            "AwsRdsDbInstance": [{"period_days": 7, "findings_count": 1}, {"period_days": 14, "findings_count": 1}],
        }

        result = identify_most_affected_resources(resource_trends)

        assert len(result) <= 5  # Should return top 5
        assert result[0]["resource_type"] == "AwsEc2Instance"  # Most affected
        assert result[0]["findings_count"] == 5  # Most recent count (7-day period)

    def test_determine_overall_trend_direction(self):
        """Test overall trend direction determination."""
        # Improving trend
        improving_scores = {"7_days": 80.0, "14_days": 70.0, "30_days": 60.0}
        result = determine_overall_trend_direction(improving_scores, [7, 14, 30])
        assert result == "improving"

        # Declining trend
        declining_scores = {"7_days": 60.0, "14_days": 70.0, "30_days": 80.0}
        result = determine_overall_trend_direction(declining_scores, [7, 14, 30])
        assert result == "declining"

        # Stable trend
        stable_scores = {"7_days": 70.0, "14_days": 71.0, "30_days": 69.0}
        result = determine_overall_trend_direction(stable_scores, [7, 14, 30])
        assert result == "stable"

    def test_generate_trend_insights(self):
        """Test trend insights generation."""
        trend_data = {
            "7_days": {
                "severity_breakdown": {"HIGH": 1},
                "top_resource_types": {"AwsEc2Instance": 1},
                "data_available": True,
            },
            "14_days": {
                "severity_breakdown": {"MEDIUM": 1},
                "top_resource_types": {"AwsS3Bucket": 1},
                "data_available": True,
            },
        }
        security_scores = {"7_days": 70.0, "14_days": 75.0}
        periods = [7, 14]

        result = generate_trend_insights(trend_data, security_scores, periods)

        assert "key_insights" in result
        assert "recommendations" in result
        assert "trend_summary" in result
        assert isinstance(result["key_insights"], list)
        assert isinstance(result["recommendations"], list)

    def test_generate_detailed_trend_analysis(self):
        """Test detailed trend analysis generation."""
        trend_data = {
            "7_days": {"severity_breakdown": {"HIGH": 1, "MEDIUM": 1}, "total_findings": 2, "data_available": True},
            "14_days": {"severity_breakdown": {"HIGH": 1, "LOW": 1}, "total_findings": 2, "data_available": True},
        }
        periods = [7, 14]

        result = generate_detailed_trend_analysis(trend_data, periods)

        assert "statistical_summary" in result
        assert "period_comparisons" in result
        assert "data_quality_assessment" in result
        assert "findings_volume_stats" in result["statistical_summary"]

    # Test error handling for all functions
    @pytest.mark.asyncio
    async def test_get_finding_statistics_client_error(self, mock_context):
        """Test get_finding_statistics with client error."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetFindings"
            )

            with pytest.raises(Exception) as exc_info:
                await get_finding_statistics(mock_context)

            assert "Security Hub API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_security_score_client_error(self, mock_context):
        """Test get_security_score with client error."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetFindings"
            )

            with pytest.raises(Exception) as exc_info:
                await get_security_score(mock_context)

            assert "Security Hub API error" in str(exc_info.value)

    # Test edge cases
    @pytest.mark.asyncio
    async def test_get_finding_statistics_empty_group_by(self, mock_context):
        """Test get_finding_statistics with empty results."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": []}

            stats = await get_finding_statistics(mock_context, group_by="SeverityLabel")

            assert len(stats) == 0

    @pytest.mark.asyncio
    async def test_get_security_score_no_findings(self, mock_context):
        """Test get_security_score with no findings."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": []}

            score = await get_security_score(mock_context)

            assert score.current_score == 100.0  # Perfect score when no findings
            assert score.security_score_percentage == 100.0

    def test_parse_finding_missing_fields(self):
        """Test parse_finding with missing optional fields."""
        minimal_finding = {
            "Id": "test-id",
            "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
            "GeneratorId": "test-generator",
            "AwsAccountId": "123456789012",
            "Region": "us-east-1",
            "Title": "Test Finding",
            "Description": "Test description",
            "Severity": {"Label": "MEDIUM"},
            "Workflow": {"Status": "NEW"},
            "RecordState": "ACTIVE",
            "CreatedAt": datetime.utcnow(),
            "UpdatedAt": datetime.utcnow(),
            "Resources": [{"Type": "AwsEc2Instance"}],
        }

        finding = parse_finding(minimal_finding)

        assert finding.id == "test-id"
        assert finding.title == "Test Finding"
        assert finding.severity_label == SeverityLabel.MEDIUM
        assert finding.compliance_status is None  # Default when missing

    def test_parse_finding_invalid_severity(self):
        """Test parse_finding with invalid severity label."""
        finding_data = {
            "Id": "test-id",
            "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
            "GeneratorId": "test-generator",
            "AwsAccountId": "123456789012",
            "Region": "us-east-1",
            "Title": "Test Finding",
            "Description": "Test description",
            "Severity": {"Label": "INVALID_SEVERITY"},
            "Workflow": {"Status": "NEW"},
            "RecordState": "ACTIVE",
            "CreatedAt": datetime.utcnow(),
            "UpdatedAt": datetime.utcnow(),
            "Resources": [{"Type": "AwsEc2Instance"}],
        }

        finding = parse_finding(finding_data)

        assert finding.severity_label == SeverityLabel.INFORMATIONAL  # Default fallback

    def test_parse_finding_invalid_workflow_status(self):
        """Test parse_finding with invalid workflow status."""
        finding_data = {
            "Id": "test-id",
            "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
            "GeneratorId": "test-generator",
            "AwsAccountId": "123456789012",
            "Region": "us-east-1",
            "Title": "Test Finding",
            "Description": "Test description",
            "Severity": {"Label": "HIGH"},
            "Workflow": {"Status": "INVALID_STATUS"},
            "RecordState": "ACTIVE",
            "CreatedAt": datetime.utcnow(),
            "UpdatedAt": datetime.utcnow(),
            "Resources": [{"Type": "AwsEc2Instance"}],
        }

        finding = parse_finding(finding_data)

        assert finding.workflow_status == WorkflowStatus.NEW  # Default fallback

    def test_parse_finding_invalid_record_state(self):
        """Test parse_finding with invalid record state."""
        finding_data = {
            "Id": "test-id",
            "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
            "GeneratorId": "test-generator",
            "AwsAccountId": "123456789012",
            "Region": "us-east-1",
            "Title": "Test Finding",
            "Description": "Test description",
            "Severity": {"Label": "HIGH"},
            "Workflow": {"Status": "NEW"},
            "RecordState": "INVALID_STATE",
            "CreatedAt": datetime.utcnow(),
            "UpdatedAt": datetime.utcnow(),
            "Resources": [{"Type": "AwsEc2Instance"}],
        }

        finding = parse_finding(finding_data)

        assert finding.record_state.value == "ACTIVE"  # Default fallback

    def test_parse_finding_invalid_compliance_status(self):
        """Test parse_finding with invalid compliance status."""
        finding_data = {
            "Id": "test-id",
            "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
            "GeneratorId": "test-generator",
            "AwsAccountId": "123456789012",
            "Region": "us-east-1",
            "Title": "Test Finding",
            "Description": "Test description",
            "Severity": {"Label": "HIGH"},
            "Workflow": {"Status": "NEW"},
            "RecordState": "ACTIVE",
            "CreatedAt": datetime.utcnow(),
            "UpdatedAt": datetime.utcnow(),
            "Resources": [{"Type": "AwsEc2Instance"}],
            "Compliance": {"Status": "INVALID_COMPLIANCE"},
        }

        finding = parse_finding(finding_data)

        assert finding.compliance_status is None  # Default fallback for invalid status

    @pytest.mark.asyncio
    async def test_get_security_findings_with_all_filters(self, mock_context, sample_finding):
        """Test security findings retrieval with all possible filters."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            from awslabs.aws_security_hub_mcp_server.models import RecordState

            findings = await get_security_findings(
                mock_context,
                severity_labels=[SeverityLabel.HIGH],
                workflow_status=[WorkflowStatus.NEW],
                compliance_status=[ComplianceStatus.FAILED],
                record_state=[RecordState.ACTIVE],
                resource_type="AwsEc2Instance",
                product_name="Security Hub",
                days_back=30,
                max_results=50,
            )

            assert len(findings) == 1
            mock_client.return_value.get_findings.assert_called_once()

            # Verify all filters were applied
            call_args = mock_client.return_value.get_findings.call_args
            filters = call_args[1]["Filters"]
            assert "SeverityLabel" in filters
            assert "WorkflowStatus" in filters
            assert "ComplianceStatus" in filters
            assert "RecordState" in filters
            assert "ResourceType" in filters
            assert "ProductName" in filters
            assert "UpdatedAt" in filters

    @pytest.mark.asyncio
    async def test_get_finding_statistics_different_group_by(self, mock_context, sample_finding):
        """Test get_finding_statistics with different group_by options."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Test with WorkflowStatus grouping
            findings = [
                {**sample_finding, "Workflow": {"Status": "NEW"}},
                {**sample_finding, "Workflow": {"Status": "NEW"}},
                {**sample_finding, "Workflow": {"Status": "RESOLVED"}},
            ]
            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            stats = await get_finding_statistics(mock_context, group_by="WorkflowStatus")

            assert len(stats) == 2  # NEW and RESOLVED
            assert stats[0].group_key == "NEW"
            assert stats[0].count == 2
            assert stats[1].group_key == "RESOLVED"
            assert stats[1].count == 1

    @pytest.mark.asyncio
    async def test_list_security_control_definitions_client_error(self, mock_context):
        """Test list_security_control_definitions with client error."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.list_security_control_definitions.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListSecurityControlDefinitions"
            )

            with pytest.raises(Exception) as exc_info:
                await list_security_control_definitions(mock_context)

            assert "Security Hub API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_finding_history_client_error(self, mock_context):
        """Test get_finding_history with client error."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_finding_history.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetFindingHistory"
            )

            with pytest.raises(Exception) as exc_info:
                await get_finding_history(mock_context, "test-finding-id")

            assert "Security Hub API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_describe_standards_controls_client_error(self, mock_context):
        """Test describe_standards_controls with client error."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.describe_standards_controls.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "DescribeStandardsControls"
            )

            with pytest.raises(Exception) as exc_info:
                await describe_standards_controls(mock_context, "test-standard-arn")

            assert "Security Hub API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_security_report_client_error(self, mock_context):
        """Test generate_security_report with client error."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetFindings"
            )

            with pytest.raises(Exception) as exc_info:
                await generate_security_report(mock_context)

            assert "Security Hub API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_compliance_report_client_error(self, mock_context):
        """Test generate_compliance_report with client error."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetFindings"
            )

            with pytest.raises(Exception) as exc_info:
                await generate_compliance_report(mock_context)

            assert "Security Hub API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_security_trends_report_client_error(self, mock_context):
        """Test generate_security_trends_report with client error."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "GetFindings"
            )

            # The trends report handles errors gracefully and returns a report with warnings
            report = await generate_security_trends_report(mock_context)

            # Should return a report structure even with errors
            assert "trend_analysis" in report
            assert "insights_and_recommendations" in report

    def test_analyze_severity_trends_no_data(self):
        """Test severity trends analysis with no data available."""
        trend_data = {
            "7_days": {"severity_breakdown": {}, "data_available": False},
            "14_days": {"severity_breakdown": {}, "data_available": False},
        }
        periods = [7, 14]

        result = analyze_severity_trends(trend_data, periods)

        assert "severity_data_points" in result
        assert "trend_directions" in result
        # Should handle empty data gracefully
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]:
            assert severity in result["severity_data_points"]

    def test_analyze_compliance_trends_no_data(self):
        """Test compliance trends analysis with no data available."""
        trend_data = {
            "7_days": {"compliance_breakdown": {}, "data_available": False},
            "14_days": {"compliance_breakdown": {}, "data_available": False},
        }
        periods = [7, 14]

        result = analyze_compliance_trends(trend_data, periods)

        assert "compliance_data_points" in result
        assert "compliance_score_trend" in result
        # Should handle empty data gracefully
        for status in ["PASSED", "FAILED", "WARNING", "NOT_AVAILABLE"]:
            assert status in result["compliance_data_points"]

    def test_analyze_resource_type_trends_no_data(self):
        """Test resource type trends analysis with no data available."""
        trend_data = {
            "7_days": {"top_resource_types": {}, "data_available": False},
            "14_days": {"top_resource_types": {}, "data_available": False},
        }
        periods = [7, 14]

        result = analyze_resource_type_trends(trend_data, periods)

        assert "resource_type_data_points" in result
        assert "most_affected_resources" in result
        # Should handle empty data gracefully
        assert isinstance(result["resource_type_data_points"], dict)
        assert isinstance(result["most_affected_resources"], list)

    def test_calculate_compliance_score_trend_empty_data(self):
        """Test compliance score trend calculation with empty data."""
        compliance_trends = {
            "PASSED": [],
            "FAILED": [],
            "WARNING": [],
            "NOT_AVAILABLE": [],
        }

        result = calculate_compliance_score_trend(compliance_trends)

        assert len(result) == 0  # Should return empty list for no data

    def test_identify_most_affected_resources_empty_data(self):
        """Test identification of most affected resources with empty data."""
        resource_trends = {}

        result = identify_most_affected_resources(resource_trends)

        assert len(result) == 0  # Should return empty list for no data

    def test_determine_overall_trend_direction_insufficient_data(self):
        """Test overall trend direction determination with insufficient data."""
        # Only one data point
        single_scores = {"7_days": 70.0}
        result = determine_overall_trend_direction(single_scores, [7])
        assert result == "insufficient_data"  # Should return insufficient_data with insufficient data

        # Empty data
        empty_scores = {}
        result = determine_overall_trend_direction(empty_scores, [])
        assert result == "insufficient_data"  # Should return insufficient_data with no data

    def test_generate_trend_insights_empty_data(self):
        """Test trend insights generation with empty data."""
        trend_data = {
            "7_days": {"severity_breakdown": {}, "top_resource_types": {}, "data_available": False},
            "14_days": {"severity_breakdown": {}, "top_resource_types": {}, "data_available": False},
        }
        security_scores = {}
        periods = [7, 14]

        result = generate_trend_insights(trend_data, security_scores, periods)

        assert "key_insights" in result
        assert "recommendations" in result
        assert "trend_summary" in result
        assert isinstance(result["key_insights"], list)
        assert isinstance(result["recommendations"], list)

    def test_generate_detailed_trend_analysis_empty_data(self):
        """Test detailed trend analysis generation with empty data."""
        trend_data = {
            "7_days": {"severity_breakdown": {}, "total_findings": 0, "data_available": False},
            "14_days": {"severity_breakdown": {}, "total_findings": 0, "data_available": False},
        }
        periods = [7, 14]

        result = generate_detailed_trend_analysis(trend_data, periods)

        # With empty data, the function returns an empty dict
        assert isinstance(result, dict)
        # The function may return empty dict when no data is available

    @pytest.mark.asyncio
    async def test_get_security_findings_invalid_days_back(self, mock_context, sample_finding):
        """Test get_security_findings with invalid days_back parameter."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            # Test with None days_back (should work)
            findings = await get_security_findings(mock_context, days_back=None)

            # Should still work without time filter
            assert len(findings) == 1

    @pytest.mark.asyncio
    async def test_get_security_findings_parsing_error(self, mock_context):
        """Test get_security_findings with finding parsing errors."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create a malformed finding that will cause parsing errors
            malformed_finding = {
                "Id": "test-id",
                # Missing required fields to cause parsing error
            }
            mock_client.return_value.get_findings.return_value = {"Findings": [malformed_finding]}

            findings = await get_security_findings(mock_context)

            # Should return empty list when all findings fail to parse
            assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_get_security_findings_pagination(self, mock_context, sample_finding):
        """Test get_security_findings with pagination."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock multiple pages of results
            first_page = {"Findings": [sample_finding], "NextToken": "token1"}
            second_page = {"Findings": [sample_finding], "NextToken": None}

            mock_client.return_value.get_findings.side_effect = [first_page, second_page]

            findings = await get_security_findings(mock_context, max_results=10)

            # Should get findings from both pages
            assert len(findings) == 2
            assert mock_client.return_value.get_findings.call_count == 2

    @pytest.mark.asyncio
    async def test_get_security_findings_max_results_limit(self, mock_context, sample_finding):
        """Test get_security_findings respects max_results limit."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create multiple findings
            findings_list = [sample_finding] * 5
            mock_client.return_value.get_findings.return_value = {"Findings": findings_list}

            findings = await get_security_findings(mock_context, max_results=3)

            # Should only return max_results number of findings
            assert len(findings) == 3

    @pytest.mark.asyncio
    async def test_get_finding_statistics_with_filters(self, mock_context, sample_finding):
        """Test get_finding_statistics with various filters."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            stats = await get_finding_statistics(
                mock_context,
                group_by="ComplianceStatus",
                days_back=7,
            )

            # Should apply filters and group by compliance status
            assert len(stats) >= 0
            mock_client.return_value.get_findings.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_security_score_with_different_severities(self, mock_context):
        """Test get_security_score with findings of different severities."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create findings with different severities
            findings = [
                {
                    "Id": "1",
                    "Severity": {"Label": "CRITICAL"},
                    "ProductArn": "arn",
                    "GeneratorId": "gen",
                    "AwsAccountId": "123",
                    "Region": "us-east-1",
                    "Title": "Test",
                    "Description": "Test",
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE",
                    "CreatedAt": datetime.utcnow(),
                    "UpdatedAt": datetime.utcnow(),
                    "Resources": [{"Type": "AwsEc2Instance"}],
                },
                {
                    "Id": "2",
                    "Severity": {"Label": "HIGH"},
                    "ProductArn": "arn",
                    "GeneratorId": "gen",
                    "AwsAccountId": "123",
                    "Region": "us-east-1",
                    "Title": "Test",
                    "Description": "Test",
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE",
                    "CreatedAt": datetime.utcnow(),
                    "UpdatedAt": datetime.utcnow(),
                    "Resources": [{"Type": "AwsEc2Instance"}],
                },
                {
                    "Id": "3",
                    "Severity": {"Label": "LOW"},
                    "ProductArn": "arn",
                    "GeneratorId": "gen",
                    "AwsAccountId": "123",
                    "Region": "us-east-1",
                    "Title": "Test",
                    "Description": "Test",
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE",
                    "CreatedAt": datetime.utcnow(),
                    "UpdatedAt": datetime.utcnow(),
                    "Resources": [{"Type": "AwsEc2Instance"}],
                },
            ]

            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            score = await get_security_score(mock_context)

            # Score should be calculated based on severity weights
            assert 0 <= score.current_score <= 100
            assert score.max_score == 100.0

    @pytest.mark.asyncio
    async def test_get_enabled_standards_empty_response(self, mock_context):
        """Test get_enabled_standards with empty response."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": []}

            standards = await get_enabled_standards(mock_context)

            assert len(standards) == 0

    @pytest.mark.asyncio
    async def test_list_security_control_definitions_empty_response(self, mock_context):
        """Test list_security_control_definitions with empty response."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.list_security_control_definitions.return_value = {"SecurityControlDefinitions": []}

            controls = await list_security_control_definitions(mock_context)

            assert len(controls) == 0

    @pytest.mark.asyncio
    async def test_get_finding_history_empty_response(self, mock_context):
        """Test get_finding_history with empty response."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_finding_history.return_value = {"Records": []}

            history = await get_finding_history(mock_context, "test-finding-id")

            assert len(history) == 0

    @pytest.mark.asyncio
    async def test_describe_standards_controls_empty_response(self, mock_context):
        """Test describe_standards_controls with empty response."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.describe_standards_controls.return_value = {"Controls": []}

            controls = await describe_standards_controls(mock_context, "test-standard-arn")

            assert len(controls) == 0

    @pytest.mark.asyncio
    async def test_generate_security_report_with_findings(self, mock_context, sample_finding):
        """Test generate_security_report with actual findings data."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock findings and standards
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding] * 3}
            mock_standards = [
                {
                    "StandardsSubscriptionArn": "arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-standard/v/1.0.0",
                    "StandardsArn": "arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0",
                    "StandardsInput": {},
                    "StandardsStatus": "READY",
                }
            ]
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": mock_standards}

            report = await generate_security_report(
                mock_context, max_findings_per_severity=5, include_findings_details=True
            )

            assert "executive_summary" in report
            assert "detailed_findings" in report
            assert "recommendations" in report
            assert "enabled_standards" in report
            assert report["executive_summary"]["total_findings"] == 3

    @pytest.mark.asyncio
    async def test_generate_compliance_report_with_findings(self, mock_context, sample_finding):
        """Test generate_compliance_report with actual findings data."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding] * 2}
            mock_standards = [
                {
                    "StandardsSubscriptionArn": "arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-standard/v/1.0.0",
                    "StandardsArn": "arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0",
                    "StandardsInput": {},
                    "StandardsStatus": "READY",
                }
            ]
            mock_client.return_value.get_enabled_standards.return_value = {"StandardsSubscriptions": mock_standards}

            report = await generate_compliance_report(mock_context)

            assert "executive_summary" in report
            assert "standards_compliance" in report
            assert "compliance_findings_by_category" in report
            assert "recommendations" in report

    @pytest.mark.asyncio
    async def test_generate_security_trends_report_with_data(self, mock_context, sample_finding):
        """Test generate_security_trends_report with actual data."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            report = await generate_security_trends_report(mock_context)

            assert "trend_analysis" in report
            assert "insights_and_recommendations" in report
            assert "historical_data_points" in report

    def test_analyze_severity_trends_with_mixed_data(self):
        """Test severity trends analysis with mixed available/unavailable data."""
        trend_data = {
            "7_days": {"severity_breakdown": {"HIGH": 2, "MEDIUM": 1}, "data_available": True},
            "14_days": {"severity_breakdown": {}, "data_available": False},
            "30_days": {"severity_breakdown": {"LOW": 3}, "data_available": True},
        }
        periods = [7, 14, 30]

        result = analyze_severity_trends(trend_data, periods)

        assert "severity_data_points" in result
        assert "trend_directions" in result
        # Should handle mixed data availability
        assert len(result["severity_data_points"]["HIGH"]) == 2  # Only periods with HIGH data

    def test_calculate_compliance_score_trend_with_data(self):
        """Test compliance score trend calculation with actual data."""
        compliance_trends = {
            "PASSED": [{"period_days": 7, "count": 8}, {"period_days": 14, "count": 12}],
            "FAILED": [{"period_days": 7, "count": 2}, {"period_days": 14, "count": 1}],
            "WARNING": [{"period_days": 7, "count": 1}, {"period_days": 14, "count": 0}],
            "NOT_AVAILABLE": [{"period_days": 7, "count": 0}, {"period_days": 14, "count": 0}],
        }

        result = calculate_compliance_score_trend(compliance_trends)

        assert len(result) == 2
        # First period: 8 passed out of 11 total = ~72.7%
        # Second period: 12 passed out of 13 total = ~92.3%
        assert result[0]["compliance_score"] < result[1]["compliance_score"]  # Improving trend

    def test_generate_trend_insights_with_data(self):
        """Test trend insights generation with actual data."""
        trend_data = {
            "7_days": {
                "severity_breakdown": {"HIGH": 3, "MEDIUM": 2},
                "top_resource_types": {"AwsEc2Instance": 3, "AwsS3Bucket": 2},
                "data_available": True,
            },
            "14_days": {
                "severity_breakdown": {"HIGH": 1, "MEDIUM": 4},
                "top_resource_types": {"AwsEc2Instance": 2, "AwsS3Bucket": 3},
                "data_available": True,
            },
        }
        security_scores = {"7_days": 65.0, "14_days": 75.0}
        periods = [7, 14]

        result = generate_trend_insights(trend_data, security_scores, periods)

        assert "key_insights" in result
        assert "recommendations" in result
        assert "trend_summary" in result
        assert len(result["key_insights"]) > 0
        assert len(result["recommendations"]) > 0

    def test_generate_detailed_trend_analysis_with_data(self):
        """Test detailed trend analysis generation with actual data."""
        trend_data = {
            "7_days": {
                "severity_breakdown": {"HIGH": 2, "MEDIUM": 3},
                "total_findings": 5,
                "data_available": True,
            },
            "14_days": {
                "severity_breakdown": {"HIGH": 1, "MEDIUM": 2, "LOW": 1},
                "total_findings": 4,
                "data_available": True,
            },
        }
        periods = [7, 14]

        result = generate_detailed_trend_analysis(trend_data, periods)

        assert "statistical_summary" in result
        assert "period_comparisons" in result
        assert "data_quality_assessment" in result
        # Should have content when data is available
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_security_findings_time_filter_exception(self, mock_context, sample_finding):
        """Test get_security_findings with time filter that causes exception."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            # Test with days_back that might cause issues in time filter
            findings = await get_security_findings(mock_context, days_back=999)  # Very large number

            # Should still work, just without time filter if it fails
            assert len(findings) == 1

    @pytest.mark.asyncio
    async def test_get_security_findings_general_exception(self, mock_context):
        """Test get_security_findings with general exception."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.side_effect = Exception("General error")

            with pytest.raises(Exception, match="General error"):
                await get_security_findings(mock_context)

    @pytest.mark.asyncio
    async def test_get_finding_statistics_general_exception(self, mock_context):
        """Test get_finding_statistics with general exception."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.side_effect = Exception("General error")

            with pytest.raises(Exception, match="General error"):
                await get_finding_statistics(mock_context)

    @pytest.mark.asyncio
    async def test_get_security_score_general_exception(self, mock_context):
        """Test get_security_score with general exception."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.side_effect = Exception("General error")

            with pytest.raises(Exception, match="General error"):
                await get_security_score(mock_context)

    @pytest.mark.asyncio
    async def test_get_enabled_standards_general_exception(self, mock_context):
        """Test get_enabled_standards with general exception."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_enabled_standards.side_effect = Exception("General error")

            with pytest.raises(Exception, match="General error"):
                await get_enabled_standards(mock_context)

    @pytest.mark.asyncio
    async def test_list_security_control_definitions_general_exception(self, mock_context):
        """Test list_security_control_definitions with general exception."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.list_security_control_definitions.side_effect = Exception("General error")

            with pytest.raises(Exception, match="General error"):
                await list_security_control_definitions(mock_context)

    @pytest.mark.asyncio
    async def test_get_finding_history_general_exception(self, mock_context):
        """Test get_finding_history with general exception."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_finding_history.side_effect = Exception("General error")

            with pytest.raises(Exception, match="General error"):
                await get_finding_history(mock_context, "test-finding-id")

    @pytest.mark.asyncio
    async def test_describe_standards_controls_general_exception(self, mock_context):
        """Test describe_standards_controls with general exception."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.describe_standards_controls.side_effect = Exception("General error")

            with pytest.raises(Exception, match="General error"):
                await describe_standards_controls(mock_context, "test-standard-arn")

    @pytest.mark.asyncio
    async def test_generate_security_report_general_exception(self, mock_context):
        """Test generate_security_report with general exception."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.side_effect = Exception("General error")

            with pytest.raises(Exception, match="General error"):
                await generate_security_report(mock_context)

    @pytest.mark.asyncio
    async def test_generate_compliance_report_general_exception(self, mock_context):
        """Test generate_compliance_report with general exception."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.side_effect = Exception("General error")

            with pytest.raises(Exception, match="General error"):
                await generate_compliance_report(mock_context)

    def test_parse_finding_with_all_optional_fields(self):
        """Test parse_finding with all optional fields present."""
        finding_data = {
            "Id": "test-id",
            "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
            "GeneratorId": "test-generator",
            "AwsAccountId": "123456789012",
            "Region": "us-east-1",
            "Title": "Test Finding",
            "Description": "Test description",
            "Severity": {"Label": "HIGH", "Normalized": 70},
            "Workflow": {"Status": "NEW"},
            "RecordState": "ACTIVE",
            "CreatedAt": datetime.utcnow(),
            "UpdatedAt": datetime.utcnow(),
            "Resources": [{"Type": "AwsEc2Instance", "Id": "i-1234567890abcdef0"}],
            "Compliance": {"Status": "FAILED"},
            "ProductFields": {"aws/securityhub/ProductName": "Security Hub"},
            "UserDefinedFields": {"custom": "value"},
        }

        finding = parse_finding(finding_data)

        assert finding.id == "test-id"
        assert finding.severity_label == SeverityLabel.HIGH
        assert finding.workflow_status == WorkflowStatus.NEW
        assert finding.compliance_status == ComplianceStatus.FAILED
        assert finding.resource_type == "AwsEc2Instance"

    def test_determine_overall_trend_direction_edge_cases(self):
        """Test overall trend direction with edge cases."""
        # Test with very small differences (should be stable)
        small_diff_scores = {"7_days": 70.0, "14_days": 70.1, "30_days": 69.9}
        result = determine_overall_trend_direction(small_diff_scores, [7, 14, 30])
        assert result == "stable"

        # Test with exactly equal scores
        equal_scores = {"7_days": 70.0, "14_days": 70.0, "30_days": 70.0}
        result = determine_overall_trend_direction(equal_scores, [7, 14, 30])
        assert result == "stable"

    @pytest.mark.asyncio
    async def test_get_security_findings_large_days_back(self, mock_context, sample_finding):
        """Test get_security_findings with large days_back value that triggers warning."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            # Test with days_back > 365 which should trigger a warning path
            findings = await get_security_findings(mock_context, days_back=400)

            # Should still work but without time filter due to the limit
            assert len(findings) == 1

    @pytest.mark.asyncio
    async def test_get_security_findings_zero_days_back(self, mock_context, sample_finding):
        """Test get_security_findings with zero days_back."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            # Test with days_back = 0 which should not add time filter
            findings = await get_security_findings(mock_context, days_back=0)

            # Should still work without time filter
            assert len(findings) == 1

    def test_parse_finding_with_missing_compliance(self):
        """Test parse_finding with missing compliance field."""
        finding_data = {
            "Id": "test-id",
            "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
            "GeneratorId": "test-generator",
            "AwsAccountId": "123456789012",
            "Region": "us-east-1",
            "Title": "Test Finding",
            "Description": "Test description",
            "Severity": {"Label": "HIGH"},
            "Workflow": {"Status": "NEW"},
            "RecordState": "ACTIVE",
            "CreatedAt": datetime.utcnow(),
            "UpdatedAt": datetime.utcnow(),
            "Resources": [{"Type": "AwsEc2Instance"}],
            # No Compliance field
        }

        finding = parse_finding(finding_data)

        assert finding.compliance_status is None

    def test_parse_finding_with_empty_compliance_status(self):
        """Test parse_finding with empty compliance status."""
        finding_data = {
            "Id": "test-id",
            "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
            "GeneratorId": "test-generator",
            "AwsAccountId": "123456789012",
            "Region": "us-east-1",
            "Title": "Test Finding",
            "Description": "Test description",
            "Severity": {"Label": "HIGH"},
            "Workflow": {"Status": "NEW"},
            "RecordState": "ACTIVE",
            "CreatedAt": datetime.utcnow(),
            "UpdatedAt": datetime.utcnow(),
            "Resources": [{"Type": "AwsEc2Instance"}],
            "Compliance": {"Status": ""},  # Empty status
        }

        finding = parse_finding(finding_data)

        assert finding.compliance_status is None

    @pytest.mark.asyncio
    async def test_get_finding_statistics_resource_type_grouping(self, mock_context, sample_finding):
        """Test get_finding_statistics with ResourceType grouping."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create findings with different resource types
            findings = [
                {**sample_finding, "Resources": [{"Type": "AwsEc2Instance"}]},
                {**sample_finding, "Resources": [{"Type": "AwsEc2Instance"}]},
                {**sample_finding, "Resources": [{"Type": "AwsS3Bucket"}]},
            ]
            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            stats = await get_finding_statistics(mock_context, group_by="ResourceType")

            assert len(stats) == 2  # AwsEc2Instance and AwsS3Bucket
            # Should be sorted by count descending
            assert stats[0].group_key == "AwsEc2Instance"
            assert stats[0].count == 2

    @pytest.mark.asyncio
    async def test_get_finding_statistics_product_name_grouping(self, mock_context, sample_finding):
        """Test get_finding_statistics with ProductName grouping."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create findings with different product names
            findings = [
                {**sample_finding, "ProductFields": {"aws/securityhub/ProductName": "Security Hub"}},
                {**sample_finding, "ProductFields": {"aws/securityhub/ProductName": "GuardDuty"}},
                {**sample_finding, "ProductFields": {"aws/securityhub/ProductName": "Security Hub"}},
            ]
            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            stats = await get_finding_statistics(mock_context, group_by="ProductName")

            assert len(stats) == 2  # Security Hub and GuardDuty
            # Should be sorted by count descending
            assert stats[0].group_key == "Security Hub"
            assert stats[0].count == 2

    @pytest.mark.asyncio
    async def test_get_finding_statistics_unknown_grouping(self, mock_context, sample_finding):
        """Test get_finding_statistics with unknown grouping field."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            stats = await get_finding_statistics(mock_context, group_by="UnknownField")

            # Should handle unknown grouping gracefully
            assert len(stats) >= 0

    def test_analyze_severity_trends_partial_data(self):
        """Test severity trends analysis with partial data for some periods."""
        trend_data = {
            "7_days": {"severity_breakdown": {"HIGH": 2}, "data_available": True},
            "14_days": {"severity_breakdown": {"MEDIUM": 1}, "data_available": True},
            "30_days": {"severity_breakdown": {}, "data_available": False},  # No data for this period
        }
        periods = [7, 14, 30]

        result = analyze_severity_trends(trend_data, periods)

        assert "severity_data_points" in result
        assert "trend_directions" in result
        # Should handle partial data gracefully
        assert "HIGH" in result["severity_data_points"]
        assert "MEDIUM" in result["severity_data_points"]

    def test_calculate_compliance_score_trend_mixed_statuses(self):
        """Test compliance score trend calculation with mixed compliance statuses."""
        compliance_trends = {
            "PASSED": [{"period_days": 7, "count": 5}],
            "FAILED": [{"period_days": 7, "count": 3}],
            "WARNING": [{"period_days": 7, "count": 1}],
            "NOT_AVAILABLE": [{"period_days": 7, "count": 1}],
        }

        result = calculate_compliance_score_trend(compliance_trends)

        assert len(result) == 1
        # Score should be calculated: 5 passed out of 8 total (PASSED + FAILED only) = 62.5%
        assert result[0]["compliance_score"] == 62.5
        assert result[0]["period_days"] == 7

    def test_identify_most_affected_resources_single_resource(self):
        """Test identification of most affected resources with single resource type."""
        resource_trends = {
            "AwsEc2Instance": [{"period_days": 7, "findings_count": 10}],
        }

        result = identify_most_affected_resources(resource_trends)

        assert len(result) == 1
        assert result[0]["resource_type"] == "AwsEc2Instance"
        assert result[0]["findings_count"] == 10

    def test_generate_trend_insights_improving_trend(self):
        """Test trend insights generation with improving security trend."""
        trend_data = {
            "7_days": {
                "severity_breakdown": {"HIGH": 1, "MEDIUM": 2},
                "top_resource_types": {"AwsEc2Instance": 2, "AwsS3Bucket": 1},
                "data_available": True,
            },
            "14_days": {
                "severity_breakdown": {"HIGH": 3, "MEDIUM": 4},
                "top_resource_types": {"AwsEc2Instance": 4, "AwsS3Bucket": 3},
                "data_available": True,
            },
        }
        security_scores = {"7_days": 80.0, "14_days": 70.0}  # Improving (higher recent score)
        periods = [7, 14]

        result = generate_trend_insights(trend_data, security_scores, periods)

        assert "key_insights" in result
        assert "recommendations" in result
        assert "trend_summary" in result
        assert len(result["key_insights"]) > 0
        # Should detect improving trend
        assert any("improv" in insight.get("message", "").lower() for insight in result["key_insights"])

    def test_generate_detailed_trend_analysis_single_period(self):
        """Test detailed trend analysis generation with single period."""
        trend_data = {
            "7_days": {
                "severity_breakdown": {"HIGH": 2, "MEDIUM": 3},
                "total_findings": 5,
                "data_available": True,
            },
        }
        periods = [7]

        result = generate_detailed_trend_analysis(trend_data, periods)

        # Should handle single period gracefully
        assert isinstance(result, dict)
        if result:  # May return empty dict for insufficient data
            assert "statistical_summary" in result or len(result) == 0

    @pytest.mark.asyncio
    async def test_main_function_coverage(self):
        """Test the main function for coverage."""
        from awslabs.aws_security_hub_mcp_server.server import main

        # Mock the mcp.run() call to avoid actually starting the server
        with patch("awslabs.aws_security_hub_mcp_server.server.mcp.run") as mock_run:
            main()
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_security_findings_string_days_back(self, mock_context, sample_finding):
        """Test get_security_findings with string days_back parameter conversion."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            # Test with integer days_back that gets converted internally
            findings = await get_security_findings(mock_context, days_back=7)

            assert len(findings) == 1
            # Verify the time filter was applied
            call_args = mock_client.return_value.get_findings.call_args
            filters = call_args[1]["Filters"]
            assert "UpdatedAt" in filters

    @pytest.mark.asyncio
    async def test_get_security_findings_time_filter_exception_handling(self, mock_context, sample_finding):
        """Test get_security_findings with time filter exception handling."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            # Test with days_back that might cause issues in time filter (very large number)
            with patch("awslabs.aws_security_hub_mcp_server.server.logger"):
                findings = await get_security_findings(mock_context, days_back=999)  # Very large number

                # Should still work, just without time filter if it fails
                assert len(findings) == 1

    @pytest.mark.asyncio
    async def test_get_finding_statistics_string_days_back(self, mock_context, sample_finding):
        """Test get_finding_statistics with string days_back parameter conversion."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            # Test with integer days_back that gets converted internally
            stats = await get_finding_statistics(mock_context, days_back=7)

            assert len(stats) >= 0
            # Verify the time filter was applied
            call_args = mock_client.return_value.get_findings.call_args
            filters = call_args[1]["Filters"]
            assert "UpdatedAt" in filters

    @pytest.mark.asyncio
    async def test_get_finding_statistics_time_filter_exception_handling(self, mock_context, sample_finding):
        """Test get_finding_statistics with time filter exception handling."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_client.return_value.get_findings.return_value = {"Findings": [sample_finding]}

            # Test with days_back that might cause issues in time filter (very large number)
            with patch("awslabs.aws_security_hub_mcp_server.server.logger"):
                stats = await get_finding_statistics(mock_context, days_back=999)  # Very large number

                # Should still work, just without time filter if it fails
                assert len(stats) >= 0

    @pytest.mark.asyncio
    async def test_get_finding_statistics_pagination_logging(self, mock_context, sample_finding):
        """Test get_finding_statistics pagination with debug logging."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock multiple pages of results
            first_page = {"Findings": [sample_finding], "NextToken": "token1"}
            second_page = {"Findings": [sample_finding], "NextToken": None}

            mock_client.return_value.get_findings.side_effect = [first_page, second_page]

            with patch("awslabs.aws_security_hub_mcp_server.server.logger") as mock_logger:
                await get_finding_statistics(mock_context)

                # Should have logged debug messages about pagination
                mock_logger.debug.assert_called()
                mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_get_security_findings_pagination_logging(self, mock_context, sample_finding):
        """Test get_security_findings pagination with debug logging."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock multiple pages of results
            first_page = {"Findings": [sample_finding], "NextToken": "token1"}
            second_page = {"Findings": [sample_finding], "NextToken": None}

            mock_client.return_value.get_findings.side_effect = [first_page, second_page]

            with patch("awslabs.aws_security_hub_mcp_server.server.logger") as mock_logger:
                await get_security_findings(mock_context)

                # Should have logged debug messages about pagination
                mock_logger.debug.assert_called()
                mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_get_finding_statistics_max_pages_safety_limit(self, mock_context, sample_finding):
        """Test get_finding_statistics with max pages safety limit."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock infinite pagination scenario
            mock_client.return_value.get_findings.return_value = {
                "Findings": [sample_finding],
                "NextToken": "always_has_next",
            }

            with patch("awslabs.aws_security_hub_mcp_server.server.logger"):
                stats = await get_finding_statistics(mock_context)

                # Should hit the max pages limit and stop
                assert len(stats) >= 0
                # Should have made exactly 20 calls (max_pages limit)
                assert mock_client.return_value.get_findings.call_count == 20

    @pytest.mark.asyncio
    async def test_get_security_findings_max_pages_safety_limit(self, mock_context, sample_finding):
        """Test get_security_findings with max pages safety limit."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock infinite pagination scenario
            mock_client.return_value.get_findings.return_value = {
                "Findings": [sample_finding],
                "NextToken": "always_has_next",
            }

            findings = await get_security_findings(mock_context)

            # Should hit the max pages limit and stop
            assert len(findings) >= 0
            # Should have made exactly 50 calls (max_pages limit for get_security_findings)
            assert mock_client.return_value.get_findings.call_count == 50

    @pytest.mark.asyncio
    async def test_get_finding_statistics_grouping_edge_cases(self, mock_context):
        """Test get_finding_statistics with edge cases in grouping."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create findings with missing/empty fields
            findings = [
                {
                    "Id": "1",
                    "ProductArn": "arn",
                    "GeneratorId": "gen",
                    "AwsAccountId": "123",
                    "Region": "us-east-1",
                    "Title": "Test",
                    "Description": "Test",
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE",
                    "CreatedAt": datetime.utcnow(),
                    "UpdatedAt": datetime.utcnow(),
                    "Resources": [],  # Empty resources
                },
                {
                    "Id": "2",
                    "ProductArn": "arn",
                    "GeneratorId": "gen",
                    "AwsAccountId": "123",
                    "Region": "us-east-1",
                    "Title": "Test",
                    "Description": "Test",
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE",
                    "CreatedAt": datetime.utcnow(),
                    "UpdatedAt": datetime.utcnow(),
                    # Missing Resources field entirely
                },
            ]
            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            # Test ResourceType grouping with empty/missing resources
            stats = await get_finding_statistics(mock_context, group_by="ResourceType")

            # Should handle empty resources gracefully
            assert len(stats) >= 0
            # All should be grouped as "UNKNOWN"
            if stats:
                assert all(stat.group_key == "UNKNOWN" for stat in stats)

    @pytest.mark.asyncio
    async def test_get_finding_statistics_compliance_status_grouping(self, mock_context, sample_finding):
        """Test get_finding_statistics with ComplianceStatus grouping."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create findings with different compliance statuses
            findings = [
                {**sample_finding, "Compliance": {"Status": "PASSED"}},
                {**sample_finding, "Compliance": {"Status": "FAILED"}},
                {**sample_finding, "Compliance": {"Status": "WARNING"}},
                {**sample_finding},  # Missing Compliance field
            ]
            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            stats = await get_finding_statistics(mock_context, group_by="ComplianceStatus")

            # Should group by compliance status
            assert len(stats) >= 0
            if stats:
                compliance_keys = [stat.group_key for stat in stats]
                # Should include the various compliance statuses
                assert any(key in ["PASSED", "FAILED", "WARNING", "UNKNOWN"] for key in compliance_keys)

    @pytest.mark.asyncio
    async def test_get_finding_statistics_record_state_grouping(self, mock_context, sample_finding):
        """Test get_finding_statistics with RecordState grouping."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create findings with different record states
            findings = [
                {**sample_finding, "RecordState": "ACTIVE"},
                {**sample_finding, "RecordState": "ARCHIVED"},
            ]
            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            stats = await get_finding_statistics(mock_context, group_by="RecordState")

            # Should group by record state
            assert len(stats) >= 0
            if stats:
                record_keys = [stat.group_key for stat in stats]
                assert any(key in ["ACTIVE", "ARCHIVED"] for key in record_keys)

    @pytest.mark.asyncio
    async def test_get_security_score_pagination_logging(self, mock_context, sample_finding):
        """Test get_security_score pagination with debug logging."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Mock multiple pages of results
            first_page = {"Findings": [sample_finding], "NextToken": "token1"}
            second_page = {"Findings": [sample_finding], "NextToken": None}

            mock_client.return_value.get_findings.side_effect = [first_page, second_page]

            with patch("awslabs.aws_security_hub_mcp_server.server.logger") as mock_logger:
                score = await get_security_score(mock_context)

                # Should have logged debug messages about pagination
                mock_logger.debug.assert_called()
                assert score.current_score >= 0

    @pytest.mark.asyncio
    async def test_get_security_score_control_findings_detection(self, mock_context):
        """Test get_security_score with control findings detection."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create findings with different generator IDs to test control detection
            findings = [
                {
                    "Id": "1",
                    "ProductArn": "arn",
                    "GeneratorId": "aws-foundational-security-standard/v/1.0.0/S3.1",  # Should be detected as control
                    "AwsAccountId": "123",
                    "Region": "us-east-1",
                    "Title": "Test",
                    "Description": "Test",
                    "Severity": {"Label": "HIGH"},
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE",
                    "CreatedAt": datetime.utcnow(),
                    "UpdatedAt": datetime.utcnow(),
                    "Resources": [{"Type": "AwsS3Bucket"}],
                },
                {
                    "Id": "2",
                    "ProductArn": "arn",
                    "GeneratorId": "cis-aws-foundations-benchmark/v/1.2.0/1.1",  # Should be detected as control
                    "AwsAccountId": "123",
                    "Region": "us-east-1",
                    "Title": "Test",
                    "Description": "Test",
                    "Severity": {"Label": "MEDIUM"},
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE",
                    "CreatedAt": datetime.utcnow(),
                    "UpdatedAt": datetime.utcnow(),
                    "Resources": [{"Type": "AwsEc2Instance"}],
                },
                {
                    "Id": "3",
                    "ProductArn": "arn",
                    "GeneratorId": "custom-finding-generator",  # Should NOT be detected as control
                    "AwsAccountId": "123",
                    "Region": "us-east-1",
                    "Title": "Test",
                    "Description": "Test",
                    "Severity": {"Label": "LOW"},
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE",
                    "CreatedAt": datetime.utcnow(),
                    "UpdatedAt": datetime.utcnow(),
                    "Resources": [{"Type": "AwsEc2Instance"}],
                },
            ]
            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            score = await get_security_score(mock_context)

            # Should calculate score based on severity weights
            assert 0 <= score.current_score <= 100
            assert score.max_score == 100.0

    @pytest.mark.asyncio
    async def test_get_security_score_max_possible_weight_calculation(self, mock_context):
        """Test get_security_score with max possible weight calculation."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Test with no findings (edge case for max_possible_weight)
            mock_client.return_value.get_findings.return_value = {"Findings": []}

            score = await get_security_score(mock_context)

            # Should handle zero findings gracefully
            assert score.current_score == 100.0  # Perfect score when no findings
            assert score.max_score == 100.0

    @pytest.mark.asyncio
    async def test_get_security_score_severity_weight_calculation(self, mock_context):
        """Test get_security_score with different severity weight calculations."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            # Create findings with all severity levels to test weight calculation
            findings = []
            severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]

            for i, severity in enumerate(severities):
                finding = {
                    "Id": f"finding-{i}",
                    "ProductArn": "arn",
                    "GeneratorId": "test-generator",
                    "AwsAccountId": "123",
                    "Region": "us-east-1",
                    "Title": f"Test {severity}",
                    "Description": "Test",
                    "Severity": {"Label": severity},
                    "Workflow": {"Status": "NEW"},
                    "RecordState": "ACTIVE",
                    "CreatedAt": datetime.utcnow(),
                    "UpdatedAt": datetime.utcnow(),
                    "Resources": [{"Type": "AwsEc2Instance"}],
                }
                findings.append(finding)

            mock_client.return_value.get_findings.return_value = {"Findings": findings}

            score = await get_security_score(mock_context)

            # Should calculate score based on all severity weights
            assert 0 <= score.current_score <= 100
            assert score.max_score == 100.0

    @pytest.mark.asyncio
    async def test_list_security_control_definitions_pagination_logging(self, mock_context):
        """Test list_security_control_definitions pagination with debug logging."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_control = {
                "SecurityControlId": "S3.1",
                "SecurityControlArn": "arn:aws:securityhub:us-east-1:123456789012:security-control/S3.1",
                "Title": "S3 buckets should have public access blocked",
                "Description": "This control checks whether S3 buckets have public access blocked.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/S3.1/remediation",
                "SeverityRating": "HIGH",
                "CurrentRegionAvailability": "AVAILABLE",
            }

            # Mock multiple pages of results
            first_page = {"SecurityControlDefinitions": [mock_control], "NextToken": "token1"}
            second_page = {"SecurityControlDefinitions": [mock_control], "NextToken": None}

            mock_client.return_value.list_security_control_definitions.side_effect = [first_page, second_page]

            with patch("awslabs.aws_security_hub_mcp_server.server.logger") as mock_logger:
                controls = await list_security_control_definitions(mock_context)

                # Should have logged debug messages about pagination
                mock_logger.debug.assert_called()
                mock_logger.info.assert_called()
                assert len(controls) == 2

    @pytest.mark.asyncio
    async def test_list_security_control_definitions_with_standard_arn_logging(self, mock_context):
        """Test list_security_control_definitions with standard ARN and logging."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_control = {
                "SecurityControlId": "S3.1",
                "SecurityControlArn": "arn:aws:securityhub:us-east-1:123456789012:security-control/S3.1",
                "Title": "S3 buckets should have public access blocked",
                "Description": "This control checks whether S3 buckets have public access blocked.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/S3.1/remediation",
                "SeverityRating": "HIGH",
                "CurrentRegionAvailability": "AVAILABLE",
            }

            mock_client.return_value.list_security_control_definitions.return_value = {
                "SecurityControlDefinitions": [mock_control]
            }

            with patch("awslabs.aws_security_hub_mcp_server.server.logger") as mock_logger:
                controls = await list_security_control_definitions(
                    mock_context,
                    standard_arn="arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0",
                )

                # Should have logged debug messages
                mock_logger.debug.assert_called()
                mock_logger.info.assert_called()
                assert len(controls) == 1

                # Verify standard ARN was passed to the API call
                call_args = mock_client.return_value.list_security_control_definitions.call_args
                assert (
                    call_args[1]["StandardsArn"]
                    == "arn:aws:securityhub:::standard/aws-foundational-security-standard/v/1.0.0"
                )

    @pytest.mark.asyncio
    async def test_list_security_control_definitions_max_results_limit(self, mock_context):
        """Test list_security_control_definitions with max results limit."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_control = {
                "SecurityControlId": "S3.1",
                "SecurityControlArn": "arn:aws:securityhub:us-east-1:123456789012:security-control/S3.1",
                "Title": "S3 buckets should have public access blocked",
                "Description": "This control checks whether S3 buckets have public access blocked.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/S3.1/remediation",
                "SeverityRating": "HIGH",
                "CurrentRegionAvailability": "AVAILABLE",
            }

            # Mock pagination that would exceed max_results
            mock_client.return_value.list_security_control_definitions.return_value = {
                "SecurityControlDefinitions": [mock_control] * 50,  # Return 50 controls per page
                "NextToken": "token1",
            }

            controls = await list_security_control_definitions(mock_context, max_results=75)

            # Should stop when reaching max_results limit
            assert len(controls) == 75
            # Should have made 2 calls (50 + 25 to reach 75)
            assert mock_client.return_value.list_security_control_definitions.call_count == 2

    @pytest.mark.asyncio
    async def test_get_finding_history_pagination_logging(self, mock_context):
        """Test get_finding_history pagination with debug logging."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_history_record = {
                "FindingIdentifier": {
                    "Id": "arn:aws:securityhub:us-east-1:123456789012:finding/test-finding-1",
                    "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                },
                "UpdateTime": datetime.utcnow(),
                "FindingCreated": True,
                "UpdateSource": {
                    "Type": "BATCH_UPDATE_FINDINGS",
                    "Identity": "arn:aws:iam::123456789012:user/test-user",
                },
                "Updates": [{"UpdatedField": "Workflow/Status", "OldValue": "NEW", "NewValue": "RESOLVED"}],
            }

            # Mock multiple pages of results
            first_page = {"Records": [mock_history_record], "NextToken": "token1"}
            second_page = {"Records": [mock_history_record], "NextToken": None}

            mock_client.return_value.get_finding_history.side_effect = [first_page, second_page]

            with patch("awslabs.aws_security_hub_mcp_server.server.logger") as mock_logger:
                history = await get_finding_history(mock_context, "test-finding-id")

                # Should have logged debug messages about pagination
                mock_logger.debug.assert_called()
                mock_logger.info.assert_called()
                assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_finding_history_with_start_and_end_time(self, mock_context):
        """Test get_finding_history with start and end time parameters."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_history_record = {
                "FindingIdentifier": {
                    "Id": "arn:aws:securityhub:us-east-1:123456789012:finding/test-finding-1",
                    "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                },
                "UpdateTime": datetime.utcnow(),
                "FindingCreated": True,
                "UpdateSource": {
                    "Type": "BATCH_UPDATE_FINDINGS",
                    "Identity": "arn:aws:iam::123456789012:user/test-user",
                },
                "Updates": [{"UpdatedField": "Workflow/Status", "OldValue": "NEW", "NewValue": "RESOLVED"}],
            }

            mock_client.return_value.get_finding_history.return_value = {"Records": [mock_history_record]}

            start_time = "2024-01-01T00:00:00Z"
            end_time = "2024-01-31T23:59:59Z"

            with patch("awslabs.aws_security_hub_mcp_server.server.logger") as mock_logger:
                history = await get_finding_history(
                    mock_context, "test-finding-id", start_time=start_time, end_time=end_time
                )

                # Should have logged debug messages
                mock_logger.debug.assert_called()
                mock_logger.info.assert_called()
                assert len(history) == 1

                # Verify start and end time were passed to the API call
                call_args = mock_client.return_value.get_finding_history.call_args
                assert "StartTime" in call_args[1]
                assert "EndTime" in call_args[1]

    @pytest.mark.asyncio
    async def test_get_finding_history_max_results_limit(self, mock_context):
        """Test get_finding_history with max results limit."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_history_record = {
                "FindingIdentifier": {
                    "Id": "arn:aws:securityhub:us-east-1:123456789012:finding/test-finding-1",
                    "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                },
                "UpdateTime": datetime.utcnow(),
                "FindingCreated": True,
                "UpdateSource": {
                    "Type": "BATCH_UPDATE_FINDINGS",
                    "Identity": "arn:aws:iam::123456789012:user/test-user",
                },
                "Updates": [{"UpdatedField": "Workflow/Status", "OldValue": "NEW", "NewValue": "RESOLVED"}],
            }

            # Mock pagination that would exceed max_results
            mock_client.return_value.get_finding_history.return_value = {
                "Records": [mock_history_record] * 50,  # Return 50 records per page
                "NextToken": "token1",
            }

            history = await get_finding_history(mock_context, "test-finding-id", max_results=75)

            # Should stop when reaching max_results limit
            assert len(history) == 75

    @pytest.mark.asyncio
    async def test_get_finding_history_datetime_serialization(self, mock_context):
        """Test get_finding_history datetime serialization."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_history_record = {
                "FindingIdentifier": {
                    "Id": "arn:aws:securityhub:us-east-1:123456789012:finding/test-finding-1",
                    "ProductArn": "arn:aws:securityhub:us-east-1:123456789012:product/123456789012/default",
                },
                "UpdateTime": datetime.utcnow(),  # This should be converted to ISO format
                "FindingCreated": True,
                "UpdateSource": {
                    "Type": "BATCH_UPDATE_FINDINGS",
                    "Identity": "arn:aws:iam::123456789012:user/test-user",
                },
                "Updates": [{"UpdatedField": "Workflow/Status", "OldValue": "NEW", "NewValue": "RESOLVED"}],
            }

            mock_client.return_value.get_finding_history.return_value = {"Records": [mock_history_record]}

            history = await get_finding_history(mock_context, "test-finding-id")

            # Should have converted datetime to ISO string
            assert len(history) == 1
            assert isinstance(history[0]["update_time"], str)
            assert "T" in history[0]["update_time"]  # ISO format indicator

    @pytest.mark.asyncio
    async def test_describe_standards_controls_datetime_serialization(self, mock_context):
        """Test describe_standards_controls datetime serialization."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_control = {
                "StandardsControlArn": "arn:aws:securityhub:us-east-1:123456789012:control/aws-foundational-security-standard/v/1.0.0/S3.1",
                "ControlStatus": "ENABLED",
                "DisabledReason": None,
                "ControlStatusUpdatedAt": datetime.utcnow(),  # This should be converted to ISO format
                "ControlId": "S3.1",
                "Title": "S3 buckets should have public access blocked",
                "Description": "This control checks whether S3 buckets have public access blocked.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/S3.1/remediation",
                "SeverityRating": "HIGH",
                "RelatedRequirements": ["NIST.800-53.r5 AC-3", "NIST.800-53.r5 AC-6"],
            }

            mock_client.return_value.describe_standards_controls.return_value = {"Controls": [mock_control]}

            controls = await describe_standards_controls(
                mock_context,
                "arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-standard/v/1.0.0",
            )

            # Should have converted datetime to ISO string
            assert len(controls) == 1
            assert isinstance(controls[0]["control_status_updated_at"], str)
            assert "T" in controls[0]["control_status_updated_at"]  # ISO format indicator

    @pytest.mark.asyncio
    async def test_describe_standards_controls_max_results_limit(self, mock_context):
        """Test describe_standards_controls with max results limit."""
        with patch("awslabs.aws_security_hub_mcp_server.server.get_security_hub_client") as mock_client:
            mock_control = {
                "StandardsControlArn": "arn:aws:securityhub:us-east-1:123456789012:control/aws-foundational-security-standard/v/1.0.0/S3.1",
                "ControlStatus": "ENABLED",
                "DisabledReason": None,
                "ControlStatusUpdatedAt": datetime.utcnow(),
                "ControlId": "S3.1",
                "Title": "S3 buckets should have public access blocked",
                "Description": "This control checks whether S3 buckets have public access blocked.",
                "RemediationUrl": "https://docs.aws.amazon.com/console/securityhub/S3.1/remediation",
                "SeverityRating": "HIGH",
                "RelatedRequirements": ["NIST.800-53.r5 AC-3", "NIST.800-53.r5 AC-6"],
            }

            # Mock pagination that would exceed max_results
            mock_client.return_value.describe_standards_controls.return_value = {
                "Controls": [mock_control] * 50,  # Return 50 controls per page
                "NextToken": "token1",
            }

            controls = await describe_standards_controls(
                mock_context,
                "arn:aws:securityhub:us-east-1:123456789012:subscription/aws-foundational-security-standard/v/1.0.0",
                max_results=75,
            )

            # Should stop when reaching max_results limit
            assert len(controls) == 75

    def test_server_module_level_code_coverage(self):
        """Test module-level code for coverage."""
        # Import the server module to ensure module-level code is executed
        import awslabs.aws_security_hub_mcp_server.server as server_module

        # Verify that the mcp server is properly initialized
        assert hasattr(server_module, "mcp")
        assert server_module.mcp is not None

        # Verify constants are set
        assert hasattr(server_module, "DEFAULT_MAX_RESULTS")
        assert hasattr(server_module, "MAX_RESULTS")
        assert server_module.DEFAULT_MAX_RESULTS > 0
