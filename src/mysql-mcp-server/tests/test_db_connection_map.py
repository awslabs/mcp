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

"""Tests for DBConnectionMap with MySQL enums."""

import json
import pytest
from awslabs.mysql_mcp_server.connection.db_connection_map import (
    SUPPORTED_CONNECTION_METHODS,
    ConnectionMethod,
    DatabaseType,
    DBConnectionMap,
    is_connection_method_supported,
)
from unittest.mock import AsyncMock, MagicMock


class TestDatabaseType:
    """Tests for DatabaseType enum.

    The enum values are pinned to AWS RDS engine strings so they can be
    forwarded directly into boto3 ``create_db_cluster`` / ``create_db_instance``
    calls. Renaming any of these values is a breaking change to both the
    MCP tool API (LLM prompts pass the value as a string) and to the
    internal cluster-creation code that uses ``database_type.value`` as
    the AWS Engine field. Test names spell out engines in full.
    """

    def test_aurora_mysql_value(self):
        """AURORA_MYSQL pins to AWS RDS engine string 'aurora-mysql'."""
        assert DatabaseType.AURORA_MYSQL.value == 'aurora-mysql'

    def test_rds_mysql_value(self):
        """RDS_MYSQL pins to AWS RDS engine string 'mysql'."""
        assert DatabaseType.RDS_MYSQL.value == 'mysql'

    def test_rds_mariadb_value(self):
        """RDS_MARIADB pins to AWS RDS engine string 'mariadb'."""
        assert DatabaseType.RDS_MARIADB.value == 'mariadb'

    def test_enum_members_exhaustive(self):
        """DatabaseType members are exactly the three RDS-managed engines.

        Self-hosted MySQL/MariaDB intentionally has no enum value; the
        wire-protocol path takes any host without requiring an engine type.
        """
        members = list(DatabaseType)
        assert len(members) == 3, (
            f'Expected exactly 3 RDS-managed engine types, found {len(members)}: '
            f'{[m.name for m in members]}. If a new engine was added, also add a '
            'row to SUPPORTED_CONNECTION_METHODS and update the routing tests.'
        )
        assert {m.name for m in members} == {'AURORA_MYSQL', 'RDS_MYSQL', 'RDS_MARIADB'}

    def test_value_is_str_subclass(self):
        """Values must be str-subtype so boto3 accepts them as Engine field."""
        for member in DatabaseType:
            assert isinstance(member.value, str)
            assert isinstance(member, str), (
                f'{member.name} is not a str subclass; '
                'boto3 requires str for the Engine parameter.'
            )

    def test_lookup_by_aws_engine_string(self):
        """DatabaseType('aurora-mysql') resolves to AURORA_MYSQL.

        This is the lookup the CLI uses when the user passes
        --db_type aurora-mysql.
        """
        assert DatabaseType('aurora-mysql') is DatabaseType.AURORA_MYSQL
        assert DatabaseType('mysql') is DatabaseType.RDS_MYSQL
        assert DatabaseType('mariadb') is DatabaseType.RDS_MARIADB

    def test_lookup_with_unknown_value_raises(self):
        """Unknown engine strings must raise ValueError, not return None."""
        with pytest.raises(ValueError):
            DatabaseType('postgres')
        with pytest.raises(ValueError):
            DatabaseType('aurora-postgresql')
        with pytest.raises(ValueError):
            DatabaseType('')

    def test_lookup_is_case_sensitive(self):
        """Engine strings are lowercase per AWS RDS API. Mixed-case must fail.

        Pinning to AWS's canonical lowercase prevents confusion in error
        messages and makes the supported-methods table unambiguous.
        """
        with pytest.raises(ValueError):
            DatabaseType('Aurora-MySQL')
        with pytest.raises(ValueError):
            DatabaseType('AURORA-MYSQL')
        with pytest.raises(ValueError):
            DatabaseType('MySQL')


