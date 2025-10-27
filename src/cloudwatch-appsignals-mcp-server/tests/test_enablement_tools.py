# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for enablement_tools module."""

import pytest
import tempfile
from awslabs.cloudwatch_appsignals_mcp_server.enablement_tools import get_enablement_guide
from pathlib import Path


class TestGetEnablementGuide:
    """Test get_enablement_guide function."""

    @pytest.fixture
    def temp_directories(self):
        """Create temporary IaC and app directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            iac_dir = base / 'infrastructure' / 'cdk'
            app_dir = base / 'app' / 'src'

            iac_dir.mkdir(parents=True)
            app_dir.mkdir(parents=True)

            yield {'iac': str(iac_dir), 'app': str(app_dir)}

    @pytest.mark.asyncio
    async def test_invalid_platform(self, temp_directories):
        """Test with invalid platform."""
        result = await get_enablement_guide(
            platform='invalid',
            language='python',
            iac_directory=temp_directories['iac'],
            app_directory=temp_directories['app'],
        )

        assert 'Error: Invalid platform' in result

    @pytest.mark.asyncio
    async def test_invalid_language(self, temp_directories):
        """Test with invalid language."""
        result = await get_enablement_guide(
            platform='ec2',
            language='invalid',
            iac_directory=temp_directories['iac'],
            app_directory=temp_directories['app'],
        )

        assert 'Error: Invalid language' in result

    @pytest.mark.asyncio
    async def test_nonexistent_iac_directory(self, temp_directories):
        """Test with non-existent IaC directory."""
        result = await get_enablement_guide(
            platform='ec2',
            language='python',
            iac_directory='/nonexistent/path',
            app_directory=temp_directories['app'],
        )

        assert 'Error: IaC directory does not exist' in result

    @pytest.mark.asyncio
    async def test_nonexistent_app_directory(self, temp_directories):
        """Test with non-existent app directory."""
        result = await get_enablement_guide(
            platform='ec2',
            language='python',
            iac_directory=temp_directories['iac'],
            app_directory='/nonexistent/path',
        )

        assert 'Error: Application directory does not exist' in result

    @pytest.mark.asyncio
    async def test_successful_guide_fetch(self, temp_directories, tmp_path, monkeypatch):
        """Test successful guide fetching when template exists."""
        result = await get_enablement_guide(
            platform='ec2',
            language='python',
            iac_directory=temp_directories['iac'],
            app_directory=temp_directories['app'],
        )

        assert '# Application Signals Enablement Guide' in result
        assert 'Placeholder content just to verify the tool can fetch the file.' in result
        assert temp_directories['iac'] in result
        assert temp_directories['app'] in result

    @pytest.mark.asyncio
    async def test_case_normalization(self, temp_directories):
        """Test that platform and language are normalized to lowercase."""
        result = await get_enablement_guide(
            platform='EC2',
            language='PYTHON',
            iac_directory=temp_directories['iac'],
            app_directory=temp_directories['app'],
        )

        assert '# Application Signals Enablement Guide' in result

    @pytest.mark.asyncio
    async def test_whitespace_trimming(self, temp_directories):
        """Test that whitespace is trimmed from inputs."""
        result = await get_enablement_guide(
            platform='   ec2   ',
            language='   python    ',
            iac_directory=temp_directories['iac'],
            app_directory=temp_directories['app'],
        )

        assert '# Application Signals Enablement Guide' in result

    @pytest.mark.asyncio
    async def test_all_valid_platforms(self, temp_directories):
        """Test that all valid platforms are accepted."""
        valid_platforms = ['ec2', 'ecs', 'lambda', 'eks']

        for platform in valid_platforms:
            result = await get_enablement_guide(
                platform=platform,
                language='python',
                iac_directory=temp_directories['iac'],
                app_directory=temp_directories['app'],
            )

            assert 'Error: Invalid platform' not in result

    @pytest.mark.asyncio
    async def test_all_valid_languages(self, temp_directories):
        """Test that all valid languages are accepted."""
        valid_languages = ['python', 'nodejs', 'java', 'dotnet']

        for language in valid_languages:
            result = await get_enablement_guide(
                platform='ec2',
                language=language,
                iac_directory=temp_directories['iac'],
                app_directory=temp_directories['app'],
            )

            assert 'Error: Invalid language' not in result

    @pytest.mark.asyncio
    async def test_relative_path_rejected(self, temp_directories):
        """Test that relative paths are rejected with clear error message."""
        result = await get_enablement_guide(
            platform='ec2',
            language='python',
            iac_directory='infrastructure/cdk',
            app_directory=temp_directories['app'],
        )

        assert 'Error: iac_directory must be an absolute path' in result
        assert 'infrastructure/cdk' in result

    @pytest.mark.asyncio
    async def test_relative_app_directory_rejected(self, temp_directories):
        """Test that relative app directory is rejected with clear error message."""
        result = await get_enablement_guide(
            platform='ec2',
            language='python',
            iac_directory=temp_directories['iac'],
            app_directory='app/src',
        )

        assert 'Error: app_directory must be an absolute path' in result
        assert 'app/src' in result

    @pytest.mark.asyncio
    async def test_absolute_path_handling(self, temp_directories):
        """Test that absolute paths are handled correctly."""
        result = await get_enablement_guide(
            platform='ec2',
            language='python',
            iac_directory=temp_directories['iac'],
            app_directory=temp_directories['app'],
        )

        assert '# Application Signals Enablement Guide' in result
        assert temp_directories['iac'] in result
        assert temp_directories['app'] in result
