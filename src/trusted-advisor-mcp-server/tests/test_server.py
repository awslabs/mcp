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
"""Tests for the Trusted Advisor MCP Server tool functions."""

import pytest
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, mock_open, patch


@pytest.fixture
def mock_ta_client():
    """Create a mock TrustedAdvisorClient."""
    client = MagicMock()
    client.list_checks = AsyncMock()
    client.list_recommendations = AsyncMock()
    client.get_recommendation = AsyncMock()
    client.list_recommendation_resources = AsyncMock()
    client.update_recommendation_lifecycle = AsyncMock()
    client.list_organization_recommendations = AsyncMock()
    return client


@pytest.fixture
def mock_context():
    """Create a mock FastMCP Context."""
    return MagicMock()


class TestListTrustedAdvisorChecks:
    """Tests for the list_trusted_advisor_checks tool."""

    async def test_list_checks_success(self, mock_ta_client, mock_context, check_summaries_data):
        """Test successful check listing."""
        mock_ta_client.list_checks.return_value = check_summaries_data

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import list_trusted_advisor_checks

            result = await list_trusted_advisor_checks(
                mock_context, pillar=None, aws_service=None, language='en'
            )

        assert 'Amazon S3 Bucket Permissions' in result
        assert 'Low Utilization Amazon EC2 Instances' in result
        mock_ta_client.list_checks.assert_called_once_with(
            pillar=None, aws_service=None, language='en'
        )

    async def test_list_checks_with_filters(self, mock_ta_client, mock_context):
        """Test check listing with filters."""
        mock_ta_client.list_checks.return_value = [
            {'arn': 'arn:1', 'id': '1', 'name': 'Security Check', 'pillar': 'security'},
        ]

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import list_trusted_advisor_checks

            result = await list_trusted_advisor_checks(
                mock_context, pillar='security', aws_service='Amazon EC2', language='ja'
            )

        mock_ta_client.list_checks.assert_called_once_with(
            pillar='security', aws_service='Amazon EC2', language='ja'
        )

    async def test_list_checks_client_error(self, mock_ta_client, mock_context):
        """Test error handling for ClientError."""
        mock_ta_client.list_checks.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'ListChecks',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import list_trusted_advisor_checks

            result = await list_trusted_advisor_checks(mock_context)

        assert 'Error' in result
        assert 'AccessDeniedException' in result

    async def test_list_checks_unexpected_error(self, mock_ta_client, mock_context):
        """Test error handling for unexpected errors."""
        mock_ta_client.list_checks.side_effect = RuntimeError('Something went wrong')

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import list_trusted_advisor_checks

            result = await list_trusted_advisor_checks(mock_context)

        assert 'Error' in result
        assert 'Something went wrong' in result


class TestListRecommendations:
    """Tests for the list_recommendations tool."""

    async def test_list_recommendations_success(
        self, mock_ta_client, mock_context, recommendation_summaries_data
    ):
        """Test successful recommendation listing."""
        mock_ta_client.list_recommendations.return_value = recommendation_summaries_data

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import list_recommendations

            result = await list_recommendations(mock_context)

        assert 'Low Utilization Amazon EC2 Instances' in result
        assert 'Idle Load Balancers' in result

    async def test_list_recommendations_with_filters(self, mock_ta_client, mock_context):
        """Test recommendation listing with filters."""
        mock_ta_client.list_recommendations.return_value = []

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import list_recommendations

            await list_recommendations(
                mock_context,
                status='warning',
                pillar='security',
                after_last_updated_at='2024-01-01T00:00:00Z',
                aws_service='Amazon EC2',
            )

        mock_ta_client.list_recommendations.assert_called_once_with(
            status='warning',
            pillar='security',
            after_last_updated_at='2024-01-01T00:00:00Z',
            aws_service='Amazon EC2',
        )

    async def test_list_recommendations_error(self, mock_ta_client, mock_context):
        """Test error handling."""
        mock_ta_client.list_recommendations.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Server error'}},
            'ListRecommendations',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import list_recommendations

            result = await list_recommendations(mock_context)

        assert 'Error' in result


