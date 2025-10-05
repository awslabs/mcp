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

This module tests the security analysis functionality for ECS clusters.
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

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_cluster_data_exception(self, mock_ecs_api):
        """Test cluster data collection with unexpected exception."""
        # Mock ecs_api_operation to raise exception
        mock_ecs_api.side_effect = Exception("Unexpected error")

        # Create adapter and collect data
        adapter = DataAdapter()
        result = await adapter.collect_cluster_data("test-cluster", "us-east-1")

        # Verify error handling
        assert "error" in result
        assert "Unexpected error" in result["error"]
        assert result["cluster_name"] == "test-cluster"


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
# IAM Security Tests
class TestIAMSecurity:
    """Tests for IAM security analysis."""

    @pytest.fixture
    def mock_task_def_with_wildcard(self):
        """Mock task definition with wildcard in role ARN."""
        return {
            "family": "test-task",
            "taskRoleArn": "arn:aws:iam::123456789012:role/*",
            "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
        }

    @pytest.fixture
    def mock_task_def_custom_execution_role(self):
        """Mock task definition with custom execution role."""
        return {
            "family": "test-task",
            "taskRoleArn": "arn:aws:iam::123456789012:role/myTaskRole",
            "executionRoleArn": "arn:aws:iam::123456789012:role/myCustomExecutionRole",
        }

    @pytest.fixture
    def mock_task_def_cross_account(self):
        """Mock task definition with cross-account role."""
        return {
            "family": "test-task",
            "taskRoleArn": "arn:aws:iam::999999999999:role/crossAccountRole",
            "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
        }

    @pytest.fixture
    def mock_cluster_no_service_linked_role(self):
        """Mock cluster without service-linked role."""
        return {
            "clusterName": "test-cluster",
            "status": "ACTIVE",
            "settings": [{"name": "containerInsights", "value": "enabled"}],
            "configuration": {"executeCommandConfiguration": {"logging": "DEFAULT"}},
        }

    @pytest.fixture
    def mock_cluster_with_service_linked_role(self):
        """Mock cluster with service-linked role."""
        return {
            "clusterName": "test-cluster",
            "status": "ACTIVE",
            "serviceLinkedRoleArn": (
                "arn:aws:iam::123456789012:role/aws-service-role/ecs.amazonaws.com/"
                "AWSServiceRoleForECS"
            ),
            "settings": [{"name": "containerInsights", "value": "enabled"}],
            "configuration": {"executeCommandConfiguration": {"logging": "DEFAULT"}},
        }

    def test_analyze_cluster_iam_no_service_linked_role(self, mock_cluster_no_service_linked_role):
        """Test detection of missing service-linked role."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze({"cluster": mock_cluster_no_service_linked_role})

        # Verify service-linked role recommendation
        iam_recs = [
            r
            for r in result["recommendations"]
            if r["title"] == "Configure ECS Service-Linked Role"
        ]
        assert len(iam_recs) == 1
        assert iam_recs[0]["severity"] == "Medium"
        assert iam_recs[0]["category"] == "IAM"

    def test_analyze_cluster_iam_with_service_linked_role(
        self, mock_cluster_with_service_linked_role
    ):
        """Test that service-linked role presence doesn't generate recommendation."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze({"cluster": mock_cluster_with_service_linked_role})

        # Verify no service-linked role recommendation
        iam_recs = [
            r
            for r in result["recommendations"]
            if r["title"] == "Configure ECS Service-Linked Role"
        ]
        assert len(iam_recs) == 0

    def test_analyze_iam_wildcard_permissions(
        self, mock_cluster_data_active, mock_task_def_with_wildcard
    ):
        """Test detection of wildcard permissions in task role."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "task_definitions": [mock_task_def_with_wildcard],
            }
        )

        # Verify wildcard permission recommendation
        wildcard_recs = [
            r
            for r in result["recommendations"]
            if r["title"] == "Avoid Wildcard Permissions in Task IAM Role"
        ]
        assert len(wildcard_recs) == 1
        assert wildcard_recs[0]["severity"] == "High"
        assert wildcard_recs[0]["category"] == "IAM"

    def test_analyze_iam_custom_execution_role(
        self, mock_cluster_data_active, mock_task_def_custom_execution_role
    ):
        """Test detection of custom execution role."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "task_definitions": [mock_task_def_custom_execution_role],
            }
        )

        # Verify custom execution role recommendation
        custom_role_recs = [
            r
            for r in result["recommendations"]
            if r["title"] == "Use Managed Execution Role Policy"
        ]
        assert len(custom_role_recs) == 1
        assert custom_role_recs[0]["severity"] == "Medium"
        assert custom_role_recs[0]["category"] == "IAM"

    def test_analyze_iam_cross_account_role(
        self, mock_cluster_data_active, mock_task_def_cross_account
    ):
        """Test detection of cross-account role usage."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "task_definitions": [mock_task_def_cross_account],
            }
        )

        # Verify cross-account role recommendation
        cross_account_recs = [
            r
            for r in result["recommendations"]
            if r["title"] == "Review Cross-Account IAM Role Usage"
        ]
        assert len(cross_account_recs) == 1
        assert cross_account_recs[0]["severity"] == "Medium"
        assert cross_account_recs[0]["category"] == "IAM"

    def test_analyze_iam_multiple_task_definitions(
        self,
        mock_cluster_data_active,
        mock_task_def_with_wildcard,
        mock_task_def_custom_execution_role,
    ):
        """Test IAM analysis with multiple task definitions."""
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "task_definitions": [
                    mock_task_def_with_wildcard,
                    mock_task_def_custom_execution_role,
                ],
            }
        )

        # Verify multiple recommendations
        iam_recs = [r for r in result["recommendations"] if r["category"] == "IAM"]
        assert len(iam_recs) >= 2


# Task Definition Collection Tests
class TestTaskDefinitionCollection:
    """Tests for task definition data collection."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_services")
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_task_definitions")
    async def test_collect_task_definitions_success(self, mock_find_task_defs, mock_find_services):
        """Test successful task definition collection."""
        # Mock find_services response
        mock_find_services.return_value = ["service1", "service2"]

        # Mock find_task_definitions response with different task defs for each service
        def mock_task_def_side_effect(cluster_name=None, service_name=None):
            if service_name == "service1":
                return [
                    {
                        "taskDefinitionArn": (
                            "arn:aws:ecs:us-east-1:123456789012:task-definition/test1:1"
                        ),
                        "family": "test1",
                        "taskRoleArn": "arn:aws:iam::123456789012:role/taskRole1",
                    }
                ]
            elif service_name == "service2":
                return [
                    {
                        "taskDefinitionArn": (
                            "arn:aws:ecs:us-east-1:123456789012:task-definition/test2:1"
                        ),
                        "family": "test2",
                        "taskRoleArn": "arn:aws:iam::123456789012:role/taskRole2",
                    }
                ]
            return []

        mock_find_task_defs.side_effect = mock_task_def_side_effect

        # Create adapter and collect data
        adapter = DataAdapter()
        result = await adapter.collect_task_definitions("test-cluster", "us-east-1")

        # Verify result
        assert result["status"] == "success"
        assert len(result["task_definitions"]) == 2  # One per service
        assert result["cluster_name"] == "test-cluster"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_services")
    async def test_collect_task_definitions_no_services(self, mock_find_services):
        """Test task definition collection when no services exist."""
        # Mock find_services response with no services
        mock_find_services.return_value = []

        # Create adapter and collect data
        adapter = DataAdapter()
        result = await adapter.collect_task_definitions("test-cluster", "us-east-1")

        # Verify result
        assert result["status"] == "success"
        assert len(result["task_definitions"]) == 0
        assert result["cluster_name"] == "test-cluster"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_services")
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_task_definitions")
    async def test_collect_task_definitions_deduplication(
        self, mock_find_task_defs, mock_find_services
    ):
        """Test that duplicate task definitions are deduplicated."""
        # Mock find_services response
        mock_find_services.return_value = ["service1", "service2"]

        # Mock find_task_definitions response (same task def for both services)
        mock_task_def = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "family": "test",
        }
        mock_find_task_defs.return_value = [mock_task_def]

        # Create adapter and collect data
        adapter = DataAdapter()
        result = await adapter.collect_task_definitions("test-cluster", "us-east-1")

        # Verify deduplication
        assert result["status"] == "success"
        assert len(result["task_definitions"]) == 1  # Deduplicated
        assert result["cluster_name"] == "test-cluster"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_services")
    async def test_collect_task_definitions_error(self, mock_find_services):
        """Test task definition collection error handling."""
        # Mock find_services to raise exception
        mock_find_services.side_effect = Exception("Test error")

        # Create adapter and collect data
        adapter = DataAdapter()
        result = await adapter.collect_task_definitions("test-cluster", "us-east-1")

        # Verify error handling
        assert "error" in result
        assert result["error"] == "Test error"
        assert result["cluster_name"] == "test-cluster"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_task_definitions")
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_services")
    async def test_collect_task_definitions_find_error(
        self, mock_find_services, mock_find_task_defs
    ):
        """Test task definition collection with find_task_definitions error."""
        # Mock find_services to return services
        mock_find_services.return_value = ["service1"]
        # Mock find_task_definitions to raise exception
        mock_find_task_defs.side_effect = Exception("Find task defs error")

        # Create adapter and collect data
        adapter = DataAdapter()
        result = await adapter.collect_task_definitions("test-cluster", "us-east-1")

        # Verify error handling
        assert "error" in result
        assert "Find task defs error" in result["error"]


