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

"""Query tools for DocumentDB MCP Server."""

from awslabs.documentdb_mcp_server.config import (
    MAX_RESULTS,
    WRITE_STAGES,
    assert_pipeline_readonly,
    bounded_limit,
)
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from awslabs.documentdb_mcp_server.errors import tool_error
from loguru import logger
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


async def find(
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
        int,
        Field(
            ge=1,
            le=MAX_RESULTS,
            description=f'Maximum number of documents to return (default: 10, max: {MAX_RESULTS})',
        ),
    ] = 10,
) -> List[Dict[str, Any]]:
    """Run a query against a DocumentDB collection.

    This tool queries documents from a specified collection based on a filter.

    Returns:
        List[Dict[str, Any]]: List of matching documents
    """
    try:
        client = DocumentDBConnection.get_client()

        db = client[database]
        coll = db[collection]

        result = list(coll.find(query, projection).limit(bounded_limit(limit)))

        # Convert ObjectId to string for JSON serialization
        for doc in result:
            if '_id' in doc and not isinstance(doc['_id'], str):
                doc['_id'] = str(doc['_id'])

        logger.info(f'Query returned {len(result)} documents')
        return result
    except Exception as e:
        raise tool_error('query DocumentDB', e) from None


async def aggregate(
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
    pipeline: Annotated[
        List[Dict[str, Any]], Field(description='DocumentDB aggregation pipeline')
    ],
    limit: Annotated[
        int,
        Field(
            ge=1,
            le=MAX_RESULTS,
            description=f'Maximum number of documents to return (default: 10, max: {MAX_RESULTS})',
        ),
    ] = 10,
) -> List[Dict[str, Any]]:
    """Run an aggregation pipeline against a DocumentDB collection.

    This tool executes a DocumentDB aggregation pipeline on a specified collection.

    Returns:
        List[Dict[str, Any]]: List of aggregation results
    """
    assert_pipeline_readonly(pipeline)

    try:
        client = DocumentDBConnection.get_client()

        db = client[database]
        coll = db[collection]

        # Always cap the result with a final server-controlled $limit, even if the
        # pipeline has its own. A pipeline that ends in $out/$merge (write mode
        # only) returns no documents and must keep that stage last.
        last_stage = pipeline[-1] if pipeline else {}
        if not any(s in last_stage for s in WRITE_STAGES):
            pipeline = [*pipeline, {'$limit': bounded_limit(limit)}]

        result = list(coll.aggregate(pipeline))

        # Convert ObjectId to string for JSON serialization
        for doc in result:
            if '_id' in doc and not isinstance(doc['_id'], str):
                doc['_id'] = str(doc['_id'])

        logger.info(f'Aggregation returned {len(result)} results')
        return result
    except Exception as e:
        raise tool_error('run aggregation', e) from None
