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

"""Tests for endpoint operations."""

import json
import pytest
from awslabs.dms_mcp_server.context import Context
from awslabs.dms_mcp_server.models import (
    ConnectionListResponse,
    ConnectionTestResponse,
    CreateEndpointResponse,
    EndpointListResponse,
)
from awslabs.dms_mcp_server.tools.endpoints import (
    create_endpoint,
    describe_connections,
    describe_endpoints,
)
from awslabs.dms_mcp_server.tools.endpoints import (
    test_connection as connection_test_func,
)
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


@pytest.fixture
def mock_dms_client():
    """Mock DMS client for testing."""
    with patch('awslabs.dms_mcp_server.tools.endpoints.get_dms_client') as mock_get_client:
        mock_dms = Mock()
        mock_get_client.return_value = mock_dms

        # Mock describe_endpoints response
        mock_dms.describe_endpoints.return_value = {
            'Endpoints': [
                {
                    'EndpointIdentifier': 'test-endpoint',
                    'EndpointType': 'source',
                    'EngineName': 'mysql',
                    'Status': 'active',
                    'EndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:test-endpoint',
                    'ServerName': 'test.example.com',
                    'Port': 3306,
                    'DatabaseName': 'testdb',
                    'Username': 'testuser',
                    'SslMode': 'none',
                }
            ],
            'Marker': None,
        }

        # Mock test_connection response
        mock_dms.test_connection.return_value = {
            'Connection': {
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                'EndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:test-endpoint',
                'Status': 'successful',
                'LastFailureMessage': None,
            }
        }

        # Mock describe_connections response
        mock_dms.describe_connections.return_value = {
            'Connections': [
                {
                    'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test-instance',
                    'EndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:test-endpoint',
                    'Status': 'successful',
                    'LastFailureMessage': None,
                    'EndpointIdentifier': 'test-endpoint',
                    'ReplicationInstanceIdentifier': 'test-instance',
                }
            ],
            'Marker': None,
        }

        # Mock create_endpoint response
        mock_dms.create_endpoint.return_value = {
            'Endpoint': {
                'EndpointIdentifier': 'new-endpoint',
                'EndpointType': 'source',
                'EngineName': 'mysql',
                'Status': 'creating',
                'EndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:new-endpoint',
                'ServerName': 'new.example.com',
                'Port': 3306,
                'DatabaseName': 'newdb',
                'Username': 'newuser',
                'SslMode': 'none',
            }
        }

        yield mock_dms


@pytest.mark.asyncio
class TestDescribeEndpoints:
    """Tests for describe_endpoints function."""

    async def test_describe_all_endpoints(self, mock_dms_client):
        """Test describing all endpoints."""
        result = await describe_endpoints()

        assert isinstance(result, EndpointListResponse)
        assert len(result.endpoints) == 1
        assert result.endpoints[0].endpoint_identifier == 'test-endpoint'
        assert result.endpoints[0].endpoint_type == 'source'
        assert result.endpoints[0].engine_name == 'mysql'

        mock_dms_client.describe_endpoints.assert_called_once()

    async def test_describe_endpoints_with_filters(self, mock_dms_client):
        """Test describing endpoints with filters."""
        await describe_endpoints(
            endpoint_identifier='test-endpoint', endpoint_type='source', engine_name='mysql'
        )

        call_args = mock_dms_client.describe_endpoints.call_args[1]
        assert 'Filters' in call_args
        assert len(call_args['Filters']) == 3

    async def test_describe_endpoints_with_pagination(self, mock_dms_client):
        """Test describing endpoints with pagination."""
        await describe_endpoints(max_records=50, marker='test-marker')

        call_args = mock_dms_client.describe_endpoints.call_args[1]
        assert call_args['MaxRecords'] == 50
        assert call_args['Marker'] == 'test-marker'


@pytest.mark.asyncio
class TestTestConnection:
    """Tests for test_connection function."""

    async def test_connection_success(self, mock_dms_client):
        """Test successful connection test."""
        result = await connection_test_func(
            replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test-instance',
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test-endpoint',
        )

        assert isinstance(result, ConnectionTestResponse)
        assert (
            result.replication_instance_arn
            == 'arn:aws:dms:us-east-1:123456789012:rep:test-instance'
        )
        assert result.endpoint_arn == 'arn:aws:dms:us-east-1:123456789012:endpoint:test-endpoint'
        assert result.status == 'successful'
        assert result.last_failure_message is None


