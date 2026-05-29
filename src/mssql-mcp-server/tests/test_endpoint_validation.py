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

"""Tests for endpoint validation in the mssql MCP server."""

import pytest
from awslabs.mssql_mcp_server.connection.db_connection_map import ConnectionMethod
from awslabs.mssql_mcp_server.server import (
    db_connection_map,
    internal_create_connection,
    internal_get_instance_valid_endpoints,
    validate_endpoint,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


# ─── internal_get_instance_valid_endpoints ─────────────────────────────────────


def test_get_instance_valid_endpoints_returns_host_port(mocker):
    """Returns (host, port) from describe_db_instances response."""
    mock_rds = MagicMock()
    mock_rds.describe_db_instances.return_value = {
        'DBInstances': [
            {
                'Endpoint': {
                    'Address': 'my-instance.abc123.us-east-1.rds.amazonaws.com',
                    'Port': 1433,
                }
            }
        ]
    }
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    result = internal_get_instance_valid_endpoints('my-instance', 'us-east-1')
    assert result == [('my-instance.abc123.us-east-1.rds.amazonaws.com', 1433)]


def test_get_instance_valid_endpoints_no_instances_raises(mocker):
    """Raises ValueError when no instances are returned."""
    mock_rds = MagicMock()
    mock_rds.describe_db_instances.return_value = {'DBInstances': []}
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    with pytest.raises(ValueError, match='not found'):
        internal_get_instance_valid_endpoints('no-such-instance', 'us-east-1')


def test_get_instance_valid_endpoints_no_endpoint_raises(mocker):
    """Raises ValueError when instance has no valid endpoint info."""
    mock_rds = MagicMock()
    mock_rds.describe_db_instances.return_value = {'DBInstances': [{'Endpoint': {}}]}
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    with pytest.raises(ValueError, match='no valid connection endpoints'):
        internal_get_instance_valid_endpoints('my-instance', 'us-east-1')


def test_get_instance_valid_endpoints_client_error_propagates(mocker):
    """ClientError from describe_db_instances is re-raised."""
    mock_rds = MagicMock()
    mock_rds.describe_db_instances.side_effect = ClientError(
        {'Error': {'Code': 'DBInstanceNotFound', 'Message': 'not found'}},
        'DescribeDBInstances',
    )
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    with pytest.raises(ClientError):
        internal_get_instance_valid_endpoints('bad-instance', 'us-east-1')


def test_get_instance_valid_endpoints_invalid_port_uses_default(mocker):
    """Invalid port falls back to DEFAULT_MSSQL_PORT (1433)."""
    mock_rds = MagicMock()
    mock_rds.describe_db_instances.return_value = {
        'DBInstances': [
            {
                'Endpoint': {
                    'Address': 'my-instance.abc123.us-east-1.rds.amazonaws.com',
                    'Port': 'not-a-number',
                }
            }
        ]
    }
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    result = internal_get_instance_valid_endpoints('my-instance', 'us-east-1')
    assert result == [('my-instance.abc123.us-east-1.rds.amazonaws.com', 1433)]


# ─── validate_endpoint ──────────────────────────────────────────────────────────


def test_validate_endpoint_matches_rds(mocker):
    """Matching RDS endpoint returns the AWS-sourced values."""
    import awslabs.mssql_mcp_server.server as srv

    old_allowed = srv.server_config.allowed_endpoints
    srv.server_config.allowed_endpoints = set()

    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_get_instance_valid_endpoints',
        return_value=[('my-instance.abc123.us-east-1.rds.amazonaws.com', 1433)],
    )
    try:
        host, port = validate_endpoint(
            'my-instance.abc123.us-east-1.rds.amazonaws.com', 1433, 'my-instance', 'us-east-1'
        )
        assert host == 'my-instance.abc123.us-east-1.rds.amazonaws.com'
        assert port == 1433
    finally:
        srv.server_config.allowed_endpoints = old_allowed


def test_validate_endpoint_case_insensitive(mocker):
    """Hostname comparison is case-insensitive."""
    import awslabs.mssql_mcp_server.server as srv

    old_allowed = srv.server_config.allowed_endpoints
    srv.server_config.allowed_endpoints = set()

    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_get_instance_valid_endpoints',
        return_value=[('My-Instance.ABC123.us-east-1.rds.amazonaws.com', 1433)],
    )
    try:
        host, port = validate_endpoint(
            'my-instance.abc123.us-east-1.rds.amazonaws.com', 1433, 'my-instance', 'us-east-1'
        )
        assert host == 'My-Instance.ABC123.us-east-1.rds.amazonaws.com'
    finally:
        srv.server_config.allowed_endpoints = old_allowed


def test_validate_endpoint_rejects_invalid(mocker):
    """Non-matching endpoint raises ValueError."""
    import awslabs.mssql_mcp_server.server as srv

    old_allowed = srv.server_config.allowed_endpoints
    srv.server_config.allowed_endpoints = set()

    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_get_instance_valid_endpoints',
        return_value=[('legit-instance.abc123.us-east-1.rds.amazonaws.com', 1433)],
    )
    try:
        with pytest.raises(ValueError, match='does not match'):
            validate_endpoint('attacker.example.com', 1433, 'my-instance', 'us-east-1')
    finally:
        srv.server_config.allowed_endpoints = old_allowed


