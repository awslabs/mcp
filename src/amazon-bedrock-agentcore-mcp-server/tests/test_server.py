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
"""Test module for modular server implementation."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.server import mcp
from unittest.mock import patch


def extract_result(mcp_result):
    """Extract the actual result string from MCP call_tool return value."""
    if isinstance(mcp_result, tuple) and len(mcp_result) >= 2:
        result_content = mcp_result[1]
        if isinstance(result_content, dict):
            return result_content.get('result', str(mcp_result))
        elif hasattr(result_content, 'content'):
            return str(result_content.content)
        return str(result_content)
    elif hasattr(mcp_result, 'content') and not isinstance(mcp_result, tuple):
        return str(mcp_result.content)  # type: ignore
    return str(mcp_result)


class TestAgentCoreMCPServer:
    """Test cases for the modular AgentCore MCP Server."""

    def test_server_initialization(self):
        """Test that server initializes correctly."""
        assert mcp is not None
        assert mcp.name == 'AgentCore MCP Server'

    @pytest.mark.asyncio
    async def test_tools_registration(self):
        """Test that all expected tools are registere."""
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        # Core server tools
        # OAuth and environment tools
        assert 'get_oauth_access_token' in tool_names
        assert 'validate_agentcore_environment' in tool_names

        # Discovery tools
        assert 'invokable_agents' in tool_names
        assert 'project_discover' in tool_names
        assert 'discover_agentcore_examples' in tool_names

        # Analysis and deployment tools
        assert 'analyze_agent_code' in tool_names
        assert 'transform_to_agentcore' in tool_names
        assert 'deploy_agentcore_app' in tool_names
        assert 'invoke_agent' in tool_names
        assert 'get_agent_status' in tool_names

        # Gateway management
        assert 'agent_gateway' in tool_names

        # Identity management
        assert 'manage_credentials' in tool_names

        # Memory management
        assert 'agent_memory' in tool_names

        # Should have at least 15 tools
        assert len(tools) >= 15

    @pytest.mark.asyncio
    async def test_validate_agentcore_environment_tool(self):
        """Test the environment validation tool."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_mcp_server.utils.get_user_working_directory'
        ) as mock_dir:
            from pathlib import Path

            mock_dir.return_value = Path.cwd()

            result_tuple = await mcp.call_tool(
                'validate_agentcore_environment',
                {'project_path': '.', 'check_existing_agents': False},
            )
            result = extract_result(result_tuple)

            assert result is not None
            assert 'Environment Validation' in result
            assert 'Project directory:' in result

    @pytest.mark.asyncio
    async def test_analyze_agent_code_tool_error_handling(self):
        """Test analyze_agent_code tool handles missing files correctly."""
        result_tuple = await mcp.call_tool(
            'analyze_agent_code', {'file_path': 'nonexistent_file.py', 'code_content': ''}
        )
        result = extract_result(result_tuple)

        assert result is not None
        assert 'No Code Found' in result or 'not found' in result or 'Error' in result

    @pytest.mark.asyncio
    async def test_analyze_agent_code_with_content(self):
        """Test analyze_agent_code tool with actual code content."""
        sample_code = """
import fastapi
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
"""

        result_tuple = await mcp.call_tool(
            'analyze_agent_code', {'file_path': '', 'code_content': sample_code}
        )
        result = extract_result(result_tuple)

        assert result is not None
        assert 'Agent Code Analysis Complete' in result
        assert 'FastAPI' in result


class TestModuleIntegration:
    """Test integration between modules."""

    @pytest.mark.asyncio
    async def test_oauth_tools_available(self):
        """Test OAuth tools are properly registered."""
        tools = await mcp.list_tools()
        oauth_tools = [tool for tool in tools if 'oauth' in tool.name.lower()]

        assert len(oauth_tools) > 0
        assert any('get_oauth_access_token' == tool.name for tool in oauth_tools)

    @pytest.mark.asyncio
    async def test_gateway_tools_available(self):
        """Test gateway tools are properly registered."""
        tools = await mcp.list_tools()
        gateway_tools = [tool for tool in tools if 'gateway' in tool.name.lower()]

        assert len(gateway_tools) > 0
        assert any('agent_gateway' == tool.name for tool in gateway_tools)

    @pytest.mark.asyncio
    async def test_memory_tools_available(self):
        """Test memory tools are properly registered."""
        tools = await mcp.list_tools()
        memory_tools = [tool for tool in tools if 'memory' in tool.name.lower()]

        assert len(memory_tools) > 0
        assert any('agent_memory' == tool.name for tool in memory_tools)

    @pytest.mark.asyncio
    async def test_credential_tools_available(self):
        """Test credential tools are properly registered."""
        tools = await mcp.list_tools()
        credential_tools = [tool for tool in tools if 'credential' in tool.name.lower()]

        assert len(credential_tools) > 0
        assert any('manage_credentials' == tool.name for tool in credential_tools)


class TestErrorHandling:
    """Test error handling across the server."""

    @pytest.mark.asyncio
    async def test_invalid_tool_call(self):
        """Test calling non-existent tool returns appropriate error."""
        with pytest.raises(Exception):  # FastMCP should raise an exception
            await mcp.call_tool('nonexistent_tool', {})

    @pytest.mark.asyncio
    async def test_tool_with_invalid_params(self):
        """Test tools handle invalid parameters gracefully."""
        # This should not crash but return an error message
        result_tuple = await mcp.call_tool(
            'deploy_agentcore_app',
            {
                'app_file': 'test.py',  # Valid file path
                'agent_name': 'test_agent',  # Required agent name
            },
        )
        result = extract_result(result_tuple)

        assert result is not None
        assert (
            'not found' in result.lower()
            or 'error' in result.lower()
            or 'missing' in result.lower()
            or 'not available' in result.lower()
            or 'sdk' in result.lower()
        )


class TestSDKAvailability:
    """Test behavior when SDK is not available."""

    @pytest.mark.asyncio
    async def test_tools_handle_missing_sdk(self):
        """Test tools provide helpful error messages when SDK is missing."""
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.SDK_AVAILABLE', False):
            # Import the tool functions to test with patched SDK_AVAILABLE
            from awslabs.amazon_bedrock_agentcore_mcp_server.runtime import (
                register_deployment_tools,
            )
            from mcp.server.fastmcp import FastMCP

            test_mcp = FastMCP('Test Server')
            register_deployment_tools(test_mcp)

            result_tuple = await test_mcp.call_tool(
                'deploy_agentcore_app', {'app_file': 'test.py', 'agent_name': 'test_agent'}
            )
            result = extract_result(result_tuple)

            assert result is not None


if __name__ == '__main__':
    import asyncio

    async def run_basic_test():
        """Run a basic test to verify server works."""
        print('Testing tool list...')
        tools = await mcp.list_tools()
        print(f'✓ {len(tools)} tools registered')

        print('All basic tests passed!')

    asyncio.run(run_basic_test())
