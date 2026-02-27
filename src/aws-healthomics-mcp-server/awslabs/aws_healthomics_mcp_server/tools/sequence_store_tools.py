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

"""Sequence store management tools for the AWS HealthOmics MCP server."""

import json
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_MAX_RESULTS
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_omics_client
from awslabs.aws_healthomics_mcp_server.utils.error_utils import handle_tool_error
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


async def create_sequence_store(
    ctx: Context,
    name: Annotated[str, Field(description='Name for the new sequence store')],
    description: Optional[str] = Field(
        None,
        description='Optional description for the sequence store',
    ),
    sse_kms_key_arn: Optional[str] = Field(
        None,
        description='KMS key ARN for server-side encryption of the sequence store',
    ),
    fallback_location: Optional[str] = Field(
        None,
        description='S3 URI for the fallback location of the sequence store',
    ),
    tags: Optional[str] = Field(
        None,
        description='JSON string of tags to apply to the sequence store, e.g. {"key": "value"}',
    ),
) -> Dict[str, Any]:
    """Create a new HealthOmics sequence store.

    Args:
        ctx: MCP context for error reporting
        name: Name for the new sequence store
        description: Optional description for the sequence store
        sse_kms_key_arn: KMS key ARN for server-side encryption
        fallback_location: S3 URI for the fallback location
        tags: JSON string of tags to apply

    Returns:
        Dictionary containing the created sequence store information
    """
    client = get_omics_client()

    params: Dict[str, Any] = {'name': name}

    if description:
        params['description'] = description

    if sse_kms_key_arn:
        params['sseConfig'] = {'type': 'KMS', 'keyArn': sse_kms_key_arn}

    if fallback_location:
        params['fallbackLocation'] = fallback_location

    if tags:
        try:
            params['tags'] = json.loads(tags)
        except json.JSONDecodeError as e:
            return await handle_tool_error(ctx, e, 'Error parsing tags JSON')

    try:
        logger.info(f'Creating sequence store: {name}')
        response = client.create_sequence_store(**params)

        creation_time = response.get('creationTime')
        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error creating sequence store')


async def list_sequence_stores(
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
    """List HealthOmics sequence stores.

    Args:
        ctx: MCP context for error reporting
        name_filter: Filter stores by name
        max_results: Maximum number of results to return
        next_token: Token for pagination

    Returns:
        Dictionary containing sequence store list and optional next token
    """
    client = get_omics_client()

    params: Dict[str, Any] = {'maxResults': max_results}

    if name_filter:
        params['filter'] = {'name': name_filter}

    if next_token:
        params['nextToken'] = next_token

    try:
        response = client.list_sequence_stores(**params)

        stores = []
        for store in response.get('sequenceStores', []):
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
                    'fallbackLocation': store.get('fallbackLocation'),
                }
            )

        result: Dict[str, Any] = {'sequenceStores': stores}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing sequence stores')


