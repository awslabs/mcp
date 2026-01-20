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

"""AI-friendly semantic search tools for vector similarity search in Valkey.

This module provides high-level, document-oriented tools for AI assistants to work with
vector embeddings without needing to understand low-level implementation details.
"""

import json
import logging
import struct
from awslabs.valkey_mcp_server.common.config import VALKEY_CFG
from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from awslabs.valkey_mcp_server.context import Context
from awslabs.valkey_mcp_server.embeddings import create_embeddings_provider
from awslabs.valkey_mcp_server.tools.index import create_vector_index
from awslabs.valkey_mcp_server.tools.vss import vector_search
from typing import Any, Dict, List, Optional, Union
from valkey import Valkey
from valkey.cluster import ValkeyCluster
from valkey.exceptions import ValkeyError


# Initialize the embeddings provider based on environment configuration
_embeddings_provider = None


def _acquire_embeddings_provider():
    global _embeddings_provider
    if _embeddings_provider is None:
        _embeddings_provider = create_embeddings_provider()
    return _embeddings_provider


def _get_collection_index_name(collection: str) -> str:
    """Get the Valkey index name for a collection."""
    return f'semantic_collection_{collection}'


def _get_document_key(collection: str, document_id: str) -> str:
    """Get the Valkey key for a document."""
    return f'semantic_collection_{collection}:doc:{document_id}'


def _index_exists(
    conn: Union[Valkey, ValkeyCluster],
    collection: str,
) -> bool:
    """Check if a collection index exists."""
    index_name = _get_collection_index_name(collection)
    try:
        conn.execute_command('FT.INFO', index_name)
        return True
    except ValkeyError:
        return False


@mcp.tool()
async def add_documents(
    collection: str,
    documents: List[Dict[str, Any]],
    text_fields: Optional[List[str]] = None,
    embedding_dimensions: Optional[int] = None,
) -> Dict[str, Any]:
    """Add documents to a collection with automatic embedding generation.

    This tool stores documents in a searchable collection, automatically generating
    vector embeddings from the specified text fields. Documents can contain any fields,
    but must have an 'id' field.

    The embedding provider is configured via the EMBEDDINGS_PROVIDER environment variable.
    The embedding dimensions are automatically detected from the provider's output.
    If embedding_dimensions is not specified, it will be determined from the first
    embedding generated.

    Args:
        collection: Name of the collection (e.g., "research_papers", "customer_reviews")
        documents: List of documents, each must have an 'id' field
        text_fields: Fields to use for embedding generation (default: ["content"])
        embedding_dimensions: Vector dimensions (auto-detected if not specified)

    Returns:
        Summary of the operation including number of documents added and provider info, or in the case
        of an error, the error message, in a similar structure.  In both cases, the "status" and "added" fields
        indicate the overall result of the operation and the number of documents successfully added.

    Example:
        result = await add_documents(
            collection="research_papers",
            documents=[
                {
                    "id": "paper_1",
                    "title": "AI in Healthcare",
                    "content": "Machine learning is transforming medical diagnosis...",
                    "author": "Dr. Smith",
                    "year": 2024
                }
            ],
            text_fields=["title", "content"]
        )
    """
    if text_fields is None:
        text_fields = ['content']

    try:
        r = ValkeyConnectionManager.get_connection(decode_responses=True)
        if Context.readonly_mode():
            return {'status': 'error', 'added': 0, 'reason': 'Valkey is in read-only mode'}

        index_name = _get_collection_index_name(collection)
        index_exists = _index_exists(r, collection)

        # Process and store each document
        added_count = 0
        error_count = 0
        actual_dimensions = embedding_dimensions

        for doc in documents:
            if 'id' not in doc:
                logging.warning(f"Document with keys {list(doc.keys())} is missing 'id', skipping")
                error_count += 1
                continue  # Skip documents without ID

            doc_id = doc['id']
            doc_key = _get_document_key(collection, doc_id)

            try:
                # Generate embedding from specified text fields
                text_to_embed = ' '.join(str(doc.get(field, '')) for field in text_fields)
                provider = _acquire_embeddings_provider()
                embedding = await provider.generate_embedding(text_to_embed)

                # Auto-detect dimensions from first embedding if not specified
                if actual_dimensions is None:
                    actual_dimensions = len(embedding)

                    # Create index now that we know the dimensions
                    if not index_exists:
                        await create_vector_index(
                            index_name,
                            actual_dimensions,
                            prefix=[_get_document_key(collection, '')],
                            structure_type=VALKEY_CFG['vec_index_type'],
                        )
                        index_exists = True

                embedding_bytes = struct.pack(f'{len(embedding)}f', *embedding)

                # Store document with embedding
                doc_data = {'embedding': embedding_bytes, 'document_json': json.dumps(doc)}

                r.hset(doc_key, mapping=doc_data)
                added_count += 1

            except Exception as e:
                logging.warning(f'Failed to process document {doc_id}: {str(e)}')
                error_count += 1
                continue

        # Valkey may need time to index, but it's never a good idea to sleep explicitly
        # So, for now, it's okay if the total documents is inaccurate
        # import time
        # time.sleep(1.0)  # Wait for index to be ready

        # Count total documents
        keys_result = r.keys(f'{_get_document_key(collection, "")}*')  # type: ignore
        total_docs = len(keys_result) if keys_result else 0  # type: ignore

        return {
            'status': 'success',
            'added': added_count,
            'errors': error_count,
            'collection': collection,
            'total_documents': total_docs,
            'embedding_dimensions': actual_dimensions,
            'embeddings_provider': _acquire_embeddings_provider().get_provider_name(),
        }

    except Exception as e:
        return {
            'status': 'error',
            'added': 0,
            'errors': len(documents),
            'collection': collection,
            'reason': str(e),
        }