class TestSupportedConnectionMethods:
    """Tests for the (engine, connection method) supported-methods table.

    The table is the single source of truth for which engine/method pairs
    are valid. Every combination is exercised here so a regression that
    silently changes the table gets caught.
    """

    def test_aurora_mysql_supports_all_methods(self):
        """Aurora MySQL is the only engine with full method coverage."""
        assert is_connection_method_supported(DatabaseType.AURORA_MYSQL, ConnectionMethod.RDS_API)
        assert is_connection_method_supported(
            DatabaseType.AURORA_MYSQL, ConnectionMethod.MYSQL_WIRE_PROTOCOL
        )
        assert is_connection_method_supported(
            DatabaseType.AURORA_MYSQL, ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL
        )

    def test_rds_mysql_supports_wire_and_iam(self):
        """RDS MySQL: wire protocol + IAM auth, but no Data API."""
        assert not is_connection_method_supported(
            DatabaseType.RDS_MYSQL, ConnectionMethod.RDS_API
        ), 'RDS Data API is Aurora-only; RDS MySQL must reject it.'
        assert is_connection_method_supported(
            DatabaseType.RDS_MYSQL, ConnectionMethod.MYSQL_WIRE_PROTOCOL
        )
        assert is_connection_method_supported(
            DatabaseType.RDS_MYSQL, ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL
        )

    def test_rds_mariadb_supports_wire_only(self):
        """RDS MariaDB: wire protocol only. No Data API, no IAM auth."""
        assert not is_connection_method_supported(
            DatabaseType.RDS_MARIADB, ConnectionMethod.RDS_API
        )
        assert is_connection_method_supported(
            DatabaseType.RDS_MARIADB, ConnectionMethod.MYSQL_WIRE_PROTOCOL
        )
        assert not is_connection_method_supported(
            DatabaseType.RDS_MARIADB, ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL
        ), 'MariaDB does not support IAM authentication; must be rejected.'

    def test_matrix_is_complete(self):
        """Every DatabaseType value has a row in SUPPORTED_CONNECTION_METHODS.

        Adding a new engine without updating the matrix would silently make
        every connection method appear unsupported (the lookup defaults to
        the empty set). This regression guard fails fast in that case.
        """
        for db_type in DatabaseType:
            assert db_type in SUPPORTED_CONNECTION_METHODS, (
                f'{db_type.name} has no entry in SUPPORTED_CONNECTION_METHODS; '
                'the supported-methods table is incomplete.'
            )

    def test_every_engine_supports_at_least_one_method(self):
        """A row in the matrix must contain at least one supported method."""
        for db_type, methods in SUPPORTED_CONNECTION_METHODS.items():
            assert methods, f'{db_type.name} has an empty supported-methods set.'

    def test_every_engine_supports_wire_protocol(self):
        """The wire protocol is the universal lower bound: every RDS engine speaks it.

        If a future engine doesn't speak wire protocol we'll have to revisit
        the assumption that AsyncmyPoolConnection is universally usable.
        """
        for db_type, methods in SUPPORTED_CONNECTION_METHODS.items():
            assert ConnectionMethod.MYSQL_WIRE_PROTOCOL in methods, (
                f'{db_type.name} unexpectedly does not support mysqlwire. '
                'AsyncmyPoolConnection assumes wire protocol works for all '
                'configured engines.'
            )

    def test_data_api_is_aurora_only(self):
        """Confirm the Aurora-only constraint on RDS Data API."""
        for db_type, methods in SUPPORTED_CONNECTION_METHODS.items():
            if db_type is DatabaseType.AURORA_MYSQL:
                assert ConnectionMethod.RDS_API in methods
            else:
                assert ConnectionMethod.RDS_API not in methods, (
                    f'{db_type.name} unexpectedly supports rdsapi. '
                    'RDS Data API is documented as Aurora-only.'
                )

    def test_unknown_engine_returns_false(self):
        """is_connection_method_supported must not raise on unknown engines.

        The function is called from validation paths that should produce
        a clean ValueError downstream, not an AttributeError or KeyError.
        """
        # Synthesise a non-enum value to simulate a bad input slipping through
        bogus = 'not-a-real-engine'
        # Must not raise; just return False.
        assert is_connection_method_supported(bogus, ConnectionMethod.MYSQL_WIRE_PROTOCOL) is False  # pyright: ignore[reportArgumentType]


class TestConnectionMethod:
    """Tests for ConnectionMethod enum."""

    def test_rds_api(self):
        """RDS_API should map to 'rdsapi'."""
        assert ConnectionMethod.RDS_API == 'rdsapi'

    def test_mysql_wire_protocol(self):
        """MYSQL_WIRE_PROTOCOL should map to 'mysqlwire'."""
        assert ConnectionMethod.MYSQL_WIRE_PROTOCOL == 'mysqlwire'

    def test_mysql_wire_iam_protocol(self):
        """MYSQL_WIRE_IAM_PROTOCOL should map to 'mysqlwire_iam'."""
        assert ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL == 'mysqlwire_iam'

    def test_enum_members(self):
        """ConnectionMethod should have exactly three members."""
        members = list(ConnectionMethod)
        assert len(members) == 3
        assert ConnectionMethod.RDS_API in members
        assert ConnectionMethod.MYSQL_WIRE_PROTOCOL in members
        assert ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL in members


