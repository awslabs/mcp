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

"""Write tools for DocumentDB MCP Server."""

from awslabs.documentdb_mcp_server.config import assert_namespace_allowed, serverConfig
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from awslabs.documentdb_mcp_server.errors import SafeToolError, tool_error
from loguru import logger
from pydantic import Field
from typing import Annotated, Any, Dict, List, Union


async def insert(
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
    documents: Annotated[
        Union[Dict[str, Any], List[Dict[str, Any]]],
        Field(description='Document or list of documents to insert'),
    ],
) -> Dict[str, Any]:
    """Insert one or more documents into a DocumentDB collection.

    This tool inserts new documents into a specified collection.

    Returns:
        Dict[str, Any]: Insert operation results including document IDs
    """
    # Check if server is in read-only mode
    if serverConfig.read_only_mode:
        logger.warning('Insert operation denied: Server is in read-only mode')
        raise SafeToolError('Operation not permitted: Server is configured in read-only mode')

    assert_namespace_allowed(database, collection)

    try:
        client = DocumentDBConnection.get_client()

        db = client[database]
        coll = db[collection]

        # Handle single document or multiple documents
        if isinstance(documents, dict):
            result = coll.insert_one(documents)
            inserted_ids = [str(result.inserted_id)]
            count = 1
        else:
            result = coll.insert_many(documents)
            inserted_ids = [str(id) for id in result.inserted_ids]
            count = len(inserted_ids)

        logger.info(f'Inserted {count} documents')
        return {'success': True, 'inserted_count': count, 'inserted_ids': inserted_ids}
    except Exception as e:
        raise tool_error('insert documents', e) from None


async def update(
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
    filter: Annotated[Dict[str, Any], Field(description='Filter to select documents to update')],
    update: Annotated[
        Dict[str, Any],
        Field(
            description='Update operators to apply, such as {"$set": {...}}. To replace a whole document instead, pass the replacement document and set replace=True.'
        ),
    ],
    upsert: Annotated[
        bool,
        Field(
            description='Whether to create a new document if no match is found (default: False)'
        ),
    ] = False,
    many: Annotated[
        bool, Field(description='Whether to update multiple documents (default: False)')
    ] = False,
    replace: Annotated[
        bool,
        Field(
            description='Replace the matched document with `update`, which must then contain no $ operators. '
            'Fields not in `update` are removed. Cannot be combined with many=True (default: False)'
        ),
    ] = False,
    confirm_destructive: Annotated[
        bool,
        Field(
            description='Required when `filter` is empty ({}), which matches every document in the collection (default: False)'
        ),
    ] = False,
) -> Dict[str, Any]:
    """Update documents in a DocumentDB collection.

    This tool updates existing documents that match a specified filter. An empty
    filter needs confirm_destructive=True. Replacing a whole document needs
    replace=True.

    Returns:
        Dict[str, Any]: Update operation results
    """
    # Check if server is in read-only mode
    if serverConfig.read_only_mode:
        logger.warning('Update operation denied: Server is in read-only mode')
        raise SafeToolError('Operation not permitted: Server is configured in read-only mode')

    if not filter and not confirm_destructive:
        raise SafeToolError(
            'An empty filter matches every document in the collection. '
            'Pass a filter, or set confirm_destructive=True to update all matching documents.'
        )

    has_operators = any(key.startswith('$') for key in update.keys())
    if replace and has_operators:
        raise SafeToolError(
            'With replace=True, update must be a replacement document without $ operators.'
        )
    if replace and many:
        raise SafeToolError(
            'replace=True replaces one document; it cannot be combined with many=True.'
        )
    if not replace and not has_operators:
        raise SafeToolError(
            'update has no $ operators (for example $set). Use operators to change fields, '
            'or set replace=True to replace the whole document.'
        )

    assert_namespace_allowed(database, collection)

    try:
        client = DocumentDBConnection.get_client()

        db = client[database]
        coll = db[collection]

        if replace:
            result = coll.replace_one(filter, update, upsert=upsert)
            matched = result.matched_count
            modified = result.modified_count
        # If the update needs to update multiple documents
        elif many:
            result = coll.update_many(filter, update, upsert=upsert)
            matched = result.matched_count
            modified = result.modified_count
        # Else only a single document needs to be updated
        else:
            result = coll.update_one(filter, update, upsert=upsert)
            matched = result.matched_count
            modified = result.modified_count

        upserted_id = str(result.upserted_id) if result.upserted_id else None

        logger.info(f'Updated {modified} documents (matched {matched})')
        return {
            'success': True,
            'matched_count': matched,
            'modified_count': modified,
            'upserted_id': upserted_id,
        }
    except Exception as e:
        raise tool_error('update documents', e) from None


async def delete(
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
    filter: Annotated[Dict[str, Any], Field(description='Filter to select documents to delete')],
    many: Annotated[
        bool, Field(description='Whether to delete multiple documents (default: False)')
    ] = False,
    confirm_destructive: Annotated[
        bool,
        Field(
            description='Required when `filter` is empty ({}), which matches every document in the collection (default: False)'
        ),
    ] = False,
) -> Dict[str, Any]:
    """Delete documents from a DocumentDB collection.

    This tool deletes documents that match a specified filter. An empty filter
    needs confirm_destructive=True.

    Returns:
        Dict[str, Any]: Delete operation results
    """
    # Check if server is in read-only mode
    if serverConfig.read_only_mode:
        logger.warning('Delete operation denied: Server is in read-only mode')
        raise SafeToolError('Operation not permitted: Server is configured in read-only mode')

    if not filter and not confirm_destructive:
        raise SafeToolError(
            'An empty filter matches every document in the collection. '
            'Pass a filter, or set confirm_destructive=True to delete all matching documents.'
        )

    assert_namespace_allowed(database, collection)

    try:
        client = DocumentDBConnection.get_client()

        db = client[database]
        coll = db[collection]

        if many:
            result = coll.delete_many(filter)
            deleted = result.deleted_count
        else:
            result = coll.delete_one(filter)
            deleted = result.deleted_count

        logger.info(f'Deleted {deleted} documents')
        return {'success': True, 'deleted_count': deleted}
    except Exception as e:
        raise tool_error('delete documents', e) from None
