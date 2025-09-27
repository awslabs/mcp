"""
Unit tests for the Security Analysis module.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from awslabs.ecs_mcp_server.modules.security_analysis import register_module


class TestSecurityAnalysisModule:
    """Tests for the Security Analysis module functions."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance."""
        return MagicMock(spec=FastMCP)

    def test_register_module(self, mock_mcp):
        """Test that register_module properly registers the security analysis tool."""
        # Call register_module
        register_module(mock_mcp)

        # Verify that mcp.tool was called to register the security analysis tool
        mock_mcp.tool.assert_called_once()

        # Get the call arguments
        call_args = mock_mcp.tool.call_args

        # Verify the tool name
        assert call_args[1]["name"] == "ecs_security_analysis_tool"
        assert call_args[1]["annotations"] is None

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.modules.security_analysis.ecs_security_analysis_tool")
    async def test_mcp_security_analysis_tool_wrapper(self, mock_security_tool, mock_mcp):
        """Test the MCP wrapper function for security analysis tool."""
        # Mock the underlying security analysis tool
        mock_security_tool.return_value = {
            "status": "success",
            "action": "list_clusters",
            "clusters": [],
        }

        # Set up the tool decorator to capture the registered function
        registered_func = None

        def mock_tool_decorator(name=None, annotations=None):
            def decorator(func):
                nonlocal registered_func
                registered_func = func
                return func

            return decorator

        mock_mcp.tool = mock_tool_decorator
        mock_mcp.prompt = MagicMock()  # Mock prompt decorator

        # Register the module to get access to the wrapper function
        register_module(mock_mcp)

        # Call the wrapper function
        result = await registered_func("list_clusters", {"region": "us-east-1"})

        # Verify the underlying tool was called correctly
        mock_security_tool.assert_called_once_with("list_clusters", {"region": "us-east-1"})

        # Verify the result is passed through
        assert result["status"] == "success"
        assert result["action"] == "list_clusters"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.modules.security_analysis.ecs_security_analysis_tool")
    async def test_mcp_security_analysis_tool_default_parameters(
        self, mock_security_tool, mock_mcp
    ):
        """Test the MCP wrapper function with default parameters."""
        # Mock the underlying security analysis tool
        mock_security_tool.return_value = {"status": "success", "action": "list_clusters"}

        # Set up the tool decorator to capture the registered function
        registered_func = None

        def mock_tool_decorator(name=None, annotations=None):
            def decorator(func):
                nonlocal registered_func
                registered_func = func
                return func

            return decorator

        mock_mcp.tool = mock_tool_decorator
        mock_mcp.prompt = MagicMock()

        # Register the module
        register_module(mock_mcp)

        # Call with None parameters (should default to empty dict)
        result = await registered_func("list_clusters", None)

        # Verify the underlying tool was called with empty dict
        mock_security_tool.assert_called_once_with("list_clusters", {})

        assert result["status"] == "success"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.modules.security_analysis.ecs_security_analysis_tool")
    async def test_mcp_security_analysis_tool_analyze_cluster(self, mock_security_tool, mock_mcp):
        """Test the MCP wrapper function for cluster analysis."""
        # Mock comprehensive security analysis response
        mock_security_tool.return_value = {
            "status": "success",
            "action": "analyze_cluster_security",
            "cluster_name": "test-cluster",
            "region": "us-east-1",
            "security_summary": {
                "total_recommendations": 5,
                "severity_breakdown": {"high": 2, "medium": 2, "low": 1},
            },
            "priority_recommendations": [
                {
                    "title": "Configure Security Groups",
                    "severity": "High",
                    "category": "network_security",
                }
            ],
        }

        # Set up the tool decorator to capture the registered function
        registered_func = None

        def mock_tool_decorator(name=None, annotations=None):
            def decorator(func):
                nonlocal registered_func
                registered_func = func
                return func

            return decorator

        mock_mcp.tool = mock_tool_decorator
        mock_mcp.prompt = MagicMock()

        # Register the module
        register_module(mock_mcp)

        # Call the analyze cluster security action
        result = await registered_func(
            "analyze_cluster_security", {"cluster_name": "test-cluster", "region": "us-east-1"}
        )

        # Verify the call
        mock_security_tool.assert_called_once_with(
            "analyze_cluster_security", {"cluster_name": "test-cluster", "region": "us-east-1"}
        )

        # Verify the comprehensive result
        assert result["status"] == "success"
        assert result["cluster_name"] == "test-cluster"
        assert result["security_summary"]["total_recommendations"] == 5
        assert len(result["priority_recommendations"]) == 1

    def test_register_security_analysis_prompts(self, mock_mcp):
        """Test that security analysis prompts are registered correctly."""
        from awslabs.ecs_mcp_server.modules.security_analysis import (
            register_security_analysis_prompts,
        )

        # Test prompt groups
        prompt_groups = {
            "Security analysis": ["analyze security", "security scan"],
            "Security issues": ["security vulnerabilities", "security problems"],
        }

        # Call the function
        register_security_analysis_prompts(mock_mcp, prompt_groups)

        # Verify that prompts were registered
        # Should be called once for each pattern (4 total patterns)
        assert mock_mcp.prompt.call_count == 4

        # Verify some of the registered patterns
        registered_patterns = [call[0][0] for call in mock_mcp.prompt.call_args_list]
        assert "analyze security" in registered_patterns
        assert "security scan" in registered_patterns
        assert "security vulnerabilities" in registered_patterns
        assert "security problems" in registered_patterns

    def test_prompt_handler_creation(self, mock_mcp):
        """Test that prompt handlers are created correctly."""
        from awslabs.ecs_mcp_server.modules.security_analysis import (
            register_security_analysis_prompts,
        )

        # Set up the prompt decorator to capture registered patterns and functions
        prompt_registrations = []

        def mock_prompt_decorator(pattern):
            def decorator(func):
                prompt_registrations.append((pattern, func))
                return func

            return decorator

        mock_mcp.prompt = mock_prompt_decorator

        # Simple test case
        prompt_groups = {"Test group": ["test pattern"]}

        # Call the function
        register_security_analysis_prompts(mock_mcp, prompt_groups)

        # Verify pattern was registered
        assert len(prompt_registrations) == 1
        pattern, handler_func = prompt_registrations[0]
        assert pattern == "test pattern"

        # Verify the handler function returns the expected tool name
        assert handler_func() == ["ecs_security_analysis_tool"]

    def test_module_docstring_completeness(self, mock_mcp):
        """Test that the registered tool has comprehensive documentation."""
        # Set up the tool decorator to capture the registered function
        registered_func = None

        def mock_tool_decorator(name=None, annotations=None):
            def decorator(func):
                nonlocal registered_func
                registered_func = func
                return func

            return decorator

        mock_mcp.tool = mock_tool_decorator
        mock_mcp.prompt = MagicMock()

        # Register the module
        register_module(mock_mcp)

        # Verify the function has comprehensive documentation
        docstring = registered_func.__doc__
        assert docstring is not None
        assert len(docstring) > 1000  # Should be comprehensive

        # Check for key sections
        assert "Available Actions and Parameters:" in docstring
        assert "Security Analysis Coverage:" in docstring
        assert "Quick Usage Examples:" in docstring
        assert "Resource Discovery:" in docstring

        # Check for specific actions
        assert "list_clusters" in docstring
        assert "analyze_cluster_security" in docstring
        assert "generate_security_report" in docstring
        assert "get_security_recommendations" in docstring
        assert "check_compliance_status" in docstring

        # Check for security domains
        assert "Network Security" in docstring
        assert "Container Security" in docstring
        assert "IAM Security" in docstring
        assert "Secrets Management" in docstring

    def test_prompt_groups_coverage(self):
        """Test that prompt groups cover major security analysis use cases."""
        # This test verifies the prompt groups defined in register_module
        # We'll import the module and check the prompt groups

        # The prompt groups are defined inline in register_module, so we'll test
        # by calling register_module and checking the registered prompts
        mock_mcp = MagicMock(spec=FastMCP)
        register_module(mock_mcp)

        # Verify that multiple prompts were registered (should be many)
        assert mock_mcp.prompt.call_count > 20  # Should have many security-related prompts

        # Get all registered patterns
        registered_patterns = [call[0][0] for call in mock_mcp.prompt.call_args_list]

        # Check for key security analysis patterns
        security_patterns = [
            "analyze security",
            "security analysis",
            "security vulnerabilities",
            "container security",
            "network security",
            "iam security",
            "compliance check",
            "security report",
            "secrets security",
        ]

        for pattern in security_patterns:
            assert pattern in registered_patterns, f"Missing security pattern: {pattern}"

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.modules.security_analysis.ecs_security_analysis_tool")
    async def test_error_handling_in_wrapper(self, mock_security_tool, mock_mcp):
        """Test error handling in the MCP wrapper function."""
        # Mock the underlying tool to raise an exception
        mock_security_tool.side_effect = Exception("Security analysis failed")

        # Set up the tool decorator to capture the registered function
        registered_func = None

        def mock_tool_decorator(name=None, annotations=None):
            def decorator(func):
                nonlocal registered_func
                registered_func = func
                return func

            return decorator

        mock_mcp.tool = mock_tool_decorator
        mock_mcp.prompt = MagicMock()

        # Register the module
        register_module(mock_mcp)

        # Call should propagate the exception
        with pytest.raises(Exception, match="Security analysis failed"):
            await registered_func("analyze_cluster_security", {"cluster_name": "test-cluster"})

    def test_function_naming_safety(self):
        """Test that prompt pattern names are safely converted to function names."""
        from awslabs.ecs_mcp_server.modules.security_analysis import (
            register_security_analysis_prompts,
        )

        # Test with patterns that have special characters
        mock_mcp = MagicMock(spec=FastMCP)
        prompt_groups = {
            "Test patterns": [
                "analyze security.*",
                "check security's status",
                'security "analysis"',
                "security analysis with spaces",
            ]
        }

        # This should not raise an exception
        register_security_analysis_prompts(mock_mcp, prompt_groups)

        # Verify all patterns were registered
        assert mock_mcp.prompt.call_count == 4

    @pytest.mark.anyio
    @patch("awslabs.ecs_mcp_server.modules.security_analysis.ecs_security_analysis_tool")
    async def test_all_security_actions(self, mock_security_tool, mock_mcp):
        """Test that all security analysis actions work through the wrapper."""
        # Mock responses for different actions
        action_responses = {
            "list_clusters": {"status": "success", "clusters": []},
            "select_cluster_for_analysis": {"status": "success", "available_clusters": []},
            "analyze_cluster_security": {"status": "success", "recommendations": []},
            "generate_security_report": {"status": "success", "report_format": "summary"},
            "get_security_recommendations": {"status": "success", "recommendations": []},
            "check_compliance_status": {
                "status": "success",
                "compliance_framework": "aws-foundational",
            },
        }

        def mock_tool_response(action, parameters):
            return action_responses.get(action, {"status": "error", "error": "Unknown action"})

        mock_security_tool.side_effect = mock_tool_response

        # Set up the tool decorator to capture the registered function
        registered_func = None

        def mock_tool_decorator(name=None, annotations=None):
            def decorator(func):
                nonlocal registered_func
                registered_func = func
                return func

            return decorator

        mock_mcp.tool = mock_tool_decorator
        mock_mcp.prompt = MagicMock()

        # Register the module
        register_module(mock_mcp)

        # Test each action
        for action in action_responses.keys():
            result = await registered_func(action, {"cluster_name": "test-cluster"})
            assert result["status"] == "success"

        # Verify all actions were called
        assert mock_security_tool.call_count == len(action_responses)