@mcp.tool()
async def update_document(
    collection: str, document: Dict[str, Any], text_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Update a single document in a collection by its ID.

    This tool updates an existing document in a collection, regenerating its vector
    embedding from the specified text fields. The document must have an 'id' field
    that matches an existing document in the collection.

    Args:
        collection: Name of the collection
        document: Document data with 'id' field matching existing document
        text_fields: Fields to use for embedding generation (default: ["content"])

    Returns:
        Summary of the operation including success status and document info

    Example:
        result = await update_document(
            collection="research_papers",
            document={
                "id": "paper_1",
                "title": "AI in Healthcare - Updated",
                "content": "Updated content about machine learning in medical diagnosis...",
                "author": "Dr. Smith",
                "year": 2024
            },
            text_fields=["title", "content"]
        )
    """
    if text_fields is None:
        text_fields = ['content']

    try:
        if 'id' not in document:
            return {'status': 'error', 'updated': 0, 'reason': "Document must have an 'id' field"}

        r = ValkeyConnectionManager.get_connection(decode_responses=True)
        if Context.readonly_mode():
            return {'status': 'error', 'updated': 0, 'reason': 'Valkey is in read-only mode'}

        doc_id = document['id']
        doc_key = _get_document_key(collection, doc_id)

        # Check if document exists
        if not r.exists(doc_key):
            return {
                'status': 'error',
                'updated': 0,
                'reason': f"Document with id '{doc_id}' not found in collection '{collection}'",
            }

        # Generate new embedding from specified text fields
        text_to_embed = ' '.join(str(document.get(field, '')) for field in text_fields)
        provider = _acquire_embeddings_provider()
        embedding = await provider.generate_embedding(text_to_embed)
        embedding_bytes = struct.pack(f'{len(embedding)}f', *embedding)

        # Update document with new embedding
        doc_data = {'embedding': embedding_bytes, 'document_json': json.dumps(document)}

        r.hset(doc_key, mapping=doc_data)

        return {
            'status': 'success',
            'updated': 1,
            'collection': collection,
            'document_id': doc_id,
            'embedding_dimensions': len(embedding),
            'embeddings_provider': _acquire_embeddings_provider().get_provider_name(),
        }

    except Exception as e:
        return {'status': 'error', 'updated': 0, 'collection': collection, 'reason': str(e)}


@mcp.tool()
async def collection_info(collection: str) -> Dict[str, Any]:
    """Get indexing information for a collection.

    This tool provides information about the indexing status of documents
    in a collection, helping users understand if their documents are
    properly indexed and searchable.

    Args:
        collection: Name of the collection to check

    Returns:
        Information about stored vs indexed documents

    Example:
        result = await collection_info(collection="research_papers")
    """
    try:
        r = ValkeyConnectionManager.get_connection(decode_responses=True)
        index_name = _get_collection_index_name(collection)

        # Count stored documents
        keys_result = r.keys(f'{_get_document_key(collection, "")}*')  # type: ignore
        stored_docs = len(keys_result) if keys_result else 0  # type: ignore

        # Get index information
        try:
            index_info_result = r.execute_command('FT.INFO', index_name)  # type: ignore
            # Parse index info to get indexed document count
            info_dict = {}
            if index_info_result:
                for i in range(0, len(index_info_result), 2):  # type: ignore
                    key = (
                        index_info_result[i].decode()  # type: ignore
                        if isinstance(index_info_result[i], bytes)  # type: ignore
                        else index_info_result[i]  # type: ignore
                    )
                    value = index_info_result[i + 1]  # type: ignore
                    if isinstance(value, bytes):
                        value = value.decode()
                    info_dict[key] = value

            indexed_docs = int(info_dict.get('num_docs', 0))

            return {
                'status': 'success',
                'collection': collection,
                'stored_documents': stored_docs,
                'indexed_documents': indexed_docs,
                'hash_indexing_failures': info_dict['hash_indexing_failures'],
                'percent_indexed': indexed_docs / stored_docs if stored_docs > 0 else 0,
                'indexing_complete': stored_docs == indexed_docs,
                'index_name': index_name,
            }

        except ValkeyError:
            return {
                'status': 'error',
                'collection': collection,
                'stored_documents': stored_docs,
                'reason': f"Index '{index_name}' not found",
            }

    except Exception as e:
        return {'status': 'error', 'collection': collection, 'reason': str(e)}


@mcp.tool()
async def semantic_search(
    collection: str,
    query: str,
    offset: int = 0,
    limit: int = 10,
    include_content: bool = True,
    filter_expression: Optional[str] = None,
) -> Dict[str, Any]:
    """Search for documents using natural language queries.

    This tool performs semantic similarity search, finding documents whose meaning
    is similar to the query text, even if they don't contain the exact same words.

    Args:
        collection: Collection to search in
        query: Natural language search query
        offset: Record offset determining the window slice of results to render (default: 0)
        limit: Maximum number of results to return (default: 10)
        include_content: Whether to include full document content (default: True)
        filter_expression: Optional filter expression to apply to the search results

    Returns:
        An object indicating the results of the operation, with a "status" field set to either "success" or "error",
        and a "reason" field (in the event of an error) set to the error reason, otherwise a "results" field
        containing a list of matching documents with similarity scores and metadata

    Example:
        results = await semantic_search(
            collection="research_papers",
            query="impact of climate change on agriculture",
            limit=5
        )
        # Returns documents ranked by semantic similarity
    """
    try:
        r_check = ValkeyConnectionManager.get_connection(decode_responses=True)
        index_name = _get_collection_index_name(collection)
        if not _index_exists(r_check, collection):
            return {
                'status': 'error',
                'type': 'index',
                'reason': f"Index '{index_name}' does not exist",
            }

        # Generate embedding for query
        try:
            provider = _acquire_embeddings_provider()
            query_embedding = await provider.generate_embedding(query)
        except Exception as e:
            return {
                'status': 'error',
                'type': 'embedding',
                'reason': f'Failed to generate embedding: {str(e)}',
            }

        try:
            search_results = await vector_search(
                index=index_name,
                field='embedding',
                vector=query_embedding,
                offset=offset,
                count=limit,
                no_content=not include_content,
                filter_expression=filter_expression,
            )
        except Exception as e:
            return {
                'status': 'error',
                'type': 'vector_search',
                'reason': f'Vector search failed: {str(e)}',
            }

        # vector_search now returns a structured dict with status/results
        if search_results['status'] != 'success':
            # Error occurred in vector_search
            return {
                'status': 'error',
                'type': search_results.get('type', 'valkey'),
                'reason': search_results.get('reason', 'Unknown vector search error'),
            }

        # Extract the actual results list
        results_list = search_results['results']

        # If we don't need full content, filter to minimal fields
        if not include_content:
            results = []
            for doc in results_list:
                if isinstance(doc, dict):
                    KEEP_FIELDS = ['id', 'title', 'name']
                    result = {k: v for k, v in doc.items() if k in KEEP_FIELDS}
                    results.append(result)
                else:
                    # Handle unexpected format
                    return {
                        'status': 'error',
                        'type': 'format',
                        'reason': f'Unexpected document format in results: {type(doc)}',
                    }
            return {'status': 'success', 'results': results}

        return {'status': 'success', 'results': results_list}

    except ValkeyError as ex:
        return {'status': 'error', 'type': 'valkey', 'reason': str(ex)}
    except Exception as ex:
        return {'status': 'error', 'type': 'general', 'reason': str(ex)}


@mcp.tool()
async def find_similar_documents(
    collection: str, document_id: str, offset: int = 0, limit: int = 10
) -> Dict[str, Any]:
    """Find documents similar to an existing document.

    Args:
        collection: Collection name
        document_id: ID of the reference document
        offset: Record offset (default: 0)
        limit: Maximum number of results (default: 10)

    Returns:
        An object indicating the results of the operation, with a "status" field set to either "success" or "error",
        and a "reason" field (in the event of an error) set to the error reason, otherwise a "results" field
        containing a list of similar documents

    Example:
        similar = await find_similar_documents(
            collection="research_papers",
            document_id="paper_123",
            limit=5
        )
    """
    try:
        r = ValkeyConnectionManager.get_connection(decode_responses=False)
        doc_key = _get_document_key(collection, document_id)

        # Get the document's embedding
        embedding_bytes = r.hget(doc_key, b'embedding')  # type: ignore
        if not embedding_bytes:
            return {
                'status': 'error',
                'type': 'content',
                'reason': f"Document '{document_id}' not found in collection '{collection}'",
            }

        # Unpack the embedding vector
        num_floats = len(embedding_bytes) // 4 if embedding_bytes else 0  # type: ignore
        embedding = (
            list(struct.unpack(f'{num_floats}f', embedding_bytes))  # type: ignore
            if embedding_bytes
            else []
        )

        index_name = _get_collection_index_name(collection)
        search_result = await vector_search(
            index=index_name,
            field='embedding',
            vector=embedding,
            offset=offset,
            count=limit + 1,  # Get one extra since we'll filter out the source doc
        )

        # vector_search returns structured dict
        if search_result['status'] != 'success':
            return {
                'status': 'error',
                'type': search_result.get('type', 'vss'),
                'reason': search_result.get('reason', 'Vector search failed'),
            }

        # Filter out the source document itself
        results = [doc for doc in search_result['results'] if doc.get('id') != document_id]

        # Return only the requested limit
        return {'status': 'success', 'results': results[:limit]}

    except ValkeyError as ex:
        return {'status': 'error', 'type': 'valkey', 'reason': str(ex)}
    except Exception as ex:
        return {'status': 'error', 'type': 'general', 'reason': str(ex)}


@mcp.tool()
async def get_document(collection: str, document_id: str) -> Dict[str, Any]:
    """Retrieve a specific document by ID.

    Args:
        collection: Collection name
        document_id: Document ID

    Returns:
        An object indicating the results of the operation, with a "status" field set to either "success" or "error",
        and a "reason" field (in the event of an error) set to the error reason, otherwise a "result" field
        containing the document, or None if not found

    Example:
        doc = await get_document(
            collection="research_papers",
            document_id="paper_123"
        )
    """
    try:
        r = ValkeyConnectionManager.get_connection(decode_responses=False)
        doc_key = _get_document_key(collection, document_id)

        doc_data = r.hgetall(doc_key)  # type: ignore
        if b'document_json' in doc_data:  # type: ignore
            try:
                document_json_bytes = doc_data[b'document_json']  # type: ignore
                document_json_str = (
                    document_json_bytes.decode('utf-8')
                    if isinstance(document_json_bytes, bytes)
                    else str(document_json_bytes)
                )
                document = json.loads(document_json_str)
                return {'status': 'success', 'result': document}
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                return {
                    'status': 'error',
                    'type': 'decode',
                    'reason': f'Failed to decode document: {str(e)}',
                }

        return {'status': 'success', 'result': None}

    except ValkeyError as ex:
        return {'status': 'error', 'type': 'valkey', 'reason': str(ex)}
    except Exception as ex:
        return {'status': 'error', 'type': 'general', 'reason': str(ex)}


@mcp.tool()
async def list_collections(limit: int = 100) -> Dict[str, Any]:
    """List all available document collections.

    Args:
        limit: Maximum number of collections to return (default: 100)

    Returns:
        An object indicating the results of the operation, with a "status" field set to either "success" or "error",
        and a "reason" field (in the event of an error) set to the error reason, otherwise a "results" field
        containing a list of collections with metadata

    Example:
        collections = await list_collections(limit=10)
        # Returns: {
        #   "status": "success",
        #   "results": [
        #     {"name": "research_papers", "document_count": 150},
        #     {"name": "customer_reviews", "document_count": 500}
        #   ]
        # }
    """
    try:
        r = ValkeyConnectionManager.get_connection(decode_responses=False)

        # Get all indices
        indices_result = r.execute_command('FT._LIST')  # type: ignore
        indices = indices_result if indices_result else []

        collections = []
        for index in indices:  # type: ignore
            # Decode index name if it's bytes
            index_str = index.decode('utf-8') if isinstance(index, bytes) else index

            # Extract collection name from index name
            if index_str.startswith('semantic_collection_'):
                collection_name = index_str.replace('semantic_collection_', '')

                # Count documents
                doc_keys_result = r.keys(f'semantic_collection_{collection_name}:doc:*')  # type: ignore
                doc_keys = doc_keys_result if doc_keys_result else []

                collections.append({'name': collection_name, 'document_count': len(doc_keys)})  # type: ignore

                # Apply limit
                if len(collections) >= limit:
                    break

        return {'status': 'success', 'results': collections}

    except ValkeyError as ex:
        return {'status': 'error', 'type': 'valkey', 'reason': str(ex)}
    except Exception as ex:
        return {'status': 'error', 'type': 'general', 'reason': str(ex)}
