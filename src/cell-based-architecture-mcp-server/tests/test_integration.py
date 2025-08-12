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
"""Integration tests for MCP protocol compliance."""

import json
import pytest
from unittest.mock import patch, AsyncMock
from mcp.server.fastmcp import FastMCP

from awslabs.cell_based_architecture_mcp_server.server import mcp


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and server communication."""

    def test_server_initialization(self):
        """Test that the MCP server initializes correctly."""
        assert isinstance(mcp, FastMCP)
        assert mcp.name == 'awslabs-cell-based-architecture-mcp-server'
        assert mcp.instructions is not None
        assert len(mcp.instructions) > 0

    def test_server_tools_registration(self):
        """Test that all required tools are registered."""
        tool_names = [tool.name for tool in mcp.tools]
        
        expected_tools = [
            'query-cell-concepts',
            'get-implementation-guidance', 
            'analyze-cell-design',
            'validate-architecture'
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    def test_server_resources_registration(self):
        """Test that all required resources are registered."""
        resource_uris = [resource.uri for resource in mcp.resources]
        
        expected_resources = [
            'resource://cell-architecture-guide',
            'resource://implementation-patterns',
            'resource://best-practices'
        ]
        
        for resource_uri in expected_resources:
            assert resource_uri in resource_uris, f"Resource {resource_uri} not registered"

    def test_tool_parameter_validation(self):
        """Test that tools have proper parameter validation."""
        query_tool = next(tool for tool in mcp.tools if tool.name == 'query-cell-concepts')
        
        # Check that the tool has required parameters
        assert hasattr(query_tool, 'func')
        
        # Verify parameter annotations exist
        import inspect
        sig = inspect.signature(query_tool.func)
        assert 'concept' in sig.parameters
        assert 'detail_level' in sig.parameters

    def test_resource_mime_types(self):
        """Test that resources have proper MIME types."""
        for resource in mcp.resources:
            assert hasattr(resource, 'mime_type')
            assert resource.mime_type == 'application/json'


class TestEndToEndWorkflows:
    """Test complete request/response cycles."""

    @pytest.mark.asyncio
    async def test_complete_query_workflow(self):
        """Test complete query workflow from request to response."""
        # Test beginner level query
        result = await mcp.tools[0].func(
            concept="cell isolation",
            detail_level="beginner"
        )
        
        assert isinstance(result, str)
        assert len(result) > 100
        assert "cell" in result.lower()
        assert "isolation" in result.lower()

    @pytest.mark.asyncio
    async def test_implementation_guidance_workflow(self):
        """Test implementation guidance workflow."""
        guidance_tool = next(tool for tool in mcp.tools if tool.name == 'get-implementation-guidance')
        
        result = await guidance_tool.func(
            stage="design",
            aws_services=["lambda", "dynamodb"],
            experience_level="intermediate"
        )
        
        assert isinstance(result, str)
        assert "design" in result.lower()
        assert "lambda" in result.lower()
        assert "dynamodb" in result.lower()

    @pytest.mark.asyncio
    async def test_resource_serving_workflow(self):
        """Test resource serving workflow."""
        guide_resource = next(res for res in mcp.resources if res.uri == 'resource://cell-architecture-guide')
        
        result = await guide_resource.func()
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert "title" in data
        assert "sections" in data

    @pytest.mark.asyncio
    async def test_analysis_workflow(self):
        """Test architecture analysis workflow."""
        analyze_tool = next(tool for tool in mcp.tools if tool.name == 'analyze-cell-design')
        
        result = await analyze_tool.func(
            architecture_description="System with isolated Lambda functions and DynamoDB tables",
            focus_areas=["isolation", "scalability"]
        )
        
        assert isinstance(result, str)
        assert "analysis" in result.lower()
        assert "compliance score" in result.lower()


class TestTimeoutHandling:
    """Test timeout handling and error recovery."""

    @pytest.mark.asyncio
    async def test_tool_timeout_handling(self):
        """Test that tools handle timeouts gracefully."""
        # Simulate a long-running operation
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = Exception("Timeout")
            
            # Tool should handle exceptions gracefully
            result = await mcp.tools[0].func(
                concept="test concept",
                detail_level="beginner"
            )
            
            assert isinstance(result, str)
            # Should not raise an exception

    @pytest.mark.asyncio
    async def test_resource_error_recovery(self):
        """Test resource error recovery."""
        # Test that resources return valid JSON even on errors
        with patch('awslabs.cell_based_architecture_mcp_server.knowledge.CellBasedArchitectureKnowledge.WHITEPAPER_SECTIONS', {}):
            guide_resource = next(res for res in mcp.resources if res.uri == 'resource://cell-architecture-guide')
            result = await guide_resource.func()
            
            # Should return valid JSON even with empty knowledge base
            assert isinstance(result, str)
            data = json.loads(result)  # Should not raise JSON decode error
            assert isinstance(data, dict)


class TestMCPInspectorCompatibility:
    """Test compatibility with MCP Inspector for testing."""

    def test_tool_descriptions(self):
        """Test that tools have proper descriptions for MCP Inspector."""
        for tool in mcp.tools:
            assert hasattr(tool, 'func')
            assert tool.func.__doc__ is not None
            assert len(tool.func.__doc__.strip()) > 0

    def test_resource_descriptions(self):
        """Test that resources have proper descriptions."""
        for resource in mcp.resources:
            assert hasattr(resource, 'func')
            assert resource.func.__doc__ is not None
            assert len(resource.func.__doc__.strip()) > 0

    def test_server_instructions_format(self):
        """Test that server instructions are properly formatted."""
        instructions = mcp.instructions
        
        # Should contain key sections
        assert "Available Tools" in instructions
        assert "Available Resources" in instructions
        assert "Usage Notes" in instructions
        
        # Should mention all tools
        for tool in mcp.tools:
            assert tool.name in instructions

    def test_parameter_field_descriptions(self):
        """Test that tool parameters have Field descriptions."""
        import inspect
        
        for tool in mcp.tools:
            sig = inspect.signature(tool.func)
            for param_name, param in sig.parameters.items():
                if param_name != 'return':
                    # Parameters should have annotations for MCP Inspector
                    assert param.annotation != inspect.Parameter.empty


class TestAWSServiceMocking:
    """Test AWS service integration with mocking."""

    @pytest.mark.asyncio
    async def test_aws_region_configuration(self):
        """Test AWS region configuration."""
        import os
        
        # Test with different AWS regions
        with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
            result = await mcp.tools[0].func(
                concept="aws integration",
                detail_level="intermediate"
            )
            
            assert isinstance(result, str)
            # Should work regardless of region

    @pytest.mark.asyncio
    async def test_aws_profile_handling(self):
        """Test AWS profile handling."""
        import os
        
        # Test with different AWS profiles
        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'}):
            result = await mcp.tools[0].func(
                concept="aws services",
                detail_level="expert"
            )
            
            assert isinstance(result, str)
            # Should work with different profiles

    @pytest.mark.asyncio
    async def test_no_aws_credentials_handling(self):
        """Test handling when AWS credentials are not available."""
        # The server should work for knowledge queries even without AWS credentials
        result = await mcp.tools[0].func(
            concept="cell design principles",
            detail_level="beginner"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Knowledge-based queries should work without AWS credentials


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test concurrent tool calls."""
        import asyncio
        
        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            task = mcp.tools[0].func(
                concept=f"concept {i}",
                detail_level="intermediate"
            )
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_concurrent_resource_access(self):
        """Test concurrent resource access."""
        import asyncio
        
        # Create multiple concurrent resource requests
        guide_resource = next(res for res in mcp.resources if res.uri == 'resource://cell-architecture-guide')
        
        tasks = [guide_resource.func() for _ in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, str)
            data = json.loads(result)
            assert isinstance(data, dict)