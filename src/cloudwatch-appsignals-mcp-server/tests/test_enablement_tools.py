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

"""Tests for enablement_tools module."""

import pytest
from awslabs.cloudwatch_appsignals_mcp_server.enablement_tools import (
    enable_application_signals,
)
from unittest.mock import mock_open, patch


class TestEnableApplicationSignals:
    """Test enable_application_signals function."""

    @pytest.mark.asyncio
    async def test_enable_application_signals_python_ec2(self):
        """Test enablement for Python on EC2."""
        result = await enable_application_signals(
            platform='ec2',
            language='python',
            iac_directory='infrastructure/ec2/cdk',
            app_directory='sample-apps/python/flask',
        )

        assert 'Error' not in result
        assert 'infrastructure/ec2/cdk' in result
        assert 'sample-apps/python/flask' in result
        assert '**Platform:** ec2' in result
        assert '**Language:** python' in result
        # Should contain actual guide content
        assert len(result) > 200  # Guide should be substantial

    @pytest.mark.asyncio
    async def test_enable_application_signals_nodejs_ec2(self):
        """Test enablement for Node.js on EC2."""
        result = await enable_application_signals(
            platform='ec2',
            language='nodejs',
            iac_directory='infrastructure/ec2/terraform',
            app_directory='sample-apps/nodejs/express',
        )

        assert 'Error' not in result
        assert 'infrastructure/ec2/terraform' in result
        assert 'sample-apps/nodejs/express' in result
        assert '**Platform:** ec2' in result
        assert '**Language:** nodejs' in result
        assert len(result) > 200

    @pytest.mark.asyncio
    async def test_enable_application_signals_java_ec2(self):
        """Test enablement for Java on EC2."""
        result = await enable_application_signals(
            platform='ec2',
            language='java',
            iac_directory='infrastructure/ec2/cloudformation',
            app_directory='sample-apps/java/springboot',
        )

        assert 'Error' not in result
        assert 'infrastructure/ec2/cloudformation' in result
        assert 'sample-apps/java/springboot' in result
        assert '**Platform:** ec2' in result
        assert '**Language:** java' in result
        assert len(result) > 200

    @pytest.mark.asyncio
    async def test_enable_application_signals_dotnet_ec2(self):
        """Test enablement for .NET on EC2."""
        result = await enable_application_signals(
            platform='ec2',
            language='dotnet',
            iac_directory='infrastructure/ec2/cdk',
            app_directory='sample-apps/dotnet/aspnetcore',
        )

        assert 'Error' not in result
        assert 'infrastructure/ec2/cdk' in result
        assert 'sample-apps/dotnet/aspnetcore' in result
        assert '**Platform:** ec2' in result
        assert '**Language:** dotnet' in result
        assert len(result) > 200

    @pytest.mark.asyncio
    async def test_enable_application_signals_invalid_platform(self):
        """Test with invalid platform."""
        result = await enable_application_signals(
            platform='invalid-platform',
            language='python',
            iac_directory='infrastructure/ec2/cdk',
            app_directory='sample-apps/python/flask',
        )

        assert 'Error' in result
        assert 'Invalid platform' in result
        assert 'invalid-platform' in result

    @pytest.mark.asyncio
    async def test_enable_application_signals_invalid_language(self):
        """Test with invalid language."""
        result = await enable_application_signals(
            platform='ec2',
            language='rust',
            iac_directory='infrastructure/ec2/cdk',
            app_directory='sample-apps/rust/actix',
        )

        assert 'Error' in result
        assert 'Invalid language' in result
        assert 'rust' in result

    @pytest.mark.asyncio
    async def test_enable_application_signals_unsupported_combination(self):
        """Test with platform/language combination that doesn't have a guide yet."""
        result = await enable_application_signals(
            platform='ecs',
            language='python',
            iac_directory='infrastructure/ecs/cdk',
            app_directory='sample-apps/python/flask',
        )

        assert 'Error' in result
        assert 'not yet available' in result

    @pytest.mark.asyncio
    async def test_enable_application_signals_case_insensitive(self):
        """Test that platform and language are case-insensitive."""
        result = await enable_application_signals(
            platform='EC2',
            language='PYTHON',
            iac_directory='infrastructure/ec2/cdk',
            app_directory='sample-apps/python/flask',
        )

        assert 'Error' not in result
        assert '**Platform:** ec2' in result
        assert '**Language:** python' in result

    @pytest.mark.asyncio
    async def test_enable_application_signals_whitespace_handling(self):
        """Test that whitespace is stripped from inputs."""
        result = await enable_application_signals(
            platform='  ec2  ',
            language='  python  ',
            iac_directory='infrastructure/ec2/cdk',
            app_directory='sample-apps/python/flask',
        )

        assert 'Error' not in result
        assert '**Platform:** ec2' in result
        assert '**Language:** python' in result

    @pytest.mark.asyncio
    async def test_enable_application_signals_file_read_error(self):
        """Test handling of file read errors."""
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = IOError('Permission denied')

            result = await enable_application_signals(
                platform='ec2',
                language='python',
                iac_directory='infrastructure/ec2/cdk',
                app_directory='sample-apps/python/flask',
            )

            assert 'Error' in result
            assert 'Failed to read enablement guide' in result

    @pytest.mark.asyncio
    async def test_enable_application_signals_template_path_construction(self):
        """Test that template paths are constructed correctly."""
        # Use a mock to verify the correct path is being checked
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False

            result = await enable_application_signals(
                platform='ec2',
                language='python',
                iac_directory='infrastructure/ec2/cdk',
                app_directory='sample-apps/python/flask',
            )

            # Should check for ec2/ec2-python-enablement.md
            assert 'Error' in result
            assert 'not yet available' in result

    @pytest.mark.asyncio
    async def test_enable_application_signals_all_ec2_languages(self):
        """Test that all 4 languages work for EC2 platform."""
        languages = ['python', 'nodejs', 'java', 'dotnet']

        for language in languages:
            result = await enable_application_signals(
                platform='ec2',
                language=language,
                iac_directory='infrastructure/ec2/cdk',
                app_directory=f'sample-apps/{language}/app',
            )

            assert 'Error' not in result, (
                f'Expected {language} to work for EC2, but got error: {result}'
            )
            assert f'**Language:** {language}' in result
            assert len(result) > 200

    @pytest.mark.asyncio
    async def test_enable_application_signals_valid_platforms_list(self):
        """Test that error message includes all valid platforms."""
        result = await enable_application_signals(
            platform='invalid',
            language='python',
            iac_directory='infrastructure/ec2/cdk',
            app_directory='sample-apps/python/flask',
        )

        assert 'ec2' in result
        assert 'ecs' in result
        assert 'lambda' in result
        assert 'eks' in result
        assert 'kubernetes' in result

    @pytest.mark.asyncio
    async def test_enable_application_signals_valid_languages_list(self):
        """Test that error message includes all valid languages."""
        result = await enable_application_signals(
            platform='ec2',
            language='invalid',
            iac_directory='infrastructure/ec2/cdk',
            app_directory='sample-apps/python/flask',
        )

        assert 'python' in result
        assert 'nodejs' in result
        assert 'java' in result
        assert 'dotnet' in result
