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

"""Tests for RDSDataAPIConnection."""

import pytest
from awslabs.mysql_mcp_server.connection.rds_data_api_connection import (
    RDSDataAPIConnection,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_execute_query_with_parameters_calls_client_correctly():
    """execute_query builds payload incl. parameters and calls boto client."""
    conn = RDSDataAPIConnection(
        cluster_arn='cluster',
        secret_arn='secret',
        database='db',
        region='us-east-1',
        readonly=False,
        is_test=True,
    )
    mock_client = MagicMock()
    mock_client.execute_statement.return_value = {'records': []}
    conn.data_client = mock_client

    # Run to_thread inline
    with patch(
        'awslabs.mysql_mcp_server.connection.rds_data_api_connection.asyncio.to_thread',
        new=AsyncMock(side_effect=lambda f, **kw: f(**kw)),
    ):
        params = [{'name': 'id', 'value': {'longValue': 1}}]
        out = await conn.execute_query('SELECT :id', parameters=params)

    assert out == {'records': []}
    mock_client.execute_statement.assert_called_once()
    called = mock_client.execute_statement.call_args.kwargs
    assert called['resourceArn'] == 'cluster'
    assert called['secretArn'] == 'secret'
    assert called['database'] == 'db'
    assert called['sql'] == 'SELECT :id'
    assert called['includeResultMetadata'] is True
    assert called['parameters'] == params


@pytest.mark.asyncio
async def test_execute_query_without_parameters_excludes_parameters_key():
    """execute_query omits 'parameters' when not provided."""
    conn = RDSDataAPIConnection(
        cluster_arn='cluster',
        secret_arn='secret',
        database='db',
        region='us-east-1',
        readonly=False,
        is_test=True,
    )
    mock_client = MagicMock()
    mock_client.execute_statement.return_value = {'records': []}
    conn.data_client = mock_client

    with patch(
        'awslabs.mysql_mcp_server.connection.rds_data_api_connection.asyncio.to_thread',
        new=AsyncMock(side_effect=lambda f, **kw: f(**kw)),
    ):
        await conn.execute_query('SELECT 1')

    called = mock_client.execute_statement.call_args.kwargs
    assert 'parameters' not in called


def test_init_creates_boto_client_when_not_test():
    """__init__ creates boto3 client when is_test=False."""
    with patch(
        'awslabs.mysql_mcp_server.connection.rds_data_api_connection.boto3.client'
    ) as mock_client:
        conn = RDSDataAPIConnection(
            cluster_arn='cluster',
            secret_arn='secret',
            database='db',
            region='us-west-2',
            readonly=True,
            is_test=False,
        )
        mock_client.assert_called_once_with('rds-data', region_name='us-west-2')
        assert hasattr(conn, 'data_client')


@pytest.mark.asyncio
async def test_close_is_noop():
    """close() is a no-op."""
    conn = RDSDataAPIConnection(
        cluster_arn='cluster',
        secret_arn='secret',
        database='db',
        region='us-east-1',
        readonly=False,
        is_test=True,
    )
    await conn.close()  # should not raise


@pytest.mark.asyncio
async def test_check_connection_health_true_when_records_present():
    """check_connection_health returns True when SELECT 1 yields rows."""
    conn = RDSDataAPIConnection(
        cluster_arn='cluster',
        secret_arn='secret',
        database='db',
        region='us-east-1',
        readonly=False,
        is_test=True,
    )
    conn.execute_query = AsyncMock(return_value={'records': [[{'longValue': 1}]]})
    assert await conn.check_connection_health() is True


@pytest.mark.asyncio
async def test_check_connection_health_false_when_no_records():
    """check_connection_health returns False on empty result."""
    conn = RDSDataAPIConnection(
        cluster_arn='cluster',
        secret_arn='secret',
        database='db',
        region='us-east-1',
        readonly=False,
        is_test=True,
    )
    conn.execute_query = AsyncMock(return_value={'records': []})
    assert await conn.check_connection_health() is False


@pytest.mark.asyncio
async def test_check_connection_health_false_on_exception():
    """check_connection_health returns False when execute_query raises."""
    conn = RDSDataAPIConnection(
        cluster_arn='cluster',
        secret_arn='secret',
        database='db',
        region='us-east-1',
        readonly=False,
        is_test=True,
    )
    conn.execute_query = AsyncMock(side_effect=Exception('fail'))
    assert await conn.check_connection_health() is False
