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

"""Tests for list-databases-with-insights tool."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from awslabs.cloudwatch_mcp_server.database_insights.tools import DatabaseInsightsTools
from awslabs.cloudwatch_mcp_server.database_insights.models import DatabaseInstance, ListDatabasesResult




@pytest.fixture
def db_insights_tools():
    """Create a DatabaseInsightsTools instance."""
    return DatabaseInsightsTools()


class TestDatabaseInsightsTools:
    """Test DatabaseInsightsTools class."""

    def test_init(self, db_insights_tools):
        """Test DatabaseInsightsTools initialization."""
        assert db_insights_tools is not None
        assert hasattr(db_insights_tools, '_get_rds_client')
        assert hasattr(db_insights_tools, '_get_pi_client')
        assert hasattr(db_insights_tools, 'register')

    def test_get_rds_client(self, db_insights_tools):
        """Test RDS client creation with correct region parameter."""
        with patch('awslabs.cloudwatch_mcp_server.database_insights.tools.boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client

            client = db_insights_tools._get_rds_client('us-east-1')

            mock_session.assert_called_once_with(region_name='us-east-1')
            mock_session.return_value.client.assert_called_once()
            call_args = mock_session.return_value.client.call_args
            assert call_args[0][0] == 'rds'
            assert client == mock_client

    def test_get_pi_client(self, db_insights_tools):
        """Test Performance Insights client creation with correct region parameter."""
        with patch('awslabs.cloudwatch_mcp_server.database_insights.tools.boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client

            client = db_insights_tools._get_pi_client('us-west-2')

            mock_session.assert_called_once_with(region_name='us-west-2')
            mock_session.return_value.client.assert_called_once()
            call_args = mock_session.return_value.client.call_args
            assert call_args[0][0] == 'pi'
            assert client == mock_client

    def test_get_rds_client_with_aws_profile(self, db_insights_tools):
        """Test RDS client creation with AWS_PROFILE environment variable."""
        with patch('awslabs.cloudwatch_mcp_server.database_insights.tools.boto3.Session') as mock_session:
            with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile'}):
                mock_client = MagicMock()
                mock_session.return_value.client.return_value = mock_client

                client = db_insights_tools._get_rds_client('eu-west-1')

                mock_session.assert_called_once_with(profile_name='test-profile', region_name='eu-west-1')
                assert client == mock_client


class TestToolRegistration:
    """Test tool registration with MCP server."""

    def test_register_tools(self, db_insights_tools):
        """Test that tools can be registered with MCP server."""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)

        # Should not raise any exceptions
        db_insights_tools.register(mock_mcp)

        # Verify tool decorator was called (once per tool)
        assert mock_mcp.tool.call_count == 2  # list-databases-with-insights, get-database-load-metrics


class TestListDatabasesWithInsightsTool:
    """Test the list-databases-with-insights tool execution."""

    @pytest.mark.asyncio
    async def test_list_databases_returns_pi_enabled_databases(self, mock_context, register_tools_and_capture):
        """Test that list_databases_with_insights returns databases with PI enabled."""
        mock_rds_response = {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'prod-db',
                    'DbiResourceId': 'db-PROD123',
                    'Engine': 'mysql',
                    'EngineVersion': '8.0.35',
                    'PerformanceInsightsEnabled': True,
                    'PerformanceInsightsRetentionPeriod': 7,
                    'DBInstanceClass': 'db.r5.large',
                },
                {
                    'DBInstanceIdentifier': 'dev-db',
                    'DbiResourceId': 'db-DEV456',
                    'Engine': 'postgres',
                    'EngineVersion': '15.4',
                    'PerformanceInsightsEnabled': False,
                    'DBInstanceClass': 'db.t3.micro',
                },
            ]
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.database_insights.tools.boto3.Session'
        ) as mock_session:
            mock_client = MagicMock()
            mock_paginator = MagicMock()
            mock_paginator.paginate.return_value = [mock_rds_response]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = DatabaseInsightsTools()
            registered = register_tools_and_capture(tools)

            # Call the tool (default: only PI-enabled databases)
            result_json = await registered['list-databases-with-insights'](
                mock_context, region='us-east-1', include_disabled=False
            )
            result = json.loads(result_json)

            assert result['total_count'] == 2  # Total in region
            assert result['insights_enabled_count'] == 1
            assert len(result['databases']) == 1
            assert result['databases'][0]['db_instance_identifier'] == 'prod-db'
            assert result['databases'][0]['insights_enabled'] is True

    @pytest.mark.asyncio
    async def test_list_databases_include_disabled(self, mock_context, register_tools_and_capture):
        """Test that include_disabled=True returns all databases."""
        mock_rds_response = {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'db1',
                    'DbiResourceId': 'db-1',
                    'Engine': 'mysql',
                    'EngineVersion': '8.0',
                    'PerformanceInsightsEnabled': True,
                    'PerformanceInsightsRetentionPeriod': 7,
                },
                {
                    'DBInstanceIdentifier': 'db2',
                    'DbiResourceId': 'db-2',
                    'Engine': 'postgres',
                    'EngineVersion': '15',
                    'PerformanceInsightsEnabled': False,
                },
            ]
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.database_insights.tools.boto3.Session'
        ) as mock_session:
            mock_client = MagicMock()
            mock_paginator = MagicMock()
            mock_paginator.paginate.return_value = [mock_rds_response]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = DatabaseInsightsTools()
            registered = register_tools_and_capture(tools)

            result_json = await registered['list-databases-with-insights'](
                mock_context, region='us-east-1', include_disabled=True
            )
            result = json.loads(result_json)

            assert result['total_count'] == 2
            assert result['insights_enabled_count'] == 1
            assert len(result['databases']) == 2

    @pytest.mark.asyncio
    async def test_list_databases_error_handling(self, mock_context, register_tools_and_capture):
        """Test that errors are returned as JSON."""
        with patch(
            'awslabs.cloudwatch_mcp_server.database_insights.tools.boto3.Session'
        ) as mock_session:
            mock_session.return_value.client.side_effect = Exception('AWS connection failed')

            tools = DatabaseInsightsTools()
            registered = register_tools_and_capture(tools)

            result_json = await registered['list-databases-with-insights'](
                mock_context, region='us-east-1', include_disabled=False
            )
            result = json.loads(result_json)

            assert 'error' in result
            assert 'AWS connection failed' in result['error']

