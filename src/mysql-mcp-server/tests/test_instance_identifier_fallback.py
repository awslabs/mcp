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

"""Tests for resolving RDS MySQL/MariaDB instances by identifier alone (#4589).

A botocore Stubber backs the RDS client so the real lookup code runs.
"""

import boto3
import pytest
from awslabs.mysql_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DatabaseType,
)
from awslabs.mysql_mcp_server.server import internal_connect_to_database
from botocore.stub import Stubber
from unittest.mock import MagicMock, patch


HOST = 'mydb.abc123.us-east-1.rds.amazonaws.com'


@pytest.fixture
def rds():
    """Stubbed RDS client wired into the connection module."""
    client = boto3.client(
        'rds',
        region_name='us-east-1',
        aws_access_key_id='x',  # pragma: allowlist secret
        aws_secret_access_key='x',  # pragma: allowlist secret
    )
    with Stubber(client) as stubber:
        with (
            patch(
                'awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client',
                return_value=client,
            ),
            patch('awslabs.mysql_mcp_server.server.db_connection_map') as cmap,
            patch('awslabs.mysql_mcp_server.server.AsyncmyPoolConnection') as pool,
        ):
            cmap.get.return_value = None
            pool.return_value = MagicMock()
            yield stubber, pool


def _no_cluster(stubber, ident):
    stubber.add_client_error(
        'describe_db_clusters',
        service_error_code='DBClusterNotFoundFault',
        service_message='not found',
        expected_params={'DBClusterIdentifier': ident},
    )


def _instance(stubber, ident, address=HOST, port=3306):
    stubber.add_response(
        'describe_db_instances',
        {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': ident,
                    'MasterUsername': 'admin',
                    'MasterUserSecret': {'SecretArn': 'arn:aws:secretsmanager:x:1:secret:s'},
                    'Endpoint': {'Address': address, 'Port': port},
                }
            ]
        },
        {'DBInstanceIdentifier': ident},
    )


def _connect(db_type, ident='mydb', endpoint=''):
    return internal_connect_to_database(
        region='us-east-1',
        database_type=db_type,
        connection_method=ConnectionMethod.MYSQL_WIRE_PROTOCOL,
        cluster_identifier=ident,
        db_endpoint=endpoint,
        port=3306,
        database='app',
    )


@pytest.mark.parametrize('db_type', [DatabaseType.RDS_MYSQL, DatabaseType.RDS_MARIADB])
def test_identifier_only_resolves_standalone_instance(rds, db_type):
    """An instance identifier with no endpoint resolves via describe_db_instances."""
    stubber, pool = rds
    _no_cluster(stubber, 'mydb')
    _instance(stubber, 'mydb', port=3307)
    _connect(db_type)
    assert pool.call_args.kwargs['host'] == HOST
    assert pool.call_args.kwargs['port'] == 3307
    stubber.assert_no_pending_responses()


def test_matching_endpoint_with_instance_identifier(rds):
    """A supplied endpoint that belongs to the instance is accepted."""
    stubber, pool = rds
    _no_cluster(stubber, 'mydb')
    _instance(stubber, 'mydb')
    _connect(DatabaseType.RDS_MYSQL, endpoint=HOST.upper())
    assert pool.call_args.kwargs['host'] == HOST


def test_foreign_endpoint_with_instance_identifier_rejected(rds):
    """An endpoint that is not the instance's own is refused (fail closed)."""
    stubber, pool = rds
    _no_cluster(stubber, 'mydb')
    _instance(stubber, 'mydb')
    with pytest.raises(ValueError, match='does not match'):
        _connect(DatabaseType.RDS_MYSQL, endpoint='evil.example.com')
    pool.assert_not_called()


def test_other_cluster_errors_do_not_fall_back(rds):
    """Access denied on the cluster lookup propagates; no instance lookup."""
    from botocore.exceptions import ClientError

    stubber, pool = rds
    stubber.add_client_error(
        'describe_db_clusters',
        service_error_code='AccessDenied',
        service_message='no',
        expected_params={'DBClusterIdentifier': 'mydb'},
    )
    with pytest.raises(ClientError):
        _connect(DatabaseType.RDS_MYSQL)
    pool.assert_not_called()


def test_aurora_does_not_fall_back(rds):
    """Aurora keeps cluster-only behavior: a missing cluster is an error."""
    from botocore.exceptions import ClientError

    stubber, pool = rds
    _no_cluster(stubber, 'mydb')
    with pytest.raises(ClientError):
        _connect(DatabaseType.AURORA_MYSQL)
    pool.assert_not_called()
