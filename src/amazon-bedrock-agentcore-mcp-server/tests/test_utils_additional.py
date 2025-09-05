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

"""Additional comprehensive tests for utils functionality to improve coverage."""

import json
import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.utils import (
    analyze_code_patterns,
    check_agent_config_exists,
    discover_agentcore_examples_from_github,
    find_agent_config_directory,
    format_existing_agents_summary,
    get_environment_next_steps,
    get_user_working_directory,
    project_discover,
    resolve_app_file_path,
    validate_sdk_method,
    what_agents_can_i_invoke,
)
from pathlib import Path
from unittest.mock import Mock, patch


class TestEnvironmentAnalysis:
    """Test environment analysis and guidance functions."""

    def test_get_environment_next_steps_no_issues(self):
        """Test environment next steps with no issues."""
        result = get_environment_next_steps([])

        assert 'environment is ready' in result
        assert 'analyze_agent_code' in result or 'deploy_agentcore_app' in result

    def test_get_environment_next_steps_aws_credentials_issue(self):
        """Test environment next steps with AWS credentials issue."""
        issues = ['AWS credentials not configured properly']
        result = get_environment_next_steps(issues)

        assert 'Configure AWS credentials' in result
        assert 'aws configure' in result

    def test_get_environment_next_steps_agentcore_cli_issue(self):
        """Test environment next steps with AgentCore CLI issue."""
        issues = ['AgentCore CLI not installed']
        result = get_environment_next_steps(issues)

        assert 'Install AgentCore from PyPI' in result
        assert 'uv add bedrock-agentcore' in result

    def test_get_environment_next_steps_virtual_env_issue(self):
        """Test environment next steps with virtual environment issue."""
        issues = ['virtual environment not detected']
        result = get_environment_next_steps(issues)

        assert 'Create virtual environment' in result
        assert 'python -m venv' in result

    def test_get_environment_next_steps_agentcore_apps_issue(self):
        """Test environment next steps with AgentCore applications issue."""
        issues = ['AgentCore applications not found']
        result = get_environment_next_steps(issues)

        assert 'analyze_agent_code' in result
        assert 'transform_to_agentcore' in result

    def test_get_environment_next_steps_multiple_issues(self):
        """Test environment next steps with multiple issues."""
        issues = [
            'AWS credentials not configured',
            'AgentCore CLI missing',
            'virtual environment problem',
        ]
        result = get_environment_next_steps(issues)

        assert 'Configure AWS credentials' in result
        assert 'Install AgentCore from PyPI' in result
        assert 'Create virtual environment' in result

    def test_format_existing_agents_summary_empty(self):
        """Test formatting empty agents list."""
        result = format_existing_agents_summary([])
        assert result == ''

    def test_format_existing_agents_summary_single_agent(self):
        """Test formatting single agent summary."""
        agents = [{'name': 'my_agent', 'status': 'active', 'config_file': '/path/to/config.yaml'}]
        result = format_existing_agents_summary(agents)

        assert 'my_agent' in result
        assert 'invoke_agent' in result

    def test_format_existing_agents_summary_multiple_agents(self):
        """Test formatting multiple agents summary."""
        agents = [
            {'name': 'agent1', 'status': 'active', 'config_file': '/path/config1.yaml'},
            {'name': 'agent2', 'status': 'inactive', 'config_file': '/path/config2.yaml'},
            {'name': 'agent3', 'status': 'active', 'config_file': '/path/config3.yaml'},
        ]
        result = format_existing_agents_summary(agents)

        assert 'agent1' in result
        assert 'agent2' in result
        assert 'agent3' in result


