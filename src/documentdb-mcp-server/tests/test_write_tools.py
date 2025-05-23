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
"""Tests for DocumentDB MCP Server write tools (insert, update, delete)."""

import pytest
import uuid
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from awslabs.documentdb_mcp_server.write_tools import delete, insert, serverConfig, update


class TestInsertTool:
    """Tests for the insert tool."""

    @pytest.mark.asyncio
    async def test_insert_single_document_read_only_mode(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test insert single document in read-only mode."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', True)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up document
        document = {'name': 'Test Document', 'value': 42}

        # Act/Assert
        with pytest.raises(
            ValueError, match='Operation not permitted: Server is configured in read-only mode'
        ):
            await insert(connection_id, 'test_db', 'test_collection', document)

    @pytest.mark.asyncio
    async def test_insert_multiple_documents_read_only_mode(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test insert multiple documents in read-only mode."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', True)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up documents
        documents = [{'name': 'Document 1', 'value': 10}, {'name': 'Document 2', 'value': 20}]

        # Act/Assert
        with pytest.raises(
            ValueError, match='Operation not permitted: Server is configured in read-only mode'
        ):
            await insert(connection_id, 'test_db', 'test_collection', documents)

    @pytest.mark.asyncio
    async def test_insert_single_document_success(self, mock_ctx, patch_client, monkeypatch):
        """Test successful insertion of a single document."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up document
        document = {'name': 'Test Document', 'value': 42}

        # Act
        result = await insert(connection_id, 'test_db', 'test_collection', document)

        # Assert
        assert result['success'] is True
        assert result['inserted_count'] == 1
        assert len(result['inserted_ids']) == 1
        assert isinstance(result['inserted_ids'][0], str)

    @pytest.mark.asyncio
    async def test_insert_multiple_documents_success(self, mock_ctx, patch_client, monkeypatch):
        """Test successful insertion of multiple documents."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up documents
        documents = [{'name': 'Document 1', 'value': 10}, {'name': 'Document 2', 'value': 20}]

        # Act
        result = await insert(connection_id, 'test_db', 'test_collection', documents)

        # Assert
        assert result['success'] is True
        assert result['inserted_count'] == 2
        assert len(result['inserted_ids']) == 2
        assert isinstance(result['inserted_ids'][0], str)
        assert isinstance(result['inserted_ids'][1], str)

    @pytest.mark.asyncio
    async def test_insert_connection_not_found(self, mock_ctx, monkeypatch):
        """Test insert with invalid connection ID."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        # Set up document
        document = {'name': 'Test Document', 'value': 42}

        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await insert(str(uuid.uuid4()), 'test_db', 'test_collection', document)

    @pytest.mark.asyncio
    async def test_insert_handles_generic_exception(self, mock_ctx, patch_client, monkeypatch):
        """Test handling of generic exceptions during insert."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Mock the insert_one method to raise an exception
        def mock_insert_one(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr(
            mock_client['test_db']['test_collection'], 'insert_one', mock_insert_one
        )

        # Set up document
        document = {'name': 'Test Document', 'value': 42}

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to insert documents: Generic error'):
            await insert(connection_id, 'test_db', 'test_collection', document)


class TestUpdateTool:
    """Tests for the update tool."""

    @pytest.mark.asyncio
    async def test_update_single_document_read_only_mode(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test update single document in read-only mode."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', True)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up filter and update
        filter_doc = {'name': 'Old Name'}
        update_doc = {'$set': {'name': 'New Name'}}

        # Act/Assert
        with pytest.raises(
            ValueError, match='Operation not permitted: Server is configured in read-only mode'
        ):
            await update(connection_id, 'test_db', 'test_collection', filter_doc, update_doc)

    @pytest.mark.asyncio
    async def test_update_single_document_success(self, mock_ctx, patch_client, monkeypatch):
        """Test successful update of a single document."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up test document
        document = {'name': 'Old Name', 'value': 42}
        mock_client['test_db']['test_collection'].insert_one(document)

        # Set up filter and update
        filter_doc = {'name': 'Old Name'}
        update_doc = {'$set': {'name': 'New Name'}}

        # Act
        result = await update(connection_id, 'test_db', 'test_collection', filter_doc, update_doc)

        # Assert
        assert result['success'] is True
        assert result['matched_count'] == 1
        assert result['modified_count'] == 1
        assert result['upserted_id'] is None

    @pytest.mark.asyncio
    async def test_update_multiple_documents_success(self, mock_ctx, patch_client, monkeypatch):
        """Test successful update of multiple documents."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up test documents
        documents = [
            {'category': 'A', 'status': 'pending'},
            {'category': 'A', 'status': 'pending'},
        ]
        for doc in documents:
            mock_client['test_db']['test_collection'].insert_one(doc)

        # Set up filter and update
        filter_doc = {'category': 'A'}
        update_doc = {'$set': {'status': 'completed'}}

        # Act
        result = await update(
            connection_id, 'test_db', 'test_collection', filter_doc, update_doc, False, True
        )

        # Assert
        assert result['success'] is True
        assert result['matched_count'] > 0
        assert result['modified_count'] > 0
        assert result['upserted_id'] is None

    @pytest.mark.asyncio
    async def test_update_with_upsert(self, mock_ctx, patch_client, monkeypatch):
        """Test update with upsert option."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up filter and update for a document that doesn't exist
        filter_doc = {'name': 'Non-existent'}
        update_doc = {'$set': {'name': 'New Document', 'value': 100}}

        # Act
        result = await update(
            connection_id, 'test_db', 'test_collection', filter_doc, update_doc, True, False
        )

        # Assert
        assert result['success'] is True
        assert result['matched_count'] == 0
        assert result['upserted_id'] is not None

    @pytest.mark.asyncio
    async def test_update_ensure_operators(self, mock_ctx, patch_client, monkeypatch):
        """Test update with implicit $set."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up test document
        document = {'name': 'Old Name', 'value': 42}
        mock_client['test_db']['test_collection'].insert_one(document)

        # Set up filter and update without $set operator
        filter_doc = {'name': 'Old Name'}
        update_doc = {'name': 'New Name'}  # No $set operator

        # Act
        result = await update(connection_id, 'test_db', 'test_collection', filter_doc, update_doc)

        # Assert
        assert result['success'] is True
        assert result['matched_count'] == 1
        assert result['modified_count'] == 1

    @pytest.mark.asyncio
    async def test_update_connection_not_found(self, mock_ctx, monkeypatch):
        """Test update with invalid connection ID."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        # Set up filter and update
        filter_doc = {'name': 'Test'}
        update_doc = {'$set': {'name': 'Updated'}}

        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await update(str(uuid.uuid4()), 'test_db', 'test_collection', filter_doc, update_doc)

    @pytest.mark.asyncio
    async def test_update_handles_generic_exception(self, mock_ctx, patch_client, monkeypatch):
        """Test handling of generic exceptions during update."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Mock the update_one method to raise an exception
        def mock_update_one(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr(
            mock_client['test_db']['test_collection'], 'update_one', mock_update_one
        )

        # Set up filter and update
        filter_doc = {'name': 'Test'}
        update_doc = {'$set': {'name': 'Updated'}}

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to update documents: Generic error'):
            await update(connection_id, 'test_db', 'test_collection', filter_doc, update_doc)


class TestDeleteTool:
    """Tests for the delete tool."""

    @pytest.mark.asyncio
    async def test_delete_single_document_read_only_mode(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test delete single document in read-only mode."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', True)

        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up filter
        filter_doc = {'name': 'Test Document'}

        # Act/Assert
        with pytest.raises(
            ValueError, match='Operation not permitted: Server is configured in read-only mode'
        ):
            await delete(connection_id, 'test_db', 'test_collection', filter_doc)

    @pytest.mark.asyncio
    async def test_delete_single_document_success(self, mock_ctx, patch_client, monkeypatch):
        """Test successful deletion of a single document."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up test document
        document = {'name': 'Test Document', 'value': 42}
        mock_client['test_db']['test_collection'].insert_one(document)

        # Set up filter
        filter_doc = {'name': 'Test Document'}

        # Act
        result = await delete(connection_id, 'test_db', 'test_collection', filter_doc)

        # Assert
        assert result['success'] is True
        assert result['deleted_count'] == 1

    @pytest.mark.asyncio
    async def test_delete_multiple_documents_success(self, mock_ctx, patch_client, monkeypatch):
        """Test successful deletion of multiple documents."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up test documents
        documents = [
            {'category': 'A', 'status': 'expired'},
            {'category': 'A', 'status': 'expired'},
        ]
        for doc in documents:
            mock_client['test_db']['test_collection'].insert_one(doc)

        # Set up filter
        filter_doc = {'category': 'A', 'status': 'expired'}

        # Act
        result = await delete(connection_id, 'test_db', 'test_collection', filter_doc, True)

        # Assert
        assert result['success'] is True
        assert result['deleted_count'] > 0

    @pytest.mark.asyncio
    async def test_delete_connection_not_found(self, mock_ctx, monkeypatch):
        """Test delete with invalid connection ID."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        # Set up filter
        filter_doc = {'name': 'Test Document'}

        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await delete(str(uuid.uuid4()), 'test_db', 'test_collection', filter_doc)

    @pytest.mark.asyncio
    async def test_delete_handles_generic_exception(self, mock_ctx, patch_client, monkeypatch):
        """Test handling of generic exceptions during delete."""
        # Arrange
        monkeypatch.setattr(serverConfig, 'read_only_mode', False)

        mock_client = patch_client()
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Mock the delete_one method to raise an exception
        def mock_delete_one(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr(
            mock_client['test_db']['test_collection'], 'delete_one', mock_delete_one
        )

        # Set up filter
        filter_doc = {'name': 'Test Document'}

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to delete documents: Generic error'):
            await delete(connection_id, 'test_db', 'test_collection', filter_doc)
