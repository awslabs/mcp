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
"""Tests for server internal functions."""

import json
import pytest
from awslabs.postgres_mcp_server.connection.db_connection_map import ConnectionMethod, DatabaseType
from awslabs.postgres_mcp_server.server import (
    DEFAULT_POSTGRES_PORT,
    MAX_IDENTIFIER_BYTES,
    _parse_identifier_parts,
    create_cluster_worker,
    internal_create_connection,
    validate_table_name,
)
from unittest.mock import MagicMock, patch


class TestInternalCreateConnection:
    """Tests for internal_create_connection function."""

    def test_missing_region_raises_error(self):
        """Test that missing region raises ValueError."""
        with pytest.raises(ValueError, match="region can't be none or empty"):
            internal_create_connection(
                region='',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

    def test_missing_connection_method_raises_error(self):
        """Test that missing connection_method raises ValueError."""
        with pytest.raises(ValueError, match="connection_method can't be none or empty"):
            internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=None,  # type: ignore
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

    def test_missing_database_type_raises_error(self):
        """Test that missing database_type raises ValueError."""
        with pytest.raises(ValueError, match="database_type can't be none or empty"):
            internal_create_connection(
                region='us-east-1',
                database_type=None,  # type: ignore
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

    def test_apg_missing_cluster_identifier_raises_error(self):
        """Test that APG without cluster_identifier raises ValueError."""
        with pytest.raises(
            ValueError,
            match="cluster_identifier can't be none or empty for Aurora Postgres Database",
        ):
            internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

    def test_returns_existing_connection(self):
        """Test that existing connection is returned if available."""
        mock_connection = MagicMock()

        with patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map:
            mock_map.get.return_value = mock_connection

            conn, response = internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

            assert conn == mock_connection
            response_dict = json.loads(response)
            assert response_dict['cluster_identifier'] == 'test-cluster'
            assert response_dict['connection_method'] == 'rdsapi'

    def test_creates_rds_api_connection(self):
        """Test creating RDS API connection."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.RDSDataAPIConnection') as mock_rds_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': True,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'test.endpoint.com',
                'Port': 5432,
            }
            mock_connection = MagicMock()
            mock_rds_conn.return_value = mock_connection

            conn, response = internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='',
                port=5432,
                database='testdb',
            )

            assert conn == mock_connection
            mock_map.set.assert_called_once()

    def test_creates_pgwire_iam_connection(self):
        """Test creating PG Wire IAM connection."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection') as mock_pg_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': False,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'test.endpoint.com',
                'Port': 5432,
            }
            mock_connection = MagicMock()
            mock_pg_conn.return_value = mock_connection

            conn, response = internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

            assert conn == mock_connection
            mock_pg_conn.assert_called_once()
            call_kwargs = mock_pg_conn.call_args[1]
            assert call_kwargs['is_iam_auth'] is True

    def test_creates_pgwire_connection_with_secrets(self):
        """Test creating PG Wire connection with Secrets Manager."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection') as mock_pg_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': False,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'test.endpoint.com',
                'Port': 5432,
            }
            mock_connection = MagicMock()
            mock_pg_conn.return_value = mock_connection

            conn, response = internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                cluster_identifier='test-cluster',
                db_endpoint='test.endpoint.com',
                port=5432,
                database='testdb',
            )

            assert conn == mock_connection
            mock_pg_conn.assert_called_once()
            call_kwargs = mock_pg_conn.call_args[1]
            assert call_kwargs['is_iam_auth'] is False
            assert call_kwargs['secret_arn'] == 'arn:secret'

    def test_rpg_instance_without_cluster(self):
        """Test connecting to RDS Postgres instance without cluster."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_instance_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection') as mock_pg_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'MasterUsername': 'postgres',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': {'Port': 5432},
            }
            mock_connection = MagicMock()
            mock_pg_conn.return_value = mock_connection

            conn, response = internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.RPG,
                connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='instance.endpoint.com',
                port=5432,
                database='testdb',
            )

            assert conn == mock_connection
            mock_props.assert_called_once()

    def test_uses_cluster_endpoint_when_not_provided(self):
        """Test that cluster endpoint is used when db_endpoint is not provided."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.RDSDataAPIConnection') as mock_rds_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': True,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'cluster.endpoint.com',
                'Port': 5432,
            }
            mock_connection = MagicMock()
            mock_rds_conn.return_value = mock_connection

            conn, response = internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='',  # Empty, should use cluster endpoint
                port=0,  # Should be overridden
                database='testdb',
            )

            response_dict = json.loads(response)
            assert response_dict['db_endpoint'] == 'cluster.endpoint.com'
            assert response_dict['port'] == 5432

    def test_rejects_endpoint_not_in_cluster(self):
        """Caller-supplied endpoint that doesn't match any cluster endpoint raises ValueError."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': False,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'legitimate.endpoint.com',
                'ReaderEndpoint': 'legitimate.reader.endpoint.com',
                'Port': 5432,
            }

            with pytest.raises(ValueError) as exc_info:
                internal_create_connection(
                    region='us-east-1',
                    database_type=DatabaseType.APG,
                    connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                    cluster_identifier='test-cluster',
                    db_endpoint='attacker.example.com',
                    port=5432,
                    database='testdb',
                )

            msg = str(exc_info.value)
            assert 'attacker.example.com' in msg
            assert 'test-cluster' in msg
            # Error message should list the legitimate endpoints so the caller
            # knows which hosts are acceptable.
            assert 'legitimate.endpoint.com' in msg

    def test_rejects_endpoint_with_wrong_port(self):
        """Caller supplies correct host but wrong port → ValueError."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': False,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'test.endpoint.com',
                'Port': 5432,
            }

            with pytest.raises(ValueError, match='does not match any endpoint'):
                internal_create_connection(
                    region='us-east-1',
                    database_type=DatabaseType.APG,
                    connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                    cluster_identifier='test-cluster',
                    db_endpoint='test.endpoint.com',
                    port=9999,
                    database='testdb',
                )

    def test_endpoint_match_is_case_insensitive(self):
        """Hostname comparison against cluster endpoints is case-insensitive (DNS is)."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection') as mock_pg_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': False,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'test.endpoint.com',
                'Port': 5432,
            }
            mock_pg_conn.return_value = MagicMock()

            conn, response = internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                cluster_identifier='test-cluster',
                # Mixed-case host should still validate against the lowercase
                # cluster endpoint.
                db_endpoint='TEST.Endpoint.COM',
                port=5432,
                database='testdb',
            )

            # The resolved (AWS-sourced) host is what's returned and what the
            # underlying connection pool is built with — never the caller's
            # mixed-case input.
            response_dict = json.loads(response)
            assert response_dict['db_endpoint'] == 'test.endpoint.com'
            call_kwargs = mock_pg_conn.call_args[1]
            assert call_kwargs['host'] == 'test.endpoint.com'

    def test_caller_endpoint_string_is_never_used_for_connection(self):
        """On successful match, the connection is built from the AWS-sourced host string."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection') as mock_pg_conn,
        ):
            mock_map.get.return_value = None
            # Note: writer endpoint intentionally has different capitalization
            # than the caller will supply, proving we don't echo caller input
            # back into the connection string.
            mock_props.return_value = {
                'HttpEndpointEnabled': False,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'canonical.endpoint.com',
                'Port': 5432,
            }
            mock_pg_conn.return_value = MagicMock()

            internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.PG_WIRE_IAM_PROTOCOL,
                cluster_identifier='test-cluster',
                db_endpoint='  Canonical.Endpoint.COM  ',  # extra whitespace + mixed case
                port=5432,
                database='testdb',
            )

            call_kwargs = mock_pg_conn.call_args[1]
            assert call_kwargs['host'] == 'canonical.endpoint.com'

    def test_cluster_invalid_port_falls_back_to_default(self):
        """Unparseable cluster Port falls back to DEFAULT_POSTGRES_PORT."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_cluster_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.RDSDataAPIConnection') as mock_rds_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'HttpEndpointEnabled': True,
                'MasterUsername': 'postgres',
                'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': 'cluster.endpoint.com',
                'Port': 'not-a-number',
            }
            mock_rds_conn.return_value = MagicMock()

            conn, response = internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                db_endpoint='',  # Take the cluster-default path
                port=0,
                database='testdb',
            )

            response_dict = json.loads(response)
            # Port round-trips through the default fallback rather than crashing.
            assert response_dict['port'] == DEFAULT_POSTGRES_PORT

    def test_rpg_instance_uses_aws_sourced_host(self):
        """RPG instance path: db_endpoint passed to connection comes from AWS, not the caller."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_instance_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection') as mock_pg_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'MasterUsername': 'postgres',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': {
                    'Address': 'resolved.instance.endpoint.com',
                    'Port': 5432,
                },
            }
            mock_pg_conn.return_value = MagicMock()

            internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.RPG,
                connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='caller.supplied.endpoint.com',
                port=5432,
                database='testdb',
            )

            # internal_get_instance_properties is the gatekeeper for RPG
            # instances — it already rejects arbitrary endpoints. Once it
            # returns, we rebuild the connection string from its Address so
            # the caller's input never reaches the connection pool.
            call_kwargs = mock_pg_conn.call_args[1]
            assert call_kwargs['host'] == 'resolved.instance.endpoint.com'
            assert call_kwargs['port'] == 5432

    def test_rpg_instance_invalid_port_falls_back_to_default(self):
        """Unparseable instance Port falls back to DEFAULT_POSTGRES_PORT."""
        with (
            patch('awslabs.postgres_mcp_server.server.db_connection_map') as mock_map,
            patch(
                'awslabs.postgres_mcp_server.server.internal_get_instance_properties'
            ) as mock_props,
            patch('awslabs.postgres_mcp_server.server.PsycopgPoolConnection') as mock_pg_conn,
        ):
            mock_map.get.return_value = None
            mock_props.return_value = {
                'MasterUsername': 'postgres',
                'MasterUserSecret': {'SecretArn': 'arn:secret'},
                'Endpoint': {
                    'Address': 'resolved.instance.endpoint.com',
                    'Port': 'not-a-number',
                },
            }
            mock_pg_conn.return_value = MagicMock()

            internal_create_connection(
                region='us-east-1',
                database_type=DatabaseType.RPG,
                connection_method=ConnectionMethod.PG_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='caller.supplied.endpoint.com',
                port=5432,
                database='testdb',
            )

            call_kwargs = mock_pg_conn.call_args[1]
            assert call_kwargs['port'] == DEFAULT_POSTGRES_PORT


class TestCreateClusterWorker:
    """Tests for create_cluster_worker function."""

    def test_worker_success_updates_job_status(self):
        """Test that worker updates job status on success."""
        with (
            patch(
                'awslabs.postgres_mcp_server.server.internal_create_serverless_cluster'
            ) as mock_create,
            patch('awslabs.postgres_mcp_server.server.setup_aurora_iam_policy_for_current_user'),
            patch('awslabs.postgres_mcp_server.server.internal_create_connection'),
            patch('awslabs.postgres_mcp_server.server.async_job_status'),
            patch('awslabs.postgres_mcp_server.server.async_job_status_lock') as mock_lock,
        ):
            mock_create.return_value = {
                'MasterUsername': 'postgres',
                'DbClusterResourceId': 'cluster-123',
                'Endpoint': 'test.endpoint.com',
            }
            mock_lock.acquire = MagicMock()
            mock_lock.release = MagicMock()

            create_cluster_worker(
                job_id='test-job',
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                engine_version='17.5',
                database='testdb',
            )

            # Verify job status was updated
            assert mock_lock.acquire.called
            assert mock_lock.release.called

    def test_worker_failure_updates_job_status(self):
        """Test that worker updates job status on failure."""
        with (
            patch(
                'awslabs.postgres_mcp_server.server.internal_create_serverless_cluster'
            ) as mock_create,
            patch('awslabs.postgres_mcp_server.server.async_job_status'),
            patch('awslabs.postgres_mcp_server.server.async_job_status_lock') as mock_lock,
        ):
            mock_create.side_effect = Exception('Cluster creation failed')
            mock_lock.acquire = MagicMock()
            mock_lock.release = MagicMock()

            create_cluster_worker(
                job_id='test-job',
                region='us-east-1',
                database_type=DatabaseType.APG,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier='test-cluster',
                engine_version='17.5',
                database='testdb',
            )

            # Verify job status was updated with failure
            assert mock_lock.acquire.called
            assert mock_lock.release.called


# ============================================================================
# Tests for _parse_identifier_parts
# ============================================================================


class TestParseIdentifierPartsUnquoted:
    """Tests for _parse_identifier_parts with unquoted identifiers."""

    def test_simple_name(self):
        """Test parsing a simple unquoted table name."""
        result = _parse_identifier_parts('users')
        assert result == ['users']

    def test_leading_underscore(self):
        """Test parsing an unquoted name starting with underscore."""
        result = _parse_identifier_parts('_my_table')
        assert result == ['_my_table']

    def test_with_digits(self):
        """Test parsing an unquoted name containing digits."""
        result = _parse_identifier_parts('table123')
        assert result == ['table123']

    def test_with_dollar_sign(self):
        """Test parsing an unquoted name containing dollar sign."""
        result = _parse_identifier_parts('my$table')
        assert result == ['my$table']

    def test_all_underscores(self):
        """Test parsing an unquoted name that is all underscores."""
        result = _parse_identifier_parts('___')
        assert result == ['___']

    def test_single_char(self):
        """Test parsing a single character identifier."""
        result = _parse_identifier_parts('a')
        assert result == ['a']

    def test_uppercase(self):
        """Test parsing an unquoted name with uppercase letters."""
        result = _parse_identifier_parts('MyTable')
        assert result == ['MyTable']

    def test_unicode_letter(self):
        """Test parsing an unquoted name with unicode letters."""
        result = _parse_identifier_parts('données')
        assert result == ['données']

    def test_mixed_case_digits_underscores_dollar(self):
        """Test parsing an unquoted name with all valid character types."""
        result = _parse_identifier_parts('Abc_123$x')
        assert result == ['Abc_123$x']


class TestParseIdentifierPartsUnquotedInvalid:
    """Tests for _parse_identifier_parts with invalid unquoted identifiers."""

    def test_starts_with_digit(self):
        """Test that an identifier starting with a digit returns None."""
        result = _parse_identifier_parts('123table')
        assert result is None

    def test_hyphen(self):
        """Test that an unquoted identifier with hyphen returns None."""
        result = _parse_identifier_parts('my-table')
        assert result is None

    def test_space(self):
        """Test that an unquoted identifier with space returns None."""
        result = _parse_identifier_parts('my table')
        assert result is None

    def test_semicolon(self):
        """Test that an identifier with semicolon returns None."""
        result = _parse_identifier_parts('users;')
        assert result is None

    def test_single_quote(self):
        """Test that an identifier with single quote returns None."""
        result = _parse_identifier_parts("users'")
        assert result is None

    def test_parenthesis(self):
        """Test that an identifier with parentheses returns None."""
        result = _parse_identifier_parts('users()')
        assert result is None

    def test_starts_with_dot(self):
        """Test that a leading dot returns None."""
        result = _parse_identifier_parts('.users')
        assert result is None

    def test_empty_string(self):
        """Test that an empty string returns None."""
        result = _parse_identifier_parts('')
        assert result is None

    def test_dollar_sign_start(self):
        """Test that an identifier starting with dollar sign returns None."""
        result = _parse_identifier_parts('$table')
        assert result is None


class TestParseIdentifierPartsQuoted:
    """Tests for _parse_identifier_parts with quoted identifiers."""

    def test_simple_quoted(self):
        """Test parsing a simple quoted identifier."""
        result = _parse_identifier_parts('"users"')
        assert result == ['users']

    def test_quoted_with_hyphen(self):
        """Test parsing a quoted identifier containing a hyphen."""
        result = _parse_identifier_parts('"my-table"')
        assert result == ['my-table']

    def test_quoted_with_spaces(self):
        """Test parsing a quoted identifier containing spaces."""
        result = _parse_identifier_parts('"table with spaces"')
        assert result == ['table with spaces']

    def test_quoted_with_special_chars(self):
        """Test parsing a quoted identifier containing special characters."""
        result = _parse_identifier_parts('"hello!@#%^&*()"')
        assert result == ['hello!@#%^&*()']

    def test_quoted_with_digits_first(self):
        """Test parsing a quoted identifier starting with digits."""
        result = _parse_identifier_parts('"123table"')
        assert result == ['123table']

    def test_quoted_with_semicolon(self):
        """Test parsing a quoted identifier containing semicolon."""
        result = _parse_identifier_parts('"has;semicolon"')
        assert result == ['has;semicolon']

    def test_quoted_with_single_quote(self):
        """Test parsing a quoted identifier containing single quote."""
        result = _parse_identifier_parts('"has\'quote"')
        assert result == ["has'quote"]

    def test_escaped_double_quote(self):
        """Test parsing a quoted identifier with escaped double quote."""
        result = _parse_identifier_parts('"has""quote"')
        assert result == ['has"quote']

    def test_multiple_escaped_double_quotes(self):
        """Test parsing a quoted identifier with multiple escaped double quotes."""
        result = _parse_identifier_parts('"a""b""c"')
        assert result == ['a"b"c']

    def test_quoted_single_char(self):
        """Test parsing a quoted single character identifier."""
        result = _parse_identifier_parts('"x"')
        assert result == ['x']

    def test_quoted_unicode(self):
        """Test parsing a quoted identifier with unicode characters."""
        result = _parse_identifier_parts('"données"')
        assert result == ['données']

    def test_quoted_newline(self):
        """Test that a quoted identifier containing newline is valid."""
        result = _parse_identifier_parts('"line1\nline2"')
        assert result == ['line1\nline2']

    def test_quoted_tab(self):
        """Test that a quoted identifier containing tab is valid."""
        result = _parse_identifier_parts('"has\ttab"')
        assert result == ['has\ttab']

    def test_quoted_dot_inside(self):
        """Test that a dot inside quotes is part of the identifier, not a separator."""
        result = _parse_identifier_parts('"a.b"')
        assert result == ['a.b']

    def test_quoted_only_escaped_quote(self):
        """Test parsing a quoted identifier whose content is a single double quote."""
        # '""""' = opening quote, escaped quote (""), closing quote → identifier is '"'
        result = _parse_identifier_parts('""""')
        assert result == ['"']


