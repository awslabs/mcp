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

"""Unit tests for helper tools."""

import pytest
from awslabs.aws_healthomics_mcp_server.consts import HEALTHOMICS_SUPPORTED_REGIONS
from awslabs.aws_healthomics_mcp_server.tools.helper_tools import get_supported_regions
from botocore.exceptions import BotoCoreError, ClientError
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_get_supported_regions_success():
    """Test successful retrieval of regions from SSM."""
    # Mock SSM response
    mock_ssm_response = {
        'Parameters': [
            {'Value': 'us-east-1'},
            {'Value': 'us-west-2'},
            {'Value': 'eu-west-1'},
        ]
    }

    # Mock context and session
    mock_ctx = AsyncMock()
    mock_session = MagicMock()
    mock_ssm = MagicMock()
    mock_ssm.get_parameters_by_path.return_value = mock_ssm_response
    mock_session.client.return_value = mock_ssm

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.helper_tools.get_aws_session',
        return_value=mock_session,
    ):
        result = await get_supported_regions(mock_ctx)

    # Verify results
    assert result['count'] == 3
    assert result['regions'] == ['eu-west-1', 'us-east-1', 'us-west-2']
    assert 'note' not in result

    # Verify SSM was called correctly
    mock_session.client.assert_called_once_with('ssm')
    mock_ssm.get_parameters_by_path.assert_called_once_with(
        Path='/aws/service/global-infrastructure/services/omics/regions'
    )


@pytest.mark.asyncio
async def test_get_supported_regions_empty_ssm():
    """Test fallback to hardcoded regions when SSM returns empty list."""
    # Mock SSM response with no parameters
    mock_ssm_response = {'Parameters': []}

    # Mock context and session
    mock_ctx = AsyncMock()
    mock_session = MagicMock()
    mock_ssm = MagicMock()
    mock_ssm.get_parameters_by_path.return_value = mock_ssm_response
    mock_session.client.return_value = mock_ssm

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.helper_tools.get_aws_session',
        return_value=mock_session,
    ):
        result = await get_supported_regions(mock_ctx)

    # Verify fallback to hardcoded regions
    assert result['count'] == len(HEALTHOMICS_SUPPORTED_REGIONS)
    assert result['regions'] == sorted(HEALTHOMICS_SUPPORTED_REGIONS)
    assert 'note' not in result


@pytest.mark.asyncio
async def test_get_supported_regions_boto_error():
    """Test handling of BotoCoreError."""
    # Mock context and session
    mock_ctx = AsyncMock()
    mock_session = MagicMock()
    mock_ssm = MagicMock()
    mock_ssm.get_parameters_by_path.side_effect = BotoCoreError()
    mock_session.client.return_value = mock_ssm

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.helper_tools.get_aws_session',
        return_value=mock_session,
    ):
        result = await get_supported_regions(mock_ctx)

    # Verify fallback to hardcoded regions with note
    assert result['count'] == len(HEALTHOMICS_SUPPORTED_REGIONS)
    assert result['regions'] == sorted(HEALTHOMICS_SUPPORTED_REGIONS)
    assert 'note' in result
    assert 'Using hardcoded region list due to error:' in result['note']


@pytest.mark.asyncio
async def test_get_supported_regions_client_error():
    """Test handling of ClientError."""
    # Mock context and session
    mock_ctx = AsyncMock()
    mock_session = MagicMock()
    mock_ssm = MagicMock()
    mock_ssm.get_parameters_by_path.side_effect = ClientError(
        {'Error': {'Code': 'InvalidParameter', 'Message': 'Test error'}}, 'GetParametersByPath'
    )
    mock_session.client.return_value = mock_ssm

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.helper_tools.get_aws_session',
        return_value=mock_session,
    ):
        result = await get_supported_regions(mock_ctx)

    # Verify fallback to hardcoded regions with note
    assert result['count'] == len(HEALTHOMICS_SUPPORTED_REGIONS)
    assert result['regions'] == sorted(HEALTHOMICS_SUPPORTED_REGIONS)
    assert 'note' in result
    assert 'Using hardcoded region list due to error:' in result['note']


@pytest.mark.asyncio
async def test_get_supported_regions_unexpected_error():
    """Test handling of unexpected errors."""
    # Mock context and session
    mock_ctx = AsyncMock()
    mock_session = MagicMock()
    mock_ssm = MagicMock()
    mock_ssm.get_parameters_by_path.side_effect = Exception('Unexpected error')
    mock_session.client.return_value = mock_ssm

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.helper_tools.get_aws_session',
        return_value=mock_session,
    ):
        result = await get_supported_regions(mock_ctx)

    # Verify fallback to hardcoded regions with note
    assert result['count'] == len(HEALTHOMICS_SUPPORTED_REGIONS)
    assert result['regions'] == sorted(HEALTHOMICS_SUPPORTED_REGIONS)
    assert 'note' in result
    assert 'Using hardcoded region list due to error:' in result['note']

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error retrieving supported regions' in mock_ctx.error.call_args[0][0]
