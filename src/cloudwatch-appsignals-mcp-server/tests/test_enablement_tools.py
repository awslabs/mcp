# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for enablement_tools module."""

import pytest
from awslabs.cloudwatch_appsignals_mcp_server.enablement_tools import (
    Platform,
    ServiceLanguage,
    get_application_signals_enablement_guide,
)
from pathlib import Path


# Absolute paths for testing (no need to create real directories)
ABSOLUTE_PATHS = {
    'iac': '/tmp/test/infrastructure/cdk',
    'app': '/tmp/test/app/src'
}


class TestGetEnablementGuide:
    """Test get_enablement_guide function."""

    @pytest.mark.asyncio
    async def test_successful_guide_fetch(self, tmp_path, monkeypatch):
        """Test successful guide fetching when template exists."""
        result = await get_application_signals_enablement_guide(
            platform=Platform.EC2,
            service_language=ServiceLanguage.PYTHON,
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
        valid_platforms = [Platform.EC2, Platform.ECS, Platform.LAMBDA, Platform.EKS]

        for platform in valid_platforms:
            result = await get_application_signals_enablement_guide(
                platform=platform,
                service_language=ServiceLanguage.PYTHON,
                iac_directory=ABSOLUTE_PATHS['iac'],
                app_directory=ABSOLUTE_PATHS['app'],
            )

            # Should either succeed or say template not found, but not invalid platform
            assert 'Error: Invalid platform' not in result

    @pytest.mark.asyncio
    async def test_all_valid_languages(self):
        """Test that all valid languages are accepted."""
        valid_languages = [
            ServiceLanguage.PYTHON,
            ServiceLanguage.NODEJS,
            ServiceLanguage.JAVA,
            ServiceLanguage.DOTNET,
        ]

        for language in valid_languages:
            result = await get_application_signals_enablement_guide(
                platform=Platform.EC2,
                service_language=language,
                iac_directory=ABSOLUTE_PATHS['iac'],
                app_directory=ABSOLUTE_PATHS['app'],
            )

            # Should either succeed or say template not found, but not invalid language
            assert 'Error: Invalid language' not in result

    @pytest.mark.asyncio
    async def test_relative_path_rejected(self):
        """Test that relative paths are rejected with clear error message."""
        result = await get_application_signals_enablement_guide(
            platform=Platform.EC2,
            service_language=ServiceLanguage.PYTHON,
            iac_directory='infrastructure/cdk',
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert 'Error: iac_directory and app_directory must be absolute paths' in result
        assert 'infrastructure/cdk' in result

    @pytest.mark.asyncio
    async def test_relative_app_directory_rejected(self):
        """Test that relative app directory is rejected with clear error message."""
        result = await get_application_signals_enablement_guide(
            platform=Platform.EC2,
            service_language=ServiceLanguage.PYTHON,
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory='app/src',
        )

        assert 'Error: iac_directory and app_directory must be absolute paths' in result
        assert 'app/src' in result

    @pytest.mark.asyncio
    async def test_absolute_path_handling(self):
        """Test that absolute paths are handled correctly."""
        result = await get_application_signals_enablement_guide(
            platform=Platform.EC2,
            service_language=ServiceLanguage.PYTHON,
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert '# Application Signals Enablement Guide' in result
        assert ABSOLUTE_PATHS['iac'] in result
        assert ABSOLUTE_PATHS['app'] in result