class TestParseIdentifierPartsQuotedInvalid:
    """Tests for _parse_identifier_parts with invalid quoted identifiers."""

    def test_zero_length_quoted(self):
        """Test that a zero-length quoted identifier returns None."""
        result = _parse_identifier_parts('""')
        assert result is None

    def test_unclosed_quote(self):
        """Test that an unclosed quoted identifier returns None."""
        result = _parse_identifier_parts('"unclosed')
        assert result is None

    def test_nul_character(self):
        """Test that a NUL character inside a quoted identifier returns None."""
        result = _parse_identifier_parts('"has\0null"')
        assert result is None

    def test_opening_quote_only(self):
        """Test that a single opening quote returns None."""
        result = _parse_identifier_parts('"')
        assert result is None


class TestParseIdentifierPartsSchemaQualified:
    """Tests for _parse_identifier_parts with schema-qualified names."""

    def test_two_parts_unquoted(self):
        """Test parsing a two-part schema.table name."""
        result = _parse_identifier_parts('public.users')
        assert result == ['public', 'users']

    def test_three_parts_unquoted(self):
        """Test parsing a three-part catalog.schema.table name."""
        result = _parse_identifier_parts('mydb.public.users')
        assert result == ['mydb', 'public', 'users']

    def test_four_parts_unquoted(self):
        """Test that parser returns four parts (MAX_PARTS enforced in validate_table_name)."""
        result = _parse_identifier_parts('a.b.c.d')
        assert result == ['a', 'b', 'c', 'd']

    def test_two_parts_both_quoted(self):
        """Test parsing a two-part name with both parts quoted."""
        result = _parse_identifier_parts('"My Schema"."My Table"')
        assert result == ['My Schema', 'My Table']

    def test_mixed_quoted_unquoted(self):
        """Test parsing a two-part name with mixed quoting."""
        result = _parse_identifier_parts('public."My-Table"')
        assert result == ['public', 'My-Table']

    def test_quoted_then_unquoted(self):
        """Test parsing a two-part name: quoted schema, unquoted table."""
        result = _parse_identifier_parts('"My Schema".users')
        assert result == ['My Schema', 'users']

    def test_three_parts_mixed(self):
        """Test parsing a three-part name with mixed quoting."""
        result = _parse_identifier_parts('mydb."my schema"."my-table"')
        assert result == ['mydb', 'my schema', 'my-table']

    def test_pg_catalog(self):
        """Test parsing pg_catalog.pg_class."""
        result = _parse_identifier_parts('pg_catalog.pg_class')
        assert result == ['pg_catalog', 'pg_class']

    def test_all_parts_quoted_with_escapes(self):
        """Test parsing multi-part name where each part has escaped quotes."""
        result = _parse_identifier_parts('"a""1"."b""2"')
        assert result == ['a"1', 'b"2']


