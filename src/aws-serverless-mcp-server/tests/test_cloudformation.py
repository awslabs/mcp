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
"""Tests for the cloudformation utility module."""

import pytest
from awslabs.aws_serverless_mcp_server.utils.cloudformation import (
    get_stack_info,
    map_cloudformation_status,
)
from botocore.exceptions import ClientError
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestCloudFormation:
    """Tests for the cloudformation utility module."""

    @pytest.mark.asyncio
    async def test_get_stack_info_success(self):
        """Test get_stack_info with a successful response."""
        # Mock the CloudFormation client
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client

        # Mock the response from describe_stacks
        creation_time = datetime.now()
        last_updated_time = datetime.now()
        mock_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackStatus': 'CREATE_COMPLETE',
                    'StackStatusReason': 'Stack creation completed successfully',
                    'LastUpdatedTime': last_updated_time,
                    'CreationTime': creation_time,
                    'Outputs': [
                        {'OutputKey': 'ApiUrl', 'OutputValue': 'https://api.example.com'},
                        {'OutputKey': 'FunctionName', 'OutputValue': 'test-function'},
                    ],
                }
            ]
        }

        # Patch boto3.Session to return our mock session
        with patch('boto3.Session', return_value=mock_session):
            # Call the function
            stack_name = 'test-stack'
            result = await get_stack_info(stack_name)

            # Verify the result
            assert result['status'] == 'CREATE_COMPLETE'
            assert result['statusReason'] == 'Stack creation completed successfully'
            assert result['lastUpdatedTime'] == last_updated_time.isoformat()
            assert result['creationTime'] == creation_time.isoformat()
            assert result['outputs'] == {
                'ApiUrl': 'https://api.example.com',
                'FunctionName': 'test-function',
            }

            # Verify the client was called correctly
            mock_session.client.assert_called_once_with('cloudformation')
            mock_client.describe_stacks.assert_called_once_with(StackName=stack_name)

    @pytest.mark.asyncio
    async def test_get_stack_info_with_region(self):
        """Test get_stack_info with a specified region."""
        # Mock the CloudFormation client
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client

        # Mock the response from describe_stacks
        creation_time = datetime.now()
        last_updated_time = datetime.now()
        mock_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackStatus': 'UPDATE_COMPLETE',
                    'StackStatusReason': 'Stack update completed successfully',
                    'LastUpdatedTime': last_updated_time,
                    'CreationTime': creation_time,
                    'Outputs': [],
                }
            ]
        }

        # Patch boto3.Session to return our mock session
        with patch('boto3.Session', return_value=mock_session):
            # Call the function with a region
            stack_name = 'test-stack'
            region = 'us-west-2'
            result = await get_stack_info(stack_name, region)

            # Verify the result
            assert result['status'] == 'UPDATE_COMPLETE'
            assert result['statusReason'] == 'Stack update completed successfully'

            # Verify the session was created with the correct region
            mock_session.client.assert_called_once_with('cloudformation')
            mock_client.describe_stacks.assert_called_once_with(StackName=stack_name)

    @pytest.mark.asyncio
    async def test_get_stack_info_not_found(self):
        """Test get_stack_info when the stack is not found."""
        # Mock the CloudFormation client
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client

        # Mock the ClientError exception
        error_response = {'Error': {'Code': 'ValidationError', 'Message': 'Stack does not exist'}}
        mock_client.exceptions = MagicMock()
        mock_client.exceptions.ClientError = ClientError
        mock_client.describe_stacks.side_effect = ClientError(error_response, 'DescribeStacks')

        # Patch boto3.Session to return our mock session
        with patch('boto3.Session', return_value=mock_session):
            # Call the function
            stack_name = 'nonexistent-stack'
            result = await get_stack_info(stack_name)

            # Verify the result
            assert result['status'] == 'NOT_FOUND'
            assert f'Stack {stack_name} not found' in result['message']

    @pytest.mark.asyncio
    async def test_get_stack_info_empty_response(self):
        """Test get_stack_info with an empty response."""
        # Mock the CloudFormation client
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client

        # Mock an empty response
        mock_client.describe_stacks.return_value = {}

        # Patch boto3.Session to return our mock session
        with patch('boto3.Session', return_value=mock_session):
            # Call the function
            stack_name = 'test-stack'
            result = await get_stack_info(stack_name)

            # Verify the result
            assert result['status'] == 'NOT_FOUND'
            assert f'Stack {stack_name} not found' in result['message']

    @pytest.mark.asyncio
    async def test_get_stack_info_other_exception(self):
        """Test get_stack_info when another exception occurs."""
        # Mock the CloudFormation client
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client

        # Mock a general exception
        mock_client.exceptions = MagicMock()
        mock_client.exceptions.ClientError = ClientError
        mock_client.describe_stacks.side_effect = Exception('Test exception')

        # Patch boto3.Session to return our mock session
        with patch('boto3.Session', return_value=mock_session):
            # Call the function and expect an exception
            stack_name = 'test-stack'
            with pytest.raises(Exception, match='Test exception'):
                await get_stack_info(stack_name)

    def test_map_cloudformation_status(self):
        """Test the map_cloudformation_status function."""
        # Test successful deployments
        assert map_cloudformation_status('CREATE_COMPLETE') == 'DEPLOYED'
        assert map_cloudformation_status('UPDATE_COMPLETE') == 'DEPLOYED'

        # Test deletion
        assert map_cloudformation_status('DELETE_COMPLETE') == 'DELETED'

        # Test failures
        assert map_cloudformation_status('CREATE_FAILED') == 'FAILED'
        assert map_cloudformation_status('UPDATE_FAILED') == 'FAILED'
        assert map_cloudformation_status('DELETE_FAILED') == 'FAILED'

        # Test in-progress statuses
        assert map_cloudformation_status('CREATE_IN_PROGRESS') == 'IN_PROGRESS'
        assert map_cloudformation_status('UPDATE_IN_PROGRESS') == 'IN_PROGRESS'
        assert map_cloudformation_status('DELETE_IN_PROGRESS') == 'IN_PROGRESS'

        # Test not found
        assert map_cloudformation_status('NOT_FOUND') == 'NOT_FOUND'

        # Test unknown status
        assert map_cloudformation_status('SOME_UNKNOWN_STATUS') == 'UNKNOWN'