class TestAnalyzeECSSecurity:
    """Tests for main analyze_ecs_security function."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_services")
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_task_definitions")
    async def test_analyze_with_cluster_names(
        self, mock_find_task_defs, mock_find_services, mock_ecs_api, mock_cluster_data_active
    ):
        """Test analysis with specific cluster names."""
        # Mock ecs_api_operation response
        mock_ecs_api.return_value = {"clusters": [mock_cluster_data_active]}

        # Mock task definition collection
        mock_find_services.return_value = []
        mock_find_task_defs.return_value = []

        # Run analysis
        result = await analyze_ecs_security(cluster_names=["test-cluster"], regions=["us-east-1"])

        # Verify result structure
        assert result["status"] == "success"
        assert result["total_clusters_analyzed"] == 1
        assert "results" in result

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_services")
    @patch("awslabs.ecs_mcp_server.api.security_analysis.find_task_definitions")
    async def test_analyze_discover_clusters(
        self, mock_find_task_defs, mock_find_services, mock_ecs_api, mock_cluster_data_active
    ):
        """Test analysis with cluster discovery."""
        # Mock task definition collection
        mock_find_services.return_value = []
        mock_find_task_defs.return_value = []

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


# Container Instance Collection Tests
class TestContainerInstanceCollection:
    """Tests for container instance data collection."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_container_instances(self, mock_ecs_api):
        """Test container instance collection - success and error cases."""
        adapter = DataAdapter()

        # Success case
        def mock_success(operation, params):
            if operation == "ListContainerInstances":
                return {
                    "containerInstanceArns": [
                        "arn:aws:ecs:us-east-1:123456789012:container-instance/test-cluster/abc123"
                    ]
                }
            return {
                "containerInstances": [
                    {
                        "ec2InstanceId": "i-1234567890abcdef0",
                        "versionInfo": {"agentVersion": "1.70.0"},
                        "agentConnected": True,
                    }
                ]
            }

        mock_ecs_api.side_effect = mock_success
        result = await adapter.collect_container_instances("test-cluster", "us-east-1")
        assert result["status"] == "success"
        assert len(result["container_instances"]) == 1

        # No instances
        mock_ecs_api.side_effect = None
        mock_ecs_api.return_value = {"containerInstanceArns": []}
        result = await adapter.collect_container_instances("test-cluster", "us-east-1")
        assert result["status"] == "success"
        assert len(result["container_instances"]) == 0

        # Error case
        mock_ecs_api.return_value = {"error": "Access denied"}
        result = await adapter.collect_container_instances("test-cluster", "us-east-1")
        assert "error" in result

        # Exception case
        mock_ecs_api.side_effect = Exception("Unexpected error")
        result = await adapter.collect_container_instances("test-cluster", "us-east-1")
        assert "error" in result
        assert "Unexpected error" in result["error"]


