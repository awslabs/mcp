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

"""Tests for the server.py module to improve coverage."""

from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server.server import (
    check_network_security_prompt,
    check_storage_security_prompt,
    main,
    mcp,
    security_assessment_precheck,
)


@pytest.mark.asyncio
async def test_security_assessment_precheck(mock_ctx):
    """Test the security_assessment_precheck function."""
    # Call the function
    result = await security_assessment_precheck(mock_ctx)

    # Verify the result is a string
    assert isinstance(result, str)
    # Verify the result contains expected content
    assert "AWS Security Assessment Workflow Guide" in result
    assert "CheckSecurityServices" in result
    assert "GetSecurityFindings" in result


@pytest.mark.asyncio
async def test_check_storage_security_prompt(mock_ctx):
    """Test the check_storage_security_prompt function."""
    # Call the function
    result = await check_storage_security_prompt(mock_ctx)

    # Verify the result is a string
    assert isinstance(result, str)
    # Verify the result contains expected content
    assert "AWS Storage Security Assessment Guide" in result
    assert "CheckStorageEncryption" in result


@pytest.mark.asyncio
async def test_check_network_security_prompt(mock_ctx):
    """Test the check_network_security_prompt function."""
    # Call the function
    result = await check_network_security_prompt(mock_ctx)

    # Verify the result is a string
    assert isinstance(result, str)
    # Verify the result contains expected content
    assert "AWS Network Security Assessment Guide" in result
    assert "CheckNetworkSecurity" in result


def test_main():
    """Test the main function."""
    # Mock argparse.ArgumentParser
    with mock.patch("argparse.ArgumentParser") as mock_parser:
        # Mock the parse_args method
        mock_parser.return_value.parse_args.return_value = mock.MagicMock(sse=False, port=8888)

        # Mock asyncio.run
        with mock.patch("asyncio.run") as mock_run:
            # Mock mcp.run
            with mock.patch(
                "awslabs.well_architected_security_mcp_server.server.mcp.run"
            ) as mock_mcp_run:
                # Call the main function
                main()

                # Verify asyncio.run was not called since initialize was removed
                mock_run.assert_not_called()

                # Verify mcp.run was called
                mock_mcp_run.assert_called_once()


def test_main_with_sse():
    """Test the main function with SSE transport."""
    # Mock argparse.ArgumentParser
    with mock.patch("argparse.ArgumentParser") as mock_parser:
        # Mock the parse_args method
        mock_parser.return_value.parse_args.return_value = mock.MagicMock(sse=True, port=9999)

        # Mock asyncio.run
        with mock.patch("asyncio.run") as mock_run:
            # Mock mcp.run
            with mock.patch(
                "awslabs.well_architected_security_mcp_server.server.mcp.run"
            ) as mock_mcp_run:
                # Call the main function
                main()

                # Verify asyncio.run was not called since initialize was removed
                mock_run.assert_not_called()

                # Verify mcp.settings.port was set
                assert mcp.settings.port == 9999

                # Verify mcp.run was called with transport="sse"
                mock_mcp_run.assert_called_once_with(transport="sse")
