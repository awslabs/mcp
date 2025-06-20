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

import importlib_resources
import jmespath
import json
from botocore import loaders
from jmespath.exceptions import ParseError
from jmespath.parser import ParsedResult
from loguru import logger
from typing import Any


loader = loaders.create_loader()
API_LIST_PATH = 'data/api_filter_parsing_config.json'


def _load_api_list():
    with (
        importlib_resources.files('awslabs.aws_mcp_server.core')
        .joinpath(API_LIST_PATH)
        .open() as stream
    ):
        data = json.load(stream)
    return data


def _includes_value(obj, value: str) -> bool:
    if isinstance(obj, (list | dict)):
        for child in obj:
            child_obj = child if isinstance(obj, list) else obj[child]
            if _includes_value(child_obj, value):
                return True
        return False
    return str(obj) == value


def _extract_filter_subtree(tree: Any) -> Any | None:
    """Traverse JMESPath AST and return the first encountered filter_projection node.

    filter_projection node represents a part of the query enclosed in [?<filter_expression>].
    See https://jmespath.org/specification.html#filter-expressions for details.
    """
    if tree.get('type') == 'filter_projection':
        return tree
    if not tree.get('children'):
        return None
    for child in tree['children']:
        subtree = _extract_filter_subtree(child)
        if subtree:
            return subtree
    return None


def _process_filter(obj, parsing_path: list[str], query: ParsedResult):
    """Recursively processes and filters nested data structures based on a JMESPath query.

    Args:
        obj: The object to filter, can be a dict or list
        parsing_path: List of strings representing the path to traverse in the object
        query: JMESPath ParsedResult object containing the filter query

    Returns:
        Filtered object maintaining the original structure but with filtered arrays

    Raises:
        Exception: If the target value to filter is not a list
    """
    if parsing_path:
        remaining_path = parsing_path[1:]
        key = parsing_path[0]
        # Nested arrays case
        # E.g. for ec2.DescribeInstances - recursively processing each Reservation
        # Except for no remaining_path left - like {Instances:[...]} object
        if isinstance(obj[key], list) and remaining_path:
            filtered_list = [_process_filter(item, remaining_path, query) for item in obj[key]]
            obj[key] = filtered_list
            return obj
        else:
            obj[key] = _process_filter(obj[key], remaining_path, query)
            return obj
    else:
        # No remaining_path - filtering target array
        if isinstance(obj, list):
            return query.search(obj)
        else:
            logger.error('Target value to filter is not a list: {}', str(obj))
            raise RuntimeError('Target value to filter is not a list')


def _handle_filter_extraction(
    response: dict[str, Any],
    client_side_query: str,
    service_name: str,
    operation_name: str,
) -> dict[str, Any]:
    try:
        # ParsingPath - operation metadata used for item extraction
        # Example: ["Reservations", "Instances"] for ec2.DescribeInstances
        parsing_path = _api_list[service_name][operation_name]['ParsingPath']
    except KeyError as error:
        logger.error(
            'Failed to get the result key for service {} and operation {}, error: {}',
            service_name,
            operation_name,
            str(error),
        )
        return response

    logger.info(
        'Handling client side filtering, service {}, operation {}.', service_name, operation_name
    )
    try:
        query_parsing_result = jmespath.compile(client_side_query)
    except ParseError as error:
        logger.error('Parsing error: {}', str(error))
        return response

    # Extracting [?<filter>] part of the query to avoid output schema manipulation
    filter_subtree = _extract_filter_subtree(query_parsing_result.parsed)
    if filter_subtree is None:
        return response

    # Filter target modification to process array as root object.
    # [?<filter>] instead of FieldName[?<filter>]
    filter_subtree['children'][0]['type'] = 'identity'
    compiled_filter = ParsedResult(client_side_query, filter_subtree)

    try:
        filtered_response = _process_filter(response, parsing_path, compiled_filter)
    except Exception as error:
        logger.error('Filter processing error: {}', str(error))
        return response

    return filtered_response


def handle_client_side_query(
    response: dict[str, Any],
    client_side_query: str | None,
    service_name: str,
    operation_name: str,
) -> dict[str, Any]:
    """Handle client-side query filtering for AWS responses."""
    if client_side_query is None:
        return response
    client_side_query = str(client_side_query)
    return _handle_filter_extraction(
        response=response,
        client_side_query=client_side_query,
        service_name=service_name,
        operation_name=operation_name,
    )


_api_list = _load_api_list()
