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
from awslabs.mysql_mcp_server.server import internal_connect_to_database
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
            'Endpoint': {'Address': 'resolved-instance.rds.amazonaws.com', 'Port': 3306},
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


class TestInternalConnectToDatabaseIdentifierOnly:
    """Tests for resolving RDS MySQL/MariaDB by cluster_identifier alone.

    Covers the case where the caller supplies only cluster_identifier (no
    db_endpoint) for a non-Aurora database_type: the identifier can name a
    standalone RDS instance, or — for MySQL only — an RDS Multi-AZ DB
    cluster. See https://github.com/awslabs/mcp/issues/4589.
    """

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_resolves_standalone_instance_by_identifier(
        self, mock_map, mock_get_inst, mock_asyncmy_cls
    ):
        """RDS MySQL, identifier-only: resolves via describe_db_instances."""
        mock_map.get.return_value = None

        mock_get_inst.return_value = {
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': {'Address': 'resolved-instance.rds.amazonaws.com', 'Port': 3306},
        }

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        result_conn, result_json = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='my-standalone-instance',
            db_endpoint='',
            port=3306,
            database='testdb',
        )

        mock_get_inst.assert_called_once_with('my-standalone-instance', 'us-east-1')
        mock_asyncmy_cls.assert_called_once()
        assert mock_asyncmy_cls.call_args[1]['host'] == 'resolved-instance.rds.amazonaws.com'
        assert result_conn is mock_conn
        parsed = json.loads(result_json)
        assert parsed['db_endpoint'] == 'resolved-instance.rds.amazonaws.com'

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_resolves_standalone_mariadb_instance_by_identifier(
        self, mock_map, mock_get_inst, mock_asyncmy_cls
    ):
        """RDS MariaDB, identifier-only: resolves via describe_db_instances too."""
        mock_map.get.return_value = None

        mock_get_inst.return_value = {
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': {'Address': 'resolved-mariadb.rds.amazonaws.com', 'Port': 3306},
        }

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        result_conn, _ = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MARIADB,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='my-mariadb-instance',
            db_endpoint='',
            port=3306,
            database='testdb',
        )

        mock_get_inst.assert_called_once_with('my-mariadb-instance', 'us-east-1')
        assert result_conn is mock_conn

    @patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_falls_back_to_multi_az_cluster_when_no_instance_found(
        self, mock_map, mock_get_inst, mock_get_cluster, mock_asyncmy_cls
    ):
        """RDS MySQL, identifier-only: falls back to cluster lookup when instance is not found."""
        from botocore.exceptions import ClientError

        mock_map.get.return_value = None

        mock_get_inst.side_effect = ClientError(
            error_response={'Error': {'Code': 'DBInstanceNotFound', 'Message': 'not found'}},
            operation_name='DescribeDBInstances',
        )
        mock_get_cluster.return_value = {
            'HttpEndpointEnabled': False,
            'MasterUsername': 'admin',
            'DBClusterArn': 'arn:aws:rds:us-east-1:123:cluster:my-multi-az-cluster',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': 'multi-az-writer.rds.amazonaws.com',
            'Port': '3306',
        }

        mock_conn = MagicMock()
        mock_asyncmy_cls.return_value = mock_conn

        result_conn, result_json = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.RDS_MYSQL,
            connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
            cluster_identifier='my-multi-az-cluster',
            db_endpoint='',
            port=3306,
            database='testdb',
        )

        mock_get_inst.assert_called_once_with('my-multi-az-cluster', 'us-east-1')
        mock_get_cluster.assert_called_once_with(
            cluster_identifier='my-multi-az-cluster', region='us-east-1'
        )
        assert result_conn is mock_conn
        parsed = json.loads(result_json)
        assert parsed['db_endpoint'] == 'multi-az-writer.rds.amazonaws.com'

    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_does_not_fall_back_for_mariadb(self, mock_map, mock_get_inst, mock_get_cluster):
        """RDS MariaDB, identifier-only: no fallback since Multi-AZ DB clusters don't support MariaDB."""
        mock_map.get.return_value = None
        mock_get_inst.side_effect = ValueError("Instance 'x' not found in region 'us-east-1'")

        with pytest.raises(ValueError, match="Instance 'x' not found"):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RDS_MARIADB,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='x',
                db_endpoint='',
                port=3306,
                database='testdb',
            )

        mock_get_cluster.assert_not_called()

    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_access_denied_propagates_without_cluster_fallback(self, mock_map, mock_get_inst):
        """A real AccessDenied/throttling error must propagate, not be swallowed into a retry."""
        from botocore.exceptions import ClientError

        mock_map.get.return_value = None
        mock_get_inst.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'nope'}},
            operation_name='DescribeDBInstances',
        )

        with pytest.raises(ClientError):
            internal_connect_to_database(
                region='us-east-1',
                database_type=DatabaseType.RDS_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='my-instance',
                db_endpoint='',
                port=3306,
                database='testdb',
            )

    @patch('awslabs.mysql_mcp_server.server.RDSDataAPIConnection')
    @patch('awslabs.mysql_mcp_server.server.internal_get_cluster_properties')
    @patch('awslabs.mysql_mcp_server.server.internal_get_instance_properties_by_identifier')
    @patch('awslabs.mysql_mcp_server.server.db_connection_map')
    def test_aurora_mysql_skips_identifier_lookup(
        self, mock_map, mock_get_inst, mock_get_cluster, mock_rds_conn_cls
    ):
        """Aurora MySQL must go straight to describe_db_clusters, never the identifier lookup."""
        mock_map.get.return_value = None
        mock_get_cluster.return_value = {
            'HttpEndpointEnabled': True,
            'MasterUsername': 'admin',
            'DBClusterArn': 'arn:aws:rds:us-east-1:123:cluster:aurora-1',
            'MasterUserSecret': {'SecretArn': 'arn:secret'},
            'Endpoint': 'aurora-writer.rds.amazonaws.com',
            'Port': '3306',
        }
        mock_conn = MagicMock()
        mock_rds_conn_cls.return_value = mock_conn

        result_conn, _ = internal_connect_to_database(
            region='us-east-1',
            database_type=DatabaseType.AURORA_MYSQL,
            connection_method=ConnectionMethod.RDS_API,
            cluster_identifier='aurora-1',
            db_endpoint='',
            port=3306,
            database='testdb',
        )

        mock_get_inst.assert_not_called()
        mock_get_cluster.assert_called_once()
        assert result_conn is mock_conn

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
            'Endpoint': {'Address': 'resolved-instance.rds.amazonaws.com', 'Port': 3306},
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
