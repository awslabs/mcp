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
import json
from collections import OrderedDict
from ..aws.pagination import build_result
from ..aws.services import (
    extract_pagination_config,
)
from ..common.command import IRCommand, OutputFile
from ..common.config import CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS, get_user_agent_extra
from ..common.file_system_controls import validate_file_path
from ..common.helpers import Boto3Encoder, operation_timer
from botocore.config import Config
from jmespath.parser import ParsedResult
from loguru import logger
from typing import Any


TIMEOUT_AFTER_SECONDS = 10
CHUNK_SIZE = 4 * 1024 * 1024

# Bounded LRU cache for boto3 clients to avoid creating heavyweight objects per request.
# Each client loads service models, creates connection pools, and allocates SSL contexts.
# Keyed on (service_name, region, access_key_id, secret_access_key, session_token, endpoint_url).
# OrderedDict gives O(1) move_to_end() for LRU eviction.
_client_cache: OrderedDict[tuple, Any] = OrderedDict()
_MAX_CACHED_CLIENTS = 30

# Auth error codes that should trigger client eviction and retry
_AUTH_ERROR_CODES = frozenset(
    {
        'ExpiredTokenException',
        'ExpiredToken',
        'RequestExpired',
        'InvalidClientTokenId',
        'UnrecognizedClientException',
    }
)


def _get_or_create_client(
    service_name: str,
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None,
    region: str,
    config: Config,
    endpoint_url: str | None,
) -> Any:
    """Return a cached boto3 client or create a new one.

    Uses LRU eviction via OrderedDict.move_to_end() when cache is full.
    """
    key = (service_name, region, access_key_id, secret_access_key, session_token, endpoint_url)

    if key in _client_cache:
        _client_cache.move_to_end(key)
        return _client_cache[key]

    if len(_client_cache) >= _MAX_CACHED_CLIENTS:
        _client_cache.popitem(last=False)

    client = boto3.client(
        service_name,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token,
        config=config,
        endpoint_url=endpoint_url,
    )
    _client_cache[key] = client
    return client


def _evict_client(
    service_name: str,
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None,
    region: str,
    endpoint_url: str | None,
) -> None:
    """Remove a client from cache, e.g. after an auth error."""
    key = (service_name, region, access_key_id, secret_access_key, session_token, endpoint_url)
    _client_cache.pop(key, None)


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
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
        read_timeout=READ_TIMEOUT_SECONDS,
        retries={'max_attempts': 3, 'mode': 'adaptive'},
        user_agent_extra=get_user_agent_extra(),
    )

    with operation_timer(ir.service_name, ir.operation_python_name, region):
        client = _get_or_create_client(
            ir.service_name,
            access_key_id,
            secret_access_key,
            session_token,
            region,
            config,
            endpoint_url,
        )

        try:
            if client.can_paginate(ir.operation_python_name):
                response = build_result(
                    paginator=client.get_paginator(ir.operation_python_name),
                    service_name=ir.service_name,
                    operation_name=ir.operation_name,
                    operation_parameters=ir.parameters,
                    pagination_config=pagination_config,
                    client_side_filter=client_side_filter,
                )
            else:
                operation = getattr(client, ir.operation_python_name)
                response = operation(**parameters)

                if client_side_filter is not None:
                    response = _apply_filter(response, client_side_filter)
        except Exception as exc:
            # Evict cached client on auth errors so next call gets fresh credentials
            error_code = ''
            resp = getattr(exc, 'response', None)
            if isinstance(resp, dict):
                error_code = resp.get('Error', {}).get('Code', '')
            if error_code in _AUTH_ERROR_CODES:
                logger.info(
                    'Auth error ({}), evicting cached client for {}/{}',
                    error_code,
                    ir.service_name,
                    region,
                )
                _evict_client(
                    ir.service_name,
                    access_key_id,
                    secret_access_key,
                    session_token,
                    region,
                    endpoint_url,
                )
            raise

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
    json_compatible_response = json.loads(json.dumps(response, cls=Boto3Encoder))
    filtered_result = client_side_filter.search(json_compatible_response)
    return {'Result': filtered_result, 'ResponseMetadata': response_metadata}