class TestDBConnectionMap:
    """Tests for DBConnectionMap."""

    def _make_mock_conn(self):
        """Create a mock AbstractDBConnection."""
        conn = MagicMock()
        conn.close = MagicMock()
        return conn

    def test_init_empty(self):
        """New map should be empty."""
        m = DBConnectionMap()
        assert m.map == {}

    def test_set_and_get(self):
        """Should store and retrieve a connection."""
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        m.set(ConnectionMethod.RDS_API, 'cluster-1', 'ep.rds.amazonaws.com', 'mydb', conn)
        result = m.get(ConnectionMethod.RDS_API, 'cluster-1', 'ep.rds.amazonaws.com', 'mydb')
        assert result is conn

    def test_get_nonexistent_returns_none(self):
        """Getting a key that doesn't exist should return None."""
        m = DBConnectionMap()
        result = m.get(ConnectionMethod.RDS_API, 'cluster-1', 'ep.rds.amazonaws.com', 'mydb')
        assert result is None

    def test_default_port_3306(self):
        """Default port should be 3306."""
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db', conn)
        # Should be retrievable with default port
        result = m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db')
        assert result is conn
        # Explicit 3306 should also work
        result2 = m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db', 3306)
        assert result2 is conn

    def test_custom_port(self):
        """Strict-tuple port axis is exact: 3306 lookup must miss a 3307 entry.

        Uses a non-matching cluster_identifier on the lookup so the
        relaxed scan cannot fire. This test pins the strict-path port
        semantics; the deliberate "relaxed scan ignores port when caller
        does not supply one" behaviour is tested separately in
        TestRelaxedLookup (see
        test_relaxed_lookup_finds_non_default_port_connection and
        test_relaxed_lookup_returns_none_for_same_cluster_multiple_ports).
        """
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db', conn, port=3307)
        # Default port (3306) on a different cluster id must not strict-match
        # the entry stored at 3307, and the relaxed scan cannot fire because
        # cluster id does not match.
        assert m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'other-cluster', 'ep', 'db') is None
        # Custom port on the original tuple should strict-match.
        assert m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db', 3307) is conn

    def test_set_raises_on_empty_database(self):
        """set() should raise ValueError if database is empty."""
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        with pytest.raises(ValueError, match='database cannot be None or empty'):
            m.set(ConnectionMethod.RDS_API, 'c1', 'ep', '', conn)

    def test_set_raises_on_none_conn(self):
        """set() should raise ValueError if conn is None."""
        m = DBConnectionMap()
        with pytest.raises(ValueError, match='conn cannot be None'):
            m.set(ConnectionMethod.RDS_API, 'c1', 'ep', 'db', None)  # pyright: ignore[reportArgumentType]

    def test_get_raises_on_none_method(self):
        """get() should raise ValueError if method is None."""
        m = DBConnectionMap()
        with pytest.raises(ValueError, match='method cannot be None'):
            m.get(None, 'c1', 'ep', 'db')  # pyright: ignore[reportArgumentType]

    def test_get_raises_on_empty_database(self):
        """get() should raise ValueError if database is empty."""
        m = DBConnectionMap()
        with pytest.raises(ValueError, match='database cannot be None or empty'):
            m.get(ConnectionMethod.RDS_API, 'c1', 'ep', '')

    def test_remove_existing(self):
        """remove() should remove an existing connection."""
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep', 'db', conn)
        m.remove(ConnectionMethod.RDS_API, 'c1', 'ep', 'db')
        assert m.get(ConnectionMethod.RDS_API, 'c1', 'ep', 'db') is None

    def test_remove_nonexistent_does_not_raise(self):
        """remove() on a non-existing key should not raise."""
        m = DBConnectionMap()
        m.remove(ConnectionMethod.RDS_API, 'c1', 'ep', 'db')

    def test_remove_raises_on_empty_database(self):
        """remove() should raise ValueError if database is empty."""
        m = DBConnectionMap()
        with pytest.raises(ValueError, match='database cannot be None or empty'):
            m.remove(ConnectionMethod.RDS_API, 'c1', 'ep', '')

    def test_get_keys_json_empty(self):
        """get_keys_json() on empty map should return empty JSON array."""
        m = DBConnectionMap()
        result = json.loads(m.get_keys_json())
        assert result == []

    def test_get_keys_json_with_entries(self):
        """get_keys_json() should return all keys as JSON."""
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep1', 'db1', conn)
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c2', 'ep2', 'db2', conn, port=3307)
        result = json.loads(m.get_keys_json())
        assert len(result) == 2
        # Check first entry
        entry = result[0]
        assert 'connection_method' in entry
        assert 'cluster_identifier' in entry
        assert 'db_endpoint' in entry
        assert 'database' in entry
        assert 'port' in entry

    async def test_close_all(self):
        """close_all() should close all connections and clear the map."""
        m = DBConnectionMap()
        conn1 = self._make_mock_conn()
        conn1.close = AsyncMock()
        conn2 = self._make_mock_conn()
        conn2.close = AsyncMock()
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep1', 'db1', conn1)
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c2', 'ep2', 'db2', conn2)
        await m.close_all()
        conn1.close.assert_called_once()
        conn2.close.assert_called_once()
        assert m.map == {}

    async def test_close_all_handles_exception(self):
        """close_all() should handle exceptions from close() gracefully."""
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        conn.close = AsyncMock(side_effect=RuntimeError('close failed'))
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep1', 'db1', conn)
        # Should not raise
        await m.close_all()
        assert m.map == {}

    def test_multiple_connections_different_keys(self):
        """Should store multiple connections with different keys."""
        m = DBConnectionMap()
        conn1 = self._make_mock_conn()
        conn2 = self._make_mock_conn()
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep1', 'db1', conn1)
        m.set(ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL, 'c1', 'ep1', 'db1', conn2)
        assert m.get(ConnectionMethod.RDS_API, 'c1', 'ep1', 'db1') is conn1
        assert m.get(ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL, 'c1', 'ep1', 'db1') is conn2

    def test_overwrite_existing_key(self):
        """Setting the same key again should overwrite the connection."""
        m = DBConnectionMap()
        conn1 = self._make_mock_conn()
        conn2 = self._make_mock_conn()
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep1', 'db1', conn1)
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep1', 'db1', conn2)
        assert m.get(ConnectionMethod.RDS_API, 'c1', 'ep1', 'db1') is conn2


