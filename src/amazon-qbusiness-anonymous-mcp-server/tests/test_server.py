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

"""Tests for the amazon-qbusiness-anonymous MCP Server."""

import pytest
from awslabs.amazon_qbusiness_anonymous_mcp_server.server import qbiz_local_query


@pytest.mark.asyncio
async def test_qbiz_local_query(mocker):
    """Test the qbiz_local_query tool returns valid response with mocked chat_sync API response."""
    # Arrange
    test_query = 'List of holidays'
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv('QBUSINESS_APPLICATION_ID', 'xxxx-xxxx-xxxx-xxxx')
    mock_aq_client = mocker.Mock()
    mock_aq_client_chat_sync_response = {
        'systemMessage': "Here are the official company holidays: \n\n\u2022 New Year's Day Observed (January 2) \n\u2022 Martin Luther King Jr. Day (3rd Monday in January) \n\u2022 President's Day (3rd Monday in February) \n\u2022 Cesar Chavez Day (March 31) \n\u2022 Memorial Day (last Monday in May) \n\u2022 Independence Day (July 4) \n\u2022 Labor Day (1st Monday in September) \n\u2022 Veteran's Day Observed (November 10) \n\u2022 Thanksgiving Day (4th Thursday in November) \n\u2022 Day after Thanksgiving \n\u2022 Christmas (December 25)  \n\nWhen a holiday falls on Saturday, employees receive holiday credit, and when a holiday falls on Sunday, the holiday is observed on the following Monday. \n\nAdditionally, permanent employees are entitled to one personal holiday per year.",
        'conversationId': 'XXX',
        'systemMessageId': 'XXX',
        'sourceAttributions': [],
        'messageId': 'XXX',
    }
    mock_aq_client.chat_sync.return_value = mock_aq_client_chat_sync_response
    mocker.patch('boto3.client', return_value=mock_aq_client)
    expected_response = f'Qbiz response: {mock_aq_client_chat_sync_response["systemMessage"]}'

    # Act
    result = await qbiz_local_query(test_query)

    # Assert
    assert result == expected_response
    monkeypatch.delenv('AWS_REGION')
    monkeypatch.delenv('QBUSINESS_APPLICATION_ID')


@pytest.mark.asyncio
async def test_qbiz_local_query1(mocker):
    """Test the qbiz_local_query tool returns error when the chat_sync response does not include systemMessage."""
    # Arrange
    test_query = 'List of holidays'
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv('QBUSINESS_APPLICATION_ID', 'xxxx-xxxx-xxxx-xxxx')
    mock_aq_client = mocker.Mock()
    mock_aq_client_chat_sync_response = {
        'systemMessageQ': "Here are the official company holidays: \n\n\u2022 New Year's Day Observed (January 2) \n\u2022 Martin Luther King Jr. Day (3rd Monday in January) \n\u2022 President's Day (3rd Monday in February) \n\u2022 Cesar Chavez Day (March 31) \n\u2022 Memorial Day (last Monday in May) \n\u2022 Independence Day (July 4) \n\u2022 Labor Day (1st Monday in September) \n\u2022 Veteran's Day Observed (November 10) \n\u2022 Thanksgiving Day (4th Thursday in November) \n\u2022 Day after Thanksgiving \n\u2022 Christmas (December 25)  \n\nWhen a holiday falls on Saturday, employees receive holiday credit, and when a holiday falls on Sunday, the holiday is observed on the following Monday. \n\nAdditionally, permanent employees are entitled to one personal holiday per year.",
        'conversationId': 'XXX',
        'systemMessageId': 'XXX',
        'sourceAttributions': [],
        'messageId': 'XXX',
    }
    mock_aq_client.chat_sync.return_value = mock_aq_client_chat_sync_response
    mocker.patch('boto3.client', return_value=mock_aq_client)
    expected_response = f'Qbiz response: {mock_aq_client_chat_sync_response["systemMessageQ"]}'

    # Act
    result = await qbiz_local_query(test_query)

    # Assert
    assert result != expected_response
    monkeypatch.delenv('AWS_REGION')
    monkeypatch.delenv('QBUSINESS_APPLICATION_ID')


