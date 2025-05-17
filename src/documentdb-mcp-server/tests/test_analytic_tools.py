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
"""Tests for DocumentDB MCP Server analytic tools (statistics and schema analysis)."""

import pytest
import uuid
from awslabs.documentdb_mcp_server.analytic_tools import (
    analyze_schema,
    count_documents,
    explain_operation,
    get_collection_stats,
    get_database_stats,
    get_field_type,
)
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from bson import ObjectId


class TestCountDocumentsTool:
    """Tests for the countDocuments tool."""

    @pytest.mark.asyncio
    async def test_count_documents_success(self, mock_ctx, patch_client):
        """Test successful counting of documents."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up test documents
        documents = [
            {'category': 'A', 'value': 10},
            {'category': 'A', 'value': 20},
            {'category': 'B', 'value': 30},
        ]

        for doc in documents:
            mock_client['test_db']['test_collection'].insert_one(doc)

        # Act
        result = await count_documents(connection_id, 'test_db', 'test_collection')

        # Assert
        assert 'count' in result
        assert result['count'] == 3
        assert result['database'] == 'test_db'
        assert result['collection'] == 'test_collection'

    @pytest.mark.asyncio
    async def test_count_documents_with_filter(self, mock_ctx, patch_client):
        """Test counting documents with a filter."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up test documents
        documents = [
            {'category': 'A', 'value': 10},
            {'category': 'A', 'value': 20},
            {'category': 'B', 'value': 30},
        ]

        for doc in documents:
            mock_client['test_db']['test_collection'].insert_one(doc)

        # Act
        filter_doc = {'category': 'A'}
        result = await count_documents(connection_id, 'test_db', 'test_collection', filter_doc)

        # Assert
        assert 'count' in result
        # In our mock implementation, filters are ignored
        # In a real implementation, it would count only category A documents
        assert result['filter'] == {'category': 'A'}

    @pytest.mark.asyncio
    async def test_count_documents_connection_not_found(self, mock_ctx):
        """Test count_documents with invalid connection ID."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await count_documents(str(uuid.uuid4()), 'test_db', 'test_collection')

    @pytest.mark.asyncio
    async def test_count_documents_handles_generic_exception(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test handling of generic exceptions during count_documents."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        def mock_count_documents(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr('conftest.MockCollection.count_documents', mock_count_documents)

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to count documents: Generic error'):
            await count_documents(connection_id, 'test_db', 'test_collection')


class TestGetDatabaseStatsTool:
    """Tests for the getDatabaseStats tool."""

    @pytest.mark.asyncio
    async def test_get_database_stats_success(self, mock_ctx, patch_client):
        """Test successful retrieval of database statistics."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Create some test collections
        mock_client['test_db']['collection1'].insert_one({'test': 'data'})
        mock_client['test_db']['collection2'].insert_one({'test': 'data'})

        # Act
        result = await get_database_stats(connection_id, 'test_db')

        # Assert
        assert 'stats' in result
        assert 'database' in result
        assert result['database'] == 'test_db'
        assert 'collections' in result['stats']
        assert 'objects' in result['stats']

        # Our mock implementation should report 2 collections
        assert result['stats']['collections'] == 2

    @pytest.mark.asyncio
    async def test_get_database_stats_connection_not_found(self, mock_ctx):
        """Test get_database_stats with invalid connection ID."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await get_database_stats(str(uuid.uuid4()), 'test_db')

    @pytest.mark.asyncio
    async def test_get_database_stats_handles_generic_exception(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test handling of generic exceptions during get_database_stats."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        def mock_command(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr('conftest.MockDatabase.command', mock_command)

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to get database statistics: Generic error'):
            await get_database_stats(connection_id, 'test_db')


class TestGetCollectionStatsTool:
    """Tests for the getCollectionStats tool."""

    @pytest.mark.asyncio
    async def test_get_collection_stats_success(self, mock_ctx, patch_client):
        """Test successful retrieval of collection statistics."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Create a test collection with some documents
        for i in range(5):
            mock_client['test_db']['test_collection'].insert_one({'index': i})

        # Act
        result = await get_collection_stats(connection_id, 'test_db', 'test_collection')

        # Assert
        assert 'stats' in result
        assert 'database' in result
        assert 'collection' in result
        assert result['database'] == 'test_db'
        assert result['collection'] == 'test_collection'

        # Our mock implementation should report 5 documents
        assert result['stats']['count'] == 5

    @pytest.mark.asyncio
    async def test_get_collection_stats_connection_not_found(self, mock_ctx):
        """Test get_collection_stats with invalid connection ID."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await get_collection_stats(str(uuid.uuid4()), 'test_db', 'test_collection')

    @pytest.mark.asyncio
    async def test_get_collection_stats_handles_generic_exception(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test handling of generic exceptions during get_collection_stats."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        def mock_command(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr('conftest.MockDatabase.command', mock_command)

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to get collection statistics: Generic error'):
            await get_collection_stats(connection_id, 'test_db', 'test_collection')


class TestAnalyzeSchemaTool:
    """Tests for the analyzeSchema tool."""

    @pytest.mark.asyncio
    async def test_analyze_schema_success(self, mock_ctx, patch_client):
        """Test successful schema analysis."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Set up test documents with different schemas
        documents = [
            {'_id': ObjectId(), 'name': 'Document 1', 'value': 10, 'tags': ['a', 'b']},
            {'_id': ObjectId(), 'name': 'Document 2', 'value': 20, 'active': True},
            {'_id': ObjectId(), 'name': 'Document 3', 'value': 30, 'tags': ['c']},
        ]

        for doc in documents:
            mock_client['test_db']['test_collection'].insert_one(doc)

        # Act
        result = await analyze_schema(connection_id, 'test_db', 'test_collection', 100)

        # Assert
        assert 'field_coverage' in result
        assert 'total_documents' in result
        assert 'sampled_documents' in result
        assert 'database' in result
        assert 'collection' in result
        assert result['database'] == 'test_db'
        assert result['collection'] == 'test_collection'
        assert result['total_documents'] == 3
        assert result['sampled_documents'] == 3

        # Since we have 3 docs with name and value fields, should have 100% coverage
        assert 'name' in result['field_coverage']
        assert 'value' in result['field_coverage']
        # Tags appear in docs 1 and 3
        assert 'tags' in result['field_coverage']
        # Active appears only in doc 2
        assert 'active' in result['field_coverage']

    @pytest.mark.asyncio
    async def test_analyze_schema_empty_collection(self, mock_ctx, patch_client):
        """Test analyze_schema with empty collection."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Act
        result = await analyze_schema(connection_id, 'test_db', 'empty_collection', 100)

        # Assert
        assert 'error' in result
        assert result['error'] == 'Collection is empty'
        assert result['total_documents'] == 0
        assert result['sampled_documents'] == 0

    @pytest.mark.asyncio
    async def test_analyze_schema_connection_not_found(self, mock_ctx):
        """Test analyze_schema with invalid connection ID."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await analyze_schema(str(uuid.uuid4()), 'test_db', 'test_collection', 100)

    @pytest.mark.asyncio
    async def test_analyze_schema_handles_generic_exception(
        self, mock_ctx, patch_client, monkeypatch
    ):
        """Test handling of generic exceptions during analyze_schema."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        def mock_count_documents(*args, **kwargs):
            raise Exception('Generic error')

        monkeypatch.setattr('conftest.MockCollection.count_documents', mock_count_documents)

        # Act/Assert
        with pytest.raises(ValueError, match='Failed to analyze collection schema: Generic error'):
            await analyze_schema(connection_id, 'test_db', 'test_collection', 100)


class TestExplainOperationTool:
    """Tests for the explainOperation tool."""

    @pytest.mark.asyncio
    async def test_explain_find_operation(self, mock_ctx, patch_client):
        """Test explaining a find operation."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Add some test data
        for i in range(5):
            mock_client['test_db']['test_collection'].insert_one({'index': i})

        # Act
        result = await explain_operation(
            connection_id,
            'test_db',
            'test_collection',
            'find',
            {'index': {'$gt': 2}},
            None,
            'queryPlanner',
        )

        # Assert
        assert 'explanation' in result
        assert 'operation_type' in result
        assert 'database' in result
        assert 'collection' in result
        assert result['operation_type'] == 'find'
        assert result['database'] == 'test_db'
        assert result['collection'] == 'test_collection'

    @pytest.mark.asyncio
    async def test_explain_aggregate_operation(self, mock_ctx, patch_client):
        """Test explaining an aggregate operation."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Add some test data
        for i in range(5):
            mock_client['test_db']['test_collection'].insert_one(
                {'category': 'A' if i < 3 else 'B', 'value': i * 10}
            )

        # Define a pipeline
        pipeline = [
            {'$match': {'category': 'A'}},
            {'$group': {'_id': '$category', 'total': {'$sum': '$value'}}},
        ]

        # Act
        result = await explain_operation(
            connection_id,
            'test_db',
            'test_collection',
            'aggregate',
            None,
            pipeline,
            'queryPlanner',
        )

        # Assert
        assert 'explanation' in result
        assert 'operation_type' in result
        assert 'database' in result
        assert 'collection' in result
        assert result['operation_type'] == 'aggregate'
        assert result['database'] == 'test_db'
        assert result['collection'] == 'test_collection'

    @pytest.mark.asyncio
    async def test_explain_operation_invalid_type(self, mock_ctx, patch_client):
        """Test explainOperation with invalid operation type."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Act/Assert
        with pytest.raises(ValueError, match='Operation type must be one of: find, aggregate'):
            await explain_operation(
                connection_id,
                'test_db',
                'test_collection',
                'invalid_type',
                {},
                None,
                'queryPlanner',
            )

    @pytest.mark.asyncio
    async def test_explain_operation_missing_pipeline(self, mock_ctx, patch_client):
        """Test explainOperation with missing pipeline for aggregate operation."""
        # Arrange
        mock_client = patch_client()  # noqa: F841
        connection_info = DocumentDBConnection.create_connection(
            'mongodb://example.com:27017/?retryWrites=false'
        )
        connection_id = connection_info.connection_id

        # Act/Assert
        with pytest.raises(ValueError, match='Pipeline is required for aggregate operations'):
            await explain_operation(
                connection_id,
                'test_db',
                'test_collection',
                'aggregate',
                None,
                None,
                'queryPlanner',
            )

    @pytest.mark.asyncio
    async def test_explain_operation_connection_not_found(self, mock_ctx):
        """Test explainOperation with invalid connection ID."""
        # Act/Assert
        with pytest.raises(ValueError, match='Connection ID .* not found'):
            await explain_operation(
                str(uuid.uuid4()), 'test_db', 'test_collection', 'find', {}, None, 'queryPlanner'
            )


