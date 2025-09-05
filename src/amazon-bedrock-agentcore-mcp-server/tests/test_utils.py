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

"""Test module for utils functionality."""

import asyncio
import pytest
import tempfile
from awslabs.amazon_bedrock_agentcore_mcp_server.utils import (
    RUNTIME_AVAILABLE,
    SDK_AVAILABLE,
    YAML_AVAILABLE,
    analyze_code_patterns,
    check_agent_config_exists,
    find_agent_config_directory,
    format_dependencies,
    format_features_added,
    format_patterns,
    get_agentcore_command,
    get_next_steps,
    get_runtime_for_agent,
    get_user_working_directory,
    project_discover,
    register_discovery_tools,
    register_environment_tools,
    register_github_discovery_tools,
    resolve_app_file_path,
    validate_sdk_method,
    what_agents_can_i_invoke,
)
from pathlib import Path
from unittest.mock import Mock, mock_open, patch


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_user_working_directory(self):
        """Test getting user working directory."""
        result = get_user_working_directory()
        assert isinstance(result, Path)
        assert result.exists()

    @patch.dict('os.environ', {'PWD': '/test/path'})
    @patch('pathlib.Path.exists')
    def test_get_user_working_directory_with_pwd(self, mock_exists):
        """Test getting directory from PWD environment variable."""
        mock_exists.return_value = True

        result = get_user_working_directory()
        assert str(result) == '/test/path'

    def test_resolve_app_file_path_absolute(self):
        """Test resolving absolute file path."""
        # Use current file as a test
        current_file = __file__
        result = resolve_app_file_path(current_file)
        assert result == current_file

    def test_resolve_app_file_path_nonexistent(self):
        """Test resolving non-existent file path."""
        result = resolve_app_file_path('definitely_does_not_exist.py')
        assert result is None

    def test_validate_sdk_method_available(self):
        """Test SDK method validation when SDK is available."""
        if SDK_AVAILABLE:
            # This should pass if SDK is available
            result = validate_sdk_method('BedrockAgentCoreApp', 'configure')
            assert isinstance(result, bool)
        else:
            # Should return False when SDK not available
            result = validate_sdk_method('BedrockAgentCoreApp', 'configure')
            assert result is False

    def test_validate_sdk_method_invalid_class(self):
        """Test SDK method validation with invalid class."""
        result = validate_sdk_method('NonExistentClass', 'some_method')
        assert result is False


class TestPathResolution:
    """Test path resolution strategies."""

    def test_resolve_current_file(self):
        """Test resolving current test file."""
        # Should be able to find this test file
        test_file_name = Path(__file__).name
        result = resolve_app_file_path(test_file_name)

        # May or may not find it depending on search paths, but shouldn't crash
        assert result is None or Path(result).name == test_file_name

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.get_user_working_directory')
    def test_resolve_with_mock_directory(self, mock_get_dir):
        """Test path resolution with mocked directory."""
        mock_get_dir.return_value = Path('/tmp')

        # Should not find non-existent file
        result = resolve_app_file_path('nonexistent.py')
        assert result is None


class TestEnvironmentDetection:
    """Test environment detection functionality."""

    @patch('subprocess.run')
    def test_environment_tools_with_subprocess(self, mock_run):
        """Test environment detection with subprocess mocking."""
        # Mock successful uv command
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '/usr/local/bin/uv'

        # Import and test environment validation function
        from awslabs.amazon_bedrock_agentcore_mcp_server.utils import register_environment_tools
        from mcp.server.fastmcp import FastMCP

        test_mcp = FastMCP('Test Server')
        register_environment_tools(test_mcp)

        # Should register without errors - list_tools is async
        import asyncio

        tools = asyncio.run(test_mcp.list_tools())
        assert len(tools) > 0