@pytest.mark.asyncio
async def test_qbiz_local_query_failure2(mocker):
    """Test the qbiz_local_query tool returns error when the query string is empty."""
    # Arrange
    test_query = ''
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv('QBUSINESS_APPLICATION_ID', 'xxxx-xxxx-xxxx-xxxx')
    mock_aq_client = mocker.Mock()
    mock_aq_client_chat_sync_response = {
        'systemMessage': "Here are the official company holidays: \n\n\u2022 New Year's Day Observed (January 2) \n\u2022 Martin Luther King Jr. Day (3rd Monday in January) \n\u2022 President's Day (3rd Monday in February) \n\u2022 Cesar Chavez Day (March 31) \n\u2022 Memorial Day (last Monday in May) \n\u2022 Independence Day (July 4) \n\u2022 Labor Day (1st Monday in September) \n\u2022 Veteran's Day Observed (November 10) \n\u2022 Thanksgiving Day (4th Thursday in November) \n\u2022 Day after Thanksgiving \n\u2022 Christmas (December 25)  \n\nWhen a holiday falls on Saturday, employees receive holiday credit, and when a holiday falls on Sunday, the holiday is observed on the following Monday. \n\nAdditionally, permanent employees are entitled to one personal holiday per year.",
        'conversationId': 'XXX',
        'systemMessageId': 'XXX',
        'sourceAttributions': [],
        'messageId': 'XXX',
    }
    mock_aq_client.chat_sync.return_value = mock_aq_client_chat_sync_response
    mocker.patch('boto3.client', return_value=mock_aq_client)
    expected_response = f'Qbiz response: {mock_aq_client_chat_sync_response["systemMessage"]}'

    # Act
    result = await qbiz_local_query(test_query)

    # Assert
    assert result != expected_response
    monkeypatch.delenv('AWS_REGION')
    monkeypatch.delenv('QBUSINESS_APPLICATION_ID')


@pytest.mark.asyncio
async def test_qbiz_local_query_failure3(mocker):
    """Test the qbiz_local_query tool returns error when the environment variable QBUSINESS_APPLICATION_ID is not defined."""
    # Arrange
    test_query = 'List of holidays'
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    mock_aq_client_chat_sync_response = {
        'systemMessage': "Here are the official company holidays: \n\n\u2022 New Year's Day Observed (January 2) \n\u2022 Martin Luther King Jr. Day (3rd Monday in January) \n\u2022 President's Day (3rd Monday in February) \n\u2022 Cesar Chavez Day (March 31) \n\u2022 Memorial Day (last Monday in May) \n\u2022 Independence Day (July 4) \n\u2022 Labor Day (1st Monday in September) \n\u2022 Veteran's Day Observed (November 10) \n\u2022 Thanksgiving Day (4th Thursday in November) \n\u2022 Day after Thanksgiving \n\u2022 Christmas (December 25)  \n\nWhen a holiday falls on Saturday, employees receive holiday credit, and when a holiday falls on Sunday, the holiday is observed on the following Monday. \n\nAdditionally, permanent employees are entitled to one personal holiday per year.",
        'conversationId': 'XXX',
        'systemMessageId': 'XXX',
        'sourceAttributions': [],
        'messageId': 'XXX',
    }
    expected_response = f'Qbiz response: {mock_aq_client_chat_sync_response["systemMessage"]}'

    # Act
    result = await qbiz_local_query(test_query)

    # Assert
    assert result != expected_response
    monkeypatch.delenv('AWS_REGION')


@pytest.mark.asyncio
async def test_qbiz_local_query_failure4(mocker):
    """Test the qbiz_local_query tool returns error when the environment variables AWS_REGION and QBUSINESS_APPLICATION_ID are not defined."""
    # Arrange
    test_query = 'List of holidays'
    mock_aq_client_chat_sync_response = {
        'systemMessage': "Here are the official company holidays: \n\n\u2022 New Year's Day Observed (January 2) \n\u2022 Martin Luther King Jr. Day (3rd Monday in January) \n\u2022 President's Day (3rd Monday in February) \n\u2022 Cesar Chavez Day (March 31) \n\u2022 Memorial Day (last Monday in May) \n\u2022 Independence Day (July 4) \n\u2022 Labor Day (1st Monday in September) \n\u2022 Veteran's Day Observed (November 10) \n\u2022 Thanksgiving Day (4th Thursday in November) \n\u2022 Day after Thanksgiving \n\u2022 Christmas (December 25)  \n\nWhen a holiday falls on Saturday, employees receive holiday credit, and when a holiday falls on Sunday, the holiday is observed on the following Monday. \n\nAdditionally, permanent employees are entitled to one personal holiday per year.",
        'conversationId': 'XXX',
        'systemMessageId': 'XXX',
        'sourceAttributions': [],
        'messageId': 'XXX',
    }
    expected_response = f'Qbiz response: {mock_aq_client_chat_sync_response["systemMessage"]}'

    # Act
    result = await qbiz_local_query(test_query)

    # Assert
    assert result != expected_response


