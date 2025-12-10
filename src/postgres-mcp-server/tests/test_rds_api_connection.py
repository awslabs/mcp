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
"""Tests for the RDS Data API connection functionality."""

import pytest
from awslabs.postgres_mcp_server.connection.rds_api_connection import RDSDataAPIConnection
from unittest.mock import ANY, MagicMock, patch


class TestRDSDataAPIConnection:
    """Tests for the RDSDataAPIConnection class."""

    @pytest.fixture
    def rds_connection(self):
        """Create a test RDS Data API connection."""
        return RDSDataAPIConnection(
            cluster_arn='arn:aws:rds:us-east-1:123456789012:cluster:test-cluster',
            secret_arn='arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret',
            database='test_db',
            region='us-east-1',
            readonly=False,
            is_test=True,
        )

    @pytest.fixture
    def rds_connection_readonly(self):
        """Create a test RDS Data API connection with readonly mode."""
        return RDSDataAPIConnection(
            cluster_arn='arn:aws:rds:us-east-1:123456789012:cluster:test-cluster',
            secret_arn='arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret',
            database='test_db',
            region='us-east-1',
            readonly=True,
            is_test=True,
        )

    def test_initialization(self, rds_connection):
        """Test that RDSDataAPIConnection initializes correctly."""
        assert (
            rds_connection.cluster_arn == 'arn:aws:rds:us-east-1:123456789012:cluster:test-cluster'
        )

    @pytest.mark.asyncio
    async def test_execute_query_with_transaction_rollback_on_error(self, rds_connection_readonly):
        """Test that transaction is rolled back when query execution fails in readonly mode."""
        # Mock the data client
        mock_client = MagicMock()
        rds_connection_readonly.data_client = mock_client

        # Mock begin_transaction to return a transaction ID
        mock_client.begin_transaction.return_value = {'transactionId': 'tx-12345'}

        # Mock first execute_statement (SET TRANSACTION READ ONLY) to succeed
        # Mock second execute_statement (actual query) to raise an exception
        mock_client.execute_statement.side_effect = [
            {},  # First call succeeds (SET TRANSACTION READ ONLY)
            Exception('Query execution failed'),  # Second call fails
        ]

        # Mock rollback_transaction
        mock_client.rollback_transaction.return_value = {}

        # Execute query and expect exception
        with pytest.raises(Exception, match='Query execution failed'):
            await rds_connection_readonly.execute_query('SELECT * FROM test_table')

        # Verify rollback was called with the transaction ID
        mock_client.rollback_transaction.assert_called_once_with(
            resourceArn='arn:aws:rds:us-east-1:123456789012:cluster:test-cluster',
            secretArn='arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret',
            transactionId='tx-12345',
        )

    @pytest.mark.asyncio
    async def test_execute_query_error_before_transaction_starts(self, rds_connection_readonly):
        """Test error handling when transaction fails to start (no tx_id)."""
        # Mock the data client
        mock_client = MagicMock()
        rds_connection_readonly.data_client = mock_client

        # Mock begin_transaction to raise an exception before returning tx_id
        mock_client.begin_transaction.side_effect = Exception('Failed to start transaction')

        # Mock rollback_transaction (should NOT be called since no tx_id)
        mock_client.rollback_transaction.return_value = {}

        # Execute query and expect exception
        with pytest.raises(Exception, match='Failed to start transaction'):
            await rds_connection_readonly.execute_query('SELECT * FROM test_table')

        # Verify rollback was NOT called (no transaction ID to rollback)
        mock_client.rollback_transaction.assert_not_called()

    def test_initialization_readonly(self, rds_connection_readonly):
        """Test that RDSDataAPIConnection initializes correctly in readonly mode."""
        assert rds_connection_readonly.readonly_query is True

    @pytest.mark.asyncio
    async def test_execute_query_without_parameters(self, rds_connection):
        """Test executing a query without parameters."""
        # Mock the data client
        mock_client = MagicMock()
        mock_client.execute_statement.return_value = {
            'columnMetadata': [{'name': 'result'}],
            'records': [[{'longValue': 1}]],
        }
        rds_connection.data_client = mock_client

        result = await rds_connection.execute_query('SELECT 1')

        # Verify the client was called correctly
        mock_client.execute_statement.assert_called_once()
        call_args = mock_client.execute_statement.call_args[1]
        assert call_args['resourceArn'] == rds_connection.cluster_arn
        assert call_args['secretArn'] == rds_connection.secret_arn
        assert call_args['database'] == rds_connection.database
        assert call_args['sql'] == 'SELECT 1'
        assert call_args['includeResultMetadata'] is True
        assert 'parameters' not in call_args

        # Verify result
        assert 'columnMetadata' in result
        assert 'records' in result

    @pytest.mark.asyncio
    async def test_execute_query_with_parameters(self, rds_connection):
        """Test executing a query with parameters."""
        # Mock the data client
        mock_client = MagicMock()
        mock_client.execute_statement.return_value = {
            'columnMetadata': [{'name': 'name'}],
            'records': [[{'stringValue': 'test'}]],
        }
        rds_connection.data_client = mock_client

        parameters = [{'name': 'id', 'value': {'longValue': 1}}]
        await rds_connection.execute_query('SELECT name FROM users WHERE id = :id', parameters)

        # Verify the client was called with parameters
        mock_client.execute_statement.assert_called_once()
        call_args = mock_client.execute_statement.call_args[1]
        assert call_args['parameters'] == parameters

    @pytest.mark.asyncio
    async def test_execute_query_readonly_mode(self, rds_connection_readonly):
        """Test executing a query in readonly mode."""
        # Mock the data client
        mock_client = MagicMock()
        mock_client.begin_transaction.return_value = {'transactionId': 'tx-123'}
        mock_client.execute_statement.return_value = {
            'columnMetadata': [{'name': 'result'}],
            'records': [[{'longValue': 1}]],
        }
        rds_connection_readonly.data_client = mock_client

        await rds_connection_readonly.execute_query('SELECT 1')

        # Verify transaction was started
        mock_client.begin_transaction.assert_called_once_with(
            resourceArn=rds_connection_readonly.cluster_arn,
            secretArn=rds_connection_readonly.secret_arn,
            database=rds_connection_readonly.database,
        )

        # Verify SET TRANSACTION READ ONLY was called
        assert mock_client.execute_statement.call_count == 2
        first_call = mock_client.execute_statement.call_args_list[0][1]
        assert first_call['sql'] == 'SET TRANSACTION READ ONLY'
        assert first_call['transactionId'] == 'tx-123'

        # Verify transaction was committed
        mock_client.commit_transaction.assert_called_once_with(
            resourceArn=rds_connection_readonly.cluster_arn,
            secretArn=rds_connection_readonly.secret_arn,
            transactionId='tx-123',
        )

    @pytest.mark.asyncio
    async def test_execute_query_readonly_with_parameters(self, rds_connection_readonly):
        """Test executing a query with parameters in readonly mode."""
        # Mock the data client
        mock_client = MagicMock()
        mock_client.begin_transaction.return_value = {'transactionId': 'tx-456'}
        mock_client.execute_statement.return_value = {
            'columnMetadata': [{'name': 'name'}],
            'records': [[{'stringValue': 'test'}]],
        }
        rds_connection_readonly.data_client = mock_client

        parameters = [{'name': 'id', 'value': {'longValue': 1}}]
        await rds_connection_readonly.execute_query(
            'SELECT name FROM users WHERE id = :id', parameters
        )

        # Verify the query was executed with parameters
        second_call = mock_client.execute_statement.call_args_list[1][1]
        assert second_call['parameters'] == parameters

    @pytest.mark.asyncio
    async def test_execute_query_readonly_rollback_on_error(self, rds_connection_readonly):
        """Test that readonly mode rolls back transaction on error."""
        # Mock the data client
        mock_client = MagicMock()
        mock_client.begin_transaction.return_value = {'transactionId': 'tx-789'}
        mock_client.execute_statement.side_effect = [
            None,  # SET TRANSACTION READ ONLY succeeds
            Exception('Query failed'),  # Actual query fails
        ]
        rds_connection_readonly.data_client = mock_client

        with pytest.raises(Exception, match='Query failed'):
            await rds_connection_readonly.execute_query('SELECT * FROM invalid_table')

        # Verify rollback was called
        mock_client.rollback_transaction.assert_called_once_with(
            resourceArn=rds_connection_readonly.cluster_arn,
            secretArn=rds_connection_readonly.secret_arn,
            transactionId='tx-789',
        )

        # Verify commit was NOT called
        mock_client.commit_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_close(self, rds_connection):
        """Test that close method completes without error."""
        # RDS Data API doesn't maintain persistent connections, so close should be a no-op
        await rds_connection.close()
        # If we get here without exception, the test passes

    @pytest.mark.asyncio
    async def test_check_connection_health_success(self, rds_connection):
        """Test connection health check when connection is healthy."""
        # Mock the data client
        mock_client = MagicMock()
        mock_client.execute_statement.return_value = {
            'columnMetadata': [{'name': 'result'}],
            'records': [[{'longValue': 1}]],
        }
        rds_connection.data_client = mock_client

        is_healthy = await rds_connection.check_connection_health()

        assert is_healthy is True
        mock_client.execute_statement.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_health_failure(self, rds_connection):
        """Test connection health check when connection fails."""
        # Mock the data client to raise an exception
        mock_client = MagicMock()
        mock_client.execute_statement.side_effect = Exception('Connection failed')
        rds_connection.data_client = mock_client

        is_healthy = await rds_connection.check_connection_health()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_check_connection_health_empty_result(self, rds_connection):
        """Test connection health check when query returns empty result."""
        # Mock the data client to return empty records
        mock_client = MagicMock()
        mock_client.execute_statement.return_value = {
            'columnMetadata': [{'name': 'result'}],
            'records': [],
        }
        rds_connection.data_client = mock_client

        is_healthy = await rds_connection.check_connection_health()

        assert is_healthy is False

    @patch('boto3.client')
    def test_initialization_with_boto3_client(self, mock_boto_client):
        """Test that RDSDataAPIConnection creates boto3 client when not in test mode."""
        mock_rds_data_client = MagicMock()
        mock_boto_client.return_value = mock_rds_data_client

        conn = RDSDataAPIConnection(
            cluster_arn='arn:aws:rds:us-east-1:123456789012:cluster:test-cluster',
            secret_arn='arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret',
            database='test_db',
            region='us-east-1',
            readonly=False,
            is_test=False,  # Not in test mode
        )

        # Verify boto3.client was called
        mock_boto_client.assert_called_once_with('rds-data', region_name='us-east-1', config=ANY)
        assert conn.data_client == mock_rds_data_client