class TestRelaxedLookup:
    """Tests for the two-phase get(): strict tuple match plus relaxed scan.

    The relaxed scan lets ``run_query`` find a connection even when the
    caller passed an empty ``db_endpoint`` to ``connect_to_database`` and
    the connect path auto-resolved it to the cluster's writer endpoint.
    Without the relaxed scan, the connection would be unreachable through
    any user-driven tool call after registration. This was caught at the
    MCP-protocol layer during live validation, so these tests pin the
    behaviour at the unit level too.
    """

    def _make_mock_conn(self):
        return MagicMock(close=MagicMock())

    def test_relaxed_lookup_by_cluster_identifier(self):
        """Match on (method, cluster, database) when endpoints differ."""
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        # connect path stored with the auto-resolved endpoint
        m.set(
            ConnectionMethod.RDS_API,
            'cluster-1',
            'cluster-1.writer.us-west-2.rds.amazonaws.com',
            'mydb',
            conn,
        )
        # caller looks up with empty endpoint (what they originally passed)
        result = m.get(ConnectionMethod.RDS_API, 'cluster-1', '', 'mydb')
        assert result is conn, (
            'Relaxed lookup must find a connection by (method, cluster, '
            'database) when the caller did not know the auto-resolved '
            'endpoint at connect time.'
        )

    def test_relaxed_lookup_by_db_endpoint_when_no_cluster(self):
        """Match on (method, endpoint, database) when caller has no cluster id.

        Standalone RDS MySQL / MariaDB instances are reached by endpoint
        without a cluster identifier. The relaxed scan must work via the
        endpoint axis too.
        """
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        m.set(
            ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            'cluster-1',  # connect path resolved this
            'instance-1.us-west-2.rds.amazonaws.com',
            'mydb',
            conn,
        )
        # caller has only the endpoint
        result = m.get(
            ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            '',
            'instance-1.us-west-2.rds.amazonaws.com',
            'mydb',
        )
        assert result is conn

    def test_strict_tuple_match_still_wins(self):
        """A 5-tuple-exact match must take precedence over the relaxed scan.

        Regression guard: dedupe inside ``internal_connect_to_database``
        relies on the strict path returning the previously-stored conn
        without scanning.
        """
        m = DBConnectionMap()
        exact = self._make_mock_conn()
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep1', 'mydb', exact)
        result = m.get(ConnectionMethod.RDS_API, 'c1', 'ep1', 'mydb')
        assert result is exact

    def test_relaxed_lookup_returns_none_on_ambiguity(self):
        """Multiple matching entries must return None rather than picking one.

        If two connections exist for the same cluster+method+database (e.g.
        different ports, or stale registrations), silently returning one
        could route a query to the wrong instance. None is safer.
        """
        m = DBConnectionMap()
        conn_a = self._make_mock_conn()
        conn_b = self._make_mock_conn()
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep1', 'mydb', conn_a, port=3306)
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep2', 'mydb', conn_b, port=3306)
        # Strict tuple miss (empty endpoint), relaxed scan finds two cluster matches
        result = m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', '', 'mydb')
        assert result is None

    def test_relaxed_lookup_misses_when_method_differs(self):
        """The method axis is non-negotiable — different methods do not match.

        rdsapi and mysqlwire are separate transports; a registered rdsapi
        connection must not satisfy a mysqlwire lookup just because cluster
        and database match.
        """
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep1', 'mydb', conn)
        result = m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', '', 'mydb')
        assert result is None

    def test_relaxed_lookup_misses_when_database_differs(self):
        """Different database name on the same cluster must not match."""
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep1', 'mydb', conn)
        result = m.get(ConnectionMethod.RDS_API, 'c1', '', 'otherdb')
        assert result is None

    def test_relaxed_lookup_returns_none_with_no_identifier_at_all(self):
        """If both cluster_identifier and db_endpoint are empty, no scan happens."""
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        m.set(ConnectionMethod.RDS_API, 'c1', 'ep1', 'mydb', conn)
        result = m.get(ConnectionMethod.RDS_API, '', '', 'mydb')
        assert result is None

    def test_relaxed_lookup_finds_non_default_port_connection(self):
        """Caller without a port reaches a connection stored on a non-default port.

        Pins the design choice in get(): when port is not supplied (the
        default for ``run_query``-style callers), the relaxed scan must
        ignore port. Otherwise a user whose MySQL listens on 3307 would
        connect successfully (storing under 3307) but be unable to issue
        any query through ``run_query`` (which has no port parameter
        and would default to 3306).
        """
        m = DBConnectionMap()
        conn = self._make_mock_conn()
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db', conn, port=3307)
        # Caller does not pass port: relaxed scan ignores port and returns
        # the 3307 entry.
        result = m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', '', 'db')
        assert result is conn

    def test_relaxed_lookup_returns_none_for_same_cluster_multiple_ports(self):
        """Two entries on different ports: ambiguity guard returns None.

        Pairs with test_relaxed_lookup_returns_none_on_ambiguity (which
        covers two entries on different *endpoints*). Without this check,
        a future caller adding two same-cluster connections on different
        ports could see queries silently routed to either one.
        """
        m = DBConnectionMap()
        conn_a = self._make_mock_conn()
        conn_b = self._make_mock_conn()
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db', conn_a, port=3306)
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db', conn_b, port=3307)
        # Caller does not pass port: relaxed scan finds two cluster matches
        # and returns None rather than silently picking one.
        result = m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', '', 'db')
        assert result is None

    def test_relaxed_lookup_filters_by_port_when_caller_supplies_one(self):
        """Caller-supplied port is honoured by the relaxed scan.

        When a caller does pass a specific port, the relaxed scan filters
        on it. This means a future tool that takes a ``port`` parameter
        and passes it through to ``get`` will not silently match an entry
        on a different port.
        """
        m = DBConnectionMap()
        conn_3306 = self._make_mock_conn()
        conn_3307 = self._make_mock_conn()
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db', conn_3306, port=3306)
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db', conn_3307, port=3307)
        # Strict tuple match wins for the port-3307 lookup.
        assert m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', 'ep', 'db', 3307) is conn_3307
        # Relaxed scan, port supplied: empty endpoint forces the scan but
        # the port filter excludes the 3306 entry, leaving only 3307.
        assert m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', '', 'db', 3307) is conn_3307
        # And the symmetric case for 3306.
        assert m.get(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'c1', '', 'db', 3306) is conn_3306


