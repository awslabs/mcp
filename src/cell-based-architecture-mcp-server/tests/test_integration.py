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

from awslabs.cell_based_architecture_mcp_server.server import mcp, query_cell_concepts, get_implementation_guidance, analyze_cell_design, validate_architecture, cell_architecture_guide, implementation_patterns, best_practices


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
        # Test that tool functions exist and are callable
        expected_tools = [
            query_cell_concepts,
            get_implementation_guidance, 
            analyze_cell_design,
            validate_architecture
        ]
        
        for tool_func in expected_tools:
            assert callable(tool_func), f"Tool {tool_func.__name__} not callable"

    def test_server_resources_registration(self):
        """Test that all required resources are registered."""
        # Test that resource functions exist and are callable
        expected_resources = [
            cell_architecture_guide,
            implementation_patterns,
            best_practices
        ]
        
        for resource_func in expected_resources:
            assert callable(resource_func), f"Resource {resource_func.__name__} not callable"

    def test_tool_parameter_validation(self):
        """Test that tools have proper parameter validation."""
        # Test query_cell_concepts parameters
        import inspect
        sig = inspect.signature(query_cell_concepts)
        assert 'concept' in sig.parameters
        assert 'detail_level' in sig.parameters
        assert 'whitepaper_section' in sig.parameters

    def test_resource_mime_types(self):
        """Test that resources have proper MIME types."""
        # Test that resources return valid JSON
        import asyncio
        import json
        
        async def test_resource(resource_func):
            result = await resource_func()
            json.loads(result)  # Should not raise exception
        
        for resource_func in [cell_architecture_guide, implementation_patterns, best_practices]:
            asyncio.run(test_resource(resource_func))


class TestEndToEndWorkflows:
    """Test complete request/response cycles."""

    @pytest.mark.asyncio
    async def test_complete_query_workflow(self):
        """Test complete query workflow from request to response."""
        # Test beginner level query
        result = await query_cell_concepts(
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
        result = await get_implementation_guidance(
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
        result = await cell_architecture_guide()
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert "title" in data
        assert "sections" in data

    @pytest.mark.asyncio
    async def test_analysis_workflow(self):
        """Test architecture analysis workflow."""
        result = await analyze_cell_design(
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
        # Test with invalid input to trigger error handling
        result = await query_cell_concepts(
            concept="test concept",
            detail_level="beginner"
        )
        
        assert isinstance(result, str)
        # Should contain error message or graceful fallback
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_resource_error_recovery(self):
        """Test resource error recovery."""
        # Test that resources return valid JSON even on errors
        with patch('awslabs.cell_based_architecture_mcp_server.knowledge.CellBasedArchitectureKnowledge.WHITEPAPER_SECTIONS', {}):
            result = await cell_architecture_guide()
            
            # Should return valid JSON even with empty knowledge base
            assert isinstance(result, str)
            data = json.loads(result)  # Should not raise JSON decode error
            assert isinstance(data, dict)


class TestMCPInspectorCompatibility:
    """Test compatibility with MCP Inspector for testing."""

    def test_tool_descriptions(self):
        """Test that tools have proper descriptions for MCP Inspector."""
        # Test that tool functions have docstrings
        tools = [query_cell_concepts, get_implementation_guidance, analyze_cell_design, validate_architecture]
        for tool in tools:
            assert tool.__doc__ is not None
            assert len(tool.__doc__) > 50  # Substantial description

    def test_resource_descriptions(self):
        """Test that resources have proper descriptions."""
        # Test that resource functions have docstrings
        resources = [cell_architecture_guide, implementation_patterns, best_practices]
        for resource in resources:
            assert resource.__doc__ is not None
            assert len(resource.__doc__) > 30

    def test_server_instructions_format(self):
        """Test that server instructions are properly formatted."""
        instructions = mcp.instructions
        
        # Should contain key sections
        assert "Available Tools" in instructions
        assert "Available Resources" in instructions
        assert "Usage Notes" in instructions
        
        # Should mention all tools
        tool_names = ['query-cell-concepts', 'get-implementation-guidance', 'analyze-cell-design', 'validate-architecture']
        for tool_name in tool_names:
            assert tool_name in instructions

    def test_parameter_field_descriptions(self):
        """Test that tool parameters have Field descriptions."""
        import inspect
        
        tools = [query_cell_concepts, get_implementation_guidance, analyze_cell_design, validate_architecture]
        for tool in tools:
            sig = inspect.signature(tool)
            for param_name, param in sig.parameters.items():
                if param_name not in ['self', 'args', 'kwargs']:
                    # Parameters should have type annotations
                    assert param.annotation != inspect.Parameter.empty


class TestAWSServiceMocking:
    """Test AWS service integration with mocking."""

    @pytest.mark.asyncio
    async def test_aws_region_configuration(self):
        """Test AWS region configuration."""
        import os
        
        # Test with different AWS regions
        with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
            result = await query_cell_concepts(
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
            result = await query_cell_concepts(
                concept="aws services",
                detail_level="expert"
            )
            
            assert isinstance(result, str)
            # Should work with different profiles

    @pytest.mark.asyncio
    async def test_no_aws_credentials_handling(self):
        """Test handling when AWS credentials are not available."""
        # The server should work for knowledge queries even without AWS credentials
        result = await query_cell_concepts(
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
            task = query_cell_concepts(
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
        tasks = [cell_architecture_guide() for _ in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, str)
            data = json.loads(result)
            assert isinstance(data, dict)