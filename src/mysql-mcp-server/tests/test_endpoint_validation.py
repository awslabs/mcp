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
    internal_resolve_cluster_endpoint,
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
# Tests for internal_resolve_cluster_endpoint()
# ---------------------------------------------------------------------------


class TestResolveClusterEndpoint:
    """Tests for resolving a caller host to a valid (host, port) endpoint."""

    def test_resolves_writer_and_reader(self):
        """Writer and reader hosts resolve to their AWS (host, port)."""
        props = _make_cluster_properties()
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            assert internal_resolve_cluster_endpoint(props, REGION, WRITER_ENDPOINT) == (
                WRITER_ENDPOINT,
                CLUSTER_PORT,
            )
            assert internal_resolve_cluster_endpoint(props, REGION, READER_ENDPOINT) == (
                READER_ENDPOINT,
                CLUSTER_PORT,
            )

    def test_resolves_custom_endpoint(self):
        """A custom endpoint host resolves."""
        props = _make_cluster_properties(custom_endpoints=[CUSTOM_ENDPOINT])
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            assert internal_resolve_cluster_endpoint(props, REGION, CUSTOM_ENDPOINT) == (
                CUSTOM_ENDPOINT,
                CLUSTER_PORT,
            )

    def test_resolves_member_instance_endpoint(self):
        """A member instance host resolves via describe_db_instances."""
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
            assert internal_resolve_cluster_endpoint(props, REGION, INSTANCE_ENDPOINT) == (
                INSTANCE_ENDPOINT,
                CLUSTER_PORT,
            )
        # A member host only resolves after enumerating instances.
        mock_rds.describe_db_instances.assert_called_once()

    def test_writer_match_skips_member_enumeration(self):
        """Matching a cluster-level endpoint makes zero describe_db_instances calls.

        Guards against an N+1: the common writer/reader case must not enumerate
        member instances.
        """
        props = _make_cluster_properties(
            members=[{'DBInstanceIdentifier': 'test-cluster-instance-1'}]
        )
        mock_rds = MagicMock()
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            assert internal_resolve_cluster_endpoint(props, REGION, WRITER_ENDPOINT) == (
                WRITER_ENDPOINT,
                CLUSTER_PORT,
            )
        mock_rds.describe_db_instances.assert_not_called()

    def test_unknown_host_returns_none(self):
        """A host that matches no endpoint returns None (caller then rejects)."""
        props = _make_cluster_properties()
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            assert internal_resolve_cluster_endpoint(props, REGION, 'attacker.evil.com') is None

    def test_matched_endpoint_malformed_port_raises(self):
        """A malformed AWS port on the matching endpoint fails closed (no 3306 guess)."""
        props = _make_cluster_properties()
        props['Port'] = 'invalid'
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            with pytest.raises(ValueError, match='malformed port'):
                internal_resolve_cluster_endpoint(props, REGION, WRITER_ENDPOINT)

    def test_matched_endpoint_missing_port_raises(self):
        """A missing AWS port on the matching endpoint fails closed."""
        props = _make_cluster_properties()
        props['Port'] = None
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            with pytest.raises(ValueError, match='no port'):
                internal_resolve_cluster_endpoint(props, REGION, WRITER_ENDPOINT)

    def test_no_member_match_returns_none(self):
        """Members are enumerated but none match the requested host → returns None.

        Covers the member-loop fall-through: a member instance is inspected, its
        address does not match, and resolution ends without a match.
        """
        props = _make_cluster_properties(
            writer='', reader='', members=[{'DBInstanceIdentifier': 'instance-1'}]
        )
        mock_rds = MagicMock()
        mock_rds.describe_db_instances.return_value = {
            'DBInstances': [
                {'Endpoint': {'Address': 'instance-1.abc.rds.amazonaws.com', 'Port': 3306}}
            ]
        }
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            assert internal_resolve_cluster_endpoint(props, REGION, 'nomatch.example.com') is None

    def test_member_not_found_skipped(self):
        """A DBInstanceNotFound on one member is skipped; another member still resolves."""
        from botocore.exceptions import ClientError

        props = _make_cluster_properties(
            writer='',
            reader='',
            members=[
                {'DBInstanceIdentifier': 'gone-instance'},
                {'DBInstanceIdentifier': 'live-instance'},
            ],
        )
        mock_rds = MagicMock()
        mock_rds.describe_db_instances.side_effect = [
            ClientError(
                {'Error': {'Code': 'DBInstanceNotFound', 'Message': 'Not found'}},
                'DescribeDBInstances',
            ),
            {'DBInstances': [{'Endpoint': {'Address': INSTANCE_ENDPOINT, 'Port': 3306}}]},
        ]
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            assert internal_resolve_cluster_endpoint(props, REGION, INSTANCE_ENDPOINT) == (
                INSTANCE_ENDPOINT,
                3306,
            )


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

    def test_bogus_endpoint_rejected_iam_auth(self):
        """IAM-auth connections must also reject an attacker-controlled endpoint.

        The IAM path is the higher-value target — a bogus endpoint would
        receive a freshly minted RDS auth token — so validation must fire on
        MYSQL_WIRE_IAM_PROTOCOL, not just MYSQL_WIRE_PROTOCOL.
        """
        mock_rds = self._mock_rds_client()

        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            with pytest.raises(ValueError, match='does not match any endpoint'):
                internal_connect_to_database(
                    region=REGION,
                    database_type=DatabaseType.AURORA_MYSQL,
                    connection_method=ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL,
                    cluster_identifier=CLUSTER_ID,
                    db_endpoint='attacker.evil.com',
                    port=CLUSTER_PORT,
                    database='testdb',
                )

    def test_warm_cache_does_not_bypass_validation(self):
        """A warm cluster connection must not let a bogus endpoint bypass validation.

        Regression test: DBConnectionMap's relaxed scan matches on
        (method, cluster, database) and ignores db_endpoint. If the cache were
        consulted before validation, a second connect with a bogus endpoint
        would reuse the legitimate warm connection and report success.
        Validation must run first for wire-protocol methods.
        """
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
            # A legitimate connect warms the cache for this cluster.
            conn, _ = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier=CLUSTER_ID,
                db_endpoint=WRITER_ENDPOINT,
                port=CLUSTER_PORT,
                database='testdb',
            )
            assert conn is not None

            # A second connect with a bogus endpoint on the same cluster must
            # still be rejected — not short-circuited to the warm connection.
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

    def test_reconnect_same_endpoint_returns_cached_connection(self):
        """A second connect to the same valid endpoint returns the cached connection.

        Exercises the wire-protocol cache lookup that runs AFTER endpoint
        resolution — the legitimate counterpart to the cache-bypass regression.
        """
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
            conn1, _ = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier=CLUSTER_ID,
                db_endpoint=WRITER_ENDPOINT,
                port=CLUSTER_PORT,
                database='testdb',
            )
            conn2, _ = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                cluster_identifier=CLUSTER_ID,
                db_endpoint=WRITER_ENDPOINT,
                port=CLUSTER_PORT,
                database='testdb',
            )
            assert conn2 is conn1

    def test_rds_api_endpoint_not_validated(self):
        """RDS_API ignores db_endpoint, so a non-matching endpoint must not be rejected.

        RDS_API connects via the Data API using cluster_arn and never dials
        db_endpoint. Validating it would reject callers for a value the method
        documents as ignored.
        """
        mock_rds = self._mock_rds_client()

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=mock_rds,
            ),
            patch('awslabs.mysql_mcp_server.server.RDSDataAPIConnection') as mock_conn_cls,
        ):
            mock_conn_cls.return_value = MagicMock()
            conn, _ = internal_connect_to_database(
                region=REGION,
                database_type=DatabaseType.AURORA_MYSQL,
                connection_method=ConnectionMethod.RDS_API,
                cluster_identifier=CLUSTER_ID,
                db_endpoint='not-a-cluster-endpoint.example.com',
                port=CLUSTER_PORT,
                database='testdb',
            )
            assert conn is not None
            mock_conn_cls.assert_called_once()

    def test_wrong_port_normalized_to_aws_value(self):
        """Valid host with a wrong (guessed) port is accepted and normalized.

        Validation matches on host only — the host is the security-relevant
        part. A caller who supplies the correct host but a wrong port should
        not be rejected; instead the port is overwritten with the AWS-sourced
        value for that endpoint.
        """
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
                port=9999,
                database='testdb',
            )
            assert conn is not None
            resp_dict = json.loads(resp)
            # Port normalized to the cluster's AWS-sourced value, not the guess.
            assert resp_dict['port'] == CLUSTER_PORT
            assert resp_dict['db_endpoint'] == WRITER_ENDPOINT

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

    def test_empty_endpoint_and_no_cluster_writer_raises(self):
        """No caller endpoint + a cluster with no writer endpoint fails closed."""
        mock_rds = MagicMock()
        mock_rds.describe_db_clusters.return_value = {
            'DBClusters': [_make_cluster_properties(writer='')]
        }
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            with pytest.raises(ValueError, match='no writer endpoint'):
                internal_connect_to_database(
                    region=REGION,
                    database_type=DatabaseType.AURORA_MYSQL,
                    connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                    cluster_identifier=CLUSTER_ID,
                    db_endpoint='',
                    port=CLUSTER_PORT,
                    database='testdb',
                )

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
# Tests for standalone instance path (server.py host/port overwrite)
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

    def test_instance_lookup_is_case_insensitive(self):
        """internal_get_instance_properties matches the endpoint case-insensitively.

        DNS is case-insensitive, so a caller endpoint in a different case must
        still resolve — consistent with the cluster resolver.
        """
        from awslabs.mysql_mcp_server.connection.cp_api_connection import (
            internal_get_instance_properties,
        )

        aws_address = 'My-Instance.abc.us-east-1.rds.amazonaws.com'
        mock_rds = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'DBInstances': [{'Endpoint': {'Address': aws_address, 'Port': 3306}}]}
        ]
        mock_rds.get_paginator.return_value = mock_paginator

        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            instance = internal_get_instance_properties(aws_address.upper(), REGION)

        assert instance['Endpoint']['Address'] == aws_address

    def test_standalone_instance_invalid_port_raises(self):
        """Standalone instance with a malformed AWS port fails closed (no 3306 guess)."""
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

        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            with pytest.raises(ValueError):
                internal_connect_to_database(
                    region=REGION,
                    database_type=DatabaseType.RDS_MYSQL,
                    connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                    cluster_identifier='',
                    db_endpoint='real-instance.abc123.us-east-1.rds.amazonaws.com',
                    port=3306,
                    database='testdb',
                )


