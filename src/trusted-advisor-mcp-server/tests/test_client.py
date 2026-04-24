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
"""Tests for the Trusted Advisor MCP Server client."""

import pytest
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_boto3_session():
    """Create a mock boto3 session with a Trusted Advisor client."""
    with patch('awslabs.trusted_advisor_mcp_server.client.boto3.Session') as mock_session_cls:
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_cls.return_value = mock_session
        yield mock_client


@pytest.fixture
def ta_client(mock_boto3_session):
    """Create a TrustedAdvisorClient with a mocked boto3 client."""
    from awslabs.trusted_advisor_mcp_server.client import TrustedAdvisorClient

    client = TrustedAdvisorClient(region_name='us-east-1')
    return client


class TestTrustedAdvisorClientInit:
    """Tests for TrustedAdvisorClient initialization."""

    def test_default_initialization(self, mock_boto3_session):
        """Test that the client initializes with default parameters."""
        from awslabs.trusted_advisor_mcp_server.client import TrustedAdvisorClient

        client = TrustedAdvisorClient()
        assert client.region_name == 'us-east-1'

    def test_custom_region(self, mock_boto3_session):
        """Test initialization with a custom region."""
        from awslabs.trusted_advisor_mcp_server.client import TrustedAdvisorClient

        client = TrustedAdvisorClient(region_name='eu-west-1')
        assert client.region_name == 'eu-west-1'

    def test_with_profile_name(self):
        """Test initialization with a profile name."""
        with patch('awslabs.trusted_advisor_mcp_server.client.boto3.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session.client.return_value = MagicMock()
            mock_session_cls.return_value = mock_session

            from awslabs.trusted_advisor_mcp_server.client import TrustedAdvisorClient

            TrustedAdvisorClient(profile_name='my-profile')
            mock_session_cls.assert_called_once()
            call_kwargs = mock_session_cls.call_args[1]
            assert call_kwargs.get('profile_name') == 'my-profile'

    def test_client_error_on_init(self):
        """Test handling of ClientError during initialization."""
        with patch('awslabs.trusted_advisor_mcp_server.client.boto3.Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session.client.side_effect = ClientError(
                {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
                'CreateClient',
            )
            mock_session_cls.return_value = mock_session

            from awslabs.trusted_advisor_mcp_server.client import TrustedAdvisorClient

            with pytest.raises(ClientError):
                TrustedAdvisorClient()


class TestListChecks:
    """Tests for TrustedAdvisorClient.list_checks."""

    async def test_list_checks_no_filters(self, ta_client, mock_boto3_session):
        """Test listing checks without filters."""
        mock_boto3_session.list_checks.return_value = {
            'checkSummaries': [
                {'arn': 'arn:1', 'id': '1', 'name': 'Check 1', 'pillar': 'security'},
                {'arn': 'arn:2', 'id': '2', 'name': 'Check 2', 'pillar': 'cost_optimizing'},
            ],
        }

        checks = await ta_client.list_checks()
        assert len(checks) == 2
        assert checks[0]['name'] == 'Check 1'
        mock_boto3_session.list_checks.assert_called_once_with(language='en')

    async def test_list_checks_with_pillar_filter(self, ta_client, mock_boto3_session):
        """Test listing checks filtered by pillar."""
        mock_boto3_session.list_checks.return_value = {
            'checkSummaries': [
                {'arn': 'arn:1', 'id': '1', 'name': 'Security Check', 'pillar': 'security'},
            ],
        }

        checks = await ta_client.list_checks(pillar='security')
        assert len(checks) == 1
        mock_boto3_session.list_checks.assert_called_once_with(
            language='en', pillar='security'
        )

    async def test_list_checks_with_service_filter(self, ta_client, mock_boto3_session):
        """Test listing checks filtered by AWS service."""
        mock_boto3_session.list_checks.return_value = {
            'checkSummaries': [
                {'arn': 'arn:1', 'id': '1', 'name': 'S3 Check', 'awsService': 'Amazon S3'},
            ],
        }

        checks = await ta_client.list_checks(aws_service='Amazon S3')
        assert len(checks) == 1

    async def test_list_checks_pagination(self, ta_client, mock_boto3_session):
        """Test that pagination is handled correctly."""
        mock_boto3_session.list_checks.side_effect = [
            {
                'checkSummaries': [{'arn': 'arn:1', 'id': '1', 'name': 'Check 1'}],
                'nextToken': 'token-1',
            },
            {
                'checkSummaries': [{'arn': 'arn:2', 'id': '2', 'name': 'Check 2'}],
            },
        ]

        checks = await ta_client.list_checks()
        assert len(checks) == 2
        assert mock_boto3_session.list_checks.call_count == 2

    async def test_list_checks_client_error(self, ta_client, mock_boto3_session):
        """Test handling of ClientError."""
        mock_boto3_session.list_checks.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'ListChecks',
        )

        with pytest.raises(ClientError):
            await ta_client.list_checks()


class TestListRecommendations:
    """Tests for TrustedAdvisorClient.list_recommendations."""

    async def test_list_recommendations_no_filters(self, ta_client, mock_boto3_session):
        """Test listing recommendations without filters."""
        mock_boto3_session.list_recommendations.return_value = {
            'recommendationSummaries': [
                {'arn': 'arn:1', 'name': 'Rec 1', 'status': 'warning'},
            ],
        }

        recs = await ta_client.list_recommendations()
        assert len(recs) == 1
        mock_boto3_session.list_recommendations.assert_called_once()

    async def test_list_recommendations_with_status(self, ta_client, mock_boto3_session):
        """Test listing recommendations filtered by status."""
        mock_boto3_session.list_recommendations.return_value = {
            'recommendationSummaries': [
                {'arn': 'arn:1', 'name': 'Rec 1', 'status': 'warning'},
            ],
        }

        recs = await ta_client.list_recommendations(status='warning')
        assert len(recs) == 1
        mock_boto3_session.list_recommendations.assert_called_once_with(status='warning')

    async def test_list_recommendations_with_all_filters(self, ta_client, mock_boto3_session):
        """Test listing recommendations with all filters."""
        mock_boto3_session.list_recommendations.return_value = {
            'recommendationSummaries': [],
        }

        await ta_client.list_recommendations(
            status='error',
            pillar='security',
            after_last_updated_at='2024-01-01T00:00:00Z',
            aws_service='Amazon EC2',
        )
        mock_boto3_session.list_recommendations.assert_called_once_with(
            status='error',
            pillar='security',
            afterLastUpdatedAt='2024-01-01T00:00:00Z',
            awsService='Amazon EC2',
        )

    async def test_list_recommendations_pagination(self, ta_client, mock_boto3_session):
        """Test pagination for recommendations."""
        mock_boto3_session.list_recommendations.side_effect = [
            {
                'recommendationSummaries': [
                    {'arn': 'arn:1', 'name': 'Rec 1', 'status': 'warning'}
                ],
                'nextToken': 'token-1',
            },
            {
                'recommendationSummaries': [
                    {'arn': 'arn:2', 'name': 'Rec 2', 'status': 'error'}
                ],
            },
        ]

        recs = await ta_client.list_recommendations()
        assert len(recs) == 2


class TestGetRecommendation:
    """Tests for TrustedAdvisorClient.get_recommendation."""

    async def test_get_recommendation(self, ta_client, mock_boto3_session):
        """Test getting a specific recommendation."""
        mock_boto3_session.get_recommendation.return_value = {
            'recommendation': {
                'arn': 'arn:rec:1',
                'name': 'Test Recommendation',
                'status': 'warning',
            },
        }

        rec = await ta_client.get_recommendation('arn:rec:1')
        assert rec['name'] == 'Test Recommendation'
        mock_boto3_session.get_recommendation.assert_called_once_with(
            recommendationIdentifier='arn:rec:1'
        )

    async def test_get_recommendation_not_found(self, ta_client, mock_boto3_session):
        """Test handling of a non-existent recommendation."""
        mock_boto3_session.get_recommendation.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetRecommendation',
        )

        with pytest.raises(ClientError):
            await ta_client.get_recommendation('arn:nonexistent')


