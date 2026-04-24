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
"""Tests for the Trusted Advisor MCP Server formatters."""

import pytest
from awslabs.trusted_advisor_mcp_server.formatters import (
    format_checks_list,
    format_cost_optimization_summary,
    format_lifecycle_update_result,
    format_organization_recommendations,
    format_recommendation_detail,
    format_recommendations_list,
    format_security_summary,
    format_service_limits_summary,
)


class TestFormatChecksList:
    """Tests for format_checks_list."""

    def test_empty_checks(self):
        """Test formatting an empty list of checks."""
        result = format_checks_list([])
        assert 'No Trusted Advisor checks found' in result

    def test_single_check(self, check_summary_data):
        """Test formatting a single check."""
        result = format_checks_list([check_summary_data])
        assert 'Amazon S3 Bucket Permissions' in result
        assert 'security' in result.lower() or 'Security' in result
        assert 'Amazon S3' in result

    def test_multiple_checks_grouped_by_pillar(self, check_summaries_data):
        """Test that checks are grouped by pillar."""
        result = format_checks_list(check_summaries_data)
        assert 'Security' in result
        assert 'Cost Optimizing' in result
        assert '3 found' in result

    def test_check_with_description(self, check_summary_data):
        """Test that check descriptions are included."""
        result = format_checks_list([check_summary_data])
        assert 'Checks the permissions' in result

    def test_long_description_truncated(self):
        """Test that long descriptions are truncated."""
        check = {
            'arn': 'arn:aws:trustedadvisor:::check/test',
            'id': 'test',
            'name': 'Test Check',
            'description': 'A' * 300,
            'pillar': 'security',
        }
        result = format_checks_list([check])
        assert '...' in result


class TestFormatRecommendationsList:
    """Tests for format_recommendations_list."""

    def test_empty_recommendations(self):
        """Test formatting an empty list of recommendations."""
        result = format_recommendations_list([])
        assert 'No Trusted Advisor recommendations found' in result

    def test_single_recommendation(self, recommendation_summary_data):
        """Test formatting a single recommendation."""
        result = format_recommendations_list([recommendation_summary_data])
        assert 'Low Utilization Amazon EC2 Instances' in result
        assert '[WARNING]' in result
        assert 'Cost Optimizing' in result
        assert '$150.50' in result

    def test_multiple_recommendations(self, recommendation_summaries_data):
        """Test formatting multiple recommendations."""
        result = format_recommendations_list(recommendation_summaries_data)
        assert '2 found' in result
        assert 'Low Utilization Amazon EC2 Instances' in result
        assert 'Idle Load Balancers' in result

    def test_recommendation_with_resources(self, recommendation_summary_data):
        """Test that resource counts are included."""
        result = format_recommendations_list([recommendation_summary_data])
        assert '5 OK' in result
        assert '3 Warning' in result
        assert '0 Error' in result

    def test_recommendation_with_savings(self, recommendation_summary_data):
        """Test that savings information is included."""
        result = format_recommendations_list([recommendation_summary_data])
        assert 'USD' in result
        assert '$150.50' in result


class TestFormatRecommendationDetail:
    """Tests for format_recommendation_detail."""

    def test_basic_detail(self, recommendation_detail_data, recommendation_resources_data):
        """Test formatting basic recommendation detail."""
        result = format_recommendation_detail(
            recommendation_detail_data, recommendation_resources_data
        )
        assert 'Low Utilization Amazon EC2 Instances' in result
        assert '[WARNING]' in result
        assert 'pending_response' in result

    def test_detail_with_resources(self, recommendation_detail_data, recommendation_resources_data):
        """Test that affected resources are listed."""
        result = format_recommendation_detail(
            recommendation_detail_data, recommendation_resources_data
        )
        assert 'i-0123456789abcdef0' in result
        assert 'i-0abcdef1234567890' in result
        assert 'us-east-1' in result
        assert 'us-west-2' in result

    def test_detail_with_savings(self, recommendation_detail_data, recommendation_resources_data):
        """Test that savings info appears in detail view."""
        result = format_recommendation_detail(
            recommendation_detail_data, recommendation_resources_data
        )
        assert 'Monthly' in result
        assert '$150.50' in result
        assert 'Annual' in result

    def test_detail_with_no_resources(self, recommendation_detail_data):
        """Test formatting when no resources are available."""
        result = format_recommendation_detail(recommendation_detail_data, [])
        assert 'Low Utilization Amazon EC2 Instances' in result
        assert 'Affected Resources' not in result

    def test_detail_with_metadata(self, recommendation_detail_data, recommendation_resources_data):
        """Test that resource metadata is displayed."""
        result = format_recommendation_detail(
            recommendation_detail_data, recommendation_resources_data
        )
        assert 'Instance Type' in result
        assert 't2.large' in result

    def test_detail_many_resources_truncated(self, recommendation_detail_data):
        """Test that more than 50 resources are truncated."""
        many_resources = [
            {
                'arn': f'arn:aws:ec2:us-east-1:123456789012:instance/i-{i:016d}',
                'awsResourceId': f'i-{i:016d}',
                'regionCode': 'us-east-1',
                'status': 'warning',
            }
            for i in range(60)
        ]
        result = format_recommendation_detail(recommendation_detail_data, many_resources)
        assert '... and 10 more resources' in result


