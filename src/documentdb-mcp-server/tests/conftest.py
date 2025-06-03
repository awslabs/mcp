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
"""Test fixtures for DocumentDB MCP server tests."""

import os
import pytest
import sys
from bson import ObjectId
from pymongo.errors import OperationFailure
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock


# Add the implementation directory to sys.path so tests can find modules properly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the specific implementation directory to sys.path
impl_dir = os.path.join(project_root, 'awslabs', 'documentdb_mcp_server')
if impl_dir not in sys.path:
    sys.path.insert(0, impl_dir)


class MockCollection:
    """Mock implementation of a DocumentDB collection."""

    def __init__(self, name: str, mock_data: Optional[List[Dict[str, Any]]] = None):
        """Initialize a mock collection.

        Args:
            name: Name of the collection
            mock_data: Optional list of documents to pre-populate the collection
        """
        self.name = name
        self._data = mock_data if mock_data is not None else []
        self._id_counter = 1

    def find(self, query=None, projection=None):
        """Mock find operation that applies actual filtering.

        Args:
            query: Query filter
            projection: Fields to include/exclude

        Returns:
            MockCursor: A cursor for the query results
        """
        # Apply actual filtering logic
        filtered_docs = self._apply_filter(query or {})

        # Apply projection if provided
        if projection:
            projected_docs = []
            for doc in filtered_docs:
                projected_doc = {}
                # Check if we're in inclusion or exclusion mode
                inclusion_mode = any(v == 1 for k, v in projection.items() if k != '_id')

                for field, value in doc.items():
                    include_field = True

                    if field in projection:
                        # Handle _id specially
                        if field == '_id':
                            include_field = projection[field] != 0
                        # For other fields
                        elif inclusion_mode:
                            include_field = projection[field] == 1
                        else:
                            include_field = projection[field] != 1
                    elif inclusion_mode and field != '_id':
                        include_field = False

                    if include_field:
                        projected_doc[field] = value

                projected_docs.append(projected_doc)
            return MockCursor(projected_docs)

        return MockCursor(filtered_docs)

    def _apply_filter(self, query):
        """Apply DocumentDB query filter to documents."""
        if not query:
            return self._data.copy()

        result = []
        for doc in self._data:
            match = True
            for field, criteria in query.items():
                if field.startswith('$'):
                    # Handle top-level operators like $and, $or
                    match = self._apply_logical_operator(doc, field, criteria)
                    if not match:
                        break
                elif isinstance(criteria, dict) and any(
                    k.startswith('$') for k in criteria.keys()
                ):
                    # Handle comparison operators like {field: {$gt: value}}
                    match = self._apply_comparison_operators(doc, field, criteria)
                    if not match:
                        break
                else:
                    # Simple equality match
                    if field not in doc or doc[field] != criteria:
                        match = False
                        break

            if match:
                result.append(doc)

        return result

    def _apply_logical_operator(self, doc, operator, criteria):
        """Apply logical operators like $and, $or."""
        if operator == '$and':
            return all(self._match_subdocument(doc, subquery) for subquery in criteria)
        elif operator == '$or':
            return any(self._match_subdocument(doc, subquery) for subquery in criteria)
        return False

    def _match_subdocument(self, doc, query):
        """Match a document against a subdocument query."""
        for field, criteria in query.items():
            if isinstance(criteria, dict) and any(k.startswith('$') for k in criteria.keys()):
                if not self._apply_comparison_operators(doc, field, criteria):
                    return False
            elif field not in doc or doc[field] != criteria:
                return False
        return True

    def _apply_comparison_operators(self, doc, field, criteria):
        """Apply comparison operators like $gt, $lt."""
        if field not in doc:
            return False

        value = doc[field]

        for op, threshold in criteria.items():
            if op == '$gt':
                if not (value > threshold):
                    return False
            elif op == '$gte':
                if not (value >= threshold):
                    return False
            elif op == '$lt':
                if not (value < threshold):
                    return False
            elif op == '$lte':
                if not (value <= threshold):
                    return False
            elif op == '$eq':
                if not (value == threshold):
                    return False
            elif op == '$ne':
                if not (value != threshold):
                    return False

        return True

    def find_one(self, query=None, projection=None):
        """Mock find_one operation.

        Args:
            query: Query filter
            projection: Fields to include/exclude

        Returns:
            dict: First document matching the query, or None if no match
        """
        cursor = self.find(query, projection)
        try:
            return next(cursor)
        except StopIteration:
            return None

    def insert_one(self, document):
        """Mock insert_one operation.

        Args:
            document: Document to insert

        Returns:
            MagicMock: A mock InsertOneResult
        """
        if '_id' not in document:
            document['_id'] = ObjectId()
        self._data.append(document)

        result = MagicMock()
        result.inserted_id = document['_id']
        return result

    def insert_many(self, documents):
        """Mock insert_many operation.

        Args:
            documents: Documents to insert

        Returns:
            MagicMock: A mock InsertManyResult
        """
        inserted_ids = []
        for doc in documents:
            if '_id' not in doc:
                doc['_id'] = ObjectId()
            self._data.append(doc)
            inserted_ids.append(doc['_id'])

        result = MagicMock()
        result.inserted_ids = inserted_ids
        return result

    def update_one(self, filter, update, upsert=False):
        """Mock update_one operation that applies filters.

        Args:
            filter: Query filter
            update: Update operations
            upsert: Whether to create document if none exists

        Returns:
            MagicMock: A mock UpdateResult
        """
        # Apply filter
        filtered_docs = self._apply_filter(filter or {})

        matched_count = 0
        modified_count = 0
        upserted_id = None

        if filtered_docs:
            # Update first matching document
            doc_to_update = filtered_docs[0]

            # Apply update operators
            if '$set' in update:
                for field, value in update['$set'].items():
                    doc_to_update[field] = value

            if '$inc' in update:
                for field, value in update['$inc'].items():
                    if field in doc_to_update:
                        doc_to_update[field] += value
                    else:
                        doc_to_update[field] = value

            # Add other update operators as needed

            matched_count = 1
            modified_count = 1
        elif upsert:
            # Create a new document
            new_doc = {}

            # Apply filter fields to new document
            for field, value in filter.items():
                if not field.startswith('$') and isinstance(value, (str, int, float, bool)):
                    new_doc[field] = value
            new_doc['_id'] = ObjectId()

            # Apply updates
            if '$set' in update:
                for field, value in update['$set'].items():
                    new_doc[field] = value

            self._data.append(new_doc)
            upserted_id = new_doc['_id']

        result = MagicMock()
        result.matched_count = matched_count
        result.modified_count = modified_count
        result.upserted_id = upserted_id
        return result

    def update_many(self, filter, update, upsert=False):
        """Mock update_many operation that applies filters.

        Args:
            filter: Query filter
            update: Update operations
            upsert: Whether to create document if none exists

        Returns:
            MagicMock: A mock UpdateResult
        """
        # Apply filter
        filtered_docs = self._apply_filter(filter or {})

        matched_count = len(filtered_docs)
        modified_count = matched_count
        upserted_id = None

        for doc in filtered_docs:
            # Apply update operators
            if '$set' in update:
                for field, value in update['$set'].items():
                    doc[field] = value

            if '$inc' in update:
                for field, value in update['$inc'].items():
                    if field in doc:
                        doc[field] += value
                    else:
                        doc[field] = value

            # Add other update operators as needed

        if not filtered_docs and upsert:
            # Create a new document
            new_doc = {}

            # Apply filter fields to new document
            for field, value in filter.items():
                if not field.startswith('$') and isinstance(value, (str, int, float, bool)):
                    new_doc[field] = value
            new_doc['_id'] = ObjectId()

            # Apply updates
            if '$set' in update:
                for field, value in update['$set'].items():
                    new_doc[field] = value

            self._data.append(new_doc)
            upserted_id = new_doc['_id']

        result = MagicMock()
        result.matched_count = matched_count
        result.modified_count = modified_count
        result.upserted_id = upserted_id
        return result

    def delete_one(self, filter):
        """Mock delete_one operation that applies filters.

        Args:
            filter: Query filter

        Returns:
            MagicMock: A mock DeleteResult
        """
        # Apply filter
        filtered_docs = self._apply_filter(filter or {})

        deleted_count = 0
        if filtered_docs:
            # Find the first document that matches the filter
            doc_to_delete = filtered_docs[0]
            # Find its index in the original data
            for i, doc in enumerate(self._data):
                if doc is doc_to_delete:  # Compare by identity
                    self._data.pop(i)
                    deleted_count = 1
                    break

        result = MagicMock()
        result.deleted_count = deleted_count
        return result

    def delete_many(self, filter):
        """Mock delete_many operation that applies filters.

        Args:
            filter: Query filter

        Returns:
            MagicMock: A mock DeleteResult
        """
        # Find documents to delete
        docs_to_delete: List[Dict[str, Any]] = self._apply_filter(filter or {})

        # Remove all matching documents
        deleted_count = 0
        if docs_to_delete:
            # Get object IDs to delete
            ids_to_delete = {doc.get('_id') for doc in docs_to_delete}

            # Remove from original data
            self._data = [doc for doc in self._data if doc.get('_id') not in ids_to_delete]

            deleted_count = len(docs_to_delete)

        result = MagicMock()
        result.deleted_count = deleted_count
        return result

    def replace_one(self, filter, replacement, upsert=False):
        """Mock replace_one operation that applies filters.

        Args:
            filter: Query filter to find the document to replace
            replacement: New document to replace with
            upsert: Whether to create a new document if none exists

        Returns:
            MagicMock: A mock UpdateResult
        """
        # Apply filter
        filtered_docs = self._apply_filter(filter or {})

        matched_count = len(filtered_docs)
        modified_count = 0
        upserted_id = None

        if filtered_docs:
            # Get the first matching document
            doc_to_replace = filtered_docs[0]

            # Find its index in the original data
            for i, doc in enumerate(self._data):
                if doc is doc_to_replace:  # Compare by identity
                    # Preserve _id field
                    original_id = doc.get('_id')

                    # Create new document with replacement content
                    new_doc = replacement.copy()
                    if '_id' not in new_doc:
                        new_doc['_id'] = original_id

                    # Replace the document
                    self._data[i] = new_doc
                    modified_count = 1
                    break
        elif upsert:
            # Create a new document with replacement content
            new_doc = replacement.copy()
            if '_id' not in new_doc:
                new_doc['_id'] = ObjectId()

            # Add the new document
            self._data.append(new_doc)
            upserted_id = new_doc['_id']

        result = MagicMock()
        result.matched_count = matched_count
        result.modified_count = modified_count
        result.upserted_id = upserted_id
        return result

    def aggregate(self, pipeline, explain=False):
        """Mock aggregate operation with pipeline processing.

        Args:
            pipeline: Aggregation pipeline
            explain: Whether to explain the operation

        Returns:
            MockCursor or dict: A cursor for the aggregation results or explanation
        """
        if explain:
            return {
                'explainVersion': '1',
                'queryPlanner': {
                    'namespace': f'{self.name}',
                    'indexFilterSet': False,
                    'parsedQuery': {},
                    'winningPlan': {'stage': 'COLLSCAN', 'direction': 'forward'},
                    'rejectedPlans': [],
                },
                'ok': 1,
            }

        # Process the pipeline stages
        result = self._data.copy()

        for stage in pipeline:
            # Process each stage
            if '$match' in stage:
                # Filter documents similar to find
                result = self._apply_filter(stage['$match'])
            elif '$group' in stage:
                result = self._process_group_stage(stage['$group'], result)
            elif '$project' in stage:
                result = self._process_project_stage(stage['$project'], result)
            elif '$sort' in stage:
                result = self._process_sort_stage(stage['$sort'], result)
            elif '$limit' in stage:
                result = result[: stage['$limit']]

        return MockCursor(result)

    def _process_group_stage(self, group_spec, documents):
        """Process $group stage in aggregation."""
        groups = {}
        id_key = group_spec.get('_id')

        # Simple implementation for basic grouping
        for doc in documents:
            # Extract group key
            if isinstance(id_key, str) and id_key.startswith('$'):
                # Field reference (e.g., "$category")
                field_name = id_key[1:]
                group_key = str(doc.get(field_name, 'null'))
            else:
                # Use the literal value or null
                group_key = str(id_key)

            # Initialize group if needed
            if group_key not in groups:
                groups[group_key] = {'_id': group_key}

            # Process aggregation operators
            for output_field, operator_def in group_spec.items():
                if output_field == '_id':
                    continue

                if isinstance(operator_def, dict):
                    for op, field_ref in operator_def.items():
                        if op == '$sum':
                            if field_ref == 1:
                                # Count
                                groups[group_key][output_field] = (
                                    groups[group_key].get(output_field, 0) + 1
                                )
                            else:
                                # Sum of field
                                field_name = (
                                    field_ref[1:]
                                    if isinstance(field_ref, str) and field_ref.startswith('$')
                                    else field_ref
                                )
                                value = doc.get(field_name, 0)
                                groups[group_key][output_field] = (
                                    groups[group_key].get(output_field, 0) + value
                                )
                        elif op == '$avg':
                            # We need to track both sum and count for average
                            if f'_{output_field}_sum' not in groups[group_key]:
                                groups[group_key][f'_{output_field}_sum'] = 0
                                groups[group_key][f'_{output_field}_count'] = 0

                            field_name = (
                                field_ref[1:]
                                if isinstance(field_ref, str) and field_ref.startswith('$')
                                else field_ref
                            )
                            value = doc.get(field_name, 0)
                            groups[group_key][f'_{output_field}_sum'] += value
                            groups[group_key][f'_{output_field}_count'] += 1
                            groups[group_key][output_field] = (
                                groups[group_key][f'_{output_field}_sum']
                                / groups[group_key][f'_{output_field}_count']
                            )

        return list(groups.values())

    def _process_project_stage(self, project_spec, documents):
        """Process $project stage in aggregation."""
        result = []
        for doc in documents:
            new_doc = {}
            for output_field, field_spec in project_spec.items():
                if isinstance(field_spec, bool) or field_spec == 1:
                    new_doc[output_field] = doc.get(output_field)
                elif isinstance(field_spec, str) and field_spec.startswith('$'):
                    field_name = field_spec[1:]
                    new_doc[output_field] = doc.get(field_name)
            result.append(new_doc)
        return result

    def _process_sort_stage(self, sort_spec, documents):
        """Process $sort stage in aggregation."""
        # Convert sort spec to a list of (field, direction) tuples
        sort_fields = [(field, direction) for field, direction in sort_spec.items()]

        # Define key function for sorting
        def sort_key(doc):
            keys = []
            for field, direction in sort_fields:
                value = doc.get(field)
                keys.append((value if value is not None else 0) * direction)
            return keys

        # Sort documents by each field in order
        return sorted(documents, key=sort_key)

    def count_documents(self, filter=None):
        """Mock count_documents operation that applies the filter.

        Args:
            filter: Query filter

        Returns:
            int: Count of documents matching the filter
        """
        # Apply the filter to the documents
        filtered_docs = self._apply_filter(filter or {})
        return len(filtered_docs)


