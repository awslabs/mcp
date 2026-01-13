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

import pytest
from unittest.mock import MagicMock, patch
from awslabs.cloudwatch_mcp_server.database_insights.tools import DatabaseInsightsTools
from awslabs.cloudwatch_mcp_server.database_insights.models import ListDatabasesResult


@pytest.fixture
def db_insights_tools():
    """Create a DatabaseInsightsTools instance."""
    return DatabaseInsightsTools()


class TestDatabaseInsightsTools:
    """Test DatabaseInsightsTools class."""

    def test_init(self, db_insights_tools):
        """Test DatabaseInsightsTools initialization."""
        assert db_insights_tools is not None

    def test_get_rds_client(self, db_insights_tools):
        """Test RDS client creation."""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client

            client = db_insights_tools._get_rds_client('us-east-1')

            mock_session.assert_called_once()
            assert client == mock_client

    def test_get_pi_client(self, db_insights_tools):
        """Test Performance Insights client creation."""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_session.return_value.client.return_value = mock_client

            client = db_insights_tools._get_pi_client('us-west-2')

            mock_session.assert_called_once()
            assert client == mock_client


class TestListDatabasesResult:
    """Test ListDatabasesResult model creation."""

    def test_list_databases_result_creation(self):
        """Test creating a ListDatabasesResult."""
        result = ListDatabasesResult(
            databases=[],
            region='us-east-1',
            total_count=0,
            insights_enabled_count=0,
        )
        assert result.region == 'us-east-1'
        assert result.total_count == 0
        assert result.insights_enabled_count == 0
        assert result.databases == []


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

