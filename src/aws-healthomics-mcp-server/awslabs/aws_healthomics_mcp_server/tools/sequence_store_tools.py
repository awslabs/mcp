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

"""Sequence store tools for the AWS HealthOmics MCP server."""

import botocore.exceptions
from awslabs.aws_healthomics_mcp_server.consts import (
    DEFAULT_MAX_RESULTS,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    get_omics_client,
)
from datetime import datetime
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from pydantic.fields import FieldInfo
from typing import Any, Dict, List, Optional


def _get_value(param):
    """Extract actual value from parameter, handling FieldInfo objects in tests."""
    if isinstance(param, FieldInfo):
        return param.default
    return param


async def list_aho_sequence_stores(
    ctx: Context,
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of sequence stores to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List available HealthOmics sequence stores.

    Args:
        ctx: MCP context for error reporting
        max_results: Maximum number of sequence stores to return
        next_token: Token for pagination from a previous response

    Returns:
        Dictionary containing sequence stores list and pagination info

    Raises:
        Exception: If there's an error listing sequence stores
    """
    try:
        client = get_omics_client()

        # Extract actual values (handles FieldInfo objects in tests)
        next_token = _get_value(next_token)

        params = {'maxResults': max_results}

        if next_token is not None:
            params['nextToken'] = next_token

        response = client.list_sequence_stores(**params)

        return {
            'sequenceStores': response.get('sequenceStores', []),
            'nextToken': response.get('nextToken'),
            'totalCount': len(response.get('sequenceStores', [])),
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to list sequence stores: {error_code} - {error_message}')

        raise Exception(f'Failed to list sequence stores: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error listing sequence stores: {str(e)}')
        raise Exception(f'Failed to list sequence stores: {str(e)}')


async def list_aho_read_sets(
    ctx: Context,
    sequence_store_id: str = Field(
        ...,
        description='ID of the sequence store to list read sets from',
    ),
    species: Optional[str] = Field(
        None,
        description='Filter by species name',
    ),
    chromosome: Optional[str] = Field(
        None,
        description='Filter by chromosome',
    ),
    uploaded_after: Optional[str] = Field(
        None,
        description='ISO datetime string to filter read sets uploaded after this time',
    ),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of read sets to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List read sets from a HealthOmics sequence store with optional filters.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: ID of the sequence store
        species: Filter by species name
        chromosome: Filter by chromosome
        uploaded_after: ISO datetime string for filtering
        max_results: Maximum number of read sets to return
        next_token: Token for pagination

    Returns:
        Dictionary containing read sets list and pagination info

    Raises:
        Exception: If there's an error listing read sets
    """
    try:
        client = get_omics_client()

        # Extract actual values (handles FieldInfo objects in tests)
        next_token = _get_value(next_token)
        species = _get_value(species)
        chromosome = _get_value(chromosome)
        uploaded_after = _get_value(uploaded_after)

        params = {'sequenceStoreId': sequence_store_id, 'maxResults': max_results}

        if next_token is not None:
            params['nextToken'] = next_token

        # Apply filters
        filters = {}

        if species is not None:
            # Note: This would need to be mapped to actual read set metadata fields
            # The exact filtering depends on how metadata is stored
            logger.info(f'Filtering by species: {species}')

        if chromosome is not None:
            logger.info(f'Filtering by chromosome: {chromosome}')

        if uploaded_after is not None:
            try:
                upload_time = datetime.fromisoformat(uploaded_after.replace('Z', '+00:00'))
                filters['createdAfter'] = upload_time
            except ValueError:
                raise Exception(f'Invalid datetime format for uploaded_after: {uploaded_after}')

        if filters:
            params['filter'] = filters

        response = client.list_read_sets(**params)

        # Post-process for additional filtering if needed
        read_sets = response.get('readSets', [])

        if species is not None or chromosome is not None:
            filtered_read_sets = []
            for read_set in read_sets:
                include = True

                # Filter by species in metadata
                if species is not None:
                    read_set_species = read_set.get('subjectId', '').lower()
                    if species.lower() not in read_set_species:
                        include = False

                # Filter by chromosome would require examining file references
                if chromosome is not None and include:
                    # This would need implementation based on HealthOmics data structure
                    pass

                if include:
                    filtered_read_sets.append(read_set)

            read_sets = filtered_read_sets

        return {
            'readSets': read_sets,
            'nextToken': response.get('nextToken'),
            'totalCount': len(read_sets),
            'sequenceStoreId': sequence_store_id,
            'appliedFilters': {
                'species': species,
                'chromosome': chromosome,
                'uploadedAfter': uploaded_after,
            },
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to list read sets: {error_code} - {error_message}')

        raise Exception(f'Failed to list read sets: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error listing read sets: {str(e)}')
        raise Exception(f'Failed to list read sets: {str(e)}')


async def get_aho_read_set(
    ctx: Context,
    sequence_store_id: str = Field(
        ...,
        description='ID of the sequence store',
    ),
    read_set_id: str = Field(
        ...,
        description='ID of the read set to retrieve',
    ),
) -> Dict[str, Any]:
    """Get detailed metadata for a specific read set.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: ID of the sequence store
        read_set_id: ID of the read set

    Returns:
        Dictionary containing read set metadata

    Raises:
        Exception: If there's an error retrieving read set metadata
    """
    try:
        client = get_omics_client()

        response = client.get_read_set_metadata(sequenceStoreId=sequence_store_id, id=read_set_id)

        return {
            'readSet': {
                'id': response.get('id'),
                'arn': response.get('arn'),
                'name': response.get('name'),
                'description': response.get('description'),
                'sampleId': response.get('sampleId'),
                'subjectId': response.get('subjectId'),
                'referenceArn': response.get('referenceArn'),
                'fileType': response.get('fileType'),
                'status': response.get('status'),
                'statusMessage': response.get('statusMessage'),
                'creationTime': response.get('creationTime'),
                'sequenceInformation': response.get('sequenceInformation'),
                'files': response.get('files'),
                'etag': response.get('etag'),
            },
            'sequenceStoreId': sequence_store_id,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to get read set metadata: {error_code} - {error_message}')

        raise Exception(f'Failed to get read set metadata: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error getting read set metadata: {str(e)}')
        raise Exception(f'Failed to get read set metadata: {str(e)}')


async def start_aho_read_set_import_job(
    ctx: Context,
    sequence_store_id: str = Field(
        ...,
        description='ID of the sequence store to import into',
    ),
    role_arn: str = Field(
        ...,
        description='ARN of the IAM role to use for the import',
    ),
    sources: List[Dict[str, Any]] = Field(
        ...,
        description='List of source files to import from S3',
    ),
    client_token: Optional[str] = Field(
        None,
        description='Client token for idempotency',
    ),
) -> Dict[str, Any]:
    """Start a read set import job from S3 sources.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: ID of the sequence store
        role_arn: ARN of the IAM role for the import
        sources: List of source file configurations
        client_token: Client token for idempotency

    Returns:
        Dictionary containing import job information

    Raises:
        Exception: If there's an error starting the import job
    """
    try:
        client = get_omics_client()

        params = {'sequenceStoreId': sequence_store_id, 'roleArn': role_arn, 'sources': sources}

        if client_token:
            params['clientToken'] = client_token

        response = client.start_read_set_import_job(**params)

        return {
            'id': response.get('id'),
            'sequenceStoreId': response.get('sequenceStoreId'),
            'roleArn': response.get('roleArn'),
            'status': response.get('status'),
            'creationTime': response.get('creationTime'),
            'sources': sources,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to start read set import job: {error_code} - {error_message}')

        raise Exception(f'Failed to start read set import job: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error starting read set import job: {str(e)}')
        raise Exception(f'Failed to start read set import job: {str(e)}')


async def get_aho_read_set_import_job(
    ctx: Context,
    sequence_store_id: str = Field(
        ...,
        description='ID of the sequence store',
    ),
    import_job_id: str = Field(
        ...,
        description='ID of the import job',
    ),
) -> Dict[str, Any]:
    """Get the status and details of a read set import job.

    Args:
        ctx: MCP context for error reporting
        sequence_store_id: ID of the sequence store
        import_job_id: ID of the import job

    Returns:
        Dictionary containing import job status and details

    Raises:
        Exception: If there's an error retrieving import job status
    """
    try:
        client = get_omics_client()

        response = client.get_read_set_import_job(
            sequenceStoreId=sequence_store_id, id=import_job_id
        )

        return {
            'id': response.get('id'),
            'sequenceStoreId': response.get('sequenceStoreId'),
            'roleArn': response.get('roleArn'),
            'status': response.get('status'),
            'statusMessage': response.get('statusMessage'),
            'creationTime': response.get('creationTime'),
            'completionTime': response.get('completionTime'),
            'sources': response.get('sources', []),
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to get read set import job: {error_code} - {error_message}')

        raise Exception(f'Failed to get read set import job: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error getting read set import job: {str(e)}')
        raise Exception(f'Failed to get read set import job: {str(e)}')


async def list_aho_read_set_import_jobs(
    ctx: Context,
    sequence_store_id: str = Field(
        ...,
        description='ID of the sequence store',
    ),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of import jobs to return',
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
        sequence_store_id: ID of the sequence store
        max_results: Maximum number of import jobs to return
        next_token: Token for pagination

    Returns:
        Dictionary containing import jobs list and pagination info

    Raises:
        Exception: If there's an error listing import jobs
    """
    try:
        client = get_omics_client()

        params = {'sequenceStoreId': sequence_store_id, 'maxResults': max_results}

        if next_token:
            params['nextToken'] = next_token

        response = client.list_read_set_import_jobs(**params)

        return {
            'importJobs': response.get('importJobs', []),
            'nextToken': response.get('nextToken'),
            'totalCount': len(response.get('importJobs', [])),
            'sequenceStoreId': sequence_store_id,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to list read set import jobs: {error_code} - {error_message}')

        raise Exception(f'Failed to list read set import jobs: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error listing read set import jobs: {str(e)}')
        raise Exception(f'Failed to list read set import jobs: {str(e)}')