class MockDatabase:
    """Mock implementation of a DocumentDB database."""

    def __init__(self, name: str):
        """Initialize a mock database.

        Args:
            name: Name of the database
        """
        self.name = name
        self._collections = {}

    def __getitem__(self, collection_name):
        """Get a collection by name.

        Args:
            collection_name: Name of the collection to get

        Returns:
            MockCollection: The requested collection
        """
        if collection_name not in self._collections:
            self._collections[collection_name] = MockCollection(collection_name)
        return self._collections[collection_name]

    def list_collection_names(self):
        """List collection names in the database.

        Returns:
            List[str]: List of collection names
        """
        return list(self._collections.keys())

    def create_collection(self, name):
        """Create a new collection.

        Args:
            name: Name of the collection to create
        """
        if name not in self._collections:
            self._collections[name] = MockCollection(name)

    def drop_collection(self, name):
        """Drop a collection.

        Args:
            name: Name of the collection to drop
        """
        if name in self._collections:
            del self._collections[name]

    def command(self, command_name, *args, **kwargs):
        """Execute a database command.

        Args:
            command_name: Name of the command
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            dict: Command results
        """
        if command_name == 'ping':
            return {'ok': 1}
        elif command_name == 'dbStats':
            # Return mock database stats
            return {
                'db': self.name,
                'collections': len(self._collections),
                'views': 0,
                'objects': sum(len(col._data) for col in self._collections.values()),
                'avgObjSize': 0,
                'dataSize': 0,
                'storageSize': 0,
                'freeStorageSize': 0,
                'indexes': 0,
                'indexSize': 0,
                'indexFreeStorageSize': 0,
                'ok': 1,
            }
        elif command_name == 'collStats':
            collection_name = args[0] if args else None
            if not collection_name or collection_name not in self._collections:
                raise OperationFailure(f"Collection '{collection_name}' not found")

            collection = self._collections[collection_name]
            # Return mock collection stats
            return {
                'ns': f'{self.name}.{collection_name}',
                'size': 0,
                'count': len(collection._data),
                'avgObjSize': 0,
                'storageSize': 0,
                'freeStorageSize': 0,
                'capped': False,
                'nindexes': 0,
                'indexSizes': {},
                'ok': 1,
            }
        elif isinstance(command_name, dict) and 'explain' in command_name:
            # Handle explain command for find and aggregate operations
            explain_info = command_name.get('explain', {})
            verbosity = command_name.get('verbosity', 'queryPlanner')

            # Basic explanation structure
            explanation = {
                'explainVersion': '1',
                'queryPlanner': {
                    'namespace': f'{self.name}.{explain_info.get("find") or explain_info.get("aggregate")}',
                    'indexFilterSet': False,
                    'parsedQuery': explain_info.get('filter', {}),
                    'winningPlan': {'stage': 'COLLSCAN', 'direction': 'forward'},
                    'rejectedPlans': [],
                },
                'ok': 1,
            }

            # Add executionStats if requested
            if verbosity.lower() == 'executionstats':
                explanation['executionStats'] = {
                    'executionSuccess': True,
                    'nReturned': 0,
                    'executionTimeMillis': 0,
                    'totalKeysExamined': 0,
                    'totalDocsExamined': 0,
                }

            return explanation
        else:
            raise OperationFailure(f"Command '{command_name}' not implemented in mock")


