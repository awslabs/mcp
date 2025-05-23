# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for DocumentDB MCP Server connection tools."""

import pytest
import uuid
from awslabs.documentdb_mcp_server.connection_tools import (
    DocumentDBConnection,
    connect,
    disconnect,
)
from datetime import datetime, timedelta
from pymongo.errors import ConnectionFailure


class TestDocumentDBConnection:
    """Tests for the DocumentDBConnection class."""

    def test_create_connection(self, patch_client):
        """Test creating a new connection."""
        # Arrange
        mock_client = patch_client()  # noqa: F841

        # Act
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )

        # Assert
        assert (
            connection_info.connection_string == 'mongodb://example.com:27017/?retryWrites=false'
        )
        assert connection_info.connection_id in DocumentDBConnection._connections
        assert isinstance(connection_info.connection_id, str)
        assert isinstance(connection_info.last_used, datetime)

    def test_create_connection_failure(self, patch_client):
        """Test connection failure."""
        # Arrange
        patch_client(raise_on_connect=ConnectionFailure('Connection refused'))

        # Act/Assert
        with pytest.raises(ConnectionFailure):
            DocumentDBConnection.create_connection(
                'mongodb://example.com:27017/?retryWrites=false'
            )

    def test_get_connection(self, patch_client):
        """Test getting an existing connection."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        orig_last_used = connection_info.last_used

        # Act
        client = DocumentDBConnection.get_connection(connection_info.connection_id)

        # Assert
        assert client is mock_client
        assert connection_info.last_used > orig_last_used

    def test_get_connection_not_found(self):
        """Test getting a non-existent connection."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            DocumentDBConnection.get_connection(str(uuid.uuid4()))

    def test_close_connection(self, patch_client):
        """Test closing a connection."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Act
        DocumentDBConnection.close_connection(connection_id)

        # Assert
        assert connection_id not in DocumentDBConnection._connections

    def test_close_connection_not_found(self):
        """Test closing a non-existent connection."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            DocumentDBConnection.close_connection(str(uuid.uuid4()))

    def test_close_idle_connections(self, patch_client):
        """Test closing idle connections."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info1 = DocumentDBConnection.create_connection(
            'mongodb://example1.com:27017/?retryWrites=false'
        )
        connection_info2 = DocumentDBConnection.create_connection(
            'mongodb://example2.com:27017/?retryWrites=false'
        )

        # Make connection1 idle by setting its last_used time in the past
        connection_info1.last_used = datetime.now() - timedelta(minutes=31)

        # Act
        DocumentDBConnection.close_idle_connections()

        # Assert
        assert connection_info1.connection_id not in DocumentDBConnection._connections
        assert connection_info2.connection_id in DocumentDBConnection._connections

    def test_close_all_connections(self, patch_client):
        """Test closing all connections."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info1 = DocumentDBConnection.create_connection(  # noqa: F841
            'mongodb://example1.com:27017/?retryWrites=false'
        )
        connection_info2 = DocumentDBConnection.create_connection(  # noqa: F841
            'mongodb://example2.com:27017/?retryWrites=false'
        )

        # Act
        DocumentDBConnection.close_all_connections()

        # Assert
        assert len(DocumentDBConnection._connections) == 0


class TestConnectTool:
    """Tests for the connect tool."""

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_ctx, patch_client):
        """Test successful connection."""
        # Arrange
        mock_client = patch_client()  # noqa: F841

        # Add some mock databases
        mock_client['test_db1']
        mock_client['test_db2']

        # Act
        result = await connect('mongodb://example.com:27017/?retryWrites=false')

        # Assert
        assert 'connection_id' in result
        assert 'message' in result
        assert 'databases' in result
        assert isinstance(result['connection_id'], str)
        assert result['message'] == 'Successfully connected to DocumentDB'
        assert 'test_db1' in result['databases']
        assert 'test_db2' in result['databases']

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_ctx, patch_client):
        """Test connection failure."""
        # Arrange
        patch_client(raise_on_connect=ConnectionFailure('Connection refused'))

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to connect to DocumentDB'):
            await connect('mongodb://example.com:27017/?retryWrites=false')

    @pytest.mark.asyncio
    async def test_connect_handles_generic_exception(self, mock_ctx, monkeypatch):
        """Test handling of generic exceptions during connection."""

        # Arrange
        def mock_create_connection(*args):
            raise Exception('Generic error')

        monkeypatch.setattr(
            'awslabs.documentdb_mcp_server.connection_tools.DocumentDBConnection.create_connection',
            mock_create_connection,
        )

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to connect to DocumentDB: Generic error'):
            await connect('mongodb://example.com:27017/?retryWrites=false')


class TestDisconnectTool:
    """Tests for the disconnect tool."""

    @pytest.mark.asyncio
    async def test_disconnect_success(self, mock_ctx, patch_client):
        """Test successful disconnection."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Act
        result = await disconnect(connection_id)

        # Assert
        assert result['success'] is True
        assert f'Successfully closed connection {connection_id}' in result['message']
        assert connection_id not in DocumentDBConnection._connections

    @pytest.mark.asyncio
    async def test_disconnect_not_found(self, mock_ctx):
        """Test disconnection with invalid connection ID."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await disconnect(str(uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_disconnect_handles_generic_exception(self, mock_ctx, monkeypatch):
        """Test handling of generic exceptions during disconnection."""

        # Arrange
        def mock_close_connection(*args):
            raise Exception('Generic error')

        monkeypatch.setattr(
            'awslabs.documentdb_mcp_server.connection_tools.DocumentDBConnection.close_connection',
            mock_close_connection,
        )

        connection_id = str(uuid.uuid4())

        # Act/Assert
        with pytest.raises(
            ValueError, match='Failed to disconnect from DocumentDB: Generic error'
        ):
            await disconnect(connection_id)
