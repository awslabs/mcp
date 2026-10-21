# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for enablement_tools module."""

import builtins
import io
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server import enablement_tools
from awslabs.cloudwatch_applicationsignals_mcp_server.enablement_tools import get_enablement_guide
from pathlib import Path
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

        assert '# Task: Enable AWS Application Signals for Python on EC2' in result
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
                or '# Task: Enable AWS Application Signals' in result
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
                or '# Task: Enable AWS Application Signals' in result
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

        assert '# Task: Enable AWS Application Signals for Python on EC2' in result
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
            '# Task: Enable AWS Application Signals' in result
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
            '# Task: Enable AWS Application Signals' in result
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
            '# Task: Enable AWS Application Signals' in result
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
    async def test_platform_with_path_separators_rejected(self):
        """A platform value containing path separators is treated as unsupported."""
        result = await get_enablement_guide(
            service_platform='../../../../../../../../../root',
            service_language='python',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert 'Enablement guide not available' in result
        assert 'not currently supported' in result
        # The response must not echo internal filesystem details.
        assert 'site-packages' not in result
        assert 'enablement_guides' not in result
        assert 'Errno' not in result

    @pytest.mark.asyncio
    async def test_overlong_platform_rejected(self):
        """An over-long platform value is rejected without surfacing a filesystem error."""
        result = await get_enablement_guide(
            service_platform='../../../../../../../../../' + 'A' * 400,
            service_language='python',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert 'Enablement guide not available' in result
        assert 'File name too long' not in result
        assert 'site-packages' not in result

    @pytest.mark.asyncio
    async def test_language_with_path_separators_rejected(self):
        """A language value containing path separators is treated as unsupported."""
        result = await get_enablement_guide(
            service_platform='ec2',
            service_language='../../../../etc/passwd',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert 'Enablement guide not available' in result
        assert 'site-packages' not in result
        assert 'Errno' not in result

    @pytest.mark.asyncio
    async def test_platform_with_embedded_separator_rejected(self):
        """A platform value with an embedded separator is treated as unsupported."""
        result = await get_enablement_guide(
            service_platform='lambda/../ec2',
            service_language='python',
            iac_directory=ABSOLUTE_PATHS['iac'],
            app_directory=ABSOLUTE_PATHS['app'],
        )

        assert 'Enablement guide not available' in result

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


GUIDE_TEMPLATES = sorted(
    (Path(enablement_tools.__file__).parent / 'enablement_guides' / 'templates').glob(
        '*/*-enablement.md'
    )
)


@pytest.fixture
def legacy_default_encoding(monkeypatch):
    """Make text-mode file I/O behave like a Windows host whose default encoding is cp1252.

    ``open()`` and ``Path.read_text()`` called without an ``encoding`` use cp1252. This
    reproduces such a host on any platform, including when the test run itself has
    UTF-8 mode enabled.
    """
    real_open = io.open

    def legacy_open(
        file,
        mode='r',
        buffering=-1,
        encoding=None,
        errors=None,
        newline=None,
        closefd=True,
        opener=None,
    ):
        if 'b' not in mode and encoding in (None, 'locale'):
            encoding = 'cp1252'
        return real_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def legacy_text_encoding(encoding, stacklevel=2):
        return 'locale' if encoding is None else encoding

    monkeypatch.setattr(builtins, 'open', legacy_open)
    monkeypatch.setattr(io, 'open', legacy_open)
    monkeypatch.setattr(io, 'text_encoding', legacy_text_encoding)


class TestGuideEncoding:
    """The bundled guides are UTF-8 and must read the same whatever the host's default is."""

    def test_guides_are_found(self):
        """Guard against the parametrized test below silently collecting nothing."""
        assert GUIDE_TEMPLATES

    @pytest.mark.parametrize('template', GUIDE_TEMPLATES, ids=lambda path: path.stem)
    async def test_guide_is_read_as_utf8(self, template, tmp_path, legacy_default_encoding):
        """Every bundled guide is returned exactly as stored, not as an error or mojibake."""
        platform, language = template.stem.removesuffix('-enablement').split('-')
        expected = template.read_text(encoding='utf-8')

        result = await get_enablement_guide(
            service_platform=platform,
            service_language=language,
            iac_directory=str(tmp_path / 'iac'),
            app_directory=str(tmp_path / 'app'),
        )

        assert not result.startswith('Fatal error')
        assert result.endswith(expected)

    async def test_non_ascii_guide_content_is_preserved(self, tmp_path, legacy_default_encoding):
        """A guide containing an arrow keeps it, rather than the cp1252 mojibake for it."""
        result = await get_enablement_guide(
            service_platform='ec2',
            service_language='python',
            iac_directory=str(tmp_path / 'iac'),
            app_directory=str(tmp_path / 'app'),
        )

        assert '→' in result
        assert 'â†’' not in result
