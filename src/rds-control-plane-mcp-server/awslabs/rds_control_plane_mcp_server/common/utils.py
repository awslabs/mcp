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

"""General utility functions for the RDS Control Plane MCP Server."""

import asyncio
from typing import Any, Callable, Dict, List, TypeVar


T = TypeVar('T')


def convert_datetime_to_string(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings.

    Args:
        obj: Object to convert

    Returns:
        Object with datetime objects converted to strings
    """
    import datetime

    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_datetime_to_string(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_string(item) for item in obj]
    return obj


async def paginate_aws_api_call(
    client_function: Callable,
    format_function: Callable[[Dict[str, Any]], T],
    result_key: str,
    **kwargs: Any,
) -> List[T]:
    """Fetch all results using AWS API pagination.

    Args:
        client_function: Boto3 client function to call (e.g. rds_client.describe_db_clusters)
        format_function: Function to format each item in the result
        result_key: Key in the response that contains the list of items
        **kwargs: Additional arguments to pass to the client function

    Returns:
        List of formatted results
    """
    results = []
    response = await asyncio.to_thread(client_function, **kwargs)

    for item in response.get(result_key, []):
        results.append(format_function(item))

    while 'Marker' in response:
        kwargs['Marker'] = response['Marker']
        response = await asyncio.to_thread(client_function, **kwargs)
        for item in response.get(result_key, []):
            results.append(format_function(item))

    return results
