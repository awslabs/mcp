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
Unit tests for security analysis module.
"""

from unittest.mock import patch

import pytest

from awslabs.ecs_mcp_server.api.security_analysis import (
    DataAdapter,
    SecurityAnalyzer,
    analyze_ecs_security,
)


# Fixtures
@pytest.fixture
def mock_cluster_data_active():
    """Mock cluster data with active status and Container Insights enabled."""
    return {
        "clusterName": "test-cluster",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {"executeCommandConfiguration": {"logging": "DEFAULT"}},
    }


@pytest.fixture
def mock_cluster_data_no_insights():
    """Mock cluster data without Container Insights."""
    return {
        "clusterName": "test-cluster",
        "status": "ACTIVE",
        "settings": [],
        "configuration": {"executeCommandConfiguration": {"logging": "DEFAULT"}},
    }


@pytest.fixture
def mock_cluster_data_no_logging():
    """Mock cluster data without execute command logging."""
    return {
        "clusterName": "test-cluster",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {},
    }


@pytest.fixture
def mock_cluster_data_inactive():
    """Mock cluster data with inactive status."""
    return {
        "clusterName": "test-cluster",
        "status": "INACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {"executeCommandConfiguration": {"logging": "DEFAULT"}},
    }


# DataAdapter Tests
class TestDataAdapter:
    """Tests for DataAdapter class."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_cluster_data_success(self, mock_ecs_api, mock_cluster_data_active):
        """Test successful cluster data collection."""
        # Mock ecs_api_operation response
        mock_ecs_api.return_value = {"clusters": [mock_cluster_data_active]}

        # Create adapter and collect data
        adapter = DataAdapter()
        result = await adapter.collect_cluster_data("test-cluster", "us-east-1")

        # Verify ecs_api_operation was called correctly
        mock_ecs_api.assert_called_once_with(
            "DescribeClusters",
            {"clusters": ["test-cluster"], "include": ["SETTINGS", "CONFIGURATIONS", "TAGS"]},
        )

        # Verify result
        assert result["status"] == "success"
        assert result["cluster"]["clusterName"] == "test-cluster"
        assert result["region"] == "us-east-1"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_cluster_data_error(self, mock_ecs_api):
        """Test cluster data collection with API error."""
        # Mock ecs_api_operation error response
        mock_ecs_api.return_value = {"error": "Access denied"}

        # Create adapter and collect data
        adapter = DataAdapter()
        result = await adapter.collect_cluster_data("test-cluster", "us-east-1")

        # Verify error handling
        assert "error" in result
        assert result["error"] == "Access denied"
        assert result["cluster_name"] == "test-cluster"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_cluster_data_not_found(self, mock_ecs_api):
        """Test cluster data collection when cluster not found."""
        # Mock ecs_api_operation response with empty clusters
        mock_ecs_api.return_value = {"clusters": []}

        # Create adapter and collect data
        adapter = DataAdapter()
        result = await adapter.collect_cluster_data("nonexistent-cluster", "us-east-1")

        # Verify error handling
        assert "error" in result
        assert result["error"] == "Cluster not found"
        assert result["cluster_name"] == "nonexistent-cluster"


