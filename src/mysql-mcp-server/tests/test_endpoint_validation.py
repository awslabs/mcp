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

"""Tests for endpoint validation in internal_connect_to_database().

These tests verify the endpoint validation security fix: caller-supplied
db_endpoint must be validated against the cluster's actual AWS-resolved
endpoints. A mismatch must be rejected with a ValueError to prevent
credential exfiltration to attacker-controlled hosts.
"""

import awslabs.mysql_mcp_server.server as server_module
import json
import pytest
from awslabs.mysql_mcp_server.connection.cp_api_connection import (
    DEFAULT_MYSQL_PORT,
    internal_get_cluster_valid_endpoints,
)
from awslabs.mysql_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DatabaseType,
    DBConnectionMap,
)
from awslabs.mysql_mcp_server.server import internal_connect_to_database
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

CLUSTER_ID = 'test-cluster'
WRITER_ENDPOINT = 'test-cluster.cluster-abc123.us-east-1.rds.amazonaws.com'
READER_ENDPOINT = 'test-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com'
CUSTOM_ENDPOINT = 'test-cluster-custom.cluster-custom-abc123.us-east-1.rds.amazonaws.com'
INSTANCE_ENDPOINT = 'test-cluster-instance-1.abc123.us-east-1.rds.amazonaws.com'
CLUSTER_PORT = 3306
REGION = 'us-east-1'
SECRET_ARN = 'arn:aws:secretsmanager:us-east-1:123456789012:secret:rds!cluster-test'


def _make_cluster_properties(
    writer=WRITER_ENDPOINT,
    reader=READER_ENDPOINT,
    custom_endpoints=None,
    members=None,
    port=CLUSTER_PORT,
):
    """Build a minimal cluster_properties dict for testing."""
    props = {
        'DBClusterIdentifier': CLUSTER_ID,
        'DBClusterArn': f'arn:aws:rds:us-east-1:123456789012:cluster:{CLUSTER_ID}',
        'Endpoint': writer,
        'ReaderEndpoint': reader,
        'Port': port,
        'MasterUsername': 'admin',
        'MasterUserSecret': {'SecretArn': SECRET_ARN},
        'HttpEndpointEnabled': False,
        'Status': 'available',
        'Engine': 'aurora-mysql',
    }
    if custom_endpoints:
        props['CustomEndpoints'] = custom_endpoints
    if members:
        props['DBClusterMembers'] = members
    return props


# ---------------------------------------------------------------------------
# Tests for internal_get_cluster_valid_endpoints()
# ---------------------------------------------------------------------------


class TestGetClusterValidEndpoints:
    """Tests for the endpoint collection function."""

    def test_returns_writer_and_reader(self):
        """Should include both writer and reader endpoints."""
        props = _make_cluster_properties()
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            endpoints = internal_get_cluster_valid_endpoints(props, REGION)

        assert (WRITER_ENDPOINT, CLUSTER_PORT) in endpoints
        assert (READER_ENDPOINT, CLUSTER_PORT) in endpoints

    def test_returns_custom_endpoints(self):
        """Should include custom endpoints."""
        props = _make_cluster_properties(custom_endpoints=[CUSTOM_ENDPOINT])
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            endpoints = internal_get_cluster_valid_endpoints(props, REGION)

        assert (CUSTOM_ENDPOINT, CLUSTER_PORT) in endpoints

    def test_returns_member_instance_endpoints(self):
        """Should include individual member instance endpoints."""
        props = _make_cluster_properties(
            members=[{'DBInstanceIdentifier': 'test-cluster-instance-1'}]
        )
        mock_rds = MagicMock()
        mock_rds.describe_db_instances.return_value = {
            'DBInstances': [{'Endpoint': {'Address': INSTANCE_ENDPOINT, 'Port': 3306}}]
        }
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            endpoints = internal_get_cluster_valid_endpoints(props, REGION)

        assert (INSTANCE_ENDPOINT, CLUSTER_PORT) in endpoints

    def test_raises_when_no_endpoints(self):
        """Should raise ValueError if no valid endpoints can be resolved."""
        props = _make_cluster_properties(writer='', reader='')
        props['Port'] = 0
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            with pytest.raises(ValueError, match='no valid connection endpoints'):
                internal_get_cluster_valid_endpoints(props, REGION)

    def test_defaults_to_mysql_port_on_invalid(self):
        """Should fall back to DEFAULT_MYSQL_PORT if Port is invalid."""
        props = _make_cluster_properties()
        props['Port'] = 'invalid'
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            endpoints = internal_get_cluster_valid_endpoints(props, REGION)

        assert (WRITER_ENDPOINT, DEFAULT_MYSQL_PORT) in endpoints

    def test_continues_on_instance_lookup_failure(self):
        """Should not fail if a single instance describe fails."""
        from botocore.exceptions import ClientError

        props = _make_cluster_properties(members=[{'DBInstanceIdentifier': 'bad-instance'}])
        mock_rds = MagicMock()
        mock_rds.describe_db_instances.side_effect = ClientError(
            {'Error': {'Code': 'DBInstanceNotFound', 'Message': 'Not found'}},
            'DescribeDBInstances',
        )
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            # Should still return writer + reader (not raise)
            endpoints = internal_get_cluster_valid_endpoints(props, REGION)

        assert (WRITER_ENDPOINT, CLUSTER_PORT) in endpoints