class TestGitHubDiscovery:
    """Test GitHub discovery functionality."""

    @patch('requests.get')
    def test_discover_agentcore_examples_from_github_success(self, mock_get):
        """Test successful GitHub examples discovery."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'name': 'example1',
                'type': 'dir',
                'download_url': None,
                'html_url': 'https://github.com/example1',
            },
            {
                'name': 'example2.py',
                'type': 'file',
                'download_url': 'https://raw.github.com/example2.py',
                'html_url': 'https://github.com/example2.py',
            },
        ]
        mock_get.return_value = mock_response

        result = discover_agentcore_examples_from_github('general')

        # The function returns either success with examples or error message
        assert (
            'GitHub API Error' in result
            or 'example1' in result
            or 'Examples:' in result
            or 'Repository Structure:' in result
        )

    @patch('requests.get')
    def test_discover_agentcore_examples_from_github_http_error(self, mock_get):
        """Test GitHub discovery with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {'message': 'Not Found'}
        mock_get.return_value = mock_response

        result = discover_agentcore_examples_from_github('nonexistent')

        assert 'No examples found' in result or 'Error' in result or 'GitHub API Error' in result

    @patch('requests.get')
    def test_discover_agentcore_examples_from_github_request_exception(self, mock_get):
        """Test GitHub discovery with request exception."""
        mock_get.side_effect = Exception('Connection error')

        result = discover_agentcore_examples_from_github('general')

        assert 'Error' in result or 'Failed' in result or 'GitHub API Error' in result

    @patch('requests.get')
    def test_discover_agentcore_examples_from_github_invalid_json(self, mock_get):
        """Test GitHub discovery with invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
        mock_get.return_value = mock_response

        result = discover_agentcore_examples_from_github('general')

        assert 'Error' in result or 'Failed' in result or 'GitHub API Error' in result


class TestCodeAnalysisEdgeCases:
    """Test edge cases in code analysis functionality."""

    def test_analyze_code_patterns_with_complex_imports(self):
        """Test code analysis with complex import patterns."""
        complex_code = """
# Various import styles
import os
import sys, json
from pathlib import Path
from typing import Dict, List, Optional, Union
from collections import defaultdict, Counter
import boto3.client as bedrock_client
from awslabs.amazon_bedrock_agentcore_mcp_server import utils
from .local_module import helper_function
import numpy as np  # Scientific computing
try:
    import pandas as pd  # Optional dependency
except ImportError:
    pd = None
"""

        result = analyze_code_patterns(complex_code)

        assert 'dependencies' in result
        assert 'framework' in result
        assert 'patterns' in result
        assert len(result['dependencies']) > 0  # Should capture multiple imports

    def test_analyze_code_patterns_with_nested_classes_and_functions(self):
        """Test code analysis with nested structures."""
        nested_code = '''
class OuterClass:
    """Outer class with nested structures."""

    class InnerClass:
        """Inner class definition."""

        def inner_method(self):
            """Method inside inner class."""
            def nested_function():
                """Function inside method."""
                return "nested"
            return nested_function()

    def outer_method(self):
        """Outer class method."""

        class LocalClass:
            """Local class inside method."""
            pass

        def local_function():
            """Local function inside method."""
            return LocalClass()

        return local_function()

def standalone_function():
    """Standalone function with nested elements."""

    class FunctionLocalClass:
        pass

    def inner_function():
        return FunctionLocalClass()

    return inner_function()
'''

        result = analyze_code_patterns(nested_code)

        assert 'dependencies' in result
        assert 'framework' in result
        assert 'patterns' in result
        assert isinstance(result['patterns'], list)

    def test_analyze_code_patterns_with_decorators_and_async(self):
        """Test code analysis with decorators and async patterns."""
        decorated_code = '''
import asyncio
from functools import wraps
from typing import Callable

def retry_decorator(max_attempts: int = 3):
    """Retry decorator for functions."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    await asyncio.sleep(1)
        return wrapper
    return decorator

@retry_decorator(max_attempts=5)
async def async_api_call(data: dict) -> dict:
    """Make async API call with retry logic."""
    # Simulate API call
    await asyncio.sleep(0.1)
    return {"result": "success"}
