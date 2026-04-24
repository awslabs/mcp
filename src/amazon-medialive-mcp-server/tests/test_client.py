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

"""Tests for the generated MediaLive boto3 client wrapper."""

import pytest
from awslabs.amazon_medialive_mcp_server.client import MediaLiveClient
from unittest.mock import MagicMock, patch


@patch('awslabs.amazon_medialive_mcp_server.client.boto3.Session')
def test_client_init_default_region(mock_session_cls):
    """Verify client initializes with default region."""
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session
    client = MediaLiveClient()
    mock_session_cls.assert_called_once_with(region_name='us-east-1', profile_name=None)
    mock_session.client.assert_called_once_with('medialive')
    assert client._client is mock_session.client.return_value


@patch('awslabs.amazon_medialive_mcp_server.client.boto3.Session')
def test_client_init_custom_region_and_profile(mock_session_cls):
    """Verify client initializes with custom region and profile."""
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session
    MediaLiveClient(region_name='eu-west-1', profile_name='myprofile')
    mock_session_cls.assert_called_once_with(region_name='eu-west-1', profile_name='myprofile')


@patch('awslabs.amazon_medialive_mcp_server.client.boto3.Session')
@pytest.mark.asyncio
async def test_client_method_delegates_to_boto3(mock_session_cls):
    """Verify each client method delegates to the underlying boto3 client."""
    mock_boto3_client = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_boto3_client
    mock_session_cls.return_value = mock_session

    client = MediaLiveClient()

    # Test a sample of methods across different HTTP verbs
    test_methods = [
        ('list_channels', 'list_channels', {}),
        ('describe_channel', 'describe_channel', {'ChannelId': '123'}),
        ('create_channel', 'create_channel', {'Name': 'test'}),
        ('delete_channel', 'delete_channel', {'ChannelId': '123'}),
        ('start_channel', 'start_channel', {'ChannelId': '123'}),
        ('stop_channel', 'stop_channel', {'ChannelId': '123'}),
        ('create_input', 'create_input', {'Name': 'test'}),
        ('list_inputs', 'list_inputs', {}),
        ('describe_input', 'describe_input', {'InputId': '123'}),
        ('update_channel', 'update_channel', {'ChannelId': '123'}),
    ]

    for method_name, boto3_method, kwargs in test_methods:
        mock_response = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        getattr(mock_boto3_client, boto3_method).return_value = mock_response

        result = await getattr(client, method_name)(**kwargs)

        getattr(mock_boto3_client, boto3_method).assert_called_with(**kwargs)
        assert result == mock_response


@patch('awslabs.amazon_medialive_mcp_server.client.boto3.Session')
@pytest.mark.asyncio
async def test_all_client_methods_exist_and_are_async(mock_session_cls):
    """Verify all generated client methods are callable async functions."""
    mock_session = MagicMock()
    mock_session.client.return_value = MagicMock()
    mock_session_cls.return_value = mock_session

    client = MediaLiveClient()

    # Every public method (not starting with _) should be async
    import asyncio

    for attr_name in dir(client):
        if attr_name.startswith('_'):
            continue
        attr = getattr(client, attr_name)
        if callable(attr):
            assert asyncio.iscoroutinefunction(attr), f'{attr_name} should be an async method'