class TestListRecommendationResources:
    """Tests for TrustedAdvisorClient.list_recommendation_resources."""

    async def test_list_resources(self, ta_client, mock_boto3_session):
        """Test listing recommendation resources."""
        mock_boto3_session.list_recommendation_resources.return_value = {
            'recommendationResourceSummaries': [
                {
                    'arn': 'arn:resource:1',
                    'awsResourceId': 'i-12345',
                    'regionCode': 'us-east-1',
                    'status': 'warning',
                },
            ],
        }

        resources = await ta_client.list_recommendation_resources('arn:rec:1')
        assert len(resources) == 1
        assert resources[0]['awsResourceId'] == 'i-12345'

    async def test_list_resources_pagination(self, ta_client, mock_boto3_session):
        """Test pagination for recommendation resources."""
        mock_boto3_session.list_recommendation_resources.side_effect = [
            {
                'recommendationResourceSummaries': [
                    {'arn': 'arn:1', 'awsResourceId': 'r-1', 'regionCode': 'us-east-1', 'status': 'warning'},
                ],
                'nextToken': 'token-1',
            },
            {
                'recommendationResourceSummaries': [
                    {'arn': 'arn:2', 'awsResourceId': 'r-2', 'regionCode': 'us-east-1', 'status': 'warning'},
                ],
            },
        ]

        resources = await ta_client.list_recommendation_resources('arn:rec:1')
        assert len(resources) == 2


