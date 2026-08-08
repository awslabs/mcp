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

"""Tests for internal_connect_to_database() with mocks."""

import json
import pytest
from awslabs.mysql_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DatabaseType,
)
from awslabs.mysql_mcp_server.server import (
    internal_connect_to_database,
    is_db_instance_not_found,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


class TestInternalConnectToDatabaseValidation:
    """Tests for input validation in internal_connect_to_database."""

    def test_empty_region_raises(self):
        """Should raise ValueError for empty region."""
        with pytest.raises(ValueError, match="region can't be none or empty"):
            internal_connect_to_database(
                region='',
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='cluster-1',
                db_endpoint='ep',
                port=3306,
                database='testdb',
            )

    def test_empty_connection_method_raises(self):
        """Should raise ValueError for empty connection_method."""
        with pytest.raises(ValueError, match="connection_method can't be none or empty"):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method='',  # pyright: ignore[reportArgumentType]
                cluster_identifier='cluster-1',
                db_endpoint='ep',
                port=3306,
                database='testdb',
            )

    def test_empty_database_type_raises(self):
        """Should raise ValueError for empty database_type."""
        with pytest.raises(ValueError, match="database_type can't be none or empty"):
            internal_connect_to_database(
                region='us-east-1',
                database_type='',  # pyright: ignore[reportArgumentType]
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='cluster-1',
                db_endpoint='ep',
                port=3306,
                database='testdb',
            )

    def test_aurora_mysql_without_cluster_identifier_raises(self):
        """Aurora MySQL must require a cluster_identifier."""
        with pytest.raises(
            ValueError, match="cluster_identifier can't be none or empty for Aurora MySQL"
        ):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='',
                db_endpoint='ep',
                port=3306,
                database='testdb',
            )

    def test_rds_mysql_without_cluster_or_endpoint_raises(self):
        """RDS MySQL: at least one of cluster_identifier or db_endpoint required."""
        with pytest.raises(
            ValueError, match='Either cluster_identifier or db_endpoint must be provided'
        ):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RDS_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='',
                port=3306,
                database='testdb',
            )

    def test_rds_mariadb_without_cluster_or_endpoint_raises(self):
        """RDS MariaDB: at least one of cluster_identifier or db_endpoint required."""
        with pytest.raises(
            ValueError, match='Either cluster_identifier or db_endpoint must be provided'
        ):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RDS_MARIADB,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='',
                port=3306,
                database='testdb',
            )

    def test_aurora_mysql_rejects_unsupported_method_combinations(self):
        """Supported-methods table is enforced at the entry point.

        Aurora MySQL supports every method, but other engines do not. This
        test exercises the AURORA_MYSQL row of the matrix; the negative
        combinations are covered by the test cases below for RDS MySQL
        (no rdsapi) and RDS MariaDB (no rdsapi, no IAM auth).
        """
        # Aurora MySQL + every method should pass past the matrix check.
        # We don't run them through the full connect logic here; we just
        # confirm they don't raise the unsupported-pair error.
        from awslabs.mysql_mcp_server.connection.db_connection_map import (
            is_connection_method_supported,
        )

        for method in ConnectionMethod:
            assert is_connection_method_supported(DatabaseType.AURORA_MYSQL, method)

    def test_rds_mysql_rejects_data_api(self):
        """RDS MySQL + rdsapi: must fail with a clear unsupported-pair error."""
        with pytest.raises(ValueError, match='not supported for database type'):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RDS_MYSQL,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='cluster-1',
                db_endpoint='ep',
                port=3306,
                database='testdb',
            )

    def test_rds_mariadb_rejects_data_api(self):
        """RDS MariaDB + rdsapi: must fail."""
        with pytest.raises(ValueError, match='not supported for database type'):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RDS_MARIADB,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='cluster-1',
                db_endpoint='ep',
                port=3306,
                database='testdb',
            )

    def test_rds_mariadb_rejects_iam_auth(self):
        """RDS MariaDB + mysqlwire_iam: must fail (MariaDB has no IAM auth)."""
        with pytest.raises(ValueError, match='not supported for database type'):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RDS_MARIADB,
                connection_method=ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL,
                cluster_identifier='cluster-1',
                db_endpoint='ep',
                port=3306,
                database='testdb',
            )


