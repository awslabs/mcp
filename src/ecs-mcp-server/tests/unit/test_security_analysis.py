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

"""Unit tests for ECS security analysis functionality."""

from unittest.mock import patch

import pytest

from awslabs.ecs_mcp_server.api.security_analysis import (
    DataAdapter,
    SecurityAnalyzer,
    _discover_clusters,
    analyze_ecs_security,
)

# ----------------------------------------------------------------------------
# Test Fixtures
# ----------------------------------------------------------------------------


@pytest.fixture
def secure_cluster():
    """Cluster with all security features enabled."""
    return {
        "clusterName": "secure-cluster",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {
            "executeCommandConfiguration": {
                "logging": "OVERRIDE",
                "logConfiguration": {
                    "cloudWatchLogGroupName": "/aws/ecs/secure-cluster/exec",
                    "cloudWatchEncryptionEnabled": True,
                },
            }
        },
    }


@pytest.fixture
def insecure_cluster():
    """Cluster with multiple security issues."""
    return {
        "clusterName": "insecure-cluster",
        "status": "ACTIVE",
        "settings": [],
        "configuration": {"executeCommandConfiguration": {"logging": "NONE"}},
    }


# ----------------------------------------------------------------------------
# DataAdapter Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_data_adapter_success(mock_api):
    """Test successful cluster data collection."""
    mock_api.return_value = {
        "clusters": [{"clusterName": "test", "status": "ACTIVE", "settings": []}]
    }

    adapter = DataAdapter("us-east-1")
    result = await adapter.collect_cluster_data("test")

    assert result["status"] == "success"
    assert result["cluster"]["clusterName"] == "test"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
@pytest.mark.parametrize(
    "api_response,expected_error",
    [
        ({"clusters": []}, "not found"),
        ({"error": "AccessDenied"}, "AccessDenied"),
    ],
)
async def test_data_adapter_errors(mock_api, api_response, expected_error):
    """Test DataAdapter error handling."""
    mock_api.return_value = api_response

    adapter = DataAdapter("us-east-1")
    result = await adapter.collect_cluster_data("test")

    assert "error" in result
    assert expected_error in result["error"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_data_adapter_exception(mock_api):
    """Test DataAdapter exception handling."""
    mock_api.side_effect = Exception("Network error")

    adapter = DataAdapter("us-east-1")
    result = await adapter.collect_cluster_data("test")

    assert "error" in result


# ----------------------------------------------------------------------------
# SecurityAnalyzer Tests
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cluster_data,expected_rec_count,expected_high,expected_medium,expected_low",
    [
        (
            {
                "clusterName": "test",
                "status": "ACTIVE",
                "settings": [],
                "configuration": {"executeCommandConfiguration": {"logging": "NONE"}},
            },
            5,
            1,
            3,
            1,
        ),  # No insights, no logging, no log group, IAM exec check, IAM general review
        (
            {
                "clusterName": "test",
                "status": "INACTIVE",
                "settings": [],
                "configuration": {"executeCommandConfiguration": {"logging": "DEFAULT"}},
            },
            6,
            1,
            4,
            1,
        ),  # Inactive + no insights + default logging + no log group + IAM checks
    ],
)
def test_security_analyzer_recommendations(
    cluster_data, expected_rec_count, expected_high, expected_medium, expected_low
):
    """Test SecurityAnalyzer generates correct recommendations."""
    analyzer = SecurityAnalyzer("test", "us-east-1")
    result = analyzer.analyze({"cluster": cluster_data})

    assert result["status"] == "success"
    assert len(result["recommendations"]) == expected_rec_count
    assert result["summary"]["by_severity"]["High"] == expected_high
    assert result["summary"]["by_severity"]["Medium"] == expected_medium
    assert result["summary"]["by_severity"]["Low"] == expected_low


def test_security_analyzer_secure_cluster(secure_cluster):
    """Test that secure cluster generates only IAM recommendations."""
    analyzer = SecurityAnalyzer("secure", "us-east-1")
    result = analyzer.analyze({"cluster": secure_cluster})

    assert result["status"] == "success"
    # Secure cluster should only have IAM recommendations (exec check + general review)
    assert len(result["recommendations"]) == 2
    assert result["summary"]["total_issues"] == 2
    # All recommendations should be IAM-related
    assert all(r["category"] == "IAM" for r in result["recommendations"])
    # Should have 1 Medium (exec check) and 1 Low (general review)
    assert result["summary"]["by_severity"]["Medium"] == 1
    assert result["summary"]["by_severity"]["Low"] == 1


