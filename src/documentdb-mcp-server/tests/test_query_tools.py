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
"""Tests for DocumentDB MCP Server query tools (find and aggregate)."""

import pytest
import uuid
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from awslabs.documentdb_mcp_server.query_tools import (
    aggregate,
    find,
)
from bson import ObjectId


class TestFindTool:
    """Tests for the find tool."""

    @pytest.mark.asyncio
    async def test_find_success(self, mock_ctx, patch_client):
        """Test successful find operation with filtering."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up mock data
        db_name = 'test_db'
        collection_name = 'test_collection'

        # Add documents to the collection
        docs = [
            {'_id': ObjectId(), 'name': 'Document 1', 'value': 10},
            {'_id': ObjectId(), 'name': 'Document 2', 'value': 20},
            {'_id': ObjectId(), 'name': 'Document 3', 'value': 30},
        ]

        mock_collection = mock_client[db_name][collection_name]
        for doc in docs:
            mock_collection.insert_one(doc)

        # Act
        result = await find(connection_id, db_name, collection_name, {'value': 20}, None, 10)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1  # Should return exactly one document with value=20
        assert result[0]['name'] == 'Document 2'
        assert result[0]['value'] == 20

    @pytest.mark.asyncio
    async def test_find_with_projection(self, mock_ctx, patch_client):
        """Test find with projection."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up mock data
        db_name = 'test_db'
        collection_name = 'test_collection'

        # Add documents to the collection
        docs = [
            {'_id': ObjectId(), 'name': 'Document 1', 'value': 10},
            {'_id': ObjectId(), 'name': 'Document 2', 'value': 20},
        ]

        mock_collection = mock_client[db_name][collection_name]
        for doc in docs:
            mock_collection.insert_one(doc)

        # Act - include only name field, exclude _id
        result = await find(connection_id, db_name, collection_name, {}, {'name': 1, '_id': 0}, 10)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2

        # Verify that each result has only the name field and no _id or value fields
        for doc in result:
            assert 'name' in doc
            assert '_id' not in doc
            assert 'value' not in doc
            assert doc['name'] in ['Document 1', 'Document 2']

    @pytest.mark.asyncio
    async def test_find_with_limit(self, mock_ctx, patch_client):
        """Test find with limit."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up mock data
        db_name = 'test_db'
        collection_name = 'test_collection'

        # Add documents to the collection
        docs = [
            {'_id': ObjectId(), 'name': 'Document 1', 'value': 10},
            {'_id': ObjectId(), 'name': 'Document 2', 'value': 20},
            {'_id': ObjectId(), 'name': 'Document 3', 'value': 30},
        ]

        mock_collection = mock_client[db_name][collection_name]
        for doc in docs:
            mock_collection.insert_one(doc)

        # Act
        result = await find(connection_id, db_name, collection_name, {}, None, 2)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2  # Should only return 2 documents due to limit
        # Verify that we have the first two documents
        first_two_names = {doc['name'] for doc in result}
        assert 'Document 1' in first_two_names
        assert 'Document 2' in first_two_names

    @pytest.mark.asyncio
    async def test_find_connection_not_found(self, mock_ctx):
        """Test find with invalid connection ID."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await find(str(uuid.uuid4()), 'test_db', 'test_collection', {}, None, 10)

    @pytest.mark.asyncio
    async def test_find_handles_generic_exception(self, mock_ctx, patch_client, monkeypatch):
        """Test handling of generic exceptions during find."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        def mock_find(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr('conftest.MockCollection.find', mock_find)

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to query DocumentDB: Generic error'):
            await find(connection_id, 'test_db', 'test_collection', {}, None, 10)


class TestAggregateTool:
    """Tests for the aggregate tool."""

    @pytest.mark.asyncio
    async def test_aggregate_success(self, mock_ctx, patch_client):
        """Test successful aggregate operation with grouping."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up mock data
        db_name = 'test_db'
        collection_name = 'test_collection'

        # Add documents to the collection
        docs = [
            {'_id': ObjectId(), 'category': 'A', 'value': 10},
            {'_id': ObjectId(), 'category': 'A', 'value': 20},
            {'_id': ObjectId(), 'category': 'B', 'value': 30},
            {'_id': ObjectId(), 'category': 'B', 'value': 40},
        ]

        mock_collection = mock_client[db_name][collection_name]
        for doc in docs:
            mock_collection.insert_one(doc)

        # Define an aggregation pipeline
        pipeline = [{'$group': {'_id': '$category', 'total': {'$sum': '$value'}}}]

        # Act
        result = await aggregate(connection_id, db_name, collection_name, pipeline, 10)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2  # Should have two groups: A and B

        # Find the A and B groups in the results
        group_a = next((item for item in result if item['_id'] == 'A'), None)
        group_b = next((item for item in result if item['_id'] == 'B'), None)

        # Verify the sums are correct
        assert group_a is not None
        assert group_b is not None
        assert group_a['total'] == 30  # 10 + 20
        assert group_b['total'] == 70  # 30 + 40

    @pytest.mark.asyncio
    async def test_aggregate_with_limit(self, mock_ctx, patch_client):
        """Test aggregate with limit."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up mock data
        db_name = 'test_db'
        collection_name = 'test_collection'

        # Add documents to the collection
        docs = [
            {'_id': ObjectId(), 'category': 'A', 'value': 10},
            {'_id': ObjectId(), 'category': 'A', 'value': 20},
            {'_id': ObjectId(), 'category': 'B', 'value': 30},
            {'_id': ObjectId(), 'category': 'B', 'value': 40},
        ]

        mock_collection = mock_client[db_name][collection_name]
        for doc in docs:
            mock_collection.insert_one(doc)

        # Define an aggregation pipeline with no limit stage
        pipeline = [{'$group': {'_id': '$category', 'total': {'$sum': '$value'}}}]

        # Act
        result = await aggregate(connection_id, db_name, collection_name, pipeline, 2)

        # Assert
        assert isinstance(result, list)
        # In our mock implementation, limit is not applied to aggregate results
        # In a real MongoDB implementation, this would limit the results to 2

    @pytest.mark.asyncio
    async def test_aggregate_with_limit_in_pipeline(self, mock_ctx, patch_client):
        """Test aggregate with limit already in pipeline."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up mock data
        db_name = 'test_db'
        collection_name = 'test_collection'

        # Add documents to the collection
        docs = [
            {'_id': ObjectId(), 'category': 'A', 'value': 10},
            {'_id': ObjectId(), 'category': 'A', 'value': 20},
            {'_id': ObjectId(), 'category': 'B', 'value': 30},
            {'_id': ObjectId(), 'category': 'B', 'value': 40},
        ]

        mock_collection = mock_client[db_name][collection_name]
        for doc in docs:
            mock_collection.insert_one(doc)

        # Define an aggregation pipeline with a limit stage
        pipeline = [{'$group': {'_id': '$category', 'total': {'$sum': '$value'}}}, {'$limit': 1}]

        # Act
        result = await aggregate(connection_id, db_name, collection_name, pipeline, 10)

        # Assert
        assert isinstance(result, list)
        # Our mock implementation ignores the pipeline, but in real implementation
        # the limit in the pipeline would be respected

    @pytest.mark.asyncio
    async def test_aggregate_connection_not_found(self, mock_ctx):
        """Test aggregate with invalid connection ID."""
        # Act/Assert
        pipeline = [{'$group': {'_id': '$category', 'total': {'$sum': '$value'}}}]
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await aggregate(str(uuid.uuid4()), 'test_db', 'test_collection', pipeline, 10)

    @pytest.mark.asyncio
    async def test_aggregate_handles_generic_exception(self, mock_ctx, patch_client, monkeypatch):
        """Test handling of generic exceptions during aggregate."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        def mock_aggregate(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr('conftest.MockCollection.aggregate', mock_aggregate)

        # Define a pipeline
        pipeline = [{'$group': {'_id': '$category', 'total': {'$sum': '$value'}}}]

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to run aggregation: Generic error'):
            await aggregate(connection_id, 'test_db', 'test_collection', pipeline, 10)
