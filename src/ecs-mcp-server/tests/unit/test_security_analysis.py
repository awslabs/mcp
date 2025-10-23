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
    "cluster_data,expected_rec_count,expected_high,expected_medium",
    [
        (
            {
                "clusterName": "test",
                "status": "ACTIVE",
                "settings": [],
                "configuration": {"executeCommandConfiguration": {"logging": "NONE"}},
            },
            3,
            1,
            2,
        ),  # No insights, no logging, no log group
        (
            {
                "clusterName": "test",
                "status": "INACTIVE",
                "settings": [],
                "configuration": {"executeCommandConfiguration": {"logging": "DEFAULT"}},
            },
            4,
            1,
            3,
        ),  # Inactive + no insights + default logging + no log group
    ],
)
def test_security_analyzer_recommendations(
    cluster_data, expected_rec_count, expected_high, expected_medium
):
    """Test SecurityAnalyzer generates correct recommendations."""
    analyzer = SecurityAnalyzer("test", "us-east-1")
    result = analyzer.analyze({"cluster": cluster_data})

    assert result["status"] == "success"
    assert len(result["recommendations"]) == expected_rec_count
    assert result["summary"]["by_severity"]["High"] == expected_high
    assert result["summary"]["by_severity"]["Medium"] == expected_medium


def test_security_analyzer_secure_cluster(secure_cluster):
    """Test that secure cluster generates no recommendations."""
    analyzer = SecurityAnalyzer("secure", "us-east-1")
    result = analyzer.analyze({"cluster": secure_cluster})

    assert result["status"] == "success"
    assert len(result["recommendations"]) == 0
    assert result["summary"]["total_issues"] == 0


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