class TestParseIdentifierPartsDotEdgeCases:
    """Tests for _parse_identifier_parts with dot separator edge cases."""

    def test_trailing_dot(self):
        """Test that a trailing dot returns None."""
        result = _parse_identifier_parts('users.')
        assert result is None

    def test_leading_dot(self):
        """Test that a leading dot returns None."""
        result = _parse_identifier_parts('.users')
        assert result is None

    def test_double_dot(self):
        """Test that consecutive dots return None."""
        result = _parse_identifier_parts('public..users')
        assert result is None

    def test_only_dot(self):
        """Test that a single dot returns None."""
        result = _parse_identifier_parts('.')
        assert result is None

    def test_dot_after_quoted_identifier(self):
        """Test that a trailing dot after a quoted identifier returns None."""
        result = _parse_identifier_parts('"schema".')
        assert result is None

    def test_dot_before_quoted_identifier(self):
        """Test that a leading dot before a quoted identifier returns None."""
        result = _parse_identifier_parts('."table"')
        assert result is None


class TestParseIdentifierPartsSQLInjection:
    """Tests for _parse_identifier_parts with SQL injection attempts."""

    def test_union_injection(self):
        """Test that UNION-based injection returns None."""
        result = _parse_identifier_parts(
            "public.users') UNION SELECT usename, passwd, null FROM pg_shadow--"
        )
        assert result is None

    def test_drop_table_injection(self):
        """Test that DROP TABLE injection returns None."""
        result = _parse_identifier_parts('users; DROP TABLE users; --')
        assert result is None

    def test_comment_injection(self):
        """Test that comment injection returns None."""
        result = _parse_identifier_parts('users--')
        assert result is None

    def test_semicolon_injection(self):
        """Test that semicolon-based injection returns None."""
        result = _parse_identifier_parts('users;SELECT 1')
        assert result is None

    def test_backslash_escape_attempt(self):
        """Test that backslash escape attempt returns None."""
        result = _parse_identifier_parts('users\\')
        assert result is None

    def test_single_quote_escape_attempt(self):
        """Test that single quote escape attempt returns None."""
        result = _parse_identifier_parts("users'OR'1'='1")
        assert result is None

    def test_quoted_injection_is_treated_as_literal(self):
        """Test that SQL keywords inside quotes are treated as a literal identifier name."""
        result = _parse_identifier_parts('"users; DROP TABLE foo"')
        assert result == ['users; DROP TABLE foo']


