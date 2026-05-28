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

"""Tests for RDSDataAPIConnection with mocked boto3 Data API calls."""

import pytest
from awslabs.mysql_mcp_server.connection.rds_api_connection import RDSDataAPIConnection
from unittest.mock import MagicMock, patch


class TestRDSDataAPIConnectionInit:
    """Tests for RDSDataAPIConnection initialization."""

    def test_init_test_mode(self):
        """Should initialize without creating boto3 client in test mode."""
        conn = RDSDataAPIConnection(
            cluster_arn='arn:aws:rds:us-east-1:123456789012:cluster:my-cluster',
            secret_arn='arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret',
            database='testdb',
            region='us-east-1',
            readonly=True,
            is_test=True,
        )
        assert conn.cluster_arn == 'arn:aws:rds:us-east-1:123456789012:cluster:my-cluster'
        assert conn.secret_arn == 'arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret'
        assert conn.database == 'testdb'
        assert conn.readonly_query is True

    def test_init_readonly_false(self):
        """Should set readonly to False."""
        conn = RDSDataAPIConnection(
            cluster_arn='arn:cluster',
            secret_arn='arn:secret',
            database='testdb',
            region='us-east-1',
            readonly=False,
            is_test=True,
        )
        assert conn.readonly_query is False

    @patch('awslabs.mysql_mcp_server.connection.rds_api_connection.boto3.client')
    def test_init_creates_client(self, mock_boto_client):
        """Should create rds-data client when not in test mode."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        conn = RDSDataAPIConnection(
            cluster_arn='arn:cluster',
            secret_arn='arn:secret',
            database='testdb',
            region='us-east-1',
            readonly=True,
            is_test=False,
        )
        mock_boto_client.assert_called_once()
        assert conn.data_client is mock_client


class TestRDSDataAPIConnectionExecuteQuery:
    """Tests for execute_query."""

    def _make_conn(self, readonly=True):
        """Create a test connection with a mocked data_client."""
        conn = RDSDataAPIConnection(
            cluster_arn='arn:cluster',
            secret_arn='arn:secret',
            database='testdb',
            region='us-east-1',
            readonly=readonly,
            is_test=True,
        )
        conn.data_client = MagicMock()
        return conn

    async def test_execute_query_readonly(self):
        """Should use read-only transaction when readonly is True."""
        conn = self._make_conn(readonly=True)

        conn.data_client.begin_transaction.return_value = {'transactionId': 'tx-123'}
        conn.data_client.execute_statement.return_value = {
            'columnMetadata': [{'name': 'id'}],
            'records': [[{'longValue': 1}]],
        }
        conn.data_client.commit_transaction.return_value = {}

        result = await conn.execute_query('SELECT 1')

        conn.data_client.begin_transaction.assert_called_once()
        # Only the actual query should be executed (no SET TRANSACTION READ ONLY)
        assert conn.data_client.execute_statement.call_count == 1
        conn.data_client.commit_transaction.assert_called_once()
        assert result['records'] == [[{'longValue': 1}]]

    async def test_execute_query_writable(self):
        """Should execute directly when readonly is False."""
        conn = self._make_conn(readonly=False)

        conn.data_client.execute_statement.return_value = {
            'columnMetadata': [{'name': 'count'}],
            'records': [[{'longValue': 5}]],
        }

        result = await conn.execute_query('INSERT INTO t VALUES (1)')  # noqa: F841

        conn.data_client.execute_statement.assert_called_once()
        conn.data_client.begin_transaction.assert_not_called()

    async def test_execute_query_with_parameters(self):
        """Should pass parameters to execute_statement."""
        conn = self._make_conn(readonly=False)

        conn.data_client.execute_statement.return_value = {
            'columnMetadata': [],
            'records': [],
        }

        params = [{'name': 'id', 'value': {'longValue': 42}}]
        await conn.execute_query('SELECT * FROM t WHERE id = :id', params)

        call_kwargs = conn.data_client.execute_statement.call_args[1]
        assert call_kwargs['parameters'] == params

    async def test_execute_query_readonly_with_parameters(self):
        """Should pass parameters in readonly transaction."""
        conn = self._make_conn(readonly=True)

        conn.data_client.begin_transaction.return_value = {'transactionId': 'tx-456'}
        conn.data_client.execute_statement.return_value = {
            'columnMetadata': [],
            'records': [],
        }
        conn.data_client.commit_transaction.return_value = {}

        params = [{'name': 'name', 'value': {'stringValue': 'test'}}]
        await conn.execute_query('SELECT * FROM t WHERE name = :name', params)

        # Only the actual query should be executed
        calls = conn.data_client.execute_statement.call_args_list
        assert len(calls) == 1
        # First (and only) call is the actual query with parameters
        assert calls[0][1].get('parameters') == params

    async def test_execute_query_readonly_rollback_on_error(self):
        """Should rollback transaction on error in readonly mode."""
        conn = self._make_conn(readonly=True)

        conn.data_client.begin_transaction.return_value = {'transactionId': 'tx-789'}
        conn.data_client.execute_statement.side_effect = RuntimeError('query failed')

        with pytest.raises(RuntimeError, match='query failed'):
            await conn.execute_query('SELECT bad_query')

        conn.data_client.rollback_transaction.assert_called_once_with(
            resourceArn='arn:cluster',
            secretArn='arn:secret',
            transactionId='tx-789',
        )

    async def test_execute_query_writable_no_params(self):
        """Should not include parameters key when params is None."""
        conn = self._make_conn(readonly=False)

        conn.data_client.execute_statement.return_value = {
            'columnMetadata': [],
            'records': [],
        }

        await conn.execute_query('SELECT 1')

        call_kwargs = conn.data_client.execute_statement.call_args[1]
        assert 'parameters' not in call_kwargs


class TestRDSDataAPIConnectionClose:
    """Tests for close."""

    async def test_close_does_nothing(self):
        """RDS Data API close should be a no-op."""
        conn = RDSDataAPIConnection(
            cluster_arn='arn:cluster',
            secret_arn='arn:secret',
            database='testdb',
            region='us-east-1',
            readonly=True,
            is_test=True,
        )
        await conn.close()  # Should not raise


class TestRDSDataAPIConnectionHealthCheck:
    """Tests for check_connection_health."""

    async def test_health_check_healthy(self):
        """Should return True when SELECT 1 succeeds."""
        conn = RDSDataAPIConnection(
            cluster_arn='arn:cluster',
            secret_arn='arn:secret',
            database='testdb',
            region='us-east-1',
            readonly=False,
            is_test=True,
        )
        conn.data_client = MagicMock()
        conn.data_client.execute_statement.return_value = {
            'columnMetadata': [{'name': '1'}],
            'records': [[{'longValue': 1}]],
        }

        result = await conn.check_connection_health()
        assert result is True

    async def test_health_check_unhealthy(self):
        """Should return False when query fails."""
        conn = RDSDataAPIConnection(
            cluster_arn='arn:cluster',
            secret_arn='arn:secret',
            database='testdb',
            region='us-east-1',
            readonly=False,
            is_test=True,
        )
        conn.data_client = MagicMock()
        conn.data_client.execute_statement.side_effect = RuntimeError('connection lost')

        result = await conn.check_connection_health()
        assert result is False

    async def test_health_check_empty_records(self):
        """Should return False when no records returned."""
        conn = RDSDataAPIConnection(
            cluster_arn='arn:cluster',
            secret_arn='arn:secret',
            database='testdb',
            region='us-east-1',
            readonly=False,
            is_test=True,
        )
        conn.data_client = MagicMock()
        conn.data_client.execute_statement.return_value = {
            'columnMetadata': [],
            'records': [],
        }

        result = await conn.check_connection_health()
        assert result is False