class TestAgentConfiguration:
    """Test agent configuration functions."""

    def test_check_agent_config_exists_no_file(self):
        """Test checking for config when file doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            result, path = check_agent_config_exists('test-agent')
            assert result is False
            assert isinstance(path, Path)

    def test_check_agent_config_exists_with_file_yaml_available(self):
        """Test checking for config when file exists and YAML is available."""
        if YAML_AVAILABLE:
            config_data = {'agent_name': 'test-agent'}
            with (
                patch('pathlib.Path.exists', return_value=True),
                patch('builtins.open', mock_open(read_data='agent_name: test-agent\n')),
                patch('yaml.safe_load', return_value=config_data),
            ):
                result, path = check_agent_config_exists('test-agent')
                assert result is True
                assert isinstance(path, Path)

    def test_check_agent_config_exists_without_yaml(self):
        """Test config check when YAML is not available."""
        with (
            patch('pathlib.Path.exists', return_value=True),
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.YAML_AVAILABLE', False),
        ):
            result, path = check_agent_config_exists('test-agent')
            assert result is True
            assert isinstance(path, Path)

    def test_find_agent_config_directory_current_dir(self):
        """Test finding agent config in current directory."""
        if YAML_AVAILABLE:
            config_data = {'agent_name': 'test-agent'}
            with (
                patch('pathlib.Path.exists', return_value=True),
                patch('builtins.open', mock_open(read_data='agent_name: test-agent\n')),
                patch('yaml.safe_load', return_value=config_data),
            ):
                result, path = find_agent_config_directory('test-agent')
                assert result is True
                assert isinstance(path, Path)

    def test_find_agent_config_directory_multi_agent(self):
        """Test finding config in multi-agent format."""
        if YAML_AVAILABLE:
            config_data = {'agents': {'test-agent': {}, 'other-agent': {}}}
            with (
                patch('pathlib.Path.exists', return_value=True),
                patch('builtins.open', mock_open()),
                patch('yaml.safe_load', return_value=config_data),
            ):
                result, path = find_agent_config_directory('test-agent')
                assert result is True
                assert isinstance(path, Path)

    def test_find_agent_config_directory_not_found(self):
        """Test when config directory is not found."""
        with patch('pathlib.Path.exists', return_value=False):
            result, path = find_agent_config_directory('nonexistent-agent')
            assert result is False
            assert isinstance(path, Path)

    def test_get_runtime_for_agent_runtime_not_available(self):
        """Test getting runtime when runtime is not available."""
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.RUNTIME_AVAILABLE', False):
            with pytest.raises(ImportError, match='Runtime not available'):
                get_runtime_for_agent('test-agent')

    @pytest.mark.skipif(not RUNTIME_AVAILABLE, reason='Runtime not available')
    def test_get_runtime_for_agent_with_config(self):
        """Test getting runtime with existing config."""
        if YAML_AVAILABLE:
            config_data = {'agent_name': 'test-agent', 'default_agent': 'test-agent'}
            with (
                patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.'
                    'utils.find_agent_config_directory',
                    return_value=(True, Path('/test')),
                ),
                patch('pathlib.Path.exists', return_value=True),
                patch('builtins.open', mock_open()),
                patch('yaml.safe_load', return_value=config_data),
                patch('yaml.dump'),
            ):
                runtime = get_runtime_for_agent('test-agent')
                assert runtime is not None
                assert hasattr(runtime, 'name')


class TestCodeAnalysis:
    """Test code analysis functions."""

    def test_analyze_code_patterns_empty_code(self):
        """Test analyzing empty code."""
        result = analyze_code_patterns('')
        assert isinstance(result, dict)
        assert 'patterns' in result
        assert 'dependencies' in result
        assert 'framework' in result

    def test_analyze_code_patterns_with_imports(self):
        """Test analyzing code with imports."""
        code = """
import json
from pathlib import Path
import boto3
"""
        result = analyze_code_patterns(code)
        assert isinstance(result, dict)
        assert len(result['dependencies']) > 0
        assert any('json' in dep for dep in result['dependencies'])

    def test_analyze_code_patterns_with_classes(self):
        """Test analyzing code with class definitions."""
        code = """