# ============================================================================
# Tests for validate_table_name
# ============================================================================


class TestValidateTableNameValid:
    """Tests for validate_table_name with legitimate PostgreSQL table names."""

    def test_simple_name(self):
        """Test that a simple table name is valid."""
        assert validate_table_name('users') is True

    def test_leading_underscore(self):
        """Test that a name starting with underscore is valid."""
        assert validate_table_name('_my_table') is True

    def test_with_digits(self):
        """Test that a name containing digits is valid."""
        assert validate_table_name('table123') is True

    def test_with_dollar_sign(self):
        """Test that a name containing dollar sign is valid."""
        assert validate_table_name('my$table') is True

    def test_schema_qualified(self):
        """Test that a schema-qualified name is valid."""
        assert validate_table_name('public.users') is True

    def test_fully_qualified(self):
        """Test that a fully qualified catalog.schema.table name is valid."""
        assert validate_table_name('mydb.public.users') is True

    def test_quoted_simple(self):
        """Test that a simple quoted identifier is valid."""
        assert validate_table_name('"my-table"') is True

    def test_quoted_with_spaces(self):
        """Test that a quoted identifier with spaces is valid."""
        assert validate_table_name('"table with spaces"') is True

    def test_quoted_with_special_chars(self):
        """Test that a quoted identifier with special characters is valid."""
        assert validate_table_name('"hello!@#%^&*()"') is True

    def test_quoted_escaped_double_quote(self):
        """Test that a quoted identifier with escaped double quote is valid."""
        assert validate_table_name('"has""quote"') is True

    def test_mixed_quoting(self):
        """Test that mixed quoted/unquoted multi-part name is valid."""
        assert validate_table_name('public."My-Table"') is True

    def test_both_quoted(self):
        """Test that both-quoted multi-part name is valid."""
        assert validate_table_name('"My Schema"."My Table"') is True

    def test_unicode_unquoted(self):
        """Test that unicode letters in unquoted identifier are valid."""
        assert validate_table_name('données') is True

    def test_unicode_schema_qualified(self):
        """Test that unicode letters in schema-qualified name are valid."""
        assert validate_table_name('schéma.données') is True

    def test_single_char(self):
        """Test that a single character identifier is valid."""
        assert validate_table_name('a') is True

    def test_quoted_single_char(self):
        """Test that a single character quoted identifier is valid."""
        assert validate_table_name('"x"') is True

    def test_pg_catalog(self):
        """Test that pg_catalog.pg_class is valid."""
        assert validate_table_name('pg_catalog.pg_class') is True

    def test_all_underscores(self):
        """Test that all-underscore identifier is valid."""
        assert validate_table_name('___') is True

    def test_uppercase(self):
        """Test that uppercase identifier is valid."""
        assert validate_table_name('MyTable') is True

    def test_max_length_identifier(self):
        """Test that an identifier at exactly MAX_IDENTIFIER_BYTES is valid."""
        name = 'a' * MAX_IDENTIFIER_BYTES
        assert validate_table_name(name) is True

    def test_max_length_each_part(self):
        """Test that each part at exactly MAX_IDENTIFIER_BYTES is valid."""
        schema = 's' * MAX_IDENTIFIER_BYTES
        table = 't' * MAX_IDENTIFIER_BYTES
        assert validate_table_name(f'{schema}.{table}') is True

    def test_three_parts_max_length_each(self):
        """Test that three parts each at exactly MAX_IDENTIFIER_BYTES is valid."""
        catalog = 'c' * MAX_IDENTIFIER_BYTES
        schema = 's' * MAX_IDENTIFIER_BYTES
        table = 't' * MAX_IDENTIFIER_BYTES
        assert validate_table_name(f'{catalog}.{schema}.{table}') is True

    def test_unicode_multibyte_at_limit(self):
        """Test that unicode identifier at exactly MAX_IDENTIFIER_BYTES is valid."""
        # 'é' is 2 bytes in UTF-8: 31 * 2 = 62 bytes + 'a' = 63 bytes
        name = 'é' * 31 + 'a'
        assert validate_table_name(name) is True

    def test_quoted_sql_keywords_is_valid(self):
        """Test that SQL keywords inside quotes are treated as a valid literal name."""
        assert validate_table_name('"users; DROP TABLE foo"') is True

    def test_quoted_union_is_valid(self):
        """Test that UNION keyword inside quotes is treated as a valid literal name."""
        assert validate_table_name('"UNION SELECT 1,2,3"') is True

    def test_exactly_three_parts(self):
        """Test that exactly three parts is valid."""
        assert validate_table_name('a.b.c') is True

    def test_exactly_two_parts(self):
        """Test that exactly two parts is valid."""
        assert validate_table_name('a.b') is True

    def test_dollar_sign_subsequent(self):
        """Test that dollar sign in subsequent position is valid."""
        assert validate_table_name('a$') is True