@pytest.mark.asyncio
class TestCreateEndpoint:
    """Tests for create_endpoint function."""

    async def test_create_endpoint_requires_write_access(self, mock_dms_client):
        """Test that create_endpoint requires write access."""
        Context.initialize(readonly=True)

        with pytest.raises(ValueError, match='Your DMS MCP server does not allow writes'):
            await create_endpoint(
                endpoint_identifier='test-endpoint', endpoint_type='source', engine_name='mysql'
            )

    async def test_create_basic_endpoint(self, mock_dms_client):
        """Test creating a basic endpoint."""
        Context.initialize(readonly=False)

        result = await create_endpoint(
            endpoint_identifier='new-endpoint',
            endpoint_type='source',
            engine_name='mysql',
            server_name='new.example.com',
            port=3306,
            database_name='newdb',
            username='newuser',
            password='testpassword',  # pragma: allowlist secret
            ssl_mode='none',
            extra_connection_attributes=None,
            kms_key_id=None,
            tags=None,
        )

        assert isinstance(result, CreateEndpointResponse)
        assert result.endpoint.endpoint_identifier == 'new-endpoint'
        assert result.endpoint.endpoint_type == 'source'
        assert result.endpoint.engine_name == 'mysql'

        call_args = mock_dms_client.create_endpoint.call_args[1]
        assert call_args['EndpointIdentifier'] == 'new-endpoint'
        assert call_args['EndpointType'] == 'source'
        assert call_args['EngineName'] == 'mysql'

    async def test_create_endpoint_with_tags(self, mock_dms_client):
        """Test creating endpoint with tags."""
        Context.initialize(readonly=False)

        tags_json = json.dumps([{'Key': 'Environment', 'Value': 'test'}])

        await create_endpoint(
            endpoint_identifier='tagged-endpoint',
            endpoint_type='target',
            engine_name='postgres',
            tags=tags_json,
        )

        call_args = mock_dms_client.create_endpoint.call_args[1]
        assert 'Tags' in call_args
        assert call_args['Tags'] == [{'Key': 'Environment', 'Value': 'test'}]

    async def test_create_endpoint_invalid_tags(self, mock_dms_client):
        """Test creating endpoint with invalid tags JSON."""
        Context.initialize(readonly=False)

        with pytest.raises(ValueError, match='tags must be valid JSON format'):
            await create_endpoint(
                endpoint_identifier='bad-tags-endpoint',
                endpoint_type='source',
                engine_name='mysql',
                tags='invalid-json',
            )


