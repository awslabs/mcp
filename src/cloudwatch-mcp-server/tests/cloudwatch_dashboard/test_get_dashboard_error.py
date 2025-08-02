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

"""Tests for CloudWatch Dashboard get_dashboard tool - error scenarios."""

import pytest
import pytest_asyncio
from awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.models import DashboardResponse
from awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.tools import CloudWatchDashboardTools
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, Mock, patch


@pytest_asyncio.fixture
async def mock_context():
    """Create mock MCP context."""
    context = Mock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest_asyncio.fixture
def dashboard_tools():
    """Create CloudWatchDashboardTools instance with mocked boto3."""
    with patch('awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.tools.boto3.Session'):
        return CloudWatchDashboardTools()


class TestParameterValidationErrors:
    """Test parameter validation error scenarios."""

    @pytest.mark.asyncio
    async def test_get_dashboard_empty_dashboard_name(self, mock_context, dashboard_tools):
        """Test error when dashboard_name is empty string."""
        with pytest.raises(ValueError) as exc_info:
            await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='', region='us-east-1'
            )

        assert 'dashboard_name must be a non-empty string' in str(exc_info.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dashboard_whitespace_only_dashboard_name(
        self, mock_context, dashboard_tools
    ):
        """Test error when dashboard_name is whitespace only."""
        with pytest.raises(ValueError) as exc_info:
            await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='   ', region='us-east-1'
            )

        assert 'dashboard_name cannot be empty or whitespace only' in str(exc_info.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dashboard_none_dashboard_name(self, mock_context, dashboard_tools):
        """Test error when dashboard_name is None."""
        with pytest.raises(ValueError) as exc_info:
            await dashboard_tools.get_dashboard(
                mock_context, dashboard_name=None, region='us-east-1'
            )

        assert 'dashboard_name must be a non-empty string' in str(exc_info.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dashboard_non_string_dashboard_name(self, mock_context, dashboard_tools):
        """Test error when dashboard_name is not a string."""
        with pytest.raises(ValueError) as exc_info:
            await dashboard_tools.get_dashboard(
                mock_context, dashboard_name=123, region='us-east-1'
            )

        assert 'dashboard_name must be a non-empty string' in str(exc_info.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dashboard_empty_region(self, mock_context, dashboard_tools):
        """Test error when region is empty string."""
        with pytest.raises(ValueError) as exc_info:
            await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='TestDashboard', region=''
            )

        assert 'region must be a non-empty string' in str(exc_info.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dashboard_whitespace_only_region(self, mock_context, dashboard_tools):
        """Test error when region is whitespace only."""
        with pytest.raises(ValueError) as exc_info:
            await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='TestDashboard', region='   '
            )

        assert 'region cannot be empty or whitespace only' in str(exc_info.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dashboard_none_region(self, mock_context, dashboard_tools):
        """Test error when region is None."""
        with pytest.raises(ValueError) as exc_info:
            await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='TestDashboard', region=None
            )

        assert 'region must be a non-empty string' in str(exc_info.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dashboard_non_string_region(self, mock_context, dashboard_tools):
        """Test error when region is not a string."""
        with pytest.raises(ValueError) as exc_info:
            await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='TestDashboard', region=123
            )

        assert 'region must be a non-empty string' in str(exc_info.value)
        mock_context.error.assert_called_once()


class TestDashboardNotFoundErrors:
    """Test dashboard not found error scenarios."""

    @pytest.mark.asyncio
    async def test_get_dashboard_not_found(self, mock_context, dashboard_tools):
        """Test error when dashboard does not exist in specified region."""
        # Mock CloudWatch client to raise generic exception (simulating ResourceNotFound)
        mock_client = Mock()
        mock_client.get_dashboard.side_effect = Exception('Dashboard not found')

        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            with pytest.raises(Exception) as exc_info:
                await dashboard_tools.get_dashboard(
                    mock_context, dashboard_name='TestDashboard', region='eu-west-1'
                )

        # Verify the correct exception was raised
        assert 'Dashboard not found' in str(exc_info.value)
        # Verify error was logged and context was notified
        mock_context.error.assert_called_once()


class TestAWSAPIErrors:
    """Test AWS API error scenarios."""

    @pytest.mark.asyncio
    async def test_get_dashboard_client_error(self, mock_context, dashboard_tools):
        """Test error when AWS API returns ClientError."""
        # Mock CloudWatch client to raise ClientError
        mock_client = Mock()
        client_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'User is not authorized to perform: cloudwatch:GetDashboard',
                }
            },
            operation_name='GetDashboard',
        )
        mock_client.get_dashboard.side_effect = client_error

        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            with pytest.raises(ClientError):
                await dashboard_tools.get_dashboard(
                    mock_context, dashboard_name='TestDashboard', region='us-east-1'
                )

        # Verify error was logged and context was notified
        mock_context.error.assert_called_once()