def test_security_analyzer_error_handling():
    """Test SecurityAnalyzer handles error data."""
    analyzer = SecurityAnalyzer("test", "us-east-1")
    result = analyzer.analyze({"error": "Cluster not found", "cluster_name": "test"})

    assert result["status"] == "error"
    assert "error" in result
    assert len(result["recommendations"]) == 0


@pytest.mark.parametrize(
    "settings,expected_rec",
    [
        ([], True),  # No Container Insights
        ([{"name": "containerInsights", "value": "disabled"}], True),
        ([{"name": "containerInsights", "value": "enabled"}], False),
    ],
)
def test_container_insights_check(settings, expected_rec):
    """Test Container Insights detection."""
    cluster = {
        "clusterName": "test",
        "status": "ACTIVE",
        "settings": settings,
        "configuration": {"executeCommandConfiguration": {"logging": "OVERRIDE"}},
    }

    analyzer = SecurityAnalyzer("test", "us-east-1")
    result = analyzer.analyze({"cluster": cluster})

    insights_recs = [r for r in result["recommendations"] if "Container Insights" in r["title"]]
    assert (len(insights_recs) > 0) == expected_rec


@pytest.mark.parametrize(
    "logging_config,expected_severity",
    [
        ("NONE", "High"),
        ("DEFAULT", "Medium"),
        ("OVERRIDE", None),
    ],
)
def test_exec_logging_check(logging_config, expected_severity):
    """Test execute command logging detection."""
    cluster = {
        "clusterName": "test",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {"executeCommandConfiguration": {"logging": logging_config}},
    }

    analyzer = SecurityAnalyzer("test", "us-east-1")
    result = analyzer.analyze({"cluster": cluster})

    exec_recs = [r for r in result["recommendations"] if "Execute Command Logging" in r["title"]]

    if expected_severity:
        assert len(exec_recs) > 0
        assert exec_recs[0]["severity"] == expected_severity
    else:
        assert len(exec_recs) == 0


def test_cloudwatch_encryption_check():
    """Test CloudWatch encryption detection."""
    cluster = {
        "clusterName": "test",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {
            "executeCommandConfiguration": {
                "logging": "OVERRIDE",
                "logConfiguration": {
                    "cloudWatchLogGroupName": "/aws/ecs/test/exec",
                    "cloudWatchEncryptionEnabled": False,
                },
            }
        },
    }

    analyzer = SecurityAnalyzer("test", "us-east-1")
    result = analyzer.analyze({"cluster": cluster})

    enc_recs = [r for r in result["recommendations"] if "Encryption" in r["title"]]
    assert len(enc_recs) == 1
    assert enc_recs[0]["severity"] == "Medium"


def test_recommendation_structure(insecure_cluster):
    """Test all recommendations have required fields."""
    analyzer = SecurityAnalyzer("test", "us-east-1")
    result = analyzer.analyze({"cluster": insecure_cluster})

    required_fields = [
        "title",
        "severity",
        "category",
        "resource",
        "issue",
        "recommendation",
        "remediation_steps",
        "documentation_links",
    ]

    for rec in result["recommendations"]:
        for field in required_fields:
            assert field in rec
        assert isinstance(rec["remediation_steps"], list)
        assert len(rec["remediation_steps"]) > 0


# ----------------------------------------------------------------------------
# Integration Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_analyze_ecs_security_success(mock_api, insecure_cluster):
    """Test main analyze_ecs_security function."""
    mock_api.return_value = {"clusters": [insecure_cluster]}

    result = await analyze_ecs_security(cluster_names=["test"], regions=["us-east-1"])

    assert result["status"] == "success"
    assert result["total_clusters_analyzed"] == 1
    assert result["total_recommendations"] > 0