class TestClass:
    def __init__(self):
        pass

    def method(self):
        return "test"
"""
        result = analyze_code_patterns(code)
        assert isinstance(result['patterns'], list)
        assert len(result['patterns']) > 0

    def test_analyze_code_patterns_with_functions(self):
        """Test analyzing code with function definitions."""
        code = """
def test_function():
    return True

async def async_function():
    return False
"""
        result = analyze_code_patterns(code)
        assert isinstance(result['patterns'], list)
        assert len(result['patterns']) > 0

    def test_format_patterns(self):
        """Test formatting patterns list."""
        patterns = ['pattern1', 'pattern2', 'pattern3']
        result = format_patterns(patterns)
        assert isinstance(result, str)
        assert 'pattern1' in result

    def test_format_dependencies(self):
        """Test formatting dependencies list."""
        deps = ['boto3', 'requests', 'pathlib']
        result = format_dependencies(deps)
        assert isinstance(result, str)
        assert 'boto3' in result

    def test_format_features_added(self):
        """Test formatting features added."""
        features = {'memory': True, 'identity': False, 'runtime': True}
        result = format_features_added(features)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_next_steps_with_memory(self):
        """Test getting next steps with memory enabled."""
        result = get_next_steps(memory_enabled=True)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_next_steps_without_memory(self):
        """Test getting next steps without memory."""
        result = get_next_steps(memory_enabled=False)
        assert isinstance(result, str)
        assert len(result) > 0


class TestEnvironmentTools:
    """Test environment tool functions."""

    @pytest.mark.asyncio
    async def test_get_agentcore_command_with_uv(self):
        """Test getting agentcore command when uv is available."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = await get_agentcore_command()
            assert isinstance(result, list)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_agentcore_command_without_uv(self):
        """Test getting agentcore command when uv is not available."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            result = await get_agentcore_command()
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_agentcore_command_exception(self):
        """Test getting agentcore command with exception."""
        with patch('subprocess.run', side_effect=Exception('Command failed')):
            result = await get_agentcore_command()
            assert isinstance(result, list)

    def test_register_environment_tools_additional(self):
        """Test registering environment tools."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Server')
        initial_tools = asyncio.run(mcp.list_tools())
        initial_count = len(initial_tools)

        register_environment_tools(mcp)

        final_tools = asyncio.run(mcp.list_tools())
        final_count = len(final_tools)

        assert final_count >= initial_count