class TestGetRecommendation:
    """Tests for the get_recommendation tool."""

    async def test_get_recommendation_success(
        self, mock_ta_client, mock_context, recommendation_detail_data, recommendation_resources_data
    ):
        """Test successful recommendation detail retrieval."""
        mock_ta_client.get_recommendation.return_value = recommendation_detail_data
        mock_ta_client.list_recommendation_resources.return_value = recommendation_resources_data

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_recommendation

            result = await get_recommendation(mock_context, recommendation_identifier='arn:rec:1')

        assert 'Low Utilization Amazon EC2 Instances' in result
        assert 'i-0123456789abcdef0' in result
        mock_ta_client.get_recommendation.assert_called_once_with('arn:rec:1')
        mock_ta_client.list_recommendation_resources.assert_called_once_with('arn:rec:1')

    async def test_get_recommendation_not_found(self, mock_ta_client, mock_context):
        """Test handling of non-existent recommendation."""
        mock_ta_client.get_recommendation.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetRecommendation',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_recommendation

            result = await get_recommendation(mock_context, recommendation_identifier='arn:bad')

        assert 'Error' in result
        assert 'ResourceNotFoundException' in result


class TestGetCostOptimizationSummary:
    """Tests for the get_cost_optimization_summary tool."""

    async def test_cost_summary_success(
        self, mock_ta_client, mock_context, recommendation_summaries_data
    ):
        """Test successful cost optimization summary."""
        mock_ta_client.list_recommendations.side_effect = [
            recommendation_summaries_data,  # warnings
            [],  # errors
        ]

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_cost_optimization_summary

            result = await get_cost_optimization_summary(mock_context)

        assert 'Cost Optimization Summary' in result
        assert '$175.50' in result
        assert mock_ta_client.list_recommendations.call_count == 2

    async def test_cost_summary_no_recommendations(self, mock_ta_client, mock_context):
        """Test cost summary with no recommendations."""
        mock_ta_client.list_recommendations.return_value = []

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_cost_optimization_summary

            result = await get_cost_optimization_summary(mock_context)

        assert 'No active cost optimization' in result

    async def test_cost_summary_error(self, mock_ta_client, mock_context):
        """Test error handling for cost summary."""
        mock_ta_client.list_recommendations.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ListRecommendations',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_cost_optimization_summary

            result = await get_cost_optimization_summary(mock_context)

        assert 'Error' in result


class TestGetSecuritySummary:
    """Tests for the get_security_summary tool."""

    async def test_security_summary_success(
        self, mock_ta_client, mock_context, security_recommendations_data
    ):
        """Test successful security summary."""
        mock_ta_client.list_recommendations.return_value = security_recommendations_data

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_security_summary

            result = await get_security_summary(mock_context)

        assert 'Security Summary' in result
        assert 'Security Groups - Unrestricted Access' in result
        mock_ta_client.list_recommendations.assert_called_once_with(pillar='security')

    async def test_security_summary_error(self, mock_ta_client, mock_context):
        """Test error handling for security summary."""
        mock_ta_client.list_recommendations.side_effect = RuntimeError('Unexpected')

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_security_summary

            result = await get_security_summary(mock_context)

        assert 'Error' in result


class TestGetServiceLimitsSummary:
    """Tests for the get_service_limits_summary tool."""

    async def test_service_limits_success(
        self, mock_ta_client, mock_context, service_limits_recommendations_data
    ):
        """Test successful service limits summary."""
        mock_ta_client.list_recommendations.side_effect = [
            service_limits_recommendations_data[:1],  # warnings
            service_limits_recommendations_data[1:],  # errors
        ]

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_service_limits_summary

            result = await get_service_limits_summary(mock_context)

        assert 'Service Limits Summary' in result
        assert mock_ta_client.list_recommendations.call_count == 2

    async def test_service_limits_empty(self, mock_ta_client, mock_context):
        """Test service limits with no concerns."""
        mock_ta_client.list_recommendations.return_value = []

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_service_limits_summary

            result = await get_service_limits_summary(mock_context)

        assert 'No service limit concerns' in result


