# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for enablement_tools module."""

import pytest
import tempfile
from awslabs.cloudwatch_appsignals_mcp_server.enablement_tools import (
    get_enablement_guide,
    Platform,
    ServiceLanguage,
)
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
    async def test_successful_guide_fetch(self, temp_directories, tmp_path, monkeypatch):
        """Test successful guide fetching when template exists."""
        result = await get_enablement_guide(
            platform=Platform.EC2,
            service_language=ServiceLanguage.PYTHON,
            iac_directory=temp_directories['iac'],
            app_directory=temp_directories['app'],
        )

        assert '# Application Signals Enablement Guide' in result
        assert 'Placeholder content just to verify the tool can fetch the file.' in result
        assert temp_directories['iac'] in result
        assert temp_directories['app'] in result

    @pytest.mark.asyncio
    async def test_all_valid_platforms(self, temp_directories):
        """Test that all valid platforms are accepted."""
        valid_platforms = [Platform.EC2, Platform.ECS, Platform.LAMBDA, Platform.EKS]

        for platform in valid_platforms:
            result = await get_enablement_guide(
                platform=platform,
                service_language=ServiceLanguage.PYTHON,
                iac_directory=temp_directories['iac'],
                app_directory=temp_directories['app'],
            )

            # Should either succeed or say template not found, but not invalid platform
            assert 'Error: Invalid platform' not in result

    @pytest.mark.asyncio
    async def test_all_valid_languages(self, temp_directories):
        """Test that all valid languages are accepted."""
        valid_languages = [ServiceLanguage.PYTHON, ServiceLanguage.NODEJS, ServiceLanguage.JAVA, ServiceLanguage.DOTNET]

        for language in valid_languages:
            result = await get_enablement_guide(
                platform=Platform.EC2,
                service_language=language,
                iac_directory=temp_directories['iac'],
                app_directory=temp_directories['app'],
            )

            # Should either succeed or say template not found, but not invalid language
            assert 'Error: Invalid language' not in result

    @pytest.mark.asyncio
    async def test_relative_path_rejected(self, temp_directories):
        """Test that relative paths are rejected with clear error message."""
        result = await get_enablement_guide(
            platform=Platform.EC2,
            service_language=ServiceLanguage.PYTHON,
            iac_directory='infrastructure/cdk',
            app_directory=temp_directories['app'],
        )

        assert 'Error: iac_directory must be an absolute path' in result
        assert 'infrastructure/cdk' in result

    @pytest.mark.asyncio
    async def test_relative_app_directory_rejected(self, temp_directories):
        """Test that relative app directory is rejected with clear error message."""
        result = await get_enablement_guide(
            platform=Platform.EC2,
            service_language=ServiceLanguage.PYTHON,
            iac_directory=temp_directories['iac'],
            app_directory='app/src',
        )

        assert 'Error: app_directory must be an absolute path' in result
        assert 'app/src' in result

    @pytest.mark.asyncio
    async def test_absolute_path_handling(self, temp_directories):
        """Test that absolute paths are handled correctly."""
        result = await get_enablement_guide(
            platform=Platform.EC2,
            service_language=ServiceLanguage.PYTHON,
            iac_directory=temp_directories['iac'],
            app_directory=temp_directories['app'],
        )

        assert '# Application Signals Enablement Guide' in result
        assert temp_directories['iac'] in result
        assert temp_directories['app'] in result
