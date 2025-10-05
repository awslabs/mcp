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

    @pytest.mark.asyncio
    async def test_collect_cluster_data_not_found(self):
        """Test cluster data collection when cluster is not found."""
        adapter = DataAdapter()
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"clusters": []}

            result = await adapter.collect_cluster_data("nonexistent-cluster", "us-east-1")

            assert result["status"] == "error"
            assert "not found" in result["error"]
            assert result["cluster_name"] == "nonexistent-cluster"

    @pytest.mark.asyncio
    async def test_collect_cluster_data_exception(self):
        """Test cluster data collection with unexpected exception."""
        adapter = DataAdapter()
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.side_effect = Exception("Network error")

            result = await adapter.collect_cluster_data("test-cluster", "us-east-1")

            assert result["status"] == "error"
            assert "Network error" in result["error"]


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

    def test_analyze_inactive_cluster(self):
        """Test analysis when cluster is not ACTIVE."""
        analyzer = SecurityAnalyzer()
        ecs_data = {
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "cluster": {
                "clusterName": "test-cluster",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                "status": "INACTIVE",
                "settings": [],
            },
        }

        result = analyzer.analyze(ecs_data)

        assert "recommendations" in result
        status_recs = [r for r in result["recommendations"] if "Cluster Status" in r["title"]]
        assert len(status_recs) == 1
        assert status_recs[0]["severity"] == "High"


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

    @pytest.mark.asyncio
    async def test_analyze_with_analysis_exception(self, mock_cluster_data):
        """Test analysis when SecurityAnalyzer raises exception."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            with patch(
                "awslabs.ecs_mcp_server.api.security_analysis.SecurityAnalyzer.analyze"
            ) as mock_analyze:
                mock_api.return_value = mock_cluster_data
                mock_analyze.side_effect = Exception("Analysis failed")

                result = await analyze_ecs_security(cluster_names=["test-cluster"])

                assert result["status"] == "success"
                assert "errors" in result
                assert len(result["errors"]) > 0


# ============================================================================
# COMPREHENSIVE TESTS - PR #2
# ============================================================================


@pytest.fixture
def mock_multiple_clusters():
    """Fixture for multiple clusters data."""
    return {
        "clusters": [
            {
                "clusterName": "cluster-1",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/cluster-1",
                "status": "ACTIVE",
                "settings": [{"name": "containerInsights", "value": "enabled"}],
            },
            {
                "clusterName": "cluster-2",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/cluster-2",
                "status": "ACTIVE",
                "settings": [],
            },
        ]
    }


@pytest.fixture
def mock_cluster_with_mixed_status():
    """Fixture for cluster with mixed status."""
    return {
        "clusters": [
            {
                "clusterName": "active-cluster",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/active-cluster",
                "status": "ACTIVE",
                "settings": [{"name": "containerInsights", "value": "enabled"}],
            }
        ]
    }


class TestDataAdapterComprehensive:
    """Comprehensive tests for DataAdapter class."""

    @pytest.mark.asyncio
    async def test_collect_cluster_data_with_different_regions(self, mock_cluster_data):
        """Test cluster data collection across different regions."""
        adapter = DataAdapter()
        regions = ["us-east-1", "us-west-2", "eu-west-1"]

        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = mock_cluster_data

            for region in regions:
                result = await adapter.collect_cluster_data("test-cluster", region)

                assert result["status"] == "success"
                assert result["region"] == region
                assert result["cluster_name"] == "test-cluster"

    @pytest.mark.asyncio
    async def test_collect_cluster_data_empty_response(self):
        """Test cluster data collection with empty response."""
        adapter = DataAdapter()
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {}

            result = await adapter.collect_cluster_data("test-cluster", "us-east-1")

            assert result["status"] == "error"
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_collect_cluster_data_malformed_response(self):
        """Test cluster data collection with malformed response."""
        adapter = DataAdapter()
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"clusters": None}

            result = await adapter.collect_cluster_data("test-cluster", "us-east-1")

            assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_collect_cluster_data_timeout(self):
        """Test cluster data collection with timeout."""
        adapter = DataAdapter()
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.side_effect = TimeoutError("Request timed out")

            result = await adapter.collect_cluster_data("test-cluster", "us-east-1")

            assert result["status"] == "error"
            assert "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_collect_cluster_data_with_special_characters(self):
        """Test cluster data collection with special characters in name."""
        adapter = DataAdapter()
        special_names = ["test-cluster_123", "test.cluster", "test-cluster-prod"]

        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"clusters": []}

            for name in special_names:
                result = await adapter.collect_cluster_data(name, "us-east-1")
                assert result["cluster_name"] == name


class TestSecurityAnalyzerComprehensive:
    """Comprehensive tests for SecurityAnalyzer class."""

    def test_analyze_with_multiple_recommendations(self, mock_cluster_data_no_insights):
        """Test analysis generating multiple recommendations."""
        analyzer = SecurityAnalyzer()
        ecs_data = {
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "cluster": {
                "clusterName": "test-cluster",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                "status": "INACTIVE",
                "settings": [],
            },
        }

        result = analyzer.analyze(ecs_data)

        assert "recommendations" in result
        # Should have both Container Insights and status recommendations
        assert len(result["recommendations"]) >= 2

    def test_analyze_with_empty_cluster_data(self):
        """Test analysis with empty cluster data."""
        analyzer = SecurityAnalyzer()
        ecs_data = {
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "cluster": {},
        }

        result = analyzer.analyze(ecs_data)

        assert "recommendations" in result
        assert "summary" in result

    def test_analyze_with_missing_settings(self):
        """Test analysis when settings field is missing."""
        analyzer = SecurityAnalyzer()
        ecs_data = {
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "cluster": {
                "clusterName": "test-cluster",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                "status": "ACTIVE",
            },
        }

        result = analyzer.analyze(ecs_data)

        assert "recommendations" in result
        # Should recommend enabling Container Insights
        insights_recs = [r for r in result["recommendations"] if "Container Insights" in r["title"]]
        assert len(insights_recs) == 1

    def test_analyze_summary_structure(self, mock_cluster_data):
        """Test that analysis summary has correct structure."""
        analyzer = SecurityAnalyzer()
        ecs_data = {
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "cluster": mock_cluster_data["clusters"][0],
        }

        result = analyzer.analyze(ecs_data)

        assert "summary" in result
        summary = result["summary"]
        assert "total_findings" in summary
        assert "by_severity" in summary
        assert "by_category" in summary
        assert isinstance(summary["total_findings"], int)
        assert isinstance(summary["by_severity"], dict)
        assert isinstance(summary["by_category"], dict)

    def test_analyze_recommendation_structure(self, mock_cluster_data_no_insights):
        """Test that recommendations have correct structure."""
        analyzer = SecurityAnalyzer()
        ecs_data = {
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "cluster": mock_cluster_data_no_insights["clusters"][0],
        }

        result = analyzer.analyze(ecs_data)

        assert len(result["recommendations"]) > 0
        rec = result["recommendations"][0]
        assert "title" in rec
        assert "severity" in rec
        assert "category" in rec
        assert "resource" in rec
        assert "issue" in rec
        assert "recommendation" in rec

    def test_analyze_severity_levels(self):
        """Test that severity levels are correctly assigned."""
        analyzer = SecurityAnalyzer()

        # Test High severity for inactive cluster
        ecs_data_inactive = {
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "cluster": {
                "clusterName": "test-cluster",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                "status": "INACTIVE",
                "settings": [],
            },
        }

        result = analyzer.analyze(ecs_data_inactive)
        status_recs = [r for r in result["recommendations"] if "Cluster Status" in r["title"]]
        assert status_recs[0]["severity"] == "High"

        # Test Medium severity for Container Insights
        ecs_data_no_insights = {
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "cluster": {
                "clusterName": "test-cluster",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
                "status": "ACTIVE",
                "settings": [],
            },
        }

        result = analyzer.analyze(ecs_data_no_insights)
        insights_recs = [r for r in result["recommendations"] if "Container Insights" in r["title"]]
        assert insights_recs[0]["severity"] == "Medium"


class TestAnalyzeECSSecurityComprehensive:
    """Comprehensive tests for analyze_ecs_security function."""

    @pytest.mark.asyncio
    async def test_analyze_multiple_clusters(self, mock_multiple_clusters):
        """Test analysis with multiple clusters."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = mock_multiple_clusters

            result = await analyze_ecs_security(cluster_names=["cluster-1", "cluster-2"])

            assert result["status"] == "success"
            assert "recommendations" in result
            assert "summary" in result
            assert result["summary"]["clusters_analyzed"] == 2

    @pytest.mark.asyncio
    async def test_analyze_multiple_regions(self, mock_cluster_data):
        """Test analysis across multiple regions."""
        regions = ["us-east-1", "us-west-2"]

        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = mock_cluster_data

            result = await analyze_ecs_security(cluster_names=["test-cluster"], regions=regions)

            assert result["status"] == "success"
            assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_analyze_partial_success(self):
        """Test analysis with partial success (some clusters fail)."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:

            def side_effect_func(*args, **kwargs):
                if "cluster-1" in str(kwargs):
                    return {
                        "clusters": [
                            {
                                "clusterName": "cluster-1",
                                "clusterArn": (
                                    "arn:aws:ecs:us-east-1:123456789012:cluster/cluster-1"
                                ),
                                "status": "ACTIVE",
                                "settings": [],
                            }
                        ]
                    }
                else:
                    return {"error": "Access denied"}

            mock_api.side_effect = side_effect_func

            result = await analyze_ecs_security(cluster_names=["cluster-1", "cluster-2"])

            assert result["status"] == "success"
            assert "errors" in result
            assert len(result["errors"]) > 0
            assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_analyze_with_empty_cluster_list(self):
        """Test analysis with empty cluster list."""
        result = await analyze_ecs_security(cluster_names=[])

        assert result["status"] == "success"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_analyze_with_none_parameters(self):
        """Test analysis with None parameters."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.find_clusters") as mock_find:
            mock_find.return_value = []

            result = await analyze_ecs_security(cluster_names=None, regions=None)

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_analyze_summary_aggregation(self, mock_multiple_clusters):
        """Test that summary correctly aggregates findings."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = mock_multiple_clusters

            result = await analyze_ecs_security(cluster_names=["cluster-1", "cluster-2"])

            assert result["status"] == "success"
            summary = result["summary"]
            assert summary["total_findings"] >= 0
            assert "by_severity" in summary
            assert "by_category" in summary

    @pytest.mark.asyncio
    async def test_analyze_error_collection(self):
        """Test that errors are properly collected and reported."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"error": "Service unavailable"}

            result = await analyze_ecs_security(cluster_names=["cluster-1", "cluster-2"])

            assert result["status"] == "success"
            assert "errors" in result
            assert len(result["errors"]) == 2

    @pytest.mark.asyncio
    async def test_analyze_with_find_clusters_integration(self, mock_cluster_data):
        """Test integration with find_clusters function."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.find_clusters") as mock_find:
            with patch(
                "awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation"
            ) as mock_api:
                mock_find.return_value = ["cluster-1", "cluster-2"]
                mock_api.return_value = mock_cluster_data

                result = await analyze_ecs_security()

                assert result["status"] == "success"
                mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_response_structure(self, mock_cluster_data):
        """Test that response has correct structure."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = mock_cluster_data

            result = await analyze_ecs_security(cluster_names=["test-cluster"])

            assert "status" in result
            assert "recommendations" in result
            assert "summary" in result
            assert "analyzed_clusters" in result
            assert isinstance(result["recommendations"], list)
            assert isinstance(result["summary"], dict)
            assert isinstance(result["analyzed_clusters"], list)

    @pytest.mark.asyncio
    async def test_analyze_with_all_clusters_failing(self):
        """Test analysis when all clusters fail."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"error": "Access denied"}

            result = await analyze_ecs_security(cluster_names=["cluster-1", "cluster-2"])

            assert result["status"] == "success"
            assert "errors" in result
            assert len(result["errors"]) == 2
            assert result["summary"]["total_findings"] == 0

    @pytest.mark.asyncio
    async def test_analyze_logging_behavior(self, mock_cluster_data, caplog):
        """Test that appropriate logging occurs during analysis."""
        import logging

        caplog.set_level(logging.INFO)

        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = mock_cluster_data

            await analyze_ecs_security(cluster_names=["test-cluster"])

            # Check that INFO level logs were created
            assert any(record.levelname == "INFO" for record in caplog.records)

    @pytest.mark.asyncio
    async def test_analyze_with_duplicate_cluster_names(self, mock_cluster_data):
        """Test analysis with duplicate cluster names."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = mock_cluster_data

            result = await analyze_ecs_security(
                cluster_names=["test-cluster", "test-cluster", "test-cluster"]
            )

            assert result["status"] == "success"
            # Should handle duplicates gracefully
            assert "recommendations" in result
