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
from typing import List, Dict, Any, Union
from valkey.exceptions import ValkeyError
from valkey.commands.search.query import Query
import struct


async def vector_search(index: str, field: str, vector: List[float], offset: int = 0, count: int = 10) -> Union[str, List[Dict[str, Any]]]:
    """Perform a Valkey vector search using the FT.SEARCH command

    Args:
        index: Name of the index to use
        field: Name of the vector field in the index to search
        vector: The vector query as a list of floats
        offset: Record offset determining the window slice of results to render (default: 0)
        count: Size of the window slice of results to render (default: 10)

    Returns:
        A list of matching documents as dictionaries containing all document fields
        (excluding the vector field itself), or an error message if there was a failure

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

        documents_list = []
        for doc in result.docs:
            # Get the document ID
            doc_id = doc.id

            # Fetch all fields from the document hash
            doc_fields = r.hgetall(doc_id)

            if doc_fields:
                # Remove the vector field from the results since it's binary data
                # and not useful for display
                doc_dict = {key: value for key, value in doc_fields.items() if key != field}
                # Add the document ID to the results
                doc_dict['id'] = doc_id
                documents_list.append(doc_dict)

        return documents_list

    except ValkeyError as e:
        return f"Error searching index '{index}', field '{field}' with vector of length {len(vector)}: {str(e)}"

