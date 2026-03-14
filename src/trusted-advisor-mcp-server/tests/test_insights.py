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
"""Tests for the Trusted Advisor MCP Server insights module."""

import pytest
from awslabs.trusted_advisor_mcp_server.insights import (
    format_executive_summary,
    format_prioritized_actions,
    _get_remediation_hint,
)


@pytest.fixture
def sample_recommendations():
    """Return a mixed set of recommendations for testing."""
    return [
        {
            'arn': 'arn:1',
            'name': 'AWS Lambda Functions Using Deprecated Runtimes',
            'status': 'error',
            'pillars': ['security'],
            'awsServices': ['lambda'],
            'resourcesAggregates': {'okCount': 0, 'warningCount': 5, 'errorCount': 9},
            'pillarSpecificAggregates': {},
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
        },
        {
            'arn': 'arn:2',
            'name': 'Low Utilization Amazon EC2 Instances',
            'status': 'warning',
            'pillars': ['cost_optimizing'],
            'awsServices': ['ec2'],
            'resourcesAggregates': {'okCount': 5, 'warningCount': 3, 'errorCount': 0},
            'pillarSpecificAggregates': {
                'costOptimizing': {
                    'estimatedMonthlySavings': 160.40,
                    'estimatedMonthlySavingsCurrency': 'USD',
                }
            },
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
        },
        {
            'arn': 'arn:3',
            'name': 'MFA on Root Account',
            'status': 'ok',
            'pillars': ['security'],
            'awsServices': ['iam'],
            'resourcesAggregates': {'okCount': 1, 'warningCount': 0, 'errorCount': 0},
            'pillarSpecificAggregates': {},
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
        },
        {
            'arn': 'arn:4',
            'name': 'Underutilized Amazon EBS Volumes',
            'status': 'warning',
            'pillars': ['cost_optimizing'],
            'awsServices': ['ebs'],
            'resourcesAggregates': {'okCount': 2, 'warningCount': 13, 'errorCount': 0},
            'pillarSpecificAggregates': {
                'costOptimizing': {
                    'estimatedMonthlySavings': 60.44,
                    'estimatedMonthlySavingsCurrency': 'USD',
                }
            },
            'lastUpdatedAt': '2024-01-14T08:00:00Z',
        },
    ]


class TestGetRemediationHint:
    """Tests for _get_remediation_hint."""

    def test_known_keyword(self):
        """Test that known keywords return specific hints."""
        hint = _get_remediation_hint('AWS Lambda Functions Using Deprecated Runtimes')
        assert 'python3.12' in hint
        assert 'aws lambda' in hint.lower()

    def test_security_group_keyword(self):
        """Test security group keyword matching."""
        hint = _get_remediation_hint('Security Groups - Unrestricted Access')
        assert '0.0.0.0/0' in hint

    def test_ec2_keyword(self):
        """Test EC2 keyword matching."""
        hint = _get_remediation_hint('Low Utilization Amazon EC2 Instances')
        assert 'EC2' in hint or 'instance' in hint.lower()

    def test_ebs_keyword(self):
        """Test EBS keyword matching."""
        hint = _get_remediation_hint('Underutilized Amazon EBS Volumes')
        assert 'EBS' in hint or 'ebs' in hint.lower() or 'gp3' in hint

    def test_unknown_keyword(self):
        """Test that unknown keywords return a generic hint."""
        hint = _get_remediation_hint('Some Unknown Recommendation')
        assert 'documentation' in hint.lower() or 'guidance' in hint.lower()

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        hint1 = _get_remediation_hint('NAT Gateway Idle')
        hint2 = _get_remediation_hint('nat gateway idle')
        assert hint1 == hint2