# ---------------------------------------------------------------------------
# Tests for cluster endpoint resolution edge cases (cp_api_connection.py)
# ---------------------------------------------------------------------------


class TestClusterEndpointEdgeCases:
    """Edge cases for resolving a cluster's valid endpoints."""

    def test_member_instance_malformed_port_raises(self):
        """Matching a member whose AWS port is malformed fails closed (no 3306 guess)."""
        # Use empty writer/reader so resolution must reach the member.
        props = _make_cluster_properties(
            writer='', reader='', members=[{'DBInstanceIdentifier': 'instance-bad-port'}]
        )
        bad_host = 'instance-bad-port.abc.rds.amazonaws.com'
        mock_rds = MagicMock()
        mock_rds.describe_db_instances.return_value = {
            'DBInstances': [{'Endpoint': {'Address': bad_host, 'Port': 'invalid'}}]
        }
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            with pytest.raises(ValueError, match='malformed port'):
                internal_resolve_cluster_endpoint(props, REGION, bad_host)

    def test_access_denied_on_instance_lookup_reraises(self):
        """AccessDenied while enumerating members must re-raise, not silently reject.

        A permissions/throttling failure means we could not enumerate the
        cluster's real endpoints. Swallowing it would surface later as a
        misleading 'endpoint does not match' rejection, so the original error
        must propagate instead. (Uses a non-writer/reader host so resolution is
        forced to enumerate members.)
        """
        from botocore.exceptions import ClientError

        props = _make_cluster_properties(members=[{'DBInstanceIdentifier': 'instance-1'}])
        mock_rds = MagicMock()
        mock_rds.describe_db_instances.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'not authorized to perform rds:DescribeDBInstances',
                }
            },
            'DescribeDBInstances',
        )
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
            return_value=mock_rds,
        ):
            with pytest.raises(ClientError):
                internal_resolve_cluster_endpoint(
                    props, REGION, 'some-member.abc.rds.amazonaws.com'
                )


