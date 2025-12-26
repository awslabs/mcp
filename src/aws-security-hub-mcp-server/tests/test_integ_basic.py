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
"""Integration tests for AWS Security Hub MCP Server."""

import pytest
import sys
import os

# Add the testing utilities to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'testing'))

try:
    from testing.mcp_test_utils import MCPTestRunner
except ImportError:
    pytest.skip("MCP test utilities not available", allow_module_level=True)


@pytest.mark.integration
class TestSecurityHubMCPIntegration:
    """Integration tests for Security Hub MCP Server."""

    @pytest.fixture(scope="class")
    def mcp_runner(self):
        """Create MCP test runner for Security Hub server."""
        return MCPTestRunner(
            server_script_path="awslabs/aws_security_hub_mcp_server/server.py",
            server_name="awslabs.aws-security-hub-mcp-server"
        )

    @pytest.mark.asyncio
    async def test_server_initialization(self, mcp_runner):
        """Test that the MCP server initializes correctly."""
        async with mcp_runner as runner:
            # Test that server starts without errors
            assert runner.server_process is not None
            
            # Test that tools are available
            tools = await runner.list_tools()
            expected_tools = [
                'get_security_findings',
                'get_compliance_summary',
                'get_insights',
                'get_finding_statistics',
                'update_finding_workflow',
                'get_security_score'
            ]
            
            tool_names = [tool['name'] for tool in tools]
            for expected_tool in expected_tools:
                assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_get_security_findings_tool(self, mcp_runner):
        """Test the get_security_findings tool."""
        async with mcp_runner as runner:
            # Test with basic parameters
            result = await runner.call_tool(
                'get_security_findings',
                {
                    'max_results': 5,
                    'days_back': 7
                }
            )
            
            # Should return a list (even if empty)
            assert isinstance(result, list)
            
            # If there are findings, they should have the expected structure
            if result:
                finding = result[0]
                required_fields = ['id', 'title', 'description', 'severity_label', 'workflow_status']
                for field in required_fields:
                    assert field in finding

    @pytest.mark.asyncio
    async def test_get_compliance_summary_tool(self, mcp_runner):
        """Test the get_compliance_summary tool."""
        async with mcp_runner as runner:
            result = await runner.call_tool('get_compliance_summary', {})
            
            # Should return a list
            assert isinstance(result, list)
            
            # If there are summaries, they should have the expected structure
            if result:
                summary = result[0]
                required_fields = ['standard_name', 'enabled', 'total_controls', 'compliance_percentage']
                for field in required_fields:
                    assert field in summary

    @pytest.mark.asyncio
    async def test_get_insights_tool(self, mcp_runner):
        """Test the get_insights tool."""
        async with mcp_runner as runner:
            result = await runner.call_tool(
                'get_insights',
                {'max_results': 10}
            )
            
            # Should return a list
            assert isinstance(result, list)
            
            # If there are insights, they should have the expected structure
            if result:
                insight = result[0]
                required_fields = ['insight_arn', 'name', 'filters']
                for field in required_fields:
                    assert field in insight

    @pytest.mark.asyncio
    async def test_get_finding_statistics_tool(self, mcp_runner):
        """Test the get_finding_statistics tool."""
        async with mcp_runner as runner:
            result = await runner.call_tool(
                'get_finding_statistics',
                {
                    'group_by': 'SeverityLabel',
                    'days_back': 30
                }
            )
            
            # Should return a list
            assert isinstance(result, list)
            
            # If there are statistics, they should have the expected structure
            if result:
                stat = result[0]
                required_fields = ['group_key', 'count', 'percentage']
                for field in required_fields:
                    assert field in stat

    @pytest.mark.asyncio
    async def test_get_security_score_tool(self, mcp_runner):
        """Test the get_security_score tool."""
        async with mcp_runner as runner:
            result = await runner.call_tool('get_security_score', {})
            
            # Should return a security score object
            assert isinstance(result, dict)
            
            required_fields = ['current_score', 'max_score', 'score_date', 'security_score_percentage']
            for field in required_fields:
                assert field in result
            
            # Score should be between 0 and 100
            assert 0 <= result['current_score'] <= 100
            assert result['max_score'] == 100

    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_runner):
        """Test error handling for invalid parameters."""
        async with mcp_runner as runner:
            # Test with invalid severity label
            with pytest.raises(Exception):
                await runner.call_tool(
                    'get_security_findings',
                    {'severity_labels': ['INVALID_SEVERITY']}
                )

    @pytest.mark.asyncio
    async def test_tool_descriptions(self, mcp_runner):
        """Test that all tools have proper descriptions."""
        async with mcp_runner as runner:
            tools = await runner.list_tools()
            
            for tool in tools:
                assert 'description' in tool
                assert len(tool['description']) > 0
                assert 'inputSchema' in tool
                assert 'properties' in tool['inputSchema']