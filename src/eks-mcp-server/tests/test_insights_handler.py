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
# ruff: noqa: D101, D102, D103
"""Tests for the InsightsHandler class."""

import pytest
from awslabs.eks_mcp_server.insights_handler import InsightsHandler
from datetime import datetime
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = MagicMock(spec=Context)
    ctx.request_id = 'test-request-id'
    return ctx


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server."""
    return MagicMock()


@pytest.fixture
def mock_eks_client():
    """Create a mock EKS client."""
    return MagicMock()


class TestInsightsHandler:
    """Tests for the InsightsHandler class."""

    @pytest.fixture(autouse=True)
    def mock_aws_helper(self, monkeypatch, mock_eks_client):
        """Mock AWS Helper to avoid actual AWS client creation."""

        def mock_create_boto3_client(service_name, region_name=None):
            if service_name == 'eks':
                return mock_eks_client
            else:
                return MagicMock()

        monkeypatch.setattr(
            'awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client',
            mock_create_boto3_client,
        )

    def test_init(self, mock_mcp):
        """Test initialization of InsightsHandler."""
        # Initialize the handler with default parameters
        with patch('awslabs.eks_mcp_server.insights_handler.AwsHelper') as mock_aws_helper:
            handler = InsightsHandler(mock_mcp)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.allow_sensitive_data_access is False

            # Verify that AWS clients were created
            mock_aws_helper.create_boto3_client.assert_called_once_with('eks')

        # Verify that the tools were registered
        assert mock_mcp.tool.call_count == 1
        tool_names = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
        assert 'get_eks_insights' in tool_names

    def test_init_with_options(self, mock_mcp):
        """Test initialization of InsightsHandler with custom options."""
        # Initialize the handler with custom parameters
        with patch('awslabs.eks_mcp_server.insights_handler.AwsHelper'):
            handler = InsightsHandler(mock_mcp, allow_sensitive_data_access=True)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.allow_sensitive_data_access is True

    # Tests for get_eks_insights tool
    @staticmethod
    def _create_mock_insight_item(insight_id='test-insight-id', category='CONFIGURATION'):
        """Helper to create a mock insight item for testing."""
        return {
            'id': insight_id,
            'name': f'Test Insight {insight_id}',
            'category': category,
            'kubernetesVersion': '1.27',
            'lastRefreshTime': datetime(2025, 7, 19, 12, 0, 0),
            'lastTransitionTime': datetime(2025, 7, 19, 11, 0, 0),
            'description': 'Test insight description',
            'insightStatus': {'status': 'PASSING', 'reason': 'All conditions are met'},
        }

    @pytest.mark.asyncio
    async def test_get_eks_insights_list_mode(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl in list mode (without an insight_id)."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock responses for list mode
        mock_eks_client.list_insights.return_value = {
            'insights': [
                self._create_mock_insight_item(insight_id='insight-1', category='CONFIGURATION'),
                self._create_mock_insight_item(
                    insight_id='insight-2', category='UPGRADE_READINESS'
                ),
            ]
        }

        # Initialize the handler with our mock client
        handler = InsightsHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method directly
        result = await handler._get_eks_insights_impl(mock_context, cluster_name='test-cluster')

        # Verify API calls
        mock_eks_client.list_insights.assert_called_once_with(clusterName='test-cluster')

        # Verify the result
        assert not result.isError
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 2
        assert result.detail_mode is False

        # Verify insight items were properly constructed
        assert result.insights[0].id == 'insight-1'
        assert result.insights[0].category == 'CONFIGURATION'
        assert result.insights[1].id == 'insight-2'
        assert result.insights[1].category == 'UPGRADE_READINESS'

        # Verify success message in content
        assert isinstance(
            result.content[0], TextContent
        )  # Ensure it's TextContent before accessing .text
        assert f'Successfully retrieved {len(result.insights)} insights' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_eks_insights_detail_mode(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl in detail mode (with an insight_id)."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock responses for detail mode
        insight_data = self._create_mock_insight_item(
            insight_id='detail-insight', category='CONFIGURATION'
        )
        insight_data['recommendation'] = 'This is a test recommendation'
        insight_data['additionalInfo'] = {'link': 'https://example.com'}
        insight_data['resources'] = ['resource-1', 'resource-2']
        insight_data['categorySpecificSummary'] = {'detail': 'Some specific details'}

        mock_eks_client.describe_insight.return_value = {'insight': insight_data}

        # Initialize the handler with our mock client
        handler = InsightsHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method directly with insight_id
        result = await handler._get_eks_insights_impl(
            mock_context, cluster_name='test-cluster', insight_id='detail-insight'
        )

        # Verify API calls
        mock_eks_client.describe_insight.assert_called_once_with(
            id='detail-insight', clusterName='test-cluster'
        )

        # Verify the result
        assert not result.isError
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 1
        assert result.detail_mode is True

        # Verify detailed insight properties
        insight = result.insights[0]
        assert insight.id == 'detail-insight'
        assert insight.category == 'CONFIGURATION'
        assert insight.recommendation == 'This is a test recommendation'
        assert insight.additional_info == {'link': 'https://example.com'}
        assert insight.resources == ['resource-1', 'resource-2']
        assert insight.category_specific_summary == {'detail': 'Some specific details'}

        # Verify success message in content
        assert isinstance(
            result.content[0], TextContent
        )  # Ensure it's TextContent before accessing .text
        assert (
            'Successfully retrieved details for insight detail-insight' in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_get_eks_insights_with_category_filter(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl with category filter."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock responses
        mock_eks_client.list_insights.return_value = {
            'insights': [
                self._create_mock_insight_item(
                    insight_id='config-insight-1', category='CONFIGURATION'
                ),
                self._create_mock_insight_item(
                    insight_id='config-insight-2', category='CONFIGURATION'
                ),
            ]
        }

        # Initialize the handler with our mock client
        handler = InsightsHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method with category filter
        result = await handler._get_eks_insights_impl(
            mock_context, cluster_name='test-cluster', category='CONFIGURATION'
        )

        # Verify API calls with category filter parameter
        mock_eks_client.list_insights.assert_called_once_with(
            clusterName='test-cluster',
            filter={'categories': ['CONFIGURATION']},  # Verify category passed to API
        )

        # Verify the result
        assert not result.isError
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 2
        assert all(insight.category == 'CONFIGURATION' for insight in result.insights)

        # Verify success message mentions insights
        assert isinstance(
            result.content[0], TextContent
        )  # Ensure it's TextContent before accessing .text
        assert f'Successfully retrieved {len(result.insights)} insights' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_eks_insights_with_pagination(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl with pagination token."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock responses with nextToken
        mock_eks_client.list_insights.return_value = {
            'insights': [
                self._create_mock_insight_item(insight_id='paginated-insight-1'),
                self._create_mock_insight_item(insight_id='paginated-insight-2'),
            ],
            'nextToken': 'test-next-token-value',
        }

        # Initialize the handler with our mock client
        handler = InsightsHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method with next_token
        result = await handler._get_eks_insights_impl(
            mock_context, cluster_name='test-cluster', next_token='previous-token'
        )

        # Verify API calls with next_token parameter
        mock_eks_client.list_insights.assert_called_once_with(
            clusterName='test-cluster', nextToken='previous-token'
        )

        # Verify the result
        assert not result.isError
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 2
        assert result.next_token == 'test-next-token-value'  # Verify next_token is passed through

        # Verify success message
        assert isinstance(result.content[0], TextContent)
        assert f'Successfully retrieved {len(result.insights)} insights' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_eks_insights_error_handling(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl when API call fails."""
        # Create mock AWS client that raises an exception
        mock_eks_client = MagicMock()
        mock_eks_client.list_insights.side_effect = Exception('Test API error')

        # Initialize the handler with our mock client
        handler = InsightsHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method
        result = await handler._get_eks_insights_impl(mock_context, cluster_name='test-cluster')

        # Verify API call was attempted
        mock_eks_client.list_insights.assert_called_once_with(clusterName='test-cluster')

        # Verify error response
        assert result.isError
        assert isinstance(result.content[0], TextContent)
        assert 'Error listing insights' in result.content[0].text
        assert 'Test API error' in result.content[0].text
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 0

    @pytest.mark.asyncio
    async def test_get_eks_insights_no_insights_found(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl when no insights are found."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock response with no insights
        mock_eks_client.list_insights.return_value = {
            'insights': []  # Empty list
        }

        # Initialize the handler with our mock client
        handler = InsightsHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method
        result = await handler._get_eks_insights_impl(mock_context, cluster_name='test-cluster')

        # Verify API call was made
        mock_eks_client.list_insights.assert_called_once_with(clusterName='test-cluster')

        # Verify appropriate empty response (not an error)
        assert not result.isError
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 0
        assert isinstance(
            result.content[0], TextContent
        )  # Ensure it's TextContent before accessing .text
        assert 'Successfully retrieved 0 insights' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_eks_insights_insight_not_found(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl when a specific insight ID can't be found."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Mock error for non-existent insight
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Insight nonexistent-id not found',
            }
        }
        mock_eks_client.describe_insight.side_effect = (
            mock_eks_client.exceptions.ResourceNotFoundException(error_response, 'DescribeInsight')
        )

        # Initialize the handler with our mock client
        handler = InsightsHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method with non-existent ID
        result = await handler._get_eks_insights_impl(
            mock_context, cluster_name='test-cluster', insight_id='nonexistent-id'
        )

        # Verify API call was attempted
        mock_eks_client.describe_insight.assert_called_once_with(
            id='nonexistent-id', clusterName='test-cluster'
        )

        # Verify error response
        assert result.isError
        assert isinstance(
            result.content[0], TextContent
        )  # Ensure it's TextContent before accessing .text
        assert 'No insight details found for ID nonexistent-id' in result.content[0].text
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 0

    @pytest.mark.asyncio
    async def test_get_eks_insights_impl_direct(self, mock_context, mock_mcp):
        """Test the internal _get_eks_insights_impl method directly."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock responses for list mode
        mock_eks_client.list_insights.return_value = {
            'insights': [
                self._create_mock_insight_item(insight_id='impl-insight-1'),
                self._create_mock_insight_item(insight_id='impl-insight-2'),
            ]
        }

        # Initialize the handler with our mock client
        handler = InsightsHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method directly in list mode
        result = await handler._get_eks_insights_impl(mock_context, cluster_name='test-cluster')

        # Verify list_insights was called with correct parameters
        mock_eks_client.list_insights.assert_called_once_with(clusterName='test-cluster')

        # Verify the result
        assert not result.isError
        assert len(result.insights) == 2
        assert result.cluster_name == 'test-cluster'
        assert not result.detail_mode

        # Now test with detail mode
        mock_eks_client.describe_insight.return_value = {
            'insight': self._create_mock_insight_item(insight_id='impl-detail-insight')
        }

        # Call the implementation method directly in detail mode
        result = await handler._get_eks_insights_impl(
            mock_context, cluster_name='test-cluster', insight_id='impl-detail-insight'
        )

        # Verify describe_insight was called with correct parameters
        mock_eks_client.describe_insight.assert_called_once_with(
            id='impl-detail-insight', clusterName='test-cluster'
        )

        # Verify the result
        assert not result.isError
        assert len(result.insights) == 1
        assert result.insights[0].id == 'impl-detail-insight'
        assert result.cluster_name == 'test-cluster'
        assert result.detail_mode

    @pytest.mark.asyncio
    async def test_get_eks_insights_impl_general_exception(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl when a general exception occurs."""
        # Create a handler
        handler = InsightsHandler(mock_mcp)

        # Create a mock eks_client
        mock_eks_client = MagicMock()
        handler.eks_client = mock_eks_client

        # Override the _list_insights method to raise a custom exception
        with patch.object(
            handler, '_list_insights', side_effect=Exception('Test general exception')
        ):
            # Call the implementation method
            result = await handler._get_eks_insights_impl(
                mock_context, cluster_name='test-cluster'
            )

        # Verify error response
        assert result.isError
        assert isinstance(result.content[0], TextContent)
        assert 'Error processing EKS insights request' in result.content[0].text
        assert 'Test general exception' in result.content[0].text
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 0
        assert result.next_token is None
        assert result.detail_mode is False

    @pytest.mark.asyncio
    async def test_get_insight_detail_exception(self, mock_context, mock_mcp):
        """Test _get_insight_detail when an exception occurs."""
        # Create mock AWS client that raises an exception
        mock_eks_client = MagicMock()
        mock_eks_client.describe_insight.side_effect = Exception('Test detail API error')

        # Initialize the handler with our mock client
        handler = InsightsHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method directly with insight_id
        result = await handler._get_eks_insights_impl(
            mock_context, cluster_name='test-cluster', insight_id='test-insight'
        )

        # Verify API call was attempted
        mock_eks_client.describe_insight.assert_called_once_with(
            id='test-insight', clusterName='test-cluster'
        )

        # Verify error response
        assert result.isError
        assert isinstance(result.content[0], TextContent)
        assert 'Error retrieving insight details' in result.content[0].text
        assert 'Test detail API error' in result.content[0].text
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 0
        assert result.next_token is None
        assert result.detail_mode is True