@pytest.mark.anyio
async def test_analyze_requires_cluster_names():
    """Test that cluster_names is required."""
    result = await analyze_ecs_security(cluster_names=[], regions=["us-east-1"])

    assert result["status"] == "error"
    assert "cluster_names is required" in result["error"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_analyze_multiple_clusters(mock_api):
    """Test analyzing multiple clusters."""

    def mock_side_effect(operation, params):
        cluster_name = params["clusters"][0]
        return {
            "clusters": [
                {
                    "clusterName": cluster_name,
                    "status": "ACTIVE",
                    "settings": [],
                    "configuration": {"executeCommandConfiguration": {"logging": "NONE"}},
                }
            ]
        }

    mock_api.side_effect = mock_side_effect

    result = await analyze_ecs_security(
        cluster_names=["cluster1", "cluster2"], regions=["us-east-1"]
    )

    assert result["status"] == "success"
    assert result["total_clusters_analyzed"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_analyze_with_errors(mock_api):
    """Test error handling during analysis."""
    mock_api.return_value = {"error": "AccessDenied"}

    result = await analyze_ecs_security(cluster_names=["test"], regions=["us-east-1"])

    assert result["status"] == "success"
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "error"


@pytest.mark.anyio
async def test_analyze_with_exception():
    """Test exception handling."""
    with patch.object(DataAdapter, "collect_cluster_data", side_effect=Exception("Error")):
        result = await analyze_ecs_security(cluster_names=["test"], regions=["us-east-1"])

        assert "errors" in result
        assert len(result["errors"]) > 0


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_discover_clusters(mock_api):
    """Test cluster discovery function."""
    mock_api.return_value = {
        "clusterArns": [
            "arn:aws:ecs:us-east-1:123:cluster/c1",
            "arn:aws:ecs:us-east-1:123:cluster/c2",
        ]
    }

    result = await _discover_clusters("us-east-1")

    assert "clusters" in result
    assert len(result["clusters"]) == 2
    assert result["clusters"][0] == "c1"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
@pytest.mark.parametrize(
    "api_response",
    [
        {"error": "AccessDenied"},
        Exception("Network error"),
    ],
)
async def test_discover_clusters_errors(mock_api, api_response):
    """Test cluster discovery error handling."""
    if isinstance(api_response, Exception):
        mock_api.side_effect = api_response
    else:
        mock_api.return_value = api_response

    result = await _discover_clusters("us-east-1")
    assert "error" in result


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_default_region(mock_api, secure_cluster):
    """Test default region is us-east-1."""
    mock_api.return_value = {"clusters": [secure_cluster]}

    result = await analyze_ecs_security(cluster_names=["test"], regions=None)

    assert result["results"][0]["region"] == "us-east-1"


# ----------------------------------------------------------------------------
# IAM Security Tests
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exec_config,capacity_providers,expected_iam_recs",
    [
        # ECS Exec configured - should generate IAM recommendation
        ({"logging": "OVERRIDE"}, [], 2),  # Exec config + general review
        # Capacity providers configured - should generate IAM recommendation
        ({}, ["arn:aws:ecs:us-east-1:123:capacity-provider/cp1"], 2),  # CP + general review
        # Both configured - should generate both IAM recommendations
        (
            {"logging": "OVERRIDE"},
            ["arn:aws:ecs:us-east-1:123:capacity-provider/cp1"],
            3,
        ),  # Exec + CP + general
        # Neither configured - should only generate general review
        ({}, [], 1),  # Only general review
    ],
)
def test_cluster_iam_security_checks(exec_config, capacity_providers, expected_iam_recs):
    """Test cluster IAM security checks for various configurations."""
    cluster = {
        "clusterName": "test-cluster",
        "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {"executeCommandConfiguration": exec_config} if exec_config else {},
        "capacityProviders": capacity_providers,
    }

    analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
    result = analyzer.analyze({"cluster": cluster})

    # Filter IAM-related recommendations
    iam_recs = [r for r in result["recommendations"] if r["category"] == "IAM"]

    assert len(iam_recs) == expected_iam_recs
    assert result["status"] == "success"


def test_iam_service_linked_role_exec_recommendation():
    """Test IAM recommendation for ECS Exec service-linked role."""
    cluster = {
        "clusterName": "exec-cluster",
        "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/exec-cluster",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {
            "executeCommandConfiguration": {
                "logging": "OVERRIDE",
                "logConfiguration": {"cloudWatchLogGroupName": "/aws/ecs/exec-cluster/exec"},
            }
        },
        "capacityProviders": [],
    }

    analyzer = SecurityAnalyzer("exec-cluster", "us-east-1")
    result = analyzer.analyze({"cluster": cluster})

    # Find the ECS Exec service-linked role recommendation
    exec_iam_recs = [
        r for r in result["recommendations"] if r["category"] == "IAM" and "ECS Exec" in r["issue"]
    ]

    assert len(exec_iam_recs) == 1
    rec = exec_iam_recs[0]

    # Verify recommendation structure
    assert rec["severity"] == "Medium"
    assert rec["resource"] == "exec-cluster"
    assert "AWSServiceRoleForECS" in rec["issue"]
    assert "service-linked role" in rec["issue"].lower()

    # Verify remediation steps include IAM commands
    assert any("aws iam get-role" in step for step in rec["remediation_steps"])
    assert any("create-service-linked-role" in step for step in rec["remediation_steps"])

    # Verify documentation links
    assert len(rec["documentation_links"]) > 0
    assert any("service-linked-roles" in link for link in rec["documentation_links"])


def test_iam_service_linked_role_capacity_provider_recommendation():
    """Test IAM recommendation for capacity provider service-linked role."""
    cluster = {
        "clusterName": "cp-cluster",
        "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/cp-cluster",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {},
        "capacityProviders": [
            "arn:aws:ecs:us-east-1:123456789012:capacity-provider/my-cp",
            "arn:aws:ecs:us-east-1:123456789012:capacity-provider/my-cp-2",
        ],
    }

    analyzer = SecurityAnalyzer("cp-cluster", "us-east-1")
    result = analyzer.analyze({"cluster": cluster})

    # Find the capacity provider service-linked role recommendation
    cp_iam_recs = [
        r
        for r in result["recommendations"]
        if r["category"] == "IAM" and "Capacity Providers" in r["title"]
    ]

    assert len(cp_iam_recs) == 1
    rec = cp_iam_recs[0]

    # Verify recommendation structure
    assert rec["severity"] == "Medium"
    assert rec["resource"] == "cp-cluster"
    assert "capacity providers" in rec["issue"].lower()
    assert "AWSServiceRoleForECS" in rec["issue"]

    # Verify remediation steps include Auto Scaling permissions
    remediation_text = " ".join(rec["remediation_steps"])
    assert "autoscaling" in remediation_text.lower()

    # Verify documentation links
    assert len(rec["documentation_links"]) > 0
    assert any("capacity-providers" in link for link in rec["documentation_links"])


def test_iam_general_review_recommendation():
    """Test general IAM review recommendation is always generated."""
    cluster = {
        "clusterName": "minimal-cluster",
        "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/minimal-cluster",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {},
        "capacityProviders": [],
    }

    analyzer = SecurityAnalyzer("minimal-cluster", "us-east-1")
    result = analyzer.analyze({"cluster": cluster})

    # Find the general IAM review recommendation
    review_recs = [
        r for r in result["recommendations"] if r["category"] == "IAM" and "Review" in r["title"]
    ]

    assert len(review_recs) == 1
    rec = review_recs[0]

    # Verify recommendation structure
    assert rec["severity"] == "Low"
    assert rec["resource"] == "minimal-cluster"
    assert "least privilege" in rec["issue"].lower()

    # Verify remediation steps include IAM best practices
    remediation_text = " ".join(rec["remediation_steps"])
    assert "aws iam" in remediation_text.lower()
    assert "list-services" in remediation_text.lower()

    # Verify documentation links include IAM best practices
    assert len(rec["documentation_links"]) > 0
    assert any("best-practices" in link for link in rec["documentation_links"])


def test_iam_recommendations_have_required_fields():
    """Test all IAM recommendations have required fields."""
    cluster = {
        "clusterName": "test",
        "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {"executeCommandConfiguration": {"logging": "OVERRIDE"}},
        "capacityProviders": ["arn:aws:ecs:us-east-1:123:capacity-provider/cp1"],
    }

    analyzer = SecurityAnalyzer("test", "us-east-1")
    result = analyzer.analyze({"cluster": cluster})

    iam_recs = [r for r in result["recommendations"] if r["category"] == "IAM"]

    required_fields = [
        "title",
        "severity",
        "category",
        "resource",
        "issue",
        "recommendation",
        "remediation_steps",
        "documentation_links",
    ]

    for rec in iam_recs:
        for field in required_fields:
            assert field in rec, f"Missing field {field} in IAM recommendation"
        assert isinstance(rec["remediation_steps"], list)
        assert len(rec["remediation_steps"]) > 0
        assert isinstance(rec["documentation_links"], list)
        assert len(rec["documentation_links"]) > 0


def test_iam_summary_includes_iam_category():
    """Test that summary includes IAM category when IAM recommendations exist."""
    cluster = {
        "clusterName": "test",
        "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test",
        "status": "ACTIVE",
        "settings": [{"name": "containerInsights", "value": "enabled"}],
        "configuration": {"executeCommandConfiguration": {"logging": "OVERRIDE"}},
        "capacityProviders": [],
    }

    analyzer = SecurityAnalyzer("test", "us-east-1")
    result = analyzer.analyze({"cluster": cluster})

    # Verify IAM category is in summary
    assert "IAM" in result["summary"]["by_category"]
    assert result["summary"]["by_category"]["IAM"] >= 1


# ----------------------------------------------------------------------------
# Enhanced Cluster Security Tests
# ----------------------------------------------------------------------------


class TestEnhancedClusterSecurity:
    """Tests for enhanced cluster security analysis including container instances."""

    @pytest.fixture
    def container_instance_healthy(self):
        """Healthy container instance with current agent."""
        return {
            "containerInstanceArn": "arn:aws:ecs:us-east-1:123:container-instance/abc123",
            "ec2InstanceId": "i-1234567890abcdef0",
            "versionInfo": {"agentVersion": "1.75.0"},
            "agentConnected": True,
            "status": "ACTIVE",
            "attributes": [
                {"name": "ecs.instance-type", "value": "t3.medium"},
            ],
        }

    @pytest.fixture
    def container_instance_outdated_agent(self):
        """Container instance with outdated agent."""
        return {
            "containerInstanceArn": "arn:aws:ecs:us-east-1:123:container-instance/def456",
            "ec2InstanceId": "i-0987654321fedcba0",
            "versionInfo": {"agentVersion": "1.65.0"},
            "agentConnected": True,
            "status": "ACTIVE",
            "attributes": [
                {"name": "ecs.instance-type", "value": "t3.large"},
            ],
        }

    @pytest.fixture
    def container_instance_disconnected(self):
        """Container instance with connectivity issues."""
        return {
            "containerInstanceArn": "arn:aws:ecs:us-east-1:123:container-instance/ghi789",
            "ec2InstanceId": "i-abcdef1234567890",
            "versionInfo": {"agentVersion": "1.75.0"},
            "agentConnected": False,
            "status": "DRAINING",
            "attributes": [
                {"name": "ecs.instance-type", "value": "m5.xlarge"},
            ],
        }

    @pytest.fixture
    def container_instance_legacy_type(self):
        """Container instance with legacy instance type."""
        return {
            "containerInstanceArn": "arn:aws:ecs:us-east-1:123:container-instance/jkl012",
            "ec2InstanceId": "i-legacy123456789",
            "versionInfo": {"agentVersion": "1.75.0"},
            "agentConnected": True,
            "status": "ACTIVE",
            "attributes": [
                {"name": "ecs.instance-type", "value": "t2.micro"},
            ],
        }

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_container_instances_success(self, mock_api):
        """Test successful container instance collection."""
        mock_api.side_effect = [
            {"containerInstanceArns": ["arn:aws:ecs:us-east-1:123:container-instance/abc"]},
            {
                "containerInstances": [
                    {"containerInstanceArn": "arn:aws:ecs:us-east-1:123:container-instance/abc"}
                ]
            },
        ]

        adapter = DataAdapter("us-east-1")
        result = await adapter.collect_container_instances("test-cluster")

        assert result["status"] == "success"
        assert len(result["container_instances"]) == 1

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_container_instances_empty(self, mock_api):
        """Test collection when no container instances exist."""
        mock_api.return_value = {"containerInstanceArns": []}

        adapter = DataAdapter("us-east-1")
        result = await adapter.collect_container_instances("test-cluster")

        assert result["status"] == "success"
        assert result["container_instances"] == []

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_container_instances_error(self, mock_api):
        """Test error handling in container instance collection."""
        mock_api.return_value = {"error": "AccessDenied"}

        adapter = DataAdapter("us-east-1")
        result = await adapter.collect_container_instances("test-cluster")

        assert "error" in result

    def test_outdated_agent_detection(self, container_instance_outdated_agent):
        """Test detection of outdated ECS agent."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "container_instances": [container_instance_outdated_agent],
            }
        )

        outdated_recs = [r for r in result["recommendations"] if "Outdated ECS Agent" in r["title"]]
        assert len(outdated_recs) == 1
        assert outdated_recs[0]["severity"] == "High"
        assert "1.65.0" in outdated_recs[0]["issue"]

    def test_agent_connectivity_issue(self, container_instance_disconnected):
        """Test detection of agent connectivity issues."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "container_instances": [container_instance_disconnected],
            }
        )

        connectivity_recs = [
            r for r in result["recommendations"] if "Connectivity Issue" in r["title"]
        ]
        assert len(connectivity_recs) == 1
        assert connectivity_recs[0]["severity"] == "High"
        assert "agent connected" in connectivity_recs[0]["issue"].lower()

    def test_legacy_instance_type_detection(self, container_instance_legacy_type):
        """Test detection of legacy instance types."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "container_instances": [container_instance_legacy_type],
            }
        )

        legacy_recs = [r for r in result["recommendations"] if "Legacy Instance Type" in r["title"]]
        assert len(legacy_recs) == 1
        assert legacy_recs[0]["severity"] == "Medium"
        assert "t2.micro" in legacy_recs[0]["issue"]

    def test_healthy_container_instance_no_recommendations(self, container_instance_healthy):
        """Test that healthy container instances generate no recommendations."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {
                    "clusterName": "test-cluster",
                    "status": "ACTIVE",
                    "settings": [{"name": "containerInsights", "value": "enabled"}],
                },
                "container_instances": [container_instance_healthy],
            }
        )

        # Should have no container instance related recommendations
        instance_recs = [
            r for r in result["recommendations"] if r["resource_type"] == "ContainerInstance"
        ]
        assert len(instance_recs) == 0

    def test_multiple_container_instances(
        self,
        container_instance_healthy,
        container_instance_outdated_agent,
        container_instance_legacy_type,
    ):
        """Test analysis of multiple container instances."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "container_instances": [
                    container_instance_healthy,
                    container_instance_outdated_agent,
                    container_instance_legacy_type,
                ],
            }
        )

        instance_recs = [
            r for r in result["recommendations"] if r["resource_type"] == "ContainerInstance"
        ]
        # Should have 2 recommendations: outdated agent + legacy type
        assert len(instance_recs) == 2

    @pytest.mark.parametrize(
        "current_version,minimum_version,expected_outdated",
        [
            ("1.75.0", "1.70.0", False),
            ("1.70.0", "1.70.0", False),
            ("1.69.9", "1.70.0", True),
            ("1.65.0", "1.70.0", True),
            ("2.0.0", "1.70.0", False),
            ("1.70.1", "1.70.0", False),
        ],
    )
    def test_agent_version_comparison(self, current_version, minimum_version, expected_outdated):
        """Test agent version comparison logic."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer._is_agent_version_outdated(current_version, minimum_version)
        assert result == expected_outdated

    def test_agent_version_comparison_invalid(self):
        """Test agent version comparison with invalid versions."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        # Invalid versions should be considered outdated for safety
        assert analyzer._is_agent_version_outdated("invalid", "1.70.0") is True
        assert analyzer._is_agent_version_outdated("1.70.0", "invalid") is True

    def test_no_container_instances(self):
        """Test analysis when cluster has no container instances (Fargate-only)."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "container_instances": [],
            }
        )

        # Should not crash and should have no container instance recommendations
        instance_recs = [
            r for r in result["recommendations"] if r["resource_type"] == "ContainerInstance"
        ]
        assert len(instance_recs) == 0

    @pytest.mark.parametrize(
        "instance_family,expected_legacy",
        [
            ("t3", False),
            ("t2", True),
            ("m5", False),
            ("m4", True),
            ("c5", False),
            ("c4", True),
            ("r5", False),
            ("r4", True),
        ],
    )
    def test_legacy_instance_family_detection(self, instance_family, expected_legacy):
        """Test detection of various legacy instance families."""
        instance = {
            "containerInstanceArn": "arn:aws:ecs:us-east-1:123:container-instance/test",
            "ec2InstanceId": "i-test",
            "versionInfo": {"agentVersion": "1.75.0"},
            "agentConnected": True,
            "status": "ACTIVE",
            "attributes": [
                {"name": "ecs.instance-type", "value": f"{instance_family}.large"},
            ],
        }

        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "container_instances": [instance],
            }
        )

        legacy_recs = [r for r in result["recommendations"] if "Legacy Instance Type" in r["title"]]
        assert (len(legacy_recs) > 0) == expected_legacy


