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

from awslabs.valkey_mcp_server.common.connection import ValkeyConnectionManager
from awslabs.valkey_mcp_server.common.server import mcp
from typing import List, Dict, Any, Union
from valkey.exceptions import ValkeyError
from valkey.commands.search.query import Query
import struct
import json


@mcp.tool()
async def vector_search(index: str, field: str, vector: List[float], offset: int = 0, count: int = 10) -> Union[str, List[Dict[str, Any]]]:
    """Perform a Valkey vector search using the FT.SEARCH command.

    This tool performs K-nearest neighbors (KNN) search on vector embeddings stored in Valkey.
    It finds documents whose vector embeddings are most similar to the provided query vector.

    Args:
        index: Name of the Valkey search index to use
        field: Name of the vector field in the index to search against
        vector: The query vector as a list of floats (must match the dimensionality of indexed vectors)
        offset: Record offset determining the window slice of results to render (default: 0)
        count: Size of the window slice of results to render (default: 10)

    Returns:
        A list of matching documents as dictionaries containing all document fields
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
        # Use connection with decode_responses=True for fetching document fields
        r = ValkeyConnectionManager.get_connection(decode_responses=True)

        # Access the search index
        ft = r.ft(index)

        # Construct the query for vector similarity search
        query = Query(f"*=>[KNN {count} @{field} $blob]").no_content().paging(0, count)

        # Convert vector to bytes for the query parameter
        vector_bytes = struct.pack(f'{len(vector)}f', *vector)

        # Execute the search to get document IDs
        result = ft.search(query, query_params={"blob": vector_bytes})

        # If no results, return empty list
        if result.total == 0:
            return []

        # Use decode_responses=False to handle binary embeddings properly
        r_raw = ValkeyConnectionManager.get_connection(decode_responses=False)

        documents_list = []
        for doc in result.docs:
            # Get the document ID
            doc_id = doc.id

            # Fetch the document hash
            doc_fields = r_raw.hgetall(doc_id.encode() if isinstance(doc_id, str) else doc_id)

            if doc_fields and b'document_json' in doc_fields:
                # Parse the document_json field which contains the original document
                document = json.loads(doc_fields[b'document_json'].decode('utf-8'))
                documents_list.append(document)

        return documents_list

    except ValkeyError as e:
        return f"Error searching index '{index}', field '{field}' with vector of length {len(vector)}: {str(e)}"