class MockDocumentDBClient:
    """Mock implementation of a DocumentDB client."""

    def __init__(self, connection_string: str, raise_on_connect: Optional[Exception] = None):
        """Initialize a mock DocumentDB client.

        Args:
            connection_string: Connection string
            raise_on_connect: Optional exception to raise when testing connection
        """
        self.connection_string = connection_string
        self.raise_on_connect = raise_on_connect
        self._databases = {}
        self.admin = MockAdminDatabase(self, raise_on_connect)

    def __getitem__(self, db_name):
        """Get a database by name.

        Args:
            db_name: Name of the database to get

        Returns:
            MockDatabase: The requested database
        """
        if db_name not in self._databases:
            self._databases[db_name] = MockDatabase(db_name)
        return self._databases[db_name]

    def list_database_names(self):
        """List database names.

        Returns:
            List[str]: List of database names
        """
        # Add default database that DocumentDB has
        default_dbs = {'admin'}

        # Include any mock databases we've created
        all_dbs = set(self._databases.keys()) | default_dbs

        return list(all_dbs)

    def close(self):
        """Close the client connection."""
        # Nothing to do in the mock
        pass


class MockContext:
    """Mock implementation of MCP context for testing."""

    def error(self, message):
        """Raise a runtime error with the given message.

        Args:
            message: Error message

        Raises:
            RuntimeError: Always raised with the given message
        """
        raise RuntimeError(f'MCP Tool Error: {message}')