def test_validate_endpoint_rejects_wrong_port(mocker):
    """Correct host but wrong port raises ValueError."""
    import awslabs.mssql_mcp_server.server as srv

    old_allowed = srv.server_config.allowed_endpoints
    srv.server_config.allowed_endpoints = set()

    mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_get_instance_valid_endpoints',
        return_value=[('my-instance.abc123.us-east-1.rds.amazonaws.com', 1433)],
    )
    try:
        with pytest.raises(ValueError, match='does not match'):
            validate_endpoint(
                'my-instance.abc123.us-east-1.rds.amazonaws.com', 9999, 'my-instance', 'us-east-1'
            )
    finally:
        srv.server_config.allowed_endpoints = old_allowed


def test_validate_endpoint_allows_configured_on_premise(mocker):
    """Endpoints in allowed_endpoints bypass RDS validation."""
    import awslabs.mssql_mcp_server.server as srv

    old_allowed = srv.server_config.allowed_endpoints
    srv.server_config.allowed_endpoints = {'onprem-db.internal.corp'}

    # Should not call RDS at all
    mock_rds_call = mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_get_instance_valid_endpoints',
    )
    try:
        host, port = validate_endpoint('onprem-db.internal.corp', 1433, 'ignored', 'us-east-1')
        assert host == 'onprem-db.internal.corp'
        assert port == 1433
        mock_rds_call.assert_not_called()
    finally:
        srv.server_config.allowed_endpoints = old_allowed


def test_validate_endpoint_allowed_list_case_insensitive(mocker):
    """Allowed endpoint matching is case-insensitive."""
    import awslabs.mssql_mcp_server.server as srv

    old_allowed = srv.server_config.allowed_endpoints
    srv.server_config.allowed_endpoints = {'OnPrem-DB.Internal.Corp'}

    mock_rds_call = mocker.patch(
        'awslabs.mssql_mcp_server.server.internal_get_instance_valid_endpoints',
    )
    try:
        host, port = validate_endpoint('onprem-db.internal.corp', 1433, 'ignored', 'us-east-1')
        assert port == 1433
        mock_rds_call.assert_not_called()
    finally:
        srv.server_config.allowed_endpoints = old_allowed


# ─── internal_create_connection with endpoint validation ────────────────────────


def test_internal_create_connection_validates_endpoint(mocker):
    """internal_create_connection calls validate_endpoint and uses its result."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(db_connection_map, 'get', return_value=None)
    old_readonly = srv.server_config.readonly_query
    srv.server_config.readonly_query = True

    rds_endpoint = 'my-instance.abc123.us-east-1.rds.amazonaws.com'
    mocker.patch(
        'awslabs.mssql_mcp_server.server.validate_endpoint',
        return_value=(rds_endpoint, 1433),
    )

    custom_arn = 'arn:aws:secretsmanager:us-east-1:123456789012:secret:my-db-user'

    try:
        conn, resp = internal_create_connection(
            region='us-east-1',
            connection_method=ConnectionMethod.MSSQL_PASSWORD,
            instance_identifier='my-instance',
            db_endpoint=rds_endpoint,
            port=1433,
            database='testdb',
            secret_arn=custom_arn,
        )
        assert conn.host == rds_endpoint
    finally:
        srv.server_config.readonly_query = old_readonly
        db_connection_map.remove(
            ConnectionMethod.MSSQL_PASSWORD, 'my-instance', rds_endpoint, 'testdb', 1433
        )


def test_internal_create_connection_rejects_invalid_endpoint(mocker):
    """internal_create_connection raises ValueError for invalid endpoints."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(db_connection_map, 'get', return_value=None)
    old_readonly = srv.server_config.readonly_query
    srv.server_config.readonly_query = True

    mocker.patch(
        'awslabs.mssql_mcp_server.server.validate_endpoint',
        side_effect=ValueError("db_endpoint 'evil.com:1433' does not match"),
    )

    try:
        with pytest.raises(ValueError, match='does not match'):
            internal_create_connection(
                region='us-east-1',
                connection_method=ConnectionMethod.MSSQL_PASSWORD,
                instance_identifier='my-instance',
                db_endpoint='evil.com',
                port=1433,
                database='testdb',
                secret_arn='arn:aws:secretsmanager:us-east-1:123:secret:x',  # pragma: allowlist secret
            )
    finally:
        srv.server_config.readonly_query = old_readonly


# ─── secret_arn empty fallthrough ───────────────────────────────────────────────


def test_internal_create_connection_missing_master_secret_raises(mocker):
    """If no secret_arn and instance has no MasterUserSecret, raises ValueError."""
    import awslabs.mssql_mcp_server.server as srv

    mocker.patch.object(db_connection_map, 'get', return_value=None)
    old_readonly = srv.server_config.readonly_query
    old_default = srv.server_config.default_secret_arn
    srv.server_config.readonly_query = True
    srv.server_config.default_secret_arn = None

    rds_endpoint = 'my-instance.abc123.us-east-1.rds.amazonaws.com'
    mocker.patch(
        'awslabs.mssql_mcp_server.server.validate_endpoint',
        return_value=(rds_endpoint, 1433),
    )

    mock_rds = MagicMock()
    mock_rds.describe_db_instances.return_value = {
        'DBInstances': [{}]  # No MasterUserSecret
    }
    mocker.patch('awslabs.mssql_mcp_server.server.boto3.client', return_value=mock_rds)

    try:
        with pytest.raises(ValueError, match='MasterUserSecret'):
            internal_create_connection(
                region='us-east-1',
                connection_method=ConnectionMethod.MSSQL_PASSWORD,
                instance_identifier='my-instance',
                db_endpoint=rds_endpoint,
                port=1433,
                database='testdb',
            )
    finally:
        srv.server_config.readonly_query = old_readonly
        srv.server_config.default_secret_arn = old_default
