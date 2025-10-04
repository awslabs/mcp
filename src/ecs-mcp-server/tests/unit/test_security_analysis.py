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

"""
Unit tests for ECS security analysis module - essential tests only.
"""

from unittest.mock import patch

import pytest

from awslabs.ecs_mcp_server.api.security_analysis import (
    DataAdapter,
    SecurityAnalyzer,
    analyze_ecs_security,
)


@pytest.fixture
def mock_cluster_data():
    """Fixture for mock cluster data."""
    return {
        "clusters": [
            {
                "clusterName": "test-cluster",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                "status": "ACTIVE",
                "settings": [
                    {"name": "containerInsights", "value": "enabled"},
                ],
            }
        ]
    }


@pytest.fixture
def mock_cluster_data_no_insights():
    """Fixture for mock cluster data without Container Insights."""
    return {
        "clusters": [
            {
                "clusterName": "test-cluster",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                "status": "ACTIVE",
                "settings": [],
            }
        ]
    }


class TestDataAdapter:
    """Tests for DataAdapter class."""

    @pytest.mark.asyncio
    async def test_collect_cluster_data_success(self, mock_cluster_data):
        """Test successful cluster data collection."""
        adapter = DataAdapter()
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = mock_cluster_data

            result = await adapter.collect_cluster_data("test-cluster", "us-east-1")

            assert result["status"] == "success"
            assert result["cluster_name"] == "test-cluster"
            assert "cluster" in result

    @pytest.mark.asyncio
    async def test_collect_cluster_data_error(self):
        """Test cluster data collection with API error."""
        adapter = DataAdapter()
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"error": "Access denied"}

            result = await adapter.collect_cluster_data("test-cluster", "us-east-1")

            assert "error" in result
            assert result["error"] == "Access denied"


class TestSecurityAnalyzer:
    """Tests for SecurityAnalyzer class."""

    def test_analyze_container_insights_enabled(self, mock_cluster_data):
        """Test analysis when Container Insights is enabled."""
        analyzer = SecurityAnalyzer()
        ecs_data = {
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "cluster": mock_cluster_data["clusters"][0],
        }

        result = analyzer.analyze(ecs_data)

        assert "recommendations" in result
        assert "summary" in result
        # Should not have Container Insights recommendation
        insights_recs = [r for r in result["recommendations"] if "Container Insights" in r["title"]]
        assert len(insights_recs) == 0

    def test_analyze_container_insights_disabled(self, mock_cluster_data_no_insights):
        """Test analysis when Container Insights is disabled."""
        analyzer = SecurityAnalyzer()
        ecs_data = {
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "cluster": mock_cluster_data_no_insights["clusters"][0],
        }

        result = analyzer.analyze(ecs_data)

        assert "recommendations" in result
        insights_recs = [r for r in result["recommendations"] if "Container Insights" in r["title"]]
        assert len(insights_recs) == 1
        assert insights_recs[0]["severity"] == "Medium"


class TestAnalyzeECSSecurity:
    """Tests for analyze_ecs_security function."""

    @pytest.mark.asyncio
    async def test_analyze_with_cluster_names(self, mock_cluster_data):
        """Test analysis with specific cluster names."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = mock_cluster_data

            result = await analyze_ecs_security(cluster_names=["test-cluster"])

            assert result["status"] == "success"
            assert "recommendations" in result
            assert "summary" in result

    @pytest.mark.asyncio
    async def test_analyze_no_clusters_found(self):
        """Test analysis when no clusters are found."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.find_clusters") as mock_find:
            mock_find.return_value = []

            result = await analyze_ecs_security()

            assert result["status"] == "success"
            assert "No ECS clusters found" in result["message"]

    @pytest.mark.asyncio
    async def test_analyze_with_errors(self):
        """Test analysis with partial errors."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"error": "Access denied"}

            result = await analyze_ecs_security(cluster_names=["test-cluster"])

            assert result["status"] == "success"
            assert "errors" in result

    @pytest.mark.asyncio
    async def test_analyze_exception_handling(self):
        """Test analysis with unexpected exception."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.find_clusters") as mock_find:
            mock_find.side_effect = Exception("Unexpected error")

            result = await analyze_ecs_security()

            assert result["status"] == "error"
            assert "error" in result