class TestStandaloneInstanceEdgeCases:
    """Tests for edge cases in the standalone instance path."""

    def setup_method(self):
        """Reset server global state before each test."""
        server_module.db_connection_map = DBConnectionMap()
        server_module.readonly_query = True
        server_module.ca_bundle_path = None

    def test_standalone_instance_missing_address_raises(self):
        """When AWS returns an empty Address, fail closed — never keep the caller host."""
        mock_instance_props = {
            'Endpoint': {'Address': '', 'Port': 3306},
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': SECRET_ARN},
        }

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=MagicMock(),
            ),
            patch(
                'awslabs.mysql_mcp_server.server.internal_get_instance_properties',
                return_value=mock_instance_props,
            ),
        ):
            with pytest.raises(ValueError, match='no endpoint address'):
                internal_connect_to_database(
                    region=REGION,
                    database_type=DatabaseType.RDS_MYSQL,
                    connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                    cluster_identifier='',
                    db_endpoint='my-instance.abc.us-east-1.rds.amazonaws.com',
                    port=CLUSTER_PORT,
                    database='testdb',
                )

    def test_standalone_instance_zero_port_raises(self):
        """A zero/absent AWS port on the standalone path fails closed (no 3306 guess)."""
        mock_instance_props = {
            'Endpoint': {'Address': 'real-host.rds.amazonaws.com', 'Port': 0},
            'MasterUsername': 'admin',
            'MasterUserSecret': {'SecretArn': SECRET_ARN},
        }

        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=MagicMock(),
            ),
            patch(
                'awslabs.mysql_mcp_server.server.internal_get_instance_properties',
                return_value=mock_instance_props,
            ),
        ):
            with pytest.raises(ValueError, match='non-positive port'):
                internal_connect_to_database(
                    region=REGION,
                    database_type=DatabaseType.RDS_MYSQL,
                    connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
                    cluster_identifier='',
                    db_endpoint='my-instance.rds.amazonaws.com',
                    port=3306,
                    database='testdb',
                )

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

    def test_falsy_custom_endpoints_skipped(self):
        """Falsy CustomEndpoints entries must not break resolution."""
        props = _make_cluster_properties()
        props['CustomEndpoints'] = ['', None]
        with patch(
            'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client'
        ):
            # Writer still resolves despite falsy custom entries...
            assert internal_resolve_cluster_endpoint(props, REGION, WRITER_ENDPOINT) == (
                WRITER_ENDPOINT,
                CLUSTER_PORT,
            )
            # ...and an empty host matches nothing.
            assert internal_resolve_cluster_endpoint(props, REGION, '') is None
