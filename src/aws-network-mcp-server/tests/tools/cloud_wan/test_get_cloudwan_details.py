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

"""Test cases for the get_cloudwan_details tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
details_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details'
)


@patch.object(details_module, 'get_aws_client')
async def test_get_cloudwan_details_success(mock_get_client):
    """Test successful Cloud WAN details retrieval."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.get_core_network.return_value = {'CoreNetwork': {'CoreNetworkId': 'core-123'}}
    mock_client.get_core_network_policy.return_value = {
        'CoreNetworkPolicy': {'PolicyDocument': '{"version": "2021.12"}'}
    }
    mock_client.list_attachments.return_value = {'Attachments': [], 'NextToken': None}

    result = await details_module.get_cwan('core-123', 'us-east-1')

    assert 'core_network' in result
    assert 'live_policy' in result
    assert 'attachments' in result
    assert result['live_policy']['version'] == '2021.12'


@patch.object(details_module, 'get_aws_client')
async def test_get_cloudwan_details_pagination(mock_get_client):
    """Test pagination with next_token."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.list_attachments.return_value = {'Attachments': [], 'NextToken': None}

    result = await details_module.get_cwan('core-123', 'us-east-1', next_token='token')

    assert 'attachments' in result
    assert 'core_network' not in result
    mock_client.list_attachments.assert_called_once_with(
        CoreNetworkId='core-123', NextToken='token'
    )


@patch.object(details_module, 'get_aws_client')
async def test_get_cloudwan_details_error(mock_get_client):
    """Test error handling."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.get_core_network.side_effect = Exception('Network not found')

    with pytest.raises(ToolError) as exc_info:
        await details_module.get_cwan('invalid', 'us-east-1')

    assert 'There was an error getting AWS Core Network details' in str(exc_info.value)
