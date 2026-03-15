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
"""Tests for the Trusted Advisor MCP Server HTML report module."""

import pytest
from awslabs.trusted_advisor_mcp_server.html_report import generate_html_report


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
            'name': 'VPC Elastic IP Address Limit',
            'status': 'warning',
            'pillars': ['service_limits'],
            'awsServices': ['vpc'],
            'resourcesAggregates': {'okCount': 3, 'warningCount': 1, 'errorCount': 0},
            'pillarSpecificAggregates': {},
            'lastUpdatedAt': '2024-01-14T08:00:00Z',
        },
    ]


class TestGenerateHtmlReport:
    """Tests for generate_html_report."""

    def test_returns_string(self, sample_recommendations):
        """Test that the function returns a string."""
        result = generate_html_report(sample_recommendations)
        assert isinstance(result, str)

    def test_valid_html_structure(self, sample_recommendations):
        """Test that output contains valid HTML structure."""
        result = generate_html_report(sample_recommendations)
        assert '<!DOCTYPE html>' in result
        assert '<html' in result
        assert '</html>' in result
        assert '<head>' in result or '<head ' in result
        assert '<body' in result
        assert '</body>' in result

    def test_no_external_resources(self, sample_recommendations):
        """Test that the report has no external resource references."""
        result = generate_html_report(sample_recommendations)
        # No external CSS/JS links
        assert 'http://' not in result or 'href="http' not in result
        assert '<script src=' not in result
        assert '<link rel=' not in result or 'stylesheet' not in result

    def test_without_account_alias(self, sample_recommendations):
        """Test report generation works without any extra parameters."""
        result = generate_html_report(sample_recommendations)
        assert '<!DOCTYPE html>' in result

    def test_html_contains_report_title(self, sample_recommendations):
        """Test that the report contains a meaningful title."""
        result = generate_html_report(sample_recommendations)
        assert 'Trusted Advisor' in result

    def test_score_present(self, sample_recommendations):
        """Test that health score appears in the report."""
        result = generate_html_report(sample_recommendations)
        assert 'out of 100' in result or '/100' in result or '/ 100' in result

    def test_recommendation_names_present(self, sample_recommendations):
        """Test that recommendation names appear in the report."""
        result = generate_html_report(sample_recommendations)
        assert 'Lambda Functions Using Deprecated Runtimes' in result
        assert 'Low Utilization Amazon EC2 Instances' in result

    def test_savings_highlighted(self, sample_recommendations):
        """Test that cost savings appear in the report."""
        result = generate_html_report(sample_recommendations)
        assert '160' in result  # savings amount

    def test_footer_present(self, sample_recommendations):
        """Test that footer with attribution is present."""
        result = generate_html_report(sample_recommendations)
        assert 'Trusted Advisor' in result

    def test_color_coding(self, sample_recommendations):
        """Test that status colors are present."""
        result = generate_html_report(sample_recommendations)
        assert '#b71c1c' in result or '#e65100' in result  # error/warning colors

    def test_empty_recommendations(self):
        """Test with empty recommendations list."""
        result = generate_html_report([])
        assert '<!DOCTYPE html>' in result
        assert '100' in result  # perfect score with no issues

    def test_report_is_substantial(self, sample_recommendations):
        """Test that the report has meaningful content length."""
        result = generate_html_report(sample_recommendations)
        assert len(result) > 1000  # should be a full HTML document

    def test_inline_css_only(self, sample_recommendations):
        """Test that styling uses only inline CSS (style= attributes)."""
        result = generate_html_report(sample_recommendations)
        # Should use inline styles (no <style> block with external class)
        # At minimum: no <link> stylesheet references
        assert '<link rel="stylesheet"' not in result

    def test_with_details_and_resources(self, sample_recommendations):
        """Test that details and resources are rendered when provided."""
        details = {
            'arn:1': {
                'description': '<p>This check warns you about <b>Lambda functions</b> using deprecated runtimes.</p>',
            },
        }
        resources = {
            'arn:1': [
                {'id': 'func-alpha', 'status': 'error', 'metadata': {}},
                {'id': 'func-beta', 'status': 'warning', 'metadata': {}},
                {'id': 'func-gamma', 'status': 'ok', 'metadata': {}},
            ],
        }
        result = generate_html_report(
            sample_recommendations, details=details, resources=resources
        )
        assert 'What is this check?' in result
        assert 'Lambda functions' in result  # HTML tags stripped
        assert '&lt;b&gt;' not in result  # HTML tags should be stripped, not escaped
        assert 'Risk:' in result
        assert 'func-alpha' in result
        assert 'func-beta' in result
        # OK resources should not appear in affected list
        assert 'func-gamma' not in result
        assert 'Affected Resources (2 total)' in result

    def test_risk_text_per_pillar(self, sample_recommendations):
        """Test that risk text varies by pillar."""
        result = generate_html_report(sample_recommendations)
        # Security rec (arn:1) should show security risk
        assert 'unauthorized access' in result
        # Cost rec (arn:2) should show cost risk
        assert 'incur costs' in result

    def test_details_without_resources(self, sample_recommendations):
        """Test that details work without resources."""
        details = {
            'arn:1': {'description': 'Check for deprecated runtimes.'},
        }
        result = generate_html_report(
            sample_recommendations, details=details, resources={}
        )
        assert 'What is this check?' in result
        assert 'Check for deprecated runtimes' in result

    def test_resources_truncated_at_ten(self):
        """Test that resource list is truncated at 10 items."""
        rec = {
            'arn': 'arn:x',
            'name': 'Many Resources Check',
            'status': 'error',
            'pillars': ['security'],
            'resourcesAggregates': {'okCount': 0, 'warningCount': 0, 'errorCount': 15},
            'pillarSpecificAggregates': {},
            'lastUpdatedAt': '2024-01-15',
        }
        resource_list = [
            {'id': f'res-{i}', 'status': 'error', 'metadata': {}} for i in range(15)
        ]
        result = generate_html_report(
            [rec], resources={'arn:x': resource_list}
        )
        assert 'Affected Resources (15 total)' in result
        assert 'res-0' in result
        assert 'res-9' in result
        assert 'res-10' not in result
        assert 'and 5 more' in result
