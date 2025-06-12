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

"""Tests for create_log_group tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.cwlogs.create_log_group import create_log_group
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_log_group_basic():
    """Test basic create_log_group functionality."""
    # Mock successful response
    mock_client = MagicMock()
    mock_client.create_log_group.return_value = {}
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call the function
        result = await create_log_group(log_group_name='test-group')

        # Verify the client was called correctly
        mock_client.create_log_group.assert_called_once_with(logGroupName='test-group')

        # Verify the response
        assert 'message' in result
        assert 'Successfully created log group: test-group' in result['message']


@pytest.mark.asyncio
async def test_create_log_group_with_all_params():
    """Test create_log_group with all optional parameters."""
    # Mock successful response
    mock_client = MagicMock()
    mock_client.create_log_group.return_value = {}
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call with all parameters
        result = await create_log_group(
            log_group_name='test-group',
            kms_key_id='arn:aws:kms:region:account:key/id',
            tags={'env': 'test', 'project': 'mcp'},
            log_group_class='INFREQUENT_ACCESS',
        )

        # Verify all parameters were passed correctly
        mock_client.create_log_group.assert_called_once_with(
            logGroupName='test-group',
            kmsKeyId='arn:aws:kms:region:account:key/id',
            tags={'env': 'test', 'project': 'mcp'},
            logGroupClass='INFREQUENT_ACCESS',
        )

        # Verify the response
        assert 'message' in result
        assert 'Successfully created log group: test-group' in result['message']


@pytest.mark.asyncio
async def test_create_log_group_error():
    """Test create_log_group error handling."""
    # Mock error response
    mock_client = MagicMock()
    mock_client.create_log_group.side_effect = ClientError(
        {
            'Error': {
                'Code': 'ResourceAlreadyExistsException',
                'Message': 'Log group already exists',
            }
        },
        'CreateLogGroup',
    )
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call the function and verify error is handled
        result = await create_log_group(log_group_name='existing-group')

        assert 'error' in result
        assert 'Log group already exists' in result['error']
