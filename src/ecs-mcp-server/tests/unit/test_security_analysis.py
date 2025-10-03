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

"""Unit tests for security analysis API with task definition support."""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.security_analysis import (
    DataAdapter,
    SecurityAnalyzer,
    analyze_ecs_security,
    register_module,
)


class TestDataAdapter:
    """Test cases for DataAdapter class."""

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
    async def test_collect_task_definitions_success(self) -> None:
        """Test successful task definition collection."""
        adapter = DataAdapter()
        mock_list = {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/test-cluster/svc"]}
        mock_describe = {
            "services": [
                {
                    "serviceName": "svc",
                    "taskDefinition": "arn:aws:ecs:us-east-1:123456789012:task-definition/task:1",
                }
            ]
        }
        mock_task = {
            "taskDefinition": {
                "family": "task",
                "revision": 1,
                "containerDefinitions": [{"name": "container", "image": "nginx:latest"}],
            }
        }

        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.side_effect = [mock_list, mock_describe, mock_task]
            result = await adapter.collect_task_definitions("test-cluster")
            assert result["status"] == "success"
            assert len(result["task_definitions"]) == 1


class TestSecurityAnalyzer:
    """Test cases for SecurityAnalyzer class."""

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

    def test_analyze_container_security_root_user(self) -> None:
        """Test container security analysis for root user detection."""
        analyzer = SecurityAnalyzer()
        cluster_data = {"cluster_name": "test-cluster"}
        task_data = {
            "status": "success",
            "task_definitions": [
                {
                    "family": "task",
                    "containerDefinitions": [
                        {"name": "root-container", "user": "0", "image": "nginx:latest"},
                        {"name": "no-user-container", "image": "nginx:latest"},
                    ],
                }
            ],
        }
        result = analyzer.analyze(cluster_data, task_data)
        root_recs = [r for r in result["recommendations"] if "Non-Root User" in r["title"]]
        assert len(root_recs) == 2
        assert all(r["severity"] == "High" for r in root_recs)

    def test_analyze_container_security_privileged_mode(self) -> None:
        """Test container security analysis for privileged mode."""
        analyzer = SecurityAnalyzer()
        cluster_data = {"cluster_name": "test-cluster"}
        task_data = {
            "status": "success",
            "task_definitions": [
                {
                    "family": "task",
                    "containerDefinitions": [
                        {
                            "name": "privileged-container",
                            "privileged": True,
                            "image": "nginx:latest",
                        }
                    ],
                }
            ],
        }
        result = analyzer.analyze(cluster_data, task_data)
        priv_recs = [r for r in result["recommendations"] if "Privileged Container" in r["title"]]
        assert len(priv_recs) == 1
        assert priv_recs[0]["severity"] == "Critical"


class TestAnalyzeEcsSecurity:
    """Test cases for analyze_ecs_security function."""

    @pytest.mark.anyio
    async def test_analyze_ecs_security_success(self) -> None:
        """Test successful security analysis."""
        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.return_value = {"clusters": [{"clusterName": "test-cluster", "settings": []}]}
            result = await analyze_ecs_security(cluster_names=["test-cluster"])
            assert result["status"] == "success"
            assert result["total_issues"] == 1  # Container Insights disabled

    @pytest.mark.anyio
    async def test_analyze_ecs_security_with_task_definitions(self) -> None:
        """Test end-to-end security analysis with task definitions."""
        mock_cluster = {"clusters": [{"clusterName": "test-cluster", "settings": []}]}
        mock_list = {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/test-cluster/svc"]}
        mock_describe = {
            "services": [
                {
                    "serviceName": "svc",
                    "taskDefinition": "arn:aws:ecs:us-east-1:123456789012:task-definition/task:1",
                }
            ]
        }
        mock_task = {
            "taskDefinition": {
                "family": "task",
                "revision": 1,
                "containerDefinitions": [
                    {"name": "insecure-container", "user": "0", "image": "nginx:latest"}
                ],
            }
        }

        with patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation") as mock_api:
            mock_api.side_effect = [mock_cluster, mock_list, mock_describe, mock_task]
            result = await analyze_ecs_security(
                cluster_names=["test-cluster"], analysis_scope="comprehensive"
            )
            assert result["status"] == "success"
            assert result["total_issues"] >= 2  # Container Insights + root user
            titles = [r["title"] for r in result["recommendations"]]
            assert any("Container Insights" in title for title in titles)
            assert any("Non-Root User" in title for title in titles)


class TestModuleRegistration:
    """Test cases for module registration."""

    def test_register_module(self) -> None:
        """Test module registration with MCP."""
        mock_mcp = MagicMock()
        register_module(mock_mcp)
        mock_mcp.tool.assert_called_once_with(name="analyze_ecs_security")


class TestDataAdapterErrorPaths:
    """Test error handling in DataAdapter."""

    @pytest.mark.anyio
    async def test_collect_cluster_data_api_error(self) -> None:
        """Test collect_cluster_data with API error."""
        adapter = DataAdapter()
        with patch(
            "awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation",
            return_value={"error": "API Error"},
        ):
            result = await adapter.collect_cluster_data("test-cluster")
            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.anyio
    async def test_collect_cluster_data_empty_clusters(self) -> None:
        """Test collect_cluster_data with no clusters returned."""
        adapter = DataAdapter()
        with patch(
            "awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation",
            return_value={"clusters": []},
        ):
            result = await adapter.collect_cluster_data("test-cluster")
            assert result["status"] == "failed"
            assert "not found" in result["error"]

    @pytest.mark.anyio
    async def test_collect_cluster_data_exception(self) -> None:
        """Test collect_cluster_data with exception."""
        adapter = DataAdapter()
        with patch(
            "awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation",
            side_effect=Exception("Test exception"),
        ):
            result = await adapter.collect_cluster_data("test-cluster")
            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.anyio
    async def test_collect_task_definitions_list_services_error(self) -> None:
        """Test collect_task_definitions with ListServices error."""
        adapter = DataAdapter()
        with patch(
            "awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation",
            return_value={"error": "ListServices failed"},
        ):
            result = await adapter.collect_task_definitions("test-cluster")
            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.anyio
    async def test_collect_task_definitions_describe_services_error(self) -> None:
        """Test collect_task_definitions with DescribeServices error."""
        adapter = DataAdapter()
        with patch(
            "awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation",
            side_effect=[
                {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/test"]},
                {"error": "DescribeServices failed"},
            ],
        ):
            result = await adapter.collect_task_definitions("test-cluster")
            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.anyio
    async def test_collect_task_definitions_exception(self) -> None:
        """Test collect_task_definitions with exception."""
        adapter = DataAdapter()
        with patch(
            "awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation",
            side_effect=Exception("Test exception"),
        ):
            result = await adapter.collect_task_definitions("test-cluster")
            assert result["status"] == "failed"
            assert "error" in result


class TestSecurityAnalyzerErrorPaths:
    """Test error handling in SecurityAnalyzer."""

    def test_analyze_with_exception(self) -> None:
        """Test analyze method with exception."""
        analyzer = SecurityAnalyzer()
        # Pass invalid data to trigger exception
        result = analyzer.analyze(None, None)
        assert result["status"] == "failed"
        assert "error" in result


class TestAnalyzeEcsSecurityErrorPaths:
    """Test error handling in analyze_ecs_security function."""

    @pytest.mark.anyio
    async def test_analyze_ecs_security_no_cluster_names(self) -> None:
        """Test analyze_ecs_security without cluster names."""
        result = await analyze_ecs_security(cluster_names=None)
        assert result["status"] == "failed"
        assert "cluster_names parameter is required" in result["error"]

    @pytest.mark.anyio
    async def test_analyze_ecs_security_cluster_data_failed(self) -> None:
        """Test analyze_ecs_security with failed cluster data collection."""
        with patch.object(
            DataAdapter,
            "collect_cluster_data",
            return_value={"status": "failed", "error": "Cluster not found"},
        ):
            result = await analyze_ecs_security(cluster_names=["test-cluster"])
            assert result["status"] == "success"
            assert result["total_issues"] == 0

    @pytest.mark.anyio
    async def test_analyze_ecs_security_task_definitions_failed(self) -> None:
        """Test analyze_ecs_security with failed task definition collection."""
        with (
            patch.object(
                DataAdapter,
                "collect_cluster_data",
                return_value={
                    "cluster": {"clusterName": "test-cluster", "settings": []},
                    "cluster_name": "test-cluster",
                    "status": "success",
                },
            ),
            patch.object(
                DataAdapter,
                "collect_task_definitions",
                return_value={"status": "failed", "error": "API error"},
            ),
        ):
            result = await analyze_ecs_security(
                cluster_names=["test-cluster"], analysis_scope="comprehensive"
            )
            assert result["status"] == "success"

    @pytest.mark.anyio
    async def test_analyze_ecs_security_cluster_exception(self) -> None:
        """Test analyze_ecs_security with exception during cluster analysis."""
        with patch.object(
            DataAdapter, "collect_cluster_data", side_effect=Exception("Test exception")
        ):
            result = await analyze_ecs_security(cluster_names=["test-cluster"])
            assert result["status"] == "success"
            assert result["total_issues"] == 0

    @pytest.mark.anyio
    async def test_analyze_ecs_security_general_exception(self) -> None:
        """Test analyze_ecs_security with general exception."""
        with patch(
            "awslabs.ecs_mcp_server.api.security_analysis.DataAdapter",
            side_effect=Exception("Test exception"),
        ):
            result = await analyze_ecs_security(cluster_names=["test-cluster"])
            assert result["status"] == "failed"
            assert "error" in result
