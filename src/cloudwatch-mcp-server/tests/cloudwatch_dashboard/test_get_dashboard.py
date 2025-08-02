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

"""Tests for CloudWatch Dashboard get_dashboard tool - success scenarios."""

import json
import pytest
import pytest_asyncio
from awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.models import DashboardResponse
from awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.tools import CloudWatchDashboardTools
from datetime import datetime
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


class TestGetDashboardSuccess:
    """Test successful dashboard retrieval scenarios."""

    @pytest.mark.asyncio
    async def test_get_dashboard_basic_success(self, mock_context, dashboard_tools):
        """Test successful dashboard retrieval with basic response."""
        # Mock CloudWatch client response
        mock_client = Mock()
        last_modified = datetime(2023, 1, 1, 12, 0, 0)
        mock_response = {
            'DashboardName': 'TestDashboard',
            'DashboardArn': 'arn:aws:cloudwatch:us-east-1:123456789012:dashboard/TestDashboard',
            'DashboardBody': '{"widgets": []}',
            'LastModified': last_modified,
        }
        mock_client.get_dashboard.return_value = mock_response

        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            result = await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='TestDashboard', region='us-east-1'
            )

        # Verify result
        assert isinstance(result, DashboardResponse)
        assert result.dashboard_name == 'TestDashboard'
        assert (
            result.dashboard_arn
            == 'arn:aws:cloudwatch:us-east-1:123456789012:dashboard/TestDashboard'
        )
        assert result.dashboard_body == {'widgets': []}
        assert result.region == 'us-east-1'
        assert result.parsing_warning is None
        assert result.last_modified == last_modified

        # Verify client was called correctly
        mock_client.get_dashboard.assert_called_once_with(DashboardName='TestDashboard')

    @pytest.mark.asyncio
    async def test_get_dashboard_complex_json_parsing(self, mock_context, dashboard_tools):
        """Test successful JSON parsing with complex dashboard body."""
        # Mock CloudWatch client response with complex dashboard body
        mock_client = Mock()
        complex_dashboard_body = {
            'widgets': [
                {
                    'type': 'metric',
                    'x': 0,
                    'y': 0,
                    'width': 12,
                    'height': 6,
                    'properties': {
                        'metrics': [
                            ['AWS/EC2', 'CPUUtilization', 'InstanceId', 'i-1234567890abcdef0']
                        ],
                        'period': 300,
                        'stat': 'Average',
                        'region': 'us-east-1',
                        'title': 'EC2 Instance CPU',
                    },
                },
                {
                    'type': 'log',
                    'x': 0,
                    'y': 6,
                    'width': 24,
                    'height': 6,
                    'properties': {
                        'query': "SOURCE '/aws/lambda/my-function' | fields @timestamp, @message\n| sort @timestamp desc\n| limit 20",
                        'region': 'us-east-1',
                        'title': 'Lambda Logs',
                    },
                },
            ],
            'start': '-PT3H',
            'end': 'PT0H',
            'timezone': 'UTC',
        }
        mock_response = {
            'DashboardName': 'ComplexDashboard',
            'DashboardArn': 'arn:aws:cloudwatch:us-east-1:123456789012:dashboard/ComplexDashboard',
            'DashboardBody': json.dumps(complex_dashboard_body),
        }
        mock_client.get_dashboard.return_value = mock_response

        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            result = await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='ComplexDashboard', region='us-east-1'
            )

        # Verify result
        assert isinstance(result, DashboardResponse)
        assert result.dashboard_name == 'ComplexDashboard'
        assert isinstance(result.dashboard_body, dict)
        assert len(result.dashboard_body['widgets']) == 2
        assert result.dashboard_body['widgets'][0]['type'] == 'metric'
        assert result.dashboard_body['widgets'][1]['type'] == 'log'
        assert result.dashboard_body['start'] == '-PT3H'
        assert result.parsing_warning is None

    @pytest.mark.asyncio
    async def test_get_dashboard_empty_body(self, mock_context, dashboard_tools):
        """Test dashboard retrieval with empty dashboard body."""
        # Mock CloudWatch client response with empty body
        mock_client = Mock()
        mock_response = {
            'DashboardName': 'EmptyDashboard',
            'DashboardBody': '',
        }
        mock_client.get_dashboard.return_value = mock_response

        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            result = await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='EmptyDashboard', region='us-east-1'
            )

        # Verify result handles empty body
        assert result.dashboard_body == ''
        assert result.parsing_warning is None

    @pytest.mark.asyncio
    async def test_get_dashboard_minimal_response(self, mock_context, dashboard_tools):
        """Test dashboard retrieval with minimal AWS response."""
        # Mock CloudWatch client response with only required fields
        mock_client = Mock()
        mock_response = {
            'DashboardName': 'MinimalDashboard',
            'DashboardBody': '{"widgets": []}',
            # Missing DashboardArn and LastModified
        }
        mock_client.get_dashboard.return_value = mock_response

        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            result = await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='MinimalDashboard', region='us-east-1'
            )

        # Verify result handles missing optional fields
        assert result.dashboard_name == 'MinimalDashboard'
        assert result.dashboard_arn is None
        assert result.last_modified is None
        assert result.dashboard_body == {'widgets': []}

