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

"""Tests for create_schema operation."""

import pytest
from awslabs.aws_appsync_mcp_server.operations.create_schema import create_schema_operation
from unittest.mock import AsyncMock, Mock, patch


class TestCreateSchemaOperation:
    """Test cases for create_schema_operation function."""

    @pytest.mark.asyncio
    async def test_validation_failure_empty_schema(self):
        """Test that empty schema fails validation before AWS call."""
        with pytest.raises(
            ValueError, match='Schema validation failed: Schema definition cannot be empty'
        ):
            await create_schema_operation('test-api-id', '')

    @pytest.mark.asyncio
    async def test_validation_failure_missing_query(self):
        """Test that schema without Query type fails validation."""
        schema = 'type User { id: ID! }'
        with pytest.raises(
            ValueError, match='Schema validation failed: Schema must include a Query type'
        ):
            await create_schema_operation('test-api-id', schema)

    @pytest.mark.asyncio
    async def test_validation_failure_unbalanced_braces(self):
        """Test that schema with unbalanced braces fails validation."""
        schema = 'type Query { hello: String'
        with pytest.raises(ValueError, match='Schema validation failed: Unbalanced braces'):
            await create_schema_operation('test-api-id', schema)

    @pytest.mark.asyncio
    async def test_validation_failure_multiple_issues(self):
        """Test that schema with multiple issues fails validation."""
        schema = 'type User { id: ID!'
        with pytest.raises(ValueError, match='Schema validation failed'):
            await create_schema_operation('test-api-id', schema)

    @pytest.mark.asyncio
    @patch('awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client')
    async def test_successful_schema_creation(self, mock_get_client):
        """Test successful schema creation with polling."""
        # Setup mocks
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_client.start_schema_creation.return_value = {'status': 'PROCESSING'}
        mock_client.get_schema_creation_status.return_value = {
            'status': 'SUCCESS',
            'details': 'Schema created successfully',
        }

        schema = 'type Query { hello: String }'
        result = await create_schema_operation('test-api-id', schema)

        # Verify calls
        mock_client.start_schema_creation.assert_called_once_with(
            apiId='test-api-id', definition=schema
        )
        mock_client.get_schema_creation_status.assert_called_once_with(apiId='test-api-id')

        # Verify result
        assert result['status'] == 'SUCCESS'
        assert result['details'] == 'Schema created successfully'

    @pytest.mark.asyncio
    @patch('awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client')
    async def test_failed_schema_creation(self, mock_get_client):
        """Test failed schema creation."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_client.start_schema_creation.return_value = {'status': 'PROCESSING'}
        mock_client.get_schema_creation_status.return_value = {
            'status': 'FAILED',
            'details': 'Invalid schema syntax',
        }

        schema = 'type Query { hello: String }'
        result = await create_schema_operation('test-api-id', schema)

        assert result['status'] == 'FAILED'
        assert result['details'] == 'Invalid schema syntax'

    @pytest.mark.asyncio
    @patch('awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client')
    @patch('awslabs.aws_appsync_mcp_server.operations.create_schema.time.time')
    async def test_timeout_handling(self, mock_time, mock_get_client):
        """Test timeout during schema creation polling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_client.start_schema_creation.return_value = {'status': 'PROCESSING'}
        mock_client.get_schema_creation_status.return_value = {'status': 'PROCESSING'}

        # Mock time to simulate timeout
        mock_time.side_effect = [0, 301]  # Start time, then past timeout

        schema = 'type Query { hello: String }'

        with pytest.raises(TimeoutError, match='Schema creation timed out after 300 seconds'):
            await create_schema_operation('test-api-id', schema)

    @pytest.mark.asyncio
    @patch('awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client')
    @patch(
        'awslabs.aws_appsync_mcp_server.operations.create_schema.asyncio.sleep',
        new_callable=AsyncMock,
    )
    async def test_polling_until_success(self, mock_sleep, mock_get_client):
        """Test polling continues until success status."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_client.start_schema_creation.return_value = {'status': 'PROCESSING'}

        # Simulate multiple status checks before success
        status_responses = [
            {'status': 'PROCESSING'},
            {'status': 'PROCESSING'},
            {'status': 'SUCCESS', 'details': 'Complete'},
        ]
        mock_client.get_schema_creation_status.side_effect = status_responses

        schema = 'type Query { hello: String }'
        result = await create_schema_operation('test-api-id', schema)

        # Verify polling occurred
        assert mock_client.get_schema_creation_status.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep called between polls
        mock_sleep.assert_called_with(2)

        assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    @patch('awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client')
    async def test_all_terminal_statuses(self, mock_get_client):
        """Test all terminal status values are handled."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        mock_client.start_schema_creation.return_value = {'status': 'PROCESSING'}

        terminal_statuses = ['SUCCESS', 'FAILED', 'ACTIVE', 'NOT_APPLICABLE']

        for status in terminal_statuses:
            mock_client.get_schema_creation_status.return_value = {
                'status': status,
                'details': f'Status: {status}',
            }

            schema = 'type Query { hello: String }'
            result = await create_schema_operation('test-api-id', schema)

            assert result['status'] == status
            assert result['details'] == f'Status: {status}'
