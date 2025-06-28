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
import time
from ..aws.client_side_filtering import handle_client_side_query
from ..aws.pagination import build_result
from ..aws.resource_counting import count_resources_via_pagination
from ..aws.services import (
    extract_pagination_config,
    update_parameters_with_max_results,
)
from ..common.command import IRCommand
from ..common.helpers import operation_timer
from botocore.config import Config
from loguru import logger
from typing import Any


TIMEOUT_AFTER_SECONDS = 10

# Get package version for user agent
try:
    PACKAGE_VERSION = importlib.metadata.version('awslabs.aws_mcp_server')
except importlib.metadata.PackageNotFoundError:
    PACKAGE_VERSION = 'unknown'


def interpret(
    ir: IRCommand,
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None,
    region: str,
    client_side_query: str | None = None,
    max_results: int | None = None,
    max_tokens: int | None = None,
    is_counting: bool | None = None,
) -> dict[str, Any]:
    """Interpret the given intermediate representation into boto3 calls.

    The function returns the response from the operation indicated by the
    intermediate representation.
    """
    logger.info("Interpreting IR in '{}' region", region)

    config_result = extract_pagination_config(
        ir.parameters, ir.service_name, ir.operation_name, max_results
    )
    parameters = config_result.parameters
    pagination_config = config_result.pagination_config
    max_results = pagination_config.get('MaxItems')

    with operation_timer(ir.service_name, ir.operation_python_name):
        config = Config(
            region_name=region,
            connect_timeout=TIMEOUT_AFTER_SECONDS,
            read_timeout=TIMEOUT_AFTER_SECONDS,
            retries={'max_attempts': 1},
            user_agent_extra=f'AWSMCP/{PACKAGE_VERSION}',
        )

        client = boto3.client(
            ir.service_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
            config=config,
        )

        start_time = time.time()
        if client.can_paginate(ir.operation_python_name):
            response = build_result(
                paginator=client.get_paginator(ir.operation_python_name),
                service_name=ir.service_name,
                operation_name=ir.operation_name,
                operation_parameters=ir.parameters,
                pagination_config=pagination_config,
                max_tokens=max_tokens,
            )

            if is_counting:
                logger.info('This is a counting request, adding resource count info')

                operation_time = time.time() - start_time
                count_result = count_resources_via_pagination(
                    client,
                    response,
                    operation_time,
                    ir.service_name,
                    ir.operation_name,
                    ir.operation_python_name,
                    parameters,
                )

                if count_result is not None:
                    total_resource_count, count_status = count_result
                    resource_count_info = {
                        'resource_count': total_resource_count,
                        'status': count_status,
                    }

                    response['resource_count_info'] = resource_count_info
        else:
            operation = getattr(client, ir.operation_python_name)
            # Inject max results into the call if the call permits it
            parameters = update_parameters_with_max_results(
                ir.parameters,
                ir.service_name,
                ir.operation_name,
                max_results,
            )
            response = operation(**parameters)

        response = handle_client_side_query(
            response, client_side_query, ir.service_name, ir.operation_name
        )

        return response