class TestHelperFunctions:
    """Tests for helper functions used by the tools."""

    def test_get_field_type_number(self):
        """Test get_field_type for numeric values."""
        docs = [{'value': 10}, {'value': 20}]

        field_type = get_field_type(docs, 'value')
        assert field_type == 'int'

    def test_get_field_type_string(self):
        """Test get_field_type for string values."""
        docs = [{'name': 'Document 1'}, {'name': 'Document 2'}]

        field_type = get_field_type(docs, 'name')
        assert field_type == 'str'

    def test_get_field_type_boolean(self):
        """Test get_field_type for boolean values."""
        docs = [{'active': True}, {'active': False}]

        field_type = get_field_type(docs, 'active')
        assert field_type == 'bool'

    def test_get_field_type_list(self):
        """Test get_field_type for list values."""
        docs = [{'tags': ['a', 'b']}, {'tags': ['c']}]

        field_type = get_field_type(docs, 'tags')
        assert field_type == 'array'

    def test_get_field_type_nested_object(self):
        """Test get_field_type for nested objects."""
        docs = [{'metadata': {'created': '2023-01-01'}}, {'metadata': {'created': '2023-01-02'}}]

        field_type = get_field_type(docs, 'metadata')
        assert field_type == 'object'

    def test_get_field_type_mixed_types(self):
        """Test get_field_type for fields with mixed types."""
        docs = [{'value': 10}, {'value': 'string'}]

        field_type = get_field_type(docs, 'value')
        # Should return a list of types
        assert isinstance(field_type, list)
        assert 'int' in field_type
        assert 'str' in field_type

    def test_get_field_type_missing_field(self):
        """Test get_field_type for missing fields."""
        docs = [{'name': 'Document 1'}, {'name': 'Document 2'}]

        field_type = get_field_type(docs, 'non_existent_field')
        assert field_type == 'null'
