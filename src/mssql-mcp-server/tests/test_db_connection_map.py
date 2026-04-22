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
from awslabs.mssql_mcp_server.connection.db_connection_map import ConnectionMethod, DBConnectionMap
from unittest.mock import MagicMock


@pytest.fixture
def conn_map():
    """Fixture providing an empty DBConnectionMap."""
    return DBConnectionMap()


@pytest.fixture
def mock_conn():
    """Fixture providing a MagicMock connection."""
    return MagicMock()


def test_set_and_get(conn_map, mock_conn):
    """set() stores a connection that get() can retrieve."""
    conn_map.set(ConnectionMethod.MSSQL_PASSWORD, 'inst1', 'endpoint1', 'db1', mock_conn, 1433)
    result = conn_map.get(ConnectionMethod.MSSQL_PASSWORD, 'inst1', 'endpoint1', 'db1', 1433)
    assert result is mock_conn


def test_get_missing_returns_none(conn_map):
    """get() returns None for an unknown key."""
    result = conn_map.get(ConnectionMethod.MSSQL_PASSWORD, 'noexist', 'noendpoint', 'nodb', 1433)
    assert result is None


def test_remove(conn_map, mock_conn):
    """remove() deletes the stored connection."""
    conn_map.set(ConnectionMethod.MSSQL_PASSWORD, 'inst2', 'ep2', 'db2', mock_conn, 1433)
    conn_map.remove(ConnectionMethod.MSSQL_PASSWORD, 'inst2', 'ep2', 'db2', 1433)
    result = conn_map.get(ConnectionMethod.MSSQL_PASSWORD, 'inst2', 'ep2', 'db2', 1433)
    assert result is None


def test_remove_nonexistent_does_not_raise(conn_map):
    """remove() on a missing key does not raise."""
    conn_map.remove(ConnectionMethod.MSSQL_PASSWORD, 'ghost', 'ep', 'db', 1433)


def test_get_keys_json(conn_map, mock_conn):
    """get_keys_json() returns JSON containing stored connection identifiers."""
    conn_map.set(ConnectionMethod.MSSQL_PASSWORD, 'i1', 'e1', 'd1', mock_conn, 1433)
    keys_json = conn_map.get_keys_json()
    assert 'instance_identifier' in keys_json
    assert 'i1' in keys_json


def test_close_all(conn_map, mock_conn):
    """close_all() empties the map."""
    conn_map.set(ConnectionMethod.MSSQL_PASSWORD, 'i1', 'e1', 'd1', mock_conn, 1433)
    conn_map.close_all()
    assert len(conn_map.map) == 0


def test_set_empty_database_raises(conn_map, mock_conn):
    """set() raises ValueError when database is empty."""
    with pytest.raises(ValueError):
        conn_map.set(ConnectionMethod.MSSQL_PASSWORD, 'i1', 'e1', '', mock_conn, 1433)


def test_set_none_conn_raises(conn_map):
    """set() raises ValueError when connection is None."""
    with pytest.raises(ValueError):
        conn_map.set(ConnectionMethod.MSSQL_PASSWORD, 'i1', 'e1', 'db1', None, 1433)


def test_default_port_1433(conn_map, mock_conn):
    """set() and get() default to port 1433."""
    conn_map.set(ConnectionMethod.MSSQL_PASSWORD, 'i1', 'e1', 'db1', mock_conn)
    result = conn_map.get(ConnectionMethod.MSSQL_PASSWORD, 'i1', 'e1', 'db1')
    assert result is mock_conn