class TestUpdateRecommendationLifecycle:
    """Tests for the update_recommendation_lifecycle tool."""

    async def test_update_lifecycle_success(self, mock_ta_client, mock_context):
        """Test successful lifecycle update."""
        mock_ta_client.update_recommendation_lifecycle.return_value = None

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import update_recommendation_lifecycle

            result = await update_recommendation_lifecycle(
                mock_context,
                recommendation_identifier='arn:rec:1',
                lifecycle_stage='dismissed',
                update_reason='Not applicable',
            )

        assert 'Lifecycle Updated' in result
        assert 'dismissed' in result
        mock_ta_client.update_recommendation_lifecycle.assert_called_once()

    async def test_update_lifecycle_invalid_stage(self, mock_ta_client, mock_context):
        """Test validation of invalid lifecycle stage."""
        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import update_recommendation_lifecycle

            result = await update_recommendation_lifecycle(
                mock_context,
                recommendation_identifier='arn:rec:1',
                lifecycle_stage='invalid_stage',
            )

        assert 'Invalid lifecycle stage' in result
        mock_ta_client.update_recommendation_lifecycle.assert_not_called()

    async def test_update_lifecycle_error(self, mock_ta_client, mock_context):
        """Test error handling for lifecycle update."""
        mock_ta_client.update_recommendation_lifecycle.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid request'}},
            'UpdateRecommendationLifecycle',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import update_recommendation_lifecycle

            result = await update_recommendation_lifecycle(
                mock_context,
                recommendation_identifier='arn:rec:1',
                lifecycle_stage='dismissed',
            )

        assert 'Error' in result