# ---------------------------------------------------------------------------
# Tests for endpoint validation in internal_connect_to_database()
# ---------------------------------------------------------------------------


class TestEndpointValidation:
    """Tests that caller-supplied db_endpoint is validated against AWS endpoints."""

    def setup_method(self):
        """Reset server global state before each test."""
        server_module.db_connection_map = DBConnectionMap()
        server_module.readonly_query = True
        server_module.ca_bundle_path = None

    def _mock_rds_client(self):
        """Create a mock RDS client returning test cluster properties."""
        mock_rds = MagicMock()
        mock_rds.describe_db_clusters.return_value = {'DBClusters': [_make_cluster_properties()]}
        return mock_rds

    def test_valid_writer_endpoint_accepted(self):
        """Connection with the cluster's real writer endpoint should succeed."""
        mock_rds = self._mock_rds_client()
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'admin', 'password': 'pass'})
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=mock_rds,
            ),
            patch('boto3.Session', return_value=mock_session),
            patch('asyncmy.create_pool', return_value=MagicMock()),
        ):
            conn, resp = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier=CLUSTER_ID,
                db_endpoint=WRITER_ENDPOINT,
                port=CLUSTER_PORT,
                database='testdb',
            )
            assert conn is not None
            resp_dict = json.loads(resp)
            assert resp_dict['db_endpoint'] == WRITER_ENDPOINT

    def test_valid_reader_endpoint_accepted(self):
        """Connection with the cluster's reader endpoint should succeed."""
        mock_rds = self._mock_rds_client()
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'admin', 'password': 'pass'})
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=mock_rds,
            ),
            patch('boto3.Session', return_value=mock_session),
            patch('asyncmy.create_pool', return_value=MagicMock()),
        ):
            conn, resp = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier=CLUSTER_ID,
                db_endpoint=READER_ENDPOINT,
                port=CLUSTER_PORT,
                database='testdb',
            )
            assert conn is not None

    def test_bogus_endpoint_rejected(self):
        """Connection with an attacker-controlled endpoint must be rejected."""
        mock_rds = self._mock_rds_client()

        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            with pytest.raises(ValueError, match='does not match any endpoint'):
                internal_connect_to_database(
                    region=REGION,
                    database_type=DatabaseType.AURORA_MYSQL,
                    connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                    cluster_identifier=CLUSTER_ID,
                    db_endpoint='attacker.evil.com',
                    port=CLUSTER_PORT,
                    database='testdb',
                )

    def test_wrong_port_rejected(self):
        """Valid host with wrong port must be rejected."""
        mock_rds = self._mock_rds_client()

        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            with pytest.raises(ValueError, match='does not match any endpoint'):
                internal_connect_to_database(
                    region=REGION,
                    database_type=DatabaseType.AURORA_MYSQL,
                    connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                    cluster_identifier=CLUSTER_ID,
                    db_endpoint=WRITER_ENDPOINT,
                    port=9999,
                    database='testdb',
                )

    def test_case_insensitive_match(self):
        """Endpoint comparison should be case-insensitive (DNS is case-insensitive)."""
        mock_rds = self._mock_rds_client()
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'admin', 'password': 'pass'})
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=mock_rds,
            ),
            patch('boto3.Session', return_value=mock_session),
            patch('asyncmy.create_pool', return_value=MagicMock()),
        ):
            conn, resp = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier=CLUSTER_ID,
                db_endpoint=WRITER_ENDPOINT.upper(),
                port=CLUSTER_PORT,
                database='testdb',
            )
            assert conn is not None

    def test_empty_endpoint_uses_cluster_writer(self):
        """When db_endpoint is empty, server should use the cluster's writer endpoint."""
        mock_rds = self._mock_rds_client()
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'admin', 'password': 'pass'})
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=mock_rds,
            ),
            patch('boto3.Session', return_value=mock_session),
            patch('asyncmy.create_pool', return_value=MagicMock()),
        ):
            conn, resp = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier=CLUSTER_ID,
                db_endpoint='',
                port=CLUSTER_PORT,
                database='testdb',
            )
            assert conn is not None
            resp_dict = json.loads(resp)
            assert resp_dict['db_endpoint'] == WRITER_ENDPOINT

    def test_localhost_rejected(self):
        """Localhost/loopback addresses must be rejected (common attack vector)."""
        mock_rds = self._mock_rds_client()

        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            with pytest.raises(ValueError, match='does not match any endpoint'):
                internal_connect_to_database(
                    region=REGION,
                    database_type=DatabaseType.AURORA_MYSQL,
                    connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                    cluster_identifier=CLUSTER_ID,
                    db_endpoint='127.0.0.1',
                    port=CLUSTER_PORT,
                    database='testdb',
                )

    def test_ip_address_rejected(self):
        """Arbitrary IP addresses must be rejected."""
        mock_rds = self._mock_rds_client()

        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            with pytest.raises(ValueError, match='does not match any endpoint'):
                internal_connect_to_database(
                    region=REGION,
                    database_type=DatabaseType.AURORA_MYSQL,
                    connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                    cluster_identifier=CLUSTER_ID,
                    db_endpoint='10.0.0.1',
                    port=CLUSTER_PORT,
                    database='testdb',
                )