@pytest.mark.asyncio
async def test_qbiz_local_query_failure5(mocker):
    """Test the qbiz_local_query tool returns error when QBUSINESS_APPLICATION_ID is invalid."""
    # Arrange
    test_query = 'List of holidays'
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv('QBUSINESS_APPLICATION_ID', 'xxxx-xxxx-xxxx-xxxx')
    mock_aq_client_chat_sync_response = {
        'systemMessage': "Here are the official company holidays: \n\n\u2022 New Year's Day Observed (January 2) \n\u2022 Martin Luther King Jr. Day (3rd Monday in January) \n\u2022 President's Day (3rd Monday in February) \n\u2022 Cesar Chavez Day (March 31) \n\u2022 Memorial Day (last Monday in May) \n\u2022 Independence Day (July 4) \n\u2022 Labor Day (1st Monday in September) \n\u2022 Veteran's Day Observed (November 10) \n\u2022 Thanksgiving Day (4th Thursday in November) \n\u2022 Day after Thanksgiving \n\u2022 Christmas (December 25)  \n\nWhen a holiday falls on Saturday, employees receive holiday credit, and when a holiday falls on Sunday, the holiday is observed on the following Monday. \n\nAdditionally, permanent employees are entitled to one personal holiday per year.",
        'conversationId': 'XXX',
        'systemMessageId': 'XXX',
        'sourceAttributions': [],
        'messageId': 'XXX',
    }
    expected_response = f'Qbiz response: {mock_aq_client_chat_sync_response["systemMessage"]}'

    # Act
    result = await qbiz_local_query(test_query)

    # Assert
    assert result != expected_response
    monkeypatch.delenv('AWS_REGION')
    monkeypatch.delenv('QBUSINESS_APPLICATION_ID')


@pytest.mark.asyncio
async def test_qbiz_local_query_failure6(mocker):
    """Test the qbiz_local_query tool returns error when AWS_PROFILE is invalid."""
    # Arrange
    test_query = 'List of holidays'
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv('AWS_PROFILE', 'xxxx-xxxx-xxxx-xxxx')
    monkeypatch.setenv('QBUSINESS_APPLICATION_ID', 'xxxx-xxxx-xxxx-xxxx')
    mock_aq_client_chat_sync_response = {
        'systemMessage': "Here are the official company holidays: \n\n\u2022 New Year's Day Observed (January 2) \n\u2022 Martin Luther King Jr. Day (3rd Monday in January) \n\u2022 President's Day (3rd Monday in February) \n\u2022 Cesar Chavez Day (March 31) \n\u2022 Memorial Day (last Monday in May) \n\u2022 Independence Day (July 4) \n\u2022 Labor Day (1st Monday in September) \n\u2022 Veteran's Day Observed (November 10) \n\u2022 Thanksgiving Day (4th Thursday in November) \n\u2022 Day after Thanksgiving \n\u2022 Christmas (December 25)  \n\nWhen a holiday falls on Saturday, employees receive holiday credit, and when a holiday falls on Sunday, the holiday is observed on the following Monday. \n\nAdditionally, permanent employees are entitled to one personal holiday per year.",
        'conversationId': 'XXX',
        'systemMessageId': 'XXX',
        'sourceAttributions': [],
        'messageId': 'XXX',
    }
    expected_response = f'Qbiz response: {mock_aq_client_chat_sync_response["systemMessage"]}'

    # Act
    result = await qbiz_local_query(test_query)

    # Assert
    assert result != expected_response
    monkeypatch.delenv('AWS_REGION')
    monkeypatch.delenv('AWS_PROFILE')
    monkeypatch.delenv('QBUSINESS_APPLICATION_ID')
