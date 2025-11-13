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

import boto3
import time
from ..aws.pagination import build_result
from ..aws.services import (
    extract_pagination_config,
)
from ..common.command import IRCommand, OutputFile
from ..common.config import get_user_agent_extra
from ..common.file_system_controls import validate_file_path
from ..common.helpers import operation_timer
from botocore.config import Config
from botocore.exceptions import ClientError
from jmespath.parser import ParsedResult
from typing import Any


TIMEOUT_AFTER_SECONDS = 10
CHUNK_SIZE = 4 * 1024 * 1024


def _should_retry_error(error: Exception) -> bool:
    """Determine if an error should be retried.

    - No retry for 4xx client errors (won't succeed on retry)
    - No retry for 503 Service Unavailable (service overload/spillover)
    - Return for other cases

    Args:
        error: The exception to evaluate

    Returns:
        bool: True if the error should be retried, False otherwise
    """
    if isinstance(error, ClientError):
        status_code = error.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)

        # Never retry 4xx errors (client errors)
        if 400 <= status_code < 500:
            return False

        # Never retry 503 (service overload)
        if status_code == 503:
            return False

    return True


def _execute_with_custom_retry(operation, **kwargs) -> dict[str, Any]:
    """Execute an operation with retry logic.

    Implements a single retry for allowed errors, with no retry for
    4xx errors or 503 Service Unavailable. Uses a 1-second delay before
    retry to match boto3's default behavior.

    Args:
        operation: The boto3 operation to execute
        **kwargs: Parameters to pass to the operation

    Returns:
        dict: The operation response

    Raises:
        Exception: The final error if all attempts fail
    """
    max_attempts = 2  # 1 initial attempt + 1 retry

    for attempt in range(max_attempts):
        try:
            return operation(**kwargs)
        except Exception as e:
            if attempt < max_attempts - 1 and _should_retry_error(e):
                time.sleep(1)  # 1 second delay before retry
                continue
            else:
                raise

    # This should never be reached, but included for type checking
    raise RuntimeError('Unexpected execution path in retry logic')


def interpret(
    ir: IRCommand,
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None,
    region: str,
    client_side_filter: ParsedResult | None = None,
    max_results: int | None = None,
    endpoint_url: str | None = None,
) -> dict[str, Any]:
    """Interpret the given intermediate representation into boto3 calls.

    The function returns the response from the operation indicated by the
    intermediate representation.
    """
    config_result = extract_pagination_config(ir.parameters, max_results)
    parameters = config_result.parameters
    pagination_config = config_result.pagination_config

    config = Config(
        region_name=region,
        connect_timeout=TIMEOUT_AFTER_SECONDS,
        read_timeout=TIMEOUT_AFTER_SECONDS,
        retries={'max_attempts': 1},  # Disable automatic retries
        user_agent_extra=get_user_agent_extra(),
    )

    with operation_timer(ir.service_name, ir.operation_python_name, region):
        client = boto3.client(
            ir.service_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
            config=config,
            endpoint_url=endpoint_url,
        )

        if client.can_paginate(ir.operation_python_name):
            # For paginated operations, wrap with custom retry logic
            paginator = client.get_paginator(ir.operation_python_name)

            def execute_pagination():
                return build_result(
                    paginator=paginator,
                    service_name=ir.service_name,
                    operation_name=ir.operation_name,
                    operation_parameters=ir.parameters,
                    pagination_config=pagination_config,
                    client_side_filter=client_side_filter,
                )

            response = _execute_with_custom_retry(execute_pagination)
        else:
            operation = getattr(client, ir.operation_python_name)
            response = _execute_with_custom_retry(operation, **parameters)

            if client_side_filter is not None:
                response = _apply_filter(response, client_side_filter)

        if ir.has_streaming_output and ir.output_file and ir.output_file.path != '-':
            response = _handle_streaming_output(response, ir.output_file)

        return response


def _handle_streaming_output(response: dict[str, Any], output_file: OutputFile) -> dict[str, Any]:
    streaming_output = response[output_file.response_key]

    # Validate file path before writing
    validated_path = validate_file_path(output_file.path)

    with open(validated_path, 'wb') as f:
        for chunk in streaming_output.iter_chunks(chunk_size=CHUNK_SIZE):
            f.write(chunk)

    del response[output_file.response_key]
    return response


def _apply_filter(response: dict[str, Any], client_side_filter: ParsedResult) -> dict[str, Any]:
    response_metadata = response.get('ResponseMetadata')
    filtered_result = client_side_filter.search(response)
    return {'Result': filtered_result, 'ResponseMetadata': response_metadata}