class TestListOrganizationRecommendations:
    """Tests for the list_organization_recommendations tool."""

    async def test_org_recommendations_success(
        self, mock_ta_client, mock_context, organization_recommendations_data
    ):
        """Test successful organization recommendation listing."""
        mock_ta_client.list_organization_recommendations.return_value = (
            organization_recommendations_data
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import list_organization_recommendations

            result = await list_organization_recommendations(mock_context)

        assert 'Organization Recommendations' in result
        assert 'Low Utilization Amazon EC2 Instances' in result

    async def test_org_recommendations_access_denied(self, mock_ta_client, mock_context):
        """Test access denied for non-management accounts."""
        mock_ta_client.list_organization_recommendations.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'}},
            'ListOrganizationRecommendations',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import list_organization_recommendations

            result = await list_organization_recommendations(mock_context)

        assert 'Access denied' in result
        assert 'management account' in result

    async def test_org_recommendations_with_filters(self, mock_ta_client, mock_context):
        """Test organization recommendations with filters."""
        mock_ta_client.list_organization_recommendations.return_value = []

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import list_organization_recommendations

            await list_organization_recommendations(
                mock_context,
                status='error',
                pillar='security',
                aws_service=None,
                after_last_updated_at=None,
            )

        mock_ta_client.list_organization_recommendations.assert_called_once_with(
            status='error',
            pillar='security',
            aws_service=None,
            after_last_updated_at=None,
        )


class TestGetExecutiveSummary:
    """Tests for the get_executive_summary tool."""

    async def test_executive_summary_success(
        self, mock_ta_client, mock_context, recommendation_summaries_data
    ):
        """Test successful executive summary generation."""
        mock_ta_client.list_recommendations.return_value = recommendation_summaries_data

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_executive_summary

            result = await get_executive_summary(mock_context)

        assert 'Executive Summary' in result
        assert '/100' in result
        mock_ta_client.list_recommendations.assert_called_once_with()

    async def test_executive_summary_client_error(self, mock_ta_client, mock_context):
        """Test error handling for ClientError."""
        mock_ta_client.list_recommendations.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ListRecommendations',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_executive_summary

            result = await get_executive_summary(mock_context)

        assert 'Error' in result
        assert 'ThrottlingException' in result

    async def test_executive_summary_unexpected_error(self, mock_ta_client, mock_context):
        """Test error handling for unexpected errors."""
        mock_ta_client.list_recommendations.side_effect = RuntimeError('Unexpected')

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_executive_summary

            result = await get_executive_summary(mock_context)

        assert 'Error' in result
        assert 'Unexpected' in result


class TestGetPrioritizedActions:
    """Tests for the get_prioritized_actions tool."""

    async def test_prioritized_actions_success(
        self, mock_ta_client, mock_context, recommendation_summaries_data
    ):
        """Test successful prioritized actions generation."""
        mock_ta_client.list_recommendations.return_value = recommendation_summaries_data

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_prioritized_actions

            result = await get_prioritized_actions(mock_context)

        assert 'Prioritized Actions' in result
        mock_ta_client.list_recommendations.assert_called_once_with()

    async def test_prioritized_actions_client_error(self, mock_ta_client, mock_context):
        """Test error handling for ClientError."""
        mock_ta_client.list_recommendations.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'ListRecommendations',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_prioritized_actions

            result = await get_prioritized_actions(mock_context)

        assert 'Error' in result
        assert 'AccessDeniedException' in result

    async def test_prioritized_actions_unexpected_error(self, mock_ta_client, mock_context):
        """Test error handling for unexpected errors."""
        mock_ta_client.list_recommendations.side_effect = RuntimeError('Broken')

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_prioritized_actions

            result = await get_prioritized_actions(mock_context)

        assert 'Error' in result
        assert 'Broken' in result


class TestGenerateTrustedAdvisorReport:
    """Tests for the generate_trusted_advisor_report tool."""

    async def test_report_html_returned(
        self, mock_ta_client, mock_context, recommendation_summaries_data
    ):
        """Test that HTML content is returned when no output_path is given."""
        mock_ta_client.list_recommendations.return_value = recommendation_summaries_data
        mock_ta_client.get_recommendation.return_value = {}
        mock_ta_client.list_recommendation_resources.return_value = []

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import generate_trusted_advisor_report

            result = await generate_trusted_advisor_report(mock_context, output_path=None)

        # HTML report should contain html tags
        assert '<html' in result.lower() or 'Trusted Advisor' in result

    async def test_report_saved_to_file(
        self, mock_ta_client, mock_context, recommendation_summaries_data
    ):
        """Test that report is saved to file when output_path is given."""
        mock_ta_client.list_recommendations.return_value = recommendation_summaries_data
        mock_ta_client.get_recommendation.return_value = {}
        mock_ta_client.list_recommendation_resources.return_value = []

        m = mock_open()
        with (
            patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client),
            patch('builtins.open', m),
        ):
            from awslabs.trusted_advisor_mcp_server.server import generate_trusted_advisor_report

            result = await generate_trusted_advisor_report(
                mock_context, output_path='/tmp/test-report.html'
            )

        assert 'saved' in result.lower() or '/tmp/test-report.html' in result
        m.assert_called_once_with('/tmp/test-report.html', 'w', encoding='utf-8')

    async def test_report_client_error(self, mock_ta_client, mock_context):
        """Test error handling for ClientError."""
        mock_ta_client.list_recommendations.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Server error'}},
            'ListRecommendations',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import generate_trusted_advisor_report

            result = await generate_trusted_advisor_report(mock_context)

        assert 'Error' in result

    async def test_report_os_error(
        self, mock_ta_client, mock_context, recommendation_summaries_data
    ):
        """Test error handling for OSError when writing file."""
        mock_ta_client.list_recommendations.return_value = recommendation_summaries_data
        mock_ta_client.get_recommendation.return_value = {}
        mock_ta_client.list_recommendation_resources.return_value = []

        with (
            patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client),
            patch('builtins.open', side_effect=OSError('Permission denied')),
        ):
            from awslabs.trusted_advisor_mcp_server.server import generate_trusted_advisor_report

            result = await generate_trusted_advisor_report(
                mock_context, output_path='/readonly/report.html'
            )

        assert 'Error' in result
        assert 'Permission denied' in result

    async def test_report_unexpected_error(self, mock_ta_client, mock_context):
        """Test error handling for unexpected errors."""
        mock_ta_client.list_recommendations.side_effect = RuntimeError('Boom')

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import generate_trusted_advisor_report

            result = await generate_trusted_advisor_report(mock_context)

        assert 'Error' in result
        assert 'Boom' in result


