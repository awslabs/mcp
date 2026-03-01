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

"""Run cache management tools for the AWS HealthOmics MCP server."""

import uuid
from awslabs.aws_healthomics_mcp_server.consts import (
    CACHE_BEHAVIORS,
    DEFAULT_MAX_RESULTS,
    ERROR_INVALID_CACHE_BEHAVIOR,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    get_aws_session,
    get_omics_client,
)
from awslabs.aws_healthomics_mcp_server.utils.error_utils import (
    handle_tool_error,
)
from awslabs.aws_healthomics_mcp_server.utils.s3_utils import (
    parse_s3_path,
)
from botocore.exceptions import ClientError
from datetime import datetime
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional


async def create_run_cache(
    ctx: Context,
    cache_behavior: str = Field(
        ..., description='Cache behavior (CACHE_ALWAYS or CACHE_ON_FAILURE)'
    ),
    cache_s3_location: str = Field(
        ..., description='S3 URI for cache storage (e.g., s3://bucket/prefix)'
    ),
    name: Optional[str] = Field(None, description='Name for the run cache'),
    description: Optional[str] = Field(None, description='Description for the run cache'),
    tags: Optional[Dict[str, str]] = Field(None, description='Tags to apply to the run cache'),
    cache_bucket_owner_id: Optional[str] = Field(
        None,
        description='AWS account ID of the S3 bucket owner for cross-account access',
    ),
) -> Dict[str, Any]:
    """Create a new HealthOmics run cache.

    Args:
        ctx: MCP context for error reporting
        cache_behavior: Cache behavior (CACHE_ALWAYS or CACHE_ON_FAILURE)
        cache_s3_location: S3 URI for cache storage (e.g., s3://bucket/prefix)
        name: Name for the run cache
        description: Description for the run cache
        tags: Tags to apply to the run cache
        cache_bucket_owner_id: AWS account ID of the S3 bucket owner

    Returns:
        Dictionary containing the created run cache's id, arn, and status, or error dict
    """
    try:
        # Validate cache behavior
        if cache_behavior not in CACHE_BEHAVIORS:
            return await handle_tool_error(
                ctx,
                ValueError(ERROR_INVALID_CACHE_BEHAVIOR.format(', '.join(CACHE_BEHAVIORS))),
                'Error creating run cache',
            )

        # Parse and validate S3 URI
        try:
            bucket_name, _ = parse_s3_path(cache_s3_location)
        except ValueError as e:
            return await handle_tool_error(ctx, e, 'Error creating run cache')

        # Verify S3 bucket exists and is accessible
        try:
            session = get_aws_session()
            s3_client = session.client('s3')
            s3_client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                msg = f"S3 bucket '{bucket_name}' does not exist"
            elif error_code == '403':
                msg = f"Access denied to S3 bucket '{bucket_name}'"
            else:
                msg = f"Error accessing S3 bucket '{bucket_name}': {e}"
            return await handle_tool_error(ctx, ValueError(msg), 'Error creating run cache')

        # Build API params with only provided optional params
        client = get_omics_client()
        params: Dict[str, Any] = {
            'requestId': str(uuid.uuid4()),
            'cacheBehavior': cache_behavior,
            'cacheS3Location': cache_s3_location,
        }

        if name is not None:
            params['name'] = name

        if description is not None:
            params['description'] = description

        if tags is not None:
            params['tags'] = tags

        if cache_bucket_owner_id is not None:
            params['cacheBucketOwnerId'] = cache_bucket_owner_id

        logger.info(f'Creating run cache with params: {params}')
        response = client.create_run_cache(**params)

        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'status': response.get('status'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error creating run cache')


async def get_run_cache(
    ctx: Context,
    cache_id: str = Field(..., description='ID of the run cache to retrieve'),
) -> Dict[str, Any]:
    """Get details of a specific HealthOmics run cache.

    Args:
        ctx: MCP context for error reporting
        cache_id: ID of the run cache to retrieve

    Returns:
        Dictionary containing the run cache details, or error dict
    """
    try:
        client = get_omics_client()

        logger.info(f'Getting run cache: {cache_id}')
        response = client.get_run_cache(id=cache_id)

        # Serialize all datetime fields to ISO 8601 format
        result: Dict[str, Any] = {}
        for key, value in response.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting run cache')


async def list_run_caches(
    ctx: Context,
    name: Optional[str] = Field(None, description='Filter by run cache name'),
    status: Optional[str] = Field(None, description='Filter by run cache status'),
    cache_behavior: Optional[str] = Field(None, description='Filter by cache behavior'),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None, description='Token for pagination from a previous response'
    ),
) -> Dict[str, Any]:
    """List HealthOmics run caches.

    Args:
        ctx: MCP context for error reporting
        name: Filter by run cache name
        status: Filter by run cache status
        cache_behavior: Filter by cache behavior
        max_results: Maximum number of results to return
        next_token: Token for pagination from a previous response

    Returns:
        Dictionary containing run cache summaries and next token if available, or error dict
    """
    try:
        client = get_omics_client()

        params: Dict[str, Any] = {
            'maxResults': max_results,
        }

        if name is not None:
            params['name'] = name

        if status is not None:
            params['status'] = status

        if cache_behavior is not None:
            params['cacheBehavior'] = cache_behavior

        if next_token is not None:
            params['startingToken'] = next_token

        logger.info(f'Listing run caches with params: {params}')
        response = client.list_run_caches(**params)

        run_caches = []
        for item in response.get('items', []):
            cache_info: Dict[str, Any] = {}
            for key, value in item.items():
                if isinstance(value, datetime):
                    cache_info[key] = value.isoformat()
                else:
                    cache_info[key] = value
            run_caches.append(cache_info)

        result: Dict[str, Any] = {'runCaches': run_caches}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing run caches')


async def update_run_cache(
    ctx: Context,
    cache_id: str = Field(..., description='ID of the run cache to update'),
    cache_behavior: Optional[str] = Field(None, description='New cache behavior'),
    name: Optional[str] = Field(None, description='New name for the run cache'),
    description: Optional[str] = Field(None, description='New description for the run cache'),
) -> Dict[str, Any]:
    """Update an existing HealthOmics run cache.

    Args:
        ctx: MCP context for error reporting
        cache_id: ID of the run cache to update
        cache_behavior: New cache behavior
        name: New name for the run cache
        description: New description for the run cache

    Returns:
        Dictionary containing the run cache ID and update status, or error dict
    """
    try:
        client = get_omics_client()

        params: Dict[str, Any] = {
            'id': cache_id,
        }

        if cache_behavior is not None:
            params['cacheBehavior'] = cache_behavior

        if name is not None:
            params['name'] = name

        if description is not None:
            params['description'] = description

        logger.info(f'Updating run cache {cache_id} with params: {params}')
        client.update_run_cache(**params)

        return {
            'id': cache_id,
            'status': 'updated',
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error updating run cache')