# ---------------------------------------------------------------------------
# Tests for standalone instance path (server.py RPG overwrite)
# ---------------------------------------------------------------------------


class TestStandaloneInstancePath:
    """Tests for the standalone RDS instance path (no cluster_identifier)."""

    def setup_method(self):
        """Reset server global state before each test."""
        server_module.db_connection_map = DBConnectionMap()
        server_module.readonly_query = True
        server_module.ca_bundle_path = None

    def test_standalone_instance_overwrites_endpoint(self):
        """Standalone instance path should overwrite db_endpoint with AWS-sourced value."""
        mock_rds = MagicMock()
        # Paginator mock for internal_get_instance_properties
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'DBInstances': [
                    {
                        'Endpoint': {
                            'Address': 'real-instance.abc123.us-east-1.rds.amazonaws.com',
                            'Port': 3306,
                        },
                        'MasterUsername': 'admin',
                        'MasterUserSecret': {'SecretArn': SECRET_ARN},
                    }
                ]
            }
        ]
        mock_rds.get_paginator.return_value = mock_paginator

        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'admin', 'password': 'pass'})
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=mock_rds,
            ),
            patch('boto3.Session', return_value=mock_session),
            patch('asyncmy.create_pool', return_value=MagicMock()),
        ):
            conn, resp = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.RDS_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='real-instance.abc123.us-east-1.rds.amazonaws.com',
                port=CLUSTER_PORT,
                database='testdb',
            )
            resp_dict = json.loads(resp)
            # Should use the AWS-resolved endpoint
            assert resp_dict['db_endpoint'] == 'real-instance.abc123.us-east-1.rds.amazonaws.com'

    def test_standalone_instance_invalid_port_fallback(self):
        """Standalone instance with invalid port should fall back to DEFAULT_MYSQL_PORT."""
        mock_rds = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'DBInstances': [
                    {
                        'Endpoint': {
                            'Address': 'real-instance.abc123.us-east-1.rds.amazonaws.com',
                            'Port': 'invalid',
                        },
                        'MasterUsername': 'admin',
                        'MasterUserSecret': {'SecretArn': SECRET_ARN},
                    }
                ]
            }
        ]
        mock_rds.get_paginator.return_value = mock_paginator

        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'admin', 'password': 'pass'})
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=mock_rds,
            ),
            patch('boto3.Session', return_value=mock_session),
            patch('asyncmy.create_pool', return_value=MagicMock()),
        ):
            conn, resp = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.RDS_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='real-instance.abc123.us-east-1.rds.amazonaws.com',
                port=3306,
                database='testdb',
            )
            assert conn is not None


