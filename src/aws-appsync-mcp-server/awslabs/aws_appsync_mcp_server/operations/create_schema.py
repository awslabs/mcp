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

"""Create Schema operation for AWS AppSync MCP Server."""

import asyncio
import time
from awslabs.aws_appsync_mcp_server.helpers import get_appsync_client, handle_exceptions
from awslabs.aws_appsync_mcp_server.validators import validate_graphql_schema
from loguru import logger
from typing import Dict


@handle_exceptions
async def create_schema_operation(
    api_id: str,
    definition: str,
) -> Dict:
    """Execute create_schema operation with polling for completion."""
    # Validate schema before sending to AWS
    issues = validate_graphql_schema(definition)
    if issues:
        raise ValueError(f'Schema validation failed: {"; ".join(issues)}')

    client = get_appsync_client()

    # Start schema creation
    response = client.start_schema_creation(apiId=api_id, definition=definition)

    logger.info(f'Schema creation started with status: {response.get("status")}')

    # Poll for completion with timeout
    start_time = time.time()
    timeout = 300  # 5 minutes

    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError(f'Schema creation timed out after {timeout} seconds')

        status_response = client.get_schema_creation_status(apiId=api_id)
        status = status_response.get('status')

        logger.info(f'Schema creation status: {status}')

        if status in ['SUCCESS', 'FAILED', 'ACTIVE', 'NOT_APPLICABLE']:
            return {
                'status': status,
                'details': status_response.get('details'),
            }

        await asyncio.sleep(2)