# ----------------------------------------------------------------------------
# Capacity Provider Tests
# ----------------------------------------------------------------------------


class TestCapacityProviders:
    """Tests for capacity provider security analysis."""

    @pytest.fixture
    def capacity_provider_secure(self):
        """Secure capacity provider configuration."""
        return {
            "name": "secure-provider",
            "capacityProviderArn": "arn:aws:ecs:us-east-1:123:capacity-provider/secure-provider",
            "autoScalingGroupProvider": {
                "autoScalingGroupArn": "arn:aws:autoscaling:us-east-1:123:autoScalingGroup:abc",
                "managedTerminationProtection": "ENABLED",
                "managedScaling": {
                    "status": "ENABLED",
                    "targetCapacity": 100,
                    "minimumScalingStepSize": 1,
                    "maximumScalingStepSize": 10000,
                },
            },
        }

    @pytest.fixture
    def capacity_provider_no_termination_protection(self):
        """Capacity provider without termination protection."""
        return {
            "name": "unprotected-provider",
            "capacityProviderArn": (
                "arn:aws:ecs:us-east-1:123:capacity-provider/unprotected-provider"
            ),
            "autoScalingGroupProvider": {
                "autoScalingGroupArn": "arn:aws:autoscaling:us-east-1:123:autoScalingGroup:def",
                "managedTerminationProtection": "DISABLED",
                "managedScaling": {
                    "status": "ENABLED",
                    "targetCapacity": 100,
                },
            },
        }

    @pytest.fixture
    def capacity_provider_no_managed_scaling(self):
        """Capacity provider without managed scaling."""
        return {
            "name": "no-scaling-provider",
            "capacityProviderArn": (
                "arn:aws:ecs:us-east-1:123:capacity-provider/no-scaling-provider"
            ),
            "autoScalingGroupProvider": {
                "autoScalingGroupArn": "arn:aws:autoscaling:us-east-1:123:autoScalingGroup:ghi",
                "managedTerminationProtection": "ENABLED",
                "managedScaling": {
                    "status": "DISABLED",
                },
            },
        }

    @pytest.fixture
    def capacity_provider_suboptimal_target(self):
        """Capacity provider with suboptimal target capacity."""
        return {
            "name": "suboptimal-provider",
            "capacityProviderArn": (
                "arn:aws:ecs:us-east-1:123:capacity-provider/suboptimal-provider"
            ),
            "autoScalingGroupProvider": {
                "autoScalingGroupArn": "arn:aws:autoscaling:us-east-1:123:autoScalingGroup:jkl",
                "managedTerminationProtection": "ENABLED",
                "managedScaling": {
                    "status": "ENABLED",
                    "targetCapacity": 50,
                },
            },
        }

    @pytest.fixture
    def capacity_provider_fargate(self):
        """Fargate capacity provider (no auto scaling group)."""
        return {
            "name": "FARGATE",
            "capacityProviderArn": "arn:aws:ecs:us-east-1:123:capacity-provider/FARGATE",
        }

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_capacity_providers_success(self, mock_api):
        """Test successful capacity provider collection."""
        mock_api.side_effect = [
            {
                "clusters": [
                    {
                        "clusterName": "test",
                        "capacityProviders": ["arn:aws:ecs:us-east-1:123:capacity-provider/test"],
                    }
                ]
            },
            {
                "capacityProviders": [
                    {
                        "name": "test",
                        "capacityProviderArn": "arn:aws:ecs:us-east-1:123:capacity-provider/test",
                    }
                ]
            },
        ]

        adapter = DataAdapter("us-east-1")
        result = await adapter.collect_capacity_providers("test-cluster")

        assert result["status"] == "success"
        assert len(result["capacity_providers"]) == 1

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_capacity_providers_empty(self, mock_api):
        """Test collection when no capacity providers exist."""
        mock_api.return_value = {"clusters": [{"clusterName": "test", "capacityProviders": []}]}

        adapter = DataAdapter("us-east-1")
        result = await adapter.collect_capacity_providers("test-cluster")

        assert result["status"] == "success"
        assert result["capacity_providers"] == []

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
    async def test_collect_capacity_providers_error(self, mock_api):
        """Test error handling in capacity provider collection."""
        mock_api.return_value = {"error": "AccessDenied"}

        adapter = DataAdapter("us-east-1")
        result = await adapter.collect_capacity_providers("test-cluster")

        assert "error" in result

    def test_termination_protection_disabled(self, capacity_provider_no_termination_protection):
        """Test detection of disabled termination protection."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "capacity_providers": [capacity_provider_no_termination_protection],
            }
        )

        protection_recs = [
            r for r in result["recommendations"] if "Termination Protection" in r["title"]
        ]
        assert len(protection_recs) == 1
        assert protection_recs[0]["severity"] == "Medium"

    def test_managed_scaling_disabled(self, capacity_provider_no_managed_scaling):
        """Test detection of disabled managed scaling."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "capacity_providers": [capacity_provider_no_managed_scaling],
            }
        )

        scaling_recs = [r for r in result["recommendations"] if "Managed Scaling" in r["title"]]
        assert len(scaling_recs) == 1
        assert scaling_recs[0]["severity"] == "Low"

    def test_suboptimal_target_capacity(self, capacity_provider_suboptimal_target):
        """Test detection of suboptimal target capacity."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "capacity_providers": [capacity_provider_suboptimal_target],
            }
        )

        target_recs = [r for r in result["recommendations"] if "Target Capacity" in r["title"]]
        assert len(target_recs) == 1
        assert target_recs[0]["severity"] == "Medium"
        assert "50%" in target_recs[0]["issue"]

    def test_secure_capacity_provider_no_recommendations(self, capacity_provider_secure):
        """Test that secure capacity provider generates no recommendations."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "capacity_providers": [capacity_provider_secure],
            }
        )

        cp_recs = [r for r in result["recommendations"] if r["resource_type"] == "CapacityProvider"]
        assert len(cp_recs) == 0

    def test_fargate_capacity_provider_ignored(self, capacity_provider_fargate):
        """Test that Fargate capacity providers are ignored."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "capacity_providers": [capacity_provider_fargate],
            }
        )

        cp_recs = [r for r in result["recommendations"] if r["resource_type"] == "CapacityProvider"]
        assert len(cp_recs) == 0

    def test_multiple_capacity_providers(
        self,
        capacity_provider_secure,
        capacity_provider_no_termination_protection,
        capacity_provider_suboptimal_target,
    ):
        """Test analysis of multiple capacity providers."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "capacity_providers": [
                    capacity_provider_secure,
                    capacity_provider_no_termination_protection,
                    capacity_provider_suboptimal_target,
                ],
            }
        )

        cp_recs = [r for r in result["recommendations"] if r["resource_type"] == "CapacityProvider"]
        # Should have 2 recommendations: no termination protection + suboptimal target
        assert len(cp_recs) == 2

    def test_no_capacity_providers(self):
        """Test analysis when cluster has no capacity providers."""
        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "capacity_providers": [],
            }
        )

        cp_recs = [r for r in result["recommendations"] if r["resource_type"] == "CapacityProvider"]
        assert len(cp_recs) == 0

    @pytest.mark.parametrize(
        "target_capacity,expected_recommendation",
        [
            (100, False),  # Optimal
            (90, False),  # Within range
            (80, False),  # Minimum acceptable
            (79, True),  # Below range
            (50, True),  # Well below range
            (101, True),  # Above range
        ],
    )
    def test_target_capacity_ranges(self, target_capacity, expected_recommendation):
        """Test various target capacity values."""
        provider = {
            "name": "test-provider",
            "capacityProviderArn": "arn:aws:ecs:us-east-1:123:capacity-provider/test",
            "autoScalingGroupProvider": {
                "autoScalingGroupArn": "arn:aws:autoscaling:us-east-1:123:autoScalingGroup:test",
                "managedTerminationProtection": "ENABLED",
                "managedScaling": {
                    "status": "ENABLED",
                    "targetCapacity": target_capacity,
                },
            },
        }

        analyzer = SecurityAnalyzer("test-cluster", "us-east-1")
        result = analyzer.analyze(
            {
                "cluster": {"clusterName": "test-cluster", "status": "ACTIVE", "settings": []},
                "capacity_providers": [provider],
            }
        )

        target_recs = [r for r in result["recommendations"] if "Target Capacity" in r["title"]]
        assert (len(target_recs) > 0) == expected_recommendation