class TestInternalConnectToDatabaseExistingConnection:
    """Tests for returning existing connections."""

    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_returns_existing_connection(self, mock_map):
        """Should return existing connection if already in map."""
        mock_conn = MagicMock()
        mock_map.get.return_value = mock_conn

        result_conn, result_json = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep',
            port=3306,
            database='testdb',
        )

        assert result_conn is mock_conn
        parsed = json.loads(result_json)
        assert parsed['database'] == 'testdb'


class TestInternalConnectToDatabaseRDSAPI:
    """Tests for RDS API connection creation."""

    @patch('awslabs.mysql_mcp_server.server.RDSDataAPIConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_creates_rds_api_connection(self, mock_map, mock_get_props, mock_rds_conn_cls):
        """Should create RDSDataAPIConnection for RDS_API method."""
        mock_map.get.return_value = None

        mock_get_props.return_value = {
            'HttpEndpointEnabled': True,
            'MasterUsername': 'admin',
            'DBClusterArn': 'arn:aws:rds:us-east-1:123:cluster:cluster-1',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': 'ep.rds.amazonaws.com',
            'Port': '3306',
        }

        mock_conn = MagicMock()
        mock_rds_conn_cls.return_value = mock_conn

        result_conn, result_json = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='ep.rds.amazonaws.com',
            port=3306,
            database='testdb',
        )

        mock_rds_conn_cls.assert_called_once()
        mock_map.set.assert_called_once()
        assert result_conn is mock_conn


class TestInternalConnectToDatabaseMySQLWire:
    """Tests for MySQL wire protocol connection creation."""

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_creates_mysqlwire_connection(self, mock_map, mock_get_props, mock_asyncmy_cls):
        """Should create AsyncmyPoolConnection for MYSQL_WIRE_PROTOCOL."""
        mock_map.get.return_value = None

        mock_get_props.return_value = {
            'HttpEndpointEnabled': False,
            'MasterUsername': 'admin',
            'DBClusterArn': 'arn:cluster',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': 'ep.rds.amazonaws.com',
            'Port': '3306',
        }

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        result_conn, _ = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='cluster-1',
            db_endpoint='ep.rds.amazonaws.com',
            port=3306,
            database='testdb',
        )

        mock_asyncmy_cls.assert_called_once()
        call_kwargs = mock_asyncmy_cls.call_args[1]
        assert call_kwargs['is_iam_auth'] is False
        assert result_conn is mock_conn

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_creates_mysqlwire_iam_connection(self, mock_map, mock_get_props, mock_asyncmy_cls):
        """Should create AsyncmyPoolConnection with IAM for MYSQL_WIRE_IAM_PROTOCOL."""
        mock_map.get.return_value = None

        mock_get_props.return_value = {
            'HttpEndpointEnabled': False,
            'MasterUsername': 'admin',
            'DBClusterArn': 'arn:cluster',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': 'ep.rds.amazonaws.com',
            'Port': '3306',
        }

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        result_conn, _ = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL,
            cluster_identifier='cluster-1',
            db_endpoint='ep.rds.amazonaws.com',
            port=3306,
            database='testdb',
        )

        mock_asyncmy_cls.assert_called_once()
        call_kwargs = mock_asyncmy_cls.call_args[1]
        assert call_kwargs['is_iam_auth'] is True


class TestInternalConnectToDatabaseRDSMySQL:
    """Tests for RDS MySQL (no cluster_identifier) connection."""

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_creates_connection_for_rds_mysql(self, mock_map, mock_get_inst, mock_asyncmy_cls):
        """Should use instance properties when no cluster_identifier."""
        mock_map.get.return_value = None

        mock_get_inst.return_value = {
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': {'Port': 3306},
        }

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        result_conn, _ = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='',
            db_endpoint='myinstance.rds.amazonaws.com',
            port=3306,
            database='testdb',
        )

        mock_get_inst.assert_called_once_with('myinstance.rds.amazonaws.com', 'us-east-1')
        assert result_conn is mock_conn


