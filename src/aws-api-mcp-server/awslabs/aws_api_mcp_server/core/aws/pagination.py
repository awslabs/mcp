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

from .services import PaginationConfig
from botocore.paginate import PageIterator, Paginator
from botocore.utils import merge_dicts, set_value_from_jmespath
from jmespath.parser import ParsedResult
from loguru import logger
from typing import Any


def _merge_page_into_result(
    result: dict[str, Any],
    page: dict[str, Any],
    page_iterator: PageIterator,
) -> dict[str, Any]:
    for result_expression in page_iterator.result_keys:
        result_value = result_expression.search(page)
        if result_value is None:
            continue

        existing_value = result_expression.search(result)
        if existing_value is None:
            # Set the initial result
            set_value_from_jmespath(
                result,
                result_expression.expression,
                result_value,
            )
            continue

        # Merge with existing value
        if isinstance(result_value, list):
            existing_value.extend(result_value)
        elif isinstance(result_value, (int | float | str)):
            # Modify the existing result with the sum or concatenation
            set_value_from_jmespath(
                result,
                result_expression.expression,
                existing_value + result_value,
            )

    return result


def _finalize_result(
    result: dict[str, Any],
    page_iterator: PageIterator,
    response_metadata: dict[str, Any] | None,
    client_side_filter: ParsedResult | None,
) -> dict[str, Any]:
    """Finalize the result by adding non-aggregate parts and processing metadata."""
    if client_side_filter is not None:
        # Apply client-side filter
        result = {'Result': client_side_filter.search(result)}

    merge_dicts(result, page_iterator.non_aggregate_part)

    result['ResponseMetadata'] = response_metadata

    if page_iterator.resume_token is not None:
        result['pagination_token'] = page_iterator.resume_token

    return result


def build_result(
    paginator: Paginator,
    service_name: str,
    operation_name: str,
    operation_parameters: dict[str, Any],
    pagination_config: PaginationConfig,
    client_side_filter: ParsedResult | None = None,
):
    """This function is based on build_full_result in botocore with some modifications.

    to take into account token limits, max results and timeouts. The first page is always processed.

    https://github.com/boto/botocore/blob/master/botocore/paginate.py#L481
    """
    result: dict[str, Any] = {}
    response_metadata = None

    logger.info(
        f'Building pagination result for {service_name} {operation_name} with config: {pagination_config}'
    )
    page_iterator = paginator.paginate(**operation_parameters, PaginationConfig=pagination_config)

    for response in page_iterator:
        page = response

        # operation object pagination comes in a tuple of two elements: (http_response, parsed_response)
        if isinstance(response, tuple) and len(response) == 2:
            page = response[1]

        # For each page in the response we need to inject the necessary components from the page into the result.
        _merge_page_into_result(result, page, page_iterator)

        response_metadata = page.get('ResponseMetadata')

    return _finalize_result(result, page_iterator, response_metadata, client_side_filter)
