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
from awslabs.aws_healthomics_mcp_server.models.store import ReferenceImportSource
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_omics_client
from awslabs.aws_healthomics_mcp_server.utils.error_utils import handle_tool_error
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


def _resolve_reference_store_id(client: Any, reference_store_id: Optional[str] = None) -> str:
    """Resolve the reference store ID.

    AWS HealthOmics allows only one reference store per account per region.
    If no reference_store_id is provided, automatically discovers it by
    listing reference stores.

    Args:
        client: The HealthOmics client
        reference_store_id: Optional explicit reference store ID

    Returns:
        The resolved reference store ID

    Raises:
        ValueError: If no reference store exists or ID cannot be resolved
    """
    if reference_store_id:
        return reference_store_id

    response = client.list_reference_stores(maxResults=1)
    stores = response.get('referenceStores', [])
    if not stores:
        raise ValueError('No reference store found in this account/region.')
    resolved_id = stores[0]['id']
    logger.info(f'Auto-resolved reference store ID: {resolved_id}')
    return resolved_id


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
    reference_store_id: Optional[str] = Field(
        None,
        description='The ID of the reference store. If not provided, auto-resolves the single store in the account/region.',
    ),
) -> Dict[str, Any]:
    """Get details about a specific HealthOmics reference store.

    AWS HealthOmics allows only one reference store per account per region.
    If reference_store_id is not provided, it will be automatically resolved.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store (auto-resolved if omitted)

    Returns:
        Dictionary containing reference store details
    """
    client = get_omics_client()

    try:
        reference_store_id = _resolve_reference_store_id(client, reference_store_id)
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


async def list_references(
    ctx: Context,
    reference_store_id: Optional[str] = Field(
        None,
        description='The ID of the reference store. If not provided, auto-resolves the single store in the account/region.',
    ),
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

    AWS HealthOmics allows only one reference store per account per region.
    If reference_store_id is not provided, it will be automatically resolved.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store (auto-resolved if omitted)
        name_filter: Filter references by name
        status_filter: Filter references by status
        max_results: Maximum number of results to return
        next_token: Token for pagination

    Returns:
        Dictionary containing reference list and optional next token
    """
    client = get_omics_client()

    try:
        reference_store_id = _resolve_reference_store_id(client, reference_store_id)
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error resolving reference store ID')

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
    reference_id: Annotated[str, Field(description='The ID of the reference')],
    reference_store_id: Optional[str] = Field(
        None,
        description='The ID of the reference store. If not provided, auto-resolves the single store in the account/region.',
    ),
) -> Dict[str, Any]:
    """Get metadata for a specific reference in a HealthOmics reference store.

    AWS HealthOmics allows only one reference store per account per region.
    If reference_store_id is not provided, it will be automatically resolved.

    Args:
        ctx: MCP context for error reporting
        reference_id: The ID of the reference
        reference_store_id: The ID of the reference store (auto-resolved if omitted)

    Returns:
        Dictionary containing reference metadata
    """
    client = get_omics_client()

    try:
        reference_store_id = _resolve_reference_store_id(client, reference_store_id)
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
    role_arn: Annotated[str, Field(description='IAM role ARN for the import job')],
    sources: Annotated[
        str,
        Field(
            description='JSON list of import sources. Each source requires: '
            'sourceFile (S3 URI to a FASTA reference file), name. '
            'Optional fields: description, tags. '
            'Example: [{"sourceFile": "s3://bucket/GRCh38.fasta", '
            '"name": "GRCh38", '
            '"description": "Human reference genome build 38", '
            '"tags": {"build": "38", "species": "human"}}]'
        ),
    ],
    reference_store_id: Optional[str] = Field(
        None,
        description='The ID of the reference store. If not provided, auto-resolves the single store in the account/region.',
    ),
) -> Dict[str, Any]:
    """Start a reference import job to import reference files from S3 into a reference store.

    AWS HealthOmics allows only one reference store per account per region.
    If reference_store_id is not provided, it will be automatically resolved.

    Each source in the sources list is validated against the ReferenceImportSource model
    and must include:
      - sourceFile: S3 URI pointing to a FASTA reference file (e.g. "s3://bucket/GRCh38.fasta")
      - name: A name for the reference (e.g. "GRCh38")
      - description (optional): A description of the reference
      - tags (optional): Key-value tags as {"key": "value"}

    Example sources JSON:
        [{"sourceFile": "s3://bucket/GRCh38.fasta", "name": "GRCh38",
          "description": "Human reference genome build 38",
          "tags": {"build": "38", "species": "human"}}]

    Args:
        ctx: MCP context for error reporting
        role_arn: IAM role ARN for the import job
        sources: JSON list of import sources (validated against ReferenceImportSource)
        reference_store_id: The ID of the reference store (auto-resolved if omitted)

    Returns:
        Dictionary containing the import job information
    """
    client = get_omics_client()

    try:
        parsed_sources = json.loads(sources)
    except json.JSONDecodeError as e:
        return await handle_tool_error(ctx, e, 'Error parsing sources JSON')

    # Validate each source against the ReferenceImportSource model
    try:
        validated = [ReferenceImportSource(**s) for s in parsed_sources]
        parsed_sources = [s.model_dump(exclude_none=True) for s in validated]
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error validating import sources')

    try:
        reference_store_id = _resolve_reference_store_id(client, reference_store_id)
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
    import_job_id: Annotated[str, Field(description='The ID of the import job')],
    reference_store_id: Optional[str] = Field(
        None,
        description='The ID of the reference store. If not provided, auto-resolves the single store in the account/region.',
    ),
) -> Dict[str, Any]:
    """Get details about a reference import job.

    AWS HealthOmics allows only one reference store per account per region.
    If reference_store_id is not provided, it will be automatically resolved.

    Args:
        ctx: MCP context for error reporting
        import_job_id: The ID of the import job
        reference_store_id: The ID of the reference store (auto-resolved if omitted)

    Returns:
        Dictionary containing the import job details
    """
    client = get_omics_client()

    try:
        reference_store_id = _resolve_reference_store_id(client, reference_store_id)
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
    reference_store_id: Optional[str] = Field(
        None,
        description='The ID of the reference store. If not provided, auto-resolves the single store in the account/region.',
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
    """List reference import jobs for a reference store.

    AWS HealthOmics allows only one reference store per account per region.
    If reference_store_id is not provided, it will be automatically resolved.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: The ID of the reference store (auto-resolved if omitted)
        max_results: Maximum number of results to return
        next_token: Token for pagination

    Returns:
        Dictionary containing import job list and optional next token
    """
    client = get_omics_client()

    try:
        reference_store_id = _resolve_reference_store_id(client, reference_store_id)
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error resolving reference store ID')

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