class TestInternalConnectToDatabaseRDSMariaDB:
    """Tests for RDS MariaDB connection.

    MariaDB is wire-protocol only (no Data API, no IAM auth). We exercise
    the full connect path here so that any future regression in matrix
    enforcement is caught at integration level, not just the unit-level
    matrix tests in test_db_connection_map.py.
    """

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_creates_wire_connection_for_rds_mariadb(
        self, mock_map, mock_get_inst, mock_asyncmy_cls
    ):
        """RDS MariaDB + mysqlwire: end-to-end path returns a connection."""
        mock_map.get.return_value = None

        mock_get_inst.return_value = {
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': {'Port': 3306},
        }

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        result_conn, _ = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MARIADB,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='',
            db_endpoint='mariadb.rds.amazonaws.com',
            port=3306,
            database='testdb',
        )

        mock_asyncmy_cls.assert_called_once()
        # MariaDB never uses IAM auth — confirm flag is False.
        assert mock_asyncmy_cls.call_args[1]['is_iam_auth'] is False
        assert result_conn is mock_conn


class TestInternalConnectToDatabaseEndpointFromCluster:
    """Tests for auto-populating endpoint from cluster properties."""

    @patch('awslabs.mysql_mcp_server.server.RDSDataAPIConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_uses_cluster_endpoint_when_not_provided(
        self, mock_map, mock_get_props, mock_rds_conn_cls
    ):
        """Should use cluster endpoint when db_endpoint is empty."""
        mock_map.get.return_value = None

        mock_get_props.return_value = {
            'HttpEndpointEnabled': True,
            'MasterUsername': 'admin',
            'DBClusterArn': 'arn:cluster',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': 'auto-ep.rds.amazonaws.com',
            'Port': '3306',
        }

        mock_conn = MagicMock()
        mock_rds_conn_cls.return_value = mock_conn

        _, result_json = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='cluster-1',
            db_endpoint='',
            port=3306,
            database='testdb',
        )

        parsed = json.loads(result_json)
        assert parsed['db_endpoint'] == 'auto-ep.rds.amazonaws.com'


class TestInternalConnectToDatabaseStandaloneInstanceByIdentifier:
    """Regression tests for issue #3787.

    A standalone RDS MySQL / MariaDB instance has no cluster at all, so
    passing its instance identifier as ``cluster_identifier`` (with no
    ``db_endpoint``) must resolve via the instance API
    (``describe_db_instances``), never via the cluster API
    (``describe_db_clusters``) — the latter always raised
    ``DBClusterNotFoundFault`` for a standalone instance.
    """

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_rds_mysql_resolves_by_instance_identifier_not_cluster(
        self, mock_map, mock_get_cluster, mock_get_inst_by_id, mock_asyncmy_cls
    ):
        """RDS MySQL with only cluster_identifier set (no db_endpoint).

        Must resolve through the instance-identifier lookup, and must
        never call the cluster lookup.
        """
        mock_map.get.return_value = None

        mock_get_inst_by_id.return_value = {
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': {
                'Address': 'standalone-instance.abc123.us-east-1.rds.amazonaws.com',
                'Port': 3306,
            },
        }

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        result_conn, result_json = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='standalone-instance',
            db_endpoint='',
            port=3306,
            database='testdb',
        )

        mock_get_inst_by_id.assert_called_once_with('standalone-instance', 'us-east-1')
        mock_get_cluster.assert_not_called()
        assert result_conn is mock_conn

        parsed = json.loads(result_json)
        assert parsed['db_endpoint'] == 'standalone-instance.abc123.us-east-1.rds.amazonaws.com'

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_rds_mysql_prefers_endpoint_lookup_when_endpoint_given(
        self,
        mock_map,
        mock_get_cluster,
        mock_get_inst_by_id,
        mock_get_inst_by_endpoint,
        mock_asyncmy_cls,
    ):
        """Endpoint lookup takes precedence when both identifiers are set.

        When both cluster_identifier and db_endpoint are set (the
        documented Scenario 4 in connect_to_database's docstring), the
        endpoint lookup takes precedence and neither the cluster lookup
        nor the identifier lookup is used.
        """
        mock_map.get.return_value = None

        mock_get_inst_by_endpoint.return_value = {
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': {'Port': 3306},
        }

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='standalone-instance',
            db_endpoint='standalone-instance.abc123.us-east-1.rds.amazonaws.com',
            port=3306,
            database='testdb',
        )

        mock_get_inst_by_endpoint.assert_called_once_with(
            'standalone-instance.abc123.us-east-1.rds.amazonaws.com', 'us-east-1'
        )
        mock_get_inst_by_id.assert_not_called()
        mock_get_cluster.assert_not_called()

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_rds_mariadb_resolves_by_instance_identifier_not_cluster(
        self, mock_map, mock_get_cluster, mock_get_inst_by_id, mock_asyncmy_cls
    ):
        """Same regression, RDS MariaDB variant."""
        mock_map.get.return_value = None

        mock_get_inst_by_id.return_value = {
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': {
                'Address': 'standalone-mariadb.abc123.us-east-1.rds.amazonaws.com',
                'Port': 3306,
            },
        }

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MARIADB,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='standalone-mariadb',
            db_endpoint='',
            port=3306,
            database='testdb',
        )

        mock_get_inst_by_id.assert_called_once_with('standalone-mariadb', 'us-east-1')
        mock_get_cluster.assert_not_called()