@pytest.fixture
def mock_documentdb_client():
    """Fixture for a mock DocumentDB client.

    Returns:
        MockDocumentDBClient: A mock DocumentDB client
    """

    def _create_mock_client(
        connection_string='mongodb://example.com:27017?retryWrites=false', raise_on_connect=None
    ):
        return MockDocumentDBClient(connection_string, raise_on_connect)

    return _create_mock_client


@pytest.fixture
def patch_client(monkeypatch):
    """Fixture that patches MongoClient with our mock.

    Args:
        monkeypatch: pytest monkeypatch fixture

    Returns:
        function: Function to create and install a mock DocumentDB client
    """
    # Import here to avoid circular imports
    from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection

    # Clear connections at the beginning of the test
    DocumentDBConnection._connections = {}

    # Store original connections dictionary to restore if needed
    original_connections = {}

    def _patch_with_mock(raise_on_connect=None):
        mock_client = MockDocumentDBClient(
            'mongodb://example.com:27017?retryWrites=false', raise_on_connect
        )

        # Capture current connections before patching
        nonlocal original_connections
        original_connections = DocumentDBConnection._connections.copy()

        # Patch MongoClient in all relevant modules - server.py imports from connection_tools, so we only need to patch there
        monkeypatch.setattr(
            'awslabs.documentdb_mcp_server.connection_tools.MongoClient',
            lambda *args, **kwargs: mock_client,
        )
        monkeypatch.setattr('pymongo.MongoClient', lambda *args, **kwargs: mock_client)

        # Make sure we don't lose our connections after patching
        for conn_id, conn_info in original_connections.items():
            DocumentDBConnection._connections[conn_id] = conn_info

        return mock_client

    return _patch_with_mock