class TestGetTrendReport:
    """Tests for the get_trend_report tool."""

    async def test_trend_report_default_30_days(
        self, mock_ta_client, mock_context, recommendation_summaries_data
    ):
        """Test trend report with default 30 days."""
        mock_ta_client.list_recommendations.return_value = recommendation_summaries_data

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_trend_report

            result = await get_trend_report(mock_context, since_days=30)

        assert 'Trend Report' in result
        assert '30' in result
        mock_ta_client.list_recommendations.assert_called_once_with()

    async def test_trend_report_custom_days(
        self, mock_ta_client, mock_context, recommendation_summaries_data
    ):
        """Test trend report with custom since_days."""
        mock_ta_client.list_recommendations.return_value = recommendation_summaries_data

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_trend_report

            result = await get_trend_report(mock_context, since_days=7)

        assert 'Trend Report' in result
        assert '7' in result

    async def test_trend_report_client_error(self, mock_ta_client, mock_context):
        """Test error handling for ClientError."""
        mock_ta_client.list_recommendations.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ListRecommendations',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_trend_report

            result = await get_trend_report(mock_context)

        assert 'Error' in result

    async def test_trend_report_unexpected_error(self, mock_ta_client, mock_context):
        """Test error handling for unexpected errors."""
        mock_ta_client.list_recommendations.side_effect = RuntimeError('Network failure')

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_trend_report

            result = await get_trend_report(mock_context)

        assert 'Error' in result
        assert 'Network failure' in result


class TestGetRecommendationRemediation:
    """Tests for the get_recommendation_remediation tool."""

    async def test_remediation_success(
        self, mock_ta_client, mock_context, recommendation_detail_data, recommendation_resources_data
    ):
        """Test successful remediation guide generation."""
        mock_ta_client.get_recommendation.return_value = recommendation_detail_data
        mock_ta_client.list_recommendation_resources.return_value = recommendation_resources_data

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_recommendation_remediation

            result = await get_recommendation_remediation(
                mock_context,
                recommendation_arn='arn:aws:trustedadvisor::123456789012:recommendation/rec-001',
            )

        assert 'Remediation Guide' in result
        assert 'Low Utilization Amazon EC2 Instances' in result
        mock_ta_client.get_recommendation.assert_called_once_with(
            'arn:aws:trustedadvisor::123456789012:recommendation/rec-001'
        )

    async def test_remediation_not_found(self, mock_ta_client, mock_context):
        """Test handling when recommendation returns empty/None."""
        mock_ta_client.get_recommendation.return_value = {}
        mock_ta_client.list_recommendation_resources.return_value = []

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_recommendation_remediation

            result = await get_recommendation_remediation(
                mock_context, recommendation_arn='arn:bad'
            )

        assert 'not found' in result.lower() or 'Remediation' in result

    async def test_remediation_client_error(self, mock_ta_client, mock_context):
        """Test error handling for ClientError."""
        mock_ta_client.get_recommendation.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetRecommendation',
        )

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_recommendation_remediation

            result = await get_recommendation_remediation(
                mock_context, recommendation_arn='arn:missing'
            )

        assert 'Error' in result
        assert 'ResourceNotFoundException' in result

    async def test_remediation_unexpected_error(self, mock_ta_client, mock_context):
        """Test error handling for unexpected errors."""
        mock_ta_client.get_recommendation.side_effect = RuntimeError('Connection lost')

        with patch('awslabs.trusted_advisor_mcp_server.server.ta_client', mock_ta_client):
            from awslabs.trusted_advisor_mcp_server.server import get_recommendation_remediation

            result = await get_recommendation_remediation(
                mock_context, recommendation_arn='arn:err'
            )

        assert 'Error' in result
        assert 'Connection lost' in result