class TestFormatPrioritizedActions:
    """Tests for format_prioritized_actions."""

    def test_empty_recommendations(self):
        """Test with empty recommendations list."""
        result = format_prioritized_actions([])
        assert 'No recommendations found' in result

    def test_all_ok_recommendations(self, sample_recommendations):
        """Test when all recommendations are OK status."""
        ok_recs = [r for r in sample_recommendations if r['status'] == 'ok']
        result = format_prioritized_actions(ok_recs)
        assert 'No actionable' in result

    def test_contains_error_items(self, sample_recommendations):
        """Test that error items appear in output."""
        result = format_prioritized_actions(sample_recommendations)
        assert 'Lambda Functions Using Deprecated Runtimes' in result
        assert '[ERROR]' in result

    def test_contains_warning_items(self, sample_recommendations):
        """Test that warning items appear in output."""
        result = format_prioritized_actions(sample_recommendations)
        assert 'Low Utilization Amazon EC2 Instances' in result
        assert '[WARNING]' in result

    def test_ok_items_excluded(self, sample_recommendations):
        """Test that OK items are excluded from the action plan."""
        result = format_prioritized_actions(sample_recommendations)
        assert 'MFA on Root Account' not in result

    def test_savings_displayed(self, sample_recommendations):
        """Test that savings amounts are displayed."""
        result = format_prioritized_actions(sample_recommendations)
        assert '$160.40' in result or '160' in result

    def test_remediation_included(self, sample_recommendations):
        """Test that remediation hints are included."""
        result = format_prioritized_actions(sample_recommendations)
        assert 'Remediation' in result

    def test_effort_included(self, sample_recommendations):
        """Test that effort levels are included."""
        result = format_prioritized_actions(sample_recommendations)
        assert 'Effort' in result

    def test_max_15_items(self):
        """Test that at most 15 items are returned."""
        many_recs = [
            {
                'arn': f'arn:{i}',
                'name': f'Recommendation {i}',
                'status': 'warning',
                'pillars': ['security'],
                'awsServices': ['ec2'],
                'resourcesAggregates': {'okCount': 0, 'warningCount': i, 'errorCount': 0},
                'pillarSpecificAggregates': {},
            }
            for i in range(1, 25)
        ]
        result = format_prioritized_actions(many_recs)
        # Count "### [" occurrences as item headers
        item_count = result.count('### [')
        assert item_count <= 15

    def test_categories_present(self, sample_recommendations):
        """Test that category sections appear in output."""
        result = format_prioritized_actions(sample_recommendations)
        # At least one category should be present
        has_category = any(
            cat in result
            for cat in ['Quick Win', 'High Impact', 'Review When Possible']
        )
        assert has_category

    def test_pillars_list_format(self):
        """Test handling of pillars as a list (API response format)."""
        recs = [
            {
                'arn': 'arn:1',
                'name': 'Low Utilization Amazon EC2 Instances',
                'status': 'warning',
                'pillars': ['cost_optimizing'],  # list format
                'awsServices': ['ec2'],
                'resourcesAggregates': {'okCount': 0, 'warningCount': 3, 'errorCount': 0},
                'pillarSpecificAggregates': {
                    'costOptimizing': {'estimatedMonthlySavings': 100.0}
                },
            }
        ]
        result = format_prioritized_actions(recs)
        # Should show 'Low' effort for cost_optimizing
        assert 'Low' in result


class TestFormatExecutiveSummary:
    """Tests for format_executive_summary."""

    def test_empty_recommendations(self):
        """Test with empty recommendations."""
        result = format_executive_summary([])
        assert 'Executive Summary' in result
        assert '100/100' in result

    def test_with_account_alias(self, sample_recommendations):
        """Test that account alias appears in output."""
        result = format_executive_summary(sample_recommendations, account_alias='Acme Corp')
        assert 'Acme Corp' in result

    def test_without_account_alias(self, sample_recommendations):
        """Test output without account alias."""
        result = format_executive_summary(sample_recommendations)
        assert 'Executive Summary' in result

    def test_score_present(self, sample_recommendations):
        """Test that health score appears in output."""
        result = format_executive_summary(sample_recommendations)
        assert '/100' in result
        assert 'Grade' in result

    def test_metrics_section(self, sample_recommendations):
        """Test that key metrics section is present."""
        result = format_executive_summary(sample_recommendations)
        assert 'Key Metrics' in result
        assert 'Warnings' in result
        assert 'Errors' in result

    def test_savings_shown_when_present(self, sample_recommendations):
        """Test that savings appear when recommendations have savings."""
        result = format_executive_summary(sample_recommendations)
        assert 'Savings' in result
        assert '$' in result

    def test_assessment_present(self, sample_recommendations):
        """Test that assessment paragraph is present."""
        result = format_executive_summary(sample_recommendations)
        assert 'Assessment' in result

    def test_grade_a_message(self):
        """Test that perfect score gives Grade A message."""
        ok_recs = [
            {
                'arn': f'arn:{i}',
                'name': f'Check {i}',
                'status': 'ok',
                'pillars': ['security'],
                'resourcesAggregates': {'okCount': 1, 'warningCount': 0, 'errorCount': 0},
                'pillarSpecificAggregates': {},
            }
            for i in range(10)
        ]
        result = format_executive_summary(ok_recs)
        assert 'A' in result
        assert 'excellent' in result.lower() or '100' in result

    def test_low_score_message(self):
        """Test that low score gives appropriate warning message."""
        bad_recs = [
            {
                'arn': f'arn:{i}',
                'name': f'Check {i}',
                'status': 'error',
                'pillars': ['security'],
                'resourcesAggregates': {'okCount': 0, 'warningCount': 0, 'errorCount': 5},
                'pillarSpecificAggregates': {},
            }
            for i in range(20)
        ]
        result = format_executive_summary(bad_recs)
        assert 'immediate' in result.lower() or 'significant' in result.lower()