class TestInternalConnectToDatabaseMultiAzDbCluster:
    """RDS Multi-AZ DB cluster resolution for database_type=mysql.

    An RDS Multi-AZ DB cluster reports ``Engine='mysql'`` but is a
    cluster resource, so it resolves through ``describe_db_clusters``
    and has no DB instance carrying the cluster's identifier. Routing
    every ``mysql`` deployment to an instance lookup would break it, so
    the instance lookup falls back to the cluster lookup on "not found".

    Multi-AZ DB clusters support only MySQL and PostgreSQL, so RDS
    MariaDB gets no such fallback.
    """

    INSTANCE_NOT_FOUND = ClientError(
        {'Error': {'Code': 'DBInstanceNotFound', 'Message': 'not found'}},
        'DescribeDBInstances',
    )

    MULTI_AZ_CLUSTER = {
        # No HttpEndpointEnabled: Multi-AZ DB clusters have no Data API.
        'MasterUsername': 'admin',
        'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:multiaz-mysql',
        'MasterUserSecret': {'SecretArn': 'arn:secret'},
        'Endpoint': 'multiaz-mysql.cluster-abc123.us-east-1.rds.amazonaws.com',
        'Port': '3306',
    }

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_falls_back_to_cluster_lookup_by_identifier(
        self, mock_map, mock_get_cluster, mock_get_inst_by_id, mock_asyncmy_cls
    ):
        """Identifier naming a Multi-AZ DB cluster resolves via the cluster API."""
        mock_map.get.return_value = None
        mock_get_inst_by_id.side_effect = self.INSTANCE_NOT_FOUND
        mock_get_cluster.return_value = self.MULTI_AZ_CLUSTER

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        result_conn, result_json = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='multiaz-mysql',
            db_endpoint='',
            port=3306,
            database='testdb',
        )

        mock_get_inst_by_id.assert_called_once_with('multiaz-mysql', 'us-east-1')
        mock_get_cluster.assert_called_once_with(
            cluster_identifier='multiaz-mysql', region='us-east-1'
        )
        assert result_conn is mock_conn

        # Endpoint and port come off the cluster, as they do for Aurora.
        parsed = json.loads(result_json)
        assert parsed['db_endpoint'] == self.MULTI_AZ_CLUSTER['Endpoint']
        assert mock_asyncmy_cls.call_args[1]['host'] == self.MULTI_AZ_CLUSTER['Endpoint']
        assert mock_asyncmy_cls.call_args[1]['port'] == 3306

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_falls_back_to_cluster_lookup_when_endpoint_given(
        self, mock_map, mock_get_cluster, mock_get_inst_by_endpoint, mock_asyncmy_cls
    ):
        """The endpoint scan can't match a cluster endpoint, so it falls back too.

        ``internal_get_instance_properties`` scans DB instances for a
        matching endpoint address; a Multi-AZ DB cluster's writer
        endpoint belongs to no instance, so the scan raises ValueError
        and the caller-supplied endpoint is kept as-is.
        """
        mock_map.get.return_value = None
        mock_get_inst_by_endpoint.side_effect = ValueError(
            'AWS error fetching instance by endpoint'
        )
        mock_get_cluster.return_value = self.MULTI_AZ_CLUSTER

        mock_asyncmy_cls.return_value = MagicMock()

        internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='multiaz-mysql',
            db_endpoint=self.MULTI_AZ_CLUSTER['Endpoint'],
            port=3306,
            database='testdb',
        )

        mock_get_cluster.assert_called_once_with(
            cluster_identifier='multiaz-mysql', region='us-east-1'
        )
        assert mock_asyncmy_cls.call_args[1]['host'] == self.MULTI_AZ_CLUSTER['Endpoint']

    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_no_cluster_fallback_for_mariadb(
        self, mock_map, mock_get_cluster, mock_get_inst_by_id
    ):
        """MariaDB can't be a Multi-AZ DB cluster, so the error propagates."""
        mock_map.get.return_value = None
        mock_get_inst_by_id.side_effect = self.INSTANCE_NOT_FOUND

        with pytest.raises(ClientError):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RDS_MARIADB,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='not-a-cluster',
                db_endpoint='',
                port=3306,
                database='testdb',
            )

        mock_get_cluster.assert_not_called()

    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_no_cluster_fallback_on_access_denied(
        self, mock_map, mock_get_cluster, mock_get_inst_by_id
    ):
        """A permissions error must surface, not be retried as a cluster lookup."""
        mock_map.get.return_value = None
        mock_get_inst_by_id.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
            'DescribeDBInstances',
        )

        with pytest.raises(ClientError) as excinfo:
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RDS_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='some-instance',
                db_endpoint='',
                port=3306,
                database='testdb',
            )

        assert excinfo.value.response['Error']['Code'] == 'AccessDenied'
        mock_get_cluster.assert_not_called()

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_aurora_identifier_under_mysql_type_now_resolves(
        self, mock_map, mock_get_cluster, mock_get_inst_by_id, mock_asyncmy_cls
    ):
        """An Aurora cluster identifier passed under database_type=mysql resolves.

        Not a supported configuration, but the cluster fallback reaches any
        DBCluster, so this misuse now connects over the wire protocol instead
        of erroring. Both wire methods valid for mysql are also valid for
        Aurora, and the Aurora-only Data API wiring stays unreachable because
        is_connection_method_supported rejects rdsapi for mysql.
        """
        mock_map.get.return_value = None
        mock_get_inst_by_id.side_effect = self.INSTANCE_NOT_FOUND
        mock_get_cluster.return_value = {
            # An Aurora DBCluster, unlike a Multi-AZ one, reports this field.
            'HttpEndpointEnabled': True,
            'MasterUsername': 'admin',
            'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:aurora-1',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': 'aurora-1.cluster-abc123.us-east-1.rds.amazonaws.com',
            'Port': '3306',
        }
        mock_asyncmy_cls.return_value = MagicMock()

        internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='aurora-1',
            db_endpoint='',
            port=3306,
            database='testdb',
        )

        mock_get_cluster.assert_called_once_with(cluster_identifier='aurora-1', region='us-east-1')
        assert (
            mock_asyncmy_cls.call_args[1]['host']
            == 'aurora-1.cluster-abc123.us-east-1.rds.amazonaws.com'
        )


class TestIsDbInstanceNotFound:
    """Tests for the is_db_instance_not_found predicate."""

    def test_value_error_is_not_found(self):
        """The endpoint scan signals "no match" with ValueError."""
        assert is_db_instance_not_found(ValueError('no instance matched')) is True

    def test_db_instance_not_found_client_error(self):
        """RDS's own DBInstanceNotFound code counts as not found."""
        error = ClientError(
            {'Error': {'Code': 'DBInstanceNotFound', 'Message': 'nope'}},
            'DescribeDBInstances',
        )
        assert is_db_instance_not_found(error) is True

    def test_other_client_error_is_not_not_found(self):
        """Any other AWS error code must not be treated as not found."""
        error = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'slow down'}},
            'DescribeDBInstances',
        )
        assert is_db_instance_not_found(error) is False

    def test_unrelated_exception_is_not_not_found(self):
        """Unrelated exception types are not not-found signals."""
        assert is_db_instance_not_found(RuntimeError('boom')) is False