async def get_sequence_store(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
) -> Dict[str, Any]:
    """Get details about a specific HealthOmics sequence store.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store

    Returns:
        Dictionary containing sequence store details
    """
    client = get_omics_client()

    try:
        response = client.get_sequence_store(id=sequence_store_id)

        creation_time = response.get('creationTime')
        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'description': response.get('description'),
            'sseConfig': response.get('sseConfig'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
            'fallbackLocation': response.get('fallbackLocation'),
            'eTag': response.get('eTag'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting sequence store')


async def update_sequence_store(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store to update')],
    name: Optional[str] = Field(
        None,
        description='New name for the sequence store',
    ),
    description: Optional[str] = Field(
        None,
        description='New description for the sequence store',
    ),
    fallback_location: Optional[str] = Field(
        None,
        description='New S3 URI for the fallback location',
    ),
) -> Dict[str, Any]:
    """Update a HealthOmics sequence store.

    Internally fetches the current ETag before performing the update to handle
    optimistic concurrency control.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store to update
        name: New name for the sequence store
        description: New description for the sequence store
        fallback_location: New S3 URI for the fallback location

    Returns:
        Dictionary containing the updated sequence store details
    """
    client = get_omics_client()

    try:
        # Step 1: Fetch current store to get ETag
        current = client.get_sequence_store(id=sequence_store_id)
        etag = current.get('eTag')

        # Step 2: Build update params with ETag
        params: Dict[str, Any] = {'id': sequence_store_id}
        if etag:
            params['eTag'] = etag

        if name:
            params['name'] = name
        if description:
            params['description'] = description
        if fallback_location:
            params['fallbackLocation'] = fallback_location

        # Step 3: Call update API
        logger.info(f'Updating sequence store: {sequence_store_id}')
        response = client.update_sequence_store(**params)

        creation_time = response.get('creationTime')
        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'description': response.get('description'),
            'sseConfig': response.get('sseConfig'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
            'fallbackLocation': response.get('fallbackLocation'),
            'eTag': response.get('eTag'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error updating sequence store')


async def list_read_sets(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
    sample_id: Optional[str] = Field(
        None,
        description='Filter by sample ID',
    ),
    subject_id: Optional[str] = Field(
        None,
        description='Filter by subject ID',
    ),
    reference_arn: Optional[str] = Field(
        None,
        description='Filter by reference ARN',
    ),
    status: Optional[str] = Field(
        None,
        description='Filter by read set status (e.g., ACTIVE, ARCHIVED)',
    ),
    file_type: Optional[str] = Field(
        None,
        description='Filter by file type (FASTQ, BAM, CRAM, or UBAM)',
    ),
    created_after: Optional[str] = Field(
        None,
        description='Filter for read sets created after this ISO 8601 datetime',
    ),
    created_before: Optional[str] = Field(
        None,
        description='Filter for read sets created before this ISO 8601 datetime',
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
    """List read sets in a HealthOmics sequence store with optional filtering.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        sample_id: Filter by sample ID
        subject_id: Filter by subject ID
        reference_arn: Filter by reference ARN
        status: Filter by read set status
        file_type: Filter by file type
        created_after: Filter for read sets created after this datetime
        created_before: Filter for read sets created before this datetime
        max_results: Maximum number of results to return
        next_token: Token for pagination

    Returns:
        Dictionary containing read set list and optional next token
    """
    client = get_omics_client()

    params: Dict[str, Any] = {
        'sequenceStoreId': sequence_store_id,
        'maxResults': max_results,
    }

    filter_dict: Dict[str, Any] = {}
    if sample_id:
        filter_dict['sampleId'] = sample_id
    if subject_id:
        filter_dict['subjectId'] = subject_id
    if reference_arn:
        filter_dict['referenceArn'] = reference_arn
    if status:
        filter_dict['status'] = status
    if file_type:
        filter_dict['fileType'] = file_type
    if created_after:
        filter_dict['createdAfter'] = created_after
    if created_before:
        filter_dict['createdBefore'] = created_before

    if filter_dict:
        params['filter'] = filter_dict

    if next_token:
        params['nextToken'] = next_token

    try:
        response = client.list_read_sets(**params)

        read_sets = []
        for rs in response.get('readSets', []):
            creation_time = rs.get('creationTime')
            read_sets.append(
                {
                    'id': rs.get('id'),
                    'arn': rs.get('arn'),
                    'sequenceStoreId': rs.get('sequenceStoreId'),
                    'name': rs.get('name'),
                    'status': rs.get('status'),
                    'fileType': rs.get('fileType'),
                    'subjectId': rs.get('subjectId'),
                    'sampleId': rs.get('sampleId'),
                    'referenceArn': rs.get('referenceArn'),
                    'creationTime': (
                        creation_time.isoformat() if creation_time is not None else None
                    ),
                }
            )

        result: Dict[str, Any] = {'readSets': read_sets}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing read sets')


async def get_read_set_metadata(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
    read_set_id: Annotated[str, Field(description='The ID of the read set')],
) -> Dict[str, Any]:
    """Get metadata for a specific read set in a HealthOmics sequence store.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        read_set_id: The ID of the read set

    Returns:
        Dictionary containing read set metadata
    """
    client = get_omics_client()

    try:
        response = client.get_read_set_metadata(sequenceStoreId=sequence_store_id, id=read_set_id)

        creation_time = response.get('creationTime')
        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'status': response.get('status'),
            'fileType': response.get('fileType'),
            'sequenceStoreId': response.get('sequenceStoreId'),
            'subjectId': response.get('subjectId'),
            'sampleId': response.get('sampleId'),
            'referenceArn': response.get('referenceArn'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
            'sequenceInformation': response.get('sequenceInformation'),
            'files': response.get('files'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting read set metadata')


async def start_read_set_import_job(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
    role_arn: Annotated[str, Field(description='IAM role ARN for the import job')],
    sources: Annotated[
        str,
        Field(
            description='JSON list of import sources, each with sourceFileType, sourceFiles, '
            'and optional referenceArn, sampleId, subjectId, name, tags'
        ),
    ],
    tags: Optional[str] = Field(
        None,
        description='JSON string of tags to apply to the import job, e.g. {"key": "value"}',
    ),
) -> Dict[str, Any]:
    """Start a read set import job to import genomic files from S3 into a sequence store.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        role_arn: IAM role ARN for the import job
        sources: JSON list of import sources
        tags: JSON string of tags to apply

    Returns:
        Dictionary containing the import job information
    """
    client = get_omics_client()

    try:
        parsed_sources = json.loads(sources)
    except json.JSONDecodeError as e:
        return await handle_tool_error(ctx, e, 'Error parsing sources JSON')

    params: Dict[str, Any] = {
        'sequenceStoreId': sequence_store_id,
        'roleArn': role_arn,
        'sources': parsed_sources,
    }

    if tags:
        try:
            params['tags'] = json.loads(tags)
        except json.JSONDecodeError as e:
            return await handle_tool_error(ctx, e, 'Error parsing tags JSON')

    try:
        logger.info(f'Starting read set import job for store: {sequence_store_id}')
        response = client.start_read_set_import_job(**params)

        creation_time = response.get('creationTime')
        return {
            'id': response.get('id'),
            'sequenceStoreId': response.get('sequenceStoreId'),
            'status': response.get('status'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error starting read set import job')


async def get_read_set_import_job(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
    import_job_id: Annotated[str, Field(description='The ID of the import job')],
) -> Dict[str, Any]:
    """Get details about a read set import job.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        import_job_id: The ID of the import job

    Returns:
        Dictionary containing the import job details
    """
    client = get_omics_client()

    try:
        response = client.get_read_set_import_job(
            sequenceStoreId=sequence_store_id, id=import_job_id
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
            'sequenceStoreId': response.get('sequenceStoreId'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting read set import job')


async def list_read_set_import_jobs(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
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
    """List read set import jobs for a sequence store.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        max_results: Maximum number of results to return
        next_token: Token for pagination

    Returns:
        Dictionary containing import job list and optional next token
    """
    client = get_omics_client()

    params: Dict[str, Any] = {
        'sequenceStoreId': sequence_store_id,
        'maxResults': max_results,
    }

    if next_token:
        params['nextToken'] = next_token

    try:
        response = client.list_read_set_import_jobs(**params)

        import_jobs = []
        for job in response.get('importJobs', []):
            creation_time = job.get('creationTime')
            completion_time = job.get('completionTime')
            import_jobs.append(
                {
                    'id': job.get('id'),
                    'sequenceStoreId': job.get('sequenceStoreId'),
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
        return await handle_tool_error(ctx, e, 'Error listing read set import jobs')


async def cancel_read_set_import_job(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
    import_job_id: Annotated[str, Field(description='The ID of the import job to cancel')],
) -> Dict[str, Any]:
    """Cancel a running read set import job.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        import_job_id: The ID of the import job to cancel

    Returns:
        Dictionary containing cancellation confirmation
    """
    client = get_omics_client()

    try:
        logger.info(f'Cancelling read set import job: {import_job_id}')
        client.cancel_read_set_import_job(sequenceStoreId=sequence_store_id, id=import_job_id)

        return {'message': f'Import job {import_job_id} cancelled successfully'}
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error cancelling read set import job')


async def start_read_set_export_job(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
    destination_s3_uri: Annotated[str, Field(description='S3 URI for the export destination')],
    role_arn: Annotated[str, Field(description='IAM role ARN for the export job')],
    read_set_ids: Annotated[
        str,
        Field(description='JSON list of read set IDs to export, e.g. ["id1", "id2"]'),
    ],
) -> Dict[str, Any]:
    """Start a read set export job to export read sets from a sequence store to S3.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        destination_s3_uri: S3 URI for the export destination
        role_arn: IAM role ARN for the export job
        read_set_ids: JSON list of read set IDs to export

    Returns:
        Dictionary containing the export job information
    """
    client = get_omics_client()

    try:
        parsed_ids = json.loads(read_set_ids)
    except json.JSONDecodeError as e:
        return await handle_tool_error(ctx, e, 'Error parsing read_set_ids JSON')

    sources = [{'readSetId': id} for id in parsed_ids]

    try:
        logger.info(f'Starting read set export job for store: {sequence_store_id}')
        response = client.start_read_set_export_job(
            sequenceStoreId=sequence_store_id,
            destination={'s3': {'s3Uri': destination_s3_uri}},
            roleArn=role_arn,
            sources=sources,
        )

        return {
            'id': response.get('id'),
            'sequenceStoreId': response.get('sequenceStoreId'),
            'status': response.get('status'),
            'destination': response.get('destination'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error starting read set export job')


async def get_read_set_export_job(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
    export_job_id: Annotated[str, Field(description='The ID of the export job')],
) -> Dict[str, Any]:
    """Get details about a read set export job.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        export_job_id: The ID of the export job

    Returns:
        Dictionary containing the export job details
    """
    client = get_omics_client()

    try:
        response = client.get_read_set_export_job(
            sequenceStoreId=sequence_store_id, id=export_job_id
        )

        creation_time = response.get('creationTime')
        completion_time = response.get('completionTime')
        return {
            'id': response.get('id'),
            'status': response.get('status'),
            'destination': response.get('destination'),
            'creationTime': creation_time.isoformat() if creation_time is not None else None,
            'completionTime': (
                completion_time.isoformat() if completion_time is not None else None
            ),
            'sequenceStoreId': response.get('sequenceStoreId'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting read set export job')


async def list_read_set_export_jobs(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
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
    """List read set export jobs for a sequence store.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        max_results: Maximum number of results to return
        next_token: Token for pagination

    Returns:
        Dictionary containing export job list and optional next token
    """
    client = get_omics_client()

    params: Dict[str, Any] = {
        'sequenceStoreId': sequence_store_id,
        'maxResults': max_results,
    }

    if next_token:
        params['nextToken'] = next_token

    try:
        response = client.list_read_set_export_jobs(**params)

        export_jobs = []
        for job in response.get('exportJobs', []):
            creation_time = job.get('creationTime')
            completion_time = job.get('completionTime')
            export_jobs.append(
                {
                    'id': job.get('id'),
                    'sequenceStoreId': job.get('sequenceStoreId'),
                    'status': job.get('status'),
                    'destination': job.get('destination'),
                    'creationTime': (
                        creation_time.isoformat() if creation_time is not None else None
                    ),
                    'completionTime': (
                        completion_time.isoformat() if completion_time is not None else None
                    ),
                }
            )

        result: Dict[str, Any] = {'exportJobs': export_jobs}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing read set export jobs')


async def activate_read_sets(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
    read_set_ids: Annotated[
        str,
        Field(description='JSON list of read set IDs to activate, e.g. ["id1", "id2"]'),
    ],
) -> Dict[str, Any]:
    """Activate archived read sets in a HealthOmics sequence store.

    Starts an activation job to move read sets from archive storage back to active storage.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        read_set_ids: JSON list of read set IDs to activate

    Returns:
        Dictionary containing the activation job information
    """
    client = get_omics_client()

    try:
        parsed_ids = json.loads(read_set_ids)
    except json.JSONDecodeError as e:
        return await handle_tool_error(ctx, e, 'Error parsing read_set_ids JSON')

    sources = [{'readSetId': id} for id in parsed_ids]

    try:
        logger.info(f'Activating read sets in store: {sequence_store_id}')
        response = client.start_read_set_activation_job(
            sequenceStoreId=sequence_store_id, sources=sources
        )

        return {
            'sequenceStoreId': response.get('sequenceStoreId'),
            'status': response.get('status'),
            'readSetIds': parsed_ids,
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error activating read sets')


async def archive_read_sets(
    ctx: Context,
    sequence_store_id: Annotated[str, Field(description='The ID of the sequence store')],
    read_set_ids: Annotated[
        str,
        Field(description='JSON list of read set IDs to archive, e.g. ["id1", "id2"]'),
    ],
) -> Dict[str, Any]:
    """Archive read sets in a HealthOmics sequence store.

    Starts an archive job to move read sets to lower-cost archive storage.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: The ID of the sequence store
        read_set_ids: JSON list of read set IDs to archive

    Returns:
        Dictionary containing the archive job information
    """
    client = get_omics_client()

    try:
        parsed_ids = json.loads(read_set_ids)
    except json.JSONDecodeError as e:
        return await handle_tool_error(ctx, e, 'Error parsing read_set_ids JSON')

    sources = [{'readSetId': id} for id in parsed_ids]

    try:
        logger.info(f'Archiving read sets in store: {sequence_store_id}')
        response = client.start_read_set_archive_job(
            sequenceStoreId=sequence_store_id, sources=sources
        )

        return {
            'sequenceStoreId': response.get('sequenceStoreId'),
            'status': response.get('status'),
            'readSetIds': parsed_ids,
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error archiving read sets')