# SecurityAnalyzer Tests
class TestClusterSecurity:
    """Tests for cluster security analysis."""

    def test_analyze_container_insights_disabled(self, mock_cluster_data_no_insights):
        """Test detection of disabled Container Insights."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze({"cluster": mock_cluster_data_no_insights})

        # Verify Container Insights recommendation is present
        insights_recs = [
            r for r in result["recommendations"] if r["title"] == "Container Insights Disabled"
        ]
        assert len(insights_recs) == 1
        assert insights_recs[0]["severity"] == "Medium"
        assert insights_recs[0]["category"] == "Monitoring"

    def test_analyze_container_insights_enabled(self, mock_cluster_data_active):
        """Test that enabled Container Insights doesn't generate recommendation."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze({"cluster": mock_cluster_data_active})

        # Verify no Container Insights recommendation
        insights_recs = [
            r for r in result["recommendations"] if r["title"] == "Container Insights Disabled"
        ]
        assert len(insights_recs) == 0

    def test_analyze_execute_command_missing(self, mock_cluster_data_no_logging):
        """Test detection of missing execute command logging."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze({"cluster": mock_cluster_data_no_logging})

        # Verify execute command logging recommendation is present
        exec_recs = [
            r
            for r in result["recommendations"]
            if r["title"] == "Execute Command Logging Not Configured"
        ]
        assert len(exec_recs) == 1
        assert exec_recs[0]["severity"] == "Medium"
        assert exec_recs[0]["category"] == "Logging"

    def test_analyze_cluster_status_inactive(self, mock_cluster_data_inactive):
        """Test detection of inactive cluster status."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze({"cluster": mock_cluster_data_inactive})

        # Verify cluster status recommendation is present
        status_recs = [r for r in result["recommendations"] if r["title"] == "Cluster Not Active"]
        assert len(status_recs) == 1
        assert status_recs[0]["severity"] == "High"
        assert status_recs[0]["category"] == "Availability"

    def test_analyze_with_error(self):
        """Test analysis with error in data."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze({"error": "Test error"})

        # Verify error handling
        assert result["status"] == "error"
        assert result["error"] == "Test error"
        assert len(result["recommendations"]) == 0


class TestLoggingSecurity:
    """Tests for logging security analysis."""

    def test_analyze_logging_disabled(self, mock_cluster_data_no_logging):
        """Test detection of disabled CloudWatch logging."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze({"cluster": mock_cluster_data_no_logging})

        # Verify CloudWatch logging recommendation is present
        logging_recs = [
            r for r in result["recommendations"] if r["title"] == "CloudWatch Logging Not Enabled"
        ]
        assert len(logging_recs) == 1
        assert logging_recs[0]["severity"] == "Medium"
        assert logging_recs[0]["category"] == "Logging"


class TestSummaryGeneration:
    """Tests for summary generation."""

    def test_generate_summary(self, mock_cluster_data_no_insights):
        """Test summary statistics generation."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze({"cluster": mock_cluster_data_no_insights})

        # Verify summary structure
        assert "summary" in result
        assert "total_issues" in result["summary"]
        assert "by_severity" in result["summary"]
        assert "by_category" in result["summary"]

        # Verify counts
        assert result["summary"]["total_issues"] > 0
        assert result["summary"]["by_severity"]["Medium"] > 0


# Integration Tests
class TestAnalyzeECSSecurity:
    """Tests for main analyze_ecs_security function."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_analyze_with_cluster_names(self, mock_ecs_api, mock_cluster_data_active):
        """Test analysis with specific cluster names."""
        # Mock ecs_api_operation response
        mock_ecs_api.return_value = {"clusters": [mock_cluster_data_active]}

        # Run analysis
        result = await analyze_ecs_security(cluster_names=["test-cluster"], regions=["us-east-1"])

        # Verify result structure
        assert result["status"] == "success"
        assert result["total_clusters_analyzed"] == 1
        assert "results" in result

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_analyze_discover_clusters(self, mock_ecs_api, mock_cluster_data_active):
        """Test analysis with cluster discovery."""

        # Mock ListClusters response
        def mock_api_operation(operation, params):
            if operation == "ListClusters":
                return {"clusterArns": ["arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster"]}
            elif operation == "DescribeClusters":
                return {"clusters": [mock_cluster_data_active]}
            return {}

        mock_ecs_api.side_effect = mock_api_operation

        # Run analysis without cluster names
        result = await analyze_ecs_security(regions=["us-east-1"])

        # Verify cluster discovery was called
        assert result["status"] == "success"
        assert result["total_clusters_analyzed"] >= 1

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_analyze_no_clusters_found(self, mock_ecs_api):
        """Test analysis when no clusters are found."""
        # Mock ListClusters response with no clusters
        mock_ecs_api.return_value = {"clusterArns": []}

        # Run analysis
        result = await analyze_ecs_security()

        # Verify result
        assert result["status"] == "success"
        assert result["message"] == "No clusters found"
        assert len(result["results"]) == 0

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_analyze_list_clusters_error(self, mock_ecs_api):
        """Test analysis when ListClusters fails."""
        # Mock ListClusters error response
        mock_ecs_api.return_value = {"error": "Access denied"}

        # Run analysis
        result = await analyze_ecs_security()

        # Verify error handling
        assert result["status"] == "error"
        assert "Failed to list clusters" in result["error"]
