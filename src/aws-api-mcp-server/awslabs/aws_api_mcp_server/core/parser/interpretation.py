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
import importlib.metadata
from ..aws.pagination import build_result
from ..aws.services import (
    extract_pagination_config,
)
from ..common.command import IRCommand
from ..common.config import OPT_IN_TELEMETRY, READ_OPERATIONS_ONLY_MODE
from ..common.helpers import operation_timer
from botocore.config import Config
from jmespath.parser import ParsedResult
from typing import Any


TIMEOUT_AFTER_SECONDS = 10

# Get package version for user agent
try:
    PACKAGE_VERSION = importlib.metadata.version('awslabs.aws_api_mcp_server')
except importlib.metadata.PackageNotFoundError:
    PACKAGE_VERSION = 'unknown'


def interpret(
    ir: IRCommand,
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None,
    region: str,
    client_side_filter: ParsedResult | None = None,
    max_results: int | None = None,
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
        retries={'max_attempts': 1},
        user_agent_extra=_get_user_agent_extra(),
    )

    with operation_timer(ir.service_name, ir.operation_python_name, region):
        client = boto3.client(
            ir.service_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
            config=config,
        )

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

        return response


def _get_user_agent_extra() -> str:
    user_agent_extra = f'awslabs/mcp/AWS-API-MCP-server/{PACKAGE_VERSION}'
    if not OPT_IN_TELEMETRY:
        return user_agent_extra
    # ReadOperationsOnly mode
    user_agent_extra += f' cfg/ro#{"1" if READ_OPERATIONS_ONLY_MODE else "0"}'
    return user_agent_extra


def _apply_filter(response: dict[str, Any], client_side_filter: ParsedResult) -> dict[str, Any]:
    response_metadata = response.get('ResponseMetadata')
    filtered_result = client_side_filter.search(response)
    return {'Result': filtered_result, 'ResponseMetadata': response_metadata}
