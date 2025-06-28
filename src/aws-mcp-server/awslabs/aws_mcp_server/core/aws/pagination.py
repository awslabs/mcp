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
import time
from .services import PaginationConfig
from botocore.paginate import PageIterator, Paginator
from botocore.utils import merge_dicts, set_value_from_jmespath
from loguru import logger
from typing import Any


PAGINATION_TIMEOUT = 4  # seconds


def estimate_llm_tokens(page: str) -> int:
    """This function estimates the amount of tokens the LLM would consume to process the given page (JSON).

    1 token ~= 4 characters. Curly brackets consume a single token.
    """
    characters_per_token = 4
    curly_brackets = (
        page.count('{') * 2  # we multiply by 2 because there will always be a matching '}'
    )
    return round((len(page) - curly_brackets) / characters_per_token + curly_brackets)


def _process_token_limits(
    remaining_tokens: int | None,
    page: dict[str, Any],
    is_first_page: bool,
) -> tuple[int | None, bool]:
    if remaining_tokens is None:
        return remaining_tokens, False

    remaining_tokens -= estimate_llm_tokens(json.dumps(page, default=str))

    should_stop = not is_first_page and remaining_tokens < 0
    if should_stop:
        logger.info('Reached max_tokens limit while paginating.')

    return remaining_tokens, should_stop


def _should_stop_early(
    elapsed_time: float,
    remaining_tokens: int | None,
    is_first_page: bool,
) -> bool:
    if elapsed_time > PAGINATION_TIMEOUT:
        logger.info('Reached pagination timeout.')
        return True

    if remaining_tokens is not None and remaining_tokens < 0 and is_first_page:
        # We always process the first page regardless of the amount of tokens
        logger.info('Reached max_tokens limit on first page.')
        return True

    return False


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
    pages_processed: int,
) -> dict[str, Any]:
    """Finalize the result by adding non-aggregate parts and processing metadata."""
    merge_dicts(result, page_iterator.non_aggregate_part)

    if page_iterator.resume_token is not None:
        result['pagination_token'] = page_iterator.resume_token

    logger.info(f'Processed {pages_processed} pages.')
    return result


def build_result(
    paginator: Paginator,
    service_name: str,
    operation_name: str,
    operation_parameters: dict[str, Any],
    pagination_config: PaginationConfig,
    max_tokens: int | None = None,
):
    """This function is based on build_full_result in botocore with some modifications.

    to take into account token limits, max results and timeouts. The first page is always processed.

    https://github.com/boto/botocore/blob/master/botocore/paginate.py#L481
    """
    result: dict[str, Any] = {}
    remaining_tokens = max_tokens
    pages_processed = 0
    start_time = time.time()

    logger.info(
        f'Building pagination result for {service_name} {operation_name} with config: {pagination_config}'
    )
    page_iterator = paginator.paginate(**operation_parameters, PaginationConfig=pagination_config)

    for response in page_iterator:
        is_first_page = pages_processed == 0
        page = response

        # operation object pagination comes in a tuple of two elements: (http_response, parsed_response)
        if isinstance(response, tuple) and len(response) == 2:
            page = response[1]

        remaining_tokens, should_stop_for_tokens = _process_token_limits(
            remaining_tokens, page, is_first_page
        )
        if should_stop_for_tokens:
            break

        # For each page in the response we need to inject the necessary components from the page into the result.
        _merge_page_into_result(result, page, page_iterator)
        pages_processed += 1

        result['ResponseMetadata'] = page.get('ResponseMetadata')

        elapsed_time = time.time() - start_time
        if _should_stop_early(elapsed_time, remaining_tokens, is_first_page):
            if is_first_page:
                # Setting resume_token manually because this is not populated if we only process the first page.
                page_iterator.resume_token = page_iterator._get_next_token(page)
            break

    _finalize_result(result, page_iterator, pages_processed)
    return result
