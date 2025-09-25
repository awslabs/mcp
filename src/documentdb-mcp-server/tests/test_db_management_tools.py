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
"""Tests for DocumentDB MCP Server database management tools."""

import pytest
import uuid
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from awslabs.documentdb_mcp_server.db_management_tools import (
    create_collection,
    drop_collection,
    list_collections,
    list_databases,
    serverConfig,
)


class TestListDatabasesTool:
    """Tests for the listDatabases tool."""

    @pytest.mark.asyncio
    async def test_list_databases_success(self, mock_ctx, patch_client):
        """Test successful listing of databases."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Create some test databases
        mock_client['test_db1']
        mock_client['test_db2']

        # Act
        result = await list_databases(connection_id)

        # Assert
        assert 'databases' in result
        assert 'count' in result
        assert isinstance(result['databases'], list)
        assert 'test_db1' in result['databases']
        assert 'test_db2' in result['databases']
        assert result['count'] >= 2  # At least our two test databases

    @pytest.mark.asyncio
    async def test_list_databases_connection_not_found(self, mock_ctx):
        """Test list_databases with invalid connection ID."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await list_databases(str(uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_list_databases_handles_generic_exception(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test handling of generic exceptions during list_databases."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        def mock_list_database_names(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr(
            'conftest.MockDocumentDBClient.list_database_names', mock_list_database_names
        )

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to list databases: Generic error'):
            await list_databases(connection_id)


class TestCreateCollectionTool:
    """Tests for the createCollection tool."""

    @pytest.mark.asyncio
    async def test_create_collection_read_only_mode(self, mock_ctx, patch_client, monkeypatch):
        """Test create collection in read-only mode."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', True)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Act/Assert
        with pytest.raises(
            ValueError, match='Operation not permitted: Server is configured in read-only mode'
        ):
            await create_collection(connection_id, 'test_db', 'new_collection')

    @pytest.mark.asyncio
    async def test_create_collection_success(self, mock_ctx, patch_client, monkeypatch):
        """Test successful creation of a collection."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Act
        result = await create_collection(connection_id, 'test_db', 'new_collection')

        # Assert
        assert result['success'] is True
        assert 'created successfully' in result['message']

        # Verify collection exists
        collections = mock_client['test_db'].list_collection_names()
        assert 'new_collection' in collections

    @pytest.mark.asyncio
    async def test_create_existing_collection(self, mock_ctx, patch_client, monkeypatch):
        """Test creating a collection that already exists."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Create the collection first
        mock_client['test_db'].create_collection('existing_collection')

        # Act
        result = await create_collection(connection_id, 'test_db', 'existing_collection')

        # Assert
        assert result['success'] is False
        assert 'already exists' in result['message']

    @pytest.mark.asyncio
    async def test_create_collection_connection_not_found(self, mock_ctx, monkeypatch):
        """Test create collection with invalid connection ID."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await create_collection(str(uuid.uuid4()), 'test_db', 'new_collection')

    @pytest.mark.asyncio
    async def test_create_collection_handles_generic_exception(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test handling of generic exceptions during create collection."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        def mock_create_collection(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr('conftest.MockDatabase.create_collection', mock_create_collection)

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to create collection: Generic error'):
            await create_collection(connection_id, 'test_db', 'new_collection')


class TestListCollectionsTool:
    """Tests for the listCollections tool."""

    @pytest.mark.asyncio
    async def test_list_collections_success(self, mock_ctx, patch_client):
        """Test successful listing of collections."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Create some test collections
        mock_client['test_db'].create_collection('collection1')
        mock_client['test_db'].create_collection('collection2')

        # Act
        result = await list_collections(connection_id, 'test_db')

        # Assert
        assert isinstance(result, list)
        assert 'collection1' in result
        assert 'collection2' in result

    @pytest.mark.asyncio
    async def test_list_collections_connection_not_found(self, mock_ctx):
        """Test list_collections with invalid connection ID."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await list_collections(str(uuid.uuid4()), 'test_db')

    @pytest.mark.asyncio
    async def test_list_collections_handles_generic_exception(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test handling of generic exceptions during list_collections."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        def mock_list_collection_names(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr(
            'conftest.MockDatabase.list_collection_names', mock_list_collection_names
        )

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to list collections: Generic error'):
            await list_collections(connection_id, 'test_db')


class TestDropCollectionTool:
    """Tests for the dropCollection tool."""

    @pytest.mark.asyncio
    async def test_drop_collection_read_only_mode(self, mock_ctx, patch_client, monkeypatch):
        """Test drop collection in read-only mode."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', True)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Create a collection first
        mock_client['test_db'].create_collection('test_collection')

        # Act/Assert
        with pytest.raises(
            ValueError, match='Operation not permitted: Server is configured in read-only mode'
        ):
            await drop_collection(connection_id, 'test_db', 'test_collection')

    @pytest.mark.asyncio
    async def test_drop_collection_success(self, mock_ctx, patch_client, monkeypatch):
        """Test successful dropping of a collection."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Create a collection first
        mock_client['test_db'].create_collection('test_collection')

        # Verify collection exists
        collections_before = mock_client['test_db'].list_collection_names()
        assert 'test_collection' in collections_before

        # Act
        result = await drop_collection(connection_id, 'test_db', 'test_collection')

        # Assert
        assert result['success'] is True
        assert 'dropped successfully' in result['message']

        # Verify collection no longer exists
        collections_after = mock_client['test_db'].list_collection_names()
        assert 'test_collection' not in collections_after

    @pytest.mark.asyncio
    async def test_drop_nonexistent_collection(self, mock_ctx, patch_client, monkeypatch):
        """Test dropping a collection that doesn't exist."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Act
        result = await drop_collection(connection_id, 'test_db', 'nonexistent_collection')

        # Assert
        assert result['success'] is False
        assert 'does not exist' in result['message']

    @pytest.mark.asyncio
    async def test_drop_collection_connection_not_found(self, mock_ctx, monkeypatch):
        """Test drop collection with invalid connection ID."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await drop_collection(str(uuid.uuid4()), 'test_db', 'test_collection')

    @pytest.mark.asyncio
    async def test_drop_collection_handles_generic_exception(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test handling of generic exceptions during drop collection."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Create the collection first to ensure it exists
        mock_client['test_db'].create_collection('test_collection')

        # Mock the drop_collection method to raise an exception
        def mock_drop_collection(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr('conftest.MockDatabase.drop_collection', mock_drop_collection)

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to drop collection: Generic error'):
            await drop_collection(connection_id, 'test_db', 'test_collection')
