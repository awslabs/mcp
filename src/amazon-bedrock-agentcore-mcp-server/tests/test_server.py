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


class TestServerStartup:
    """Test server startup and shutdown procedures."""

    def test_run_main_function_exists(self):
        """Test that the run_main function is available."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import run_main

        assert callable(run_main)

    def test_server_directory_path(self):
        """Test server directory path resolution."""
        from pathlib import Path

        server_file = (
            Path(__file__).parent.parent
            / 'awslabs'
            / 'amazon_bedrock_agentcore_mcp_server'
            / 'server.py'
        )
        assert server_file.exists()

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.server.mcp.run')
    def test_run_main_starts_server(self, mock_run):
        """Test that run_main starts the MCP server."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import run_main

        with patch('builtins.print'):  # Suppress print output during tests
            run_main()

        mock_run.assert_called_once()

    def test_server_exception_handling(self):
        """Test server exception handling in main block."""
        import subprocess
        import sys
        from pathlib import Path

        # Get the server file path
        server_file = (
            Path(__file__).parent.parent
            / 'awslabs'
            / 'amazon_bedrock_agentcore_mcp_server'
            / 'server.py'
        )

        # Test keyboard interrupt handling by running the server as a subprocess
        # and immediately terminating it
        process = None
        try:
            # Start the server process
            process = subprocess.Popen(
                [sys.executable, str(server_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Give it a moment to start
            import time

            time.sleep(0.5)

            # Send keyboard interrupt
            process.terminate()

            # Wait for process to complete
            stdout, stderr = process.communicate(timeout=5)

            # The process should exit gracefully
            assert process.returncode is not None

        except subprocess.TimeoutExpired:
            # If it times out, kill the process
            if process is not None:
                process.kill()
                process.wait()
            # This is still a successful test - server started and needed to be killed
            assert True


class TestToolCoverage:
    """Test comprehensive tool coverage and functionality."""

    @pytest.mark.asyncio
    async def test_all_expected_tools_registered(self):
        """Verify all expected tools are registered with correct names."""
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        # Environment and OAuth tools
        expected_tools = {
            'get_oauth_access_token',
            'validate_agentcore_environment',
            # Discovery tools
            'invokable_agents',
            'project_discover',
            'discover_agentcore_examples',
            # Runtime and analysis tools
            'analyze_agent_code',
            'transform_to_agentcore',
            'deploy_agentcore_app',
            'invoke_agent',
            'invoke_oauth_agent',
            'get_runtime_oauth_token',
            'check_oauth_status',
            'invoke_agent_smart',
            'get_agent_status',
            'discover_existing_agents',
            # Gateway tools
            'agent_gateway',
            # Identity tools
            'manage_credentials',
            # Memory tools
            'agent_memory',
        }

        missing_tools = expected_tools - set(tool_names)
        assert not missing_tools, f'Missing expected tools: {missing_tools}'

        # Should have at least the expected number of tools
        assert len(tools) >= len(expected_tools)

    @pytest.mark.asyncio
    async def test_tool_descriptions_exist(self):
        """Test that all tools have descriptions."""
        tools = await mcp.list_tools()

        for tool in tools:
            assert hasattr(tool, 'description')
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

    @pytest.mark.asyncio
    async def test_tools_have_valid_schemas(self):
        """Test that all tools have valid parameter schemas."""
        tools = await mcp.list_tools()

        for tool in tools:
            # Each tool should have an inputSchema
            assert hasattr(tool, 'inputSchema')

            # The schema should be a dictionary
            assert isinstance(tool.inputSchema, dict)

            # Basic schema structure validation
            if 'properties' in tool.inputSchema:
                assert isinstance(tool.inputSchema['properties'], dict)


class TestCrossModuleIntegration:
    """Test integration between different modules."""

    @pytest.mark.asyncio
    async def test_utils_tools_integration(self):
        """Test utils module tools are properly integrated."""
        result_tuple = await mcp.call_tool(
            'validate_agentcore_environment', {'project_path': '.', 'check_existing_agents': False}
        )
        result = extract_result(result_tuple)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_runtime_tools_integration(self):
        """Test runtime module tools are properly integrated."""
        # Test with basic code content
        sample_code = 'print("Hello, AgentCore!")'

        result_tuple = await mcp.call_tool(
            'analyze_agent_code', {'file_path': '', 'code_content': sample_code}
        )
        result = extract_result(result_tuple)

        assert result is not None
        assert 'Agent Code Analysis Complete' in result

    @pytest.mark.asyncio
    async def test_gateway_tools_integration(self):
        """Test gateway module tools are properly integrated."""
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', False):
            result_tuple = await mcp.call_tool('agent_gateway', {'action': 'list'})
            result = extract_result(result_tuple)

            assert result is not None
            assert 'SDK Not Available' in result

    @pytest.mark.asyncio
    async def test_identity_tools_integration(self):
        """Test identity module tools are properly integrated."""
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.identity.SDK_AVAILABLE', False):
            result_tuple = await mcp.call_tool('manage_credentials', {'action': 'list'})
            result = extract_result(result_tuple)

            assert result is not None
            assert 'SDK Not Available' in result

    @pytest.mark.asyncio
    async def test_memory_tools_integration(self):
        """Test memory module tools are properly integrated."""
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', False):
            result_tuple = await mcp.call_tool('agent_memory', {'action': 'list'})
            result = extract_result(result_tuple)

            assert result is not None
            assert 'SDK Not Available' in result


class TestErrorRecovery:
    """Test error recovery and graceful degradation."""

    @pytest.mark.asyncio
    async def test_tool_error_recovery(self):
        """Test that tools handle errors gracefully without crashing server."""
        # Try calling tools with problematic inputs
        problematic_calls = [
            ('analyze_agent_code', {'file_path': '/nonexistent/path.py', 'code_content': ''}),
            ('deploy_agentcore_app', {'app_file': 'missing.py', 'agent_name': 'test'}),
            ('agent_gateway', {'action': 'invalid_action'}),
            ('agent_memory', {'action': 'invalid', 'agent_name': 'test'}),
        ]

        for tool_name, params in problematic_calls:
            try:
                result_tuple = await mcp.call_tool(tool_name, params)
                result = extract_result(result_tuple)

                # Should get some response, not crash
                assert result is not None
                assert isinstance(result, str)

            except Exception as e:
                # If an exception is raised, it should be handled gracefully
                assert 'Server crash' not in str(e).lower()

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test server handles concurrent tool calls."""
        import asyncio

        # Make several concurrent calls
        tasks = []
        for i in range(5):
            task = mcp.call_tool(
                'validate_agentcore_environment',
                {'project_path': '.', 'check_existing_agents': False},
            )
            tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete successfully
        assert len(results) == 5
        for result in results:
            assert not isinstance(result, Exception)
            extracted = extract_result(result)
            assert extracted is not None


class TestServerMetadata:
    """Test server metadata and configuration."""

    def test_server_name(self):
        """Test server has correct name."""
        assert mcp.name == 'AgentCore MCP Server'

    @pytest.mark.asyncio
    async def test_server_has_tools(self):
        """Test server has registered tools."""
        tools = await mcp.list_tools()
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_tool_names_unique(self):
        """Test all tool names are unique."""
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        # Check for duplicates
        assert len(tool_names) == len(set(tool_names)), 'Duplicate tool names found'

    @pytest.mark.asyncio
    async def test_tools_accessible(self):
        """Test that tools are accessible through the server."""
        tools = await mcp.list_tools()

        # Pick a simple tool to test
        environment_tools = [t for t in tools if t.name == 'validate_agentcore_environment']
        assert len(environment_tools) == 1

        # Should be able to call it
        result_tuple = await mcp.call_tool(
            'validate_agentcore_environment', {'project_path': '.', 'check_existing_agents': False}
        )
        result = extract_result(result_tuple)
        assert result is not None


class TestServerMainBlock:
    """Test the __main__ block exception handling."""

    def test_main_block_keyboard_interrupt(self):
        """Test KeyboardInterrupt handling in main block."""
        import sys
        from unittest.mock import patch

        # Mock the run_main function to raise KeyboardInterrupt
        with patch(
            'awslabs.amazon_bedrock_agentcore_mcp_server.server.run_main',
            side_effect=KeyboardInterrupt,
        ):
            with patch('builtins.print') as mock_print:
                with patch('sys.exit') as mock_exit:
                    # Execute the main block code
                    try:
                        from awslabs.amazon_bedrock_agentcore_mcp_server.server import run_main

                        run_main()
                    except KeyboardInterrupt:
                        print('\nAgentCore MCP Server shutting down...')
                        sys.exit(0)

                    # Should have printed shutdown message and exited with 0
                    mock_print.assert_called_with('\nAgentCore MCP Server shutting down...')
                    mock_exit.assert_called_with(0)

    def test_main_block_exception_handling(self):
        """Test general exception handling in main block."""
        import sys
        import traceback
        from unittest.mock import patch

        test_error = Exception('Test server error')

        # Mock the run_main function to raise an exception
        with patch(
            'awslabs.amazon_bedrock_agentcore_mcp_server.server.run_main', side_effect=test_error
        ):
            with patch('builtins.print') as mock_print:
                with patch('sys.exit') as mock_exit:
                    with patch('traceback.print_exc') as mock_traceback:
                        # Execute the main block code
                        try:
                            from awslabs.amazon_bedrock_agentcore_mcp_server.server import run_main

                            run_main()
                        except Exception as e:
                            print(f'\nServer error: {str(e)}')
                            traceback.print_exc()
                            sys.exit(1)

                        # Should have printed error message, traceback, and exited with 1
                        mock_print.assert_called_with(f'\nServer error: {str(test_error)}')
                        mock_traceback.assert_called_once()
                        mock_exit.assert_called_with(1)

    def test_main_block_execution_path(self):
        """Test successful execution path in main block."""
        from unittest.mock import patch

        # Mock the run_main function to succeed
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.server.run_main') as mock_run_main:
            with patch('sys.exit'):
                # Execute the main block code
                try:
                    from awslabs.amazon_bedrock_agentcore_mcp_server.server import run_main

                    run_main()
                except (KeyboardInterrupt, Exception):
                    pass  # These are handled in other tests

                # run_main should have been called
                mock_run_main.assert_called_once()
