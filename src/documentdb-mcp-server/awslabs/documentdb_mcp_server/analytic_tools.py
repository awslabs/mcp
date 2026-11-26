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

"""Analytic tools for DocumentDB MCP Server."""

from awslabs.documentdb_mcp_server.config import (
    MAX_RESULTS,
    assert_pipeline_readonly,
    bounded_limit,
    serverConfig,
)
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from awslabs.documentdb_mcp_server.errors import SafeToolError, tool_error
from loguru import logger
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


async def count_documents(
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
    filter: Annotated[
        Optional[Dict[str, Any]], Field(description='Query filter to count specific documents')
    ] = None,
) -> Dict[str, Any]:
    """Count documents in a DocumentDB collection.

    This tool counts the number of documents in a collection that match the provided filter.
    If no filter is provided, it counts all documents.

    Returns:
        Dict[str, Any]: Count result
    """
    try:
        client = DocumentDBConnection.get_client()

        db = client[database]
        coll = db[collection]

        # Use empty filter if none provided
        if filter is None:
            filter = {}

        count = coll.count_documents(filter)

        logger.info(f"Counted {count} documents in '{database}.{collection}'")
        return {'count': count, 'database': database, 'collection': collection, 'filter': filter}
    except Exception as e:
        raise tool_error('count documents', e) from None


async def get_database_stats(
    database: Annotated[str, Field(description='Name of the database')],
) -> Dict[str, Any]:
    """Get statistics about a DocumentDB database.

    This tool retrieves statistics about the specified database,
    including storage information and collection data.

    Returns:
        Dict[str, Any]: Database statistics
    """
    try:
        client = DocumentDBConnection.get_client()

        db = client[database]

        # Get database stats
        stats = db.command('dbStats')

        logger.info(f"Retrieved database statistics for '{database}'")
        return {'stats': stats, 'database': database}
    except Exception as e:
        raise tool_error('get database statistics', e) from None


async def get_collection_stats(
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
) -> Dict[str, Any]:
    """Get statistics about a DocumentDB collection.

    This tool retrieves detailed statistics about the specified collection,
    including size, document count, and storage information.

    Returns:
        Dict[str, Any]: Collection statistics
    """
    try:
        client = DocumentDBConnection.get_client()

        db = client[database]

        # Get collection stats
        stats = db.command('collStats', collection)

        logger.info(f"Retrieved collection statistics for '{database}.{collection}'")
        return {'stats': stats, 'database': database, 'collection': collection}
    except Exception as e:
        raise tool_error('get collection statistics', e) from None


def get_field_type(docs, path):
    """Helper function to determine the data type of a field across documents."""
    parts = path.split('.')
    types = set()

    for doc in docs:
        value = doc
        try:
            for part in parts:
                if '[' in part:
                    # Handle array indexing
                    array_part = part.split('[')[0]
                    if array_part in value:
                        value = value[array_part]
                        # Try to get array item
                        if isinstance(value, list) and len(value) > 0:
                            index = int(part.split('[')[1].split(']')[0])
                            if len(value) > index:
                                value = value[index]
                            else:
                                value = None
                                break
                        else:
                            value = None
                            break
                    else:
                        value = None
                        break
                else:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = None
                        break

            if value is not None:
                value_type = type(value).__name__
                if value_type == 'dict':
                    types.add('object')
                elif value_type == 'list':
                    types.add('array')
                else:
                    types.add(value_type)
        except (ValueError, IndexError, KeyError, TypeError, AttributeError) as e:
            # Never log the document or the exception text: both can contain field values.
            doc_id_type = type(doc.get('_id')).__name__ if isinstance(doc, dict) else 'n/a'
            logger.warning(
                f'Error processing field {path!r} (document _id type: {doc_id_type}): '
                f'{type(e).__name__}'
            )
            continue

    if not types:
        return 'null'
    elif len(types) == 1:
        return next(iter(types))
    else:
        return list(types)