@pytest.fixture
def mock_ctx():
    """Fixture for a mock MCP context.

    Returns:
        MockContext: A mock MCP context
    """
    return MockContext()


class MockAdminDatabase:
    """Mock implementation of a DocumentDB admin database."""

    def __init__(self, client, raise_on_connect=None):
        """Initialize a mock admin database.

        Args:
            client: Parent client
            raise_on_connect: Optional exception to raise when testing connection
        """
        self.client = client
        self.raise_on_connect = raise_on_connect

    def command(self, command_name, *args, **kwargs):
        """Execute an admin command.

        Args:
            command_name: Name of the command
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            dict: Command results

        Raises:
            Exception: If raise_on_connect was provided
        """
        if self.raise_on_connect:
            raise self.raise_on_connect

        if command_name == 'ping':
            return {'ok': 1}
        else:
            return {'ok': 1}


class MockCursor:
    """Mock implementation of a DocumentDB cursor."""

    def __init__(self, data):
        """Initialize a mock cursor.

        Args:
            data: Data to iterate over
        """
        self._data = data.copy() if data else []
        self._position = 0
        self._limit = None

    def __iter__(self):
        """Get iterator for the cursor.

        Returns:
            MockCursor: Self
        """
        return self

    def __next__(self):
        """Get next document from the cursor.

        Returns:
            dict: Next document

        Raises:
            StopIteration: When no more documents are available
        """
        if self._limit is not None and self._position >= self._limit:
            raise StopIteration

        if self._position >= len(self._data):
            raise StopIteration

        doc = self._data[self._position]
        self._position += 1
        return doc

    def limit(self, limit_value):
        """Set limit on the cursor.

        Args:
            limit_value: Maximum number of documents to return

        Returns:
            MockCursor: Self
        """
        if limit_value > 0:
            self._limit = min(limit_value, len(self._data))
        return self

    def explain(self, verbosity='queryPlanner'):
        """Explain the query.

        Args:
            verbosity: Level of verbosity

        Returns:
            dict: Explanation of the query
        """
        return {
            'explainVersion': '1',
            'queryPlanner': {
                'namespace': 'test_db.test_collection',
                'indexFilterSet': False,
                'parsedQuery': {},
                'winningPlan': {'stage': 'COLLSCAN', 'direction': 'forward'},
                'rejectedPlans': [],
            },
            'ok': 1,
        }