class TestFormatCostOptimizationSummary:
    """Tests for format_cost_optimization_summary."""

    def test_empty_recommendations(self):
        """Test formatting with no cost optimization recommendations."""
        result = format_cost_optimization_summary([])
        assert 'No active cost optimization recommendations' in result
        assert 'well-optimized' in result

    def test_with_recommendations(self, recommendation_summaries_data):
        """Test formatting cost optimization summary."""
        result = format_cost_optimization_summary(recommendation_summaries_data)
        assert 'Cost Optimization Summary' in result
        assert '$175.50' in result  # 150.50 + 25.00
        assert 'Annual' in result
        assert 'Low Utilization Amazon EC2 Instances' in result

    def test_sorted_by_savings(self, recommendation_summaries_data):
        """Test that recommendations are sorted by savings descending."""
        result = format_cost_optimization_summary(recommendation_summaries_data)
        ec2_pos = result.find('Low Utilization Amazon EC2')
        elb_pos = result.find('Idle Load Balancers')
        assert ec2_pos < elb_pos  # Higher savings first


class TestFormatSecuritySummary:
    """Tests for format_security_summary."""

    def test_empty_recommendations(self):
        """Test formatting with no security recommendations."""
        result = format_security_summary([])
        assert 'No security recommendations found' in result

    def test_with_recommendations(self, security_recommendations_data):
        """Test formatting security summary with mixed statuses."""
        result = format_security_summary(security_recommendations_data)
        assert 'Security Summary' in result
        assert 'Passed: 1' in result
        assert 'Warnings: 1' in result
        assert 'Errors: 1' in result

    def test_active_issues_listed(self, security_recommendations_data):
        """Test that active issues are listed."""
        result = format_security_summary(security_recommendations_data)
        assert 'Security Groups - Unrestricted Access' in result
        assert 'S3 Bucket Permissions' in result
        assert '[ERROR]' in result
        assert '[WARNING]' in result

    def test_errors_listed_first(self, security_recommendations_data):
        """Test that errors appear before warnings."""
        result = format_security_summary(security_recommendations_data)
        error_pos = result.find('Security Groups - Unrestricted Access')
        warning_pos = result.find('S3 Bucket Permissions')
        assert error_pos < warning_pos


class TestFormatServiceLimitsSummary:
    """Tests for format_service_limits_summary."""

    def test_empty_recommendations(self):
        """Test formatting with no service limit concerns."""
        result = format_service_limits_summary([])
        assert 'No service limit concerns found' in result

    def test_with_recommendations(self, service_limits_recommendations_data):
        """Test formatting service limits summary."""
        result = format_service_limits_summary(service_limits_recommendations_data)
        assert 'Service Limits Summary' in result
        assert 'VPC Elastic IP Address Limit' in result
        assert 'EC2 On-Demand Instances Limit' in result

    def test_errors_listed_first(self, service_limits_recommendations_data):
        """Test that errors appear before warnings."""
        result = format_service_limits_summary(service_limits_recommendations_data)
        error_pos = result.find('EC2 On-Demand Instances Limit')
        warning_pos = result.find('VPC Elastic IP Address Limit')
        assert error_pos < warning_pos


class TestFormatOrganizationRecommendations:
    """Tests for format_organization_recommendations."""

    def test_empty_recommendations(self):
        """Test formatting with no organization recommendations."""
        result = format_organization_recommendations([])
        assert 'No organization-wide recommendations found' in result

    def test_with_recommendations(self, organization_recommendations_data):
        """Test formatting organization recommendations."""
        result = format_organization_recommendations(organization_recommendations_data)
        assert 'Organization Recommendations' in result
        assert '2 found' in result
        assert 'Low Utilization Amazon EC2 Instances' in result
        assert 'Security Groups - Unrestricted Access' in result

    def test_status_counts(self, organization_recommendations_data):
        """Test that status counts are shown."""
        result = format_organization_recommendations(organization_recommendations_data)
        assert 'Warnings: 1' in result
        assert 'Errors: 1' in result


class TestFormatLifecycleUpdateResult:
    """Tests for format_lifecycle_update_result."""

    def test_basic_update(self):
        """Test formatting a basic lifecycle update."""
        result = format_lifecycle_update_result(
            'arn:aws:trustedadvisor::123456789012:recommendation/rec-001',
            'dismissed',
        )
        assert 'Lifecycle Updated' in result
        assert 'dismissed' in result
        assert 'rec-001' in result

    def test_update_with_reason(self):
        """Test formatting an update with a reason."""
        result = format_lifecycle_update_result(
            'arn:aws:trustedadvisor::123456789012:recommendation/rec-001',
            'dismissed',
            'Expected behavior for our use case',
        )
        assert 'Expected behavior' in result
        assert 'Reason' in result