# ---------------------------------------------------------------------------
# Tests for SSL context on Secrets Manager path (asyncmy_pool_connection.py)
# ---------------------------------------------------------------------------


class TestSecretArnSSLContext:
    """Tests for TLS enforcement on the Secrets Manager credential path."""

    async def test_ssl_context_created_when_no_ca_bundle(self):
        """Should create SSL context from system store when bundled CA is missing."""
        import awslabs.mysql_mcp_server.connection.asyncmy_pool_connection as mod
        from awslabs.mysql_mcp_server.connection.asyncmy_pool_connection import (
            AsyncmyPoolConnection,
        )
        from unittest.mock import AsyncMock
        from unittest.mock import patch as mock_patch

        # Simulate missing CA bundle
        with (
            mock_patch.object(mod, '_bundled_ca_file', return_value=None),
            mock_patch.object(mod.asyncmy, 'create_pool', new_callable=AsyncMock) as mock_pool,
        ):
            conn = AsyncmyPoolConnection(
                host='localhost',
                port=3306,
                database='testdb',
                readonly=True,
                secret_arn='arn:secret',
                db_user='',
                region='us-east-1',
                is_iam_auth=False,
                is_test=True,
            )
            await conn.initialize_pool()

            # SSL context should still be created (from system store)
            call_kwargs = mock_pool.call_args[1]
            assert call_kwargs['ssl'] is not None

    def test_member_instance_invalid_port_excluded(self):
        """Member instance with invalid port should be excluded from valid endpoints."""
        props = _make_cluster_properties(members=[{'DBInstanceIdentifier': 'instance-bad-port'}])
        mock_rds = MagicMock()
        mock_rds.describe_db_instances.return_value = {
            'DBInstances': [
                {
                    'Endpoint': {
                        'Address': 'instance-bad-port.abc.rds.amazonaws.com',
                        'Port': 'invalid',
                    }
                }
            ]
        }
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            endpoints = internal_get_cluster_valid_endpoints(props, REGION)

        # Instance with invalid port excluded, but writer/reader still included
        assert (WRITER_ENDPOINT, CLUSTER_PORT) in endpoints
        assert not any(ep[0] == 'instance-bad-port.abc.rds.amazonaws.com' for ep in endpoints)

    def test_cluster_port_none_excludes_endpoints(self):
        """When Port is None (cluster_port=0), endpoints are excluded and ValueError raised."""
        props = _make_cluster_properties()
        props['Port'] = None  # Force port=0 path
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            with pytest.raises(ValueError, match='no valid connection endpoints'):
                internal_get_cluster_valid_endpoints(props, REGION)


