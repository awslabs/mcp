# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for enablement_tools module."""

import pytest
from awslabs.cloudwatch_appsignals_mcp_server.enablement_tools import get_enablement_guide
from unittest.mock import patch


# Absolute paths for testing (no need to create real directories)
ABSOLUTE_PATHS = {'iac': '/tmp/test/infrastructure/cdk', 'app': '/tmp/test/app/src'}


class TestGetEnablementGuide:
    """Test get_enablement_guide function."""

    @pytest.mark.asyncio
    async def test_successful_guide_fetch(self, tmp_path, monkeypatch):
        """Test successful guide fetching when template exists."""
        result = await get_enablement_guide(
            service_platform='ec2',
            service_language='python',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert '# Application Signals Enablement Guide' in result
        assert 'Placeholder content just to verify the tool can fetch the file.' in result
        assert ABSOLUTE_PATHS['iac'] in result
        assert ABSOLUTE_PATHS['app'] in result

    @pytest.mark.asyncio
    async def test_all_valid_platforms(self):
        """Test that all valid platforms are accepted."""
        valid_platforms = ['ec2', 'ecs', 'lambda', 'eks']

        for platform in valid_platforms:
            result = await get_enablement_guide(
                service_platform=platform,
                service_language='python',
                iac_directory=ABSOLUTE_PATHS['iac'],
                app_directory=ABSOLUTE_PATHS['app'],
            )

            # Should either succeed or say template not found with friendly message
            assert (
                'Enablement guide not available' in result
                or '# Application Signals Enablement Guide' in result
            )

    @pytest.mark.asyncio
    async def test_all_valid_languages(self):
        """Test that all valid languages are accepted."""
        valid_languages = ['python', 'nodejs', 'java', 'dotnet']

        for language in valid_languages:
            result = await get_enablement_guide(
                service_platform='ec2',
                service_language=language,
                iac_directory=ABSOLUTE_PATHS['iac'],
                app_directory=ABSOLUTE_PATHS['app'],
            )

            # Should either succeed or say template not found with friendly message
            assert (
                'Enablement guide not available' in result
                or '# Application Signals Enablement Guide' in result
            )

    @pytest.mark.asyncio
    async def test_relative_path_rejected(self):
        """Test that relative paths are rejected with clear error message."""
        result = await get_enablement_guide(
            service_platform='ec2',
            service_language='python',
            iac_directory='infrastructure/cdk',
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert 'Error: iac_directory and app_directory must be absolute paths' in result
        assert 'infrastructure/cdk' in result

    @pytest.mark.asyncio
    async def test_relative_app_directory_rejected(self):
        """Test that relative app directory is rejected with clear error message."""
        result = await get_enablement_guide(
            service_platform='ec2',
            service_language='python',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory='app/src',
        )

        assert 'Error: iac_directory and app_directory must be absolute paths' in result
        assert 'app/src' in result

    @pytest.mark.asyncio
    async def test_absolute_path_handling(self):
        """Test that absolute paths are handled correctly."""
        result = await get_enablement_guide(
            service_platform='ec2',
            service_language='python',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert '# Application Signals Enablement Guide' in result
        assert ABSOLUTE_PATHS['iac'] in result
        assert ABSOLUTE_PATHS['app'] in result

    @pytest.mark.asyncio
    async def test_unsupported_language_ruby(self):
        """Test that unsupported language (ruby) returns friendly error message."""
        result = await get_enablement_guide(
            service_platform='ec2',
            service_language='ruby',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert 'Enablement guide not available' in result
        assert 'ruby' in result.lower()
        assert 'not currently supported' in result

    @pytest.mark.asyncio
    async def test_unsupported_platform_k8s(self):
        """Test that unsupported platform (k8s) returns friendly error message."""
        result = await get_enablement_guide(
            service_platform='k8s',
            service_language='python',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert 'Enablement guide not available' in result
        assert 'k8s' in result.lower()
        assert 'not currently supported' in result

    @pytest.mark.asyncio
    async def test_case_insensitive_platform(self):
        """Test that uppercase platform names are normalized to lowercase."""
        result = await get_enablement_guide(
            service_platform='EC2',
            service_language='python',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        # Should work the same as lowercase
        assert 'Error: iac_directory and app_directory must be absolute paths' not in result
        assert (
            '# Application Signals Enablement Guide' in result
            or 'Enablement guide not available' in result
        )

    @pytest.mark.asyncio
    async def test_case_insensitive_language(self):
        """Test that uppercase language names are normalized to lowercase."""
        result = await get_enablement_guide(
            service_platform='ec2',
            service_language='PYTHON',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        # Should work the same as lowercase
        assert 'Error: iac_directory and app_directory must be absolute paths' not in result
        assert (
            '# Application Signals Enablement Guide' in result
            or 'Enablement guide not available' in result
        )

    @pytest.mark.asyncio
    async def test_whitespace_trimming(self):
        """Test that leading/trailing whitespace is trimmed from inputs."""
        result = await get_enablement_guide(
            service_platform='  ec2  ',
            service_language='  python  ',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        # Should work the same as trimmed input
        assert 'Error: iac_directory and app_directory must be absolute paths' not in result
        assert (
            '# Application Signals Enablement Guide' in result
            or 'Enablement guide not available' in result
        )

    @pytest.mark.asyncio
    async def test_both_paths_relative(self):
        """Test that error message shows both paths when both are relative."""
        result = await get_enablement_guide(
            service_platform='ec2',
            service_language='python',
            iac_directory='infrastructure/cdk',
            app_directory='app/src',
        )

        assert 'Error: iac_directory and app_directory must be absolute paths' in result
        assert 'infrastructure/cdk' in result
        assert 'app/src' in result

    @pytest.mark.asyncio
    async def test_file_read_error(self):
        """Test that file read errors are handled gracefully with helpful message."""
        with patch('builtins.open', side_effect=PermissionError('Permission denied')):
            result = await get_enablement_guide(
                service_platform='ec2',
                service_language='python',
                iac_directory=ABSOLUTE_PATHS['iac'],
                app_directory=ABSOLUTE_PATHS['app'],
            )

        assert 'Fatal error: Cannot read enablement guide' in result
        assert 'Permission denied' in result
        assert 'file permissions or reinstall' in result
        assert 'issue with the MCP server installation' in result
