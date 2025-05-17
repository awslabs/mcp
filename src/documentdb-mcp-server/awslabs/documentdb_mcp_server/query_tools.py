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

"""Query tools for DocumentDB MCP Server."""

from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from loguru import logger
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


async def find(
    connection_id: Annotated[
        str, Field(description='The connection ID returned by the connect tool')
    ],
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
    query: Annotated[
        Dict[str, Any], Field(description='Query filter (e.g., {"name": "example"})')
    ],
    projection: Annotated[
        Optional[Dict[str, Any]],
        Field(description='Fields to include/exclude (e.g., {"_id": 0, "name": 1})'),
    ] = None,
    limit: Annotated[
        int, Field(description='Maximum number of documents to return (default: 10)')
    ] = 10,
) -> List[Dict[str, Any]]:
    """Run a query against a DocumentDB collection.

    This tool queries documents from a specified collection based on a filter.

    Returns:
        List[Dict[str, Any]]: List of matching documents
    """
    try:
        # Get connection
        if connection_id not in DocumentDBConnection._connections:
            raise ValueError(f'Connection ID {connection_id} not found. You must connect first.')

        connection_info = DocumentDBConnection._connections[connection_id]
        client = connection_info.client

        db = client[database]
        coll = db[collection]

        result = list(coll.find(query, projection).limit(limit))

        # Convert ObjectId to string for JSON serialization
        for doc in result:
            if '_id' in doc and not isinstance(doc['_id'], str):
                doc['_id'] = str(doc['_id'])

        logger.info(f'Query returned {len(result)} documents')
        return result
    except ValueError as e:
        logger.error(f'Connection error: {str(e)}')
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f'Error querying DocumentDB: {str(e)}')
        raise ValueError(f'Failed to query DocumentDB: {str(e)}')


async def aggregate(
    connection_id: Annotated[
        str, Field(description='The connection ID returned by the connect tool')
    ],
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
    pipeline: Annotated[
        List[Dict[str, Any]], Field(description='DocumentDB aggregation pipeline')
    ],
    limit: Annotated[
        int, Field(description='Maximum number of documents to return (default: 10)')
    ] = 10,
) -> List[Dict[str, Any]]:
    """Run an aggregation pipeline against a DocumentDB collection.

    This tool executes a DocumentDB aggregation pipeline on a specified collection.

    Returns:
        List[Dict[str, Any]]: List of aggregation results
    """
    try:
        # Get connection
        if connection_id not in DocumentDBConnection._connections:
            raise ValueError(f'Connection ID {connection_id} not found. You must connect first.')

        connection_info = DocumentDBConnection._connections[connection_id]
        client = connection_info.client

        db = client[database]
        coll = db[collection]

        # Add limit stage if not already in pipeline
        if limit > 0 and not any('$limit' in stage for stage in pipeline):
            pipeline.append({'$limit': limit})

        result = list(coll.aggregate(pipeline))

        # Convert ObjectId to string for JSON serialization
        for doc in result:
            if '_id' in doc and not isinstance(doc['_id'], str):
                doc['_id'] = str(doc['_id'])

        logger.info(f'Aggregation returned {len(result)} results')
        return result
    except ValueError as e:
        logger.error(f'Connection error: {str(e)}')
        raise ValueError(str(e))
    except Exception as e:
        logger.error(f'Error running aggregation in DocumentDB: {str(e)}')
        raise ValueError(f'Failed to run aggregation: {str(e)}')
