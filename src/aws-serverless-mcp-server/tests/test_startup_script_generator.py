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
"""Tests for the startup_script_generator module."""

import os
import pytest
import stat
from awslabs.aws_serverless_mcp_server.tools.webapps.utils.startup_script_generator import (
    EntryPointNotFoundError,
    generate_script_content,
    generate_startup_script,
    get_default_startup_script_name,
)
from unittest.mock import MagicMock, mock_open, patch


class TestStartupScriptGenerator:
    """Tests for the startup_script_generator module."""

    def test_entry_point_not_found_error(self):
        """Test EntryPointNotFoundError initialization."""
        entry_point = 'app.js'
        built_artifacts_path = '/dir/artifacts'

        error = EntryPointNotFoundError(entry_point, built_artifacts_path)

        assert error.entry_point == entry_point
        assert error.built_artifacts_path == built_artifacts_path
        assert error.name == 'EntryPointNotFoundError'
        expected_message = (
            f'Entry point file not found: {os.path.join(built_artifacts_path, entry_point)}'
        )
        assert str(error) == expected_message

    def test_get_default_startup_script_name(self):
        """Test get_default_startup_script_name for various runtimes."""
        # All runtimes should return 'bootstrap'
        runtimes = ['nodejs18.x', 'python3.9', 'java11', 'dotnet6', 'go1.x', 'ruby3.2']

        for runtime in runtimes:
            result = get_default_startup_script_name(runtime)
            assert result == 'bootstrap'

    def test_generate_script_content_nodejs(self):
        """Test generate_script_content for Node.js runtime."""
        runtime = 'nodejs18.x'
        entry_point = 'app.js'

        result = generate_script_content(runtime, entry_point)

        expected = """#!/bin/bash
# Start the application
exec node app.js
"""
        assert result == expected

    def test_generate_script_content_nodejs_with_env(self):
        """Test generate_script_content for Node.js with environment variables."""
        runtime = 'nodejs18.x'
        entry_point = 'server.js'
        additional_env = {'NODE_ENV': 'production', 'PORT': '3000'}

        result = generate_script_content(runtime, entry_point, additional_env)

        expected = """#!/bin/bash
export NODE_ENV="production"
export PORT="3000"

# Start the application
exec node server.js
"""
        assert result == expected

    def test_generate_script_content_python(self):
        """Test generate_script_content for Python runtime."""
        runtime = 'python3.9'
        entry_point = 'app.py'

        result = generate_script_content(runtime, entry_point)

        expected = """#!/bin/bash
# Start the application
exec python app.py
"""
        assert result == expected

    def test_generate_script_content_python_with_env(self):
        """Test generate_script_content for Python with environment variables."""
        runtime = 'python3.11'
        entry_point = 'main.py'
        additional_env = {'PYTHONPATH': '/app', 'DEBUG': 'true'}

        result = generate_script_content(runtime, entry_point, additional_env)

        expected = """#!/bin/bash
export PYTHONPATH="/app"
export DEBUG="true"

# Start the application
exec python main.py
"""
        assert result == expected

    def test_generate_script_content_java_jar(self):
        """Test generate_script_content for Java JAR file."""
        runtime = 'java11'
        entry_point = 'app.jar'

        result = generate_script_content(runtime, entry_point)

        expected = """#!/bin/bash
# Start the application
exec java -jar app.jar
"""
        assert result == expected

    def test_generate_script_content_java_class(self):
        """Test generate_script_content for Java class."""
        runtime = 'java17'
        entry_point = 'com.example.App'

        result = generate_script_content(runtime, entry_point)

        expected = """#!/bin/bash
# Start the application
exec java com.example.App
"""
        assert result == expected

    def test_generate_script_content_dotnet(self):
        """Test generate_script_content for .NET runtime."""
        runtime = 'dotnet6'
        entry_point = 'app.dll'

        result = generate_script_content(runtime, entry_point)

        expected = """#!/bin/bash
# Start the application
exec dotnet app.dll
"""
        assert result == expected

    def test_generate_script_content_go(self):
        """Test generate_script_content for Go runtime."""
        runtime = 'go1.x'
        entry_point = 'main'

        result = generate_script_content(runtime, entry_point)

        expected = """#!/bin/bash
# Start the application
exec ./main
"""
        assert result == expected

    def test_generate_script_content_ruby(self):
        """Test generate_script_content for Ruby runtime."""
        runtime = 'ruby3.2'
        entry_point = 'app.rb'

        result = generate_script_content(runtime, entry_point)

        expected = """#!/bin/bash
# Start the application
exec ruby app.rb
"""
        assert result == expected

    def test_generate_script_content_unknown_runtime(self):
        """Test generate_script_content for unknown runtime."""
        runtime = 'unknown-runtime'
        entry_point = 'start.sh'

        result = generate_script_content(runtime, entry_point)

        expected = """#!/bin/bash
# Start the application
exec start.sh
"""
        assert result == expected

    @pytest.mark.asyncio
    async def test_generate_startup_script_success(self):
        """Test successful generate_startup_script."""
        runtime = 'nodejs18.x'
        entry_point = 'app.js'
        built_artifacts_path = '/dir/artifacts'

        mock_file = mock_open()
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o644

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_file),
            patch('os.stat', return_value=mock_stat_result),
            patch('os.chmod') as mock_chmod,
        ):
            result = await generate_startup_script(runtime, entry_point, built_artifacts_path)

            assert result == 'bootstrap'

            # Verify file was written
            mock_file.assert_called_once_with('/dir/artifacts/bootstrap', 'w', encoding='utf-8')

            # Verify script content was written
            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            expected_content = """#!/bin/bash
# Start the application
exec node app.js
"""
            assert written_content == expected_content

            # Verify file was made executable
            mock_chmod.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_startup_script_custom_name(self):
        """Test generate_startup_script with custom script name."""
        runtime = 'python3.9'
        entry_point = 'app.py'
        built_artifacts_path = '/dir/artifacts'
        startup_script_name = 'start.sh'

        mock_file = mock_open()
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o644

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_file),
            patch('os.stat', return_value=mock_stat_result),
            patch('os.chmod'),
        ):
            result = await generate_startup_script(
                runtime, entry_point, built_artifacts_path, startup_script_name
            )

            assert result == 'start.sh'
            mock_file.assert_called_once_with('/dir/artifacts/start.sh', 'w', encoding='utf-8')

    @pytest.mark.asyncio
    async def test_generate_startup_script_with_env_vars(self):
        """Test generate_startup_script with additional environment variables."""
        runtime = 'nodejs18.x'
        entry_point = 'server.js'
        built_artifacts_path = '/dir/artifacts'
        additional_env = {'NODE_ENV': 'production', 'PORT': '8080'}

        mock_file = mock_open()
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o644

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_file),
            patch('os.stat', return_value=mock_stat_result),
            patch('os.chmod'),
        ):
            result = await generate_startup_script(
                runtime, entry_point, built_artifacts_path, additional_env=additional_env
            )

            assert result == 'bootstrap'

            # Verify script content includes environment variables
            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            assert 'export NODE_ENV="production"' in written_content
            assert 'export PORT="8080"' in written_content

    @pytest.mark.asyncio
    async def test_generate_startup_script_entry_point_not_found(self):
        """Test generate_startup_script with non-existent entry point."""
        runtime = 'nodejs18.x'
        entry_point = 'nonexistent.js'
        built_artifacts_path = '/dir/artifacts'

        with (
            patch('os.path.exists', return_value=False),
            patch('os.listdir', return_value=['app.js', 'package.json']),
        ):
            with pytest.raises(EntryPointNotFoundError) as exc_info:
                await generate_startup_script(runtime, entry_point, built_artifacts_path)

            error = exc_info.value
            assert error.entry_point == entry_point
            assert error.built_artifacts_path == built_artifacts_path

    @pytest.mark.asyncio
    async def test_generate_startup_script_entry_point_not_found_empty_dir(self):
        """Test generate_startup_script with non-existent entry point in empty directory."""
        runtime = 'python3.9'
        entry_point = 'app.py'
        built_artifacts_path = '/dir/empty'

        with (
            patch('os.path.exists', return_value=False),
            patch('os.listdir', return_value=[]),
        ):
            with pytest.raises(EntryPointNotFoundError):
                await generate_startup_script(runtime, entry_point, built_artifacts_path)

    @pytest.mark.asyncio
    async def test_generate_startup_script_entry_point_not_found_listdir_error(self):
        """Test generate_startup_script with listdir error."""
        runtime = 'nodejs18.x'
        entry_point = 'app.js'
        built_artifacts_path = '/dir/artifacts'

        with (
            patch('os.path.exists', return_value=False),
            patch('os.listdir', side_effect=OSError('Permission denied')),
        ):
            with pytest.raises(EntryPointNotFoundError):
                await generate_startup_script(runtime, entry_point, built_artifacts_path)

    @pytest.mark.asyncio
    async def test_generate_startup_script_chmod_permissions(self):
        """Test generate_startup_script sets correct file permissions."""
        runtime = 'python3.9'
        entry_point = 'app.py'
        built_artifacts_path = '/dir/artifacts'

        mock_file = mock_open()
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o644  # Initial file permissions

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_file),
            patch('os.stat', return_value=mock_stat_result),
            patch('os.chmod') as mock_chmod,
        ):
            await generate_startup_script(runtime, entry_point, built_artifacts_path)

            # Verify chmod was called with executable permissions
            mock_chmod.assert_called_once()
            args = mock_chmod.call_args[0]
            script_path = args[0]
            permissions = args[1]

            assert script_path == '/dir/artifacts/bootstrap'
            # Check that executable bits are set
            assert permissions & stat.S_IXUSR  # Owner execute
            assert permissions & stat.S_IXGRP  # Group execute
            assert permissions & stat.S_IXOTH  # Other execute

    def test_generate_script_content_environment_variable_escaping(self):
        """Test that environment variables are properly escaped in script content."""
        runtime = 'nodejs18.x'
        entry_point = 'app.js'
        additional_env = {
            'SIMPLE_VAR': 'value',
            'VAR_WITH_QUOTES': 'value with "quotes"',
            'VAR_WITH_SPACES': 'value with spaces',
            'VAR_WITH_SPECIAL': 'value$with&special*chars',
        }

        result = generate_script_content(runtime, entry_point, additional_env)

        # All values should be wrapped in double quotes
        assert 'export SIMPLE_VAR="value"' in result
        assert 'export VAR_WITH_QUOTES="value with "quotes""' in result
        assert 'export VAR_WITH_SPACES="value with spaces"' in result
        assert 'export VAR_WITH_SPECIAL="value$with&special*chars"' in result

    @pytest.mark.asyncio
    async def test_generate_startup_script_file_write_error(self):
        """Test generate_startup_script with file write error."""
        runtime = 'nodejs18.x'
        entry_point = 'app.js'
        built_artifacts_path = '/dir/artifacts'

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', side_effect=IOError('Permission denied')),
        ):
            with pytest.raises(IOError, match='Permission denied'):
                await generate_startup_script(runtime, entry_point, built_artifacts_path)

    @pytest.mark.asyncio
    async def test_generate_startup_script_chmod_error(self):
        """Test generate_startup_script with chmod error."""
        runtime = 'nodejs18.x'
        entry_point = 'app.js'
        built_artifacts_path = '/dir/artifacts'

        mock_file = mock_open()
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o644

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_file),
            patch('os.stat', return_value=mock_stat_result),
            patch('os.chmod', side_effect=OSError('Permission denied')),
        ):
            with pytest.raises(OSError, match='Permission denied'):
                await generate_startup_script(runtime, entry_point, built_artifacts_path)