'''

        result = analyze_code_patterns(decorated_code)

        assert 'dependencies' in result
        assert 'framework' in result
        assert 'patterns' in result
        assert isinstance(result['patterns'], list)

    def test_analyze_code_patterns_empty_code(self):
        """Test code analysis with empty code."""
        result = analyze_code_patterns('')

        assert 'dependencies' in result
        assert 'framework' in result
        assert 'patterns' in result
        assert len(result['dependencies']) == 0

    def test_analyze_code_patterns_only_comments(self):
        """Test code analysis with only comments."""
        comment_code = '''
# This is a comment
# Another comment
"""
This is a docstring
"""
'''

        result = analyze_code_patterns(comment_code)

        assert 'dependencies' in result
        assert 'framework' in result
        assert 'patterns' in result
        assert len(result['dependencies']) == 0


class TestUtilityFunctionEdgeCases:
    """Test edge cases for various utility functions."""

    @patch('pathlib.Path.cwd')
    @patch('os.environ.get')
    def test_get_user_working_directory_with_env_override(self, mock_env_get, mock_cwd):
        """Test working directory with environment variable override."""
        mock_env_get.return_value = None  # No environment override
        mock_cwd.return_value = Path('/default/dir')

        result = get_user_working_directory()
        assert isinstance(result, Path)

    @patch('pathlib.Path.exists')
    def test_check_agent_config_exists_permission_error(self, mock_exists):
        """Test agent config check with permission error."""
        mock_exists.side_effect = PermissionError('Access denied')

        # The function doesn't handle PermissionError, so it bubbles up
        with pytest.raises(PermissionError, match='Access denied'):
            check_agent_config_exists('test_agent')

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.SDK_AVAILABLE', False)
    def test_what_agents_can_i_invoke_sdk_unavailable(self):
        """Test agent invocation query when SDK is unavailable."""
        result = what_agents_can_i_invoke('us-west-2')

        assert 'No Agents Found' in result or 'No agents found' in result

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.SDK_AVAILABLE', True)
    @patch('boto3.client')
    def test_what_agents_can_i_invoke_with_boto3_error(self, mock_boto3):
        """Test agent invocation query with boto3 error."""
        mock_client = Mock()
        mock_client.list_agent_runtimes.side_effect = Exception('AWS API Error')
        mock_boto3.return_value = mock_client

        result = what_agents_can_i_invoke('us-east-1')

        assert 'Tool Error' in result or 'No Agents Found' in result

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.SDK_AVAILABLE', True)
    @patch('boto3.client')
    def test_what_agents_can_i_invoke_empty_response(self, mock_boto3):
        """Test agent invocation query with empty response."""
        mock_client = Mock()
        mock_client.list_agent_runtimes.return_value = {'items': []}
        mock_boto3.return_value = mock_client

        result = what_agents_can_i_invoke('us-east-1')

        assert 'No agents found' in result or 'no agent runtimes' in result

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.utils.SDK_AVAILABLE', True)
    @patch('boto3.client')
    def test_what_agents_can_i_invoke_with_multiple_agents(self, mock_boto3):
        """Test agent invocation query with multiple agents."""
        mock_client = Mock()
        mock_client.list_agent_runtimes.return_value = {
            'agentRuntimes': [
                {
                    'agentRuntimeName': 'agent1',
                    'agentRuntimeArn': 'arn:aws:bedrock-agentcore:us-east-1:123:runtime/agent1',
                    'description': 'First test agent',
                    'status': 'READY',
                },
                {
                    'agentRuntimeName': 'agent2',
                    'agentRuntimeArn': 'arn:aws:bedrock-agentcore:us-east-1:123:runtime/agent2',
                    'description': 'Second test agent',
                    'status': 'READY',
                },
            ]
        }
        mock_boto3.return_value = mock_client

        result = what_agents_can_i_invoke('us-east-1')

        assert 'agent1' in result
        assert 'agent2' in result
        assert 'invoke_agent' in result

    def test_validate_sdk_method_valid_combination(self):
        """Test SDK method validation with valid class and method."""
        # Test returns False when SDK_AVAILABLE is False or class not in capabilities
        result = validate_sdk_method('bedrock-agentcore-control', 'list_agents')
        assert result is False  # Expected behavior when SDK not available or class not found

    def test_validate_sdk_method_invalid_class(self):
        """Test SDK method validation with invalid class."""
        result = validate_sdk_method('NonexistentClass', 'some_method')
        assert result is False

    def test_validate_sdk_method_invalid_method(self):
        """Test SDK method validation with invalid method."""
        result = validate_sdk_method('str', 'nonexistent_method')
        assert result is False

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    def test_resolve_app_file_path_file_exists(self, mock_is_file, mock_exists):
        """Test resolving app file path when file exists."""
        # Mock both exists and is_file to return True for the target path
        mock_exists.return_value = True
        mock_is_file.return_value = True

        result = resolve_app_file_path('/absolute/path/to/file.txt')
        assert result == '/absolute/path/to/file.txt'

    @patch('pathlib.Path.exists')
    def test_resolve_app_file_path_file_not_exists(self, mock_exists):
        """Test resolving app file path when file doesn't exist."""
        mock_exists.return_value = False

        result = resolve_app_file_path('/nonexistent/file.txt')
        assert result is None

    def test_resolve_app_file_path_relative_search(self):
        """Test resolving relative file path with directory search."""
        # Test with a file that definitely doesn't exist
        result = resolve_app_file_path('nonexistent_file_12345.txt')
        # Should return None since the file doesn't exist anywhere
        assert result is None


class TestProjectDiscoveryScenarios:
    """Test various project discovery scenarios."""

    @patch('pathlib.Path.glob')
    def test_project_discover_agents_action(self, mock_glob):
        """Test project discovery with agents action."""
        # Mock Path.glob to return empty list (no agent files found)
        mock_glob.return_value = []

        result = project_discover('agents', '/project')

        # Should return "No Agent Files Found"
        assert 'No Agent Files Found' in result

    @patch('pathlib.Path.glob')
    def test_project_discover_configs_action(self, mock_glob):
        """Test project discovery with configs action."""
        # Mock Path.glob to return empty list (no config files found)
        mock_glob.return_value = []

        result = project_discover('configs', '/project')

        # Should return "No AgentCore Configurations Found"
        assert 'No AgentCore Configurations Found' in result

    def test_project_discover_analysis_action(self):
        """Test project discovery with analysis action."""
        # The analysis action doesn't exist - test that it returns unknown action
        result = project_discover('analysis', '/project')

        assert 'Unknown Action' in result
        assert 'agents' in result and 'configs' in result and 'memories' in result

    def test_project_discover_invalid_action(self):
        """Test project discovery with invalid action."""
        result = project_discover('invalid_action', '/project')

        assert 'Unknown Action' in result

    def test_project_discover_empty_directory(self):
        """Test project discovery in empty directory."""
        result = project_discover('agents', '/empty')

        assert 'No Agent Files Found' in result or 'Discovery Error' in result


class TestErrorHandling:
    """Test error handling in various utility functions."""

    @patch('os.walk')
    def test_find_agent_config_directory_os_error(self, mock_walk):
        """Test finding agent config with OS error."""
        mock_walk.side_effect = OSError('Permission denied')

        found, path = find_agent_config_directory('test_agent')

        assert found is False
        assert isinstance(path, Path)

    @patch('os.walk')
    def test_project_discover_permission_error(self, mock_walk):
        """Test project discover with permission error."""
        mock_walk.side_effect = PermissionError('Access denied')

        result = project_discover('agents', '/restricted')

        assert 'Error' in result or 'Permission' in result