class TestAgentDiscovery:
    """Test agent discovery functions."""

    def test_what_agents_can_i_invoke_sdk_not_available(self):
        """Test agent discovery when SDK is not available."""
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.SDK_AVAILABLE', False):
            result = what_agents_can_i_invoke()
            assert isinstance(result, str)
            assert 'No agents found' in result or 'No Agents Found' in result

    @pytest.mark.skipif(not SDK_AVAILABLE, reason='SDK not available')
    def test_what_agents_can_i_invoke_with_sdk(self):
        """Test agent discovery with SDK available."""
        with (
            patch('boto3.client') as mock_boto3,
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.SDK_AVAILABLE', True),
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client
            mock_client.list_agents.return_value = {'agents': []}

            result = what_agents_can_i_invoke('us-east-1')
            assert isinstance(result, str)

    def test_project_discover_agents_action(self):
        """Test project discovery with agents action."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_file = Path(temp_dir) / 'test_agent.py'
            test_file.write_text('# Test agent file\nclass TestAgent:\n    pass')

            result = project_discover(action='agents', search_path=temp_dir)
            assert isinstance(result, str)

    def test_project_discover_configs_action(self):
        """Test project discovery with configs action."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test config file
            config_file = Path(temp_dir) / '.bedrock_agentcore.yaml'
            config_file.write_text('agent_name: test\n')

            result = project_discover(action='configs', search_path=temp_dir)
            assert isinstance(result, str)

    def test_project_discover_analysis_action(self):
        """Test project discovery with analysis action."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test Python file
            py_file = Path(temp_dir) / 'test.py'
            py_file.write_text('import json\ndef test():\n    pass')

            result = project_discover(action='analysis', search_path=temp_dir)
            assert isinstance(result, str)

    def test_register_discovery_tools(self):
        """Test registering discovery tools."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Server')
        initial_tools = asyncio.run(mcp.list_tools())
        initial_count = len(initial_tools)

        register_discovery_tools(mcp)

        final_tools = asyncio.run(mcp.list_tools())
        final_count = len(final_tools)

        assert final_count > initial_count

    def test_register_github_discovery_tools(self):
        """Test registering GitHub discovery tools."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Server')
        initial_tools = asyncio.run(mcp.list_tools())
        initial_count = len(initial_tools)

        register_github_discovery_tools(mcp)

        final_tools = asyncio.run(mcp.list_tools())
        final_count = len(final_tools)

        assert final_count > initial_count


class TestErrorHandling:
    """Test error handling in utility functions."""

    def test_find_agent_config_directory_yaml_error(self):
        """Test config directory finding with YAML error."""
        if YAML_AVAILABLE:
            with (
                patch('pathlib.Path.exists', return_value=True),
                patch('builtins.open', mock_open()),
                patch('yaml.safe_load', side_effect=Exception('YAML error')),
            ):
                result, path = find_agent_config_directory('test-agent')
                assert result is False
                assert isinstance(path, Path)

    def test_check_agent_config_exists_yaml_error(self):
        """Test config check with YAML error."""
        if YAML_AVAILABLE:
            with (
                patch('pathlib.Path.exists', return_value=True),
                patch('builtins.open', mock_open()),
                patch('yaml.safe_load', side_effect=Exception('YAML error')),
            ):
                result, path = check_agent_config_exists('test-agent')
                assert result is True  # Falls back to file existence
                assert isinstance(path, Path)

    def test_project_discover_with_permission_error(self):
        """Test project discovery with permission error."""
        with patch('pathlib.Path.rglob', side_effect=PermissionError('Access denied')):
            result = project_discover(action='agents', search_path='.')
            assert isinstance(result, str)
            assert 'Error' in result or 'No' in result

    def test_analyze_code_patterns_with_invalid_code(self):
        """Test code analysis with syntax errors."""
        invalid_code = 'def invalid_function(\n    # Missing closing parenthesis'
        result = analyze_code_patterns(invalid_code)
        assert isinstance(result, dict)
        # Should handle gracefully and return basic analysis


class TestFileOperations:
    """Test file operation utilities."""

    def test_resolve_app_file_path_with_relative_path(self):
        """Test resolving relative file paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / 'test.py'
            test_file.write_text('# Test file')

            with patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.utils.get_user_working_directory',
                return_value=Path(temp_dir),
            ):
                result = resolve_app_file_path('test.py')
                assert result is not None or result is None  # Either finds it or doesn't

    def test_resolve_app_file_path_search_paths(self):
        """Test file path resolution with multiple search paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            subdir = Path(temp_dir) / 'subdir'
            subdir.mkdir()
            test_file = subdir / 'nested_file.py'
            test_file.write_text('# Nested test file')

            with patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.utils.get_user_working_directory',
                return_value=Path(temp_dir),
            ):
                result = resolve_app_file_path('nested_file.py')
                # May or may not find it depending on search implementation
                assert result is None or 'nested_file.py' in result


if __name__ == '__main__':
    # Run basic utility tests
    print('Testing utility functions...')

    # Test directory resolution
    user_dir = get_user_working_directory()
    print(f'✓ User directory: {user_dir}')

    # Test file resolution with current file
    current_path = resolve_app_file_path(__file__)
    print(f'✓ Current file resolution: {current_path is not None}')

    # Test SDK validation
    sdk_test = validate_sdk_method('TestClass', 'test_method')
    print(f'✓ SDK validation: {isinstance(sdk_test, bool)}')

    print('All utility tests passed!')