class TestJSONParsingSuccess:
    """Test JSON parsing success scenarios."""

    @pytest.mark.asyncio
    async def test_json_parsing_nested_objects(self, mock_context, dashboard_tools):
        """Test JSON parsing with deeply nested objects."""
        # Mock CloudWatch client response with nested JSON
        mock_client = Mock()
        nested_dashboard_body = {
            'widgets': [
                {
                    'type': 'metric',
                    'properties': {
                        'metrics': [
                            ['AWS/EC2', 'CPUUtilization'],
                            ['AWS/EC2', 'NetworkIn'],
                        ],
                        'view': 'timeSeries',
                        'stacked': False,
                        'region': 'us-east-1',
                        'yAxis': {'left': {'min': 0, 'max': 100}},
                        'annotations': {
                            'horizontal': [
                                {
                                    'label': 'High CPU',
                                    'value': 80,
                                    'fill': 'above',
                                    'color': '#d62728',
                                }
                            ]
                        },
                    },
                }
            ],
            'annotations': {
                'horizontal': [
                    {
                        'label': 'Critical Threshold',
                        'value': 90,
                        'fill': 'above',
                        'color': '#ff0000',
                    }
                ]
            },
        }
        mock_response = {
            'DashboardName': 'NestedDashboard',
            'DashboardBody': json.dumps(nested_dashboard_body),
        }
        mock_client.get_dashboard.return_value = mock_response

        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            result = await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='NestedDashboard', region='us-east-1'
            )

        # Verify nested JSON is parsed correctly
        assert isinstance(result.dashboard_body, dict)
        assert result.dashboard_body['widgets'][0]['properties']['yAxis']['left']['max'] == 100
        assert result.dashboard_body['annotations']['horizontal'][0]['color'] == '#ff0000'
        assert result.parsing_warning is None

    @pytest.mark.asyncio
    async def test_json_parsing_unicode_characters(self, mock_context, dashboard_tools):
        """Test JSON parsing with unicode characters."""
        # Mock CloudWatch client response with unicode
        mock_client = Mock()
        unicode_dashboard_body = {
            'widgets': [
                {
                    'type': 'text',
                    'properties': {
                        'markdown': '# Dashboard 📊\n\nThis dashboard shows metrics for:\n- CPU utilization 💻\n- Network traffic 🌐\n- Disk usage 💾',
                        'title': 'Welcome to Monitoring 🚀',
                    },
                }
            ],
            'title': 'Système de Surveillance 🇫🇷',
        }
        mock_response = {
            'DashboardName': 'UnicodeDashboard',
            'DashboardBody': json.dumps(unicode_dashboard_body, ensure_ascii=False),
        }
        mock_client.get_dashboard.return_value = mock_response

        with patch.object(dashboard_tools, '_get_cloudwatch_client', return_value=mock_client):
            result = await dashboard_tools.get_dashboard(
                mock_context, dashboard_name='UnicodeDashboard', region='us-east-1'
            )

        # Verify unicode characters are parsed correctly
        assert isinstance(result.dashboard_body, dict)
        assert '📊' in result.dashboard_body['widgets'][0]['properties']['markdown']
        assert '🚀' in result.dashboard_body['widgets'][0]['properties']['title']
        assert '🇫🇷' in result.dashboard_body['title']
        assert result.parsing_warning is None


class TestToolsRegistration:
    """Test tools registration functionality."""

    def test_register_tools(self, dashboard_tools):
        """Test that tools are properly registered with MCP server."""
        mock_mcp = Mock()
        dashboard_tools.register(mock_mcp)

        # Verify get_dashboard tool is registered
        mock_mcp.tool.assert_called_once_with(name='get_dashboard')

    def test_tools_initialization(self):
        """Test CloudWatchDashboardTools initialization."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.tools.boto3.Session'):
            tools = CloudWatchDashboardTools()
            assert isinstance(tools, CloudWatchDashboardTools)


class TestClientCreation:
    """Test AWS client creation scenarios."""

    def test_get_cloudwatch_client_with_profile(self, dashboard_tools):
        """Test CloudWatch client creation with AWS profile."""
        with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile'}):
            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.tools.boto3.Session'
            ) as mock_session:
                mock_client = Mock()
                mock_session.return_value.client.return_value = mock_client

                result = dashboard_tools._get_cloudwatch_client('us-west-2')

                # Verify session created with profile and region
                mock_session.assert_called_once_with(
                    profile_name='test-profile', region_name='us-west-2'
                )
                mock_session.return_value.client.assert_called_once()
                assert result == mock_client

    def test_get_cloudwatch_client_without_profile(self, dashboard_tools):
        """Test CloudWatch client creation without AWS profile."""
        with patch.dict('os.environ', {}, clear=True):
            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.tools.boto3.Session'
            ) as mock_session:
                mock_client = Mock()
                mock_session.return_value.client.return_value = mock_client

                result = dashboard_tools._get_cloudwatch_client('eu-central-1')

                # Verify session created with region only
                mock_session.assert_called_once_with(region_name='eu-central-1')
                mock_session.return_value.client.assert_called_once()
                assert result == mock_client

    def test_get_cloudwatch_client_with_user_agent(self, dashboard_tools):
        """Test CloudWatch client creation includes proper user agent."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_dashboard.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            dashboard_tools._get_cloudwatch_client('us-east-1')

            # Verify client created with config including user agent
            call_args = mock_session.return_value.client.call_args
            assert call_args[0][0] == 'cloudwatch'
            config = call_args[1]['config']
            assert 'awslabs/mcp/cloudwatch-mcp-server' in config.user_agent_extra
