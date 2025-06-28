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

import time
from loguru import logger
from typing import Any


MAX_RESOURCE_COUNT = 500
TIMEOUT = 4


def get_current_time() -> float:
    """Return the current time as a float timestamp."""
    return time.time()


def determine_count_status(has_more_pages):
    """Determine the count status based on whether there are more pages."""
    return 'at_least' if has_more_pages else 'exact'


def limit_total_resource_count(total_resource_count, count_status):
    """Limit the total resource count and update the count status if the limit is exceeded.

    Args:
        total_resource_count: The current total resource count.
        count_status: The status object to update if the limit is exceeded.
    """
    if total_resource_count > MAX_RESOURCE_COUNT:
        logger.info(
            'Resource count is at least {}, capping to {}',
            total_resource_count,
            MAX_RESOURCE_COUNT,
        )
        if count_status == 'exact':
            logger.info('Updating the count_status from exact to at_least')
            count_status = 'at_least'
        return MAX_RESOURCE_COUNT, count_status
    else:
        return total_resource_count, count_status


def count_resources_from_path(data: Any, parsing_path: list[str]) -> int:
    """Count resources in the data structure by traversing the given parsing path.

    Args:
        data: The data structure to traverse.
        parsing_path: The list of keys representing the path to traverse.

    Returns:
        The number of resources found at the specified path.
    """
    if not parsing_path:
        return 1

    current_key = parsing_path[0]
    next_data = data.get(current_key)

    if isinstance(next_data, list):
        return sum(count_resources_from_path(item, parsing_path[1:]) for item in next_data)
    elif isinstance(next_data, dict):
        return count_resources_from_path(next_data, parsing_path[1:])

    return 0


def count_resources_via_pagination(
    client,
    first_page: dict[str, Any],
    first_page_time: float,
    service_name: str,
    operation_name: str,
    operation_python_name: str,
    parameters: dict,
) -> tuple[int, str] | None:
    """Paginate through AWS resources and count them."""
    # Determine the parsing path based on the service and operation
    parsing_path = (
        RESOURCE_PARSING_MAP[service_name][operation_name]['ParsingPath']
        if service_name in RESOURCE_PARSING_MAP
        and operation_name in RESOURCE_PARSING_MAP[service_name]
        else None
    )
    resource_key = None
    # Count resources in the first page
    if parsing_path:
        total_resource_count = count_resources_from_path(first_page, parsing_path)
    else:
        resource_key = next((key for key in first_page if isinstance(first_page[key], list)), None)
        if resource_key is None:
            logger.info(
                "Did not find list of resources in the response for operation '{}'",
                operation_python_name,
            )
            return None
        total_resource_count = len(first_page[resource_key])

    pagination_token = first_page.get('pagination_token')
    has_more_pages = pagination_token is not None

    # First page retrieval took too much, doesn't make sense to paginate
    if first_page_time > TIMEOUT:
        logger.info("Not paginating as first page took '{}' seconds to retrieve", first_page_time)
        return limit_total_resource_count(
            total_resource_count, determine_count_status(has_more_pages)
        )

    if pagination_token is None:
        logger.info('No pagination token found; returning count of the first page')
        return total_resource_count, 'exact'

    try:
        start_time = get_current_time()
        paginator = client.get_paginator(operation_python_name)
        pagination_token_key = paginator._pagination_cfg['output_token']
        for page in paginator.paginate(
            **parameters, PaginationConfig={'StartingToken': pagination_token}
        ):
            if parsing_path:
                total_resource_count += count_resources_from_path(page, parsing_path)
            else:
                total_resource_count += len(page.get(resource_key, []))

            # Check if there's a NextToken for more pages
            has_more_pages = pagination_token_key in page
            count_status = determine_count_status(has_more_pages)

            # Check for timeout or resource limit
            if get_current_time() - start_time > TIMEOUT:
                logger.warning("Pagination stopped due to '{}' second timeout", TIMEOUT)
                return total_resource_count, count_status
            if total_resource_count > MAX_RESOURCE_COUNT:
                logger.info(
                    "Pagination stopped due to reaching '{}' resources", total_resource_count
                )
                return limit_total_resource_count(total_resource_count, count_status)
    except Exception as error:
        logger.exception(
            "Failed to paginate with resource key '{}' and operation {}, error: {}",
            resource_key,
            operation_python_name,
            str(error),
        )
        return None
    return total_resource_count, 'exact'


RESOURCE_PARSING_MAP = {
    'cloudfront': {
        'ListFunctions': {'ParsingPath': ['FunctionList', 'Items']},
        'ListDistributions': {'ParsingPath': ['DistributionList', 'Items']},
        'ListKeyValueStores': {'ParsingPath': ['KeyValueStoreList', 'Items']},
        'ListStreamingDistributions': {'ParsingPath': ['StreamingDistributionList', 'Items']},
        'ListCloudFrontOriginAccessIdentities': {
            'ParsingPath': ['CloudFrontOriginAccessIdentityList', 'Items']
        },
        'ListInvalidations': {'ParsingPath': ['InvalidationList', 'Items']},
    },
    'ec2': {
        'DescribeInstances': {'ParsingPath': ['Reservations', 'Instances']},
    },
    'elasticache': {
        'DescribeEngineDefaultParameters': {'ParsingPath': ['EngineDefaults', 'Parameters']},
    },
    'neptune': {
        'DescribeEngineDefaultClusterParameters': {
            'ParsingPath': ['EngineDefaults', 'Parameters']
        },
        'DescribeEngineDefaultParameters': {'ParsingPath': ['EngineDefaults', 'Parameters']},
    },
    'rds': {
        'DescribeEngineDefaultClusterParameters': {
            'ParsingPath': ['EngineDefaults', 'Parameters']
        },
        'DescribeEngineDefaultParameters': {'ParsingPath': ['EngineDefaults', 'Parameters']},
    },
    'redshift': {
        'DescribeDefaultClusterParameters': {
            'ParsingPath': ['DefaultClusterParameters', 'Parameters']
        },
    },
}