class TestJSONParsingErrors:
    """Test JSON parsing error scenarios."""

    @pytest.mark.asyncio
    async def test_get_dashboard_malformed_json(self, mock_context, dashboard_tools):
        """Test handling of malformed JSON in dashboard body."""
        # Mock CloudWatch client response with malformed JSON
        mock_client = Mock()
        mock_response = {
            'DashboardName': 'TestDashboard',
            'DashboardArn': 'arn:aws:cloudwatch:us-east-1:123456789012:dashboard/TestDashboard',
            'DashboardBody': '{"widgets": [}',  # Malformed JSON - missing closing bracket
        }
        mock_client.get_dashboard.return_value = mock_response

        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            result = await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='TestDashboard', region='us-east-1'
            )

        # Verify result handles malformed JSON gracefully
        assert isinstance(result, DashboardResponse)
        assert result.dashboard_name == 'TestDashboard'
        assert result.dashboard_body == '{"widgets": [}'  # Raw string returned
        assert result.parsing_warning is not None
        assert 'Failed to parse dashboard body as JSON' in result.parsing_warning

    @pytest.mark.asyncio
    async def test_get_dashboard_json_parsing_unexpected_error(
        self, mock_context, dashboard_tools
    ):
        """Test handling of unexpected error during JSON parsing."""
        # Mock CloudWatch client response
        mock_client = Mock()
        mock_response = {
            'DashboardName': 'TestDashboard',
            'DashboardBody': '{"widgets": []}',
        }
        mock_client.get_dashboard.return_value = mock_response

        # Mock json.loads to raise unexpected error
        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.tools.json.loads'
            ) as mock_json_loads:
                mock_json_loads.side_effect = RuntimeError('Unexpected JSON parsing error')

                result = await dashboard_tools.get_dashboard(
                    mock_context, dashboard_name='TestDashboard', region='us-east-1'
                )

        # Verify unexpected error is handled gracefully
        assert isinstance(result, DashboardResponse)
        assert result.dashboard_body == '{"widgets": []}'  # Raw string returned
        assert result.parsing_warning is not None
        assert 'Unexpected error parsing dashboard body' in result.parsing_warning
        assert 'Unexpected JSON parsing error' in result.parsing_warning


class TestClientCreationErrors:
    """Test AWS client creation error scenarios."""

    def test_get_cloudwatch_client_client_creation_error(self, dashboard_tools):
        """Test error when CloudWatch client creation fails."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.tools.boto3.Session'
        ) as mock_session:
            mock_session.return_value.client.side_effect = Exception('Failed to create client')

            with pytest.raises(Exception) as exc_info:
                dashboard_tools._get_cloudwatch_client('us-east-1')

            assert 'Failed to create client' in str(exc_info.value)


class TestUnexpectedErrors:
    """Test unexpected error scenarios."""

    @pytest.mark.asyncio
    async def test_get_dashboard_unexpected_error_in_processing(
        self, mock_context, dashboard_tools
    ):
        """Test handling of unexpected error during response processing."""
        # Mock CloudWatch client to raise an unexpected error
        mock_client = Mock()
        mock_client.get_dashboard.side_effect = RuntimeError('Unexpected processing error')

        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                await dashboard_tools.get_dashboard(
                    mock_context, dashboard_name='TestDashboard', region='us-east-1'
                )

            assert 'Unexpected processing error' in str(exc_info.value)
            mock_context.error.assert_called_once()