class TestStandaloneInstanceEdgeCases:
    """Tests for edge cases in the standalone instance path."""

    def setup_method(self):
        """Reset server global state before each test."""
        server_module.db_connection_map = DBConnectionMap()
        server_module.readonly_query = True
        server_module.ca_bundle_path = None

    def test_standalone_instance_empty_host_preserves_original(self):
        """When AWS returns empty Address, db_endpoint is not overwritten."""
        mock_rds = MagicMock()
        mock_rds.describe_db_clusters.return_value = {'DBClusters': []}

        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'admin', 'password': 'pass'})
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm

        mock_instance_props = {
            'Endpoint': {'Address': '', 'Port': 3306},
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': SECRET_ARN},
        }

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=mock_rds,
            ),
            patch(
                'awslabs.mysql_mcp_server.server.internal_get_instance_properties',
                return_value=mock_instance_props,
            ),
            patch('boto3.Session', return_value=mock_session),
            patch('asyncmy.create_pool', return_value=MagicMock()),
        ):
            conn, resp = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.RDS_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='my-instance.abc.us-east-1.rds.amazonaws.com',
                port=CLUSTER_PORT,
                database='testdb',
            )
            resp_dict = json.loads(resp)
            # Empty resolved_host means original db_endpoint preserved
            assert resp_dict['db_endpoint'] == 'my-instance.abc.us-east-1.rds.amazonaws.com'

    async def test_ssl_context_with_ca_bundle_for_secret_arn(self):
        """Should use bundled CA when available for Secrets Manager path."""
        import awslabs.mysql_mcp_server.connection.asyncmy_pool_connection as mod
        from awslabs.mysql_mcp_server.connection.asyncmy_pool_connection import (
            AsyncmyPoolConnection,
        )
        from unittest.mock import AsyncMock
        from unittest.mock import MagicMock as MM
        from unittest.mock import patch as mock_patch

        fake_ctx = MM()

        # Simulate CA bundle present + mock ssl context creation
        with (
            mock_patch.object(mod, '_bundled_ca_file', return_value='/path/to/bundle.pem'),
            mock_patch.object(mod.ssl_module, 'create_default_context', return_value=fake_ctx),
            mock_patch.object(mod.asyncmy, 'create_pool', new_callable=AsyncMock) as mock_pool,
        ):
            conn = AsyncmyPoolConnection(
                host='localhost',
                port=3306,
                database='testdb',
                readonly=True,
                secret_arn='arn:secret',
                db_user='',
                region='us-east-1',
                is_iam_auth=False,
                is_test=True,
            )
            await conn.initialize_pool()

            call_kwargs = mock_pool.call_args[1]
            assert call_kwargs['ssl'] is fake_ctx

    def test_standalone_instance_zero_port_uses_default(self):
        """When resolved_port is 0, original port is preserved."""
        mock_instance_props = {
            'Endpoint': {'Address': 'real-host.rds.amazonaws.com', 'Port': 0},
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': SECRET_ARN},
        }

        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'admin', 'password': 'pass'})
        }
        mock_session = MagicMock()
        mock_session.client.return_value = mock_sm

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=MagicMock(),
            ),
            patch(
                'awslabs.mysql_mcp_server.server.internal_get_instance_properties',
                return_value=mock_instance_props,
            ),
            patch('boto3.Session', return_value=mock_session),
            patch('asyncmy.create_pool', return_value=MagicMock()),
        ):
            conn, resp = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.RDS_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier='',
                db_endpoint='my-instance.rds.amazonaws.com',
                port=3306,
                database='testdb',
            )
            resp_dict = json.loads(resp)
            # resolved_port=0 means port not overwritten, keeps original 3306
            assert resp_dict['port'] == 3306

    async def test_no_ssl_when_no_secret_arn_and_no_iam(self):
        """When neither secret_arn nor is_iam_auth is set, ssl_ctx stays None."""
        import awslabs.mysql_mcp_server.connection.asyncmy_pool_connection as mod
        from awslabs.mysql_mcp_server.connection.asyncmy_pool_connection import (
            AsyncmyPoolConnection,
        )
        from unittest.mock import AsyncMock
        from unittest.mock import patch as mock_patch

        with mock_patch.object(mod.asyncmy, 'create_pool', new_callable=AsyncMock) as mock_pool:
            conn = AsyncmyPoolConnection(
                host='localhost',
                port=3306,
                database='testdb',
                readonly=True,
                secret_arn='',  # No secret_arn
                db_user='testuser',
                region='us-east-1',
                is_iam_auth=False,  # No IAM auth
                is_test=True,
            )
            await conn.initialize_pool()

            call_kwargs = mock_pool.call_args[1]
            assert call_kwargs['ssl'] is None  # No TLS when no credentials path

    def test_empty_custom_endpoints_list(self):
        """CustomEndpoints with falsy entries should be skipped."""
        props = _make_cluster_properties()
        # Add CustomEndpoints with empty string — should be skipped
        props['CustomEndpoints'] = ['', None]
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            endpoints = internal_get_cluster_valid_endpoints(props, REGION)

        # Only writer + reader, falsy custom endpoints skipped
        assert len(endpoints) == 2
        assert (WRITER_ENDPOINT, CLUSTER_PORT) in endpoints
        assert (READER_ENDPOINT, CLUSTER_PORT) in endpoints