@pytest.mark.asyncio
class TestDescribeConnections:
    """Tests for describe_connections function."""

    async def test_describe_all_connections(self, mock_dms_client):
        """Test describing all connections."""
        result = await describe_connections(filters=None, max_records=20, marker=None)

        assert isinstance(result, ConnectionListResponse)
        assert len(result.connections) == 1
        assert (
            result.connections[0].replication_instance_arn
            == 'arn:aws:dms:us-east-1:123456789012:rep:test-instance'
        )
        assert (
            result.connections[0].endpoint_arn
            == 'arn:aws:dms:us-east-1:123456789012:endpoint:test-endpoint'
        )
        assert result.connections[0].status == 'successful'
        assert result.connections[0].endpoint_identifier == 'test-endpoint'
        assert result.connections[0].replication_instance_identifier == 'test-instance'

    async def test_describe_endpoints_aws_error(self, mock_dms_client):
        """Test describe_endpoints with AWS ClientError."""
        mock_dms_client.describe_endpoints.side_effect = ClientError(
            {'Error': {'Code': 'InvalidParameterValue', 'Message': 'Invalid parameter'}},
            'DescribeEndpoints',
        )

        with pytest.raises(ValueError, match='Failed to describe endpoints'):
            await describe_endpoints(
                endpoint_identifier=None,
                endpoint_type=None,
                engine_name=None,
                max_records=20,
                marker=None,
            )

    async def test_describe_connections_invalid_filter_dict(self, mock_dms_client):
        """Test describe_connections with invalid filter format (not a dict)."""
        with pytest.raises(ValueError, match='Each filter must be a dictionary'):
            await describe_connections(
                filters=['invalid_filter_format'], max_records=20, marker=None
            )

    async def test_describe_connections_missing_keys(self, mock_dms_client):
        """Test describe_connections with missing required keys."""
        with pytest.raises(ValueError, match="Each filter must have 'Name' and 'Values' keys"):
            await describe_connections(
                filters=[{'Name': 'endpoint-arn'}],  # Missing 'Values'
                max_records=20,
                marker=None,
            )

    async def test_describe_connections_invalid_filter_name(self, mock_dms_client):
        """Test describe_connections with invalid filter name."""
        with pytest.raises(ValueError, match='Invalid filter name'):
            await describe_connections(
                filters=[{'Name': 'invalid-filter', 'Values': ['test']}],
                max_records=20,
                marker=None,
            )

    async def test_describe_connections_empty_values(self, mock_dms_client):
        """Test describe_connections with empty values list."""
        with pytest.raises(ValueError, match="Filter 'Values' cannot be empty"):
            await describe_connections(
                filters=[{'Name': 'endpoint-arn', 'Values': []}], max_records=20, marker=None
            )

    async def test_create_endpoint_invalid_json_tags(self, mock_dms_client):
        """Test create_endpoint with invalid JSON tags."""
        Context.initialize(readonly=False)

        with pytest.raises(ValueError, match='tags must be valid JSON format'):
            await create_endpoint(
                endpoint_identifier='test-endpoint',
                endpoint_type='source',
                engine_name='mysql',
                server_name='test.example.com',
                port=3306,
                database_name='testdb',
                username='testuser',
                password='testpass',  # pragma: allowlist secret
                ssl_mode='none',
                extra_connection_attributes=None,
                kms_key_id=None,
                tags='invalid_json',  # Invalid JSON
            )

    async def test_create_endpoint_with_all_optional_params(self, mock_dms_client):
        """Test create_endpoint with all optional parameters provided."""
        Context.initialize(readonly=False)

        mock_dms_client.create_endpoint.return_value = {
            'Endpoint': {
                'EndpointIdentifier': 'test-endpoint',
                'EndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:test-endpoint',
                'EndpointType': 'source',
                'EngineName': 'mysql',
                'Status': 'active',
            }
        }

        result = await create_endpoint(
            endpoint_identifier='test-endpoint',
            endpoint_type='source',
            engine_name='mysql',
            server_name='test.example.com',
            port=3306,
            database_name='testdb',
            username='testuser',
            password='testpass',  # pragma: allowlist secret
            ssl_mode='require',
            extra_connection_attributes='connectTimeout=600',
            kms_key_id='arn:aws:kms:us-east-1:123456789012:key/test-key',
            tags='[{"Key": "Environment", "Value": "test"}]',
        )

        assert isinstance(result, CreateEndpointResponse)

        # Verify all optional parameters were passed
        call_args = mock_dms_client.create_endpoint.call_args[1]
        assert call_args['ExtraConnectionAttributes'] == 'connectTimeout=600'
        assert call_args['KmsKeyId'] == 'arn:aws:kms:us-east-1:123456789012:key/test-key'
        assert 'Tags' in call_args

    async def test_describe_connections_with_filters(self, mock_dms_client):
        """Test describing connections with filters."""
        filters = [
            {
                'Name': 'endpoint-arn',
                'Values': ['arn:aws:dms:us-east-1:123456789012:endpoint:test-endpoint'],
            }
        ]

        result = await describe_connections(filters=filters)

        assert isinstance(result, ConnectionListResponse)
        call_args = mock_dms_client.describe_connections.call_args[1]
        assert 'Filters' in call_args
        assert call_args['Filters'] == filters

    async def test_describe_connections_invalid_filter(self, mock_dms_client):
        """Test describing connections with invalid filter."""
        filters = [{'Name': 'invalid-filter', 'Values': ['some-value']}]

        with pytest.raises(ValueError, match="Invalid filter name 'invalid-filter'"):
            await describe_connections(filters=filters)

    async def test_describe_connections_empty_filter_values(self, mock_dms_client):
        """Test describing connections with empty filter values."""
        filters = [{'Name': 'endpoint-arn', 'Values': []}]

        with pytest.raises(ValueError, match="Filter 'Values' cannot be empty"):
            await describe_connections(filters=filters)