class TestHasConnectionForCluster:
    """Tests for has_connection_for_cluster scan-by-cluster helper."""

    def _make_mock_conn(self):
        conn = MagicMock()
        conn.close = AsyncMock()
        return conn

    def test_returns_true_when_cluster_has_connection(self):
        """Any cached entry for the cluster should satisfy the scan."""
        m = DBConnectionMap()
        m.set(ConnectionMethod.RDS_API, 'prod', 'ep', 'app', self._make_mock_conn())
        assert m.has_connection_for_cluster('prod') is True

    def test_returns_false_when_cluster_has_no_connection(self):
        """Returns False when the cluster identifier has no cached entries."""
        m = DBConnectionMap()
        m.set(ConnectionMethod.RDS_API, 'other-cluster', 'ep', 'app', self._make_mock_conn())
        assert m.has_connection_for_cluster('prod') is False

    def test_returns_false_for_empty_map(self):
        """Returns False when the map is empty."""
        m = DBConnectionMap()
        assert m.has_connection_for_cluster('prod') is False

    def test_returns_false_for_empty_cluster_identifier(self):
        """Empty cluster_identifier returns False without scanning."""
        m = DBConnectionMap()
        m.set(ConnectionMethod.RDS_API, '', 'ep', 'app', self._make_mock_conn())
        assert m.has_connection_for_cluster('') is False

    def test_matches_any_method_for_cluster(self):
        """A match is found regardless of which connection method was used."""
        m = DBConnectionMap()
        m.set(
            ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL,
            'prod',
            'ep',
            'app',
            self._make_mock_conn(),
        )
        assert m.has_connection_for_cluster('prod') is True

    def test_matches_any_endpoint_or_database_for_cluster(self):
        """A match is found regardless of the stored endpoint or database.

        Regression guard for the original is_database_connected bug where
        the tool required callers to pass the exact endpoint and database
        used at connect time.
        """
        m = DBConnectionMap()
        m.set(
            ConnectionMethod.RDS_API,
            'prod',
            'writer.rds.amazonaws.com',
            'mealplanner',
            self._make_mock_conn(),
        )
        # Caller doesn't know the endpoint or the database — still matches.
        assert m.has_connection_for_cluster('prod') is True


