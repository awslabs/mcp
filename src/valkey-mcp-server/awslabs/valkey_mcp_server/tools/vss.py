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

import json
import logging
import struct
from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from typing import Any, Dict, List, Optional, Union
from valkey import Valkey
from valkey.cluster import ValkeyCluster
from valkey.commands.search.query import Query
from valkey.exceptions import ValkeyError


def _search_module_enabled(r: Union[Valkey, ValkeyCluster]) -> bool:
    try:
        r.execute_command('FT._LIST')
        return True
    except ValkeyError:
        return False


@mcp.tool()
async def vector_search(
    index: str,
    field: str,
    vector: List[float],
    filter_expression: Optional[str] = None,
    offset: int = 0,
    count: int = 10,
    no_content: bool = False,
) -> Dict[str, Any]:
    """Perform a Valkey vector search using the FT.SEARCH command.

    This tool performs K-nearest neighbors (KNN) search on vector embeddings stored in Valkey.
    It finds documents whose vector embeddings are most similar to the provided query vector.

    Args:
        index: Name of the Valkey search index to use
        field: Name of the vector field in the index to search against
        vector: The query vector as a list of floats (must match the dimensionality of indexed vectors)
        filter_expression: Optional filter expression to apply to the search results
        offset: Record offset determining the window slice of results to render (default: 0)
        count: Size of the window slice of results to render (default: 10)
        no_content: If True, return only document IDs without content (default: False)

    Returns:
        An object indicating the results of the operation, with a "status" field set to either "success" or "error",
        and a "reason" field (in the event of an error) set to the error reason, otherwise a "results" field
        containing a list of matching documents as dictionaries containing all document fields
        (excluding the vector field itself), or an error message if there was a failure

    Example:
        # Search for documents similar to a query vector
        results = await vector_search(
            index="products_idx",
            field="description_vector",
            vector=[0.1, 0.2, 0.3, ...],  # 768-dimensional vector
            count=5
        )
    """
    try:
        # Validate filter_expression to prevent injection attacks
        if filter_expression is not None and '=>' in filter_expression:
            return {
                'status': 'error',
                'type': 'validation',
                'reason': "Invalid filter expression: '=>' character sequence not allowed",
            }

        # Use connection with decode_responses=True for fetching document fields
        r = ValkeyConnectionManager.get_connection(decode_responses=False)

        # Check if search module is available
        if not _search_module_enabled(r):
            return {'status': 'error', 'type': 'valkey', 'reason': 'Search module not available'}

        # Access the search index
        ft = r.ft(index)

        # Construct the query for vector similarity search
        if filter_expression is None:
            filter_expression = '*'

        query = Query(f'{filter_expression}=>[KNN {count} @{field} $blob]').paging(offset, count)
        if no_content:
            query = query.no_content()

        # Convert vector to bytes for the query parameter
        vector_bytes = struct.pack(f'{len(vector)}f', *vector)

        # Execute the search to get document IDs
        query_params: dict[str, str | int | float | bytes] = {'blob': vector_bytes}
        result = ft.search(query, query_params=query_params)

        # If no results, return empty list
        if hasattr(result, 'total') and result.total == 0:  # type: ignore
            return {'status': 'success', 'results': []}

        documents_list = []
        if hasattr(result, 'docs'):  # type: ignore
            for doc in result.docs:  # type: ignore
                doc_id = doc.id

                if no_content:
                    documents_list.append({'id': doc_id})
                else:
                    # Check if doc has document_json field directly
                    if hasattr(doc, 'document_json') and doc.document_json:
                        try:
                            # Parse the document_json field which contains the original document
                            document_json_bytes = doc.document_json
                            # Ensure we decode bytes properly
                            if isinstance(document_json_bytes, bytes):
                                document_json_str = document_json_bytes.decode('utf-8')
                            else:
                                document_json_str = str(document_json_bytes)

                            document = json.loads(document_json_str)
                            documents_list.append(document)
                        except (UnicodeDecodeError, json.JSONDecodeError) as e:
                            # Skip documents that can't be decoded/parsed
                            logging.warning(
                                f'Skipping document {doc_id} due to decode error: {str(e)}'
                            )
                            continue

        return {'status': 'success', 'results': documents_list}

    except ValkeyError as e:
        return {
            'status': 'error',
            'type': 'valkey',
            'reason': f"Error searching index '{index}', field '{field}' with vector of length {len(vector)}: {str(e)}",
        }
    except Exception as e:
        return {
            'status': 'error',
            'type': 'general',
            'reason': f"Error searching index '{index}', field '{field}' with vector of length {len(vector)}: {str(e)}",
        }
