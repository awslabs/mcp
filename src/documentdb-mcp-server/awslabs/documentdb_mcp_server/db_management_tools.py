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

"""Database management tools for DocumentDB MCP Server."""

from awslabs.documentdb_mcp_server.config import serverConfig
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from loguru import logger
from pydantic import Field
from typing import Annotated, Any, Dict, List


async def list_databases(
    connection_id: Annotated[
        str, Field(description='The connection ID returned by the connect tool')
    ],
) -> Dict[str, Any]:
    """List all available databases in the DocumentDB cluster.

    This tool returns the names of all accessible databases in the connected cluster.

    Returns:
        Dict[str, Any]: List of database names
    """
    try:
        client = DocumentDBConnection.get_connection(connection_id)
        databases = client.list_database_names()
        logger.info(f'Found {len(databases)} databases')
        return {'databases': databases, 'count': len(databases)}
    except ValueError as e:
        logger.error(f'Connection error: {str(e)}')
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f'Error listing databases: {str(e)}')
        raise ValueError(f'Failed to list databases: {str(e)}')


async def create_collection(
    connection_id: Annotated[
        str, Field(description='The connection ID returned by the connect tool')
    ],
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection to create')],
) -> Dict[str, Any]:
    """Create a new collection in a DocumentDB database.

    This tool creates a new collection in the specified database.

    Returns:
        Dict[str, Any]: Status of collection creation
    """
    # Check if server is in read-only mode
    if serverConfig.read_only_mode:
        logger.warning('Create collection operation denied: Server is in read-only mode')
        raise ValueError('Operation not permitted: Server is configured in read-only mode')

    try:
        # Get connection
        if connection_id not in DocumentDBConnection._connections:
            raise ValueError(f'Connection ID {connection_id} not found. You must connect first.')

        connection_info = DocumentDBConnection._connections[connection_id]
        client = connection_info.client

        db = client[database]

        # Check if collection already exists
        existing_collections = db.list_collection_names()
        if collection in existing_collections:
            return {
                'success': False,
                'message': f"Collection '{collection}' already exists in database '{database}'",
            }

        # Create the collection
        db.create_collection(collection)

        logger.info(f"Created collection '{collection}' in database '{database}'")
        return {'success': True, 'message': f"Collection '{collection}' created successfully"}
    except ValueError as e:
        logger.error(f'Connection error: {str(e)}')
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f'Error creating collection: {str(e)}')
        raise ValueError(f'Failed to create collection: {str(e)}')


async def list_collections(
    connection_id: Annotated[
        str, Field(description='The connection ID returned by the connect tool')
    ],
    database: Annotated[str, Field(description='Name of the database')],
) -> List[str]:
    """List collections in a DocumentDB database.

    This tool returns the names of all collections in a specified database.

    Returns:
        List[str]: List of collection names
    """
    try:
        # Get connection
        if connection_id not in DocumentDBConnection._connections:
            raise ValueError(f'Connection ID {connection_id} not found. You must connect first.')

        connection_info = DocumentDBConnection._connections[connection_id]
        client = connection_info.client
        db = client[database]
        collections = db.list_collection_names()
        logger.info(f"Found {len(collections)} collections in database '{database}'")
        return collections
    except ValueError as e:
        logger.error(f'Connection error: {str(e)}')
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f'Error listing collections: {str(e)}')
        raise ValueError(f'Failed to list collections: {str(e)}')


async def drop_collection(
    connection_id: Annotated[
        str, Field(description='The connection ID returned by the connect tool')
    ],
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection to drop')],
) -> Dict[str, Any]:
    """Drop a collection from a DocumentDB database.

    This tool completely removes a collection and all its documents from the specified database.
    This operation cannot be undone, so use it with caution.

    Returns:
        Dict[str, Any]: Status of the drop operation
    """
    # Check if server is in read-only mode
    if serverConfig.read_only_mode:
        logger.warning('Drop collection operation denied: Server is in read-only mode')
        raise ValueError('Operation not permitted: Server is configured in read-only mode')

    try:
        # Get connection
        if connection_id not in DocumentDBConnection._connections:
            raise ValueError(f'Connection ID {connection_id} not found. You must connect first.')

        connection_info = DocumentDBConnection._connections[connection_id]
        client = connection_info.client

        db = client[database]

        # Check if collection exists
        existing_collections = db.list_collection_names()
        if collection not in existing_collections:
            return {
                'success': False,
                'message': f"Collection '{collection}' does not exist in database '{database}'",
            }

        # Drop the collection
        db.drop_collection(collection)

        logger.info(f"Dropped collection '{collection}' from database '{database}'")
        return {'success': True, 'message': f"Collection '{collection}' dropped successfully"}
    except ValueError as e:
        logger.error(f'Connection error: {str(e)}')
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f'Error dropping collection: {str(e)}')
        raise ValueError(f'Failed to drop collection: {str(e)}')
