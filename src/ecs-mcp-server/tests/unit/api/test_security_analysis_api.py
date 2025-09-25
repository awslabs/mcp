"""
Unit tests for the Security Analysis API module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.security_analysis import ecs_security_analysis_tool


class TestSecurityAnalysisAPI:
    """Tests for the Security Analysis API functions."""

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.get_aws_client")
    async def test_ecs_security_analysis_tool_list_clusters(self, mock_get_aws_client):
        """Test ecs_security_analysis_tool with list_clusters action."""
        # Mock AWS client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1", "cluster-2"]}
        mock_ecs.describe_clusters.return_value = {
            "clusters": [
                {"clusterName": "cluster-1", "status": "ACTIVE"},
                {"clusterName": "cluster-2", "status": "ACTIVE"}
            ]
        }
        mock_get_aws_client.return_value = mock_ecs

        # Call ecs_security_analysis_tool with list_clusters action
        result = await ecs_security_analysis_tool("list_clusters", {"region": "us-east-1"})

        # Verify get_aws_client was called
        mock_get_aws_client.assert_called_once_with('ecs')

        # Verify ECS methods were called
        mock_ecs.list_clusters.assert_called_once()
        mock_ecs.describe_clusters.assert_called_once()

        # Verify the result
        assert result["status"] == "success"
        assert len(result["clusters"]) == 2
        assert result["total_clusters"] == 2

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ECSSecurityAnalyzer")
    async def test_ecs_security_analysis_tool_analyze_cluster_security(self, mock_analyzer_class):
        """Test ecs_security_analysis_tool with analyze_cluster_security action."""
        # Mock ECSSecurityAnalyzer with comprehensive security analysis response
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_cluster = AsyncMock(return_value={
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "status": "success",
            "assessment": "Security analysis complete for ECS cluster 'test-cluster'. Found 3 security areas requiring attention.",
            "recommendations": [
                {
                    "title": "Enable Container Insights for Security Monitoring",
                    "severity": "Medium",
                    "category": "monitoring",
                    "resource": "Cluster: test-cluster",
                    "issue": "Container Insights monitoring is disabled",
                    "recommendation": "Enable Container Insights for comprehensive monitoring",
                    "implementation": {
                        "aws_cli": "aws ecs modify-cluster --cluster test-cluster --settings name=containerInsights,value=enabled",
                        "description": "Enable Container Insights to improve security visibility"
                    }
                },
                {
                    "title": "Configure Security Groups",
                    "severity": "High",
                    "category": "network_security",
                    "resource": "Service: test-service",
                    "issue": "No security groups configured for the service",
                    "recommendation": "Configure restrictive security groups"
                }
            ],
            "total_issues": 2,
            "analysis_summary": {
                "total_issues": 2,
                "severity_breakdown": {
                    "High": 1,
                    "Medium": 1,
                    "Low": 0
                },
                "category_breakdown": {
                    "monitoring": 1,
                    "network_security": 1
                }
            },
            "security_domains": {
                "iam_security": {"issues": 0, "status": "compliant"},
                "network_security": {"issues": 1, "status": "non_compliant"},
                "container_security": {"issues": 0, "status": "compliant"},
                "monitoring": {"issues": 1, "status": "non_compliant"}
            }
        })
        mock_analyzer_class.return_value = mock_analyzer

        # Call ecs_security_analysis_tool with analyze_cluster_security action
        result = await ecs_security_analysis_tool(
            "analyze_cluster_security",
            {"cluster_name": "test-cluster", "region": "us-east-1"}
        )

        # Verify analyzer was instantiated and called
        mock_analyzer_class.assert_called_once()
        mock_analyzer.analyze_cluster.assert_called_once_with("test-cluster", "us-east-1")

        # Verify the comprehensive result structure
        assert result["status"] == "success"
        assert result["cluster_name"] == "test-cluster"
        assert result["region"] == "us-east-1"
        assert result["action"] == "analyze_cluster_security"
        assert len(result["priority_recommendations"]) >= 1  # At least high severity recommendations
        assert result["total_issues_found"] == 2
        assert result["security_summary"]["total_recommendations"] == 2
        assert result["security_summary"]["severity_breakdown"]["high"] == 1
        assert result["security_summary"]["severity_breakdown"]["medium"] == 1
        assert "assessment" in result
        assert "next_steps" in result

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ECSSecurityAnalyzer")
    async def test_ecs_security_analysis_tool_generate_security_report(self, mock_analyzer_class):
        """Test ecs_security_analysis_tool with generate_security_report action."""
        # Mock ECSSecurityAnalyzer with comprehensive report data
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_cluster = AsyncMock(return_value={
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "status": "success",
            "assessment": "Security analysis complete for ECS cluster 'test-cluster'.",
            "recommendations": [
                {
                    "title": "Enable KMS Encryption for Execute Command",
                    "severity": "High",
                    "category": "encryption",
                    "resource": "Cluster: test-cluster",
                    "issue": "Execute command sessions are not encrypted with customer-managed KMS keys",
                    "recommendation": "Configure KMS encryption for execute command sessions",
                    "implementation": {
                        "aws_cli": "aws ecs put-cluster --cluster test-cluster --configuration executeCommandConfiguration='{logging=OVERRIDE,kmsKeyId=arn:aws:kms:region:account:key/key-id}'",
                        "description": "Enable KMS encryption for secure command execution"
                    },
                    "compliance_frameworks": ["AWS Well-Architected", "SOC 2"],
                    "security_impact": "High - Protects sensitive data in command sessions"
                }
            ],
            "total_issues": 1,
            "analysis_summary": {
                "total_issues": 1,
                "severity_breakdown": {
                    "High": 1,
                    "Medium": 0,
                    "Low": 0
                },
                "category_breakdown": {"encryption": 1}
            },
            "security_domains": {
                "iam_security": {"issues": 0, "status": "compliant"},
                "network_security": {"issues": 0, "status": "compliant"},
                "container_security": {"issues": 0, "status": "compliant"},
                "encryption": {"issues": 1, "status": "non_compliant"}
            },
            "analysis_timestamp": "2023-01-01T00:00:00Z"
        })
        mock_analyzer_class.return_value = mock_analyzer

        # Call ecs_security_analysis_tool with generate_security_report action
        result = await ecs_security_analysis_tool(
            "generate_security_report",
            {"cluster_name": "test-cluster", "region": "us-east-1", "format": "json"}
        )

        # Verify analyzer was called
        mock_analyzer_class.assert_called_once()
        mock_analyzer.analyze_cluster.assert_called_once_with("test-cluster", "us-east-1")

        # Verify the comprehensive report structure
        assert result["status"] == "success"
        assert result["cluster_name"] == "test-cluster"
        assert result["report_format"] == "json"
        assert result["action"] == "generate_security_report"
        assert "report_data" in result
        assert "filters_applied" in result
        assert "assessment" in result
        assert "assessment" in result

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ECSSecurityAnalyzer")
    async def test_ecs_security_analysis_tool_get_security_recommendations(self, mock_analyzer_class):
        """Test ecs_security_analysis_tool with get_security_recommendations action."""
        # Mock ECSSecurityAnalyzer with diverse recommendations
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_cluster = AsyncMock(return_value={
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "status": "success",
            "assessment": "Security analysis complete for ECS cluster 'test-cluster'.",
            "recommendations": [
                {
                    "title": "Disable Public IP Assignment",
                    "severity": "High",
                    "category": "network_security",
                    "resource": "Service: test-service",
                    "issue": "Service has public IP assignment enabled",
                    "recommendation": "Disable public IP assignment and use NAT Gateway",
                    "implementation": {
                        "aws_cli": "aws ecs update-service --cluster test-cluster --service test-service --network-configuration 'awsvpcConfiguration={assignPublicIp=DISABLED}'",
                        "description": "Remove direct internet exposure"
                    },
                    "security_impact": "High - Reduces attack surface"
                },
                {
                    "title": "Enable Read-Only Root Filesystem",
                    "severity": "Medium",
                    "category": "container_security",
                    "resource": "Container: test-container",
                    "issue": "Container root filesystem is writable, increasing attack surface",
                    "recommendation": "Enable read-only root filesystem and use tmpfs for temporary files",
                    "implementation": {
                        "aws_cli": "Update task definition to set readonlyRootFilesystem: true",
                        "description": "Improve container security by making filesystem immutable"
                    },
                    "security_impact": "Medium - Reduces attack surface"
                },
                {
                    "title": "Consider Using Private Container Registry",
                    "severity": "Low",
                    "category": "container_security",
                    "resource": "Container: test-container",
                    "issue": "Using public registry images may pose supply chain security risks",
                    "recommendation": "Migrate to Amazon ECR for better control and security scanning",
                    "implementation": {
                        "aws_cli": "aws ecr create-repository --repository-name app-name",
                        "description": "Improve supply chain security"
                    },
                    "security_impact": "Low - Improves supply chain security"
                }
            ],
            "total_issues": 3,
            "analysis_summary": {
                "total_issues": 3,
                "severity_breakdown": {
                    "High": 1,
                    "Medium": 1,
                    "Low": 1
                },
                "category_breakdown": {
                    "network_security": 1,
                    "container_security": 2
                }
            }
        })
        mock_analyzer_class.return_value = mock_analyzer

        # Call ecs_security_analysis_tool with get_security_recommendations action
        result = await ecs_security_analysis_tool(
            "get_security_recommendations",
            {"cluster_name": "test-cluster", "severity_filter": "High", "limit": 5}
        )

        # Verify analyzer was called
        mock_analyzer_class.assert_called_once()
        mock_analyzer.analyze_cluster.assert_called_once_with("test-cluster", "us-east-1")

        # Verify the filtered result
        assert result["status"] == "success"
        assert result["cluster_name"] == "test-cluster"
        assert result["action"] == "get_security_recommendations"
        assert len(result["recommendations"]) == 1  # Filtered to High severity only
        assert result["recommendations"][0]["severity"] == "High"
        assert result["recommendations"][0]["title"] == "Disable Public IP Assignment"
        assert result["filter_criteria"]["severity_filter"] == "High"
        assert result["filter_criteria"]["limit"] == 5
        assert result["results_summary"]["filtered_results"] == 1
        assert "guidance" in result

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ECSSecurityAnalyzer")
    async def test_ecs_security_analysis_tool_check_compliance_status(self, mock_analyzer_class):
        """Test ecs_security_analysis_tool with check_compliance_status action."""
        # Mock ECSSecurityAnalyzer with compliance-focused recommendations
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_cluster = AsyncMock(return_value={
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "status": "success",
            "assessment": "Security analysis complete for ECS cluster 'test-cluster'.",
            "recommendations": [
                {
                    "title": "Enable VPC Flow Logs",
                    "severity": "Critical",
                    "category": "network_security",
                    "resource": "VPC: vpc-12345",
                    "issue": "VPC Flow Logs are not enabled for network monitoring",
                    "recommendation": "Enable VPC Flow Logs for security monitoring and compliance",
                    "compliance_frameworks": ["AWS Well-Architected", "SOC 2", "PCI DSS"],
                    "implementation": {
                        "aws_cli": "aws ec2 create-flow-logs --resource-type VPC --resource-ids vpc-12345 --traffic-type ALL",
                        "description": "Enable comprehensive network traffic logging"
                    }
                },
                {
                    "title": "Configure Container Runtime Security",
                    "severity": "High",
                    "category": "container_security",
                    "resource": "Task Definition: test-task-def",
                    "issue": "Container is running as root user",
                    "recommendation": "Configure non-root user for container execution",
                    "compliance_frameworks": ["AWS Well-Architected", "CIS Benchmarks"],
                    "implementation": {
                        "description": "Update task definition to use non-root user"
                    }
                }
            ],
            "total_issues": 2,
            "analysis_summary": {
                "total_issues": 2,
                "severity_breakdown": {
                    "High": 2,
                    "Medium": 0,
                    "Low": 0
                },
                "category_breakdown": {
                    "network_security": 1,
                    "container_security": 1
                }
            },
            "security_domains": {
                "iam_security": {"issues": 0, "status": "compliant"},
                "network_security": {"issues": 1, "status": "non_compliant"},
                "container_security": {"issues": 1, "status": "non_compliant"},
                "monitoring": {"issues": 0, "status": "compliant"}
            }
        })
        mock_analyzer_class.return_value = mock_analyzer

        # Call ecs_security_analysis_tool with check_compliance_status action
        result = await ecs_security_analysis_tool(
            "check_compliance_status",
            {"cluster_name": "test-cluster", "compliance_framework": "aws-foundational"}
        )

        # Verify analyzer was called
        mock_analyzer_class.assert_called_once()
        mock_analyzer.analyze_cluster.assert_called_once_with("test-cluster", "us-east-1")

        # Verify the comprehensive compliance result
        assert result["status"] == "success"
        assert result["cluster_name"] == "test-cluster"
        assert result["compliance_framework"] == "aws-foundational"
        assert result["action"] == "check_compliance_status"
        assert result["security_findings"]["total_issues"] == 2
        assert result["security_findings"]["high_priority"] >= 1
        assert result["security_findings"]["high_priority"] == 1
        assert "compliance_breakdown" in result
        assert "remediation_guidance" in result
        assert len(result["recommendations"]) == 2

    @pytest.mark.anyio
    async def test_ecs_security_analysis_tool_missing_cluster_name(self):
        """Test ecs_security_analysis_tool with missing cluster_name parameter."""
        # Call ecs_security_analysis_tool without cluster_name
        result = await ecs_security_analysis_tool(
            "analyze_cluster_security",
            {"region": "us-east-1"}
        )

        # Verify error handling
        assert result["status"] == "error"
        assert "cluster_name is required" in result["error"]

    @pytest.mark.anyio
    async def test_ecs_security_analysis_tool_invalid_action(self):
        """Test ecs_security_analysis_tool with invalid action."""
        # Call ecs_security_analysis_tool with invalid action
        result = await ecs_security_analysis_tool(
            "invalid_action",
            {"cluster_name": "test-cluster"}
        )

        # Verify error handling
        assert result["status"] == "error"
        assert "Unknown action" in result["error"]

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ECSSecurityAnalyzer")
    async def test_ecs_security_analysis_tool_analyzer_exception(self, mock_analyzer_class):
        """Test ecs_security_analysis_tool when analyzer raises exception."""
        # Mock ECSSecurityAnalyzer to raise exception
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_cluster = AsyncMock(side_effect=Exception("Analysis failed"))
        mock_analyzer_class.return_value = mock_analyzer

        # Call ecs_security_analysis_tool
        result = await ecs_security_analysis_tool(
            "analyze_cluster_security",
            {"cluster_name": "test-cluster"}
        )

        # Verify error handling
        assert result["status"] == "error"
        assert "Analysis failed" in result["error"]
        assert result["action"] == "analyze_cluster_security"
        assert "assessment" in result

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ECSSecurityAnalyzer")
    async def test_ecs_security_analysis_tool_with_category_filter(self, mock_analyzer_class):
        """Test ecs_security_analysis_tool with category filtering."""
        # Mock ECSSecurityAnalyzer with diverse categories
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_cluster = AsyncMock(return_value={
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "status": "success",
            "recommendations": [
                {
                    "title": "Network Security Issue",
                    "severity": "High",
                    "category": "network_security",
                    "resource": "Service: test-service"
                },
                {
                    "title": "IAM Security Issue",
                    "severity": "Critical",
                    "category": "iam_security",
                    "resource": "Task Role: test-role"
                },
                {
                    "title": "Container Security Issue",
                    "severity": "Medium",
                    "category": "container_security",
                    "resource": "Container: test-container"
                }
            ],
            "total_issues": 3,
            "analysis_summary": {"total_issues": 3}
        })
        mock_analyzer_class.return_value = mock_analyzer

        # Call with category filter
        result = await ecs_security_analysis_tool(
            "get_security_recommendations",
            {"cluster_name": "test-cluster", "category_filter": "network_security", "limit": 10}
        )

        # Verify filtering worked
        assert result["status"] == "success"
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["category"] == "network_security"
        assert result["filter_criteria"]["category_filter"] == "network_security"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ECSSecurityAnalyzer")
    async def test_ecs_security_analysis_tool_summary_format_report(self, mock_analyzer_class):
        """Test ecs_security_analysis_tool with summary format report."""
        # Mock ECSSecurityAnalyzer
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_cluster = AsyncMock(return_value={
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "status": "success",
            "recommendations": [
                {"title": "Test Issue", "severity": "High", "category": "network"}
            ],
            "total_issues": 1,
            "analysis_summary": {
                "total_issues": 1,
                "severity_breakdown": {
                    "High": 1,
                    "Medium": 0,
                    "Low": 0
                },
                "category_breakdown": {
                    "network": 1
                }
            }
        })
        mock_analyzer_class.return_value = mock_analyzer

        # Call with summary format
        result = await ecs_security_analysis_tool(
            "generate_security_report",
            {"cluster_name": "test-cluster", "format": "summary"}
        )

        # Verify summary format
        assert result["status"] == "success"
        assert result["report_format"] == "summary"
        # For summary format, the response structure is different
        assert "assessment" in result
        assert "report_summary" in result
        assert result["report_summary"]["total_issues"] == 1

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ECSSecurityAnalyzer")
    async def test_ecs_security_analysis_tool_compliance_framework_variations(self, mock_analyzer_class):
        """Test ecs_security_analysis_tool with different compliance frameworks."""
        # Mock ECSSecurityAnalyzer
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_cluster = AsyncMock(return_value={
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "status": "success",
            "recommendations": [
                {
                    "title": "PCI DSS Compliance Issue",
                    "severity": "Critical",
                    "category": "encryption",
                    "compliance_frameworks": ["PCI DSS", "SOC 2"]
                }
            ],
            "total_issues": 1,
            "analysis_summary": {"total_issues": 1}
        })
        mock_analyzer_class.return_value = mock_analyzer

        # Test PCI DSS compliance
        result = await ecs_security_analysis_tool(
            "check_compliance_status",
            {"cluster_name": "test-cluster", "compliance_framework": "pci-dss"}
        )

        # Verify PCI DSS specific response
        assert result["status"] == "success"
        assert result["compliance_framework"] == "pci-dss"
        assert "compliance_breakdown" in result
        assert "remediation_guidance" in result

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.get_aws_client")
    async def test_ecs_security_analysis_tool_default_parameters(self, mock_get_aws_client):
        """Test ecs_security_analysis_tool with default parameters (None)."""
        # Mock AWS client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1", "cluster-2"]}
        mock_ecs.describe_clusters.return_value = {
            "clusters": [
                {"clusterName": "cluster-1", "status": "ACTIVE"},
                {"clusterName": "cluster-2", "status": "ACTIVE"}
            ]
        }
        mock_get_aws_client.return_value = mock_ecs

        # Call with None parameters
        result = await ecs_security_analysis_tool("list_clusters", None)

        # Should handle None parameters gracefully
        assert result["status"] == "success"
        assert result["region"] == "us-east-1"  # Default region

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.get_aws_client")
    async def test_ecs_security_analysis_tool_select_cluster_for_analysis(self, mock_get_aws_client):
        """Test ecs_security_analysis_tool with select_cluster_for_analysis action."""
        # Mock AWS client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1", "cluster-2"]}
        mock_ecs.describe_clusters.return_value = {
            "clusters": [
                {"clusterName": "test-cluster-1", "status": "ACTIVE"},
                {"clusterName": "test-cluster-2", "status": "ACTIVE"}
            ]
        }
        mock_get_aws_client.return_value = mock_ecs

        # Test without cluster_name (should show selection interface)
        result = await ecs_security_analysis_tool(
            "select_cluster_for_analysis",
            {"region": "us-east-1"}
        )

        # Verify the selection interface
        assert result["status"] == "success"
        assert result["action"] == "select_cluster_for_analysis"
        assert result["total_clusters"] == 2
        assert "available_clusters" in result
        assert "cluster_selection" in result
        assert "example_usage" in result
        assert "quick_actions" in result
        
        # Verify cluster selection guidance
        assert "Choose a cluster and analysis type" in result["cluster_selection"]["description"]
        assert "analysis_types" in result["cluster_selection"]
        assert "comprehensive" in result["cluster_selection"]["analysis_types"]
        assert "quick" in result["cluster_selection"]["analysis_types"]

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.get_aws_client")
    async def test_ecs_security_analysis_tool_select_cluster_invalid_name(self, mock_get_aws_client):
        """Test ecs_security_analysis_tool with invalid cluster name in select_cluster_for_analysis."""
        # Mock AWS client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1"]}
        mock_ecs.describe_clusters.return_value = {
            "clusters": [{"clusterName": "valid-cluster", "status": "ACTIVE"}]
        }
        mock_get_aws_client.return_value = mock_ecs

        # Test with invalid cluster_name
        result = await ecs_security_analysis_tool(
            "select_cluster_for_analysis",
            {"cluster_name": "invalid-cluster", "region": "us-east-1"}
        )

        # Verify error handling
        assert result["status"] == "error"
        assert result["action"] == "select_cluster_for_analysis"
        assert "not found" in result["error"]
        assert "available_clusters" in result
        assert "valid-cluster" in result["available_clusters"]
        assert "suggestion" in result

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.get_aws_client")
    async def test_ecs_security_analysis_tool_enhanced_error_handling(self, mock_get_aws_client):
        """Test enhanced error handling for cluster not found scenarios."""
        # Mock AWS client to simulate cluster not found
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.return_value = {"clusterArns": []}
        mock_ecs.describe_clusters.return_value = {"clusters": []}
        mock_get_aws_client.return_value = mock_ecs

        # Test analyze_cluster_security with missing cluster_name
        result = await ecs_security_analysis_tool(
            "analyze_cluster_security",
            {"region": "us-east-1"}
        )

        # Verify helpful error message
        assert result["status"] == "error"
        assert result["action"] == "analyze_cluster_security"
        assert "cluster_name is required" in result["error"]
        assert "helpful_guidance" in result
        assert "suggestion" in result["helpful_guidance"]
        assert "list_clusters" in result["helpful_guidance"]["suggestion"]

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.get_aws_client")
    async def test_ecs_security_analysis_tool_cluster_selection_guidance(self, mock_get_aws_client):
        """Test that list_clusters provides comprehensive cluster selection guidance."""
        # Mock AWS client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1"]}
        mock_ecs.describe_clusters.return_value = {
            "clusters": [{"clusterName": "production-cluster", "status": "ACTIVE"}]
        }
        mock_get_aws_client.return_value = mock_ecs

        # Test list_clusters
        result = await ecs_security_analysis_tool("list_clusters", {"region": "us-east-1"})

        # Verify comprehensive guidance
        assert result["status"] == "success"
        assert "cluster_selection" in result
        assert "available_actions" in result["cluster_selection"]
        assert "select_cluster_for_analysis" in str(result["cluster_selection"]["available_actions"])
        assert "guidance" in result
        assert "quick_start" in result["guidance"]
        assert "production-cluster" in result["guidance"]["quick_start"]

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ECSSecurityAnalyzer")
    async def test_ecs_security_analysis_tool_comprehensive_security_domains(self, mock_analyzer_class):
        """Test that security analysis covers all major security domains."""
        # Mock ECSSecurityAnalyzer with comprehensive security findings
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_cluster = AsyncMock(return_value={
            "cluster_name": "comprehensive-cluster",
            "region": "us-east-1",
            "status": "success",
            "recommendations": [
                {
                    "title": "IAM Role Overprivileged",
                    "severity": "High",
                    "category": "iam_security",
                    "resource": "Task Role: overprivileged-role",
                    "issue": "Task role has wildcard permissions",
                    "recommendation": "Apply principle of least privilege",
                    "implementation": {
                        "aws_cli": "aws iam put-role-policy --role-name task-role --policy-name restricted-policy --policy-document file://policy.json",
                        "description": "Restrict IAM permissions to minimum required"
                    },
                    "compliance_frameworks": ["AWS Well-Architected", "SOC 2", "PCI DSS"]
                },
                {
                    "title": "Container Running as Root",
                    "severity": "High",
                    "category": "container_security",
                    "resource": "Container: web-app",
                    "issue": "Container is running with root privileges",
                    "recommendation": "Configure non-root user for container execution",
                    "implementation": {
                        "description": "Update Dockerfile to use non-root user"
                    }
                },
                {
                    "title": "Secrets in Environment Variables",
                    "severity": "High",
                    "category": "secrets_management",
                    "resource": "Task Definition: app-task",
                    "issue": "Hardcoded secrets found in environment variables",
                    "recommendation": "Use AWS Secrets Manager or Parameter Store",
                    "implementation": {
                        "aws_cli": "aws secretsmanager create-secret --name app-secret --secret-string '{\"key\":\"value\"}'",
                        "description": "Store secrets securely and reference them in task definition"
                    }
                },
                {
                    "title": "Missing VPC Flow Logs",
                    "severity": "Medium",
                    "category": "network_security",
                    "resource": "VPC: vpc-12345",
                    "issue": "VPC Flow Logs are not enabled",
                    "recommendation": "Enable VPC Flow Logs for network monitoring",
                    "implementation": {
                        "aws_cli": "aws ec2 create-flow-logs --resource-type VPC --resource-ids vpc-12345 --traffic-type ALL",
                        "description": "Enable comprehensive network traffic logging"
                    }
                }
            ],
            "total_issues": 4,
            "analysis_summary": {
                "total_issues": 4,
                "high_issues": 3,
                "medium_issues": 1,
                "low_issues": 0
            }
        })
        mock_analyzer_class.return_value = mock_analyzer

        # Call analyze_cluster_security
        result = await ecs_security_analysis_tool(
            "analyze_cluster_security",
            {"cluster_name": "comprehensive-cluster"}
        )

        # Verify comprehensive security coverage
        assert result["status"] == "success"
        assert result["security_summary"]["total_recommendations"] == 4
        assert result["security_summary"]["severity_breakdown"]["high"] == 3
        assert result["security_summary"]["severity_breakdown"]["medium"] == 1
        
        # Verify different security categories are covered (only High priority shown)
        categories = [rec["category"] for rec in result["priority_recommendations"]]
        assert "iam_security" in categories
        assert "container_security" in categories
        assert "secrets_management" in categories
        # network_security is Medium priority, so not in priority_recommendations
        assert len(result["priority_recommendations"]) == 3  # Only High priority

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.api.security_analysis.ECSSecurityAnalyzer")
    async def test_ecs_security_analysis_tool_implementation_guidance(self, mock_analyzer_class):
        """Test that security recommendations include detailed implementation guidance."""
        # Mock ECSSecurityAnalyzer with implementation details
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_cluster = AsyncMock(return_value={
            "cluster_name": "guidance-cluster",
            "region": "us-east-1",
            "status": "success",
            "recommendations": [
                {
                    "title": "Enable KMS Encryption",
                    "severity": "High",
                    "category": "encryption",
                    "resource": "Cluster: guidance-cluster",
                    "issue": "Data at rest is not encrypted with customer-managed keys",
                    "recommendation": "Configure KMS encryption for ECS resources",
                    "implementation": {
                        "aws_cli": "aws ecs put-cluster --cluster guidance-cluster --configuration executeCommandConfiguration='{kmsKeyId=arn:aws:kms:region:account:key/key-id}'",
                        "description": "Enable KMS encryption for secure data protection",
                        "terraform": "resource \"aws_ecs_cluster\" \"main\" { configuration { execute_command_configuration { kms_key_id = aws_kms_key.ecs.arn } } }",
                        "cloudformation": "ExecuteCommandConfiguration: { KmsKeyId: !Ref ECSKMSKey }"
                    },
                    "security_impact": "High - Protects sensitive data with customer-managed encryption",
                    "compliance_frameworks": ["AWS Well-Architected", "SOC 2", "PCI DSS", "HIPAA"],
                    "estimated_effort": "Low - 1-2 hours",
                    "prerequisites": ["KMS key must be created", "IAM permissions for KMS access"]
                }
            ],
            "total_issues": 1,
            "analysis_summary": {"total_issues": 1}
        })
        mock_analyzer_class.return_value = mock_analyzer

        # Call get_security_recommendations
        result = await ecs_security_analysis_tool(
            "get_security_recommendations",
            {"cluster_name": "guidance-cluster", "limit": 1}
        )

        # Verify comprehensive implementation guidance
        assert result["status"] == "success"
        recommendation = result["recommendations"][0]
        
        # Check implementation details
        assert "implementation" in recommendation
        assert "aws_cli" in recommendation["implementation"]
        assert "description" in recommendation["implementation"]
        
        # Check additional guidance fields
        assert "security_impact" in recommendation
        assert "compliance_frameworks" in recommendation
        assert isinstance(recommendation["compliance_frameworks"], list)
        assert len(recommendation["compliance_frameworks"]) > 0