async def analyze_schema(
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection to analyze')],
    sample_size: Annotated[
        int,
        Field(
            ge=1,
            le=MAX_RESULTS,
            description=f'Number of documents to sample (default: 100, max: {MAX_RESULTS})',
        ),
    ] = 100,
) -> Dict[str, Any]:
    """Analyze the schema of a collection by sampling documents.

    This tool samples documents from a collection and provides information about
    the document structure and field coverage across the sampled documents.

    Returns:
        Dict[str, Any]: Schema analysis results including field coverage
    """
    try:
        client = DocumentDBConnection.get_client()

        db = client[database]
        coll = db[collection]

        # Count total documents to adjust sample size if needed
        total_docs = coll.count_documents({})
        actual_sample_size = min(bounded_limit(sample_size), total_docs)

        if actual_sample_size == 0:
            return {
                'error': 'Collection is empty',
                'field_coverage': {},
                'total_documents': 0,
                'sampled_documents': 0,
            }

        # Sample documents (using aggregation with $sample stage)
        sample_pipeline = [{'$sample': {'size': actual_sample_size}}]
        sampled_docs = list(coll.aggregate(sample_pipeline))

        # Analyze schema and calculate field coverage
        field_paths = set()
        field_counts = {}

        def extract_paths(obj, prefix=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == '_id':
                        continue  # Skip _id field

                    path = f'{prefix}.{key}' if prefix else key
                    field_paths.add(path)

                    if path not in field_counts:
                        field_counts[path] = 0
                    field_counts[path] += 1

                    extract_paths(value, path)
            elif isinstance(obj, list) and len(obj) > 0:
                # For arrays, we'll only analyze the first item to avoid complexity
                extract_paths(obj[0], f'{prefix}[0]')

        for doc in sampled_docs:
            extract_paths(doc)

        # Calculate coverage percentages
        coverage = {}
        for path, count in field_counts.items():
            coverage[path] = {
                'count': count,
                'percentage': round((count / actual_sample_size) * 100, 2),
                'data_type': get_field_type(sampled_docs, path),
            }

        logger.info(
            f"Analyzed schema for '{database}.{collection}' with {actual_sample_size} documents"
        )
        return {
            'field_coverage': coverage,
            'total_documents': total_docs,
            'sampled_documents': actual_sample_size,
            'database': database,
            'collection': collection,
        }
    except Exception as e:
        raise tool_error('analyze collection schema', e) from None


async def explain_operation(
    database: Annotated[str, Field(description='Name of the database')],
    collection: Annotated[str, Field(description='Name of the collection')],
    operation_type: Annotated[
        str, Field(description='Type of operation to explain (find, aggregate)')
    ],
    query: Annotated[
        Optional[Dict[str, Any]], Field(description='Query for find operations')
    ] = None,
    pipeline: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(description='Pipeline for DocumentDB aggregation operations'),
    ] = None,
    verbosity: Annotated[
        str,
        Field(
            description=(
                'Explanation verbosity level (queryPlanner, executionStats). In read-only '
                'mode, aggregate explains always use queryPlanner.'
            )
        ),
    ] = 'queryPlanner',
) -> Dict[str, Any]:
    """Get an explanation of how an operation will be executed.

    This tool returns the execution plan for a query or aggregation operation,
    helping you understand how DocumentDB will process your operations.

    In read-only mode, aggregation pipelines are checked for write stages ($out,
    $merge) and explained with queryPlanner only, so the pipeline is planned but
    not executed.

    Returns:
        Dict[str, Any]: Operation explanation
    """
    try:
        client = DocumentDBConnection.get_client()

        db = client[database]
        # Get collection but no need to store in variable since we use db.command directly
        db[collection]  # Validate collection exists

        # Validate operation type
        operation_type = operation_type.lower()
        if operation_type not in ['find', 'aggregate']:
            raise SafeToolError('Operation type must be one of: find, aggregate')

        # Validate verbosity
        verbosity_lower = verbosity.lower()
        if verbosity_lower not in ['queryplanner', 'executionstats']:
            verbosity = 'queryPlanner'  # Default to queryPlanner if invalid

        # Get explanation based on operation type
        if operation_type == 'find':
            if not query:
                query = {}

            explanation = db.command(
                {'explain': {'find': collection, 'filter': query}, 'verbosity': verbosity}
            )
            logger.info(f"Explained find operation on '{database}.{collection}'")

        else:  # aggregate
            if not pipeline:
                raise SafeToolError('Pipeline is required for aggregate operations')

            assert_pipeline_readonly(pipeline)
            if serverConfig.read_only_mode and verbosity.lower() != 'queryplanner':
                logger.info('Read-only mode: explaining aggregate with queryPlanner only')
                verbosity = 'queryPlanner'

            explanation = db.command(
                {
                    'explain': {'aggregate': collection, 'pipeline': pipeline, 'cursor': {}},
                    'verbosity': verbosity,
                }
            )
            logger.info(f"Explained aggregate operation on '{database}.{collection}'")

        return {
            'explanation': explanation,
            'operation_type': operation_type,
            'verbosity': verbosity,
            'database': database,
            'collection': collection,
        }
    except Exception as e:
        raise tool_error('explain operation', e) from None