class TestValidateTableNameInvalidType:
    """Tests for validate_table_name with invalid input types."""

    def test_empty_string(self):
        """Test that empty string is rejected."""
        assert validate_table_name('') is False


class TestValidateTableNameInvalidIdentifier:
    """Tests for validate_table_name with invalid identifiers."""

    def test_zero_length_quoted(self):
        """Test that zero-length quoted identifier is rejected."""
        assert validate_table_name('""') is False

    def test_leading_dot(self):
        """Test that leading dot is rejected."""
        assert validate_table_name('.users') is False

    def test_trailing_dot(self):
        """Test that trailing dot is rejected."""
        assert validate_table_name('users.') is False

    def test_double_dot(self):
        """Test that consecutive dots are rejected."""
        assert validate_table_name('public..users') is False

    def test_starts_with_digit_unquoted(self):
        """Test that unquoted identifier starting with digit is rejected."""
        assert validate_table_name('123table') is False

    def test_hyphen_unquoted(self):
        """Test that unquoted identifier with hyphen is rejected."""
        assert validate_table_name('my-table') is False

    def test_space_unquoted(self):
        """Test that unquoted identifier with space is rejected."""
        assert validate_table_name('my table') is False

    def test_unclosed_quote(self):
        """Test that unclosed quoted identifier is rejected."""
        assert validate_table_name('"unclosed') is False

    def test_only_dot(self):
        """Test that a single dot is rejected."""
        assert validate_table_name('.') is False

    def test_nul_in_quoted(self):
        """Test that NUL character in quoted identifier is rejected."""
        assert validate_table_name('"has\0null"') is False

    def test_whitespace_only(self):
        """Test that whitespace-only string is rejected."""
        assert validate_table_name('   ') is False

    def test_newline(self):
        """Test that unquoted identifier with newline is rejected."""
        assert validate_table_name('users\n') is False

    def test_tab(self):
        """Test that unquoted identifier with tab is rejected."""
        assert validate_table_name('users\t') is False

    def test_carriage_return(self):
        """Test that unquoted identifier with carriage return is rejected."""
        assert validate_table_name('users\r') is False

    def test_dollar_sign_start(self):
        """Test that unquoted identifier starting with dollar sign is rejected."""
        assert validate_table_name('$table') is False

    def test_backtick(self):
        """Test that backtick-quoted identifier is rejected (MySQL syntax, not PostgreSQL)."""
        assert validate_table_name('`users`') is False


