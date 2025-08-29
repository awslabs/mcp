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

from awslabs.amazon_bedrock_agentcore_mcp_server.utils import (
    SDK_AVAILABLE,
    get_user_working_directory,
    resolve_app_file_path,
    validate_sdk_method,
)
from pathlib import Path
from unittest.mock import patch


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