class TestCloseAllSync:
    """Tests for the synchronous best-effort close path used at process shutdown."""

    def test_closes_pool_on_each_connection(self):
        """close_all_sync calls .pool.close() on every cached connection and clears the map."""
        from awslabs.mysql_mcp_server.connection.db_connection_map import (
            ConnectionMethod,
            DBConnectionMap,
        )
        from unittest.mock import MagicMock

        m = DBConnectionMap()

        conn1 = MagicMock()
        conn1.pool = MagicMock()
        conn2 = MagicMock()
        conn2.pool = MagicMock()

        m.set(ConnectionMethod.RDS_API, 'cluster-1', 'ep1', 'app', conn1)
        m.set(ConnectionMethod.MYSQL_WIRE_PROTOCOL, 'cluster-2', 'ep2', 'app', conn2)

        m.close_all_sync()

        conn1.pool.close.assert_called_once()
        conn2.pool.close.assert_called_once()
        # After close_all_sync the map must be empty so the next process
        # restart starts fresh.
        assert len(m.map) == 0

    def test_skips_connection_without_pool_attribute(self):
        """A connection that exposes no .pool attribute (e.g. Data API) is silently skipped."""
        from awslabs.mysql_mcp_server.connection.db_connection_map import (
            ConnectionMethod,
            DBConnectionMap,
        )
        from unittest.mock import MagicMock

        m = DBConnectionMap()

        # spec=[] so .pool attribute access raises AttributeError. hasattr()
        # returns False, and the connection is skipped without error.
        conn = MagicMock(spec=[])
        m.set(ConnectionMethod.RDS_API, 'cluster-1', 'ep', 'app', conn)

        m.close_all_sync()
        assert len(m.map) == 0

    def test_swallows_close_exceptions(self):
        """A close() that raises must not prevent the rest of the connections from closing."""
        from awslabs.mysql_mcp_server.connection.db_connection_map import (
            ConnectionMethod,
            DBConnectionMap,
        )
        from unittest.mock import MagicMock

        m = DBConnectionMap()

        bad = MagicMock()
        bad.pool = MagicMock()
        bad.pool.close.side_effect = RuntimeError('socket already shut')

        good = MagicMock()
        good.pool = MagicMock()

        m.set(ConnectionMethod.RDS_API, 'cluster-bad', 'ep', 'app', bad)
        m.set(ConnectionMethod.RDS_API, 'cluster-good', 'ep2', 'app', good)

        # Must not raise.
        m.close_all_sync()
        good.pool.close.assert_called_once()
        assert len(m.map) == 0
