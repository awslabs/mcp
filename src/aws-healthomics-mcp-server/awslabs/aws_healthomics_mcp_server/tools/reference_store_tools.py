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

"""Reference store management tools for the AWS HealthOmics MCP server."""

import json
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_MAX_RESULTS
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_omics_client
from awslabs.aws_healthomics_mcp_server.utils.error_utils import handle_tool_error
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


async def create_reference_store(
    ctx: Context,
    name: Annotated[str, Field(description='Name for the new reference store')],
    description: Optional[str] = Field(
        None,
        description='Optional description for the reference store',
    ),
    sse_kms_key_arn: Optional[str] = Field(
        None,
        description='KMS key ARN for server-side encryption of the reference store',
    ),
    tags: Optional[str] = Field(
        None,
        description='JSON string of tags to apply to the reference store, e.g. {"key": "value"}',
    ),
) -> Dict[str, Any]:
    """Create a new HealthOmics reference store.

    Args:
        ctx: MCP context for error reporting
        name: Name for the new reference store
        description: Optional description for the reference store
        sse_kms_key_arn: KMS key ARN for server-side encryption
        tags: JSON string of tags to apply

    Returns:
        Dictionary containing the created reference store information
    """
    client = get_omics_client()

    params: Dict[str, Any] = {'name': name}

    if description:
        params['description'] = description

    if sse_kms_key_arn:
        params['sseConfig'] = {'type': 'KMS', 'keyArn': sse_kms_key_arn}

    if tags:
        try:
            params['tags'] = json.loads(tags)
        except json.JSONDecodeError as e:
            return await handle_tool_error(ctx, e, 'Error parsing tags JSON')

    try:
        logger.info(f'Creating reference store: {name}')
        response = client.create_reference_store(**params)

        creation_time = response.get('creationTime')
        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error creating reference store')


