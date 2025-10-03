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
Unit tests for security analysis API - minimal implementation for PR #2.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.security_analysis import (
    DataAdapter,
    SecurityAnalyzer,
    analyze_ecs_security,
    register_module,
)


class TestDataAdapter:
    """Test cases for minimal DataAdapter class."""

    def test_init(self) -> None:
        """Test DataAdapter initialization."""
        adapter = DataAdapter()
        assert adapter.logger is not None

    @pytest.mark.anyio
    async def test_collect_cluster_data_success(self) -> None:
        """Test successful cluster data collection."""
        adapter = DataAdapter()

        mock_response = {"clusters": [{"clusterName": "test-cluster", "status": "ACTIVE"}]}

        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = mock_response

            result = await adapter.collect_cluster_data("test-cluster")

            assert result["status"] == "success"
            assert result["cluster_name"] == "test-cluster"

    @pytest.mark.anyio
    async def test_collect_cluster_data_not_found(self) -> None:
        """Test cluster data collection when cluster is not found."""
        adapter = DataAdapter()

        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"clusters": []}

            result = await adapter.collect_cluster_data("nonexistent-cluster")

            assert result["status"] == "failed"
            assert "not found" in result["error"]

    @pytest.mark.anyio
    async def test_collect_cluster_data_api_error(self) -> None:
        """Test cluster data collection with API error."""
        adapter = DataAdapter()

        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"error": "Access denied"}

            result = await adapter.collect_cluster_data("test-cluster")

            assert result["status"] == "failed"
            assert "Access denied" in result["error"]

    @pytest.mark.anyio
    async def test_collect_cluster_data_exception(self) -> None:
        """Test cluster data collection with exception."""
        adapter = DataAdapter()

        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.side_effect = Exception("Network error")

            result = await adapter.collect_cluster_data("test-cluster")

            assert result["status"] == "failed"
            assert "Network error" in result["error"]


class TestSecurityAnalyzer:
    """Test cases for minimal SecurityAnalyzer class."""

    def test_init(self) -> None:
        """Test SecurityAnalyzer initialization."""
        analyzer = SecurityAnalyzer()
        assert analyzer.logger is not None

    def test_analyze_with_container_insights_disabled(self) -> None:
        """Test analysis when Container Insights is disabled."""
        analyzer = SecurityAnalyzer()

        cluster_data = {
            "cluster": {"clusterName": "test-cluster", "settings": []},
            "cluster_name": "test-cluster",
        }

        result = analyzer.analyze(cluster_data)

        assert result["status"] == "success"
        assert len(result["recommendations"]) == 1
        assert "Container Insights" in result["recommendations"][0]["title"]

    def test_analyze_with_container_insights_enabled(self) -> None:
        """Test analysis when Container Insights is enabled."""
        analyzer = SecurityAnalyzer()

        cluster_data = {
            "cluster": {
                "clusterName": "test-cluster",
                "settings": [{"name": "containerInsights", "value": "enabled"}],
            },
            "cluster_name": "test-cluster",
        }

        result = analyzer.analyze(cluster_data)

        assert result["status"] == "success"
        assert len(result["recommendations"]) == 0

    def test_analyze_exception(self) -> None:
        """Test analysis with exception."""
        analyzer = SecurityAnalyzer()

        with patch("awslabs.ecs_mcp_server.api.security_analysis.datetime") as mock_datetime:
            mock_datetime.utcnow.side_effect = Exception("Time error")

            result = analyzer.analyze({})

            assert result["status"] == "failed"
            assert "Time error" in result["error"]

    def test_generate_summary(self) -> None:
        """Test analysis summary generation."""
        analyzer = SecurityAnalyzer()

        recommendations = [
            {"severity": "Medium", "category": "monitoring"},
            {"severity": "High", "category": "security"},
        ]

        summary = analyzer._generate_summary(recommendations)

        assert summary["total_recommendations"] == 2
        assert summary["severity_breakdown"]["Medium"] == 1
        assert summary["severity_breakdown"]["High"] == 1


class TestAnalyzeEcsSecurity:
    """Test cases for minimal analyze_ecs_security function."""

    @pytest.mark.anyio
    async def test_analyze_ecs_security_no_clusters(self) -> None:
        """Test security analysis with no cluster names provided."""
        result = await analyze_ecs_security()

        assert result["status"] == "failed"
        assert "cluster_names parameter is required" in result["error"]

    @pytest.mark.anyio
    async def test_analyze_ecs_security_success(self) -> None:
        """Test successful security analysis."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"clusters": [{"clusterName": "test-cluster", "settings": []}]}

            result = await analyze_ecs_security(cluster_names=["test-cluster"])

            assert result["status"] == "success"
            assert result["total_issues"] == 1

    @pytest.mark.anyio
    async def test_analyze_ecs_security_data_collection_failure(self) -> None:
        """Test security analysis with data collection failure."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"error": "Access denied"}

            result = await analyze_ecs_security(cluster_names=["test-cluster"])

            assert result["status"] == "success"
            assert result["total_issues"] == 0  # No clusters analyzed due to failure

    @pytest.mark.anyio
    async def test_analyze_ecs_security_exception(self) -> None:
        """Test security analysis with exception."""
        with patch(
            "awslabs.ecs_mcp_server.api.security_analysis.DataAdapter"
        ) as mock_adapter_class:
            mock_adapter_class.side_effect = Exception("Test exception")

            result = await analyze_ecs_security(cluster_names=["test-cluster"])

            assert result["status"] == "failed"
            assert "Test exception" in result["error"]


class TestModuleRegistration:
    """Test cases for module registration."""

    @pytest.mark.anyio
    async def test_register_module(self) -> None:
        """Test module registration with MCP."""
        mock_mcp = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_tool_decorator

        register_module(mock_mcp)

        mock_mcp.tool.assert_called_once_with(name="analyze_ecs_security")


class TestIntegration:
    """Integration tests - minimal implementation."""

    def test_module_imports(self) -> None:
        """Test that all modules import correctly."""
        from awslabs.ecs_mcp_server.api import security_analysis

        assert security_analysis is not None
