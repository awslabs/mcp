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

from awslabs.documentdb_mcp_server.config import serverConfig
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from loguru import logger
from pydantic import Field
from typing import Annotated, Any, Dict, List, Union


async def insert(
    connection_id: Annotated[
        str, Field(description='The connection ID returned by the connect tool')
    ],
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
        raise ValueError('Operation not permitted: Server is configured in read-only mode')

    try:
        # Get connection
        if connection_id not in DocumentDBConnection._connections:
            raise ValueError(f'Connection ID {connection_id} not found. You must connect first.')

        connection_info = DocumentDBConnection._connections[connection_id]
        client = connection_info.client

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
    except ValueError as e:
        logger.error(f'Connection error: {str(e)}')
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f'Error inserting into DocumentDB: {str(e)}')
        raise ValueError(f'Failed to insert documents: {str(e)}')


async def update(
    connection_id: Annotated[
        str, Field(description='The connection ID returned by the connect tool')
    ],
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
    filter: Annotated[Dict[str, Any], Field(description='Filter to select documents to update')],
    update: Annotated[
        Dict[str, Any],
        Field(
            description='Update operations to apply. It should either include DocumentDB operators like $set, or an entire document if the entire document needs to be replaced.'
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
) -> Dict[str, Any]:
    """Update documents in a DocumentDB collection.

    This tool updates existing documents that match a specified filter.

    Returns:
        Dict[str, Any]: Update operation results
    """
    # Check if server is in read-only mode
    if serverConfig.read_only_mode:
        logger.warning('Update operation denied: Server is in read-only mode')
        raise ValueError('Operation not permitted: Server is configured in read-only mode')

    try:
        # Get connection
        if connection_id not in DocumentDBConnection._connections:
            raise ValueError(f'Connection ID {connection_id} not found. You must connect first.')

        connection_info = DocumentDBConnection._connections[connection_id]
        client = connection_info.client

        db = client[database]
        coll = db[collection]

        # If the update doesn't have any operators, then it's a replace
        if not any(key.startswith('$') for key in update.keys()):
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
    except ValueError as e:
        logger.error(f'Connection error: {str(e)}')
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f'Error updating DocumentDB: {str(e)}')
        raise ValueError(f'Failed to update documents: {str(e)}')


async def delete(
    connection_id: Annotated[
        str, Field(description='The connection ID returned by the connect tool')
    ],
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
    filter: Annotated[Dict[str, Any], Field(description='Filter to select documents to delete')],
    many: Annotated[
        bool, Field(description='Whether to delete multiple documents (default: False)')
    ] = False,
) -> Dict[str, Any]:
    """Delete documents from a DocumentDB collection.

    This tool deletes documents that match a specified filter.

    Returns:
        Dict[str, Any]: Delete operation results
    """
    # Check if server is in read-only mode
    if serverConfig.read_only_mode:
        logger.warning('Delete operation denied: Server is in read-only mode')
        raise ValueError('Operation not permitted: Server is configured in read-only mode')

    try:
        # Get connection
        if connection_id not in DocumentDBConnection._connections:
            raise ValueError(f'Connection ID {connection_id} not found. You must connect first.')

        connection_info = DocumentDBConnection._connections[connection_id]
        client = connection_info.client

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
    except ValueError as e:
        logger.error(f'Connection error: {str(e)}')
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f'Error deleting from DocumentDB: {str(e)}')
        raise ValueError(f'Failed to delete documents: {str(e)}')