# Capacity Provider Collection Tests
class TestCapacityProviderCollection:
    """Tests for capacity provider data collection."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_capacity_providers(self, mock_ecs_api):
        """Test capacity provider collection - success and error cases."""
        adapter = DataAdapter()

        # Success case
        def mock_success(operation, params):
            if operation == "DescribeClusters":
                return {
                    "clusters": [
                        {"clusterName": "test-cluster", "capacityProviders": ["test-cp-1"]}
                    ]
                }
            return {"capacityProviders": [{"name": "test-cp-1"}]}

        mock_ecs_api.side_effect = mock_success
        result = await adapter.collect_capacity_providers("test-cluster", "us-east-1")
        assert result["status"] == "success"
        assert len(result["capacity_providers"]) == 1

        # No providers
        mock_ecs_api.side_effect = None
        mock_ecs_api.return_value = {
            "clusters": [{"clusterName": "test-cluster", "capacityProviders": []}]
        }
        result = await adapter.collect_capacity_providers("test-cluster", "us-east-1")
        assert len(result["capacity_providers"]) == 0

        # Error case
        mock_ecs_api.return_value = {"error": "Access denied"}
        result = await adapter.collect_capacity_providers("test-cluster", "us-east-1")
        assert "error" in result

        # Exception case
        mock_ecs_api.side_effect = Exception("Unexpected error")
        result = await adapter.collect_capacity_providers("test-cluster", "us-east-1")
        assert "error" in result
        assert "Unexpected error" in result["error"]


# Enhanced Cluster Security Tests
class TestEnhancedClusterSecurity:
    """Tests for enhanced cluster security analysis."""

    @pytest.fixture
    def mock_container_instance_outdated_agent(self):
        """Mock container instance with outdated ECS agent."""
        return {
            "ec2InstanceId": "i-1234567890abcdef0",
            "versionInfo": {"agentVersion": "1.60.0"},
            "agentConnected": True,
            "attributes": [{"name": "ecs.instance-type", "value": "t3.medium"}],
        }

    @pytest.fixture
    def mock_container_instance_disconnected(self):
        """Mock container instance with disconnected agent."""
        return {
            "ec2InstanceId": "i-1234567890abcdef1",
            "versionInfo": {"agentVersion": "1.70.0"},
            "agentConnected": False,
            "attributes": [{"name": "ecs.instance-type", "value": "t3.medium"}],
        }

    @pytest.fixture
    def mock_container_instance_legacy_type(self):
        """Mock container instance with legacy instance type."""
        return {
            "ec2InstanceId": "i-1234567890abcdef2",
            "versionInfo": {"agentVersion": "1.70.0"},
            "agentConnected": True,
            "attributes": [{"name": "ecs.instance-type", "value": "m1.large"}],
        }

    @pytest.fixture
    def mock_container_instance_invalid_version(self):
        """Mock container instance with invalid version format."""
        return {
            "ec2InstanceId": "i-1234567890abcdef3",
            "versionInfo": {"agentVersion": "invalid-version"},
            "agentConnected": True,
            "attributes": [{"name": "ecs.instance-type", "value": "t3.medium"}],
        }

    def test_analyze_container_instance_security(
        self,
        mock_cluster_data_active,
        mock_container_instance_outdated_agent,
        mock_container_instance_disconnected,
        mock_container_instance_legacy_type,
        mock_container_instance_invalid_version,
    ):
        """Test container instance security analysis - all cases."""
        analyzer = SecurityAnalyzer()

        # Test outdated agent
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "container_instances": [mock_container_instance_outdated_agent],
            }
        )
        assert any(
            r["title"] == "Critical ECS Agent Security Update Required"
            for r in result["recommendations"]
        )

        # Test disconnected agent
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "container_instances": [mock_container_instance_disconnected],
            }
        )
        assert any(
            r["title"] == "ECS Agent Disconnected - Security Risk"
            for r in result["recommendations"]
        )

        # Test legacy instance type
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "container_instances": [mock_container_instance_legacy_type],
            }
        )
        assert any(
            r["title"] == "Legacy Instance Type Security Risk" for r in result["recommendations"]
        )

        # Test invalid version
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "container_instances": [mock_container_instance_invalid_version],
            }
        )
        assert any(r["title"] == "Verify ECS Agent Version" for r in result["recommendations"])

        # Test multiple instances
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "container_instances": [
                    mock_container_instance_outdated_agent,
                    mock_container_instance_disconnected,
                ],
            }
        )
        security_recs = [r for r in result["recommendations"] if r["category"] == "Security"]
        assert len(security_recs) >= 2


# Capacity Provider Security Tests
class TestCapacityProviderSecurity:
    """Tests for capacity provider security analysis."""

    @pytest.fixture
    def mock_capacity_provider_no_protection(self):
        """Mock capacity provider without termination protection."""
        return {
            "name": "test-cp-no-protection",
            "autoScalingGroupProvider": {
                "managedScaling": {"status": "ENABLED"},
                "managedTerminationProtection": "DISABLED",
            },
        }

    @pytest.fixture
    def mock_capacity_provider_with_protection(self):
        """Mock capacity provider with termination protection."""
        return {
            "name": "test-cp-with-protection",
            "autoScalingGroupProvider": {
                "managedScaling": {"status": "ENABLED"},
                "managedTerminationProtection": "ENABLED",
            },
        }

    @pytest.fixture
    def mock_capacity_provider_no_managed_scaling(self):
        """Mock capacity provider without managed scaling."""
        return {
            "name": "test-cp-no-scaling",
            "autoScalingGroupProvider": {
                "managedScaling": {"status": "DISABLED"},
                "managedTerminationProtection": "DISABLED",
            },
        }

    def test_analyze_capacity_provider_security(
        self,
        mock_cluster_data_active,
        mock_capacity_provider_no_protection,
        mock_capacity_provider_with_protection,
        mock_capacity_provider_no_managed_scaling,
    ):
        """Test capacity provider security analysis - all cases."""
        analyzer = SecurityAnalyzer()

        # Test missing termination protection
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "capacity_providers": [mock_capacity_provider_no_protection],
            }
        )
        protection_recs = [
            r
            for r in result["recommendations"]
            if r["title"] == "Enable Managed Termination Protection"
        ]
        assert len(protection_recs) == 1

        # Test with termination protection (no recommendation)
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "capacity_providers": [mock_capacity_provider_with_protection],
            }
        )
        protection_recs = [
            r
            for r in result["recommendations"]
            if r["title"] == "Enable Managed Termination Protection"
        ]
        assert len(protection_recs) == 0

        # Test no managed scaling (no recommendation)
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "capacity_providers": [mock_capacity_provider_no_managed_scaling],
            }
        )
        protection_recs = [
            r
            for r in result["recommendations"]
            if r["title"] == "Enable Managed Termination Protection"
        ]
        assert len(protection_recs) == 0

        # Test multiple providers
        result = analyzer.analyze(
            {
                "cluster": mock_cluster_data_active,
                "capacity_providers": [
                    mock_capacity_provider_no_protection,
                    mock_capacity_provider_with_protection,
                ],
            }
        )
        protection_recs = [
            r
            for r in result["recommendations"]
            if r["title"] == "Enable Managed Termination Protection"
        ]
        assert len(protection_recs) == 1