class TestValidateTableNameTooManyParts:
    """Tests for validate_table_name with too many dot-separated parts."""

    def test_four_parts(self):
        """Test that four dot-separated parts are rejected."""
        assert validate_table_name('a.b.c.d') is False

    def test_five_parts(self):
        """Test that five dot-separated parts are rejected."""
        assert validate_table_name('a.b.c.d.e') is False

    def test_four_parts_quoted(self):
        """Test that four quoted dot-separated parts are rejected."""
        assert validate_table_name('"a"."b"."c"."d"') is False


class TestValidateTableNameIdentifierTooLong:
    """Tests for validate_table_name with identifiers exceeding MAX_IDENTIFIER_BYTES."""

    def test_one_byte_over_limit(self):
        """Test that an identifier one byte over the limit is rejected."""
        name = 'a' * (MAX_IDENTIFIER_BYTES + 1)
        assert validate_table_name(name) is False

    def test_schema_part_too_long(self):
        """Test that a schema part exceeding the limit is rejected."""
        long_schema = 's' * (MAX_IDENTIFIER_BYTES + 1)
        assert validate_table_name(f'{long_schema}.users') is False

    def test_table_part_too_long(self):
        """Test that a table part exceeding the limit is rejected."""
        long_table = 't' * (MAX_IDENTIFIER_BYTES + 1)
        assert validate_table_name(f'public.{long_table}') is False

    def test_quoted_identifier_too_long(self):
        """Test that a quoted identifier exceeding the limit is rejected."""
        long_name = '"' + 'a' * (MAX_IDENTIFIER_BYTES + 1) + '"'
        assert validate_table_name(long_name) is False

    def test_unicode_multibyte_over_limit(self):
        """Test that a unicode identifier exceeding the byte limit is rejected."""
        # 'é' is 2 bytes in UTF-8: 32 * 2 = 64 bytes > 63
        name = 'é' * 32
        assert validate_table_name(name) is False