async def list_reference_stores(
    ctx: Context,
    name_filter: Optional[str] = Field(
        None,
        description='Filter stores by name',
    ),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List HealthOmics reference stores.

    Args:
        ctx: MCP context for error reporting
        name_filter: Filter stores by name
        max_results: Maximum number of results to return
        next_token: Token for pagination

    Returns:
        Dictionary containing reference store list and optional next token
    """
    client = get_omics_client()

    params: Dict[str, Any] = {'maxResults': max_results}

    if name_filter:
        params['filter'] = {'name': name_filter}

    if next_token:
        params['nextToken'] = next_token

    try:
        response = client.list_reference_stores(**params)

        stores = []
        for store in response.get('referenceStores', []):
            creation_time = store.get('creationTime')
            stores.append(
                {
                    'id': store.get('id'),
                    'arn': store.get('arn'),
                    'name': store.get('name'),
                    'description': store.get('description'),
                    'creationTime': (
                        creation_time.isoformat() if creation_time is not None else None
                    ),
                }
            )

        result: Dict[str, Any] = {'referenceStores': stores}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing reference stores')


async def get_reference_store(
    ctx: Context,
    reference_store_id: Annotated[str, Field(description='The ID of the reference store')],
) -> Dict[str, Any]:
    """Get details about a specific HealthOmics reference store.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store

    Returns:
        Dictionary containing reference store details
    """
    client = get_omics_client()

    try:
        response = client.get_reference_store(id=reference_store_id)

        creation_time = response.get('creationTime')
        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'description': response.get('description'),
            'sseConfig': response.get('sseConfig'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
            'eTag': response.get('eTag'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting reference store')


async def update_reference_store(
    ctx: Context,
    reference_store_id: Annotated[
        str, Field(description='The ID of the reference store to update')
    ],
    name: Optional[str] = Field(
        None,
        description='New name for the reference store',
    ),
    description: Optional[str] = Field(
        None,
        description='New description for the reference store',
    ),
) -> Dict[str, Any]:
    """Update a HealthOmics reference store.

    Internally fetches the current ETag before performing the update to handle
    optimistic concurrency control.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store to update
        name: New name for the reference store
        description: New description for the reference store

    Returns:
        Dictionary containing the updated reference store details
    """
    client = get_omics_client()

    try:
        # Step 1: Fetch current store to get ETag
        current = client.get_reference_store(id=reference_store_id)
        etag = current.get('eTag')

        # Step 2: Build update params with ETag
        params: Dict[str, Any] = {'id': reference_store_id}
        if etag:
            params['eTag'] = etag

        if name:
            params['name'] = name
        if description:
            params['description'] = description

        # Step 3: Call update API
        logger.info(f'Updating reference store: {reference_store_id}')
        response = client.update_reference_store(**params)

        creation_time = response.get('creationTime')
        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'description': response.get('description'),
            'sseConfig': response.get('sseConfig'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
            'eTag': response.get('eTag'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error updating reference store')


async def list_references(
    ctx: Context,
    reference_store_id: Annotated[str, Field(description='The ID of the reference store')],
    name_filter: Optional[str] = Field(
        None,
        description='Filter references by name',
    ),
    status_filter: Optional[str] = Field(
        None,
        description='Filter references by status (e.g., ACTIVE, DELETING)',
    ),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List references in a HealthOmics reference store with optional filtering.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store
        name_filter: Filter references by name
        status_filter: Filter references by status
        max_results: Maximum number of results to return
        next_token: Token for pagination

    Returns:
        Dictionary containing reference list and optional next token
    """
    client = get_omics_client()

    params: Dict[str, Any] = {
        'referenceStoreId': reference_store_id,
        'maxResults': max_results,
    }

    filter_dict: Dict[str, Any] = {}
    if name_filter:
        filter_dict['name'] = name_filter
    if status_filter:
        filter_dict['status'] = status_filter

    if filter_dict:
        params['filter'] = filter_dict

    if next_token:
        params['nextToken'] = next_token

    try:
        response = client.list_references(**params)

        references = []
        for ref in response.get('references', []):
            creation_time = ref.get('creationTime')
            references.append(
                {
                    'id': ref.get('id'),
                    'arn': ref.get('arn'),
                    'referenceStoreId': ref.get('referenceStoreId'),
                    'name': ref.get('name'),
                    'status': ref.get('status'),
                    'description': ref.get('description'),
                    'md5': ref.get('md5'),
                    'creationTime': (
                        creation_time.isoformat() if creation_time is not None else None
                    ),
                }
            )

        result: Dict[str, Any] = {'references': references}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing references')


async def get_reference_metadata(
    ctx: Context,
    reference_store_id: Annotated[str, Field(description='The ID of the reference store')],
    reference_id: Annotated[str, Field(description='The ID of the reference')],
) -> Dict[str, Any]:
    """Get metadata for a specific reference in a HealthOmics reference store.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store
        reference_id: The ID of the reference

    Returns:
        Dictionary containing reference metadata
    """
    client = get_omics_client()

    try:
        response = client.get_reference_metadata(
            referenceStoreId=reference_store_id, id=reference_id
        )

        creation_time = response.get('creationTime')
        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'status': response.get('status'),
            'description': response.get('description'),
            'md5': response.get('md5'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
            'files': response.get('files'),
            'referenceStoreId': response.get('referenceStoreId'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting reference metadata')


async def start_reference_import_job(
    ctx: Context,
    reference_store_id: Annotated[str, Field(description='The ID of the reference store')],
    role_arn: Annotated[str, Field(description='IAM role ARN for the import job')],
    sources: Annotated[
        str,
        Field(
            description='JSON list of import sources, each with sourceFile, name, '
            'and optional description, tags'
        ),
    ],
) -> Dict[str, Any]:
    """Start a reference import job to import reference files from S3 into a reference store.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store
        role_arn: IAM role ARN for the import job
        sources: JSON list of import sources

    Returns:
        Dictionary containing the import job information
    """
    client = get_omics_client()

    try:
        parsed_sources = json.loads(sources)
    except json.JSONDecodeError as e:
        return await handle_tool_error(ctx, e, 'Error parsing sources JSON')

    try:
        logger.info(f'Starting reference import job for store: {reference_store_id}')
        response = client.start_reference_import_job(
            referenceStoreId=reference_store_id,
            roleArn=role_arn,
            sources=parsed_sources,
        )

        creation_time = response.get('creationTime')
        return {
            'id': response.get('id'),
            'referenceStoreId': response.get('referenceStoreId'),
            'status': response.get('status'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error starting reference import job')


async def get_reference_import_job(
    ctx: Context,
    reference_store_id: Annotated[str, Field(description='The ID of the reference store')],
    import_job_id: Annotated[str, Field(description='The ID of the import job')],
) -> Dict[str, Any]:
    """Get details about a reference import job.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store
        import_job_id: The ID of the import job

    Returns:
        Dictionary containing the import job details
    """
    client = get_omics_client()

    try:
        response = client.get_reference_import_job(
            referenceStoreId=reference_store_id, id=import_job_id
        )

        creation_time = response.get('creationTime')
        completion_time = response.get('completionTime')
        return {
            'id': response.get('id'),
            'status': response.get('status'),
            'sources': response.get('sources'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
            'completionTime': (
                completion_time.isoformat() if completion_time is not None else None
            ),
            'roleArn': response.get('roleArn'),
            'referenceStoreId': response.get('referenceStoreId'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting reference import job')


async def list_reference_import_jobs(
    ctx: Context,
    reference_store_id: Annotated[str, Field(description='The ID of the reference store')],
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List reference import jobs for a reference store.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store
        max_results: Maximum number of results to return
        next_token: Token for pagination

    Returns:
        Dictionary containing import job list and optional next token
    """
    client = get_omics_client()

    params: Dict[str, Any] = {
        'referenceStoreId': reference_store_id,
        'maxResults': max_results,
    }

    if next_token:
        params['nextToken'] = next_token

    try:
        response = client.list_reference_import_jobs(**params)

        import_jobs = []
        for job in response.get('importJobs', []):
            creation_time = job.get('creationTime')
            completion_time = job.get('completionTime')
            import_jobs.append(
                {
                    'id': job.get('id'),
                    'referenceStoreId': job.get('referenceStoreId'),
                    'status': job.get('status'),
                    'roleArn': job.get('roleArn'),
                    'creationTime': (
                        creation_time.isoformat() if creation_time is not None else None
                    ),
                    'completionTime': (
                        completion_time.isoformat() if completion_time is not None else None
                    ),
                }
            )

        result: Dict[str, Any] = {'importJobs': import_jobs}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing reference import jobs')


async def cancel_reference_import_job(
    ctx: Context,
    reference_store_id: Annotated[str, Field(description='The ID of the reference store')],
    import_job_id: Annotated[str, Field(description='The ID of the import job to cancel')],
) -> Dict[str, Any]:
    """Cancel a running reference import job.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store
        import_job_id: The ID of the import job to cancel

    Returns:
        Dictionary containing cancellation confirmation
    """
    client = get_omics_client()

    try:
        logger.info(f'Cancelling reference import job: {import_job_id}')
        client.cancel_reference_import_job(referenceStoreId=reference_store_id, id=import_job_id)

        return {'message': f'Import job {import_job_id} cancelled successfully'}
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error cancelling reference import job')