# ----------------------------------------------------------------------------
# Additional Coverage Tests for Error Paths
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_collect_container_instances_describe_error(mock_api):
    """Test error handling when describe operation fails."""
    mock_api.side_effect = [
        {"containerInstanceArns": ["arn:aws:ecs:us-east-1:123:container-instance/abc"]},
        {"error": "DescribeError"},
    ]

    adapter = DataAdapter("us-east-1")
    result = await adapter.collect_container_instances("test-cluster")

    assert "error" in result
    assert result["error"] == "DescribeError"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.security_analysis.ecs_api_operation")
async def test_collect_capacity_providers_describe_error(mock_api):
    """Test error handling when describe capacity providers fails."""
    mock_api.side_effect = [
        {"clusters": [{"clusterName": "test", "capacityProviders": ["arn:test"]}]},
        {"error": "DescribeError"},
    ]

    adapter = DataAdapter("us-east-1")
    result = await adapter.collect_capacity_providers("test-cluster")

    assert "error" in result
    assert result["error"] == "DescribeError"


@pytest.mark.anyio
async def test_analyze_region_exception():
    """Test exception handling at region level."""
    with patch.object(DataAdapter, "collect_cluster_data", side_effect=Exception("Region error")):
        result = await analyze_ecs_security(cluster_names=["test"], regions=["us-east-1"])

        assert "errors" in result
        assert len(result["errors"]) > 0
        assert any("Region error" in str(e.get("error", "")) for e in result["errors"])