class TestValidateTableNameSQLInjection:
    """Tests for validate_table_name with SQL injection attempts."""

    def test_union_injection(self):
        """Test that UNION-based SQL injection is rejected."""
        assert (
            validate_table_name(
                "public.users') UNION SELECT usename, passwd, null FROM pg_shadow--"
            )
            is False
        )

    def test_drop_table_injection(self):
        """Test that DROP TABLE injection is rejected."""
        assert validate_table_name('users; DROP TABLE users; --') is False

    def test_semicolon_injection(self):
        """Test that semicolon-based injection is rejected."""
        assert validate_table_name('users;') is False

    def test_comment_injection_double_dash(self):
        """Test that double-dash comment injection is rejected."""
        assert validate_table_name('users--') is False

    def test_comment_injection_block(self):
        """Test that block comment injection is rejected."""
        assert validate_table_name('users/**/') is False

    def test_single_quote_injection(self):
        """Test that single quote injection is rejected."""
        assert validate_table_name("users'") is False

    def test_or_1_equals_1(self):
        """Test that OR 1=1 injection is rejected."""
        assert validate_table_name("users' OR '1'='1") is False

    def test_stacked_query(self):
        """Test that stacked query injection is rejected."""
        assert validate_table_name('users; SELECT pg_sleep(5)--') is False

    def test_hex_escape_attempt(self):
        """Test that hex escape injection attempt is rejected."""
        assert validate_table_name('users\\x27') is False

    def test_encoded_space(self):
        """Test that URL-encoded space injection is rejected."""
        assert validate_table_name('users%20') is False

    def test_subquery_attempt(self):
        """Test that subquery injection attempt is rejected."""
        assert validate_table_name('(SELECT 1)') is False

    def test_backtick_injection(self):
        """Test that backtick injection attempt is rejected."""
        assert validate_table_name('`users`') is False
