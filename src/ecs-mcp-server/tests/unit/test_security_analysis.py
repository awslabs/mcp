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
Unit tests for security analysis API - minimal implementation for PR #1.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.security_analysis import (
    DataAdapter,
    SecurityAnalyzer,
    analyze_ecs_security,
)
from awslabs.ecs_mcp_server.modules.security_analysis import register_module


class TestDataAdapter:
    """Test cases for DataAdapter class - minimal implementation."""

    def test_init(self) -> None:
        """Test DataAdapter initialization."""
        adapter = DataAdapter()
        assert adapter.logger is not None


class TestSecurityAnalyzer:
    """Test cases for SecurityAnalyzer class - minimal implementation."""

    def test_init(self) -> None:
        """Test SecurityAnalyzer initialization."""
        analyzer = SecurityAnalyzer()
        assert analyzer.logger is not None


class TestAnalyzeEcsSecurity:
    """Test cases for analyze_ecs_security function - minimal implementation."""

    @pytest.mark.anyio
    async def test_analyze_ecs_security_basic(self) -> None:
        """Test basic security analysis functionality."""
        result = await analyze_ecs_security()

        assert "recommendations" in result
        assert "total_issues" in result
        assert "analysis_summary" in result
        assert "timestamp" in result

        assert result["recommendations"] == []
        assert result["total_issues"] == 0
        assert isinstance(result["analysis_summary"], dict)

    @pytest.mark.anyio
    async def test_analyze_ecs_security_with_params(self) -> None:
        """Test security analysis with parameters."""
        result = await analyze_ecs_security(
            cluster_names=["test-cluster"], regions=["us-east-1"], analysis_scope="basic"
        )

        assert "recommendations" in result
        assert result["total_issues"] == 0

    @pytest.mark.anyio
    async def test_analyze_ecs_security_error_handling(self) -> None:
        """Test security analysis error handling."""
        # Mock datetime to raise an exception
        with patch("awslabs.ecs_mcp_server.api.security_analysis.datetime") as mock_datetime:
            mock_datetime.utcnow.side_effect = Exception("Test exception")

            result = await analyze_ecs_security()

            assert "error" in result
            assert "Test exception" in result["error"]
            assert result["recommendations"] == []
            assert result["total_issues"] == 0


class TestModuleRegistration:
    """Test cases for module registration."""

    @pytest.mark.anyio
    async def test_register_module(self) -> None:
        """Test module registration with MCP."""
        mock_mcp = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Register the module
        register_module(mock_mcp)

        # Verify tool was registered
        mock_mcp.tool.assert_called_once_with(name="analyze_ecs_security")

    @pytest.mark.anyio
    async def test_mcp_tool_functionality(self) -> None:
        """Test the MCP tool functionality."""
        mock_mcp = MagicMock()
        registered_tool = None

        def capture_tool(name):
            def decorator(func):
                nonlocal registered_tool
                registered_tool = func
                return func

            return decorator

        mock_mcp.tool.side_effect = capture_tool

        # Register the module
        register_module(mock_mcp)

        # Test the registered tool
        assert registered_tool is not None
        result = await registered_tool()

        assert "recommendations" in result
        assert "status" in result
        assert result["status"] == "success"

    @pytest.mark.anyio
    async def test_mcp_tool_error_handling(self) -> None:
        """Test MCP tool error handling."""
        mock_mcp = MagicMock()
        registered_tool = None

        def capture_tool(name):
            def decorator(func):
                nonlocal registered_tool
                registered_tool = func
                return func

            return decorator

        mock_mcp.tool.side_effect = capture_tool

        # Register the module
        register_module(mock_mcp)

        # Mock logger to raise exception
        with patch("awslabs.ecs_mcp_server.modules.security_analysis.logger") as mock_logger:
            mock_logger.info.side_effect = Exception("Test exception")

            result = await registered_tool()

            assert "error" in result
            assert "Test exception" in result["error"]


# Integration test placeholder
class TestIntegration:
    """Integration tests - minimal implementation."""

    def test_module_imports(self) -> None:
        """Test that all modules import correctly."""
        from awslabs.ecs_mcp_server.api import security_analysis
        from awslabs.ecs_mcp_server.modules import security_analysis as security_module

        assert security_analysis is not None
        assert security_module is not None
