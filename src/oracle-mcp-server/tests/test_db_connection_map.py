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

"""Tests for DBConnectionMap."""

import pytest
from awslabs.oracle_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DBConnectionMap,
)
from unittest.mock import MagicMock


@pytest.fixture
def conn_map():
    """Create a fresh DBConnectionMap."""
    return DBConnectionMap()


@pytest.fixture
def mock_conn():
    """Create a mock database connection."""
    return MagicMock()


def test_set_and_get(conn_map, mock_conn):
    """Set a connection and retrieve it by key."""
    conn_map.set(ConnectionMethod.ORACLE_PASSWORD, 'inst1', 'endpoint1', 'db1', mock_conn, 1521)
    result = conn_map.get(ConnectionMethod.ORACLE_PASSWORD, 'inst1', 'endpoint1', 'db1', 1521)
    assert result is mock_conn


def test_get_missing_returns_none(conn_map):
    """Get returns None for a key that was never set."""
    result = conn_map.get(ConnectionMethod.ORACLE_PASSWORD, 'noexist', 'noendpoint', 'nodb', 1521)
    assert result is None


def test_remove(conn_map, mock_conn):
    """Remove deletes a connection so get returns None."""
    conn_map.set(ConnectionMethod.ORACLE_PASSWORD, 'inst2', 'ep2', 'db2', mock_conn, 1521)
    conn_map.remove(ConnectionMethod.ORACLE_PASSWORD, 'inst2', 'ep2', 'db2', 1521)
    result = conn_map.get(ConnectionMethod.ORACLE_PASSWORD, 'inst2', 'ep2', 'db2', 1521)
    assert result is None


def test_remove_nonexistent_does_not_raise(conn_map):
    """Removing a non-existent key does not raise."""
    conn_map.remove(ConnectionMethod.ORACLE_PASSWORD, 'ghost', 'ep', 'db', 1521)


def test_get_keys(conn_map, mock_conn):
    """get_keys returns a list of dicts describing stored connections."""
    mock_conn.service_name = 'ORCL'
    mock_conn.sid = None
    conn_map.set(ConnectionMethod.ORACLE_PASSWORD, 'i1', 'e1', 'd1', mock_conn, 1521)
    keys = conn_map.get_keys()
    assert len(keys) == 1
    assert keys[0]['instance_identifier'] == 'i1'
    assert keys[0]['service_name'] == 'ORCL'
    assert keys[0]['sid'] is None


def test_get_keys_with_sid(conn_map):
    """get_keys returns sid when connection uses SID instead of service_name."""
    conn = MagicMock()
    conn.service_name = None
    conn.sid = 'MYSID'
    conn_map.set(ConnectionMethod.ORACLE_PASSWORD, 'i1', 'e1', 'd1', conn, 1521)
    keys = conn_map.get_keys()
    assert len(keys) == 1
    assert keys[0]['service_name'] is None
    assert keys[0]['sid'] == 'MYSID'


def test_close_all(conn_map, mock_conn):
    """close_all closes every connection and empties the map."""
    conn_map.set(ConnectionMethod.ORACLE_PASSWORD, 'i1', 'e1', 'd1', mock_conn, 1521)
    conn_map.close_all()
    assert len(conn_map.map) == 0


def test_set_empty_database_raises(conn_map, mock_conn):
    """Setting a connection with an empty database name raises ValueError."""
    with pytest.raises(ValueError):
        conn_map.set(ConnectionMethod.ORACLE_PASSWORD, 'i1', 'e1', '', mock_conn, 1521)


def test_set_none_conn_raises(conn_map):
    """Setting a None connection raises ValueError."""
    with pytest.raises(ValueError):
        conn_map.set(ConnectionMethod.ORACLE_PASSWORD, 'i1', 'e1', 'db1', None, 1521)


def test_default_port_1521(conn_map, mock_conn):
    """Port defaults to 1521 when omitted."""
    conn_map.set(ConnectionMethod.ORACLE_PASSWORD, 'i1', 'e1', 'db1', mock_conn)
    result = conn_map.get(ConnectionMethod.ORACLE_PASSWORD, 'i1', 'e1', 'db1')
    assert result is mock_conn


def test_get_fallback_by_endpoint_when_identifier_differs(conn_map, mock_conn):
    """When stored with a short instance_identifier, lookup by endpoint alone still finds it."""
    conn_map.set(
        ConnectionMethod.ORACLE_PASSWORD,
        'my-instance',
        'my-instance.rds.amazonaws.com',
        'ORCL',
        mock_conn,
        1521,
    )
    # Caller passes db_endpoint as both args (no explicit instance_identifier)
    result = conn_map.get(
        ConnectionMethod.ORACLE_PASSWORD,
        'my-instance.rds.amazonaws.com',
        'my-instance.rds.amazonaws.com',
        'ORCL',
        1521,
    )
    assert result is mock_conn


def test_get_no_fallback_when_identifier_differs_and_not_endpoint(conn_map, mock_conn):
    """Fallback only triggers when instance_identifier equals db_endpoint (i.e. was defaulted)."""
    conn_map.set(
        ConnectionMethod.ORACLE_PASSWORD, 'inst-a', 'ep.rds.amazonaws.com', 'ORCL', mock_conn, 1521
    )
    # Explicit wrong identifier — no fallback should occur
    result = conn_map.get(
        ConnectionMethod.ORACLE_PASSWORD,
        'inst-b',
        'ep.rds.amazonaws.com',
        'ORCL',
        1521,
    )
    assert result is None


def test_get_exact_match_takes_priority_over_fallback(conn_map):
    """Exact key match is returned even when a fallback candidate also exists."""
    conn_exact = MagicMock()
    conn_fallback = MagicMock()
    endpoint = 'ep.rds.amazonaws.com'
    conn_map.set(ConnectionMethod.ORACLE_PASSWORD, endpoint, endpoint, 'ORCL', conn_exact, 1521)
    conn_map.set(
        ConnectionMethod.ORACLE_PASSWORD, 'short-name', endpoint, 'ORCL', conn_fallback, 1521
    )
    result = conn_map.get(ConnectionMethod.ORACLE_PASSWORD, endpoint, endpoint, 'ORCL', 1521)
    assert result is conn_exact