class TestUpdateRecommendationLifecycle:
    """Tests for TrustedAdvisorClient.update_recommendation_lifecycle."""

    async def test_update_lifecycle(self, ta_client, mock_boto3_session):
        """Test updating recommendation lifecycle."""
        mock_boto3_session.update_recommendation_lifecycle.return_value = {}

        await ta_client.update_recommendation_lifecycle(
            recommendation_identifier='arn:rec:1',
            lifecycle_stage='dismissed',
            update_reason='Not applicable',
        )

        mock_boto3_session.update_recommendation_lifecycle.assert_called_once_with(
            recommendationIdentifier='arn:rec:1',
            lifecycleStage='dismissed',
            updateReason='Not applicable',
        )

    async def test_update_lifecycle_without_reason(self, ta_client, mock_boto3_session):
        """Test updating lifecycle without a reason."""
        mock_boto3_session.update_recommendation_lifecycle.return_value = {}

        await ta_client.update_recommendation_lifecycle(
            recommendation_identifier='arn:rec:1',
            lifecycle_stage='in_progress',
        )

        mock_boto3_session.update_recommendation_lifecycle.assert_called_once_with(
            recommendationIdentifier='arn:rec:1',
            lifecycleStage='in_progress',
        )

    async def test_update_lifecycle_error(self, ta_client, mock_boto3_session):
        """Test handling of errors during lifecycle update."""
        mock_boto3_session.update_recommendation_lifecycle.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid stage'}},
            'UpdateRecommendationLifecycle',
        )

        with pytest.raises(ClientError):
            await ta_client.update_recommendation_lifecycle(
                recommendation_identifier='arn:rec:1',
                lifecycle_stage='invalid',
            )


class TestListOrganizationRecommendations:
    """Tests for TrustedAdvisorClient.list_organization_recommendations."""

    async def test_list_org_recommendations(self, ta_client, mock_boto3_session):
        """Test listing organization recommendations."""
        mock_boto3_session.list_organization_recommendations.return_value = {
            'organizationRecommendationSummaries': [
                {'arn': 'arn:org:1', 'name': 'Org Rec 1', 'status': 'warning'},
            ],
        }

        recs = await ta_client.list_organization_recommendations()
        assert len(recs) == 1
        assert recs[0]['name'] == 'Org Rec 1'

    async def test_list_org_recommendations_with_filters(self, ta_client, mock_boto3_session):
        """Test listing organization recommendations with filters."""
        mock_boto3_session.list_organization_recommendations.return_value = {
            'organizationRecommendationSummaries': [],
        }

        await ta_client.list_organization_recommendations(
            status='error', pillar='security'
        )
        mock_boto3_session.list_organization_recommendations.assert_called_once_with(
            status='error', pillar='security'
        )

    async def test_list_org_recommendations_access_denied(self, ta_client, mock_boto3_session):
        """Test access denied for non-management accounts."""
        mock_boto3_session.list_organization_recommendations.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not a management account'}},
            'ListOrganizationRecommendations',
        )

        with pytest.raises(ClientError) as exc_info:
            await ta_client.list_organization_recommendations()
        assert exc_info.value.response['Error']['Code'] == 'AccessDeniedException'
